"""
Powerplay Bullies Card

Highest strike rates in overs 1-6 (powerplay phase).
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query, build_query_url
from .constants import DEFAULT_MIN_BALLS, DEFAULT_TOP_TEAMS


def get_powerplay_bullies_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = DEFAULT_MIN_BALLS,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: Powerplay Bullies
    
    Finds batters with highest strike rates during powerplay (overs 0-5).
    Filters by minimum balls faced for statistical significance.
    """
    
    # Build filters with powerplay condition
    where_clause, params = build_base_filters(
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        top_teams=top_teams,
        table_alias="dd",
        use_year=True,
        extra_conditions=[
            "dd.over < 6",  # Powerplay: overs 0-5
            "dd.bat_hand IN ('LHB', 'RHB')"  # Valid batter hand
        ]
    )
    
    params["min_balls"] = min_balls
    
    # Note: Using score for per-ball runs, checking wide/noball as integers
    query = f"""
        WITH player_stats AS (
            SELECT 
                dd.bat as player,
                dd.team_bat as team,
                COUNT(*) as balls,
                SUM(dd.score) as runs,
                SUM(CASE WHEN dd.score = 0 AND COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 ELSE 0 END) as dots
            FROM delivery_details dd
            {where_clause}
            GROUP BY dd.bat, dd.team_bat
        ),
        player_primary_team AS (
            SELECT DISTINCT ON (player) player, team
            FROM player_stats
            ORDER BY player, balls DESC
        ),
        player_totals AS (
            SELECT 
                ps.player,
                SUM(ps.balls) as balls,
                SUM(ps.runs) as runs,
                SUM(ps.dots) as dots
            FROM player_stats ps
            GROUP BY ps.player
            HAVING SUM(ps.balls) >= :min_balls
        )
        SELECT 
            pt.player,
            ppt.team,
            pt.balls,
            pt.runs,
            ROUND((pt.runs * 100.0 / pt.balls)::numeric, 2) as strike_rate,
            ROUND((pt.dots * 100.0 / pt.balls)::numeric, 2) as dot_percentage
        FROM player_totals pt
        JOIN player_primary_team ppt ON pt.player = ppt.player
        ORDER BY strike_rate DESC
        LIMIT 20
    """
    
    results = execute_query(db, query, params)
    
    players = [
        {
            "name": row.player,
            "team": row.team,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
            "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0
        }
        for row in results
    ]
    
    return {
        "card_id": "powerplay_bullies",
        "card_title": "Powerplay Bullies",
        "card_subtitle": f"Highest strike rates in overs 1-6 (min {min_balls} balls)",
        "visualization_type": "scatter",
        "axes": {
            "x": "dot_percentage",
            "y": "strike_rate",
            "x_label": "Dot %",
            "y_label": "Strike Rate"
        },
        "players": players,
        "deep_links": {
            "query_builder": build_query_url(
                start_date=start_date,
                end_date=end_date,
                leagues=leagues,
                include_international=include_international,
                top_teams=top_teams,
                over_max=5,
                group_by="batter",
                min_balls=min_balls
            )
        }
    }
