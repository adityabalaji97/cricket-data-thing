"""
360 Batters Card

Batters who score all around the ground - measuring wagon wheel zone distribution.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_MIN_BALLS, DEFAULT_TOP_TEAMS


def get_three_sixty_batters_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 100,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: 360° Batters
    
    Identifies batters who score evenly across all wagon wheel zones.
    360° Score rewards even distribution + high strike rate.
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
            "dd.wagon_zone IS NOT NULL",
            "dd.wagon_zone BETWEEN 1 AND 8"
        ]
    )
    
    params["min_balls"] = min_balls
    
    query = f"""
        WITH zone_stats AS (
            SELECT 
                dd.bat as player,
                dd.team_bat as team,
                dd.bat_hand,
                dd.wagon_zone as zone,
                COUNT(*) as balls,
                SUM(dd.score) as runs
            FROM delivery_details dd
            {where_clause}
            GROUP BY dd.bat, dd.team_bat, dd.bat_hand, dd.wagon_zone
        ),
        player_primary AS (
            SELECT DISTINCT ON (player) player, team, bat_hand
            FROM zone_stats
            ORDER BY player, balls DESC
        ),
        player_zone_totals AS (
            SELECT 
                zs.player,
                zs.zone,
                SUM(zs.runs) as zone_runs,
                SUM(zs.balls) as zone_balls
            FROM zone_stats zs
            GROUP BY zs.player, zs.zone
        ),
        player_totals AS (
            SELECT 
                player,
                SUM(zone_runs) as total_runs,
                SUM(zone_balls) as total_balls,
                COUNT(DISTINCT zone) as zones_used
            FROM player_zone_totals
            GROUP BY player
            HAVING SUM(zone_balls) >= :min_balls
        ),
        player_zone_pcts AS (
            SELECT 
                pzt.player,
                pzt.zone,
                pzt.zone_runs,
                ROUND((pzt.zone_runs * 100.0 / pt.total_runs)::numeric, 2) as run_pct
            FROM player_zone_totals pzt
            JOIN player_totals pt ON pzt.player = pt.player
        ),
        -- Calculate 360 score: rewards even distribution + volume
        player_360_scores AS (
            SELECT 
                pt.player,
                pt.total_runs,
                pt.total_balls,
                pt.zones_used,
                ROUND((pt.total_runs * 100.0 / pt.total_balls)::numeric, 2) as strike_rate,
                -- Evenness: stddev of zone percentages (lower is better, invert for score)
                -- 360 Score = zones_used * 10 + SR/10 - stddev_penalty
                ROUND((
                    pt.zones_used * 10 + 
                    (pt.total_runs * 100.0 / pt.total_balls) / 10 +
                    20 - COALESCE(STDDEV(pzp.run_pct), 0)
                )::numeric, 1) as score_360
            FROM player_totals pt
            JOIN player_zone_pcts pzp ON pt.player = pzp.player
            GROUP BY pt.player, pt.total_runs, pt.total_balls, pt.zones_used
        )
        SELECT 
            p360.player,
            pp.team,
            pp.bat_hand,
            p360.total_runs as runs,
            p360.total_balls as balls,
            p360.strike_rate,
            p360.zones_used,
            p360.score_360
        FROM player_360_scores p360
        JOIN player_primary pp ON p360.player = pp.player
        ORDER BY p360.score_360 DESC
        LIMIT 10
    """
    
    results = execute_query(db, query, params)
    
    players = []
    for row in results:
        # Get zone breakdown for this player
        zone_query = f"""
            SELECT 
                dd.wagon_zone as zone,
                COUNT(*) as balls,
                SUM(dd.score) as runs,
                ROUND((SUM(dd.score) * 100.0 / SUM(SUM(dd.score)) OVER ())::numeric, 2) as run_pct
            FROM delivery_details dd
            {where_clause}
            AND dd.bat = :player_name
            AND dd.wagon_zone BETWEEN 1 AND 8
            GROUP BY dd.wagon_zone
            ORDER BY dd.wagon_zone
        """
        
        zone_params = {**params, "player_name": row.player}
        zone_results = execute_query(db, zone_query, zone_params)
        
        zone_breakdown = [
            {
                "zone": zr.zone,
                "runs": int(zr.runs) if zr.runs else 0,
                "balls": zr.balls,
                "run_pct": float(zr.run_pct) if zr.run_pct else 0
            }
            for zr in zone_results
        ]
        
        players.append({
            "name": row.player,
            "team": row.team,
            "bat_hand": row.bat_hand,
            "runs": int(row.runs) if row.runs else 0,
            "balls": row.balls,
            "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
            "zones_used": row.zones_used,
            "score_360": float(row.score_360) if row.score_360 else 0,
            "zone_breakdown": zone_breakdown
        })
    
    zone_labels = {
        1: "Fine Leg",
        2: "Sq Leg", 
        3: "Midwicket",
        4: "Long On",
        5: "Long Off",
        6: "Cover",
        7: "Point",
        8: "Third Man"
    }
    
    return {
        "card_id": "three_sixty_batters",
        "card_title": "360° Batters",
        "card_subtitle": f"Most zones hit by batters (min {min_balls} balls)",
        "visualization_type": "wagon_wheel",
        "zone_labels": zone_labels,
        "players": players,
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=batter&min_balls={min_balls}"
        }
    }
