"""Feature vectors for the statistical twins (DOPPELGANGER_PLAN.md S1).

For one period (a season or a window), one role and one scope, every player's raw features, in groups. The groups are
what the engine weights equally (services/twins.py), so a group with many features (shot mix) can't drown one with few:

  batting  style: usage, scoring, shots (tracked), matchups      value: value
  bowling  style: usage, lengths (tracked), lines (tracked), outcomes   value: value

Everything comes from run_deliveries_query (the query builder), so the numbers match the site's. Players below the
period's floor (services/qualification.py) are stored but marked unqualified.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from services.player_verdict import scope_params
from services.qualification import min_balls, qualifying_players
from services.query_builder_v2 import run_deliveries_query
from services.shot_families import FAMILIES

PHASES = ("powerplay", "middle", "death")
LENGTHS = ("YORKER", "FULL", "GOOD_LENGTH", "SHORT_OF_A_GOOD_LENGTH", "SHORT", "FULL_TOSS")
LINES = ("ON_THE_STUMPS", "OUTSIDE_OFFSTUMP", "WIDE_OUTSIDE_OFFSTUMP", "DOWN_LEG", "WIDE_DOWN_LEG")
KINDS = {"pace bowler": "pace", "spin bowler": "spin"}
PREFILTER_BALLS = 30

# group -> "style" | "value": which twin a group feeds.
GROUPS = {
    "bat": {"usage": "style", "scoring": "style", "shots": "style", "matchups": "style", "value": "value"},
    "bowl": {"usage": "style", "lengths": "style", "lines": "style", "outcomes": "style", "value": "value"},
}
TRACKED_GROUPS = {"shots", "lengths", "lines"}

ROLE = {
    "bat": {"group": "batter", "filter": "batters", "perspective": "batting"},
    "bowl": {"group": "bowler", "filter": "bowlers", "perspective": "bowling"},
}


def _n(v: Any) -> Optional[float]:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def _div(a: Any, b: Any) -> Optional[float]:
    a, b = _n(a), _n(b)
    return a / b if a is not None and b else None


def _q(db, fmt: str, role: str, group_by: List[str], window: Dict[str, Any], scope: Dict[str, Any], **extra):
    r = ROLE[role]
    rows = run_deliveries_query(db, fmt=fmt, limit=10000 * 5, group_by=[r["group"], *group_by],
                                metrics_perspective=r["perspective"], **window, **scope, **extra)
    return list((rows or {}).get("data") or [])


def _by_player(rows, key: str, sub: Optional[str] = None) -> Dict[str, Dict[Any, Dict[str, Any]]]:
    out: Dict[str, Dict[Any, Dict[str, Any]]] = {}
    for row in rows:
        out.setdefault(row.get(key), {})[row.get(sub) if sub else None] = row
    return out


def _shares(parts: Dict[Any, Dict[str, Any]], keys, total: float) -> Dict[str, Optional[float]]:
    return {str(k).lower(): (_div((parts.get(k) or {}).get("balls") or 0, total) if total else None) for k in keys}


def batting_features(db, fmt: str, window: Dict[str, Any], scope: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    overall = _by_player(_q(db, fmt, "bat", [], window, scope, min_balls=PREFILTER_BALLS), "batter")
    phase = _by_player(_q(db, fmt, "bat", ["phase"], window, scope), "batter", "phase")
    position = _by_player(_q(db, fmt, "bat", ["batting_position"], window, scope), "batter", "batting_position")
    family = _by_player(_q(db, fmt, "bat", ["shot_family"], window, scope), "batter", "shot_family")
    kind = _by_player(_q(db, fmt, "bat", ["bowl_kind"], window, scope), "batter", "bowl_kind")

    out = {}
    for name, rows in overall.items():
        o = rows[None]
        balls = o.get("balls") or 0
        ph = phase.get(name, {})
        pos = position.get(name, {})
        pos_inns = sum((r.get("innings_count") or 0) for p, r in pos.items() if p is not None)
        fam = family.get(name, {})
        tagged = sum((r.get("balls") or 0) for f, r in fam.items() if f)
        kd = kind.get(name, {})
        pace, spin = kd.get("pace bowler") or {}, kd.get("spin bowler") or {}
        features = {
            "usage": {
                "position": _div(sum((p or 0) * (r.get("innings_count") or 0) for p, r in pos.items() if p is not None), pos_inns),
                "balls_per_innings": _div(balls, o.get("innings_count")),
                **{f"share_{p}": _div((ph.get(p) or {}).get("balls") or 0, balls) for p in PHASES},
            },
            "scoring": {
                "dot_pct": _n(o.get("dot_percentage")),
                "boundary_pct": _n(o.get("boundary_percentage")),
                "six_share": _div(o.get("sixes"), o.get("boundaries")),
                **{f"sr_{p}": _n((ph.get(p) or {}).get("strike_rate")) if ((ph.get(p) or {}).get("balls") or 0) >= 30 else None
                   for p in PHASES},
            },
            "shots": {**_shares(fam, FAMILIES.keys(), tagged), "control_pct": _n(o.get("control_percentage"))} if tagged else {},
            "matchups": {
                "sr_pace": _n(pace.get("strike_rate")) if (pace.get("balls") or 0) >= 30 else None,
                "sr_spin": _n(spin.get("strike_rate")) if (spin.get("balls") or 0) >= 30 else None,
                "bpd_pace": _n(pace.get("balls_per_dismissal")) if (pace.get("balls") or 0) >= 30 else None,
                "bpd_spin": _n(spin.get("balls_per_dismissal")) if (spin.get("balls") or 0) >= 30 else None,
            },
            "value": {
                "raa_per_100": _n(o.get("raa_per_100")),
                **{f"raa_per_100_{p}": _n((ph.get(p) or {}).get("raa_per_100")) if ((ph.get(p) or {}).get("balls") or 0) >= 30 else None
                   for p in PHASES},
                "impact_per_innings": _n(o.get("impact_per_innings")),
                "wpa_per_innings": _div(o.get("wpa"), o.get("innings_count")),
                "balls_per_dismissal": _n(o.get("balls_per_dismissal")),
                "average": _n(o.get("average")),
            },
        }
        out[name] = {"balls": balls, "innings": o.get("innings_count") or 0, "kind": None,
                     "tracked_share": _div(tagged, balls), "features": features}
    return out


def bowling_features(db, fmt: str, window: Dict[str, Any], scope: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    overall = _by_player(_q(db, fmt, "bowl", [], window, scope, min_balls=PREFILTER_BALLS), "bowler")
    phase = _by_player(_q(db, fmt, "bowl", ["phase"], window, scope), "bowler", "phase")
    length = _by_player(_q(db, fmt, "bowl", ["length"], window, scope), "bowler", "length")
    line = _by_player(_q(db, fmt, "bowl", ["line"], window, scope), "bowler", "line")
    hand = _by_player(_q(db, fmt, "bowl", ["bat_hand"], window, scope), "bowler", "bat_hand")
    kind = _by_player(_q(db, fmt, "bowl", ["bowl_kind"], window, scope), "bowler", "bowl_kind")

    out = {}
    for name, rows in overall.items():
        o = rows[None]
        balls = o.get("balls") or 0
        ph = phase.get(name, {})
        ln = length.get(name, {})
        li = line.get(name, {})
        len_tagged = sum((r.get("balls") or 0) for k, r in ln.items() if k)
        line_tagged = sum((r.get("balls") or 0) for k, r in li.items() if k)
        hd = hand.get(name, {})
        kinds = kind.get(name, {})
        main_kind = max(kinds.items(), key=lambda kv: kv[1].get("balls") or 0)[0] if kinds else None
        econ = lambda r: _div((r.get("runs") or 0) * 6, r.get("balls"))  # noqa: E731
        features = {
            "usage": {
                "balls_per_innings": _div(balls, o.get("innings_count")),
                **{f"share_{p}": _div((ph.get(p) or {}).get("balls") or 0, balls) for p in PHASES},
            },
            "lengths": _shares(ln, LENGTHS, len_tagged) if len_tagged else {},
            "lines": _shares(li, LINES, line_tagged) if line_tagged else {},
            "outcomes": {
                "dot_pct": _n(o.get("dot_percentage")),
                "boundary_pct": _n(o.get("boundary_percentage")),
                "control_induced": _n(o.get("control_percentage")),
                "econ_v_lhb": econ(hd["LHB"]) if (hd.get("LHB") or {}).get("balls", 0) >= 30 else None,
                "econ_v_rhb": econ(hd["RHB"]) if (hd.get("RHB") or {}).get("balls", 0) >= 30 else None,
            },
            "value": {
                "economy": econ(o),
                **{f"economy_{p}": econ(ph[p]) if (ph.get(p) or {}).get("balls", 0) >= 30 else None for p in PHASES},
                "raa_per_over": _n(o.get("raa_per_over")),
                "balls_per_wicket": _n(o.get("balls_per_dismissal")),
                "waa_per_over": _n(o.get("waa_per_over")),
                "wpa_per_innings": _div(o.get("wpa"), o.get("innings_count")),
            },
        }
        out[name] = {"balls": balls, "innings": o.get("innings_count") or 0, "kind": main_kind,
                     "tracked_share": _div(len_tagged, balls), "features": features}
    return out


def build_period(db, role: str, start: date, end: date, fmt: str = "T20", scope: str = "strong",
                 unit: str = "season", match_ids: Optional[List[str]] = None,
                 floor: Optional[int] = None) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """({player: vector}, qualification) for one role and period. A season qualifies on its own floor; a window
    needs the floor in 2+ of its seasons (services/qualification.qualifying_players)."""
    window = {"start_date": start, "end_date": end}
    if match_ids:  # validation's split halves
        window["match_ids"] = match_ids
    sp = scope_params(fmt, scope)
    vectors = (batting_features if role == "bat" else bowling_features)(db, fmt, window, sp)
    if unit == "season":
        fl = floor if floor is not None else min_balls(vectors.values())["min_balls"]
        qual = {"floor": fl, "players": {n for n, v in vectors.items() if v["balls"] >= fl}}
    else:
        r = ROLE[role]
        seasons = run_deliveries_query(db, fmt=fmt, limit=50000, group_by=[r["group"], "year"],
                                       metrics_perspective=r["perspective"], min_balls=PREFILTER_BALLS, **window, **sp)["data"]
        q = qualifying_players(seasons, r["group"])
        qual = {"floor": min(q["floors"].values(), default=0), "players": q["players"]}
    for n, v in vectors.items():
        v["qualified"] = n in qual["players"]
        v["floor_balls"] = qual["floor"]
    return vectors, qual
