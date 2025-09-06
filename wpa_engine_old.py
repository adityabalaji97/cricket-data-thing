"""
WPA Engine - Per-Delivery WPA Calculation Engine

This module implements the core engine for calculating Win Probability Added (WPA)
for every delivery in T20 matches, following the WPA_ENGINE_PRD.md specifications.

Key Features:
- Per-delivery WPA calculation using historical venue data
- Integration with existing WPA infrastructure (wpa_curve_trainer, wpa_fallback)
- Strict chronological constraints to avoid data leakage
- Venue fallback hierarchy (venue → cluster → league → global)
- Efficient match state extraction and win probability calculation
"""

from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, desc
from models import Match, Delivery
from wpa_fallback import WPAEngineWithFallback
from context_model import VenueResourceTableBuilder
from datetime import date, datetime
import logging
import json

logger = logging.getLogger(__name__)


class MatchState:
    """
    Represents the state of a match at a specific delivery.
    
    This class encapsulates all the information needed to calculate
    win probability for a given match situation.
    """
    
    def __init__(self, target: int, current_score: int, overs_completed: float, 
                 wickets_lost: int, balls_remaining: int, wickets_remaining: int):
        self.target = target
        self.current_score = current_score
        self.overs_completed = overs_completed
        self.wickets_lost = wickets_lost
        self.balls_remaining = balls_remaining
        self.wickets_remaining = wickets_remaining
        
        # Derived metrics
        self.runs_needed = max(0, target - current_score)
        self.required_run_rate = (self.runs_needed * 6) / balls_remaining if balls_remaining > 0 else float('inf')
        self.current_run_rate = (current_score * 6) / ((20 * 6) - balls_remaining) if balls_remaining < 120 else 0
    
    def __repr__(self):
        return f"MatchState(target={self.target}, score={self.current_score}, overs={self.overs_completed}, wickets={self.wickets_lost})"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert match state to dictionary for debugging/logging"""
        return {
            "target": self.target,
            "current_score": self.current_score,
            "overs_completed": self.overs_completed,
            "wickets_lost": self.wickets_lost,
            "balls_remaining": self.balls_remaining,
            "wickets_remaining": self.wickets_remaining,
            "runs_needed": self.runs_needed,
            "required_run_rate": round(self.required_run_rate, 2),
            "current_run_rate": round(self.current_run_rate, 2)
        }


class PerDeliveryWPAEngine:
    """
    Core engine for calculating Win Probability Added (WPA) per delivery.
    
    This engine processes individual deliveries and calculates the change in
    win probability caused by each ball, attributing the impact to both
    batter and bowler following standard WPA methodology.
    """
    
    def __init__(self):
        self.wpa_engine = WPAEngineWithFallback()
        self.resource_builder = VenueResourceTableBuilder()
        
        # WPA calculation parameters
        self.max_overs = 20
        self.max_wickets = 10
        
        # Minimum win probability change to avoid noise in decided matches
        self.min_meaningful_wpa = 0.001  # 0.1% win probability change
        
        # Cache for venue data to avoid repeated database queries
        self._venue_cache = {}
        self._match_cache = {}
    
    def get_match_info(self, session: Session, match_id: str) -> Optional[Dict[str, Any]]:
        """
        Get essential match information needed for WPA calculations.
        
        Args:
            session: Database session
            match_id: Match ID
            
        Returns:
            Dictionary with match info or None if not found
        """
        if match_id in self._match_cache:
            return self._match_cache[match_id]
        
        try:
            match = session.query(Match).filter(Match.id == match_id).first()
            
            if not match:
                logger.warning(f"Match {match_id} not found")
                return None
            
            # Get first innings total
            first_innings_query = text("""
                SELECT SUM(runs_off_bat + COALESCE(extras, 0)) as total_runs
                FROM deliveries 
                WHERE match_id = :match_id AND innings = 1
            """)
            
            first_innings_result = session.execute(first_innings_query, {"match_id": match_id}).fetchone()
            first_innings_total = first_innings_result.total_runs if first_innings_result else 0
            
            match_info = {
                "match_id": match_id,
                "date": match.date,
                "venue": match.venue,
                "competition": match.competition,
                "team1": match.team1,
                "team2": match.team2,
                "winner": match.winner,
                "first_innings_total": first_innings_total or 0
            }
            
            self._match_cache[match_id] = match_info
            return match_info
            
        except Exception as e:
            logger.error(f"Error getting match info for {match_id}: {e}")
            return None
    
    def get_match_state_at_delivery(self, session: Session, delivery: Delivery) -> Optional[MatchState]:
        """
        Calculate the match state at a specific delivery.
        
        Args:
            session: Database session
            delivery: The delivery to calculate state for
            
        Returns:
            MatchState object or None if cannot calculate
        """
        try:
            match_info = self.get_match_info(session, delivery.match_id)
            if not match_info:
                return None
            
            # Only calculate WPA for second innings (chase scenarios)
            if delivery.innings != 2:
                return None
            
            target = match_info["first_innings_total"] + 1  # Target to win
            
            # Get cumulative runs and wickets up to this delivery
            cumulative_query = text("""
                SELECT 
                    COALESCE(SUM(runs_off_bat + COALESCE(extras, 0)), 0) as runs_so_far,
                    COUNT(CASE WHEN wicket_type IS NOT NULL THEN 1 END) as wickets_so_far
                FROM deliveries
                WHERE match_id = :match_id 
                    AND innings = :innings
                    AND (over < :current_over OR (over = :current_over AND ball <= :current_ball))
            """)
            
            cumulative_result = session.execute(cumulative_query, {
                "match_id": delivery.match_id,
                "innings": delivery.innings,
                "current_over": delivery.over,
                "current_ball": delivery.ball
            }).fetchone()
            
            if not cumulative_result:
                return None
            
            current_score = cumulative_result.runs_so_far
            wickets_lost = cumulative_result.wickets_so_far
            
            # Calculate overs and balls
            balls_completed = (delivery.over * 6) + delivery.ball
            overs_completed = balls_completed / 6.0
            balls_remaining = (self.max_overs * 6) - balls_completed
            wickets_remaining = self.max_wickets - wickets_lost
            
            return MatchState(
                target=target,
                current_score=current_score,
                overs_completed=overs_completed,
                wickets_lost=wickets_lost,
                balls_remaining=max(0, balls_remaining),
                wickets_remaining=max(0, wickets_remaining)
            )
            
        except Exception as e:
            logger.error(f"Error calculating match state for delivery {delivery.id}: {e}")
            return None
    
    def get_match_state_after_delivery(self, session: Session, delivery: Delivery) -> Optional[MatchState]:
        """
        Calculate the match state after a specific delivery.
        
        Args:
            session: Database session
            delivery: The delivery to calculate post-state for
            
        Returns:
            MatchState after the delivery or None if cannot calculate
        """
        try:
            # Get the before state
            before_state = self.get_match_state_at_delivery(session, delivery)
            if not before_state:
                return None
            
            # Calculate runs and wickets from this delivery
            delivery_runs = (delivery.runs_off_bat or 0) + (delivery.extras or 0)
            delivery_wickets = 1 if delivery.wicket_type else 0
            
            # Calculate new state
            new_score = before_state.current_score + delivery_runs
            new_wickets_lost = before_state.wickets_lost + delivery_wickets
            new_balls_remaining = before_state.balls_remaining - 1
            new_wickets_remaining = before_state.wickets_remaining - delivery_wickets
            
            # Update overs completed
            balls_completed = ((delivery.over * 6) + delivery.ball) + 1
            new_overs_completed = balls_completed / 6.0
            
            return MatchState(
                target=before_state.target,
                current_score=new_score,
                overs_completed=new_overs_completed,
                wickets_lost=new_wickets_lost,
                balls_remaining=max(0, new_balls_remaining),
                wickets_remaining=max(0, new_wickets_remaining)
            )
            
        except Exception as e:
            logger.error(f"Error calculating post-delivery state for delivery {delivery.id}: {e}")
            return None
    
    def calculate_win_probability(self, session: Session, match_state: MatchState, 
                                venue: str, match_date: date, league: str) -> float:
        """
        Calculate win probability for a given match state using historical data.
        
        Args:
            session: Database session
            match_state: Current match state
            venue: Venue name
            match_date: Match date (for chronological constraint)
            league: League/competition
            
        Returns:
            Win probability (0.0 to 1.0)
        """
        try:
            # Check if match is already decided
            if match_state.runs_needed <= 0:
                return 1.0  # Already won
            
            if match_state.balls_remaining <= 0 or match_state.wickets_remaining <= 0:
                return 0.0  # Cannot win
            
            # Use cached venue data if available
            cache_key = f"{venue}_{match_date}_{league}"
            if cache_key not in self._venue_cache:
                # Get WPA lookup table with fallback
                wpa_data = self.wpa_engine.get_wpa_lookup_table_with_fallback(
                    session, venue, match_date, league
                )
                self._venue_cache[cache_key] = wpa_data
            else:
                wpa_data = self._venue_cache[cache_key]
            
            if not wpa_data or "wpa_table" not in wpa_data:
                logger.warning(f"No WPA data available for {venue}, using fallback")
                return self._calculate_fallback_win_probability(match_state)
            
            # Get historical outcomes from the WPA trainer
            outcomes_data = self.wpa_engine.trainer.get_second_innings_outcomes(
                session, venue, match_date, league
            )
            
            if not outcomes_data:
                logger.debug(f"No historical outcomes for {venue}, using fallback")
                return self._calculate_fallback_win_probability(match_state)
            
            # Calculate win probability using the trainer
            win_prob = self.wpa_engine.trainer.calculate_win_probability(
                target_score=match_state.target,
                current_score=match_state.current_score,
                over=int(match_state.overs_completed),
                wickets=match_state.wickets_lost,
                outcomes_data=outcomes_data
            )
            
            return max(0.0, min(1.0, win_prob))
            
        except Exception as e:
            logger.error(f"Error calculating win probability: {e}")
            return self._calculate_fallback_win_probability(match_state)
    
    def _calculate_fallback_win_probability(self, match_state: MatchState) -> float:
        """
        Calculate fallback win probability using simple heuristics.
        
        Args:
            match_state: Current match state
            
        Returns:
            Estimated win probability
        """
        if match_state.runs_needed <= 0:
            return 1.0
        
        if match_state.balls_remaining <= 0 or match_state.wickets_remaining <= 0:
            return 0.0
        
        # Simple probability based on required rate and resources
        required_rr = match_state.required_run_rate
        wickets_factor = match_state.wickets_remaining / self.max_wickets
        
        if required_rr <= 6:  # Easy chase
            base_prob = 0.8
        elif required_rr <= 9:  # Moderate chase
            base_prob = 0.6
        elif required_rr <= 12:  # Difficult chase
            base_prob = 0.3
        else:  # Very difficult
            base_prob = 0.1
        
        return max(0.0, min(1.0, base_prob * wickets_factor))
    
    def calculate_delivery_wpa(self, session: Session, delivery: Delivery) -> Optional[Tuple[float, float]]:
        """
        Calculate WPA for a specific delivery.
        
        Args:
            session: Database session
            delivery: Delivery to calculate WPA for
            
        Returns:
            Tuple of (wpa_batter, wpa_bowler) or None if cannot calculate
        """
        try:
            # Get match information
            match_info = self.get_match_info(session, delivery.match_id)
            if not match_info:
                return None
            
            # Only calculate WPA for second innings
            if delivery.innings != 2:
                return None
            
            # Get match states before and after delivery
            before_state = self.get_match_state_at_delivery(session, delivery)
            after_state = self.get_match_state_after_delivery(session, delivery)
            
            if not before_state or not after_state:
                return None
            
            # Calculate win probabilities
            before_wp = self.calculate_win_probability(
                session, before_state, match_info["venue"], 
                match_info["date"], match_info["competition"]
            )
            
            after_wp = self.calculate_win_probability(
                session, after_state, match_info["venue"],
                match_info["date"], match_info["competition"]
            )
            
            # Calculate WPA
            wpa_change = after_wp - before_wp
            
            # Filter out very small changes to reduce noise
            if abs(wpa_change) < self.min_meaningful_wpa:
                wpa_change = 0.0
            
            # WPA for batter is the change in win probability
            wpa_batter = round(wpa_change, 3)
            # WPA for bowler is the negative of batter WPA
            wpa_bowler = round(-wpa_change, 3)
            
            logger.debug(f"Delivery {delivery.id}: WPA_bat={wpa_batter}, WPA_bowl={wpa_bowler}")
            
            return (wpa_batter, wpa_bowler)
            
        except Exception as e:
            logger.error(f"Error calculating WPA for delivery {delivery.id}: {e}")
            return None
    
    def update_delivery_wpa(self, session: Session, delivery: Delivery, 
                          wpa_batter: float, wpa_bowler: float) -> bool:
        """
        Update a delivery record with calculated WPA values.
        
        Args:
            session: Database session
            delivery: Delivery object to update
            wpa_batter: WPA value for batter
            wpa_bowler: WPA value for bowler
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update the delivery object
            delivery.wpa_batter = wpa_batter
            delivery.wpa_bowler = wpa_bowler
            delivery.wpa_computed_date = datetime.utcnow()
            
            # Commit changes
            session.add(delivery)
            session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating delivery {delivery.id} with WPA: {e}")
            session.rollback()
            return False
    
    def calculate_and_store_delivery_wpa(self, session: Session, delivery: Delivery) -> bool:
        """
        Calculate and store WPA for a single delivery.
        
        Args:
            session: Database session
            delivery: Delivery to process
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Skip if WPA already calculated
            if delivery.has_wpa_calculated():
                logger.debug(f"Delivery {delivery.id} already has WPA calculated")
                return True
            
            # Calculate WPA
            wpa_result = self.calculate_delivery_wpa(session, delivery)
            
            if wpa_result is None:
                logger.debug(f"Cannot calculate WPA for delivery {delivery.id} (likely first innings)")
                return True  # Not an error, just not applicable
            
            wpa_batter, wpa_bowler = wpa_result
            
            # Store WPA values
            success = self.update_delivery_wpa(session, delivery, wpa_batter, wpa_bowler)
            
            if success:
                logger.debug(f"Successfully calculated WPA for delivery {delivery.id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing delivery {delivery.id}: {e}")
            return False
    
    def clear_cache(self):
        """Clear internal caches to free memory"""
        self._venue_cache.clear()
        self._match_cache.clear()
        logger.info("WPA engine caches cleared")
