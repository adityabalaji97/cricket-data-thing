from sqlalchemy.sql import text
from fastapi import HTTPException
from typing import List, Optional
from datetime import date
from models import teams_mapping
from services.teams import get_all_team_name_variations

def get_team_batting_order_service(
    team_name: str,
    start_date: Optional[date],
    end_date: Optional[date],
    players: Optional[List[str]],
    db
) -> dict:
    """
    Get batting order with aggregated overall and phase-wise statistics
    Supports both team-based and custom player list queries
    """
    try:
        if players:
            # Custom player list mode
            player_filter = "bs.striker = ANY(:players)"
            filter_params = {"players": players}
        else:
            # Team-based mode
            team_variations = get_all_team_name_variations(team_name)
            player_filter = "bs.batting_team = ANY(:team_variations)"
            filter_params = {"team_variations": team_variations}
        
        # Add date parameters
        filter_params.update({
            "start_date": start_date,
            "end_date": end_date
        })
        
        batting_order_query = text(f"""
            WITH player_position_frequency AS (
                -- Find most frequent batting position for each player
                SELECT 
                    bs.striker,
                    bs.batting_position,
                    COUNT(*) as position_frequency,
                    ROW_NUMBER() OVER (PARTITION BY bs.striker ORDER BY COUNT(*) DESC, bs.batting_position ASC) as position_rank
                FROM batting_stats bs
                INNER JOIN matches m ON bs.match_id = m.id
                WHERE {player_filter}
                AND bs.batting_position IS NOT NULL
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                GROUP BY bs.striker, bs.batting_position
            ),
            primary_positions AS (
                -- Get primary batting position for each player
                SELECT 
                    striker,
                    batting_position as primary_batting_position,
                    position_frequency
                FROM player_position_frequency
                WHERE position_rank = 1
            ),
            player_aggregates AS (
                -- Aggregate all stats for each player
                SELECT 
                    bs.striker,
                    COUNT(DISTINCT bs.match_id) as total_innings,
                    
                    -- Overall stats
                    COALESCE(SUM(bs.runs), 0) as total_runs,
                    COALESCE(SUM(bs.balls_faced), 0) as total_balls,
                    COALESCE(SUM(bs.wickets), 0) as total_wickets,
                    COALESCE(SUM(bs.fours), 0) as total_fours,
                    COALESCE(SUM(bs.sixes), 0) as total_sixes,
                    COALESCE(SUM(bs.dots), 0) as total_dots,
                    
                    -- Phase-wise stats
                    COALESCE(SUM(bs.pp_runs), 0) as pp_runs,
                    COALESCE(SUM(bs.pp_balls), 0) as pp_balls,
                    COALESCE(SUM(bs.pp_wickets), 0) as pp_wickets,
                    COALESCE(SUM(bs.pp_dots), 0) as pp_dots,
                    COALESCE(SUM(bs.pp_boundaries), 0) as pp_boundaries,
                    
                    COALESCE(SUM(bs.middle_runs), 0) as middle_runs,
                    COALESCE(SUM(bs.middle_balls), 0) as middle_balls,
                    COALESCE(SUM(bs.middle_wickets), 0) as middle_wickets,
                    COALESCE(SUM(bs.middle_dots), 0) as middle_dots,
                    COALESCE(SUM(bs.middle_boundaries), 0) as middle_boundaries,
                    
                    COALESCE(SUM(bs.death_runs), 0) as death_runs,
                    COALESCE(SUM(bs.death_balls), 0) as death_balls,
                    COALESCE(SUM(bs.death_wickets), 0) as death_wickets,
                    COALESCE(SUM(bs.death_dots), 0) as death_dots,
                    COALESCE(SUM(bs.death_boundaries), 0) as death_boundaries
                    
                FROM batting_stats bs
                INNER JOIN matches m ON bs.match_id = m.id
                WHERE {player_filter}
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                GROUP BY bs.striker
            )
            SELECT 
                pa.striker,
                pp.primary_batting_position,
                pp.position_frequency,
                pa.total_innings,
                
                -- Overall calculated metrics
                pa.total_runs,
                pa.total_balls,
                pa.total_wickets,
                pa.total_fours,
                pa.total_sixes,
                pa.total_dots,
                CASE WHEN pa.total_wickets > 0 THEN ROUND(pa.total_runs::numeric / pa.total_wickets, 2) ELSE NULL END as overall_average,
                CASE WHEN pa.total_balls > 0 THEN ROUND(pa.total_runs::numeric * 100 / pa.total_balls, 2) ELSE 0 END as overall_strike_rate,
                CASE WHEN pa.total_balls > 0 THEN ROUND((pa.total_fours + pa.total_sixes)::numeric * 100 / pa.total_balls, 2) ELSE 0 END as overall_boundary_percentage,
                CASE WHEN pa.total_balls > 0 THEN ROUND(pa.total_dots::numeric * 100 / pa.total_balls, 2) ELSE 0 END as overall_dot_percentage,
                
                -- Powerplay calculated metrics
                pa.pp_runs,
                pa.pp_balls,
                pa.pp_wickets,
                pa.pp_dots,
                pa.pp_boundaries,
                CASE WHEN pa.pp_wickets > 0 THEN ROUND(pa.pp_runs::numeric / pa.pp_wickets, 2) ELSE NULL END as pp_average,
                CASE WHEN pa.pp_balls > 0 THEN ROUND(pa.pp_runs::numeric * 100 / pa.pp_balls, 2) ELSE 0 END as pp_strike_rate,
                CASE WHEN pa.pp_balls > 0 THEN ROUND(pa.pp_boundaries::numeric * 100 / pa.pp_balls, 2) ELSE 0 END as pp_boundary_percentage,
                CASE WHEN pa.pp_balls > 0 THEN ROUND(pa.pp_dots::numeric * 100 / pa.pp_balls, 2) ELSE 0 END as pp_dot_percentage,
                
                -- Middle overs calculated metrics
                pa.middle_runs,
                pa.middle_balls,
                pa.middle_wickets,
                pa.middle_dots,
                pa.middle_boundaries,
                CASE WHEN pa.middle_wickets > 0 THEN ROUND(pa.middle_runs::numeric / pa.middle_wickets, 2) ELSE NULL END as middle_average,
                CASE WHEN pa.middle_balls > 0 THEN ROUND(pa.middle_runs::numeric * 100 / pa.middle_balls, 2) ELSE 0 END as middle_strike_rate,
                CASE WHEN pa.middle_balls > 0 THEN ROUND(pa.middle_boundaries::numeric * 100 / pa.middle_balls, 2) ELSE 0 END as middle_boundary_percentage,
                CASE WHEN pa.middle_balls > 0 THEN ROUND(pa.middle_dots::numeric * 100 / pa.middle_balls, 2) ELSE 0 END as middle_dot_percentage,
                
                -- Death overs calculated metrics
                pa.death_runs,
                pa.death_balls,
                pa.death_wickets,
                pa.death_dots,
                pa.death_boundaries,
                CASE WHEN pa.death_wickets > 0 THEN ROUND(pa.death_runs::numeric / pa.death_wickets, 2) ELSE NULL END as death_average,
                CASE WHEN pa.death_balls > 0 THEN ROUND(pa.death_runs::numeric * 100 / pa.death_balls, 2) ELSE 0 END as death_strike_rate,
                CASE WHEN pa.death_balls > 0 THEN ROUND(pa.death_boundaries::numeric * 100 / pa.death_balls, 2) ELSE 0 END as death_boundary_percentage,
                CASE WHEN pa.death_balls > 0 THEN ROUND(pa.death_dots::numeric * 100 / pa.death_balls, 2) ELSE 0 END as death_dot_percentage
                
            FROM player_aggregates pa
            LEFT JOIN primary_positions pp ON pa.striker = pp.striker
            WHERE pa.total_balls > 0  -- Only include players who have faced balls
            ORDER BY COALESCE(pp.primary_batting_position, 99), pa.total_runs DESC
        """)
        
        results = db.execute(batting_order_query, filter_params).fetchall()
        
        batting_order = []
        for row in results:
            player_data = {
                "player": row.striker,
                "primary_batting_position": row.primary_batting_position or 0,
                "position_frequency": row.position_frequency or 0,
                "total_innings": row.total_innings,
                "overall": {
                    "runs": row.total_runs,
                    "balls": row.total_balls,
                    "wickets": row.total_wickets,
                    "average": float(row.overall_average) if row.overall_average else None,
                    "strike_rate": float(row.overall_strike_rate),
                    "boundary_percentage": float(row.overall_boundary_percentage),
                    "dot_percentage": float(row.overall_dot_percentage),
                    "fours": row.total_fours,
                    "sixes": row.total_sixes
                },
                "powerplay": {
                    "runs": row.pp_runs,
                    "balls": row.pp_balls,
                    "wickets": row.pp_wickets,
                    "average": float(row.pp_average) if row.pp_average else None,
                    "strike_rate": float(row.pp_strike_rate),
                    "boundary_percentage": float(row.pp_boundary_percentage),
                    "dot_percentage": float(row.pp_dot_percentage)
                },
                "middle_overs": {
                    "runs": row.middle_runs,
                    "balls": row.middle_balls,
                    "wickets": row.middle_wickets,
                    "average": float(row.middle_average) if row.middle_average else None,
                    "strike_rate": float(row.middle_strike_rate),
                    "boundary_percentage": float(row.middle_boundary_percentage),
                    "dot_percentage": float(row.middle_dot_percentage)
                },
                "death_overs": {
                    "runs": row.death_runs,
                    "balls": row.death_balls,
                    "wickets": row.death_wickets,
                    "average": float(row.death_average) if row.death_average else None,
                    "strike_rate": float(row.death_strike_rate),
                    "boundary_percentage": float(row.death_boundary_percentage),
                    "dot_percentage": float(row.death_dot_percentage)
                }
            }
            batting_order.append(player_data)
        
        return {
            "team": team_name if not players else "Custom Players",
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "total_players": len(batting_order),
            "batting_order": batting_order
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching team batting order: {str(e)}")
