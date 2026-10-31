"""
India's bowling in 2026, 30 Oct 2026 (New Zealand made 259 against India in Auckland today: the match isn't in our
ball-by-ball yet, so it's the hook only; every chart is our data to 24 Oct). Five of the six biggest totals India
have conceded in T20Is came since July 2026; the era explains some of it, the rest is India's attack sliding from
the best among the top 10 sides to sixth on runs above par. No bowler named (no-blame framing).

    python articles/india-259/post.py              # dry run
    python articles/india-259/post.py --write      # queue, render, voiced Reel (reel.json from the same numbers), thread
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from sqlalchemy import text  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

KEY = "spotlight-india-bowling-2026-10-30"
SITE = "https://hindsightcricket.com"
T = "India"
TOP10 = {"fmt": "T20", "include_international": True, "top_teams": 10}
BEFORE = (date(2023, 1, 1), date(2025, 12, 31))
NOW = (date(2026, 1, 1), date(2026, 10, 26))
TEAM_SHORT = {"India": "IND", "Australia": "AUS", "England": "ENG", "South Africa": "RSA", "New Zealand": "NZ",
              "Pakistan": "PAK", "Sri Lanka": "SL", "West Indies": "WI", "Afghanistan": "AFG", "Bangladesh": "BAN"}
STYLES = [("Pace", {"bowl_kind": ["pace bowler"]}), ("Off-spin", {"bowl_style": ["OB"]}),
          ("Left-arm orthodox", {"bowl_style": ["SLA"]}), ("Wrist spin", {"bowl_style": ["LB", "LBG", "LWS"]})]
LENGTHS = ["FULL", "GOOD_LENGTH", "SHORT_OF_A_GOOD_LENGTH", "SHORT"]
LINES = ["WIDE_OUTSIDE_OFFSTUMP", "OUTSIDE_OFFSTUMP", "ON_THE_STUMPS", "DOWN_LEG"]  # wide down leg: too few balls

THREAD_PLAYERS = []  # each one's first mention in the thread becomes a hashtag


def sg(v, d=1):
    return f"{v:+.{d}f}".replace("-", "−")


def card(cid, visual, title, payload, sample, help_=""):
    assert len(title) <= 80, (len(title), title)
    return {"id": cid, "visual": visual, "title": title, "help": help_, "sample": sample, "payload": payload}


def q(db, **kw):
    from services.query_builder_v2 import run_deliveries_query

    kw.setdefault("limit", 10000)
    kw.setdefault("metrics_perspective", "bowling")
    return run_deliveries_query(db, **kw)["data"]


def econ(r):
    return r["runs"] * 6 / r["balls"] if r.get("balls") else None


def period(p):
    return {"start_date": p[0], "end_date": p[1]}


# ---- slides -----------------------------------------------------------------------------------------------------

def totals_card(db):
    """Every innings against India in T20Is, 2006 on: one dot each, 2026 highlighted."""
    from sqlalchemy import text

    rows = db.execute(text("""
        SELECT d.p_match, d.inns, max(d.inns_runs) AS total, min(m.date) AS dt, max(d.team_bat) AS opp,
               max(d.inns_wkts) AS wkts,
               count(*) FILTER (WHERE coalesce(d.wide, 0) = 0 AND coalesce(d.noball, 0) = 0) AS legal
        FROM delivery_details d JOIN matches m ON m.id::text = d.p_match
        WHERE m.format = 'T20' AND m.gender = 'male' AND m.match_type = 'international' AND d.team_bowl = 'India'
          AND m.date < '2026-10-30'  -- before today's 259: the post's "before today" claim
        GROUP BY 1, 2""")).mappings().all()
    pts = [{"year": r["dt"].year, "total": int(r["total"]), "won": r["dt"] >= date(2026, 1, 1), "recent": True,
            "opp": r["opp"], "dt": r["dt"]} for r in rows]
    top = sorted(pts, key=lambda p: -p["total"])[:6]
    in_2026 = sum(1 for p in top if p["won"])
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    # The cover shows the six biggest as bars (a totals scatter can't be drawn on a cover), 2026 highlighted.
    c = card("totals", "metric_bars",
             f"{in_2026} of the 6 biggest totals India have conceded in T20Is came in 2026",
             {"metric": {"label": "Total conceded", "format": "int"}, "label_width": 150,
              "rows": [{"name": f"{TEAM_SHORT.get(p['opp'], p['opp'][:3].upper())}, {months[p['dt'].month - 1]} {p['year']}", "value": p["total"],
                        "highlight": p["won"]} for p in top]},
             "Every innings against India in men's T20Is · 2006 to 24 Oct 2026")
    return c, {"top": top, "in_2026": in_2026, "n": len(pts)}


def rates_card(db):
    years = list(range(2015, 2027))
    rows = {}
    for lab, kw in (("All", {}), ("India bowl", {"bowling_teams": [T]}), ("India bat", {"batting_teams": [T]})):
        by = {r["year"]: r for r in q(db, group_by=["year"], start_date=date(2015, 1, 1), end_date=date(2026, 10, 24), **TOP10, **kw)}
        rows[lab] = {y: round(econ(by[y]), 2) for y in years if y in by}
    a, i = rows["All"], rows["India bowl"]
    c = card("rates", "metric_lines",
             f"2026 runs at {a[2026]:.1f} an over between top-10 sides. India have conceded {i[2026]:.1f}",
             {"x": {"label": "", "ticks": [2015, 2018, 2021, 2024, 2026]}, "y": {"label": "runs an over", "format": "dec1"},
              "series": [{"name": "India bowl", "highlight": True, "points": [{"x": y, "y": v} for y, v in i.items()]},
                         {"name": "All", "points": [{"x": y, "y": v} for y, v in a.items()]},
                         {"name": "India bat", "points": [{"x": y, "y": v} for y, v in rows["India bat"].items()]}]},
             "Runs an over · T20Is between top-10 sides, to 24 Oct")
    c["kicker"] = "The era"
    return c, rows


def par_card(db):
    def ranks(p):
        return {r["bowling_team"]: r for r in q(db, group_by=["bowling_team"], **period(p), **TOP10)}
    b, n = ranks(BEFORE), ranks(NOW)
    teams = sorted(b.keys() & n.keys(), key=lambda t: -n[t]["raa_per_100"])
    rank = lambda d, t: sorted(d, key=lambda x: -d[x]["raa_per_100"]).index(t) + 1  # noqa: E731
    rb, rn = rank(b, T), rank(n, T)
    rows = [{"label": TEAM_SHORT.get(t, t), "a": round(b[t]["raa_per_100"], 1), "b": round(n[t]["raa_per_100"], 1),
             "highlight": t == T} for t in teams][:8]  # 10 rows overflow the card; India is 6th, so the top 8 show it
    assert any(r["highlight"] for r in rows)
    c = card("par", "pair_dumbbell",
             f"India's bowling: {['', '1st', '2nd', '3rd'][rb] if rb <= 3 else f'{rb}th'} of 10 for runs above par in 2023-25, "
             f"{rn}th in 2026",
             {"series": ["2023-25", "2026"], "format": "signed1", "values": True, "full_labels": True, "no_diff": True,
              "rows": rows},
             "Runs above par per 100 balls · top 8 of 10 sides in 2026")
    c["kicker"] = "The deeper cut"
    return c, {"rb": rb, "rn": rn, "b": b[T]["raa_per_100"], "n": n[T]["raa_per_100"], "wb": b[T]["wpa"], "wn": n[T]["wpa"]}


def styles_card(db):
    rows, raw = [], {}
    for lab, f in STYLES:
        pb = q(db, group_by=["bowling_team"], bowling_teams=[T], **period(BEFORE), **TOP10, **f)
        pn = q(db, group_by=["bowling_team"], bowling_teams=[T], **period(NOW), **TOP10, **f)
        if not pb or not pn or pn[0]["balls"] < 120 or pb[0]["balls"] < 120:
            continue
        raw[lab] = (pb[0], pn[0])
        rows.append({"label": lab, "a": round(pb[0]["raa_per_100"], 1), "b": round(pn[0]["raa_per_100"], 1),
                     "highlight": lab != "Pace"})
    spin_b = q(db, group_by=["bowling_team"], bowling_teams=[T], bowl_kind=["spin bowler"], **period(BEFORE), **TOP10)[0]
    spin_n = q(db, group_by=["bowling_team"], bowling_teams=[T], bowl_kind=["spin bowler"], **period(NOW), **TOP10)[0]
    c = card("styles", "pair_dumbbell",
             f"India's spin: {sg(spin_b['raa_per_100'])} runs above par per 100 balls in 2023-25, {sg(spin_n['raa_per_100'])} in 2026",
             {"series": ["2023-25", "2026"], "format": "signed1", "values": True, "full_labels": True, "no_diff": True,
              "rows": rows},
             "Runs above par per 100 balls, by style · v top-10 sides")
    c["kicker"] = "The spin edge"
    return c, {"spin_b": spin_b, "spin_n": spin_n, "raw": raw}


def lengths_card(db):
    def cells(p):
        rows = q(db, group_by=["line", "length"], bowling_teams=[T], **period(p), **TOP10)
        return {(r["line"], r["length"]): r for r in rows if r["line"] and r["length"]}
    b, n = cells(BEFORE), cells(NOW)
    tot_n = sum(r["balls"] for r in n.values())
    out = []
    for key, r in n.items():
        if key in b and key[0] in LINES and key[1] in LENGTHS and r["balls"] >= 15 and b[key]["balls"] >= 15:
            out.append({"line": key[0], "length": key[1], "value": round(econ(r) - econ(b[key]), 1), "balls": r["balls"]})
    big = max(out, key=lambda c_: c_["balls"])
    big["highlight"] = True
    lb = q(db, group_by=["length"], bowling_teams=[T], **period(BEFORE), **TOP10)
    ln = q(db, group_by=["length"], bowling_teams=[T], **period(NOW), **TOP10)
    share = lambda rows, L: 100 * sum(r["balls"] for r in rows if r["length"] == L) / sum(r["balls"] for r in rows if r["length"])  # noqa: E731
    gl_b = next(r for r in lb if r["length"] == "GOOD_LENGTH")
    gl_n = next(r for r in ln if r["length"] == "GOOD_LENGTH")
    c = card("lengths", "pitch_map",
             f"Fewer good-length balls ({share(ln, 'GOOD_LENGTH'):.0f}%, from {share(lb, 'GOOD_LENGTH'):.0f}%), and they cost "
             f"{econ(gl_n):.1f} an over, from {econ(gl_b):.1f}",
             {"hand": "RHB", "lines": LINES, "lengths": LENGTHS, "min_balls": 15,
              "metric": {"label": "Runs an over, change on 2023-25", "format": "signed1", "higher_better": False, "mid": 0},
              "legend": ["Cheaper for India", "Costlier for India"], "cells": out},
             "Change in runs an over, 2026 v 2023-25 · 15+ balls a cell")
    c["kicker"] = "Where it lands"
    return c, {"gl_share": (share(lb, "GOOD_LENGTH"), share(ln, "GOOD_LENGTH")), "gl_econ": (econ(gl_b), econ(gl_n))}


def overs_card(db):
    def by_over(p):
        return {r["over"]: econ(r) for r in q(db, group_by=["over"], bowling_teams=[T], **period(p), **TOP10)}
    b, n = by_over(BEFORE), by_over(NOW)
    death_b = q(db, group_by=["phase"], bowling_teams=[T], **period(BEFORE), **TOP10)
    death_n = q(db, group_by=["phase"], bowling_teams=[T], **period(NOW), **TOP10)
    db_ = econ(next(r for r in death_b if r["phase"] == "death"))
    dn = econ(next(r for r in death_n if r["phase"] == "death"))
    c = card("overs", "metric_lines",
             f"Overs 16-20: India go at {dn:.1f} an over in 2026, from {db_:.1f}",
             {"x": {"label": "over", "ticks": [1, 6, 10, 15, 20]}, "y": {"label": "runs an over", "format": "dec1"},
              "series": [{"name": "2026", "highlight": True, "points": [{"x": o + 1, "y": round(v, 2)} for o, v in sorted(n.items())]},
                         {"name": "2023-25", "points": [{"x": o + 1, "y": round(v, 2)} for o, v in sorted(b.items())]}]},
             "Runs an over, by over · India v top-10 sides")
    c["kicker"] = "Over by over"
    return c, {"death": (db_, dn)}


def control_card(db):
    rows = []
    vals = {}
    for p, lab in ((BEFORE, "2023-25"), (NOW, "2026")):
        for r in q(db, group_by=["phase"], bowling_teams=[T], **period(p), **TOP10):
            vals[(lab, r["phase"])] = 100 - r["control_percentage"]
    for ph, name in (("powerplay", "Powerplay"), ("middle", "Middle overs"), ("death", "Death")):
        rows.append({"label": name, "a": round(vals[("2023-25", ph)], 1), "b": round(vals[("2026", ph)], 1)})
    tb = q(db, group_by=["bowling_team"], bowling_teams=[T], **period(BEFORE), **TOP10)[0]
    tn = q(db, group_by=["bowling_team"], bowling_teams=[T], **period(NOW), **TOP10)[0]
    fb, fn = 100 - tb["control_percentage"], 100 - tn["control_percentage"]
    c = card("control", "pair_dumbbell",
             f"Fewer false shots against India: {fn:.1f}% of balls in 2026, from {fb:.1f}%",
             {"series": ["2023-25", "2026"], "format": "dec1", "values": True, "full_labels": True, "no_diff": True,
              "rows": rows},
             "False shots per 100 balls · India v top-10 sides")
    c["kicker"] = "Fewer chances"
    return c, {"fb": fb, "fn": fn}


def build(db):
    lead, tn = totals_card(db)
    rates, rn = rates_card(db)
    par, pn = par_card(db)
    styles, sn = styles_card(db)
    lengths, ln = lengths_card(db)
    overs, on = overs_card(db)
    control, cn = control_card(db)
    return {"lead": lead, "cards": [rates, par, styles, lengths, overs, control],
            "tn": tn, "rn": rn, "pn": pn, "sn": sn, "ln": ln, "on": on, "cn": cn}


def copy(b):
    tn, rn, pn, sn, ln, on, cn = (b[k] for k in ("tn", "rn", "pn", "sn", "ln", "on", "cn"))
    rn = {"All top-10 sides": rn["All"], "India conceding": rn["India bowl"], "India scoring": rn["India bat"]}
    hook = f"New Zealand made 259 today. {tn['in_2026']} of India's 6 biggest T20I totals conceded came in 2026"
    a, i, s = rn["All top-10 sides"], rn["India conceding"], rn["India scoring"]
    caption = "\n\n".join([
        f"New Zealand's 259 in Auckland today is the most India have conceded in a T20I and New Zealand's highest "
        f"total. It isn't in our ball-by-ball data yet, but the pattern is: {tn['in_2026']} of the 6 biggest totals "
        "against India before today came in 2026.",
        f"Part of it is the era: T20Is between top-10 sides have gone at {a[2026]:.1f} an over in 2026, from "
        f"{a[2025]:.1f} in 2025. India's bowling has gone at {i[2026]:.1f}, from {i[2025]:.1f}.",
        f"Part of it is India: on runs above par per 100 balls (adjusted for the match situation), their bowling was "
        f"{'the best' if pn['rb'] == 1 else f'{pn[chr(114)+chr(98)]}th'} of the top 10 sides in 2023-25 and is {pn['rn']}th "
        f"in 2026. The biggest change is spin: {sg(sn['spin_b']['raa_per_100'])} runs above par per 100 balls, now "
        f"{sg(sn['spin_n']['raa_per_100'])}.",
        f"Fewer good-length balls ({ln['gl_share'][1]:.0f}%, from {ln['gl_share'][0]:.0f}%), and they cost "
        f"{ln['gl_econ'][1]:.1f} an over, from {ln['gl_econ'][0]:.1f}. Overs 16-20: {on['death'][1]:.1f} an over, from "
        f"{on['death'][0]:.1f}. Batters play false shots less often: {cn['fn']:.1f}% of balls, from {cn['fb']:.1f}%.",
        f"And India still win: they score at {s[2026]:.1f} an over this year, faster than any other top-10 side.",
        "T20Is between top-10 sides, to 24 Oct 2026. Runs above par and wins added: T20 Primer method. Ball-by-ball "
        "data: Himanish Ganjoo & TechRadar, Cricsheet.",
        "Is 250 the new par?",
        "Free ball-by-ball cricket stats: link in bio.\n.\n#NZvIND #TeamIndia #T20I #cricket",
    ])
    return hook, caption


def thread(b, link):
    tn, rn, pn, sn, ln, on, cn = (b[k] for k in ("tn", "rn", "pn", "sn", "ln", "on", "cn"))
    a, i, s = rn["All"], rn["India bowl"], rn["India bat"]
    texts = [
        f"New Zealand made 259 today, the most India have conceded in a T20I. It's not a one-off: {tn['in_2026']} of the 6 "
        f"biggest totals against India before today came in 2026. 🧵",
        f"The era first: T20Is between top-10 sides go at {a[2026]:.1f} an over in 2026, from {a[2025]:.1f} last year. India "
        f"concede {i[2026]:.1f}, from {i[2025]:.1f}. They score {s[2026]:.1f}, faster than any other top-10 side.",
        f"On runs above par (adjusted for the match situation), India's bowling was {'the best' if pn['rb'] == 1 else str(pn['rb']) + 'th'} "
        f"of the top 10 sides in 2023-25. In 2026: {pn['rn']}th.",
        f"The biggest change is spin: {sg(sn['spin_b']['raa_per_100'])} runs above par per 100 balls in 2023-25, "
        f"{sg(sn['spin_n']['raa_per_100'])} in 2026.",
        f"Where it lands: fewer good-length balls ({ln['gl_share'][1]:.0f}%, from {ln['gl_share'][0]:.0f}%), and those cost "
        f"{ln['gl_econ'][1]:.1f} an over, from {ln['gl_econ'][0]:.1f}.",
        f"Over by over, the death is where it jumps: overs 16-20 at {on['death'][1]:.1f} an over, from {on['death'][0]:.1f}.",
        f"And batters are beaten less often: false shots on {cn['fn']:.1f}% of balls, from {cn['fb']:.1f}%. Fewer chances.",
        f"Is 250 the new par?\n\nEvery ball, free: {link}\nData: @himganj153 & @TechRadar9",
    ]
    from services.ig_x import hand_thread

    return hand_thread(texts, copy(b)[1], THREAD_PLAYERS)


def reel_script(b):
    tn, pn, sn, ln, on = (b[k] for k in ("tn", "pn", "sn", "ln", "on"))
    return {"hook": "New Zealand made 259 today. It's not a one-off.",
            "lines": [f"{tn['in_2026']} of the 6 biggest totals India have conceded in T20Is came this year.",
                      f"India's bowling was the best of the top 10 sides on runs above par. In 2026, it's {pn['rn']}th.",
                      "The biggest change is spin: from well above par to well below it.",
                      f"Fewer balls on a good length, and those cost {ln['gl_econ'][1]:.1f} an over, up from {ln['gl_econ'][0]:.1f}.",
                      f"And at the death, {on['death'][1]:.1f} an over, from {on['death'][0]:.1f}."]}


def slides_of(b, hook):
    from services.ig_cover import hero_from

    cover = {"type": "hook", "text": hook, "cover": "hero", "hero": {**hero_from(b["lead"]), "card": b["lead"]}}
    return ([cover] + [{"type": "card", "card": c, "teams": [T]} for c in b["cards"]]
            + [{"type": "end", "heading": "Is 250 the new par?",
                "body": "Every T20I, ball by ball, with runs above par and win probability: free on Hindsight."}])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--base", default=SITE)
    parser.add_argument("--thread-only", action="store_true", help="replace the queued pack's X thread, nothing else")
    args = parser.parse_args()
    if args.write:
        assert "localhost" not in os.environ.get("DATABASE_URL", ""), "--write is production: leave DATABASE_URL unset"
    from database import get_session
    from services.social_rules import findings, hook_problem, thread_problems

    db = next(get_session())
    b = build(db)
    hook, caption = copy(b)
    slides = slides_of(b, hook)
    print("HOOK:", hook, f"({len(hook)})")
    for n_, s in enumerate(slides, 1):
        c = s.get("card") or (s.get("hero") or {}).get("card") or {}
        print(f"  {n_}. [{c.get('visual') or s['type']}] {c.get('title') or s.get('heading')} ({len(c.get('title') or '')})")
    problems = findings(slides, "spotlight")
    hp = hook_problem(hook)
    print("lint:", problems or "clean", "| hook:", hp or "ok")
    print(caption)
    th = thread(b, "hindsightcricket.com")
    for t in th:
        print(f"--- tweet {t['n']} ({len(t['text'])})\n{t['text']}")
    tp = thread_problems(th, THREAD_PLAYERS)
    print("thread:", tp or "ok")
    if args.thread_only and not tp:
        from database import engine
        from services.ig_backlog import set_thread
        from services.ig_links import post_link

        with engine.begin() as conn:
            fact = conn.execute(text("SELECT facts FROM content_packs WHERE angle_key = :k"), {"k": f"ig:{KEY}"}).scalar()
            print("thread replaced:", set_thread(conn, KEY, thread(b, post_link(fact))), "pack")
        return 0
    (HERE / "reel.json").write_text(json.dumps(reel_script(b), indent=1))
    print("REEL:", json.dumps(reel_script(b)))
    (HERE / "slides.json").write_text(json.dumps({"slides": slides, "hook": hook, "caption": caption, "x": th},
                                                 default=str, indent=1))
    if problems or hp or tp or not args.write:
        return 1 if (problems or hp or tp) else 0

    from database import engine
    from services import ig_backlog, ig_carousel, ig_slides
    from services.ig_links import post_link
    from services.ig_notes import youtube_copy

    carousel = ig_carousel.save(db, slides, hook, {"spotlight": KEY}, "ig-spotlight")
    n = len(slides)
    fact = {"kind": "spotlight", "title": hook, "hook": hook, "subject": T, "subject_role": "team",
            "carousel_id": carousel["id"], "slides": n, "render": True, "post_time": "8 pm"}
    fact["x"] = thread(b, post_link(fact))
    fact["youtube"] = youtube_copy(fact, caption, hook)
    ist = timezone(timedelta(hours=5, minutes=30))
    today = datetime.now(ist).date()
    post = {"key": KEY, "pillar": "reactive", "fact": fact, "snapshot_id": carousel["id"], "warnings": [],
            "players": [], "caption": caption}
    with engine.begin() as conn:
        ig_backlog.upsert_pack(conn, post, today, source="hand", post_by=datetime.combine(today, time.max, tzinfo=ist))
    print(f"queued ig:{KEY} for {today} · carousel {carousel['id']} ({n} slides)")
    r = ig_slides.render(carousel["id"], n, args.base)
    print(f"rendered {len(r['ok'])}/{n}" + (f", failed {r['failed']}" if r["failed"] else "") + f"; layout {r.get('layout') or 'clean'}")
    # Reels are always voiced (the user's rule): the hand script replaces whatever the render stored.
    env = {**os.environ, "REEL_V2": "1", "REEL_AB": "0"}
    done = subprocess.run([sys.executable, str(ROOT / "scripts/make_reel_v2.py"), "--key", f"ig:{KEY}", "--beats", "1,3,4,5,6",
                           "--script", str(HERE / "reel.json"), "--close", "Is 250 the new par?", "--base", args.base,
                           "--store"], env=env, capture_output=True, text=True)
    ok = "stored as the post's Reel" in done.stdout
    print("voiced Reel:", "stored" if ok else f"FAILED\n{done.stderr[-800:]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
