"""
WPA Curve Trainer - Part 2: Lookup Table Builder

This module contains the lookup table building methods for the WPA Curve Trainer.
Separated to keep files manageable and modular.
"""

from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from venue_utils import VenueClusterManager, get_venue_hierarchy
from datetime import date
import logging

logger = logging.getLogger(__name__)


class WPALookupTableBuilder:
    """
    Builds and manages WPA lookup tables with fallback hierarchy.
    
    This class extends the WPACurveTrainer functionality to create
    cached lookup tables for efficient WPA calculations.
    """
    
    def __init__(self, wpa_trainer):
        """
        Initialize with a WPACurveTrainer instance.
        
        Args:
            wpa_trainer: WPACurveTrainer instance
        """
        self.trainer = wpa_trainer
        self.venue_manager = wpa_trainer.venue_manager
        
    def build_venue_lookup_table(self, session: Session, venue: str,
                                before_date: date, league: Optional[str] = None) -> Dict[str, Any]:
        """
        Build complete WPA lookup table for a venue.
        
        Args:
            session: Database session
            venue: Venue name
            before_date: Only use matches before this date
            league: Optional league filter
            
        Returns:
            Complete WPA lookup table
        """
        logger.info(f"Building WPA lookup table for venue: {venue} before {before_date}")
        
        # Get historical chase outcomes
        outcomes_data = self.trainer.get_second_innings_outcomes(
            session, venue, before_date, league
        )
        
        if not outcomes_data:
            logger.warning(f"No chase data for {venue}")
            return {
                "venue": venue,
                "league": league,
                "build_date": before_date.isoformat(),
                "lookup_table": {},
                "sample_size": 0
            }
        
        # Build lookup table structure
        lookup_table = {}
        
        # Get target score range from data
        targets = list(set(outcome["target"] for outcome in outcomes_data))
        score_range = range(0, max(targets) + 50, 10)  # Score buckets of 10
        
        logger.info(f"Building lookup table for {len(targets)} unique targets")
        
        for target_score in score_range:
            lookup_table[target_score] = {}
            
            for over in range(0, self.trainer.max_overs):
                lookup_table[target_score][over] = {}
                
                for wickets in range(0, self.trainer.max_wickets):
                    # Calculate max reasonable score at this over/wickets
                    max_reasonable_score = min(target_score, (over + 1) * 15)  # ~15 runs per over
                    
                    lookup_table[target_score][over][wickets] = {}
                    
                    for current_score in range(0, max_reasonable_score + 20, 5):  # Score steps of 5
                        win_prob = self.trainer.calculate_win_probability(
                            target_score, current_score, over, wickets, outcomes_data
                        )
                        lookup_table[target_score][over][wickets][current_score] = round(win_prob, 3)
        
        result = {
            "venue": venue,
            "league": league,
            "build_date": before_date.isoformat(),
            "lookup_table": lookup_table,
            "sample_size": len(outcomes_data)
        }
        
        logger.info(f"Completed WPA lookup table for {venue}")
        return result
    
    def get_win_probability_from_table(self, lookup_table: Dict, target_score: int,
                                     current_score: int, over: int, wickets: int) -> float:
        """
        Get win probability from pre-built lookup table with interpolation.
        
        Args:
            lookup_table: Pre-built lookup table
            target_score: Target to chase
            current_score: Current score
            over: Current over
            wickets: Wickets lost
            
        Returns:
            Win probability (0.0 to 1.0)
        """
        table = lookup_table.get("lookup_table", {})
        
        # Find closest target score bucket
        target_bucket = self._find_closest_bucket(target_score, list(table.keys()))
        if target_bucket is None:
            return 0.5  # Default fallback
        
        target_table = table[target_bucket]
        
        # Check exact match first
        if (over in target_table and 
            wickets in target_table[over] and 
            current_score in target_table[over][wickets]):
            return target_table[over][wickets][current_score]
        
        # Interpolate if needed
        return self._interpolate_win_probability(
            target_table, current_score, over, wickets
        )
    
    def _find_closest_bucket(self, value: int, buckets: List[int]) -> Optional[int]:
        """
        Find the closest bucket for a given value.
        
        Args:
            value: Value to find bucket for
            buckets: Available bucket values
            
        Returns:
            Closest bucket value or None if no buckets
        """
        if not buckets:
            return None
        
        return min(buckets, key=lambda x: abs(x - value))
    
    def _interpolate_win_probability(self, target_table: Dict, current_score: int,
                                   over: int, wickets: int) -> float:
        """
        Interpolate win probability from nearby states in lookup table.
        
        Args:
            target_table: Lookup table for specific target
            current_score: Current score
            over: Current over
            wickets: Wickets lost
            
        Returns:
            Interpolated win probability
        """
        # Find nearby states
        nearby_probs = []
        
        for over_offset in [-1, 0, 1]:
            for wicket_offset in [-1, 0, 1]:
                check_over = over + over_offset
                check_wickets = wickets + wicket_offset
                
                if (check_over in target_table and 
                    check_wickets in target_table[check_over]):
                    
                    over_table = target_table[check_over][check_wickets]
                    
                    # Find closest score
                    scores = list(over_table.keys())
                    if scores:
                        closest_score = min(scores, key=lambda x: abs(x - current_score))
                        prob = over_table[closest_score]
                        
                        # Weight by distance
                        distance = abs(over_offset) + abs(wicket_offset) + abs(closest_score - current_score) / 10
                        weight = 1 / (1 + distance)
                        
                        nearby_probs.append((prob, weight))
        
        if not nearby_probs:
            return 0.5  # Default fallback
        
        # Weighted average
        total_weight = sum(weight for _, weight in nearby_probs)
        weighted_prob = sum(prob * weight for prob, weight in nearby_probs)
        
        return weighted_prob / total_weight if total_weight > 0 else 0.5
