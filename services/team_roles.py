"""
Every player's job in every team-season of a league (TEAM_TEMPLATE_PLAN.md, T1).

A job is usage, not reputation: where he batted and in which phase he faced his balls; when he bowled and whether pace or
spin; and what share of the side's balls that was. Value is the T20 Primer's (runs above par, Impact, wins added; 2015 on)
alongside the stable rates (strike rate, economy, dot %, false shots). One season at a time, the window being the season's
own dates from the ledger (services/season_ledger.py), so a league that runs across New Year works the same as the IPL.

Familiar labels (the display vocabulary):
  batting  - openers (1-2), top order (3-4), middle and finishers (5-7), lower order (8+), by his most common position;
  bowling  - phase x kind slots (powerplay pace, middle-overs spin...), every ball counted in its own slot.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from services.season_ledger import ledger, team_key

BAT_SLOTS = [("openers", 1, 2), ("top", 3, 4), ("middle", 5, 7), ("lower", 8, 11)]
PHASES = ["powerplay", "middle", "death"]
KINDS = {"pace bowler": "pace", "spin bowler": "spin"}


def bat_slot(position: int) -> str:
    return next((name for name, lo, hi in BAT_SLOTS if lo <= position <= hi), "lower")


def _q(db, league: str, start, end, **kw) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    rows = run_deliveries_query(db, fmt="T20", include_international=False, leagues=[league], start_date=start,
                                end_date=end, limit=10000, **kw)["data"]
    assert len(rows) < 10000, "page the query: a season returned 10,000 rows"
    return rows


def season_roles(db, league: str, season: Dict[str, Any]) -> Dict[str, Any]:
    """One season: per team, per player, his batting by position and phase and his bowling by phase and kind."""
    start, end = season["start"], season["end"]
    players: Dict[tuple, Dict[str, Any]] = defaultdict(lambda: {"bat": {}, "bat_phase": {}, "bowl": {}})
    for r in _q(db, league, start, end, group_by=["batting_team", "batter", "batting_position"], metrics_perspective="batting"):
        if not r.get("batter") or not r.get("batting_position"):
            continue
        p = players[(team_key(r["batting_team"]), r["batter"])]
        p["bat"][int(r["batting_position"])] = _bat_row(r)
    for r in _q(db, league, start, end, group_by=["batting_team", "batter", "phase"], metrics_perspective="batting"):
        if r.get("batter") and r.get("phase"):
            players[(team_key(r["batting_team"]), r["batter"])]["bat_phase"][r["phase"]] = _bat_row(r)
    for r in _q(db, league, start, end, group_by=["bowling_team", "bowler", "phase", "bowl_kind"], metrics_perspective="bowling"):
        if not r.get("bowler") or not r.get("phase"):
            continue
        kind = KINDS.get(r.get("bowl_kind"), "unknown")
        players[(team_key(r["bowling_team"]), r["bowler"])]["bowl"][f"{r['phase']}|{kind}"] = _bowl_row(r)
    teams: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for (team, name), p in players.items():
        teams[team].append({"name": name, **p})
    return {"season": season["season"], "teams": dict(teams)}


def _bat_row(r: Dict[str, Any]) -> Dict[str, Any]:
    return {k: r.get(k) for k in ("balls", "runs", "wickets", "innings_count", "dots", "boundaries", "control_percentage",
                                  "control_tagged", "raa", "impact", "wpa")}


def _bowl_row(r: Dict[str, Any]) -> Dict[str, Any]:
    return {k: r.get(k) for k in ("balls", "runs", "wickets", "innings_count", "dots", "boundaries", "control_percentage",
                                  "control_tagged", "raa", "impact", "wpa")}


def league_roles(db, league: str) -> Dict[str, Any]:
    """Every season of a league, with its ledger entry (playoff sides, champion) alongside."""
    out = []
    for s in ledger(db, league):
        out.append({**{k: v for k, v in s.items() if k not in ("table",)}, "table": s["table"], **season_roles(db, league, s)})
    return {"league": league, "seasons": out}
