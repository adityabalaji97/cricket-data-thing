"""
A squad against the winners' template (TEAM_TEMPLATE_PLAN.md, T4).

Each graded role is filled by the squad's busiest players in it, on their league record over the recent window at any
side (Sanju Samson's opening counts wherever he opened). Their pooled number is then placed among the league's
team-seasons of the template era, the role's value for a team-season worked out the same way (its busiest players in
the role that season), so a squad's best two openers are set against other sides' best two, not their whole rotation.

Each role is marked against the template: at playoff sides' level, short (between the rest and playoff sides), or a gap
(below the rest). Roles are weighted by how consistently they separated playoff sides across every season
(services/team_template.py), so the overall fit leans on what reliably matters.
"""
from __future__ import annotations

import statistics
from datetime import date
from typing import Any, Dict, List, Optional

from services.team_roles import bat_slot

#: The graded roles: (key, display, side, slot, measure, holders, lower_is_better, template feature for the weight).
ROLES = [
    ("openers", "Openers", "bat", "openers", "average", 2, False, "bat:openers:average"),
    ("top", "Top order (3-4)", "bat", "top", "strike_rate", 3, False, "bat:top:strike_rate"),  # 3: sides rotate it
    ("finishers", "Middle & finishers (5-7)", "bat", "middle", "strike_rate", 3, False, "bat:middle:strike_rate"),
    ("pp_pace", "Powerplay pace", "bowl", "powerplay|pace", "wickets_per_24", 2, False, "bowl:powerplay|pace:wickets_per_24"),
    ("mid_spin", "Middle-overs spin", "bowl", "middle|spin", "wickets_per_24", 2, False, "bowl:middle|spin:wickets_per_24"),
    ("death_pace", "Death pace", "bowl", "death|pace", "economy", 2, True, "bowl:death|pace:economy"),
    ("depth", "Bowling depth", "depth", None, "regular_bowlers", None, False, "structure:regular_bowlers"),
]
UNITS = {"average": "average", "strike_rate": "strike rate", "wickets_per_24": "wickets per 4 overs",
         "economy": "an over", "regular_bowlers": "regular bowlers"}
SEASON_MIN, SQUAD_MIN = 30, 60          # balls in the role for a holder: in a season / over the squad's window
REGULAR_SEASON = 120  # balls bowled in a season to count as a regular bowler (a squad's: in any one season of its window)


def _slot_rows(p: Dict[str, Any], side: str, slot: str) -> Dict[str, float]:
    if side == "bat":
        rows = [r for pos, r in p["bat"].items() if bat_slot(int(pos)) == slot]
    else:
        rows = [r for s, r in p["bowl"].items() if s == slot]
    return {k: sum((r.get(k) or 0) for r in rows) for k in ("balls", "runs", "wickets", "dots", "boundaries")}


#: Recency when choosing who holds a role: each season counts twice the one before it.
RECENCY = {2026: 4, 2025: 2, 2024: 1}


def _weight(p: Dict[str, Any], side: str, slot: str) -> float:
    """How much of a role a player has, recent seasons counting more (`w_bat` / `w_bowl` when the squad's per-season
    record was read; a single season's balls otherwise)."""
    w = p.get("w_bat" if side == "bat" else "w_bowl")
    return w.get(slot, 0.0) if w is not None else _slot_rows(p, side, slot)["balls"]


def main_bat_slot(p: Dict[str, Any]) -> Optional[str]:
    """A batter's one batting role: the slot he has most of (recent seasons counting more)."""
    slots = {s: _weight(p, "bat", s) for s in ("openers", "top", "middle", "lower")}
    best = max(slots, key=slots.get)
    return best if slots[best] > 0 else None


def role_value(players: List[Dict[str, Any]], role, min_balls: int):
    """The role's pooled number from its holders, and who they are. None when nobody qualifies.

    Holders: batters whose main batting role this is (one each: Samson is an opener, not also a 3-4), bowlers with the
    phase-and-kind slot (a bowler can hold several); ranked by recent usage, with min_balls of it in all."""
    key, _, side, slot, measure, n, _, _ = role
    if side == "depth":
        # A regular: 120+ balls in a season (a squad's player: his busiest season in the window, `best_season_balls`).
        regulars = [p["name"] for p in players
                    if p.get("best_season_balls", sum((r.get("balls") or 0) for r in p["bowl"].values())) >= REGULAR_SEASON]
        return float(len(regulars)), regulars
    cands = [p for p in players if (side != "bat" or main_bat_slot(p) == slot) and _slot_rows(p, side, slot)["balls"] >= min_balls]
    held = [(p["name"], _slot_rows(p, side, slot)) for p in sorted(cands, key=lambda p: -_weight(p, side, slot))[:n]]
    if not held:
        return None, []
    tot = {k: sum(h[1][k] for h in held) for k in ("balls", "runs", "wickets")}
    if measure == "average":
        v = tot["runs"] / tot["wickets"] if tot["wickets"] else None
    elif measure == "strike_rate":
        v = 100 * tot["runs"] / tot["balls"]
    elif measure == "wickets_per_24":
        v = 24 * tot["wickets"] / tot["balls"]
    else:  # economy
        v = 6 * tot["runs"] / tot["balls"]
    return v, [h[0] for h in held]


def benchmarks(league_data: Dict[str, Any], seasons: List[str]) -> Dict[str, Dict[str, Any]]:
    """Per role, every team-season's value in the template era, and playoff sides' and the rest's averages."""
    out = {}
    for role in ROLES:
        vals, po, rest = [], [], []
        for s in league_data["seasons"]:
            if s["season"] not in seasons:
                continue
            for team, players in s["teams"].items():
                v, _ = role_value(players, role, SEASON_MIN)
                if v is None:
                    continue
                vals.append(v)
                (po if team in s["playoff"] else rest).append(v)
        lower = role[6]
        out[role[0]] = {"values": vals, "playoff": statistics.mean(po), "rest": statistics.mean(rest),
                        "playoff_place": statistics.mean(place(vals, v, lower) for v in po)}
    return out


def place(values: List[float], v: float, lower: bool) -> float:
    """0-100: the share of team-seasons this value beats."""
    beaten = sum(1 for x in values if (x > v if lower else x < v)) + 0.5 * sum(1 for x in values if x == v)
    return 100 * beaten / len(values)


def squad_players(db, league: str, names: List[str], start: date, end: date) -> List[Dict[str, Any]]:
    """The squad's players in the role structure team_roles uses, from their record at any side in the window, with
    recency-weighted usage per role (RECENCY) for choosing who holds it."""
    from services.query_builder_v2 import run_deliveries_query
    from services.team_roles import KINDS

    # league None: every men's T20 (leagues=[] with include_international off is all of them, internationals included).
    base = dict(fmt="T20", include_international=False, leagues=[league] if league else [], start_date=start, end_date=end,
                limit=10000)
    players: Dict[str, Dict[str, Any]] = {}
    keys = ("balls", "runs", "wickets", "dots", "boundaries")

    def add(rows, k, row):
        prev = rows.get(k)
        rows[k] = {x: ((prev or {}).get(x) or 0) + (row.get(x) or 0) for x in keys}

    def player(name):
        return players.setdefault(name, {"name": name, "bat": {}, "bowl": {}, "w_bat": {}, "w_bowl": {}})

    for r in run_deliveries_query(db, batters=names, group_by=["batter", "year", "batting_position"], metrics_perspective="batting", **base)["data"]:
        if r.get("batter") and r.get("batting_position"):
            p = player(r["batter"])
            pos = int(r["batting_position"])
            add(p["bat"], pos, r)
            slot = bat_slot(pos)
            p["w_bat"][slot] = p["w_bat"].get(slot, 0) + RECENCY.get(int(r["year"]), 1) * (r.get("balls") or 0)
    for r in run_deliveries_query(db, bowlers=names, group_by=["bowler", "year", "phase", "bowl_kind"], metrics_perspective="bowling", **base)["data"]:
        if r.get("bowler") and r.get("phase"):
            p = player(r["bowler"])
            slot = f"{r['phase']}|{KINDS.get(r.get('bowl_kind'), 'unknown')}"
            add(p["bowl"], slot, r)
            p["w_bowl"][slot] = p["w_bowl"].get(slot, 0) + RECENCY.get(int(r["year"]), 1) * (r.get("balls") or 0)
    for r in run_deliveries_query(db, bowlers=names, group_by=["bowler", "year"], metrics_perspective="bowling", **base)["data"]:
        if r.get("bowler") in players:
            p = players[r["bowler"]]
            p["best_season_balls"] = max(p.get("best_season_balls", 0), r.get("balls") or 0)
    return list(players.values())


TEMPLATE_DIR = "services/pinned"  # committed: pages read it on the server too


def load_template(league: str) -> Dict[str, Any]:
    """The pinned template (scripts/build_team_template.py): benchmarks by role and the weights."""
    import json
    from pathlib import Path

    return json.loads((Path(__file__).resolve().parents[1] / TEMPLATE_DIR / f"team_template_{league}.json").read_text())


def grade(players: List[Dict[str, Any]], bench: Dict[str, Dict[str, Any]], weights: Dict[str, float]) -> Dict[str, Any]:
    """Each role's value, place, the template's levels and the verdict; and the weighted overall fit."""
    rows = []
    for role in ROLES:
        key, label, side, slot, measure, n, lower, feat = role
        v, holders = role_value(players, role, SQUAD_MIN)
        b = bench[key]
        if v is None:
            status, pl = "gap", 0.0
        else:
            pl = place(b["values"], v, lower)
            better = (lambda a, c: a <= c) if lower else (lambda a, c: a >= c)
            status = "playoff level" if better(v, b["playoff"]) else "short" if better(v, b["rest"]) else "gap"
        rows.append({"key": key, "label": label, "measure": measure, "unit": UNITS[measure], "lower_is_better": lower,
                     "value": v, "holders": holders, "place": pl, "playoff_level": b["playoff"], "rest_level": b["rest"],
                     # The tick: where playoff sides' average value would place, so dot, tick and verdict agree.
                     "playoff_place": place(b["values"], b["playoff"], lower),
                     "status": status, "weight": weights.get(feat, 0.5)})
    w = sum(r["weight"] for r in rows)
    fit = sum(r["weight"] * (r["status"] == "playoff level") for r in rows) / w if w else 0
    return {"roles": rows, "fit": fit, "at_level": sum(r["status"] == "playoff level" for r in rows), "of": len(rows)}
