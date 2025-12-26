"""
Powerplay Thieves Card

Best economy bowlers in overs 1-6 (powerplay phase).
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_MIN_BALLS, DEFAULT_TOP_TEAMS


def get_powerplay_thieves_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 60,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: Powerplay Thieves
    
    Finds bowlers with best economy in powerplay overs.
    Lower strike rate and boundary% is better.
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
            "dd.over < 6",  # Powerplay: overs 0-5
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
            ROUND((bt.runs * 6.0 / bt.balls)::numeric, 2) as economy,
            CASE 
                WHEN bt.wickets > 0 THEN ROUND((bt.balls::numeric / bt.wickets), 2)
                ELSE NULL
            END as strike_rate,
            ROUND((bt.dots * 100.0 / bt.balls)::numeric, 2) as dot_percentage,
            ROUND((bt.boundaries * 100.0 / bt.balls)::numeric, 2) as boundary_percentage
        FROM bowler_totals bt
        JOIN bowler_primary_team bpt ON bt.bowler = bpt.bowler
        WHERE bt.wickets > 0
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
            "economy": float(row.economy) if row.economy else 0,
            "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
            "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
            "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0
        }
        for row in results
    ]
    
    return {
        "card_id": "powerplay_thieves",
        "card_title": "Powerplay Thieves",
        "card_subtitle": f"Best economy in overs 1-6 (min {min_balls} balls)",
        "visualization_type": "scatter",
        "axes": {
            "x": "boundary_percentage",
            "y": "strike_rate",
            "x_label": "Boundary %",
            "y_label": "Strike Rate"
        },
        "bowlers": bowlers,
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_max=5&group_by=bowler&min_balls={min_balls}"
        }
    }
