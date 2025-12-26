"""
Nineteenth Over Gods Card

Best performers in the crucial 19th over.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_TOP_TEAMS


def get_nineteenth_over_gods_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 30,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: 19th Over Gods
    
    Bowlers who excel in the crucial 19th over (over index 18).
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
            "dd.over = 18"  # 19th over (0-indexed)
        ]
    )
    
    params["min_balls"] = min_balls
    
    query = f"""
        WITH bowler_stats AS (
            SELECT 
                dd.bowl as player,
                dd.team_bowl as team,
                COUNT(*) as balls,
                SUM(dd.score) as runs,
                SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets,
                SUM(CASE WHEN dd.score = 0 AND COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 ELSE 0 END) as dots
            FROM delivery_details dd
            {where_clause}
            GROUP BY dd.bowl, dd.team_bowl
        ),
        bowler_primary_team AS (
            SELECT DISTINCT ON (player) player, team
            FROM bowler_stats
            ORDER BY player, balls DESC
        ),
        bowler_totals AS (
            SELECT 
                bs.player,
                SUM(bs.balls) as balls,
                SUM(bs.runs) as runs,
                SUM(bs.wickets) as wickets,
                SUM(bs.dots) as dots
            FROM bowler_stats bs
            GROUP BY bs.player
            HAVING SUM(bs.balls) >= :min_balls
        )
        SELECT 
            bt.player,
            bpt.team,
            bt.balls,
            bt.runs,
            bt.wickets,
            bt.dots,
            ROUND((bt.runs * 6.0 / bt.balls)::numeric, 2) as economy,
            ROUND((bt.dots * 100.0 / bt.balls)::numeric, 2) as dot_percentage
        FROM bowler_totals bt
        JOIN bowler_primary_team bpt ON bt.player = bpt.player
        ORDER BY economy ASC
        LIMIT 20
    """
    
    results = execute_query(db, query, params)
    
    players = [
        {
            "name": row.player,
            "team": row.team,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "wickets": row.wickets or 0,
            "dots": row.dots or 0,
            "economy": float(row.economy) if row.economy else 0,
            "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0
        }
        for row in results
    ]
    
    return {
        "card_id": "nineteenth_over_gods",
        "card_title": "19th Over Gods",
        "card_subtitle": f"Best economy in the crucial 19th over (min {min_balls} balls)",
        "visualization_type": "bar_ranking",
        "metric": "economy",
        "players": players,
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=18&over_max=18&group_by=bowler"
        }
    }
