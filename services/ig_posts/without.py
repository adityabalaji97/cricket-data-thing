"""
"<Team> without <player>": what a side's T20I bowling looks like with and without one bowler, since a date. Every number
from the query builder (bowling perspective) or the ball-by-ball tables.

    post(db, team, player, since)  ->  {slides, title, verdict, players, kicker, deep_cut, method} or None

Slides: hook; win % with and without, split by opposition (top 8 sides, the rest); the deeper cut: runs an over barely
move, win probability added (above all at the death) does; who bowls the death without him (runs saved against an
average bowler); the caveat (winning isn't one player; the samples); end.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.ig_posts.cards import card
from services.ig_posts.spotlight import short_name

TOP = ["India", "Australia", "England", "South Africa", "New Zealand", "Pakistan", "West Indies", "Sri Lanka", "Afghanistan"]
PHASES = (("powerplay", "Powerplay"), ("middle", "Middle overs"), ("death", "Death overs"))
MIN_DEATH_BALLS = 36


def _q(db, ids, **kw):
    from services.query_builder_v2 import run_deliveries_query

    return run_deliveries_query(db, fmt="T20", gender="male", include_international=True, leagues=[], match_ids=ids,
                                metrics_perspective="bowling", limit=50, **kw).get("data") or []


def post(db: Session, team: str, player: str, since: date) -> Optional[Dict[str, Any]]:
    rows = db.execute(text("""
        SELECT p_match, BOOL_OR(bowl = :p) AS played, MAX(winner) AS winner,
               MAX(team_bat) FILTER (WHERE team_bat <> :t) AS opp
        FROM delivery_details WHERE competition = 'T20I' AND team_bowl = :t AND match_date >= :s GROUP BY 1
    """), {"p": player, "t": team, "s": since.isoformat()}).mappings().all()
    side = {True: [r for r in rows if r["played"]], False: [r for r in rows if not r["played"]]}
    if min(len(side[True]), len(side[False])) < 10:
        return None
    who = short_name(player)
    sample = f"{team} in men's T20Is since {since.year}"

    def win(rs):
        return round(100 * sum(1 for r in rs if r["winner"] == team) / len(rs)) if rs else None
    top = {k: [r for r in v if r["opp"] in TOP] for k, v in side.items()}
    rest = {k: [r for r in v if r["opp"] not in TOP] for k, v in side.items()}
    wins = [
        {"name": f"With {who}", "value": win(top[True]), "detail": f"v top sides · {len(top[True])} games", "highlight": False},
        {"name": f"Without {who}", "value": win(top[False]), "detail": f"v top sides · {len(top[False])} games", "highlight": True},
        {"name": f"With {who}", "value": win(rest[True]), "detail": f"v the rest · {len(rest[True])} games", "highlight": False},
        {"name": f"Without {who}", "value": win(rest[False]), "detail": f"v the rest · {len(rest[False])} games", "highlight": True},
    ]
    wins = [w for w in wins if w["value"] is not None]
    hook = (f"{team} win {wins[0]['value']}% of T20Is against top sides with {who}. Without him, {wins[1]['value']}%.")
    c_win = card("wins", "metric_bars",
                 f"Against top sides, {team} win {wins[0]['value']}% with {who} and {wins[1]['value']}% without",
                 {"metric": {"label": "% of games won", "format": "pct0", "signed": False}, "rows": wins,
                  "label_width": 150}, sample,
                 f"Top sides: {', '.join(t for t in TOP if t != team)}. The gap holds against the rest too.")

    ids = {k: [str(r["p_match"]) for r in v] for k, v in side.items()}
    by = {k: {r["phase"]: r for r in _q(db, ids[k], bowling_teams=[team], group_by=["phase"])} for k in (True, False)}
    allr = {k: (_q(db, ids[k], bowling_teams=[team], group_by=["bowling_team"]) or [{}])[0] for k in (True, False)}
    econ = lambda r: round(6 * r["runs"] / r["balls"], 1)  # noqa: E731
    wpa_g = lambda r, k: round(100 * r["wpa"] / len(ids[k]), 1)  # noqa: E731  win-probability points per game
    d1, d0 = by[True].get("death"), by[False].get("death")
    if not (d1 and d0 and allr[True] and allr[False]):
        return None
    # One unit on the chart: win probability added a game, by phase. The runs an over go in the title and help line.
    rows_ = [{"label": label, "subject": wpa_g(by[False][k], False), "field": wpa_g(by[True][k], True),
              "highlight": k == "death"} for k, label in PHASES if k in by[False] and k in by[True]]
    deep = card("runs-v-wins", "deep_compare",
                f"Death overs without {who}: {econ(d0)} an over (with him {econ(d1)}), but win probability added falls "
                f"from {wpa_g(d1, True)} to {wpa_g(d0, False)} a game",
                {"metric": {"label": "win probability added by the bowling, points a game", "format": "dec1",
                            "signed": False},
                 "series": [f"Without {who}", f"With {who}"], "rows": rows_}, sample,
                f"Win probability added: how much the bowling moved {team}'s chance of winning, in percentage points, "
                f"over a game. All game: {wpa_g(allr[True], True)} with him, {wpa_g(allr[False], False)} without; runs an "
                f"over {econ(allr[True])} with him, {econ(allr[False])} without.")
    from services.ig_posts.deep_cut import KICKER

    deep["kicker"] = KICKER

    death = sorted([r for r in _q(db, ids[False], bowling_teams=[team], group_by=["bowler"], over_min=15)
                    if r["balls"] >= MIN_DEATH_BALLS], key=lambda r: -r["balls"])[:6]
    bars = [{"name": short_name(r["bowler"]), "value": round(6 * r["raa_per_100"] / 100, 2),
             "detail": f"{r['balls'] // 6}.{r['balls'] % 6} overs · {round(6 * r['runs'] / r['balls'], 1)} an over",
             "team": team} for r in death if r.get("raa_per_100") is not None]
    mine = (_q(db, ids[True], bowlers=[player], group_by=["phase"]) or [])
    pd = next((r for r in mine if r["phase"] == "death"), None)
    best = max(bars, key=lambda b: b["value"]) if bars else None
    c_death = card("death", "metric_bars",
                   f"Without {who}, {short_name(death[0]['bowler'])} has bowled the most death overs; "
                   f"{best['name']} has saved the most runs there" if best else f"Who bowls the death without {who}",
                   {"metric": {"label": "runs saved an over at the death, against an average bowler", "format": "signed2",
                               "signed": True}, "rows": bars, "label_width": 130}, sample,
                   (f"{who} at the death in this time: {round(6 * pd['raa_per_100'] / 100, 2):+.2f} runs saved an over, "
                    f"{round(6 * pd['runs'] / pd['balls'], 1)} an over." if pd and pd.get("raa_per_100") is not None else ""))
    caveat = {"type": "text", "heading": "The caveat", "body": "\n".join([
        f"Winning isn't one player: other changes come with {who}'s absences (injuries, rest, other players out).",
        f"Samples: {len(top[True])} and {len(top[False])} games against top sides.",
        "The bowling numbers are what the ball-by-ball shows; the wins are the results."])}
    slides = ([{"type": "hook", "text": hook, "kicker": f"{team} without {who}", "sub": "Runs, wins, and where the gap opens"}]
              + [{"type": "card", "card": c, "teams": None} for c in (c_win, deep, c_death)]
              + [caveat, {"type": "end", "heading": "Every ball, every over",
                          "body": "Win probability, runs saved, by bowler and phase: free on Hindsight."}])
    return {"slides": slides, "title": hook, "verdict": f"{c_win['title']}. {deep['title']}.", "players": [player],
            "kicker": f"{team} without {who}",
            "deep_cut": {"probe": "without-wpa", "subject": player, "sentence": deep["title"] + ".", "by": "recap"},
            "method": "win probability and runs saved (against an average bowler in the same situations) are computed "
                      "ball by ball (T20 Primer method)."}
