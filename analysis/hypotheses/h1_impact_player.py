"""
H1 - The Impact Player rule inflated IPL scoring: difference-in-differences against BBL, PSL and
CPL, seasons starting 2020-2022 vs 2023-2026. Definitions: preregistration/h1_impact_player.md.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Callable, Dict, List

import numpy as np

from analysis.hypotheses.common import (
    Chart, Effect, Result, boot_p, bootstrap, ci, database_label, fmt_ci, query, read_only_session, resample,
    verdict_directional,
)

TREATED = "IPL"
CONTROLS = ["BBL", "PSL", "CPL"]
DESCRIPTIVE = ["SA20"]
PRE, POST = range(2020, 2023), range(2023, 2027)


def _innings(db) -> List[dict]:
    return query(db, query_mode="team_innings", leagues=[TREATED, *CONTROLS, *DESCRIPTIVE], start_date=date(2019, 7, 1),
                 group_by=["match_id", "innings", "competition", "season_start_year"],
                 dimension_filters=["full_length:eq:1", "season_start_year:gte:2020"])


def _ratio(num: str, den: str, scale: float) -> Callable[[List[List[dict]]], float]:
    def f(matches):
        rows = [r for m in matches for r in m]
        d = sum(r.get(den) or 0 for r in rows)
        return scale * sum(r.get(num) or 0 for r in rows) / d if d else np.nan
    return f


def _share(threshold: int) -> Callable[[List[List[dict]]], float]:
    def f(matches):
        firsts = [r for m in matches for r in m if r["innings"] == 1]
        return 100.0 * np.mean([r["avg_total"] >= threshold for r in firsts]) if firsts else np.nan
    return f


OUTCOMES: Dict[str, tuple] = {
    "runs per over": (_ratio("runs", "balls", 6.0), 0.3),
    "powerplay runs per over": (_ratio("powerplay_runs", "powerplay_balls", 6.0), 0.3),
    "middle-overs runs per over": (_ratio("middle_runs", "middle_balls", 6.0), 0.3),
    "death runs per over": (_ratio("death_runs", "death_balls", 6.0), 0.3),
    "boundary % of balls": (_ratio("boundaries", "balls", 100.0), 1.0),
    "dot % of balls": (_ratio("dots", "balls", 100.0), -1.0),
    "first innings 200+ (%)": (_share(200), 5.0),
    "first innings 250+ (%)": (_share(250), 1.0),
}


def _cells(rows: List[dict], pre=PRE, post=POST) -> Dict[tuple, List[List[dict]]]:
    by_match: Dict[tuple, Dict[str, List[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        year = int(r["season_start_year"])
        period = "pre" if year in pre else "post" if year in post else None
        if period is None:
            continue
        group = "treated" if r["competition"] == TREATED else "control" if r["competition"] in CONTROLS else None
        if group:
            by_match[(group, period)][r["match_id"]].append(r)
    return {k: list(v.values()) for k, v in by_match.items()}


def _did(cells, fn, name, meaningful) -> Effect:
    keys = [("treated", "post"), ("treated", "pre"), ("control", "post"), ("control", "pre")]
    if any(not cells.get(k) for k in keys):
        return Effect(name, None, [None, None], None, "bootstrap DiD", "", "positive", meaningful)
    est = (fn(cells[keys[0]]) - fn(cells[keys[1]])) - (fn(cells[keys[2]]) - fn(cells[keys[3]]))
    reps = bootstrap(lambda g: (fn(resample(g, cells[keys[0]])) - fn(resample(g, cells[keys[1]])))
                     - (fn(resample(g, cells[keys[2]])) - fn(resample(g, cells[keys[3]]))))
    direction = "negative" if meaningful < 0 else "positive"
    return Effect(f"DiD: {name}", float(est), ci(reps), boot_p(reps), "bootstrap difference-in-differences (matches)",
                  name, direction, meaningful,
                  n={f"{g}_{p}_innings": sum(len(m) for m in cells[(g, p)]) for g, p in keys},
                  detail={f"{g}_{p}": float(fn(cells[(g, p)])) for g, p in keys})


def run() -> Result:
    with read_only_session() as db:
        rows = _innings(db)
    cells = _cells(rows)
    effects = [_did(cells, fn, name, m) for name, (fn, m) in OUTCOMES.items()]
    primary = effects[0]
    # Minimum: 100 innings in every league-period cell, controls checked one league at a time.
    per_league = defaultdict(int)
    for r in rows:
        y = int(r["season_start_year"])
        per_league[(r["competition"], "pre" if y in PRE else "post")] += 1
    minimum = all(per_league[(lg, p)] >= 100 for lg in [TREATED, *CONTROLS] for p in ("pre", "post"))
    verdict = verdict_directional(primary, minimum)
    sens = _did(_cells(rows, pre=range(2022, 2023)), OUTCOMES["runs per over"][0], "runs per over (pre = 2022 only)", 0.3)
    sa20 = defaultdict(list)
    for r in rows:
        if r["competition"] == "SA20":
            sa20[int(r["season_start_year"])].append(r)
    sa20_rr = {y: round(6 * sum(r["runs"] for r in v) / sum(r["balls"] for r in v), 2) for y, v in sorted(sa20.items())}

    ipl_pre, ipl_post = primary.detail.get("treated_pre"), primary.detail.get("treated_post")
    headline = (f"IPL scoring rose from {ipl_pre:.2f} to {ipl_post:.2f} runs per over; after netting out BBL, PSL and "
                f"CPL over the same seasons the Impact Player era adds {fmt_ci(primary)} runs per over."
                if ipl_pre is not None and primary.estimate is not None else "Not enough data.")
    base = dict(query_mode="team_innings", fmt="T20", start_date=date(2019, 7, 1),
                dimension_filters=["full_length:eq:1", "season_start_year:gte:2020"])
    charts = [
        Chart("ipl_rr", "IPL runs per over by season (full-length innings)", dict(base, leagues=[TREATED], group_by=["season"]),
              {"chart": "line", "chart_metric": "run_rate"}),
        Chart("leagues", "Runs per over before and after 2023: IPL vs leagues without the rule",
              dict(base, leagues=[TREATED, *CONTROLS], group_by=["competition", "impact_player_era"]),
              {"chart": "table", "limit": 20}),
        Chart("ipl_200", "IPL first innings reaching 200, by season (%)",
              dict(base, leagues=[TREATED], innings=1, group_by=["season"]), {"chart": "bar", "chart_metric": "pct_200_plus"}),
        Chart("phases", "Runs per over by phase, IPL and control leagues, before and after 2023",
              dict(base, leagues=[TREATED, *CONTROLS], group_by=["impact_player_era", "competition"]),
              {"chart": "table", "limit": 20}),
    ]
    return Result(
        hypothesis="H1", slug="h1-impact-player", verdict=verdict, headline=headline,
        claim="A common claim is that the Impact Player rule, introduced in IPL 2023, inflated IPL scoring.",
        effects=effects + [sens], charts=charts,
        tables={"cells_innings": {f"{k[0]}|{k[1]}": v for k, v in per_league.items()}, "sa20_runs_per_over": sa20_rr},
        samples={"innings": len(rows)},
        caveats=["Difference-in-differences attributes to the rule every IPL-specific change from 2023 (squads, "
                 "conditions, balls, strategy), not only the extra batter.",
                 "IPL 2020 and part of 2021 were played in the UAE; the 2022-only sensitivity check addresses that.",
                 "SA20 started in 2023, so it has no before period and is shown for context only."],
        database=database_label(),
    )


if __name__ == "__main__":
    res = run()
    print(res.save())
    print(res.verdict, res.headline)
