from services import results_parity as P
from sync_from_delivery_details import clean_winner


def _m(date, winner=None, outcome=None):
    return {"date": date, "winner": winner, "outcome": outcome}


def test_record_counts_ties_and_no_results_apart_from_losses():
    rows = [_m("2024-01-17", None, {"result": "tie", "eliminator": "India"}), _m("2024-06-29", "India"),
            _m("2024-07-06", "Zimbabwe"), _m("2023-10-07", None, {"result": "no result"}), _m("2023-08-06", "-")]
    rec = P.record(rows, "India")
    assert rec["2024"] == [3, 1, 1, 1, 0] and rec["2023"] == [2, 0, 0, 0, 2]  # "-" is never a winner


def test_compare_lists_only_the_years_that_differ():
    assert P.compare({"2010": [6, 3, 3, 0, 0], "2011": [4, 2, 2, 0, 0]}, {"2010": [7, 4, 3, 0, 0], "2011": [4, 2, 2, 0, 0]}) == [
        {"year": "2010", "ours": [6, 3, 3, 0, 0], "reference": [7, 4, 3, 0, 0]}]


def test_the_reference_adds_up():
    for year, (m, w, l, t, nr) in P.reference_for("India").items():
        assert m == w + l + t + nr, year
    assert sum(r[0] for r in P.reference_for("India").values()) == 300


def test_the_feed_s_blank_winner_is_no_winner():
    assert clean_winner("-") is None and clean_winner("") is None and clean_winner(None) is None
    assert clean_winner(" India ") == "India"


def test_the_byes_on_noballs_fix_sets_the_batter_to_nothing():
    from services.delivery_fixes import BYES_ON_NOBALLS

    assert "batruns = 0" in BYES_ON_NOBALLS and "WHERE batruns < 0" in BYES_ON_NOBALLS
    assert "COALESCE(byes, 0) + COALESCE(legbyes, 0)" in BYES_ON_NOBALLS
