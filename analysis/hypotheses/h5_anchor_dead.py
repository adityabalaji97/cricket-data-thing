"""
H5 - The anchor is dead: innings of 30+ balls by strike rate, team win % and batter WPA,
2015-19 vs 2023-26, IPL and top-10 T20Is. Definitions: preregistration/h5_anchor_dead.md.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

import numpy as np

from analysis.hypotheses.common import (
    Chart, Effect, Result, boot_p, bootstrap, ci, database_label, fmt_ci, mean, query, read_only_session, resample,
    small, verdict_directional,
)

ERAS = {"2015-19": (date(2015, 1, 1), date(2019, 12, 31)), "2023-26": (date(2023, 1, 1), date(2026, 10, 3))}
SCOPE = dict(leagues=["IPL"], include_international=True, top_teams=10)
BUCKETS = ("under 110", "110-129", "130-149", "150+")
LONG = ["batter_balls_faced:gte:30"]


def run() -> Result:
    cells = defaultdict(list)
    with read_only_session() as db:
        for era, (start, end) in ERAS.items():
            rows = query(db, group_by=["match_id", "batter", "match_outcome", "batter_innings_strike_rate_bucket"],
                         dimension_filters=LONG, start_date=start, end_date=end, **SCOPE)
            for r in rows:
                cells[(era, r["batter_innings_strike_rate_bucket"])].append(r)

    def wpa(rs):
        vals = [r["wpa"] for r in rs if r.get("wpa") is not None]
        return float(np.mean(vals)) if vals else np.nan

    def win(rs):
        dec = [r for r in rs if r["match_outcome"] in ("win", "loss")]
        return 100.0 * np.mean([r["match_outcome"] == "win" for r in dec]) if dec else np.nan

    def did(fn, name, unit, meaningful):
        keys = [("2023-26", "under 110"), ("2023-26", "150+"), ("2015-19", "under 110"), ("2015-19", "150+")]
        if any(not cells.get(k) for k in keys):
            return Effect(name, None, [None, None], None, "bootstrap over innings", unit, "negative", meaningful)
        est = (fn(cells[keys[0]]) - fn(cells[keys[1]])) - (fn(cells[keys[2]]) - fn(cells[keys[3]]))
        reps = bootstrap(lambda g: (fn(resample(g, cells[keys[0]])) - fn(resample(g, cells[keys[1]])))
                         - (fn(resample(g, cells[keys[2]])) - fn(resample(g, cells[keys[3]]))))
        return Effect(name, float(est), ci(reps), boot_p(reps), "bootstrap difference-in-differences (innings)", unit,
                      "negative", meaningful, n={f"{e} {b}": len(cells[(e, b)]) for e, b in keys},
                      detail={f"{e} {b}": float(fn(cells[(e, b)])) for e, b in keys})

    primary = did(wpa, "Slow (<110) minus fast (150+) 30-ball innings, WPA per innings: 2023-26 minus 2015-19",
                  "WPA per innings", -0.03)
    secondary = did(win, "Same contrast in team win %", "percentage points", -10)
    counts = {f"{e} {b}": len(cells[(e, b)]) for e in ERAS for b in BUCKETS}
    minimum = all(len(cells[(e, b)]) >= 30 for e in ERAS for b in BUCKETS)
    verdict = verdict_directional(primary, minimum)
    table = {e: {b: {"innings": len(cells[(e, b)]), "wpa_per_innings": wpa(cells[(e, b)]) if cells[(e, b)] else None,
                     "team_win_pct": win(cells[(e, b)]) if cells[(e, b)] else None} for b in BUCKETS} for e in ERAS}
    share_slow = {e: round(100 * len(cells[(e, "under 110")]) / max(1, sum(len(cells[(e, b)]) for b in BUCKETS)), 1) for e in ERAS}

    def chart(era, key, presentation):
        start, end = ERAS[era]
        return Chart(f"{key}_{era}", f"Innings of 30+ balls by strike rate, {era}: team result and WPA (batting view)",
                     dict(group_by=["batter_innings_strike_rate_bucket", "match_outcome"], dimension_filters=LONG,
                          start_date=start, end_date=end, fmt="T20", **SCOPE), presentation,
                     small({b: len(cells[(era, b)]) for b in BUCKETS}))

    charts = [
        chart("2015-19", "result", {"chart": "table"}),
        chart("2023-26", "result", {"chart": "table"}),
        Chart("impact_2023", "Innings of 30+ balls, 2023-26: Impact per 100 balls by strike-rate band",
              dict(group_by=["batter_innings_strike_rate_bucket"], dimension_filters=LONG,
                   start_date=ERAS["2023-26"][0], end_date=ERAS["2023-26"][1], fmt="T20", **SCOPE),
              {"chart": "bar", "chart_metric": "impact_per_100"}),
    ]
    headline = (f"A sub-110 30-ball innings vs a 150+ one: the WPA gap changed by {fmt_ci(primary, 3)} per innings "
                f"between 2015-19 and 2023-26.")
    return Result(
        hypothesis="H5", slug="h5-anchor-dead", verdict=verdict, headline=headline,
        claim="A common claim is that the anchor is dead: a long, slow innings used to be useful in T20 and now loses games.",
        effects=[primary, secondary], charts=charts, tables={"cells": table, "share_of_long_innings_under_110": share_slow},
        samples={"innings": counts},
        caveats=["A slow innings is often a response to early wickets; WPA credits the batter only for what happened on "
                 "his balls, but team result also reflects the collapse around him.",
                 "T20Is restricted to matches between the top 10 teams."],
        database=database_label(),
    )


if __name__ == "__main__":
    res = run()
    print(res.save())
    print(res.verdict, res.headline)
