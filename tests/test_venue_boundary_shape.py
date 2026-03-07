import math

from services.venue_boundary_shape import (
    CENTER_X,
    CENTER_Y,
    _compose_warning_flags,
    _to_angle_bin,
    compute_boundary_shape_model,
)


def _point_from_polar(
    match_id: str,
    angle_deg: float,
    radius: float,
    competition: str = "IPL",
    venue: str = "Test Venue",
):
    theta = math.radians(angle_deg)
    return {
        "competition": competition,
        "venue": venue,
        "match_id": match_id,
        "date": "2025-01-01",
        "wagon_x": CENTER_X + (radius * math.cos(theta)),
        "wagon_y": CENTER_Y + (radius * math.sin(theta)),
    }


def test_angle_bin_assignment_cardinal_points():
    bins = 24
    assert _to_angle_bin(0.0, 15, bins) == 0
    assert _to_angle_bin(89.9, 15, bins) == 5
    assert _to_angle_bin(90.0, 15, bins) == 6
    assert _to_angle_bin(180.0, 15, bins) == 12
    assert _to_angle_bin(270.0, 15, bins) == 18
    assert _to_angle_bin(359.9, 15, bins) == 23


def test_model_computes_match_q90_and_venue_profile_median():
    points = []

    # Two matches with 12 bins each, enough to qualify as used matches.
    for match_id in ("M1", "M2"):
        for bin_idx in range(12):
            angle_deg = (bin_idx * 15) + 1
            radii = [180.0, 180.0]
            if match_id == "M1" and bin_idx == 0:
                radii = [180.0, 185.0, 186.0]  # q90 ~= 185.8
            if match_id == "M2" and bin_idx == 0:
                radii = [180.0, 180.0]  # q90 = 180
            for radius in radii:
                points.append(_point_from_polar(match_id, angle_deg, radius))

    model = compute_boundary_shape_model(points=points, angle_bin_size=15, min_matches=20)

    assert model["matches_used"] == 2
    assert model["avg_bins_with_data"] >= 12

    match1_bin0 = next(
        row for row in model["match_bin_rows"]
        if row["match_id"] == "M1" and row["angle_bin"] == 0
    )
    assert 184.0 <= match1_bin0["r_q90"] <= 186.0

    profile_bin0 = next(bin_row for bin_row in model["profile_bins"] if bin_row["angle_bin"] == 0)
    # Median should sit between match-level q90 values for M1 and M2.
    assert 181.5 <= float(profile_bin0["r_median"]) <= 183.5
    assert abs(float(profile_bin0["bin_coverage_pct"]) - 100.0) < 0.01


def test_outlier_is_soft_clipped_from_contour_inputs():
    points = []
    # Build dense sample so p99.5 clipping excludes an extreme outlier.
    for match_id in ("M1", "M2"):
        for bin_idx in range(12):
            angle_deg = (bin_idx * 15) + 1
            for _ in range(8):
                points.append(_point_from_polar(match_id, angle_deg, 180.0))

    # Single extreme point that should be clipped by p99.5 bound.
    points.append(_point_from_polar("M1", 1.0, 320.0))

    model = compute_boundary_shape_model(points=points, angle_bin_size=15, min_matches=20)
    profile_bin0 = next(bin_row for bin_row in model["profile_bins"] if bin_row["angle_bin"] == 0)

    assert model["matches_used"] == 2
    # If outlier leaked in, median contour near bin 0 would inflate materially.
    assert float(profile_bin0["r_median"]) < 200.0


def test_warning_flags_thresholds():
    warnings = _compose_warning_flags(
        matches_used=10,
        fours_nonzero_xy=800,
        nonzero_rate=0.40,
        avg_bins_with_data=6.0,
        bins_count=24,
        relative_sd=0.08,
    )
    assert "LOW_SAMPLE" in warnings
    assert "HIGH_SENTINEL_RATE" in warnings
    assert "SPARSE_ANGLE_COVERAGE" in warnings
    assert "HIGH_SHAPE_VOLATILITY" in warnings
