"""
The XI Builder's engine (XI_BUILDER_PLAN.md X5): the data the builder screen needs, and the reference scorer the browser
mirrors (src/utils/xiEngine.js) so a swap is scored without a server call.

    payload(db, code)           the team's squad, the auction pool, each player's role totals, the benchmarks, the limits
    score(players, bench)       roles at playoff level for a set of players (the grade's rules: services/squad_grade.py)
    limits_state(squad, lim)    purse used, overseas count, squad size, and whether it can be saved

Scoring is description, not prediction (XI_SCORE_CHECK.md): "roles at playoff level", never "would make the playoffs".
The purse is a hard limit only to save and share (user, 11 Nov 2026): over it, the screen still scores, Save stays off.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

from services.squad_grade import ROLES, SQUAD_MIN, _slot_rows, main_bat_slot, place

#: IPL squad rules for 2027 (purse in crore: the 2026 cycle's; confirm when the league announces 2027's).
LIMITS = {"purse": 120.0, "overseas_max": 8, "squad_min": 18, "squad_max": 25, "xi_overseas_max": 4}
KEYS = ("balls", "runs", "wickets")


def _roles_of(p: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """A player's totals in each graded role (batting: his main slot only, as the grade holds them), and his weight in
    it (recent usage) for choosing holders."""
    out = {}
    for key, _l, side, slot, _m, _n, _lo, _f in ROLES:
        if side == "depth":
            continue
        if side == "bat" and main_bat_slot(p) != slot:
            continue
        r = _slot_rows(p, side, slot)
        if r["balls"] <= 0:
            continue
        w = (p.get("w_bat" if side == "bat" else "w_bowl") or {}).get(slot, r["balls"])
        out[key] = {**{k: round(r[k], 1) for k in KEYS}, "w": round(w, 1)}
    return out


def score(players: List[Dict[str, Any]], bench: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """The template rows for these players, from compact role totals ({name, roles: {key: {balls, runs, wickets, w}},
    best_season_balls}): the busiest N holders per role pooled; place among IPL sides; status against playoff sides."""
    rows = []
    for key, label, side, _slot, measure, n, lower, _f in ROLES:
        b = bench[key]
        if side == "depth":
            holders = [p["name"] for p in players if (p.get("best_season_balls") or 0) >= 120]
            v = float(len(holders))
        else:
            cands = [p for p in players if key in p["roles"] and p["roles"][key]["balls"] >= SQUAD_MIN]
            held = sorted(cands, key=lambda p: -p["roles"][key]["w"])[:n]
            holders = [p["name"] for p in held]
            tot = {k: sum(p["roles"][key][k] for p in held) for k in KEYS}
            if not held:
                v = None
            elif measure == "average":
                v = tot["runs"] / tot["wickets"] if tot["wickets"] else None
            elif measure == "strike_rate":
                v = 100 * tot["runs"] / tot["balls"]
            elif measure == "wickets_per_24":
                v = 24 * tot["wickets"] / tot["balls"]
            else:
                v = 6 * tot["runs"] / tot["balls"]
        if v is None:
            status, pl = "gap", 0.0
        else:
            pl = place(b["values"], v, lower)
            better = (lambda a, c: a <= c) if lower else (lambda a, c: a >= c)
            status = "playoff level" if better(v, b["playoff"]) else "short" if better(v, b["rest"]) else "gap"
        rows.append({"key": key, "label": label, "measure": measure, "value": v, "holders": holders, "place": pl,
                     "status": status})
    return {"roles": rows, "at_level": sum(r["status"] == "playoff level" for r in rows), "of": len(rows)}


def limits_state(squad: List[Dict[str, Any]], lim: Dict[str, Any] = LIMITS) -> Dict[str, Any]:
    spent = round(sum(p.get("price") or 0 for p in squad), 2)
    overseas = sum(1 for p in squad if p.get("overseas"))
    problems = []
    if spent > lim["purse"]:
        problems.append(f"₹{spent - lim['purse']:.2f} crore over the purse")
    if overseas > lim["overseas_max"]:
        problems.append(f"{overseas - lim['overseas_max']} overseas too many")
    if len(squad) > lim["squad_max"]:
        problems.append(f"{len(squad) - lim['squad_max']} over the squad limit")
    if len(squad) < lim["squad_min"]:
        problems.append(f"{lim['squad_min'] - len(squad)} short of a full squad")
    return {"spent": spent, "left": round(lim["purse"] - spent, 2), "overseas": overseas, "size": len(squad),
            "problems": problems, "can_save": not problems}


def payload(db, code: str, season: int = 2027) -> Dict[str, Any]:
    """Everything the builder screen needs for one team, cached per team and day (refreshed by a new squad move)."""
    from sqlalchemy import text

    from services.fit import END, START, pool
    from services.ipl_squads import squad as squad_of
    from services.query_cache import cached_run
    from services.squad_grade import load_template, squad_players
    from services.squad_view import TEAMS

    moves = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM squad_moves WHERE league = 'ipl'")).scalar()

    def run():
        sq = squad_of(db, code, season)
        ipl = {p["name"]: p for p in pool(db)}
        # Squad players without IPL balls in the window still need their (empty) roles.
        missing = [n for n in sq if n not in ipl]
        extra = {p["name"]: p for p in (squad_players(db, "IPL", missing, START, END) if missing else [])}

        def compact(name, meta):
            p = ipl.get(name) or extra.get(name) or {"name": name, "bat": {}, "bowl": {}}
            return {"name": name, "price": meta.get("price"), "overseas": bool(meta.get("overseas")),
                    "role": meta.get("role") or "", "roles": _roles_of(p),
                    "best_season_balls": p.get("best_season_balls", 0)}

        squad = [compact(n, m) for n, m in sq.items()]
        avail = set(db.execute(text("""
            SELECT p.display_name FROM auction_lots a JOIN player_identity p ON p.pid = a.pid
            WHERE a.tournament = 'ipl' AND a.year = :y AND a.status = 'unsold'
            UNION SELECT player_name FROM squad_moves WHERE league = 'ipl' AND season = :s AND kind = 'released'"""),
            {"y": season - 1, "s": season}).scalars().all())
        lots = {r[0]: r for r in db.execute(text("""
            SELECT DISTINCT ON (p.display_name) p.display_name, a.price_lakh, a.base_lakh, a.overseas, a.role
            FROM auction_lots a JOIN player_identity p ON p.pid = a.pid
            WHERE a.tournament = 'ipl' ORDER BY p.display_name, a.year DESC"""))}
        pool_rows = []
        for n in sorted(avail):
            if n in sq:
                continue
            lot = lots.get(n)
            # A stand-in price until the auction: his last price, else his base (rule 6), labelled on the screen.
            price = float((lot[1] or lot[2] or 30) if lot else 30) / 100
            pool_rows.append({**compact(n, {"price": price, "overseas": bool(lot and lot[3]), "role": lot[4] if lot else ""}),
                              "price_is": "last price" if lot and lot[1] else "base price"})
        tmpl = load_template("IPL")
        return {"team": TEAMS[code]["name"], "code": code, "season": season, "limits": LIMITS,
                "squad": squad, "pool": [p for p in pool_rows if p["roles"]],
                "bench": {k: {"values": v["values"], "playoff": v["playoff"], "rest": v["rest"]}
                          for k, v in tmpl["benchmarks"].items()},
                "roles": [{"key": r[0], "label": r[1], "side": r[2], "measure": r[4], "n": r[5], "lower": r[6]}
                          for r in ROLES]}
    return cached_run(db, {"kind": "xi_payload", "v": 1, "code": code, "day": date.today(), "moves": moves}, run)
