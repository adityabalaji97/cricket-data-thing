from datetime import date

import services.on_this_day as otd


def _c(key, score):
    return {"key": key, "score": score}


def test_the_best_story_goes_out_whatever_ran_yesterday(monkeypatch):
    monkeypatch.setattr(otd, "candidates", lambda db, day: [_c("T20I", 1.4), _c("IPL", 1.2)])
    assert otd.pick(None, date(2026, 1, 1))["key"] == "T20I"


def test_two_stories_beat_one_bigger_number():
    # Kohli at the MCG: a comeback and a match-winning innings, against one big bowling spell.
    both, angle = otd.story_score({"performance": 0.85, "clutch": 1.5, "comeback": 1.24})
    one, _ = otd.story_score({"performance": 1.6, "clutch": 0.3, "comeback": 0.0})
    assert angle == "clutch" and both > one


def test_world_cup_is_the_main_event_not_its_qualifiers():
    assert otd._world_cup("ICC Men's T20 World Cup") and otd._world_cup("ICC World Twenty20") and otd._world_cup("World T20")
    assert not otd._world_cup("ICC Men's T20 World Cup Europe Region Qualifier")
    assert not otd._world_cup("ICC Men's T20 World Cup Asia Qualifier Final") and not otd._world_cup(None)


def test_no_matches_no_post(monkeypatch):
    monkeypatch.setattr(otd, "candidates", lambda db, day: [])
    assert otd.pick(None, date(2026, 1, 1)) is None


def test_tags():
    assert otd._competition_tag("IPL") == "#IPL" and otd._competition_tag("Nepal Premier League") is None
    assert otd._fixture_tag({"key": "IPL", "team1": "Kolkata Knight Riders", "team2": "Mumbai Indians"}) == "#KKRvMI"
