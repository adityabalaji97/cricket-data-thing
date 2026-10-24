import services.ig_posts.splits as sp

SCOPE = {"fmt": "T20", "params": {"leagues": ["IPL"]}}


def _rows(group_key, cells):
    """cells: {cell value: [(batter, runs, balls), ...]} -> query-builder-like rows"""
    out = []
    for value, players in cells.items():
        for name, runs, balls in players:
            out.append({"batter": name, group_key: value, "runs": runs, "balls": balls,
                        "strike_rate": 100 * runs / balls, "average": runs / 3})
    return out


def _field(n, sr):
    return [(f"Player {i}", int(sr * 2), 200) for i in range(n)]


def test_the_cell_where_the_player_leads_is_the_question(monkeypatch):
    phase = _rows("phase", {"powerplay": _field(14, 130) + [("Star", 330, 150)],   # 220 SR: leads
                            "death": _field(14, 160) + [("Star", 230, 150)]})      # 153: below the field
    monkeypatch.setattr(sp, "BATTER_DIMS", [sp.BATTER_DIMS[0]])
    monkeypatch.setattr(sp, "_query", lambda db, role, scope, gb: phase)
    found = sp.find(None, "Star", "batter", SCOPE)
    assert len(found) == 1 and found[0].phrase == "in the powerplay" and found[0].rank == 1 and found[0].of == 15


def test_a_small_field_or_an_ordinary_player_is_no_story(monkeypatch):
    monkeypatch.setattr(sp, "BATTER_DIMS", [sp.BATTER_DIMS[0]])
    small = _rows("phase", {"powerplay": _field(5, 130) + [("Star", 330, 150)]})
    monkeypatch.setattr(sp, "_query", lambda db, role, scope, gb: small)
    assert sp.find(None, "Star", "batter", SCOPE) == []
    ordinary = _rows("phase", {"powerplay": _field(14, 130) + [("Star", 196, 150)]})  # 131: no gap
    monkeypatch.setattr(sp, "_query", lambda db, role, scope, gb: ordinary)
    assert sp.find(None, "Star", "batter", SCOPE) == []


def test_profile_labels_read_in_cricket_order():
    keys = [("death", "LHB"), ("powerplay", "RHB"), ("middle", "spin bowler"), ("powerplay", "pace bowler")]
    assert [sp._label(k) for k in sorted(keys, key=sp._order)] == [
        "Pace · powerplay", "Spin · middle overs", "Right-handers · powerplay", "Left-handers · death"]


def test_trend_titles_lead_with_the_player_and_fit_two_lines():
    long_name = "Jan Nicol Loftie-Eaton"
    phrase = "against back-of-a-length balls in the middle overs"
    rows = [{"batter": f"P{i}", "runs": 300 - i, "balls": 150, "strike_rate": 200 - i, "impact_per_100": 20 - i,
             "wpa": 0.1} for i in range(80)]
    rows[9] = {**rows[9], "batter": long_name}
    for rank in (1, 10):
        s = sp.Split("length", ["length"], ("SHORT_OF_A_GOOD_LENGTH",), phrase, 191.0, 141.0, rank, 81, 0.1, 1.0,
                     rows if rank == 10 else [{**rows[9], "batter": long_name}] + rows[:9] + rows[10:])
        board = sp.leaderboard(s, long_name, "batter", "sample", "in the IPL since 2023")
        assert len(board["title"]) <= 80 and "191" in board["title"], board["title"]
        assert "leads at" not in board["title"] and "the next best" not in board["title"]
        value = sp.value_board(s, long_name, "batter", "sample")
        assert value is None or len(value["title"]) <= 80, value["title"]
