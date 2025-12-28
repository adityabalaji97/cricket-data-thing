from sqlalchemy.sql import text
from fastapi import HTTPException
from typing import List, Optional
from datetime import date
from models import teams_mapping
from services.teams import get_all_team_name_variations
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_team_bowling_order_service(
    team_name: str,
    start_date: Optional[date],
    end_date: Optional[date],
    players: Optional[List[str]],
    db
) -> dict:
    """
    Get bowling order with aggregated overall and phase-wise statistics.
    Uses hybrid approach - checks both deliveries (legacy) and delivery_details (new) tables.
    """
    try:
        logger.info(f"Starting bowling order service for team: {team_name}, players: {players}")
        
        if players:
            player_filter = "bs.bowler = ANY(:players)"
            filter_params = {"players": players}
        else:
            team_variations = get_all_team_name_variations(team_name)
            player_filter = "bs.bowling_team = ANY(:team_variations)"
            filter_params = {"team_variations": team_variations}
        
        filter_params.update({
            "start_date": start_date,
            "end_date": end_date
        })
        
        # Hybrid query using both deliveries and delivery_details tables
        bowling_order_query = text(f"""
            WITH 
            -- Over combinations from LEGACY deliveries table
            legacy_bowler_overs AS (
                SELECT 
                    d.bowler,
                    d.match_id,
                    d.innings,
                    d.over,
                    COUNT(CASE WHEN COALESCE(d.wides, 0) = 0 AND COALESCE(d.noballs, 0) = 0 THEN 1 END) as legal_balls
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE d.bowler IS NOT NULL
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                GROUP BY d.bowler, d.match_id, d.innings, d.over
                HAVING COUNT(CASE WHEN COALESCE(d.wides, 0) = 0 AND COALESCE(d.noballs, 0) = 0 THEN 1 END) >= 3
            ),
            -- Over combinations from NEW delivery_details table
            dd_bowler_overs AS (
                SELECT 
                    dd.bowl as bowler,
                    dd.p_match as match_id,
                    dd.inns as innings,
                    dd.over,
                    COUNT(CASE WHEN COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 END) as legal_balls
                FROM delivery_details dd
                JOIN matches m ON dd.p_match = m.id
                WHERE dd.bowl IS NOT NULL
                AND dd.p_match IS NOT NULL
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                GROUP BY dd.bowl, dd.p_match, dd.inns, dd.over
                HAVING COUNT(CASE WHEN COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 END) >= 3
            ),
            -- Combined bowler overs (UNION removes duplicates)
            combined_bowler_overs AS (
                SELECT * FROM legacy_bowler_overs
                UNION
                SELECT * FROM dd_bowler_overs
            ),
            innings_overs AS (
                SELECT 
                    bowler,
                    match_id,
                    innings,
                    ARRAY_AGG(over ORDER BY over) as overs_bowled,
                    COUNT(*) as num_overs
                FROM combined_bowler_overs
                GROUP BY bowler, match_id, innings
                HAVING COUNT(*) >= 2
            ),
            over_combinations AS (
                SELECT 
                    bowler,
                    overs_bowled,
                    COUNT(*) as frequency
                FROM innings_overs
                GROUP BY bowler, overs_bowled
            ),
            top_combinations AS (
                SELECT 
                    bowler,
                    overs_bowled,
                    frequency,
                    ROW_NUMBER() OVER (PARTITION BY bowler ORDER BY frequency DESC, overs_bowled) as combo_rank
                FROM over_combinations
            ),
            player_over_combinations AS (
                SELECT 
                    bowler,
                    overs_bowled as most_frequent_overs,
                    frequency as over_combination_frequency
                FROM top_combinations
                WHERE combo_rank = 1
            ),
            player_aggregates AS (
                SELECT 
                    bs.bowler,
                    COUNT(DISTINCT bs.match_id) as total_innings,
                    COALESCE(SUM(CAST(bs.overs AS NUMERIC) * 6), 0) as total_balls,
                    COALESCE(SUM(bs.runs_conceded), 0) as total_runs,
                    COALESCE(SUM(bs.wickets), 0) as total_wickets,
                    COALESCE(SUM(bs.dots), 0) as total_dots,
                    COALESCE(SUM(bs.fours_conceded), 0) as total_fours,
                    COALESCE(SUM(bs.sixes_conceded), 0) as total_sixes,
                    
                    COALESCE(SUM(CAST(COALESCE(bs.pp_overs, 0) AS NUMERIC) * 6), 0) as pp_balls,
                    COALESCE(SUM(COALESCE(bs.pp_runs, 0)), 0) as pp_runs,
                    COALESCE(SUM(COALESCE(bs.pp_wickets, 0)), 0) as pp_wickets,
                    COALESCE(SUM(COALESCE(bs.pp_dots, 0)), 0) as pp_dots,
                    COALESCE(SUM(COALESCE(bs.pp_boundaries, 0)), 0) as pp_boundaries,
                    
                    COALESCE(SUM(CAST(COALESCE(bs.middle_overs, 0) AS NUMERIC) * 6), 0) as middle_balls,
                    COALESCE(SUM(COALESCE(bs.middle_runs, 0)), 0) as middle_runs,
                    COALESCE(SUM(COALESCE(bs.middle_wickets, 0)), 0) as middle_wickets,
                    COALESCE(SUM(COALESCE(bs.middle_dots, 0)), 0) as middle_dots,
                    COALESCE(SUM(COALESCE(bs.middle_boundaries, 0)), 0) as middle_boundaries,
                    
                    COALESCE(SUM(CAST(COALESCE(bs.death_overs, 0) AS NUMERIC) * 6), 0) as death_balls,
                    COALESCE(SUM(COALESCE(bs.death_runs, 0)), 0) as death_runs,
                    COALESCE(SUM(COALESCE(bs.death_wickets, 0)), 0) as death_wickets,
                    COALESCE(SUM(COALESCE(bs.death_dots, 0)), 0) as death_dots,
                    COALESCE(SUM(COALESCE(bs.death_boundaries, 0)), 0) as death_boundaries
                    
                FROM bowling_stats bs
                INNER JOIN matches m ON bs.match_id = m.id
                WHERE {player_filter}
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                GROUP BY bs.bowler
            )
            SELECT 
                pa.bowler,
                COALESCE(poc.most_frequent_overs, ARRAY[]::integer[]) as most_frequent_overs,
                COALESCE(poc.over_combination_frequency, 0) as over_combination_frequency,
                pa.total_innings,
                
                pa.total_balls,
                pa.total_runs,
                pa.total_wickets,
                pa.total_dots,
                pa.total_fours,
                pa.total_sixes,
                CASE WHEN pa.total_wickets > 0 THEN ROUND(CAST(pa.total_runs AS NUMERIC) / CAST(pa.total_wickets AS NUMERIC), 2) ELSE NULL END as overall_average,
                CASE WHEN pa.total_wickets > 0 THEN ROUND(CAST(pa.total_balls AS NUMERIC) / CAST(pa.total_wickets AS NUMERIC), 2) ELSE NULL END as overall_strike_rate,
                CASE WHEN pa.total_balls > 0 THEN ROUND(CAST(pa.total_runs AS NUMERIC) * 6 / CAST(pa.total_balls AS NUMERIC), 2) ELSE 0 END as overall_economy,
                CASE WHEN pa.total_balls > 0 THEN ROUND((CAST(pa.total_fours AS NUMERIC) + CAST(pa.total_sixes AS NUMERIC)) * 100 / CAST(pa.total_balls AS NUMERIC), 2) ELSE 0 END as overall_boundary_percentage,
                CASE WHEN pa.total_balls > 0 THEN ROUND(CAST(pa.total_dots AS NUMERIC) * 100 / CAST(pa.total_balls AS NUMERIC), 2) ELSE 0 END as overall_dot_percentage,
                
                pa.pp_balls, pa.pp_runs, pa.pp_wickets, pa.pp_dots, pa.pp_boundaries,
                CASE WHEN pa.pp_wickets > 0 THEN ROUND(CAST(pa.pp_runs AS NUMERIC) / CAST(pa.pp_wickets AS NUMERIC), 2) ELSE NULL END as pp_average,
                CASE WHEN pa.pp_wickets > 0 THEN ROUND(CAST(pa.pp_balls AS NUMERIC) / CAST(pa.pp_wickets AS NUMERIC), 2) ELSE NULL END as pp_strike_rate,
                CASE WHEN pa.pp_balls > 0 THEN ROUND(CAST(pa.pp_runs AS NUMERIC) * 6 / CAST(pa.pp_balls AS NUMERIC), 2) ELSE 0 END as pp_economy,
                CASE WHEN pa.pp_balls > 0 THEN ROUND(CAST(pa.pp_boundaries AS NUMERIC) * 100 / CAST(pa.pp_balls AS NUMERIC), 2) ELSE 0 END as pp_boundary_percentage,
                CASE WHEN pa.pp_balls > 0 THEN ROUND(CAST(pa.pp_dots AS NUMERIC) * 100 / CAST(pa.pp_balls AS NUMERIC), 2) ELSE 0 END as pp_dot_percentage,
                
                pa.middle_balls, pa.middle_runs, pa.middle_wickets, pa.middle_dots, pa.middle_boundaries,
                CASE WHEN pa.middle_wickets > 0 THEN ROUND(CAST(pa.middle_runs AS NUMERIC) / CAST(pa.middle_wickets AS NUMERIC), 2) ELSE NULL END as middle_average,
                CASE WHEN pa.middle_wickets > 0 THEN ROUND(CAST(pa.middle_balls AS NUMERIC) / CAST(pa.middle_wickets AS NUMERIC), 2) ELSE NULL END as middle_strike_rate,
                CASE WHEN pa.middle_balls > 0 THEN ROUND(CAST(pa.middle_runs AS NUMERIC) * 6 / CAST(pa.middle_balls AS NUMERIC), 2) ELSE 0 END as middle_economy,
                CASE WHEN pa.middle_balls > 0 THEN ROUND(CAST(pa.middle_boundaries AS NUMERIC) * 100 / CAST(pa.middle_balls AS NUMERIC), 2) ELSE 0 END as middle_boundary_percentage,
                CASE WHEN pa.middle_balls > 0 THEN ROUND(CAST(pa.middle_dots AS NUMERIC) * 100 / CAST(pa.middle_balls AS NUMERIC), 2) ELSE 0 END as middle_dot_percentage,
                
                pa.death_balls, pa.death_runs, pa.death_wickets, pa.death_dots, pa.death_boundaries,
                CASE WHEN pa.death_wickets > 0 THEN ROUND(CAST(pa.death_runs AS NUMERIC) / CAST(pa.death_wickets AS NUMERIC), 2) ELSE NULL END as death_average,
                CASE WHEN pa.death_wickets > 0 THEN ROUND(CAST(pa.death_balls AS NUMERIC) / CAST(pa.death_wickets AS NUMERIC), 2) ELSE NULL END as death_strike_rate,
                CASE WHEN pa.death_balls > 0 THEN ROUND(CAST(pa.death_runs AS NUMERIC) * 6 / CAST(pa.death_balls AS NUMERIC), 2) ELSE 0 END as death_economy,
                CASE WHEN pa.death_balls > 0 THEN ROUND(CAST(pa.death_boundaries AS NUMERIC) * 100 / CAST(pa.death_balls AS NUMERIC), 2) ELSE 0 END as death_boundary_percentage,
                CASE WHEN pa.death_balls > 0 THEN ROUND(CAST(pa.death_dots AS NUMERIC) * 100 / CAST(pa.death_balls AS NUMERIC), 2) ELSE 0 END as death_dot_percentage
                
            FROM player_aggregates pa
            LEFT JOIN player_over_combinations poc ON pa.bowler = poc.bowler
            WHERE pa.total_balls > 0
            ORDER BY pa.total_wickets DESC, pa.total_runs ASC
        """)
        
        logger.info("Executing bowling order query...")
        results = db.execute(bowling_order_query, filter_params).fetchall()
        logger.info(f"Query executed successfully, found {len(results)} players")
        
        bowling_order = []
        for row in results:
            over_combination_display = "N/A"
            if row.most_frequent_overs and len(row.most_frequent_overs) > 0:
                over_combination_display = f"[{', '.join(map(str, row.most_frequent_overs))}]"
            
            player_data = {
                "player": row.bowler,
                "most_frequent_overs": over_combination_display,
                "over_combination_frequency": row.over_combination_frequency or 0,
                "total_innings": row.total_innings,
                "overall": {
                    "balls": int(row.total_balls),
                    "runs": row.total_runs,
                    "wickets": row.total_wickets,
                    "average": float(row.overall_average) if row.overall_average else None,
                    "strike_rate": float(row.overall_strike_rate) if row.overall_strike_rate else None,
                    "economy": float(row.overall_economy),
                    "boundary_percentage": float(row.overall_boundary_percentage),
                    "dot_percentage": float(row.overall_dot_percentage)
                },
                "powerplay": {
                    "balls": int(row.pp_balls),
                    "runs": row.pp_runs,
                    "wickets": row.pp_wickets,
                    "average": float(row.pp_average) if row.pp_average else None,
                    "strike_rate": float(row.pp_strike_rate) if row.pp_strike_rate else None,
                    "economy": float(row.pp_economy),
                    "boundary_percentage": float(row.pp_boundary_percentage),
                    "dot_percentage": float(row.pp_dot_percentage)
                },
                "middle_overs": {
                    "balls": int(row.middle_balls),
                    "runs": row.middle_runs,
                    "wickets": row.middle_wickets,
                    "average": float(row.middle_average) if row.middle_average else None,
                    "strike_rate": float(row.middle_strike_rate) if row.middle_strike_rate else None,
                    "economy": float(row.middle_economy),
                    "boundary_percentage": float(row.middle_boundary_percentage),
                    "dot_percentage": float(row.middle_dot_percentage)
                },
                "death_overs": {
                    "balls": int(row.death_balls),
                    "runs": row.death_runs,
                    "wickets": row.death_wickets,
                    "average": float(row.death_average) if row.death_average else None,
                    "strike_rate": float(row.death_strike_rate) if row.death_strike_rate else None,
                    "economy": float(row.death_economy),
                    "boundary_percentage": float(row.death_boundary_percentage),
                    "dot_percentage": float(row.death_dot_percentage)
                }
            }
            bowling_order.append(player_data)
        
        return {
            "team": team_name if not players else "Custom Players",
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "total_players": len(bowling_order),
            "bowling_order": bowling_order
        }
        
    except Exception as e:
        logger.error(f"Error in get_team_bowling_order_service: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching team bowling order: {str(e)}")
