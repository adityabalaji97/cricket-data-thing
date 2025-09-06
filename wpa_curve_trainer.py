"""
WPA Curve Trainer for WPA Engine - Win Probability Lookup Table Builder

This module builds win probability lookup tables based on historical second innings
chase data, following chronological constraints to avoid data leakage.
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

logger = logging.getLogger(__name__)


class WPACurveTrainer:
    """
    Builds win probability lookup tables for WPA calculations.
    
    Focuses on second innings chase scenarios to create venue-specific
    win probability curves based on (score, over, wickets) states.
    """
    
    def __init__(self):
        self.venue_manager = VenueClusterManager()
        
        # Parameters for WPA calculation
        self.max_overs = 20
        self.max_wickets = 10
        self.score_buckets = 5  # Group scores in buckets for smoother curves
        
        # Minimum data requirements (same as context model)
        self.min_matches_venue = 5
        self.min_matches_cluster = 15
        self.min_matches_league = 50
        
    def get_second_innings_outcomes(self, session: Session, venue: str,
                                   before_date: date, league: Optional[str] = None) -> List[Dict]:
        """
        Get all second innings chase outcomes at a venue before a given date.
        
        Args:
            session: Database session
            venue: Venue name
            before_date: Only consider matches before this date
            league: Optional league filter
            
        Returns:
            List of chase outcomes with match states and final results
        """
        query = text("""
            WITH chase_matches AS (
                -- Get second innings target and result for each match
                SELECT 
                    m.id as match_id,
                    m.winner,
                    first_inn.team1_score as target,
                    second_inn.team2_score as chase_score,
                    second_inn.batting_team as chasing_team,
                    CASE 
                        WHEN m.winner = second_inn.batting_team THEN 1 
                        ELSE 0 
                    END as won_chase
                FROM matches m
                JOIN (
                    -- First innings total
                    SELECT 
                        match_id,
                        SUM(runs_off_bat + extras) as team1_score
                    FROM deliveries
                    WHERE innings = 1
                    GROUP BY match_id
                ) first_inn ON m.id = first_inn.match_id
                JOIN (
                    -- Second innings details
                    SELECT 
                        match_id,
                        batting_team,
                        SUM(runs_off_bat + extras) as team2_score
                    FROM deliveries
                    WHERE innings = 2
                    GROUP BY match_id, batting_team
                ) second_inn ON m.id = second_inn.match_id
                WHERE m.venue = :venue
                    AND m.date < :before_date
                    AND (:league IS NULL OR m.competition = :league)
                    AND m.winner IS NOT NULL  -- Only completed matches
            ),
            ball_by_ball_states AS (
                -- Get ball-by-ball state during second innings
                SELECT 
                    d.match_id,
                    d.over,
                    d.ball,
                    cm.target,
                    cm.won_chase,
                    -- Calculate runs scored so far (cumulative)
                    SUM(d2.runs_off_bat + d2.extras) OVER (
                        PARTITION BY d.match_id 
                        ORDER BY d2.over, d2.ball 
                        ROWS UNBOUNDED PRECEDING
                    ) as runs_so_far,
                    -- Calculate wickets lost so far  
                    COUNT(CASE WHEN d2.wicket_type IS NOT NULL THEN 1 END) OVER (
                        PARTITION BY d.match_id 
                        ORDER BY d2.over, d2.ball 
                        ROWS UNBOUNDED PRECEDING
                    ) as wickets_lost
                FROM deliveries d
                JOIN chase_matches cm ON d.match_id = cm.match_id
                JOIN deliveries d2 ON d.match_id = d2.match_id 
                    AND d.innings = d2.innings 
                    AND (d2.over < d.over OR (d2.over = d.over AND d2.ball <= d.ball))
                WHERE d.innings = 2
                    AND d.over < :max_overs
            )
            SELECT 
                over,
                runs_so_far,
                wickets_lost,
                target,
                won_chase,
                COUNT(*) as sample_size
            FROM ball_by_ball_states
            WHERE wickets_lost < :max_wickets
            GROUP BY over, runs_so_far, wickets_lost, target, won_chase
            ORDER BY over, runs_so_far, wickets_lost
        """)
        
        result = session.execute(query, {
            "venue": venue,
            "before_date": before_date,
            "league": league,
            "max_overs": self.max_overs,
            "max_wickets": self.max_wickets
        }).fetchall()
        
        return [
            {
                "over": row.over,
                "runs_so_far": row.runs_so_far,
                "wickets_lost": row.wickets_lost,
                "target": row.target,
                "won_chase": bool(row.won_chase),
                "sample_size": row.sample_size
            }
            for row in result
        ]
    
    def calculate_win_probability(self, target_score: int, current_score: int,
                                 over: int, wickets: int, 
                                 outcomes_data: List[Dict]) -> float:
        """
        Calculate win probability for a given match state.
        
        Args:
            target_score: Target to chase
            current_score: Current score
            over: Current over
            wickets: Wickets lost
            outcomes_data: Historical outcomes data
            
        Returns:
            Win probability (0.0 to 1.0)
        """
        # Define tolerance for matching similar states
        score_tolerance = max(10, target_score * 0.05)  # 5% of target or min 10 runs
        over_tolerance = 1
        wicket_tolerance = 1
        
        # Find similar match states
        similar_states = []
        for outcome in outcomes_data:
            # Check if target is similar
            target_diff = abs(outcome["target"] - target_score)
            if target_diff > score_tolerance:
                continue
                
            # Check if current state is similar
            score_diff = abs(outcome["runs_so_far"] - current_score)
            over_diff = abs(outcome["over"] - over)
            wicket_diff = abs(outcome["wickets_lost"] - wickets)
            
            if (score_diff <= score_tolerance and 
                over_diff <= over_tolerance and 
                wicket_diff <= wicket_tolerance):
                similar_states.append(outcome)
        
        if not similar_states:
            # Fallback to simple heuristic
            return self._calculate_fallback_probability(
                target_score, current_score, over, wickets
            )
        
        # Calculate weighted win probability
        total_weight = 0
        weighted_wins = 0
        
        for state in similar_states:
            # Weight by sample size and similarity
            score_sim = 1 / (1 + abs(state["runs_so_far"] - current_score))
            over_sim = 1 / (1 + abs(state["over"] - over))
            wicket_sim = 1 / (1 + abs(state["wickets_lost"] - wickets))
            
            weight = state["sample_size"] * score_sim * over_sim * wicket_sim
            
            if state["won_chase"]:
                weighted_wins += weight
            total_weight += weight
        
        return weighted_wins / total_weight if total_weight > 0 else 0.5
    
    def _calculate_fallback_probability(self, target_score: int, current_score: int,
                                       over: int, wickets: int) -> float:
        """
        Calculate fallback win probability using simple heuristics.
        
        Args:
            target_score: Target to chase
            current_score: Current score
            over: Current over
            wickets: Wickets lost
            
        Returns:
            Estimated win probability
        """
        required_runs = target_score - current_score
        overs_remaining = self.max_overs - over
        wickets_remaining = self.max_wickets - wickets
        
        if required_runs <= 0:
            return 1.0
        
        if overs_remaining <= 0 or wickets_remaining <= 0:
            return 0.0
        
        # Required run rate
        required_rr = required_runs / overs_remaining if overs_remaining > 0 else float('inf')
        
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
        wicket_factor = wickets_remaining / self.max_wickets
        
        return min(1.0, max(0.0, base_prob * wicket_factor))
