"""
Tag coverage, control %, shot families and partnership semantics (docs/query_builder_metrics.md).

The data checks run on any database with ODI ball-by-ball data and compare the query builder with
itself (control % against group_by=control counts). With HINDSIGHT_FULL_DATA=1 and DATABASE_URL on
a full copy they also assert the production numbers from the Oct 2026 audit:

    HINDSIGHT_FULL_DATA=1 DATABASE_URL=... pytest tests/test_tag_coverage.py
"""
import os
from datetime import date

import pytest

from services.coverage import rank_with_coverage
from services.shot_families import FAMILIES, families_for_shots, family_case_sql, shots_for

FULL_DATA = os.getenv("HINDSIGHT_FULL_DATA") == "1"


# --- shot families ----------------------------------------------------------------------------

def test_pull_hook_family_spans_both_schemes():
    assert set(shots_for(["PULL_HOOK"])) == {"PULL", "HOOK", "PULL_HOOK_ON_BACK_FOOT", "PULL_HOOK_ON_FRONT_FOOT"}
    assert set(shots_for(["CUT"])) >= {"CUT_SHOT", "CUT_SHOT_ON_BACK_FOOT", "CUT_SHOT_ON_FRONT_FOOT"}
    assert set(shots_for(["SWEEP"])) >= {"SWEEP", "SWEEP_SHOT"}
    assert set(shots_for(["DEFENCE"])) == {"DEFENDED", "FORWARD_DEFENCE", "BACK_DEFENCE"}


def test_every_label_has_one_family():
    labels = [s for _, shots in FAMILIES.values() for s in shots]
    assert len(labels) == len(set(labels))
    assert families_for_shots(["PULL", "HOOK"]) == ["PULL_HOOK"]
    assert "'PULL_HOOK_ON_BACK_FOOT'" in family_case_sql("dd.shot")


def test_unknown_family_is_an_error():
    with pytest.raises(ValueError):
        shots_for(["NOT_A_FAMILY"])


# --- coverage-aware ranking -------------------------------------------------------------------

def test_rows_under_the_floor_rank_last_and_leave_the_count():
    rows = [  # already sorted by control % descending
        {"partnership": "MacLeod & Berrington", "control_percentage": 93.4, "control_coverage_pct": 34.2},
        {"partnership": "Kumar & Mukkamalla", "control_percentage": 90.4, "control_coverage_pct": 58.4},
        {"partnership": "Rayudu & Kohli", "control_percentage": 89.0, "control_coverage_pct": 99.9},
        {"partnership": "Gill & Kohli", "control_percentage": 88.6, "control_coverage_pct": 99.9},
    ]
    ranked, summary = rank_with_coverage(rows, "control_percentage", 90)
    assert [r["partnership"] for r in ranked] == ["Rayudu & Kohli", "Gill & Kohli", "MacLeod & Berrington",
                                                  "Kumar & Mukkamalla"]
    assert [r["coverage_excluded"] for r in ranked] == [False, False, True, True]
    assert summary["included"] == 2 and summary["excluded"] == 2
    # Untagged metrics, or a floor of 0, leave the order alone.
    assert rank_with_coverage(list(rows), "runs", 90)[1] is None
    assert rank_with_coverage(list(rows), "control_percentage", 0)[1] is None


def test_graphic_blocks_a_subject_below_the_floor(monkeypatch):
    import services.snapshots as snapshots
    from services import content_ideas

    rows = [{"partnership": "Rayudu & Kohli", "control_percentage": 89.0, "control_coverage_pct": 99.9},
            {"partnership": "MacLeod & Berrington", "control_percentage": 93.4, "control_coverage_pct": 34.2,
             "coverage_excluded": True}]
    rows[0]["coverage_excluded"] = False
    structured = {"rows": rows, "total_rows": 211, "filter_chips": ["ODI"],
                  "coverage": {"tag": "control", "label": "control", "column": "control_coverage_pct", "min": 90.0,
                               "included": 155, "excluded": 56}}
    monkeypatch.setattr(snapshots, "_query_data", lambda db, params: structured)
    stored = {}
    monkeypatch.setattr(snapshots, "create_static_snapshot",
                        lambda db, kind, data, title, key, created_by: stored.setdefault("s", {"id": "x", "data": data}))
    plan = {"params": {"fmt": "ODI", "group_by": ["partnership"], "min_balls": 1000}, "metric": "control_percentage"}
    blocked = content_ideas.attempt(None, "t", {**plan, "highlight": ["Calum MacLeod & Richie Berrington"]})
    assert blocked["status"] == "parked" and "34.2% of balls" in blocked["note"]
    top = content_ideas.attempt(None, "t", plan)
    assert top["status"] == "resolved"
    assert "1st of 155 ODI partnerships (1,000+ balls, 90%+ control data)" in top["fact"]["title"]
    assert "control data: 99.9% of Rayudu and Kohli's balls (90% min)" in stored["s"]["data"]["footnote"]


# --- the data -----------------------------------------------------------------------------------

def _q(**kw):
    from database import SessionLocal
    from services.query_builder_v2 import _run_deliveries_query_uncached

    db = SessionLocal()
    try:
        return _run_deliveries_query_uncached(db, fmt="ODI", gender="male", limit=5000, **kw)
    finally:
        db.close()


@pytest.mark.parametrize("player,expected", [("Shubman Gill", 87.98), ("Virat Kohli", 86.90)])
def test_control_percentage_matches_group_by_control(player, expected):
    rows = _q(batters=[player], group_by=["batter"])["data"]
    if not rows or rows[0].get("control_percentage") is None:
        pytest.skip(f"no ODI control data for {player} in this database")
    by_control = {r["control"]: r["balls"] for r in _q(batters=[player], group_by=["batter", "control"])["data"]}
    controlled, tagged = by_control.get(1, 0), by_control.get(1, 0) + by_control.get(0, 0)
    # The same balls: control % is controlled / control-tagged legal balls, wides excluded.
    assert rows[0]["control_tagged"] == tagged
    assert rows[0]["control_percentage"] == pytest.approx(100.0 * controlled / tagged)
    assert rows[0]["control_coverage_pct"] == pytest.approx(100.0 * tagged / rows[0]["balls"], abs=0.05)
    if FULL_DATA:  # Gill 3,156 of 3,587; Kohli 13,894 of 15,989 (production, Oct 2026)
        assert round(rows[0]["control_percentage"], 2) == expected


def test_odi_pull_hook_sixes_count_both_schemes():
    rows = _q(shot_family=["PULL_HOOK"], group_by=["batter"])["data"]
    if not rows:
        pytest.skip("no ODI shot data in this database")
    sixes = {r["batter"]: r["sixes"] for r in rows}
    assert all("shot_coverage_pct" in r for r in rows)
    narrow = {r["batter"]: r["sixes"] for r in _q(shot=["PULL", "HOOK"], group_by=["batter"])["data"]}
    assert all(sixes.get(b, 0) >= n for b, n in narrow.items())  # a family never loses a shot
    if FULL_DATA:
        assert (sixes["Rohit Sharma"], sixes["AB de Villiers"], sixes["Eoin Morgan"], sixes["Chris Gayle"]) == (170, 69, 57, 70)  # Gayle 57 before 2000-04 ODIs were read


def test_partnership_with_a_batters_filter_counts_both_batters():
    from database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    pair = db.execute(text("""
        SELECT bat, non_striker FROM delivery_details WHERE format = 'ODI' AND gender = 'male'
          AND non_striker IS NOT NULL GROUP BY 1, 2 ORDER BY COUNT(*) DESC LIMIT 1""")).first()
    db.close()
    if not pair:
        pytest.skip("no ODI partnerships in this database")
    player = pair[0]
    filtered = _q(batters=[player], group_by=["partnership"])
    explicit = _q(partnership_players=[player], group_by=["partnership"])
    assert any("partnerships involving" in w for w in filtered["metadata"]["warnings"])
    assert {r["partnership"]: r["balls"] for r in filtered["data"]} == {r["partnership"]: r["balls"] for r in explicit["data"]}
    assert "runs" in explicit["metadata"]["definitions"]


def test_a_stand_owns_its_wicket_ball_whatever_the_feed_says():
    """The feed often names the wrong non-striker on a wicket ball (migration 016); the stand's pair,
    from the striker sequence, gets the ball and the wicket."""
    from database import SessionLocal
    from sqlalchemy import text

    from services.metrics.sql_defs import NON_DISMISSALS, _sql_list

    db = SessionLocal()
    try:
        if not db.execute(text("SELECT to_regclass('partnership_stands')")).scalar():
            pytest.skip("migration 016 not applied")
        # The pair with the most wicket balls whose feed non_striker is outside the stand, among pairs
        # whose names never appear in an unpaired stand (those balls fall back to the feed's pair).
        within = ("dd.p_match = ps.p_match AND dd.inns = ps.inns AND (dd.over, dd.ball) BETWEEN "
                  "(ps.first_over, ps.first_ball) AND (ps.last_over, ps.last_ball)")
        pair = db.execute(text(f"""
            WITH unpaired AS (
                SELECT DISTINCT COALESCE(pa.alias_name, dd.bat) AS name
                FROM partnership_stands ps JOIN delivery_details dd ON {within}
                LEFT JOIN player_alias_unambiguous pa ON pa.player_name = dd.bat
                WHERE ps.batter_a IS NULL)
            SELECT ps.batter_a, ps.batter_b
            FROM partnership_stands ps
            JOIN delivery_details dd ON {within}
            LEFT JOIN player_alias_unambiguous pn ON pn.player_name = dd.non_striker
            WHERE dd.format = 'ODI' AND dd.gender = 'male' AND dd.match_date >= '2005-01-01'
              AND LOWER(dd.out) = 'true' AND ps.batter_a IS NOT NULL
              AND COALESCE(pn.alias_name, dd.non_striker) NOT IN (ps.batter_a, ps.batter_b)
              AND ps.batter_a NOT IN (SELECT name FROM unpaired) AND ps.batter_b NOT IN (SELECT name FROM unpaired)
            GROUP BY 1, 2 ORDER BY COUNT(*) DESC, 1, 2 LIMIT 1""")).first()
        if not pair:
            pytest.skip("no ODI wicket ball with a misnamed non-striker in this database")
        a, b = pair
        expected = db.execute(text(f"""
            SELECT SUM(CASE WHEN COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN LOWER(dd.out) = 'true'
                             AND LOWER(COALESCE(dd.dismissal, '')) NOT IN ({_sql_list(NON_DISMISSALS)}) THEN 1 ELSE 0 END)
            FROM partnership_stands ps JOIN delivery_details dd ON {within}
            WHERE ps.batter_a = :a AND ps.batter_b = :b
              AND dd.format = 'ODI' AND dd.gender = 'male' AND dd.match_date >= '2005-01-01'"""),
            {"a": a, "b": b}).first()
    finally:
        db.close()
    rows = _q(partnership_players=[a], group_by=["partnership"], start_date=date(2005, 1, 1))["data"]
    row = next(r for r in rows if r["partnership"] == f"{a} & {b}")
    assert (row["balls"], row["wickets"]) == (expected[0], expected[1])


def test_odi_without_a_start_date_reads_from_the_first_match():
    """No start_date means all of it: the 2005 floor (the men's T20 legacy table's start) used to
    clip ODIs, which go back to 2000."""
    from services.query_builder_v2 import analyze_query_requirements

    for fmt in ("ODI", "ALL"):
        routing = analyze_query_requirements(None, None, [], {}, fmt=fmt, gender="male")
        assert routing["new_date_range"][0] < date(2000, 1, 1)
    t20 = analyze_query_requirements(None, None, [], {}, fmt="T20", gender="male")
    assert t20["use_legacy"]  # men's T20 still reaches the pre-2015 table
