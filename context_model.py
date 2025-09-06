"""
Context Model for WPA Engine - DLS-style Resource Table Builder

This module creates historical par scores and resource curves for every venue,
for each innings phase, following chronological constraints.
"""

from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
from models import Match, Delivery
from venue_utils import VenueClusterManager, get_venue_hierarchy
from datetime import date
import logging
import json
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


class VenueResourceTableBuilder:
    """
    Builds venue-specific resource tables for WPA calculations.
    
    Creates resource curves similar to DLS method but venue-specific.
    """
    
    def __init__(self):
        self.venue_manager = VenueClusterManager()
        
        # Parameters for resource calculation
        self.max_overs = 20
        self.max_wickets = 10
        
        # Minimum data requirements
        self.min_matches_venue = 5
        self.min_matches_cluster = 15
        self.min_matches_league = 50
    
    def get_historical_match_states(self, session: Session, venue: str,
                                   innings: int, before_date: date,
                                   league: Optional[str] = None) -> List[Dict]:
        """
        Get all historical match states at a venue before a given date.
        
        Args:
            session: Database session
            venue: Venue name
            innings: Innings number (1 or 2)
            before_date: Only consider matches before this date
            league: Optional league filter
            
        Returns:
            List of match states with over, wickets, runs, final_score
        """
        query = text("""
            WITH match_states AS (
                SELECT 
                    d.match_id,
                    d.over,
                    COUNT(CASE WHEN d2.wicket_type IS NOT NULL THEN 1 END) as wickets,
                    SUM(d2.runs_off_bat + d2.extras) as runs_so_far,
                    final_scores.final_score
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                JOIN deliveries d2 ON d.match_id = d2.match_id 
                    AND d.innings = d2.innings 
                    AND (d2.over < d.over OR (d2.over = d.over AND d2.ball <= d.ball))
                JOIN (
                    SELECT 
                        match_id,
                        innings,
                        SUM(runs_off_bat + extras) as final_score
                    FROM deliveries
                    WHERE innings = :innings
                    GROUP BY match_id, innings
                ) final_scores ON d.match_id = final_scores.match_id 
                    AND d.innings = final_scores.innings
                WHERE d.innings = :innings
                    AND m.venue = :venue
                    AND m.date < :before_date
                    AND (:league IS NULL OR m.competition = :league)
                    AND d.over < :max_overs
                GROUP BY d.match_id, d.over, d.ball, final_scores.final_score
                HAVING COUNT(CASE WHEN d2.wicket_type IS NOT NULL THEN 1 END) < :max_wickets
            )
            SELECT 
                over,
                wickets,
                AVG(runs_so_far) as avg_runs_so_far,
                AVG(final_score) as avg_final_score,
                COUNT(*) as sample_size
            FROM match_states
            GROUP BY over, wickets
            ORDER BY over, wickets
        """)
        
        result = session.execute(query, {
            "venue": venue,
            "innings": innings,
            "before_date": before_date,
            "league": league,
            "max_overs": self.max_overs,
            "max_wickets": self.max_wickets
        }).fetchall()
        
        return [
            {
                "over": row.over,
                "wickets": row.wickets,
                "avg_runs_so_far": float(row.avg_runs_so_far),
                "avg_final_score": float(row.avg_final_score),
                "sample_size": row.sample_size
            }
            for row in result
        ]
    
    def calculate_resource_percentage(self, over: int, wickets: int,
                                    match_states: List[Dict]) -> float:
        """
        Calculate resource percentage remaining at a given (over, wickets) state.
        
        Args:
            over: Current over
            wickets: Current wickets lost
            match_states: Historical match states data
            
        Returns:
            Resource percentage remaining (0-100)
        """
        # Find matching state
        matching_states = [
            s for s in match_states 
            if s["over"] == over and s["wickets"] == wickets
        ]
        
        if not matching_states:
            # Interpolation logic for missing states
            return self._interpolate_resource(over, wickets, match_states)
        
        state = matching_states[0]
        if state["avg_final_score"] == 0:
            return 0.0
            
        # Resource = (Expected remaining runs / Expected final score) * 100
        remaining_runs = max(0, state["avg_final_score"] - state["avg_runs_so_far"])
        resource_percentage = (remaining_runs / state["avg_final_score"]) * 100
        
        return min(100.0, max(0.0, resource_percentage))
    
    def _interpolate_resource(self, over: int, wickets: int,
                            match_states: List[Dict]) -> float:
        """
        Interpolate resource percentage for missing (over, wickets) combinations.
        
        Args:
            over: Target over
            wickets: Target wickets
            match_states: Available match states
            
        Returns:
            Interpolated resource percentage
        """
        # Simple interpolation - find nearest neighbors
        nearby_states = []
        
        for state in match_states:
            distance = abs(state["over"] - over) + abs(state["wickets"] - wickets)
            if distance <= 2:  # Within 2 steps
                nearby_states.append((distance, state))
        
        if not nearby_states:
            # Default fallback based on overs and wickets
            overs_remaining = max(0, self.max_overs - over)
            wickets_remaining = max(1, self.max_wickets - wickets)
            
            # Simple heuristic: resource decreases with overs and wickets
            base_resource = (overs_remaining / self.max_overs) * 100
            wicket_factor = wickets_remaining / self.max_wickets
            
            return base_resource * wicket_factor
        
        # Weighted average based on distance
        total_weight = 0
        weighted_resource = 0
        
        for distance, state in nearby_states:
            weight = 1 / (distance + 1)  # Closer states get higher weight
            resource = self.calculate_resource_percentage(
                state["over"], state["wickets"], [state]
            )
            
            weighted_resource += weight * resource
            total_weight += weight
        
        return weighted_resource / total_weight if total_weight > 0 else 0.0
    
    def build_venue_resource_table(self, session: Session, venue: str,
                                  before_date: date, league: Optional[str] = None) -> Dict[str, Any]:
        """
        Build complete resource table for a venue.
        
        Args:
            session: Database session
            venue: Venue name
            before_date: Only use matches before this date
            league: Optional league filter
            
        Returns:
            Complete resource table with both innings
        """
        logger.info(f"Building resource table for venue: {venue} before {before_date}")
        
        resource_table = {
            "venue": venue,
            "league": league,
            "build_date": before_date.isoformat(),
            "innings": {}
        }
        
        # Build for both innings
        for innings in [1, 2]:
            logger.info(f"Processing innings {innings} for {venue}")
            
            # Get historical match states
            match_states = self.get_historical_match_states(
                session, venue, innings, before_date, league
            )
            
            if not match_states:
                logger.warning(f"No historical data for {venue} innings {innings}")
                resource_table["innings"][innings] = {}
                continue
            
            # Build resource grid
            innings_table = {}
            for over in range(0, self.max_overs):
                innings_table[over] = {}
                for wickets in range(0, self.max_wickets):
                    resource_pct = self.calculate_resource_percentage(
                        over, wickets, match_states
                    )
                    innings_table[over][wickets] = round(resource_pct, 2)
            
            resource_table["innings"][innings] = innings_table
            
        logger.info(f"Completed resource table for {venue}")
        return resource_table
    
    def build_par_score_distribution(self, session: Session, venue: str,
                                    before_date: date, league: Optional[str] = None) -> Dict[str, Any]:
        """
        Build par score distribution for a venue.
        
        Args:
            session: Database session
            venue: Venue name
            before_date: Only use matches before this date
            league: Optional league filter
            
        Returns:
            Par score distribution by innings and over
        """
        logger.info(f"Building par score distribution for venue: {venue}")
        
        query = text("""
            WITH match_totals AS (
                -- Get total runs for each match/innings
                SELECT 
                    d.match_id,
                    d.innings,
                    SUM(d.runs_off_bat + d.extras) as final_score
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE m.venue = :venue
                    AND m.date < :before_date
                    AND (:league IS NULL OR m.competition = :league)
                GROUP BY d.match_id, d.innings
            ),
            over_scores AS (
                -- Get cumulative runs at each over for each match
                SELECT 
                    d.match_id,
                    d.innings,
                    d.over,
                    SUM(d.runs_off_bat + d.extras) as runs_at_over
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE m.venue = :venue
                    AND m.date < :before_date
                    AND (:league IS NULL OR m.competition = :league)
                    AND d.over < :max_overs
                GROUP BY d.match_id, d.innings, d.over
            ),
            cumulative_scores AS (
                -- Calculate cumulative runs using window function
                SELECT 
                    match_id,
                    innings,
                    over,
                    SUM(runs_at_over) OVER (
                        PARTITION BY match_id, innings 
                        ORDER BY over 
                        ROWS UNBOUNDED PRECEDING
                    ) as cumulative_runs
                FROM over_scores
            )
            SELECT 
                innings,
                over,
                AVG(cumulative_runs) as avg_score,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY cumulative_runs) as q25,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cumulative_runs) as median,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY cumulative_runs) as q75,
                MIN(cumulative_runs) as min_score,
                MAX(cumulative_runs) as max_score,
                COUNT(*) as sample_size
            FROM cumulative_scores
            GROUP BY innings, over
            ORDER BY innings, over
        """)
        
        result = session.execute(query, {
            "venue": venue,
            "before_date": before_date,
            "league": league,
            "max_overs": self.max_overs
        }).fetchall()
        
        par_distribution = {
            "venue": venue,
            "league": league,
            "build_date": before_date.isoformat(),
            "innings": {}
        }
        
        # Organize by innings
        for row in result:
            innings = row.innings
            if innings not in par_distribution["innings"]:
                par_distribution["innings"][innings] = {}
            
            par_distribution["innings"][innings][row.over] = {
                "avg_score": float(row.avg_score),
                "q25": float(row.q25),
                "median": float(row.median),
                "q75": float(row.q75),
                "min_score": int(row.min_score),
                "max_score": int(row.max_score),
                "sample_size": row.sample_size
            }
        
        logger.info(f"Completed par score distribution for {venue}")
        return par_distribution
    
    def get_resource_table_with_fallback(self, session: Session, venue: str,
                                        before_date: date, league: Optional[str] = None) -> Dict[str, Any]:
        """
        Get resource table with fallback hierarchy: venue > cluster > league > global.
        
        Args:
            session: Database session
            venue: Primary venue
            before_date: Only use matches before this date
            league: League for league-level fallback
            
        Returns:
            Resource table with fallback info
        """
        logger.info(f"Getting resource table with fallback for {venue}")
        
        # Check venue hierarchy
        hierarchy = get_venue_hierarchy(session, venue, league, before_date)
        
        # Try venue-specific first
        if hierarchy["venue"] >= self.min_matches_venue:
            logger.info(f"Using venue-specific data for {venue} ({hierarchy['venue']} matches)")
            return {
                "source": "venue",
                "matches_used": hierarchy["venue"],
                "resource_table": self.build_venue_resource_table(session, venue, before_date, league)
            }
        
        # Try cluster fallback
        cluster = self.venue_manager.get_venue_cluster(venue)
        if cluster and hierarchy["cluster"] >= self.min_matches_cluster:
            logger.info(f"Using cluster fallback for {venue} ({cluster}, {hierarchy['cluster']} matches)")
            cluster_venues = self.venue_manager.venue_clusters[cluster]
            return {
                "source": "cluster",
                "cluster": cluster,
                "matches_used": hierarchy["cluster"],
                "resource_table": self._build_cluster_resource_table(session, cluster_venues, before_date, league)
            }
        
        # Try league fallback
        if league and hierarchy["league"] >= self.min_matches_league:
            logger.info(f"Using league fallback for {venue} ({league}, {hierarchy['league']} matches)")
            return {
                "source": "league",
                "league": league,
                "matches_used": hierarchy["league"],
                "resource_table": self._build_league_resource_table(session, league, before_date)
            }
        
        # Global fallback
        logger.info(f"Using global fallback for {venue} ({hierarchy['global']} matches)")
        return {
            "source": "global",
            "matches_used": hierarchy["global"],
            "resource_table": self._build_global_resource_table(session, before_date)
        }
    
    def _build_cluster_resource_table(self, session: Session, cluster_venues: List[str],
                                     before_date: date, league: Optional[str] = None) -> Dict[str, Any]:
        """
        Build resource table using cluster of venues.
        """
        # Aggregate data from all venues in cluster
        all_match_states = {1: [], 2: []}
        
        for venue in cluster_venues:
            for innings in [1, 2]:
                states = self.get_historical_match_states(session, venue, innings, before_date, league)
                all_match_states[innings].extend(states)
        
        # Build resource table from aggregated data
        resource_table = {
            "venue": "CLUSTER",
            "cluster_venues": cluster_venues,
            "league": league,
            "build_date": before_date.isoformat(),
            "innings": {}
        }
        
        for innings in [1, 2]:
            innings_table = {}
            for over in range(0, self.max_overs):
                innings_table[over] = {}
                for wickets in range(0, self.max_wickets):
                    resource_pct = self.calculate_resource_percentage(
                        over, wickets, all_match_states[innings]
                    )
                    innings_table[over][wickets] = round(resource_pct, 2)
            resource_table["innings"][innings] = innings_table
        
        return resource_table
    
    def _build_league_resource_table(self, session: Session, league: str,
                                    before_date: date) -> Dict[str, Any]:
        """
        Build resource table using all venues from a league.
        """
        # Get all match states from league - using simplified approach
        all_match_states = {1: [], 2: []}
        
        for innings in [1, 2]:
            # Get sample of venues from league first
            venues_query = text("""
                SELECT DISTINCT venue 
                FROM matches 
                WHERE competition = :league 
                AND date < :before_date 
                AND venue IS NOT NULL
                LIMIT 10
            """)
            
            venues_result = session.execute(venues_query, {
                "league": league,
                "before_date": before_date
            }).fetchall()
            
            # Aggregate data from these venues
            for venue_row in venues_result:
                venue = venue_row.venue
                states = self.get_historical_match_states(session, venue, innings, before_date, league)
                all_match_states[innings].extend(states)
        
        # Build resource table
        resource_table = {
            "venue": "LEAGUE",
            "league": league,
            "build_date": before_date.isoformat(),
            "innings": {}
        }
        
        for innings in [1, 2]:
            innings_table = {}
            for over in range(0, self.max_overs):
                innings_table[over] = {}
                for wickets in range(0, self.max_wickets):
                    resource_pct = self.calculate_resource_percentage(
                        over, wickets, all_match_states[innings]
                    )
                    innings_table[over][wickets] = round(resource_pct, 2)
            resource_table["innings"][innings] = innings_table
        
        return resource_table
    
    def _build_global_resource_table(self, session: Session, before_date: date) -> Dict[str, Any]:
        """
        Build global resource table using all available data.
        """
        # Get sample of venues globally to avoid overwhelming query
        all_match_states = {1: [], 2: []}
        
        for innings in [1, 2]:
            # Get sample of venues globally
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
            
            # Aggregate data from these venues
            for venue_row in venues_result:
                venue = venue_row.venue
                states = self.get_historical_match_states(session, venue, innings, before_date, None)
                all_match_states[innings].extend(states)
        
        # Build resource table
        resource_table = {
            "venue": "GLOBAL",
            "build_date": before_date.isoformat(),
            "innings": {}
        }
        
        for innings in [1, 2]:
            innings_table = {}
            for over in range(0, self.max_overs):
                innings_table[over] = {}
                for wickets in range(0, self.max_wickets):
                    resource_pct = self.calculate_resource_percentage(
                        over, wickets, all_match_states[innings]
                    )
                    innings_table[over][wickets] = round(resource_pct, 2)
            resource_table["innings"][innings] = innings_table
        
        return resource_table
