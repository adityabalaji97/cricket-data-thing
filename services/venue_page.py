"""
The venue page (TEAM_VENUE_PLAN.md G1): the match preview with no teams picked. One cached call returns

* the ground's identity (city, the side that plays most of its games there),
* a summary ranked against every ground of its main competition in the same window (scoring rate, chases won,
  spin's share), with the T20 Primer par from the preview's par card as its first line,
* the preview's own ground cards, built from PreviewContext with no teams (none of them reads the sides),
* who does well there: batters by runs above par, bowlers by wickets then economy.

The window is the player profile's: recent (since Jan two years back for T20s) or career, or custom dates.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import text

PAGE_VERSION = "v2"
#: The page's cards: the par card, then the ground chapter.
CARD_IDS = ("par", "totals", "results", "innings-shape", "phases", "pace-spin", "boundary-zones", "dismissals",
            "winning-phases", "recent-results")
MIN_GROUND_MATCHES = 6     # a ground with fewer matches in the window isn't ranked
LEADER_BAT_BALLS = 60
LEADER_BOWL_BALLS = 72
LEADERS = 5


def _ctx(db, venue: str, fmt: str, start: date, end: date):
    from services.preview_cards import PreviewContext

    return PreviewContext(db=db, venue=venue, team1=None, team2=None, fmt=fmt, start=start, end=end,
                          include_international=True, top_teams=20)


def _cards(ctx) -> List[Dict[str, Any]]:
    from services.preview_cards import REGISTRY, build_story
    from services.player_identity import drop_obvious_sides  # noqa: F401  (build_story uses it)

    registry = [s for s in REGISTRY if s.id in CARD_IDS]
    story = build_story(ctx, registry)
    cards = [c for ch in story["chapters"] for c in ch["cards"] if c["id"] in CARD_IDS]
    # Par first (it opens the summary too), then the ground chapter as the story ranked it: the most unusual first.
    return sorted(cards, key=lambda c: 0 if c["id"] == "par" else 1)


def _competition_filter(ctx) -> Optional[Dict[str, Any]]:
    """The competitions the ground is ranked within: its main competition (a league, or the format's internationals)."""
    from services.competition_normalizer import international_competitions

    comp = ctx.main_competition
    if not comp:
        return None
    intl = international_competitions(ctx.fmt)
    if comp in intl:
        return {"competitions": intl, "label": "T20I grounds" if ctx.fmt == "T20" else f"{ctx.fmt} grounds"}
    return {"competitions": [comp], "label": f"{comp} grounds"}


def ranks(db, ctx) -> Optional[Dict[str, Any]]:
    """The ground against every ground of its main competition, same window: runs an over, chases won, spin's share."""
    from services.analytics_common import format_filter_sql

    comp = _competition_filter(ctx)
    if not comp:
        return None
    rows = db.execute(text(f"""
        WITH m AS (
          SELECT dd.p_match, dd.ground, MAX(dd.winner) AS winner,
                 MAX(CASE WHEN dd.inns = 1 THEN dd.team_bat END) AS bat1, MAX(CASE WHEN dd.inns = 2 THEN dd.team_bat END) AS bat2,
                 SUM(COALESCE(dd.score, 0)) AS runs,
                 SUM(CASE WHEN COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 ELSE 0 END) AS balls,
                 SUM(CASE WHEN dd.bowl_kind ILIKE '%spin%' THEN 1 ELSE 0 END) AS spin
          FROM delivery_details dd
          WHERE dd.competition = ANY(:comps) AND {format_filter_sql('dd', ctx.fmt, ctx.gender)}
            AND dd.match_date >= :start AND dd.match_date <= :end AND dd.inns IN (1, 2)
          GROUP BY dd.p_match, dd.ground)
        SELECT ground, COUNT(*) AS n, SUM(runs) AS runs, SUM(balls) AS balls, SUM(spin) AS spin,
               SUM(CASE WHEN winner IS NOT NULL AND winner = bat2 THEN 1 ELSE 0 END) AS chased,
               SUM(CASE WHEN winner IS NOT NULL AND winner IN (bat1, bat2) THEN 1 ELSE 0 END) AS decided
        FROM m GROUP BY ground
    """), {"comps": comp["competitions"], "start": ctx.start.isoformat(), "end": ctx.end.isoformat()}).mappings().all()
    aliases = set(ctx.venue_aliases) | {ctx.venue}
    # The ground under all its spellings, as one row; every other ground as it is.
    mine = [r for r in rows if r["ground"] in aliases]
    if not mine:
        return None
    me = {"ground": ctx.venue, **{k: int(sum(r[k] or 0 for r in mine)) for k in ("n", "runs", "balls", "spin", "chased", "decided")}}
    grounds = [{k: (int(v) if k != "ground" and v is not None else v) for k, v in dict(r).items()} for r in rows if r["ground"] not in aliases and r["n"] >= MIN_GROUND_MATCHES] + [me]
    if me["n"] < 3 or len(grounds) < 3:
        return None
    for g in grounds:
        g["rate"] = 6 * g["runs"] / g["balls"] if g["balls"] else None
        g["chase_pct"] = 100 * g["chased"] / g["decided"] if g["decided"] else None
        g["spin_pct"] = 100 * g["spin"] / g["balls"] if g["balls"] else None

    def rank(key):
        vals = [g for g in grounds if g[key] is not None]
        if me[key] is None:
            return None
        return {"value": round(float(me[key]), 2 if key == "rate" else 0), "rank": 1 + sum(1 for g in vals if g[key] > me[key]),
                "of": len(vals)}

    return {"label": comp["label"], "matches": me["n"], "chased": me["chased"], "decided": me["decided"],
            "rate": rank("rate"), "chase": rank("chase_pct"), "spin": rank("spin_pct")}


def leaders(ctx) -> Dict[str, List[Dict[str, Any]]]:
    from services.query_builder_v2 import run_deliveries_query

    def run(group, persp, min_balls):
        args = ctx.query_args([group])
        return run_deliveries_query(ctx.db, **args, metrics_perspective=persp, min_balls=min_balls, limit=1000)["data"]

    # By runs above par; ODIs have no par yet, so by runs.
    bat = sorted(run("batter", "batting", LEADER_BAT_BALLS),
                 key=lambda r: -(r["raa"] if r.get("raa") is not None else (r.get("runs") or 0) / 1000))[:LEADERS]
    bowl = sorted(run("bowler", "bowling", LEADER_BOWL_BALLS),
                  key=lambda r: (-(r.get("wickets") or 0), (r.get("runs") or 0) / max(1, r.get("balls") or 1)))[:LEADERS]
    return {
        "bat": [{"name": r["batter"], "runs": r["runs"], "balls": r["balls"], "strike_rate": round(r["strike_rate"] or 0),
                 "raa": round(r["raa"]) if r.get("raa") is not None else None} for r in bat],
        "bowl": [{"name": r["bowler"], "wickets": r["wickets"], "balls": r["balls"],
                  "economy": round(6 * r["runs"] / r["balls"], 2) if r["balls"] else None,
                  "dot_percentage": round(r["dot_percentage"]) if r.get("dot_percentage") is not None else None} for r in bowl],
        "min_balls": {"bat": LEADER_BAT_BALLS, "bowl": LEADER_BOWL_BALLS},
    }


def identity(db, ctx) -> Dict[str, Any]:
    names = list(set(ctx.venue_aliases) | {ctx.venue})
    # matches.city holds the country for some recent matches ("India"): the latest name that isn't a country.
    city = db.execute(text("""
        SELECT city FROM matches WHERE venue = ANY(:v) AND city IS NOT NULL
          AND city NOT IN (SELECT DISTINCT country FROM delivery_details WHERE ground = ANY(:v) AND country IS NOT NULL)
        GROUP BY city ORDER BY MAX(date) DESC LIMIT 1"""), {"v": names}).scalar()
    # The home side: one team in more than half of the ground's matches in the window.
    sides = Counter()
    for m in ctx.ground_matches:
        for inn in (m.first, m.second):
            if inn and inn.get("batting_team"):
                sides[inn["batting_team"]] += 1
    n = len(ctx.ground_matches)
    home = next((t for t, c in sides.most_common(1) if n and c > n / 2), None)
    return {"city": city, "home": home}


def build_page(db, venue: str, fmt: str = "T20", period: str = "recent", start_date: Optional[date] = None,
               end_date: Optional[date] = None) -> Dict[str, Any]:
    from services.player_verdict import default_window

    start, end = default_window(fmt, period=period)
    ctx = _ctx(db, venue, fmt, start_date or start, end_date or end)
    cards = _cards(ctx)
    par = next((c for c in cards if c["id"] == "par"), None)
    return {
        "venue": venue, "format": fmt, "period": period, "version": PAGE_VERSION,
        "window": {"start_date": ctx.start.isoformat(), "end_date": ctx.end.isoformat()},
        "matches": len(ctx.ground_matches),
        "identity": identity(db, ctx),
        "par": {"value": par["payload"].get("value"), "title": par["title"]} if par else None,
        "ranks": ranks(db, ctx),
        "cards": cards,
        "leaders": leaders(ctx),
    }


def page_key(venue: str, fmt: str, period: str, start_date: Optional[date], end_date: Optional[date]) -> Dict[str, Any]:
    key = {"kind": "venue_page", "v": PAGE_VERSION, "venue": venue, "fmt": fmt, "period": period,
           "start_date": start_date, "end_date": end_date}
    if end_date is None:
        key["day"] = date.today()
    return key


def get_page(db, venue: str, fmt: str = "T20", period: str = "recent", start_date: Optional[date] = None,
             end_date: Optional[date] = None, wait: bool = False) -> Dict[str, Any]:
    """The cached page, or PageBuilding while it's built in the background (services/page_builds.py)."""
    from services.page_builds import get_or_build

    return get_or_build(db, page_key(venue, fmt, period, start_date, end_date),
                        lambda d: build_page(d, venue, fmt, period, start_date, end_date), wait=wait)
