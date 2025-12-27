"""
Length Masters Card

Batters who dominate vs different bowling lengths.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_MIN_BALLS, DEFAULT_TOP_TEAMS


# Standard bowling lengths in logical order (pitcher to batter)
LENGTH_ORDER = ['FULL_TOSS', 'YORKER', 'FULL', 'GOOD_LENGTH', 'SHORT_OF_A_GOOD_LENGTH', 'SHORT_OF_GOOD_LENGTH', 'SHORT']

LENGTH_LABELS = {
    'YORKER': 'Yorker',
    'FULL': 'Full',
    'FULL_TOSS': 'Full Toss',
    'GOOD_LENGTH': 'Good Length',
    'GOOD': 'Good',
    'SHORT_OF_GOOD_LENGTH': 'Short of Good',
    'SHORT_OF_A_GOOD_LENGTH': 'Short of Good',
    'SHORT': 'Short',
    'BOUNCER': 'Bouncer',
    'HALF_VOLLEY': 'Half Volley',
    'OVERPITCHED': 'Overpitched'
}


def get_length_masters_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 100,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: Length Masters
    
    Finds batters who dominate balls of all lengths.
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
            "dd.length IS NOT NULL"
        ]
    )
    
    params["min_balls"] = min_balls
    
    query = f"""
        WITH length_stats AS (
            SELECT 
                dd.bat as player,
                dd.team_bat as team,
                UPPER(REPLACE(dd.length, ' ', '_')) as length_type,
                COUNT(*) as balls,
                SUM(dd.score) as runs
            FROM delivery_details dd
            {where_clause}
            GROUP BY dd.bat, dd.team_bat, UPPER(REPLACE(dd.length, ' ', '_'))
        ),
        player_primary_team AS (
            SELECT DISTINCT ON (player) player, team
            FROM length_stats
            ORDER BY player, balls DESC
        ),
        player_totals AS (
            SELECT 
                player,
                SUM(runs) as total_runs,
                SUM(balls) as total_balls
            FROM length_stats
            GROUP BY player
            HAVING SUM(balls) >= :min_balls
        ),
        player_length_sr AS (
            SELECT 
                ls.player,
                ls.length_type,
                ls.balls,
                ls.runs,
                ROUND((ls.runs * 100.0 / ls.balls)::numeric, 2) as strike_rate
            FROM length_stats ls
            JOIN player_totals pt ON ls.player = pt.player
            WHERE ls.balls >= 10
        ),
        player_scores AS (
            SELECT 
                pt.player,
                pt.total_runs,
                pt.total_balls,
                ROUND((pt.total_runs * 100.0 / pt.total_balls)::numeric, 2) as overall_sr,
                ROUND((
                    AVG(pls.strike_rate) + 
                    (100 - COALESCE(STDDEV(pls.strike_rate), 0)) * 0.2
                )::numeric, 1) as length_master_score
            FROM player_totals pt
            JOIN player_length_sr pls ON pt.player = pls.player
            GROUP BY pt.player, pt.total_runs, pt.total_balls
            HAVING COUNT(DISTINCT pls.length_type) >= 3
        )
        SELECT 
            ps.player,
            ppt.team,
            ps.total_balls,
            ps.total_runs,
            ps.overall_sr,
            ps.length_master_score
        FROM player_scores ps
        JOIN player_primary_team ppt ON ps.player = ppt.player
        ORDER BY ps.length_master_score DESC
        LIMIT 10
    """
    
    results = execute_query(db, query, params)
    
    players = []
    for row in results:
        length_query = f"""
            SELECT 
                UPPER(REPLACE(dd.length, ' ', '_')) as length_type,
                COUNT(*) as balls,
                SUM(dd.score) as runs,
                ROUND((SUM(dd.score) * 100.0 / COUNT(*))::numeric, 2) as strike_rate
            FROM delivery_details dd
            {where_clause}
            AND dd.bat = :player_name
            AND dd.length IS NOT NULL
            GROUP BY UPPER(REPLACE(dd.length, ' ', '_'))
            HAVING COUNT(*) >= 5
        """
        
        length_params = {**params, "player_name": row.player}
        length_results = execute_query(db, length_query, length_params)
        
        # Sort by logical length order
        def get_length_order(length_type):
            try:
                return LENGTH_ORDER.index(length_type)
            except ValueError:
                return 99
        
        length_breakdown = sorted([
            {
                "length": lr.length_type,
                "length_label": LENGTH_LABELS.get(lr.length_type, lr.length_type.replace('_', ' ').title()),
                "balls": lr.balls,
                "runs": int(lr.runs) if lr.runs else 0,
                "strike_rate": float(lr.strike_rate) if lr.strike_rate else 0
            }
            for lr in length_results
        ], key=lambda x: get_length_order(x['length']))
        
        players.append({
            "name": row.player,
            "team": row.team,
            "total_balls": row.total_balls,
            "total_runs": int(row.total_runs) if row.total_runs else 0,
            "overall_sr": float(row.overall_sr) if row.overall_sr else 0,
            "length_master_score": float(row.length_master_score) if row.length_master_score else 0,
            "length_breakdown": length_breakdown
        })
    
    return {
        "card_id": "length_masters",
        "card_title": "Length Masters",
        "card_subtitle": f"Dominating all lengths (min {min_balls} balls)",
        "visualization_type": "length_heatmap",
        "length_labels": LENGTH_LABELS,
        "length_order": LENGTH_ORDER,
        "players": players,
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=batter&min_balls={min_balls}"
        }
    }
