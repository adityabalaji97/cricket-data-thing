"""Ties, Super Over winners and no-results the feed leaves out (services/match_results.py)."""
from services.match_results import parse_result
from services.match_scorecard import _result_text


def _summary(text, winners=(False, False), teams=(("Lucknow Super Giants", "LSG"), ("Kolkata Knight Riders", "KKR"))):
    return {"header": {"competitions": [{
        "status": {"summary": text},
        "competitors": [{"team": {"displayName": n, "abbreviation": a}, "winner": "true" if w else "false"}
                        for (n, a), w in zip(teams, winners)],
    }]}}


def test_super_over_winner_from_the_abbreviation():
    out = parse_result(_summary("Match tied (KKR won the Super Over)"), "Kolkata Knight Riders", "Lucknow Super Giants")
    assert out["result"] == "tie" and out["eliminator"] == "Kolkata Knight Riders"


def test_boundary_count_decides_a_tie():
    out = parse_result(_summary("Match tied (England won the boundary count)", teams=(("New Zealand", "NZ"), ("England", "ENG"))),
                       "New Zealand", "England")
    assert out["eliminator"] == "England" and out["method"] == "boundary count"
    assert _result_text({"winner": None, "outcome": {"result": "tie", "eliminator": "England", "method": "boundary count"}}, []) == \
        "Match tied (England won on boundary count)"


def test_plain_tie_and_no_result():
    assert parse_result(_summary("Match tied"), "Kolkata Knight Riders", "Lucknow Super Giants")["result"] == "tie"
    assert parse_result(_summary("No result"), "Kolkata Knight Riders", "Lucknow Super Giants")["result"] == "no result"
    assert parse_result(_summary("Match abandoned without a ball bowled"), "A", "B")["result"] == "no result"


def test_an_unrecognised_side_is_not_guessed():
    assert parse_result(_summary("Match tied (XYZ won the Super Over)"), "Kolkata Knight Riders", "Lucknow Super Giants") is None
    assert parse_result({}, "A", "B") is None


def test_a_winner_espn_reports_is_flagged_not_written():
    out = parse_result(_summary("KKR won by 5 wkts", winners=(False, True)), "Kolkata Knight Riders", "Lucknow Super Giants")
    assert out == {"result": "win", "winner": "Kolkata Knight Riders", "text": "KKR won by 5 wkts"}


def test_scorecard_result_line_for_ties_and_no_results():
    assert _result_text({"winner": None, "outcome": {"result": "tie", "eliminator": "Kolkata Knight Riders"}}, []) == \
        "Match tied (Kolkata Knight Riders won the Super Over)"
    assert _result_text({"winner": None, "outcome": {"result": "tie"}}, []) == "Match tied"
    assert _result_text({"winner": None, "outcome": {"result": "no result"}}, []) == "No result"
    assert _result_text({"winner": None, "outcome": None}, []) == "Result unavailable"
