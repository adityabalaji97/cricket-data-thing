from services import query_builder_v2 as qb


def _row(batter, balls, runs=0, wickets=0, innings=1):
    return {"batter": batter, "balls": balls, "runs": runs, "wickets": wickets, "innings_count": innings,
            "dots": 0, "boundaries": 0, "fours": 0, "sixes": 0}


def test_merging_sources_fetch_an_unfiltered_head_from_row_zero():
    assert qb._source_page_params(10, 30, merging=False, grouped=True) == {"limit": 10, "offset": 30}
    assert qb._source_page_params(10, 30, merging=True, grouped=False) == {"limit": 40, "offset": 0}
    assert qb._source_page_params(10, 30, merging=True, grouped=True) == {
        "limit": qb.MERGE_GROUP_FETCH_CAP, "offset": 0,
    }


def test_group_thresholds_cover_balls_runs_and_wickets():
    rows = [_row("a", 600, 700, 30), _row("b", 400, 500, 10), _row("c", 40, 25, 0)]
    keep = lambda **t: [r["batter"] for r in qb._apply_group_thresholds(
        rows, t.get("min_balls"), t.get("max_balls"), t.get("min_runs"), t.get("max_runs"),
        t.get("min_wickets"), t.get("max_wickets"))]
    assert keep(min_balls=500) == ["a"]
    assert keep(min_wickets=10) == ["a", "b"]
    assert keep(max_balls=50, min_runs=20) == ["c"]


def test_legacy_spellings_of_one_player_are_combined(monkeypatch):
    monkeypatch.setattr(qb, "normalize_player_name_for_merge", lambda name, _m: {"AJ Finch": "Aaron Finch"}.get(name, name))
    merged = qb.merge_grouped_results(
        [], [_row("AJ Finch", 100, 120, 2), _row("Aaron Finch", 50, 70, 1), _row("V Kohli", 80)],
        ["batter"], {}, 230,
    )
    finch = [r for r in merged if r["batter"] == "Aaron Finch"]
    assert len(finch) == 1 and finch[0]["balls"] == 150 and finch[0]["runs"] == 190 and finch[0]["wickets"] == 3
    assert [r["batter"] for r in merged] == ["Aaron Finch", "V Kohli"]


def test_merge_combines_new_and_legacy_and_keeps_new_names(monkeypatch):
    monkeypatch.setattr(qb, "normalize_player_name_for_merge", lambda name, _m: {"AJ Finch": "Aaron Finch"}.get(name, name))
    merged = qb.merge_grouped_results(
        [_row("Aaron Finch", 3, 4)], [_row("AJ Finch", 1604, 2000, 40)], ["batter"], {}, 1607,
    )
    assert len(merged) == 1 and merged[0]["batter"] == "Aaron Finch" and merged[0]["balls"] == 1607
