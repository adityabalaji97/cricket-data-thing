from datetime import date

import services.on_this_day as otd


def _c(key, score):
    return {"key": key, "score": score}


def test_yesterdays_competition_loses_to_a_close_second(monkeypatch):
    monkeypatch.setattr(otd, "candidates", lambda db, day: [_c("IPL", 1.0), _c("BBL", 0.85)])
    assert otd.pick(None, date(2026, 1, 1), avoid=("IPL",))["key"] == "BBL"


def test_but_not_to_a_much_weaker_one(monkeypatch):
    monkeypatch.setattr(otd, "candidates", lambda db, day: [_c("IPL", 1.0), _c("BBL", 0.5)])
    assert otd.pick(None, date(2026, 1, 1), avoid=("IPL",))["key"] == "IPL"


def test_no_matches_no_post(monkeypatch):
    monkeypatch.setattr(otd, "candidates", lambda db, day: [])
    assert otd.pick(None, date(2026, 1, 1)) is None


def test_tags():
    assert otd._competition_tag("IPL") == "#IPL" and otd._competition_tag("Nepal Premier League") is None
    assert otd._fixture_tag({"key": "IPL", "team1": "Kolkata Knight Riders", "team2": "Mumbai Indians"}) == "#KKRvMI"
