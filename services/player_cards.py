"""
The player profile's role cards (PROFILE_SIMPLIFY_PLAN.md P2): every number the cards below the verdict draw, for the
same window and scope as the verdict, from one cached call (GET /player/{name}/cards).

Batters: his start (strike rate and typical runs v par by ball of the innings), where he scores (runs by area),
against each bowling type (six families), how he gets out. Bowlers: where he bowls (line x length), by phase (economy,
dots, false shots), right- v left-handers, how he takes wickets. An all-rounder gets both sets.
"""
from __future__ import annotations

import statistics
import threading
from datetime import date
from typing import Any, Dict, List, Optional

from services.player_verdict import ROLE_MIN_BALLS, default_window, scope_params
from services.query_cache import cached_run

CARDS_VERSION = "c1"
START_BALLS = 30          # the start card runs to the 30th ball of an innings
FAMILY_MIN_BALLS = 40     # a bowling family with fewer balls is left off
CELL_MIN_BALLS = 15       # a pitch-map cell with fewer balls is left blank
FAMILIES = {
    "RF": "Right-arm pace", "RFM": "Right-arm pace", "RMF": "Right-arm pace", "RM": "Right-arm pace",
    "LF": "Left-arm pace", "LFM": "Left-arm pace", "LMF": "Left-arm pace", "LM": "Left-arm pace",
    "OB": "Off-spin", "LB": "Leg-spin", "LBG": "Leg-spin", "SLA": "Left-arm orthodox", "LWS": "Left-arm wrist spin",
}
FAMILY_ORDER = ["Right-arm pace", "Left-arm pace", "Off-spin", "Leg-spin", "Left-arm orthodox", "Left-arm wrist spin"]
NOT_BOWLER = {"run out", "retired hurt", "retired out", "retired not out (hurt)", "obstructing the field"}


def _q(db, fmt: str, **kw) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    kw.setdefault("limit", 10000)
    return run_deliveries_query(db, fmt=fmt, **kw)["data"]


def _n(v: Any) -> Optional[float]:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


# ---- batting ------------------------------------------------------------------------------------------------------

def start_curve(rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Rows of (match_id, innings, batter_ball_number, runs, balls, impact): by ball 1..30, the strike rate on that
    ball and so far (all innings' runs over their balls), the typical (median) innings' running Impact with a finished
    innings keeping its final total, and how many innings were still going."""
    innings: Dict[tuple, Dict[int, Dict[str, float]]] = {}
    for r in rows:
        n = r.get("batter_ball_number")
        if n is None or (r.get("balls") or 0) < 1:
            continue
        innings.setdefault((r["match_id"], r.get("innings")), {})[int(n)] = {
            "runs": _n(r.get("runs")) or 0.0, "impact": _n(r.get("impact")) or 0.0}
    if not innings:
        return None
    lists = [[b[k] for k in sorted(b)] for b in innings.values()]
    points, runs_cum, balls_cum = [], 0.0, 0
    for n in range(1, START_BALLS + 1):
        alive = [x for x in lists if len(x) >= n]
        if not alive:
            break
        on_ball = sum(x[n - 1]["runs"] for x in alive)
        runs_cum += on_ball
        balls_cum += len(alive)
        carried = [sum(b["impact"] for b in x[:min(n, len(x))]) for x in lists]
        points.append({"n": n, "alive": len(alive), "sr_ball": round(100 * on_ball / len(alive), 1),
                       "sr_cum": round(100 * runs_cum / balls_cum, 1), "par": round(statistics.median(carried), 1),
                       "ahead": round(100 * sum(1 for c in carried if c > 0) / len(carried))})
    return {"innings": len(lists), "points": points}


def batting_cards(db, fmt: str, player: str, base: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    who = dict(batters=[player], metrics_perspective="batting", **base)
    overall = _q(db, fmt, group_by=["batter"], **who)
    if not overall or (overall[0].get("balls") or 0) < ROLE_MIN_BALLS:
        return None
    me = overall[0]
    families: Dict[str, Dict[str, float]] = {}
    for r in _q(db, fmt, group_by=["bowl_style"], **who):
        fam = FAMILIES.get(r.get("bowl_style"))
        if fam:
            f = families.setdefault(fam, {"balls": 0, "runs": 0, "outs": 0})
            f["balls"] += r.get("balls") or 0
            f["runs"] += r.get("runs") or 0
            f["outs"] += r.get("wickets") or 0
    fam_rows = [{"family": k, **v, "strike_rate": round(100 * v["runs"] / v["balls"], 1)}
                for k, v in sorted(families.items(), key=lambda kv: FAMILY_ORDER.index(kv[0]))
                if v["balls"] >= FAMILY_MIN_BALLS]
    zones = [{"zone": int(r["wagon_zone"]), "runs": r.get("runs") or 0, "balls": r.get("balls") or 0,
              "strike_rate": _n(r.get("strike_rate"))}
             for r in _q(db, fmt, group_by=["wagon_zone"], **who) if r.get("wagon_zone") and 1 <= int(r["wagon_zone"]) <= 8]
    outs = [{"how": r["dismissal"], "count": r.get("wickets") or 0}
            for r in _q(db, fmt, group_by=["dismissal"], **who) if r.get("dismissal") and (r.get("wickets") or 0) > 0]
    start = None
    if fmt == "T20":  # runs v par need the T20 Primer's per-ball Impact
        start = start_curve(_q(db, fmt, group_by=["match_id", "innings", "batter_ball_number"], **who))
    return {
        "balls": me.get("balls"), "runs": me.get("runs"), "strike_rate": _n(me.get("strike_rate")),
        "start": start,
        "zones": zones,
        "families": fam_rows,
        "dismissals": sorted(outs, key=lambda r: -r["count"]),
    }


# ---- bowling ------------------------------------------------------------------------------------------------------

def _econ(r: Dict[str, Any]) -> Optional[float]:
    return 6 * r["runs"] / r["balls"] if r.get("balls") else None


def bowling_cards(db, fmt: str, player: str, base: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    who = dict(bowlers=[player], metrics_perspective="bowling", **base)
    overall = _q(db, fmt, group_by=["bowler"], **who)
    if not overall or (overall[0].get("balls") or 0) < ROLE_MIN_BALLS:
        return None
    me = overall[0]
    cells = [{"line": r["line"], "length": r["length"], "balls": r.get("balls") or 0, "runs": r.get("runs") or 0,
              "economy": round(_econ(r), 2), "wickets": r.get("wickets") or 0}
             for r in _q(db, fmt, group_by=["line", "length"], **who)
             if r.get("line") and r.get("length") and (r.get("balls") or 0) >= CELL_MIN_BALLS]

    def false_shots(r):
        ctl, cov = _n(r.get("control_percentage")), _n(r.get("control_coverage_pct"))
        return round(100 - ctl, 1) if ctl is not None and (cov or 0) >= 80 else None

    phases = [{"phase": r["phase"], "balls": r.get("balls") or 0, "economy": round(_econ(r), 2),
               "dot_percentage": _n(r.get("dot_percentage")), "false_shots": false_shots(r), "wickets": r.get("wickets") or 0}
              for r in _q(db, fmt, group_by=["phase"], **who) if r.get("phase") and r.get("balls")]
    hands = [{"hand": r["bat_hand"], "balls": r.get("balls") or 0, "economy": round(_econ(r), 2),
              "dot_percentage": _n(r.get("dot_percentage")), "wickets": r.get("wickets") or 0}
             for r in _q(db, fmt, group_by=["bat_hand"], **who) if r.get("bat_hand") in ("RHB", "LHB") and r.get("balls")]
    wkts = [{"how": r["dismissal"], "count": r.get("wickets") or 0}
            for r in _q(db, fmt, group_by=["dismissal"], **who)
            if r.get("dismissal") and r["dismissal"] not in NOT_BOWLER and (r.get("wickets") or 0) > 0]
    return {
        "balls": me.get("balls"), "economy": round(_econ(me), 2),
        "cells": cells,
        "phases": sorted(phases, key=lambda r: ["powerplay", "middle", "death"].index(r["phase"])
                         if r["phase"] in ("powerplay", "middle", "death") else 9),
        "hands": hands,
        "wickets": sorted(wkts, key=lambda r: -r["count"]),
    }


# ---- the call -----------------------------------------------------------------------------------------------------

def build_cards(db, player: str, fmt: str = "T20", scope: str = "strong", start_date: Optional[date] = None,
                end_date: Optional[date] = None, period: str = "recent") -> Dict[str, Any]:
    start, end = default_window(fmt, period=period)
    window = {"start_date": start_date or start, "end_date": end_date or end}
    base = {**window, **scope_params(fmt, scope)}
    roles = {"bat": batting_cards(db, fmt, player, base), "bowl": bowling_cards(db, fmt, player, base)}
    return {"player": player, "format": fmt, "scope": scope, "period": period,
            "window": {k: v.isoformat() for k, v in window.items()}, "version": CARDS_VERSION,
            "roles": {k: v for k, v in roles.items() if v}}


# One build at a time per web process, as with the summary (services/player_verdict.py): each is a handful of
# queries, and several at once starved the database pool on 29 Oct 2026.
_SLOT = threading.BoundedSemaphore(1)
WAIT_SECONDS = 20


class CardsBusy(RuntimeError):
    pass


def get_cards(db, player: str, fmt: str = "T20", scope: str = "strong", start_date: Optional[date] = None,
              end_date: Optional[date] = None, period: str = "recent") -> Dict[str, Any]:
    from services.query_cache import cached_get

    key = {"kind": "player_cards", "v": CARDS_VERSION, "player": player.strip().lower(), "fmt": fmt, "scope": scope,
           "start_date": start_date, "end_date": end_date, "period": period}
    if end_date is None:
        key["day"] = date.today()
    hit = cached_get(db, key)
    if hit is not None:
        return hit
    db.rollback()  # give the connection back before waiting
    if not _SLOT.acquire(timeout=WAIT_SECONDS):
        raise CardsBusy("another player's cards are being built")
    try:
        return cached_run(db, key, lambda: build_cards(db, player, fmt, scope, start_date, end_date, period))
    finally:
        _SLOT.release()
