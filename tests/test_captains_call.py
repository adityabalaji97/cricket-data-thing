"""The captain's call (services/ig_posts/captains_call.py) and its card in the special recap: no database."""
from services.ig_posts import captains_call as C
from services.ig_posts import recap_special as R


def over(n, bowler, kind, runs, wp_from=None, wp_to=None):
    return {"over": n, "bowler": bowler, "kind": kind, "style": None, "runs": runs, "team": "Bowlers",
            "batting": "Batters", "wp_from": wp_from, "wp_to": wp_to, "batters": {}}


def innings():
    p, s = "pace bowler", "spin bowler"
    seq = [("A", p), ("B", p), ("A", p), ("C", s), ("B", p), ("A", p), ("D", p), ("E", s), ("D", p), ("E", s),
           ("F", s), ("C", s), ("F", s), ("B", p), ("E", s), ("C", s), ("E", s), ("B", p), ("C", s)]
    return [over(i + 1, b, k, 10, 80 - i, 79 - i - (30 if i + 1 == 17 else 0)) for i, (b, k) in enumerate(seq)]


def test_overs_left_before_the_marked_over():
    rows = {r["name"]: r for r in C.plan(innings(), 17)}
    assert rows["A"]["left"] == 1 and len(rows["A"]["cells"]) == 3  # 3 in the powerplay, the 4th never bowled
    assert rows["B"]["left"] == 1  # 3 before the 17th; the 4th came in the 18th
    assert rows["D"]["left"] == 2
    assert rows["E"]["left"] == 1  # the 17th itself isn't "before" it
    assert rows["C"]["kind"] == "spin" and rows["A"]["kind"] == "pace"


def test_swing_over_is_the_biggest_drop_for_the_bowling_side():
    assert C.swing_over(innings())["over"] == 17


def gate(monkeypatch, spin_death, death, other_left, norm=21.0, mark=17):
    fake = {"id": "bowling-plan", "help": "plan.", "facts": {"mark": mark, "spin_death": spin_death, "death": death,
                                                              "other_left": other_left}}
    monkeypatch.setattr(C, "plan_card", lambda db, mid, mark=None, sample="": dict(fake))
    monkeypatch.setattr(C, "mix_norm", lambda db, day, mark: {"defended": {"death": norm}})
    x = object.__new__(R.Match)
    x.db, x.id, x.day, x.sample, x.loser = None, "1", None, "", "Bowlers"
    x.innings = {2: [{"team_bowl": "Bowlers"}]}
    return R.captains_plan(x)


def test_plan_card_fires_on_a_spin_heavy_death(monkeypatch):
    c = gate(monkeypatch, spin_death=3, death=4, other_left=0)
    assert c and "about 21%" in c["help"]


def test_plan_card_fires_with_overs_of_the_other_kind_in_hand(monkeypatch):
    assert gate(monkeypatch, spin_death=1, death=4, other_left=2)


def test_plan_card_quiet_for_a_normal_plan(monkeypatch):
    assert gate(monkeypatch, spin_death=1, death=4, other_left=1) is None


def test_plan_card_quiet_before_the_death(monkeypatch):
    assert gate(monkeypatch, spin_death=3, death=4, other_left=3, mark=12) is None
