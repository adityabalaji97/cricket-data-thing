"""
Venue Vibes Card

How different grounds played this year.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_TOP_TEAMS


def get_venue_vibes_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: Venue Vibes
    
    Compares venue characteristics - run rates, boundary %, etc.
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
            "dd.ground IS NOT NULL"
        ]
    )
    
    query = f"""
        SELECT 
            dd.ground as venue,
            COUNT(DISTINCT dd.p_match) as matches,
            COUNT(*) as balls,
            SUM(dd.score) as runs,
            SUM(CASE WHEN dd.score IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
            SUM(CASE WHEN dd.score = 6 THEN 1 ELSE 0 END) as sixes,
            SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets,
            ROUND((SUM(dd.score) * 6.0 / COUNT(*))::numeric, 2) as run_rate,
            ROUND((SUM(CASE WHEN dd.score IN (4, 6) THEN 1 ELSE 0 END) * 100.0 / COUNT(*))::numeric, 2) as boundary_pct
        FROM delivery_details dd
        {where_clause}
        GROUP BY dd.ground
        HAVING COUNT(DISTINCT dd.p_match) >= 3
        ORDER BY run_rate DESC
        LIMIT 20
    """
    
    results = execute_query(db, query, params)
    
    venues = [
        {
            "venue": row.venue,
            "matches": row.matches,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "boundaries": row.boundaries or 0,
            "sixes": row.sixes or 0,
            "wickets": row.wickets or 0,
            "run_rate": float(row.run_rate) if row.run_rate else 0,
            "boundary_pct": float(row.boundary_pct) if row.boundary_pct else 0
        }
        for row in results
    ]
    
    # Find highest and lowest scoring venues
    highest_scoring = venues[:5] if venues else []
    lowest_scoring = sorted(venues, key=lambda x: x['run_rate'])[:5] if venues else []
    
    return {
        "card_id": "venue_vibes",
        "card_title": "Venue Vibes",
        "card_subtitle": "How different grounds played",
        "visualization_type": "venue_comparison",
        "venues": venues,
        "highest_scoring": highest_scoring,
        "lowest_scoring": lowest_scoring,
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=venue"
        }
    }
