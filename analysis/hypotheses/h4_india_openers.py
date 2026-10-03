"""
H4 - India's T20I openers are all or nothing: spread of Impact per innings for Samson, Abhishek
Sharma and Ishan Kishan vs India's other openers; India's win rate and WPA when they fail vs fire.
Definitions: preregistration/h4_india_openers.md.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

import numpy as np
from scipy import stats

from analysis.hypotheses.common import (
    Chart, Effect, Result, boot_p, bootstrap, canonical, ci, database_label, mean, query, read_only_session,
    resample, verdict_directional,
)

NAMED = ["Sanju Samson", "Abhishek Sharma", "Ishan Kishan"]
SCOPE = dict(batting_teams=["India"], include_international=True, start_date=date(2015, 1, 1))
FAIL, FIRE = -5.0, 10.0


def _cls(impact):
    return "fail" if impact < FAIL else "fire" if impact > FIRE else "middle"


def run() -> Result:
    with read_only_session() as db:
        named = [canonical(db, n) for n in NAMED]
        rows = query(db, group_by=["batter", "match_id", "batting_position", "match_outcome"], **SCOPE)

    openers = [r for r in rows if r.get("batting_position") in (1, 2) and r.get("impact") is not None]
    by_batter = defaultdict(list)
    for r in openers:
        by_batter[r["batter"]].append(r)
    comparison = [b for b, v in by_batter.items() if b not in named and len(v) >= 15]
    named_imp = [r["impact"] for b in named for r in by_batter[b]]
    comp_imp = [r["impact"] for b in comparison for r in by_batter[b]]

    def sd_ratio(a, b):
        return np.std(a, ddof=1) / np.std(b, ddof=1) if len(a) > 1 and len(b) > 1 else np.nan

    est = sd_ratio(named_imp, comp_imp)
    reps = bootstrap(lambda g: sd_ratio(resample(g, named_imp), resample(g, comp_imp))) if named_imp and comp_imp else np.array([])
    # Verdict on log(ratio) so that "above 1" maps to the positive direction; meaningful = log(1.2).
    log_eff = Effect("Spread of Impact per innings: SD(named) / SD(other openers), log scale", float(np.log(est)) if est == est else None,
                     [float(np.log(x)) for x in ci(reps)] if len(reps) else [None, None], boot_p(np.log(reps), 0.0) if len(reps) else None,
                     "bootstrap over innings", "log SD ratio", "positive", float(np.log(1.2)))
    ratio = Effect("SD ratio (named three / other India openers)", float(est) if est == est else None, ci(reps) if len(reps) else [None, None],
                   log_eff.p_value, "bootstrap over innings", "ratio", "positive", 1.2,
                   n={"named_innings": len(named_imp), "comparison_innings": len(comp_imp)},
                   detail={"sd_named": float(np.std(named_imp, ddof=1)) if len(named_imp) > 1 else None,
                           "sd_comparison": float(np.std(comp_imp, ddof=1)) if len(comp_imp) > 1 else None,
                           "comparison_openers": comparison})
    # Pre-registered: named players are reported individually from 15 opening innings; the pooled
    # comparison needs the same floor on both sides.
    minimum = len(named_imp) >= 15 and len(comp_imp) >= 15
    verdict = verdict_directional(log_eff, minimum)

    shares = {}
    for b in named + ["other India openers"]:
        imps = comp_imp if b == "other India openers" else [r["impact"] for r in by_batter[b]]
        if imps:
            shares[b] = {"innings": len(imps), "fail_pct": round(100 * np.mean([x < FAIL for x in imps]), 1),
                         "fire_pct": round(100 * np.mean([x > FIRE for x in imps]), 1),
                         "mean_impact": round(float(np.mean(imps)), 2), "sd_impact": round(float(np.std(imps, ddof=1)), 2) if len(imps) > 1 else None,
                         "small_sample": len(imps) < 15}

    decided = [r for b in named for r in by_batter[b] if r["match_outcome"] in ("win", "loss")]
    fire = [r for r in decided if _cls(r["impact"]) == "fire"]
    fail = [r for r in decided if _cls(r["impact"]) == "fail"]
    wins = lambda rs: sum(r["match_outcome"] == "win" for r in rs)
    win_eff = Effect("India win % when the opener fires minus when he fails", None, [None, None], None,
                     "Fisher's exact test; bootstrap CI over innings", "percentage points", "positive", 20)
    if fire and fail:
        table = [[wins(fire), len(fire) - wins(fire)], [wins(fail), len(fail) - wins(fail)]]
        p = float(stats.fisher_exact(table).pvalue)
        diff = lambda a, b: 100 * (np.mean([r["match_outcome"] == "win" for r in a]) - np.mean([r["match_outcome"] == "win" for r in b]))
        reps_w = bootstrap(lambda g: diff(resample(g, fire), resample(g, fail)))
        win_eff = Effect(win_eff.name, float(diff(fire, fail)), ci(reps_w), p, win_eff.test, win_eff.unit, "positive", 20,
                         n={"fire": len(fire), "fail": len(fail)},
                         detail={"win_pct_fire": 100 * wins(fire) / len(fire), "win_pct_fail": 100 * wins(fail) / len(fail),
                                 "wpa_per_innings_fire": mean([r.get("wpa") for r in fire]),
                                 "wpa_per_innings_fail": mean([r.get("wpa") for r in fail])})

    charts = [
        Chart("impact", "India T20I innings: Impact per innings by batting position (named openers)",
              dict(batters=named, group_by=["batter", "batting_position"], fmt="T20", **SCOPE),
              {"chart": "table"}),
        Chart("result", "Impact per innings for the three, India wins vs losses",
              dict(batters=named, group_by=["batter", "match_outcome"], fmt="T20", **SCOPE), {"chart": "table"}),
        Chart("wpa", "Win probability added per innings, India T20Is (all positions)",
              dict(batters=named + comparison[:6], group_by=["batter"], fmt="T20", **SCOPE),
              {"chart": "bar", "chart_metric": "wpa_per_innings"}),
    ]
    headline = (f"The three's Impact per innings is {ratio.estimate:.2f}x as spread out as other India openers' "
                f"(95% CI {ratio.ci[0]:.2f}-{ratio.ci[1]:.2f}); India win {win_eff.detail.get('win_pct_fire', float('nan')):.0f}% "
                f"when they fire vs {win_eff.detail.get('win_pct_fail', float('nan')):.0f}% when they fail."
                if ratio.estimate is not None and ratio.ci[0] is not None and win_eff.detail else "Not enough data.")
    return Result(
        hypothesis="H4", slug="h4-india-openers", verdict=verdict, headline=headline,
        claim="A common claim is that India's T20I openers Sanju Samson, Abhishek Sharma and Ishan Kishan are all or "
              "nothing: they either win the game or fail cheaply.",
        effects=[ratio, log_eff, win_eff], charts=charts, tables={"shares": shares},
        samples={"opening_innings": {b: len(by_batter[b]) for b in named}},
        caveats=[f"Fail = Impact below {FAIL:+.0f}, fire = above {FIRE:+.0f} runs added to the projected total.",
                 "Batting position is the order of arrival at the crease; position 1-2 = opener.",
                 "A spread measure says nothing about the average; both are shown."],
        database=database_label(),
    )


if __name__ == "__main__":
    res = run()
    print(res.save())
    print(res.verdict, res.headline)
