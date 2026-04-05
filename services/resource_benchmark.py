"""
Match-level resource benchmark service using venue_resources.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from services.analytics_common import percentile_rank


def compute_par_score_from_resource(
    first_innings_score: float,
    resource_remaining_pct: float,
) -> float:
    """
    Convert remaining resource % to expected score-at-state.
    """
    used = 100.0 - float(resource_remaining_pct or 0)
    return (float(first_innings_score) * used) / 100.0


def _get_match_info(db: Session, match_id: str) -> Optional[Dict]:
    query = text(
        """
        SELECT id, date, venue, competition, team1, team2, winner
        FROM matches
        WHERE id = :match_id
        LIMIT 1
        """
    )
    row = db.execute(query, {"match_id": match_id}).mappings().first()
    return dict(row) if row else None


def _get_innings_totals_dd(db: Session, match_id: str) -> Dict[int, Dict]:
    query = text(
        """
        SELECT
            dd.inns AS innings,
            MAX(COALESCE(dd.inns_runs, 0)) AS runs,
            MAX(COALESCE(dd.inns_wkts, 0)) AS wickets,
            MAX(COALESCE(dd.target, 0)) AS target
        FROM delivery_details dd
        WHERE dd.p_match = :match_id
          AND dd.inns IN (1, 2)
        GROUP BY dd.inns
        """
    )
    rows = db.execute(query, {"match_id": match_id}).mappings().all()
    out: Dict[int, Dict] = {}
    for row in rows:
        innings = int(row["innings"])
        out[innings] = {
            "runs": int(row.get("runs") or 0),
            "wickets": int(row.get("wickets") or 0),
            "target": int(row.get("target") or 0),
        }
    return out


def _get_innings_totals_deliveries(db: Session, match_id: str) -> Dict[int, Dict]:
    query = text(
        """
        SELECT
            d.innings,
            SUM(COALESCE(d.runs_off_bat, 0) + COALESCE(d.extras, 0)) AS runs,
            SUM(CASE WHEN d.wicket_type IS NOT NULL AND d.wicket_type != '' THEN 1 ELSE 0 END) AS wickets
        FROM deliveries d
        WHERE d.match_id = :match_id
          AND d.innings IN (1, 2)
        GROUP BY d.innings
        """
    )
    rows = db.execute(query, {"match_id": match_id}).mappings().all()
    out: Dict[int, Dict] = {}
    first_innings_runs = 0
    for row in rows:
        innings = int(row["innings"])
        runs = int(row.get("runs") or 0)
        wkts = int(row.get("wickets") or 0)
        out[innings] = {"runs": runs, "wickets": wkts, "target": 0}
        if innings == 1:
            first_innings_runs = runs
    if 2 in out:
        out[2]["target"] = first_innings_runs + 1
    return out


def _get_second_innings_checkpoints_dd(db: Session, match_id: str) -> List[Dict]:
    query = text(
        """
        WITH over_last AS (
            SELECT
                dd.over AS over_num,
                dd.ball AS ball_num,
                COALESCE(dd.inns_runs, 0) AS inns_runs,
                COALESCE(dd.inns_wkts, 0) AS inns_wkts,
                COALESCE(dd.target, 0) AS target,
                COALESCE(dd.inns_runs_rem, 0) AS runs_remaining,
                COALESCE(dd.inns_balls_rem, 0) AS balls_remaining,
                ROW_NUMBER() OVER (PARTITION BY dd.over ORDER BY dd.ball DESC) AS rn
            FROM delivery_details dd
            WHERE dd.p_match = :match_id
              AND dd.inns = 2
        )
        SELECT over_num, ball_num, inns_runs, inns_wkts, target, runs_remaining, balls_remaining
        FROM over_last
        WHERE rn = 1
        ORDER BY over_num
        """
    )
    rows = db.execute(query, {"match_id": match_id}).mappings().all()
    return [dict(r) for r in rows]


def _get_second_innings_checkpoints_deliveries(db: Session, match_id: str) -> List[Dict]:
    query = text(
        """
        WITH innings_two AS (
            SELECT
                d.over AS over_num,
                d.ball AS ball_num,
                (COALESCE(d.runs_off_bat, 0) + COALESCE(d.extras, 0)) AS total_runs,
                CASE WHEN d.wicket_type IS NOT NULL AND d.wicket_type != '' THEN 1 ELSE 0 END AS wicket
            FROM deliveries d
            WHERE d.match_id = :match_id
              AND d.innings = 2
        ),
        cumulative AS (
            SELECT
                over_num,
                ball_num,
                SUM(total_runs) OVER (ORDER BY over_num, ball_num) AS inns_runs,
                SUM(wicket) OVER (ORDER BY over_num, ball_num) AS inns_wkts,
                ROW_NUMBER() OVER (PARTITION BY over_num ORDER BY ball_num DESC) AS rn
            FROM innings_two
        )
        SELECT over_num, ball_num, inns_runs, inns_wkts
        FROM cumulative
        WHERE rn = 1
        ORDER BY over_num
        """
    )
    rows = db.execute(query, {"match_id": match_id}).mappings().all()
    return [dict(r) for r in rows]


def _get_recent_first_innings_scores(
    *,
    db: Session,
    venue: str,
    match_id: str,
    match_date: date,
    benchmark_window_matches: int,
) -> List[int]:
    dd_query = text(
        """
        WITH venue_totals AS (
            SELECT
                dd.p_match AS match_id,
                MAX(dd.match_date::date) AS match_date,
                MAX(COALESCE(dd.inns_runs, 0)) AS first_innings_score
            FROM delivery_details dd
            WHERE dd.inns = 1
              AND dd.ground = :venue
              AND dd.p_match != :match_id
              AND dd.match_date::date < :match_date
            GROUP BY dd.p_match
            ORDER BY MAX(dd.match_date::date) DESC
            LIMIT :window
        )
        SELECT first_innings_score
        FROM venue_totals
        ORDER BY match_date DESC
        """
    )
    dd_rows = db.execute(
        dd_query,
        {
            "venue": venue,
            "match_id": match_id,
            "match_date": match_date,
            "window": benchmark_window_matches,
        },
    ).fetchall()
    if dd_rows:
        return [int(r[0]) for r in dd_rows]

    fallback_query = text(
        """
        WITH venue_totals AS (
            SELECT
                d.match_id,
                MAX(m.date) AS match_date,
                SUM(COALESCE(d.runs_off_bat, 0) + COALESCE(d.extras, 0)) AS first_innings_score
            FROM deliveries d
            JOIN matches m ON m.id = d.match_id
            WHERE d.innings = 1
              AND m.venue = :venue
              AND d.match_id != :match_id
              AND m.date < :match_date
            GROUP BY d.match_id
            ORDER BY MAX(m.date) DESC
            LIMIT :window
        )
        SELECT first_innings_score
        FROM venue_totals
        ORDER BY match_date DESC
        """
    )
    rows = db.execute(
        fallback_query,
        {
            "venue": venue,
            "match_id": match_id,
            "match_date": match_date,
            "window": benchmark_window_matches,
        },
    ).fetchall()
    return [int(r[0]) for r in rows]


def _get_venue_resource_rows(db: Session, venue: str, overs: List[int]) -> Dict[Tuple[int, int], Dict]:
    if not overs:
        return {}
    query = text(
        """
        SELECT
            over_num,
            wickets_lost,
            resource_percentage,
            avg_runs_at_state,
            avg_final_score,
            sample_size
        FROM venue_resources
        WHERE venue = :venue
          AND innings = 2
          AND over_num = ANY(:overs)
        """
    )
    rows = db.execute(query, {"venue": venue, "overs": overs}).mappings().all()
    out = {}
    for row in rows:
        key = (int(row["over_num"]), int(row["wickets_lost"]))
        out[key] = dict(row)
    return out


def _pick_resource_row(
    resource_rows: Dict[Tuple[int, int], Dict],
    over_num: int,
    wickets_lost: int,
) -> Optional[Dict]:
    wkts = max(0, min(9, int(wickets_lost)))
    exact = resource_rows.get((int(over_num), wkts))
    if exact:
        return exact

    # Fallback to nearest wicket state for same over.
    same_over = [row for (over, _), row in resource_rows.items() if int(over) == int(over_num)]
    if not same_over:
        return None
    same_over.sort(key=lambda r: abs(int(r["wickets_lost"]) - wkts))
    return same_over[0]


def get_match_resource_benchmark(
    *,
    db: Session,
    match_id: str,
    benchmark_window_matches: int,
) -> Dict:
    match_info = _get_match_info(db, match_id)
    if not match_info:
        raise ValueError(f"Match not found: {match_id}")

    venue = match_info.get("venue")
    match_date = match_info.get("date")
    data_quality_note = []

    innings_totals = _get_innings_totals_dd(db, match_id)
    checkpoints = _get_second_innings_checkpoints_dd(db, match_id)
    used_fallback = False

    if not innings_totals:
        innings_totals = _get_innings_totals_deliveries(db, match_id)
        checkpoints = _get_second_innings_checkpoints_deliveries(db, match_id)
        used_fallback = True

    innings1 = innings_totals.get(1, {"runs": 0, "wickets": 0, "target": 0})
    innings2 = innings_totals.get(2, {"runs": 0, "wickets": 0, "target": innings1["runs"] + 1})
    target = innings2.get("target") or (innings1["runs"] + 1)

    benchmark_scores = _get_recent_first_innings_scores(
        db=db,
        venue=venue,
        match_id=match_id,
        match_date=match_date,
        benchmark_window_matches=benchmark_window_matches,
    )

    innings1_percentile = percentile_rank(
        float(innings1["runs"]) if benchmark_scores else None,
        [float(s) for s in benchmark_scores],
        higher_is_better=True,
    )

    overs = sorted({int(cp.get("over_num") or 0) for cp in checkpoints})
    resource_rows = _get_venue_resource_rows(db, venue, overs)
    if not resource_rows:
        data_quality_note.append("No venue_resources rows found for this venue; par curve unavailable.")

    par_curve = []
    for cp in checkpoints:
        over_num = int(cp.get("over_num") or 0)
        wickets_lost = int(cp.get("inns_wkts") or 0)
        actual_runs = int(cp.get("inns_runs") or 0)
        row = _pick_resource_row(resource_rows, over_num, wickets_lost) if resource_rows else None
        resource_remaining = float(row["resource_percentage"]) if row and row.get("resource_percentage") is not None else None
        par_score = (
            compute_par_score_from_resource(innings1["runs"], resource_remaining)
            if resource_remaining is not None
            else None
        )
        par_delta = (actual_runs - par_score) if par_score is not None else None

        par_curve.append(
            {
                "over": over_num,
                "actual_runs": actual_runs,
                "wickets_lost": wickets_lost,
                "resource_remaining_pct": round(resource_remaining, 2) if resource_remaining is not None else None,
                "par_score": round(par_score, 2) if par_score is not None else None,
                "par_delta": round(par_delta, 2) if par_delta is not None else None,
                "avg_runs_at_state": round(float(row["avg_runs_at_state"]), 2)
                if row and row.get("avg_runs_at_state") is not None
                else None,
                "sample_size": int(row["sample_size"]) if row and row.get("sample_size") is not None else None,
            }
        )

    final_state = par_curve[-1] if par_curve else None
    final_delta = final_state.get("par_delta") if final_state else None

    if used_fallback:
        data_quality_note.append(
            "Used deliveries fallback for innings totals/checkpoints because delivery_details data was unavailable."
        )

    response = {
        "match_id": match_id,
        "venue": venue,
        "date": str(match_date) if match_date else None,
        "competition": match_info.get("competition"),
        "teams": {
            "team1": match_info.get("team1"),
            "team2": match_info.get("team2"),
            "winner": match_info.get("winner"),
        },
        "innings_1": {
            "runs": int(innings1["runs"]),
            "wickets": int(innings1["wickets"]),
            "benchmark_window_matches": benchmark_window_matches,
            "benchmark_scores": benchmark_scores,
            "percentile_at_venue": innings1_percentile,
        },
        "innings_2": {
            "runs": int(innings2["runs"]),
            "wickets": int(innings2["wickets"]),
            "target": int(target),
            "par_curve": par_curve,
            "final_state": {
                "actual_runs": int(innings2["runs"]),
                "required": int(target) - int(innings2["runs"]),
                "par_delta": final_delta,
                "chase_completed": int(innings2["runs"]) >= int(target),
            },
        },
    }
    if data_quality_note:
        response["data_quality_note"] = " ".join(data_quality_note)
    return response

