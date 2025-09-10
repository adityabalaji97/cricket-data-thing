from sqlalchemy.sql import text
from fastapi import HTTPException
from typing import List, Dict, Optional
from datetime import date
from models import teams_mapping, leagues_mapping, INTERNATIONAL_TEAMS_RANKED

def get_recent_matches_by_league_service(db) -> Dict:
    """
    Get the most recent match for each league and T20 internationals, 
    along with match counts for each competition
    Optimized version without expensive deliveries joins
    T20I matches prioritized at the top
    """
    try:
        # Simplified query for most recent match per league - no scores for speed
        recent_league_matches_query = text("""
            WITH recent_matches AS (
                SELECT DISTINCT ON (m.competition)
                    m.id,
                    m.date,
                    m.venue,
                    m.team1,
                    m.team2,
                    m.winner,
                    m.competition,
                    m.match_type
                FROM matches m
                WHERE m.match_type = 'league'
                ORDER BY m.competition, m.date DESC
            )
            SELECT * FROM recent_matches
            ORDER BY date DESC
        """)
        
        # Simplified query for most recent T20 international match
        recent_t20i_query = text("""
            SELECT 
                m.id,
                m.date,
                m.venue,
                m.team1,
                m.team2,
                m.winner,
                m.competition,
                m.match_type
            FROM matches m
            WHERE m.match_type = 'international'
            AND (m.team1 = ANY(:international_teams) AND m.team2 = ANY(:international_teams))
            ORDER BY m.date DESC
            LIMIT 1
        """)
        
        # Simple and fast match counts query
        match_counts_query = text("""
            SELECT 
                m.competition,
                m.match_type,
                COUNT(*) as match_count,
                MIN(m.date) as earliest_date,
                MAX(m.date) as latest_date
            FROM matches m
            WHERE m.match_type IN ('league', 'international')
            GROUP BY m.competition, m.match_type
            ORDER BY match_count DESC, m.competition
        """)
        
        # Execute queries
        league_results = db.execute(recent_league_matches_query).fetchall()
        t20i_result = db.execute(recent_t20i_query, {
            "international_teams": INTERNATIONAL_TEAMS_RANKED
        }).fetchone()
        count_results = db.execute(match_counts_query).fetchall()
        
        # Format matches - T20I first, then leagues
        recent_matches = []
        
        # Add T20I match first if exists
        if t20i_result:
            t20i_match = {
                "match_id": t20i_result.id,
                "date": t20i_result.date.isoformat() if t20i_result.date else None,
                "venue": t20i_result.venue,
                "team1": teams_mapping.get(t20i_result.team1, t20i_result.team1),
                "team2": teams_mapping.get(t20i_result.team2, t20i_result.team2),
                "team1_full": t20i_result.team1,
                "team2_full": t20i_result.team2,
                "team1_score": None,  # Skip scores for performance
                "team2_score": None,  # Skip scores for performance
                "winner": teams_mapping.get(t20i_result.winner, t20i_result.winner) if t20i_result.winner else None,
                "competition": t20i_result.competition,
                "competition_abbr": "T20I",
                "match_type": t20i_result.match_type,
                "is_international": True
            }
            recent_matches.append(t20i_match)
        
        # Then add league matches sorted by date (most recent first)
        league_matches = []
        for row in league_results:
            match_data = {
                "match_id": row.id,
                "date": row.date.isoformat() if row.date else None,
                "venue": row.venue,
                "team1": teams_mapping.get(row.team1, row.team1),
                "team2": teams_mapping.get(row.team2, row.team2),
                "team1_full": row.team1,
                "team2_full": row.team2,
                "team1_score": None,  # Skip scores for performance
                "team2_score": None,  # Skip scores for performance
                "winner": teams_mapping.get(row.winner, row.winner) if row.winner else None,
                "competition": row.competition,
                "competition_abbr": leagues_mapping.get(row.competition, row.competition),
                "match_type": row.match_type,
                "is_international": False
            }
            league_matches.append(match_data)
        
        # Sort league matches by date (most recent first) and add to recent_matches
        league_matches.sort(key=lambda x: x["date"] or "1900-01-01", reverse=True)
        recent_matches.extend(league_matches)
        
        # Format match counts with T20I prioritized
        competition_stats = {}
        
        # Process international matches first
        for row in count_results:
            if row.match_type == 'international':
                competition_key = "T20 Internationals"
                competition_stats[competition_key] = {
                    "competition": row.competition,
                    "competition_display": "T20I",
                    "match_type": row.match_type,
                    "match_count": row.match_count,
                    "earliest_date": row.earliest_date.isoformat() if row.earliest_date else None,
                    "latest_date": row.latest_date.isoformat() if row.latest_date else None,
                    "date_range": f"{row.earliest_date} to {row.latest_date}" if row.earliest_date and row.latest_date else None,
                    "priority": 1  # Highest priority for sorting
                }
        
        # Then process league matches
        for row in count_results:
            if row.match_type == 'league':
                competition_key = row.competition
                competition_stats[competition_key] = {
                    "competition": row.competition,
                    "competition_display": leagues_mapping.get(row.competition, row.competition),
                    "match_type": row.match_type,
                    "match_count": row.match_count,
                    "earliest_date": row.earliest_date.isoformat() if row.earliest_date else None,
                    "latest_date": row.latest_date.isoformat() if row.latest_date else None,
                    "date_range": f"{row.earliest_date} to {row.latest_date}" if row.earliest_date and row.latest_date else None,
                    "priority": 2  # Lower priority than T20I
                }
        
        return {
            "recent_matches": recent_matches,
            "competition_stats": competition_stats,
            "total_competitions": len(competition_stats),
            "total_recent_matches": len(recent_matches)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recent matches by league: {str(e)}")
