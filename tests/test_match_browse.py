from datetime import date

from services.match_browse import _where


def test_on_this_day_and_year_filters():
    where, params = _where("all", None, None, 2016, "10-16", None, None)
    assert "to_char(m.date, 'MM-DD') = :month_day" in where and params["month_day"] == "10-16"
    assert params["year_start"] == date(2016, 1, 1) and params["year_end"] == date(2017, 1, 1)


def test_a_bad_month_day_is_ignored():
    where, params = _where("all", None, None, None, "13-40", None, None)
    assert "month_day" not in params and "MM-DD" not in where


def test_head_to_head_needs_both_sides():
    where, params = _where("T20I", "India", "West Indies", None, None, None, None)
    assert params["intl_format"] == "T20"
    assert "india" in params["team_candidates"] and "west indies" in params["opponent_candidates"]
    assert where.count("LOWER(m.team1)") == 2


def test_a_league_filters_by_its_names():
    where, params = _where("IPL", None, None, None, None, None, None)
    assert "m.competition = ANY(:competition_values)" in where and params["competition_values"]
