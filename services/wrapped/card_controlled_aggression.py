"""
Controlled Aggression Card

Batters with high strike rate AND high control percentage.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_MIN_BALLS, DEFAULT_TOP_TEAMS


def get_controlled_aggression_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 100,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: Controlled Aggression
    
    Finds batters who score quickly while maintaining high control.
    CA Score = Control (25%) + SR (35%) + Boundary% (25%) + Anti-Dot (15%)
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
            "dd.bat_hand IN ('LHB', 'RHB')"
        ]
    )
    
    params["min_balls"] = min_balls
    
    query = f"""
        WITH player_stats AS (
            SELECT 
                dd.bat as player,
                dd.team_bat as team,
                COUNT(*) as balls,
                SUM(dd.score) as runs,
                SUM(CASE WHEN dd.control = 1 THEN 1 ELSE 0 END) as controlled_shots,
                SUM(CASE WHEN dd.control IS NOT NULL THEN 1 ELSE 0 END) as shots_with_control_data,
                SUM(CASE WHEN dd.score = 0 AND COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 ELSE 0 END) as dots,
                SUM(CASE WHEN dd.score IN (4, 6) THEN 1 ELSE 0 END) as boundaries
            FROM delivery_details dd
            {where_clause}
            GROUP BY dd.bat, dd.team_bat
        ),
        player_primary_team AS (
            SELECT DISTINCT ON (player) player, team
            FROM player_stats
            ORDER BY player, balls DESC
        ),
        player_totals AS (
            SELECT 
                ps.player,
                SUM(ps.balls) as balls,
                SUM(ps.runs) as runs,
                SUM(ps.controlled_shots) as controlled_shots,
                SUM(ps.shots_with_control_data) as shots_with_control_data,
                SUM(ps.dots) as dots,
                SUM(ps.boundaries) as boundaries
            FROM player_stats ps
            GROUP BY ps.player
            HAVING SUM(ps.balls) >= :min_balls
        )
        SELECT 
            pt.player,
            ppt.team,
            pt.balls,
            pt.runs,
            ROUND((pt.runs * 100.0 / pt.balls)::numeric, 2) as strike_rate,
            CASE 
                WHEN pt.shots_with_control_data > 0 
                THEN ROUND((pt.controlled_shots * 100.0 / pt.shots_with_control_data)::numeric, 2)
                ELSE NULL
            END as control_pct,
            ROUND((pt.dots * 100.0 / pt.balls)::numeric, 2) as dot_pct,
            ROUND((pt.boundaries * 100.0 / pt.balls)::numeric, 2) as boundary_pct
        FROM player_totals pt
        JOIN player_primary_team ppt ON pt.player = ppt.player
        WHERE pt.shots_with_control_data > 0
        ORDER BY 
            -- CA Score formula: Control (25%) + SR (35%) + Boundary% (25%) + Anti-Dot (15%)
            (
                (pt.controlled_shots * 100.0 / pt.shots_with_control_data) * 0.25 +
                (pt.runs * 100.0 / pt.balls) * 0.35 +
                (pt.boundaries * 100.0 / pt.balls) * 0.25 +
                (100 - pt.dots * 100.0 / pt.balls) * 0.15
            ) DESC
        LIMIT 20
    """
    
    results = execute_query(db, query, params)
    
    players = []
    for row in results:
        control_pct = float(row.control_pct) if row.control_pct else 0
        strike_rate = float(row.strike_rate) if row.strike_rate else 0
        dot_pct = float(row.dot_pct) if row.dot_pct else 0
        boundary_pct = float(row.boundary_pct) if row.boundary_pct else 0
        
        # Calculate CA Score
        ca_score = round(
            control_pct * 0.25 +
            strike_rate * 0.35 +
            boundary_pct * 0.25 +
            (100 - dot_pct) * 0.15,
            1
        )
        
        players.append({
            "name": row.player,
            "team": row.team,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "strike_rate": strike_rate,
            "control_pct": control_pct,
            "dot_pct": dot_pct,
            "boundary_pct": boundary_pct,
            "ca_score": ca_score
        })
    
    return {
        "card_id": "controlled_aggression",
        "card_title": "Controlled Aggression",
        "card_subtitle": f"High strike rate + high control % (min {min_balls} balls)",
        "visualization_type": "ranked_bars",
        "players": players,
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=batter&min_balls={min_balls}"
        }
    }
