"""
The team page (TEAM_VENUE_PLAN.md T1): one cached call for a side's page in a window.

A franchise is ranked against the sides of its league; an international side against the top-12 sides (the player
verdict's TOP_TEAMS), its record counted in matches between them. Cards: rating (Elo after each match), by phase
(batting runs above par and bowling economy, each ranked), who bats where, who bowls when (overs grid), top players,
batting first v chasing, and the record against each side.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import text

PAGE_VERSION = "v5"
PEER_MIN_BALLS = 600          # a side needs this many balls in a phase to be ranked in it
TOP_BAT_BALLS, TOP_BOWL_BALLS = 60, 120
POSITIONS = 8
GRID_BOWLERS = 8
LAST = 8
PHASES = (("powerplay", "Powerplay"), ("middle", "Middle"), ("death", "Death"))


def _q(db, scope, **kw) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    return run_deliveries_query(db, **{**scope, **kw}, limit=10000)["data"]


def _short(team: str) -> str:
    from models import teams_mapping

    if teams_mapping.get(team):
        return teams_mapping[team]
    words = team.split()
    return team.upper()[:3] if len(words) == 1 else "".join(w[0] for w in words[:3]).upper()


def team_scope(db, team: str, fmt: str, start: date, end: date) -> Optional[Dict[str, Any]]:
    """Where the side plays: internationals (ranked against the top 12) or its league."""
    from services.competition_normalizer import international_competitions
    from services.player_verdict import TOP_TEAMS
    from services.teams import get_all_team_name_variations

    names = get_all_team_name_variations(team)
    rows = db.execute(text("""
        SELECT competition, COUNT(DISTINCT p_match) AS n FROM delivery_details
        WHERE team_bat = ANY(:t) AND format = :f AND gender = 'male' AND match_date >= :s AND match_date <= :e
        GROUP BY competition ORDER BY n DESC"""), {"t": names, "f": fmt, "s": start.isoformat(), "e": end.isoformat()}).all()
    if not rows:
        return None
    intl = set(international_competitions(fmt))
    n_intl = sum(r.n for r in rows if r.competition in intl)
    if n_intl >= sum(r.n for r in rows) / 2:
        return {"kind": "international", "label": f"top-{TOP_TEAMS} sides", "competition": "T20Is" if fmt == "T20" else f"{fmt}s",
                "filters": {"fmt": fmt, "include_international": True, "leagues": [], "top_teams": TOP_TEAMS,
                            "start_date": start, "end_date": end},
                "competitions": sorted(intl)}
    comp = next(r.competition for r in rows if r.competition not in intl)
    return {"kind": "league", "label": f"{comp} sides", "competition": comp,
            "filters": {"fmt": fmt, "include_international": False, "leagues": [comp], "start_date": start, "end_date": end},
            "competitions": [comp]}


def phases(db, team: str, scope) -> Dict[str, Any]:
    f = scope["filters"]
    bat = _q(db, f, group_by=["batting_team", "phase"], metrics_perspective="batting")
    bowl = _q(db, f, group_by=["bowling_team", "phase"], metrics_perspective="bowling")
    from services.teams import get_all_team_name_variations

    names = set(get_all_team_name_variations(team)) | {team}
    eco = lambda r: 6 * r["runs"] / r["balls"]  # noqa: E731
    # Batting by runs above par (the T20 Primer); ODIs have no par yet, so by strike rate.
    key = "raa_per_100" if f["fmt"] == "T20" else "strike_rate"
    out, peers = {}, set()
    for ph, _ in PHASES:
        b = [r for r in bat if r["phase"] == ph and r["balls"] >= PEER_MIN_BALLS and r.get(key) is not None]
        w = [r for r in bowl if r["phase"] == ph and r["balls"] >= PEER_MIN_BALLS]
        peers |= {r["batting_team"] for r in b}
        me_b = next((r for r in b if r["batting_team"] in names), None)
        me_w = next((r for r in w if r["bowling_team"] in names), None)
        if not me_b or not me_w:
            continue
        out[ph] = {
            "bat": {"raa_per_100": round(me_b["raa_per_100"], 1) if me_b.get("raa_per_100") is not None else None,
                    "strike_rate": round(me_b["strike_rate"]), "measure": "raa" if key == "raa_per_100" else "strike_rate",
                    "rank": 1 + sum(1 for r in b if r[key] > me_b[key]), "of": len(b)},
            "bowl": {"economy": round(eco(me_w), 2), "dot_percentage": round(me_w.get("dot_percentage") or 0),
                     "rank": 1 + sum(1 for r in w if eco(r) < eco(me_w)), "of": len(w)},
        }
    return {"phases": out, "peers": sorted(peers)}


def results(db, team: str, scope, peers: List[str]) -> Dict[str, Any]:
    """Every match in scope from the ball-by-ball feed: won-lost, batting first v chasing, last 8, against each side."""
    from services.analytics_common import format_filter_sql
    from services.teams import get_all_team_name_variations

    names = get_all_team_name_variations(team)
    f = scope["filters"]
    rows = db.execute(text(f"""
        SELECT p_match, MIN(match_date) AS d, MAX(winner) AS winner, MAX(ground) AS ground,
               MAX(CASE WHEN inns = 1 THEN team_bat END) AS bat1, MAX(CASE WHEN inns = 2 THEN team_bat END) AS bat2,
               MAX(CASE WHEN inns = 1 THEN inns_runs END) AS r1, MAX(CASE WHEN inns = 2 THEN inns_runs END) AS r2,
               MAX(CASE WHEN inns = 2 THEN inns_wkts END) AS w2
        FROM delivery_details dd
        WHERE (team_bat = ANY(:t) OR team_bowl = ANY(:t)) AND competition = ANY(:c) AND {format_filter_sql('dd', f['fmt'], 'male')}
          AND match_date >= :s AND match_date <= :e AND inns IN (1, 2)
        GROUP BY p_match ORDER BY MIN(match_date)"""),
                      {"t": names, "c": scope["competitions"], "s": f["start_date"].isoformat(),
                       "e": f["end_date"].isoformat()}).mappings().all()
    peer_set = set(peers)
    games = []
    for r in rows:
        if not r["bat1"] or not r["bat2"]:
            continue
        mine_first = r["bat1"] in names
        opp = r["bat2"] if mine_first else r["bat1"]
        if scope["kind"] == "international" and opp not in peer_set:
            continue  # internationals count matches between the top sides only
        result = None if not r["winner"] else ("won" if r["winner"] in names else "lost")
        games.append({"match_id": str(r["p_match"]), "date": str(r["d"]), "opp": opp, "opp_short": _short(opp), "first": mine_first, "result": result,
                      "score": f"{r['r1']}" if mine_first else f"{r['r2']}/{r['w2']}", "ground": r["ground"]})
    decided = [g for g in games if g["result"]]
    opp = defaultdict(lambda: {"won": 0, "lost": 0})
    for g in decided:
        opp[g["opp"]][g["result"]] += 1
    first = [g for g in decided if g["first"]]
    chase = [g for g in decided if not g["first"]]
    return {
        "played": len(games), "won": sum(g["result"] == "won" for g in games), "lost": sum(g["result"] == "lost" for g in games),
        "last": games[-LAST:][::-1],
        "batting_first": {"won": sum(g["result"] == "won" for g in first), "of": len(first)},
        "chasing": {"won": sum(g["result"] == "won" for g in chase), "of": len(chase)},
        "against": sorted(({"team": t, "short": _short(t), **v} for t, v in opp.items()),
                          key=lambda x: (-(x["won"] + x["lost"]), x["team"])),
    }


def rating(db, team: str, peers: List[str], start: date, end: date, fmt: str) -> Optional[Dict[str, Any]]:
    """Elo after each match in the window, and where the side's latest rating ranks among its peers' latest."""
    from services.teams import get_all_team_name_variations

    names = get_all_team_name_variations(team)
    series = db.execute(text("""
        SELECT date, CASE WHEN team1 = ANY(:t) THEN team1_elo ELSE team2_elo END AS elo FROM matches
        WHERE (team1 = ANY(:t) OR team2 = ANY(:t)) AND format = :f AND gender = 'male' AND date >= :s AND date <= :e
        ORDER BY date"""), {"t": names, "f": fmt, "s": start, "e": end}).all()
    series = [{"date": str(r.date), "elo": int(r.elo)} for r in series if r.elo is not None]
    if not series:
        return None
    pool = list(set(peers) | set(names))
    # Each peer's latest rating, one per side: a renamed side (Royal Challengers Bangalore, then Bengaluru) is one side,
    # rated as of its last match under either name.
    others = {}
    for r in db.execute(text("""
        SELECT side, elo FROM (
          SELECT team1 AS side, team1_elo AS elo, date AS d FROM matches WHERE team1 = ANY(:p) AND format = :f AND gender = 'male' AND date <= :e
          UNION ALL
          SELECT team2, team2_elo, date FROM matches WHERE team2 = ANY(:p) AND format = :f AND gender = 'male' AND date <= :e) x
        WHERE elo IS NOT NULL ORDER BY d"""), {"p": pool, "f": fmt, "e": end}).mappings().all():
        if r["side"] not in names:
            others[_short(r["side"])] = r["elo"]
    now = series[-1]["elo"]
    return {"series": series, "now": now, "rank": 1 + sum(1 for v in others.values() if v > now), "of": len(others) + 1}


def batting_order(db, team: str, scope) -> List[Dict[str, Any]]:
    """The usual order: each spot to the batter who batted there most, each batter once (a floater who batted 4th to
    7th takes the spot he batted most), so the card reads as a line-up. share: his share of that spot's innings."""
    rows = _q(db, scope["filters"], batting_teams=[team], group_by=["batting_position", "batter"], metrics_perspective="batting")
    totals = Counter()
    for r in rows:
        totals[int(r["batting_position"] or 0)] += r["innings_count"] or 0
    taken, used = {}, set()
    for r in sorted(rows, key=lambda r: -(r["innings_count"] or 0)):
        n = int(r["batting_position"] or 0)
        if 1 <= n <= POSITIONS and n not in taken and r["batter"] not in used:
            taken[n] = r
            used.add(r["batter"])
    out = []
    for n in sorted(taken):
        r = taken[n]
        out.append({"position": n, "batter": r["batter"], "share": round(100 * (r["innings_count"] or 0) / max(1, totals[n])),
                    "innings": r["innings_count"], "strike_rate": round(r["strike_rate"] or 0),
                    "raa_per_100": round(r["raa_per_100"], 1) if r.get("raa_per_100") is not None else None})
    return out


def bowling_overs(db, team: str, scope) -> Dict[str, Any]:
    """Who bowls which over: for the side's most-used bowlers, each over's share of the balls (overs counted from 1)."""
    rows = _q(db, scope["filters"], bowling_teams=[team], group_by=["over", "bowler"], metrics_perspective="bowling")
    balls = Counter()
    for r in rows:
        balls[r["bowler"]] += r["balls"] or 0
    bowlers = [b for b, _ in balls.most_common(GRID_BOWLERS)]
    per_over = defaultdict(Counter)
    for r in rows:
        per_over[int(r["over"]) + 1][r["bowler"]] += r["balls"] or 0  # the data counts overs from 0
    overs = sorted(per_over)
    return {"overs": overs, "bowlers": [
        {"name": b, "balls": balls[b], "shares": [round(per_over[o][b] / max(1, sum(per_over[o].values())), 3) for o in overs]}
        for b in bowlers]}


def top_players(db, team: str, scope) -> Dict[str, Any]:
    f = scope["filters"]
    bat = _q(db, f, batting_teams=[team], group_by=["batter"], metrics_perspective="batting", min_balls=TOP_BAT_BALLS)
    bowl = _q(db, f, bowling_teams=[team], group_by=["bowler"], metrics_perspective="bowling", min_balls=TOP_BOWL_BALLS)
    # Batters by runs above par; bowlers by economy (bowling runs above par doesn't repeat season to season, so it
    # doesn't rank them: docs/social_rules.md), with wickets and dots beside it.
    return {
        # ODIs have no par yet: their batters by runs.
        "bat": [{"name": r["batter"], "runs": r["runs"], "balls": r["balls"], "strike_rate": round(r["strike_rate"] or 0),
                 "raa": round(r["raa"]) if r.get("raa") is not None else None}
                for r in sorted(bat, key=lambda r: -(r.get("raa") if r.get("raa") is not None else (r.get("runs") or 0) / 1000))[:5]],
        "bowl": [{"name": r["bowler"], "wickets": r["wickets"], "balls": r["balls"], "economy": round(6 * r["runs"] / r["balls"], 2),
                  "dot_percentage": round(r.get("dot_percentage") or 0)} for r in sorted(bowl, key=lambda r: r["runs"] / r["balls"])[:5]],
        "min_balls": {"bat": TOP_BAT_BALLS, "bowl": TOP_BOWL_BALLS},
    }


def build_page(db, team: str, fmt: str = "T20", period: str = "recent", start_date: Optional[date] = None,
               end_date: Optional[date] = None) -> Dict[str, Any]:
    from services.player_verdict import default_window

    s, e = default_window(fmt, period=period)
    start, end = start_date or s, end_date or e
    scope = team_scope(db, team, fmt, start, end)
    base = {"team": team, "short": _short(team), "format": fmt, "period": period, "version": PAGE_VERSION,
            "window": {"start_date": start.isoformat(), "end_date": end.isoformat()}}
    if not scope:
        return {**base, "played": 0}
    ph = phases(db, team, scope)
    res = results(db, team, scope, ph["peers"])
    return {**base, "scope": {k: scope[k] for k in ("kind", "label", "competition")},
            "played": res["played"], "won": res["won"], "lost": res["lost"],
            "rating": rating(db, team, ph["peers"], start, end, fmt),
            "phases": ph["phases"], "results": res,
            "batting_order": batting_order(db, team, scope), "bowling_overs": bowling_overs(db, team, scope),
            "top": top_players(db, team, scope)}


def page_key(team: str, fmt: str, period: str, start_date: Optional[date], end_date: Optional[date]) -> Dict[str, Any]:
    key = {"kind": "team_page", "v": PAGE_VERSION, "team": team, "fmt": fmt, "period": period,
           "start_date": start_date, "end_date": end_date}
    if end_date is None:
        key["day"] = date.today()
    return key


def canonical_team(team: str) -> str:
    """A full name for any spelling the site links with ("CSK", "Chennai Super Kings"): the latest full name."""
    from models import teams_mapping

    t = (team or "").strip()
    if t in teams_mapping:
        return t
    fulls = [full for full, short in teams_mapping.items() if short.lower() == t.lower()]
    if not fulls:
        return t
    # Of a renamed side's names (Royal Challengers Bangalore, Bengaluru), the one in the latest matches.
    from database import SessionLocal

    db = SessionLocal()
    try:
        row = db.execute(text("""
            SELECT side FROM (SELECT team1 AS side, date FROM matches WHERE team1 = ANY(:f)
                           UNION ALL SELECT team2, date FROM matches WHERE team2 = ANY(:f)) x
            ORDER BY date DESC LIMIT 1"""), {"f": fulls}).scalar()
    finally:
        db.close()
    return row or fulls[0]


def get_page(db, team: str, fmt: str = "T20", period: str = "recent", start_date: Optional[date] = None,
             end_date: Optional[date] = None, wait: bool = False) -> Dict[str, Any]:
    from services.page_builds import get_or_build

    team = canonical_team(team)
    return get_or_build(db, page_key(team, fmt, period, start_date, end_date),
                        lambda d: build_page(d, team, fmt, period, start_date, end_date), wait=wait)
