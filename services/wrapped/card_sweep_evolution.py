"""
Sweep Evolution Card

The rise of sweep shots in T20 cricket.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_MIN_BALLS, DEFAULT_TOP_TEAMS


# Sweep shot types
SWEEP_SHOTS = ['SWEEP', 'PADDLE_SWEEP', 'REVERSE_SWEEP', 'SLOG_SWEEP']

SHOT_LABELS = {
    'SWEEP': 'Sweep',
    'PADDLE_SWEEP': 'Paddle Sweep',
    'REVERSE_SWEEP': 'Reverse Sweep',
    'SLOG_SWEEP': 'Slog Sweep'
}


def get_sweep_evolution_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 20,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: Sweep Evolution
    
    Analyzes sweep shot usage and effectiveness vs spin and pace.
    """
    
    where_clause, params = build_base_filters(
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        top_teams=top_teams,
        table_alias="dd",
        use_year=True,
        extra_conditions=[
            "dd.bat_hand IN ('LHB', 'RHB')",
            "dd.shot IS NOT NULL"
        ]
    )
    
    params["sweep_shots"] = SWEEP_SHOTS
    params["min_balls"] = min_balls
    
    # Get sweep stats by shot type, split by bowling type
    sweep_stats_query = f"""
        WITH sweep_data AS (
            SELECT 
                UPPER(REPLACE(dd.shot, ' ', '_')) as shot_type,
                CASE 
                    WHEN dd.bowl_kind ILIKE '%spin%' OR dd.bowl_kind ILIKE '%slow%' THEN 'spin'
                    ELSE 'pace'
                END as bowl_category,
                COUNT(*) as balls,
                SUM(dd.score) as runs
            FROM delivery_details dd
            {where_clause}
            AND UPPER(REPLACE(dd.shot, ' ', '_')) = ANY(:sweep_shots)
            GROUP BY 
                UPPER(REPLACE(dd.shot, ' ', '_')),
                CASE 
                    WHEN dd.bowl_kind ILIKE '%spin%' OR dd.bowl_kind ILIKE '%slow%' THEN 'spin'
                    ELSE 'pace'
                END
        )
        SELECT 
            shot_type,
            SUM(balls) as total_balls,
            SUM(runs) as total_runs,
            SUM(CASE WHEN bowl_category = 'spin' THEN balls ELSE 0 END) as spin_balls,
            SUM(CASE WHEN bowl_category = 'spin' THEN runs ELSE 0 END) as spin_runs,
            SUM(CASE WHEN bowl_category = 'pace' THEN balls ELSE 0 END) as pace_balls,
            SUM(CASE WHEN bowl_category = 'pace' THEN runs ELSE 0 END) as pace_runs
        FROM sweep_data
        GROUP BY shot_type
        ORDER BY SUM(balls) DESC
    """
    
    sweep_results = execute_query(db, sweep_stats_query, params)
    
    sweep_stats = []
    for row in sweep_results:
        spin_sr = round((row.spin_runs * 100) / row.spin_balls, 2) if row.spin_balls > 0 else 0
        pace_sr = round((row.pace_runs * 100) / row.pace_balls, 2) if row.pace_balls > 0 else 0
        
        sweep_stats.append({
            "shot": row.shot_type,
            "total_balls": row.total_balls,
            "total_runs": int(row.total_runs) if row.total_runs else 0,
            "vs_spin": {
                "balls": row.spin_balls,
                "runs": int(row.spin_runs) if row.spin_runs else 0,
                "strike_rate": spin_sr
            },
            "vs_pace": {
                "balls": row.pace_balls,
                "runs": int(row.pace_runs) if row.pace_runs else 0,
                "strike_rate": pace_sr
            }
        })
    
    # Get top sweepers
    top_sweepers_query = f"""
        WITH player_sweeps AS (
            SELECT 
                dd.bat as player,
                dd.team_bat as team,
                UPPER(REPLACE(dd.shot, ' ', '_')) as shot_type,
                COUNT(*) as balls,
                SUM(dd.score) as runs
            FROM delivery_details dd
            {where_clause}
            AND UPPER(REPLACE(dd.shot, ' ', '_')) = ANY(:sweep_shots)
            GROUP BY dd.bat, dd.team_bat, UPPER(REPLACE(dd.shot, ' ', '_'))
        ),
        player_primary_team AS (
            SELECT DISTINCT ON (player) player, team
            FROM player_sweeps
            ORDER BY player, balls DESC
        ),
        player_totals AS (
            SELECT 
                ps.player,
                SUM(ps.balls) as total_balls,
                SUM(ps.runs) as total_runs,
                COUNT(DISTINCT ps.shot_type) as sweep_types_used
            FROM player_sweeps ps
            GROUP BY ps.player
            HAVING SUM(ps.balls) >= :min_balls
        )
        SELECT 
            pt.player,
            ppt.team,
            pt.total_balls,
            pt.total_runs,
            ROUND((pt.total_runs * 100.0 / pt.total_balls)::numeric, 2) as strike_rate,
            pt.sweep_types_used
        FROM player_totals pt
        JOIN player_primary_team ppt ON pt.player = ppt.player
        ORDER BY pt.total_runs DESC
        LIMIT 10
    """
    
    sweeper_results = execute_query(db, top_sweepers_query, params)
    
    top_sweepers = [
        {
            "name": row.player,
            "team": row.team,
            "total_balls": row.total_balls,
            "total_runs": int(row.total_runs) if row.total_runs else 0,
            "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
            "sweep_types_used": row.sweep_types_used
        }
        for row in sweeper_results
    ]
    
    return {
        "card_id": "sweep_evolution",
        "card_title": "Sweep Evolution",
        "card_subtitle": "The rise of the sweep shots",
        "visualization_type": "sweep_breakdown",
        "shot_labels": SHOT_LABELS,
        "sweep_stats": sweep_stats,
        "top_sweepers": top_sweepers,
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=batter"
        }
    }
