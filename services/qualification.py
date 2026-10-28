"""Who qualifies for a peer pool: a minimum ball count that follows the period, not a fixed number.

The user's rule (2026-10-27, DOPPELGANGER_PLAN.md and VERDICT_SCREEN_PLAN.md V2b): take the role's players in the
period with at least REGULAR_MIN_INNINGS innings (its regulars); the floor is FLOOR_SHARE of their median balls,
never below NOISE_FLOOR. So the floor rises and falls with how much cricket there was: 2015, with fewer leagues,
asks for fewer balls than 2025. Shared by the verdict screen's peer strips and the statistical twins.
"""
from __future__ import annotations

from statistics import median
from typing import Any, Dict, Iterable

REGULAR_MIN_INNINGS = 5
FLOOR_SHARE = 0.4
NOISE_FLOOR = 120  # percentiles from a few dozen balls are luck


def min_balls(rows: Iterable[Dict[str, Any]], balls_key: str = "balls",
              innings_key: str = "innings_count") -> Dict[str, Any]:
    """{"min_balls", "median_balls", "regulars"} for one role's rows (one per player) in one period."""
    regulars = [r.get(balls_key) or 0 for r in rows if (r.get(innings_key) or 0) >= REGULAR_MIN_INNINGS]
    regulars = [b for b in regulars if b > 0]
    if not regulars:
        return {"min_balls": NOISE_FLOOR, "median_balls": None, "regulars": 0}
    mid = median(regulars)
    return {"min_balls": max(NOISE_FLOOR, int(round(FLOOR_SHARE * mid))), "median_balls": int(round(mid)),
            "regulars": len(regulars)}


def qualifying_players(rows: Iterable[Dict[str, Any]], name_key: str, year_key: str = "year",
                       seasons_needed: int = 2) -> Dict[str, Any]:
    """Players who clear their season's floor in at least `seasons_needed` seasons of a multi-season window (or in
    every season, when the window has fewer). One floor across a three-season window landed on the noise floor and
    let part-timers in; per season, a player has to be a regular more than once (the user, 2026-10-28).

    rows: one per player per season, with balls and innings_count."""
    by_year: Dict[Any, list] = {}
    for r in rows:
        by_year.setdefault(r.get(year_key), []).append(r)
    floors = {y: min_balls(rs) for y, rs in by_year.items()}
    need = min(seasons_needed, len(floors)) or 1
    cleared: Dict[str, int] = {}
    for y, rs in by_year.items():
        floor = floors[y]["min_balls"]
        for r in rs:
            if (r.get("balls") or 0) >= floor:
                cleared[r.get(name_key)] = cleared.get(r.get(name_key), 0) + 1
    return {
        "players": {n for n, c in cleared.items() if c >= need},
        "floors": {str(y): f["min_balls"] for y, f in sorted(floors.items(), key=lambda kv: str(kv[0]))},
        "seasons_needed": need,
    }
