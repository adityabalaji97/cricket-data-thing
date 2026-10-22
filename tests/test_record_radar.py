from datetime import date

from services import record_radar as R

DAY = date(2026, 10, 22)
T20I = R.Scope("t20i", "in T20Is", {"t20i": True})
PP = next(t for t in R.TEMPLATES if t.id == "pp-sixes")
POS = next(t for t in R.TEMPLATES if t.id == "pos-sixes")


def row(name, sixes, today=False, phase="pp", pos=1, team="India", t20i=True):
    return {"name": name, "team": team, "comp": "T20I", "t20i": t20i, "phase": phase, "pos": pos, "today": today,
            "runs": 6 * sixes, "sixes": sixes, "fours": 0}


def test_passing_the_leader_names_him():
    rows = [row("Rohit Sharma", 98), row("Abhishek Sharma", 96), row("Abhishek Sharma", 3, today=True)]
    ev = R.events_for(rows, PP, T20I, DAY)
    passed = [e for e in ev if e["kind"] == "passed"]
    assert len(passed) == 1 and passed[0]["rank_after"] == 1 and passed[0]["passed"] == [("Rohit Sharma", 98)]
    assert R.headline(passed[0]) == ("Abhishek Sharma now has the most powerplay sixes in T20Is: 99, past Rohit "
                                     "Sharma (98)")


def test_a_tie_is_level_not_passed():
    rows = [row("Jos Buttler", 95, team="England"), row("Abhishek Sharma", 93), row("Abhishek Sharma", 2, today=True)]
    e = next(e for e in R.events_for(rows, PP, T20I, DAY) if e["kind"] == "passed")
    assert e["passed"] == [] and e["level"] == [("Jos Buttler", 95)]


def test_small_counts_and_low_positions_are_not_records():
    rows = [row("A", 3), row("B", 2), row("B", 2, today=True)]  # 4 sixes: below the template's first milestone
    assert R.events_for(rows, PP, T20I, DAY) == []
    rows = [row("C", 70, pos=10), row("D", 69, pos=10), row("D", 2, today=True, pos=10)]
    assert R.events_for(rows, POS, T20I, DAY) == []


def test_milestone_and_its_order():
    rows = [row("X", 120), row("Y", 98), row("Y", 3, today=True)]
    m = next(e for e in R.events_for(rows, PP, T20I, DAY) if e["kind"] == "milestone")
    assert (m["milestone"], m["nth"]) == (100, 2)
    assert R.headline(m) == "Y reaches 100 powerplay sixes in T20Is, the 2nd to get there"


def test_scope_filters_team_and_t20i():
    rows = [row("E", 60, team="Nepal"), row("F", 55), row("F", 6, today=True), row("G", 500, t20i=False)]
    india = R.Scope("t20i:India", "for India in T20Is", {"t20i": True, "team": "India"})
    board = R._boards(PP, rows, india, False)[None]
    assert board == {"F": 61}


def test_pick_one_per_player_best_first():
    e = lambda p, kind, rank, scope="t20i", tid="sixes", nth=9: {  # noqa: E731
        "player": p, "kind": kind, "rank_after": rank, "scope": scope, "template": tid, "nth": nth}
    events = [e("A", "passed", 1), e("A", "entered", 9), e("B", "milestone", 4, nth=1), e("C", "entered", 10, "t20i:Malaysia")]
    fame = {"A": 1.4, "B": 1.4, "C": 1.4}
    got = R.pick(events, fame, 2)
    assert [x["player"] for x in got] == ["A", "B"] and got[0]["kind"] == "passed"


def test_associate_team_lists_weigh_less_than_top_sides():
    assert R._scope_weight("t20i:India") > R._scope_weight("t20i:Malaysia")
    assert R._scope_weight("t20i") > R._scope_weight("t20i:India")


def test_namesakes_split_by_side_main_side_keeps_the_name():
    split = {"Rohit Sharma": {"India": "Rohit Sharma", "Indonesia": "Rohit Sharma (Indonesia)", "__main__": "Rohit Sharma"}}
    rows = [row("Rohit Sharma", 98, team="India"), row("Rohit Sharma", 3, team="Indonesia"),
            row("Rohit Sharma", 50, team="Mumbai Indians", t20i=False)]
    got = R.split_namesakes(rows, split)
    assert [r["name"] for r in got] == ["Rohit Sharma", "Rohit Sharma (Indonesia)", "Rohit Sharma"]
    assert R._boards(PP, got, T20I, False)[None] == {"Rohit Sharma": 98, "Rohit Sharma (Indonesia)": 3}


def test_switchers_and_renamed_sides_are_one_person():
    assert "Tim David" in R.SWITCHED
    assert R.SIDE_ALIAS["Swaziland"] == "Eswatini"
