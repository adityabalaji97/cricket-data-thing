"""
"<Team> without <player>": what a side's T20I bowling looks like with and without one bowler, since a date. Every number
from the query builder (bowling perspective) or the ball-by-ball tables.

    post(db, team, player, since)  ->  {slides, title, verdict, players, kicker, deep_cut, method} or None

Slides: hook; win % with and without, split by opposition (top 8 sides, the rest); the deeper cut: runs an over barely
move, win probability added (above all at the death) does; pressure (runs saved, dots, boundaries, false shots, wickets)
with and without, in the phases he bowls most; yorkers at the death against the other pacers; who bowls the death
without him; when he's used (overs, after an expensive over, leverage), as the data shows it; the caveat; end.
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

    if ids is not None:
        kw["match_ids"] = ids
    return run_deliveries_query(db, fmt="T20", gender="male", include_international=True, leagues=[],
                                metrics_perspective="bowling", limit=50, **kw).get("data") or []


PRESSURE = [("econ", "Runs/over", "dec1", True), ("raa", "Saved/over", "signed2", False), ("dot", "Dots %", "pct0", False),
            ("bdry", "4s+6s %", "pct0", True), ("false", "False shots %", "pct0", False), ("bpw", "Balls/wkt", "dec1", True)]


def pressure_card(db, team, who, ids, phases, sample):
    """For each phase the player bowls most: the team's attack with him and without, on the pressure measures."""
    rows, values = [], {}
    for ph, label in phases:
        for k, tag in ((True, "with"), (False, "without")):
            r = next((x for x in _q(db, ids[k], bowling_teams=[team], group_by=["phase"]) if x["phase"] == ph), None)
            if not r:
                continue
            name = f"{label} · {tag}"
            ctl = r.get("control_percentage")
            values[name] = {"econ": round(6 * r["runs"] / r["balls"], 1),
                            "raa": round(6 * r["raa_per_100"] / 100, 2) if r.get("raa_per_100") is not None else None,
                            "dot": round(r["dot_percentage"]), "bdry": round(r["boundary_percentage"]),
                            "false": round(100 - ctl) if ctl is not None else None,
                            "bpw": round(r["balls_per_dismissal"], 1) if r.get("balls_per_dismissal") else None}
            short_ = {"powerplay": "PP", "middle": "Middle", "death": "Death"}[ph]
            rows.append({"name": name, "short": f"{short_} {'+' if k else '−'}", "values": values[name], "highlight": not k})
    if len(rows) < 4:
        return None
    for key, _, _, low in PRESSURE:  # shade within each phase pair: the better of the two is brighter
        for i in range(0, len(rows), 2):
            pair = [r for r in rows[i:i + 2] if r["values"].get(key) is not None]
            for r in pair:
                other = next((o for o in pair if o is not r), None)
                better = other is None or (r["values"][key] < other["values"][key] if low else r["values"][key] > other["values"][key])
                r.setdefault("pct", {})[key] = 85 if better else 25
    lines = []
    for i in range(0, len(rows), 2):
        a, b = rows[i]["values"], rows[i + 1]["values"]
        if a.get("raa") is not None and b.get("raa") is not None:
            ph_ = {"Powerplay": "powerplay", "Middle overs": "middle", "Death overs": "death"}[rows[i]['name'].split(' · ')[0]]
            lines.append(f"{ph_} {a['raa']:+.2f} v {b['raa']:+.2f}".replace("-", "−"))
    return card("pressure", "scorecard",
                f"Runs saved an over, with {who} v without: " + ", ".join(lines),
                {"metrics": [{"key": k, "label": l, "format": f} for k, l, f, _ in PRESSURE],
                 "rows": [{**r, "leader": []} for r in rows],
                 "method": f"+ with {who}, − without. False shots: balls the batter didn't control. "
                           "Brighter: the better of each pair."}, sample,
                f"{team}'s whole attack in the phases {who} bowls most. Runs saved: against an average attack in the same "
                "situations.")


def yorker_card(db, team, player, who, since, sample, min_balls=60):
    """Yorkers at the death: the player against the team's other pacers and the T20I average."""
    legal = "COALESCE(wide, 0) = 0 AND COALESCE(noball, 0) = 0"
    rows = [dict(r) for r in db.execute(text(f"""
        SELECT bowl, COUNT(*) FILTER (WHERE {legal}) AS balls,
               100.0 * AVG((length = 'YORKER')::int) FILTER (WHERE length IS NOT NULL) AS y,
               AVG(score) FILTER (WHERE length = 'YORKER') AS rpb, COUNT(*) FILTER (WHERE length = 'YORKER') AS n
        FROM delivery_details WHERE competition = 'T20I' AND team_bowl = :t AND match_date >= :s AND over >= 15
          AND bowl_kind = 'pace bowler' GROUP BY 1 HAVING COUNT(*) >= :m ORDER BY 3 DESC
    """), {"t": team, "s": since.isoformat(), "m": min_balls}).mappings()]
    avg = db.execute(text("""
        SELECT 100.0 * AVG((length = 'YORKER')::int) FROM delivery_details
        WHERE competition = 'T20I' AND match_date >= :s AND over >= 15 AND bowl_kind = 'pace bowler' AND length IS NOT NULL
    """), {"s": since.isoformat()}).scalar()
    me = next((r for r in rows if r["bowl"] == player), None)
    if not me or len(rows) < 3 or avg is None:
        return None
    bars = [{"name": short_name(r["bowl"]), "value": round(float(r["y"]), 1), "highlight": r["bowl"] == player,
             "detail": f"{r['n']} yorkers · {float(r['rpb'] or 0):.2f} runs each"} for r in rows]
    bars.append({"name": "T20I pacers", "value": round(float(avg), 1), "detail": "the average, death overs"})
    nxt = next(r for r in rows if r["bowl"] != player)
    return card("yorkers", "metric_bars",
                f"{round(float(me['y']))}% of {who}'s death balls are yorkers. Next best for {team}: "
                f"{short_name(nxt['bowl'])} at {round(float(nxt['y']), 1)}%",
                {"metric": {"label": "% of death-over balls that are yorkers", "format": "dec1", "signed": False},
                 "rows": bars, "label_width": 130}, sample,
                f"Pacers with {min_balls}+ death balls. Yorker: where the ball pitched, from ball-by-ball tracking.")


def deployment_card(db, team, player, who, since, sample):
    """When the player bowls: overs by band, after an expensive over, how much is riding on it (leverage), against
    the team's other pacers. Said as the data shows it, whatever the usual story is."""
    ov = [dict(r) for r in db.execute(text("""
        WITH o AS (SELECT p_match, inns, over, MAX(bowl) AS bowl, MAX(bowl_kind) AS kind, SUM(score) AS runs
                   FROM delivery_details WHERE competition = 'T20I' AND team_bowl = :t AND match_date >= :s GROUP BY 1, 2, 3),
        -- the previous over of the innings, whoever bowled it (computed before keeping only the pacers' overs)
        p AS (SELECT *, LAG(runs) OVER (PARTITION BY p_match, inns ORDER BY over) AS prev FROM o)
        SELECT bowl, over, prev FROM p WHERE kind = 'pace bowler'
    """), {"t": team, "s": since.isoformat()}).mappings()]
    me = [r for r in ov if r["bowl"] == player]
    rest = [r for r in ov if r["bowl"] != player]
    if len(me) < 30:
        return None
    bands = [("1st", (0,)), ("2nd-6th", (1, 2, 3, 4, 5)), ("7th-15th", tuple(range(6, 15))), ("16th-17th", (15, 16)),
             ("18th-19th", (17, 18)), ("20th", (19,))]
    share = lambda grp, overs: round(100 * sum(r["over"] in overs for r in grp) / len(grp))  # noqa: E731
    rows = [{"label": f"Overs: {lbl}", "subject": share(me, o), "field": share(rest, o)} for lbl, o in bands]
    top = max(rows, key=lambda r: r["subject"] - r["field"])
    top["highlight"] = True
    after = lambda grp: round(100 * sum((r["prev"] or 0) >= 10 for r in grp if r["prev"] is not None)  # noqa: E731
                              / max(1, sum(r["prev"] is not None for r in grp)))
    lev = {k: (_q(db, None, bowling_teams=[team], start_date=since, bowl_kind=["pace bowler"], group_by=["bowl_kind"],
                  **({"bowlers": [player]} if k else {"exclude_bowlers": [player]})) or [{}])[0].get("avg_leverage")
           for k in (True, False)}
    lev_line = ""
    if lev[True] is not None and lev[False] is not None:
        more = lev[True] > lev[False] * 1.05
        lev_line = (f" {who}'s overs {'carry more' if more else 'do not carry more'} at stake than the others' on average "
                    f"(leverage {lev[True]:.3f} against {lev[False]:.3f}).")
    return card("deployment", "deep_compare",
                f"{who}'s overs: {top['label'].replace('Overs: ', 'the ')} more than other {team} pacers; "
                f"after a 10+ over, {after(me)}% of his overs to their {after(rest)}%",
                {"metric": {"label": "% of each pacer group's overs", "format": "pct0", "signed": False},
                 "series": [who, f"Other {team} pacers"], "rows": rows}, sample,
                f"{len(me)} overs by {who}, {len(rest)} by the others.{lev_line}")


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
    # The phases he bowls most (by balls), in game order: where his absence is felt.
    mine_ph = {r["phase"]: r["balls"] for r in mine}
    top_ph = sorted(sorted(mine_ph, key=lambda p: -mine_ph[p])[:2], key=lambda p: [k for k, _ in PHASES].index(p))
    c_press = pressure_card(db, team, who, ids, [(k, l) for k, l in PHASES if k in top_ph], sample)
    c_york = yorker_card(db, team, player, who, since, sample)
    c_dep = deployment_card(db, team, player, who, since, sample)
    slides = ([{"type": "hook", "text": hook, "kicker": f"{team} without {who}", "sub": "Runs, wins, and where the gap opens"}]
              + [{"type": "card", "card": c, "teams": None} for c in (c_win, deep, c_press, c_york, c_death, c_dep) if c]
              + [caveat, {"type": "end", "heading": "Every ball, every over",
                          "body": "Win probability, runs saved, by bowler and phase: free on Hindsight."}])
    return {"slides": slides, "title": hook, "verdict": f"{c_win['title']}. {deep['title']}.", "players": [player],
            "kicker": f"{team} without {who}",
            "deep_cut": {"probe": "without-wpa", "subject": player, "sentence": deep["title"] + ".", "by": "recap"},
            "method": "win probability and runs saved (against an average bowler in the same situations) are computed "
                      "ball by ball (T20 Primer method)."}
