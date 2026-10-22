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
