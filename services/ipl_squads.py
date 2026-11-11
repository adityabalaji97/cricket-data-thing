"""
IPL squads as of a date (XI_BUILDER_PLAN.md X0): the last auction's squads (auction_lots, migration 038) with the moves
since (squad_moves, migration 040) applied. One source for the retention posts, the team pages and the XI builder.

    squad(db, code, season=2027, as_of=None, reported=True)   {display name: player}
    moves(db, code=None, season=2027, as_of=None)             the moves (one team's, or all), oldest first
    deals(db, code, ...)                                       the moves grouped by deal, for "News first" copy

A player: name (our display name), pid, role, price (crore), overseas, and for a move in: traded_in (the side he came
from), state (confirmed / reported). `reported=False` leaves out moves that aren't official yet.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import text

SQUAD_STATUSES = ("sold", "retained", "rtm", "traded", "drafted", "replacement")
LAST_AUCTION = {2027: 2026}
CLEAN = "regexp_replace(regexp_replace({c}, E'\\\\u00a0', ' ', 'g'), ' {{2,}}', ' ', 'g')"


def moves(db, code: Optional[str] = None, season: int = 2027, as_of: Optional[date] = None,
          reported: bool = True) -> List[Dict[str, Any]]:
    rows = db.execute(text("""
        SELECT id, deal, player_name, pid, from_team, to_team, price_lakh, kind, state, source, announced
        FROM squad_moves WHERE league = 'ipl' AND season = :s
          AND (CAST(:c AS text) IS NULL OR from_team = :c OR to_team = :c)
          AND (CAST(:d AS date) IS NULL OR announced IS NULL OR announced <= :d)
          AND (:r OR state = 'confirmed')
        ORDER BY announced NULLS FIRST, id"""), {"s": season, "c": code, "d": as_of, "r": reported}).mappings().all()
    return [dict(r) for r in rows]


def squad(db, code: str, season: int = 2027, as_of: Optional[date] = None, reported: bool = True) -> Dict[str, Dict[str, Any]]:
    year = LAST_AUCTION[season]
    rows = db.execute(text(f"""
        SELECT COALESCE({CLEAN.format(c='p.display_name')}, a.player_name) AS name, a.pid, a.role, a.price_lakh, a.overseas
        FROM auction_lots a LEFT JOIN player_identity p ON p.pid = a.pid
        WHERE a.tournament = 'ipl' AND a.year = :y AND a.team = :c AND a.status = ANY(:st)
        ORDER BY a.price_lakh DESC NULLS LAST"""), {"y": year, "c": code, "st": list(SQUAD_STATUSES)}).mappings().all()
    out = {r["name"]: {"name": r["name"], "pid": r["pid"], "role": r["role"] or "",
                       "price": float(r["price_lakh"] or 0) / 100, "overseas": bool(r["overseas"])} for r in rows}
    by_pid = {p["pid"]: n for n, p in out.items() if p["pid"]}
    for m in moves(db, code, season, as_of, reported):
        key = by_pid.get(m["pid"]) if m["pid"] else None
        key = key or m["player_name"]
        if m["from_team"] == code and m["kind"] in ("trade", "released"):
            out.pop(key, None)
        if m["to_team"] == code and m["kind"] in ("trade", "bought"):
            base = _lot(db, m["pid"], year) if m["pid"] else {}
            out[m["player_name"]] = {"name": m["player_name"], "pid": m["pid"], "role": base.get("role") or "",
                                     "price": float(m["price_lakh"] or base.get("price_lakh") or 0) / 100,
                                     "overseas": bool(base.get("overseas")), "traded_in": m["from_team"],
                                     "state": m["state"]}
        if m["to_team"] == code and m["kind"] == "retained" and key in out:
            out[key]["retained"] = True
    return out


def _lot(db, pid: int, year: int) -> Dict[str, Any]:
    r = db.execute(text("""SELECT role, price_lakh, overseas FROM auction_lots
                           WHERE tournament = 'ipl' AND pid = :p AND year <= :y ORDER BY year DESC LIMIT 1"""),
                   {"p": pid, "y": year}).mappings().first()
    return dict(r) if r else {}


def deals(db, code: str, season: int = 2027, as_of: Optional[date] = None, reported: bool = True) -> List[Dict[str, Any]]:
    """The team's trades as deals: [{other, ins, outs, state, source, when}], for the posts' "News first" copy."""
    by: Dict[str, List[Dict[str, Any]]] = {}
    for m in moves(db, code, season, as_of, reported):
        if m["kind"] == "trade":
            by.setdefault(m["deal"] or f"m{m['id']}", []).append(m)
    out = []
    # Newest dated deal first (the day's news leads the copy), undated ones after.
    for ms in sorted(by.values(), key=lambda ms: (ms[0]["announced"] is None, -(ms[0]["announced"] or date.min).toordinal())):
        others = {t for m in ms for t in (m["from_team"], m["to_team"]) if t and t != code}
        out.append({"other": sorted(others)[0] if others else None,
                    "ins": [m["player_name"] for m in ms if m["to_team"] == code],
                    "outs": [m["player_name"] for m in ms if m["from_team"] == code],
                    "state": "reported" if any(m["state"] == "reported" for m in ms) else "confirmed",
                    "source": ms[0]["source"], "when": ms[0]["announced"]})
    return out
