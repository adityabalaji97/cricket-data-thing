"""
Helpers for extracting toss + XI context from Cricinfo links.

Primary strategy:
1) Parse ESPN event id from the Cricinfo URL
2) Query ESPN summary JSON endpoint
3) Heuristically extract teams, toss decision, venue, XI, impact subs

If any critical step fails, returns source='failed' with empty payload fields
so the frontend can fall back to manual entry without breaking UX.
"""

from __future__ import annotations

import json
import logging
import re
from html import unescape
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from services.matchups import _canonicalize_players

logger = logging.getLogger(__name__)

ESPN_CRICKET_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/cricket/summary?event={event_id}"
DEFAULT_TIMEOUT_SECONDS = 5.0
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _dedupe_names(names: List[str]) -> List[str]:
    deduped: List[str] = []
    seen = set()
    for raw in names or []:
        name = _safe_str(raw)
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(name)
    return deduped


def _extract_event_id(cricinfo_url: str) -> Optional[str]:
    parsed = urlparse(cricinfo_url or "")
    path = parsed.path or ""

    # Query-string variants first.
    qs = parse_qs(parsed.query or "")
    for key in ("event", "event_id", "matchId", "match_id", "gameId"):
        values = qs.get(key) or []
        if values and str(values[0]).isdigit():
            return str(values[0])

    # Common Cricinfo path patterns.
    for pattern in (
        r"/live-cricket-score/(\d+)",
        r"/match/(?:[^/]+-)?(\d+)",
        r"-(\d{6,})$",
    ):
        match = re.search(pattern, path)
        if match:
            return match.group(1)

    fallback_hits = re.findall(r"-(\d{6,})(?:/|$)", path)
    if fallback_hits:
        return fallback_hits[-1]

    return None


def _fetch_json(url: str, timeout_seconds: float) -> Optional[Dict[str, Any]]:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("Cricinfo scraper fetch failed for %s: %s", url, exc)
        return None


def _fetch_html(url: str, timeout_seconds: float) -> Optional[str]:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return response.read().decode("utf-8", errors="ignore")
    except (URLError, HTTPError, TimeoutError) as exc:
        logger.warning("Cricinfo scraper HTML fetch failed for %s: %s", url, exc)
        return None


def _extract_team_name(team_payload: Dict[str, Any]) -> str:
    return (
        _safe_str(team_payload.get("displayName"))
        or _safe_str(team_payload.get("shortDisplayName"))
        or _safe_str(team_payload.get("name"))
        or _safe_str(team_payload.get("location"))
    )


def _extract_team_pair(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], List[Dict[str, Any]]]:
    competitions = payload.get("competitions") or []
    comp = competitions[0] if competitions else {}
    competitors = comp.get("competitors") or []
    if len(competitors) < 2:
        return None, None, []

    # Prefer stable home/away ordering when available.
    def sort_key(item: Dict[str, Any]) -> int:
        home_away = _safe_str(item.get("homeAway")).lower()
        return 0 if home_away == "home" else 1

    competitors = sorted(competitors, key=sort_key)
    team1 = _extract_team_name(competitors[0].get("team") or competitors[0])
    team2 = _extract_team_name(competitors[1].get("team") or competitors[1])
    return team1 or None, team2 or None, competitors


def _extract_player_names_from_competitor(competitor: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    xi: List[str] = []
    impact_subs: List[str] = []

    containers = []
    for key in ("roster", "lineup", "athletes", "players"):
        value = competitor.get(key)
        if isinstance(value, list):
            containers.append(value)

    for group_key in ("statistics", "leaders"):
        group = competitor.get(group_key)
        if isinstance(group, list):
            for row in group:
                athletes = (row or {}).get("athletes")
                if isinstance(athletes, list):
                    containers.append(athletes)

    for container in containers:
        for row in container:
            if not isinstance(row, dict):
                continue
            athlete = row.get("athlete") if isinstance(row.get("athlete"), dict) else row
            name = (
                _safe_str(athlete.get("displayName"))
                or _safe_str(athlete.get("fullName"))
                or _safe_str(athlete.get("shortName"))
                or _safe_str(athlete.get("name"))
            )
            if not name:
                continue

            label_blob = " ".join(
                _safe_str(row.get(k))
                for k in ("position", "type", "status", "note", "role")
            ).lower()
            if "sub" in label_blob or "impact" in label_blob:
                impact_subs.append(name)
            else:
                xi.append(name)

    return _dedupe_names(xi), _dedupe_names(impact_subs)


def _parse_toss_from_text(text_value: str) -> Tuple[Optional[str], Optional[str]]:
    text = _safe_str(text_value)
    if not text:
        return None, None
    match = re.search(
        r"(?P<winner>.+?) won the toss and (?:elected|chose|decided) to (?P<decision>bat|field|bowl)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None, None
    winner = _safe_str(match.group("winner"))
    decision_raw = _safe_str(match.group("decision")).lower()
    decision = "field" if decision_raw == "bowl" else decision_raw
    return winner or None, decision or None


def _extract_toss(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    competitions = payload.get("competitions") or []
    comp = competitions[0] if competitions else {}

    note_candidates: List[str] = []
    for note in comp.get("notes") or []:
        if isinstance(note, dict):
            note_candidates.append(_safe_str(note.get("headline") or note.get("text")))
        elif isinstance(note, str):
            note_candidates.append(_safe_str(note))

    status = payload.get("status") or {}
    for key in ("detail", "shortDetail"):
        val = _safe_str(((status.get("type") or {}).get(key)) or status.get(key))
        if val:
            note_candidates.append(val)

    for candidate in note_candidates:
        winner, decision = _parse_toss_from_text(candidate)
        if winner and decision:
            return winner, decision
    return None, None


def _extract_basic_html_setup(cricinfo_url: str, timeout_seconds: float) -> Dict[str, Any]:
    html = _fetch_html(cricinfo_url, timeout_seconds=timeout_seconds)
    if not html:
        return {}

    title_match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    title = unescape(title_match.group(1).strip()) if title_match else ""
    cleaned_title = re.sub(r"\s+", " ", title).strip()

    team1 = team2 = None
    vs_match = re.search(r"([A-Za-z .&'-]+)\s+vs\.?\s+([A-Za-z .&'-]+)", cleaned_title, flags=re.IGNORECASE)
    if vs_match:
        team1 = _safe_str(vs_match.group(1))
        team2 = _safe_str(vs_match.group(2))

    toss_winner, toss_decision = _parse_toss_from_text(html)

    venue = None
    venue_match = re.search(r"Venue[:\s]+([^<\n\r]+)", html, flags=re.IGNORECASE)
    if venue_match:
        venue = _safe_str(unescape(venue_match.group(1)))

    match_date = None
    date_match = re.search(r'"startDate"\s*:\s*"([^"]+)"', html)
    if date_match:
        match_date = _safe_str(date_match.group(1))

    batting_first_team = None
    if toss_winner and toss_decision and team1 and team2:
        toss_norm = toss_winner.lower()
        team1_norm = team1.lower()
        team2_norm = team2.lower()
        if toss_norm == team1_norm:
            batting_first_team = team1 if toss_decision == "bat" else team2
        elif toss_norm == team2_norm:
            batting_first_team = team2 if toss_decision == "bat" else team1

    if not any([team1, team2, toss_winner, toss_decision, venue, match_date]):
        return {}

    return {
        "team1": team1,
        "team2": team2,
        "toss_winner": toss_winner,
        "toss_decision": toss_decision,
        "batting_first_team": batting_first_team,
        "venue": venue,
        "match_date": match_date,
    }


def _canonicalize_if_possible(players: List[str], db) -> List[str]:
    if not players:
        return []
    if db is None:
        return _dedupe_names(players)
    try:
        canonical = _canonicalize_players(players, db)
        return _dedupe_names(canonical if canonical else players)
    except Exception:
        return _dedupe_names(players)


def scrape_match_setup(
    cricinfo_url: str,
    *,
    db=None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    base_payload: Dict[str, Any] = {
        "toss_winner": None,
        "toss_decision": None,
        "batting_first_team": None,
        "team1": None,
        "team2": None,
        "team1_xi": [],
        "team2_xi": [],
        "impact_subs": [],
        "venue": None,
        "match_date": None,
        "source": "failed",
        "event_id": None,
        "error": None,
    }

    event_id = _extract_event_id(cricinfo_url)
    if not event_id:
        base_payload["error"] = "Could not parse ESPN event id from URL"
        return base_payload
    base_payload["event_id"] = event_id

    summary_url = ESPN_CRICKET_SUMMARY_URL.format(event_id=event_id)
    payload = _fetch_json(summary_url, timeout_seconds=timeout_seconds)
    if not payload:
        fallback = _extract_basic_html_setup(cricinfo_url, timeout_seconds=timeout_seconds)
        if fallback:
            base_payload.update(
                {
                    **fallback,
                    "source": "html",
                    "error": None,
                }
            )
            return base_payload
        base_payload["error"] = "Failed to fetch ESPN summary payload"
        return base_payload

    team1, team2, competitors = _extract_team_pair(payload)
    base_payload["team1"] = team1
    base_payload["team2"] = team2

    if not competitors:
        fallback = _extract_basic_html_setup(cricinfo_url, timeout_seconds=timeout_seconds)
        if fallback:
            base_payload.update(
                {
                    **fallback,
                    "source": "html",
                    "error": None,
                }
            )
            return base_payload
        base_payload["error"] = "No competitors found in ESPN payload"
        return base_payload

    team1_xi, team1_subs = _extract_player_names_from_competitor(competitors[0])
    team2_xi, team2_subs = _extract_player_names_from_competitor(competitors[1])
    impact_subs = _dedupe_names([*team1_subs, *team2_subs])

    toss_winner, toss_decision = _extract_toss(payload)
    batting_first_team: Optional[str] = None
    if toss_winner and toss_decision and team1 and team2:
        toss_winner_norm = toss_winner.lower()
        team1_norm = team1.lower()
        team2_norm = team2.lower()
        if toss_winner_norm == team1_norm:
            batting_first_team = team1 if toss_decision == "bat" else team2
        elif toss_winner_norm == team2_norm:
            batting_first_team = team2 if toss_decision == "bat" else team1

    game_info = payload.get("gameInfo") or {}
    venue_obj = game_info.get("venue") or {}
    venue = _safe_str(venue_obj.get("fullName") or venue_obj.get("name"))
    header_competitions = (payload.get("header") or {}).get("competitions") or []
    header_date = None
    if header_competitions and isinstance(header_competitions[0], dict):
        header_date = header_competitions[0].get("date")
    match_date = _safe_str(header_date or payload.get("date"))

    base_payload.update(
        {
            "toss_winner": toss_winner,
            "toss_decision": toss_decision,
            "batting_first_team": batting_first_team,
            "team1_xi": _canonicalize_if_possible(team1_xi, db),
            "team2_xi": _canonicalize_if_possible(team2_xi, db),
            "impact_subs": _canonicalize_if_possible(impact_subs, db),
            "venue": venue or None,
            "match_date": match_date or None,
            "source": "espn_api",
            "error": None,
        }
    )
    return base_payload
