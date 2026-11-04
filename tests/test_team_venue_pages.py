import pytest

import services.page_builds as pb
import services.team_page as tp


def test_short_names():
    assert tp._short("England") == "ENG"
    assert tp._short("Central Districts") == "CD"
    assert tp._short("Royal Challengers Bengaluru") == tp._short("Royal Challengers Bangalore") == "RCB"


def test_batting_order_is_a_line_up(monkeypatch):
    # A floater who batted 4th to 7th takes only the spot he batted most; the others go to the next regular.
    rows = [
        {"batting_position": 4, "batter": "Dube", "innings_count": 13, "strike_rate": 170, "raa_per_100": 10.6},
        {"batting_position": 5, "batter": "Dube", "innings_count": 11, "strike_rate": 131, "raa_per_100": -6.4},
        {"batting_position": 5, "batter": "Brevis", "innings_count": 8, "strike_rate": 180, "raa_per_100": 20.0},
        {"batting_position": 6, "batter": "Dube", "innings_count": 9, "strike_rate": 132, "raa_per_100": -9.7},
        {"batting_position": 6, "batter": "Jadeja", "innings_count": 8, "strike_rate": 140, "raa_per_100": 2.0},
        {"batting_position": 4, "batter": "Jadeja", "innings_count": 2, "strike_rate": 120, "raa_per_100": -3.0},
    ]
    monkeypatch.setattr(tp, "_q", lambda db, scope, **kw: rows)
    order = tp.batting_order(None, "CSK", {"filters": {}})
    assert [(o["position"], o["batter"]) for o in order] == [(4, "Dube"), (5, "Brevis"), (6, "Jadeja")]
    assert order[1]["share"] == round(100 * 8 / 19)  # Brevis's share of all innings at 5


def test_get_or_build_starts_one_background_build(monkeypatch):
    import services.query_cache as qc

    monkeypatch.setattr(qc, "cached_get", lambda db, key: None)
    started = []

    class FakeThread:
        def __init__(self, target, args, daemon):
            started.append(args)

        def start(self):
            pass

    monkeypatch.setattr(pb.threading, "Thread", FakeThread)

    class Db:
        def rollback(self):
            pass

    key = {"kind": "test_page", "n": 1}
    for _ in range(2):
        with pytest.raises(pb.PageBuilding):
            pb.get_or_build(Db(), key, lambda d: {"ok": True})
    assert len(started) == 1  # the second request waits on the same build
    pb._BUILDING.discard(pb._key_str(key))


def test_get_or_build_serves_a_finished_build(monkeypatch):
    import services.query_cache as qc

    monkeypatch.setattr(qc, "cached_get", lambda db, key: None)
    key = {"kind": "test_page", "n": 2}
    pb._DONE[pb._key_str(key)] = {"ok": True}
    assert pb.get_or_build(object(), key, lambda d: None) == {"ok": True}
    pb._DONE.pop(pb._key_str(key))
