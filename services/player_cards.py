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
from services.wicket_style import wicket_style

CARDS_VERSION = "c4"  # c2: the scouting cards (PROFILE_SCOUTING_PLAN.md); c3: catches on the wheels; c4: wicket style
START_BALLS = 30          # the start card runs to the 30th ball of an innings
FAMILY_MIN_BALLS = 40     # a bowling family with fewer balls is left off
CELL_MIN_BALLS = 15       # a pitch-map cell with fewer balls is left blank
FAMILIES = {
    "RF": "Right-arm pace", "RFM": "Right-arm pace", "RMF": "Right-arm pace", "RM": "Right-arm pace",
    "LF": "Left-arm pace", "LFM": "Left-arm pace", "LMF": "Left-arm pace", "LM": "Left-arm pace",
    "OB": "Off-spin", "LB": "Leg-spin", "LBG": "Leg-spin", "SLA": "Left-arm orthodox", "LWS": "Left-arm wrist spin",
}
FAMILY_ORDER = ["Right-arm pace", "Left-arm pace", "Off-spin", "Leg-spin", "Left-arm orthodox", "Left-arm wrist spin"]
SHOT_FAMILY_MIN = 30     # a shot family with fewer balls (against a bowler) is left off
PACE_CELL_MIN = 20       # the batter's pitch map against pace
NOT_SCORING = {"LEAVE", "DEFENCE"}
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
    sr = _n(me.get("strike_rate")) or 0
    for f in fam_rows:  # against his own: "−36% v his 145"
        f["vs_own"] = round(100 * (f["strike_rate"] / sr - 1), 1) if sr else None
    return {
        "balls": me.get("balls"), "runs": me.get("runs"), "strike_rate": sr,
        "start": start,
        "zones": zones,
        "families": fam_rows,
        "dismissals": sorted(outs, key=lambda r: -r["count"]),
        **scouting_batting(db, fmt, who, base),
    }


# ---- scouting (PROFILE_SCOUTING_PLAN.md) ---------------------------------------------------------------------------

PACE = {"bowl_kind": ["pace bowler"]}
PACE_SHORT_OF_FULL = {"bowl_kind": ["pace bowler"], "length": ["GOOD_LENGTH", "SHORT_OF_A_GOOD_LENGTH"]}
LEG_SQUARE = {"RHB": (1, 2, 3), "LHB": (7, 6, 5)}  # fine leg, square leg, midwicket (wagon zones are the field's, not the batter's)


def _boundary_shares(rows: List[Dict[str, Any]]) -> Dict[int, float]:
    got = {int(r["wagon_zone"]): 4 * (r.get("fours") or 0) + 6 * (r.get("sixes") or 0)
           for r in rows if r.get("wagon_zone") is not None and 1 <= int(r["wagon_zone"]) <= 8}
    t = sum(got.values())
    return {z: 100 * v / t for z, v in got.items()} if t else {}


def _family_run_shares(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    got = {r["shot_family"]: r.get("runs") or 0 for r in rows if r.get("shot_family")}
    t = sum(got.values())
    return {k: 100 * v / t for k, v in got.items()} if t else {}


def _average_batter(db, fmt: str, base: Dict[str, Any], hand: str) -> Dict[str, Any]:
    """The average batter of a hand in the window and scope: where his boundaries go against pace short of full, and
    his share of runs by shot. Cached once and shared by every profile with that window."""
    def run():
        common = dict(bat_hand=hand, metrics_perspective="batting", **base)
        return {"boundary": _boundary_shares(_q(db, fmt, group_by=["wagon_zone"], **PACE_SHORT_OF_FULL, **common)),
                "shots": _family_run_shares(_q(db, fmt, group_by=["shot_family"], **common))}

    key = {"kind": "scout_average_batter", "v": CARDS_VERSION, "fmt": fmt, "hand": hand,
           **{k: v for k, v in base.items()}}
    out = cached_run(db, key, run)
    # JSON round-trips turn zone keys into strings.
    return {"boundary": {int(k): v for k, v in out["boundary"].items()}, "shots": out["shots"]}


def scouting_batting(db, fmt: str, who: Dict[str, Any], base: Dict[str, Any]) -> Dict[str, Any]:
    """How to bowl to him: pace by line and length against his strike rate against pace; where his boundaries go
    against pace short of full, against the average batter of his hand (and the fielder who matters); his scoring shots
    against the same average."""
    hands = _q(db, fmt, group_by=["bat_hand"], **who)
    hand = max(hands, key=lambda r: r.get("balls") or 0)["bat_hand"] if hands else "RHB"
    hand = hand if hand in ("RHB", "LHB") else "RHB"
    pace_me = _q(db, fmt, group_by=["batter"], **PACE, **who)
    pace_sr = _n(pace_me[0].get("strike_rate")) if pace_me else None
    pace_cells = []
    if pace_sr:
        pace_cells = [{"line": r["line"], "length": r["length"], "balls": r.get("balls") or 0,
                       "strike_rate": round(_n(r.get("strike_rate")) or 0, 1), "outs": r.get("wickets") or 0}
                      for r in _q(db, fmt, group_by=["line", "length"], **PACE, **who)
                      if r.get("line") and r.get("length") and (r.get("balls") or 0) >= PACE_CELL_MIN]
    avg = _average_batter(db, fmt, base, hand)
    zone_rows = _q(db, fmt, group_by=["wagon_zone"], **PACE_SHORT_OF_FULL, **who)
    mine = _boundary_shares(zone_rows)
    boundary_runs = sum(4 * (r.get("fours") or 0) + 6 * (r.get("sixes") or 0) for r in zone_rows)
    boundary = None
    if mine and boundary_runs >= 60:
        key_zone = max(mine, key=mine.get)
        boundary = {"leg_square": round(sum(mine.get(z, 0) for z in LEG_SQUARE[hand])),
                    "leg_square_avg": round(sum(avg["boundary"].get(z, 0) for z in LEG_SQUARE[hand])),
                    "key_zone": key_zone, "key_share": round(mine[key_zone]), "runs": boundary_runs}
    shot_rows = _q(db, fmt, group_by=["shot_family"], **who)
    shares = _family_run_shares(shot_rows)
    tagged = sum(r.get("runs") or 0 for r in shot_rows if r.get("shot_family"))
    shots = None
    if shares and tagged >= 150:
        top = sorted((k for k in shares if k not in NOT_SCORING), key=lambda k: -shares[k])[:6]
        shots = {"rows": [{"family": k, "share": round(shares[k], 1), "average": round(avg["shots"].get(k, 0), 1)} for k in top],
                 "runs": tagged}
    return {"hand": hand, "pace_sr": pace_sr, "pace_cells": pace_cells, "boundary": boundary, "shot_mix": shots,
            "catches": catch_points(db, fmt, who)}


def catch_points(db, fmt: str, who: Dict[str, Any], by_hand: bool = False):
    """Where the catches were taken, on the feed's grid (a fixed view of the ground, as the scoring wheel draws it), and
    how many catches there were in all: about half carry a position (58% in 2022, 43% in 2025-26). by_hand: per batter's
    hand, for a bowler (his wheel has a right-/left-hander switch)."""
    group = (["bat_hand"] if by_hand else []) + ["wagon_x", "wagon_y"]
    rows = _q(db, fmt, group_by=group, dismissal=["caught"], **who)

    def pack(rs):
        pts = [{"x": int(r["wagon_x"]), "y": int(r["wagon_y"]), "n": int(r.get("wickets") or 0)}
               for r in rs if r.get("wagon_x") is not None and (r.get("wickets") or 0) > 0
               and not (int(r["wagon_x"]) == 0 and int(r["wagon_y"]) == 0)]
        total = sum(int(r.get("wickets") or 0) for r in rs)
        return {"points": pts, "plotted": sum(p["n"] for p in pts), "total": total}

    if not by_hand:
        return pack(rows)
    return {h: pack([r for r in rows if r.get("bat_hand") == h]) for h in ("RHB", "LHB")}


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
    # What works against him: batters' strike rate with each shot, against their strike rate off him, with the cost.
    sr_off = 100 * (me.get("runs") or 0) / me["balls"]
    shots_against = [{"family": r["shot_family"], "balls": r.get("balls") or 0, "runs": r.get("runs") or 0,
                      "wickets": r.get("wickets") or 0, "strike_rate": round(100 * (r.get("runs") or 0) / r["balls"], 1),
                      "vs_all": round(100 * (r.get("runs") or 0) / r["balls"] - sr_off, 1)}
                     for r in _q(db, fmt, group_by=["shot_family"], **who)
                     if r.get("shot_family") and r["shot_family"] not in NOT_SCORING and (r.get("balls") or 0) >= SHOT_FAMILY_MIN]
    # Where batters score off him, by their hand (his wheel has a switch), with his catches on it.
    zones_by_hand = {}
    for h in ("RHB", "LHB"):
        zr = [{"zone": int(r["wagon_zone"]), "runs": r.get("runs") or 0, "balls": r.get("balls") or 0,
               "strike_rate": _n(r.get("strike_rate"))}
              for r in _q(db, fmt, group_by=["wagon_zone"], bat_hand=h, **who)
              if r.get("wagon_zone") and 1 <= int(r["wagon_zone"]) <= 8]
        hb = sum(z["balls"] for z in zr)
        if hb >= 120:
            zones_by_hand[h] = {"zones": zr, "strike_rate": round(100 * sum(z["runs"] for z in zr) / hb, 1) if hb else None}
    return {
        "balls": me.get("balls"), "economy": round(_econ(me), 2),
        "strike_rate_against": round(sr_off, 1),
        "zones_by_hand": zones_by_hand,
        "catches_by_hand": catch_points(db, fmt, who, by_hand=True),
        "shots_against": sorted(shots_against, key=lambda r: -r["vs_all"]),
        "cells": cells,
        "phases": sorted(phases, key=lambda r: ["powerplay", "middle", "death"].index(r["phase"])
                         if r["phase"] in ("powerplay", "middle", "death") else 9),
        "hands": hands,
        "wickets": sorted(wkts, key=lambda r: -r["count"]),
        "wicket_style": wicket_style(db, fmt, player, base),
    }


# ---- the wheel's own filters (the gear on "Where he scores" / "Where batters score off him") ------------------------

KIND_CODES = {"pace": ["pace bowler"], "spin": ["spin bowler"]}


def _filters(fmt: str, phase: Optional[str], kind: Optional[str], family: Optional[str], hand: Optional[str]) -> Dict[str, Any]:
    """A card's own filters as query-builder arguments: a phase, pace or spin (or one bowling family), the batter's hand."""
    from services.analytics_common import phase_bounds

    f: Dict[str, Any] = {}
    if phase:
        ph = next((p for p in phase_bounds(fmt, "male") if p.key == phase), None)
        if ph:
            f["over_min"] = ph.start_over
            if ph.end_over is not None:
                f["over_max"] = ph.end_over
    if family:
        f["bowl_style"] = [code for code, fam in FAMILIES.items() if fam == family]
    elif kind in KIND_CODES:
        f["bowl_kind"] = KIND_CODES[kind]
    if hand in ("RHB", "LHB"):
        f["bat_hand"] = hand
    return f


def card_slice(db, player: str, card: str, fmt: str = "T20", scope: str = "strong", period: str = "recent",
               start_date: Optional[date] = None, end_date: Optional[date] = None, phase: Optional[str] = None,
               kind: Optional[str] = None, family: Optional[str] = None, hand: Optional[str] = None) -> Dict[str, Any]:
    """One profile card's numbers under the card's own filter (the sliders icon), in the page's window and scope:
    wheel_bat / wheel_bowl (zones and catches), pace_map, shot_mix (and the average batter under the same filter),
    pitch (the bowler's line and length), shots_against, wickets (services/wicket_style.py). Cached per card and filter."""
    def run():
        start, end = default_window(fmt, period=period)
        base = {"start_date": start_date or start, "end_date": end_date or end, **scope_params(fmt, scope)}
        flt = _filters(fmt, phase, kind, family, hand)
        bat = dict(metrics_perspective="batting", **base, **flt)
        if card in ("wheel_bat", "wheel_bowl"):
            who = {"batters": [player]} if card == "wheel_bat" else {"bowlers": [player], "metrics_perspective": "bowling"}
            q = {**bat, **who}
            zr = [{"zone": int(r["wagon_zone"]), "runs": r.get("runs") or 0, "balls": r.get("balls") or 0,
                   "strike_rate": _n(r.get("strike_rate"))}
                  for r in _q(db, fmt, group_by=["wagon_zone"], **q) if r.get("wagon_zone") and 1 <= int(r["wagon_zone"]) <= 8]
            balls = sum(z["balls"] for z in zr)
            return {"zones": zr, "balls": balls, "strike_rate": round(100 * sum(z["runs"] for z in zr) / balls, 1) if balls else None,
                    "catches": catch_points(db, fmt, q)}
        if card == "pace_map":
            q = {**bat, "batters": [player], **PACE}
            me = _q(db, fmt, group_by=["batter"], **q)
            pace_sr = _n(me[0].get("strike_rate")) if me else None
            cells = [{"line": r["line"], "length": r["length"], "balls": r.get("balls") or 0,
                      "strike_rate": round(_n(r.get("strike_rate")) or 0, 1), "outs": r.get("wickets") or 0}
                     for r in _q(db, fmt, group_by=["line", "length"], **q)
                     if r.get("line") and r.get("length") and (r.get("balls") or 0) >= PACE_CELL_MIN] if pace_sr else []
            return {"pace_sr": pace_sr, "pace_cells": cells, "balls": (me[0].get("balls") if me else 0)}
        if card == "shot_mix":
            rows = _q(db, fmt, group_by=["shot_family"], batters=[player], **bat)
            shares = _family_run_shares(rows)
            tagged = sum(r.get("runs") or 0 for r in rows if r.get("shot_family"))
            hands = _q(db, fmt, group_by=["bat_hand"], batters=[player], metrics_perspective="batting", **base)
            h = max(hands, key=lambda r: r.get("balls") or 0)["bat_hand"] if hands else "RHB"
            avg = _family_run_shares(_q(db, fmt, group_by=["shot_family"], **{**bat, "bat_hand": h}))
            if not shares or tagged < 60:
                return {"shot_mix": None, "balls": sum(r.get("balls") or 0 for r in rows)}
            top = sorted((k for k in shares if k not in NOT_SCORING), key=lambda k: -shares[k])[:6]
            return {"shot_mix": {"rows": [{"family": k, "share": round(shares[k], 1), "average": round(avg.get(k, 0), 1)} for k in top],
                                 "runs": tagged}, "balls": sum(r.get("balls") or 0 for r in rows)}
        bowl = dict(bowlers=[player], metrics_perspective="bowling", **base, **flt)
        if card == "pitch":
            me = _q(db, fmt, group_by=["bowler"], **bowl)
            if not me:
                return {"cells": [], "economy": None, "balls": 0}
            cells = [{"line": r["line"], "length": r["length"], "balls": r.get("balls") or 0, "runs": r.get("runs") or 0,
                      "economy": round(_econ(r), 2), "wickets": r.get("wickets") or 0}
                     for r in _q(db, fmt, group_by=["line", "length"], **bowl)
                     if r.get("line") and r.get("length") and (r.get("balls") or 0) >= CELL_MIN_BALLS]
            return {"cells": cells, "economy": round(_econ(me[0]), 2), "balls": me[0].get("balls")}
        if card == "shots_against":
            me = _q(db, fmt, group_by=["bowler"], **bowl)
            if not me or not me[0].get("balls"):
                return {"shots_against": [], "strike_rate_against": None, "balls": 0}
            sr_off = 100 * (me[0].get("runs") or 0) / me[0]["balls"]
            rows = [{"family": r["shot_family"], "balls": r.get("balls") or 0, "runs": r.get("runs") or 0,
                     "wickets": r.get("wickets") or 0, "strike_rate": round(100 * (r.get("runs") or 0) / r["balls"], 1),
                     "vs_all": round(100 * (r.get("runs") or 0) / r["balls"] - sr_off, 1)}
                    for r in _q(db, fmt, group_by=["shot_family"], **bowl)
                    if r.get("shot_family") and r["shot_family"] not in NOT_SCORING and (r.get("balls") or 0) >= SHOT_FAMILY_MIN]
            return {"shots_against": sorted(rows, key=lambda r: -r["vs_all"]), "strike_rate_against": round(sr_off, 1),
                    "balls": me[0]["balls"]}
        if card == "wickets":
            return {"wicket_style": wicket_style(db, fmt, player, base, flt)}
        raise ValueError(f"unknown card {card!r}")

    key = {"kind": "player_card_slice", "v": CARDS_VERSION, "player": player.strip().lower(), "card": card, "fmt": fmt,
           "scope": scope, "period": period, "start_date": start_date, "end_date": end_date, "phase": phase,
           "bowl": family or kind, "hand": hand}
    if end_date is None:
        key["day"] = date.today()
    return cached_run(db, key, run)


def wheel(db, player: str, role: str, fmt: str = "T20", scope: str = "strong", period: str = "recent",
          start_date: Optional[date] = None, end_date: Optional[date] = None, phase: Optional[str] = None,
          kind: Optional[str] = None, family: Optional[str] = None, hand: Optional[str] = None) -> Dict[str, Any]:
    """The wheel cards' filter (kept for the /wheel route): card_slice's wheel_bat / wheel_bowl."""
    return card_slice(db, player, "wheel_bat" if role == "bat" else "wheel_bowl", fmt, scope, period, start_date,
                      end_date, phase, kind, family, hand)


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
