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

from models import teams_mapping

logger = logging.getLogger(__name__)

ESPN_CRICKET_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/personalized/v2/scoreboard/header"
    "?sport=cricket&region=in&lang=en"
)

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
_CACHE_TTL = timedelta(hours=1)


def _cached_fixtures_valid() -> bool:
    ts = _fixture_cache.get("timestamp")
    if not isinstance(ts, datetime):
        return False
    return datetime.now(timezone.utc) - ts < _CACHE_TTL


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


def _event_is_upcoming(event: Dict[str, Any], now_utc: datetime) -> bool:
    status = event.get("status") or {}
    status_type = status.get("type") or {}

    # Prefer explicit status fields when present
    if status_type.get("completed") is True:
        return False
    state = str(status_type.get("state") or "").lower()
    if state and state not in {"pre", "scheduled"}:
        return False

    event_dt = _parse_event_datetime(event.get("date"))
    if event_dt and event_dt < now_utc - timedelta(hours=6):
        return False

    return True


def _extract_fixture(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    competitions = event.get("competitions") or []
    comp = competitions[0] if competitions else {}
    competitors = comp.get("competitors") or []
    if len(competitors) < 2:
        return None

    # ESPN competitor ordering is usually stable, but sort by home/away flag if available.
    def competitor_sort_key(c: Dict[str, Any]) -> int:
        home_away = str(c.get("homeAway") or "").lower()
        return 0 if home_away == "home" else 1

    competitors_sorted = sorted(competitors, key=competitor_sort_key)
    c1, c2 = competitors_sorted[0], competitors_sorted[1]
    t1 = c1.get("team") or {}
    t2 = c2.get("team") or {}

    team1 = t1.get("displayName") or t1.get("shortDisplayName")
    team2 = t2.get("displayName") or t2.get("shortDisplayName")
    if not team1 or not team2:
        return None

    event_dt = _parse_event_datetime(event.get("date"))
    date_str = event_dt.date().isoformat() if event_dt else None
    time_str = event_dt.strftime("%H:%M") if event_dt else None

    venue_obj = comp.get("venue") or {}
    venue_name = venue_obj.get("fullName") or venue_obj.get("name")
    if venue_obj.get("address") and venue_obj["address"].get("city"):
        city = venue_obj["address"]["city"]
        if venue_name and city and city not in venue_name:
            venue_name = f"{venue_name}, {city}"

    series_name = (
        comp.get("series", {}).get("shortName")
        or comp.get("series", {}).get("name")
        or event.get("shortName")
        or event.get("name")
    )

    return {
        "date": date_str,
        "time": time_str,
        "venue": _normalize_venue(venue_name),
        "team1": team1,
        "team2": team2,
        "team1_abbr": _team_abbreviation(t1, team1),
        "team2_abbr": _team_abbreviation(t2, team2),
        "series": series_name,
        "match_id": event.get("id"),
    }


def _fetch_from_espn() -> List[Dict[str, Any]]:
    req = Request(
        ESPN_CRICKET_SCOREBOARD_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; CricketDataThing/1.0)",
            "Accept": "application/json",
        },
    )
    with urlopen(req, timeout=15) as resp:
        body = resp.read()
    payload = json.loads(body.decode("utf-8"))
    events = _extract_events(payload)
    now_utc = datetime.now(timezone.utc)

    fixtures: List[Dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        if not _event_is_upcoming(event, now_utc):
            continue
        fixture = _extract_fixture(event)
        if fixture and fixture.get("date") and fixture.get("team1") and fixture.get("team2"):
            fixtures.append(fixture)

    fixtures.sort(key=lambda item: (item.get("date") or "9999-12-31", item.get("time") or "99:99"))
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
