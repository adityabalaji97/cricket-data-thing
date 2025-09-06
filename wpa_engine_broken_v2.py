"""
WPA Engine v2 - Optimized Per-Delivery WPA Calculation Using Precomputed Data

This module implements the core engine for calculating Win Probability Added (WPA)
using precomputed tables for sub-second performance, following WPA_ENGINE_PRD.md.

Key Features:
- Uses precomputed wpa_outcomes and venue_resources tables (FAST)
- Falls back to raw calculation only when precomputed data missing (RARE)
- Maintains strict chronological constraints
- Venue fallback hierarchy (venue → cluster → league → global)
- Sub-second per-delivery WPA calculation
"""

from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from models import Match, Delivery
from precomputed_service import PrecomputedDataService
from datetime import date, datetime
import logging

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
        self.over = int(overs_completed)
    
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
            "current_run_rate": round(self.current_run_rate, 2),
            "over": self.over
        }


class OptimizedWPAEngine:
    """
    Optimized WPA Engine using precomputed data for fast calculations.
    
    This engine prioritizes precomputed table lookups over raw calculations,
    achieving sub-second performance for per-delivery WPA calculations.
    """
    
    def __init__(self):
        self.precomputed_service = PrecomputedDataService()
        
        # WPA calculation parameters
        self.max_overs = 20
        self.max_wickets = 10
        
        # Minimum win probability change to avoid noise in decided matches
        self.min_meaningful_wpa = 0.001  # 0.1% win probability change
        
        # Cache for match information to avoid repeated queries
        self._match_cache = {}
        
        # Performance tracking
        self._calculation_stats = {
            "total_calculations": 0,
            "precomputed_hits": 0,
            "fallback_calculations": 0,
            "cache_hits": 0
        }
    
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
            self._calculation_stats["cache_hits"] += 1
            return self._match_cache[match_id]
        
        try:
            match = session.query(Match).filter(Match.id == match_id).first()
            
            if not match:
                logger.warning(f"Match {match_id} not found")
                return None
    
    def calculate_win_probability(self, session: Session, match_state: MatchState, 
                                venue: str, match_date: date, league: str) -> Tuple[float, str]:
        """
        Calculate win probability using precomputed data (FAST).
        
        Args:
            session: Database session
            match_state: Current match state
            venue: Venue name
            match_date: Match date (for chronological constraint)
            league: League/competition
            
        Returns:
            Tuple of (win_probability, data_source)
        """
        try:
            self._calculation_stats["total_calculations"] += 1
            
            # Check if match is already decided
            if match_state.runs_needed <= 0:
                return 1.0, "decided_win"
            
            if match_state.balls_remaining <= 0 or match_state.wickets_remaining <= 0:
                return 0.0, "decided_loss"
            
            # Use precomputed service for fast lookup
            win_prob, data_source = self.precomputed_service.get_win_probability(
                session=session,
                venue=venue,
                target=match_state.target,
                over=match_state.over,
                wickets=match_state.wickets_lost,
                runs=match_state.current_score,
                match_date=match_date,
                league=league
            )
            
            if data_source != "heuristic":
                self._calculation_stats["precomputed_hits"] += 1
            else:
                self._calculation_stats["fallback_calculations"] += 1
            
            return max(0.0, min(1.0, win_prob)), data_source
            
        except Exception as e:
            logger.error(f"Error calculating win probability: {e}")
            # Emergency fallback
            heuristic_wp = self._emergency_fallback_probability(match_state)
            return heuristic_wp, "emergency_fallback"
    
    def _emergency_fallback_probability(self, match_state: MatchState) -> float:
        """
        Emergency fallback when all else fails.
        """
        if match_state.runs_needed <= 0:
            return 1.0
        if match_state.balls_remaining <= 0 or match_state.wickets_remaining <= 0:
            return 0.0
        
        # Very simple heuristic
        required_rr = match_state.required_run_rate
        wickets_factor = match_state.wickets_remaining / self.max_wickets
        
        if required_rr <= 8:
            base_prob = 0.7
        elif required_rr <= 12:
            base_prob = 0.4
        else:
            base_prob = 0.1
        
        return max(0.0, min(1.0, base_prob * wickets_factor))
            
            # Get first innings total using optimized query
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
        Calculate the match state at a specific delivery using optimized queries.
        
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
            
            # Optimized cumulative query - single database hit
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
