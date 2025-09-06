"""
WPA Curve Trainer - Part 3: Fallback and Integration Methods

This module contains the fallback hierarchy and integration methods
for the WPA Curve Trainer, following the same patterns as context_model.py.
"""

from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from venue_utils import VenueClusterManager, get_venue_hierarchy
from wpa_curve_trainer import WPACurveTrainer
from wpa_lookup_builder import WPALookupTableBuilder
from datetime import date
import logging

logger = logging.getLogger(__name__)


class WPAEngineWithFallback:
    """
    Complete WPA Engine with fallback hierarchy support.
    
    Integrates WPACurveTrainer with fallback logic following the same
    pattern as VenueResourceTableBuilder.
    """
    
    def __init__(self):
        self.trainer = WPACurveTrainer()
        self.lookup_builder = WPALookupTableBuilder(self.trainer)
        self.venue_manager = self.trainer.venue_manager
    
    def get_wpa_lookup_table_with_fallback(self, session: Session, venue: str,
                                          before_date: date, league: Optional[str] = None) -> Dict[str, Any]:
        """
        Get WPA lookup table with fallback hierarchy: venue > cluster > league > global.
        
        Args:
            session: Database session
            venue: Primary venue
            before_date: Only use matches before this date
            league: League for league-level fallback
            
        Returns:
            WPA lookup table with fallback info
        """
        logger.info(f"Getting WPA lookup table with fallback for {venue}")
        
        # Check venue hierarchy (same logic as context_model)
        hierarchy = get_venue_hierarchy(session, venue, league, before_date)
        
        # Try venue-specific first
        if hierarchy["venue"] >= self.trainer.min_matches_venue:
            logger.info(f"Using venue-specific WPA data for {venue} ({hierarchy['venue']} matches)")
            return {
                "source": "venue",
                "matches_used": hierarchy["venue"],
                "wpa_table": self.lookup_builder.build_venue_lookup_table(
                    session, venue, before_date, league
                )
            }
        
        # Try cluster fallback
        cluster = self.venue_manager.get_venue_cluster(venue)
        if cluster and hierarchy["cluster"] >= self.trainer.min_matches_cluster:
            logger.info(f"Using cluster fallback for WPA {venue} ({cluster}, {hierarchy['cluster']} matches)")
            cluster_venues = self.venue_manager.venue_clusters[cluster]
            return {
                "source": "cluster",
                "cluster": cluster,
                "matches_used": hierarchy["cluster"],
                "wpa_table": self._build_cluster_wpa_table(
                    session, cluster_venues, before_date, league
                )
            }
        
        # Try league fallback
        if league and hierarchy["league"] >= self.trainer.min_matches_league:
            logger.info(f"Using league fallback for WPA {venue} ({league}, {hierarchy['league']} matches)")
            return {
                "source": "league",
                "league": league,
                "matches_used": hierarchy["league"],
                "wpa_table": self._build_league_wpa_table(session, league, before_date)
            }
        
        # Global fallback
        logger.info(f"Using global fallback for WPA {venue} ({hierarchy['global']} matches)")
        return {
            "source": "global",
            "matches_used": hierarchy["global"],
            "wpa_table": self._build_global_wpa_table(session, before_date)
        }
    
    def _build_cluster_wpa_table(self, session: Session, cluster_venues: List[str],
                                before_date: date, league: Optional[str] = None) -> Dict[str, Any]:
        """
        Build WPA lookup table using cluster of venues.
        
        Args:
            session: Database session
            cluster_venues: List of venues in cluster
            before_date: Only use matches before this date
            league: Optional league filter
            
        Returns:
            Aggregated WPA lookup table
        """
        # Aggregate outcomes from all venues in cluster
        all_outcomes = []
        
        for venue in cluster_venues:
            venue_outcomes = self.trainer.get_second_innings_outcomes(
                session, venue, before_date, league
            )
            all_outcomes.extend(venue_outcomes)
        
        if not all_outcomes:
            logger.warning(f"No chase data for cluster venues: {cluster_venues}")
            return {
                "venue": "CLUSTER",
                "cluster_venues": cluster_venues,
                "league": league,
                "build_date": before_date.isoformat(),
                "lookup_table": {},
                "sample_size": 0
            }
        
        # Build lookup table from aggregated outcomes
        return self._build_lookup_table_from_outcomes(
            all_outcomes, "CLUSTER", before_date, league, cluster_venues
        )
    
    def _build_league_wpa_table(self, session: Session, league: str,
                               before_date: date) -> Dict[str, Any]:
        """
        Build WPA lookup table using all venues from a league.
        
        Args:
            session: Database session
            league: League name
            before_date: Only use matches before this date
            
        Returns:
            League-level WPA lookup table
        """
        # Get sample of venues from league to avoid overwhelming query
        from sqlalchemy import text
        
        venues_query = text("""
            SELECT DISTINCT venue 
            FROM matches 
            WHERE competition = :league 
            AND date < :before_date 
            AND venue IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 10
        """)
        
        venues_result = session.execute(venues_query, {
            "league": league,
            "before_date": before_date
        }).fetchall()
        
        # Aggregate outcomes from league venues
        all_outcomes = []
        for venue_row in venues_result:
            venue = venue_row.venue
            venue_outcomes = self.trainer.get_second_innings_outcomes(
                session, venue, before_date, league
            )
            all_outcomes.extend(venue_outcomes)
        
        if not all_outcomes:
            logger.warning(f"No chase data for league: {league}")
            return {
                "venue": "LEAGUE",
                "league": league,
                "build_date": before_date.isoformat(),
                "lookup_table": {},
                "sample_size": 0
            }
        
        return self._build_lookup_table_from_outcomes(
            all_outcomes, "LEAGUE", before_date, league
        )
    
    def _build_global_wpa_table(self, session: Session, before_date: date) -> Dict[str, Any]:
        """
        Build global WPA lookup table using all available data.
        
        Args:
            session: Database session
            before_date: Only use matches before this date
            
        Returns:
            Global WPA lookup table
        """
        # Get sample of venues globally to avoid overwhelming query
        from sqlalchemy import text
        
        venues_query = text("""
            SELECT DISTINCT venue 
            FROM matches 
            WHERE date < :before_date 
            AND venue IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 15
        """)
        
        venues_result = session.execute(venues_query, {
            "before_date": before_date
        }).fetchall()
        
        # Aggregate outcomes from global venues
        all_outcomes = []
        for venue_row in venues_result:
            venue = venue_row.venue
            venue_outcomes = self.trainer.get_second_innings_outcomes(
                session, venue, before_date, None
            )
            all_outcomes.extend(venue_outcomes)
        
        if not all_outcomes:
            logger.warning("No global chase data available")
            return {
                "venue": "GLOBAL",
                "build_date": before_date.isoformat(),
                "lookup_table": {},
                "sample_size": 0
            }
        
        return self._build_lookup_table_from_outcomes(
            all_outcomes, "GLOBAL", before_date
        )
    
    def _build_lookup_table_from_outcomes(self, outcomes_data: List[Dict], 
                                         venue_type: str, before_date: date,
                                         league: Optional[str] = None, 
                                         cluster_venues: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Build WPA lookup table from aggregated outcomes data.
        
        Args:
            outcomes_data: List of chase outcomes
            venue_type: Type of venue (VENUE, CLUSTER, LEAGUE, GLOBAL)
            before_date: Build date
            league: Optional league
            cluster_venues: Optional cluster venues list
            
        Returns:
            WPA lookup table structure
        """
        if not outcomes_data:
            return {
                "venue": venue_type,
                "league": league,
                "build_date": before_date.isoformat(),
                "lookup_table": {},
                "sample_size": 0
            }
        
        # Build simplified lookup table structure
        lookup_table = {}
        
        # Get target score range from data
        targets = list(set(outcome["target"] for outcome in outcomes_data))
        if not targets:
            return {
                "venue": venue_type,
                "league": league,
                "build_date": before_date.isoformat(),
                "lookup_table": {},
                "sample_size": 0
            }
        
        # Build lookup table for common target ranges
        target_buckets = range(120, 220, 20)  # 120, 140, 160, 180, 200
        
        for target_bucket in target_buckets:
            lookup_table[target_bucket] = {}
            
            for over in range(0, self.trainer.max_overs, 2):  # Every 2 overs
                lookup_table[target_bucket][over] = {}
                
                for wickets in range(0, self.trainer.max_wickets, 2):  # Every 2 wickets
                    lookup_table[target_bucket][over][wickets] = {}
                    
                    # Calculate scores at intervals
                    max_score = min(target_bucket, (over + 1) * 12)  # ~12 runs per over
                    score_range = range(0, max_score + 30, 15)  # Every 15 runs
                    
                    for score in score_range:
                        win_prob = self.trainer.calculate_win_probability(
                            target_bucket, score, over, wickets, outcomes_data
                        )
                        lookup_table[target_bucket][over][wickets][score] = round(win_prob, 3)
        
        result = {
            "venue": venue_type,
            "league": league,
            "build_date": before_date.isoformat(),
            "lookup_table": lookup_table,
            "sample_size": len(outcomes_data)
        }
        
        if cluster_venues:
            result["cluster_venues"] = cluster_venues
            
        return result
