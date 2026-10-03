"""
H3 - Shreyas Iyer is an anchor, not an accelerator: middle-overs Impact per 100 and strike rate vs
Suryakumar Yadav, Tilak Varma and Rinku Singh, 2024-26; short-ball record. Definitions:
preregistration/h3_iyer_anchor.md.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, List

import numpy as np

from analysis.hypotheses.common import (
    Chart, Effect, Result, boot_p, bootstrap, canonical, ci, database_label, fmt_ci, query, read_only_session,
    resample, verdict_directional,
)

IYER = "Shreyas Iyer"
PEERS = ["Suryakumar Yadav", "Tilak Varma", "Rinku Singh"]
SCOPE = dict(start_date=date(2024, 1, 1))
MIDDLE = dict(over_min=6, over_max=14)
SHORT = ["SHORT", "SHORT_OF_A_GOOD_LENGTH"]
MIN_BALLS = 300


def _impact100(innings: List[dict]) -> float:
    mb = sum(r.get("metric_balls") or 0 for r in innings)
    return 100.0 * sum(r.get("impact") or 0 for r in innings) / mb if mb else np.nan


def _sr(innings: List[dict]) -> float:
    b = sum(r.get("balls") or 0 for r in innings)
    return 100.0 * sum(r.get("runs") or 0 for r in innings) / b if b else np.nan


def _diff(name: str, fn, iyer: List[dict], peers: List[dict], unit: str, meaningful: float) -> Effect:
    if not iyer or not peers:
        return Effect(name, None, [None, None], None, "bootstrap over innings", unit, "negative", meaningful)
    est = fn(iyer) - fn(peers)
    reps = bootstrap(lambda g: fn(resample(g, iyer)) - fn(resample(g, peers)))
    return Effect(name, float(est), ci(reps), boot_p(reps), "bootstrap over innings (ratio estimator)", unit, "negative",
                  meaningful, n={"iyer_innings": len(iyer), "peer_innings": len(peers)},
                  detail={"iyer": float(fn(iyer)), "peers": float(fn(peers))})


def run() -> Result:
    with read_only_session() as db:
        iyer = canonical(db, IYER)
        peers = [canonical(db, p) for p in PEERS]
        players = [iyer] + peers
        mid = query(db, batters=players, group_by=["batter", "match_id"], **MIDDLE, **SCOPE)
        mid_kind = query(db, batters=players, group_by=["batter", "match_id", "bowl_kind"], **MIDDLE, **SCOPE)
        short = query(db, batters=players, group_by=["batter"], length=SHORT, **SCOPE)
        totals = query(db, batters=players, group_by=["batter"], **SCOPE)

    by_player: Dict[str, List[dict]] = defaultdict(list)
    for r in mid:
        by_player[r["batter"]].append(r)
    balls = {p: sum(r["balls"] for r in by_player[p]) for p in players}
    kept = [p for p in peers if balls.get(p, 0) >= MIN_BALLS]
    dropped = [p for p in peers if p not in kept]
    peer_innings = [r for p in kept for r in by_player[p]]
    minimum = balls.get(iyer, 0) >= MIN_BALLS and bool(kept)

    impact = _diff("Iyer minus peers: middle-overs Impact per 100 balls", _impact100, by_player[iyer], peer_innings,
                   "Impact per 100 balls", -5)
    sr = _diff("Iyer minus peers: middle-overs strike rate", _sr, by_player[iyer], peer_innings, "strike rate", -10)
    kind_effects = []
    for kind in ("pace bowler", "spin bowler"):
        k_iyer = [r for r in mid_kind if r["batter"] == iyer and r["bowl_kind"] == kind]
        k_peers = [r for r in mid_kind if r["batter"] in kept and r["bowl_kind"] == kind]
        kind_effects.append(_diff(f"Iyer minus peers vs {kind.split()[0]}: Impact per 100 (exploratory)", _impact100,
                                  k_iyer, k_peers, "Impact per 100 balls", -5))
    verdict = verdict_directional(impact, minimum)

    total_balls = {r["batter"]: r["balls"] for r in totals}
    short_table = {r["batter"]: {"balls": r["balls"], "strike_rate": r.get("strike_rate"), "impact_per_100": r.get("impact_per_100"),
                                 "balls_per_dismissal": r.get("balls_per_dismissal"),
                                 "coverage_pct_of_all_balls": round(100 * r["balls"] / total_balls[r["batter"]], 1) if total_balls.get(r["batter"]) else None}
                   for r in short}
    player_table = {p: {"middle_balls": balls.get(p, 0), "innings": len(by_player[p]),
                        "strike_rate": _sr(by_player[p]) if by_player[p] else None,
                        "impact_per_100": _impact100(by_player[p]) if by_player[p] else None} for p in players}

    common = dict(batters=players, fmt="T20", **SCOPE)
    charts = [
        Chart("middle_impact", "Middle overs (7-15), 2024-26: Impact per 100 balls (batting view)",
              dict(common, group_by=["batter"], **MIDDLE), {"chart": "bar", "chart_metric": "impact_per_100"}),
        Chart("middle_sr", "Middle overs (7-15), 2024-26: strike rate", dict(common, group_by=["batter"], **MIDDLE),
              {"chart": "bar", "chart_metric": "strike_rate"}),
        Chart("kind", "Middle overs vs pace and spin, 2024-26", dict(common, group_by=["batter", "bowl_kind"], **MIDDLE),
              {"chart": "table"}),
        Chart("short", "Against short and short-of-a-length balls, 2024-26 (balls with length recorded)",
              dict(common, group_by=["batter"], length=SHORT), {"chart": "bar", "chart_metric": "strike_rate"}),
    ]
    headline = (f"In the middle overs Iyer adds {impact.detail.get('iyer', float('nan')):+.1f} Impact per 100 balls vs "
                f"{impact.detail.get('peers', float('nan')):+.1f} for the comparison group: {fmt_ci(impact, 1)}."
                if impact.estimate is not None else "Not enough data.")
    return Result(
        hypothesis="H3", slug="h3-iyer-anchor", verdict=verdict, headline=headline,
        claim="A common claim is that Shreyas Iyer anchors rather than accelerates in the middle overs, and struggles "
              "against the short ball.",
        effects=[impact, sr, *kind_effects], charts=charts,
        tables={"players": player_table, "short_balls": short_table, "dropped_for_sample": dropped},
        samples={"middle_balls": balls},
        caveats=["All men's T20 competitions in the window, so opposition strength differs between players.",
                 "Length is recorded for part of the balls only; short-ball numbers are exploratory."],
        database=database_label(),
    )


if __name__ == "__main__":
    res = run()
    print(res.save())
    print(res.verdict, res.headline)
