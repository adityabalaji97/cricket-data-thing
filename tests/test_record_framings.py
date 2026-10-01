"""Record framings (services/record_framings.py): streaks, firsts, fastest milestones, ground records."""
from datetime import date

import pytest

from services import record_framings as rf
from services.content_rules import check_title

IPL = {"fmt": "T20", "label": "IPL", "where": "1=1", "params": {}, "international": False}
ODI = {"fmt": "ODI", "label": "ODI", "where": "1=1", "params": {}, "international": True}


def _match(**kw):
    return {"id": "9", "date": date(2026, 4, 20), "team1": "A", "team2": "B", "winner": "A", "venue": "Ground X, City",
            "gender": "male", "data_source": "bbb", **kw}


def _results(team_runs):
    """{team: 'WWLW...'} -> the shape _team_results returns; the last entry of team A is match 9."""
    out = {}
    for team, seq in team_runs.items():
        rows = []
        for i, r in enumerate(seq):
            mid = "9" if team == "A" and i == len(seq) - 1 else f"{team}{i}"
            rows.append({"match_id": mid, "date": date(2016 + i // 10, 1 + i % 10, 1), "opp": "Z", "venue": "V", "r": r})
        out[team] = rows
    return out


def _checks(fact):
    errors, _ = check_title(fact["title"], [fact["numbers"], {"n": fact.get("n"), "since": fact.get("since_year"),
                                                              "rank": fact.get("rank")}], fact["subject"])
    assert not errors, (fact["title"], errors)


def test_runs_are_maximal():
    seq = [{"r": x} for x in "WWLWWWNW"]
    assert [r["length"] for r in rf._runs(seq, lambda e: e["r"] == "W")] == [2, 3, 1]


def test_winning_run_ranked_against_every_run(monkeypatch):
    # 60 other teams each with a 2-match run; A's current run of 7 is the longest.
    teams = {f"T{i}": "WWL" for i in range(60)}
    teams["A"] = "LLWWWWWWW"
    teams["B"] = "WWWWWWWWL"
    monkeypatch.setattr(rf, "_team_results", lambda db, scope, g: _results(teams))
    facts = rf.team_streaks(None, _match(), IPL)
    a = next(f for f in facts if f["subject"] == "A")
    assert a["title"].startswith("A have won 7 IPL matches in a row, the 2nd-longest IPL winning run since 2016")
    assert a["rank"] == 2 and a["chart"]["rows"][1]["highlight"]
    _checks(a)


def test_own_longest_run_says_since_when(monkeypatch):
    # A's 5-match run is ordinary overall but A's best since its 2016 runs.
    teams = {f"T{i}": "WWWWWWWWWL" for i in range(60)}
    teams["A"] = "WWLWLWWWLLLWWWLLLLLLLLLLLLLLLWWWWW"[:-5] + "WWWWW"
    monkeypatch.setattr(rf, "_team_results", lambda db, scope, g: _results(teams))
    fact = next(f for f in rf.team_streaks(None, _match(), IPL) if f["subject"] == "A")
    assert "A's longest IPL winning run since 2016" in fact["title"] and fact["rank"] is None
    # The chart is A's own runs, the current one first and highlighted.
    assert fact["chart"]["rows"][0]["highlight"] and fact["chart"]["rows"][0]["length"] == 5
    _checks(fact)


def test_head_to_head_first_since(monkeypatch):
    history = [{"date": date(2019, 3, 1), "r": "W"}] + [{"date": date(2021 + i, 3, 1), "r": "L"} for i in range(5)]
    monkeypatch.setattr(rf, "_history", lambda db, m, s, team, extra, params: history if "opp" in params else [])
    facts = rf.team_firsts(None, _match(), ODI)
    assert len(facts) == 1
    assert facts[0]["title"] == "A beat B in an ODI for the first time since 2019, ending a run of 5 defeats"
    assert facts[0]["chart"]["rows"][0] == {"rank": 1, "label": "2026", "wins": 1, "display": "1-0", "highlight": True}
    _checks(facts[0])


def test_first_ever_win_and_ground_wording(monkeypatch):
    defeats = [{"date": date(2023 + i // 3, 1 + i, 1), "r": "L"} for i in range(4)]
    monkeypatch.setattr(rf, "_history", lambda db, m, s, team, extra, params: defeats)
    facts = {f["kind"]: f for f in rf.team_firsts(None, _match(), {**IPL, "label": "MLC"})}
    assert facts["h2h_first_since"]["title"] == "A beat B in the MLC for the first time, at the 5th attempt"
    assert facts["venue_first_since"]["title"].startswith("A won an MLC match at Ground X for the first time")
    for f in facts.values():
        _checks(f)


def test_no_first_without_a_run_of_defeats(monkeypatch):
    monkeypatch.setattr(rf, "_history", lambda *a: [{"date": date(2025, 1, 1), "r": "L"}] * 3)
    assert rf.team_firsts(None, _match(), IPL) == []


def test_fastest_fifty_uses_lower_is_better_chart(monkeypatch):
    pop = [{"match_id": f"m{i}", "inns": 1, "name": f"P{i}", "team": "C", "opp": "D", "date": date(2018, 1, 1),
            "b50": 20 + i % 15, "b100": None} for i in range(300)]
    pop.append({"match_id": "9", "inns": 1, "name": "Star", "team": "A", "opp": "B", "date": date(2026, 4, 20), "b50": 14, "b100": None})
    monkeypatch.setattr(rf, "_cached", lambda db, key, build: pop)
    facts = rf.fastest_milestones(None, _match(), IPL)
    assert len(facts) == 1
    f = facts[0]
    assert f["title"] == "Star's fifty v B came off 14 balls, the fastest IPL fifty since 2018"
    assert f["chart"]["lower_is_better"] and f["chart"]["rows"][0]["highlight"]
    _checks(f)


def test_fastest_skips_basic_data_matches():
    assert rf.fastest_milestones(None, _match(data_source="cricsheet"), IPL) == []


def test_ground_records_only_the_top(monkeypatch):
    base = [{"match_id": f"m{i}", "inns": 1 + i % 2, "team": f"T{i}", "venue": "Ground X, City", "date": date(2020, 1, 1),
             "winner": f"T{i}", "runs": 140 + i, "wkts": 5, "max_balls": 120} for i in range(60)]
    mine = [{"match_id": "9", "inns": 1, "team": "A", "venue": "Ground X, City", "date": date(2026, 4, 20), "winner": "A",
             "runs": 250, "wkts": 3, "max_balls": 120},
            {"match_id": "9", "inns": 2, "team": "B", "venue": "Ground X, City", "date": date(2026, 4, 20), "winner": "A",
             "runs": 180, "wkts": 9, "max_balls": 120}]
    monkeypatch.setattr(rf, "_team_totals", lambda db, fmt, g: base + mine)
    facts = rf.venue_records(None, _match(), IPL)
    assert [f["kind"] for f in facts] == ["venue_total"]
    assert facts[0]["title"] == "A's 250/3 is the highest T20 total at Ground X since 2020"
    _checks(facts[0])


@pytest.mark.parametrize("word,expected", [("MLC", "an"), ("BBL", "a"), ("SA20", "an"), ("IPL", "an"), ("T20 Blast", "a")])
def test_article(word, expected):
    assert rf._article(word) == expected
