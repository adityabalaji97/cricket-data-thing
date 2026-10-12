"""Match-context dimensions on the legacy table (pre-2015 men's T20) and the batter's Nth-ball dimension."""
from datetime import date

from services import query_dimensions as QD
from services.query_builder_v2 import ADVANCED_COLUMNS, analyze_query_requirements


def test_dimensions_no_longer_force_2015_except_raa():
    for name in ("bowler_over_number", "prev_over_runs_bucket", "batter_ball_number_bucket", "batter_balls_faced"):
        assert name not in ADVANCED_COLUMNS
    assert "prev_over_raa" in ADVANCED_COLUMNS and "prev_over_raa_bucket" in ADVANCED_COLUMNS


def test_legacy_ctes_cover_every_family_on_deliveries():
    ctes, joins = QD.build_legacy_ctes(["bowler_ctx", "prev_over", "next_over", "batter_inns", "batter_ball"],
                                       "FROM deliveries d JOIN matches m ON d.match_id = m.id WHERE 1=1")
    sql = " ".join(ctes + joins)
    assert "delivery_details" not in sql and "FROM deliveries x" in sql
    for alias in ("bo", "po", "nxo", "bi", "bb"):
        assert f" {alias} ON " in sql
    # the batter's balls are counted in bowling order, wides not counted
    assert "ORDER BY x.over, x.ball, x.id" in sql and "COALESCE(x.wides, 0) = 0" in sql


def test_legacy_dimensions_share_expressions_and_drop_raa():
    new, old = QD.dimensions("dd.competition"), QD.legacy_dimensions("m.competition")
    assert set(new) == set(old)
    assert old["bowler_over_number"].expr == new["bowler_over_number"].expr
    assert new["batter_ball_number"].expr == "dd.cur_bat_bf" and old["batter_ball_number"].expr == "bb.n"
    assert old["prev_over_raa"].expr.startswith("NULL")
    assert "m.date" in old["season"].expr


def test_ball_number_buckets():
    sql = QD.dimensions("dd.competition")["batter_ball_number_bucket"].expr
    assert "'1-10'" in sql and "'31+'" in sql
