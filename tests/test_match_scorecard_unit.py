from datetime import date

from services.match_scorecard import (
    data_source_for_match_date,
    _balls_to_overs,
    _bowl_vs_row,
    _capabilities_for_source,
    _econ_color,
    _top_performers,
    _build_summary,
    _result_text,
    _worm_ticks,
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


def _inn(number, team, runs, wickets, target=None, worm=None):
    return {
        "innings": number,
        "batting_team": team,
        "score": {"team": team, "runs": runs, "wickets": wickets, "target": target},
        "worm": worm or [],
    }


def test_result_text_uses_singular_margins():
    match = {"winner": "A", "outcome": {"by": {"wickets": 1}}}
    assert _result_text(match, []) == "A won by 1 wicket"
    assert _result_text({"winner": "A", "outcome": {"by": {"runs": 1}}}, []) == "A won by 1 run"


def test_result_text_derives_bat_first_margin_only_without_a_revised_target():
    innings = [_inn(1, "AUS", 356, 6), _inn(2, "ZIM", 272, 10, target=357)]
    assert _result_text({"winner": "AUS"}, innings) == "AUS won by 84 runs"
    # DLS: the chase target was revised, so raw scores do not give the margin.
    revised = [_inn(1, "AUS", 356, 6), _inn(2, "ZIM", 200, 10, target=250)]
    assert _result_text({"winner": "AUS"}, revised) == "AUS won"


def test_worm_ticks_follow_the_format_length():
    assert _worm_ticks(20) == [5, 10, 15, 20]
    assert _worm_ticks(50) == [10, 20, 30, 40, 50]


def test_worm_innings_share_one_scale():
    innings = [
        _inn(1, "AUS", 200, 5, worm=[50, 100, 200]),
        _inn(2, "ZIM", 100, 10, worm=[50, 100]),
    ]
    summary = _build_summary({"format": "T20"}, innings)
    first, second = summary["worm"]
    # Same runs at the same over land on the same point; the shorter, lower innings ends lower
    # and earlier instead of being stretched to the top-right corner.
    assert first["points"].split()[1] == second["points"].split()[1]
    assert second["points"].split()[-1] != first["points"].split()[-1]
    assert summary["worm_axis"] == [5, 10, 15, 20]

