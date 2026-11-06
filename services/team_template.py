"""
The winners' template (TEAM_TEMPLATE_PLAN.md, T2-T3): what playoff sides' squads look like, role by role, against the
rest of their league, and which of those differences hold season after season.

Input: services/team_roles.league_roles (every player's job in every team-season, with the ledger's playoff sides).
Every measure is ranked within its season (0 = the season's worst side, 1 = its best), so 2008's run rates and 2026's
compare. A role's measure belongs to "the shape" when playoff sides beat the rest on it in most seasons, not just on
average.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any, Dict, List, Optional

from services.team_roles import BAT_SLOTS, PHASES, bat_slot

BOWL_SLOTS = [f"{ph}|{k}" for ph in PHASES for k in ("pace", "spin")]
SLOT_NAMES = {"openers": "Openers (1-2)", "top": "Top order (3-4)", "middle": "Middle & finishers (5-7)",
              "lower": "Lower order (8+)", "powerplay|pace": "Powerplay pace", "powerplay|spin": "Powerplay spin",
              "middle|pace": "Middle-overs pace", "middle|spin": "Middle-overs spin", "death|pace": "Death pace",
              "death|spin": "Death spin"}
CORE_BAT, CORE_BOWL, ALLROUND = 120, 120, 120   # balls in a season to count as a regular / an all-rounder


def _sum(rows, key):
    return sum((r.get(key) or 0) for r in rows)


def _ratio(a, b, scale=1.0):
    return scale * a / b if b else None


def team_features(players: List[Dict[str, Any]], with_primer: bool) -> Dict[str, Optional[float]]:
    """One team-season's measures: per batting slot and bowling slot, and the squad's structure."""
    f: Dict[str, Optional[float]] = {}
    bat_rows = [(pos, r) for p in players for pos, r in p["bat"].items()]
    team_bat_balls = sum(r.get("balls") or 0 for _, r in bat_rows)
    for slot, _, _ in BAT_SLOTS:
        rows = [r for pos, r in bat_rows if bat_slot(int(pos)) == slot]
        b, runs, outs = _sum(rows, "balls"), _sum(rows, "runs"), _sum(rows, "wickets")
        f[f"bat:{slot}:share"] = _ratio(b, team_bat_balls)
        f[f"bat:{slot}:strike_rate"] = _ratio(runs, b, 100)
        f[f"bat:{slot}:average"] = _ratio(runs, outs)
        f[f"bat:{slot}:boundary_pct"] = _ratio(_sum(rows, "boundaries"), b, 100)
        f[f"bat:{slot}:dot_pct"] = _ratio(_sum(rows, "dots"), b, 100)
        if with_primer:
            f[f"bat:{slot}:raa_per_100"] = _ratio(_sum(rows, "raa"), b, 100)
            f[f"bat:{slot}:wpa"] = _sum(rows, "wpa")
    bowl_rows = [(slot, r) for p in players for slot, r in p["bowl"].items()]
    team_bowl_balls = sum(r.get("balls") or 0 for _, r in bowl_rows)
    for slot in BOWL_SLOTS:
        rows = [r for s, r in bowl_rows if s == slot]
        b = _sum(rows, "balls")
        f[f"bowl:{slot}:share"] = _ratio(b, team_bowl_balls)
        f[f"bowl:{slot}:economy"] = _ratio(_sum(rows, "runs"), b, 6) if b >= 60 else None
        f[f"bowl:{slot}:wickets_per_24"] = _ratio(_sum(rows, "wickets"), b, 24) if b >= 60 else None
        f[f"bowl:{slot}:dot_pct"] = _ratio(_sum(rows, "dots"), b, 100) if b >= 60 else None
        if with_primer:
            f[f"bowl:{slot}:runs_saved_per_24"] = _ratio(_sum(rows, "raa"), b, 24) if b >= 60 else None
    for ph in PHASES:
        rows = [r for s, r in bowl_rows if s.startswith(ph + "|")]
        b = _sum(rows, "balls")
        f[f"bowl:{ph}:economy"] = _ratio(_sum(rows, "runs"), b, 6)
        f[f"bowl:{ph}:wickets_per_24"] = _ratio(_sum(rows, "wickets"), b, 24)
        brows = [r for p in players for phx, r in p["bat_phase"].items() if phx == ph]
        bb = _sum(brows, "balls")
        f[f"bat:{ph}:strike_rate"] = _ratio(_sum(brows, "runs"), bb, 100)
        f[f"bat:{ph}:average"] = _ratio(_sum(brows, "runs"), _sum(brows, "wickets"))
    # Structure: how many carry the side, and how concentrated it is.
    bat_balls = sorted((sum((r.get("balls") or 0) for r in p["bat"].values()) for p in players), reverse=True)
    bowl_balls = sorted((sum((r.get("balls") or 0) for r in p["bowl"].values()) for p in players), reverse=True)
    f["structure:regular_batters"] = sum(1 for b in bat_balls if b >= CORE_BAT)
    f["structure:regular_bowlers"] = sum(1 for b in bowl_balls if b >= CORE_BOWL)
    f["structure:top3_bat_share"] = _ratio(sum(bat_balls[:3]), team_bat_balls)
    f["structure:top5_bowl_share"] = _ratio(sum(bowl_balls[:5]), team_bowl_balls)
    f["structure:allrounders"] = sum(1 for p in players
                                     if sum((r.get("balls") or 0) for r in p["bat"].values()) >= ALLROUND
                                     and sum((r.get("balls") or 0) for r in p["bowl"].values()) >= ALLROUND)
    f["structure:players_used"] = sum(1 for p in players if p["bat"] or p["bowl"])
    f["structure:spin_share"] = _ratio(sum(r.get("balls") or 0 for s, r in bowl_rows if s.endswith("|spin")), team_bowl_balls)
    return f


#: Measures where lower is better.
LOWER_BETTER = ("economy", "dot_pct:bat")


def lower_is_better(feature: str) -> bool:
    kind, _, measure = feature.split(":")
    return (kind == "bowl" and measure == "economy") or (kind == "bat" and measure == "dot_pct")


def percentiles(values: Dict[str, Optional[float]], lower: bool) -> Dict[str, float]:
    """Each team's place in its season, 0 (worst) to 1 (best); ties share their place."""
    have = {t: v for t, v in values.items() if v is not None}
    if len(have) < 3:
        return {}
    xs = sorted(have.values(), reverse=lower)
    n = len(xs)
    out = {}
    for t, v in have.items():
        below = sum(1 for x in xs if (x > v if lower else x < v))
        equal = sum(1 for x in xs if x == v)
        out[t] = (below + (equal - 1) / 2) / (n - 1)
    return out


def template(league_data: Dict[str, Any], seasons: Optional[List[str]] = None, min_seasons: int = 5) -> Dict[str, Any]:
    """Per measure: playoff sides' average place in their season, the rest's, how often playoff sides were ahead, and
    the champions' place. Sorted by how consistently it separates them."""
    rows = []   # (season, team, playoff, champion, features)
    for s in league_data["seasons"]:
        if seasons and s["season"] not in seasons:
            continue
        primer = int(str(s["season"])[:4]) >= 2015
        for team, players in s["teams"].items():
            rows.append((s["season"], team, team in s["playoff"], team == s["champion"], team_features(players, primer)))
    features = sorted({k for *_, f in rows for k in f})
    by_season: Dict[str, List] = defaultdict(list)
    for r in rows:
        by_season[r[0]].append(r)
    result = []
    for feat in features:
        playoff_p, rest_p, champ_p, ahead, seasons_used = [], [], [], 0, 0
        playoff_v, rest_v = [], []
        for season, rs in by_season.items():
            pct = percentiles({t: f.get(feat) for _, t, _, _, f in rs}, lower_is_better(feat) if feat.count(":") == 2 else False)
            if not pct:
                continue
            po = [pct[t] for _, t, p, _, _ in rs if p and t in pct]
            re = [pct[t] for _, t, p, _, _ in rs if not p and t in pct]
            if not po or not re:
                continue
            seasons_used += 1
            playoff_p += po
            rest_p += re
            champ_p += [pct[t] for _, t, _, c, _ in rs if c and t in pct]
            ahead += statistics.mean(po) > statistics.mean(re)
            playoff_v += [f[feat] for _, t, p, _, f in rs if p and f.get(feat) is not None]
            rest_v += [f[feat] for _, t, p, _, f in rs if not p and f.get(feat) is not None]
        if seasons_used < min_seasons:
            continue
        result.append({
            "feature": feat, "seasons": seasons_used,
            "playoff_pct": statistics.mean(playoff_p), "rest_pct": statistics.mean(rest_p),
            "gap": statistics.mean(playoff_p) - statistics.mean(rest_p),
            "seasons_ahead": ahead / seasons_used,
            "champion_pct": statistics.mean(champ_p) if champ_p else None,
            "playoff_value": statistics.mean(playoff_v) if playoff_v else None,
            "rest_value": statistics.mean(rest_v) if rest_v else None,
        })
    result.sort(key=lambda r: (-abs(r["seasons_ahead"] - 0.5), -abs(r["gap"])))
    return {"league": league_data["league"], "teams": len(rows),
            "seasons": sorted(by_season), "measures": result}
