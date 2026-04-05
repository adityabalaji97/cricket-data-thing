from services.analytics_common import rolling_mean, split_spells_by_gap
from services.bowling_context import _aggregate_bowler_overs, classify_pressure_bucket
from services.resource_benchmark import compute_par_score_from_resource
from services.rolling_form import (
    _compute_batting_fantasy_points,
    _compute_bowling_fantasy_points,
    _merge_timeline_rows,
    _needs_delivery_details_augmentation,
    calculate_form_flag,
)
from datetime import date


def test_split_spells_by_gap():
    overs = [1, 3, 4, 8, 10, 15]
    spells = split_spells_by_gap(overs, gap_threshold=2)
    assert spells == [[1, 3, 4], [8, 10], [15]]


def test_pressure_bucket_assignment():
    assert classify_pressure_bucket(12, 10) == "high_pressure"
    assert classify_pressure_bucket(5, 10) == "low_pressure"
    assert classify_pressure_bucket(8, 10) == "neutral_pressure"
    assert classify_pressure_bucket(None, 10) == "no_previous_over"


def test_first_and_last_ball_boundary_detection():
    rows = [
        {
            "match_id": "m1",
            "innings": 1,
            "over_num": 7,
            "ball_num": 1,
            "bowler": "A",
            "total_runs": 4,
            "bat_runs": 4,
            "wicket": 0,
            "wide": 0,
            "noball": 0,
        },
        {
            "match_id": "m1",
            "innings": 1,
            "over_num": 7,
            "ball_num": 2,
            "bowler": "A",
            "total_runs": 1,
            "bat_runs": 1,
            "wicket": 0,
            "wide": 0,
            "noball": 0,
        },
        {
            "match_id": "m1",
            "innings": 1,
            "over_num": 7,
            "ball_num": 6,
            "bowler": "A",
            "total_runs": 6,
            "bat_runs": 6,
            "wicket": 0,
            "wide": 0,
            "noball": 0,
        },
    ]
    over_map = _aggregate_bowler_overs(rows)
    over = over_map[("m1", 1, 7)]
    assert over["first_ball_boundary"] is True
    assert over["last_ball_boundary"] is True
    assert over["boundaries"] == 2


def test_rolling_mean():
    values = [10, 20, 30, 40]
    assert rolling_mean(values, 2) == [10.0, 15.0, 25.0, 35.0]


def test_form_flag_logic():
    assert calculate_form_flag(130, 100, higher_is_better=True) == "hot"
    assert calculate_form_flag(80, 100, higher_is_better=True) == "cold"
    assert calculate_form_flag(100, 100, higher_is_better=True) == "neutral"


def test_resource_to_par_score():
    # 40% resource remaining means ~60% of baseline score should be reached.
    par = compute_par_score_from_resource(180, 40)
    assert round(par, 2) == 108.0


def test_delivery_details_augmentation_gap_check():
    assert _needs_delivery_details_augmentation([], date(2026, 4, 1)) is True
    assert _needs_delivery_details_augmentation([{"date": date(2026, 3, 20)}], date(2026, 4, 1)) is False
    assert _needs_delivery_details_augmentation([{"date": date(2026, 1, 1)}], date(2026, 4, 1)) is True


def test_fantasy_points_formula_smoke():
    batting_points = _compute_batting_fantasy_points(
        runs=52,
        balls_faced=30,
        fours=5,
        sixes=2,
        dismissed=True,
    )
    assert batting_points == 98.0

    bowling_points = _compute_bowling_fantasy_points(
        wickets=3,
        dots=10,
        overs=4.0,
        economy=6.5,
    )
    assert bowling_points == 91.0


def test_timeline_merge_prefers_augmented_rows():
    base = [
        {"match_id": "m1", "innings": 1, "date": date(2025, 5, 1), "economy": 8.4},
    ]
    augmented = [
        {"match_id": "m1", "innings": 1, "date": date(2025, 5, 1), "economy": 7.2},
        {"match_id": "m2", "innings": 1, "date": date(2026, 4, 2), "economy": 6.9},
    ]
    merged = _merge_timeline_rows(base, augmented)
    assert len(merged) == 2
    assert merged[0]["match_id"] == "m1"
    assert merged[0]["economy"] == 7.2
    assert merged[1]["match_id"] == "m2"
