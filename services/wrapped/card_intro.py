"""
Intro Card

Overview statistics for the wrapped experience.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_TOP_TEAMS


def get_intro_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: Intro
    
    Provides overview statistics for the year.
    """
    
    # Build filters
    where_clause, params = build_base_filters(
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        top_teams=top_teams,
        table_alias="dd",
        use_year=True
    )
    
    # Get total deliveries, runs, wickets
    stats_query = f"""
        SELECT 
            COUNT(*) as total_balls,
            SUM(dd.batruns) as total_runs,
            SUM(CASE WHEN dd.out = true THEN 1 ELSE 0 END) as total_wickets,
            SUM(CASE WHEN dd.batruns = 6 THEN 1 ELSE 0 END) as total_sixes,
            SUM(CASE WHEN dd.batruns = 4 THEN 1 ELSE 0 END) as total_fours,
            COUNT(DISTINCT dd.p_match) as total_matches,
            COUNT(DISTINCT dd.bat) as total_batters,
            COUNT(DISTINCT dd.bowl) as total_bowlers
        FROM delivery_details dd
        {where_clause}
    """
    
    result = execute_query(db, stats_query, params)
    
    if result and len(result) > 0:
        row = result[0]
        stats = {
            "total_balls": row.total_balls or 0,
            "total_runs": row.total_runs or 0,
            "total_wickets": row.total_wickets or 0,
            "total_sixes": row.total_sixes or 0,
            "total_fours": row.total_fours or 0,
            "total_matches": row.total_matches or 0,
            "total_batters": row.total_batters or 0,
            "total_bowlers": row.total_bowlers or 0
        }
    else:
        stats = {
            "total_balls": 0,
            "total_runs": 0,
            "total_wickets": 0,
            "total_sixes": 0,
            "total_fours": 0,
            "total_matches": 0,
            "total_batters": 0,
            "total_bowlers": 0
        }
    
    # Calculate derived stats
    if stats["total_balls"] > 0:
        stats["avg_run_rate"] = round((stats["total_runs"] * 6) / stats["total_balls"], 2)
        stats["boundary_percentage"] = round(
            ((stats["total_fours"] + stats["total_sixes"]) * 100) / stats["total_balls"], 2
        )
    else:
        stats["avg_run_rate"] = 0
        stats["boundary_percentage"] = 0
    
    return {
        "card_id": "intro",
        "card_title": "2025 In Hindsight",
        "card_subtitle": f"The Year in T20 Cricket",
        "visualization_type": "stats_grid",
        "stats": stats,
        "date_range": {
            "start": start_date,
            "end": end_date
        },
        "filters_applied": {
            "leagues": leagues,
            "include_international": include_international,
            "top_teams": top_teams
        }
    }
