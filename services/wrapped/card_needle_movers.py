"""
Needle Movers Card

Who moved the predicted score the most (per-ball delta impact).
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_TOP_TEAMS


def get_needle_movers_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 100,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: Needle Movers
    
    For each ball faced by a batter:
      delta = next_pred_score - current_pred_score
    
    Measures how much the predicted final score changed after each delivery.
    """
    
    # Build base params for year filtering  
    start_year = int(start_date[:4])
    end_year = int(end_date[:4])
    
    params = {
        "start_year": start_year,
        "end_year": end_year,
        "min_balls": min_balls,
        "wrapped_leagues": leagues,
        "wrapped_top_teams": [
            'India', 'Australia', 'England', 'West Indies', 'New Zealand',
            'South Africa', 'Pakistan', 'Sri Lanka', 'Bangladesh', 'Afghanistan',
            'Ireland', 'Zimbabwe', 'Scotland', 'Netherlands', 'Namibia',
            'UAE', 'Nepal', 'USA', 'Oman', 'Papua New Guinea'
        ][:top_teams]
    }
    
    # Competition filter
    comp_filter = """
        AND (dd.competition = ANY(:wrapped_leagues) 
             OR (dd.competition = 'T20I' 
                 AND dd.team_bat = ANY(:wrapped_top_teams) 
                 AND dd.team_bowl = ANY(:wrapped_top_teams)))
    """
    
    query = f"""
        WITH ball_deltas AS (
            SELECT 
                dd.bat as player,
                dd.team_bat as team,
                dd.p_match,
                dd.inns,
                dd.ball_id,
                dd.score as batruns,
                dd.pred_score,
                LEAD(dd.pred_score) OVER (
                    PARTITION BY dd.p_match, dd.inns 
                    ORDER BY dd.ball_id
                ) as next_pred_score
            FROM delivery_details dd
            WHERE dd.year >= :start_year
            AND dd.year <= :end_year
            AND dd.pred_score IS NOT NULL
            AND dd.pred_score != -1
            AND dd.bat_hand IN ('LHB', 'RHB')
            {comp_filter}
        ),
        player_ball_impact AS (
            SELECT 
                player,
                team,
                COUNT(*) as balls,
                SUM(batruns) as runs,
                SUM(CASE 
                    WHEN next_pred_score IS NOT NULL AND next_pred_score != -1 
                    THEN next_pred_score - pred_score 
                    ELSE 0 
                END) as total_pred_delta
            FROM ball_deltas
            WHERE next_pred_score IS NOT NULL AND next_pred_score != -1
            GROUP BY player, team
        ),
        player_primary_team AS (
            SELECT DISTINCT ON (player) player, team
            FROM player_ball_impact
            ORDER BY player, balls DESC
        ),
        player_totals AS (
            SELECT 
                player,
                SUM(balls) as balls,
                SUM(runs) as runs,
                SUM(total_pred_delta) as total_pred_delta
            FROM player_ball_impact
            GROUP BY player
            HAVING SUM(balls) >= :min_balls
        )
        SELECT 
            pt.player,
            ppt.team,
            pt.balls,
            pt.runs,
            ROUND(pt.total_pred_delta::numeric, 1) as pred_score_impact,
            ROUND((pt.total_pred_delta / pt.balls)::numeric, 2) as impact_per_ball,
            ROUND((pt.runs * 100.0 / pt.balls)::numeric, 2) as strike_rate
        FROM player_totals pt
        JOIN player_primary_team ppt ON pt.player = ppt.player
        ORDER BY pt.total_pred_delta DESC
        LIMIT 20
    """
    
    results = execute_query(db, query, params)
    
    positive_impact = [
        {
            "name": row.player,
            "team": row.team,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "pred_score_impact": float(row.pred_score_impact) if row.pred_score_impact else 0,
            "impact_per_ball": float(row.impact_per_ball) if row.impact_per_ball else 0,
            "strike_rate": float(row.strike_rate) if row.strike_rate else 0
        }
        for row in results if row.pred_score_impact and row.pred_score_impact > 0
    ][:7]
    
    # Get bottom performers
    bottom_query = query.replace("ORDER BY pt.total_pred_delta DESC", "ORDER BY pt.total_pred_delta ASC")
    bottom_results = execute_query(db, bottom_query, params)
    
    negative_impact = [
        {
            "name": row.player,
            "team": row.team,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "pred_score_impact": float(row.pred_score_impact) if row.pred_score_impact else 0,
            "impact_per_ball": float(row.impact_per_ball) if row.impact_per_ball else 0,
            "strike_rate": float(row.strike_rate) if row.strike_rate else 0
        }
        for row in bottom_results if row.pred_score_impact and row.pred_score_impact < 0
    ][:5]
    
    return {
        "card_id": "needle_movers",
        "card_title": "Needle Movers",
        "card_subtitle": f"Who moved the predicted score most (min {min_balls} balls)",
        "visualization_type": "diverging_impact",
        "positive_impact": positive_impact,
        "negative_impact": negative_impact,
        "deep_links": {}
    }
