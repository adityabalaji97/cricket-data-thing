from sqlalchemy.sql import text
from fastapi import HTTPException
from typing import List, Optional
from datetime import date
from models import teams_mapping, Match, BattingStats
import logging
import traceback

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
    db
) -> dict:
    """
    Get aggregated phase-wise batting statistics for a team with FIXED SQL queries
    """
    logger.info(f"=== STARTING PHASE STATS SERVICE (FIXED VERSION) ===")
    logger.info(f"Team: {team_name}, Start: {start_date}, End: {end_date}")
    
    try:
        # Step 1: Get team variations
        logger.info("Step 1: Getting team variations")
        team_variations = get_all_team_name_variations(team_name)
        logger.info(f"Team variations: {team_variations}")
        
        # Step 2: Determine team type
        logger.info("Step 2: Determining team type")
        from models import INTERNATIONAL_TEAMS_RANKED
        is_international_team = any(variation in INTERNATIONAL_TEAMS_RANKED for variation in team_variations)
        logger.info(f"Is international team: {is_international_team}")
        
        # Step 3: Get team's phase stats
        logger.info("Step 3: Executing team phase stats query")
        team_phase_stats_query = text("""
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
                WHERE bs.batting_team = ANY(:team_variations)
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
        
        team_params = {
            "team_variations": team_variations,
            "start_date": start_date,
            "end_date": end_date
        }
        logger.info(f"Team query parameters: {team_params}")
        
        try:
            team_result = db.execute(team_phase_stats_query, team_params).fetchone()
            logger.info(f"Team query executed successfully")
            
            if team_result:
                logger.info(f"Team stats: matches={team_result.total_matches}, pp_runs={team_result.total_pp_runs}")
            else:
                logger.warning("Team query returned no results")
                
        except Exception as e:
            logger.error(f"TEAM QUERY FAILED: {str(e)}")
            logger.error(f"Team query traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Team query failed: {str(e)}")
        
        # Step 4: Handle no data case
        if not team_result or team_result.total_matches == 0:
            logger.info("No team data found, returning default values")
            return {
                "powerplay": {"runs": 0, "balls": 0, "wickets": 0, "average": 0, "strike_rate": 0, "normalized_average": 50, "normalized_strike_rate": 50},
                "middle_overs": {"runs": 0, "balls": 0, "wickets": 0, "average": 0, "strike_rate": 0, "normalized_average": 50, "normalized_strike_rate": 50},
                "death_overs": {"runs": 0, "balls": 0, "wickets": 0, "average": 0, "strike_rate": 0, "normalized_average": 50, "normalized_strike_rate": 50},
                "total_matches": 0, "context": "No data", "benchmark_teams": 0
            }
        
        # Step 5: Determine benchmark context
        logger.info("Step 5: Determining benchmark context")
        if is_international_team:
            context = "International Teams"
            benchmark_filter = "m.match_type = 'international'"
            league_param = None
            logger.info("Using international team benchmarking")
        else:
            # FIXED: Get the league from recent matches - fix the SQL query
            logger.info("Getting league for benchmarking")
            league_query = text("""
                SELECT m.competition, m.date
                FROM matches m
                INNER JOIN batting_stats bs ON m.id = bs.match_id
                WHERE bs.batting_team = ANY(:team_variations)
                AND m.match_type = 'league'
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                ORDER BY m.date DESC 
                LIMIT 1
            """)
            
            try:
                league_result = db.execute(league_query, {
                    "team_variations": team_variations,
                    "start_date": start_date,
                    "end_date": end_date
                }).fetchone()
                
                league_param = league_result.competition if league_result else None
                context = f"{league_param} Teams" if league_param else "League Teams"
                benchmark_filter = "m.match_type = 'league' AND (:league_param IS NULL OR m.competition = :league_param)"
                logger.info(f"League query successful: league_param={league_param}, context={context}")
                
            except Exception as e:
                logger.error(f"LEAGUE QUERY FAILED: {str(e)}")
                logger.error(f"League query traceback: {traceback.format_exc()}")
                raise HTTPException(status_code=500, detail=f"League query failed: {str(e)}")
        
        # Step 6: Execute SIMPLIFIED benchmark query (remove complex percentiles for now)
        logger.info("Step 6: Executing simplified benchmark query")
        benchmark_query = text(f"""
            WITH team_stats AS (
                SELECT 
                    bs.batting_team,
                    SUM(bs.pp_runs)::float / NULLIF(SUM(bs.pp_wickets), 0) as team_pp_avg,
                    SUM(bs.pp_runs)::float * 100 / NULLIF(SUM(bs.pp_balls), 0) as team_pp_sr,
                    SUM(bs.middle_runs)::float / NULLIF(SUM(bs.middle_wickets), 0) as team_middle_avg,
                    SUM(bs.middle_runs)::float * 100 / NULLIF(SUM(bs.middle_balls), 0) as team_middle_sr,
                    SUM(bs.death_runs)::float / NULLIF(SUM(bs.death_wickets), 0) as team_death_avg,
                    SUM(bs.death_runs)::float * 100 / NULLIF(SUM(bs.death_balls), 0) as team_death_sr
                FROM batting_stats bs
                INNER JOIN matches m ON bs.match_id = m.id
                WHERE {benchmark_filter}
                AND bs.batting_team != ANY(:team_variations)
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                GROUP BY bs.batting_team
                HAVING SUM(bs.pp_balls) > 0 AND SUM(bs.middle_balls) > 0 AND SUM(bs.death_balls) > 0
            )
            SELECT 
                COUNT(*) as benchmark_teams,
                AVG(team_pp_avg) as pp_avg_mean,
                STDDEV(team_pp_avg) as pp_avg_stddev,
                AVG(team_pp_sr) as pp_sr_mean,
                STDDEV(team_pp_sr) as pp_sr_stddev,
                AVG(team_middle_avg) as middle_avg_mean,
                STDDEV(team_middle_avg) as middle_avg_stddev,
                AVG(team_middle_sr) as middle_sr_mean,
                STDDEV(team_middle_sr) as middle_sr_stddev,
                AVG(team_death_avg) as death_avg_mean,
                STDDEV(team_death_avg) as death_avg_stddev,
                AVG(team_death_sr) as death_sr_mean,
                STDDEV(team_death_sr) as death_sr_stddev
            FROM team_stats
        """)
        
        # Execute benchmark query with proper parameters
        benchmark_params = {
            "team_variations": team_variations,
            "start_date": start_date,
            "end_date": end_date
        }
        if not is_international_team:
            benchmark_params["league_param"] = league_param
            
        logger.info(f"Benchmark query parameters: {benchmark_params}")
        
        try:
            benchmark_result = db.execute(benchmark_query, benchmark_params).fetchone()
            logger.info(f"Simplified benchmark query executed successfully")
            
            if benchmark_result:
                logger.info(f"Benchmark stats: teams={benchmark_result.benchmark_teams}")
            else:
                logger.warning("Benchmark query returned no results")
                
        except Exception as e:
            logger.error(f"BENCHMARK QUERY FAILED: {str(e)}")
            logger.error(f"Benchmark query traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Benchmark query failed: {str(e)}")
        
        # Step 7: Use SIMPLE normalization (remove complex percentile calculations)
        logger.info("Step 7: Using simplified normalization")
        
        # Extract team stats
        team_pp_avg = float(team_result.pp_average) if team_result.pp_average else None
        team_pp_sr = float(team_result.pp_strike_rate) if team_result.pp_strike_rate else 0
        team_middle_avg = float(team_result.middle_average) if team_result.middle_average else None
        team_middle_sr = float(team_result.middle_strike_rate) if team_result.middle_strike_rate else 0
        team_death_avg = float(team_result.death_average) if team_result.death_average else None
        team_death_sr = float(team_result.death_strike_rate) if team_result.death_strike_rate else 0
        
        logger.info(f"Team stats extracted - PP: avg={team_pp_avg}, sr={team_pp_sr}")
        
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
        
        context += " (Simplified normalization)"
        logger.info("Simplified normalization completed successfully")
        
        # Step 8: Format response
        logger.info("Step 8: Formatting response")
        
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
                "benchmark_teams": benchmark_result.benchmark_teams if benchmark_result else 0
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
