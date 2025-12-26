"""
Death Hitters Card

Most destructive batters in overs 16-20 (death phase).
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_MIN_BALLS, DEFAULT_TOP_TEAMS


def get_death_hitters_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 50,  # Lower threshold for death overs
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: Death Hitters
    
    Finds batters with highest strike rates during death overs (16-20).
    """
    
    # Build filters with death overs condition
    where_clause, params = build_base_filters(
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        top_teams=top_teams,
        table_alias="dd",
        use_year=True,
        extra_conditions=[
            "dd.over >= 15",  # Death overs: 16-20 (0-indexed: 15-19)
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
                SUM(CASE WHEN dd.score = 6 THEN 1 ELSE 0 END) as sixes,
                SUM(CASE WHEN dd.score = 4 THEN 1 ELSE 0 END) as fours,
                SUM(CASE WHEN dd.score = 0 AND COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 ELSE 0 END) as dots
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
                SUM(ps.sixes) as sixes,
                SUM(ps.fours) as fours,
                SUM(ps.dots) as dots
            FROM player_stats ps
            GROUP BY ps.player
            HAVING SUM(ps.balls) >= :min_balls
        )
        SELECT 
            pt.player,
            ppt.team,
            pt.balls,
            pt.runs,
            pt.sixes,
            pt.fours,
            ROUND((pt.runs * 100.0 / pt.balls)::numeric, 2) as strike_rate,
            ROUND((pt.dots * 100.0 / pt.balls)::numeric, 2) as dot_percentage,
            ROUND(((pt.sixes + pt.fours) * 100.0 / pt.balls)::numeric, 2) as boundary_percentage
        FROM player_totals pt
        JOIN player_primary_team ppt ON pt.player = ppt.player
        ORDER BY strike_rate DESC
        LIMIT 20
    """
    
    results = execute_query(db, query, params)
    
    players = [
        {
            "name": row.player,
            "team": row.team,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "sixes": row.sixes or 0,
            "fours": row.fours or 0,
            "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
            "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
            "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0
        }
        for row in results
    ]
    
    return {
        "card_id": "death_hitters",
        "card_title": "Death Hitters",
        "card_subtitle": f"Most destructive in overs 16-20 (min {min_balls} balls)",
        "visualization_type": "scatter",
        "axes": {
            "x": "dot_percentage",
            "y": "strike_rate",
            "x_label": "Dot %",
            "y_label": "Strike Rate"
        },
        "players": players,
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=15&group_by=batter&min_balls={min_balls}"
        }
    }
