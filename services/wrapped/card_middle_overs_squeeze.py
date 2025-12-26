"""
Middle Overs Squeeze Card

Spinners who choked the run flow in middle overs (7-15).
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_MIN_BALLS, DEFAULT_TOP_TEAMS


def get_middle_overs_squeeze_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 60,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: Middle Overs Squeeze
    
    Finds bowlers with best economy in middle overs.
    High dot% and low economy is better.
    """
    
    where_clause, params = build_base_filters(
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        top_teams=top_teams,
        table_alias="dd",
        use_year=True,
        extra_conditions=[
            "dd.over >= 6 AND dd.over < 15",  # Middle overs: 7-15
            "dd.bowl_style IS NOT NULL"
        ]
    )
    
    params["min_balls"] = min_balls
    
    query = f"""
        WITH bowler_stats AS (
            SELECT 
                dd.bowl as bowler,
                dd.team_bowl as team,
                COUNT(*) as balls,
                SUM(dd.score) as runs,
                SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets,
                SUM(CASE WHEN dd.score = 0 AND COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 ELSE 0 END) as dots,
                SUM(CASE WHEN dd.score IN (4, 6) THEN 1 ELSE 0 END) as boundaries
            FROM delivery_details dd
            {where_clause}
            GROUP BY dd.bowl, dd.team_bowl
        ),
        bowler_primary_team AS (
            SELECT DISTINCT ON (bowler) bowler, team
            FROM bowler_stats
            ORDER BY bowler, balls DESC
        ),
        bowler_totals AS (
            SELECT 
                bs.bowler,
                SUM(bs.balls) as balls,
                SUM(bs.runs) as runs,
                SUM(bs.wickets) as wickets,
                SUM(bs.dots) as dots,
                SUM(bs.boundaries) as boundaries
            FROM bowler_stats bs
            GROUP BY bs.bowler
            HAVING SUM(bs.balls) >= :min_balls
        )
        SELECT 
            bt.bowler,
            bpt.team,
            bt.balls,
            bt.runs,
            bt.wickets,
            ROUND((bt.balls / 6.0)::numeric, 1) as overs,
            ROUND((bt.runs * 6.0 / bt.balls)::numeric, 2) as economy,
            ROUND((bt.dots * 100.0 / bt.balls)::numeric, 2) as dot_percentage,
            ROUND((bt.boundaries * 100.0 / bt.balls)::numeric, 2) as boundary_percentage
        FROM bowler_totals bt
        JOIN bowler_primary_team bpt ON bt.bowler = bpt.bowler
        ORDER BY economy ASC
        LIMIT 20
    """
    
    results = execute_query(db, query, params)
    
    bowlers = [
        {
            "name": row.bowler,
            "team": row.team,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "wickets": row.wickets or 0,
            "overs": float(row.overs) if row.overs else 0,
            "economy": float(row.economy) if row.economy else 0,
            "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
            "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0
        }
        for row in results
    ]
    
    return {
        "card_id": "middle_overs_squeeze",
        "card_title": "Middle Overs Squeeze",
        "card_subtitle": f"Bowlers who choked the run flow (min {min_balls} balls)",
        "visualization_type": "scatter",
        "axes": {
            "x": "dot_percentage",
            "y": "economy",
            "x_label": "Dot %",
            "y_label": "Economy"
        },
        "bowlers": bowlers,
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=6&over_max=14&group_by=bowler&min_balls={min_balls}"
        }
    }
