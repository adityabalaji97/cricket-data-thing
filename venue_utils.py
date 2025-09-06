"""
Venue utilities for WPA Engine - Venue clustering and fallback logic

This module handles venue grouping and provides fallback mechanisms
for venues with insufficient historical data.
"""

from typing import Dict, List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import text
from models import Match
from datetime import date
import logging

logger = logging.getLogger(__name__)


class VenueClusterManager:
    """
    Manages venue clustering and fallback hierarchy for WPA calculations.
    
    Fallback hierarchy: venue > venue cluster > league > global average
    """
    
    def __init__(self):
        # Venue clusters based on characteristics (expandable)
        self.venue_clusters = {
            # High scoring venues
            "high_scoring": [
                "M Chinnaswamy Stadium, Bangalore", "Chinnaswamy Stadium",
                "Eden Gardens", "Wankhede Stadium, Mumbai", "Mumbai",
                "Sharjah Cricket Stadium", "Dubai International Cricket Stadium"
            ],
            
            # Balanced venues  
            "balanced": [
                "Feroz Shah Kotla", "Arun Jaitley Stadium", "Delhi",
                "MA Chidambaram Stadium, Chennai", "Chennai", "Chepauk",
                "Rajiv Gandhi International Stadium", "Hyderabad"
            ],
            
            # Bowling friendly venues
            "bowling_friendly": [
                "MA Chidambaram Stadium, Chennai", "Chennai",
                "Sawai Mansingh Stadium", "Jaipur",
                "Punjab Cricket Association IS Bindra Stadium", "Mohali"
            ],
            
            # International venues
            "international": [
                "Lord's", "The Oval", "Old Trafford", "Edgbaston, Birmingham",
                "MCG", "SCG", "Adelaide Oval", "WACA",
                "Basin Reserve", "Eden Park", "Hagley Oval"
            ]
        }
        
        # Minimum matches required for venue-specific analysis
        self.min_matches_venue = 5
        self.min_matches_cluster = 20
        
    def get_venue_cluster(self, venue: str) -> Optional[str]:
        """
        Get the cluster for a given venue.
        
        Args:
            venue: Venue name
            
        Returns:
            Cluster name or None if not found
        """
        for cluster, venues in self.venue_clusters.items():
            if any(v.lower() in venue.lower() or venue.lower() in v.lower() 
                   for v in venues):
                return cluster
        return None
    
    def get_fallback_venues(self, venue: str, league: Optional[str] = None) -> List[str]:
        """
        Get fallback venues for insufficient data scenarios.
        
        Args:
            venue: Primary venue
            league: League name for league-level fallback
            
        Returns:
            List of fallback venue names in priority order
        """
        fallbacks = []
        
        # First try venue cluster
        cluster = self.get_venue_cluster(venue)
        if cluster:
            cluster_venues = [v for v in self.venue_clusters[cluster] if v != venue]
            fallbacks.extend(cluster_venues)
        
        # Then add league-level fallback (all venues from same league)
        if league:
            fallbacks.append(f"LEAGUE_{league}")
        
        # Finally global fallback
        fallbacks.append("GLOBAL")
        
        return fallbacks
    
    def normalize_venue_name(self, venue: str) -> str:
        """
        Normalize venue names for consistent grouping.
        
        Args:
            venue: Raw venue name
            
        Returns:
            Normalized venue name
        """
        if not venue:
            return "Unknown"
            
        # Basic normalization
        normalized = venue.strip()
        
        # Handle common variations
        venue_mappings = {
            "M Chinnaswamy Stadium": "Chinnaswamy Stadium",
            "M. Chinnaswamy Stadium": "Chinnaswamy Stadium",
            "Arun Jaitley Stadium": "Feroz Shah Kotla",
            "Feroz Shah Kotla Ground": "Feroz Shah Kotla",
            "MA Chidambaram Stadium": "Chepauk Stadium",
            "M. A. Chidambaram Stadium": "Chepauk Stadium"
        }
        
        return venue_mappings.get(normalized, normalized)
    
    def get_venue_match_count(self, session: Session, venue: str, 
                             before_date: Optional[date] = None) -> int:
        """
        Get number of matches at a venue before a given date.
        
        Args:
            session: Database session
            venue: Venue name
            before_date: Only count matches before this date
            
        Returns:
            Number of matches
        """
        query = session.query(Match).filter(Match.venue == venue)
        
        if before_date:
            query = query.filter(Match.date < before_date)
            
        return query.count()


def get_venue_hierarchy(session: Session, venue: str, league: Optional[str] = None,
                       before_date: Optional[date] = None) -> Dict[str, int]:
    """
    Get venue hierarchy with match counts for fallback logic.
    
    Args:
        session: Database session
        venue: Primary venue
        league: League for league-level fallback
        before_date: Only consider matches before this date
        
    Returns:
        Dictionary with hierarchy levels and their match counts
    """
    manager = VenueClusterManager()
    hierarchy = {}
    
    # Primary venue
    venue_count = manager.get_venue_match_count(session, venue, before_date)
    hierarchy["venue"] = venue_count
    
    # Cluster level
    cluster = manager.get_venue_cluster(venue)
    if cluster:
        cluster_venues = manager.venue_clusters[cluster]
        # Use LIKE matching for venue names with cities
        cluster_query = session.query(Match)
        conditions = []
        for cluster_venue in cluster_venues:
            conditions.append(Match.venue.ilike(f"%{cluster_venue}%"))
        
        if conditions:
            from sqlalchemy import or_
            cluster_query = cluster_query.filter(or_(*conditions))
            if before_date:
                cluster_query = cluster_query.filter(Match.date < before_date)
            hierarchy["cluster"] = cluster_query.count()
        else:
            hierarchy["cluster"] = 0
    else:
        hierarchy["cluster"] = 0
    
    # League level
    if league:
        league_query = session.query(Match).filter(Match.competition == league)
        if before_date:
            league_query = league_query.filter(Match.date < before_date)
        hierarchy["league"] = league_query.count()
    else:
        hierarchy["league"] = 0
    
    # Global level
    global_query = session.query(Match)
    if before_date:
        global_query = global_query.filter(Match.date < before_date)
    hierarchy["global"] = global_query.count()
    
    return hierarchy
