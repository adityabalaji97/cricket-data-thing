"""
Batter v bowler for the Compare page: every ball between two players, with pictures and context.

* the head-to-head numbers, Impact, runs above par and wins added (T20; ODIs have no par);
* each player's usual against the other's type, so the head-to-head reads against something: the batter against
  that kind of bowling (pace or spin), the bowler against that hand of batter;
* where the bowler pitched it to him (line and length), where he scored off him (wagon zones), how he got out, and
  year by year.
Eight grouped queries, too slow for one request cold (Heroku cuts at 30 s), so it builds in the background like the
venue and team pages (services/page_builds) and is cached for the day.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from services.page_builds import get_or_build
from services.player_verdict import _num, _query

MATCHUP_VERSION = "m1"
START = date(2005, 1, 1)
KIND_WORDS = {"pace bowler": "pace", "spin bowler": "spin"}
HAND_WORDS = {"RHB": "right-handers", "LHB": "left-handers"}
HOW = {"lbw": "LBW", "leg before wicket": "LBW", "caught and bowled": "Caught and bowled", "hit wicket": "Hit wicket"}


def _false_shots(row: Dict[str, Any]) -> Optional[float]:
    c = _num(row.get("control_percentage"))
    return None if c is None else round(100 - c, 1)


def _line(row: Dict[str, Any]) -> Dict[str, Any]:
    balls = row.get("balls") or 0
    runs = row.get("runs") or 0
    return {
        "balls": balls, "runs": runs, "wickets": row.get("wickets") or 0, "innings": row.get("innings_count"),
        "strike_rate": _num(row.get("strike_rate")), "economy": round(runs * 6 / balls, 2) if balls else None,
        "dot_percentage": _num(row.get("dot_percentage")), "boundary_percentage": _num(row.get("boundary_percentage")),
        "false_shot_percentage": _false_shots(row), "balls_per_dismissal": _num(row.get("balls_per_dismissal")),
        "fours": row.get("fours"), "sixes": row.get("sixes"),
        "impact": _num(row.get("impact")), "raa": _num(row.get("raa")), "raa_per_100": _num(row.get("raa_per_100")),
        "wpa": _num(row.get("wpa")),
    }


def _biggest(rows: List[Dict[str, Any]], key: str) -> Optional[str]:
    rows = [r for r in rows if r.get(key)]
    return max(rows, key=lambda r: r.get("balls") or 0)[key] if rows else None


def build_matchup(db, batter: str, bowler: str, fmt: str = "T20") -> Dict[str, Any]:
    end = date.today()
    pair = dict(batters=[batter], bowlers=[bowler], start_date=START, end_date=end, metrics_perspective="batting")
    overall = _query(db, fmt, group_by=["batter", "bowler"], **pair)
    if not overall:
        return {"batter": batter, "bowler": bowler, "format": fmt, "balls": 0}
    me = max(overall, key=lambda r: r.get("balls") or 0)
    names = {"batter": me.get("batter") or batter, "bowler": me.get("bowler") or bowler}

    types = _query(db, fmt, group_by=["bowl_kind", "bat_hand"], **pair)
    kind, hand = _biggest(types, "bowl_kind"), _biggest(types, "bat_hand")

    cells = [{"line": r["line"], "length": r["length"], "balls": r.get("balls") or 0, "runs": r.get("runs") or 0,
              "wickets": r.get("wickets") or 0, "strike_rate": _num(r.get("strike_rate"))}
             for r in _query(db, fmt, group_by=["line", "length"], **pair) if r.get("line") and r.get("length")]
    zones = [{"zone": int(r["wagon_zone"]), "runs": r.get("runs") or 0, "balls": r.get("balls") or 0,
              "strike_rate": _num(r.get("strike_rate")) or 0}
             for r in _query(db, fmt, group_by=["wagon_zone"], **pair)
             if r.get("wagon_zone") is not None and 1 <= int(r["wagon_zone"]) <= 8]
    how: Dict[str, int] = {}
    for r in _query(db, fmt, group_by=["dismissal"], **pair):
        if r.get("dismissal") and r.get("wickets"):
            name = HOW.get(r["dismissal"].lower(), r["dismissal"].capitalize())
            how[name] = how.get(name, 0) + r["wickets"]
    outs = [{"how": k, "count": v} for k, v in sorted(how.items(), key=lambda kv: -kv[1])]
    years = sorted(({"year": r["year"], "balls": r.get("balls") or 0, "runs": r.get("runs") or 0,
                     "wickets": r.get("wickets") or 0, "strike_rate": _num(r.get("strike_rate"))}
                    for r in _query(db, fmt, group_by=["year"], **pair) if r.get("year")), key=lambda r: r["year"])

    # Their usual, against the other's type, over the same years: what the head-to-head is read against.
    first, last = (years[0]["year"], years[-1]["year"]) if years else (START.year, end.year)
    span = dict(start_date=date(first, 1, 1), end_date=end)
    bat_usual = bowl_usual = None
    if kind:
        rows = _query(db, fmt, group_by=["batter"], batters=[batter], bowl_kind=[kind], metrics_perspective="batting", **span)
        if rows:
            bat_usual = {"against": KIND_WORDS.get(kind, kind), **_line(max(rows, key=lambda r: r.get("balls") or 0))}
    if hand:
        rows = _query(db, fmt, group_by=["bowler"], bowlers=[bowler], bat_hand=hand, metrics_perspective="batting", **span)
        if rows:
            # Runs, dots and false shots off his bowling; Impact and par are the batters' side, so they're left off.
            line = _line(max(rows, key=lambda r: r.get("balls") or 0))
            bowl_usual = {"against": HAND_WORDS.get(hand, hand),
                          **{k: v for k, v in line.items() if k not in ("impact", "raa", "raa_per_100", "wpa")}}

    return {
        **names, "format": fmt, "hand": hand, "bowl_kind": kind, "since": first, "until": last,
        "balls": me.get("balls") or 0, "overall": _line(me), "batter_usual": bat_usual, "bowler_usual": bowl_usual,
        "cells": cells, "zones": zones, "dismissals": outs, "years": years, "version": MATCHUP_VERSION,
    }


def get_matchup(db, batter: str, bowler: str, fmt: str = "T20", wait: bool = False) -> Dict[str, Any]:
    key = {"kind": "matchup", "v": MATCHUP_VERSION, "batter": batter.strip().lower(), "bowler": bowler.strip().lower(),
           "fmt": fmt, "day": date.today()}
    return get_or_build(db, key, lambda s: build_matchup(s, batter, bowler, fmt), wait=wait)
