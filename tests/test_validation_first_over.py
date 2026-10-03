"""
Integration check for the connector (Phase 1 validation):

    Varun Chakravarthy, men's T20, IPL + T20Is. Group his matches by runs conceded in his first
    over (0-6 / 7-9 / 10+). Expected roughly: 68 / 36 / 36 matches; bowling-view RAA per over for
    the rest of the match +0.40 / +0.46 / -0.20; Welch t-test, 10+ vs 0-6: p ~ 0.34.

Runs through query_cricket_data exactly as a model would: two grouped queries, the full CSV block
parsed, per-match RAA per over computed from it.

The expected numbers are for the full production data. hindsight_local holds 2024 onward only, so
by default this test checks the mechanics and prints the numbers; set HINDSIGHT_FULL_DATA=1 with
DATABASE_URL pointing at a full copy to assert them too:

    DATABASE_URL=postgresql://localhost:5432/hindsight_local pytest -s tests/test_validation_first_over.py
"""
import csv
import io
import math
import os
from collections import defaultdict

import pytest
from scipy import stats

import database

LOCAL_DB = any(h in database.DATABASE_URL for h in ("@localhost", "//localhost", "127.0.0.1"))
FULL_DATA = os.getenv("HINDSIGHT_FULL_DATA") == "1"
pytestmark = pytest.mark.skipif(not (LOCAL_DB or FULL_DATA), reason="needs a database with ball_metrics")

BUCKETS = ("0-6", "7-9", "10+")
EXPECTED_MATCHES = {"0-6": 68, "7-9": 36, "10+": 36}
EXPECTED_RAA_PER_OVER = {"0-6": 0.40, "7-9": 0.46, "10+": -0.20}
EXPECTED_P = 0.34


def _rows(**extra):
    from mcp_server.server import query_cricket_data

    res = query_cricket_data(
        None, group_by=["match_id", "bowler_first_over_runs_bucket"], bowlers=["Varun Chakravarthy"],
        leagues=["IPL"], include_international=True, format="T20", metrics_perspective="bowling",
        limit=10000, **extra,
    )
    assert not res.is_error, res.content[0].text
    assert "bowling view" in res.content[0].text
    body = res.content[1].text.split("```csv\n", 1)[1].rsplit("```", 1)[0]
    return list(csv.DictReader(io.StringIO(body)))


def first_over_check():
    every_match = _rows()
    rest = _rows(dimension_filters=["bowler_over_number:gte:2"])
    matches = defaultdict(set)
    for r in every_match:
        matches[r["bowler_first_over_runs_bucket"]].add(r["match_id"])
    per_match = defaultdict(list)
    pooled = defaultdict(lambda: [0.0, 0.0])  # raa, metric overs
    for r in rest:
        if r["raa_per_over"] == "":
            continue  # no Primer metrics for this match
        raa_over = float(r["raa_per_over"])
        per_match[r["bowler_first_over_runs_bucket"]].append(raa_over)
        overs = float(r["raa"]) / raa_over if raa_over else float(r["balls"]) / 6
        pooled[r["bowler_first_over_runs_bucket"]][0] += float(r["raa"])
        pooled[r["bowler_first_over_runs_bucket"]][1] += overs
    welch = stats.ttest_ind(per_match["10+"], per_match["0-6"], equal_var=False)
    return {
        "matches": {b: len(matches[b]) for b in BUCKETS},
        "matches_with_rest": {b: len(per_match[b]) for b in BUCKETS},
        "mean_raa_per_over": {b: sum(v) / len(v) if v else None for b, v in ((b, per_match[b]) for b in BUCKETS)},
        "pooled_raa_per_over": {b: (pooled[b][0] / pooled[b][1]) if pooled[b][1] else None for b in BUCKETS},
        "welch_t": float(welch.statistic), "welch_p": float(welch.pvalue),
        "rest_match_ids": {m for r in rest for m in [r["match_id"]]},
        "all_match_ids": {m for b in matches for m in matches[b]},
    }


def test_first_over_validation():
    out = first_over_check()
    print("\nFirst-over check:", {k: v for k, v in out.items() if not k.endswith("_ids")})
    # Mechanics: every bucket is populated, rest-of-match rows are a subset of his matches, the
    # numbers are finite.
    assert all(out["matches"][b] > 0 for b in BUCKETS)
    assert out["rest_match_ids"] <= out["all_match_ids"]
    assert all(math.isfinite(v) for v in out["mean_raa_per_over"].values() if v is not None)
    assert 0 <= out["welch_p"] <= 1
    if FULL_DATA:
        for b in BUCKETS:
            assert abs(out["matches"][b] - EXPECTED_MATCHES[b]) <= 4, (b, out["matches"][b])
            assert abs(out["mean_raa_per_over"][b] - EXPECTED_RAA_PER_OVER[b]) <= 0.12, (b, out["mean_raa_per_over"][b])
        assert abs(out["welch_p"] - EXPECTED_P) <= 0.1
