"""The wicket-style card: his split against a typical bowler of his type where he bowled (services/wicket_style.py)."""
from services import wicket_style as W


def _fake(monkeypatch, mine, typ):
    monkeypatch.setattr(W, "_tables", lambda db, fmt, who, balls=True: mine)
    monkeypatch.setattr(W, "typical_tables", lambda db, fmt, base, flt, perspective="bowling": typ)


def test_typical_is_weighted_by_where_he_took_his_wickets(monkeypatch):
    # 30 wickets in a league where a quarter of wickets are LBW, 10 where none are: typical LBW = 30*0.25/40.
    mine = {"wickets": {("A", 2025, "spin bowler"): {"bowled": 10, "lbw": 10, "caught": 10, "stumped": 0},
                        ("B", 2025, "spin bowler"): {"bowled": 2, "lbw": 0, "caught": 8, "stumped": 0}},
            "balls": {("A", 2025, "spin bowler"): {"tagged": 400, "attack": 200}}}
    typ = {"wickets": {"A|2025|spin bowler": {"bowled": 25, "lbw": 25, "caught": 50, "stumped": 0},
                       "B|2025|spin bowler": {"bowled": 20, "lbw": 0, "caught": 80, "stumped": 0}},
           "balls": {"A|2025|spin bowler": {"tagged": 1000, "attack": 300}}}
    _fake(monkeypatch, mine, typ)
    s = W.wicket_style(None, "T20", "X", {})
    assert s["kind"] == "spin" and s["wickets"] == 40
    assert s["split"] == {"bowled": 12, "lbw": 10, "caught": 18, "stumped": 0}
    assert s["typical"]["lbw"] == round(100 * 7.5 / 40, 1)
    assert s["attack"] == {"share": 50.0, "typical": 30.0, "tagged": 400}


def test_floors_hide_the_comparison_not_the_split(monkeypatch):
    mine = {"wickets": {("A", 2025, "pace bowler"): {"bowled": 3, "lbw": 1, "caught": 6, "stumped": 0}},
            "balls": {("A", 2025, "pace bowler"): {"tagged": 100, "attack": 30}}}
    typ = {"wickets": {"A|2025|pace bowler": {"bowled": 20, "lbw": 5, "caught": 75, "stumped": 0}},
           "balls": {"A|2025|pace bowler": {"tagged": 1000, "attack": 200}}}
    _fake(monkeypatch, mine, typ)
    s = W.wicket_style(None, "T20", "X", {})
    assert s["wickets"] == 10 and s["typical"] is None and s["attack"] is None


def test_no_wickets_no_card(monkeypatch):
    _fake(monkeypatch, {"wickets": {}, "balls": {}}, {"wickets": {}, "balls": {}})
    assert W.wicket_style(None, "T20", "X", {}) is None


def test_a_batter_needs_more_dismissals_and_has_no_stumps_line(monkeypatch):
    w = {("A", 2025, "pace bowler"): {"bowled": 8, "lbw": 2, "caught": 15, "stumped": 0}}
    typ = {"wickets": {"A|2025|pace bowler": {"bowled": 20, "lbw": 5, "caught": 75, "stumped": 0}}, "balls": {}}
    _fake(monkeypatch, {"wickets": w, "balls": {}}, typ)
    s = W.wicket_style(None, "T20", "X", {}, role="bat")
    assert s["wickets"] == 25 and s["typical"] is None and s["attack"] is None and s["kind"] is None  # 25 < 30
    w[("A", 2025, "pace bowler")]["caught"] = 25
    s = W.wicket_style(None, "T20", "X", {}, role="bat")
    assert s["typical"] == {"bowled": 20.0, "lbw": 5.0, "caught": 75.0, "stumped": 0.0}
