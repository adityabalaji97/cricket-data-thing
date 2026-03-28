import logging
import time
from sqlalchemy.sql import text
from fastapi import HTTPException
from typing import List, Optional, Dict
from datetime import date
from models import teams_mapping

logger = logging.getLogger(__name__)

# Cache for player_aliases to avoid full table scan on every call
_ALIAS_CACHE: Dict[str, str] = {}
_ALIAS_CACHE_TIME: float = 0

def get_all_team_name_variations(team_name):
    reverse_mapping = {}
    for full_name, abbrev in teams_mapping.items():
        if abbrev not in reverse_mapping:
            reverse_mapping[abbrev] = []
        reverse_mapping[abbrev].append(full_name)
    if team_name in reverse_mapping:
        return reverse_mapping[team_name]
    abbrev = teams_mapping.get(team_name)
    if abbrev and abbrev in reverse_mapping:
        return reverse_mapping[abbrev]
    return [team_name]

def _dedupe_player_names(players: List[str]) -> List[str]:
    deduped: List[str] = []
    seen = set()
    for player in players or []:
        if not player:
            continue
        cleaned = player.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return deduped

def _get_alias_lookup(db) -> Dict[str, str]:
    """Return cached alias lookup dict. Refreshes every hour."""
    global _ALIAS_CACHE, _ALIAS_CACHE_TIME
    now = time.time()
    if _ALIAS_CACHE and (now - _ALIAS_CACHE_TIME) < 3600:
        return _ALIAS_CACHE

    try:
        alias_rows = db.execute(
            text(
                """
                SELECT player_name, alias_name
                FROM player_aliases
                WHERE alias_name IS NOT NULL
                """
            )
        ).fetchall()
    except Exception:
        return _ALIAS_CACHE

    alias_lookup: Dict[str, str] = {}
    for row in alias_rows:
        legacy_name = (row[0] or "").strip()
        canonical_name = (row[1] or "").strip()
        if not canonical_name:
            continue
        alias_lookup[canonical_name.lower()] = canonical_name
        if legacy_name:
            alias_lookup[legacy_name.lower()] = canonical_name

    _ALIAS_CACHE = alias_lookup
    _ALIAS_CACHE_TIME = now
    logger.info("Refreshed player alias cache: %d entries", len(alias_lookup))
    return alias_lookup


def _canonicalize_players(players: List[str], db) -> List[str]:
    deduped_players = _dedupe_player_names(players)
    if not deduped_players:
        return []

    alias_lookup = _get_alias_lookup(db)
    if not alias_lookup:
        return deduped_players

    canonicalized = [alias_lookup.get(player.lower(), player) for player in deduped_players]
    return _dedupe_player_names(canonicalized)

# Fantasy point constants (shared with fantasy_planner)
# Batting points
_RUN_POINT = 1
_BOUNDARY_BONUS = 4
_SIX_BONUS = 6
_RUNS_25_BONUS = 4
_RUNS_50_BONUS = 8
_SR_ABOVE_170 = 6
_SR_150_TO_170 = 4
_SR_130_TO_150 = 2
_SR_60_TO_70 = -2
_SR_50_TO_60 = -4
_SR_BELOW_50 = -6

# Bowling points
_DOT_BALL_POINT = 1
_WICKET_POINT = 25
_ECONOMY_BELOW_5 = 6
_ECONOMY_5_TO_6 = 4
_ECONOMY_6_TO_7 = 2
_ECONOMY_10_TO_11 = -2
_ECONOMY_11_TO_12 = -4
_ECONOMY_ABOVE_12 = -6


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _calculate_batting_projection_points(overall_stats: Dict) -> Dict[str, float]:
    """Per-match normalized batting projection points."""
    if not overall_stats:
        return {"points": 0.0, "confidence": 0.0}

    runs = float(overall_stats.get("average") or overall_stats.get("runs") or 0.0)
    balls_sample = float(overall_stats.get("balls") or 0.0)
    strike_rate = float(overall_stats.get("strike_rate") or 0.0)
    boundary_pct = float(overall_stats.get("boundary_percentage") or 0.0)

    balls = runs * 100.0 / strike_rate if strike_rate > 0 else balls_sample
    points = runs * _RUN_POINT

    boundary_runs = runs * (boundary_pct / 100.0)
    estimated_fours = boundary_runs * 0.7 / 4.0
    estimated_sixes = boundary_runs * 0.3 / 6.0
    points += estimated_fours * _BOUNDARY_BONUS
    points += estimated_sixes * _SIX_BONUS

    if runs >= 50:
        points += _RUNS_50_BONUS
    elif runs >= 25:
        points += _RUNS_25_BONUS

    if balls >= 10:
        if strike_rate > 170:
            points += _SR_ABOVE_170
        elif 150 < strike_rate <= 170:
            points += _SR_150_TO_170
        elif 130 <= strike_rate <= 150:
            points += _SR_130_TO_150
        elif 60 <= strike_rate < 70:
            points += _SR_60_TO_70
        elif 50 <= strike_rate < 60:
            points += _SR_50_TO_60
        elif strike_rate < 50:
            points += _SR_BELOW_50

    confidence = _clamp(balls_sample / 50.0 if balls_sample else 0.0, 0.3, 0.9) if balls_sample else 0.0
    return {"points": max(0.0, points), "confidence": confidence}


def _calculate_bowling_projection_points(bowling_stats: Dict) -> Dict[str, float]:
    """Per-match normalized bowling projection points (normalized to 24-ball spell)."""
    if not bowling_stats:
        return {"points": 0.0, "confidence": 0.0}

    balls_sample = float(bowling_stats.get("balls") or 0.0)
    runs = float(bowling_stats.get("runs") or 0.0)
    wickets = float(bowling_stats.get("wickets") or 0.0)
    dot_pct = float(bowling_stats.get("dot_percentage") or 0.0)

    if balls_sample <= 0:
        return {"points": 0.0, "confidence": 0.0}

    normalized_runs = runs * (24.0 / max(balls_sample, 1.0))
    normalized_wickets = wickets * (24.0 / max(balls_sample, 1.0))
    normalized_dots = (dot_pct / 100.0) * 24.0
    normalized_economy = normalized_runs / 4.0

    points = (normalized_dots * _DOT_BALL_POINT) + (normalized_wickets * _WICKET_POINT)

    if normalized_economy < 5:
        points += _ECONOMY_BELOW_5
    elif 5 <= normalized_economy < 6:
        points += _ECONOMY_5_TO_6
    elif 6 <= normalized_economy <= 7:
        points += _ECONOMY_6_TO_7
    elif 10 <= normalized_economy < 11:
        points += _ECONOMY_10_TO_11
    elif 11 <= normalized_economy < 12:
        points += _ECONOMY_11_TO_12
    elif normalized_economy >= 12:
        points += _ECONOMY_ABOVE_12

    confidence = _clamp(balls_sample / 30.0, 0.3, 0.9)
    return {"points": max(0.0, points), "confidence": confidence}


def add_bowling_consolidated_rows(team1_batting, team2_batting, team1_players, team2_players):
    """
    Add consolidated rows for bowlers showing their performance against the opposing batting lineup
    
    Args:
        team1_batting (Dict): Team 1 batting matchups
        team2_batting (Dict): Team 2 batting matchups 
        team1_players (List[str]): Team 1 player names
        team2_players (List[str]): Team 2 player names
    
    Returns:
        Tuple: (team1_bowling_consolidated, team2_bowling_consolidated)
    """
    
    # For team1 bowlers vs team2 batters
    team1_bowling_consolidated = {}
    for bowler in team1_players:
        consolidated_stats = {
            "balls": 0, "runs": 0, "wickets": 0, "boundaries": 0, "dots": 0
        }
        
        # Aggregate across all batters from team2
        for batter in team2_players:
            if batter in team2_batting and bowler in team2_batting[batter]:
                stats = team2_batting[batter][bowler]
                for key in consolidated_stats:
                    consolidated_stats[key] += stats[key]
        
        # Only include bowlers with actual matchup data
        if consolidated_stats["balls"] > 0:
            # Calculate derived metrics
            effective_wickets = consolidated_stats["wickets"] if consolidated_stats["wickets"] > 0 else 1
            consolidated_stats["average"] = consolidated_stats["runs"] / effective_wickets
            consolidated_stats["economy"] = (6 * consolidated_stats["runs"]) / consolidated_stats["balls"] if consolidated_stats["balls"] > 0 else 0
            consolidated_stats["strike_rate"] = consolidated_stats["balls"] / effective_wickets  # balls per wicket
            consolidated_stats["dot_percentage"] = (consolidated_stats["dots"] * 100) / consolidated_stats["balls"] if consolidated_stats["balls"] > 0 else 0
            consolidated_stats["boundary_percentage"] = (consolidated_stats["boundaries"] * 100) / consolidated_stats["balls"] if consolidated_stats["balls"] > 0 else 0
            
            team1_bowling_consolidated[bowler] = consolidated_stats
    
    # For team2 bowlers vs team1 batters
    team2_bowling_consolidated = {}
    for bowler in team2_players:
        consolidated_stats = {
            "balls": 0, "runs": 0, "wickets": 0, "boundaries": 0, "dots": 0
        }
        
        # Aggregate across all batters from team1
        for batter in team1_players:
            if batter in team1_batting and bowler in team1_batting[batter]:
                stats = team1_batting[batter][bowler]
                for key in consolidated_stats:
                    consolidated_stats[key] += stats[key]
        
        # Only include bowlers with actual matchup data
        if consolidated_stats["balls"] > 0:
            # Calculate derived metrics
            effective_wickets = consolidated_stats["wickets"] if consolidated_stats["wickets"] > 0 else 1
            consolidated_stats["average"] = consolidated_stats["runs"] / effective_wickets
            consolidated_stats["economy"] = (6 * consolidated_stats["runs"]) / consolidated_stats["balls"] if consolidated_stats["balls"] > 0 else 0
            consolidated_stats["strike_rate"] = consolidated_stats["balls"] / effective_wickets  # balls per wicket
            consolidated_stats["dot_percentage"] = (consolidated_stats["dots"] * 100) / consolidated_stats["balls"] if consolidated_stats["balls"] > 0 else 0
            consolidated_stats["boundary_percentage"] = (consolidated_stats["boundaries"] * 100) / consolidated_stats["balls"] if consolidated_stats["balls"] > 0 else 0
            
            team2_bowling_consolidated[bowler] = consolidated_stats
    
    return team1_bowling_consolidated, team2_bowling_consolidated

def calculate_fantasy_points_from_matchups(team1_batting, team2_batting, team1_bowling_consolidated, team2_bowling_consolidated, team1_players, team2_players):
    """
    Calculate expected fantasy points using per-match normalized projections.
    Uses the same projection model as fantasy_planner for consistent numbers.
    """
    all_fantasy_players = []

    for team_label, batting, bowling_cons, players in [
        ("team1", team1_batting, team1_bowling_consolidated, team1_players),
        ("team2", team2_batting, team2_bowling_consolidated, team2_players),
    ]:
        player_map = {}

        # Batting projections
        for batter in players:
            if batter in batting and "Overall" in batting[batter]:
                overall_stats = batting[batter]["Overall"]
                result = _calculate_batting_projection_points(overall_stats)
                player_map[batter] = {
                    "player_name": batter,
                    "team": team_label,
                    "role": "batsman",
                    "expected_points": result["points"],
                    "confidence": result["confidence"],
                    "breakdown": {"batting": result["points"], "bowling": 0.0},
                }

        # Bowling projections
        for bowler in players:
            if bowler in bowling_cons:
                result = _calculate_bowling_projection_points(bowling_cons[bowler])
                if bowler in player_map:
                    player_map[bowler]["role"] = "all-rounder"
                    player_map[bowler]["expected_points"] += result["points"]
                    player_map[bowler]["confidence"] = (
                        player_map[bowler]["confidence"] + result["confidence"]
                    ) / 2.0
                    player_map[bowler]["breakdown"]["bowling"] = result["points"]
                else:
                    player_map[bowler] = {
                        "player_name": bowler,
                        "team": team_label,
                        "role": "bowler",
                        "expected_points": result["points"],
                        "confidence": result["confidence"],
                        "breakdown": {"batting": 0.0, "bowling": result["points"]},
                    }

        all_fantasy_players.extend(player_map.values())

    all_fantasy_players.sort(key=lambda x: x["expected_points"], reverse=True)

    return {
        "top_fantasy_picks": all_fantasy_players[:15],
    }

def get_team_matchups_service(
    team1: str,
    team2: str,
    start_date: Optional[date],
    end_date: Optional[date],
    team1_players: List[str],
    team2_players: List[str],
    db,
    use_current_roster: bool = False,
):
    try:
        use_custom_teams = len(team1_players) > 0 and len(team2_players) > 0
        team1_lineup_source = "custom" if use_custom_teams else "recent_10"
        team2_lineup_source = "custom" if use_custom_teams else "recent_10"

        # When use_current_roster is True, populate player lists from current roster service.
        if not use_custom_teams and use_current_roster:
            try:
                from services.team_roster import get_team_roster_service

                roster1 = get_team_roster_service(team1, db)
                roster2 = get_team_roster_service(team2, db)
                if roster1["players"]:
                    team1_players = [p["name"] for p in roster1["players"]]
                    team1_lineup_source = roster1.get("source", "match_data")
                if roster2["players"]:
                    team2_players = [p["name"] for p in roster2["players"]]
                    team2_lineup_source = roster2.get("source", "match_data")
                if team1_players and team2_players:
                    use_custom_teams = True
                    # Canonicalize but keep originals as fallback if canon empties the list
                    canon1 = _canonicalize_players(team1_players, db)
                    canon2 = _canonicalize_players(team2_players, db)
                    team1_players = canon1 if canon1 else team1_players
                    team2_players = canon2 if canon2 else team2_players
                logger.info(
                    "Roster loaded: team1=%d players, team2=%d players, source1=%s, source2=%s",
                    len(team1_players), len(team2_players), team1_lineup_source, team2_lineup_source,
                )
            except ImportError:
                pass

        # Canonicalize custom player lists (only for user-provided custom teams, not roster)
        if use_custom_teams and not use_current_roster:
            canon1 = _canonicalize_players(team1_players, db)
            canon2 = _canonicalize_players(team2_players, db)
            team1_players = canon1 if canon1 else team1_players
            team2_players = canon2 if canon2 else team2_players

        if not use_custom_teams:
            team1_lineup_source = "recent_10"
            team2_lineup_source = "recent_10"
            team1_names = get_all_team_name_variations(team1)
            team2_names = get_all_team_name_variations(team2)
            recent_matches_query = text("""
                WITH recent_matches AS (
                    SELECT id 
                    FROM matches
                    WHERE ((team1 = ANY(:team1_names) OR team2 = ANY(:team1_names)) 
                           OR (team1 = ANY(:team2_names) OR team2 = ANY(:team2_names)))
                    AND (:start_date IS NULL OR date >= :start_date)
                    AND (:end_date IS NULL OR date <= :end_date)
                    ORDER BY date DESC
                    LIMIT 10
                ),
                alias_map AS (
                    SELECT DISTINCT ON (name_key)
                        name_key,
                        canonical_name
                    FROM (
                        SELECT LOWER(player_name) AS name_key, alias_name AS canonical_name
                        FROM player_aliases
                        WHERE player_name IS NOT NULL AND alias_name IS NOT NULL
                        UNION ALL
                        SELECT LOWER(alias_name) AS name_key, alias_name AS canonical_name
                        FROM player_aliases
                        WHERE alias_name IS NOT NULL
                    ) mapped_aliases
                ),
                team1_players AS (
                    SELECT DISTINCT COALESCE(am.canonical_name, d.batter) AS player
                    FROM deliveries d
                    JOIN recent_matches rm ON d.match_id = rm.id
                    LEFT JOIN alias_map am ON LOWER(d.batter) = am.name_key
                    WHERE d.batting_team = ANY(:team1_names)
                      AND d.batter IS NOT NULL
                    UNION
                    SELECT DISTINCT COALESCE(am.canonical_name, d.bowler) AS player
                    FROM deliveries d
                    JOIN recent_matches rm ON d.match_id = rm.id
                    LEFT JOIN alias_map am ON LOWER(d.bowler) = am.name_key
                    WHERE d.bowling_team = ANY(:team1_names)
                      AND d.bowler IS NOT NULL
                    UNION
                    SELECT DISTINCT COALESCE(am.canonical_name, dd.bat) AS player
                    FROM delivery_details dd
                    JOIN recent_matches rm ON dd.p_match = rm.id
                    LEFT JOIN alias_map am ON LOWER(dd.bat) = am.name_key
                    WHERE dd.team_bat = ANY(:team1_names)
                      AND dd.bat IS NOT NULL
                    UNION
                    SELECT DISTINCT COALESCE(am.canonical_name, dd.bowl) AS player
                    FROM delivery_details dd
                    JOIN recent_matches rm ON dd.p_match = rm.id
                    LEFT JOIN alias_map am ON LOWER(dd.bowl) = am.name_key
                    WHERE dd.team_bowl = ANY(:team1_names)
                      AND dd.bowl IS NOT NULL
                ),
                team2_players AS (
                    SELECT DISTINCT COALESCE(am.canonical_name, d.batter) AS player
                    FROM deliveries d
                    JOIN recent_matches rm ON d.match_id = rm.id
                    LEFT JOIN alias_map am ON LOWER(d.batter) = am.name_key
                    WHERE d.batting_team = ANY(:team2_names)
                      AND d.batter IS NOT NULL
                    UNION
                    SELECT DISTINCT COALESCE(am.canonical_name, d.bowler) AS player
                    FROM deliveries d
                    JOIN recent_matches rm ON d.match_id = rm.id
                    LEFT JOIN alias_map am ON LOWER(d.bowler) = am.name_key
                    WHERE d.bowling_team = ANY(:team2_names)
                      AND d.bowler IS NOT NULL
                    UNION
                    SELECT DISTINCT COALESCE(am.canonical_name, dd.bat) AS player
                    FROM delivery_details dd
                    JOIN recent_matches rm ON dd.p_match = rm.id
                    LEFT JOIN alias_map am ON LOWER(dd.bat) = am.name_key
                    WHERE dd.team_bat = ANY(:team2_names)
                      AND dd.bat IS NOT NULL
                    UNION
                    SELECT DISTINCT COALESCE(am.canonical_name, dd.bowl) AS player
                    FROM delivery_details dd
                    JOIN recent_matches rm ON dd.p_match = rm.id
                    LEFT JOIN alias_map am ON LOWER(dd.bowl) = am.name_key
                    WHERE dd.team_bowl = ANY(:team2_names)
                      AND dd.bowl IS NOT NULL
                )
                SELECT player, :team1 as team FROM team1_players
                UNION ALL
                SELECT player, :team2 as team FROM team2_players
            """)
            recent_players = db.execute(recent_matches_query, {
                "team1": team1,
                "team2": team2,
                "team1_names": team1_names,
                "team2_names": team2_names,
                "start_date": start_date,
                "end_date": end_date
            }).fetchall()
            team1_players = _dedupe_player_names([row[0] for row in recent_players if row[1] == team1])
            team2_players = _dedupe_player_names([row[0] for row in recent_players if row[1] == team2])

        matchup_query = text("""
            WITH alias_map AS (
                SELECT DISTINCT ON (name_key)
                    name_key,
                    canonical_name
                FROM (
                    SELECT LOWER(player_name) AS name_key, alias_name AS canonical_name
                    FROM player_aliases
                    WHERE player_name IS NOT NULL AND alias_name IS NOT NULL
                    UNION ALL
                    SELECT LOWER(alias_name) AS name_key, alias_name AS canonical_name
                    FROM player_aliases
                    WHERE alias_name IS NOT NULL
                ) mapped_aliases
            ),
            raw_stats AS (
                SELECT
                    COALESCE(bat_alias.canonical_name, d.batter) AS batter,
                    COALESCE(bowl_alias.canonical_name, d.bowler) AS bowler,
                    COUNT(*) as balls,
                    SUM(d.runs_off_bat + d.extras) as runs,
                    SUM(CASE WHEN d.wicket_type IS NOT NULL AND d.wicket_type != 'run out' THEN 1 ELSE 0 END) as wickets,
                    SUM(CASE WHEN d.runs_off_bat IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                    SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as dots
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                LEFT JOIN alias_map bat_alias ON LOWER(d.batter) = bat_alias.name_key
                LEFT JOIN alias_map bowl_alias ON LOWER(d.bowler) = bowl_alias.name_key
                WHERE
                    ((COALESCE(bat_alias.canonical_name, d.batter) = ANY(:team1_players)
                      AND COALESCE(bowl_alias.canonical_name, d.bowler) = ANY(:team2_players))
                     OR (COALESCE(bat_alias.canonical_name, d.batter) = ANY(:team2_players)
                      AND COALESCE(bowl_alias.canonical_name, d.bowler) = ANY(:team1_players)))
                    AND (:start_date IS NULL OR m.date >= :start_date)
                    AND (:end_date IS NULL OR m.date <= :end_date)
                GROUP BY COALESCE(bat_alias.canonical_name, d.batter), COALESCE(bowl_alias.canonical_name, d.bowler)

                UNION ALL

                SELECT
                    COALESCE(bat_alias.canonical_name, dd.bat) AS batter,
                    COALESCE(bowl_alias.canonical_name, dd.bowl) AS bowler,
                    COUNT(*) as balls,
                    SUM(dd.score) as runs,
                    SUM(CASE WHEN dd.out::boolean = true THEN 1 ELSE 0 END) as wickets,
                    SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                    SUM(CASE WHEN dd.score = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as dots
                FROM delivery_details dd
                LEFT JOIN alias_map bat_alias ON LOWER(dd.bat) = bat_alias.name_key
                LEFT JOIN alias_map bowl_alias ON LOWER(dd.bowl) = bowl_alias.name_key
                WHERE
                    ((COALESCE(bat_alias.canonical_name, dd.bat) = ANY(:team1_players)
                      AND COALESCE(bowl_alias.canonical_name, dd.bowl) = ANY(:team2_players))
                     OR (COALESCE(bat_alias.canonical_name, dd.bat) = ANY(:team2_players)
                      AND COALESCE(bowl_alias.canonical_name, dd.bowl) = ANY(:team1_players)))
                    AND (:start_date IS NULL OR dd.match_date::date >= :start_date)
                    AND (:end_date IS NULL OR dd.match_date::date <= :end_date)
                GROUP BY COALESCE(bat_alias.canonical_name, dd.bat), COALESCE(bowl_alias.canonical_name, dd.bowl)
            ),
            player_stats AS (
                SELECT
                    batter,
                    bowler,
                    SUM(balls) as balls,
                    SUM(runs) as runs,
                    SUM(wickets) as wickets,
                    SUM(boundaries) as boundaries,
                    SUM(dots) as dots
                FROM raw_stats
                GROUP BY batter, bowler
                HAVING SUM(balls) >= 6
            )
            SELECT 
                batter,
                bowler,
                balls,
                runs,
                wickets,
                boundaries,
                dots,
                CAST(
                    CASE 
                        WHEN wickets = 0 THEN NULL 
                        ELSE (runs::numeric / wickets)
                    END AS numeric(10,2)
                ) as average,
                CAST(
                    (runs::numeric * 100 / NULLIF(balls, 0))
                    AS numeric(10,2)
                ) as strike_rate,
                CAST(
                    (dots::numeric * 100 / NULLIF(balls, 0))
                    AS numeric(10,2)
                ) as dot_percentage,
                CAST(
                    (boundaries::numeric * 100 / NULLIF(balls, 0))
                    AS numeric(10,2)
                ) as boundary_percentage
            FROM player_stats
            ORDER BY balls DESC
        """)

        matchups = db.execute(matchup_query, {
            "team1_players": team1_players,
            "team2_players": team2_players,
            "start_date": start_date,
            "end_date": end_date
        }).fetchall()

        team1_batting = {}
        team2_batting = {}

        for row in matchups:
            matchup_data = {
                "balls": int(row[2]),
                "runs": int(row[3]),
                "wickets": int(row[4]),
                "boundaries": int(row[5]),
                "dots": int(row[6]),
                "average": float(row[7]) if row[7] is not None else None,
                "strike_rate": float(row[8]) if row[8] is not None else 0.0,
                "dot_percentage": float(row[9]) if row[9] is not None else 0.0,
                "boundary_percentage": float(row[10]) if row[10] is not None else 0.0
            }
            if row[0] in team1_players:
                if row[0] not in team1_batting:
                    team1_batting[row[0]] = {}
                team1_batting[row[0]][row[1]] = matchup_data
            else:
                if row[0] not in team2_batting:
                    team2_batting[row[0]] = {}
                team2_batting[row[0]][row[1]] = matchup_data

        # Add "Overall" entry for each batter in team1_batting
        for batter, bowler_stats in team1_batting.items():
            if not bowler_stats:
                continue
            agg_balls = 0
            agg_runs = 0
            agg_wickets = 0
            agg_boundaries = 0
            agg_dots = 0

            for stats in bowler_stats.values():
                agg_balls += stats["balls"]
                agg_runs += stats["runs"]
                agg_wickets += stats["wickets"]
                agg_boundaries += stats["boundaries"]
                agg_dots += stats["dots"]

            # If wickets are 0, treat it as 1 for average calculation
            effective_wickets = agg_wickets if agg_wickets != 0 else 1

            overall_average = agg_runs / effective_wickets  if agg_runs is not None else None
            overall_strike_rate = (agg_runs * 100 / agg_balls) if agg_balls != 0 else 0.0
            overall_dot_percentage = (agg_dots * 100 / agg_balls) if agg_balls != 0 else 0.0
            overall_boundary_percentage = (agg_boundaries * 100 / agg_balls) if agg_balls != 0 else 0.0

            team1_batting[batter]["Overall"] = {
                "balls": agg_balls,
                "runs": agg_runs,
                "wickets": agg_wickets,
                "boundaries": agg_boundaries,
                "dots": agg_dots,
                "average": overall_average,
                "strike_rate": overall_strike_rate,
                "dot_percentage": overall_dot_percentage,
                "boundary_percentage": overall_boundary_percentage
            }

        # Add "Overall" entry for each batter in team2_batting
        for batter, bowler_stats in team2_batting.items():
            if not bowler_stats:
                continue
            agg_balls = 0
            agg_runs = 0
            agg_wickets = 0
            agg_boundaries = 0
            agg_dots = 0

            for stats in bowler_stats.values():
                agg_balls += stats["balls"]
                agg_runs += stats["runs"]
                agg_wickets += stats["wickets"]
                agg_boundaries += stats["boundaries"]
                agg_dots += stats["dots"]

            effective_wickets = agg_wickets if agg_wickets != 0 else 1

            overall_average = agg_runs / effective_wickets  if agg_runs is not None else None
            overall_strike_rate = (agg_runs * 100 / agg_balls) if agg_balls != 0 else 0.0
            overall_dot_percentage = (agg_dots * 100 / agg_balls) if agg_balls != 0 else 0.0
            overall_boundary_percentage = (agg_boundaries * 100 / agg_balls) if agg_balls != 0 else 0.0

            team2_batting[batter]["Overall"] = {
                "balls": agg_balls,
                "runs": agg_runs,
                "wickets": agg_wickets,
                "boundaries": agg_boundaries,
                "dots": agg_dots,
                "average": overall_average,
                "strike_rate": overall_strike_rate,
                "dot_percentage": overall_dot_percentage,
                "boundary_percentage": overall_boundary_percentage
            }

        # Calculate bowling consolidated rows
        team1_bowling_consolidated, team2_bowling_consolidated = add_bowling_consolidated_rows(
            team1_batting, team2_batting, team1_players, team2_players
        )

        # Calculate fantasy points from matchups
        fantasy_analysis = calculate_fantasy_points_from_matchups(
            team1_batting, team2_batting, team1_bowling_consolidated, team2_bowling_consolidated, 
            team1_players, team2_players
        )

        return {
            "team1": {
                "name": team1,
                "players": team1_players,
                "batting_matchups": team1_batting,
                "bowling_consolidated": team1_bowling_consolidated
            },
            "team2": {
                "name": team2,
                "players": team2_players,
                "batting_matchups": team2_batting,
                "bowling_consolidated": team2_bowling_consolidated
            },
            "lineup_sources": {
                "team1": team1_lineup_source,
                "team2": team2_lineup_source,
            },
            "fantasy_analysis": fantasy_analysis
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
