"""
Games Router - endpoints for interactive game modes.
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from database import get_session
from utils.league_utils import expand_league_abbreviations

router = APIRouter(prefix="/games", tags=["games"])

# Top 10 international teams for T20I filtering
TOP_10_TEAMS = [
    'India', 'Australia', 'England', 'West Indies', 'New Zealand',
    'South Africa', 'Pakistan', 'Sri Lanka', 'Bangladesh', 'Afghanistan'
]


@router.get("/guess-innings")
def get_guess_innings(
    leagues: List[str] = Query(default=["IPL", "T20I"]),
    competitions: List[str] = Query(default=[]),
    start_date: Optional[date] = Query(default=date(2015, 1, 1)),
    end_date: Optional[date] = Query(default=None),
    pool_limit: int = Query(default=1000, ge=1, le=5000),
    min_runs: int = Query(default=0, ge=0),
    min_balls: int = Query(default=0, ge=0),
    min_strike_rate: float = Query(default=0, ge=0),
    include_answer: bool = Query(default=False),
    db: Session = Depends(get_session),
):
    """
    Fetch a random innings (with wagon wheel data) for the Guess the Innings game.

    The innings pool is restricted to the top N by runs, balls faced, or strike rate,
    and is filtered by competition and date range.
    """

    if end_date and start_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date cannot be earlier than start_date")

    expanded_leagues = expand_league_abbreviations(leagues) if leagues else []
    competition_filter = competitions or expanded_leagues
    if not competition_filter:
        raise HTTPException(status_code=400, detail="At least one competition or league must be provided")

    # Use pre-computed materialized view for speed (no GROUP BY needed)
    # For T20I, filter to only top 10 international teams
    innings_query = text(
        """
        SELECT
            match_id,
            innings,
            batter,
            venue,
            competition,
            match_date,
            balls,
            runs,
            strike_rate,
            bat_hand,
            batting_team,
            bowling_team
        FROM guess_innings_pool
        WHERE competition = ANY(:competitions)
          AND match_date::date >= :start_date
          AND (:end_date IS NULL OR match_date::date <= :end_date)
          AND balls >= :min_balls
          AND runs >= :min_runs
          AND strike_rate >= :min_strike_rate
          AND (
            competition != 'International Twenty20'
            OR (batting_team = ANY(:top_teams) AND bowling_team = ANY(:top_teams))
          )
        ORDER BY RANDOM()
        LIMIT 1
        """
    )

    result = db.execute(
        innings_query,
        {
            "competitions": competition_filter,
            "start_date": start_date,
            "end_date": end_date,
            "min_runs": min_runs,
            "min_balls": min_balls,
            "min_strike_rate": min_strike_rate,
            "top_teams": TOP_10_TEAMS,
        },
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="No innings found for the specified filters")

    deliveries_query = text(
        """
        SELECT
            dd.over,
            dd.ball,
            dd.score AS runs,
            dd.shot,
            dd.bowl AS bowler,
            dd.wagon_x,
            dd.wagon_y,
            dd.wagon_zone,
            dd.bat_hand,
            dd.team_bat AS batting_team,
            dd.team_bowl AS bowling_team,
            dd.cur_bat_runs,
            dd.cur_bat_bf
        FROM delivery_details dd
        WHERE dd.p_match = :match_id
          AND dd.inns = :innings
          AND dd.bat = :batter
          AND dd.wagon_x IS NOT NULL
          AND dd.wagon_y IS NOT NULL
        ORDER BY dd.over, dd.ball
        """
    )

    deliveries = db.execute(
        deliveries_query,
        {
            "match_id": result.match_id,
            "innings": result.innings,
            "batter": result.batter,
        },
    ).fetchall()

    if not deliveries:
        raise HTTPException(status_code=404, detail="No wagon wheel deliveries found for this innings")

    # Use pre-computed values from materialized view, fall back to deliveries if needed
    last_delivery = deliveries[-1] if deliveries else None

    # Use cur_bat_runs and cur_bat_bf from last delivery for accurate batter stats
    batter_runs = int(last_delivery.cur_bat_runs) if last_delivery and last_delivery.cur_bat_runs is not None else int(result.runs) if result.runs else 0
    batter_balls = int(last_delivery.cur_bat_bf) if last_delivery and last_delivery.cur_bat_bf is not None else int(result.balls) if result.balls else 0
    batter_sr = round((batter_runs * 100.0 / batter_balls), 2) if batter_balls > 0 else 0.0

    # Use pre-computed fields from view
    bat_hand = result.bat_hand if hasattr(result, 'bat_hand') else (deliveries[0].bat_hand if deliveries else None)
    batting_team = result.batting_team if hasattr(result, 'batting_team') else (deliveries[0].batting_team if deliveries else None)
    bowling_team = result.bowling_team if hasattr(result, 'bowling_team') else (deliveries[0].bowling_team if deliveries else None)

    payload = {
        "innings": {
            "match_id": result.match_id,
            "innings": result.innings,
            "venue": result.venue,
            "competition": result.competition,
            "match_date": str(result.match_date) if result.match_date else None,
            "runs": batter_runs,
            "balls": batter_balls,
            "strike_rate": batter_sr,
            "bat_hand": bat_hand,
            "batting_team": batting_team,
            "bowling_team": bowling_team,
        },
        "deliveries": [
            {
                "over": row.over,
                "ball": row.ball,
                "runs": row.runs,
                "shot": row.shot,
                "bowler": row.bowler,
                "wagon_x": row.wagon_x,
                "wagon_y": row.wagon_y,
                "wagon_zone": row.wagon_zone,
            }
            for row in deliveries
        ],
        "filters": {
            "competitions": competition_filter,
            "start_date": str(start_date) if start_date else None,
            "end_date": str(end_date) if end_date else None,
            "pool_limit": pool_limit,
            "min_runs": min_runs,
            "min_balls": min_balls,
            "min_strike_rate": min_strike_rate,
        },
    }

    if include_answer:
        payload["answer"] = {
            "batter": result.batter,
        }

    return payload


# IPL team name normalization for franchise renames
IPL_TEAM_NAMES = {
    'Delhi Daredevils': 'Delhi Capitals',
    'Deccan Chargers': 'Sunrisers Hyderabad',
    'Rising Pune Supergiants': 'Rising Pune Supergiant',
    'Kings XI Punjab': 'Punjab Kings',
}


def normalize_ipl_team(team_name: str) -> str:
    """Normalize IPL team names for franchise renames."""
    return IPL_TEAM_NAMES.get(team_name, team_name)


def collapse_year_ranges(team_years: list) -> list:
    """
    Collapse consecutive years into ranges.
    Input: [('CSK', 2008), ('CSK', 2009), ('CSK', 2010), ('PWI', 2011), ...]
    Output: [{'team': 'Chennai Super Kings', 'years': '2008-2010'}, ...]
    """
    if not team_years:
        return []

    result = []
    current_team = team_years[0][0]
    start_year = team_years[0][1]
    end_year = team_years[0][1]

    for i in range(1, len(team_years)):
        team, year = team_years[i]
        if team == current_team and year == end_year + 1:
            # Consecutive year, same team
            end_year = year
        else:
            # New team or gap in years
            years_str = str(start_year) if start_year == end_year else f"{start_year}-{end_year}"
            result.append({"team": current_team, "years": years_str})
            current_team = team
            start_year = year
            end_year = year

    # Don't forget the last range
    years_str = str(start_year) if start_year == end_year else f"{start_year}-{end_year}"
    result.append({"team": current_team, "years": years_str})

    return result


@router.get("/player-journey")
def get_player_journey(
    include_answer: bool = Query(default=False),
    min_seasons: int = Query(default=3, ge=1),
    db: Session = Depends(get_session),
):
    """
    Fetch a random player's IPL team journey for the guessing game.
    Returns chronological list of teams the player has played for.
    Combines batting and bowling appearances from delivery_details,
    using player_aliases for canonical names.
    """

    # Combine batting and bowling appearances, use canonical names from player_aliases
    journey_query = text(
        """
        WITH all_appearances AS (
            -- Batting appearances
            SELECT
                dd.bat AS raw_name,
                dd.team_bat AS team,
                EXTRACT(YEAR FROM m.date)::int AS year,
                SUM(dd.score) AS runs,
                COUNT(*) AS balls,
                0 AS wickets
            FROM delivery_details dd
            JOIN matches m ON dd.p_match = m.id
            WHERE m.competition = 'Indian Premier League'
              AND dd.bat IS NOT NULL
              AND dd.team_bat IS NOT NULL
            GROUP BY dd.bat, dd.team_bat, EXTRACT(YEAR FROM m.date)

            UNION ALL

            -- Bowling appearances
            SELECT
                dd.bowl AS raw_name,
                dd.team_bowl AS team,
                EXTRACT(YEAR FROM m.date)::int AS year,
                0 AS runs,
                0 AS balls,
                SUM(CASE WHEN dd.out::boolean = true THEN 1 ELSE 0 END) AS wickets
            FROM delivery_details dd
            JOIN matches m ON dd.p_match = m.id
            WHERE m.competition = 'Indian Premier League'
              AND dd.bowl IS NOT NULL
              AND dd.team_bowl IS NOT NULL
            GROUP BY dd.bowl, dd.team_bowl, EXTRACT(YEAR FROM m.date)
        ),
        -- Map to canonical names using player_aliases
        appearances_with_canonical AS (
            SELECT
                COALESCE(pa.alias_name, aa.raw_name) AS player_name,
                aa.raw_name,
                aa.team,
                aa.year,
                aa.runs,
                aa.balls,
                aa.wickets
            FROM all_appearances aa
            LEFT JOIN player_aliases pa ON aa.raw_name = pa.player_name
        ),
        -- Aggregate by canonical name, team, year
        player_team_years AS (
            SELECT
                player_name,
                team,
                year,
                SUM(runs) AS total_runs,
                SUM(balls) AS total_balls,
                SUM(wickets) AS total_wickets
            FROM appearances_with_canonical
            GROUP BY player_name, team, year
        ),
        player_stats AS (
            SELECT
                player_name,
                COUNT(DISTINCT year) AS seasons,
                SUM(total_runs) AS career_runs,
                SUM(total_balls) AS career_balls,
                SUM(total_wickets) AS career_wickets,
                COUNT(DISTINCT team) AS num_teams
            FROM player_team_years
            GROUP BY player_name
            HAVING COUNT(DISTINCT year) >= :min_seasons
        )
        SELECT
            pty.player_name,
            pty.team,
            pty.year,
            ps.career_runs,
            ps.career_balls,
            ps.career_wickets,
            ps.seasons,
            ps.num_teams
        FROM player_team_years pty
        JOIN player_stats ps ON pty.player_name = ps.player_name
        WHERE pty.player_name = (
            SELECT player_name FROM player_stats ORDER BY RANDOM() LIMIT 1
        )
        ORDER BY pty.year, pty.team
        """
    )

    results = db.execute(
        journey_query,
        {"min_seasons": min_seasons}
    ).fetchall()

    if not results:
        raise HTTPException(status_code=404, detail="No player journey found")

    player_name = results[0].player_name
    career_runs = int(results[0].career_runs) if results[0].career_runs else 0
    career_balls = int(results[0].career_balls) if results[0].career_balls else 0
    career_wickets = int(results[0].career_wickets) if results[0].career_wickets else 0
    seasons = int(results[0].seasons) if results[0].seasons else 0
    num_teams = int(results[0].num_teams) if results[0].num_teams else 0

    # Normalize team names and build team-year list
    team_years = []
    for row in results:
        normalized_team = normalize_ipl_team(row.team)
        team_years.append((normalized_team, row.year))

    # Remove duplicates (same team, same year) and sort
    team_years = sorted(set(team_years), key=lambda x: (x[1], x[0]))

    # Collapse into ranges
    journey = collapse_year_ranges(team_years)

    payload = {
        "journey": journey,
        "stats": {
            "total_runs": career_runs,
            "total_balls": career_balls,
            "total_wickets": career_wickets,
            "total_seasons": seasons,
            "total_teams": num_teams,
            "strike_rate": round(career_runs * 100.0 / career_balls, 2) if career_balls > 0 else 0,
        },
        "filters": {
            "min_seasons": min_seasons,
        },
    }

    if include_answer:
        payload["answer"] = {
            "player": player_name,
        }

    return payload
