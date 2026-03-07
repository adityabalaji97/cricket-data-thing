"""
Venue boundary-shape inference from wagon-wheel 4s.

This service powers venue-level boundary profile summaries used in Venue Notes.
"""

from __future__ import annotations

import logging
import math
import time
from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from services.delivery_data_service import (
    build_competition_filter_delivery_details,
    get_venue_aliases,
)
from utils.league_utils import expand_league_abbreviations

logger = logging.getLogger(__name__)


CENTER_X = 180.0
CENTER_Y = 180.0
_CACHE_TTL_SECONDS = 1800  # 30 minutes
_CACHE: Dict[Tuple[Any, ...], Dict[str, Any]] = {}


def _safe_round(value: Optional[float], digits: int = 3) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), digits)


def _safe_div(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return float(numerator) / float(denominator)


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


def _percentile(sorted_values: List[float], p: float) -> Optional[float]:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    p = _clamp(p, 0.0, 1.0)
    rank = p * (len(sorted_values) - 1)
    low_idx = int(math.floor(rank))
    high_idx = int(math.ceil(rank))
    if low_idx == high_idx:
        return float(sorted_values[low_idx])
    low_value = float(sorted_values[low_idx])
    high_value = float(sorted_values[high_idx])
    frac = rank - low_idx
    return low_value + (high_value - low_value) * frac


def _stddev(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean_value = sum(values) / len(values)
    variance = sum((v - mean_value) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def _normalize_angle_deg(angle_deg: float) -> float:
    normalized = angle_deg % 360.0
    if normalized < 0:
        normalized += 360.0
    return normalized


def _to_angle_bin(theta_deg: float, angle_bin_size: int, bins_count: int) -> int:
    return int(theta_deg // angle_bin_size) % bins_count


def _min_bins_threshold(bins_count: int) -> int:
    # 15-degree default => 24 bins => 12 bins threshold.
    return max(1, round(0.5 * bins_count))


def _compose_warning_flags(
    matches_used: int,
    fours_nonzero_xy: int,
    nonzero_rate: float,
    avg_bins_with_data: float,
    bins_count: int,
    relative_sd: float,
) -> List[str]:
    warnings: List[str] = []
    if matches_used < 20 or fours_nonzero_xy < 1000:
        warnings.append("LOW_SAMPLE")
    if nonzero_rate < 0.55:
        warnings.append("HIGH_SENTINEL_RATE")

    sparse_threshold = 12.0 * (bins_count / 24.0)
    if avg_bins_with_data < sparse_threshold:
        warnings.append("SPARSE_ANGLE_COVERAGE")
    if relative_sd > 0.06:
        warnings.append("HIGH_SHAPE_VOLATILITY")
    return warnings


def _surface_regime_signal(matches_used: int, relative_sd: float) -> Dict[str, str]:
    if matches_used >= 30 and relative_sd > 0.06:
        return {
            "surface_regime_signal": "mixed_signal",
            "reason": "Inter-match contour volatility is elevated for this venue sample.",
        }
    return {
        "surface_regime_signal": "single_likely",
        "reason": "Inter-match contour volatility is moderate for this venue sample.",
    }


def compute_boundary_shape_model(
    points: List[Dict[str, Any]],
    angle_bin_size: int = 15,
    min_matches: int = 20,
) -> Dict[str, Any]:
    """
    Pure boundary-shape model from non-sentinel 4s points.
    """
    bins_count = int(360 / angle_bin_size)
    min_bins_hit = _min_bins_threshold(bins_count)

    # 1) Per-competition radial clipping bounds.
    radii_by_comp: Dict[str, List[float]] = defaultdict(list)
    for point in points:
        comp = point.get("competition") or "Unknown"
        x = float(point["wagon_x"])
        y = float(point["wagon_y"])
        r = math.sqrt((x - CENTER_X) ** 2 + (y - CENTER_Y) ** 2)
        point["__r"] = r
        radii_by_comp[comp].append(r)

    comp_bounds: Dict[str, Tuple[float, float]] = {}
    for comp, comp_radii in radii_by_comp.items():
        if not comp_radii:
            continue
        sorted_radii = sorted(comp_radii)
        low = _percentile(sorted_radii, 0.01)
        high = _percentile(sorted_radii, 0.995)
        if low is None or high is None or high <= low:
            low = min(sorted_radii)
            high = max(sorted_radii)
        comp_bounds[comp] = (float(low), float(high))

    # 2) Build match/bin radii buckets with clipping applied.
    per_match_total_nonzero4: Dict[str, int] = defaultdict(int)
    bin_radii: Dict[Tuple[str, str, str, str, int], List[float]] = defaultdict(list)

    for point in points:
        comp = point.get("competition") or "Unknown"
        venue = point.get("venue") or "Unknown Venue"
        match_id = str(point.get("match_id"))
        match_date = str(point.get("date") or "")
        r = float(point["__r"])
        per_match_total_nonzero4[match_id] += 1

        low, high = comp_bounds.get(comp, (0.0, float("inf")))
        if r < low or r > high:
            continue

        x = float(point["wagon_x"])
        y = float(point["wagon_y"])
        theta = _normalize_angle_deg(math.degrees(math.atan2(y - CENTER_Y, x - CENTER_X)))
        angle_bin = _to_angle_bin(theta, angle_bin_size, bins_count)
        key = (comp, venue, match_id, match_date, angle_bin)
        bin_radii[key].append(r)

    # 3) Per-match contour bins (q90), keep bins with >=2 points.
    match_bin_rows: List[Dict[str, Any]] = []
    bins_hit_by_match: Dict[str, int] = defaultdict(int)
    for (comp, venue, match_id, match_date, angle_bin), radii in bin_radii.items():
        if len(radii) < 2:
            continue
        q90 = _percentile(sorted(radii), 0.9)
        if q90 is None:
            continue
        bins_hit_by_match[match_id] += 1
        match_bin_rows.append(
            {
                "competition": comp,
                "venue": venue,
                "match_id": match_id,
                "date": match_date,
                "angle_bin": angle_bin,
                "r_q90": float(q90),
                "points_in_bin": len(radii),
                "match_total_fours_nonzero": per_match_total_nonzero4.get(match_id, 0),
            }
        )

    # 4) Use all matches in the filter window that have non-sentinel 4s.
    # The per-bin q90 still requires >=2 points in that match/bin.
    used_matches = set(per_match_total_nonzero4.keys())

    # 5) Venue profile bins and summary.
    r_q90_by_bin: Dict[int, List[float]] = defaultdict(list)
    for row in match_bin_rows:
        if row["match_id"] in used_matches:
            r_q90_by_bin[row["angle_bin"]].append(float(row["r_q90"]))

    profile_bins: List[Dict[str, Any]] = []
    bin_sds: List[float] = []
    bin_medians: List[float] = []
    matches_used_count = len(used_matches)

    for bin_idx in range(bins_count):
        values = sorted(r_q90_by_bin.get(bin_idx, []))
        angle_start = bin_idx * angle_bin_size
        angle_mid = angle_start + (angle_bin_size / 2.0)
        if values:
            q25 = _percentile(values, 0.25) or 0.0
            q50 = _percentile(values, 0.50) or 0.0
            q75 = _percentile(values, 0.75) or 0.0
            iqr = max(0.0, q75 - q25)
            bin_sd = _stddev(values)
            bin_sds.append(bin_sd)
            bin_medians.append(q50)
            coverage_pct = _safe_div(len(values) * 100.0, matches_used_count)
            profile_bins.append(
                {
                    "angle_bin": bin_idx,
                    "angle_start_deg": angle_start,
                    "angle_mid_deg": _safe_round(angle_mid, 3),
                    "r_median": _safe_round(q50, 3),
                    "r_iqr": _safe_round(iqr, 3),
                    "bin_coverage_pct": _safe_round(coverage_pct, 3),
                }
            )
        else:
            profile_bins.append(
                {
                    "angle_bin": bin_idx,
                    "angle_start_deg": angle_start,
                    "angle_mid_deg": _safe_round(angle_mid, 3),
                    "r_median": None,
                    "r_iqr": None,
                    "bin_coverage_pct": 0.0,
                }
            )

    avg_bins_with_data = (
        _safe_div(sum(bins_hit_by_match.get(m, 0) for m in used_matches), matches_used_count)
        if matches_used_count
        else 0.0
    )
    mean_boundary_r = sum(bin_medians) / len(bin_medians) if bin_medians else 0.0
    mean_bin_sd = sum(bin_sds) / len(bin_sds) if bin_sds else 0.0
    relative_sd = _safe_div(mean_bin_sd, mean_boundary_r) if mean_boundary_r else 0.0

    return {
        "match_bin_rows": match_bin_rows,
        "matches_used": matches_used_count,
        "avg_bins_with_data": avg_bins_with_data,
        "mean_boundary_r": mean_boundary_r,
        "mean_bin_sd": mean_bin_sd,
        "relative_sd": relative_sd,
        "profile_bins": profile_bins,
        "bins_count": bins_count,
        "min_bins_hit": min_bins_hit,
    }


def _build_cache_key(
    venue: str,
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: Optional[List[str]],
    include_international: bool,
    top_teams: Optional[int],
    min_matches: int,
    angle_bin_size: int,
) -> Tuple[Any, ...]:
    return (
        venue,
        str(start_date) if start_date else None,
        str(end_date) if end_date else None,
        tuple(sorted(leagues or [])),
        bool(include_international),
        int(top_teams) if top_teams else None,
        int(min_matches),
        int(angle_bin_size),
    )


def get_venue_boundary_shape_data(
    db: Session,
    venue: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: Optional[List[str]] = None,
    include_international: bool = False,
    top_teams: Optional[int] = None,
    min_matches: int = 20,
    angle_bin_size: int = 15,
) -> Dict[str, Any]:
    """
    Compute venue boundary-shape profile and confidence metrics from 4s.
    """
    if angle_bin_size not in (10, 15, 20):
        raise ValueError("angle_bin_size must be one of 10, 15, or 20")

    expanded_leagues = expand_league_abbreviations(leagues or []) if leagues else []

    cache_key = _build_cache_key(
        venue=venue,
        start_date=start_date,
        end_date=end_date,
        leagues=expanded_leagues,
        include_international=include_international,
        top_teams=top_teams,
        min_matches=min_matches,
        angle_bin_size=angle_bin_size,
    )
    cached = _CACHE.get(cache_key)
    if cached and (time.time() - cached["ts"] < _CACHE_TTL_SECONDS):
        return cached["data"]

    params: Dict[str, Any] = {"venue": venue}
    conditions = ["dd.score = 4"]

    if start_date:
        conditions.append("dd.match_date >= :start_date")
        params["start_date"] = str(start_date)
    if end_date:
        conditions.append("dd.match_date <= :end_date")
        params["end_date"] = str(end_date)

    if venue and venue != "All Venues":
        venue_aliases = get_venue_aliases(venue)
        conditions.append("dd.ground = ANY(:venue_aliases)")
        params["venue_aliases"] = venue_aliases

    competition_filter = build_competition_filter_delivery_details(
        leagues=expanded_leagues,
        include_international=include_international,
        top_teams=top_teams,
        params=params,
    )
    if competition_filter:
        # Utility returns "AND (...)" so trim the leading AND and append.
        conditions.append(competition_filter.replace("AND ", "", 1).strip())

    where_sql = " AND ".join(f"({c})" for c in conditions)

    quality_query = text(
        f"""
        SELECT
            COUNT(*) AS fours_total,
            COUNT(*) FILTER (WHERE dd.wagon_x IS NOT NULL AND dd.wagon_y IS NOT NULL) AS fours_with_xy,
            COUNT(*) FILTER (
                WHERE dd.wagon_x IS NOT NULL
                  AND dd.wagon_y IS NOT NULL
                  AND NOT (dd.wagon_x = 0 AND dd.wagon_y = 0)
            ) AS fours_nonzero_xy,
            COUNT(DISTINCT dd.p_match) AS matches_total,
            COUNT(DISTINCT CASE
                WHEN dd.wagon_x IS NOT NULL
                 AND dd.wagon_y IS NOT NULL
                 AND NOT (dd.wagon_x = 0 AND dd.wagon_y = 0)
                THEN dd.p_match END
            ) AS matches_with_nonzero4
        FROM delivery_details dd
        WHERE {where_sql}
        """
    )
    quality_row = db.execute(quality_query, params).fetchone()
    fours_total = int(quality_row.fours_total or 0)
    fours_with_xy = int(quality_row.fours_with_xy or 0)
    fours_nonzero_xy = int(quality_row.fours_nonzero_xy or 0)
    matches_total = int(quality_row.matches_total or 0)
    matches_with_nonzero4 = int(quality_row.matches_with_nonzero4 or 0)
    nonzero_rate = _safe_div(fours_nonzero_xy, fours_with_xy)

    points_query = text(
        f"""
        SELECT
            dd.competition,
            dd.ground AS venue,
            dd.p_match AS match_id,
            dd.match_date AS date,
            dd.wagon_x,
            dd.wagon_y
        FROM delivery_details dd
        WHERE {where_sql}
          AND dd.wagon_x IS NOT NULL
          AND dd.wagon_y IS NOT NULL
          AND NOT (dd.wagon_x = 0 AND dd.wagon_y = 0)
          AND dd.p_match IS NOT NULL
        """
    )
    raw_rows = db.execute(points_query, params).fetchall()
    points: List[Dict[str, Any]] = [
        {
            "competition": row.competition or "Unknown",
            "venue": row.venue or venue,
            "match_id": str(row.match_id),
            "date": str(row.date) if row.date is not None else None,
            "wagon_x": float(row.wagon_x),
            "wagon_y": float(row.wagon_y),
        }
        for row in raw_rows
    ]

    model = compute_boundary_shape_model(
        points=points,
        angle_bin_size=angle_bin_size,
        min_matches=min_matches,
    )

    matches_used = int(model["matches_used"])
    avg_bins_with_data = float(model["avg_bins_with_data"])
    mean_boundary_r = float(model["mean_boundary_r"])
    mean_bin_sd = float(model["mean_bin_sd"])
    relative_sd = float(model["relative_sd"])
    bins_count = int(model["bins_count"])

    coverage_score = 100.0 * (0.6 * nonzero_rate + 0.4 * _safe_div(avg_bins_with_data, bins_count))
    sample_score = 100.0 * (
        0.7 * min(_safe_div(matches_used, 60.0), 1.0) +
        0.3 * min(_safe_div(fours_nonzero_xy, 5000.0), 1.0)
    )
    stability_score = _clamp(100.0 * (1.0 - _safe_div(relative_sd, 0.10)), 0.0, 100.0)
    confidence_score = (0.4 * coverage_score) + (0.3 * sample_score) + (0.3 * stability_score)

    warning_flags = _compose_warning_flags(
        matches_used=matches_used,
        fours_nonzero_xy=fours_nonzero_xy,
        nonzero_rate=nonzero_rate,
        avg_bins_with_data=avg_bins_with_data,
        bins_count=bins_count,
        relative_sd=relative_sd,
    )
    diagnostics = _surface_regime_signal(matches_used=matches_used, relative_sd=relative_sd)

    result = {
        "venue": venue,
        "filters": {
            "start_date": str(start_date) if start_date else None,
            "end_date": str(end_date) if end_date else None,
            "leagues": expanded_leagues,
            "include_international": include_international,
            "top_teams": top_teams,
            "min_matches": min_matches,
            "angle_bin_size": angle_bin_size,
        },
        "quality": {
            "fours_total": fours_total,
            "fours_with_xy": fours_with_xy,
            "fours_nonzero_xy": fours_nonzero_xy,
            "nonzero_rate": _safe_round(nonzero_rate, 4),
        },
        "sample": {
            "matches_total": matches_total,
            "matches_with_nonzero4": matches_with_nonzero4,
            "matches_used": matches_used,
        },
        "profile_bins": model["profile_bins"],
        "summary": {
            "mean_boundary_r": _safe_round(mean_boundary_r, 3),
            "mean_bin_sd": _safe_round(mean_bin_sd, 3),
            "relative_sd": _safe_round(relative_sd, 4),
            "avg_bins_with_data": _safe_round(avg_bins_with_data, 3),
        },
        "confidence": {
            "confidence_score": _safe_round(confidence_score, 3),
            "coverage_score": _safe_round(coverage_score, 3),
            "sample_score": _safe_round(sample_score, 3),
            "stability_score": _safe_round(stability_score, 3),
            "warning_flags": warning_flags,
        },
        "diagnostics": diagnostics,
    }

    _CACHE[cache_key] = {"ts": time.time(), "data": result}
    return result
