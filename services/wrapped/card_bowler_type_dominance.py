"""
Bowler Type Dominance Card

Which bowling styles ruled the year - Pace vs Spin breakdown.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from .query_helpers import BOWL_DEFS as _W, build_base_filters, execute_query, build_query_url
from .constants import DEFAULT_TOP_TEAMS


def get_bowler_type_dominance_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """
    Card: Bowler Type Dominance
    
    Compares pace vs spin performance with top performers in each category.
    Returns `kind_stats` (pace/spin), `top_pace`, `top_spin`, `style_stats`.
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
            "dd.bowl_kind IS NOT NULL"
        ]
    )
    
    # Get pace vs spin aggregate stats
    kind_query = f"""
        SELECT 
            CASE 
                WHEN LOWER(dd.bowl_kind) LIKE '%pace%' OR LOWER(dd.bowl_kind) LIKE '%fast%' OR LOWER(dd.bowl_kind) LIKE '%seam%' OR LOWER(dd.bowl_kind) LIKE '%medium%'
                THEN 'pace'
                ELSE 'spin'
            END as kind,
            {_W.balls_sum} as balls,
            {_W.runs_sum} as runs,
            {_W.wickets_sum} as wickets,
            {_W.dots_sum} as dots,
            ROUND(({_W.runs_sum} * 6.0 / NULLIF({_W.balls_sum}, 0))::numeric, 2) as economy,
            CASE 
                WHEN {_W.wickets_sum} > 0 
                THEN ROUND(({_W.balls_sum}::numeric / {_W.wickets_sum}), 1)
                ELSE NULL
            END as strike_rate
        FROM delivery_details dd
        {where_clause}
        GROUP BY 
            CASE 
                WHEN LOWER(dd.bowl_kind) LIKE '%pace%' OR LOWER(dd.bowl_kind) LIKE '%fast%' OR LOWER(dd.bowl_kind) LIKE '%seam%' OR LOWER(dd.bowl_kind) LIKE '%medium%'
                THEN 'pace'
                ELSE 'spin'
            END
    """
    
    kind_results = execute_query(db, kind_query, params)
    
    kind_stats = {}
    for row in kind_results:
        kind_stats[row.kind] = {
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "wickets": row.wickets or 0,
            "dots": row.dots or 0,
            "economy": float(row.economy) if row.economy else 0,
            "strike_rate": float(row.strike_rate) if row.strike_rate else 0
        }
    
    # Get top pace bowlers by wickets
    top_pace_query = f"""
        SELECT 
            dd.bowl as name,
            dd.team_bowl as team,
            {_W.balls_sum} as balls,
            {_W.runs_sum} as runs,
            {_W.wickets_sum} as wickets,
            ROUND(({_W.runs_sum} * 6.0 / NULLIF({_W.balls_sum}, 0))::numeric, 2) as economy
        FROM delivery_details dd
        {where_clause}
        AND (LOWER(dd.bowl_kind) LIKE '%pace%' OR LOWER(dd.bowl_kind) LIKE '%fast%' OR LOWER(dd.bowl_kind) LIKE '%seam%' OR LOWER(dd.bowl_kind) LIKE '%medium%')
        GROUP BY dd.bowl, dd.team_bowl
        HAVING {_W.balls_sum} >= 60
        ORDER BY {_W.wickets_sum} DESC
        LIMIT 5
    """
    
    top_pace_results = execute_query(db, top_pace_query, params)
    top_pace = [
        {
            "name": row.name,
            "team": row.team,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "wickets": row.wickets or 0,
            "economy": float(row.economy) if row.economy else 0
        }
        for row in top_pace_results
    ]
    
    # Get top spin bowlers by wickets
    top_spin_query = f"""
        SELECT 
            dd.bowl as name,
            dd.team_bowl as team,
            {_W.balls_sum} as balls,
            {_W.runs_sum} as runs,
            {_W.wickets_sum} as wickets,
            ROUND(({_W.runs_sum} * 6.0 / NULLIF({_W.balls_sum}, 0))::numeric, 2) as economy
        FROM delivery_details dd
        {where_clause}
        AND NOT (LOWER(dd.bowl_kind) LIKE '%pace%' OR LOWER(dd.bowl_kind) LIKE '%fast%' OR LOWER(dd.bowl_kind) LIKE '%seam%' OR LOWER(dd.bowl_kind) LIKE '%medium%')
        GROUP BY dd.bowl, dd.team_bowl
        HAVING {_W.balls_sum} >= 60
        ORDER BY {_W.wickets_sum} DESC
        LIMIT 5
    """
    
    top_spin_results = execute_query(db, top_spin_query, params)
    top_spin = [
        {
            "name": row.name,
            "team": row.team,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "wickets": row.wickets or 0,
            "economy": float(row.economy) if row.economy else 0
        }
        for row in top_spin_results
    ]
    
    # Get individual style stats
    style_query = f"""
        SELECT 
            dd.bowl_style as style,
            CASE 
                WHEN LOWER(dd.bowl_kind) LIKE '%pace%' OR LOWER(dd.bowl_kind) LIKE '%fast%' OR LOWER(dd.bowl_kind) LIKE '%seam%' OR LOWER(dd.bowl_kind) LIKE '%medium%'
                THEN 'pace'
                ELSE 'spin'
            END as kind,
            {_W.balls_sum} as balls,
            {_W.runs_sum} as runs,
            {_W.wickets_sum} as wickets,
            ROUND(({_W.runs_sum} * 6.0 / NULLIF({_W.balls_sum}, 0))::numeric, 2) as economy
        FROM delivery_details dd
        {where_clause}
        AND dd.bowl_style IS NOT NULL
        GROUP BY dd.bowl_style, 
            CASE 
                WHEN LOWER(dd.bowl_kind) LIKE '%pace%' OR LOWER(dd.bowl_kind) LIKE '%fast%' OR LOWER(dd.bowl_kind) LIKE '%seam%' OR LOWER(dd.bowl_kind) LIKE '%medium%'
                THEN 'pace'
                ELSE 'spin'
            END
        HAVING {_W.balls_sum} >= 500
        ORDER BY economy ASC
    """
    
    style_results = execute_query(db, style_query, params)
    style_stats = [
        {
            "style": row.style,
            "kind": row.kind,
            "balls": row.balls,
            "runs": int(row.runs) if row.runs else 0,
            "wickets": row.wickets or 0,
            "economy": float(row.economy) if row.economy else 0
        }
        for row in style_results
    ]
    
    return {
        "card_id": "bowler_type_dominance",
        "card_title": "Bowler Type Dominance",
        "card_subtitle": "Pace vs Spin battle",
        "visualization_type": "pace_spin_comparison",
        "kind_stats": kind_stats,
        "top_pace": top_pace,
        "top_spin": top_spin,
        "style_stats": style_stats,
        "deep_links": {
            "query_builder": build_query_url(
                start_date=start_date,
                end_date=end_date,
                leagues=leagues,
                include_international=include_international,
                top_teams=top_teams,
                group_by=["bowl_kind", "bowl_style"]
            )
        }
    }
