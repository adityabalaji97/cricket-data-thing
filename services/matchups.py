from sqlalchemy.sql import text
from fastapi import HTTPException
from typing import List, Optional, Dict
from datetime import date
from models import teams_mapping
from fantasy_points_v2 import FantasyPointsCalculator

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
    Calculate expected fantasy points for players based on their matchup data
    
    Args:
        team1_batting (Dict): Team 1 batting matchups
        team2_batting (Dict): Team 2 batting matchups
        team1_bowling_consolidated (Dict): Team 1 bowling consolidated stats
        team2_bowling_consolidated (Dict): Team 2 bowling consolidated stats
        team1_players (List[str]): Team 1 player names
        team2_players (List[str]): Team 2 player names
    
    Returns:
        Dict: Fantasy points analysis for both teams
    """
    fantasy_calc = FantasyPointsCalculator()
    
    # Calculate batting fantasy points for team1
    team1_batting_fantasy = {}
    for batter in team1_players:
        if batter in team1_batting and "Overall" in team1_batting[batter]:
            overall_stats = team1_batting[batter]["Overall"]
            fantasy_result = fantasy_calc.calculate_expected_batting_points_from_matchup(overall_stats)
            team1_batting_fantasy[batter] = fantasy_result
    
    # Calculate batting fantasy points for team2
    team2_batting_fantasy = {}
    for batter in team2_players:
        if batter in team2_batting and "Overall" in team2_batting[batter]:
            overall_stats = team2_batting[batter]["Overall"]
            fantasy_result = fantasy_calc.calculate_expected_batting_points_from_matchup(overall_stats)
            team2_batting_fantasy[batter] = fantasy_result
    
    # Calculate bowling fantasy points for team1
    team1_bowling_fantasy = {}
    for bowler in team1_players:
        if bowler in team1_bowling_consolidated:
            bowling_stats = team1_bowling_consolidated[bowler]
            fantasy_result = fantasy_calc.calculate_expected_bowling_points_from_matchup(bowling_stats)
            team1_bowling_fantasy[bowler] = fantasy_result
    
    # Calculate bowling fantasy points for team2
    team2_bowling_fantasy = {}
    for bowler in team2_players:
        if bowler in team2_bowling_consolidated:
            bowling_stats = team2_bowling_consolidated[bowler]
            fantasy_result = fantasy_calc.calculate_expected_bowling_points_from_matchup(bowling_stats)
            team2_bowling_fantasy[bowler] = fantasy_result
    
    # Create fantasy recommendations
    all_fantasy_players = []
    
    # Add team1 batting fantasy points
    for player, fantasy_data in team1_batting_fantasy.items():
        all_fantasy_players.append({
            "player_name": player,
            "team": "team1",
            "role": "batsman",
            "expected_points": fantasy_data.get("expected_batting_points", 0),
            "confidence": fantasy_data.get("confidence", 0),
            "breakdown": fantasy_data.get("breakdown", {})
        })
    
    # Add team1 bowling fantasy points
    for player, fantasy_data in team1_bowling_fantasy.items():
        existing_player = next((p for p in all_fantasy_players if p["player_name"] == player), None)
        if existing_player:
            # Player has both batting and bowling data - make them all-rounder
            existing_player["role"] = "all-rounder"
            existing_player["expected_points"] += fantasy_data.get("expected_bowling_points", 0)
            existing_player["bowling_breakdown"] = fantasy_data.get("breakdown", {})
        else:
            all_fantasy_players.append({
                "player_name": player,
                "team": "team1",
                "role": "bowler",
                "expected_points": fantasy_data.get("expected_bowling_points", 0),
                "confidence": fantasy_data.get("confidence", 0),
                "breakdown": fantasy_data.get("breakdown", {})
            })
    
    # Add team2 batting fantasy points
    for player, fantasy_data in team2_batting_fantasy.items():
        all_fantasy_players.append({
            "player_name": player,
            "team": "team2",
            "role": "batsman",
            "expected_points": fantasy_data.get("expected_batting_points", 0),
            "confidence": fantasy_data.get("confidence", 0),
            "breakdown": fantasy_data.get("breakdown", {})
        })
    
    # Add team2 bowling fantasy points
    for player, fantasy_data in team2_bowling_fantasy.items():
        existing_player = next((p for p in all_fantasy_players if p["player_name"] == player), None)
        if existing_player:
            # Player has both batting and bowling data - make them all-rounder
            existing_player["role"] = "all-rounder"
            existing_player["expected_points"] += fantasy_data.get("expected_bowling_points", 0)
            existing_player["bowling_breakdown"] = fantasy_data.get("breakdown", {})
        else:
            all_fantasy_players.append({
                "player_name": player,
                "team": "team2",
                "role": "bowler",
                "expected_points": fantasy_data.get("expected_bowling_points", 0),
                "confidence": fantasy_data.get("confidence", 0),
                "breakdown": fantasy_data.get("breakdown", {})
            })
    
    # Sort by expected points descending
    all_fantasy_players.sort(key=lambda x: x["expected_points"], reverse=True)
    
    return {
        "top_fantasy_picks": all_fantasy_players[:15],  # Top 15 picks
        "team1_batting_fantasy": team1_batting_fantasy,
        "team1_bowling_fantasy": team1_bowling_fantasy,
        "team2_batting_fantasy": team2_batting_fantasy,
        "team2_bowling_fantasy": team2_bowling_fantasy
    }

def get_team_matchups_service(
    team1: str,
    team2: str,
    start_date: Optional[date],
    end_date: Optional[date],
    team1_players: List[str],
    team2_players: List[str],
    db
):
    try:
        use_custom_teams = len(team1_players) > 0 and len(team2_players) > 0

        if not use_custom_teams:
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
                team1_players AS (
                    SELECT DISTINCT batter as player
                    FROM deliveries d
                    JOIN recent_matches rm ON d.match_id = rm.id
                    WHERE batting_team = ANY(:team1_names)
                    UNION
                    SELECT DISTINCT bowler
                    FROM deliveries d
                    JOIN recent_matches rm ON d.match_id = rm.id
                    WHERE bowling_team = :team1
                ),
                team2_players AS (
                    SELECT DISTINCT batter as player
                    FROM deliveries d
                    JOIN recent_matches rm ON d.match_id = rm.id
                    WHERE batting_team = ANY(:team2_names)
                    UNION
                    SELECT DISTINCT bowler
                    FROM deliveries d
                    JOIN recent_matches rm ON d.match_id = rm.id
                    WHERE bowling_team = :team2
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
            team1_players = [row[0] for row in recent_players if row[1] == team1]
            team2_players = [row[0] for row in recent_players if row[1] == team2]

        matchup_query = text("""
            WITH player_stats AS (
                SELECT 
                    d.batter,
                    d.bowler,
                    COUNT(*) as balls,
                    SUM(d.runs_off_bat + d.extras) as runs,
                    SUM(CASE WHEN d.wicket_type IS NOT NULL AND d.wicket_type != 'run out' THEN 1 ELSE 0 END) as wickets,
                    SUM(CASE WHEN d.runs_off_bat IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                    SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as dots
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE 
                    (d.batter = ANY(:team1_players) AND d.bowler = ANY(:team2_players)
                    OR d.batter = ANY(:team2_players) AND d.bowler = ANY(:team1_players))
                    AND (:start_date IS NULL OR m.date >= :start_date)
                    AND (:end_date IS NULL OR m.date <= :end_date)
                GROUP BY d.batter, d.bowler
                HAVING COUNT(*) >= 6
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
                "balls": row[2],
                "runs": row[3],
                "wickets": row[4],
                "boundaries": row[5],
                "dots": row[6],
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
            "fantasy_analysis": fantasy_analysis
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))