"""
Precomputed Models for Cricket Analytics Platform

SQLAlchemy ORM models for precomputed tables following the 
PRECOMPUTATION_ENGINE_PRD.md specifications.
"""

from sqlalchemy import Column, Integer, String, Date, DECIMAL, Boolean, Text, TIMESTAMP, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class WPAOutcome(Base):
    """
    Pre-computed chase outcome aggregations for instant WPA calculations.
    
    Stores win probability data bucketed by venue, target, over, wickets, and score ranges.
    """
    __tablename__ = 'wpa_outcomes'
    
    id = Column(Integer, primary_key=True)
    venue = Column(String(255), nullable=False)
    league = Column(String(100))
    target_bucket = Column(Integer, nullable=False)  # Grouped in 10-run buckets
    over_bucket = Column(Integer, nullable=False)    # 0, 2, 4, 6, 8, 10, 12, 14, 16, 18
    wickets_lost = Column(Integer, nullable=False)   # 0-9 wickets
    runs_range_min = Column(Integer, nullable=False) # Score bucket start
    runs_range_max = Column(Integer, nullable=False) # Score bucket end
    total_outcomes = Column(Integer, nullable=False)
    successful_chases = Column(Integer, nullable=False)
    win_probability = Column(DECIMAL(5,3), nullable=False)  # 0.000 to 1.000
    sample_size = Column(Integer, nullable=False)
    computed_date = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    data_through_date = Column(Date, nullable=False)
    
    # Define indexes at class level
    __table_args__ = (
        Index('idx_wpa_lookup', 'venue', 'target_bucket', 'over_bucket', 'wickets_lost'),
        Index('idx_wpa_league', 'league', 'target_bucket', 'over_bucket', 'wickets_lost'),
        Index('idx_wpa_computed_date', 'computed_date'),
        Index('idx_wpa_data_through_date', 'data_through_date'),
    )
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'venue': self.venue,
            'league': self.league,
            'target_bucket': self.target_bucket,
            'over_bucket': self.over_bucket,
            'wickets_lost': self.wickets_lost,
            'runs_range_min': self.runs_range_min,
            'runs_range_max': self.runs_range_max,
            'total_outcomes': self.total_outcomes,
            'successful_chases': self.successful_chases,
            'win_probability': float(self.win_probability),
            'sample_size': self.sample_size,
            'computed_date': self.computed_date.isoformat() if self.computed_date else None,
            'data_through_date': self.data_through_date.isoformat() if self.data_through_date else None
        }


class VenueResource(Base):
    """
    Pre-computed DLS-style resource percentages for venue context analysis.
    
    Stores resource percentages for each (venue, innings, over, wickets) combination.
    """
    __tablename__ = 'venue_resources'
    
    id = Column(Integer, primary_key=True)
    venue = Column(String(255), nullable=False)
    league = Column(String(100))
    innings = Column(Integer, nullable=False)        # 1 or 2
    over_num = Column(Integer, nullable=False)       # 0-19
    wickets_lost = Column(Integer, nullable=False)   # 0-9
    resource_percentage = Column(DECIMAL(5,2), nullable=False)  # 0.00 to 100.00
    avg_runs_at_state = Column(DECIMAL(6,2))
    avg_final_score = Column(DECIMAL(6,2))
    sample_size = Column(Integer, nullable=False)
    computed_date = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    data_through_date = Column(Date, nullable=False)
    
    __table_args__ = (
        Index('idx_venue_resources', 'venue', 'innings', 'over_num', 'wickets_lost'),
        Index('idx_venue_resources_league', 'league', 'innings', 'over_num', 'wickets_lost'),
        Index('idx_venue_resources_computed', 'computed_date'),
    )
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'venue': self.venue,
            'league': self.league,
            'innings': self.innings,
            'over_num': self.over_num,
            'wickets_lost': self.wickets_lost,
            'resource_percentage': float(self.resource_percentage),
            'avg_runs_at_state': float(self.avg_runs_at_state) if self.avg_runs_at_state else None,
            'avg_final_score': float(self.avg_final_score) if self.avg_final_score else None,
            'sample_size': self.sample_size,
            'computed_date': self.computed_date.isoformat() if self.computed_date else None,
            'data_through_date': self.data_through_date.isoformat() if self.data_through_date else None
        }


class PlayerBaseline(Base):
    """
    Pre-computed player performance metrics for RAR and impact calculations.
    
    Stores baseline performance stats for players across different venue types and phases.
    """
    __tablename__ = 'player_baselines'
    
    id = Column(Integer, primary_key=True)
    player_name = Column(String(255), nullable=False)
    venue_type = Column(String(50), nullable=False)  # 'venue_specific', 'cluster', 'league', 'global'
    venue_identifier = Column(String(255))           # Venue name or cluster name
    league = Column(String(100))
    phase = Column(String(20), nullable=False)       # 'powerplay', 'middle', 'death', 'overall'
    role = Column(String(20), nullable=False)        # 'batting', 'bowling'
    
    # Batting metrics
    avg_runs = Column(DECIMAL(5,2))
    avg_strike_rate = Column(DECIMAL(5,2))
    avg_balls_faced = Column(DECIMAL(5,2))
    boundary_percentage = Column(DECIMAL(4,2))
    dot_percentage = Column(DECIMAL(4,2))
    
    # Bowling metrics  
    avg_economy = Column(DECIMAL(4,2))
    avg_wickets = Column(DECIMAL(4,2))
    dot_ball_percentage = Column(DECIMAL(4,2))
    avg_overs = Column(DECIMAL(3,1))
    strike_rate = Column(DECIMAL(5,2))
    average = Column(DECIMAL(5,2))
    
    matches_played = Column(Integer, nullable=False)
    computed_date = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    data_through_date = Column(Date, nullable=False)
    
    __table_args__ = (
        Index('idx_player_baselines', 'player_name', 'venue_type', 'phase', 'role'),
        Index('idx_player_baselines_venue', 'venue_identifier', 'phase', 'role'),
        Index('idx_player_baselines_league', 'league', 'phase', 'role'),
        Index('idx_player_baselines_computed', 'computed_date'),
    )
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'player_name': self.player_name,
            'venue_type': self.venue_type,
            'venue_identifier': self.venue_identifier,
            'league': self.league,
            'phase': self.phase,
            'role': self.role,
            'avg_runs': float(self.avg_runs) if self.avg_runs else None,
            'avg_strike_rate': float(self.avg_strike_rate) if self.avg_strike_rate else None,
            'avg_balls_faced': float(self.avg_balls_faced) if self.avg_balls_faced else None,
            'boundary_percentage': float(self.boundary_percentage) if self.boundary_percentage else None,
            'dot_percentage': float(self.dot_percentage) if self.dot_percentage else None,
            'avg_economy': float(self.avg_economy) if self.avg_economy else None,
            'avg_wickets': float(self.avg_wickets) if self.avg_wickets else None,
            'dot_ball_percentage': float(self.dot_ball_percentage) if self.dot_ball_percentage else None,
            'avg_overs': float(self.avg_overs) if self.avg_overs else None,
            'strike_rate': float(self.strike_rate) if self.strike_rate else None,
            'average': float(self.average) if self.average else None,
            'matches_played': self.matches_played,
            'computed_date': self.computed_date.isoformat() if self.computed_date else None,
            'data_through_date': self.data_through_date.isoformat() if self.data_through_date else None
        }


class TeamPhaseStat(Base):
    """
    Pre-computed team-level performance for contextual comparisons.
    
    Stores team performance statistics broken down by venue type, phase, and innings.
    """
    __tablename__ = 'team_phase_stats'
    
    id = Column(Integer, primary_key=True)
    team = Column(String(255), nullable=False)
    venue_type = Column(String(50), nullable=False)  # 'venue_specific', 'cluster', 'league', 'global'
    venue_identifier = Column(String(255))           # Venue name or cluster name
    league = Column(String(100))
    phase = Column(String(20), nullable=False)       # 'powerplay', 'middle', 'death', 'overall'
    innings = Column(Integer, nullable=False)        # 1 or 2
    
    avg_runs = Column(DECIMAL(6,2), nullable=False)
    avg_wickets = Column(DECIMAL(4,2), nullable=False)
    avg_run_rate = Column(DECIMAL(4,2), nullable=False)
    avg_balls_faced = Column(Integer)
    boundary_rate = Column(DECIMAL(4,2))
    dot_rate = Column(DECIMAL(4,2))
    
    matches_played = Column(Integer, nullable=False)
    computed_date = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    data_through_date = Column(Date, nullable=False)
    
    __table_args__ = (
        Index('idx_team_stats', 'team', 'venue_type', 'phase', 'innings'),
        Index('idx_team_stats_venue', 'venue_identifier', 'phase', 'innings'),
        Index('idx_team_stats_league', 'league', 'phase', 'innings'),
        Index('idx_team_stats_computed', 'computed_date'),
    )
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'team': self.team,
            'venue_type': self.venue_type,
            'venue_identifier': self.venue_identifier,
            'league': self.league,
            'phase': self.phase,
            'innings': self.innings,
            'avg_runs': float(self.avg_runs),
            'avg_wickets': float(self.avg_wickets),
            'avg_run_rate': float(self.avg_run_rate),
            'avg_balls_faced': self.avg_balls_faced,
            'boundary_rate': float(self.boundary_rate) if self.boundary_rate else None,
            'dot_rate': float(self.dot_rate) if self.dot_rate else None,
            'matches_played': self.matches_played,
            'computed_date': self.computed_date.isoformat() if self.computed_date else None,
            'data_through_date': self.data_through_date.isoformat() if self.data_through_date else None
        }


class ComputationRun(Base):
    """
    Track computation status, dependencies, and data lineage.
    
    Stores metadata about batch computation processes for monitoring and debugging.
    """
    __tablename__ = 'computation_runs'
    
    id = Column(Integer, primary_key=True)
    table_name = Column(String(100), nullable=False)
    computation_type = Column(String(50), nullable=False)  # 'full_rebuild', 'incremental', 'backfill'
    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP)
    status = Column(String(20), nullable=False)           # 'running', 'completed', 'failed'
    records_processed = Column(Integer)
    records_inserted = Column(Integer)
    records_updated = Column(Integer)
    data_through_date = Column(Date, nullable=False)
    error_message = Column(Text)
    execution_details = Column(JSONB)                     # Store additional metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_computation_status', 'table_name', 'status', 'start_time'),
        Index('idx_computation_date', 'data_through_date'),
        Index('idx_computation_type', 'computation_type', 'status'),
    )
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'table_name': self.table_name,
            'computation_type': self.computation_type,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'records_processed': self.records_processed,
            'records_inserted': self.records_inserted,
            'records_updated': self.records_updated,
            'data_through_date': self.data_through_date.isoformat() if self.data_through_date else None,
            'error_message': self.error_message,
            'execution_details': self.execution_details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class VenueCluster(Base):
    """
    Store venue clustering configuration for consistent fallback behavior.
    
    Maintains the venue cluster mappings used in fallback hierarchy.
    """
    __tablename__ = 'venue_clusters'
    
    id = Column(Integer, primary_key=True)
    cluster_name = Column(String(100), nullable=False)
    venue_name = Column(String(255), nullable=False)
    cluster_type = Column(String(50), nullable=False)     # 'high_scoring', 'balanced', 'bowling_friendly', 'international'
    priority = Column(Integer, nullable=False, default=1) # Priority within cluster
    created_date = Column(TIMESTAMP, default=datetime.utcnow)
    updated_date = Column(TIMESTAMP, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_venue_clusters_name', 'venue_name'),
        Index('idx_venue_clusters_cluster', 'cluster_name', 'cluster_type'),
    )
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'cluster_name': self.cluster_name,
            'venue_name': self.venue_name,
            'cluster_type': self.cluster_type,
            'priority': self.priority,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None
        }


class DataQualityCheck(Base):
    """
    Store data quality validation results.
    
    Tracks data quality metrics and validation results for monitoring.
    """
    __tablename__ = 'data_quality_checks'
    
    id = Column(Integer, primary_key=True)
    table_name = Column(String(100), nullable=False)
    check_name = Column(String(100), nullable=False)
    check_type = Column(String(50), nullable=False)      # 'completeness', 'consistency', 'accuracy', 'validity'
    status = Column(String(20), nullable=False)          # 'passed', 'failed', 'warning'
    check_value = Column(DECIMAL(10,3))
    threshold_value = Column(DECIMAL(10,3))
    details = Column(JSONB)
    computed_date = Column(TIMESTAMP, nullable=False)
    data_through_date = Column(Date, nullable=False)
    
    __table_args__ = (
        Index('idx_data_quality_table', 'table_name', 'check_name', 'status'),
        Index('idx_data_quality_date', 'computed_date'),
    )
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'table_name': self.table_name,
            'check_name': self.check_name,
            'check_type': self.check_type,
            'status': self.status,
            'check_value': float(self.check_value) if self.check_value else None,
            'threshold_value': float(self.threshold_value) if self.threshold_value else None,
            'details': self.details,
            'computed_date': self.computed_date.isoformat() if self.computed_date else None,
            'data_through_date': self.data_through_date.isoformat() if self.data_through_date else None
        }
