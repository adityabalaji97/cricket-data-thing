"""
Match-day posts: a preview before each match of a series, a "what decided it" post after.

  preview  the fixture's own preview-story cards (services/ig_backlog.preview_post), chosen here when not given:
           each chapter's lead card, the one the site's story shows when you swipe (StoryViewer's
           FEATURED_PER_CHAPTER), in chapter order; "Dig deeper" (the links card) is left out
  recap    the match's win-probability swing (the story's last-meeting card, with the story's end set to the match
           day so the last meeting is this match), who swung it (WPA), who added and saved the most runs
           (Impact for batters, RAA for bowlers): all from ball_metrics through the query builder; then the Impact
           scorecard, one slide per innings (batting in order: runs (balls), strike rate, Impact; bowling as on the
           match page: figures, wickets, Impact), from the scorecard service the match page uses

Labels like "2nd T20I · Ekana Cricket Stadium" count the sides' meetings in the past SERIES_DAYS.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.ig_posts.cards import card, fmt, short

#: Chapters left out of the preview carousel: "Dig deeper" is a card of links, not a picture.
SKIP_CHAPTERS = ("more",)
SERIES_DAYS = 30
FORMAT_WORD = {"T20": "T20I", "ODI": "ODI"}


def ordinal(n: int) -> str:
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def series_label(db: Session, team1: str, team2: str, fmt: str, day: date, venue: str, played: bool = False) -> str:
    """'2nd T20I · Ekana Cricket Stadium': this match's number among the sides' meetings in the last SERIES_DAYS."""
    n = db.execute(text("""
        SELECT COUNT(*) FROM matches
        WHERE ((team1 = :a AND team2 = :b) OR (team1 = :b AND team2 = :a)) AND format = :fmt AND gender = 'male'
          AND date >= :since AND date < :day
    """), {"a": team1, "b": team2, "fmt": fmt, "since": day - timedelta(days=SERIES_DAYS), "day": day}).scalar() or 0
    # "Ground, City" -> the city (short and recognisable); a bare ground name stays as it is.
    place = venue.split(",")[-1].strip() if "," in venue else venue
    return f"{ordinal(n + 1)} {FORMAT_WORD.get(fmt, fmt)} · {place}"


def chapter_leads(story: Dict[str, Any], skip=SKIP_CHAPTERS) -> List[str]:
    """Each chapter's first card (chapters arrive with their cards ranked), in chapter order."""
    return [ch["cards"][0]["id"] for ch in story["chapters"] if ch["cards"] and ch.get("id") not in skip]


def _players(db: Session, match_id: str, fmt: str, role: str) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    team_col = "batting_team" if role == "batter" else "bowling_team"
    args = {"fmt": fmt, "gender": "male", "group_by": [role, team_col], "match_ids": [match_id], "limit": 50}
    if role == "bowler":
        args["metrics_perspective"] = "bowling"
    rows = run_deliveries_query(db, **args).get("data") or []
    return [{"name": r[role], "team": r.get(team_col), "balls": r.get("balls"), "runs": r.get("runs"),
             "wickets": r.get("wickets"), "wpa": r.get("wpa"), "impact": r.get("impact"), "raa": r.get("raa"),
             "role": role} for r in rows if r.get(role)]


def innings_scorecards(db: Session, match_id: str, sample: str) -> List[Dict[str, Any]]:
    """One card per innings: the match page's full scorecard (services/match_scorecard.py), batting with strike rate."""
    from services.match_scorecard import get_match_scorecard_service

    sc = get_match_scorecard_service(match_id=str(match_id), min_balls=6, db=db)
    accents = {t["name"]: t.get("accent") for t in (sc.get("match") or {}).get("teams") or []}
    cards = []
    for inn in sc.get("innings") or []:
        s = inn["score"]
        batting = [{"name": r["name"], "runs": r["runs"], "balls": r["balls"], "sr": r.get("strike_rate"),
                    "impact": r.get("impact"), "not_out": bool(r.get("not_out"))} for r in inn["batting"]]
        bowling = [{"name": r["name"], "figures": r["figures"], "wickets": r["wickets"], "impact": r.get("impact")}
                   for r in inn["bowling"]]
        has_impact = any(r["impact"] is not None for r in batting + bowling)
        total = f"{s['runs']} all out" if s["wickets"] == 10 else f"{s['runs']}/{s['wickets']}"
        title = f"{inn['batting_team']} {total}"
        lead = max((r for r in batting if r["impact"] is not None), key=lambda r: r["impact"], default=None)
        if lead and lead["impact"] > 0:
            title += f": {short(lead['name'])}'s {lead['runs']} led, {fmt(lead['impact'], 'signed1')} Impact"
        payload = {"batting_team": inn["batting_team"], "bowling_team": inn["bowling_team"], "overs": s["overs"],
                   "accent": accents.get(inn["batting_team"]), "bowl_accent": accents.get(inn["bowling_team"]),
                   "batting": batting, "bowling": bowling, "has_impact": has_impact}
        cards.append(card(f"scorecard-{inn['innings']}", "innings_scorecard", title, payload, sample,
                          "Impact: runs added batting, or saved bowling" if has_impact else ""))
    return cards


def _bars(cid: str, rows: List[Dict[str, Any]], value_key: str, label: str, fmt_: str, title: str, sample: str,
          detail, scale: float = 1.0) -> Dict[str, Any]:
    teams = sorted({r["team"] for r in rows if r.get("team")})
    return card(cid, "metric_bars", title, {
        "metric": {"label": label, "format": fmt_, "signed": True},
        "rows": [{"name": r["name"], "value": round(r[value_key] * scale, 2), "team": r.get("team"), "detail": detail(r)}
                 for r in rows],
        "legend": teams,
    }, sample, "")


def recap_post(db: Session, match_id: str) -> Optional[Dict[str, Any]]:
    """{hook, kicker, cards, title, verdict, players, teams, day} for a played men's T20I/ODI, or None."""
    from services.preview_cards import PreviewContext
    from services.preview_cards.teams import last_meeting

    m = db.execute(text("SELECT id, date, venue, team1, team2, format, winner FROM matches WHERE id = :id"),
                   {"id": str(match_id)}).mappings().first()
    if not m or m["format"] not in FORMAT_WORD:
        return None
    ctx = PreviewContext(db=db, venue=m["venue"], team1=m["team1"], team2=m["team2"], fmt=m["format"], gender="male",
                         end=m["date"])
    swing = last_meeting(ctx)
    if not swing or str((swing.payload or {}).get("match_id")) != str(m["id"]):
        return None
    cards = []
    sj = swing.to_json()
    sj["title"] = sj["title"].replace("Last time: ", "")
    sj["title"] = sj["title"][:1].upper() + sj["title"][1:]
    cards.append(sj)
    label = series_label(db, m["team1"], m["team2"], m["format"], m["date"], m["venue"], played=True)
    sample = f"{label} · {m['date']:%d %b %Y}"
    players = [*_players(db, m["id"], m["format"], "batter"), *_players(db, m["id"], m["format"], "bowler")]
    with_wpa = sorted([p for p in players if p["wpa"] is not None], key=lambda p: abs(p["wpa"]), reverse=True)[:7]
    if with_wpa:
        top = with_wpa[0]
        cards.append(_bars("wpa", with_wpa, "wpa", "win probability added (% points)", "signed0",
                           f"{top['name']} swung it most: {fmt(top['wpa'] * 100, 'signed0')} points of win probability",
                           sample, lambda p: (f"{p['runs']} off {p['balls']}" if p["role"] == "batter"
                                              else f"{p['wickets']} for {p['runs']}"), scale=100))
    bats = sorted([p for p in players if p["role"] == "batter" and p["impact"] is not None], key=lambda p: p["impact"], reverse=True)[:6]
    if bats:
        cards.append(_bars("impact", bats, "impact", "Impact (runs added)", "signed1",
                           f"{bats[0]['name']} added the most with the bat: {fmt(bats[0]['impact'], 'signed1')} runs of Impact",
                           sample, lambda p: f"{p['runs']} off {p['balls']}"))
    bowls = sorted([p for p in players if p["role"] == "bowler" and p["raa"] is not None], key=lambda p: p["raa"], reverse=True)[:6]
    if bowls:
        cards.append(_bars("raa-bowl", bowls, "raa", "runs saved against an average bowler", "signed1",
                           f"{bowls[0]['name']} saved the most runs: {fmt(bowls[0]['raa'], 'signed1')}",
                           sample, lambda p: f"{p['wickets']} for {p['runs']} off {p['balls']}"))
    if not with_wpa:
        # No win probability or Impact (ODIs, or a T20 before ball metrics are computed): the scorecard angles.
        top_bats = sorted([p for p in players if p["role"] == "batter" and p["runs"]], key=lambda p: p["runs"], reverse=True)[:6]
        if top_bats:
            cards.append(_bars("runs", top_bats, "runs", "runs", "int",
                               f"{top_bats[0]['name']} top-scored: {top_bats[0]['runs']} off {top_bats[0]['balls']}",
                               sample, lambda p: f"SR {100 * p['runs'] / p['balls']:.0f}" if p["balls"] else None))
            cards[-1]["payload"]["metric"]["signed"] = False
        top_bowl = sorted([p for p in players if p["role"] == "bowler" and p["balls"]],
                          key=lambda p: (-(p["wickets"] or 0), p["runs"] / p["balls"]))[:6]
        if top_bowl and (top_bowl[0]["wickets"] or 0) > 0:
            cards.append(_bars("wickets", top_bowl, "wickets", "wickets", "int",
                               f"{top_bowl[0]['name']} led the bowling: {top_bowl[0]['wickets']} for {top_bowl[0]['runs']}",
                               sample, lambda p: f"{p['runs']} off {p['balls']} · econ {6 * p['runs'] / p['balls']:.1f}"))
            cards[-1]["payload"]["metric"]["signed"] = False
    if len(cards) < 2:
        return None
    cards += innings_scorecards(db, m["id"], sample)
    t1, t2 = ctx.t1, ctx.t2
    verdict = cards[0]["title"] + (f". {cards[1]['title']}." if len(cards) > 1 else ".")
    names = [c["payload"]["rows"][0]["name"] for c in cards[1:] if c["visual"] == "metric_bars"]
    return {"hook": f"What decided {t1} v {t2}?", "kicker": label, "cards": cards, "title": cards[0]["title"],
            "verdict": verdict, "players": names, "teams": [t1, t2], "day": m["date"]}
