"""
Two players side by side for the Compare page: every measure the profile ranks, and more, against the same pool.

Three sections per shared role, all ranked among the role's qualified players (the profile's peer pool) in the window:
* overall: the measures that rate a player (wins added, Impact, runs above par, strike rate or economy, dots,
  boundaries, false shots, balls per wicket), from a compare pool cached like the peer pool (one grouped query per
  format, role, window and scope; warmed nightly with the rest by scripts/warm_verdict.py);
* by phase and by opponent (pace or spin for batters, right- or left-handed batters for bowlers): from the profile's
  split pool, the one its standouts already read.
Each measure carries both values and ranks, the pool's median and quantiles, so the page draws both players on one strip.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from services.player_verdict import (
    PREFILTER_BALLS, ROLES, _num, _peer_pool, _query, _split_pool, _split_rows, default_window, quantiles, rank_among,
    scope_params, scope_label,
)
from services.player_aliases import expand_name_group
from services.query_cache import cached_run

COMPARE_VERSION = "c1"

# (key, label, lower is better, format)
OVERALL = {
    "bat": [("wpa", "Wins added", False, "signed2"), ("impact_per_innings", "Impact per innings", False, "signed1"),
            ("raa_per_100", "Runs above par /100 balls", False, "signed1"), ("strike_rate", "Strike rate", False, "int"),
            ("average", "Average", False, "dec1"), ("boundary_percentage", "Boundary %", False, "pct"),
            ("dot_percentage", "Dot %", True, "pct"), ("false_shot_percentage", "False shots", True, "pct")],
    "bowl": [("wpa", "Wins added", False, "signed2"), ("impact_per_innings", "Impact per innings", False, "signed1"),
             ("economy", "Economy", True, "dec2"), ("dot_percentage", "Dot %", False, "pct"),
             ("false_shot_percentage", "False shots forced", False, "pct"), ("balls_per_dismissal", "Balls per wicket", True, "int")],
}
SPLIT = {
    "bat": [("strike_rate", "Strike rate", False, "int"), ("boundary_percentage", "Boundary %", False, "pct")],
    "bowl": [("economy", "Economy", True, "dec2"), ("dot_percentage", "Dot %", False, "pct"),
             ("false_shot_percentage", "False shots forced", False, "pct")],
}
SPLIT_LABELS = {"phase:powerplay": "Powerplay", "phase:middle": "Middle overs", "phase:death": "Death",
                "bowl_kind:pace bowler": "v pace", "bowl_kind:spin bowler": "v spin",
                "bat_hand:RHB": "v right-handers", "bat_hand:LHB": "v left-handers"}
SECTIONS = {"bat": [("By phase", ["phase:powerplay", "phase:middle", "phase:death"]),
                    ("By opponent", ["bowl_kind:pace bowler", "bowl_kind:spin bowler"])],
            "bowl": [("By phase", ["phase:powerplay", "phase:middle", "phase:death"]),
                     ("By opponent", ["bat_hand:RHB", "bat_hand:LHB"])]}
SPLIT_MIN_BALLS = 60


def _compare_pool(db, fmt: str, role: str, window: Dict[str, Any], scope: Dict[str, Any], names: List[str]) -> Dict[str, Any]:
    r = ROLES[role]
    keys = [k for k, *_ in OVERALL[role]]

    def run():
        base = dict(metrics_perspective=r["perspective"], min_balls=PREFILTER_BALLS, **window, **scope)
        keep = set(names)
        out = {}
        for row in _query(db, fmt, group_by=[r["group"]], **base):
            name = row.get(r["group"])
            if name in keep:
                rec = {k: _num(row.get(k)) for k in keys}
                rec.update({k: v for k, v in _split_rows(row).items() if k in ("economy", "false_shot_percentage")})
                rec["balls"] = _num(row.get("balls")) or 0
                out[name] = rec
        return {"players": out}

    key = {"kind": "compare_pool", "v": COMPARE_VERSION, "fmt": fmt, "role": role, **window, **scope}
    return cached_run(db, key, run)


def _metric(key, label, lower, fmt_, rows: Dict[str, Dict[str, Any]], a: str, b: str, min_balls: float = 0) -> Optional[Dict[str, Any]]:
    pool = {n: r for n, r in rows.items() if r.get(key) is not None and (r.get("balls") or 0) >= min_balls}
    if a not in pool or b not in pool or len(pool) < 10:
        return None
    values = [r[key] for r in pool.values()]
    va, vb = pool[a][key], pool[b][key]
    return {"key": key, "label": label, "lower_is_better": lower, "format": fmt_, "n": len(values),
            "a": {"value": round(va, 3), "rank": rank_among(values, va, lower)},
            "b": {"value": round(vb, 3), "rank": rank_among(values, vb, lower)},
            "median": quantiles(values, 2)[1], "quantiles": [round(v, 3) for v in quantiles(values)]}


def _in_pool(db, name: str, names: List[str]) -> Optional[str]:
    """The pool's spelling of a player given in any of his spellings ("JJ Bumrah" from the player list, "Jasprit Bumrah" in the pool)."""
    pool = set(names)
    return next((n for n in [name, *expand_name_group([name], db)] if n in pool), None)


def build_compare(db, a: str, b: str, fmt: str = "T20", period: str = "recent", scope: str = "strong") -> Dict[str, Any]:
    start, end = default_window(fmt, period=period)
    window = {"start_date": start, "end_date": end}
    sc = scope_params(fmt, scope)
    roles = {}
    for role in ("bat", "bowl"):
        peers = _peer_pool(db, fmt, role, window, sc, build=period != "career")
        names = [p["name"] for p in peers["players"]]
        pa, pb = _in_pool(db, a, names), _in_pool(db, b, names)
        if not pa or not pb or pa == pb:
            continue
        a_, b_ = pa, pb
        overall = [m for m in (_metric(k, l, lo, f, _compare_pool(db, fmt, role, window, sc, names)["players"], a_, b_)
                               for k, l, lo, f in OVERALL[role]) if m]
        sections = [{"title": "Overall", "groups": [{"label": None, "metrics": overall}]}]
        split = _split_pool(db, fmt, role, window, sc, names, build=period != "career")
        for title, splits in SECTIONS[role]:
            groups = []
            for s in splits:
                rows = (split or {}).get("splits", {}).get(s, {})
                ms = [m for m in (_metric(k, l, lo, f, rows, a_, b_, SPLIT_MIN_BALLS) for k, l, lo, f in SPLIT[role]) if m]
                if ms:
                    groups.append({"label": SPLIT_LABELS[s], "metrics": ms})
            if groups:
                sections.append({"title": title, "groups": groups})
        roles[role] = {"a": a_, "b": b_, "pool": len(names), "floor_label": peers["floor_label"], "sections": sections}
    return {"a": a, "b": b, "format": fmt, "period": period, "scope": scope, "scope_label": scope_label(fmt, scope),
            "window": {"start_date": start.isoformat(), "end_date": end.isoformat()}, "roles": roles, "version": COMPARE_VERSION}


def get_compare(db, a: str, b: str, fmt: str = "T20", period: str = "recent", scope: str = "strong") -> Dict[str, Any]:
    key = {"kind": "player_compare", "v": COMPARE_VERSION, "a": a.lower(), "b": b.lower(), "fmt": fmt, "period": period,
           "scope": scope, "day": date.today()}
    return cached_run(db, key, lambda: build_compare(db, a, b, fmt, period, scope))
