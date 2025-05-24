from sqlalchemy.sql import text
from fastapi import HTTPException
from typing import List, Optional
from datetime import date
from models import teams_mapping

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

        return {
            "team1": {
                "name": team1,
                "players": team1_players,
                "batting_matchups": team1_batting
            },
            "team2": {
                "name": team2,
                "players": team2_players,
                "batting_matchups": team2_batting
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))