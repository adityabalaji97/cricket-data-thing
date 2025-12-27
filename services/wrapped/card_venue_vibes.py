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
    
    Compares venue characteristics - par scores, boundary %, run rates.
    Uses delivery_details table for accurate ball-by-ball data.
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
    
    # Get venue stats including estimated par score and chase win %
    query = f"""
        WITH venue_innings AS (
            SELECT 
                dd.ground as venue,
                dd.p_match,
                dd.innings,
                SUM(dd.score) as inns_runs,
                COUNT(*) as balls
            FROM delivery_details dd
            {where_clause}
            GROUP BY dd.ground, dd.p_match, dd.innings
        ),
        venue_matches AS (
            SELECT 
                venue,
                p_match,
                MAX(CASE WHEN innings = 1 THEN inns_runs END) as first_inns_score,
                MAX(CASE WHEN innings = 2 THEN inns_runs END) as second_inns_score
            FROM venue_innings
            GROUP BY venue, p_match
            HAVING COUNT(DISTINCT innings) = 2
        ),
        venue_stats AS (
            SELECT 
                venue,
                COUNT(DISTINCT p_match) as matches,
                ROUND(AVG(first_inns_score + second_inns_score) / 2.0, 0) as par_score,
                ROUND(
                    SUM(CASE WHEN second_inns_score > first_inns_score THEN 1 ELSE 0 END) * 100.0 
                    / NULLIF(COUNT(*), 0), 
                    1
                ) as chase_win_pct
            FROM venue_matches
            WHERE first_inns_score IS NOT NULL AND second_inns_score IS NOT NULL
            GROUP BY venue
            HAVING COUNT(DISTINCT p_match) >= 3
        )
        SELECT 
            venue,
            matches,
            par_score,
            COALESCE(chase_win_pct, 50) as chase_win_pct
        FROM venue_stats
        ORDER BY matches DESC
        LIMIT 20
    """
    
    results = execute_query(db, query, params)
    
    venues = [
        {
            "name": row.venue,
            "matches": row.matches,
            "par_score": int(row.par_score) if row.par_score else 160,
            "chase_win_pct": float(row.chase_win_pct) if row.chase_win_pct else 50
        }
        for row in results
    ]
    
    # Sort for highest/lowest scoring
    highest_scoring = sorted(venues, key=lambda x: x['par_score'], reverse=True)[:5]
    lowest_scoring = sorted(venues, key=lambda x: x['par_score'])[:5]
    
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
