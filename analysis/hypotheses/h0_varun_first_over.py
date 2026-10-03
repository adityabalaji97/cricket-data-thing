"""
H0 - Varun Chakravarthy: (a) a 10+ first over and the rest of the match, vs five IPL spinners;
(b) powerplay vs middle-overs entry; (c) pressure from the other end, with a next-over placebo.

Definitions: preregistration/h0_varun_first_over.md.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, List

import numpy as np

from analysis.hypotheses.common import (
    INCONCLUSIVE, NOT_SUPPORTED, PARTLY, SUPPORTED, Chart, Effect, Result, boot_p, bootstrap, canonical, ci,
    database_label, fmt_ci, mean, mean_diff_effect, per_over, query, read_only_session, resample, small,
    verdict_directional,
)

VARUN = "Varun Chakravarthy"
PEERS = ["Yuzvendra Chahal", "Rashid Khan", "Kuldeep Yadav", "Ravi Bishnoi", "Axar Patel"]
SCOPE = dict(leagues=["IPL"], include_international=True, start_date=date(2015, 1, 1), metrics_perspective="bowling")
BUCKETS = ("0-6", "7-9", "10+")


def _economy(rows: List[dict]) -> float | None:
    balls = sum(r.get("balls") or 0 for r in rows)
    return round(sum(r.get("runs") or 0 for r in rows) * 6 / balls, 2) if balls else None


def first_over(db, bowlers: List[str]) -> Dict[str, Dict[str, list]]:
    """bowler -> bucket -> list of (match_id, rest-of-match RAA/over, row); plus all matches per bucket."""
    every = query(db, bowlers=bowlers, group_by=["bowler", "match_id", "bowler_first_over_runs_bucket"], **SCOPE)
    rest = query(db, bowlers=bowlers, group_by=["bowler", "match_id", "bowler_first_over_runs_bucket"],
                 dimension_filters=["bowler_over_number:gte:2"], **SCOPE)
    out: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
    matches: Dict[str, Dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for r in every:
        matches[r["bowler"]][r["bowler_first_over_runs_bucket"]].add(r["match_id"])
    for r in rest:
        v = per_over(r)
        if v is not None:
            out[r["bowler"]][r["bowler_first_over_runs_bucket"]].append((r["match_id"], v, r))
    return out, matches


def part_a(db, varun: str, peers: List[str]):
    data, matches = first_over(db, [varun] + peers)
    v = data[varun]
    peer_vals = {b: [x for p in peers for x in data[p][b]] for b in BUCKETS}
    eff = mean_diff_effect("Varun: rest-of-match RAA/over, 10+ first over minus 0-6", [x[1] for x in v["10+"]],
                           [x[1] for x in v["0-6"]], unit="RAA per over", direction="negative", meaningful=-0.5,
                           label_a="10+", label_b="0-6")
    peer_eff = mean_diff_effect("Five IPL spinners pooled: same effect", [x[1] for x in peer_vals["10+"]],
                                [x[1] for x in peer_vals["0-6"]], unit="RAA per over", direction="negative",
                                meaningful=-0.5, label_a="10+", label_b="0-6")
    groups = [[x[1] for x in v["10+"]], [x[1] for x in v["0-6"]],
              [x[1] for x in peer_vals["10+"]], [x[1] for x in peer_vals["0-6"]]]
    did_est = None
    if all(groups):
        did_est = (mean(groups[0]) - mean(groups[1])) - (mean(groups[2]) - mean(groups[3]))
        reps = bootstrap(lambda g: (np.mean(resample(g, groups[0])) - np.mean(resample(g, groups[1])))
                         - (np.mean(resample(g, groups[2])) - np.mean(resample(g, groups[3]))))
    else:
        reps = np.array([])
    did = Effect("Varun's effect minus the peers' effect", did_est, ci(reps) if len(reps) else [None, None],
                 boot_p(reps) if len(reps) else None, "bootstrap difference-in-differences", "RAA per over",
                 "negative", -0.5, n={"varun_matches": len(groups[0]) + len(groups[1]),
                                      "peer_matches": len(groups[2]) + len(groups[3])})
    per_peer = {}
    for p in peers:
        e = mean_diff_effect(p, [x[1] for x in data[p]["10+"]], [x[1] for x in data[p]["0-6"]], unit="RAA per over",
                             direction="negative", meaningful=-0.5, label_a="10+", label_b="0-6")
        per_peer[p] = {"estimate": e.estimate, "ci": e.ci, "p": e.p_value, "n": e.n}
    table = {b: {"matches": len(matches[varun][b]), "matches_with_rest": len(v[b]),
                 "mean_raa_per_over_rest": mean([x[1] for x in v[b]]),
                 "economy_rest": _economy([x[2] for x in v[b]]),
                 "peer_matches_with_rest": len(peer_vals[b]),
                 "peer_mean_raa_per_over_rest": mean([x[1] for x in peer_vals[b]])} for b in BUCKETS}
    minimum = len(v["10+"]) >= 15 and len(v["0-6"]) >= 15
    return eff, peer_eff, did, per_peer, table, minimum, {b: len(matches[varun][b]) for b in BUCKETS}


def part_b(db, varun: str):
    rows = query(db, bowlers=[varun], group_by=["match_id", "bowler_entry_over"], **SCOPE)
    pp = [per_over(r) for r in rows if r["bowler_entry_over"] is not None and r["bowler_entry_over"] <= 5]
    mid = [per_over(r) for r in rows if r["bowler_entry_over"] is not None and 6 <= r["bowler_entry_over"] <= 14]
    death = [per_over(r) for r in rows if r["bowler_entry_over"] is not None and r["bowler_entry_over"] >= 15]
    pp, mid, death = ([x for x in xs if x is not None] for xs in (pp, mid, death))
    eff = mean_diff_effect("Varun: match RAA/over, middle-overs entry minus powerplay entry", mid, pp,
                           unit="RAA per over", direction="positive", meaningful=0.5, label_a="middle", label_b="powerplay")
    table = {"powerplay (overs 1-6)": {"matches": len(pp), "mean_raa_per_over": mean(pp)},
             "middle (overs 7-15)": {"matches": len(mid), "mean_raa_per_over": mean(mid)},
             "death (overs 16-20, not tested)": {"matches": len(death), "mean_raa_per_over": mean(death)}}
    return eff, table, len(pp) >= 15 and len(mid) >= 15


def _clustered_effect(rows: List[dict], key: str, name: str) -> Effect:
    """mean(10+) - mean(0-6) of per-over RAA/over, bootstrap resampling matches (their overs together)."""
    by_match: Dict[str, List[tuple]] = defaultdict(list)
    for r in rows:
        v = per_over(r)
        if v is not None and r.get(key) in BUCKETS:
            by_match[r["match_id"]].append((r[key], v))
    matches = list(by_match.values())

    def stat(sample):
        hi = [v for m in sample for b, v in m if b == "10+"]
        lo = [v for m in sample for b, v in m if b == "0-6"]
        return (np.mean(hi) - np.mean(lo)) if hi and lo else np.nan

    est = stat(matches)
    reps = bootstrap(lambda g: stat(resample(g, matches))) if matches else np.array([])
    counts = {b: sum(1 for m in matches for bb, _ in m if bb == b) for b in BUCKETS}
    return Effect(name, None if np.isnan(est) else float(est), ci(reps) if len(reps) else [None, None],
                  boot_p(reps) if len(reps) else None, "bootstrap over matches", "RAA per over", "negative", -0.5,
                  n={f"overs_{b}": c for b, c in counts.items()},
                  detail={f"mean_{b}": mean([v for m in matches for bb, v in m if bb == b]) for b in BUCKETS})


def part_c(db, varun: str):
    prev = query(db, bowlers=[varun], group_by=["match_id", "over", "prev_over_runs_bucket"], **SCOPE)
    nxt = query(db, bowlers=[varun], group_by=["match_id", "over", "next_over_runs_bucket"], **SCOPE)
    eff = _clustered_effect(prev, "prev_over_runs_bucket", "Varun: RAA/over of his over, previous over 10+ minus 0-6")
    placebo = _clustered_effect(nxt, "next_over_runs_bucket", "Placebo: same split by the NEXT over's runs")
    econ = {b: _economy([r for r in prev if r["prev_over_runs_bucket"] == b]) for b in BUCKETS}
    minimum = eff.n.get("overs_10+", 0) >= 30 and eff.n.get("overs_0-6", 0) >= 30
    return eff, placebo, econ, minimum


def run() -> Result:
    with read_only_session() as db:
        varun = canonical(db, VARUN)
        peers = [canonical(db, p) for p in PEERS]
        a_eff, a_peer, a_did, per_peer, a_table, a_min, a_counts = part_a(db, varun, peers)
        b_eff, b_table, b_min = part_b(db, varun)
        c_eff, c_placebo, c_econ, c_min = part_c(db, varun)

    v_a = verdict_directional(a_eff, a_min)
    v_b = verdict_directional(b_eff, b_min)
    v_c = verdict_directional(c_eff, c_min)
    # Pre-registered: supported only if the placebo's CI includes zero; a placebo shift in the same
    # (negative) direction means the previous-over pattern is confounding.
    if v_c == SUPPORTED and c_placebo.ci[1] is not None:
        if c_placebo.ci[1] < 0:
            v_c = NOT_SUPPORTED + " (placebo shifts the same way: confounded)"
        elif c_placebo.ci[0] > 0:
            v_c = INCONCLUSIVE + " (placebo shifts the other way)"
    parts = {"a. 10+ first over hurts the rest of his match": v_a, "b. better entering in the middle overs": v_b,
             "c. hurt by a big over from the other end": v_c}
    distinct = {v.split(" (")[0] for v in parts.values()}
    verdict = distinct.pop() if len(distinct) == 1 else PARTLY

    common = dict(bowlers=[varun], group_by=["bowler_first_over_runs_bucket"], fmt="T20", **SCOPE)
    charts = [
        Chart("first_over", "Varun's rest-of-match RAA per over by runs off his first over, pooled over all those balls "
              "(bowling view; the test compares per-match averages)",
              dict(common, dimension_filters=["bowler_over_number:gte:2"]),
              {"chart": "bar", "chart_metric": "raa_per_over"}, small({b: a_table[b]["matches_with_rest"] for b in BUCKETS})),
        Chart("peers", "Five IPL spinners pooled: rest-of-match RAA per over by first-over runs (all their balls)",
              dict(common, bowlers=peers, dimension_filters=["bowler_over_number:gte:2"]),
              {"chart": "bar", "chart_metric": "raa_per_over"}),
        Chart("entry", "Varun's RAA per over by the over he came on (0 = first over of the innings)",
              dict(bowlers=[varun], group_by=["bowler_entry_over"], fmt="T20", **SCOPE),
              {"chart": "line", "chart_metric": "raa_per_over"}),
        Chart("pressure", "Varun's RAA per over by runs off the previous over from the other end",
              dict(bowlers=[varun], group_by=["prev_over_runs_bucket"], fmt="T20", **SCOPE),
              {"chart": "bar", "chart_metric": "raa_per_over"}),
    ]
    placebo_chart = Chart("placebo", "Placebo: Varun's RAA per over by runs off the NEXT over",
                          dict(bowlers=[varun], group_by=["next_over_runs_bucket"], fmt="T20", **SCOPE),
                          {"chart": "bar", "chart_metric": "raa_per_over"})
    headline = (f"After a 10+ first over, Varun's RAA per over for the rest of the match moves by {fmt_ci(a_eff)} "
                f"vs a 0-6 first over ({a_counts['10+']} and {a_counts['0-6']} matches).")
    return Result(
        hypothesis="H0", slug="h0-varun-first-over", verdict=verdict, headline=headline,
        claim="A common claim is that Varun Chakravarthy can't recover from an expensive first over, is better "
              "used in the middle overs than the powerplay, and suffers when the bowler at the other end leaks runs.",
        effects=[a_eff, a_peer, a_did, b_eff, c_eff, c_placebo], charts=charts + [placebo_chart], parts=parts,
        tables={"first_over": a_table, "per_peer": per_peer, "entry": b_table, "pressure_economy": c_econ},
        samples={"first_over_matches": a_counts},
        caveats=["Line/length is not used here. RAA is per six balls that carry metrics (wides carry none).",
                 "Matches where he bowled one over have no rest of match and are excluded from part a.",
                 "Peers are pooled by match, so bowlers with more matches weigh more."],
        database=database_label(),
    )


if __name__ == "__main__":
    res = run()
    print(res.save())
    print(res.verdict, res.parts, res.headline)
