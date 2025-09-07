#!/usr/bin/env python3
"""
ELO Rating Calculation Engine for Cricket Teams

This module calculates ELO ratings for all teams based on historical match results.
Processes matches chronologically and updates the database with pre-match ELO ratings.
"""

import logging
from typing import Dict, Tuple, Optional
from datetime import datetime
from database import get_session
from models import Match, teams_mapping, INTERNATIONAL_TEAMS_RANKED
from sqlalchemy import text
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def normalize_team_name(team_name: str) -> str:
    """
    Normalize team name using the teams_mapping from models.py
    This handles variations like 'Royal Challengers Bangalore' -> 'RCB'
    """
    # Return the mapped abbreviation if it exists, otherwise return original name
    return teams_mapping.get(team_name, team_name)

def teams_are_same(team1: str, team2: str) -> bool:
    """
    Check if two team names refer to the same team after normalization
    """
    return normalize_team_name(team1) == normalize_team_name(team2)

def get_starting_elo(team_name: str, is_international: bool = True) -> int:
    """
    Get appropriate starting ELO rating based on team's ranking tier
    
    Args:
        team_name: Name of the team
        is_international: Whether this is an international team context
        
    Returns:
        Starting ELO rating based on tier
    """
    if not is_international:
        # League teams start at 1500
        return 1500
    
    # Normalize team name for consistent lookup
    normalized_name = normalize_team_name(team_name)
    
    # Check if team is in the ranked list
    if normalized_name in INTERNATIONAL_TEAMS_RANKED:
        rank = INTERNATIONAL_TEAMS_RANKED.index(normalized_name) + 1
        
        if rank <= 10:
            # Top 10 teams: 1500 ELO
            return 1500
        elif rank <= 20:
            # Teams 11-20: 1400 ELO  
            return 1400
    
    # Other international teams (unranked): 1300 ELO
    return 1300

class ELOCalculator:
    """Calculate and manage ELO ratings for cricket teams"""
    
    def __init__(self, k_factor: int = 32, initial_rating: int = 1500):
        """
        Initialize ELO calculator
        
        Args:
            k_factor: How much ratings change per match (default: 32)
            initial_rating: Default starting rating (only used for league teams now)
        """
        self.k_factor = k_factor
        self.initial_rating = initial_rating
        self.team_ratings: Dict[str, int] = {}
        
    def get_team_rating(self, team_name: str, match_type: str = 'league') -> int:
        """Get current ELO rating for a team, initializing if new"""
        # Normalize team name to handle variations
        normalized_name = normalize_team_name(team_name)
        
        if normalized_name not in self.team_ratings:
            # Determine if this is an international context
            is_international = (match_type == 'international')
            starting_elo = get_starting_elo(team_name, is_international)
            
            self.team_ratings[normalized_name] = starting_elo
            tier_info = ""
            if is_international:
                if normalized_name in INTERNATIONAL_TEAMS_RANKED:
                    rank = INTERNATIONAL_TEAMS_RANKED.index(normalized_name) + 1
                    tier_info = f" (Rank #{rank})"
                else:
                    tier_info = " (Unranked international)"
            else:
                tier_info = " (League team)"
            
            logger.info(f"Initialized new team '{normalized_name}' (from '{team_name}') with rating {starting_elo}{tier_info}")
            
        return self.team_ratings[normalized_name]
    
    def calculate_expected_score(self, team1_elo: int, team2_elo: int) -> float:
        """
        Calculate expected score for team1 against team2
        
        Args:
            team1_elo: Team1's current ELO rating
            team2_elo: Team2's current ELO rating
            
        Returns:
            Expected score for team1 (0.0 to 1.0)
        """
        return 1 / (1 + 10**((team2_elo - team1_elo) / 400))
    
    def get_actual_score(self, team1: str, team2: str, winner: Optional[str]) -> Tuple[float, float]:
        """
        Get actual match scores for ELO calculation
        
        Args:
            team1: Name of first team
            team2: Name of second team  
            winner: Name of winning team (None for tie/no result)
            
        Returns:
            Tuple of (team1_score, team2_score)
        """
        if winner is None:
            # Tie or no result - both teams get 0.5 points
            return 0.5, 0.5
        elif teams_are_same(winner, team1):
            return 1.0, 0.0
        elif teams_are_same(winner, team2):
            return 0.0, 1.0
        else:
            # Winner not one of the two teams (shouldn't happen, but handle gracefully)
            logger.warning(f"Winner '{winner}' not found in teams '{team1}' vs '{team2}'. Treating as tie.")
            logger.warning(f"  Normalized: Winner='{normalize_team_name(winner)}', Team1='{normalize_team_name(team1)}', Team2='{normalize_team_name(team2)}'")
            return 0.5, 0.5
    
    def calculate_rating_changes(self, team1: str, team2: str, winner: Optional[str], match_type: str = 'league') -> Tuple[int, int]:
        """
        Calculate ELO rating changes for both teams after a match
        
        Args:
            team1: Name of first team
            team2: Name of second team
            winner: Name of winning team (None for tie/no result)
            match_type: Type of match ('international' or 'league')
            
        Returns:
            Tuple of (team1_change, team2_change)
        """
        # Get current ratings
        team1_elo = self.get_team_rating(team1, match_type)
        team2_elo = self.get_team_rating(team2, match_type)
        
        # Calculate expected scores
        expected1 = self.calculate_expected_score(team1_elo, team2_elo)
        expected2 = 1 - expected1
        
        # Get actual scores
        actual1, actual2 = self.get_actual_score(team1, team2, winner)
        
        # Calculate rating changes
        change1 = round(self.k_factor * (actual1 - expected1))
        change2 = round(self.k_factor * (actual2 - expected2))
        
        return change1, change2
    
    def update_ratings(self, team1: str, team2: str, winner: Optional[str], match_type: str = 'league') -> Tuple[int, int, int, int]:
        """
        Update team ratings after a match
        
        Args:
            team1: Name of first team
            team2: Name of second team
            winner: Name of winning team (None for tie/no result)
            match_type: Type of match ('international' or 'league')
            
        Returns:
            Tuple of (team1_old_elo, team2_old_elo, team1_new_elo, team2_new_elo)
        """
        # Normalize team names
        norm_team1 = normalize_team_name(team1)
        norm_team2 = normalize_team_name(team2)
        
        # Store old ratings
        team1_old = self.get_team_rating(team1, match_type)
        team2_old = self.get_team_rating(team2, match_type)
        
        # Calculate changes
        change1, change2 = self.calculate_rating_changes(team1, team2, winner, match_type)
        
        # Update ratings using normalized names
        self.team_ratings[norm_team1] = team1_old + change1
        self.team_ratings[norm_team2] = team2_old + change2
        
        return team1_old, team2_old, self.team_ratings[norm_team1], self.team_ratings[norm_team2]


def get_all_matches_chronological(session: Session):
    """Get all matches ordered by date and match ID"""
    return session.query(Match).order_by(Match.date, Match.id).all()


def calculate_historical_elos(dry_run: bool = False, batch_size: int = 1000):
    """
    Calculate ELO ratings for all historical matches
    
    Args:
        dry_run: If True, don't update database, just print progress
        batch_size: Number of matches to process before committing to database
    """
    session = next(get_session())
    calculator = ELOCalculator()
    
    try:
        logger.info("Starting ELO calculation for all historical matches...")
        
        # Get all matches in chronological order
        logger.info("Fetching all matches from database...")
        matches = get_all_matches_chronological(session)
        total_matches = len(matches)
        logger.info(f"Found {total_matches} matches to process")
        
        if dry_run:
            logger.info("DRY RUN MODE - No database updates will be made")
        
        # Process matches in batches
        processed_count = 0
        updates_to_commit = []
        
        for i, match in enumerate(matches):
            # Calculate ELO ratings before this match
            team1_old, team2_old, team1_new, team2_new = calculator.update_ratings(
                match.team1, match.team2, match.winner, match.match_type
            )
            
            # Prepare database update
            if not dry_run:
                updates_to_commit.append({
                    'match_id': match.id,
                    'team1_elo': team1_old,
                    'team2_elo': team2_old
                })
            
            processed_count += 1
            
            # Log progress every 1000 matches
            if processed_count % 1000 == 0:
                logger.info(f"Processed {processed_count}/{total_matches} matches ({processed_count/total_matches*100:.1f}%)")
                logger.info(f"Sample: {match.team1} ({team1_old}→{team1_new}) vs {match.team2} ({team2_old}→{team2_new})")
            
            # Commit batch to database
            if not dry_run and len(updates_to_commit) >= batch_size:
                commit_elo_updates(session, updates_to_commit)
                updates_to_commit = []
                logger.info(f"Committed batch of {batch_size} updates to database")
        
        # Commit remaining updates
        if not dry_run and updates_to_commit:
            commit_elo_updates(session, updates_to_commit)
            logger.info(f"Committed final batch of {len(updates_to_commit)} updates")
        
        logger.info(f"ELO calculation complete! Processed {processed_count} matches")
        
        # Display final ratings for top teams
        display_final_ratings(calculator)
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error during ELO calculation: {e}")
        raise
    finally:
        session.close()


def commit_elo_updates(session: Session, updates: list):
    """Commit ELO updates to database using bulk update"""
    try:
        # Use bulk update for performance
        for update in updates:
            session.execute(
                text("UPDATE matches SET team1_elo = :team1_elo, team2_elo = :team2_elo WHERE id = :match_id"),
                update
            )
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error committing ELO updates: {e}")
        raise


def display_final_ratings(calculator: ELOCalculator, top_n: int = 20):
    """Display final ELO ratings for top teams"""
    logger.info(f"\n=== TOP {top_n} TEAMS BY ELO RATING ===")
    
    # Sort teams by rating
    sorted_teams = sorted(calculator.team_ratings.items(), key=lambda x: x[1], reverse=True)
    
    logger.info(f"{'Rank':<4} {'Team':<30} {'ELO Rating':<10}")
    logger.info("-" * 50)
    
    for i, (team, rating) in enumerate(sorted_teams[:top_n], 1):
        logger.info(f"{i:<4} {team:<30} {rating:<10}")


def verify_elo_calculation(sample_size: int = 10):
    """Verify ELO calculations by spot-checking some matches"""
    session = next(get_session())
    
    try:
        # Get a sample of matches with ELO ratings
        matches = session.execute(
            text("""
                SELECT id, date, team1, team2, winner, team1_elo, team2_elo 
                FROM matches 
                WHERE team1_elo IS NOT NULL AND team2_elo IS NOT NULL
                ORDER BY date DESC
                LIMIT :limit
            """),
            {'limit': sample_size}
        ).fetchall()
        
        logger.info(f"\n=== SAMPLE ELO CALCULATIONS ===")
        logger.info(f"{'Date':<12} {'Team1':<20} {'ELO1':<6} {'Team2':<20} {'ELO2':<6} {'Winner':<20}")
        logger.info("-" * 100)
        
        for match in matches:
            logger.info(f"{match.date.strftime('%Y-%m-%d'):<12} {match.team1:<20} {match.team1_elo:<6} {match.team2:<20} {match.team2_elo:<6} {match.winner or 'Tie':<20}")
            
    except Exception as e:
        logger.error(f"Error verifying ELO calculations: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    import sys
    
    # Check command line arguments
    dry_run = '--dry-run' in sys.argv
    verify = '--verify' in sys.argv
    
    if verify:
        verify_elo_calculation()
    else:
        calculate_historical_elos(dry_run=dry_run)
