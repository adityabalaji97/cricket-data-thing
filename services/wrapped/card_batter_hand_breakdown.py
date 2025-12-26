"""
Batter Hand Breakdown Card

Left vs Right hand batting performance.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_TOP_TEAMS


def get_batter_hand_breakdown_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: Batter Hand Breakdown
    
    Compares left-hand vs right-hand batters.
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
            "dd.bat_hand IN ('LHB', 'RHB')"
        ]
    )
    
    query = f"""
        SELECT 
            dd.bat_hand as hand,
            COUNT(*) as balls,
            SUM(dd.score) as runs,
            SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as dismissals,
            SUM(CASE WHEN dd.score IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
            SUM(CASE WHEN dd.score = 0 AND COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 ELSE 0 END) as dots,
            COUNT(DISTINCT dd.bat) as unique_batters,
            ROUND((SUM(dd.score) * 100.0 / COUNT(*))::numeric, 2) as strike_rate,
            ROUND((SUM(CASE WHEN dd.score IN (4, 6) THEN 1 ELSE 0 END) * 100.0 / COUNT(*))::numeric, 2) as boundary_pct,
            ROUND((SUM(CASE WHEN dd.score = 0 AND COALESCE(dd.wide, 0) = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*))::numeric, 2) as dot_pct
        FROM delivery_details dd
        {where_clause}
        GROUP BY dd.bat_hand
        ORDER BY dd.bat_hand
    """
    
    results = execute_query(db, query, params)
    
    hands = {}
    for row in results:
        hand_name = "Left Hand" if row.hand == "LHB" else "Right Hand"
        hands[row.hand] = {
            "hand": row.hand,
            "hand_name": hand_name,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "dismissals": row.dismissals or 0,
            "boundaries": row.boundaries or 0,
            "unique_batters": row.unique_batters,
            "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
            "boundary_pct": float(row.boundary_pct) if row.boundary_pct else 0,
            "dot_pct": float(row.dot_pct) if row.dot_pct else 0,
            "average": round(int(row.runs) / row.dismissals, 2) if row.dismissals and row.dismissals > 0 else 0
        }
    
    return {
        "card_id": "batter_hand_breakdown",
        "card_title": "Batter Hand Breakdown",
        "card_subtitle": "Left vs Right hand performance",
        "visualization_type": "hand_comparison",
        "left_hand": hands.get("LHB", {}),
        "right_hand": hands.get("RHB", {}),
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=bat_hand"
        }
    }
