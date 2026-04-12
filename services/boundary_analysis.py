"""
Unified Boundary Analysis Service.

Provides boundary analysis across three contexts:
- venue: boundaries at a ground, grouped by pace/spin + bowl_style + shot
- batter: boundaries by a batter, grouped by pace/spin + bowl_style + shot
- bowler: boundaries conceded by a bowler, grouped by bat_hand + shot
"""

from __future__ import annotations

from datetime import date
from typing import List, Literal, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.visualizations import get_player_name_for_delivery_details
from services.delivery_data_service import build_competition_filter_delivery_details
from services.analytics_common import normalize_leagues


PHASE_CASE_SQL = """CASE
    WHEN dd."over" >= 0 AND dd."over" < 6 THEN 'powerplay'
    WHEN dd."over" >= 6 AND dd."over" < 15 THEN 'middle'
    WHEN dd."over" >= 15 THEN 'death'
    ELSE 'other'
END"""

# Use bowl_kind column (values like 'pace bowler', 'spin bowler') with ILIKE,
# matching the pattern used across the codebase (venue_similarity, wrapped cards, etc.)
BOWL_KIND_CASE_SQL = """CASE
    WHEN LOWER(COALESCE(dd.bowl_kind, '')) LIKE '%pace%'
      OR LOWER(COALESCE(dd.bowl_kind, '')) LIKE '%fast%'
      OR LOWER(COALESCE(dd.bowl_kind, '')) LIKE '%seam%'
      OR LOWER(COALESCE(dd.bowl_kind, '')) LIKE '%medium%'
    THEN 'pace'
    WHEN LOWER(COALESCE(dd.bowl_kind, '')) LIKE '%spin%'
      OR LOWER(COALESCE(dd.bowl_kind, '')) LIKE '%slow%'
    THEN 'spin'
    ELSE NULL
END"""

PHASE_ORDER = ["powerplay", "middle", "death"]


def get_boundary_analysis(
    db: Session,
    context: Literal["venue", "batter", "bowler"],
    name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: Optional[List[str]] = None,
    include_international: bool = False,
) -> dict:
    """
    Unified boundary analysis for venue, batter, or bowler context.

    Returns phase-wise and overall boundary stats grouped by the relevant
    dimension (pace/spin for venue/batter, bat_hand for bowler).
    """
    # delivery_details uses 'bat'/'bowl' columns (not 'batter'/'bowler')
    # and full names (e.g. "Virat Kohli" not "V Kohli")
    needs_name_resolve = context in ("batter", "bowler")

    if context == "venue":
        filter_col = "ground"
        group_dim = "bowl_kind"
        group_sql = f"({BOWL_KIND_CASE_SQL}) AS group_key, dd.bowl_style AS sub_group"
        group_by = "group_key, sub_group"
        extra_where = f"AND ({BOWL_KIND_CASE_SQL}) IS NOT NULL"
    elif context == "batter":
        filter_col = "bat"
        group_dim = "bowl_kind"
        group_sql = f"({BOWL_KIND_CASE_SQL}) AS group_key, dd.bowl_style AS sub_group"
        group_by = "group_key, sub_group"
        extra_where = f"AND ({BOWL_KIND_CASE_SQL}) IS NOT NULL"
    elif context == "bowler":
        filter_col = "bowl"
        group_dim = "bat_hand"
        group_sql = "dd.bat_hand AS group_key, NULL AS sub_group"
        group_by = "group_key"
        extra_where = "AND dd.bat_hand IS NOT NULL AND dd.bat_hand != ''"
    else:
        raise ValueError(f"Invalid context: {context}")

    if needs_name_resolve:
        player_names = get_player_name_for_delivery_details(db, name)
        where_clauses = [f"dd.{filter_col} = ANY(:names)"]
        params: dict = {"names": player_names}
    else:
        where_clauses = [f"dd.{filter_col} = :name"]
        params: dict = {"name": name}

    if start_date:
        where_clauses.append("dd.date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where_clauses.append("dd.date <= :end_date")
        params["end_date"] = end_date

    # Competition / international filter (uses dd.competition column)
    expanded_leagues = normalize_leagues(leagues)
    if expanded_leagues:
        params["leagues"] = expanded_leagues
    comp_filter = build_competition_filter_delivery_details(
        expanded_leagues, include_international, None, params
    )

    where_clauses.append("(dd.wide IS NULL OR dd.wide = 0)")
    where_sql = " AND ".join(where_clauses)

    query = text(f"""
        SELECT
            {PHASE_CASE_SQL} AS phase,
            {group_sql},
            dd.shot,
            COUNT(*) AS total_balls,
            COALESCE(SUM(dd.score), 0) AS total_runs,
            SUM(CASE WHEN dd.score = 4 THEN 1 ELSE 0 END) AS fours,
            SUM(CASE WHEN dd.score = 6 THEN 1 ELSE 0 END) AS sixes
        FROM delivery_details dd
        WHERE {where_sql}
          {comp_filter}
          {extra_where}
        GROUP BY phase, {group_by}, dd.shot
        ORDER BY phase, group_key, dd.shot
    """)

    rows = db.execute(query, params).fetchall()

    # Build nested result
    phases_data: dict = {}
    overall_data: dict = {}

    for row in rows:
        phase = row.phase
        if phase == "other":
            continue
        group_key = row.group_key  # 'pace'/'spin' or 'RHB'/'LHB'
        sub_group = row.sub_group  # bowl_style or None
        shot = row.shot or "UNKNOWN"
        total_balls = int(row.total_balls)
        total_runs = int(row.total_runs or 0)
        fours = int(row.fours or 0)
        sixes = int(row.sixes or 0)
        boundaries = fours + sixes

        for target in [phases_data.setdefault(phase, {}), overall_data]:
            group = target.setdefault(group_key, _empty_group(context != "bowler"))
            _accumulate(group, total_balls, total_runs, fours, sixes, boundaries)
            _accumulate_shot(group["shots"], shot, total_balls, total_runs, fours, sixes, boundaries)

            if sub_group and "styles" in group:
                style_bucket = group["styles"].setdefault(sub_group, _empty_bucket())
                _accumulate(style_bucket, total_balls, total_runs, fours, sixes, boundaries)

    # Finalize percentages
    for phase_groups in list(phases_data.values()) + [overall_data]:
        for group in phase_groups.values():
            _finalize(group)
            for shot_data in group["shots"].values():
                _finalize(shot_data)
            if "styles" in group:
                for style_data in group["styles"].values():
                    _finalize(style_data)

    # Structure into final response
    result_phases = {}
    for phase_name in PHASE_ORDER:
        groups = phases_data.get(phase_name, {})
        result_phases[phase_name] = {"groups": groups}

    return {
        "context": context,
        "name": name,
        "grouping_dimension": group_dim,
        "phases": result_phases,
        "overall": {"groups": overall_data},
    }


def _empty_bucket() -> dict:
    return {
        "total_balls": 0,
        "total_runs": 0,
        "fours": 0,
        "sixes": 0,
        "boundaries": 0,
        "boundary_pct": 0.0,
    }


def _empty_group(include_styles: bool) -> dict:
    group = {
        **_empty_bucket(),
        "shots": {},
    }
    if include_styles:
        group["styles"] = {}
    return group


def _accumulate(bucket, total_balls, total_runs, fours, sixes, boundaries):
    bucket["total_balls"] += total_balls
    bucket["total_runs"] += total_runs
    bucket["fours"] += fours
    bucket["sixes"] += sixes
    bucket["boundaries"] += boundaries


def _accumulate_shot(shots_dict, shot, total_balls, total_runs, fours, sixes, boundaries):
    if shot not in shots_dict:
        shots_dict[shot] = _empty_bucket()
    s = shots_dict[shot]
    _accumulate(s, total_balls, total_runs, fours, sixes, boundaries)


def _finalize(bucket):
    if bucket["total_balls"] > 0:
        bucket["boundary_pct"] = round(
            bucket["boundaries"] / bucket["total_balls"] * 100, 2
        )
