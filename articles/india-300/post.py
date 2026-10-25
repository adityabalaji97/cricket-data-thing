"""
India's 300th men's T20I (NZ v India, Christchurch, 24 Oct 2026): 300 matches, 200 wins. Match-level records cover all
300 (results, toss, who batted first) and the ball-by-ball goes back to 2006 (scoring rates, the raw batting and
bowling numbers); Impact and win probability are T20 Primer metrics, from 2015.

Slides (10, approved for this landmark): cover (results by opponent); the deeper cut (toss -> batted first or chased
-> result, a Sankey); scoring rate and economy by year; team totals since 2015; batting raw; batting by Impact and win
probability; bowling raw; bowling by Impact and win probability; the games that turned; end.

    python articles/india-300/post.py              # dry run: titles, lint; nothing saved (writes slides.json)
    python articles/india-300/post.py --write      # queue for today and render
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

KEY = "spotlight-india-300-t20is-2026-10-25"
SITE = "https://hindsightcricket.com"
TEAM = "India"
WON, LOST, TIED, NR = "#b6f24a", "#e66767", "#9aa1ac", "#3a4150"
MATCHES = ("m.format = 'T20' AND m.gender = 'male' AND m.match_type = 'international' "
           "AND 'India' IN (m.team1, m.team2)")
SHOWN = 6           # players on the batting and bowling grids
BAT_FIELD = 300     # balls for an India batter to be in the shading field
#: India's two T20Is with no ball-by-ball anywhere (Cricsheet hasn't them either): v Afghanistan, Gros Islet 2010
#: (412679) and Colombo 2012 (533274). Their scorecard innings for the batters on the grid (ESPNcricinfo / ESPN
#: scorecards), added to the ball-by-ball career totals so they match the official ones; dot balls aren't on a
#: scorecard, so dot % stays ball-by-ball.
SCORECARD_ONLY = {"Virat Kohli": {"runs": 50, "balls": 39, "fours": 4, "sixes": 2, "outs": 1},   # 533274
                  "Rohit Sharma": {"runs": 1, "balls": 1, "fours": 0, "sixes": 0, "outs": 0}}   # 533274, not out
BOWL_FIELD = 300    # balls for an India bowler


def sg(v, d=1):
    return f"{v:+.{d}f}".replace("-", "−")


def card(cid, visual, title, payload, sample, help_=""):
    return {"id": cid, "visual": visual, "title": title, "help": help_, "sample": sample, "payload": payload}


def q(db, **kw):
    from services.query_builder_v2 import run_deliveries_query

    return run_deliveries_query(db, fmt="T20", gender="male", include_international=True, limit=10000, **kw)["data"]


def matches(db):
    from sqlalchemy import text

    rows = [dict(r) for r in db.execute(text(f"""
        SELECT m.id, m.date, m.team1, m.team2, m.winner, m.outcome, m.toss_winner, m.bat_first
        FROM matches m WHERE {MATCHES} ORDER BY m.date""")).mappings()]
    for r in rows:
        oc = r["outcome"] or {}
        r["opp"] = r["team2"] if r["team1"] == TEAM else r["team1"]
        r["res"] = ("tied" if oc.get("result") == "tie" else "nr" if not r["winner"] else
                    "won" if r["winner"] == TEAM else "lost")
    return rows


# ---- results -------------------------------------------------------------------------------------------------------

def opponents_card(ms):
    by = {}
    for m in ms:
        by.setdefault(m["opp"], {"won": 0, "lost": 0, "tied": 0, "nr": 0})[m["res"]] += 1
    top = sorted(by, key=lambda o: -sum(by[o].values()))[:5]
    won = sum(m["res"] == "won" for m in ms)
    return card("by-opponent", "share_bars", f"{len(ms)} T20Is, {won} wins",
                {"absolute": True, "format": "int",
                 "groups": [{"key": "won", "label": "Won", "colour": WON}, {"key": "lost", "label": "Lost", "colour": LOST},
                            {"key": "tied", "label": "Tied", "colour": TIED}, {"key": "nr", "label": "No result", "colour": NR}],
                 "rows": [{"name": o, "detail": f"{sum(by[o].values())} T20Is",
                           "segments": [{"key": k, "value": by[o][k]} for k in ("won", "lost", "tied", "nr")]} for o in top]},
                "India's men's T20Is, Dec 2006 to Oct 2026 · the five most-played opponents",
                "Tied includes Super Over results; no result includes matches abandoned after the toss.")


def sankey_card(ms):
    known = [m for m in ms if m["toss_winner"] and m["bat_first"]]
    links = {}
    for m in known:
        toss = "toss-won" if m["toss_winner"] == TEAM else "toss-lost"
        inn = "bat" if m["bat_first"] == TEAM else "chase"
        res = {"won": "won", "lost": "lost"}.get(m["res"], "other")
        links[(toss, inn)] = links.get((toss, inn), 0) + 1
        links[(inn, res)] = links.get((inn, res), 0) + 1
    rate = lambda inn: (links.get((inn, "won"), 0), sum(v for (a, _), v in links.items() if a == inn))  # noqa: E731
    cw, cn = rate("chase")
    bw, bn = rate("bat")
    title = (f"Chasing, India have won {round(100 * cw / cn)}% ({cw} of {cn}); batting first, "
             f"{round(100 * bw / bn)}% ({bw} of {bn})")
    c = card("toss-to-result", "sankey", title,
             {"columns": [[{"id": "toss-won", "label": "Won the toss"}, {"id": "toss-lost", "label": "Lost the toss"}],
                          [{"id": "bat", "label": "Batted first"}, {"id": "chase", "label": "Chased"}],
                          [{"id": "won", "label": "Won", "colour": WON}, {"id": "lost", "label": "Lost", "colour": LOST},
                           {"id": "other", "label": "Tied or no result", "colour": TIED}]],
              "links": [{"source": a, "target": b, "value": v} for (a, b), v in links.items()]},
             f"{len(known)} of India's {len(ms)} T20Is with the toss recorded · Dec 2006 to Oct 2026",
             "Read left to right: who won the toss, who batted first, how it ended.")
    c["kicker"] = "The deeper cut"
    return c, {"cw": cw, "cn": cn, "bw": bw, "bn": bn}


# ---- scoring by year -----------------------------------------------------------------------------------------------

def rates_card(db):
    bat = {r["year"]: r for r in q(db, batting_teams=[TEAM], group_by=["year"], metrics_perspective="batting")}
    bowl = {r["year"]: r for r in q(db, bowling_teams=[TEAM], group_by=["year"], metrics_perspective="bowling")}
    years = sorted(set(bat) & set(bowl))
    rpo = lambda r: round(6 * r["runs"] / r["balls"], 2)  # noqa: E731
    fastest = max(years, key=lambda y: rpo(bat[y]))
    first = years[0]
    c = card("rates-by-year", "metric_lines",
             f"{fastest}: India score at {rpo(bat[fastest]):.1f} an over, their fastest year. {first}: {rpo(bat[first]):.1f}",
             {"x": {"label": "", "ticks": [y for y in years if (y % 5 == 0 and years[-1] - y >= 3) or y in (first, years[-1])]},
              "y": {"label": "runs an over", "format": "dec1"},
              "series": [{"name": "Scoring", "highlight": True, "points": [{"x": y, "y": rpo(bat[y])} for y in years]},
                         {"name": "Conceding", "points": [{"x": y, "y": rpo(bowl[y])} for y in years]}]},
             "India's men's T20Is by calendar year, ball by ball · 2006 to Oct 2026",
             "Runs an over India scored (batting) and conceded (bowling), every ball of the year.")
    return c, {"fastest": fastest, "rpo": rpo(bat[fastest]), "first": first, "first_rpo": rpo(bat[first])}


# ---- team totals since 2015 ----------------------------------------------------------------------------------------

def totals_card(db, ms):
    from sqlalchemy import text

    res = {m["id"]: m["res"] for m in ms}
    rows = db.execute(text(f"""
        SELECT d.p_match, d.inns, MAX(d.inns_runs) AS total, MAX(d.inns_wkts) AS wkts, MIN(m.date) AS date,
               SUM(CASE WHEN COALESCE(d.wide, 0) = 0 AND COALESCE(d.noball, 0) = 0 THEN 1 ELSE 0 END) AS legal
        FROM delivery_details d JOIN matches m ON m.id::text = d.p_match
        WHERE {MATCHES} AND d.team_bat = 'India' AND d.inns IN (1, 2)
        GROUP BY 1, 2""")).mappings().all()
    pts = [{"year": r["date"].year, "total": int(r["total"]), "won": res.get(r["p_match"]) == "won", "recent": True,
            "id": r["p_match"], "inns": r["inns"], "complete": r["wkts"] >= 10 or r["legal"] >= 120}
           for r in rows if res.get(r["p_match"]) in ("won", "lost")]
    hi = max(pts, key=lambda p: p["total"])
    # Lowest: a complete innings only, all out or a full 20 overs (a rain-shortened match or a chase won early
    # isn't a low score).
    lo = min((p for p in pts if p["complete"]), key=lambda p: p["total"])
    opp = {m["id"]: m["opp"] for m in ms}
    c = card("totals", "totals_scatter",
             f"India's highest T20I total: {hi['total']} v {opp[hi['id']]}, {hi['year']}. Lowest since 2015: {lo['total']}",
             {"points": [{k: p[k] for k in ("year", "total", "won", "recent")} for p in pts], "line": None,
              "years": [min(p["year"] for p in pts), max(p["year"] for p in pts)], "legend": ["Won", "Lost"],
              "callouts": [{"year": hi["year"], "total": hi["total"], "label": f"{hi['total']} v {opp[hi['id']]}"},
                           {"year": lo["year"], "total": lo["total"], "label": f"{lo['total']} v {opp[lo['id']]}", "place": "below"}]},
             "Every India innings with a result · T20Is since 2015, ball by ball",
             "Lowest: a complete innings (all out or 20 overs). Every innings with a result is a dot.")
    return c, {"hi": hi, "lo": lo, "hi_opp": opp[hi["id"]], "lo_opp": opp[lo["id"]]}


# ---- players -------------------------------------------------------------------------------------------------------

def _pct(field, key, v, higher=True):
    vals = sorted(r[key] for r in field if r.get(key) is not None)
    if v is None or not vals:
        return None
    below = sum(x < v for x in vals) if higher else sum(x > v for x in vals)
    return round(100 * below / max(1, len(vals) - 1))


def grid(cid, rows, field, metrics, title, sample, help_):
    out = []
    surnames = [r["name"].split()[-1] for r in rows]
    for r in rows:
        vals = {m["key"]: (round(r[m["key"]], 2) if r.get(m["key"]) is not None else None) for m in metrics}
        pct = {m["key"]: _pct(field, m["key"], r.get(m["key"]), m.get("higher", True)) for m in metrics}
        # The surname, unless two of the rows share it (Rohit and Abhishek Sharma): then the full name.
        short = r["name"].split()[-1] if surnames.count(r["name"].split()[-1]) == 1 else r["name"]
        out.append({"name": r["name"], "short": short, "values": vals, "pct": pct, "leader": []})
    for m in metrics:
        have = [o for o in out if o["values"][m["key"]] is not None]
        if len(have) > 1:
            best = (max if m.get("higher", True) else min)(have, key=lambda o: o["values"][m["key"]])
            best["leader"].append(m["key"])
    return card(cid, "scorecard", title,
                {"metrics": [{"key": m["key"], "label": m["label"], "format": m["format"]} for m in metrics],
                 "rows": out, "label_width": 112}, sample, help_)


def batting(db):
    allb = q(db, batting_teams=[TEAM], group_by=["batter"], metrics_perspective="batting")
    for r in allb:
        r["name"] = r["batter"]
        add = SCORECARD_ONLY.get(r["name"])
        if add:  # the scorecard-only innings: runs, balls, boundaries and dismissals; dots stay ball-by-ball
            outs = (r["runs"] / r["average"]) if r.get("average") else 0
            bounds = r["boundary_percentage"] * r["balls"] / 100
            r["runs"] += add["runs"]
            r["balls"] += add["balls"]
            r["average"] = r["runs"] / (outs + add["outs"]) if outs + add["outs"] else None
            r["strike_rate"] = 100 * r["runs"] / r["balls"]
            r["boundary_percentage"] = 100 * (bounds + add["fours"] + add["sixes"]) / r["balls"]
    top = sorted(allb, key=lambda r: -r["runs"])[:SHOWN]
    field = [r for r in allb if r["balls"] >= BAT_FIELD]
    raw_m = [{"key": "runs", "label": "Runs", "format": "int"}, {"key": "average", "label": "Avg", "format": "dec1"},
             {"key": "strike_rate", "label": "SR", "format": "int"},
             {"key": "dot_percentage", "label": "Dot %", "format": "pct0", "higher": False},
             {"key": "boundary_percentage", "label": "4s/6s %", "format": "pct0"}]
    most = top[0]
    avg = max(top, key=lambda r: r["average"] or 0)
    raw = grid("batting-raw", top, field, raw_m,
               f"{most['name']}: most runs, {most['runs']:,}. {avg['name'].split()[-1]} averages the most: {avg['average']:.1f}",
               "India's six leading run-scorers in men's T20Is · Dec 2006 to Oct 2026",
               f"Shading: where each figure ranks among India batters with {BAT_FIELD}+ balls. Ring: the best of the six. "
               "Ball by ball, plus the scorecards of the two 2010 and 2012 games against Afghanistan, which have no "
               "ball-by-ball (dot % leaves them out).")
    since = {r["batter"]: r for r in q(db, batting_teams=[TEAM], group_by=["batter"], metrics_perspective="batting",
                                       start_date=__import__("datetime").date(2015, 1, 1))}
    sfield = [dict(r, name=n) for n, r in since.items() if r["balls"] >= BAT_FIELD]
    rows2 = [dict(since[r["name"]], name=r["name"]) for r in top if r["name"] in since]
    for r in rows2 + sfield:
        r["wpa_pts"] = 100 * (r.get("wpa") or 0)
    imp_m = [{"key": "impact_per_100", "label": "Impact/100", "format": "signed1"},
             {"key": "raa_per_100", "label": "Above par/100", "format": "signed1"},
             {"key": "wpa_pts", "label": "Win prob. pts", "format": "signed0"}]
    best = max(rows2, key=lambda r: r["impact_per_100"])
    imp = grid("batting-impact", rows2, sfield, imp_m,
               f"{best['name']}: {sg(best['impact_per_100'])} Impact per 100 balls, the most of the six",
               "The same six · T20Is since 2015 (Impact and win probability start in 2015)",
               "Impact: runs added to India's projected total. Above par: runs above par in the same situations. Win "
               "probability points: 100 = one match won. All per the T20 Primer method.")
    return raw, imp, {"most": most, "avg": avg, "best": best}


def bowling(db):
    allb = q(db, bowling_teams=[TEAM], group_by=["bowler"], metrics_perspective="bowling")
    for r in allb:
        r["name"] = r["bowler"]
        r["economy"] = 6 * r["runs"] / r["balls"] if r["balls"] else None
    top = sorted(allb, key=lambda r: -(r["wickets"] or 0))[:SHOWN]
    field = [r for r in allb if r["balls"] >= BOWL_FIELD]
    raw_m = [{"key": "wickets", "label": "Wkts", "format": "int"},
             {"key": "economy", "label": "Econ", "format": "dec2", "higher": False},
             {"key": "balls_per_dismissal", "label": "Balls/wkt", "format": "dec1", "higher": False},
             {"key": "dot_percentage", "label": "Dot %", "format": "pct0"}]
    most = top[0]
    econ = min(top, key=lambda r: r["economy"])
    raw = grid("bowling-raw", top, field, raw_m,
               f"{most['name']}: most wickets, {most['wickets']}. {econ['name'].split()[-1]} goes for the least: {econ['economy']:.2f}",
               "India's six leading wicket-takers in men's T20Is · 2006 to Oct 2026, ball by ball",
               f"Shading: where each figure ranks among India bowlers with {BOWL_FIELD}+ balls. Ring: the best of the six.")
    since = {r["bowler"]: r for r in q(db, bowling_teams=[TEAM], group_by=["bowler"], metrics_perspective="bowling",
                                       start_date=__import__("datetime").date(2015, 1, 1))}
    sfield = [dict(r, name=n) for n, r in since.items() if r["balls"] >= BOWL_FIELD]
    rows2 = [dict(since[r["name"]], name=r["name"]) for r in top if r["name"] in since]
    for r in rows2 + sfield:
        r["wpa_pts"] = 100 * (r.get("wpa") or 0)
    imp_m = [{"key": "impact_per_100", "label": "Impact/100", "format": "signed1"},
             {"key": "wpa_pts", "label": "Win prob. pts", "format": "signed0"}]
    best = max(rows2, key=lambda r: r["impact_per_100"])
    imp = grid("bowling-impact", rows2, sfield, imp_m,
               f"{best['name']}: {sg(best['impact_per_100'])} Impact per 100 balls, the most of the six",
               "The same six · T20Is since 2015 (Impact and win probability start in 2015)",
               "Impact for a bowler: runs saved from the batting side's projected total, wickets included. Win "
               "probability points: 100 = one match won. T20 Primer method.")
    return raw, imp, {"most": most, "econ": econ, "best": best}


# ---- games that turned ---------------------------------------------------------------------------------------------

def turns_card(db, ms):
    from sqlalchemy import text

    res = {m["id"]: m for m in ms}
    rows = db.execute(text(f"""
        SELECT d.p_match,
               MIN(CASE WHEN d.team_bat = 'India' THEN bm.wp_after ELSE 1 - bm.wp_after END) AS lo,
               MAX(CASE WHEN d.team_bat = 'India' THEN bm.wp_after ELSE 1 - bm.wp_after END) AS hi
        FROM delivery_details d JOIN ball_metrics bm ON bm.delivery_id = d.id
        JOIN matches m ON m.id::text = d.p_match
        WHERE {MATCHES} AND (m.outcome IS NULL OR m.outcome->>'method' IS NULL)
        GROUP BY 1""")).mappings().all()
    won = sorted((r for r in rows if res.get(r["p_match"], {}).get("res") == "won"), key=lambda r: r["lo"])[:3]
    lost = sorted((r for r in rows if res.get(r["p_match"], {}).get("res") == "lost"), key=lambda r: -r["hi"])[:3]
    pc = lambda v: max(1, round(100 * v)) if v < 0.995 else round(100 * v)  # noqa: E731
    lab = lambda r: f"v {res[r['p_match']]['opp']}, {res[r['p_match']]['date'].year}"  # noqa: E731
    rows_out = ([{"name": lab(r), "value": 100 - pc(r["lo"]), "highlight": i == 0, "detail": f"won from {pc(r['lo'])}%"}
                 for i, r in enumerate(won)]
                + [{"name": lab(r), "value": -pc(r["hi"]), "detail": f"lost from {pc(r['hi'])}%"} for r in lost])
    w0, l0 = won[0], lost[0]
    c = card("turns", "metric_bars",
             f"India won from {pc(w0['lo'])}% {lab(w0)}, and lost from {pc(l0['hi'])}% {lab(l0)}",
             {"metric": {"label": "Win probability swung (points)", "format": "signed0", "signed": True},
              "rows": rows_out, "label_width": 150},
             "India's T20Is since 2015 with a result · win probability (T20 Primer)",
             "Up: points India came back from their lowest chance to win. Down: points from their highest to a defeat. "
             "Rain-rule matches left out.")
    return c, {"won": [(lab(r), pc(r["lo"])) for r in won], "lost": [(lab(r), pc(r["hi"])) for r in lost]}


def build(db):
    ms = matches(db)
    lead = opponents_card(ms)
    sk, sn = sankey_card(ms)
    rates, rn = rates_card(db)
    tot, tn = totals_card(db, ms)
    braw, bimp, bn = batting(db)
    wraw, wimp, wn = bowling(db)
    turns, un = turns_card(db, ms)
    won = sum(m["res"] == "won" for m in ms)
    counts = {k: sum(m["res"] == k for m in ms) for k in ("won", "lost", "tied", "nr")}
    years = {}
    for m in ms:
        y = years.setdefault(m["date"].year, [0, 0])
        y[0] += 1
        y[1] += m["res"] == "won"
    best_year = max((y for y in years if years[y][0] >= 10), key=lambda y: years[y][1] / years[y][0])
    return {"lead": lead, "cards": [sk, rates, tot, braw, bimp, wraw, wimp, turns], "n": len(ms), "won": won,
            "counts": counts, "best_year": (best_year, *years[best_year]), "sn": sn, "rn": rn, "tn": tn, "bn": bn,
            "wn": wn, "un": un}


def copy(b):
    c, sn, rn, tn, bn, wn, un = b["counts"], b["sn"], b["rn"], b["tn"], b["bn"], b["wn"], b["un"]
    by, bp, bw = b["best_year"]
    hook = f"India have played {b['n']} T20Is and won {b['won']} of them"
    caption = "\n\n".join([
        f"India's 300th T20I, in Christchurch on Saturday, was win number {b['won']}: {c['won']} won, {c['lost']} lost, "
        f"{c['tied']} tied, {c['nr']} no result since December 2006.",
        f"Chasing, they've won {round(100 * sn['cw'] / sn['cn'])}% ({sn['cw']} of {sn['cn']}). Batting first, "
        f"{round(100 * sn['bw'] / sn['bn'])}% ({sn['bw']} of {sn['bn']}). Best year: {by}, {bw} wins in {bp}.",
        f"{rn['fastest']} is India's fastest-scoring year: {rn['rpo']:.1f} an over, against {rn['first_rpo']:.1f} in {rn['first']}.",
        f"Highest total: {tn['hi']['total']} v {tn['hi_opp']} ({tn['hi']['year']}). The lowest since 2015 is "
        f"{tn['lo']['total']}; all-time it's 74, v Australia in 2008 (ESPNcricinfo).",
        f"Most runs: {bn['most']['name']}, {bn['most']['runs']:,}. Most wickets: {wn['most']['name']}, "
        f"{wn['most']['wickets']}. By Impact since 2015: {bn['best']['name']} with the bat, {wn['best']['name']} "
        "with the ball.",
        f"The biggest turnaround: won from {un['won'][0][1]}% {un['won'][0][0]}.",
        "Impact and win probability are ball by ball (T20 Primer method), from 2015. Ball-by-ball data: Himanish "
        "Ganjoo & TechRadar, Cricsheet.",
        "Which of the 300 do you remember most?",
        "Free ball-by-ball cricket stats: link in bio.\n.\n#TeamIndia #T20I #NZvIND #cricket #India300",
    ])
    return hook, caption


def slides_of(b, hook):
    from services.ig_cover import hero_from

    cover = {"type": "hook", "text": hook, "kicker": "300 T20Is · Dec 2006 to Oct 2026", "cover": "hero",
             "hero": {**hero_from(b["lead"]), "card": b["lead"]}}
    return ([cover] + [{"type": "card", "card": c, "teams": [TEAM]} for c in b["cards"]]
            + [{"type": "end", "heading": "Every T20I, ball by ball",
                "body": "Results, Impact and win probability for every India T20I: free on Hindsight."}])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--base", default=SITE)
    args = parser.parse_args()
    if args.write:
        assert "localhost" not in os.environ.get("DATABASE_URL", ""), "--write is production"
    from database import get_session
    from services.social_rules import findings

    db = next(get_session())
    b = build(db)
    hook, caption = copy(b)
    slides = slides_of(b, hook)
    print("HOOK:", hook, f"({len(hook)})")
    for i, s in enumerate(slides, 1):
        c = s.get("card") or {}
        print(f"  {i}. [{c.get('visual') or s['type']}] {c.get('title') or s.get('text') or s.get('heading')} ({len(c.get('title') or '')})")
    # 10 slides were approved for this landmark (25 Oct 2026): every other rule still has to pass.
    problems = [f for f in findings(slides, "spotlight") if f["rule"] != "slide_count"]
    print("lint:", problems or "clean (10 slides: approved)")
    print(caption)
    (HERE / "slides.json").write_text(json.dumps({"slides": slides, "hook": hook, "caption": caption}, default=str, indent=1))
    if problems or not args.write:
        return 1 if problems else 0

    from database import engine
    from services import ig_backlog, ig_carousel, ig_slides
    from services.ig_notes import youtube_copy

    carousel = ig_carousel.save(db, slides, hook, {"spotlight": KEY}, "ig-spotlight")
    n = len(slides)
    fact = {"kind": "spotlight", "title": hook, "hook": hook, "subject": None, "carousel_id": carousel["id"],
            "slides": n, "render": True, "post_time": "6 pm", "slide_count_approved": True}
    fact["youtube"] = youtube_copy(fact, caption, hook)
    ist = timezone(timedelta(hours=5, minutes=30))
    today = datetime.now(ist).date()
    post = {"key": KEY, "pillar": "reactive", "fact": fact, "snapshot_id": carousel["id"], "warnings": [],
            "players": [], "caption": caption}
    with engine.begin() as conn:
        ig_backlog.upsert_pack(conn, post, today, source="hand", post_by=datetime.combine(today, time.max, tzinfo=ist))
    print(f"queued ig:{KEY} for {today} · carousel {carousel['id']} ({n} slides)")
    os.environ.pop("REEL_V2", None)
    r = ig_slides.render(carousel["id"], n, args.base)
    print(f"rendered {len(r['ok'])}/{n}" + (f", failed {r['failed']}" if r["failed"] else "") + f"; layout {r.get('layout') or 'clean'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
