"""
Precomputed Data Service - Fast Lookup Interface for WPA Engine

This service provides fast access to precomputed analytics data with automatic
fallback hierarchy, designed for sub-second API responses.
"""

from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, text
from precomputed_models import WPAOutcome, VenueResource, PlayerBaseline, TeamPhaseStat, VenueCluster
from venue_utils import VenueClusterManager
from datetime import date
import logging

logger = logging.getLogger(__name__)


class PrecomputedDataService:
    """
    Service layer for accessing pre-computed analytics data.
    
    Provides simple, fast methods for retrieving pre-calculated values
    with automatic fallback hierarchy.
    """
    
    def __init__(self):
        self.venue_manager = VenueClusterManager()
        
        # Cache for frequently accessed data
        self._venue_cluster_cache = {}
        self._fallback_cache = {}
    
    def get_win_probability(self, session: Session, venue: str, target: int, 
                          over: int, wickets: int, runs: int, 
                          match_date: date, league: str = None) -> Tuple[float, str]:
        """
        Get win probability from pre-computed data with fallback.
        
        Args:
            session: Database session
            venue: Venue name (exact match from database)
            target: Target score to chase
            over: Current over (0-19)
            wickets: Wickets lost (0-9)
            runs: Current runs scored
            match_date: Match date (for chronological constraint)
            league: League for filtering (optional)
            
        Returns:
            Tuple of (win_probability, data_source)
        """
        logger.debug(f"Getting WP for {venue}, target={target}, over={over}, wickets={wickets}, runs={runs}")
        
        # Calculate target bucket and over bucket for precomputed lookup
        target_bucket = self._get_target_bucket(target)
        over_bucket = self._get_over_bucket(over)
        
        # Try venue-specific data first (with relaxed chronological constraint for development)
        wp = self._query_wpa_outcomes(
            session, venue, target_bucket, over_bucket, wickets, runs, match_date, league, strict_chronological=True
        )
        if wp is not None:
            logger.debug(f"Found venue-specific WP: {wp}")
            return wp, "venue"
        
        # If no data with strict chronological constraint, try relaxed for development
        wp_relaxed = self._query_wpa_outcomes(
            session, venue, target_bucket, over_bucket, wickets, runs, match_date, league, strict_chronological=False
        )
        if wp_relaxed is not None:
            logger.debug(f"Found venue WP (relaxed chronological): {wp_relaxed}")
            return wp_relaxed, "venue_relaxed"
        
        # Try cluster fallback
        cluster_wp = self._try_cluster_fallback(
            session, venue, target_bucket, over_bucket, wickets, runs, match_date, league
        )
        if cluster_wp is not None:
            logger.debug(f"Found cluster WP: {cluster_wp}")
            return cluster_wp, "cluster"
        
        # Try league fallback
        if league:
            league_wp = self._try_league_fallback(
                session, league, target_bucket, over_bucket, wickets, runs, match_date
            )
            if league_wp is not None:
                logger.debug(f"Found league WP: {league_wp}")
                return league_wp, "league"
        
        # Try global fallback
        global_wp = self._try_global_fallback(
            session, target_bucket, over_bucket, wickets, runs, match_date
        )
        if global_wp is not None:
            logger.debug(f"Found global WP: {global_wp}")
            return global_wp, "global"
        
        # Last resort: heuristic calculation
        heuristic_wp = self._calculate_heuristic_win_probability(target, runs, over, wickets)
        logger.debug(f"Using heuristic WP: {heuristic_wp}")
        return heuristic_wp, "heuristic"
    
    def _get_target_bucket(self, target: int) -> int:
        """Convert target to bucket (grouped in 10-run buckets)"""
        return (target // 10) * 10
    
    def _get_over_bucket(self, over: int) -> int:
        """Convert over to bucket (grouped in 2-over buckets)"""
        return (over // 2) * 2
    
    def _query_wpa_outcomes(self, session: Session, venue: str, target_bucket: int,
                           over_bucket: int, wickets: int, runs: int,
                           match_date: date, league: str = None, strict_chronological: bool = True) -> Optional[float]:
        """
        Query precomputed WPA outcomes table.
        
        Args:
            strict_chronological: If True, only use data before match_date. If False, use all data.
        
        Returns:
            Win probability or None if not found
        """
        try:
            # Find matching WPA outcome with score range
            query = session.query(WPAOutcome).filter(
                WPAOutcome.venue == venue,
                WPAOutcome.target_bucket == target_bucket,
                WPAOutcome.over_bucket == over_bucket,
                WPAOutcome.wickets_lost == wickets,
                WPAOutcome.runs_range_min <= runs,
                WPAOutcome.runs_range_max >= runs
            )
            
            # Apply chronological constraint only if strict and match_date is provided
            if strict_chronological and match_date is not None:
                query = query.filter(WPAOutcome.data_through_date < match_date)
            
            if league:
                query = query.filter(WPAOutcome.league == league)
            
            # Get the most recent computation
            outcome = query.order_by(WPAOutcome.computed_date.desc()).first()
            
            if outcome and outcome.sample_size >= 5:  # Minimum sample size
                return float(outcome.win_probability)
            
            return None
            
        except Exception as e:
            logger.error(f"Error querying WPA outcomes: {e}")
            return None
    
    def _try_cluster_fallback(self, session: Session, venue: str, target_bucket: int,
                             over_bucket: int, wickets: int, runs: int,
                             match_date: date, league: str = None) -> Optional[float]:
        """Try cluster-level fallback for win probability"""
        try:
            cluster = self.venue_manager.get_venue_cluster(venue)
            if not cluster:
                return None
            
            cluster_venues = self.venue_manager.venue_clusters.get(cluster, [])
            
            # Try each venue in the cluster
            for cluster_venue in cluster_venues:
                wp = self._query_wpa_outcomes(
                    session, cluster_venue, target_bucket, over_bucket, 
                    wickets, runs, match_date, league
                )
                if wp is not None:
                    return wp
            
            return None
            
        except Exception as e:
            logger.error(f"Error in cluster fallback: {e}")
            return None
    
    def _try_league_fallback(self, session: Session, league: str, target_bucket: int,
                            over_bucket: int, wickets: int, runs: int,
                            match_date: date) -> Optional[float]:
        """Try league-level fallback for win probability"""
        try:
            # Query for any venue in the league
            query = session.query(WPAOutcome).filter(
                WPAOutcome.league == league,
                WPAOutcome.target_bucket == target_bucket,
                WPAOutcome.over_bucket == over_bucket,
                WPAOutcome.wickets_lost == wickets,
                WPAOutcome.runs_range_min <= runs,
                WPAOutcome.runs_range_max >= runs,
                WPAOutcome.data_through_date < match_date,
                WPAOutcome.sample_size >= 10  # Higher minimum for league data
            )
            
            outcome = query.order_by(WPAOutcome.sample_size.desc()).first()
            
            if outcome:
                return float(outcome.win_probability)
            
            return None
            
        except Exception as e:
            logger.error(f"Error in league fallback: {e}")
            return None
    
    def _try_global_fallback(self, session: Session, target_bucket: int,
                            over_bucket: int, wickets: int, runs: int,
                            match_date: date) -> Optional[float]:
        """Try global fallback for win probability"""
        try:
            # Query for any venue globally
            query = session.query(WPAOutcome).filter(
                WPAOutcome.target_bucket == target_bucket,
                WPAOutcome.over_bucket == over_bucket,
                WPAOutcome.wickets_lost == wickets,
                WPAOutcome.runs_range_min <= runs,
                WPAOutcome.runs_range_max >= runs,
                WPAOutcome.data_through_date < match_date,
                WPAOutcome.sample_size >= 15  # Higher minimum for global data
            )
            
            outcome = query.order_by(WPAOutcome.sample_size.desc()).first()
            
            if outcome:
                return float(outcome.win_probability)
            
            return None
            
        except Exception as e:
            logger.error(f"Error in global fallback: {e}")
            return None
    
    def _calculate_heuristic_win_probability(self, target: int, current_score: int,
                                           over: int, wickets: int) -> float:
        """
        Calculate fallback win probability using simple heuristics.
        
        Args:
            target: Target score
            current_score: Current runs scored
            over: Current over
            wickets: Wickets lost
            
        Returns:
            Estimated win probability
        """
        runs_needed = target - current_score
        overs_remaining = 20 - over
        wickets_remaining = 10 - wickets
        
        if runs_needed <= 0:
            return 1.0
        
        if overs_remaining <= 0 or wickets_remaining <= 0:
            return 0.0
        
        # Required run rate
        balls_remaining = overs_remaining * 6
        required_rr = (runs_needed * 6) / balls_remaining if balls_remaining > 0 else float('inf')
        
        # Simple probability based on required rate and wickets
        if required_rr <= 6:  # Easy chase
            base_prob = 0.8
        elif required_rr <= 9:  # Moderate chase
            base_prob = 0.6
        elif required_rr <= 12:  # Difficult chase
            base_prob = 0.3
        else:  # Very difficult
            base_prob = 0.1
        
        # Adjust for wickets remaining
        wicket_factor = wickets_remaining / 10
        
        return max(0.0, min(1.0, base_prob * wicket_factor))
    
    def get_venue_resource_percentage(self, session: Session, venue: str, innings: int, 
                                    over: int, wickets: int, match_date: date,
                                    league: str = None) -> Tuple[float, str]:
        """
        Get resource percentage remaining from pre-computed venue data.
        
        Args:
            session: Database session
            venue: Venue name
            innings: Innings (1 or 2)
            over: Current over
            wickets: Wickets lost
            match_date: Match date
            league: League (optional)
            
        Returns:
            Tuple of (resource_percentage, data_source)
        """
        try:
            # Try venue-specific data first
            query = session.query(VenueResource).filter(
                VenueResource.venue == venue,
                VenueResource.innings == innings,
                VenueResource.over_num == over,
                VenueResource.wickets_lost == wickets,
                VenueResource.data_through_date < match_date
            )
            
            if league:
                query = query.filter(VenueResource.league == league)
            
            resource = query.order_by(VenueResource.computed_date.desc()).first()
            
            if resource and resource.sample_size >= 3:
                return float(resource.resource_percentage), "venue"
            
            # Try cluster fallback
            cluster = self.venue_manager.get_venue_cluster(venue)
            if cluster:
                cluster_venues = self.venue_manager.venue_clusters.get(cluster, [])
                for cluster_venue in cluster_venues:
                    query = session.query(VenueResource).filter(
                        VenueResource.venue == cluster_venue,
                        VenueResource.innings == innings,
                        VenueResource.over_num == over,
                        VenueResource.wickets_lost == wickets,
                        VenueResource.data_through_date < match_date
                    )
                    
                    resource = query.order_by(VenueResource.computed_date.desc()).first()
                    if resource and resource.sample_size >= 3:
                        return float(resource.resource_percentage), "cluster"
            
            # Fallback to heuristic
            overs_remaining = max(0, 20 - over)
            wickets_remaining = max(1, 10 - wickets)
            
            base_resource = (overs_remaining / 20) * 100
            wicket_factor = wickets_remaining / 10
            
            return max(0.0, min(100.0, base_resource * wicket_factor)), "heuristic"
            
        except Exception as e:
            logger.error(f"Error getting venue resource: {e}")
            return 50.0, "error"  # Default 50% resource
    
    def check_precomputed_data_availability(self, session: Session, venue: str, 
                                          match_date: date, league: str = None) -> Dict[str, Any]:
        """
        Check what precomputed data is available for a venue.
        
        Args:
            session: Database session
            venue: Venue name
            match_date: Match date
            league: League (optional)
            
        Returns:
            Dictionary with data availability information
        """
        try:
            # Check WPA outcomes availability
            wpa_count = session.query(WPAOutcome).filter(
                WPAOutcome.venue == venue,
                WPAOutcome.data_through_date < match_date
            ).count()
            
            # Check venue resources availability
            resource_count = session.query(VenueResource).filter(
                VenueResource.venue == venue,
                VenueResource.data_through_date < match_date
            ).count()
            
            # Get latest computation dates
            latest_wpa = session.query(WPAOutcome).filter(
                WPAOutcome.venue == venue,
                WPAOutcome.data_through_date < match_date
            ).order_by(WPAOutcome.computed_date.desc()).first()
            
            latest_resource = session.query(VenueResource).filter(
                VenueResource.venue == venue,
                VenueResource.data_through_date < match_date
            ).order_by(VenueResource.computed_date.desc()).first()
            
            return {
                "venue": venue,
                "match_date": match_date.isoformat(),
                "wpa_outcomes_available": wpa_count > 0,
                "wpa_outcomes_count": wpa_count,
                "venue_resources_available": resource_count > 0,
                "venue_resources_count": resource_count,
                "latest_wpa_computation": latest_wpa.computed_date.isoformat() if latest_wpa else None,
                "latest_resource_computation": latest_resource.computed_date.isoformat() if latest_resource else None,
                "data_quality": "good" if wpa_count > 10 and resource_count > 10 else "limited"
            }
            
        except Exception as e:
            logger.error(f"Error checking data availability: {e}")
            return {
                "venue": venue,
                "error": str(e),
                "data_quality": "unknown"
            }
