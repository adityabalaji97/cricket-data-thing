"""The statistical twins engine (DOPPELGANGER_PLAN.md S2).

Every feature in player_vectors becomes a percentile within its period (a season compares with its own season, which
is the era adjustment), then twins are nearest neighbours by group-weighted distance:

  d(a, b) = sqrt( mean over groups g used of  mean over features f in g of (p_a,f - p_b,f)^2 )

so each group counts the same however many features it has. Two twins per player: "plays like" (style groups) and
"worth like" (value). Tracked groups (shots, lengths, lines) are left out of a pair when either player has under
TRACKED_MIN of his balls tagged. Bowlers' style twins stay within their kind (pace or spin). All-rounders (qualified
in both roles in the period) are matched on both roles together, each weighted by its share of the innings, and only
against other all-rounders.
"""
from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional, Tuple

from services.twins_features import GROUPS, TRACKED_GROUPS

TRACKED_MIN = 0.7
MIN_GROUP_SHARE = 0.5  # a pair needs at least half its groups to be compared at all
# A "worth like" twin carried at least this share of the player's workload (balls) in his season: a part-timer's one
# lucky 150-ball season ranked level with Bumrah's 500 (Khushdil Shah as Bumrah's twin, first local run).
VALUE_MIN_WORKLOAD = 0.5
# "Same" only counts where it's something: both players near nothing (no reverse sweeps) isn't a likeness.
NOTABLE = 0.25
_CACHE: Dict[Tuple, Tuple[float, Any]] = {}
_TTL = 600

LABELS = {
    "position": "batting position", "balls_per_innings": "balls per innings", "share_powerplay": "share of balls in the powerplay",
    "share_middle": "share in the middle overs", "share_death": "share at the death", "dot_pct": "dot %",
    "boundary_pct": "boundary %", "six_share": "sixes among boundaries", "sr_powerplay": "powerplay strike rate",
    "sr_middle": "middle-overs strike rate", "sr_death": "death strike rate", "control_pct": "control %",
    "sr_pace": "strike rate v pace", "sr_spin": "strike rate v spin", "bpd_pace": "balls per dismissal v pace",
    "bpd_spin": "balls per dismissal v spin", "raa_per_100": "runs above par per 100 balls",
    "raa_per_100_powerplay": "runs above par, powerplay", "raa_per_100_middle": "runs above par, middle overs",
    "raa_per_100_death": "runs above par, death", "impact_per_innings": "Impact per innings",
    "wpa_per_innings": "wins added per innings", "balls_per_dismissal": "balls per dismissal", "average": "average",
    "control_induced": "batters' control %", "econ_v_lhb": "economy v left-handers", "econ_v_rhb": "economy v right-handers",
    "economy": "economy", "economy_powerplay": "powerplay economy", "economy_middle": "middle-overs economy",
    "economy_death": "death economy", "raa_per_over": "runs above par per over", "balls_per_wicket": "balls per wicket",
    "waa_per_over": "wickets above par per over",
}


def label(feature: str) -> str:
    role, _, feature = feature.rpartition(":")
    text = _label(feature)
    return f"{text} ({'bat' if role == 'bat' else 'ball'})" if role else text


def _label(feature: str) -> str:
    group, _, key = feature.partition(".")
    if group == "shots" and key not in LABELS:
        return f"{key.replace('_', ' ')} shots"
    if group in ("lengths", "lines"):
        return key.replace("_", " ").lower()
    return LABELS.get(key, key.replace("_", " "))


def _load(db, unit: str, role: str, scope: str) -> List[Dict[str, Any]]:
    from sqlalchemy import text

    rows = db.execute(text("""
        SELECT period, player, balls, innings, kind, tracked_share, features FROM player_vectors
        WHERE unit = :u AND role = :r AND scope = :s AND qualified
    """), {"u": unit, "r": role, "s": scope}).mappings().all()
    return [dict(r) for r in rows]


def percentiles(rows: List[Dict[str, Any]]) -> None:
    """Adds row["p"] = {"group.feature": percentile 0-1 within the row's period}."""
    by_period: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        r["p"] = {}
        by_period.setdefault(r["period"], []).append(r)
    for members in by_period.values():
        keys = {f"{g}.{k}" for r in members for g, fs in r["features"].items() for k in fs}
        for key in keys:
            g, k = key.split(".", 1)
            vals = sorted((r["features"].get(g) or {}).get(k) for r in members
                          if (r["features"].get(g) or {}).get(k) is not None)
            if len(vals) < 2:
                continue
            for r in members:
                v = (r["features"].get(g) or {}).get(k)
                if v is None:
                    continue
                below = sum(1 for x in vals if x < v)
                equal = sum(1 for x in vals if x == v)
                r["p"][key] = (below + (equal - 1) / 2) / (len(vals) - 1)


def pool(db, unit: str, role: str, scope: str = "strong") -> List[Dict[str, Any]]:
    """Qualified vectors with percentiles; 'allround' joins bat and bowl for players qualified in both."""
    key = (unit, role, scope)
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    if role == "allround":
        bat = {(r["period"], r["player"]): r for r in pool(db, unit, "bat", scope)}
        bowl = {(r["period"], r["player"]): r for r in pool(db, unit, "bowl", scope)}
        rows = []
        for k in bat.keys() & bowl.keys():
            a, b = bat[k], bowl[k]
            share = a["innings"] / ((a["innings"] + b["innings"]) or 1)
            # A second role he plays in under 40% of the innings of his main one isn't all-rounding
            # (services/player_verdict.SECOND_ROLE_SHARE).
            if min(a["innings"], b["innings"]) < 0.4 * max(a["innings"], b["innings"]):
                continue
            rows.append({"period": k[0], "player": k[1], "balls": a["balls"] + b["balls"], "kind": b["kind"],
                         "bat_weight": share, "tracked_share": min(a["tracked_share"] or 0, b["tracked_share"] or 0),
                         "p": {**{f"bat:{f}": v for f, v in a["p"].items()}, **{f"bowl:{f}": v for f, v in b["p"].items()}},
                         "features": {"bat": a["features"], "bowl": b["features"]}, "tracked": {"bat": a["tracked_share"], "bowl": b["tracked_share"]}})
    else:
        rows = _load(db, unit, role, scope)
        percentiles(rows)
    _CACHE[key] = (time.time(), rows)
    return rows


def _groups(role: str, kind: str) -> List[Tuple[str, str]]:
    """(prefix, group) pairs a twin of this kind compares."""
    if role == "allround":
        return [(f"{r}:", g) for r in ("bat", "bowl") for g, k in GROUPS[r].items() if k == kind]
    return [("", g) for g, k in GROUPS[role].items() if k == kind]


def distance(a: Dict[str, Any], b: Dict[str, Any], role: str, kind: str,
             skip_groups: Tuple[str, ...] = ()) -> Optional[Tuple[float, List[Tuple[str, float]]]]:
    """(distance, [(feature, |difference|)]) or None when too few groups can be compared."""
    groups = [(p, g) for p, g in _groups(role, kind) if g not in skip_groups]
    total, used, diffs = 0.0, 0.0, []
    for prefix, g in groups:
        if g in TRACKED_GROUPS:
            ta = (a.get("tracked") or {}).get(prefix[:-1]) if prefix else a.get("tracked_share")
            tb = (b.get("tracked") or {}).get(prefix[:-1]) if prefix else b.get("tracked_share")
            if (ta or 0) < TRACKED_MIN or (tb or 0) < TRACKED_MIN:
                continue
        keys = [k for k in a["p"] if k.startswith(f"{prefix}{g}.") and k in b["p"]]
        if not keys:
            continue
        weight = 1.0
        if prefix:  # all-rounders: each role by its share of the innings
            w = a.get("bat_weight", 0.5)
            weight = 2 * (w if prefix == "bat:" else 1 - w)
        sq = [(k, abs(a["p"][k] - b["p"][k])) for k in keys]
        total += weight * sum(d * d for _, d in sq) / len(sq)
        used += weight
        diffs += sq
    if not used or used < MIN_GROUP_SHARE * len(groups):
        return None
    return math.sqrt(total / used), diffs


def find(db, player: str, period: str, role: str = "bat", kind: str = "style", n: int = 5, unit: str = "season",
         scope: str = "strong", same_period: bool = False) -> Dict[str, Any]:
    """The player's n nearest twins in the pool (every season, unless same_period), never himself."""
    rows = pool(db, unit, role, scope)
    out = find_in(rows, player, period, role, kind, n, same_period)
    out["pool"] = len(rows)
    return out


def find_in(rows: List[Dict[str, Any]], player: str, period: str, role: str = "bat", kind: str = "style", n: int = 5,
            same_period: bool = False, skip_groups: Tuple[str, ...] = ()) -> Dict[str, Any]:
    """find() over rows already loaded (validation runs it on split halves and with groups dropped)."""
    me = next((r for r in rows if r["player"].lower() == player.lower() and r["period"] == period), None)
    if me is None:
        return {"player": player, "period": period, "role": role, "kind": kind, "twins": [], "qualified": False}
    out = []
    for r in rows:
        if r["player"] == me["player"] or (same_period and r["period"] != period):
            continue
        if kind == "style" and role in ("bowl", "allround") and me.get("kind") and r.get("kind") != me.get("kind"):
            continue
        if kind == "value" and (r.get("balls") or 0) < VALUE_MIN_WORKLOAD * (me.get("balls") or 0):
            continue
        d = distance(me, r, role, kind, skip_groups)
        if d is None:
            continue
        out.append((d[0], r, d[1]))
    out.sort(key=lambda t: t[0])
    twins, seen = [], set()
    for dist, r, diffs in out:
        if r["player"] in seen:  # each player once, at his closest season
            continue
        seen.add(r["player"])
        notable = [(f, g) for f, g in diffs if max(me["p"][f], r["p"][f]) >= NOTABLE]
        notable.sort(key=lambda t: t[1])
        diffs.sort(key=lambda t: t[1])
        twins.append({
            "player": r["player"], "period": r["period"], "distance": round(dist, 4),
            "closest": [{"feature": f, "label": label(f), "gap": round(g, 3)} for f, g in notable[:3]],
            "furthest": [{"feature": f, "label": label(f), "gap": round(g, 3)} for f, g in diffs[-3:][::-1]],
        })
        if len(twins) == n:
            break
    return {"player": me["player"], "period": period, "role": role, "kind": kind, "qualified": True, "twins": twins}
