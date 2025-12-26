"""
Rare Shot Specialists Card

Masters of unconventional shots like reverse scoops, ramps, upper cuts.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_TOP_TEAMS


SHOT_LABELS = {
    'REVERSE_SCOOP': 'Reverse Scoop',
    'REVERSE_SWEEP': 'Reverse Sweep',
    'SCOOP': 'Scoop',
    'RAMP': 'Ramp',
    'PADDLE_SWEEP': 'Paddle Sweep',
    'SWITCH_HIT': 'Switch Hit',
    'LATE_CUT': 'Late Cut',
    'UPPER_CUT': 'Upper Cut',
    'HOOK': 'Hook',
    'REVERSE_PULL': 'Reverse Pull'
}


def get_rare_shot_specialists_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls_per_shot: int = 3,  # Lowered threshold
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: Rare Shot Specialists
    
    Finds the best player for each rare/unconventional shot type.
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
    
    params["min_balls"] = min_balls_per_shot
    
    # First get all distinct shots to see what's in the data
    shots_query = f"""
        SELECT DISTINCT UPPER(REPLACE(dd.shot, ' ', '_')) as shot_type
        FROM delivery_details dd
        {where_clause}
    """
    
    all_shots = execute_query(db, shots_query, params)
    available_shots = [row.shot_type for row in all_shots]
    
    # Filter to rare shots that exist in data
    rare_shot_list = [s for s in SHOT_LABELS.keys() if s in available_shots]
    
    if not rare_shot_list:
        return {
            "card_id": "rare_shot_specialists",
            "card_title": "Rare Shot Specialists",
            "card_subtitle": "Masters of unconventional shots",
            "visualization_type": "shot_grid",
            "rare_shots": [],
            "shot_labels": SHOT_LABELS,
            "best_per_shot": {},
            "message": "No rare shot data available for this period"
        }
    
    params["rare_shots"] = rare_shot_list
    
    query = f"""
        WITH shot_stats AS (
            SELECT 
                dd.bat as player,
                dd.team_bat as team,
                UPPER(REPLACE(dd.shot, ' ', '_')) as shot_type,
                COUNT(*) as balls,
                SUM(dd.score) as runs,
                SUM(CASE WHEN dd.score IN (4, 6) THEN 1 ELSE 0 END) as boundaries
            FROM delivery_details dd
            {where_clause}
            AND UPPER(REPLACE(dd.shot, ' ', '_')) = ANY(:rare_shots)
            GROUP BY dd.bat, dd.team_bat, UPPER(REPLACE(dd.shot, ' ', '_'))
            HAVING COUNT(*) >= :min_balls
        ),
        player_primary_team AS (
            SELECT DISTINCT ON (player) player, team
            FROM shot_stats
            ORDER BY player, balls DESC
        ),
        ranked_by_shot AS (
            SELECT 
                ss.player,
                ppt.team,
                ss.shot_type,
                ss.balls,
                ss.runs,
                ss.boundaries,
                ROUND((ss.runs * 100.0 / ss.balls)::numeric, 2) as strike_rate,
                ROW_NUMBER() OVER (PARTITION BY ss.shot_type ORDER BY ss.runs * 100.0 / ss.balls DESC) as rn
            FROM shot_stats ss
            JOIN player_primary_team ppt ON ss.player = ppt.player
        )
        SELECT *
        FROM ranked_by_shot
        WHERE rn <= 3
        ORDER BY shot_type, rn
    """
    
    results = execute_query(db, query, params)
    
    best_per_shot = {}
    found_shots = set()
    
    for row in results:
        shot_type = row.shot_type
        found_shots.add(shot_type)
        
        if shot_type not in best_per_shot:
            best_per_shot[shot_type] = []
        
        best_per_shot[shot_type].append({
            "name": row.player,
            "team": row.team,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "boundaries": row.boundaries or 0,
            "strike_rate": float(row.strike_rate) if row.strike_rate else 0
        })
    
    return {
        "card_id": "rare_shot_specialists",
        "card_title": "Rare Shot Specialists",
        "card_subtitle": f"Masters of unconventional shots (min {min_balls_per_shot} attempts)",
        "visualization_type": "shot_grid",
        "rare_shots": list(found_shots),
        "shot_labels": SHOT_LABELS,
        "best_per_shot": best_per_shot,
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=batter"
        }
    }
