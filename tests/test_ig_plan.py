from datetime import date

import services.ig_plan as plan
import services.ig_season as season

DAY = date(2026, 10, 23)


def _row(i, key, source, status="ready"):
    return {"id": i, "angle_key": key, "source": source, "pillar": "reactive", "title": key, "status": status,
            "planned_for": DAY, "post_by": None, "facts": {}}


def _week(monkeypatch, rows):
    monkeypatch.setattr(plan, "_rows", lambda db, s, e: rows)
    monkeypatch.setattr(season, "major_series", lambda db, day: None)
    monkeypatch.setattr(season, "focus", lambda day, series: None)
    monkeypatch.setattr(season, "post_format", lambda facts, key: "carousel")
    return plan.week(None, DAY, 1)[0]


def test_a_hand_made_look_back_takes_the_slot(monkeypatch):
    d = _week(monkeypatch, [_row(1, "ig:otd-2026-10-23", "ig-otd"), _row(2, "ig:otd-ind-pak-mcg-2022", "hand")])
    assert [p["id"] for p in d["posts"]] == [2] and [e["id"] for e in d["extras"]] == [1]


def test_the_automatic_one_stays_when_it_is_the_only_one(monkeypatch):
    d = _week(monkeypatch, [_row(1, "ig:otd-2026-10-23", "ig-otd")])
    assert [p["id"] for p in d["posts"]] == [1] and d["extras"] == []
