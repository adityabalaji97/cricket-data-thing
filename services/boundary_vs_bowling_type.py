"""
Boundary shots vs Pace/Spin analysis service.

Groups by phase (powerplay, middle1, middle2, death), bowling type (pace/spin),
and shot type. Supports both batter and bowler perspectives.
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.bowler_types import BOWL_STYLE_CATEGORY_SQL


def _phase_case() -> str:
    return """CASE
        WHEN "over" >= 0 AND "over" < 6 THEN 'powerplay'
        WHEN "over" >= 6 AND "over" < 11 THEN 'middle1'
        WHEN "over" >= 11 AND "over" < 15 THEN 'middle2'
        WHEN "over" >= 15 AND "over" < 20 THEN 'death'
        ELSE 'other'
    END"""


def get_boundary_vs_bowling_type(
    db: Session,
    player_name: str,
    role: str = "batter",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: Optional[List[str]] = None,
) -> dict:
    """
    Return phase-wise boundary analysis vs pace/spin with shot breakdown.

    Parameters
    ----------
    db : Session
    player_name : str
    role : 'batter' | 'bowler'
    start_date, end_date : optional date filters
    leagues : optional competition filter
    """
    player_col = "batter" if role == "batter" else "bowler"

    phase_case = _phase_case()
    bowl_cat = BOWL_STYLE_CATEGORY_SQL

    where_clauses = [f"{player_col} = :player_name"]
    params: dict = {"player_name": player_name}

    if start_date:
        where_clauses.append("date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where_clauses.append("date <= :end_date")
        params["end_date"] = end_date
    if leagues:
        where_clauses.append("competition = ANY(:leagues)")
        params["leagues"] = leagues

    # Only consider legal deliveries (exclude wides)
    where_clauses.append("(wide IS NULL OR wide = 0)")

    where_sql = " AND ".join(where_clauses)

    query = text(f"""
        SELECT
            {phase_case} AS phase,
            {bowl_cat} AS bowling_type,
            shot,
            COUNT(*) AS total_balls,
            SUM(score) AS total_runs,
            SUM(CASE WHEN score = 4 THEN 1 ELSE 0 END) AS fours,
            SUM(CASE WHEN score = 6 THEN 1 ELSE 0 END) AS sixes
        FROM delivery_details
        WHERE {where_sql}
          AND ({bowl_cat}) IS NOT NULL
        GROUP BY phase, bowling_type, shot
        ORDER BY phase, bowling_type, shot
    """)

    rows = db.execute(query, params).fetchall()

    # Build nested result structure
    phases_data: dict = {}
    overall_data: dict = {"pace": _empty_bucket(), "spin": _empty_bucket()}

    for row in rows:
        phase = row.phase
        btype = row.bowling_type  # 'pace' or 'spin'
        shot = row.shot or "UNKNOWN"
        total_balls = int(row.total_balls)
        total_runs = int(row.total_runs or 0)
        fours = int(row.fours or 0)
        sixes = int(row.sixes or 0)
        boundaries = fours + sixes

        if phase not in phases_data:
            phases_data[phase] = {"pace": _empty_bucket(), "spin": _empty_bucket()}

        bucket = phases_data[phase][btype]
        _add_to_bucket(bucket, total_balls, total_runs, fours, sixes, boundaries, shot)

        overall_bucket = overall_data[btype]
        _add_to_bucket(overall_bucket, total_balls, total_runs, fours, sixes, boundaries, shot)

    # Finalize percentages
    for phase_dict in list(phases_data.values()) + [overall_data]:
        for btype in ("pace", "spin"):
            _finalize_bucket(phase_dict[btype])

    return {
        "player": player_name,
        "role": role,
        "phases": phases_data,
        "overall": overall_data,
    }


def _empty_bucket() -> dict:
    return {
        "total_balls": 0,
        "total_runs": 0,
        "boundaries": 0,
        "fours": 0,
        "sixes": 0,
        "boundary_pct": 0.0,
        "shots": {},
    }


def _add_to_bucket(bucket, total_balls, total_runs, fours, sixes, boundaries, shot):
    bucket["total_balls"] += total_balls
    bucket["total_runs"] += total_runs
    bucket["fours"] += fours
    bucket["sixes"] += sixes
    bucket["boundaries"] += boundaries

    if shot not in bucket["shots"]:
        bucket["shots"][shot] = {
            "total_balls": 0,
            "total_runs": 0,
            "boundaries": 0,
            "fours": 0,
            "sixes": 0,
        }
    s = bucket["shots"][shot]
    s["total_balls"] += total_balls
    s["total_runs"] += total_runs
    s["fours"] += fours
    s["sixes"] += sixes
    s["boundaries"] += boundaries


def _finalize_bucket(bucket):
    if bucket["total_balls"] > 0:
        bucket["boundary_pct"] = round(
            bucket["boundaries"] / bucket["total_balls"] * 100, 2
        )
    for shot_data in bucket["shots"].values():
        if shot_data["total_balls"] > 0:
            shot_data["boundary_pct"] = round(
                shot_data["boundaries"] / shot_data["total_balls"] * 100, 2
            )
