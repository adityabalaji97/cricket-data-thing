"""
H7 - The toss doesn't matter at Indian venues: toss-winner win %, chase win % and toss decisions
by venue, IPL and T20Is in India, 2023-26. Definitions: preregistration/h7_toss_india.md.
"""
from __future__ import annotations

from datetime import date

import numpy as np
from scipy import stats

from analysis.hypotheses.common import (
    Chart, Effect, Result, bootstrap, ci, database_label, query, read_only_session, resample, small,
    verdict_equivalence, wilson,
)

SCOPE = dict(query_mode="team_innings", leagues=["IPL"], include_international=True, start_date=date(2023, 1, 1),
             innings=1, dimension_filters=["country:eq:India"])
BAND = 5.0


def run() -> Result:
    with read_only_session() as db:
        matches = query(db, group_by=["match_id", "venue", "toss_decision"], **SCOPE)

    decided = [m for m in matches if m.get("toss_winner_win_percentage") is not None]
    won = [m["toss_winner_win_percentage"] == 100.0 for m in decided]
    n, k = len(won), int(sum(won))
    pct = 100 * k / n if n else None
    reps = bootstrap(lambda g: 100 * np.mean(resample(g, won)) - 50) if n else np.array([])
    p = float(stats.binomtest(k, n, 0.5).pvalue) if n else None
    eff = Effect("Toss winner's win % minus 50", (pct - 50) if pct is not None else None, ci(reps) if n else [None, None], p,
                 "exact binomial test; bootstrap CI over matches", "percentage points", "none", BAND,
                 n={"decided_matches": n}, detail={"toss_winner_wins": k, "wilson_ci_pct": [100 * x for x in wilson(k, n)] if n else None})
    verdict = verdict_equivalence(eff, BAND, minimum_met=n >= 30)

    venues = {}
    for m in decided:
        v = venues.setdefault(m["venue"], {"matches": 0, "toss_wins": 0, "bat_first_wins": 0, "chose_field": 0})
        v["matches"] += 1
        v["toss_wins"] += m["toss_winner_win_percentage"] == 100.0
        v["bat_first_wins"] += (m.get("win_percentage") or 0) == 100.0
        v["chose_field"] += m.get("toss_decision") == "field"
    by_venue, other = {}, {"matches": 0, "toss_wins": 0, "bat_first_wins": 0, "chose_field": 0}
    for name, v in sorted(venues.items(), key=lambda kv: -kv[1]["matches"]):
        if v["matches"] >= 15:
            by_venue[name] = v
        else:
            for key in other:
                other[key] += v[key]
    if other["matches"]:
        by_venue["other venues"] = other
    for v in by_venue.values():
        m = v["matches"]
        v.update({"toss_winner_win_pct": round(100 * v["toss_wins"] / m, 1),
                  "toss_winner_ci": [round(100 * x, 1) for x in wilson(v["toss_wins"], m)],
                  "chase_win_pct": round(100 * (m - v["bat_first_wins"]) / m, 1),
                  "chose_field_pct": round(100 * v["chose_field"] / m, 1),
                  "binomial_p": round(float(stats.binomtest(v["toss_wins"], m, 0.5).pvalue), 3)})

    venue_counts = {}
    for m in decided:
        venue_counts[m["venue"]] = venue_counts.get(m["venue"], 0) + 1
    common = dict(SCOPE, fmt="T20")
    charts = [
        Chart("venues", "Toss winner's win % by venue in India, IPL and T20Is 2023-26 (first-innings row per match)",
              dict(common, group_by=["venue"]), {"chart": "bar", "chart_metric": "toss_winner_win_percentage", "limit": 15},
              small({k: c for k, c in venue_counts.items()})[:6]),
        Chart("decision", "Bat-first win % by toss decision (India, 2023-26)", dict(common, group_by=["toss_decision"]),
              {"chart": "bar", "chart_metric": "win_percentage"}),
        Chart("season", "Toss winner's win % by season (India)", dict(common, group_by=["season"]),
              {"chart": "line", "chart_metric": "toss_winner_win_percentage"}),
    ]
    headline = (f"Toss winners won {k} of {n} decided matches in India ({pct:.1f}%); the 95% CI for the edge is "
                f"{eff.ci[0]:+.1f} to {eff.ci[1]:+.1f} points." if n else "No matches.")
    return Result(
        hypothesis="H7", slug="h7-toss-india", verdict=verdict, headline=headline,
        claim="A common claim is that the toss doesn't matter at Indian venues.",
        effects=[eff], charts=charts, tables={"by_venue": by_venue}, samples={"decided_matches": n},
        caveats=["Venue-level results are exploratory: many grounds, few matches each.",
                 f"'Doesn't matter' is tested as an equivalence band of +/-{BAND:.0f} points around 50%."],
        database=database_label(),
    )


if __name__ == "__main__":
    res = run()
    print(res.save())
    print(res.verdict, res.headline)
