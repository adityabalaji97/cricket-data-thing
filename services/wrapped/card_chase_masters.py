"""
Chase Masters Card

Who moves win probability the most in chases (2nd innings).
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_TOP_TEAMS


def get_chase_masters_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 50,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: Chase Masters
    
    For each ball faced in 2nd innings:
      delta = next_win_prob - current_win_prob
    
    Measures how much the batting team's win probability changed.
    """
    
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
                dd.ball_id,
                dd.score as batruns,
                dd.win_prob,
                LEAD(dd.win_prob) OVER (
                    PARTITION BY dd.p_match 
                    ORDER BY dd.ball_id
                ) as next_win_prob
            FROM delivery_details dd
            WHERE dd.year >= :start_year
            AND dd.year <= :end_year
            AND dd.inns = 2
            AND dd.win_prob IS NOT NULL
            AND dd.win_prob != -1
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
                    WHEN next_win_prob IS NOT NULL AND next_win_prob != -1 
                    THEN next_win_prob - win_prob 
                    ELSE 0 
                END) as total_wp_delta,
                AVG(win_prob) as avg_entry_wp
            FROM ball_deltas
            WHERE next_win_prob IS NOT NULL AND next_win_prob != -1
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
                SUM(total_wp_delta) as total_wp_delta,
                AVG(avg_entry_wp) as avg_entry_wp
            FROM player_ball_impact
            GROUP BY player
            HAVING SUM(balls) >= :min_balls
        )
        SELECT 
            pt.player,
            ppt.team,
            pt.balls,
            pt.runs,
            ROUND(pt.total_wp_delta::numeric, 2) as wp_change_pct,
            ROUND((pt.total_wp_delta / pt.balls)::numeric, 3) as wp_per_ball,
            ROUND((pt.runs * 100.0 / pt.balls)::numeric, 2) as strike_rate,
            ROUND(pt.avg_entry_wp::numeric, 1) as avg_entry_wp_pct
        FROM player_totals pt
        JOIN player_primary_team ppt ON pt.player = ppt.player
        ORDER BY pt.total_wp_delta DESC
        LIMIT 15
    """
    
    results = execute_query(db, query, params)
    
    clutch_performers = [
        {
            "name": row.player,
            "team": row.team,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "wp_change_pct": float(row.wp_change_pct) if row.wp_change_pct else 0,
            "wp_per_ball": float(row.wp_per_ball) if row.wp_per_ball else 0,
            "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
            "avg_entry_wp_pct": float(row.avg_entry_wp_pct) if row.avg_entry_wp_pct else 0
        }
        for row in results if row.wp_change_pct and row.wp_change_pct > 0
    ][:7]
    
    # Get bottom performers
    bottom_query = query.replace("ORDER BY pt.total_wp_delta DESC", "ORDER BY pt.total_wp_delta ASC")
    bottom_results = execute_query(db, bottom_query, params)
    
    pressure_folders = [
        {
            "name": row.player,
            "team": row.team,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "wp_change_pct": float(row.wp_change_pct) if row.wp_change_pct else 0,
            "strike_rate": float(row.strike_rate) if row.strike_rate else 0
        }
        for row in bottom_results if row.wp_change_pct and row.wp_change_pct < 0
    ][:5]
    
    return {
        "card_id": "chase_masters",
        "card_title": "Chase Masters",
        "card_subtitle": f"Who moves win probability in chases (min {min_balls} chase balls)",
        "visualization_type": "clutch_ranking",
        "clutch_performers": clutch_performers,
        "pressure_folders": pressure_folders,
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&innings=2&group_by=batter"
        }
    }
