"""
Fantasy Team Planner Service

Provides multi-match squad optimization for IPL 2026 season-long fantasy
(fantasy.iplt20.com). Uses matchup data + current rosters to recommend
optimal 11-player squads across upcoming fixtures.

Squad rules (fantasy.iplt20.com):
  - 11 players, 100 credit budget
  - Min 1 WK, 3 BAT, 1 AR, 3 BOWL
  - Max 7 from one team, max 4 overseas
  - Captain 2x, Vice-captain 1.5x
  - 160 transfers across league stage
"""

from __future__ import annotations

import json
import logging
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ipl_rosters import get_ipl_roster, get_team_abbrev_from_name, IPL_2026_ROSTERS
from services.matchups import (
    get_team_matchups_service,
    _clamp,
    _calculate_batting_projection_points,
    _calculate_bowling_projection_points,
    _RUN_POINT, _BOUNDARY_BONUS, _SIX_BONUS, _RUNS_25_BONUS, _RUNS_50_BONUS,
    _SR_ABOVE_170, _SR_150_TO_170, _SR_130_TO_150, _SR_60_TO_70, _SR_50_TO_60, _SR_BELOW_50,
    _DOT_BALL_POINT, _WICKET_POINT,
    _ECONOMY_BELOW_5, _ECONOMY_5_TO_6, _ECONOMY_6_TO_7,
    _ECONOMY_10_TO_11, _ECONOMY_11_TO_12, _ECONOMY_ABOVE_12,
)
from services.team_roster import get_team_roster_service

logger = logging.getLogger(__name__)

SCHEDULE_PATH = Path(__file__).resolve().parent.parent / "data" / "ipl_2026_schedule.json"
PRICES_PATH = Path(__file__).resolve().parent.parent / "data" / "ipl_2026_player_prices.json"

# Role mapping from ipl_rosters.py roles to fantasy categories
ROLE_MAP = {
    "batter": "BAT",
    "bowler": "BOWL",
    "all-rounder": "AR",
    "wicket-keeper": "WK",
}

# Cached player prices {name_lower: {credits, role, team, is_overseas, ...}}
_PLAYER_PRICES: Dict[str, Dict] = {}

# Cached matchup payloads by fixture identity.
_MATCHUP_CACHE: Dict[str, Dict[str, Any]] = {}
_MATCHUP_CACHE_TTL_SECONDS = 600
_MAX_MATCHES_AHEAD = 5


# Point constants are imported from services.matchups


def _default_matchup_start_date() -> date:
    """Return Jan 1 of (current_year - 1), matching the venue page's date filter."""
    return date(date.today().year - 1, 1, 1)


def _load_player_prices() -> Dict[str, Dict]:
    """Load player prices from JSON, cached after first call."""
    global _PLAYER_PRICES
    if _PLAYER_PRICES:
        return _PLAYER_PRICES
    try:
        with open(PRICES_PATH) as f:
            data = json.load(f)
        for p in data.get("players", []):
            _PLAYER_PRICES[p["name"].lower()] = p
        logger.info("Loaded %d player prices", len(_PLAYER_PRICES))
    except FileNotFoundError:
        logger.warning("Player prices file not found: %s", PRICES_PATH)
    return _PLAYER_PRICES


def get_all_players() -> List[Dict[str, Any]]:
    """Return all players from prices file for autocomplete."""
    prices = _load_player_prices()
    players = [
        {
            "name": p.get("name"),
            "team": p.get("team"),
            "role": ROLE_MAP.get(p.get("role", ""), "BAT"),
            "credits": p.get("credits", 7.0),
        }
        for p in prices.values()
        if p.get("name") and p.get("team")
    ]
    players.sort(key=lambda p: (p["name"], p["team"]))
    return players


def _resolve_player_price_entry(name: str) -> Optional[Dict[str, Any]]:
    prices = _load_player_prices()
    entry = prices.get(name.lower())
    if entry:
        return entry
    for p in prices.values():
        if p.get("name_fantasy", "").lower() == name.lower():
            return p
    return None


def _resolve_fantasy_role(name: str, roster_role: str, display_name: Optional[str] = None) -> str:
    lookup_name = display_name or name
    price_entry = _resolve_player_price_entry(lookup_name)
    if not price_entry and lookup_name != name:
        price_entry = _resolve_player_price_entry(name)
    if price_entry and price_entry.get("role"):
        return ROLE_MAP.get(price_entry["role"], "BAT")
    return ROLE_MAP.get(roster_role, "BAT")


def _matchup_cache_key(fixture: Dict[str, Any]) -> str:
    return f"{fixture.get('match_num')}|{fixture.get('date')}|{fixture.get('team1')}|{fixture.get('team2')}"


def _get_cached_matchup_payload(cache_key: str) -> Optional[Dict[str, Any]]:
    item = _MATCHUP_CACHE.get(cache_key)
    if not item:
        return None
    if time.time() - item.get("ts", 0) > _MATCHUP_CACHE_TTL_SECONDS:
        _MATCHUP_CACHE.pop(cache_key, None)
        return None
    return item.get("data")


def _set_cached_matchup_payload(cache_key: str, matchup_data: Dict[str, Any]) -> None:
    _MATCHUP_CACHE[cache_key] = {
        "ts": time.time(),
        "data": matchup_data,
    }


def _lineup_source_rank(source: Optional[str]) -> int:
    ranking = {
        "none": 0,
        "recent_10": 1,
        "pre_season": 2,
        "match_data": 3,
        "custom": 4,
    }
    return ranking.get(source or "none", 0)


def _merge_lineup_source(existing: Optional[str], new_value: Optional[str]) -> str:
    if _lineup_source_rank(new_value) > _lineup_source_rank(existing):
        return new_value or "none"
    return existing or "none"


def _get_team_players_for_projection(team_abbrev: str, db, lookback_days: int = 30) -> Dict[str, Any]:
    """
    Resolve team players for planner projections.

    IPL teams use roster service first (match_data/pre_season fallback), then static roster.
    """
    source = "none"
    players: List[Dict[str, str]] = []

    normalized_abbrev = get_team_abbrev_from_name(team_abbrev) or team_abbrev
    is_ipl_team = bool(get_ipl_roster(normalized_abbrev))

    if is_ipl_team and db is not None:
        try:
            roster = get_team_roster_service(team_name=normalized_abbrev, db=db, lookback_days=lookback_days)
            if roster.get("players"):
                players = [
                    {"name": p.get("name"), "role": p.get("role", "batter"),
                     "display_name": p.get("display_name", p.get("name"))}
                    for p in roster["players"] if p.get("name")
                ]
                source = roster.get("source", "match_data")
        except Exception as exc:
            logger.warning("Roster service lookup failed for %s: %s", team_abbrev, exc)

    if not players:
        static_roster = get_ipl_roster(normalized_abbrev)
        if static_roster and static_roster.get("players"):
            players = static_roster["players"]
            source = "pre_season"

    return {
        "players": players,
        "source": source,
    }


def _infer_roster_from_matchup(team_data: Dict[str, Any]) -> List[Dict[str, str]]:
    players = team_data.get("players") or []
    batting = team_data.get("batting_matchups") or {}
    bowling = team_data.get("bowling_consolidated") or {}
    inferred: List[Dict[str, str]] = []
    for name in players:
        batting_stats = (batting.get(name) or {}).get("Overall") if isinstance(batting.get(name), dict) else None
        bowling_stats = bowling.get(name) or {}
        has_batting = bool(batting_stats)
        has_bowling = float(bowling_stats.get("balls", 0) or 0.0) > 0 or float(bowling_stats.get("wickets", 0) or 0.0) > 0
        role = "all-rounder" if has_batting and has_bowling else ("bowler" if has_bowling else "batter")
        inferred.append({"name": name, "role": role})
    return inferred


def _build_normalized_match_points(matchup_data: Dict[str, Any], team_key: str) -> Dict[str, Dict[str, float]]:
    team_data = ((matchup_data or {}).get(team_key) or {})
    players = team_data.get("players") or []
    batting = team_data.get("batting_matchups") or {}
    bowling = team_data.get("bowling_consolidated") or {}
    fantasy_top = ((matchup_data or {}).get("fantasy_analysis") or {}).get("top_fantasy_picks") or []
    raw_lookup = {
        p.get("player_name"): float(p.get("expected_points", 0) or 0.0)
        for p in fantasy_top
        if p.get("team") == team_key and p.get("player_name")
    }

    projections: Dict[str, Dict[str, float]] = {}
    for player in players:
        overall_stats = ((batting.get(player) or {}).get("Overall")) if isinstance(batting.get(player), dict) else None
        batting_result = _calculate_batting_projection_points(overall_stats or {})
        bowling_result = _calculate_bowling_projection_points(bowling.get(player) or {})
        total_points = batting_result["points"] + bowling_result["points"]

        confidence_parts = [c for c in [batting_result["confidence"], bowling_result["confidence"]] if c > 0]
        confidence = sum(confidence_parts) / len(confidence_parts) if confidence_parts else 0.0

        projections[player] = {
            "expected_points": round(total_points, 1),
            "confidence": round(confidence, 2),
            "expected_points_raw": round(raw_lookup.get(player, 0.0), 1),
        }

    return projections


def _last_name_key(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    parts = [part for part in str(name).replace(".", " ").split() if part]
    if not parts:
        return None
    return parts[-1].lower()


def _build_last_name_lookup(names: List[str]) -> Dict[str, str]:
    grouped: Dict[str, Dict[str, str]] = {}
    for name in names:
        key = _last_name_key(name)
        if not key:
            continue
        normalized = name.strip()
        if not normalized:
            continue
        grouped.setdefault(key, {})
        grouped[key].setdefault(normalized.lower(), normalized)
    return {
        key: next(iter(value_map.values()))
        for key, value_map in grouped.items()
        if len(value_map) == 1
    }


def _zero_projection() -> Dict[str, float]:
    return {
        "expected_points": 0.0,
        "confidence": 0.0,
        "expected_points_raw": 0.0,
    }


def _resolve_player_projection(
    points_map: Dict[str, Dict[str, float]],
    name: str,
    display_name: Optional[str] = None,
    canonical_last_name_lookup: Optional[Dict[str, str]] = None,
) -> Dict[str, float]:
    for candidate_name in (display_name, name):
        if candidate_name and candidate_name in points_map:
            return points_map[candidate_name]

    if canonical_last_name_lookup:
        for candidate_name in (display_name, name):
            candidate_last_name = _last_name_key(candidate_name)
            if not candidate_last_name:
                continue
            canonical_name = canonical_last_name_lookup.get(candidate_last_name)
            if canonical_name and canonical_name in points_map:
                return points_map[canonical_name]

    return _zero_projection()


def get_player_credit(name: str) -> float:
    """Get a player's fantasy credit value. Returns 7.0 as default."""
    prices = _load_player_prices()
    entry = prices.get(name.lower())
    if entry:
        return entry["credits"]
    # Check fantasy_name variant
    for p in prices.values():
        if p.get("name_fantasy", "").lower() == name.lower():
            return p["credits"]
    return 7.0  # default for unknown players


def is_overseas(name: str) -> bool:
    """Check if a player is overseas using price data."""
    prices = _load_player_prices()
    entry = prices.get(name.lower())
    if entry:
        return entry.get("is_overseas", False)
    return False


def _load_schedule() -> List[Dict[str, Any]]:
    """Load IPL 2026 schedule from JSON file."""
    try:
        with open(SCHEDULE_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Schedule file not found: %s", SCHEDULE_PATH)
        return []


def get_schedule_with_density(
    from_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return full schedule with per-team fixture density analysis.
    """
    schedule = _load_schedule()
    if not schedule:
        return {"fixtures": [], "team_density": {}}

    today = from_date or date.today().isoformat()

    # Build per-team fixture lists
    team_fixtures: Dict[str, List[Dict]] = {}
    for team_abbrev in IPL_2026_ROSTERS:
        team_fixtures[team_abbrev] = []

    for match in schedule:
        for team_key in ("team1", "team2"):
            team = match[team_key]
            if team in team_fixtures:
                team_fixtures[team].append(match)

    # Compute density metrics
    team_density = {}
    for team, fixtures in team_fixtures.items():
        upcoming = [f for f in fixtures if f["date"] >= today]
        next_match = upcoming[0] if upcoming else None

        # Matches in next 7 / 14 / 21 days
        def _count_in_days(days: int) -> int:
            cutoff = (date.fromisoformat(today) + timedelta(days=days)).isoformat()
            return len([f for f in upcoming if f["date"] <= cutoff])

        team_density[team] = {
            "total_matches": len(fixtures),
            "remaining_matches": len(upcoming),
            "next_match_date": next_match["date"] if next_match else None,
            "next_match_num": next_match["match_num"] if next_match else None,
            "next_opponent": (
                next_match["team2"] if next_match and next_match["team1"] == team
                else (next_match["team1"] if next_match else None)
            ),
            "matches_in_7_days": _count_in_days(7),
            "matches_in_14_days": _count_in_days(14),
            "matches_in_21_days": _count_in_days(21),
        }

    return {
        "fixtures": schedule,
        "team_density": team_density,
        "as_of": today,
    }


def _get_upcoming_fixtures(matches_ahead: int = 3, from_date: Optional[str] = None) -> List[Dict]:
    """Get the next N fixtures from today."""
    bounded_matches = max(1, min(_MAX_MATCHES_AHEAD, int(matches_ahead or 3)))
    schedule = _load_schedule()
    today = from_date or date.today().isoformat()
    upcoming = [f for f in schedule if f["date"] >= today]
    return upcoming[:bounded_matches]


def _get_team_players(team_abbrev: str) -> List[Dict[str, str]]:
    """Get current roster for a team."""
    roster = get_ipl_roster(team_abbrev)
    if not roster:
        return []
    return roster["players"]


def get_fantasy_recommendations(
    db,
    matches_ahead: int = 3,
    current_team: Optional[List[str]] = None,
    transfers_remaining: int = 160,
    matches_played: int = 0,
    from_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate fantasy squad recommendations for the next N matches.

    1. Gets upcoming fixtures
    2. For each fixture, gets both teams' rosters and matchup data
    3. Calculates expected fantasy points per player
    4. Runs multi-match optimizer with constraints
    """
    upcoming = _get_upcoming_fixtures(matches_ahead, from_date)
    if not upcoming:
        return {"error": "No upcoming fixtures found", "recommendations": []}

    # Collect all players with expected points across matches
    player_scores: Dict[str, Dict[str, Any]] = {}
    match_details = []
    lineup_sources: Dict[str, str] = {}

    for fixture in upcoming:
        t1 = fixture["team1"]
        t2 = fixture["team2"]
        venue = fixture.get("venue_db", fixture.get("venue", ""))
        t1_meta = _get_team_players_for_projection(t1, db)
        t2_meta = _get_team_players_for_projection(t2, db)
        t1_roster = t1_meta.get("players", [])
        t2_roster = t2_meta.get("players", [])
        lineup_sources[t1] = _merge_lineup_source(lineup_sources.get(t1), t1_meta.get("source", "none"))
        lineup_sources[t2] = _merge_lineup_source(lineup_sources.get(t2), t2_meta.get("source", "none"))

        match_info = {
            "match_num": fixture["match_num"],
            "date": fixture["date"],
            "team1": t1,
            "team2": t2,
            "venue": venue,
            "player_points": [],
        }

        t1_names = [p["name"] for p in t1_roster]
        t2_names = [p["name"] for p in t2_roster]

        cache_key = _matchup_cache_key(fixture)
        matchup_data = _get_cached_matchup_payload(cache_key)
        if matchup_data is None:
            try:
                matchup_data = get_team_matchups_service(
                    team1=t1,
                    team2=t2,
                    start_date=_default_matchup_start_date(),
                    end_date=None,
                    team1_players=t1_names,
                    team2_players=t2_names,
                    db=db,
                )
                if matchup_data:
                    _set_cached_matchup_payload(cache_key, matchup_data)
            except Exception as e:
                logger.warning("Matchup fetch failed for %s vs %s: %s", t1, t2, e)
                matchup_data = None

        if not matchup_data:
            match_details.append(match_info)
            continue

        matchup_lineup_sources = (matchup_data.get("lineup_sources") or {})
        t1_matchup_source = matchup_lineup_sources.get("team1")
        t2_matchup_source = matchup_lineup_sources.get("team2")
        if t1_matchup_source and t1_matchup_source != "custom" and (lineup_sources.get(t1) in (None, "none")):
            lineup_sources[t1] = _merge_lineup_source(lineup_sources.get(t1), t1_matchup_source)
        if t2_matchup_source and t2_matchup_source != "custom" and (lineup_sources.get(t2) in (None, "none")):
            lineup_sources[t2] = _merge_lineup_source(lineup_sources.get(t2), t2_matchup_source)

        if not t1_roster:
            t1_roster = _infer_roster_from_matchup((matchup_data or {}).get("team1") or {})
        if not t2_roster:
            t2_roster = _infer_roster_from_matchup((matchup_data or {}).get("team2") or {})
        if not t1_roster or not t2_roster:
            match_details.append(match_info)
            continue

        team1_points = _build_normalized_match_points(matchup_data, "team1")
        team2_points = _build_normalized_match_points(matchup_data, "team2")
        team1_last_name_lookup = _build_last_name_lookup(list(team1_points.keys()))
        team2_last_name_lookup = _build_last_name_lookup(list(team2_points.keys()))

        # Process all players from both rosters
        for team_abbrev, roster, points_map, canonical_last_name_lookup in [
            (t1, t1_roster, team1_points, team1_last_name_lookup),
            (t2, t2_roster, team2_points, team2_last_name_lookup),
        ]:
            for player in roster:
                name = player["name"]
                display_name = player.get("display_name", name)
                roster_role = player.get("role", "batter")
                projection = _resolve_player_projection(
                    points_map=points_map,
                    name=name,
                    display_name=display_name,
                    canonical_last_name_lookup=canonical_last_name_lookup,
                )
                expected = float(projection.get("expected_points", 0.0) or 0.0)
                expected_raw = float(projection.get("expected_points_raw", 0.0) or 0.0)
                confidence = float(projection.get("confidence", 0.0) or 0.0)

                # Accumulate across matches
                if name not in player_scores:
                    player_scores[name] = {
                        "name": name,
                        "display_name": display_name,
                        "team": team_abbrev,
                        "role": _resolve_fantasy_role(name, roster_role, display_name=display_name),
                        "roster_role": roster_role,
                        "credits": get_player_credit(display_name),
                        "is_overseas": is_overseas(display_name),
                        "total_expected": 0.0,
                        "match_count": 0,
                        "matches": [],
                        "best_match_points": 0.0,
                    }

                player_scores[name]["total_expected"] += expected
                player_scores[name]["match_count"] += 1
                player_scores[name]["matches"].append({
                    "match_num": fixture["match_num"],
                    "vs": t2 if team_abbrev == t1 else t1,
                    "venue": venue,
                    "expected_points": round(expected, 1),
                    "expected_points_raw": round(expected_raw, 1),
                    "confidence": round(confidence, 2),
                })
                if expected > player_scores[name]["best_match_points"]:
                    player_scores[name]["best_match_points"] = expected

                match_info["player_points"].append({
                    "name": name,
                    "team": team_abbrev,
                    "expected_points": round(expected, 1),
                    "expected_points_raw": round(expected_raw, 1),
                })

        match_details.append(match_info)

    # Sort all players by total expected points
    all_players = sorted(
        player_scores.values(),
        key=lambda p: p["total_expected"],
        reverse=True,
    )

    # Build recommended squad using greedy selection with constraints
    # If user has a current team, lock those players and fill remaining slots
    locked_players = None
    if current_team:
        current_set_lower = {n.strip().lower() for n in current_team}
        locked_players = [
            p for p in all_players if p["name"].lower() in current_set_lower
        ]

    recommended = _build_optimal_squad(all_players, locked_players=locked_players, matches_ahead=len(upcoming))

    # Calculate transfers needed
    transfers_needed = 0
    if current_team:
        current_set = set(n.strip() for n in current_team)
        recommended_set = set(p["name"] for p in recommended)
        transfers_needed = len(current_set - recommended_set)

    # Captain / Vice-captain suggestions
    captain = max(recommended, key=lambda p: p["best_match_points"]) if recommended else None
    vice_captain = None
    if len(recommended) > 1:
        non_captain = [p for p in recommended if p["name"] != (captain or {}).get("name")]
        vice_captain = max(non_captain, key=lambda p: p["best_match_points"]) if non_captain else None

    return {
        "points_model": "per_match_normalized_v1",
        "upcoming_matches": [
            {
                "match_num": f["match_num"],
                "date": f["date"],
                "team1": f["team1"],
                "team2": f["team2"],
                "venue": f.get("venue_db", f.get("venue", "")),
            }
            for f in upcoming
        ],
        "recommended_squad": [
            {
                "name": p["name"],
                "team": p["team"],
                "role": p["role"],
                "roster_role": p["roster_role"],
                "credits": p.get("credits", 7.0),
                "is_overseas": p.get("is_overseas", False),
                "total_expected_points": round(p["total_expected"], 1),
                "match_count": p["match_count"],
                "best_match_points": round(p["best_match_points"], 1),
                "matches": p["matches"],
            }
            for p in recommended
        ],
        "squad_cost": round(sum(p.get("credits", 7.0) for p in recommended), 1),
        "captain": captain["name"] if captain else None,
        "vice_captain": vice_captain["name"] if vice_captain else None,
        "transfers_needed": transfers_needed,
        "transfers_remaining": transfers_remaining,
        "all_players": [
            {
                "name": p["name"],
                "team": p["team"],
                "role": p["role"],
                "credits": p.get("credits", 7.0),
                "is_overseas": p.get("is_overseas", False),
                "total_expected_points": round(p["total_expected"], 1),
                "match_count": p["match_count"],
            }
            for p in all_players[:50]
        ],
        "lineup_sources": lineup_sources,
        "match_details": match_details,
    }


def _build_optimal_squad(
    players: List[Dict],
    locked_players: Optional[List[Dict]] = None,
    matches_ahead: int = 1,
) -> List[Dict]:
    """
    Greedy squad builder respecting fantasy constraints:
    - 11 players, 100 credit budget
    - Min 1 WK, 3 BAT, 1 AR, 3 BOWL
    - Max 7 per team, max 4 overseas
    - Max N players whose primary match is the same fixture (diversification)

    If locked_players is provided, those are added first and the optimizer
    fills the remaining slots.
    """
    squad: List[Dict] = []
    team_count: Dict[str, int] = {}
    role_count = {"BAT": 0, "BOWL": 0, "AR": 0, "WK": 0}
    budget_used = 0.0

    # Minimum requirements
    min_roles = {"BAT": 3, "BOWL": 3, "AR": 1, "WK": 1}
    max_per_team = 7
    max_overseas = 4
    squad_size = 11
    budget_limit = 100.0

    # Per-match diversification: spread players across fixtures
    matches_ahead = max(1, matches_ahead)
    max_per_match = max(3, (squad_size + matches_ahead) // matches_ahead)

    overseas_count = 0
    selected_names: set = set()
    match_player_count: Dict[int, int] = {}  # match_num -> count of selected players

    def _primary_match(p: Dict) -> Optional[int]:
        """Return the match_num where this player has the highest expected points."""
        matches = p.get("matches") or []
        if not matches:
            return None
        best = max(matches, key=lambda m: float(m.get("expected_points", 0.0) or 0.0))
        return best.get("match_num")

    def _add(p: Dict):
        nonlocal budget_used, overseas_count
        squad.append(p)
        selected_names.add(p["name"])
        role_count[p["role"]] = role_count.get(p["role"], 0) + 1
        team_count[p["team"]] = team_count.get(p["team"], 0) + 1
        budget_used += p.get("credits", 7.0)
        if p.get("is_overseas", False):
            overseas_count += 1
        pm = _primary_match(p)
        if pm is not None:
            match_player_count[pm] = match_player_count.get(pm, 0) + 1

    def _can_add(p: Dict) -> bool:
        if p["name"] in selected_names:
            return False
        tc = team_count.get(p["team"], 0)
        if tc >= max_per_team:
            return False
        cost = p.get("credits", 7.0)
        if budget_used + cost > budget_limit:
            return False
        if p.get("is_overseas", False) and overseas_count >= max_overseas:
            return False
        # Per-match diversification constraint
        pm = _primary_match(p)
        if pm is not None and match_player_count.get(pm, 0) >= max_per_match:
            return False
        return True

    # Seed with locked players first
    if locked_players:
        for lp in locked_players:
            if len(squad) >= squad_size:
                break
            _add(lp)

    # First pass: fill minimum role requirements
    for role in ["WK", "BAT", "AR", "BOWL"]:
        for p in players:
            if len(squad) >= squad_size:
                break
            if p["role"] != role:
                continue
            if not _can_add(p):
                continue
            if role_count.get(role, 0) >= min_roles.get(role, 0):
                continue
            _add(p)

    # Second pass: fill remaining spots by highest expected points
    for p in players:
        if len(squad) >= squad_size:
            break
        if not _can_add(p):
            continue
        _add(p)

    return squad


def get_player_outlook(
    db,
    player_name: str,
    from_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return a player's upcoming fixtures, venue history, and expected points.
    """
    schedule = _load_schedule()
    today = from_date or date.today().isoformat()

    # Find player's team
    player_team = None
    player_role = None
    for abbrev, data in IPL_2026_ROSTERS.items():
        for p in data["players"]:
            if p["name"].lower() == player_name.lower():
                player_team = abbrev
                player_role = p["role"]
                player_name = p["name"]  # normalize casing
                break
        if player_team:
            break

    if not player_team:
        return {"error": f"Player '{player_name}' not found in IPL 2026 rosters"}

    # Get upcoming fixtures for this player's team
    upcoming = [
        f for f in schedule
        if f["date"] >= today and (f["team1"] == player_team or f["team2"] == player_team)
    ]

    fixture_outlook = []
    for fixture in upcoming[:10]:
        opponent = fixture["team2"] if fixture["team1"] == player_team else fixture["team1"]
        venue = fixture.get("venue_db", fixture.get("venue", ""))

        # Get matchup data for this specific fixture
        opp_roster_meta = _get_team_players_for_projection(opponent, db)
        own_roster_meta = _get_team_players_for_projection(player_team, db)
        opp_roster = opp_roster_meta.get("players", [])
        own_roster = own_roster_meta.get("players", [])
        expected_points = 0.0

        if opp_roster and own_roster:
            try:
                player_display_name = player_name
                for p in own_roster:
                    roster_name = (p.get("name") or "").strip().lower()
                    roster_display_name = (p.get("display_name") or "").strip().lower()
                    if player_name.lower() in {roster_name, roster_display_name}:
                        player_display_name = p.get("display_name") or p.get("name") or player_name
                        break
                matchup_data = get_team_matchups_service(
                    team1=player_team,
                    team2=opponent,
                    start_date=_default_matchup_start_date(),
                    end_date=None,
                    team1_players=[p["name"] for p in own_roster],
                    team2_players=[p["name"] for p in opp_roster],
                    db=db,
                )
                team_key = "team1"
                if ((matchup_data or {}).get("team1") or {}).get("name") != player_team:
                    team_key = "team2"
                normalized_points = _build_normalized_match_points(matchup_data, team_key)
                projection = _resolve_player_projection(
                    points_map=normalized_points,
                    name=player_name,
                    display_name=player_display_name,
                    canonical_last_name_lookup=_build_last_name_lookup(list(normalized_points.keys())),
                )
                expected_points = projection.get("expected_points", 0.0)
            except Exception:
                pass

        fixture_outlook.append({
            "match_num": fixture["match_num"],
            "date": fixture["date"],
            "opponent": opponent,
            "venue": venue,
            "expected_points": round(expected_points, 1),
        })

    return {
        "player": player_name,
        "team": player_team,
        "role": player_role,
        "upcoming_fixtures": fixture_outlook,
        "total_upcoming_matches": len(upcoming),
    }


def get_transfer_plan(
    db,
    current_team: List[str],
    gameweek_start: int = 1,
    gameweek_end: int = 3,
    transfers_budget: int = 160,
    from_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Multi-gameweek transfer planner that minimizes transfers while maximizing points.
    """
    schedule = _load_schedule()
    today = from_date or date.today().isoformat()
    upcoming = [f for f in schedule if f["date"] >= today]

    # Group fixtures into gameweeks (windows of ~3 matches)
    window_size = 3
    gameweeks = []
    for i in range(gameweek_start - 1, min(gameweek_end, len(upcoming) // window_size + 1)):
        start_idx = i * window_size
        end_idx = min(start_idx + window_size, len(upcoming))
        if start_idx >= len(upcoming):
            break
        gw_fixtures = upcoming[start_idx:end_idx]
        gameweeks.append({
            "gameweek": i + 1,
            "fixtures": gw_fixtures,
            "date_range": f"{gw_fixtures[0]['date']} to {gw_fixtures[-1]['date']}",
        })

    current_set = set(n.strip() for n in current_team) if current_team else set()
    total_transfers_used = 0
    plan = []

    for gw in gameweeks:
        # Get recommendations for this window
        recs = get_fantasy_recommendations(
            db=db,
            matches_ahead=len(gw["fixtures"]),
            current_team=list(current_set),
            transfers_remaining=transfers_budget - total_transfers_used,
            from_date=gw["fixtures"][0]["date"],
        )

        recommended_names = set(p["name"] for p in recs.get("recommended_squad", []))

        transfers_out = current_set - recommended_names
        transfers_in = recommended_names - current_set
        transfers_this_gw = len(transfers_out)

        # Identify hold vs punt players
        hold_players = current_set & recommended_names

        plan.append({
            "gameweek": gw["gameweek"],
            "date_range": gw["date_range"],
            "squad": recs.get("recommended_squad", []),
            "captain": recs.get("captain"),
            "vice_captain": recs.get("vice_captain"),
            "transfers_in": list(transfers_in),
            "transfers_out": list(transfers_out),
            "transfers_used": transfers_this_gw,
            "hold_players": list(hold_players),
            "expected_total_points": sum(
                p.get("total_expected_points", 0)
                for p in recs.get("recommended_squad", [])
            ),
        })

        total_transfers_used += transfers_this_gw
        current_set = recommended_names

    return {
        "plan": plan,
        "total_transfers_used": total_transfers_used,
        "transfers_remaining": transfers_budget - total_transfers_used,
    }
