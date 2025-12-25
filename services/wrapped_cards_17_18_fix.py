"""
REPLACEMENT CODE FOR CARDS 17 & 18 in wrapped.py

Replace the existing get_needle_movers_data and get_chase_masters_data methods
with these corrected implementations that use per-ball delta calculations.
"""

# ========================================================================
# CARD 17: NEEDLE MOVERS (pred_score per-ball delta impact)
# ========================================================================

def get_needle_movers_data(
    self,
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 100,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """Card 17: Needle Movers - Who moved pred_score the most (per-ball delta).
    
    For each ball faced by a batter:
      delta = next_pred_score - current_pred_score
    
    This measures how much the predicted final score changed after each delivery.
    Positive delta = batter increased the predicted score (good for batting team).
    Sum of deltas across all balls = total impact on predicted score.
    """
    
    params = {
        "start_year": int(start_date[:4]),
        "end_year": int(end_date[:4]),
        "min_balls": min_balls
    }
    
    # Per-ball delta approach: calculate pred_score change for each delivery
    query = text(f"""
        WITH ball_deltas AS (
            SELECT 
                dd.bat as player,
                dd.team_bat as team,
                dd.p_match,
                dd.inns,
                dd.ball_id,
                dd.batruns,
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
    """)
    
    results = db.execute(query, params).fetchall()
    
    # Split into positive and negative impact
    positive_impact = [r for r in results if r.pred_score_impact and r.pred_score_impact > 0][:7]
    
    # Get bottom performers
    bottom_query = text(f"""
        WITH ball_deltas AS (
            SELECT 
                dd.bat as player,
                dd.team_bat as team,
                dd.p_match,
                dd.inns,
                dd.ball_id,
                dd.batruns,
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
        ORDER BY pt.total_pred_delta ASC
        LIMIT 5
    """)
    
    bottom_results = db.execute(bottom_query, params).fetchall()
    negative_impact = [r for r in bottom_results if r.pred_score_impact and r.pred_score_impact < 0]
    
    # Get coverage stats
    coverage_query = text(f"""
        SELECT 
            COUNT(*) as total_balls,
            SUM(CASE WHEN pred_score IS NOT NULL AND pred_score != -1 THEN 1 ELSE 0 END) as balls_with_data
        FROM delivery_details dd
        WHERE dd.year >= :start_year
        AND dd.year <= :end_year
    """)
    
    coverage_result = db.execute(coverage_query, params).fetchone()
    coverage_pct = round((coverage_result.balls_with_data * 100 / coverage_result.total_balls), 1) if coverage_result.total_balls > 0 else 0
    
    return {
        "card_id": "needle_movers",
        "card_title": "Needle Movers",
        "card_subtitle": f"Who moved the predicted score most (min {min_balls} balls)",
        "visualization_type": "diverging_impact",
        "coverage_pct": coverage_pct,
        "data_note": f"Based on {coverage_pct}% of deliveries with pred_score data",
        "positive_impact": [
            {
                "name": row.player,
                "team": row.team,
                "balls": row.balls,
                "runs": row.runs,
                "pred_score_impact": float(row.pred_score_impact) if row.pred_score_impact else 0,
                "impact_per_ball": float(row.impact_per_ball) if row.impact_per_ball else 0,
                "strike_rate": float(row.strike_rate) if row.strike_rate else 0
            }
            for row in positive_impact
        ],
        "negative_impact": [
            {
                "name": row.player,
                "team": row.team,
                "balls": row.balls,
                "runs": row.runs,
                "pred_score_impact": float(row.pred_score_impact) if row.pred_score_impact else 0,
                "impact_per_ball": float(row.impact_per_ball) if row.impact_per_ball else 0,
                "strike_rate": float(row.strike_rate) if row.strike_rate else 0
            }
            for row in negative_impact
        ],
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=batter"
        }
    }


# ========================================================================
# CARD 18: CHASE MASTERS (win_prob per-ball delta impact)
# ========================================================================

def get_chase_masters_data(
    self,
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 50,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """Card 18: Chase Masters - Who moved win probability the most in chases.
    
    For each ball faced by a batter in 2nd innings:
      delta = next_win_prob - current_win_prob
    
    This measures how much the batting team's win probability changed after each delivery.
    Positive delta = batter improved team's chances of winning.
    Sum of deltas = total win probability contribution.
    
    Note: win_prob is stored as percentage (0-100), so deltas are in percentage points.
    """
    
    params = {
        "start_year": int(start_date[:4]),
        "end_year": int(end_date[:4]),
        "min_balls": min_balls
    }
    
    # Per-ball delta approach for win probability in chases
    query = text(f"""
        WITH ball_deltas AS (
            SELECT 
                dd.bat as player,
                dd.team_bat as team,
                dd.p_match,
                dd.ball_id,
                dd.batruns,
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
    """)
    
    results = db.execute(query, params).fetchall()
    
    # Split into clutch performers and pressure folders
    clutch_performers = [r for r in results if r.wp_change_pct and r.wp_change_pct > 0][:7]
    
    # Get bottom performers
    bottom_query = text(f"""
        WITH ball_deltas AS (
            SELECT 
                dd.bat as player,
                dd.team_bat as team,
                dd.p_match,
                dd.ball_id,
                dd.batruns,
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
                END) as total_wp_delta
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
                SUM(total_wp_delta) as total_wp_delta
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
            ROUND((pt.runs * 100.0 / pt.balls)::numeric, 2) as strike_rate
        FROM player_totals pt
        JOIN player_primary_team ppt ON pt.player = ppt.player
        ORDER BY pt.total_wp_delta ASC
        LIMIT 5
    """)
    
    bottom_results = db.execute(bottom_query, params).fetchall()
    pressure_folders = [r for r in bottom_results if r.wp_change_pct and r.wp_change_pct < 0]
    
    # Get coverage stats
    coverage_query = text(f"""
        SELECT 
            COUNT(*) as total_chase_balls,
            SUM(CASE WHEN win_prob IS NOT NULL AND win_prob != -1 THEN 1 ELSE 0 END) as balls_with_data
        FROM delivery_details dd
        WHERE dd.year >= :start_year
        AND dd.year <= :end_year
        AND dd.inns = 2
    """)
    
    coverage_result = db.execute(coverage_query, params).fetchone()
    coverage_pct = round((coverage_result.balls_with_data * 100 / coverage_result.total_chase_balls), 1) if coverage_result.total_chase_balls > 0 else 0
    
    return {
        "card_id": "chase_masters",
        "card_title": "Chase Masters",
        "card_subtitle": f"Who moves the needle in chases (min {min_balls} chase balls)",
        "visualization_type": "clutch_ranking",
        "coverage_pct": coverage_pct,
        "data_note": f"Based on {coverage_pct}% of chase deliveries with win probability",
        "clutch_performers": [
            {
                "name": row.player,
                "team": row.team,
                "balls": row.balls,
                "runs": row.runs,
                "wp_change_pct": float(row.wp_change_pct) if row.wp_change_pct else 0,
                "wp_per_ball": float(row.wp_per_ball) if row.wp_per_ball else 0,
                "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
                "avg_entry_wp_pct": float(row.avg_entry_wp_pct) if row.avg_entry_wp_pct else 0
            }
            for row in clutch_performers
        ],
        "pressure_folders": [
            {
                "name": row.player,
                "team": row.team,
                "balls": row.balls,
                "runs": row.runs,
                "wp_change_pct": float(row.wp_change_pct) if row.wp_change_pct else 0,
                "strike_rate": float(row.strike_rate) if row.strike_rate else 0
            }
            for row in pressure_folders
        ],
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&innings=2&group_by=batter"
        }
    }
