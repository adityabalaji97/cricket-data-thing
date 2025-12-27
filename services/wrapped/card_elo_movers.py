"""
ELO Movers Card

Biggest ELO rating changes during the year.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import execute_query
from .constants import DEFAULT_TOP_TEAMS, WRAPPED_DEFAULT_LEAGUES, INTERNATIONAL_TEAMS_RANKED


def get_elo_movers_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: ELO Movers
    
    Teams with biggest ELO rating changes in the period.
    Uses matches table which has team1_elo and team2_elo columns.
    """
    
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "wrapped_leagues": leagues,
        "wrapped_top_teams": INTERNATIONAL_TEAMS_RANKED[:top_teams]
    }
    
    comp_filter = """
        AND (m.competition = ANY(:wrapped_leagues) 
             OR (m.competition = 'T20I' 
                 AND m.team1 = ANY(:wrapped_top_teams) 
                 AND m.team2 = ANY(:wrapped_top_teams)))
    """
    
    # Get first and last ELO for each team
    # Fixed: Apply ROW_NUMBER after UNION ALL to avoid duplicates
    query = f"""
        WITH all_team_elos AS (
            -- Combine team1 and team2 appearances
            SELECT team, elo, date, match_id
            FROM (
                SELECT 
                    m.team1 as team,
                    m.team1_elo as elo,
                    m.date,
                    m.id as match_id
                FROM matches m
                WHERE m.date >= :start_date 
                AND m.date <= :end_date
                AND m.team1_elo IS NOT NULL
                {comp_filter}
                
                UNION ALL
                
                SELECT 
                    m.team2 as team,
                    m.team2_elo as elo,
                    m.date,
                    m.id as match_id
                FROM matches m
                WHERE m.date >= :start_date 
                AND m.date <= :end_date
                AND m.team2_elo IS NOT NULL
                {comp_filter}
            ) combined
        ),
        team_ranked AS (
            SELECT 
                team,
                elo,
                date,
                ROW_NUMBER() OVER (PARTITION BY team ORDER BY date ASC, match_id ASC) as first_rn,
                ROW_NUMBER() OVER (PARTITION BY team ORDER BY date DESC, match_id DESC) as last_rn
            FROM all_team_elos
        ),
        first_elo AS (
            SELECT team, elo as start_elo
            FROM team_ranked
            WHERE first_rn = 1
        ),
        last_elo AS (
            SELECT team, elo as end_elo
            FROM team_ranked
            WHERE last_rn = 1
        ),
        team_counts AS (
            SELECT team, COUNT(*) as matches
            FROM all_team_elos
            GROUP BY team
            HAVING COUNT(*) >= 3
        )
        SELECT 
            f.team,
            f.start_elo,
            l.end_elo,
            (l.end_elo - f.start_elo) as elo_change,
            tc.matches
        FROM first_elo f
        JOIN last_elo l ON f.team = l.team
        JOIN team_counts tc ON f.team = tc.team
        ORDER BY elo_change DESC
    """
    
    results = execute_query(db, query, params)
    
    teams = [
        {
            "team": row.team,
            "start_elo": float(row.start_elo) if row.start_elo else 1500,
            "end_elo": float(row.end_elo) if row.end_elo else 1500,
            "elo_change": float(row.elo_change) if row.elo_change else 0,
            "matches": row.matches
        }
        for row in results
    ]
    
    # Split into risers and fallers
    risers = [t for t in teams if t['elo_change'] > 0][:7]
    fallers = [t for t in teams if t['elo_change'] < 0]
    fallers = sorted(fallers, key=lambda x: x['elo_change'])[:5]
    
    return {
        "card_id": "elo_movers",
        "card_title": "ELO Movers",
        "card_subtitle": "Biggest rating changes",
        "visualization_type": "elo_changes",
        "risers": risers,
        "fallers": fallers,
        "all_teams": teams,
        "deep_links": {}
    }
