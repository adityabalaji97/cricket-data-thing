"""WPA Engine v2 - Optimized Per-Delivery WPA Calculation Using Precomputed Data

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
        }\n            # Calculate win probabilities using precomputed data\n            before_wp, before_source = self.calculate_win_probability(\n                session, before_state, match_info[\"venue\"], \n                match_info[\"date\"], match_info[\"competition\"]\n            )\n            \n            after_wp, after_source = self.calculate_win_probability(\n                session, after_state, match_info[\"venue\"],\n                match_info[\"date\"], match_info[\"competition\"]\n            )\n            \n            # Calculate WPA\n            wpa_change = after_wp - before_wp\n            \n            # Filter out very small changes to reduce noise\n            if abs(wpa_change) < self.min_meaningful_wpa:\n                wpa_change = 0.0\n            \n            # WPA for batter is the change in win probability\n            wpa_batter = round(wpa_change, 3)\n            # WPA for bowler is the negative of batter WPA\n            wpa_bowler = round(-wpa_change, 3)\n            \n            # Create metadata for debugging/analysis\n            metadata = {\n                \"before_wp\": round(before_wp, 3),\n                \"after_wp\": round(after_wp, 3),\n                \"before_source\": before_source,\n                \"after_source\": after_source,\n                \"venue\": match_info[\"venue\"],\n                \"target\": before_state.target,\n                \"before_score\": before_state.current_score,\n                \"after_score\": after_state.current_score,\n                \"over\": before_state.over,\n                \"wickets\": before_state.wickets_lost\n            }\n            \n            logger.debug(f\"Delivery {delivery.id}: WPA_bat={wpa_batter}, WPA_bowl={wpa_bowler}, source={before_source}\")\n            \n            return (wpa_batter, wpa_bowler, metadata)\n            \n        except Exception as e:\n            logger.error(f\"Error calculating WPA for delivery {delivery.id}: {e}\")\n            return None\n    \n    def update_delivery_wpa(self, session: Session, delivery: Delivery, \n                          wpa_batter: float, wpa_bowler: float) -> bool:\n        \"\"\"\n        Update a delivery record with calculated WPA values.\n        \n        Args:\n            session: Database session\n            delivery: Delivery object to update\n            wpa_batter: WPA value for batter\n            wpa_bowler: WPA value for bowler\n            \n        Returns:\n            True if successful, False otherwise\n        \"\"\"\n        try:\n            # Update the delivery object\n            delivery.wpa_batter = wpa_batter\n            delivery.wpa_bowler = wpa_bowler\n            delivery.wpa_computed_date = datetime.utcnow()\n            \n            # Commit changes\n            session.add(delivery)\n            session.commit()\n            \n            return True\n            \n        except Exception as e:\n            logger.error(f\"Error updating delivery {delivery.id} with WPA: {e}\")\n            session.rollback()\n            return False\n    \n    def calculate_and_store_delivery_wpa(self, session: Session, delivery: Delivery) -> bool:\n        \"\"\"\n        Calculate and store WPA for a single delivery using optimized precomputed data.\n        \n        Args:\n            session: Database session\n            delivery: Delivery to process\n            \n        Returns:\n            True if successful, False otherwise\n        \"\"\"\n        try:\n            # Skip if WPA already calculated\n            if delivery.has_wpa_calculated():\n                logger.debug(f\"Delivery {delivery.id} already has WPA calculated\")\n                return True\n            \n            # Calculate WPA using optimized engine\n            wpa_result = self.calculate_delivery_wpa(session, delivery)\n            \n            if wpa_result is None:\n                logger.debug(f\"Cannot calculate WPA for delivery {delivery.id} (likely first innings)\")\n                return True  # Not an error, just not applicable\n            \n            wpa_batter, wpa_bowler, metadata = wpa_result\n            \n            # Store WPA values\n            success = self.update_delivery_wpa(session, delivery, wpa_batter, wpa_bowler)\n            \n            if success:\n                logger.debug(f\"Successfully calculated WPA for delivery {delivery.id} using {metadata['before_source']} data\")\n            \n            return success\n            \n        except Exception as e:\n            logger.error(f\"Error processing delivery {delivery.id}: {e}\")\n            return False\n    \n    def get_performance_stats(self) -> Dict[str, Any]:\n        \"\"\"\n        Get performance statistics for the WPA engine.\n        \n        Returns:\n            Dictionary with performance metrics\n        \"\"\"\n        total = self._calculation_stats[\"total_calculations\"]\n        precomputed = self._calculation_stats[\"precomputed_hits\"]\n        \n        return {\n            \"total_calculations\": total,\n            \"precomputed_hits\": precomputed,\n            \"fallback_calculations\": self._calculation_stats[\"fallback_calculations\"],\n            \"cache_hits\": self._calculation_stats[\"cache_hits\"],\n            \"precomputed_hit_rate\": round((precomputed / total) * 100, 1) if total > 0 else 0,\n            \"cache_hit_rate\": round((self._calculation_stats[\"cache_hits\"] / total) * 100, 1) if total > 0 else 0\n        }\n    \n    def clear_cache(self):\n        \"\"\"Clear internal caches to free memory\"\"\"\n        self._match_cache.clear()\n        self.precomputed_service._venue_cluster_cache.clear()\n        self.precomputed_service._fallback_cache.clear()\n        logger.info(\"Optimized WPA engine caches cleared\")\n    \n    def reset_performance_stats(self):\n        \"\"\"Reset performance statistics\"\"\"\n        self._calculation_stats = {\n            \"total_calculations\": 0,\n            \"precomputed_hits\": 0,\n            \"fallback_calculations\": 0,\n            \"cache_hits\": 0\n        }\n        logger.info(\"Performance statistics reset\")\n\n\n# Backward compatibility alias\nPerDeliveryWPAEngine = OptimizedWPAEngine\n