"""services/ig_posts/openers_case.py: powerplay innings sorted big / middling / cost, the possible top threes (a keeper
in each) and the case slide written from them."""
from services.ig_posts import openers_case as O

SPEC = {"candidates": ["A One", "B Two", "C Three", "D Four"], "keepers": ["C Three", "D Four"],
        "names": {n: n for n in ["A One", "B Two", "C Three", "D Four"]},
        "side_word": "India's"}


def _inn(impact, runs=10, balls=8, wickets=0, wpa=0.0):
    return {"impact": impact, "runs": runs, "balls": balls, "wickets": wickets, "wpa": wpa, "strike_rate": 100 * runs / balls}


def test_groups_split_at_zero_and_fifteen():
    assert [O.group(x) for x in (-0.1, 0, 14.9, 15, 40)] == ["cost", "mid", "mid", "big", "big"]


def test_profile_shares_add_up():
    p = O.profile([_inn(20), _inn(5), _inn(-3), _inn(-8)])
    assert (p["big"], p["mid"], p["cost"]) == (25, 25, 50)
    assert p["big"] + p["mid"] + p["cost"] == 100


def test_hook_is_one_pooled_number():
    mine = [_inn(-1)] * 3 + [_inn(20)] * 5
    assert O.hook_text(SPEC, mine).startswith("India's four openers fail in 38% of their powerplay innings.")


def test_every_top_three_has_a_keeper(monkeypatch):
    monkeypatch.setattr(O, "batter_hand", lambda db, p: "RHB" if p == "C Three" else "LHB")
    prof = {p: {"big": 20 + i, "cost": 40 - i, "n": 30} for i, p in enumerate(SPEC["candidates"])}
    rows = {p: {"impact": 10.0 * (i + 1), "balls": 100} for i, p in enumerate(SPEC["candidates"])}
    ups = O.lineups(None, SPEC, prof, rows)
    assert len(ups) == 4  # one of the four sits out; leaving out a keeper still leaves the other
    assert all(set(u["three"]) & set(SPEC["keepers"]) for u in ups)
    allleft = next(u for u in ups if u["out"] == "C Three")
    assert allleft["lefties"] == 3


def test_case_slide_gives_each_top_three_a_reason(monkeypatch):
    monkeypatch.setattr(O, "batter_hand", lambda db, p: "RHB" if p == "C Three" else "LHB")
    prof = {p: {"big": 20 + i, "cost": 40 - i, "n": 30 + i} for i, p in enumerate(SPEC["candidates"])}
    rows = {p: {"impact": 10.0 * (i + 1), "balls": 100} for i, p in enumerate(SPEC["candidates"])}
    ups = O.lineups(None, SPEC, prof, rows)
    attack = {"payload": {"metrics": [{"key": "Off-spin"}], "rows": [
        {"name": "C Three", "values": {"Off-spin": 40}}, {"name": "A One", "values": {"Off-spin": 5}}]}}
    body = O.case_slide(SPEC, ups, attack, "One caution.")["body"].split("\n")
    assert len(body) == 5 and body[-1] == "One caution."
    left = next(l for l in body if l.startswith("Without C Three"))
    assert "loses C Three v off-spin (+40)" in left and "all left-handed" in left
