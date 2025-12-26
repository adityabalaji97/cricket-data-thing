"""
Middle Merchants Card

Best performers in overs 7-15 (middle overs phase).
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_MIN_BALLS, DEFAULT_TOP_TEAMS


def get_middle_merchants_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 75,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: Middle Merchants
    
    Finds batters who excel in middle overs (7-15).
    Balance of strike rate and low dot percentage valued.
    """
    
    # Build filters with middle overs condition
    where_clause, params = build_base_filters(
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        top_teams=top_teams,
        table_alias="dd",
        use_year=True,
        extra_conditions=[
            "dd.over >= 6 AND dd.over < 15",  # Middle overs: 7-15 (0-indexed: 6-14)
            "dd.bat_hand IN ('LHB', 'RHB')"
        ]
    )
    
    params["min_balls"] = min_balls
    
    query = f"""
        WITH player_stats AS (
            SELECT 
                dd.bat as player,
                dd.team_bat as team,
                COUNT(*) as balls,
                SUM(dd.score) as runs,
                SUM(CASE WHEN dd.score = 0 AND COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 ELSE 0 END) as dots,
                SUM(CASE WHEN dd.score IN (4, 6) THEN 1 ELSE 0 END) as boundaries
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
                SUM(ps.dots) as dots,
                SUM(ps.boundaries) as boundaries
            FROM player_stats ps
            GROUP BY ps.player
            HAVING SUM(ps.balls) >= :min_balls
        )
        SELECT 
            pt.player,
            ppt.team,
            pt.balls,
            pt.runs,
            pt.boundaries,
            ROUND((pt.runs * 100.0 / pt.balls)::numeric, 2) as strike_rate,
            ROUND((pt.dots * 100.0 / pt.balls)::numeric, 2) as dot_percentage,
            ROUND((pt.boundaries * 100.0 / pt.balls)::numeric, 2) as boundary_percentage
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
            "boundaries": row.boundaries or 0,
            "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
            "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
            "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0
        }
        for row in results
    ]
    
    return {
        "card_id": "middle_merchants",
        "card_title": "Middle Merchants",
        "card_subtitle": f"Best performers in overs 7-15 (min {min_balls} balls)",
        "visualization_type": "scatter",
        "axes": {
            "x": "dot_percentage",
            "y": "strike_rate",
            "x_label": "Dot %",
            "y_label": "Strike Rate"
        },
        "players": players,
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=6&over_max=14&group_by=batter&min_balls={min_balls}"
        }
    }
