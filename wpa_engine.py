"""
WPA Engine v2 - OPTIMIZED for Precomputed Data

CRITICAL FIX: Now uses precomputed wpa_outcomes table for sub-second performance!
This eliminates the 8+ minute lookup table generation issue.
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
    """Match state for WPA calculations"""
    
    def __init__(self, target: int, current_score: int, overs_completed: float, 
                 wickets_lost: int, balls_remaining: int, wickets_remaining: int):
        self.target = target
        self.current_score = current_score
        self.overs_completed = overs_completed
        self.wickets_lost = wickets_lost
        self.balls_remaining = balls_remaining
        self.wickets_remaining = wickets_remaining
        self.runs_needed = max(0, target - current_score)
        self.over = int(overs_completed)
    
    def __repr__(self):
        return f"MatchState(target={self.target}, score={self.current_score}, over={self.over}, wickets={self.wickets_lost})"
    
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
            "over": self.over
        }


class OptimizedWPAEngine:
    """WPA Engine using precomputed data for FAST calculations (milliseconds vs minutes)"""
    
    def __init__(self):
        self.precomputed_service = PrecomputedDataService()
        self._match_cache = {}
        self._stats = {"total": 0, "precomputed_hits": 0, "fallback": 0}
    
    def get_match_info(self, session: Session, match_id: str) -> Optional[Dict]:
        """Get match info with caching"""
        if match_id in self._match_cache:
            return self._match_cache[match_id]
        
        try:
            match = session.query(Match).filter(Match.id == match_id).first()
            if not match:
                return None
            
            # Get first innings total
            result = session.execute(text("""
                SELECT SUM(runs_off_bat + COALESCE(extras, 0)) as total
                FROM deliveries WHERE match_id = :match_id AND innings = 1
            """), {"match_id": match_id}).fetchone()
            
            match_info = {
                "date": match.date,
                "venue": match.venue,
                "competition": match.competition,
                "team1": match.team1,
                "team2": match.team2,
                "winner": match.winner,
                "first_innings_total": result.total if result else 0
            }
            
            self._match_cache[match_id] = match_info
            return match_info
            
        except Exception as e:
            logger.error(f"Error getting match info: {e}")
            return None
    
    def get_match_state_at_delivery(self, session: Session, delivery: Delivery) -> Optional[MatchState]:
        """Get match state using optimized query"""
        try:
            match_info = self.get_match_info(session, delivery.match_id)
            if not match_info or delivery.innings != 2:
                return None
            
            target = match_info["first_innings_total"] + 1
            
            # Single optimized query
            result = session.execute(text("""
                SELECT 
                    COALESCE(SUM(runs_off_bat + COALESCE(extras, 0)), 0) as runs,
                    COUNT(CASE WHEN wicket_type IS NOT NULL THEN 1 END) as wickets
                FROM deliveries
                WHERE match_id = :match_id AND innings = :innings
                    AND (over < :over OR (over = :over AND ball <= :ball))
            """), {
                "match_id": delivery.match_id,
                "innings": delivery.innings,
                "over": delivery.over,
                "ball": delivery.ball
            }).fetchone()
            
            if not result:
                return None
            
            balls_completed = (delivery.over * 6) + delivery.ball
            
            return MatchState(
                target=target,
                current_score=result.runs,
                overs_completed=balls_completed / 6.0,
                wickets_lost=result.wickets,
                balls_remaining=max(0, 120 - balls_completed),
                wickets_remaining=max(0, 10 - result.wickets)
            )
            
        except Exception as e:
            logger.error(f"Error calculating match state: {e}")
            return None
    
    def get_match_state_after_delivery(self, session: Session, delivery: Delivery) -> Optional[MatchState]:
        """Get match state after delivery"""
        before_state = self.get_match_state_at_delivery(session, delivery)
        if not before_state:
            return None
        
        delivery_runs = (delivery.runs_off_bat or 0) + (delivery.extras or 0)
        delivery_wickets = 1 if delivery.wicket_type else 0
        
        return MatchState(
            target=before_state.target,
            current_score=before_state.current_score + delivery_runs,
            overs_completed=before_state.overs_completed + (1/6),
            wickets_lost=before_state.wickets_lost + delivery_wickets,
            balls_remaining=max(0, before_state.balls_remaining - 1),
            wickets_remaining=max(0, before_state.wickets_remaining - delivery_wickets)
        )
    
    def calculate_win_probability(self, session: Session, match_state: MatchState, 
                                venue: str, match_date: date, league: str) -> Tuple[float, str]:
        """Calculate win probability using PRECOMPUTED data (FAST!)"""
        self._stats["total"] += 1
        
        # Check if decided
        if match_state.runs_needed <= 0:
            return 1.0, "decided_win"
        if match_state.balls_remaining <= 0 or match_state.wickets_remaining <= 0:
            return 0.0, "decided_loss"
        
        try:
            # Use precomputed service for INSTANT lookup
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
                self._stats["precomputed_hits"] += 1
            else:
                self._stats["fallback"] += 1
            
            return max(0.0, min(1.0, win_prob)), data_source
            
        except Exception as e:
            logger.error(f"Error calculating win probability: {e}")
            self._stats["fallback"] += 1
            return self._simple_fallback(match_state), "emergency"
    
    def _simple_fallback(self, match_state: MatchState) -> float:
        """Emergency fallback calculation"""
        if match_state.runs_needed <= 0:
            return 1.0
        if match_state.balls_remaining <= 0 or match_state.wickets_remaining <= 0:
            return 0.0
        
        required_rr = (match_state.runs_needed * 6) / match_state.balls_remaining
        wickets_factor = match_state.wickets_remaining / 10
        
        if required_rr <= 8:
            base_prob = 0.7
        elif required_rr <= 12:
            base_prob = 0.4
        else:
            base_prob = 0.1
        
        return max(0.0, min(1.0, base_prob * wickets_factor))
    
    def calculate_delivery_wpa(self, session: Session, delivery: Delivery) -> Optional[Tuple[float, float, Dict]]:
        """Calculate WPA for delivery using OPTIMIZED approach"""
        try:
            match_info = self.get_match_info(session, delivery.match_id)
            if not match_info or delivery.innings != 2:
                return None
            
            before_state = self.get_match_state_at_delivery(session, delivery)
            after_state = self.get_match_state_after_delivery(session, delivery)
            
            if not before_state or not after_state:
                return None
            
            # Calculate win probabilities using PRECOMPUTED data
            before_wp, before_source = self.calculate_win_probability(
                session, before_state, match_info["venue"], 
                match_info["date"], match_info["competition"]
            )
            
            after_wp, after_source = self.calculate_win_probability(
                session, after_state, match_info["venue"],
                match_info["date"], match_info["competition"]
            )
            
            # Calculate WPA
            wpa_change = after_wp - before_wp
            
            # Filter very small changes
            if abs(wpa_change) < 0.001:
                wpa_change = 0.0
            
            wpa_batter = round(wpa_change, 3)
            wpa_bowler = round(-wpa_change, 3)
            
            metadata = {
                "before_wp": round(before_wp, 3),
                "after_wp": round(after_wp, 3),
                "data_source": before_source,
                "venue": match_info["venue"]
            }
            
            return (wpa_batter, wpa_bowler, metadata)
            
        except Exception as e:
            logger.error(f"Error calculating WPA: {e}")
            return None
    
    def calculate_and_store_delivery_wpa(self, session: Session, delivery: Delivery) -> bool:
        """Calculate and store WPA using OPTIMIZED engine"""
        try:
            if delivery.has_wpa_calculated():
                return True
            
            wpa_result = self.calculate_delivery_wpa(session, delivery)
            if wpa_result is None:
                return True  # Not applicable
            
            wpa_batter, wpa_bowler, metadata = wpa_result
            
            delivery.wpa_batter = wpa_batter
            delivery.wpa_bowler = wpa_bowler
            delivery.wpa_computed_date = datetime.utcnow()
            
            session.add(delivery)
            session.commit()
            
            logger.debug(f"WPA stored for delivery {delivery.id} using {metadata['data_source']} data")
            return True
            
        except Exception as e:
            logger.error(f"Error storing WPA: {e}")
            session.rollback()
            return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        total = self._stats["total"]
        precomputed = self._stats["precomputed_hits"]
        
        return {
            "total_calculations": total,
            "precomputed_hits": precomputed,
            "fallback_calculations": self._stats["fallback"],
            "precomputed_hit_rate": round((precomputed / total) * 100, 1) if total > 0 else 0,
            "performance_mode": "OPTIMIZED" if precomputed > 0 else "NEEDS_PRECOMPUTED_DATA"
        }
    
    def clear_cache(self):
        """Clear caches"""
        self._match_cache.clear()


# Backward compatibility alias
PerDeliveryWPAEngine = OptimizedWPAEngine
