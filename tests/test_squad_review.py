from services import squad_review as S


def v(bat=0, bowl=0, pos=5.0, bowl_by=None):
    return {"bat": {}, "bowl": bowl_by or {}, "bat_balls": bat, "bowl_balls": bowl, "pos": pos, "kind": "pace"}


def test_regulars_first_then_the_most_established_and_the_overseas_cap():
    values = {f"R{i}": v(bat=500) for i in range(9)}
    values.update({"fringe": v(bat=10), "marquee": v(bat=3000), "O1": v(bat=2000), "O2": v(bat=2000)})
    apps = {**{f"R{i}": 10 for i in range(9)}, "fringe": 1}
    xi = S.likely_xi(list(values), {"O1", "O2", "marquee"}, values, apps, cap=2)
    assert all(f"R{i}" in xi for i in range(9))
    assert "fringe" not in xi  # one game last season doesn't beat an established player
    assert sum(1 for p in xi if p in {"O1", "O2", "marquee"}) == 2


def test_unknown_players_start_below_average():
    assert S.bat_value(v(), "middle") < 0
    assert S.bowl_value(v(bowl=60, bowl_by={"middle": (0.0, 60)}), "death") < 0
    assert S.bowl_value(v(), "middle") is None  # never bowled: no overs


def test_usage_overs_fill_twenty_and_cap_four():
    values = {f"B{i}": v(bowl=600, bowl_by={"powerplay": (0, 200), "middle": (0, 200), "death": (0, 200)}) for i in range(5)}
    plan = S.usage_overs(list(values), values)
    assert sum(n for by in plan.values() for n in by.values()) == 20
    assert all(sum(by.values()) <= S.MAX_OVERS for by in plan.values())
    assert sum(plan[p].get("powerplay", 0) for p in plan) == 6
