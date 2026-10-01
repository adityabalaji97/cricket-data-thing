"""Season tallies (services/season_tallies.py): ESPN event parsing, the points table, the simulation."""
from datetime import date

import pytest

from services import season_tallies as st
from services.content_rules import check_title


def _espn_event(eid, d, desc, a, b, winner=None, summary="", state="post", abbr=("AAA", "BBB")):
    return {"id": eid, "date": f"{d}T14:00Z", "description": desc, "season": {"year": 2027},
            "status": {"type": {"state": state}, "summary": summary},
            "competitions": [{"competitors": [
                {"team": {"displayName": a, "abbreviation": abbr[0]}, "winner": "true" if winner == a else "false"},
                {"team": {"displayName": b, "abbreviation": abbr[1]}, "winner": "true" if winner == b else "false"}]}]}


def test_event_parsing_marks_playoffs_and_super_overs():
    league = st._event(_espn_event("1", "2027-04-01", "30th Match (N), Indian Premier League at Pune, Apr 1 2027", "A", "B", "A"))
    assert not league["playoff"] and league["winner"] == "A" and league["date"] == "2027-04-01"
    final = st._event(_espn_event("2", "2027-05-30", "Final (N), Indian Premier League at Ahmedabad", "A", "B"))
    assert final["playoff"]
    tie = st._event(_espn_event("3", "2027-04-26", "38th Match", "Lucknow", "Kolkata", None,
                                "Match tied (KKR won the Super Over)", abbr=("LSG", "KKR")))
    assert tie["winner"] == "Kolkata"
    # "Final" in the venue part of a description is not a final.
    assert st._event(_espn_event("4", "2027-04-02", "12th Match, Final Frontier Series at X", "A", "B"))["playoff"] is False


class _DB:
    """Stub session: no stored results, no ball-by-ball totals."""
    def execute(self, *a, **k):
        class R:
            def mappings(self):
                return []
        return R()


def test_points_table_counts_results_and_leaves_the_rest():
    schedule = [st._event(e) for e in [
        _espn_event("1", "2027-04-01", "1st Match", "A", "B", "A"),
        _espn_event("2", "2027-04-02", "2nd Match", "C", "D", None, "No result"),
        _espn_event("3", "2027-04-03", "3rd Match", "A", "C", "C"),
        _espn_event("4", "2027-04-09", "4th Match", "B", "D", state="pre"),
        _espn_event("5", "2027-05-01", "Qualifier 1", "A", "C", state="pre"),
    ]]
    state = st.points_table(_DB(), schedule)
    table = {r["team"]: r for r in state["table"]}
    assert state["played"] == 3 and state["remaining"] == [("B", "D")]
    assert (table["A"]["points"], table["C"]["points"], table["D"]["points"], table["B"]["points"]) == (2, 3, 1, 0)
    replay = st.points_table(_DB(), schedule, as_of=date(2027, 4, 3))
    assert replay["played"] == 2 and ("A", "C") in replay["remaining"]


def test_simulation_respects_a_settled_table():
    table = [{"team": t, "points": p, "nrr": 0.0} for t, p in [("A", 20), ("B", 18), ("C", 2), ("D", 0)]]
    probs = st.simulate(table, [("C", "D")], {t: 1500 for t in "ABCD"}, spots=2, sims=2000)
    assert probs["A"]["top"] == 1.0 and probs["B"]["top"] == 1.0 and probs["D"]["top"] == 0.0


def test_simulation_follows_elo():
    table = [{"team": t, "points": 0, "nrr": 0.0} for t in "AB"]
    remaining = [("A", "B")] * 10
    probs = st.simulate(table, remaining, {"A": 1700, "B": 1300}, spots=1, sims=4000)
    assert probs["A"]["top"] > 0.9
    assert st.win_probability(1500, 1500) == pytest.approx(0.5)


@pytest.mark.parametrize("p,shown", [(1.0, "100%"), (0.997, ">99%"), (0.5, "50%"), (0.003, "<1%"), (0.0, "0%")])
def test_percentages_are_honest_at_the_ends(p, shown):
    assert st._pct(p) == shown


def test_playoff_title_passes_the_content_rules(monkeypatch):
    schedule = [st._event(_espn_event(str(i), f"2027-04-{1 + i:02d}", f"{i}th Match", a, b, a))
                for i, (a, b) in enumerate([("A", "B"), ("C", "D"), ("A", "C"), ("B", "D"), ("A", "D"), ("B", "C")] * 2)]
    schedule += [st._event(_espn_event("99", "2027-05-20", "50th Match", "A", "B", state="pre"))]
    monkeypatch.setattr(st, "MIN_PLAYED", 4)
    import services.match_preview as mp
    monkeypatch.setattr(mp, "_get_latest_elo", lambda db, team, before=None: 1500)
    fact = st.playoff_fact(_DB(), "IPL", schedule)
    errors, _ = check_title(fact["title"], [fact["numbers"]], fact["subject"])
    assert not errors, fact["title"]
    assert fact["title"].startswith("A are ") and "IPL 2027 playoffs after 12 matches" in fact["title"]


def test_season_label():
    assert st.season_label("IPL", date(2027, 3, 20), date(2027, 5, 30)) == "IPL 2027"
    assert st.season_label("BBL", date(2026, 12, 12), date(2027, 1, 25)) == "BBL 2026-27"
