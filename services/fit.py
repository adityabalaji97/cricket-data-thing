"""
Who fits a squad's gaps (XI_BUILDER_PLAN.md X4): for each role a squad is short of playoff level on, the players who'd
fill it, on the same measure the template grades (services/squad_grade.py ROLES).

Pool: everyone with IPL balls in the template window (2024-26) at any side. Each player's own value in a role is his
record in it (batting: his main batting slot, as the grade holds them; bowling: the phase and kind), shrunk toward the
league's rate in the role by K balls, so 109 balls can't top a list. Two lists per gap: the auction pool (players who
entered the last auction and went unsold, then the released lists from 17 Nov: in no squad isn't enough, it includes
the retired, Karthik and Dhawan) and players at other sides (they'd need a trade). Only players who'd improve the role
on the squad's own number are listed. Fit, not a verdict: the numbers and samples are shown.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from services.squad_grade import ROLES, _slot_rows, main_bat_slot, squad_players

START, END = date(2024, 1, 1), date(2026, 10, 31)
MIN_BALLS = {"bat": 120, "bowl": 120}     # balls in the role to be listed
SHRINK = {"bat": 120, "bowl": 240}        # balls of the league's rate added to his own
SHOW = 3


def _measure(tot: Dict[str, float], measure: str) -> Optional[float]:
    if measure == "average":
        return tot["runs"] / tot["wickets"] if tot["wickets"] else None
    if measure == "strike_rate":
        return 100 * tot["runs"] / tot["balls"] if tot["balls"] else None
    if measure == "wickets_per_24":
        return 24 * tot["wickets"] / tot["balls"] if tot["balls"] else None
    return 6 * tot["runs"] / tot["balls"] if tot["balls"] else None  # economy


def pool(db) -> List[Dict[str, Any]]:
    """Everyone with IPL balls in the window, in the grade's role structure. Cached per day (one heavy build)."""
    from sqlalchemy import text

    from services.query_cache import cached_run

    def run():
        names = db.execute(text("""
            SELECT DISTINCT p FROM (
              SELECT bat AS p FROM delivery_details WHERE competition = 'IPL' AND match_date BETWEEN :a AND :b
              UNION SELECT bowl FROM delivery_details WHERE competition = 'IPL' AND match_date BETWEEN :a AND :b) x
            WHERE p IS NOT NULL"""), {"a": START.isoformat(), "b": END.isoformat()}).scalars().all()
        return squad_players(db, "IPL", sorted(names), START, END)
    return cached_run(db, {"kind": "fit_pool", "v": 1, "day": date.today()}, run)


def _league_rates(players: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Per role, the league's pooled balls / runs / wickets per ball, for shrinking."""
    out = {}
    for key, _, side, slot, measure, _n, _lower, _f in ROLES:
        if side == "depth":
            continue
        tot = {"balls": 0.0, "runs": 0.0, "wickets": 0.0}
        for p in players:
            if side == "bat" and main_bat_slot(p) != slot:
                continue
            r = _slot_rows(p, side, slot)
            for k in tot:
                tot[k] += r[k]
        out[key] = {k: tot[k] / tot["balls"] for k in ("runs", "wickets")} if tot["balls"] else {"runs": 0, "wickets": 0}
    return out


def fits(db, code: str, gaps: List[Dict[str, Any]], season: int = 2027) -> List[Dict[str, Any]]:
    """For each gap ({key, value, playoff_level, ...} from the grade, depth aside): the best fits not in a squad and at
    other sides, each with his shrunk value, raw value, balls in the role, and his 2027 side (None: not in a squad)."""
    from services.ipl_squads import squad
    from services.squad_view import TEAMS

    from sqlalchemy import text

    players = pool(db)
    rates = _league_rates(players)
    side_of = {}
    for c in TEAMS:
        for name in squad(db, c, season):
            side_of[name] = c
    # The auction pool: unsold at the last auction (and, from 17 Nov, released: squad_moves kind 'released').
    available = set(db.execute(text("""
        SELECT p.display_name FROM auction_lots a JOIN player_identity p ON p.pid = a.pid
        WHERE a.tournament = 'ipl' AND a.year = :y AND a.status = 'unsold'
        UNION SELECT player_name FROM squad_moves WHERE league = 'ipl' AND season = :s AND kind = 'released'"""),
        {"y": season - 1, "s": season}).scalars().all())
    roles = {r[0]: r for r in ROLES}
    out = []
    for g in gaps:
        role = roles.get(g["key"])
        if not role or role[2] == "depth":
            continue
        key, label, side, slot, measure, _n, lower, _f = role
        k = SHRINK[side]
        rows = []
        for p in players:
            if side == "bat" and main_bat_slot(p) != slot:
                continue
            r = _slot_rows(p, side, slot)
            if r["balls"] < MIN_BALLS[side] or side_of.get(p["name"]) == code:
                continue
            if not side_of.get(p["name"]) and p["name"] not in available:
                continue  # in no squad and not in the auction pool: retired, or not registered
            raw = _measure(r, measure)
            shrunk = _measure({"balls": r["balls"] + k, "runs": r["runs"] + k * rates[key]["runs"],
                               "wickets": r["wickets"] + k * rates[key]["wickets"]}, measure)
            if raw is None or shrunk is None:
                continue
            rows.append({"name": p["name"], "value": round(raw, 2), "shrunk": round(shrunk, 2), "balls": int(r["balls"]),
                         "side": side_of.get(p["name"])})
        mine = g.get("value")
        if mine is not None:  # only players who'd improve the role, on the squad's own number
            rows = [x for x in rows if (x["shrunk"] < mine if lower else x["shrunk"] > mine)]
        rows.sort(key=lambda x: x["shrunk"] if lower else -x["shrunk"])
        out.append({"key": key, "label": label, "measure": measure, "lower_is_better": lower,
                    "squad_value": g.get("value"), "playoff_level": g.get("playoff_level"),
                    "free": [x for x in rows if not x["side"]][:SHOW],
                    "elsewhere": [x for x in rows if x["side"]][:SHOW]})
    return out
