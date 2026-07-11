from datetime import date

from services.match_scorecard import (
    data_source_for_match_date,
    _balls_to_overs,
    _bowl_vs_row,
    _capabilities_for_source,
    _econ_color,
    _top_performers,
)


def test_data_source_routes_pre_2015_to_legacy_deliveries():
    assert data_source_for_match_date(date(2014, 12, 31)) == "deliveries"


def test_data_source_routes_2015_and_later_to_delivery_details():
    assert data_source_for_match_date(date(2015, 1, 1)) == "delivery_details"
    assert data_source_for_match_date(date(2026, 7, 10)) == "delivery_details"


def test_balls_to_overs_uses_cricket_notation():
    assert _balls_to_overs(0) == "0.0"
    assert _balls_to_overs(20) == "3.2"
    assert _balls_to_overs(120) == "20.0"


def test_economy_bar_colors_match_scorecard_thresholds():
    assert _econ_color(6.9) == "#b6f24a"
    assert _econ_color(7.0) == "#f0b429"
    assert _econ_color(9.0) == "#f0b429"
    assert _econ_color(9.1) == "#e5484d"


def test_delivery_details_capabilities_include_advanced_lenses():
    capabilities = _capabilities_for_source("delivery_details", [])
    assert capabilities["core_scorecard"] is True
    assert capabilities["zones"] is True
    assert capabilities["line_length"] is True
    assert capabilities["control"] is True


def test_legacy_capabilities_disable_advanced_tracking():
    capabilities = _capabilities_for_source("deliveries", [])
    assert capabilities["core_scorecard"] is True
    assert capabilities["vs_player"] is True
    assert capabilities["phase"] is True
    assert capabilities["pace_spin"] is True
    assert capabilities["zones"] is False
    assert capabilities["line_length"] is False
    assert capabilities["control"] is False


def test_bowler_vs_batter_row_includes_boundaries_conceded():
    row = _bowl_vs_row({
        "item": "Phil Salt",
        "runs": 16,
        "balls": 12,
        "wickets": 1,
        "fours": 2,
        "sixes": 1,
        "dots": 5,
    })

    assert row["fours"] == 2
    assert row["sixes"] == 1
    assert row["econ"] == 8.0


def test_top_performers_include_scorecard_navigation_metadata():
    performers = _top_performers([
        {
            "innings": 1,
            "batting_team": "India",
            "bowling_team": "England",
            "batting": [{"id": "shreyas-iyer", "name": "Shreyas Iyer", "runs": 80, "not_out": False}],
            "bowling": [{"id": "jofra-archer", "name": "Jofra Archer", "wickets": 3, "runs": 28}],
        }
    ])

    assert performers[0]["screen"] == "batting"
    assert performers[0]["innings"] == 1
    assert performers[0]["player_id"] == "shreyas-iyer"
    assert performers[1]["screen"] == "bowling"
    assert performers[1]["lens"] == "batter"
