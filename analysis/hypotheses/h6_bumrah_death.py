"""
H6 - Jasprit Bumrah is the best death bowler: leverage-weighted death-overs RAA for every bowler
with 600+ death balls since 2015, rank, gap and bootstrap rank stability. Definitions:
preregistration/h6_bumrah_death.md.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

import numpy as np

from analysis.hypotheses.common import (
    INCONCLUSIVE, NOT_SUPPORTED, PARTLY, SUPPORTED, Chart, Effect, Result, N_BOOT, canonical, ci, database_label,
    query, read_only_session, rng,
)

BUMRAH = "Jasprit Bumrah"
DEATH = dict(over_min=15, over_max=19, start_date=date(2015, 1, 1))
MIN_BALLS = 600


def run() -> Result:
    with read_only_session() as db:
        bumrah = canonical(db, BUMRAH)
        pop = query(db, group_by=["bowler"], min_balls=MIN_BALLS, **DEATH)
        names = [r["bowler"] for r in pop if r.get("raa_lw_per_100") is not None]
        per_match = query(db, bowlers=names, group_by=["bowler", "match_id"], **DEATH)

    # Per match: numerator sum(raa * leverage) and denominator sum(leverage), so resampled matches
    # combine exactly like the engine's pooled raa_lw_per_100.
    num, den, wpa, balls = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    for r in per_match:
        if r["bowler"] not in names or not r.get("metric_balls") or r.get("avg_leverage") is None:
            continue
        lev = float(r["avg_leverage"]) * float(r["metric_balls"])
        num[r["bowler"]].append((r.get("raa_lw_per_100") or 0) / 100.0 * lev)
        den[r["bowler"]].append(lev)
        wpa[r["bowler"]].append(r.get("wpa") or 0.0)
        balls[r["bowler"]].append(r["metric_balls"])
    names = [n for n in names if den[n]]
    point = {n: 100 * sum(num[n]) / sum(den[n]) for n in names}
    ranking = sorted(names, key=lambda n: -point[n])

    g = rng()
    reps = np.empty((N_BOOT, len(names)))
    for j, n in enumerate(names):
        a, b = np.array(num[n]), np.array(den[n])
        idx = g.integers(0, len(a), (N_BOOT, len(a)))
        reps[:, j] = 100 * a[idx].sum(axis=1) / b[idx].sum(axis=1)
    rank_of = {n: j for j, n in enumerate(names)}
    if bumrah in rank_of:
        bj = rank_of[bumrah]
        best_other = np.max(np.delete(reps, bj, axis=1), axis=1)
        gap_reps = reps[:, bj] - best_other
        p_first = float(np.mean(gap_reps > 0))
        rank = ranking.index(bumrah) + 1
        other = ranking[1] if ranking[0] == bumrah else ranking[0]
        gap = point[bumrah] - point[other]
    else:
        gap_reps, p_first, rank, other, gap = np.array([]), None, None, None, None
    gap_eff = Effect(f"Bumrah's leverage-weighted death RAA per 100 minus the best other bowler's", gap,
                     ci(gap_reps) if len(gap_reps) else [None, None], None,
                     "bootstrap over each bowler's matches (gap to the best other bowler in each replicate)",
                     "RAA per 100 balls (leverage-weighted)", "positive", 0.0,
                     n={"bowlers": len(names), "bumrah_matches": len(den.get(bumrah, []))},
                     detail={"rank": rank, "next_best": other, "share_of_resamples_ranked_first": p_first})

    # Pre-registered: Supported = ranked first with the gap CI above zero; Partly = first with the gap
    # CI including zero, or 2nd-3rd while the leader's gap over him includes zero; Not supported =
    # below 3rd, or the leader's gap over him excludes zero.
    leader_clear = False
    if rank and rank > 1:
        lead_gap = reps[:, rank_of[ranking[0]]] - reps[:, rank_of[bumrah]]
        leader_clear = float(np.percentile(lead_gap, 2.5)) > 0
    if rank is None:
        verdict = INCONCLUSIVE
    elif rank == 1:
        verdict = SUPPORTED if (gap_eff.ci[0] is not None and gap_eff.ci[0] > 0) else PARTLY
    elif rank <= 3 and not leader_clear:
        verdict = PARTLY
    else:
        verdict = NOT_SUPPORTED

    top = [{"rank": i + 1, "bowler": n, "raa_lw_per_100": round(point[n], 2),
            "ci": [round(x, 2) for x in ci(reps[:, rank_of[n]])], "wpa_per_100": round(100 * sum(wpa[n]) / sum(balls[n]), 3),
            "death_balls": int(sum(balls[n]))} for i, n in enumerate(ranking[:15])]
    pop_rows = {r["bowler"]: r for r in pop}
    for row in top:
        src = pop_rows.get(row["bowler"], {})
        row.update({"raa_per_100": src.get("raa_per_100"), "economy": round(src["runs"] * 6 / src["balls"], 2) if src.get("balls") else None})

    common = dict(group_by=["bowler"], min_balls=MIN_BALLS, fmt="T20", **DEATH)
    charts = [
        Chart("lw_raa", "Death overs (16-20) since 2015, 600+ balls: leverage-weighted RAA per 100 balls (bowling view)",
              common, {"chart": "bar", "chart_metric": "raa_lw_per_100", "sort_by": "raa_lw_per_100", "limit": 10,
                       "highlight": bumrah}),
        Chart("wpa", "Death overs since 2015, 600+ balls: win probability added (total)",
              common, {"chart": "bar", "chart_metric": "wpa", "sort_by": "wpa", "limit": 10, "highlight": bumrah}),
        Chart("bumrah_year", "Bumrah at the death by year: leverage-weighted RAA per 100 balls",
              dict(bowlers=[bumrah], group_by=["year"], fmt="T20", **DEATH), {"chart": "line", "chart_metric": "raa_lw_per_100"}),
    ]
    headline = (f"Bumrah ranks {rank} of {len(names)} death bowlers on leverage-weighted RAA "
                f"({point[bumrah]:+.1f} per 100 balls); ahead of the next best in {100 * p_first:.0f}% of resamples."
                if rank else "Bumrah does not reach the sample minimum.")
    return Result(
        hypothesis="H6", slug="h6-bumrah-death", verdict=verdict, headline=headline,
        claim="A common claim is that Jasprit Bumrah is the best death bowler in T20 cricket.",
        effects=[gap_eff], charts=charts, tables={"top15": top}, samples={"qualifying_bowlers": len(names)},
        caveats=["All men's T20 competitions with Primer metrics since 2015 (The Hundred excluded by the metrics).",
                 "Leverage-weighted RAA weights each ball by how much was at stake on it."],
        database=database_label(),
    )


if __name__ == "__main__":
    res = run()
    print(res.save())
    print(res.verdict, res.headline)
