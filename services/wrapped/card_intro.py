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
    
    Provides overview statistics for the year including:
    - Total matches
    - Phase-wise run rates
    - Toss/chase statistics
    """
    
    # Build filters for delivery_details
    where_clause, params = build_base_filters(
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        top_teams=top_teams,
        table_alias="dd",
        use_year=True
    )
    
    # Get total matches
    matches_query = f"""
        SELECT COUNT(DISTINCT dd.p_match) as total_matches
        FROM delivery_details dd
        {where_clause}
    """
    
    matches_result = execute_query(db, matches_query, params)
    total_matches = matches_result[0].total_matches if matches_result else 0
    
    # Get phase-wise run rates
    phases_query = f"""
        SELECT 
            phase,
            balls,
            runs,
            run_rate
        FROM (
            SELECT 
                CASE 
                    WHEN dd.over < 6 THEN 'powerplay'
                    WHEN dd.over < 15 THEN 'middle'
                    ELSE 'death'
                END as phase,
                COUNT(*) as balls,
                SUM(dd.score) as runs,
                ROUND((SUM(dd.score) * 6.0 / COUNT(*))::numeric, 2) as run_rate
            FROM delivery_details dd
            {where_clause}
            GROUP BY 
                CASE 
                    WHEN dd.over < 6 THEN 'powerplay'
                    WHEN dd.over < 15 THEN 'middle'
                    ELSE 'death'
                END
        ) phase_stats
        ORDER BY 
            CASE phase
                WHEN 'powerplay' THEN 1
                WHEN 'middle' THEN 2
                ELSE 3
            END
    """
    
    phases_result = execute_query(db, phases_query, params)
    
    phases = []
    for row in phases_result:
        phases.append({
            "phase": row.phase,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "run_rate": float(row.run_rate) if row.run_rate else 0
        })
    
    # Get toss/batting first stats using matches table
    match_where, match_params = build_base_filters(
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        top_teams=top_teams,
        table_alias="m",
        use_year=False  # matches table uses date column
    )
    
    toss_query = f"""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN m.winner = m.bat_first THEN 1 ELSE 0 END) as bat_first_wins,
            SUM(CASE WHEN m.winner = m.bowl_first THEN 1 ELSE 0 END) as chase_wins
        FROM matches m
        {match_where}
        AND m.winner IS NOT NULL
        AND m.bat_first IS NOT NULL
    """
    
    toss_result = execute_query(db, toss_query, match_params)
    
    toss_stats = None
    if toss_result and toss_result[0].total and toss_result[0].total > 0:
        total = toss_result[0].total
        bat_first_wins = toss_result[0].bat_first_wins or 0
        chase_wins = toss_result[0].chase_wins or 0
        
        toss_stats = {
            "total_decided": total,
            "bat_first_wins": bat_first_wins,
            "chase_wins": chase_wins,
            "bat_first_pct": round((bat_first_wins * 100) / total, 1) if total > 0 else 50
        }
    
    return {
        "card_id": "intro",
        "card_title": "2025 In Hindsight",
        "card_subtitle": "The Year in T20 Cricket",
        "visualization_type": "intro",
        "total_matches": total_matches,
        "phases": phases,
        "toss_stats": toss_stats,
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
