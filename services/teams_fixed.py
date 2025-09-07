from sqlalchemy.sql import text
from fastapi import HTTPException
from typing import List, Optional
from datetime import date
from models import teams_mapping, Match, BattingStats, BowlingStats
import logging
import traceback

# Import the new true percentiles functions
from .teams_percentiles import (
    calculate_true_batting_percentiles,
    apply_true_batting_percentiles
)

# Set up detailed logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_all_team_name_variations(team_name: str) -> List[str]:
    """Get all possible name variations for a given team based on teams_mapping"""
    try:
        logger.info(f"Getting team variations for: {team_name}")
        
        # Create a reverse mapping from abbreviation to all team names
        reverse_mapping = {}
        for full_name, abbrev in teams_mapping.items():
            if abbrev not in reverse_mapping:
                reverse_mapping[abbrev] = []
            reverse_mapping[abbrev].append(full_name)
        
        # If team_name is an abbreviation, return all full names for it
        if team_name in reverse_mapping:
            variations = reverse_mapping[team_name]
            logger.info(f"Found variations for abbreviation {team_name}: {variations}")
            return variations
        
        # If it's a full name, find its abbreviation and return all related names
        abbrev = teams_mapping.get(team_name)
        if abbrev and abbrev in reverse_mapping:
            variations = reverse_mapping[abbrev]
            logger.info(f"Found variations for full name {team_name} (abbrev {abbrev}): {variations}")
            return variations
        
        # If not found in mapping, return just the original name
        logger.info(f"No variations found for {team_name}, returning original")
        return [team_name]
    except Exception as e:
        logger.error(f"Error in get_all_team_name_variations: {str(e)}")
        return [team_name]

def get_team_phase_stats_service_fixed(
    team_name: str,
    start_date: Optional[date],
    end_date: Optional[date],
    players: Optional[List[str]],
    db
) -> dict:
    """
    Get aggregated phase-wise batting statistics for a team or custom players with FIXED SQL queries
    """
    logger.info(f"=== STARTING PHASE STATS SERVICE (FIXED VERSION) ===")
    logger.info(f"Team: {team_name}, Players: {players}, Start: {start_date}, End: {end_date}")
    
    try:
        # Step 1: Determine if we're using team-based or custom player analysis
        use_custom_players = players is not None and len(players) > 0
        logger.info(f"Using custom players: {use_custom_players}")
        
        if use_custom_players:
            # Custom player mode
            player_filter = "bs.striker = ANY(:players)"
            filter_params = {"players": players}
            context_prefix = "Custom Players"
            logger.info(f"Custom players: {players}")
        else:
            # Team-based mode
            team_variations = get_all_team_name_variations(team_name)
            player_filter = "bs.batting_team = ANY(:team_variations)"
            filter_params = {"team_variations": team_variations}
            context_prefix = team_name
            logger.info(f"Team variations: {team_variations}")
        
        # Add date parameters
        filter_params.update({
            "start_date": start_date,
            "end_date": end_date
        })
        
        # Step 2: Determine team type and benchmark context
        logger.info("Step 2: Determining team type and benchmark context")
        from models import INTERNATIONAL_TEAMS_RANKED
        
        if use_custom_players:
            # For custom players, always use global benchmarks
            context = "All Teams (Global Benchmark)"
            benchmark_filter = "1=1"  # No additional filter - use all teams
            league_param = None
            logger.info("Using global benchmarking for custom players")
        else:
            # Team-based mode - existing logic
            international_check_query = text(f"""
                SELECT COUNT(*) as international_matches
                FROM matches m
                INNER JOIN batting_stats bs ON m.id = bs.match_id
                WHERE {player_filter}
                AND m.match_type = 'international'
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
            """)
            
            try:
                international_result = db.execute(international_check_query, filter_params).fetchone()
                has_international_matches = international_result.international_matches > 0
                logger.info(f"International matches found: {international_result.international_matches}")
            except Exception as e:
                logger.error(f"Error checking international matches: {str(e)}")
                has_international_matches = False
            
            # Fallback to ranked list check (for teams that might not have recent matches in date range)
            if not use_custom_players:
                team_variations = filter_params.get("team_variations", [])
                is_top_ranked = any(variation in INTERNATIONAL_TEAMS_RANKED for variation in team_variations)
            else:
                is_top_ranked = False
            
            # Team is international if it has played international matches OR is in top ranked list
            is_international_team = has_international_matches or is_top_ranked
            
            logger.info(f"Has international matches: {has_international_matches}")
            logger.info(f"Is top ranked: {is_top_ranked}")
            logger.info(f"Final is_international_team decision: {is_international_team}")
            
            if is_international_team:
                context = "International Teams"
                benchmark_filter = "m.match_type = 'international'"
                league_param = None
                logger.info("Using international team benchmarking")
            else:
                # Get the league from recent matches
                logger.info("Getting league for benchmarking")
                league_query = text(f"""
                    SELECT m.competition, m.date
                    FROM matches m
                    INNER JOIN batting_stats bs ON m.id = bs.match_id
                    WHERE {player_filter}
                    AND m.match_type = 'league'
                    AND (:start_date IS NULL OR m.date >= :start_date)
                    AND (:end_date IS NULL OR m.date <= :end_date)
                    ORDER BY m.date DESC 
                    LIMIT 1
                """)
                
                try:
                    league_result = db.execute(league_query, filter_params).fetchone()
                    league_param = league_result.competition if league_result else None
                    context = f"{league_param} Teams" if league_param else "League Teams"
                    benchmark_filter = "m.match_type = 'league' AND (:league_param IS NULL OR m.competition = :league_param)"
                    logger.info(f"League query successful: league_param={league_param}, context={context}")
                    
                except Exception as e:
                    logger.error(f"LEAGUE QUERY FAILED: {str(e)}")
                    logger.error(f"League query traceback: {traceback.format_exc()}")
                    raise HTTPException(status_code=500, detail=f"League query failed: {str(e)}")
        # Step 3: Get team/player phase stats
        logger.info("Step 3: Executing phase stats query")
        team_phase_stats_query = text(f"""
            WITH team_phase_aggregates AS (
                SELECT 
                    COALESCE(SUM(bs.pp_runs), 0) as total_pp_runs,
                    COALESCE(SUM(bs.pp_balls), 0) as total_pp_balls,
                    COALESCE(SUM(bs.pp_wickets), 0) as total_pp_wickets,
                    COALESCE(SUM(bs.middle_runs), 0) as total_middle_runs,
                    COALESCE(SUM(bs.middle_balls), 0) as total_middle_balls,
                    COALESCE(SUM(bs.middle_wickets), 0) as total_middle_wickets,
                    COALESCE(SUM(bs.death_runs), 0) as total_death_runs,
                    COALESCE(SUM(bs.death_balls), 0) as total_death_balls,
                    COALESCE(SUM(bs.death_wickets), 0) as total_death_wickets,
                    COUNT(DISTINCT bs.match_id) as total_matches
                FROM batting_stats bs
                INNER JOIN matches m ON bs.match_id = m.id
                WHERE {player_filter}
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
            )
            SELECT 
                total_pp_runs, total_pp_balls, total_pp_wickets,
                total_middle_runs, total_middle_balls, total_middle_wickets,
                total_death_runs, total_death_balls, total_death_wickets,
                total_matches,
                CASE WHEN total_pp_wickets > 0 THEN ROUND(total_pp_runs::numeric / total_pp_wickets, 2) ELSE NULL END as pp_average,
                CASE WHEN total_pp_balls > 0 THEN ROUND(total_pp_runs::numeric * 100 / total_pp_balls, 2) ELSE 0 END as pp_strike_rate,
                CASE WHEN total_middle_wickets > 0 THEN ROUND(total_middle_runs::numeric / total_middle_wickets, 2) ELSE NULL END as middle_average,
                CASE WHEN total_middle_balls > 0 THEN ROUND(total_middle_runs::numeric * 100 / total_middle_balls, 2) ELSE 0 END as middle_strike_rate,
                CASE WHEN total_death_wickets > 0 THEN ROUND(total_death_runs::numeric / total_death_wickets, 2) ELSE NULL END as death_average,
                CASE WHEN total_death_balls > 0 THEN ROUND(total_death_runs::numeric * 100 / total_death_balls, 2) ELSE 0 END as death_strike_rate
            FROM team_phase_aggregates
        """)
        logger.info(f"Query parameters: {filter_params}")
        
        try:
            team_result = db.execute(team_phase_stats_query, filter_params).fetchone()
            logger.info(f"Phase stats query executed successfully")
            
            if team_result:
                logger.info(f"Stats: matches={team_result.total_matches}, pp_runs={team_result.total_pp_runs}")
            else:
                logger.warning("Phase stats query returned no results")
                
        except Exception as e:
            logger.error(f"PHASE STATS QUERY FAILED: {str(e)}")
            logger.error(f"Query traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Phase stats query failed: {str(e)}")
        
        # Step 4: Handle no data case
        if not team_result or team_result.total_matches == 0:
            logger.info("No phase stats data found, returning default values")
            return {
                "powerplay": {"runs": 0, "balls": 0, "wickets": 0, "average": 0, "strike_rate": 0, "normalized_average": 50, "normalized_strike_rate": 50},
                "middle_overs": {"runs": 0, "balls": 0, "wickets": 0, "average": 0, "strike_rate": 0, "normalized_average": 50, "normalized_strike_rate": 50},
                "death_overs": {"runs": 0, "balls": 0, "wickets": 0, "average": 0, "strike_rate": 0, "normalized_average": 50, "normalized_strike_rate": 50},
                "total_matches": 0, "context": "No data", "benchmark_teams": 0
            }
        
        # Step 5: Calculate TRUE SQL percentiles from benchmark data
        logger.info("Step 5: Calculating true SQL percentiles")
        
        # Set up benchmark parameters for true percentiles calculation
        if use_custom_players:
            benchmark_params = {
                "players": players,
                "start_date": start_date,
                "end_date": end_date
            }
        else:
            benchmark_params = {
                "team_variations": filter_params["team_variations"],
                "start_date": start_date,
                "end_date": end_date
            }
            if league_param:  # Add league parameter if applicable
                benchmark_params["league_param"] = league_param
        
        # Calculate true percentiles using the new function
        percentile_data = calculate_true_batting_percentiles(
            team_name=context_prefix,
            start_date=start_date,
            end_date=end_date,
            players=players,
            benchmark_filter=benchmark_filter,
            benchmark_params=benchmark_params,
            db=db
        )
        
        # Step 6: Apply percentile normalization (with fallback to simplified)
        logger.info("Step 6: Applying percentile normalization")
        
        # Extract team stats for normalization
        team_pp_avg = float(team_result.pp_average) if team_result.pp_average else None
        team_pp_sr = float(team_result.pp_strike_rate) if team_result.pp_strike_rate else 0
        team_middle_avg = float(team_result.middle_average) if team_result.middle_average else None
        team_middle_sr = float(team_result.middle_strike_rate) if team_result.middle_strike_rate else 0
        team_death_avg = float(team_result.death_average) if team_result.death_average else None
        team_death_sr = float(team_result.death_strike_rate) if team_result.death_strike_rate else 0
        
        logger.info(f"Stats extracted - PP: avg={team_pp_avg}, sr={team_pp_sr}")
        
        if percentile_data:  # Use true percentiles if available
            team_batting_stats = {
                "pp_average": team_pp_avg,
                "pp_strike_rate": team_pp_sr,
                "middle_average": team_middle_avg,
                "middle_strike_rate": team_middle_sr,
                "death_average": team_death_avg,
                "death_strike_rate": team_death_sr
            }
            
            percentile_scores = apply_true_batting_percentiles(team_batting_stats, percentile_data)
            
            pp_avg_norm = percentile_scores["pp_avg_percentile"]
            pp_sr_norm = percentile_scores["pp_sr_percentile"]
            middle_avg_norm = percentile_scores["middle_avg_percentile"]
            middle_sr_norm = percentile_scores["middle_sr_percentile"]
            death_avg_norm = percentile_scores["death_avg_percentile"]
            death_sr_norm = percentile_scores["death_sr_percentile"]
            benchmark_teams_count = percentile_scores["benchmark_teams_count"]
            
            context += " (True SQL Percentiles)"
            logger.info(f"True percentiles applied successfully with {benchmark_teams_count} benchmark teams")
            
        else:  # Fallback to simplified normalization
            logger.warning("Falling back to simplified normalization due to insufficient benchmark data")
            
            # Use simple normalization based on typical cricket values
            def simple_normalize_avg(avg):
                if avg is None: return 50
                if avg <= 15: return 25
                elif avg <= 30: return 25 + (avg - 15) * 25 / 15
                elif avg <= 45: return 50 + (avg - 30) * 25 / 15
                else: return 75 + min(25, (avg - 45) * 25 / 15)
                
            def simple_normalize_sr(sr):
                if sr <= 100: return 25
                elif sr <= 130: return 25 + (sr - 100) * 25 / 30
                elif sr <= 160: return 50 + (sr - 130) * 25 / 30
                else: return 75 + min(25, (sr - 160) * 25 / 30)
            
            pp_avg_norm = simple_normalize_avg(team_pp_avg)
            pp_sr_norm = simple_normalize_sr(team_pp_sr)
            middle_avg_norm = simple_normalize_avg(team_middle_avg)
            middle_sr_norm = simple_normalize_sr(team_middle_sr)
            death_avg_norm = simple_normalize_avg(team_death_avg)
            death_sr_norm = simple_normalize_sr(team_death_sr)
            benchmark_teams_count = 0
            
            context += " (Simplified Fallback)"
            logger.info("Simplified normalization completed as fallback")
        
        # Step 7: Format response
        logger.info("Step 7: Formatting response")
        
        try:
            phase_stats = {
                "powerplay": {
                    "runs": team_result.total_pp_runs or 0,
                    "balls": team_result.total_pp_balls or 0,
                    "wickets": team_result.total_pp_wickets or 0,
                    "average": team_pp_avg or 0,
                    "strike_rate": team_pp_sr,
                    "normalized_average": round(pp_avg_norm, 1),
                    "normalized_strike_rate": round(pp_sr_norm, 1)
                },
                "middle_overs": {
                    "runs": team_result.total_middle_runs or 0,
                    "balls": team_result.total_middle_balls or 0,
                    "wickets": team_result.total_middle_wickets or 0,
                    "average": team_middle_avg or 0,
                    "strike_rate": team_middle_sr,
                    "normalized_average": round(middle_avg_norm, 1),
                    "normalized_strike_rate": round(middle_sr_norm, 1)
                },
                "death_overs": {
                    "runs": team_result.total_death_runs or 0,
                    "balls": team_result.total_death_balls or 0,
                    "wickets": team_result.total_death_wickets or 0,
                    "average": team_death_avg or 0,
                    "strike_rate": team_death_sr,
                    "normalized_average": round(death_avg_norm, 1),
                    "normalized_strike_rate": round(death_sr_norm, 1)
                },
                "total_matches": team_result.total_matches or 0,
                "context": context,
                "benchmark_teams": benchmark_teams_count
            }
            
            logger.info("Response formatted successfully")
            logger.info(f"=== PHASE STATS SERVICE COMPLETED SUCCESSFULLY ===")
            
            return phase_stats
            
        except Exception as e:
            logger.error(f"Error formatting response: {e}")
            logger.error(f"Response formatting traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Response formatting failed: {str(e)}")
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"UNEXPECTED ERROR IN PHASE STATS SERVICE: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Unexpected error in phase stats service: {str(e)}")

def get_team_bowling_phase_stats_service_fixed(
    team_name: str,
    start_date: Optional[date],
    end_date: Optional[date],
    players: Optional[List[str]],
    db
) -> dict:
    """
    Get aggregated phase-wise bowling statistics for a team or custom players with FIXED SQL queries
    """
    logger.info(f"=== STARTING BOWLING PHASE STATS SERVICE (FIXED VERSION) ===")
    logger.info(f"Team: {team_name}, Players: {players}, Start: {start_date}, End: {end_date}")
    
    try:
        # Step 1: Determine if we're using team-based or custom player analysis
        use_custom_players = players is not None and len(players) > 0
        logger.info(f"Using custom players: {use_custom_players}")
        
        if use_custom_players:
            # Custom player mode
            player_filter = "bs.bowler = ANY(:players)"
            filter_params = {"players": players}
            context_prefix = "Custom Players"
            logger.info(f"Custom players: {players}")
        else:
            # Team-based mode
            team_variations = get_all_team_name_variations(team_name)
            player_filter = "bs.bowling_team = ANY(:team_variations)"
            filter_params = {"team_variations": team_variations}
            context_prefix = team_name
            logger.info(f"Team variations: {team_variations}")
        
        # Add date parameters
        filter_params.update({
            "start_date": start_date,
            "end_date": end_date
        })
        
        # Step 2: Determine team type and benchmark context
        logger.info("Step 2: Determining team type and benchmark context")
        from models import INTERNATIONAL_TEAMS_RANKED
        
        if use_custom_players:
            # For custom players, always use global benchmarks
            context = "All Teams (Global Benchmark)"
            benchmark_filter = "1=1"  # No additional filter - use all teams
            league_param = None
            logger.info("Using global benchmarking for custom players")
        else:
            # Team-based mode - existing logic
            international_check_query = text(f"""
                SELECT COUNT(*) as international_matches
                FROM matches m
                INNER JOIN bowling_stats bs ON m.id = bs.match_id
                WHERE {player_filter}
                AND m.match_type = 'international'
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
            """)
            
            try:
                international_result = db.execute(international_check_query, filter_params).fetchone()
                has_international_matches = international_result.international_matches > 0
                logger.info(f"International bowling matches found: {international_result.international_matches}")
            except Exception as e:
                logger.error(f"Error checking international bowling matches: {str(e)}")
                has_international_matches = False
            
            # Fallback to ranked list check
            if not use_custom_players:
                team_variations = filter_params.get("team_variations", [])
                is_top_ranked = any(variation in INTERNATIONAL_TEAMS_RANKED for variation in team_variations)
            else:
                is_top_ranked = False
            
            # Team is international if it has played international matches OR is in top ranked list
            is_international_team = has_international_matches or is_top_ranked
            
            logger.info(f"Has international bowling matches: {has_international_matches}")
            logger.info(f"Is top ranked: {is_top_ranked}")
            logger.info(f"Final is_international_team decision: {is_international_team}")
            
            if is_international_team:
                context = "International Teams"
                benchmark_filter = "m.match_type = 'international'"
                league_param = None
                logger.info("Using international team bowling benchmarking")
            else:
                # Get the league from recent matches
                logger.info("Getting league for bowling benchmarking")
                league_query = text(f"""
                    SELECT m.competition, m.date
                    FROM matches m
                    INNER JOIN bowling_stats bs ON m.id = bs.match_id
                    WHERE {player_filter}
                    AND m.match_type = 'league'
                    AND (:start_date IS NULL OR m.date >= :start_date)
                    AND (:end_date IS NULL OR m.date <= :end_date)
                    ORDER BY m.date DESC 
                    LIMIT 1
                """)
                
                try:
                    league_result = db.execute(league_query, filter_params).fetchone()
                    league_param = league_result.competition if league_result else None
                    context = f"{league_param} Teams" if league_param else "League Teams"
                    benchmark_filter = "m.match_type = 'league' AND (:league_param IS NULL OR m.competition = :league_param)"
                    logger.info(f"League bowling query successful: league_param={league_param}, context={context}")
                    
                except Exception as e:
                    logger.error(f"LEAGUE BOWLING QUERY FAILED: {str(e)}")
                    logger.error(f"League bowling query traceback: {traceback.format_exc()}")
                    raise HTTPException(status_code=500, detail=f"League bowling query failed: {str(e)}")
        
        # Step 3: Get team/player bowling phase stats
        logger.info("Step 3: Executing bowling phase stats query")
        team_bowling_phase_stats_query = text(f"""
            WITH team_bowling_phase_aggregates AS (
                SELECT 
                    COALESCE(SUM(bs.pp_runs), 0) as total_pp_runs,
                    COALESCE(SUM(bs.pp_overs * 6), 0) as total_pp_balls,
                    COALESCE(SUM(bs.pp_wickets), 0) as total_pp_wickets,
                    COALESCE(SUM(bs.middle_runs), 0) as total_middle_runs,
                    COALESCE(SUM(bs.middle_overs * 6), 0) as total_middle_balls,
                    COALESCE(SUM(bs.middle_wickets), 0) as total_middle_wickets,
                    COALESCE(SUM(bs.death_runs), 0) as total_death_runs,
                    COALESCE(SUM(bs.death_overs * 6), 0) as total_death_balls,
                    COALESCE(SUM(bs.death_wickets), 0) as total_death_wickets,
                    COUNT(DISTINCT bs.match_id) as total_matches
                FROM bowling_stats bs
                INNER JOIN matches m ON bs.match_id = m.id
                WHERE {player_filter}
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
            )
            SELECT 
                total_pp_runs, total_pp_balls, total_pp_wickets,
                total_middle_runs, total_middle_balls, total_middle_wickets,
                total_death_runs, total_death_balls, total_death_wickets,
                total_matches,
                -- Bowling Average = runs/wickets (lower is better)
                CASE WHEN total_pp_wickets > 0 THEN ROUND((total_pp_runs::numeric / total_pp_wickets::numeric), 2) ELSE NULL END as pp_bowling_average,
                -- Bowling Strike Rate = balls/wickets (lower is better)
                CASE WHEN total_pp_wickets > 0 THEN ROUND((total_pp_balls::numeric / total_pp_wickets::numeric), 2) ELSE NULL END as pp_bowling_strike_rate,
                -- Economy Rate = (runs * 6)/balls (lower is better)
                CASE WHEN total_pp_balls > 0 THEN ROUND((total_pp_runs::numeric * 6 / total_pp_balls::numeric), 2) ELSE 0 END as pp_economy_rate,
                
                CASE WHEN total_middle_wickets > 0 THEN ROUND((total_middle_runs::numeric / total_middle_wickets::numeric), 2) ELSE NULL END as middle_bowling_average,
                CASE WHEN total_middle_wickets > 0 THEN ROUND((total_middle_balls::numeric / total_middle_wickets::numeric), 2) ELSE NULL END as middle_bowling_strike_rate,
                CASE WHEN total_middle_balls > 0 THEN ROUND((total_middle_runs::numeric * 6 / total_middle_balls::numeric), 2) ELSE 0 END as middle_economy_rate,
                
                CASE WHEN total_death_wickets > 0 THEN ROUND((total_death_runs::numeric / total_death_wickets::numeric), 2) ELSE NULL END as death_bowling_average,
                CASE WHEN total_death_wickets > 0 THEN ROUND((total_death_balls::numeric / total_death_wickets::numeric), 2) ELSE NULL END as death_bowling_strike_rate,
                CASE WHEN total_death_balls > 0 THEN ROUND((total_death_runs::numeric * 6 / total_death_balls::numeric), 2) ELSE 0 END as death_economy_rate
            FROM team_bowling_phase_aggregates
        """)
        logger.info(f"Bowling query parameters: {filter_params}")
        
        try:
            team_result = db.execute(team_bowling_phase_stats_query, filter_params).fetchone()
            logger.info(f"Bowling phase stats query executed successfully")
            
            if team_result:
                logger.info(f"Bowling stats: matches={team_result.total_matches}, pp_runs={team_result.total_pp_runs}")
            else:
                logger.warning("Bowling phase stats query returned no results")
                
        except Exception as e:
            logger.error(f"BOWLING PHASE STATS QUERY FAILED: {str(e)}")
            logger.error(f"Bowling query traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Bowling phase stats query failed: {str(e)}")
        
        # Step 4: Handle no data case
        if not team_result or team_result.total_matches == 0:
            logger.info("No bowling phase stats data found, returning default values")
            return {
                "powerplay": {"runs": 0, "balls": 0, "wickets": 0, "bowling_average": 0, "bowling_strike_rate": 0, "economy_rate": 0, "normalized_average": 50, "normalized_strike_rate": 50, "normalized_economy": 50},
                "middle_overs": {"runs": 0, "balls": 0, "wickets": 0, "bowling_average": 0, "bowling_strike_rate": 0, "economy_rate": 0, "normalized_average": 50, "normalized_strike_rate": 50, "normalized_economy": 50},
                "death_overs": {"runs": 0, "balls": 0, "wickets": 0, "bowling_average": 0, "bowling_strike_rate": 0, "economy_rate": 0, "normalized_average": 50, "normalized_strike_rate": 50, "normalized_economy": 50},
                "total_matches": 0, "context": "No data", "benchmark_teams": 0
            }
        
        # Step 5: Execute SIMPLIFIED bowling benchmark query
        logger.info("Step 5: Executing simplified bowling benchmark query")
        
        # For custom players, exclude them from benchmarks. For teams, exclude the team.
        if use_custom_players:
            exclude_filter = "bs.bowling_team != ANY(:players)"  # Exclude individual players
            benchmark_params = {
                "players": players,
                "start_date": start_date,
                "end_date": end_date
            }
        else:
            exclude_filter = "bs.bowling_team != ANY(:team_variations)"  # Exclude team
            benchmark_params = {
                "team_variations": filter_params["team_variations"],
                "start_date": start_date,
                "end_date": end_date
            }
            if not use_custom_players and league_param:  # Only add league_param for team-based queries
                benchmark_params["league_param"] = league_param
        
        bowling_benchmark_query = text(f"""
            WITH team_bowling_stats AS (
                SELECT 
                    bs.bowling_team,
                    SUM(bs.pp_runs)::float / NULLIF(SUM(bs.pp_wickets), 0) as team_pp_bowling_avg,
                    SUM(bs.pp_overs * 6)::float / NULLIF(SUM(bs.pp_wickets), 0) as team_pp_bowling_sr,
                    SUM(bs.pp_runs)::float * 6 / NULLIF(SUM(bs.pp_overs * 6), 0) as team_pp_economy,
                    SUM(bs.middle_runs)::float / NULLIF(SUM(bs.middle_wickets), 0) as team_middle_bowling_avg,
                    SUM(bs.middle_overs * 6)::float / NULLIF(SUM(bs.middle_wickets), 0) as team_middle_bowling_sr,
                    SUM(bs.middle_runs)::float * 6 / NULLIF(SUM(bs.middle_overs * 6), 0) as team_middle_economy,
                    SUM(bs.death_runs)::float / NULLIF(SUM(bs.death_wickets), 0) as team_death_bowling_avg,
                    SUM(bs.death_overs * 6)::float / NULLIF(SUM(bs.death_wickets), 0) as team_death_bowling_sr,
                    SUM(bs.death_runs)::float * 6 / NULLIF(SUM(bs.death_overs * 6), 0) as team_death_economy
                FROM bowling_stats bs
                INNER JOIN matches m ON bs.match_id = m.id
                WHERE {benchmark_filter}
                AND {exclude_filter}
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                GROUP BY bs.bowling_team
                HAVING SUM(bs.pp_overs * 6) > 0 AND SUM(bs.middle_overs * 6) > 0 AND SUM(bs.death_overs * 6) > 0
            )
            SELECT 
                COUNT(*) as benchmark_teams
            FROM team_bowling_stats
        """)
        
        logger.info(f"Bowling benchmark query parameters: {benchmark_params}")
        
        try:
            benchmark_result = db.execute(bowling_benchmark_query, benchmark_params).fetchone()
            logger.info(f"Simplified bowling benchmark query executed successfully")
            
            if benchmark_result:
                logger.info(f"Bowling benchmark stats: teams={benchmark_result.benchmark_teams}")
            else:
                logger.warning("Bowling benchmark query returned no results")
                
        except Exception as e:
            logger.error(f"BOWLING BENCHMARK QUERY FAILED: {str(e)}")
            logger.error(f"Bowling benchmark query traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Bowling benchmark query failed: {str(e)}")
        
        # Step 6: Use SIMPLE normalization for bowling stats (inverted for bowling - lower is better)
        logger.info("Step 6: Using simplified bowling normalization")
        
        # Extract team bowling stats
        team_pp_bowling_avg = float(team_result.pp_bowling_average) if team_result.pp_bowling_average else None
        team_pp_bowling_sr = float(team_result.pp_bowling_strike_rate) if team_result.pp_bowling_strike_rate else None
        team_pp_economy = float(team_result.pp_economy_rate) if team_result.pp_economy_rate else 0
        team_middle_bowling_avg = float(team_result.middle_bowling_average) if team_result.middle_bowling_average else None
        team_middle_bowling_sr = float(team_result.middle_bowling_strike_rate) if team_result.middle_bowling_strike_rate else None
        team_middle_economy = float(team_result.middle_economy_rate) if team_result.middle_economy_rate else 0
        team_death_bowling_avg = float(team_result.death_bowling_average) if team_result.death_bowling_average else None
        team_death_bowling_sr = float(team_result.death_bowling_strike_rate) if team_result.death_bowling_strike_rate else None
        team_death_economy = float(team_result.death_economy_rate) if team_result.death_economy_rate else 0
        
        logger.info(f"Bowling stats extracted - PP: avg={team_pp_bowling_avg}, sr={team_pp_bowling_sr}, econ={team_pp_economy}")
        
        # Use simple normalization based on typical bowling values (INVERTED - lower values = higher percentiles)
        def simple_normalize_bowling_avg(avg):
            if avg is None: return 50
            # For bowling average, lower is better: 15-35 range, inverted scale
            if avg >= 35: return 25
            elif avg >= 25: return 25 + (35 - avg) * 25 / 10
            elif avg >= 15: return 50 + (25 - avg) * 25 / 10
            else: return 75 + min(25, (15 - avg) * 25 / 5)
            
        def simple_normalize_bowling_sr(sr):
            if sr is None: return 50
            # For bowling strike rate, lower is better: 12-24 balls per wicket, inverted scale
            if sr >= 24: return 25
            elif sr >= 18: return 25 + (24 - sr) * 25 / 6
            elif sr >= 12: return 50 + (18 - sr) * 25 / 6
            else: return 75 + min(25, (12 - sr) * 25 / 6)
        
        def simple_normalize_economy(econ):
            # For economy rate, lower is better: 6-12 runs per over, inverted scale
            if econ >= 12: return 25
            elif econ >= 9: return 25 + (12 - econ) * 25 / 3
            elif econ >= 6: return 50 + (9 - econ) * 25 / 3
            else: return 75 + min(25, (6 - econ) * 25 / 3)
        
        pp_bowling_avg_norm = simple_normalize_bowling_avg(team_pp_bowling_avg)
        pp_bowling_sr_norm = simple_normalize_bowling_sr(team_pp_bowling_sr)
        pp_economy_norm = simple_normalize_economy(team_pp_economy)
        middle_bowling_avg_norm = simple_normalize_bowling_avg(team_middle_bowling_avg)
        middle_bowling_sr_norm = simple_normalize_bowling_sr(team_middle_bowling_sr)
        middle_economy_norm = simple_normalize_economy(team_middle_economy)
        death_bowling_avg_norm = simple_normalize_bowling_avg(team_death_bowling_avg)
        death_bowling_sr_norm = simple_normalize_bowling_sr(team_death_bowling_sr)
        death_economy_norm = simple_normalize_economy(team_death_economy)
        
        context += " (Simplified normalization)"
        logger.info("Simplified bowling normalization completed successfully")
        
        # Step 7: Format bowling response
        logger.info("Step 7: Formatting bowling response")
        
        try:
            bowling_phase_stats = {
                "powerplay": {
                    "runs": team_result.total_pp_runs or 0,
                    "balls": team_result.total_pp_balls or 0,
                    "wickets": team_result.total_pp_wickets or 0,
                    "bowling_average": team_pp_bowling_avg or 0,
                    "bowling_strike_rate": team_pp_bowling_sr or 0,
                    "economy_rate": team_pp_economy,
                    "normalized_average": round(pp_bowling_avg_norm, 1),
                    "normalized_strike_rate": round(pp_bowling_sr_norm, 1),
                    "normalized_economy": round(pp_economy_norm, 1)
                },
                "middle_overs": {
                    "runs": team_result.total_middle_runs or 0,
                    "balls": team_result.total_middle_balls or 0,
                    "wickets": team_result.total_middle_wickets or 0,
                    "bowling_average": team_middle_bowling_avg or 0,
                    "bowling_strike_rate": team_middle_bowling_sr or 0,
                    "economy_rate": team_middle_economy,
                    "normalized_average": round(middle_bowling_avg_norm, 1),
                    "normalized_strike_rate": round(middle_bowling_sr_norm, 1),
                    "normalized_economy": round(middle_economy_norm, 1)
                },
                "death_overs": {
                    "runs": team_result.total_death_runs or 0,
                    "balls": team_result.total_death_balls or 0,
                    "wickets": team_result.total_death_wickets or 0,
                    "bowling_average": team_death_bowling_avg or 0,
                    "bowling_strike_rate": team_death_bowling_sr or 0,
                    "economy_rate": team_death_economy,
                    "normalized_average": round(death_bowling_avg_norm, 1),
                    "normalized_strike_rate": round(death_bowling_sr_norm, 1),
                    "normalized_economy": round(death_economy_norm, 1)
                },
                "total_matches": team_result.total_matches or 0,
                "context": context,
                "benchmark_teams": benchmark_result.benchmark_teams if benchmark_result else 0
            }
            
            logger.info("Bowling response formatted successfully")
            logger.info(f"=== BOWLING PHASE STATS SERVICE COMPLETED SUCCESSFULLY ===")
            
            return bowling_phase_stats
            
        except Exception as e:
            logger.error(f"Error formatting bowling response: {e}")
            logger.error(f"Bowling response formatting traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Bowling response formatting failed: {str(e)}")
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"UNEXPECTED ERROR IN BOWLING PHASE STATS SERVICE: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Unexpected error in bowling phase stats service: {str(e)}")
