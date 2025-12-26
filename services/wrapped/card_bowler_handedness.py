"""
Bowler Handedness Card

Left arm vs Right arm bowling performance.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_TOP_TEAMS


def get_bowler_handedness_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: Bowler Handedness
    
    Compares left-arm vs right-arm bowling.
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
            "dd.bowl_style IS NOT NULL"
        ]
    )
    
    # Determine arm from bowl_style (L* = left arm, others = right arm)
    query = f"""
        SELECT 
            CASE 
                WHEN dd.bowl_style LIKE 'L%' THEN 'Left Arm'
                ELSE 'Right Arm'
            END as arm,
            COUNT(*) as balls,
            SUM(dd.score) as runs,
            SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets,
            SUM(CASE WHEN dd.score = 0 AND COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 ELSE 0 END) as dots,
            COUNT(DISTINCT dd.bowl) as unique_bowlers,
            ROUND((SUM(dd.score) * 6.0 / COUNT(*))::numeric, 2) as economy,
            ROUND((SUM(CASE WHEN dd.score = 0 AND COALESCE(dd.wide, 0) = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*))::numeric, 2) as dot_pct,
            CASE 
                WHEN SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) > 0 
                THEN ROUND((COUNT(*)::numeric / SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END)), 2)
                ELSE NULL
            END as strike_rate
        FROM delivery_details dd
        {where_clause}
        GROUP BY 
            CASE 
                WHEN dd.bowl_style LIKE 'L%' THEN 'Left Arm'
                ELSE 'Right Arm'
            END
        ORDER BY arm
    """
    
    results = execute_query(db, query, params)
    
    arms = {}
    for row in results:
        arms[row.arm] = {
            "arm": row.arm,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "wickets": row.wickets or 0,
            "dots": row.dots or 0,
            "unique_bowlers": row.unique_bowlers,
            "economy": float(row.economy) if row.economy else 0,
            "dot_pct": float(row.dot_pct) if row.dot_pct else 0,
            "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
            "average": round(int(row.runs) / row.wickets, 2) if row.wickets and row.wickets > 0 else 0
        }
    
    return {
        "card_id": "bowler_handedness",
        "card_title": "Bowler Handedness",
        "card_subtitle": "Left arm vs Right arm bowling",
        "visualization_type": "hand_comparison",
        "left_arm": arms.get("Left Arm", {}),
        "right_arm": arms.get("Right Arm", {}),
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=bowl_style"
        }
    }
