"""
Batch Processing Pipeline for Precomputation Engine

Core framework for weekly batch processing that transforms expensive 
real-time calculations into fast database lookups.
"""

from typing import Dict, List, Optional, Any, Callable
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date, datetime
from precomputed_models import ComputationRun, TeamPhaseStat, PlayerBaseline
from database import get_session
import logging

logger = logging.getLogger(__name__)


class PrecomputationPipeline:
    """
    Weekly batch processing pipeline for pre-computing analytics tables.
    
    Executes in dependency order to ensure data consistency.
    """
    
    def __init__(self):
        self.session: Optional[Session] = None
        self.pipeline_start_time = None
        
        # Define processing order based on dependencies
        self.pipeline_steps = [
            ("team_phase_stats", self._rebuild_team_stats),
            ("player_baselines", self._rebuild_player_baselines), 
            ("venue_resources", self._rebuild_venue_resources),
            ("wpa_outcomes", self._rebuild_wpa_outcomes)
        ]
    
    def execute_weekly_rebuild(self, through_date: date, session: Session = None) -> Dict[str, Any]:
        """
        Full weekly rebuild of all pre-computed tables.
        
        Args:
            through_date: Process all matches up to this date (exclusive)
            session: Optional database session
            
        Returns:
            Dictionary with execution results and statistics
        """
        logger.info(f"Starting weekly precomputation rebuild through {through_date}")
        
        # Setup session
        if session:
            self.session = session
        else:
            session_gen = get_session()
            self.session = next(session_gen)
        
        self.pipeline_start_time = datetime.utcnow()
        execution_results = {
            "start_time": self.pipeline_start_time.isoformat(),
            "through_date": through_date.isoformat(),
            "steps": {},
            "total_records_processed": 0,
            "total_duration_seconds": 0,
            "status": "running"
        }
        
        try:
            # Execute each step in order
            for table_name, rebuild_func in self.pipeline_steps:
                logger.info(f"Processing step: {table_name}")
                step_result = self._execute_with_monitoring(
                    table_name, rebuild_func, through_date
                )
                execution_results["steps"][table_name] = step_result
                execution_results["total_records_processed"] += step_result.get("records_processed", 0)
            
            # Calculate total duration
            end_time = datetime.utcnow()
            execution_results["end_time"] = end_time.isoformat()
            execution_results["total_duration_seconds"] = (end_time - self.pipeline_start_time).total_seconds()
            execution_results["status"] = "completed"
            
            logger.info(f"Weekly rebuild completed in {execution_results['total_duration_seconds']:.2f} seconds")
            
            return execution_results
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {str(e)}")
            execution_results["status"] = "failed"
            execution_results["error"] = str(e)
            return execution_results
        
        finally:
            if not session and self.session:
                self.session.close()
    
    def _execute_with_monitoring(self, table_name: str, rebuild_func: Callable, 
                                through_date: date) -> Dict[str, Any]:
        """Execute a rebuild function with monitoring and error handling."""
        step_start_time = datetime.utcnow()
        
        # Create computation run record
        run_record = ComputationRun(
            table_name=table_name,
            computation_type="full_rebuild",
            start_time=step_start_time,
            status="running",
            data_through_date=through_date
        )
        self.session.add(run_record)
        self.session.commit()
        
        step_result = {
            "start_time": step_start_time.isoformat(),
            "table_name": table_name,
            "status": "running",
            "records_processed": 0,
            "records_inserted": 0,
            "computation_run_id": run_record.id
        }
        
        try:
            # Execute the rebuild function
            result = rebuild_func(through_date)
            
            # Update step result
            step_result.update(result)
            step_result["status"] = "completed"
            
            # Update computation run record
            run_record.end_time = datetime.utcnow()
            run_record.status = "completed"
            run_record.records_processed = result.get("records_processed", 0)
            run_record.records_inserted = result.get("records_inserted", 0)
            run_record.execution_details = result
            
            duration = (run_record.end_time - step_start_time).total_seconds()
            step_result["duration_seconds"] = duration
            
            logger.info(f"Completed {table_name}: {result.get('records_inserted', 0)} records in {duration:.2f}s")
            
        except Exception as e:
            logger.error(f"Error rebuilding {table_name}: {str(e)}")
            
            # Update records with error
            run_record.end_time = datetime.utcnow()
            run_record.status = "failed"
            run_record.error_message = str(e)
            
            step_result["status"] = "failed"
            step_result["error"] = str(e)
        
        finally:
            self.session.commit()
        
        return step_result
    
    # Placeholder methods - we'll implement these one by one
    def _rebuild_team_stats(self, through_date: date) -> Dict[str, Any]:
        """Rebuild team phase statistics table."""
        logger.info("Rebuilding team phase statistics table...")
        
        # Clear existing data
        self.session.execute(text("TRUNCATE TABLE team_phase_stats"))
        self.session.commit()

        team_query = text("""
            SELECT 
                team_stats.batting_team as team,
                team_stats.venue as venue,
                team_stats.phase as phase,
                team_stats.innings as innings,
                AVG(team_stats.team_runs) as avg_runs,
                AVG(team_stats.team_wickets) as avg_wickets,
                (SUM(team_stats.team_runs) * 6.0 / NULLIF(SUM(team_stats.team_balls_faced), 0)) as avg_run_rate,
                AVG(team_stats.team_balls_faced) as avg_balls_faced,
                (SUM(team_stats.team_fours + team_stats.team_sixes) * 100.0 / NULLIF(SUM(team_stats.team_balls_faced), 0)) as boundary_rate,
                (SUM(team_stats.team_dots) * 100.0 / NULLIF(SUM(team_stats.team_balls_faced), 0)) as dot_rate,
                COUNT(DISTINCT team_stats.match_id) as matches_played
            FROM (
                SELECT 
                    bs.batting_team,
                    m.venue,
                    'powerplay' as phase,
                    bs.innings,
                    SUM(bs.pp_runs) as team_runs,
                    SUM(bs.pp_wickets) as team_wickets,
                    SUM(bs.pp_balls) as team_balls_faced,
                    SUM(bs.pp_boundaries) as team_fours,
                    0 as team_sixes,
                    SUM(bs.pp_dots) as team_dots,
                    bs.match_id
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE m.date < :through_date AND bs.pp_balls > 0
                GROUP BY bs.batting_team, m.venue, bs.innings, bs.match_id
                UNION ALL
                SELECT 
                    bs.batting_team,
                    m.venue,
                    'middle' as phase,
                    bs.innings,
                    SUM(bs.middle_runs) as team_runs,
                    SUM(bs.middle_wickets) as team_wickets,
                    SUM(bs.middle_balls) as team_balls_faced,
                    SUM(bs.middle_boundaries) as team_fours,
                    0 as team_sixes,
                    SUM(bs.middle_dots) as team_dots,
                    bs.match_id
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE m.date < :through_date AND bs.middle_balls > 0
                GROUP BY bs.batting_team, m.venue, bs.innings, bs.match_id
                UNION ALL
                SELECT 
                    bs.batting_team,
                    m.venue,
                    'death' as phase,
                    bs.innings,
                    SUM(bs.death_runs) as team_runs,
                    SUM(bs.death_wickets) as team_wickets,
                    SUM(bs.death_balls) as team_balls_faced,
                    SUM(bs.death_boundaries) as team_fours,
                    0 as team_sixes,
                    SUM(bs.death_dots) as team_dots,
                    bs.match_id
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE m.date < :through_date AND bs.death_balls > 0
                GROUP BY bs.batting_team, m.venue, bs.innings, bs.match_id
                UNION ALL
                SELECT 
                    bs.batting_team,
                    m.venue,
                    'overall' as phase,
                    bs.innings,
                    SUM(bs.runs) as team_runs,
                    SUM(bs.wickets) as team_wickets,
                    SUM(bs.balls_faced) as team_balls_faced,
                    SUM(bs.fours) as team_fours,
                    SUM(bs.sixes) as team_sixes,
                    SUM(bs.dots) as team_dots,
                    bs.match_id
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE m.date < :through_date AND bs.balls_faced > 0
                GROUP BY bs.batting_team, m.venue, bs.innings, bs.match_id
            ) as team_stats
            GROUP BY team_stats.batting_team, team_stats.venue, team_stats.phase, team_stats.innings
            HAVING COUNT(DISTINCT team_stats.match_id) >= 5
        """)

        teams = self.session.execute(team_query, {"through_date": through_date}).fetchall()
        logger.info(f"Processing {len(teams)} teams")

        # Prepare team records for bulk insert
        team_records = []
        for team in teams:
            team_records.append({
                'team': team.team,
                'venue_type': 'global',  # Ignoring venue_type for now
                'venue_identifier': team.venue,
                'league': None,  # Assuming league is not available
                'phase': team.phase,
                'innings': team.innings,
                'avg_runs': round(float(team.avg_runs or 0), 2),
                'avg_wickets': round(float(team.avg_wickets or 0), 2),
                'avg_run_rate': round(float(team.avg_run_rate or 0), 2),
                'avg_balls_faced': int(team.avg_balls_faced or 0),
                'boundary_rate': round(float(team.boundary_rate or 0), 2),
                'dot_rate': round(float(team.dot_rate or 0), 2),
                'matches_played': team.matches_played,
                'computed_date': datetime.utcnow(),
                'data_through_date': through_date
            })

        records_inserted = 0
        if team_records:
            self.session.bulk_insert_mappings(TeamPhaseStat, team_records)
            records_inserted = len(team_records)
            self.session.commit()

        logger.info(f"Team stats rebuild completed: {records_inserted} records inserted")
        
        return {
            "records_processed": len(teams),
            "records_inserted": records_inserted,
            "teams_processed": len(teams)
        }
    
    def _rebuild_player_baselines(self, through_date: date) -> Dict[str, Any]:
        """Rebuild player baselines table with performance metrics for RAR calculations."""
        logger.info("Rebuilding player baselines table...")
    
        # Clear existing data
        self.session.execute(text("TRUNCATE TABLE player_baselines"))
        self.session.commit()
        
        records_inserted = 0
        
        # Process batting baselines with phase-specific data
        batting_query = text("""
            SELECT 
                player_stats.striker as player_name,
                player_stats.venue as venue,
                player_stats.phase as phase,
                AVG(player_stats.runs) as avg_runs,
                AVG(player_stats.strike_rate) as avg_strike_rate,
                AVG(player_stats.balls_faced) as avg_balls_faced,
                AVG(player_stats.boundary_percentage) as boundary_percentage,
                AVG(player_stats.dot_percentage) as dot_percentage,
                COUNT(DISTINCT player_stats.match_id) as matches_played
            FROM (
                SELECT 
                    bs.striker,
                    m.venue,
                    'powerplay' as phase,
                    bs.pp_runs as runs,
                    CASE WHEN bs.pp_balls > 0 THEN (bs.pp_runs * 100.0 / bs.pp_balls) ELSE 0 END as strike_rate,
                    bs.pp_balls as balls_faced,
                    CASE WHEN bs.pp_balls > 0 THEN LEAST(100.0, bs.pp_boundaries * 100.0 / bs.pp_balls) ELSE 0 END as boundary_percentage,
                    CASE WHEN bs.pp_balls > 0 THEN LEAST(100.0, bs.pp_dots * 100.0 / bs.pp_balls) ELSE 0 END as dot_percentage,
                    bs.match_id
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE m.date < :through_date AND bs.pp_balls > 0
                UNION ALL
                SELECT 
                    bs.striker,
                    m.venue,
                    'middle' as phase,
                    bs.middle_runs as runs,
                    CASE WHEN bs.middle_balls > 0 THEN (bs.middle_runs * 100.0 / bs.middle_balls) ELSE 0 END as strike_rate,
                    bs.middle_balls as balls_faced,
                    CASE WHEN bs.middle_balls > 0 THEN LEAST(100.0, bs.middle_boundaries * 100.0 / bs.middle_balls) ELSE 0 END as boundary_percentage,
                    CASE WHEN bs.middle_balls > 0 THEN LEAST(100.0, bs.middle_dots * 100.0 / bs.middle_balls) ELSE 0 END as dot_percentage,
                    bs.match_id
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE m.date < :through_date AND bs.middle_balls > 0
                UNION ALL
                SELECT 
                    bs.striker,
                    m.venue,
                    'death' as phase,
                    bs.death_runs as runs,
                    CASE WHEN bs.death_balls > 0 THEN (bs.death_runs * 100.0 / bs.death_balls) ELSE 0 END as strike_rate,
                    bs.death_balls as balls_faced,
                    CASE WHEN bs.death_balls > 0 THEN LEAST(100.0, bs.death_boundaries * 100.0 / bs.death_balls) ELSE 0 END as boundary_percentage,
                    CASE WHEN bs.death_balls > 0 THEN LEAST(100.0, bs.death_dots * 100.0 / bs.death_balls) ELSE 0 END as dot_percentage,
                    bs.match_id
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE m.date < :through_date AND bs.death_balls > 0
                UNION ALL
                SELECT 
                    bs.striker,
                    m.venue,
                    'overall' as phase,
                    bs.runs as runs,
                    CASE WHEN bs.balls_faced > 0 THEN (bs.runs * 100.0 / bs.balls_faced) ELSE 0 END as strike_rate,
                    bs.balls_faced as balls_faced,
                    CASE WHEN bs.balls_faced > 0 THEN LEAST(100.0, (bs.fours + bs.sixes) * 100.0 / bs.balls_faced) ELSE 0 END as boundary_percentage,
                    CASE WHEN bs.balls_faced > 0 THEN LEAST(100.0, bs.dots * 100.0 / bs.balls_faced) ELSE 0 END as dot_percentage,
                    bs.match_id
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE m.date < :through_date AND bs.balls_faced > 0
            ) as player_stats
            GROUP BY player_stats.striker, player_stats.venue, player_stats.phase
            HAVING COUNT(DISTINCT player_stats.match_id) >= 5
        """)
        
        batting_players = self.session.execute(batting_query, {"through_date": through_date}).fetchall()
        logger.info(f"Processing {len(batting_players)} batting player/venue/phase combinations")
        
        # Prepare batting records
        batting_records = []
        for player in batting_players:
            batting_records.append({
                'player_name': player.player_name,
                'venue_type': 'venue_specific',
                'venue_identifier': player.venue,
                'league': None,
                'phase': player.phase,
                'role': 'batting',
                'avg_runs': round(float(player.avg_runs or 0), 2),
                'avg_strike_rate': round(float(player.avg_strike_rate or 0), 2),
                'avg_balls_faced': round(float(player.avg_balls_faced or 0), 2),
                'boundary_percentage': round(float(player.boundary_percentage or 0), 2),
                'dot_percentage': round(float(player.dot_percentage or 0), 2),
                'matches_played': player.matches_played,
                'computed_date': datetime.utcnow(),
                'data_through_date': through_date
            })
        
        if batting_records:
            self.session.bulk_insert_mappings(PlayerBaseline, batting_records)
            records_inserted += len(batting_records)
            self.session.commit()
        
        # Process bowling baselines with phase-specific data
        bowling_query = text("""
            SELECT 
                player_stats.bowler as player_name,
                player_stats.venue as venue,
                player_stats.phase as phase,
                AVG(player_stats.economy) as avg_economy,
                AVG(player_stats.wickets) as avg_wickets,
                AVG(player_stats.dot_ball_percentage) as dot_ball_percentage,
                AVG(player_stats.overs) as avg_overs,
                AVG(player_stats.strike_rate) as strike_rate,
                AVG(player_stats.average) as average,
                COUNT(DISTINCT player_stats.match_id) as matches_played
            FROM (
                SELECT 
                    bw.bowler,
                    m.venue,
                    'powerplay' as phase,
                    bw.pp_economy as economy,
                    bw.pp_wickets as wickets,
                    CASE WHEN bw.pp_overs > 0 THEN (bw.pp_dots * 100.0 / (bw.pp_overs * 6)) ELSE 0 END as dot_ball_percentage,
                    bw.pp_overs as overs,
                    CASE WHEN bw.pp_wickets > 0 THEN ((bw.pp_overs * 6) / bw.pp_wickets) ELSE 0 END as strike_rate,
                    CASE WHEN bw.pp_wickets > 0 THEN (bw.pp_runs / bw.pp_wickets) ELSE 0 END as average,
                    bw.match_id
                FROM bowling_stats bw
                JOIN matches m ON bw.match_id = m.id
                WHERE m.date < :through_date AND bw.pp_overs > 0
                UNION ALL
                SELECT 
                    bw.bowler,
                    m.venue,
                    'middle' as phase,
                    bw.middle_economy as economy,
                    bw.middle_wickets as wickets,
                    CASE WHEN bw.middle_overs > 0 THEN (bw.middle_dots * 100.0 / (bw.middle_overs * 6)) ELSE 0 END as dot_ball_percentage,
                    bw.middle_overs as overs,
                    CASE WHEN bw.middle_wickets > 0 THEN ((bw.middle_overs * 6) / bw.middle_wickets) ELSE 0 END as strike_rate,
                    CASE WHEN bw.middle_wickets > 0 THEN (bw.middle_runs / bw.middle_wickets) ELSE 0 END as average,
                    bw.match_id
                FROM bowling_stats bw
                JOIN matches m ON bw.match_id = m.id
                WHERE m.date < :through_date AND bw.middle_overs > 0
                UNION ALL
                SELECT 
                    bw.bowler,
                    m.venue,
                    'death' as phase,
                    bw.death_economy as economy,
                    bw.death_wickets as wickets,
                    CASE WHEN bw.death_overs > 0 THEN (bw.death_dots * 100.0 / (bw.death_overs * 6)) ELSE 0 END as dot_ball_percentage,
                    bw.death_overs as overs,
                    CASE WHEN bw.death_wickets > 0 THEN ((bw.death_overs * 6) / bw.death_wickets) ELSE 0 END as strike_rate,
                    CASE WHEN bw.death_wickets > 0 THEN (bw.death_runs / bw.death_wickets) ELSE 0 END as average,
                    bw.match_id
                FROM bowling_stats bw
                JOIN matches m ON bw.match_id = m.id
                WHERE m.date < :through_date AND bw.death_overs > 0
                UNION ALL
                SELECT 
                    bw.bowler,
                    m.venue,
                    'overall' as phase,
                    bw.economy as economy,
                    bw.wickets as wickets,
                    CASE WHEN bw.overs > 0 THEN (bw.dots * 100.0 / (bw.overs * 6)) ELSE 0 END as dot_ball_percentage,
                    bw.overs as overs,
                    CASE WHEN bw.wickets > 0 THEN ((bw.overs * 6) / bw.wickets) ELSE 0 END as strike_rate,
                    CASE WHEN bw.wickets > 0 THEN (bw.runs_conceded / bw.wickets) ELSE 0 END as average,
                    bw.match_id
                FROM bowling_stats bw
                JOIN matches m ON bw.match_id = m.id
                WHERE m.date < :through_date AND bw.overs > 0
            ) as player_stats
            GROUP BY player_stats.bowler, player_stats.venue, player_stats.phase
            HAVING COUNT(DISTINCT player_stats.match_id) >= 5
        """)
        
        bowling_players = self.session.execute(bowling_query, {"through_date": through_date}).fetchall()
        logger.info(f"Processing {len(bowling_players)} bowling player/venue/phase combinations")
        
        # Prepare bowling records
        bowling_records = []
        for player in bowling_players:
            bowling_records.append({
                'player_name': player.player_name,
                'venue_type': 'venue_specific',
                'venue_identifier': player.venue,
                'league': None,
                'phase': player.phase,
                'role': 'bowling',
                'avg_economy': round(float(player.avg_economy or 0), 2),
                'avg_wickets': round(float(player.avg_wickets or 0), 2),
                'dot_ball_percentage': round(float(player.dot_ball_percentage or 0), 2),
                'avg_overs': round(float(player.avg_overs or 0), 1),
                'strike_rate': round(float(player.strike_rate or 0), 2),
                'average': round(float(player.average or 0), 2),
                'matches_played': player.matches_played,
                'computed_date': datetime.utcnow(),
                'data_through_date': through_date
            })
        
        if bowling_records:
            self.session.bulk_insert_mappings(PlayerBaseline, bowling_records)
            records_inserted += len(bowling_records)
            self.session.commit()
        
        logger.info(f"Player baselines rebuild completed: {records_inserted} records inserted")
        
        return {
            "records_processed": len(batting_players) + len(bowling_players),
            "records_inserted": records_inserted,
            "batting_combinations": len(batting_players),
            "bowling_combinations": len(bowling_players)
        }
    
    def _rebuild_venue_resources(self, through_date: date) -> Dict[str, Any]:
        """Rebuild venue resource tables with DLS-style resource percentages."""
        logger.info("Rebuilding venue resources table...")
        
        # Clear existing data
        self.session.execute(text("TRUNCATE TABLE venue_resources"))
        self.session.commit()
        
        # Build venue-specific resource tables using ball-by-ball data
        # This creates DLS-style resource percentages based on historical outcomes
        
        resources_query = text("""
            WITH ball_states AS (
                -- Extract all ball-by-ball states with cumulative runs and wickets
                SELECT 
                    d.match_id,
                    m.venue,
                    d.innings,
                    d.over as over_num,
                    COUNT(*) FILTER (WHERE d.wicket_type IS NOT NULL) OVER (
                        PARTITION BY d.match_id, d.innings 
                        ORDER BY d.over, d.ball
                    ) as wickets_lost,
                    SUM(d.runs_off_bat + d.extras) OVER (
                        PARTITION BY d.match_id, d.innings 
                        ORDER BY d.over, d.ball
                    ) as runs_at_state,
                    -- Get final score for this innings
                    SUM(d.runs_off_bat + d.extras) OVER (
                        PARTITION BY d.match_id, d.innings
                    ) as final_score
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE m.date < :through_date
                    AND d.over < 20  -- T20 format
            ),
            venue_state_averages AS (
                -- Calculate average remaining runs and resource percentages per state
                SELECT 
                    venue,
                    innings,
                    over_num,
                    wickets_lost,
                    AVG(final_score - runs_at_state) as avg_runs_remaining,
                    AVG(final_score) as avg_final_score,
                    AVG(runs_at_state) as avg_runs_at_state,
                    COUNT(DISTINCT match_id) as sample_size
                FROM ball_states
                GROUP BY venue, innings, over_num, wickets_lost
                HAVING COUNT(DISTINCT match_id) >= 5  -- Minimum sample size
            ),
            resource_calculations AS (
                -- Calculate resource percentage as proportion of remaining runs vs maximum possible
                SELECT 
                    venue,
                    innings,
                    over_num,
                    wickets_lost,
                    avg_runs_remaining,
                    avg_final_score,
                    avg_runs_at_state,
                    sample_size,
                    -- Resource percentage based on remaining overs and wickets
                    -- Formula: (remaining_overs * expected_runs_per_over * wickets_factor) / total_expected
                    CASE 
                        WHEN avg_final_score > 0 AND over_num < 20 THEN
                            LEAST(100.0, 
                                (avg_runs_remaining * 100.0 / NULLIF(avg_final_score, 0)) *
                                ((20 - over_num) / 20.0) *  -- Overs remaining factor
                                ((10 - wickets_lost) / 10.0)  -- Wickets remaining factor
                            )
                        ELSE 0.0
                    END as resource_percentage
                FROM venue_state_averages
                WHERE avg_final_score > 0
            )
            SELECT 
                venue,
                innings,
                over_num,
                wickets_lost,
                ROUND(CAST(resource_percentage AS NUMERIC), 2) as resource_percentage,
                ROUND(CAST(avg_runs_at_state AS NUMERIC), 2) as avg_runs_at_state,
                ROUND(CAST(avg_final_score AS NUMERIC), 2) as avg_final_score,
                sample_size
            FROM resource_calculations
            WHERE resource_percentage >= 0 
                AND sample_size >= 5
            ORDER BY venue, innings, over_num, wickets_lost
        """)
        
        resources = self.session.execute(resources_query, {"through_date": through_date}).fetchall()
        logger.info(f"Processing {len(resources)} venue/innings/over/wickets combinations")
        
        # Prepare resource records for bulk insert
        resource_records = []
        for resource in resources:
            resource_records.append({
                'venue': resource.venue,
                'league': None,  # Could be added later if league info available
                'innings': resource.innings,
                'over_num': resource.over_num,
                'wickets_lost': resource.wickets_lost,
                'resource_percentage': float(resource.resource_percentage),
                'avg_runs_at_state': float(resource.avg_runs_at_state) if resource.avg_runs_at_state else None,
                'avg_final_score': float(resource.avg_final_score) if resource.avg_final_score else None,
                'sample_size': resource.sample_size,
                'computed_date': datetime.utcnow(),
                'data_through_date': through_date
            })
        
        records_inserted = 0
        if resource_records:
            # Import VenueResource model
            from precomputed_models import VenueResource
            self.session.bulk_insert_mappings(VenueResource, resource_records)
            records_inserted = len(resource_records)
            self.session.commit()
        
        logger.info(f"Venue resources rebuild completed: {records_inserted} records inserted")
        
        return {
            "records_processed": len(resources),
            "records_inserted": records_inserted,
            "venue_combinations": len(resources)
        }
    
    def _rebuild_wpa_outcomes(self, through_date: date) -> Dict[str, Any]:
        """Rebuild WPA outcomes table with chase success probabilities."""
        logger.info("Rebuilding WPA outcomes table...")
        
        # Clear existing data
        self.session.execute(text("TRUNCATE TABLE wpa_outcomes"))
        self.session.commit()
        
        # Build WPA outcomes using second innings chase data
        # This creates win probability lookup tables based on historical outcomes
        
        wpa_query = text("""
            WITH chase_data AS (
                -- Extract second innings chase scenarios with ball-by-ball states
                SELECT 
                    d.match_id,
                    m.venue,
                    m.competition as league,
                    -- Get target from first innings total
                    first_innings.total_runs + 1 as target,
                    d.over as current_over,
                    -- Count wickets lost up to this ball
                    COUNT(*) FILTER (WHERE d.wicket_type IS NOT NULL) OVER (
                        PARTITION BY d.match_id, d.innings 
                        ORDER BY d.over, d.ball
                    ) as wickets_lost,
                    -- Current score up to this ball
                    SUM(d.runs_off_bat + d.extras) OVER (
                        PARTITION BY d.match_id, d.innings 
                        ORDER BY d.over, d.ball
                    ) as current_runs,
                    -- Final result (did chasing team win?)
                    CASE WHEN m.winner = d.batting_team THEN 1 ELSE 0 END as chase_successful
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                JOIN (
                    -- Get first innings totals for target calculation
                    SELECT 
                        match_id,
                        SUM(runs_off_bat + extras) as total_runs
                    FROM deliveries 
                    WHERE innings = 1
                    GROUP BY match_id
                ) first_innings ON d.match_id = first_innings.match_id
                WHERE m.date < :through_date
                    AND d.innings = 2  -- Only second innings (chases)
                    AND d.over < 20    -- T20 format
                    AND m.winner IS NOT NULL  -- Only completed matches
            ),
            bucketed_outcomes AS (
                -- Group outcomes into buckets for statistical significance
                SELECT 
                    venue,
                    league,
                    -- Target buckets (10-run groups: 120-129, 130-139, etc.)
                    (target / 10) * 10 as target_bucket,
                    -- Over buckets (every 2 overs: 0-1, 2-3, 4-5, etc.)
                    (current_over / 2) * 2 as over_bucket,
                    wickets_lost,
                    -- Score range buckets (20-run groups)
                    (current_runs / 20) * 20 as runs_range_min,
                    ((current_runs / 20) * 20) + 19 as runs_range_max,
                    chase_successful,
                    COUNT(*) as total_outcomes
                FROM chase_data
                WHERE target BETWEEN 100 AND 250  -- Reasonable T20 targets
                    AND current_over <= 19
                    AND wickets_lost <= 9
                GROUP BY venue, league, target_bucket, over_bucket, wickets_lost, 
                         runs_range_min, runs_range_max, chase_successful
            ),
            aggregated_outcomes AS (
                -- Calculate win probabilities per bucket
                SELECT 
                    venue,
                    league,
                    target_bucket,
                    over_bucket,
                    wickets_lost,
                    runs_range_min,
                    runs_range_max,
                    SUM(total_outcomes) as total_outcomes,
                    SUM(CASE WHEN chase_successful = 1 THEN total_outcomes ELSE 0 END) as successful_chases,
                    -- Win probability calculation
                    CASE 
                        WHEN SUM(total_outcomes) > 0 THEN
                            ROUND(
                                CAST(SUM(CASE WHEN chase_successful = 1 THEN total_outcomes ELSE 0 END) AS NUMERIC) / 
                                CAST(SUM(total_outcomes) AS NUMERIC), 3
                            )
                        ELSE 0.000
                    END as win_probability,
                    SUM(total_outcomes) as sample_size
                FROM bucketed_outcomes
                GROUP BY venue, league, target_bucket, over_bucket, wickets_lost, 
                         runs_range_min, runs_range_max
                HAVING SUM(total_outcomes) >= 5  -- Minimum sample size for reliability
            )
            SELECT 
                venue,
                league,
                target_bucket::INTEGER,
                over_bucket::INTEGER,
                wickets_lost,
                runs_range_min::INTEGER,
                runs_range_max::INTEGER,
                total_outcomes,
                successful_chases,
                win_probability,
                sample_size
            FROM aggregated_outcomes
            WHERE win_probability >= 0.000 AND win_probability <= 1.000
            ORDER BY venue, target_bucket, over_bucket, wickets_lost, runs_range_min
        """)
        
        outcomes = self.session.execute(wpa_query, {"through_date": through_date}).fetchall()
        logger.info(f"Processing {len(outcomes)} WPA outcome combinations")
        
        # Prepare WPA outcome records for bulk insert
        wpa_records = []
        for outcome in outcomes:
            wpa_records.append({
                'venue': outcome.venue,
                'league': outcome.league,
                'target_bucket': outcome.target_bucket,
                'over_bucket': outcome.over_bucket,
                'wickets_lost': outcome.wickets_lost,
                'runs_range_min': outcome.runs_range_min,
                'runs_range_max': outcome.runs_range_max,
                'total_outcomes': outcome.total_outcomes,
                'successful_chases': outcome.successful_chases,
                'win_probability': float(outcome.win_probability),
                'sample_size': outcome.sample_size,
                'computed_date': datetime.utcnow(),
                'data_through_date': through_date
            })
        
        records_inserted = 0
        if wpa_records:
            # Import WPAOutcome model
            from precomputed_models import WPAOutcome
            self.session.bulk_insert_mappings(WPAOutcome, wpa_records)
            records_inserted = len(wpa_records)
            self.session.commit()
        
        logger.info(f"WPA outcomes rebuild completed: {records_inserted} records inserted")
        
        return {
            "records_processed": len(outcomes),
            "records_inserted": records_inserted,
            "wpa_combinations": len(outcomes)
        }
