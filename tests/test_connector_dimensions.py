"""
Phase 1 connector/engine changes: match-context dimensions, dimension filters, team_innings,
metrics_perspective, match/exclusion filters, canonical names, full results and paging.

Unit tests run anywhere. Tests marked `local_db` read hindsight_local and check each computed
dimension against an independent SQL computation:

    DATABASE_URL=postgresql://localhost:5432/hindsight_local pytest tests/test_connector_dimensions.py
"""
import csv
import io

import pytest

import database
from services import query_dimensions as qd

LOCAL_DB = any(h in database.DATABASE_URL for h in ("@localhost", "//localhost", "127.0.0.1"))
local_db = pytest.mark.skipif(not LOCAL_DB, reason="reads hindsight_local; set DATABASE_URL to it")


# ----------------------------------------------------------------------------------------------
# Unit
# ----------------------------------------------------------------------------------------------

def test_parse_dimension_filters():
    parsed = qd.parse_filters(["bowler_over_number:gte:2", "prev_over_runs_bucket:in:7-9|10+"], qd.DIMENSION_NAMES)
    assert parsed == [("bowler_over_number", "gte", ["2"]), ("prev_over_runs_bucket", "in", ["7-9", "10+"])]
    with pytest.raises(qd.DimensionFilterError):
        qd.parse_filters(["nonsense:gte:2"], qd.DIMENSION_NAMES)
    with pytest.raises(qd.DimensionFilterError):
        qd.parse_filters(["bowler_over_number>=2"], qd.DIMENSION_NAMES)


def test_filter_sql_binds_values_and_types():
    dims = qd.dimensions("dd.competition")
    params = {}
    conds = qd.filter_sql(qd.parse_filters(["bowler_over_number:gte:2", "prev_over_runs_bucket:in:10+",
                                            "prev_over_raa:lt:-1.5"], qd.DIMENSION_NAMES), dims, params)
    assert conds[0] == "bo.bowler_over_number >= :dimf_0" and params["dimf_0"] == 2
    assert "= ANY(:dimf_1)" in conds[1] and params["dimf_1"] == ["10+"]
    # Filtered on the unrounded RAA, grouped on the rounded one.
    assert conds[2] == "po.raa < :dimf_2" and params["dimf_2"] == -1.5
    with pytest.raises(qd.DimensionFilterError):
        qd.filter_sql([("spell_number", "eq", ["two"])], dims, {})


def test_bucket_sql_boundaries():
    sql = qd._int_bucket_sql("x", qd.RUNS_BUCKETS)
    assert "WHEN x <= 6 THEN '0-6'" in sql and "WHEN x <= 9 THEN '7-9'" in sql and "ELSE '10+'" in sql


def test_ctes_only_for_requested_families():
    ctes, joins = qd.build_ctes([], "FROM delivery_details dd WHERE 1=1", True)
    assert ctes == [] and joins == []
    ctes, joins = qd.build_ctes(["prev_over"], "FROM delivery_details dd WHERE 1=1", False)
    assert ctes[0].startswith("scope_matches") and "innings_over" in ctes[1]
    assert "ball_metrics" not in ctes[1]  # no metrics join when the Primer metrics are off
    assert joins == ["LEFT JOIN innings_over po ON po.p_match = dd.p_match AND po.inns = dd.inns AND po.over = dd.over - 1"]


def test_perspective_labels_in_header():
    from mcp_server.server import _markdown_table, perspective_label

    assert perspective_label("bowling") == "bowling view: + = good for bowler"
    table = _markdown_table(["bowler", "balls", "raa"], [{"bowler": "A", "balls": 6, "raa": 1.5}], perspective="bowling")
    assert "raa (bowling view: + = good for bowler)" in table.splitlines()[0]
    assert "balls (" not in table


def test_canonicalize_rows_merges_spellings():
    from mcp_server.server import canonicalize_rows

    rows = [
        {"bowler": "CV Varun", "balls": 12, "runs": 12, "wickets": 1, "metric_balls": 12, "raa": 2.0,
         "strike_rate": 100.0, "raa_per_100": 16.67},
        {"bowler": "Varun Chakaravarthy", "balls": 6, "runs": 18, "wickets": 0, "metric_balls": 6, "raa": -4.0,
         "strike_rate": 300.0, "raa_per_100": -66.67},
        {"bowler": "Rashid Khan", "balls": 6, "runs": 3, "wickets": 0},
    ]
    alias = {"cv varun": "Varun Chakaravarthy", "varun chakaravarthy": "Varun Chakaravarthy"}
    out, merged = canonicalize_rows(rows, ["bowler"], alias)
    assert merged == 1
    varun = next(r for r in out if r["bowler"] == "Varun Chakaravarthy")
    assert varun["balls"] == 18 and varun["runs"] == 30 and varun["strike_rate"] == round(30 * 100 / 18, 2)
    assert varun["raa"] == -2.0 and varun["raa_per_100"] == round(-2.0 * 100 / 18, 2)
    assert {r["bowler"] for r in out} == {"Varun Chakaravarthy", "Rashid Khan"}


def test_structure_paging_and_per_over():
    from mcp_server.server import structure_query_result

    data = [{"bowler": f"B{i}", "balls": 100 - i, "raa": float(i), "metric_balls": 60, "metrics_perspective": "bowling"}
            for i in range(30)]
    out = structure_query_result({"data": data, "metadata": {"total_groups": 30}}, {"bowlers": []}, ["bowler"],
                                 sort_by="raa", limit=10, offset=10)
    assert [r["bowler"] for r in out["rows"]] == [f"B{i}" for i in range(19, 9, -1)]
    assert out["next_offset"] == 20 and out["metrics_perspective"] == "bowling"
    assert out["rows"][0]["raa_per_over"] == round(19 * 6 / 60, 3)
    assert "offset=10" in out["hindsight_url"]


def test_hindsight_url_carries_large_limit_only():
    from mcp_server.server import _hindsight_url

    assert "limit=" not in _hindsight_url({}, ["batter"], "T20", "male", limit=50)
    assert "limit=5000" in _hindsight_url({}, ["batter"], "T20", "male", limit=5000)
    # Graphics pull 20,000 rows; the query page's API takes at most 10,000 (a 422 blanked the page).
    assert "limit=10000" in _hindsight_url({}, ["batter"], "T20", "male", limit=20000)


def test_rows_as_csv_round_trips():
    from mcp_server.server import rows_as_csv

    text = rows_as_csv(["a", "b"], [{"a": "x, y", "b": 1}, {"a": "z", "b": None}])
    assert list(csv.reader(io.StringIO(text))) == [["a", "b"], ["x, y", "1"], ["z", ""]]


def test_team_innings_rejects_ball_level_filters(mock_db):
    from services.query_builder_v2 import QueryValidationError, _run_deliveries_query_uncached

    with pytest.raises(QueryValidationError, match="ball-level"):
        _run_deliveries_query_uncached(mock_db, query_mode="team_innings", group_by=["season"], bowlers=["X"], fmt="T20")
    with pytest.raises(QueryValidationError, match="not available for team_innings"):
        _run_deliveries_query_uncached(mock_db, query_mode="team_innings", group_by=["bowler"], fmt="T20")


def test_bad_perspective_rejected(mock_db):
    from services.query_builder_v2 import QueryValidationError, _run_deliveries_query_uncached

    with pytest.raises(QueryValidationError):
        _run_deliveries_query_uncached(mock_db, group_by=["bowler"], metrics_perspective="fielding")


# ----------------------------------------------------------------------------------------------
# Against hindsight_local
# ----------------------------------------------------------------------------------------------

@pytest.fixture
def db():
    session = database.SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _q(db, **kw):
    from services.query_builder_v2 import _run_deliveries_query_uncached

    kw.setdefault("fmt", "T20")
    kw.setdefault("limit", 10000)
    return _run_deliveries_query_uncached(db, **kw)["data"]


# The feed stores him as "Varun Chakravarthy"; his canonical name is "Varun Chakaravarthy".
STORED = "Varun Chakravarthy"


def _varun_match(db):
    from sqlalchemy import text

    return db.execute(text("""
        SELECT p_match FROM delivery_details WHERE bowl = :b AND format = 'T20'
        GROUP BY p_match HAVING COUNT(DISTINCT over) = 4 ORDER BY p_match LIMIT 1"""), {"b": STORED}).scalar()


@local_db
def test_bowler_dimensions_match_independent_sql(db):
    from sqlalchemy import text

    mid = _varun_match(db)
    overs = [r[0] for r in db.execute(text(
        "SELECT DISTINCT over FROM delivery_details WHERE p_match = :m AND bowl = :b ORDER BY 1"),
        {"m": mid, "b": STORED})]
    first_runs = db.execute(text("""
        SELECT SUM(COALESCE(score,0) - COALESCE(byes,0) - COALESCE(legbyes,0)) FROM delivery_details
        WHERE p_match = :m AND bowl = :b AND over = :o"""), {"m": mid, "o": overs[0], "b": STORED}).scalar()
    rows = _q(db, bowlers=["Varun Chakravarthy"], match_ids=[mid],
              group_by=["over", "bowler_over_number", "bowler_entry_over", "spell_number", "bowler_first_over_runs"])
    got = sorted((r["over"], r["bowler_over_number"], r["bowler_entry_over"], r["spell_number"], r["bowler_first_over_runs"])
                 for r in rows)
    spells, spell = [], 0
    for i, o in enumerate(overs):
        if i == 0 or o - overs[i - 1] != 2:
            spell += 1
        spells.append(spell)
    assert got == [(o, i + 1, overs[0], spells[i], first_runs) for i, o in enumerate(overs)]


@local_db
def test_over_number_filter_keeps_true_numbering(db):
    """Filtering to overs 2+ must not renumber: the first over is counted even though it is dropped."""
    mid = _varun_match(db)
    rows = _q(db, bowlers=["Varun Chakravarthy"], match_ids=[mid], group_by=["bowler_over_number"],
              dimension_filters=["bowler_over_number:gte:2"])
    assert sorted(r["bowler_over_number"] for r in rows) == [2, 3, 4]


@local_db
def test_prev_over_runs_is_previous_over_total(db):
    from sqlalchemy import text

    mid = _varun_match(db)
    rows = _q(db, bowlers=["Varun Chakravarthy"], match_ids=[mid], group_by=["over", "prev_over_runs"])
    for r in rows:
        expected = db.execute(text("SELECT SUM(COALESCE(score,0)) FROM delivery_details WHERE p_match=:m AND over=:o "
                                   "AND inns = (SELECT MIN(inns) FROM delivery_details WHERE p_match=:m AND bowl=:b)"),
                              {"m": mid, "o": r["over"] - 1, "b": STORED}).scalar()
        assert r["prev_over_runs"] == expected


@local_db
def test_metrics_perspective_flips_sign(db):
    base = dict(bowlers=["Varun Chakravarthy"], leagues=["IPL"], group_by=["phase"])
    batting = {r["phase"]: r for r in _q(db, **base)}
    bowling = {r["phase"]: r for r in _q(db, metrics_perspective="bowling", **base)}
    for phase, row in bowling.items():
        assert row["metrics_perspective"] == "bowling"
        assert row["raa"] == pytest.approx(-batting[phase]["raa"], abs=0.02)
        # Bowling view charges the bowler only with his own runs.
        assert row["runs"] <= batting[phase]["runs"]


@local_db
def test_exclusions_and_match_ids(db):
    all_rows = _q(db, leagues=["IPL"], group_by=["bowler"], bowl_kind=["spin bowler"])
    names = {r["bowler"] for r in all_rows}
    assert "Varun Chakaravarthy" in names
    # Excluding by another spelling still drops him.
    without = {r["bowler"] for r in _q(db, leagues=["IPL"], group_by=["bowler"], bowl_kind=["spin bowler"],
                                         exclude_bowlers=["CV Varun"])}
    assert "Varun Chakaravarthy" not in without and len(without) == len(names) - 1
    mid = _varun_match(db)
    assert {r["match_id"] for r in _q(db, group_by=["match_id"], match_ids=[mid])} == {mid}


@local_db
def test_team_innings_totals_match_ball_sums(db):
    from sqlalchemy import text

    from services.query_builder_v2 import _run_deliveries_query_uncached

    mid = _varun_match(db)
    out = _run_deliveries_query_uncached(db, query_mode="team_innings", group_by=["match_id", "innings"],
                                         match_ids=[mid], fmt="T20")["data"]
    for row in out:
        total = db.execute(text("SELECT SUM(COALESCE(score,0)) FROM delivery_details WHERE p_match=:m AND inns=:i"),
                           {"m": mid, "i": row["innings"]}).scalar()
        assert row["avg_total"] == total and row["innings_count"] == 1
        assert row["pct_200_plus"] == (100.0 if total >= 200 else 0.0)
    seasons = _run_deliveries_query_uncached(db, query_mode="team_innings", group_by=["season"], leagues=["IPL"],
                                             fmt="T20", dimension_filters=["full_length:eq:1"])["data"]
    assert seasons and all(0 <= r["pct_200_plus"] <= 100 for r in seasons)


@local_db
def test_season_labels_cross_year_leagues(db):
    rows = _q(db, leagues=["BBL", "IPL"], group_by=["competition", "season"])
    labels = {(r["competition"], r["season"]) for r in rows}
    assert any(c == "BBL" and "/" in s for c, s in labels)
    assert all("/" not in s for c, s in labels if c == "IPL")


@local_db
def test_bowling_context_has_raa_versions(db):
    from services.bowling_context import get_bowling_context

    ctx = get_bowling_context(db=db, player_name="CV Varun", start_date=None, end_date=None, leagues=["IPL"],
                              include_international=False, venue=None, min_overs=1, pressure_threshold=10)
    high = ctx["previous_over_pressure_stats"]["high_pressure"]
    assert high["economy"] is not None and high["raa_per_over"] is not None and high["metric_balls"] > 0
    assert ctx["spell_stats"]["first_spell"]["raa_per_over"] is not None
    assert ctx["metric_notes"]["economy"] == "unadjusted for game state"


@local_db
def test_connector_returns_full_csv_and_canonical_names():
    from mcp_server.server import query_cricket_data

    res = query_cricket_data(None, group_by=["bowler"], leagues=["IPL"], format="T20", bowl_kind=["spin bowler"],
                             limit=200)
    assert not res.is_error
    summary, full = res.content[0].text, res.content[1].text
    assert "Metric perspective: bowling view" in summary
    body = full.split("```csv\n", 1)[1].rsplit("```", 1)[0]
    parsed = list(csv.DictReader(io.StringIO(body)))
    assert len(parsed) == len(res.structured_content["rows"]) > 25
    res = query_cricket_data(None, group_by=["bowler"], bowlers=["CV Varun"], format="T20")
    assert res.structured_content["rows"][0]["bowler"] == "Varun Chakaravarthy"
    assert "Varun Chakaravarthy" in res.structured_content["title"]


@local_db
def test_next_over_placebo_and_match_date(db):
    from sqlalchemy import text

    mid = _varun_match(db)
    rows = _q(db, bowlers=["Varun Chakravarthy"], match_ids=[mid], group_by=["over", "next_over_runs", "match_date"])
    date_ = db.execute(text("SELECT MIN(match_date) FROM delivery_details WHERE p_match = :m"), {"m": mid}).scalar()
    for r in rows:
        expected = db.execute(text("SELECT SUM(COALESCE(score,0)) FROM delivery_details WHERE p_match=:m AND over=:o "
                                   "AND inns = (SELECT MIN(inns) FROM delivery_details WHERE p_match=:m AND bowl=:b)"),
                              {"m": mid, "o": r["over"] + 1, "b": STORED}).scalar()
        assert r["next_over_runs"] == expected
        assert r["match_date"] == date_


@local_db
def test_batter_innings_strike_rate_and_era(db):
    from sqlalchemy import text

    rows = _q(db, batters=["Virat Kohli"], leagues=["IPL"], group_by=["match_id", "batter_innings_strike_rate"],
              dimension_filters=["batter_balls_faced:gte:30"])
    assert rows
    for r in rows[:5]:
        runs, balls = db.execute(text("""SELECT SUM(COALESCE(batruns,0)), SUM(CASE WHEN COALESCE(wide,0)=0 THEN 1 ELSE 0 END)
            FROM delivery_details WHERE p_match = :m AND bat = 'Virat Kohli'"""), {"m": r["match_id"]}).one()
        assert balls >= 30 and r["batter_innings_strike_rate"] == round(runs * 100.0 / balls)
    # Era follows the season's start: January 2024 BBL matches belong to 2023/24, i.e. 2023+.
    eras = {(r["season"], r["impact_player_era"]) for r in _q(db, leagues=["BBL"], group_by=["season", "impact_player_era"])}
    assert all(era == "2023+" for season, era in eras if season.startswith("2023"))


def test_year_suffixed_seasons_are_their_league():
    from services.competition_aliases import canonical_competition
    from utils.league_utils import expand_league_abbreviations

    assert canonical_competition("BBL 2023") == "BBL"
    assert canonical_competition("CPL 2024") == "CPL"
    assert canonical_competition("GSL 2024") == "GSL 2024"  # ambiguous: left alone
    assert {"BBL 2023"} <= set(expand_league_abbreviations(["BBL"]))
    assert {"CPL 2023", "CPL 2024"} <= set(expand_league_abbreviations(["CPL"]))
