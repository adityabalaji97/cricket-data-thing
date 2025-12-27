"""
Pace vs Spin Card

Analyzes batters' performance against pace vs spin bowling.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query
from .constants import DEFAULT_MIN_BALLS, DEFAULT_TOP_TEAMS


def get_pace_vs_spin_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 50,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: Pace vs Spin
    
    Identifies batters who dominate pace or spin bowling.
    - Pace crushers: Higher SR vs pace than spin
    - Spin crushers: Higher SR vs spin than pace
    - Complete batters: Good vs both
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
            "dd.bowl_kind IS NOT NULL"
        ]
    )
    
    params["min_balls"] = min_balls
    
    query = f"""
        WITH player_bowl_type_stats AS (
            SELECT 
                dd.bat as player,
                dd.team_bat as team,
                CASE 
                    WHEN dd.bowl_kind ILIKE '%pace%' OR dd.bowl_kind ILIKE '%fast%' OR dd.bowl_kind ILIKE '%seam%' THEN 'pace'
                    WHEN dd.bowl_kind ILIKE '%spin%' OR dd.bowl_kind ILIKE '%slow%' THEN 'spin'
                    ELSE 'other'
                END as bowl_type,
                COUNT(*) as balls,
                SUM(dd.score) as runs,
                SUM(CASE WHEN dd.score = 0 AND COALESCE(dd.wide, 0) = 0 THEN 1 ELSE 0 END) as dots,
                SUM(CASE WHEN dd.score IN (4, 6) THEN 1 ELSE 0 END) as boundaries
            FROM delivery_details dd
            {where_clause}
            GROUP BY dd.bat, dd.team_bat, 
                CASE 
                    WHEN dd.bowl_kind ILIKE '%pace%' OR dd.bowl_kind ILIKE '%fast%' OR dd.bowl_kind ILIKE '%seam%' THEN 'pace'
                    WHEN dd.bowl_kind ILIKE '%spin%' OR dd.bowl_kind ILIKE '%slow%' THEN 'spin'
                    ELSE 'other'
                END
        ),
        player_primary_team AS (
            SELECT DISTINCT ON (player) player, team
            FROM player_bowl_type_stats
            ORDER BY player, balls DESC
        ),
        player_vs_pace AS (
            SELECT 
                player,
                SUM(balls) as balls,
                SUM(runs) as runs,
                SUM(dots) as dots,
                SUM(boundaries) as boundaries,
                ROUND((SUM(runs) * 100.0 / NULLIF(SUM(balls), 0))::numeric, 2) as strike_rate,
                ROUND((SUM(dots) * 100.0 / NULLIF(SUM(balls), 0))::numeric, 2) as dot_pct,
                ROUND((SUM(boundaries) * 100.0 / NULLIF(SUM(balls), 0))::numeric, 2) as boundary_pct
            FROM player_bowl_type_stats
            WHERE bowl_type = 'pace'
            GROUP BY player
            HAVING SUM(balls) >= :min_balls
        ),
        player_vs_spin AS (
            SELECT 
                player,
                SUM(balls) as balls,
                SUM(runs) as runs,
                SUM(dots) as dots,
                SUM(boundaries) as boundaries,
                ROUND((SUM(runs) * 100.0 / NULLIF(SUM(balls), 0))::numeric, 2) as strike_rate,
                ROUND((SUM(dots) * 100.0 / NULLIF(SUM(balls), 0))::numeric, 2) as dot_pct,
                ROUND((SUM(boundaries) * 100.0 / NULLIF(SUM(balls), 0))::numeric, 2) as boundary_pct
            FROM player_bowl_type_stats
            WHERE bowl_type = 'spin'
            GROUP BY player
            HAVING SUM(balls) >= :min_balls
        ),
        combined AS (
            SELECT 
                p.player,
                ppt.team,
                p.strike_rate as sr_vs_pace,
                s.strike_rate as sr_vs_spin,
                ROUND((p.strike_rate - s.strike_rate)::numeric, 2) as sr_delta,
                p.dot_pct as dot_pct_vs_pace,
                s.dot_pct as dot_pct_vs_spin,
                p.boundary_pct as boundary_pct_vs_pace,
                s.boundary_pct as boundary_pct_vs_spin,
                ROUND(((p.strike_rate + s.strike_rate) / 2)::numeric, 2) as combined_sr,
                p.balls as balls_vs_pace,
                s.balls as balls_vs_spin
            FROM player_vs_pace p
            JOIN player_vs_spin s ON p.player = s.player
            JOIN player_primary_team ppt ON p.player = ppt.player
        )
        SELECT * FROM combined
        ORDER BY sr_delta DESC
    """
    
    results = execute_query(db, query, params)
    
    pace_crushers = []
    spin_crushers = []
    complete_batters = []
    
    for row in results:
        player_data = {
            "name": row.player,
            "team": row.team,
            "sr_vs_pace": float(row.sr_vs_pace) if row.sr_vs_pace else 0,
            "sr_vs_spin": float(row.sr_vs_spin) if row.sr_vs_spin else 0,
            "sr_delta": float(row.sr_delta) if row.sr_delta else 0,
            "combined_sr": float(row.combined_sr) if row.combined_sr else 0,
            "balls_vs_pace": row.balls_vs_pace,
            "balls_vs_spin": row.balls_vs_spin
        }
        
        # Categorize
        if row.sr_delta and row.sr_delta > 15:
            pace_crushers.append(player_data)
        elif row.sr_delta and row.sr_delta < -15:
            spin_crushers.append(player_data)
        
        # Complete batters: good vs both (SR > 120, low dots, decent boundaries)
        if (row.sr_vs_pace and row.sr_vs_pace > 120 and 
            row.sr_vs_spin and row.sr_vs_spin > 120 and
            row.dot_pct_vs_pace and row.dot_pct_vs_pace < 35 and
            row.dot_pct_vs_spin and row.dot_pct_vs_spin < 35 and
            row.boundary_pct_vs_pace and row.boundary_pct_vs_pace > 10 and
            row.boundary_pct_vs_spin and row.boundary_pct_vs_spin > 10):
            complete_batters.append(player_data)
    
    # Sort
    pace_crushers.sort(key=lambda x: x["sr_delta"], reverse=True)
    spin_crushers.sort(key=lambda x: x["sr_delta"])
    complete_batters.sort(key=lambda x: x["combined_sr"], reverse=True)
    
    return {
        "card_id": "pace_vs_spin",
        "card_title": "Pace vs Spin",
        "card_subtitle": f"Who dominates which bowling type? (min {min_balls} balls vs each)",
        "visualization_type": "diverging_bar",
        "pace_crushers": pace_crushers[:5],
        "spin_crushers": spin_crushers[:5],
        "complete_batters": complete_batters[:5],
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=batter&group_by=bowl_kind"
        }
    }
