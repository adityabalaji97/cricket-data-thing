"""
Fixture scraper service for upcoming cricket matches.

Uses ESPN's public scoreboard header endpoint and returns a small normalized payload
for the landing page fixture cards.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import json
import logging
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from models import teams_mapping, INTERNATIONAL_TEAMS_RANKED

logger = logging.getLogger(__name__)

ESPN_CRICKET_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/personalized/v2/scoreboard/header"
    "?sport=cricket&region=in&lang=en"
)
ESPN_LOOKAHEAD_DAYS = 4  # today + next 3 days

# Translate common ESPN venue strings to the DB venue names used in this app.
VENUE_NAME_MAP = {
    "M.Chinnaswamy Stadium, Bengaluru": "M Chinnaswamy Stadium, Bangalore",
    "M Chinnaswamy Stadium, Bengaluru": "M Chinnaswamy Stadium, Bangalore",
    "Arun Jaitley Stadium, Delhi": "Feroz Shah Kotla",
}

_fixture_cache: Dict[str, Any] = {
    "timestamp": None,
    "fixtures": [],
}
_CACHE_TTL_DEFAULT = timedelta(hours=1)
_CACHE_TTL_LIVE = timedelta(minutes=3)

TOP_T20_LEAGUE_KEYWORDS = [
    "indian premier league",
    "ipl",
    "pakistan super league",
    "psl",
    "big bash league",
    "bbl",
    "sa20",
    "international league t20",
    "ilt20",
]

TOP_T20I_TEAMS = set(INTERNATIONAL_TEAMS_RANKED[:20])
_TEAM_ABBR_TO_NAME = {abbr: name for name, abbr in teams_mapping.items()}
_ESPN_TEAM_NAME_ALIASES = {
    "United Arab Emirates": "UAE",
    "United States": "USA",
    "Papua New Guinea": "Papua New Guinea",
}


def _cached_fixtures_valid() -> bool:
    ts = _fixture_cache.get("timestamp")
    if not isinstance(ts, datetime):
        return False
    fixtures = _fixture_cache.get("fixtures") or []
    has_live = any(bool(f.get("is_live")) for f in fixtures if isinstance(f, dict))
    ttl = _CACHE_TTL_LIVE if has_live else _CACHE_TTL_DEFAULT
    return datetime.now(timezone.utc) - ts < ttl


def _normalize_venue(raw_venue: Optional[str]) -> Optional[str]:
    if not raw_venue:
        return raw_venue
    return VENUE_NAME_MAP.get(raw_venue, raw_venue)


def _team_abbreviation(team_obj: Dict[str, Any], display_name: str) -> str:
    if display_name in teams_mapping:
        return teams_mapping[display_name]
    abbr = (team_obj or {}).get("abbreviation")
    if abbr:
        return abbr.upper()
    short_name = (team_obj or {}).get("shortDisplayName")
    if short_name:
        return short_name.upper()
    return display_name


def _normalize_team_name_for_ranking(team_obj: Dict[str, Any], display_name: str) -> str:
    if display_name in TOP_T20I_TEAMS:
        return display_name
    if display_name in _ESPN_TEAM_NAME_ALIASES:
        return _ESPN_TEAM_NAME_ALIASES[display_name]

    abbr = (team_obj or {}).get("abbreviation")
    if abbr:
        mapped = _TEAM_ABBR_TO_NAME.get(str(abbr).upper())
        if mapped:
            return mapped

    return display_name


def _parse_event_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _extract_events(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    # ESPN structures vary; support a few shapes.
    if isinstance(payload.get("events"), list):
        return payload["events"]

    content = payload.get("content") or {}
    sb = content.get("scoreboard") or {}
    for key in ("events", "evts"):
        if isinstance(sb.get(key), list):
            return sb[key]

    # Some variants embed in sports[0].leagues[*].events
    events: List[Dict[str, Any]] = []
    for sport in payload.get("sports", []) or []:
        for league in sport.get("leagues", []) or []:
            for event in league.get("events", []) or []:
                if isinstance(event, dict):
                    events.append(event)
    return events


def _scoreboard_url_for_date(target_date: datetime) -> str:
    return f"{ESPN_CRICKET_SCOREBOARD_URL}&dates={target_date.strftime('%Y%m%d')}"


def _event_is_upcoming_or_live(event: Dict[str, Any], now_utc: datetime) -> bool:
    status_type: Dict[str, Any] = {}
    status = event.get("status")
    if isinstance(status, dict):
        status_type = status.get("type") or {}
    elif isinstance(event.get("fullStatus"), dict):
        status_type = (event.get("fullStatus") or {}).get("type") or {}

    # Prefer explicit status fields when present
    if status_type.get("completed") is True:
        return False
    state = str(status_type.get("state") or "").lower()
    if state and state not in {"pre", "scheduled", "in"}:
        return False

    event_dt = _parse_event_datetime(event.get("date"))
    if event_dt and event_dt < now_utc - timedelta(hours=6):
        return False

    return True


def _is_t20i_event(event: Dict[str, Any], competitors: List[Dict[str, Any]]) -> bool:
    event_class = event.get("class") or {}
    class_card = str(event_class.get("generalClassCard") or "").upper()
    is_t20i = False
    if class_card == "T20I":
        is_t20i = True
    intl_class_id = str(event_class.get("internationalClassId") or "")
    if intl_class_id == "3":
        is_t20i = True
    if not is_t20i:
        is_t20i = (
            all(bool(c.get("isNational")) for c in competitors if isinstance(c, dict))
            and str(event.get("eventType") or "").upper() == "T20"
        )
    if not is_t20i:
        return False

    team_names: List[str] = []
    for c in competitors:
        if not isinstance(c, dict):
            continue
        t = c.get("team") or c
        raw_name = t.get("displayName") or t.get("shortDisplayName") or t.get("location")
        if not raw_name:
            continue
        team_names.append(_normalize_team_name_for_ranking(t, raw_name))

    if len(team_names) < 2:
        return False

    return all(name in TOP_T20I_TEAMS for name in team_names[:2])


def _is_top_t20_league_event(series_name: str, event: Dict[str, Any], competitors: List[Dict[str, Any]]) -> bool:
    if any(bool(c.get("isNational")) for c in competitors if isinstance(c, dict)):
        return False
    if str(event.get("eventType") or "").upper() != "T20":
        return False
    hay = (series_name or "").lower()
    return any(keyword in hay for keyword in TOP_T20_LEAGUE_KEYWORDS)


def _is_allowed_event(event: Dict[str, Any], competitors: List[Dict[str, Any]], series_name: str) -> bool:
    return _is_t20i_event(event, competitors) or _is_top_t20_league_event(series_name, event, competitors)


def _extract_fixture(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    competitions = event.get("competitions") or []
    comp = competitions[0] if competitions else {}
    competitors = comp.get("competitors") or event.get("competitors") or []
    if len(competitors) < 2:
        return None

    # ESPN competitor ordering is usually stable, but sort by home/away flag if available.
    def competitor_sort_key(c: Dict[str, Any]) -> int:
        home_away = str(c.get("homeAway") or "").lower()
        return 0 if home_away == "home" else 1

    competitors_sorted = sorted(competitors, key=competitor_sort_key)
    c1, c2 = competitors_sorted[0], competitors_sorted[1]
    t1 = c1.get("team") or c1
    t2 = c2.get("team") or c2

    team1 = t1.get("displayName") or t1.get("shortDisplayName") or t1.get("location")
    team2 = t2.get("displayName") or t2.get("shortDisplayName") or t2.get("location")
    if not team1 or not team2:
        return None

    event_dt = _parse_event_datetime(event.get("date"))
    date_str = event_dt.date().isoformat() if event_dt else None
    time_str = event_dt.strftime("%H:%M") if event_dt else None

    venue_obj = comp.get("venue") or {}
    venue_name = venue_obj.get("fullName") or venue_obj.get("name") or event.get("location")
    if venue_obj.get("address") and venue_obj["address"].get("city"):
        city = venue_obj["address"]["city"]
        if venue_name and city and city not in venue_name:
            venue_name = f"{venue_name}, {city}"

    series_name = (
        comp.get("series", {}).get("shortName")
        or comp.get("series", {}).get("name")
        or (event.get("group") or {}).get("shortName")
        or event.get("shortName")
        or event.get("name")
    )

    status_obj = event.get("fullStatus") or {}
    status_type = (status_obj.get("type") or {}) if isinstance(status_obj, dict) else {}
    state = str(status_type.get("state") or event.get("status") or "").lower()
    is_live = state == "in"

    if not _is_allowed_event(event, competitors_sorted, str(series_name or "")):
        return None

    return {
        "date": date_str,
        "time": time_str,
        "venue": _normalize_venue(venue_name),
        "team1": team1,
        "team2": team2,
        "team1_abbr": _team_abbreviation(t1, team1),
        "team2_abbr": _team_abbreviation(t2, team2),
        "series": series_name,
        "event_type": event.get("eventType"),
        "is_live": is_live,
        "status": state or "pre",
        "status_text": (status_obj.get("summary") or event.get("summary") or ("Live" if is_live else "Scheduled")),
        "match_id": event.get("id"),
    }


def _fetch_from_espn() -> List[Dict[str, Any]]:
    def _fetch_payload(url: str) -> Dict[str, Any]:
        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; CricketDataThing/1.0)",
                "Accept": "application/json",
            },
        )
        with urlopen(req, timeout=15) as resp:
            body = resp.read()
        return json.loads(body.decode("utf-8"))

    now_utc = datetime.now(timezone.utc)
    all_events: List[Dict[str, Any]] = []
    seen_event_ids = set()

    # Fetch today + next few days so we don't drop to only the single live match.
    for day_offset in range(ESPN_LOOKAHEAD_DAYS):
        target_dt = now_utc + timedelta(days=day_offset)
        try:
            payload = _fetch_payload(_scoreboard_url_for_date(target_dt))
        except Exception as e:
            logger.warning(f"Skipping ESPN fixtures date fetch for {target_dt.date()}: {e}")
            continue
        for event in _extract_events(payload):
            if not isinstance(event, dict):
                continue
            event_id = event.get("id")
            if event_id and event_id in seen_event_ids:
                continue
            if event_id:
                seen_event_ids.add(event_id)
            all_events.append(event)

    # Fallback to the original header feed if the date-based fetch returns nothing.
    if not all_events:
        try:
            payload = _fetch_payload(ESPN_CRICKET_SCOREBOARD_URL)
            for event in _extract_events(payload):
                if not isinstance(event, dict):
                    continue
                event_id = event.get("id")
                if event_id and event_id in seen_event_ids:
                    continue
                if event_id:
                    seen_event_ids.add(event_id)
                all_events.append(event)
        except Exception as e:
            logger.warning(f"ESPN header fallback fetch failed: {e}")

    events = all_events
    fixtures: List[Dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        if not _event_is_upcoming_or_live(event, now_utc):
            continue
        fixture = _extract_fixture(event)
        if fixture and fixture.get("date") and fixture.get("team1") and fixture.get("team2"):
            fixtures.append(fixture)

    fixtures.sort(
        key=lambda item: (
            0 if item.get("is_live") else 1,
            item.get("date") or "9999-12-31",
            item.get("time") or "99:99",
        )
    )
    return fixtures


def fetch_upcoming_fixtures(count: int = 5) -> List[Dict[str, Any]]:
    """
    Return normalized upcoming fixtures, cached for 1 hour.
    Falls back to [] on error.
    """
    count = max(1, min(int(count), 20))

    try:
        if _cached_fixtures_valid():
            return (_fixture_cache.get("fixtures") or [])[:count]

        fixtures = _fetch_from_espn()
        _fixture_cache["timestamp"] = datetime.now(timezone.utc)
        _fixture_cache["fixtures"] = fixtures
        return fixtures[:count]
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as e:
        logger.warning(f"Fixture scraper failed; returning empty list: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected fixture scraper error: {e}", exc_info=True)
        return []
