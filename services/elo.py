from sqlalchemy.sql import text
from fastapi import HTTPException
from typing import List, Optional, Dict
from datetime import date
from models import teams_mapping

def get_delhi_team_name_variations(team_name: str) -> List[str]:
    """Special handler for Delhi teams to manage the DD->DC transition properly"""
    delhi_names = ['Delhi Capitals', 'Delhi Daredevils']
    
    # If requesting Delhi Capitals, return both names to get complete history
    if team_name == 'Delhi Capitals':
        return delhi_names
    # If requesting Delhi Daredevils, return both names to get complete history  
    elif team_name == 'Delhi Daredevils':
        return delhi_names
    # If requesting DC abbreviation, return both names
    elif team_name == 'DC':
        return delhi_names
    else:
        return [team_name]

def get_all_team_name_variations(team_name: str) -> List[str]:
    """Get all possible name variations for a given team based on teams_mapping"""
    
    # Special handling for Delhi teams
    if team_name in ['Delhi Capitals', 'Delhi Daredevils', 'DC']:
        return get_delhi_team_name_variations(team_name)
    
    # Regular handling for other teams
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

def get_teams_elo_rankings_service(
    league: Optional[str] = None,
    include_international: bool = True,
    top_teams: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db = None
) -> List[dict]:
    """
    Get current ELO rankings for teams based on their most recent ratings
    
    Args:
        league: Specific league to filter by (e.g., 'Indian Premier League')
        include_international: Whether to include international teams
        top_teams: Limit to top N international teams (only applies to international matches)
        start_date: Optional start date for filtering matches used to calculate latest ELO
        end_date: Optional end date for filtering matches used to calculate latest ELO
        db: Database session
    
    Returns:
        List of team ELO rankings with current ratings
    """
    try:
        # Build the base query to get the latest ELO rating for each team
        params = {
            "league": league,
            "include_international": include_international,
            "start_date": start_date,
            "end_date": end_date
        }
        
        # Determine competition filter
        competition_conditions = []
        
        if league:
            competition_conditions.append("(m.match_type = 'league' AND m.competition = :league)")
        
        if include_international:
            if top_teams:
                # Use the predefined ranked international teams list
                from models import INTERNATIONAL_TEAMS_RANKED
                top_team_list = INTERNATIONAL_TEAMS_RANKED[:top_teams]
                params["top_team_list"] = top_team_list
                competition_conditions.append(
                    "(m.match_type = 'international' AND m.team1 = ANY(:top_team_list) AND m.team2 = ANY(:top_team_list))"
                )
            else:
                competition_conditions.append("(m.match_type = 'international')")
        
        # Build competition filter
        if competition_conditions:
            competition_filter = "AND (" + " OR ".join(competition_conditions) + ")"
        else:
            competition_filter = "AND false"  # No teams if no conditions
        
        # Query to get latest ELO for each team
        elo_rankings_query = text(f"""
            WITH latest_team_elos AS (
                -- Get the most recent ELO rating for each team from either team1 or team2 position
                SELECT DISTINCT ON (team_name)
                    team_name,
                    latest_elo,
                    latest_date,
                    total_matches,
                    wins,
                    losses,
                    win_percentage,
                    match_type,
                    latest_competition
                FROM (
                    -- Team1 ELOs
                    SELECT 
                        m.team1 as team_name,
                        m.team1_elo as latest_elo,
                        m.date as latest_date,
                        COUNT(*) OVER (PARTITION BY m.team1) as total_matches,
                        SUM(CASE WHEN m.winner = m.team1 THEN 1 ELSE 0 END) OVER (PARTITION BY m.team1) as wins,
                        SUM(CASE WHEN m.winner IS NOT NULL AND m.winner != m.team1 THEN 1 ELSE 0 END) OVER (PARTITION BY m.team1) as losses,
                        ROUND(
                            (SUM(CASE WHEN m.winner = m.team1 THEN 1 ELSE 0 END) OVER (PARTITION BY m.team1) * 100.0) / 
                            NULLIF(COUNT(CASE WHEN m.winner IS NOT NULL THEN 1 END) OVER (PARTITION BY m.team1), 0), 
                            2
                        ) as win_percentage,
                        m.match_type,
                        m.competition as latest_competition,
                        ROW_NUMBER() OVER (PARTITION BY m.team1 ORDER BY m.date DESC, m.id DESC) as rn
                    FROM matches m
                    WHERE m.team1_elo IS NOT NULL
                    AND (:start_date IS NULL OR m.date >= :start_date)
                    AND (:end_date IS NULL OR m.date <= :end_date)
                    {competition_filter}
                    
                    UNION ALL
                    
                    -- Team2 ELOs  
                    SELECT 
                        m.team2 as team_name,
                        m.team2_elo as latest_elo,
                        m.date as latest_date,
                        COUNT(*) OVER (PARTITION BY m.team2) as total_matches,
                        SUM(CASE WHEN m.winner = m.team2 THEN 1 ELSE 0 END) OVER (PARTITION BY m.team2) as wins,
                        SUM(CASE WHEN m.winner IS NOT NULL AND m.winner != m.team2 THEN 1 ELSE 0 END) OVER (PARTITION BY m.team2) as losses,
                        ROUND(
                            (SUM(CASE WHEN m.winner = m.team2 THEN 1 ELSE 0 END) OVER (PARTITION BY m.team2) * 100.0) / 
                            NULLIF(COUNT(CASE WHEN m.winner IS NOT NULL THEN 1 END) OVER (PARTITION BY m.team2), 0), 
                            2
                        ) as win_percentage,
                        m.match_type,
                        m.competition as latest_competition,
                        ROW_NUMBER() OVER (PARTITION BY m.team2 ORDER BY m.date DESC, m.id DESC) as rn
                    FROM matches m
                    WHERE m.team2_elo IS NOT NULL
                    AND (:start_date IS NULL OR m.date >= :start_date)
                    AND (:end_date IS NULL OR m.date <= :end_date)
                    {competition_filter}
                ) combined_elos
                WHERE rn = 1
                ORDER BY team_name, latest_date DESC
            )
            SELECT 
                team_name,
                latest_elo as current_elo,
                latest_date,
                total_matches,
                wins,
                losses,
                COALESCE(win_percentage, 0) as win_percentage,
                match_type,
                latest_competition
            FROM latest_team_elos
            WHERE latest_elo IS NOT NULL
            ORDER BY latest_elo DESC, team_name ASC
        """)
        
        results = db.execute(elo_rankings_query, params).fetchall()
        
        if not results:
            return []
        
        # Format results
        rankings = []
        for i, row in enumerate(results, 1):
            team_data = {
                "rank": i,
                "team_name": row.team_name,
                "team_abbreviation": teams_mapping.get(row.team_name, row.team_name),
                "current_elo": row.current_elo,
                "last_match_date": row.latest_date.isoformat() if row.latest_date else None,
                "total_matches": row.total_matches or 0,
                "wins": row.wins or 0,
                "losses": row.losses or 0,
                "win_percentage": float(row.win_percentage or 0),
                "match_type": row.match_type,
                "latest_competition": row.latest_competition
            }
            rankings.append(team_data)
        
        return rankings
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching ELO rankings: {str(e)}")

def get_teams_elo_history_service(
    teams: List[str],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db = None
) -> Dict[str, List[dict]]:
    """
    Get ELO history for multiple teams over a specified time period for racer chart visualization
    
    Args:
        teams: List of team names (full names or abbreviations)
        start_date: Start date for the ELO history
        end_date: End date for the ELO history
        db: Database session
    
    Returns:
        Dictionary with team names as keys and ELO history arrays as values
    """
    try:
        if not teams:
            return {}
        
        # Get all team name variations for the requested teams
        all_team_variations = []
        team_mapping = {}  # Maps any variation to the standardized name
        
        for team in teams:
            variations = get_all_team_name_variations(team)
            all_team_variations.extend(variations)
            # Map all variations to the original requested team name (preserve full names)
            for var in variations:
                team_mapping[var] = team
        
        params = {
            "team_variations": all_team_variations,
            "start_date": start_date,
            "end_date": end_date
        }
        
        # Query to get ELO evolution for all requested teams
        elo_history_query = text("""
            WITH team_elo_evolution AS (
                -- Get ELO ratings from team1 position
                SELECT 
                    m.team1 as team_name,
                    m.team1_elo as elo_rating,
                    m.date,
                    m.id as match_id,
                    m.team2 as opponent,
                    m.winner,
                    1 as team_position
                FROM matches m
                WHERE m.team1 = ANY(:team_variations)
                AND m.team1_elo IS NOT NULL
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                
                UNION ALL
                
                -- Get ELO ratings from team2 position
                SELECT 
                    m.team2 as team_name,
                    m.team2_elo as elo_rating,
                    m.date,
                    m.id as match_id,
                    m.team1 as opponent,
                    m.winner,
                    2 as team_position
                FROM matches m
                WHERE m.team2 = ANY(:team_variations)
                AND m.team2_elo IS NOT NULL
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
            )
            SELECT 
                team_name,
                elo_rating,
                date,
                match_id,
                opponent,
                winner,
                team_position
            FROM team_elo_evolution
            ORDER BY team_name, date ASC, match_id ASC
        """)
        
        results = db.execute(elo_history_query, params).fetchall()
        
        # Group results by team
        team_histories = {}
        
        for row in results:
            # Use the standardized team name
            std_team_name = team_mapping.get(row.team_name, row.team_name)
            
            if std_team_name not in team_histories:
                team_histories[std_team_name] = []
            
            # Determine match result for this team
            match_result = "NR"  # No result
            if row.winner:
                # Check if this team won
                winner_variations = get_all_team_name_variations(row.winner)
                match_result = "W" if row.team_name in winner_variations else "L"
            
            elo_point = {
                "date": row.date.isoformat(),
                "elo": row.elo_rating,
                "match_id": row.match_id,
                "opponent": teams_mapping.get(row.opponent, row.opponent),
                "result": match_result
            }
            
            team_histories[std_team_name].append(elo_point)
        
        return team_histories
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching ELO history: {str(e)}")
