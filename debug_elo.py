#!/usr/bin/env python3
"""
ELO Rating Tracker - Debug version that tracks rating changes for specific teams
"""

import logging
from typing import Dict, Tuple, Optional, List
from datetime import datetime
from database import get_session
from models import Match, teams_mapping, INTERNATIONAL_TEAMS_RANKED
from sqlalchemy import text
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def normalize_team_name(team_name: str) -> str:
    """Normalize team name using the teams_mapping from models.py"""
    return teams_mapping.get(team_name, team_name)

def teams_are_same(team1: str, team2: str) -> bool:
    """Check if two team names refer to the same team after normalization"""
    return normalize_team_name(team1) == normalize_team_name(team2)

def get_starting_elo(team_name: str, is_international: bool = True) -> int:
    """Get appropriate starting ELO rating based on team's ranking tier"""
    if not is_international:
        return 1500
    
    normalized_name = normalize_team_name(team_name)
    
    if normalized_name in INTERNATIONAL_TEAMS_RANKED:
        rank = INTERNATIONAL_TEAMS_RANKED.index(normalized_name) + 1
        if rank <= 10:
            return 1500
        elif rank <= 20:
            return 1400
    
    return 1300

class ELOTracker:
    """ELO Calculator with detailed tracking for debugging"""
    
    def __init__(self, k_factor: int = 32, initial_rating: int = 1500, track_teams: List[str] = None):
        self.k_factor = k_factor
        self.initial_rating = initial_rating
        self.team_ratings: Dict[str, int] = {}
        self.track_teams = track_teams or []  # Teams to track in detail
        self.match_history = {}  # Track match history for specific teams
        
    def get_team_rating(self, team_name: str, match_type: str = 'league') -> int:
        """Get current ELO rating for a team, initializing if new"""
        normalized_name = normalize_team_name(team_name)
        
        if normalized_name not in self.team_ratings:
            is_international = (match_type == 'international')
            starting_elo = get_starting_elo(team_name, is_international)
            self.team_ratings[normalized_name] = starting_elo
            
            if normalized_name in self.track_teams:
                tier_info = ""
                if is_international:
                    if normalized_name in INTERNATIONAL_TEAMS_RANKED:
                        rank = INTERNATIONAL_TEAMS_RANKED.index(normalized_name) + 1
                        tier_info = f" (Rank #{rank})"
                    else:
                        tier_info = " (Unranked international)"
                else:
                    tier_info = " (League team)"
                logger.info(f"🔍 TRACKED: Initialized {normalized_name} with rating {starting_elo}{tier_info}")
                
        return self.team_ratings[normalized_name]
    
    def calculate_expected_score(self, team1_elo: int, team2_elo: int) -> float:
        """Calculate expected score for team1 against team2"""
        return 1 / (1 + 10**((team2_elo - team1_elo) / 400))
    
    def get_actual_score(self, team1: str, team2: str, winner: Optional[str]) -> Tuple[float, float]:
        """Get actual match scores for ELO calculation"""
        if winner is None:
            return 0.5, 0.5
        elif teams_are_same(winner, team1):
            return 1.0, 0.0
        elif teams_are_same(winner, team2):
            return 0.0, 1.0
        else:
            logger.warning(f"Winner '{winner}' not found in teams '{team1}' vs '{team2}'. Treating as tie.")
            return 0.5, 0.5
    
    def update_ratings(self, team1: str, team2: str, winner: Optional[str], match_info: dict = None) -> Tuple[int, int, int, int]:
        """Update team ratings after a match with detailed tracking"""
        norm_team1 = normalize_team_name(team1)
        norm_team2 = normalize_team_name(team2)
        
        # Determine match type from match_info
        match_type = match_info.get('match_type', 'league') if match_info else 'league'
        
        # Store old ratings
        team1_old = self.get_team_rating(team1, match_type)
        team2_old = self.get_team_rating(team2, match_type)
        
        # Calculate expected scores
        expected1 = self.calculate_expected_score(team1_old, team2_old)
        expected2 = 1 - expected1
        
        # Get actual scores
        actual1, actual2 = self.get_actual_score(team1, team2, winner)
        
        # Calculate rating changes
        change1 = round(self.k_factor * (actual1 - expected1))
        change2 = round(self.k_factor * (actual2 - expected2))
        
        # Update ratings
        self.team_ratings[norm_team1] = team1_old + change1
        self.team_ratings[norm_team2] = team2_old + change2
        
        # Track detailed information for specified teams
        if norm_team1 in self.track_teams or norm_team2 in self.track_teams:
            match_date = match_info.get('date', 'Unknown') if match_info else 'Unknown'
            match_id = match_info.get('id', 'Unknown') if match_info else 'Unknown'
            
            logger.info(f"🔍 TRACKED MATCH: {match_date} ({match_id})")
            logger.info(f"   {norm_team1} ({team1_old}) vs {norm_team2} ({team2_old})")
            logger.info(f"   Winner: {normalize_team_name(winner) if winner else 'Tie/NR'}")
            logger.info(f"   Expected: {norm_team1}={expected1:.3f}, {norm_team2}={expected2:.3f}")
            logger.info(f"   Actual: {norm_team1}={actual1:.1f}, {norm_team2}={actual2:.1f}")
            logger.info(f"   Changes: {norm_team1}={change1:+d}, {norm_team2}={change2:+d}")
            logger.info(f"   New ratings: {norm_team1}={self.team_ratings[norm_team1]}, {norm_team2}={self.team_ratings[norm_team2]}")
            
            # Store match history for tracked teams
            for tracked_team in [norm_team1, norm_team2]:
                if tracked_team in self.track_teams:
                    if tracked_team not in self.match_history:
                        self.match_history[tracked_team] = []
                    
                    opponent = norm_team2 if tracked_team == norm_team1 else norm_team1
                    old_rating = team1_old if tracked_team == norm_team1 else team2_old
                    new_rating = self.team_ratings[tracked_team]
                    change = change1 if tracked_team == norm_team1 else change2
                    result = actual1 if tracked_team == norm_team1 else actual2
                    
                    self.match_history[tracked_team].append({
                        'date': match_date,
                        'match_id': match_id,
                        'opponent': opponent,
                        'old_rating': old_rating,
                        'new_rating': new_rating,
                        'change': change,
                        'result': result,
                        'winner': normalize_team_name(winner) if winner else 'Tie/NR'
                    })
        
        return team1_old, team2_old, self.team_ratings[norm_team1], self.team_ratings[norm_team2]

def get_all_matches_chronological(session: Session):
    """Get all matches ordered by date and match ID"""
    return session.query(Match).order_by(Match.date, Match.id).all()

def debug_elo_calculation(teams_to_track: List[str] = None, max_matches: int = None):
    """
    Debug ELO calculation by tracking specific teams
    
    Args:
        teams_to_track: List of team names to track in detail
        max_matches: Maximum number of matches to process (for testing)
    """
    if teams_to_track is None:
        teams_to_track = ['Uganda', 'India', 'Australia', 'New Zealand']
    
    session = next(get_session())
    tracker = ELOTracker(track_teams=teams_to_track)
    
    try:
        logger.info(f"Starting ELO debugging for teams: {teams_to_track}")
        
        # Get all matches in chronological order
        matches = get_all_matches_chronological(session)
        total_matches = len(matches)
        
        if max_matches:
            matches = matches[:max_matches]
            logger.info(f"Processing first {len(matches)} matches (limited for testing)")
        else:
            logger.info(f"Processing all {total_matches} matches")
        
        processed_count = 0
        
        for match in matches:
            match_info = {
                'id': match.id,
                'date': match.date,
                'venue': match.venue,
                'competition': match.competition,
                'match_type': match.match_type
            }
            
            # Update ratings and track changes
            tracker.update_ratings(match.team1, match.team2, match.winner, match_info)
            processed_count += 1
            
            # Log progress periodically
            if processed_count % 1000 == 0:
                logger.info(f"Processed {processed_count}/{len(matches)} matches")
        
        logger.info(f"Processing complete! Processed {processed_count} matches")
        
        # Display final ratings for tracked teams
        logger.info("\n=== FINAL RATINGS FOR TRACKED TEAMS ===")
        for team in teams_to_track:
            if team in tracker.team_ratings:
                rating = tracker.team_ratings[team]
                matches_played = len(tracker.match_history.get(team, []))
                logger.info(f"{team}: {rating} (played {matches_played} matches)")
            else:
                logger.info(f"{team}: Not found in database")
        
        # Show detailed history for each tracked team
        for team in teams_to_track:
            if team in tracker.match_history:
                show_team_history(team, tracker.match_history[team])
        
        # Show top 10 teams overall
        logger.info("\n=== TOP 10 TEAMS OVERALL ===")
        sorted_teams = sorted(tracker.team_ratings.items(), key=lambda x: x[1], reverse=True)
        for i, (team, rating) in enumerate(sorted_teams[:10], 1):
            logger.info(f"{i:2d}. {team:<30} {rating}")
        
    except Exception as e:
        logger.error(f"Error during debugging: {e}")
        raise
    finally:
        session.close()

def show_team_history(team_name: str, history: List[dict], max_matches: int = 10):
    """Show detailed match history for a team"""
    logger.info(f"\n=== MATCH HISTORY FOR {team_name} ===")
    logger.info(f"{'Date':<12} {'Opponent':<20} {'Result':<6} {'Old':<5} {'Change':<7} {'New':<5} {'Match ID'}")
    logger.info("-" * 80)
    
    # Show first few and last few matches
    display_matches = history[:max_matches//2] + history[-max_matches//2:] if len(history) > max_matches else history
    
    for i, match in enumerate(display_matches):
        if i == max_matches//2 and len(history) > max_matches:
            logger.info("... (middle matches omitted) ...")
            continue
            
        date_str = match['date'].strftime('%Y-%m-%d') if hasattr(match['date'], 'strftime') else str(match['date'])
        result_char = 'W' if match['result'] == 1.0 else 'L' if match['result'] == 0.0 else 'T'
        change_str = f"{match['change']:+d}"
        
        logger.info(f"{date_str:<12} {match['opponent']:<20} {result_char:<6} {match['old_rating']:<5} {change_str:<7} {match['new_rating']:<5} {match['match_id']}")

def find_uganda_matches():
    """Find all matches involving Uganda to understand their rating"""
    session = next(get_session())
    
    try:
        # Find all Uganda matches
        uganda_matches = session.query(Match).filter(
            (Match.team1 == 'Uganda') | (Match.team2 == 'Uganda')
        ).order_by(Match.date).all()
        
        logger.info(f"Found {len(uganda_matches)} matches involving Uganda")
        
        for match in uganda_matches[:20]:  # Show first 20
            opponent = match.team2 if match.team1 == 'Uganda' else match.team1
            winner_info = f"Winner: {match.winner}" if match.winner else "No result"
            logger.info(f"{match.date} - Uganda vs {opponent} ({match.competition}) - {winner_info}")
            
    except Exception as e:
        logger.error(f"Error finding Uganda matches: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    import sys
    
    if '--find-uganda' in sys.argv:
        find_uganda_matches()
    elif '--track-top' in sys.argv:
        # Track top 4 teams
        debug_elo_calculation(['Uganda', 'India', 'Australia', 'New Zealand'], max_matches=1000)
    else:
        # Full debug of Uganda specifically
        debug_elo_calculation(['Uganda'], max_matches=500)
