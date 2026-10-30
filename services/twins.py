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
# Features whose split-half reliability over careers was under r = 0.4 (scripts/dev/twins_validate.py --reliability,
# local 2024-26, 28 Oct 2026): matching on them is matching on noise. Impact and wins added per innings (r 0.02-0.09)
# describe what happened but don't repeat, so they stay on the cards as context, never in the distance.
UNRELIABLE = {
    "bat": {"value.impact_per_innings", "value.wpa_per_innings", "value.raa_per_100_death", "value.average",
            "scoring.sr_death", "matchups.bpd_pace", "matchups.bpd_spin", "shots.ramp_scoop"},
    "bowl": {"value.wpa_per_innings", "value.balls_per_wicket", "value.economy_death", "value.economy_middle",
             "value.economy_powerplay", "value.waa_per_over", "value.raa_per_over", "lines.wide_down_leg",
             "outcomes.econ_v_lhb"},
}


def _unreliable(key: str) -> bool:
    role, _, feature = key.rpartition(":")
    return any(feature in UNRELIABLE[r] for r in ([role] if role else ("bat", "bowl")))
MIN_GROUP_SHARE = 0.5  # a pair needs at least half its groups to be compared at all
# A "worth like" twin carried at least this share of the player's workload (balls) in his season: a part-timer's one
# lucky 150-ball season ranked level with Bumrah's 500 (Khushdil Shah as Bumrah's twin, first local run).
VALUE_MIN_WORKLOAD = 0.5
# "Same" only counts where it's something: both players near nothing (no reverse sweeps) isn't a likeness.
NOTABLE = 0.25
_CACHE: Dict[Tuple, Tuple[float, Any]] = {}
_TTL = 600

LABELS = {
    "position": "batting position", "balls_per_innings": "balls per innings", "share_powerplay": "powerplay share",
    "share_middle": "middle-overs share", "share_death": "death share", "dot_pct": "dot %",
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

    # Careers: only the latest window built (the nightly job writes today's; older ones stay until the next run).
    latest = "AND period = (SELECT period FROM player_vectors WHERE unit = :u AND role = :r AND scope = :s " \
             "ORDER BY built_at DESC LIMIT 1)" if unit in ("window", "career") else ""
    rows = db.execute(text(f"""
        SELECT period, player, balls, innings, kind, tracked_share, features FROM player_vectors
        WHERE unit = :u AND role = :r AND scope = :s AND qualified {latest}
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
        keys = [k for k in a["p"] if k.startswith(f"{prefix}{g}.") and k in b["p"] and not _unreliable(k)]
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


def _tracked(r: Dict[str, Any]) -> bool:
    if r.get("tracked"):  # all-rounders: both roles
        return all((v or 0) >= TRACKED_MIN for v in r["tracked"].values())
    return (r.get("tracked_share") or 0) >= TRACKED_MIN


def comparable(me: Dict[str, Any], other: Dict[str, Any]) -> bool:
    """Shot-tracked players are matched only with each other, and the rest only with each other. Without this, a player missing the
    tracked groups was compared on fewer groups, looked close to everyone, and became the nearest twin of half
    the board (Aneurin Donald, 4 points from Abhishek, Arya and Allen)."""
    return _tracked(me) == _tracked(other)  # both ways: an untracked player isn't matched with a tracked one either


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
        if r["player"] == me["player"] or (same_period and r["period"] != period) or not comparable(me, r):
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


# What each twin's card shows of value, side by side (not matched on: see UNRELIABLE).
VALUE_SHOWN = {
    "bat": [("value", "raa_per_100", "Runs above par per 100 balls"), ("value", "wpa_per_innings", "Wins added per innings"),
            ("scoring", "boundary_pct", "Boundary %")],
    "bowl": [("value", "economy", "Economy"), ("value", "wpa_per_innings", "Wins added per innings"),
             ("outcomes", "dot_pct", "Dot balls %")],
}


def latest_window(db, scope: str = "strong", unit: str = "window") -> Optional[str]:
    from sqlalchemy import text

    return db.execute(text("SELECT period FROM player_vectors WHERE unit = :u AND scope = :s "
                           "ORDER BY built_at DESC LIMIT 1"), {"u": unit, "s": scope}).scalar()


def role_of(db, player: str, unit: str, period: str, scope: str = "strong") -> Optional[str]:
    """'allround' when qualified in both roles with the second in 40%+ of the main role's innings, else the role
    with more innings (qualified first)."""
    rows = {r["role"]: r for r in pool_rows(db, player, unit, period, scope)}
    q = {k: v for k, v in rows.items() if v["qualified"]}
    if len(q) == 2 and min(q["bat"]["innings"], q["bowl"]["innings"]) >= 0.4 * max(q["bat"]["innings"], q["bowl"]["innings"]):
        return "allround"
    pick = q or rows
    return max(pick, key=lambda r: pick[r]["innings"]) if pick else None


def pool_rows(db, player: str, unit: str, period: str, scope: str):
    from sqlalchemy import text

    return [dict(r) for r in db.execute(text("""
        SELECT role, innings, qualified FROM player_vectors
        WHERE unit = :u AND period = :p AND scope = :s AND lower(player) = lower(:n)
    """), {"u": unit, "p": period, "s": scope, "n": player}).mappings().all()]


def compare_values(me: Dict[str, Any], twin: Dict[str, Any], role: str) -> List[Dict[str, Any]]:
    roles = ["bat", "bowl"] if role == "allround" else [role]
    out = []
    for r in roles:
        mf = me["features"].get(r, me["features"]) if role == "allround" else me["features"]
        tf = twin["features"].get(r, twin["features"]) if role == "allround" else twin["features"]
        for g, k, text_ in VALUE_SHOWN[r]:
            out.append({"role": r, "key": k, "label": text_,
                        "player": (mf.get(g) or {}).get(k), "twin": (tf.get(g) or {}).get(k)})
    return out


def twins_for(db, player: str, unit: str = "window", period: Optional[str] = None, role: Optional[str] = None,
              n: int = 5, scope: str = "strong") -> Dict[str, Any]:
    """The API's answer: "plays like" twins with their closest and furthest features, and both players' value side
    by side. Careers (unit window) compare within the window; seasons compare across every season (cross-era)."""
    windowed = unit in ("window", "career")
    period = period or (latest_window(db, scope, unit) if windowed else None)
    if not period:
        return {"player": player, "qualified": False, "twins": []}
    role = role or role_of(db, player, unit, period, scope)
    if not role:
        return {"player": player, "period": period, "qualified": False, "twins": []}
    rows = pool(db, unit, role, scope)
    out = find_in(rows, player, period, role, "style", n, same_period=windowed)
    if not out.get("qualified"):
        return {**out, "unit": unit}
    me = next(r for r in rows if r["player"] == out["player"] and r["period"] == period)
    by = {(r["player"], r["period"]): r for r in rows}
    for t in out["twins"]:
        twin = by[(t["player"], t["period"])]
        t["gap_points"] = round(100 * t["distance"])
        t["values"] = compare_values(me, twin, role)
        t["compare"] = compare_rows(me, twin, role)
    near = find_in(rows, out["player"], period, role, "style", MAP_N, same_period=windowed)["twins"]
    stats = gap_stats(db, unit, role, scope)
    nearest = out["twins"][0]["distance"] if out["twins"] else None
    unique = bool(stats.get("p90") and nearest is not None and nearest > stats["p90"])
    return {**out, "unit": unit, "pool": len(rows), "kind": "style",
            "map": twin_map(me, [(t["distance"], by[(t["player"], t["period"])]) for t in near], role),
            "typical_gap_points": round(100 * stats["median"]) if stats.get("median") else None,
            "unique": unique}


# ---- uniqueness (how far the nearest twin is, against everyone's) ---------------------------------------------------

UNIQUE_QUANTILE = 0.9   # nearest twin further than 90% of players' nearest twins: "no close twin"
GAP_SAMPLE = 300        # seasons pool (~7,000 player-seasons): the gap distribution from a sample


def nearest_gap_stats(rows: List[Dict[str, Any]], role: str, same_period: bool, sample: int = GAP_SAMPLE) -> Dict[str, Any]:
    """Median and 90th percentile of each player's nearest-twin distance in the pool (a sample of players for big
    pools, each against the whole pool). Built nightly (scripts/build_player_vectors.py) into app_meta."""
    import random

    members = rows if len(rows) <= sample else random.Random(7).sample(rows, sample)
    gaps = []
    for r in members:
        best = None
        for o in rows:
            if o["player"] == r["player"] or (same_period and o["period"] != r["period"]) or not comparable(r, o):
                continue
            if role in ("bowl", "allround") and r.get("kind") and o.get("kind") != r.get("kind"):
                continue
            d = distance(r, o, role, "style")
            if d is not None and (best is None or d[0] < best):
                best = d[0]
        if best is not None:
            gaps.append(best)
    gaps.sort()
    if not gaps:
        return {}
    at = lambda q: gaps[min(len(gaps) - 1, int(q * (len(gaps) - 1)))]  # noqa: E731
    return {"median": round(at(0.5), 4), "p90": round(at(UNIQUE_QUANTILE), 4), "players": len(gaps)}


def store_gap_stats(db, unit: str, scope: str = "strong") -> Dict[str, Any]:
    import json
    from sqlalchemy import text

    out = {}
    for role in ("bat", "bowl", "allround"):
        _CACHE.pop((unit, role, scope), None)
        rows = pool(db, unit, role, scope)
        out[role] = nearest_gap_stats(rows, role, same_period=unit in ("window", "career"))
    db.execute(text("""
        INSERT INTO app_meta (key, value, updated_at) VALUES (:k, :v, now())
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
    """), {"k": f"twins_gaps:{unit}:{scope}", "v": json.dumps(out)})
    db.commit()
    return out


def gap_stats(db, unit: str, role: str, scope: str = "strong") -> Dict[str, Any]:
    import json
    from sqlalchemy import text

    key = ("gaps", unit, scope)
    hit = _CACHE.get(key)
    if not hit or time.time() - hit[0] >= _TTL:
        raw = db.execute(text("SELECT value FROM app_meta WHERE key = :k"), {"k": f"twins_gaps:{unit}:{scope}"}).scalar()
        hit = (time.time(), json.loads(raw) if raw else {})
        _CACHE[key] = hit
    return hit[1].get(role) or {}


# ---- the map (who sits where around the player) --------------------------------------------------------------------

MAP_N = 24


def twin_map(me: Dict[str, Any], near: List[Tuple[float, Dict[str, Any]]], role: str) -> List[Dict[str, Any]]:
    """The nearest players around the player: radius = the true distance, angle from a 2-D classical MDS of the
    group's pairwise distances (so players alike to each other sit on the same side)."""
    import numpy as np

    pts = [me] + [r for _, r in near]
    k = len(pts)
    if k < 3:
        return [{"player": r["player"], "period": r["period"], "distance": round(d, 4), "angle": 0.0} for d, r in near]
    dm = np.zeros((k, k))
    for i in range(k):
        for j in range(i + 1, k):
            d = distance(pts[i], pts[j], role, "style")
            dm[i, j] = dm[j, i] = d[0] if d else 0.5
    j = np.eye(k) - np.ones((k, k)) / k
    b = -0.5 * j @ (dm ** 2) @ j
    vals, vecs = np.linalg.eigh(b)
    order = np.argsort(vals)[::-1][:2]
    xy = vecs[:, order] * np.sqrt(np.maximum(vals[order], 0))
    cx, cy = xy[0]
    out = []
    for (d, r), (x, y) in zip(near, xy[1:]):
        out.append({"player": r["player"], "period": r["period"], "distance": round(d, 4),
                    "angle": round(math.degrees(math.atan2(y - cy, x - cx)), 1)})
    return out


def compare_rows(me: Dict[str, Any], twin: Dict[str, Any], role: str) -> List[Dict[str, Any]]:
    """Both players' percentiles on every feature the style distance compared, in group order."""
    rows = []
    for prefix, g in _groups(role, "style"):
        if g in TRACKED_GROUPS:
            ta = (me.get("tracked") or {}).get(prefix[:-1]) if prefix else me.get("tracked_share")
            tb = (twin.get("tracked") or {}).get(prefix[:-1]) if prefix else twin.get("tracked_share")
            if (ta or 0) < TRACKED_MIN or (tb or 0) < TRACKED_MIN:
                continue
        for k in sorted(k for k in me["p"] if k.startswith(f"{prefix}{g}.") and k in twin["p"] and not _unreliable(k)):
            rows.append({"feature": k, "group": f"{prefix}{g}", "label": label(k),
                         "player": round(100 * me["p"][k]), "twin": round(100 * twin["p"][k])})
    return rows


# ---- the board (/doppelgangers): closest pairs and the players with no close twin -----------------------------------

BOARD_N = 15


def build_board(db, unit: str = "window", scope: str = "strong") -> Dict[str, Any]:
    """Per role: every player's nearest twin, then the closest pairs (each pair once) and the players whose nearest
    twin is furthest away. Careers only (the season pool is too big to compare all against all on request)."""
    out = {}
    for role in ("bat", "bowl", "allround"):
        _CACHE.pop((unit, role, scope), None)
        rows = pool(db, unit, role, scope)
        nearest = []
        for r in rows:
            res = find_in(rows, r["player"], r["period"], role, "style", 1, same_period=(unit == "window"))
            if res.get("twins"):
                t = res["twins"][0]
                nearest.append({"player": r["player"], "twin": t["player"], "gap_points": round(100 * t["distance"]),
                                "distance": t["distance"], "same": [c["label"] for c in t["closest"][:2]]})
        pairs, seen = [], set()
        for n_ in sorted(nearest, key=lambda x: x["distance"]):
            key = tuple(sorted((n_["player"], n_["twin"])))
            if key in seen:
                continue
            seen.add(key)
            pairs.append(n_)
            if len(pairs) == BOARD_N:
                break
        unique = sorted(nearest, key=lambda x: -x["distance"])[:BOARD_N]
        gaps = sorted(n_["distance"] for n_ in nearest)
        out[role] = {"pool": len(rows), "pairs": pairs, "unique": unique,
                     "typical_gap_points": round(100 * gaps[len(gaps) // 2]) if gaps else None}
    return out


def store_board(db, unit: str = "window", scope: str = "strong") -> Dict[str, Any]:
    import json
    from sqlalchemy import text

    board = build_board(db, unit, scope)
    db.execute(text("""
        INSERT INTO app_meta (key, value, updated_at) VALUES (:k, :v, now())
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
    """), {"k": f"twins_board:{unit}:{scope}", "v": json.dumps(board)})
    db.commit()
    _CACHE.pop(("board", unit, scope), None)
    return board


def board(db, unit: str = "window", scope: str = "strong") -> Dict[str, Any]:
    import json
    from sqlalchemy import text

    key = ("board", unit, scope)
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    raw = db.execute(text("SELECT value FROM app_meta WHERE key = :k"), {"k": f"twins_board:{unit}:{scope}"}).scalar()
    value = json.loads(raw) if raw else store_board(db, unit, scope)
    _CACHE[key] = (time.time(), value)
    return value
