from sqlalchemy.sql import text
from fastapi import HTTPException
from typing import List, Optional, Dict
from datetime import date
from models import teams_mapping

def get_all_team_name_variations(team_name: str) -> List[str]:
    """Get all possible name variations for a given team based on teams_mapping"""
    # Create a reverse mapping from abbreviation to all team names
    reverse_mapping = {}
    for full_name, abbrev in teams_mapping.items():
        if abbrev not in reverse_mapping:
            reverse_mapping[abbrev] = []
        reverse_mapping[abbrev].append(full_name)
    
    # If team_name is an abbreviation, return all full names for it
    if team_name in reverse_mapping:
        return reverse_mapping[team_name]
    
    # If it's a full name, find its abbreviation and return all related names
    abbrev = teams_mapping.get(team_name)
    if abbrev and abbrev in reverse_mapping:
        return reverse_mapping[abbrev]
    
    # If not found in mapping, return just the original name
    return [team_name]

def get_team_elo_stats_service(
    team_name: str,
    start_date: Optional[date],
    end_date: Optional[date],
    db
) -> Dict:
    """
    Get ELO statistics for a team within the specified date range
    
    Returns:
        - Starting ELO (as of start date)
        - Ending ELO (as of end date) 
        - Peak ELO in the time period
        - Lowest ELO in the time period
        - ELO evolution over time
    """
    try:
        team_variations = get_all_team_name_variations(team_name)
        
        # Get ELO data for the team within date range
        elo_query = text("""
            WITH team_elo_data AS (
                SELECT 
                    m.date,
                    m.id as match_id,
                    m.team1,
                    m.team2,
                    m.team1_elo,
                    m.team2_elo,
                    m.winner,
                    CASE 
                        WHEN m.team1 = ANY(:team_variations) THEN m.team1_elo
                        WHEN m.team2 = ANY(:team_variations) THEN m.team2_elo
                        ELSE NULL
                    END as team_elo,
                    CASE 
                        WHEN m.team1 = ANY(:team_variations) THEN m.team2
                        WHEN m.team2 = ANY(:team_variations) THEN m.team1
                        ELSE NULL
                    END as opponent,
                    CASE 
                        WHEN m.team1 = ANY(:team_variations) THEN m.team2_elo
                        WHEN m.team2 = ANY(:team_variations) THEN m.team1_elo
                        ELSE NULL
                    END as opponent_elo
                FROM matches m
                WHERE (m.team1 = ANY(:team_variations) OR m.team2 = ANY(:team_variations))
                AND m.team1_elo IS NOT NULL 
                AND m.team2_elo IS NOT NULL
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                ORDER BY m.date ASC, m.id ASC
            )
            SELECT 
                date,
                match_id,
                team_elo,
                opponent,
                opponent_elo,
                winner,
                -- Calculate if team won
                CASE 
                    WHEN winner = ANY(:team_variations) THEN 'W'
                    WHEN winner IS NULL THEN 'NR'
                    ELSE 'L'
                END as result
            FROM team_elo_data
            WHERE team_elo IS NOT NULL
            ORDER BY date ASC, match_id ASC
        """)
        
        results = db.execute(elo_query, {
            "team_variations": team_variations,
            "start_date": start_date,
            "end_date": end_date
        }).fetchall()
        
        if not results:
            return {
                "team": team_name,
                "starting_elo": None,
                "ending_elo": None,
                "peak_elo": None,
                "lowest_elo": None,
                "total_matches": 0,
                "elo_history": []
            }
        
        # Extract ELO values
        elo_values = [row.team_elo for row in results]
        
        # Calculate statistics
        starting_elo = elo_values[0]
        ending_elo = elo_values[-1]
        peak_elo = max(elo_values)
        lowest_elo = min(elo_values)
        
        # Build ELO history for visualization
        elo_history = []
        for row in results:
            elo_history.append({
                "date": row.date.isoformat(),
                "match_id": row.match_id,
                "elo": row.team_elo,
                "opponent": teams_mapping.get(row.opponent, row.opponent),
                "opponent_elo": row.opponent_elo,
                "result": row.result,
                "winner": teams_mapping.get(row.winner, row.winner) if row.winner else None
            })
        
        return {
            "team": teams_mapping.get(team_name, team_name),
            "starting_elo": starting_elo,
            "ending_elo": ending_elo,
            "peak_elo": peak_elo,
            "lowest_elo": lowest_elo,
            "total_matches": len(results),
            "elo_change": ending_elo - starting_elo,
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "elo_history": elo_history
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching team ELO stats: {str(e)}")

def get_team_matches_with_elo_service(
    team_name: str,
    start_date: Optional[date],
    end_date: Optional[date],
    db
) -> List[dict]:
    """
    Get all matches played by a team with ELO information included
    """
    try:
        team_variations = get_all_team_name_variations(team_name)
        
        matches_query = text("""
            WITH match_scores AS (
                SELECT 
                    m.id, m.date, m.venue, m.city, m.event_name,
                    m.team1, m.team2, m.winner, m.toss_winner, m.toss_decision,
                    m.competition, m.match_type,
                    m.team1_elo, m.team2_elo,
                    (SELECT CONCAT(COALESCE(SUM(d1.runs_off_bat + d1.extras), 0), '/', 
                                   COALESCE(COUNT(CASE WHEN d1.wicket_type IS NOT NULL THEN 1 END), 0))
                     FROM deliveries d1 WHERE d1.match_id = m.id AND d1.innings = 1) as team1_score,
                    (SELECT CONCAT(COALESCE(SUM(d2.runs_off_bat + d2.extras), 0), '/', 
                                   COALESCE(COUNT(CASE WHEN d2.wicket_type IS NOT NULL THEN 1 END), 0))
                     FROM deliveries d2 WHERE d2.match_id = m.id AND d2.innings = 2) as team2_score
                FROM matches m
                WHERE (m.team1 = ANY(:team_variations) OR m.team2 = ANY(:team_variations))
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                ORDER BY m.date DESC
            )
            SELECT * FROM match_scores
        """)
        
        results = db.execute(matches_query, {
            "team_variations": team_variations,
            "start_date": start_date,
            "end_date": end_date
        }).fetchall()
        
        matches = []
        for row in results:
            team_was_team1 = row.team1 in team_variations
            opponent = row.team2 if team_was_team1 else row.team1
            team_score = row.team1_score if team_was_team1 else row.team2_score
            opponent_score = row.team2_score if team_was_team1 else row.team1_score
            
            # Get ELO ratings
            team_elo = row.team1_elo if team_was_team1 else row.team2_elo
            opponent_elo = row.team2_elo if team_was_team1 else row.team1_elo
            
            match_result = "NR"
            if row.winner:
                match_result = "W" if row.winner in team_variations else "L"
            
            match_data = {
                "match_id": row.id,
                "date": row.date.isoformat() if row.date else None,
                "venue": row.venue,
                "city": row.city,
                "event_name": row.event_name,
                "competition": row.competition,
                "match_type": row.match_type,
                "team": teams_mapping.get(team_name, team_name),
                "opponent": teams_mapping.get(opponent, opponent),
                "team_score": team_score,
                "opponent_score": opponent_score,
                "result": match_result,
                "toss_winner": teams_mapping.get(row.toss_winner, row.toss_winner) if row.toss_winner else None,
                "toss_decision": row.toss_decision,
                "batted_first": team_was_team1,
                "winner": teams_mapping.get(row.winner, row.winner) if row.winner else None,
                # ELO information
                "elo": {
                    "team_elo": team_elo,
                    "opponent_elo": opponent_elo,
                    "elo_difference": team_elo - opponent_elo if team_elo and opponent_elo else None
                }
            }
            matches.append(match_data)
        
        return matches
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching team matches with ELO: {str(e)}")
