"""
Bowler Handedness Card

Bowlers who specialize against left-hand vs right-hand batters.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import build_base_filters, execute_query, build_query_url
from .constants import DEFAULT_TOP_TEAMS


def get_bowler_handedness_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    top_teams: int = DEFAULT_TOP_TEAMS,
    min_balls_per_hand: int = 30
) -> Dict[str, Any]:
    """
    Card: Bowler Handedness
    
    Finds bowlers who are specialists against LHB or RHB batters.
    Compares their economy rate differential between batting hands.
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
    
    params["min_balls"] = min_balls_per_hand
    
    query = f"""
        WITH bowler_vs_hand AS (
            SELECT 
                dd.bowl as bowler,
                dd.team_bowl as team,
                dd.bat_hand,
                COUNT(*) as balls,
                SUM(dd.score) as runs,
                SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets,
                ROUND((SUM(dd.score) * 6.0 / COUNT(*))::numeric, 2) as economy
            FROM delivery_details dd
            {where_clause}
            GROUP BY dd.bowl, dd.team_bowl, dd.bat_hand
            HAVING COUNT(*) >= :min_balls
        ),
        bowler_primary_team AS (
            SELECT DISTINCT ON (bowler) bowler, team
            FROM bowler_vs_hand
            ORDER BY bowler, balls DESC
        ),
        bowler_both_hands AS (
            SELECT 
                lhb.bowler,
                lhb.economy as econ_vs_lhb,
                lhb.balls as balls_vs_lhb,
                lhb.wickets as wickets_vs_lhb,
                rhb.economy as econ_vs_rhb,
                rhb.balls as balls_vs_rhb,
                rhb.wickets as wickets_vs_rhb,
                (rhb.economy - lhb.economy) as econ_delta_lhb,  -- negative = better vs LHB
                (lhb.economy - rhb.economy) as econ_delta_rhb   -- negative = better vs RHB
            FROM bowler_vs_hand lhb
            JOIN bowler_vs_hand rhb ON lhb.bowler = rhb.bowler
            WHERE lhb.bat_hand = 'LHB' AND rhb.bat_hand = 'RHB'
        )
        SELECT 
            bbh.bowler as name,
            bpt.team,
            bbh.econ_vs_lhb,
            bbh.econ_vs_rhb,
            bbh.balls_vs_lhb,
            bbh.balls_vs_rhb,
            bbh.wickets_vs_lhb,
            bbh.wickets_vs_rhb,
            bbh.econ_delta_lhb,
            bbh.econ_delta_rhb,
            ABS(bbh.econ_delta_lhb) as econ_delta
        FROM bowler_both_hands bbh
        JOIN bowler_primary_team bpt ON bbh.bowler = bpt.bowler
        ORDER BY ABS(bbh.econ_delta_lhb) DESC
        LIMIT 20
    """
    
    results = execute_query(db, query, params)
    
    lhb_specialists = []  # Better vs left-hand batters
    rhb_specialists = []  # Better vs right-hand batters
    
    for row in results:
        bowler_data = {
            "name": row.name,
            "team": row.team,
            "econ_vs_lhb": float(row.econ_vs_lhb) if row.econ_vs_lhb else 0,
            "econ_vs_rhb": float(row.econ_vs_rhb) if row.econ_vs_rhb else 0,
            "balls_vs_lhb": row.balls_vs_lhb,
            "balls_vs_rhb": row.balls_vs_rhb,
            "econ_delta": float(row.econ_delta) if row.econ_delta else 0
        }
        
        # Positive econ_delta_lhb means better vs LHB (lower economy vs lefties)
        # econ_delta_lhb = rhb.economy - lhb.economy
        # If positive: LHB economy < RHB economy → better vs LHB
        if row.econ_delta_lhb > 0:
            lhb_specialists.append(bowler_data)
        else:
            rhb_specialists.append(bowler_data)
    
    # Sort by delta magnitude and take top 5 each
    lhb_specialists = sorted(lhb_specialists, key=lambda x: x['econ_delta'], reverse=True)[:5]
    rhb_specialists = sorted(rhb_specialists, key=lambda x: x['econ_delta'], reverse=True)[:5]
    
    return {
        "card_id": "bowler_handedness",
        "card_title": "Bowler Handedness",
        "card_subtitle": "Specialists vs left or right-hand batters",
        "visualization_type": "handedness_specialists",
        "lhb_specialists": lhb_specialists,
        "rhb_specialists": rhb_specialists,
        "deep_links": {
            "query_builder": build_query_url(
                start_date=start_date,
                end_date=end_date,
                leagues=leagues,
                include_international=include_international,
                top_teams=top_teams,
                group_by=["bowler", "bat_hand"]
            )
        }
    }
