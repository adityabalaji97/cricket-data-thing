"""
Batter Hand Breakdown Card

Left vs Right hand batting performance.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_TOP_TEAMS, DEFAULT_MIN_BALLS


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
    
    Compares left-hand vs right-hand batters with aggregate stats,
    top performers, and crease combination stats.
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
    
    # 1. Aggregate stats by hand
    agg_query = f"""
        SELECT 
            dd.bat_hand as hand,
            COUNT(*) as balls,
            SUM(dd.score) as runs,
            SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as dismissals,
            SUM(CASE WHEN dd.score IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
            COUNT(DISTINCT dd.bat) as unique_batters,
            ROUND((SUM(dd.score) * 100.0 / COUNT(*))::numeric, 2) as strike_rate,
            ROUND((SUM(CASE WHEN dd.score IN (4, 6) THEN 1 ELSE 0 END) * 100.0 / COUNT(*))::numeric, 2) as boundary_pct
        FROM delivery_details dd
        {where_clause}
        GROUP BY dd.bat_hand
        ORDER BY dd.bat_hand
    """
    
    agg_results = execute_query(db, agg_query, params)
    
    hand_stats = {}
    for row in agg_results:
        avg = round(int(row.runs) / row.dismissals, 2) if row.dismissals and row.dismissals > 0 else 0
        hand_stats[row.hand] = {
            "hand": row.hand,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "dismissals": row.dismissals or 0,
            "boundaries": row.boundaries or 0,
            "unique_batters": row.unique_batters,
            "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
            "boundary_pct": float(row.boundary_pct) if row.boundary_pct else 0,
            "average": avg
        }
    
    # 2. Top performers by hand (min 50 balls for wrapped)
    params["min_balls"] = 50
    
    top_lhb_query = f"""
        SELECT 
            dd.bat as name,
            dd.team_bat as team,
            COUNT(*) as balls,
            SUM(dd.score) as runs,
            ROUND((SUM(dd.score) * 100.0 / COUNT(*))::numeric, 2) as strike_rate
        FROM delivery_details dd
        {where_clause}
        AND dd.bat_hand = 'LHB'
        GROUP BY dd.bat, dd.team_bat
        HAVING COUNT(*) >= :min_balls
        ORDER BY strike_rate DESC
        LIMIT 5
    """
    
    top_rhb_query = f"""
        SELECT 
            dd.bat as name,
            dd.team_bat as team,
            COUNT(*) as balls,
            SUM(dd.score) as runs,
            ROUND((SUM(dd.score) * 100.0 / COUNT(*))::numeric, 2) as strike_rate
        FROM delivery_details dd
        {where_clause}
        AND dd.bat_hand = 'RHB'
        GROUP BY dd.bat, dd.team_bat
        HAVING COUNT(*) >= :min_balls
        ORDER BY strike_rate DESC
        LIMIT 5
    """
    
    lhb_results = execute_query(db, top_lhb_query, params)
    rhb_results = execute_query(db, top_rhb_query, params)
    
    top_lhb = [
        {
            "name": row.name,
            "team": row.team,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "strike_rate": float(row.strike_rate) if row.strike_rate else 0
        }
        for row in lhb_results
    ]
    
    top_rhb = [
        {
            "name": row.name,
            "team": row.team,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "strike_rate": float(row.strike_rate) if row.strike_rate else 0
        }
        for row in rhb_results
    ]
    
    # 3. Crease combination stats (if crease_combo column exists)
    crease_combo_stats = []
    try:
        combo_query = f"""
            SELECT 
                CASE 
                    WHEN dd.crease_combo IN ('LHB_RHB', 'RHB_LHB') THEN 'Mixed'
                    WHEN dd.crease_combo = 'LHB_LHB' THEN 'LHB_LHB'
                    WHEN dd.crease_combo = 'RHB_RHB' THEN 'RHB_RHB'
                    ELSE 'Other'
                END as combo,
                COUNT(*) as balls,
                SUM(dd.score) as runs,
                ROUND((SUM(dd.score) * 100.0 / COUNT(*))::numeric, 2) as strike_rate
            FROM delivery_details dd
            {where_clause}
            AND dd.crease_combo IS NOT NULL
            GROUP BY 
                CASE 
                    WHEN dd.crease_combo IN ('LHB_RHB', 'RHB_LHB') THEN 'Mixed'
                    WHEN dd.crease_combo = 'LHB_LHB' THEN 'LHB_LHB'
                    WHEN dd.crease_combo = 'RHB_RHB' THEN 'RHB_RHB'
                    ELSE 'Other'
                END
            HAVING COUNT(*) >= 100
            ORDER BY strike_rate DESC
        """
        
        combo_results = execute_query(db, combo_query, params)
        crease_combo_stats = [
            {
                "combo": row.combo,
                "balls": row.balls,
                "runs": int(row.runs) if row.runs else 0,
                "strike_rate": float(row.strike_rate) if row.strike_rate else 0
            }
            for row in combo_results
            if row.combo != 'Other'
        ]
    except Exception:
        # crease_combo column may not exist
        pass
    
    return {
        "card_id": "batter_hand_breakdown",
        "card_title": "Batter Hand Breakdown",
        "card_subtitle": "Left vs Right hand performance",
        "visualization_type": "hand_comparison",
        "hand_stats": hand_stats,
        "top_lhb": top_lhb,
        "top_rhb": top_rhb,
        "crease_combo_stats": crease_combo_stats,
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=crease_combo"
        }
    }
