"""
Venue Similarity Service

Builds venue-level feature vectors from delivery_details, then computes
venue-to-venue similarity using Euclidean distance on z-score normalized features.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from services.delivery_data_service import (
    build_competition_filter_delivery_details,
    get_venue_aliases,
)

try:
    from venue_standardization import VENUE_STANDARDIZATION
except Exception:  # pragma: no cover - defensive import fallback
    VENUE_STANDARDIZATION = {}

logger = logging.getLogger(__name__)


PACE_KIND_CONDITION = """
(
    LOWER(COALESCE(dd.bowl_kind, '')) LIKE '%pace%'
    OR LOWER(COALESCE(dd.bowl_kind, '')) LIKE '%fast%'
    OR LOWER(COALESCE(dd.bowl_kind, '')) LIKE '%seam%'
    OR LOWER(COALESCE(dd.bowl_kind, '')) LIKE '%medium%'
)
""".strip()

SPIN_KIND_CONDITION = """
(
    LOWER(COALESCE(dd.bowl_kind, '')) LIKE '%spin%'
    OR LOWER(COALESCE(dd.bowl_kind, '')) LIKE '%slow%'
)
""".strip()

WICKET_CONDITION = "LOWER(COALESCE(dd.out::text, '')) = 'true'"

SHORT_LENGTH_CONDITION = """
(
    UPPER(COALESCE(dd.length, '')) IN ('SHORT', 'SHORT_OF_A_GOOD_LENGTH', 'SHORT_OF_GOOD_LENGTH')
)
""".strip()
GOOD_LENGTH_CONDITION = "UPPER(COALESCE(dd.length, '')) = 'GOOD_LENGTH'"
FULL_LENGTH_CONDITION = """
(
    UPPER(COALESCE(dd.length, '')) IN ('FULL', 'YORKER', 'FULL_TOSS')
)
""".strip()

FEATURE_SPACE: List[str] = [
    "bat_first_win_pct",
    "avg_first_innings_score",
    "avg_second_innings_score",
    "avg_winning_score",
    "avg_chasing_score",
    "pp_run_rate",
    "middle_run_rate",
    "death_run_rate",
    "pp_wicket_rate",
    "middle_wicket_rate",
    "death_wicket_rate",
    "pp_boundary_pct",
    "death_boundary_pct",
    "pace_economy",
    "spin_economy",
    "pace_wicket_rate",
    "spin_wicket_rate",
    "pace_dot_pct",
    "spin_dot_pct",
    "short_pct",
    "good_length_pct",
    "full_pct",
    "short_sr",
    "good_length_sr",
] + [f"zone_{z}_run_pct" for z in range(1, 9)] + [f"zone_{z}_boundary_pct" for z in range(1, 9)]


def _safe_div(numerator: float, denominator: float) -> Optional[float]:
    if denominator in (None, 0):
        return None
    return float(numerator) / float(denominator)


def _mean(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def _round_or_none(value: Optional[float], digits: int = 3) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), digits)


def _round_metrics(metrics: Dict[str, Optional[float]], digits: int = 3) -> Dict[str, Optional[float]]:
    return {key: _round_or_none(value, digits=digits) for key, value in metrics.items()}


def _canonicalize_venue(venue: Optional[str]) -> Optional[str]:
    if not venue:
        return venue
    canonical = VENUE_STANDARDIZATION.get(venue, venue)
    if isinstance(canonical, str):
        return canonical.strip()
    return venue


def _build_delivery_details_filters(
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: Optional[List[str]],
    include_international: Optional[bool],
    top_teams: Optional[int],
) -> Tuple[str, Dict[str, Any]]:
    params: Dict[str, Any] = {}
    clauses: List[str] = []

    if start_date:
        clauses.append("dd.match_date::date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        clauses.append("dd.match_date::date <= :end_date")
        params["end_date"] = end_date

    where_sql = ""
    if clauses:
        where_sql += " AND " + " AND ".join(clauses)

    apply_competition_filter = (
        leagues is not None or include_international is not None or top_teams is not None
    )
    if apply_competition_filter:
        competition_filter = build_competition_filter_delivery_details(
            leagues=leagues or [],
            include_international=include_international if include_international is not None else False,
            top_teams=top_teams,
            params=params,
        )
        where_sql += f" {competition_filter}"

    return where_sql, params


def _empty_match_agg() -> Dict[str, Any]:
    return {
        "total_matches": 0,
        "bat_first_wins": 0,
        "sum_first_innings": 0.0,
        "sum_second_innings": 0.0,
        "winning_scores": [],
        "chasing_scores": [],
    }


def _empty_phase_agg() -> Dict[str, float]:
    return {
        "total_balls": 0.0,
        "pp_runs": 0.0,
        "pp_balls": 0.0,
        "pp_wickets": 0.0,
        "pp_boundaries": 0.0,
        "pp_innings": 0.0,
        "middle_runs": 0.0,
        "middle_balls": 0.0,
        "middle_wickets": 0.0,
        "middle_boundaries": 0.0,
        "middle_innings": 0.0,
        "death_runs": 0.0,
        "death_balls": 0.0,
        "death_wickets": 0.0,
        "death_boundaries": 0.0,
        "death_innings": 0.0,
        "pace_runs": 0.0,
        "pace_balls": 0.0,
        "pace_wickets": 0.0,
        "pace_dots": 0.0,
        "spin_runs": 0.0,
        "spin_balls": 0.0,
        "spin_wickets": 0.0,
        "spin_dots": 0.0,
        "short_balls": 0.0,
        "short_runs": 0.0,
        "good_balls": 0.0,
        "good_runs": 0.0,
        "full_balls": 0.0,
    }


def _derive_phase_metrics(raw: Dict[str, float]) -> Dict[str, Optional[float]]:
    return {
        "pp_run_rate": _safe_div(raw["pp_runs"] * 6.0, raw["pp_balls"]),
        "middle_run_rate": _safe_div(raw["middle_runs"] * 6.0, raw["middle_balls"]),
        "death_run_rate": _safe_div(raw["death_runs"] * 6.0, raw["death_balls"]),
        "pp_wicket_rate": _safe_div(raw["pp_wickets"], raw["pp_innings"]),
        "middle_wicket_rate": _safe_div(raw["middle_wickets"], raw["middle_innings"]),
        "death_wicket_rate": _safe_div(raw["death_wickets"], raw["death_innings"]),
        "pp_boundary_pct": _safe_div(raw["pp_boundaries"] * 100.0, raw["pp_balls"]),
        "death_boundary_pct": _safe_div(raw["death_boundaries"] * 100.0, raw["death_balls"]),
        "pace_economy": _safe_div(raw["pace_runs"] * 6.0, raw["pace_balls"]),
        "spin_economy": _safe_div(raw["spin_runs"] * 6.0, raw["spin_balls"]),
        "pace_wicket_rate": _safe_div(raw["pace_wickets"] * 6.0, raw["pace_balls"]),
        "spin_wicket_rate": _safe_div(raw["spin_wickets"] * 6.0, raw["spin_balls"]),
        "pace_dot_pct": _safe_div(raw["pace_dots"] * 100.0, raw["pace_balls"]),
        "spin_dot_pct": _safe_div(raw["spin_dots"] * 100.0, raw["spin_balls"]),
        "short_pct": _safe_div(raw["short_balls"] * 100.0, raw["total_balls"]),
        "good_length_pct": _safe_div(raw["good_balls"] * 100.0, raw["total_balls"]),
        "full_pct": _safe_div(raw["full_balls"] * 100.0, raw["total_balls"]),
        "short_sr": _safe_div(raw["short_runs"] * 100.0, raw["short_balls"]),
        "good_length_sr": _safe_div(raw["good_runs"] * 100.0, raw["good_balls"]),
    }


def _build_zone_profile(
    zone_totals: Dict[int, Dict[str, float]]
) -> Tuple[Dict[str, Dict[str, Optional[float]]], Dict[str, Optional[float]]]:
    total_zone_runs = sum(v["runs"] for v in zone_totals.values())
    profile: Dict[str, Dict[str, Optional[float]]] = {}
    feature_values: Dict[str, Optional[float]] = {}

    for zone in range(1, 9):
        zone_row = zone_totals.get(zone, {"balls": 0.0, "runs": 0.0, "boundaries": 0.0})
        run_pct = _safe_div(zone_row["runs"] * 100.0, total_zone_runs)
        boundary_pct = _safe_div(zone_row["boundaries"] * 100.0, zone_row["balls"])
        strike_rate = _safe_div(zone_row["runs"] * 100.0, zone_row["balls"])
        zone_key = str(zone)
        profile[zone_key] = {
            "run_pct": _round_or_none(run_pct),
            "boundary_pct": _round_or_none(boundary_pct),
            "sr": _round_or_none(strike_rate),
        }
        feature_values[f"zone_{zone}_run_pct"] = run_pct
        feature_values[f"zone_{zone}_boundary_pct"] = boundary_pct

    return profile, feature_values


def _aggregate_zone_profile(
    zone_map: Dict[str, Dict[int, Dict[str, float]]],
    venues: List[str],
) -> Dict[str, Dict[str, Optional[float]]]:
    combined: Dict[int, Dict[str, float]] = {
        zone: {"balls": 0.0, "runs": 0.0, "boundaries": 0.0}
        for zone in range(1, 9)
    }

    for venue in venues:
        venue_zones = zone_map.get(venue, {})
        for zone in range(1, 9):
            zone_row = venue_zones.get(zone)
            if not zone_row:
                continue
            combined[zone]["balls"] += float(zone_row.get("balls") or 0.0)
            combined[zone]["runs"] += float(zone_row.get("runs") or 0.0)
            combined[zone]["boundaries"] += float(zone_row.get("boundaries") or 0.0)

    profile, _ = _build_zone_profile(combined)
    return profile


def _format_style_stats(style_totals: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, Optional[float]]]:
    output: Dict[str, Dict[str, Optional[float]]] = {}

    sorted_styles = sorted(
        style_totals.items(),
        key=lambda kv: kv[1].get("balls", 0.0),
        reverse=True,
    )
    for style, raw in sorted_styles:
        balls = float(raw.get("balls") or 0.0)
        runs = float(raw.get("runs") or 0.0)
        wickets = float(raw.get("wickets") or 0.0)
        dots = float(raw.get("dots") or 0.0)
        matches = float(raw.get("matches") or 0.0)
        if balls <= 0:
            continue
        output[style] = {
            "balls": int(balls),
            "economy": _round_or_none(_safe_div(runs * 6.0, balls)),
            "dot_pct": _round_or_none(_safe_div(dots * 100.0, balls)),
            "avg": _round_or_none(_safe_div(runs, wickets)),
            "wickets_per_match": _round_or_none(_safe_div(wickets, matches)),
        }

    return output


def get_similar_venues(
    venue: str,
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    min_matches: int = 10,
    top_n: int = 5,
    leagues: Optional[List[str]] = None,
    include_international: Optional[bool] = None,
    top_teams: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Find most similar and dissimilar venues using normalized venue feature vectors.
    """
    where_sql, params = _build_delivery_details_filters(
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        top_teams=top_teams,
    )

    match_rows = db.execute(
        text(
            f"""
            SELECT
                dd.ground AS venue,
                dd.p_match AS match_id,
                SUM(CASE WHEN dd.inns = 1 THEN dd.score ELSE 0 END) AS first_innings_runs,
                SUM(CASE WHEN dd.inns = 2 THEN dd.score ELSE 0 END) AS second_innings_runs,
                MAX(CASE WHEN COALESCE(m.won_batting_first, false) THEN 1 ELSE 0 END) AS won_batting_first,
                MAX(CASE WHEN COALESCE(m.won_fielding_first, false) THEN 1 ELSE 0 END) AS won_fielding_first
            FROM delivery_details dd
            JOIN matches m ON dd.p_match = m.id
            WHERE 1=1
                {where_sql}
            GROUP BY dd.ground, dd.p_match
            """
        ),
        params,
    ).fetchall()

    phase_rows = db.execute(
        text(
            f"""
            SELECT
                dd.ground AS venue,
                COUNT(*) AS total_balls,
                SUM(CASE WHEN dd.over BETWEEN 0 AND 5 THEN dd.score ELSE 0 END) AS pp_runs,
                SUM(CASE WHEN dd.over BETWEEN 0 AND 5 THEN 1 ELSE 0 END) AS pp_balls,
                SUM(CASE WHEN dd.over BETWEEN 0 AND 5 AND {WICKET_CONDITION} THEN 1 ELSE 0 END) AS pp_wickets,
                SUM(CASE WHEN dd.over BETWEEN 0 AND 5 AND dd.score IN (4, 6) THEN 1 ELSE 0 END) AS pp_boundaries,
                COUNT(DISTINCT CASE WHEN dd.over BETWEEN 0 AND 5 THEN dd.p_match::text || '-' || dd.inns::text END) AS pp_innings,

                SUM(CASE WHEN dd.over BETWEEN 6 AND 14 THEN dd.score ELSE 0 END) AS middle_runs,
                SUM(CASE WHEN dd.over BETWEEN 6 AND 14 THEN 1 ELSE 0 END) AS middle_balls,
                SUM(CASE WHEN dd.over BETWEEN 6 AND 14 AND {WICKET_CONDITION} THEN 1 ELSE 0 END) AS middle_wickets,
                SUM(CASE WHEN dd.over BETWEEN 6 AND 14 AND dd.score IN (4, 6) THEN 1 ELSE 0 END) AS middle_boundaries,
                COUNT(DISTINCT CASE WHEN dd.over BETWEEN 6 AND 14 THEN dd.p_match::text || '-' || dd.inns::text END) AS middle_innings,

                SUM(CASE WHEN dd.over BETWEEN 15 AND 19 THEN dd.score ELSE 0 END) AS death_runs,
                SUM(CASE WHEN dd.over BETWEEN 15 AND 19 THEN 1 ELSE 0 END) AS death_balls,
                SUM(CASE WHEN dd.over BETWEEN 15 AND 19 AND {WICKET_CONDITION} THEN 1 ELSE 0 END) AS death_wickets,
                SUM(CASE WHEN dd.over BETWEEN 15 AND 19 AND dd.score IN (4, 6) THEN 1 ELSE 0 END) AS death_boundaries,
                COUNT(DISTINCT CASE WHEN dd.over BETWEEN 15 AND 19 THEN dd.p_match::text || '-' || dd.inns::text END) AS death_innings,

                SUM(CASE WHEN {PACE_KIND_CONDITION} THEN dd.score ELSE 0 END) AS pace_runs,
                SUM(CASE WHEN {PACE_KIND_CONDITION} THEN 1 ELSE 0 END) AS pace_balls,
                SUM(CASE WHEN {PACE_KIND_CONDITION} AND {WICKET_CONDITION} THEN 1 ELSE 0 END) AS pace_wickets,
                SUM(CASE WHEN {PACE_KIND_CONDITION} AND dd.score = 0 THEN 1 ELSE 0 END) AS pace_dots,

                SUM(CASE WHEN {SPIN_KIND_CONDITION} THEN dd.score ELSE 0 END) AS spin_runs,
                SUM(CASE WHEN {SPIN_KIND_CONDITION} THEN 1 ELSE 0 END) AS spin_balls,
                SUM(CASE WHEN {SPIN_KIND_CONDITION} AND {WICKET_CONDITION} THEN 1 ELSE 0 END) AS spin_wickets,
                SUM(CASE WHEN {SPIN_KIND_CONDITION} AND dd.score = 0 THEN 1 ELSE 0 END) AS spin_dots,

                SUM(CASE WHEN {SHORT_LENGTH_CONDITION} THEN 1 ELSE 0 END) AS short_balls,
                SUM(CASE WHEN {SHORT_LENGTH_CONDITION} THEN dd.score ELSE 0 END) AS short_runs,
                SUM(CASE WHEN {GOOD_LENGTH_CONDITION} THEN 1 ELSE 0 END) AS good_balls,
                SUM(CASE WHEN {GOOD_LENGTH_CONDITION} THEN dd.score ELSE 0 END) AS good_runs,
                SUM(CASE WHEN {FULL_LENGTH_CONDITION} THEN 1 ELSE 0 END) AS full_balls
            FROM delivery_details dd
            WHERE 1=1
                {where_sql}
            GROUP BY dd.ground
            """
        ),
        params,
    ).fetchall()

    zone_rows = db.execute(
        text(
            f"""
            SELECT
                dd.ground AS venue,
                dd.wagon_zone AS wagon_zone,
                COUNT(*) AS balls,
                SUM(dd.score) AS runs,
                SUM(CASE WHEN dd.score IN (4, 6) THEN 1 ELSE 0 END) AS boundaries
            FROM delivery_details dd
            WHERE 1=1
                {where_sql}
                AND dd.wagon_zone BETWEEN 1 AND 8
            GROUP BY dd.ground, dd.wagon_zone
            """
        ),
        params,
    ).fetchall()

    style_rows = db.execute(
        text(
            f"""
            SELECT
                dd.ground AS venue,
                COALESCE(NULLIF(dd.bowl_style, ''), 'Unknown') AS bowl_style,
                COUNT(*) AS balls,
                SUM(dd.score) AS runs,
                SUM(CASE WHEN {WICKET_CONDITION} THEN 1 ELSE 0 END) AS wickets,
                SUM(CASE WHEN dd.score = 0 THEN 1 ELSE 0 END) AS dots,
                COUNT(DISTINCT dd.p_match) AS matches
            FROM delivery_details dd
            WHERE 1=1
                {where_sql}
                AND dd.bowl_style IS NOT NULL
            GROUP BY dd.ground, COALESCE(NULLIF(dd.bowl_style, ''), 'Unknown')
            """
        ),
        params,
    ).fetchall()

    phase_kind_rows = db.execute(
        text(
            f"""
            SELECT
                dd.ground AS venue,
                CASE
                    WHEN dd.over BETWEEN 0 AND 5 THEN 'powerplay'
                    WHEN dd.over BETWEEN 6 AND 14 THEN 'middle'
                    ELSE 'death'
                END AS phase,
                CASE
                    WHEN {PACE_KIND_CONDITION} THEN 'pace'
                    WHEN {SPIN_KIND_CONDITION} THEN 'spin'
                    ELSE NULL
                END AS kind,
                COUNT(*) AS balls,
                SUM(dd.score) AS runs
            FROM delivery_details dd
            WHERE 1=1
                {where_sql}
                AND ({PACE_KIND_CONDITION} OR {SPIN_KIND_CONDITION})
            GROUP BY dd.ground, phase, kind
            """
        ),
        params,
    ).fetchall()

    match_map: Dict[str, Dict[str, Any]] = defaultdict(_empty_match_agg)
    phase_raw_map: Dict[str, Dict[str, float]] = defaultdict(_empty_phase_agg)
    zone_map: Dict[str, Dict[int, Dict[str, float]]] = defaultdict(
        lambda: defaultdict(lambda: {"balls": 0.0, "runs": 0.0, "boundaries": 0.0})
    )
    style_map: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(
        lambda: defaultdict(lambda: {"balls": 0.0, "runs": 0.0, "wickets": 0.0, "dots": 0.0, "matches": 0.0})
    )
    phase_kind_map: Dict[str, Dict[str, Dict[str, Dict[str, float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: {"balls": 0.0, "runs": 0.0}))
    )

    for row in match_rows:
        raw_venue = row._mapping["venue"]
        canonical_venue = _canonicalize_venue(raw_venue)
        if not canonical_venue:
            continue
        rec = match_map[canonical_venue]
        first_runs = float(row._mapping.get("first_innings_runs") or 0.0)
        second_runs = float(row._mapping.get("second_innings_runs") or 0.0)
        won_batting_first = int(row._mapping.get("won_batting_first") or 0)
        won_fielding_first = int(row._mapping.get("won_fielding_first") or 0)

        rec["total_matches"] += 1
        rec["sum_first_innings"] += first_runs
        rec["sum_second_innings"] += second_runs
        rec["bat_first_wins"] += won_batting_first
        if won_batting_first:
            rec["winning_scores"].append(first_runs)
        if won_fielding_first:
            rec["chasing_scores"].append(first_runs)

    for row in phase_rows:
        raw_venue = row._mapping["venue"]
        canonical_venue = _canonicalize_venue(raw_venue)
        if not canonical_venue:
            continue
        rec = phase_raw_map[canonical_venue]
        for key in rec.keys():
            rec[key] += float(row._mapping.get(key) or 0.0)

    for row in zone_rows:
        raw_venue = row._mapping["venue"]
        canonical_venue = _canonicalize_venue(raw_venue)
        if not canonical_venue:
            continue
        zone = row._mapping.get("wagon_zone")
        if zone is None:
            continue
        zone_int = int(zone)
        if zone_int < 1 or zone_int > 8:
            continue
        zone_rec = zone_map[canonical_venue][zone_int]
        zone_rec["balls"] += float(row._mapping.get("balls") or 0.0)
        zone_rec["runs"] += float(row._mapping.get("runs") or 0.0)
        zone_rec["boundaries"] += float(row._mapping.get("boundaries") or 0.0)

    for row in style_rows:
        raw_venue = row._mapping["venue"]
        canonical_venue = _canonicalize_venue(raw_venue)
        if not canonical_venue:
            continue
        style = row._mapping.get("bowl_style") or "Unknown"
        style_rec = style_map[canonical_venue][style]
        style_rec["balls"] += float(row._mapping.get("balls") or 0.0)
        style_rec["runs"] += float(row._mapping.get("runs") or 0.0)
        style_rec["wickets"] += float(row._mapping.get("wickets") or 0.0)
        style_rec["dots"] += float(row._mapping.get("dots") or 0.0)
        style_rec["matches"] += float(row._mapping.get("matches") or 0.0)

    for row in phase_kind_rows:
        raw_venue = row._mapping["venue"]
        canonical_venue = _canonicalize_venue(raw_venue)
        if not canonical_venue:
            continue
        phase = row._mapping.get("phase")
        kind = row._mapping.get("kind")
        if phase not in {"powerplay", "middle", "death"}:
            continue
        if kind not in {"pace", "spin"}:
            continue
        phase_kind_map[canonical_venue][phase][kind]["balls"] += float(row._mapping.get("balls") or 0.0)
        phase_kind_map[canonical_venue][phase][kind]["runs"] += float(row._mapping.get("runs") or 0.0)

    match_metrics: Dict[str, Dict[str, Optional[float]]] = {}
    for venue_name, raw in match_map.items():
        total_matches = int(raw["total_matches"])
        match_metrics[venue_name] = {
            "total_matches": total_matches,
            "bat_first_win_pct": _safe_div(raw["bat_first_wins"] * 100.0, total_matches),
            "avg_first_innings_score": _safe_div(raw["sum_first_innings"], total_matches),
            "avg_second_innings_score": _safe_div(raw["sum_second_innings"], total_matches),
            "avg_winning_score": _mean(raw["winning_scores"]),
            "avg_chasing_score": _mean(raw["chasing_scores"]),
        }

    phase_metrics: Dict[str, Dict[str, Optional[float]]] = {}
    for venue_name, raw in phase_raw_map.items():
        phase_metrics[venue_name] = _derive_phase_metrics(raw)

    zone_profiles: Dict[str, Dict[str, Dict[str, Optional[float]]]] = {}
    zone_features_map: Dict[str, Dict[str, Optional[float]]] = {}
    for venue_name in set(list(match_map.keys()) + list(zone_map.keys())):
        profile, feature_values = _build_zone_profile(zone_map.get(venue_name, {}))
        zone_profiles[venue_name] = profile
        zone_features_map[venue_name] = feature_values

    candidate_venues: List[str] = []
    venue_feature_vectors: Dict[str, Dict[str, Optional[float]]] = {}
    all_venues = set(list(match_metrics.keys()) + list(phase_metrics.keys()) + list(zone_features_map.keys()))
    for venue_name in all_venues:
        total_matches = int(match_metrics.get(venue_name, {}).get("total_matches") or 0)
        if total_matches < min_matches:
            continue

        candidate_venues.append(venue_name)
        merged = {
            key: None for key in FEATURE_SPACE
        }
        merged.update({k: v for k, v in match_metrics.get(venue_name, {}).items() if k in FEATURE_SPACE})
        merged.update(phase_metrics.get(venue_name, {}))
        merged.update(zone_features_map.get(venue_name, {}))
        venue_feature_vectors[venue_name] = merged

    if not candidate_venues:
        return {
            "found": False,
            "error": "No venues found for the selected filters and minimum match threshold",
            "qualified_venues": 0,
        }

    target_is_all_venues = venue == "All Venues"
    target_venue: Optional[str] = None

    if not target_is_all_venues:
        alias_candidates = get_venue_aliases(venue) or [venue]
        canonical_candidates = {_canonicalize_venue(v) for v in alias_candidates if v}
        canonical_candidates.add(_canonicalize_venue(venue))
        target_venue = next((v for v in canonical_candidates if v in venue_feature_vectors), None)
        if not target_venue:
            available_matches = 0
            for candidate in canonical_candidates:
                if not candidate:
                    continue
                available_matches = max(
                    available_matches,
                    int(match_metrics.get(candidate, {}).get("total_matches") or 0),
                )
            return {
                "found": False,
                "error": f"Venue '{venue}' not found in qualified pool (min_matches={min_matches})",
                "qualified_venues": len(candidate_venues),
                "available_matches": available_matches,
            }

    zscore_stats: Dict[str, Dict[str, float]] = {}
    league_averages: Dict[str, Optional[float]] = {}
    for feature in FEATURE_SPACE:
        values = [
            float(venue_feature_vectors[v][feature])
            for v in candidate_venues
            if venue_feature_vectors[v].get(feature) is not None
        ]
        mean_value = _mean(values)
        league_averages[feature] = mean_value
        if not values:
            zscore_stats[feature] = {"mean": 0.0, "std": 1.0}
            continue
        variance = sum((v - mean_value) ** 2 for v in values) / len(values) if mean_value is not None else 0.0
        std = math.sqrt(variance)
        zscore_stats[feature] = {
            "mean": float(mean_value or 0.0),
            "std": std if std > 0 else 1.0,
        }

    if target_is_all_venues:
        target_metrics = {feature: league_averages.get(feature) for feature in FEATURE_SPACE}
        target_zone_profile = _aggregate_zone_profile(zone_map, candidate_venues)
    else:
        target_metrics = venue_feature_vectors[target_venue]  # type: ignore[index]
        target_zone_profile = zone_profiles.get(target_venue, {})

    def _zscore_vector(metric_map: Dict[str, Optional[float]]) -> List[float]:
        vector: List[float] = []
        for feature in FEATURE_SPACE:
            raw_value = metric_map.get(feature)
            if raw_value is None:
                vector.append(0.0)
                continue
            stat = zscore_stats[feature]
            vector.append((float(raw_value) - stat["mean"]) / stat["std"])
        return vector

    target_vector = _zscore_vector(target_metrics)

    scored: List[Dict[str, Any]] = []
    for venue_name in candidate_venues:
        if not target_is_all_venues and venue_name == target_venue:
            continue
        vector = _zscore_vector(venue_feature_vectors[venue_name])
        distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(target_vector, vector)))
        scored.append({"venue": venue_name, "distance": round(distance, 4)})

    scored.sort(key=lambda item: item["distance"])
    most_similar_raw = scored[:top_n]
    most_dissimilar_raw = list(reversed(scored[-top_n:])) if scored else []

    def _build_bowling_insights_for_venue(venue_name: str) -> Dict[str, Any]:
        phase_raw = phase_raw_map.get(venue_name, _empty_phase_agg())
        style_stats = _format_style_stats(style_map.get(venue_name, {}))
        return {
            "pace": {
                "economy": _round_or_none(_safe_div(phase_raw["pace_runs"] * 6.0, phase_raw["pace_balls"])),
                "dot_pct": _round_or_none(_safe_div(phase_raw["pace_dots"] * 100.0, phase_raw["pace_balls"])),
                "wicket_rate": _round_or_none(_safe_div(phase_raw["pace_wickets"] * 6.0, phase_raw["pace_balls"])),
            },
            "spin": {
                "economy": _round_or_none(_safe_div(phase_raw["spin_runs"] * 6.0, phase_raw["spin_balls"])),
                "dot_pct": _round_or_none(_safe_div(phase_raw["spin_dots"] * 100.0, phase_raw["spin_balls"])),
                "wicket_rate": _round_or_none(_safe_div(phase_raw["spin_wickets"] * 6.0, phase_raw["spin_balls"])),
            },
            "by_style": style_stats,
        }

    def _build_scored_entry(scored_row: Dict[str, Any]) -> Dict[str, Any]:
        venue_name = scored_row["venue"]
        return {
            "venue": venue_name,
            "distance": scored_row["distance"],
            "total_matches": int(match_metrics.get(venue_name, {}).get("total_matches") or 0),
            "metrics": _round_metrics(venue_feature_vectors.get(venue_name, {})),
            "zone_profile": zone_profiles.get(venue_name, {}),
            "bowling_insights": _build_bowling_insights_for_venue(venue_name),
        }

    most_similar = [_build_scored_entry(row) for row in most_similar_raw]
    most_dissimilar = [_build_scored_entry(row) for row in most_dissimilar_raw]

    similar_venues = [row["venue"] for row in most_similar_raw]
    combined_style_totals: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"balls": 0.0, "runs": 0.0, "wickets": 0.0, "dots": 0.0, "matches": 0.0}
    )
    similar_phase_raw = _empty_phase_agg()
    for venue_name in similar_venues:
        raw = phase_raw_map.get(venue_name, _empty_phase_agg())
        for key in similar_phase_raw.keys():
            similar_phase_raw[key] += raw.get(key, 0.0)

        for style, style_raw in style_map.get(venue_name, {}).items():
            combined_style_totals[style]["balls"] += style_raw.get("balls", 0.0)
            combined_style_totals[style]["runs"] += style_raw.get("runs", 0.0)
            combined_style_totals[style]["wickets"] += style_raw.get("wickets", 0.0)
            combined_style_totals[style]["dots"] += style_raw.get("dots", 0.0)
            combined_style_totals[style]["matches"] += style_raw.get("matches", 0.0)

    by_phase: Dict[str, Dict[str, Optional[float]]] = {}
    for phase in ["powerplay", "middle", "death"]:
        pace_runs = 0.0
        pace_balls = 0.0
        spin_runs = 0.0
        spin_balls = 0.0
        for venue_name in similar_venues:
            pace_data = phase_kind_map.get(venue_name, {}).get(phase, {}).get("pace", {"balls": 0.0, "runs": 0.0})
            spin_data = phase_kind_map.get(venue_name, {}).get(phase, {}).get("spin", {"balls": 0.0, "runs": 0.0})
            pace_runs += float(pace_data.get("runs") or 0.0)
            pace_balls += float(pace_data.get("balls") or 0.0)
            spin_runs += float(spin_data.get("runs") or 0.0)
            spin_balls += float(spin_data.get("balls") or 0.0)
        by_phase[phase] = {
            "pace_economy": _round_or_none(_safe_div(pace_runs * 6.0, pace_balls)),
            "spin_economy": _round_or_none(_safe_div(spin_runs * 6.0, spin_balls)),
        }

    total_similar_matches = sum(
        int(match_metrics.get(venue_name, {}).get("total_matches") or 0)
        for venue_name in similar_venues
    )
    similar_aggregate_zone_profile = _aggregate_zone_profile(zone_map, similar_venues)

    similar_aggregate_insights = {
        "description": f"Aggregate bowling stats across the {len(similar_venues)} most similar venues",
        "total_matches": total_similar_matches,
        "pace": {
            "economy": _round_or_none(_safe_div(similar_phase_raw["pace_runs"] * 6.0, similar_phase_raw["pace_balls"])),
            "dot_pct": _round_or_none(_safe_div(similar_phase_raw["pace_dots"] * 100.0, similar_phase_raw["pace_balls"])),
            "avg": _round_or_none(_safe_div(similar_phase_raw["pace_runs"], similar_phase_raw["pace_wickets"])),
            "wicket_rate": _round_or_none(_safe_div(similar_phase_raw["pace_wickets"] * 6.0, similar_phase_raw["pace_balls"])),
        },
        "spin": {
            "economy": _round_or_none(_safe_div(similar_phase_raw["spin_runs"] * 6.0, similar_phase_raw["spin_balls"])),
            "dot_pct": _round_or_none(_safe_div(similar_phase_raw["spin_dots"] * 100.0, similar_phase_raw["spin_balls"])),
            "avg": _round_or_none(_safe_div(similar_phase_raw["spin_runs"], similar_phase_raw["spin_wickets"])),
            "wicket_rate": _round_or_none(_safe_div(similar_phase_raw["spin_wickets"] * 6.0, similar_phase_raw["spin_balls"])),
        },
        "by_style": _format_style_stats(combined_style_totals),
        "by_phase": by_phase,
        "zone_profile": similar_aggregate_zone_profile,
    }

    requested_venue_label = "All Venues" if target_is_all_venues else target_venue

    return {
        "found": True,
        "venue": requested_venue_label,
        "requested_venue": venue,
        "date_range": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
        "qualified_venues": len(candidate_venues),
        "min_matches": min_matches,
        "feature_space": FEATURE_SPACE,
        "distance_explanation": {
            "method": "euclidean_distance_on_z_scores",
            "summary": "Lower distance means more similar. Features are z-score normalized within the qualified venue pool before Euclidean distance is computed.",
            "target_mode": "all_venues_average" if target_is_all_venues else "single_venue",
        },
        "target_metrics": _round_metrics(target_metrics),
        "league_averages": _round_metrics(league_averages),
        "target_zone_profile": target_zone_profile,
        "most_similar": most_similar,
        "most_dissimilar": most_dissimilar,
        "similar_aggregate_insights": similar_aggregate_insights,
    }

