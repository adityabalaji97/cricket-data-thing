"""
Venue Vibes Card

How different grounds played this year.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_TOP_TEAMS, WRAPPED_DEFAULT_LEAGUES, INTERNATIONAL_TEAMS_RANKED


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
    
    Compares venue characteristics - par scores, chase win %, etc.
    Uses matches table for accurate match-level stats.
    """
    
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "wrapped_leagues": leagues,
        "wrapped_top_teams": INTERNATIONAL_TEAMS_RANKED[:top_teams]
    }
    
    # Build competition filter for matches table
    comp_filter = """
        AND (m.competition = ANY(:wrapped_leagues) 
             OR (m.competition = 'T20I' 
                 AND m.team1 = ANY(:wrapped_top_teams) 
                 AND m.team2 = ANY(:wrapped_top_teams)))
    """
    
    query = f"""
        WITH venue_matches AS (
            SELECT 
                m.ground as venue,
                m.id,
                m.team1_score,
                m.team2_score,
                m.winner,
                m.team1,
                m.team2,
                m.toss_winner,
                m.toss_decision
            FROM matches m
            WHERE m.date >= :start_date 
            AND m.date <= :end_date
            AND m.ground IS NOT NULL
            AND m.team1_score IS NOT NULL
            AND m.team2_score IS NOT NULL
            {comp_filter}
        ),
        venue_stats AS (
            SELECT 
                venue,
                COUNT(*) as matches,
                ROUND(AVG(team1_score + team2_score) / 2.0, 0) as par_score,
                -- Chase win % = matches where team batting second won
                ROUND(
                    SUM(CASE 
                        WHEN toss_decision = 'field' AND winner = toss_winner THEN 1
                        WHEN toss_decision = 'bat' AND winner != toss_winner AND winner IS NOT NULL THEN 1
                        ELSE 0
                    END) * 100.0 / NULLIF(COUNT(*), 0),
                    1
                ) as chase_win_pct
            FROM venue_matches
            GROUP BY venue
            HAVING COUNT(*) >= 3
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
