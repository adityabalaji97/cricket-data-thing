"""
Bowler Type Dominance Card

Which bowling styles ruled the year.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_TOP_TEAMS


def get_bowler_type_dominance_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: Bowler Type Dominance
    
    Compares performance of different bowling styles (pace vs spin variants).
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
            "dd.bowl_kind IS NOT NULL"
        ]
    )
    
    query = f"""
        SELECT 
            dd.bowl_kind as bowling_type,
            COUNT(*) as balls,
            SUM(dd.score) as runs,
            SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets,
            SUM(CASE WHEN dd.score = 0 AND COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 ELSE 0 END) as dots,
            ROUND((SUM(dd.score) * 6.0 / COUNT(*))::numeric, 2) as economy,
            ROUND((SUM(CASE WHEN dd.score = 0 AND COALESCE(dd.wide, 0) = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*))::numeric, 2) as dot_percentage,
            CASE 
                WHEN SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) > 0 
                THEN ROUND((COUNT(*)::numeric / SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END)), 2)
                ELSE NULL
            END as strike_rate
        FROM delivery_details dd
        {where_clause}
        GROUP BY dd.bowl_kind
        HAVING COUNT(*) >= 500
        ORDER BY economy ASC
    """
    
    results = execute_query(db, query, params)
    
    bowling_types = [
        {
            "type": row.bowling_type,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "wickets": row.wickets or 0,
            "dots": row.dots or 0,
            "economy": float(row.economy) if row.economy else 0,
            "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
            "strike_rate": float(row.strike_rate) if row.strike_rate else None
        }
        for row in results
    ]
    
    return {
        "card_id": "bowler_type_dominance",
        "card_title": "Bowler Type Dominance",
        "card_subtitle": "Which bowling styles ruled?",
        "visualization_type": "comparison_bars",
        "bowling_types": bowling_types,
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=bowl_kind"
        }
    }
