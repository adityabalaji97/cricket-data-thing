"""
H2 - Has Varun Chakravarthy been figured out? Recent seasons vs earlier, by season and
half-season, by batter's hand, length, shot and dismissal. Definitions: preregistration/h2.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date

import numpy as np

from analysis.hypotheses.common import (
    Chart, Effect, Result, bootstrap, canonical, ci, database_label, fmt_ci, mean, mean_diff_effect, per_over,
    query, read_only_session, resample, small, verdict_directional,
)

VARUN = "Varun Chakravarthy"
SCOPE = dict(leagues=["IPL"], include_international=True, start_date=date(2015, 1, 1), metrics_perspective="bowling")
RECENT = {"2025", "2026"}


def _slope(points):
    """OLS slope of RAA/over on time (years)."""
    if len(points) < 3:
        return np.nan
    x = np.array([p[0] for p in points]); y = np.array([p[1] for p in points])
    if np.ptp(x) == 0:
        return np.nan
    return float(np.polyfit(x, y, 1)[0])


def run() -> Result:
    with read_only_session() as db:
        varun = canonical(db, VARUN)
        matches = query(db, bowlers=[varun], group_by=["match_id", "match_date", "season", "competition"], **SCOPE)
        by_hand = query(db, bowlers=[varun], group_by=["bat_hand", "season"], **SCOPE)
        by_length = query(db, bowlers=[varun], group_by=["length"], **SCOPE)
        by_shot = query(db, bowlers=[varun], group_by=["shot"], **SCOPE)
        dismissals = {
            "earlier": query(db, bowlers=[varun], group_by=["dismissal"], end_date=date(2024, 12, 31), **SCOPE),
            "2025-26": query(db, bowlers=[varun], group_by=["dismissal"], **dict(SCOPE, start_date=date(2025, 1, 1))),
        }

    rows = [r for r in matches if per_over(r) is not None]
    recent = [per_over(r) for r in rows if str(r["season"]) in RECENT]
    earlier = [per_over(r) for r in rows if str(r["season"]) not in RECENT]
    raa = mean_diff_effect("Varun: per-match RAA/over, 2025-26 minus earlier seasons", recent, earlier,
                           unit="RAA per over", direction="negative", meaningful=-0.5, label_a="2025-26", label_b="earlier")
    waa = mean_diff_effect("Varun: per-match WAA/over, 2025-26 minus earlier", [per_over(r, "waa") for r in rows if str(r["season"]) in RECENT],
                           [per_over(r, "waa") for r in rows if str(r["season"]) not in RECENT],
                           unit="WAA per over", direction="negative", meaningful=-0.05, label_a="2025-26", label_b="earlier")
    points = []
    for r in rows:
        d = date.fromisoformat(str(r["match_date"]))
        points.append((d.year + (d.timetuple().tm_yday - 1) / 365.25, per_over(r)))
    slope_reps = bootstrap(lambda g: _slope(resample(g, points)))
    slope = Effect("Trend: change in per-match RAA/over per year", None if math.isnan(_slope(points)) else _slope(points),
                   ci(slope_reps), None, "OLS slope, bootstrap over matches", "RAA per over per year", "negative", -0.25,
                   n={"matches": len(points)})

    by_season = defaultdict(list)
    for r in rows:
        by_season[str(r["season"])].append(r)
    season_table = {s: {"matches": len(v), "raa_per_over": mean([per_over(r) for r in v]),
                        "waa_per_over": mean([per_over(r, "waa") for r in v])} for s, v in sorted(by_season.items())}
    halves = {}
    for s, v in sorted(by_season.items()):
        ipl = sorted((r for r in v if r["competition"] == "IPL"), key=lambda r: r["match_date"])
        if not ipl:
            continue
        cut = math.ceil(len(ipl) / 2)
        for label, part in (("1st half", ipl[:cut]), ("2nd half", ipl[cut:])):
            halves[f"IPL {s} {label}"] = {"matches": len(part), "raa_per_over": mean([per_over(r) for r in part])}

    minimum = len(recent) >= 15 and len(earlier) >= 30
    verdict = verdict_directional(raa, minimum)
    total_balls = sum(r["balls"] for r in by_length)
    coverage = {"length": round(100 * sum(r["balls"] for r in by_length if r.get("length")) / total_balls, 1) if total_balls else None}

    def _dist(rs):
        w = sum(r.get("wickets") or 0 for r in rs) or 1
        return {r["dismissal"]: round(100 * (r.get("wickets") or 0) / w, 1) for r in rs if r.get("dismissal")}

    charts = [
        Chart("season", "Varun's RAA per over by season (bowling view)",
              dict(bowlers=[varun], group_by=["season"], fmt="T20", **SCOPE), {"chart": "line", "chart_metric": "raa_per_over"},
              small({s: t["matches"] for s, t in season_table.items()})),
        Chart("hand", "Varun's RAA per over against left- and right-handers, by season",
              dict(bowlers=[varun], group_by=["season", "bat_hand"], fmt="T20", **SCOPE), {"chart": "table", "limit": 40}),
        Chart("length", "Varun's RAA per 100 balls by length (balls with length recorded)",
              dict(bowlers=[varun], group_by=["length"], fmt="T20", **SCOPE), {"chart": "bar", "chart_metric": "raa_per_100"}),
        Chart("dismissal", "How Varun's wickets fall (all seasons)",
              dict(bowlers=[varun], group_by=["dismissal"], fmt="T20", **SCOPE), {"chart": "bar", "chart_metric": "wickets"}),
    ]
    headline = (f"Varun's RAA per over in 2025-26 vs earlier: {fmt_ci(raa)} "
                f"({len(recent)} recent and {len(earlier)} earlier matches).")
    return Result(
        hypothesis="H2", slug="h2-varun-figured-out", verdict=verdict, headline=headline,
        claim="A common claim is that batters have figured Varun Chakravarthy out.",
        effects=[raa, waa, slope], charts=charts,
        tables={"by_season": season_table, "half_seasons": halves,
                "by_hand": [{k: r.get(k) for k in ("season", "bat_hand", "balls", "raa_per_100", "economy", "runs", "wickets")} for r in by_hand],
                "by_length": [{k: r.get(k) for k in ("length", "balls", "raa_per_100", "runs", "wickets")} for r in by_length],
                "by_shot": [{k: r.get(k) for k in ("shot", "balls", "raa_per_100", "runs", "wickets")} for r in by_shot][:15],
                "dismissal_share": {k: _dist(v) for k, v in dismissals.items()}},
        samples={"matches": len(rows), "coverage_percent": coverage},
        caveats=["Length and shot are recorded for part of the balls only (coverage in samples).",
                 "Seasons mix IPL and T20Is; T20Is cluster around tournaments."],
        database=database_label(),
    )


if __name__ == "__main__":
    res = run()
    print(res.save())
    print(res.verdict, res.headline)
