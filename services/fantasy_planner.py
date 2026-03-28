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
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ipl_rosters import get_ipl_roster, get_team_abbrev_from_name, IPL_2026_ROSTERS
from services.matchups import get_team_matchups_service

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
    schedule = _load_schedule()
    today = from_date or date.today().isoformat()
    upcoming = [f for f in schedule if f["date"] >= today]
    return upcoming[:matches_ahead]


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

    for fixture in upcoming:
        t1 = fixture["team1"]
        t2 = fixture["team2"]
        venue = fixture.get("venue_db", fixture.get("venue", ""))

        t1_roster = _get_team_players(t1)
        t2_roster = _get_team_players(t2)

        if not t1_roster or not t2_roster:
            continue

        t1_names = [p["name"] for p in t1_roster]
        t2_names = [p["name"] for p in t2_roster]

        # Get matchup-based fantasy analysis
        try:
            matchup_data = get_team_matchups_service(
                team1=t1,
                team2=t2,
                start_date=None,
                end_date=None,
                team1_players=t1_names,
                team2_players=t2_names,
                db=db,
            )
        except Exception as e:
            logger.warning("Matchup fetch failed for %s vs %s: %s", t1, t2, e)
            matchup_data = None

        fantasy = (matchup_data or {}).get("fantasy_analysis", {})
        top_picks = fantasy.get("top_fantasy_picks", [])

        match_info = {
            "match_num": fixture["match_num"],
            "date": fixture["date"],
            "team1": t1,
            "team2": t2,
            "venue": venue,
            "player_points": [],
        }

        # Process all players from both rosters
        for team_abbrev, roster, team_key in [(t1, t1_roster, "team1"), (t2, t2_roster, "team2")]:
            for player in roster:
                name = player["name"]
                role = player["role"]

                # Find this player's expected points from matchup analysis
                pick = next((p for p in top_picks if p["player_name"] == name), None)
                expected = pick["expected_points"] if pick else 0.0
                confidence = pick.get("confidence", 0) if pick else 0.0

                # Accumulate across matches
                if name not in player_scores:
                    player_scores[name] = {
                        "name": name,
                        "team": team_abbrev,
                        "role": ROLE_MAP.get(role, "BAT"),
                        "roster_role": role,
                        "credits": get_player_credit(name),
                        "is_overseas": is_overseas(name),
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
                    "confidence": round(confidence, 2),
                })
                if expected > player_scores[name]["best_match_points"]:
                    player_scores[name]["best_match_points"] = expected

                match_info["player_points"].append({
                    "name": name,
                    "team": team_abbrev,
                    "expected_points": round(expected, 1),
                })

        match_details.append(match_info)

    # Sort all players by total expected points
    all_players = sorted(
        player_scores.values(),
        key=lambda p: p["total_expected"],
        reverse=True,
    )

    # Build recommended squad using greedy selection with constraints
    recommended = _build_optimal_squad(all_players)

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
        "match_details": match_details,
    }


def _build_optimal_squad(players: List[Dict]) -> List[Dict]:
    """
    Greedy squad builder respecting fantasy constraints:
    - 11 players, 100 credit budget
    - Min 1 WK, 3 BAT, 1 AR, 3 BOWL
    - Max 7 per team, max 4 overseas
    """
    squad = []
    team_count: Dict[str, int] = {}
    role_count = {"BAT": 0, "BOWL": 0, "AR": 0, "WK": 0}
    budget_used = 0.0

    # Minimum requirements
    min_roles = {"BAT": 3, "BOWL": 3, "AR": 1, "WK": 1}
    max_per_team = 7
    max_overseas = 4
    squad_size = 11
    budget_limit = 100.0

    overseas_count = 0
    selected_names: set = set()

    def _can_add(p: Dict) -> bool:
        nonlocal budget_used, overseas_count
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
        return True

    def _add(p: Dict):
        nonlocal budget_used, overseas_count
        squad.append(p)
        selected_names.add(p["name"])
        role_count[p["role"]] = role_count.get(p["role"], 0) + 1
        team_count[p["team"]] = team_count.get(p["team"], 0) + 1
        budget_used += p.get("credits", 7.0)
        if p.get("is_overseas", False):
            overseas_count += 1

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
        opp_roster = _get_team_players(opponent)
        own_roster = _get_team_players(player_team)
        expected_points = 0.0

        if opp_roster and own_roster:
            try:
                matchup_data = get_team_matchups_service(
                    team1=player_team,
                    team2=opponent,
                    start_date=None,
                    end_date=None,
                    team1_players=[p["name"] for p in own_roster],
                    team2_players=[p["name"] for p in opp_roster],
                    db=db,
                )
                picks = (matchup_data or {}).get("fantasy_analysis", {}).get("top_fantasy_picks", [])
                pick = next((p for p in picks if p["player_name"] == player_name), None)
                expected_points = pick["expected_points"] if pick else 0.0
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
