"""
H8 - Matchups are overrated: leg-spin to left-handers and left-arm pace to right-handers in the
powerplay, within-bowler RAA difference vs the same bowlers' other balls. Definitions:
preregistration/h8_matchups.md.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

import numpy as np

from analysis.hypotheses.common import (
    INCONCLUSIVE, NOT_SUPPORTED, PARTLY, Chart, Effect, Result, boot_p, bootstrap, ci, database_label, fmt_ci,
    query, read_only_session, resample, verdict_equivalence,
)

BAND = 3.0
MIN_BALLS = 120
MATCHUPS = {
    "A": {"label": "leg-spin to left-handers", "bowl_style": ["LB", "LBG"], "matchup": "LHB", "other": "RHB", "overs": {}},
    "B": {"label": "left-arm pace to right-handers, powerplay", "bowl_style": ["LF", "LFM", "LMF", "LM"],
          "matchup": "RHB", "other": "LHB", "overs": {"over_min": 0, "over_max": 5}},
}
SCOPE = dict(start_date=date(2015, 1, 1))


def _effect(rows, spec) -> tuple:
    per = defaultdict(dict)
    for r in rows:
        if r.get("bat_hand") in ("LHB", "RHB") and r.get("raa_per_100") is not None:
            per[r["bowler"]][r["bat_hand"]] = r
    units = []
    for bowler, hands in per.items():
        m, o = hands.get(spec["matchup"]), hands.get(spec["other"])
        if m and o and m["balls"] >= MIN_BALLS and o["balls"] >= MIN_BALLS:
            units.append((bowler, m["raa_per_100"] - o["raa_per_100"], min(m["balls"], o["balls"]), m, o))

    def wmean(us):
        w = np.array([u[2] for u in us], dtype=float)
        return float(np.sum(w * np.array([u[1] for u in us])) / np.sum(w)) if len(us) else np.nan

    est = wmean(units)
    reps = bootstrap(lambda g: wmean(resample(g, units))) if units else np.array([])
    eff = Effect(f"{spec['label']}: within-bowler RAA per 100 balls, matchup hand minus other hand",
                 None if np.isnan(est) else est, ci(reps) if len(reps) else [None, None], boot_p(reps) if len(reps) else None,
                 "weighted mean of within-bowler differences, bootstrap over bowlers", "RAA per 100 balls", "none", BAND,
                 n={"bowlers": len(units)})
    econ = {}
    for hand in ("LHB", "RHB"):
        rs = [u[3] if spec["matchup"] == hand else u[4] for u in units]
        b = sum(r["balls"] for r in rs)
        econ[hand] = {"balls": b, "economy": round(6 * sum(r["runs"] for r in rs) / b, 2) if b else None,
                      "waa_per_100": round(100 * sum(r.get("waa") or 0 for r in rs) / max(1, sum(r.get("metric_balls") or 0 for r in rs)), 3)}
    return eff, units, econ


def _verdict(eff: Effect, n: int) -> str:
    v = verdict_equivalence(eff, BAND, minimum_met=n >= 10)
    if v == NOT_SUPPORTED and eff.ci[1] is not None and eff.ci[1] < 0:
        return "Not supported — the matchup backfires"
    return v


def run() -> Result:
    effects, verdicts, tables, charts = [], {}, {}, []
    with read_only_session() as db:
        for key, spec in MATCHUPS.items():
            rows = query(db, bowl_style=spec["bowl_style"], group_by=["bowler", "bat_hand"], **spec["overs"], **SCOPE)
            eff, units, econ = _effect(rows, spec)
            effects.append(eff)
            verdicts[f"{key}. {spec['label']}"] = _verdict(eff, len(units))
            tables[key] = {"economy_by_hand": econ,
                           "bowlers": sorted([{"bowler": u[0], "diff_raa_per_100": round(u[1], 2), "min_balls": u[2]}
                                              for u in units], key=lambda d: -d["min_balls"])[:25]}
            common = dict(bowl_style=spec["bowl_style"], fmt="T20", metrics_perspective="bowling", **spec["overs"], **SCOPE)
            charts.append(Chart(f"{key}_pooled", f"{spec['label'].capitalize()}: RAA per 100 balls by batter's hand (bowling view)",
                                dict(common, group_by=["bat_hand"]), {"chart": "bar", "chart_metric": "raa_per_100"}))
            charts.append(Chart(f"{key}_bowlers", f"{spec['label'].capitalize()}: each bowler by batter's hand (120+ balls)",
                                dict(common, group_by=["bowler", "bat_hand"], min_balls=MIN_BALLS), {"chart": "table", "limit": 60}))
    distinct = {v.split(" —")[0] for v in verdicts.values()}
    verdict = distinct.pop() if len(distinct) == 1 else PARTLY
    if all(v == INCONCLUSIVE for v in verdicts.values()):
        verdict = INCONCLUSIVE
    a, b = effects
    headline = (f"Leg-spin to left-handers: {fmt_ci(a)} RAA per 100 balls vs the same bowlers to right-handers; "
                f"left-arm pace to right-handers in the powerplay: {fmt_ci(b)}.")
    return Result(
        hypothesis="H8", slug="h8-matchups", verdict=verdict, headline=headline,
        claim="A common claim is that bowling matchups (leg-spin to left-handers, left-arm pace to right-handers in "
              "the powerplay) are overrated.",
        effects=effects, charts=[charts[0], charts[2], charts[1], charts[3]], parts=verdicts, tables=tables,
        samples={k: len(t["bowlers"]) for k, t in tables.items()},
        caveats=["Balls to each hand come from the overs captains chose; a bowler kept away from a hand faces it "
                 "in different situations. RAA adjusts for game state, not for that selection.",
                 f"'Overrated' is tested as an equivalence band of +/-{BAND:.0f} RAA per 100 balls."],
        database=database_label(),
    )


if __name__ == "__main__":
    res = run()
    print(res.save())
    print(res.verdict, res.headline)
