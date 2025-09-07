from sqlalchemy.sql import text
from fastapi import HTTPException
from typing import List, Optional
from datetime import date
import logging

# Set up detailed logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_true_batting_percentiles(
    team_name: str,
    start_date: Optional[date],
    end_date: Optional[date],
    players: Optional[List[str]],
    benchmark_filter: str,
    benchmark_params: dict,
    db
) -> dict:
    """
    Calculate true SQL percentiles for batting statistics using actual benchmark data
    
    Args:
        team_name: Name of team or "Custom Players"
        start_date, end_date: Date filters
        players: Optional list of custom players
        benchmark_filter: SQL filter for benchmark context (league/international)
        benchmark_params: Parameters for benchmark query
        db: Database session
        
    Returns:
        Dict with percentile breakpoints for all phases and metrics
    """
    logger.info("=== CALCULATING TRUE BATTING PERCENTILES ===")
    
    try:
        # Set up exclusion filter based on whether using custom players or teams
        use_custom_players = players is not None and len(players) > 0
        
        if use_custom_players:
            # For custom players, we can't easily exclude them from team-based benchmarks
            # So we'll use all teams as benchmarks
            exclude_filter = "1=1"  # No exclusion for custom players
        else:
            # For teams, exclude the target team from benchmarks
            exclude_filter = "bs.batting_team != ANY(:team_variations)"
        
        # Calculate TRUE SQL percentiles from benchmark teams
        true_percentiles_query = text(f"""
            WITH benchmark_teams AS (
                SELECT 
                    bs.batting_team,
                    -- Calculate team-level phase stats
                    SUM(bs.pp_runs)::float / NULLIF(SUM(bs.pp_wickets), 0) as team_pp_avg,
                    SUM(bs.pp_runs)::float * 100 / NULLIF(SUM(bs.pp_balls), 0) as team_pp_sr,
                    SUM(bs.middle_runs)::float / NULLIF(SUM(bs.middle_wickets), 0) as team_middle_avg,
                    SUM(bs.middle_runs)::float * 100 / NULLIF(SUM(bs.middle_balls), 0) as team_middle_sr,
                    SUM(bs.death_runs)::float / NULLIF(SUM(bs.death_wickets), 0) as team_death_avg,
                    SUM(bs.death_runs)::float * 100 / NULLIF(SUM(bs.death_balls), 0) as team_death_sr,
                    -- Include balls for minimum sample size filtering
                    SUM(bs.pp_balls) as total_pp_balls,
                    SUM(bs.middle_balls) as total_middle_balls,
                    SUM(bs.death_balls) as total_death_balls
                FROM batting_stats bs
                INNER JOIN matches m ON bs.match_id = m.id
                WHERE {benchmark_filter}
                AND {exclude_filter}
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                GROUP BY bs.batting_team
                -- Minimum sample size requirements (at least 10 overs per phase)
                HAVING SUM(bs.pp_balls) >= 60 
                AND SUM(bs.middle_balls) >= 60 
                AND SUM(bs.death_balls) >= 30
            ),
            percentile_benchmarks AS (
                SELECT 
                    COUNT(*) as benchmark_teams_count,
                    
                    -- PP Strike Rate percentiles
                    percentile_cont(0.10) WITHIN GROUP (ORDER BY team_pp_sr) as pp_sr_p10,
                    percentile_cont(0.25) WITHIN GROUP (ORDER BY team_pp_sr) as pp_sr_p25,
                    percentile_cont(0.50) WITHIN GROUP (ORDER BY team_pp_sr) as pp_sr_p50,
                    percentile_cont(0.75) WITHIN GROUP (ORDER BY team_pp_sr) as pp_sr_p75,
                    percentile_cont(0.90) WITHIN GROUP (ORDER BY team_pp_sr) as pp_sr_p90,
                    
                    -- PP Average percentiles (exclude NULLs where no wickets)
                    percentile_cont(0.10) WITHIN GROUP (ORDER BY team_pp_avg) FILTER (WHERE team_pp_avg IS NOT NULL) as pp_avg_p10,
                    percentile_cont(0.25) WITHIN GROUP (ORDER BY team_pp_avg) FILTER (WHERE team_pp_avg IS NOT NULL) as pp_avg_p25,
                    percentile_cont(0.50) WITHIN GROUP (ORDER BY team_pp_avg) FILTER (WHERE team_pp_avg IS NOT NULL) as pp_avg_p50,
                    percentile_cont(0.75) WITHIN GROUP (ORDER BY team_pp_avg) FILTER (WHERE team_pp_avg IS NOT NULL) as pp_avg_p75,
                    percentile_cont(0.90) WITHIN GROUP (ORDER BY team_pp_avg) FILTER (WHERE team_pp_avg IS NOT NULL) as pp_avg_p90,
                    
                    -- Middle Strike Rate percentiles
                    percentile_cont(0.10) WITHIN GROUP (ORDER BY team_middle_sr) as middle_sr_p10,
                    percentile_cont(0.25) WITHIN GROUP (ORDER BY team_middle_sr) as middle_sr_p25,
                    percentile_cont(0.50) WITHIN GROUP (ORDER BY team_middle_sr) as middle_sr_p50,
                    percentile_cont(0.75) WITHIN GROUP (ORDER BY team_middle_sr) as middle_sr_p75,
                    percentile_cont(0.90) WITHIN GROUP (ORDER BY team_middle_sr) as middle_sr_p90,
                    
                    -- Middle Average percentiles
                    percentile_cont(0.10) WITHIN GROUP (ORDER BY team_middle_avg) FILTER (WHERE team_middle_avg IS NOT NULL) as middle_avg_p10,
                    percentile_cont(0.25) WITHIN GROUP (ORDER BY team_middle_avg) FILTER (WHERE team_middle_avg IS NOT NULL) as middle_avg_p25,
                    percentile_cont(0.50) WITHIN GROUP (ORDER BY team_middle_avg) FILTER (WHERE team_middle_avg IS NOT NULL) as middle_avg_p50,
                    percentile_cont(0.75) WITHIN GROUP (ORDER BY team_middle_avg) FILTER (WHERE team_middle_avg IS NOT NULL) as middle_avg_p75,
                    percentile_cont(0.90) WITHIN GROUP (ORDER BY team_middle_avg) FILTER (WHERE team_middle_avg IS NOT NULL) as middle_avg_p90,
                    
                    -- Death Strike Rate percentiles
                    percentile_cont(0.10) WITHIN GROUP (ORDER BY team_death_sr) as death_sr_p10,
                    percentile_cont(0.25) WITHIN GROUP (ORDER BY team_death_sr) as death_sr_p25,
                    percentile_cont(0.50) WITHIN GROUP (ORDER BY team_death_sr) as death_sr_p50,
                    percentile_cont(0.75) WITHIN GROUP (ORDER BY team_death_sr) as death_sr_p75,
                    percentile_cont(0.90) WITHIN GROUP (ORDER BY team_death_sr) as death_sr_p90,
                    
                    -- Death Average percentiles
                    percentile_cont(0.10) WITHIN GROUP (ORDER BY team_death_avg) FILTER (WHERE team_death_avg IS NOT NULL) as death_avg_p10,
                    percentile_cont(0.25) WITHIN GROUP (ORDER BY team_death_avg) FILTER (WHERE team_death_avg IS NOT NULL) as death_avg_p25,
                    percentile_cont(0.50) WITHIN GROUP (ORDER BY team_death_avg) FILTER (WHERE team_death_avg IS NOT NULL) as death_avg_p50,
                    percentile_cont(0.75) WITHIN GROUP (ORDER BY team_death_avg) FILTER (WHERE team_death_avg IS NOT NULL) as death_avg_p75,
                    percentile_cont(0.90) WITHIN GROUP (ORDER BY team_death_avg) FILTER (WHERE team_death_avg IS NOT NULL) as death_avg_p90
                    
                FROM benchmark_teams
            )
            SELECT * FROM percentile_benchmarks
        """)
        
        logger.info(f"Executing true percentiles query with params: {benchmark_params}")
        percentiles_result = db.execute(true_percentiles_query, benchmark_params).fetchone()
        
        if not percentiles_result or percentiles_result.benchmark_teams_count < 3:
            logger.warning(f"Insufficient benchmark data: {percentiles_result.benchmark_teams_count if percentiles_result else 0} teams")
            return None  # Signal to fall back to simplified normalization
        
        logger.info(f"Successfully calculated percentiles from {percentiles_result.benchmark_teams_count} benchmark teams")
        
        # Return percentile breakpoints for use in normalization
        return {
            "benchmark_teams_count": percentiles_result.benchmark_teams_count,
            "pp_sr": {
                "p10": float(percentiles_result.pp_sr_p10),
                "p25": float(percentiles_result.pp_sr_p25),
                "p50": float(percentiles_result.pp_sr_p50),
                "p75": float(percentiles_result.pp_sr_p75),
                "p90": float(percentiles_result.pp_sr_p90)
            },
            "pp_avg": {
                "p10": float(percentiles_result.pp_avg_p10) if percentiles_result.pp_avg_p10 else None,
                "p25": float(percentiles_result.pp_avg_p25) if percentiles_result.pp_avg_p25 else None,
                "p50": float(percentiles_result.pp_avg_p50) if percentiles_result.pp_avg_p50 else None,
                "p75": float(percentiles_result.pp_avg_p75) if percentiles_result.pp_avg_p75 else None,
                "p90": float(percentiles_result.pp_avg_p90) if percentiles_result.pp_avg_p90 else None
            },
            "middle_sr": {
                "p10": float(percentiles_result.middle_sr_p10),
                "p25": float(percentiles_result.middle_sr_p25),
                "p50": float(percentiles_result.middle_sr_p50),
                "p75": float(percentiles_result.middle_sr_p75),
                "p90": float(percentiles_result.middle_sr_p90)
            },
            "middle_avg": {
                "p10": float(percentiles_result.middle_avg_p10) if percentiles_result.middle_avg_p10 else None,
                "p25": float(percentiles_result.middle_avg_p25) if percentiles_result.middle_avg_p25 else None,
                "p50": float(percentiles_result.middle_avg_p50) if percentiles_result.middle_avg_p50 else None,
                "p75": float(percentiles_result.middle_avg_p75) if percentiles_result.middle_avg_p75 else None,
                "p90": float(percentiles_result.middle_avg_p90) if percentiles_result.middle_avg_p90 else None
            },
            "death_sr": {
                "p10": float(percentiles_result.death_sr_p10),
                "p25": float(percentiles_result.death_sr_p25),
                "p50": float(percentiles_result.death_sr_p50),
                "p75": float(percentiles_result.death_sr_p75),
                "p90": float(percentiles_result.death_sr_p90)
            },
            "death_avg": {
                "p10": float(percentiles_result.death_avg_p10) if percentiles_result.death_avg_p10 else None,
                "p25": float(percentiles_result.death_avg_p25) if percentiles_result.death_avg_p25 else None,
                "p50": float(percentiles_result.death_avg_p50) if percentiles_result.death_avg_p50 else None,
                "p75": float(percentiles_result.death_avg_p75) if percentiles_result.death_avg_p75 else None,
                "p90": float(percentiles_result.death_avg_p90) if percentiles_result.death_avg_p90 else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating true percentiles: {str(e)}")
        return None  # Signal to fall back to simplified normalization


def calculate_true_percentile_score(value, percentile_breakpoints):
    """
    Calculate exact percentile score using SQL percentile breakpoints
    
    Args:
        value: The value to score (e.g., strike rate or average)
        percentile_breakpoints: Dict with p10, p25, p50, p75, p90 values
        
    Returns:
        Percentile score between 5-95
    """
    if value is None:
        return 50  # Default for NULL averages (no wickets)
    
    # Handle case where all percentile breakpoints are None (no data)
    if all(p is None for p in percentile_breakpoints.values()):
        return 50
    
    p10 = percentile_breakpoints.get("p10", 0)
    p25 = percentile_breakpoints.get("p25", 0)
    p50 = percentile_breakpoints.get("p50", 0)
    p75 = percentile_breakpoints.get("p75", 0)
    p90 = percentile_breakpoints.get("p90", 0)
    
    # Handle None values in percentiles (shouldn't happen for strike rates, but safety check)
    if any(p is None for p in [p10, p25, p50, p75, p90]):
        return 50
    
    # Linear interpolation between percentile breakpoints
    if value <= p10:
        return 10
    elif value <= p25:
        return 10 + ((value - p10) / (p25 - p10)) * 15
    elif value <= p50:
        return 25 + ((value - p25) / (p50 - p25)) * 25
    elif value <= p75:
        return 50 + ((value - p50) / (p75 - p50)) * 25
    elif value <= p90:
        return 75 + ((value - p75) / (p90 - p75)) * 15
    else:
        # Cap at 95th percentile for extreme outliers
        return min(95, 90 + ((value - p90) / max(p90, 1)) * 5)


def calculate_true_percentile_score_for_average(value, percentile_breakpoints):
    """
    Special handling for batting averages which can be None when no wickets taken
    
    Args:
        value: The batting average (can be None)
        percentile_breakpoints: Dict with p10, p25, p50, p75, p90 values
        
    Returns:
        Percentile score between 5-95, or 50 if value is None
    """
    if value is None:
        return 50  # Default for no wickets taken - treat as median performance
    
    # Check if we have any valid percentile data for averages
    valid_percentiles = {k: v for k, v in percentile_breakpoints.items() if v is not None}
    
    if len(valid_percentiles) < 3:  # Need at least 3 percentiles for interpolation
        return 50  # Fall back to median if insufficient percentile data
    
    return calculate_true_percentile_score(value, percentile_breakpoints)


def apply_true_batting_percentiles(team_stats, percentile_data):
    """
    Apply true percentile calculations to team batting stats
    
    Args:
        team_stats: Dict with team's batting statistics
        percentile_data: Dict with percentile breakpoints from calculate_true_batting_percentiles
        
    Returns:
        Dict with normalized percentile scores
    """
    logger.info("Applying true batting percentiles to team stats")
    
    # Calculate percentiles for each phase and metric
    pp_avg_percentile = calculate_true_percentile_score_for_average(
        team_stats.get("pp_average"), 
        percentile_data["pp_avg"]
    )
    
    pp_sr_percentile = calculate_true_percentile_score(
        team_stats.get("pp_strike_rate"), 
        percentile_data["pp_sr"]
    )
    
    middle_avg_percentile = calculate_true_percentile_score_for_average(
        team_stats.get("middle_average"), 
        percentile_data["middle_avg"]
    )
    
    middle_sr_percentile = calculate_true_percentile_score(
        team_stats.get("middle_strike_rate"), 
        percentile_data["middle_sr"]
    )
    
    death_avg_percentile = calculate_true_percentile_score_for_average(
        team_stats.get("death_average"), 
        percentile_data["death_avg"]
    )
    
    death_sr_percentile = calculate_true_percentile_score(
        team_stats.get("death_strike_rate"), 
        percentile_data["death_sr"]
    )
    
    logger.info(f"Calculated percentiles - PP SR: {pp_sr_percentile:.1f}, Middle SR: {middle_sr_percentile:.1f}, Death SR: {death_sr_percentile:.1f}")
    
    return {
        "pp_avg_percentile": round(pp_avg_percentile, 1),
        "pp_sr_percentile": round(pp_sr_percentile, 1),
        "middle_avg_percentile": round(middle_avg_percentile, 1),
        "middle_sr_percentile": round(middle_sr_percentile, 1),
        "death_avg_percentile": round(death_avg_percentile, 1),
        "death_sr_percentile": round(death_sr_percentile, 1),
        "benchmark_teams_count": percentile_data["benchmark_teams_count"]
    }
