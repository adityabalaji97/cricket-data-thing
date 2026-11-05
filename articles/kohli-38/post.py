"""
Virat Kohli at 38 (his birthday, 5 Nov 2026): faster than in any year of his ODI career. ODI strike rate by year since
2008, then 2022-25 ("then") against 2026 to 3 Nov ("now"): by length against pace and spin, scoring zones, shots, line
and length, and false shots. Every number from the query builder; the 2026 shot names match 2022-25's (both the
current tagging). The Eden Park ODI of 4 Nov (74 off 51) hadn't reached the data: credited text in the caption.

    python articles/kohli-38/post.py [--write --date 2026-11-05]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

KEY = "spotlight-kohli-38-2026-11-05"
SITE = "https://hindsightcricket.com"
P = "Virat Kohli"
ODI = {"fmt": "ODI", "include_international": True, "leagues": [], "batters": [P], "metrics_perspective": "batting", "limit": 1000}
THEN = {"start_date": date(2022, 1, 1), "end_date": date(2025, 12, 31)}
NOW = {"start_date": date(2026, 1, 1), "end_date": date(2026, 11, 3)}
LINES = ["WIDE_OUTSIDE_OFFSTUMP", "OUTSIDE_OFFSTUMP", "ON_THE_STUMPS", "DOWN_LEG"]
LENGTHS = ["YORKER", "FULL", "GOOD_LENGTH", "SHORT_OF_A_GOOD_LENGTH", "SHORT"]
TODAY = ("At Eden Park on 4 Nov, after these numbers: 74 off 51, with 13 fours, as India won by five wickets. "
         "Scorecard: ESPNcricinfo.")


def sg(v, d=0):
    return f"{v:+.{d}f}".replace("-", "−")


def card(cid, visual, title, payload, sample, kicker=None):
    assert len(title) <= 80, (len(title), title)
    c = {"id": cid, "visual": visual, "title": title, "help": "", "sample": sample, "payload": payload}
    if kicker:
        c["kicker"] = kicker
    return c


def q(db, **kw):
    from services.query_builder_v2 import run_deliveries_query

    return run_deliveries_query(db, **{**ODI, **kw})["data"]


def sr(r):
    return 100 * r["runs"] / r["balls"] if r and r.get("balls") else None


def build(db):
    years = sorted(q(db, start_date=date(2008, 1, 1), end_date=NOW["end_date"], group_by=["year"]), key=lambda r: r["year"])
    years = [r for r in years if r["balls"] >= 150]   # 2021 and 2024 were a handful of games
    now_y = next(r for r in years if r["year"] == 2026)
    prev_best = max((r for r in years if r["year"] != 2026), key=sr)
    assert sr(now_y) > sr(prev_best)
    lead = card("years", "metric_lines",
                f"Kohli's ODI strike rate: {sr(now_y):.0f} in 2026, his fastest year. Before: {sr(prev_best):.0f} in {prev_best['year']}",
                {"x": {"label": "", "ticks": [2010, 2014, 2018, 2022, 2026]}, "y": {"label": "Strike rate", "format": "int", "zero": False},
                 "series": [{"name": "Kohli", "points": [{"x": r["year"], "y": round(sr(r))} for r in years], "highlight": True}]},
                f"ODIs, years with 150+ balls · 2026 to 3 Nov: {now_y['innings_count']} innings, {now_y['balls']} balls")

    def by(group, w, **kw):
        return q(db, group_by=group, **w, **kw)

    kind_t = {r["bowl_kind"]: r for r in by(["bowl_kind"], THEN)}
    kind_n = {r["bowl_kind"]: r for r in by(["bowl_kind"], NOW)}
    len_t = {(r["bowl_kind"], r["length"]): r for r in by(["bowl_kind", "length"], THEN)}
    len_n = {(r["bowl_kind"], r["length"]): r for r in by(["bowl_kind", "length"], NOW)}
    K = {"pace bowler": "pace", "spin bowler": "spin"}
    rows2 = []
    for k in ("spin bowler", "pace bowler"):
        rows2.append({"label": f"v {K[k]}, all balls", "a": round(sr(kind_t[k])), "b": round(sr(kind_n[k]))})
        rows2.append({"label": f"v {K[k]}, good length", "a": round(sr(len_t[(k, 'GOOD_LENGTH')])), "b": round(sr(len_n[(k, 'GOOD_LENGTH')])),
                      "highlight": k == "spin bowler"})
    gs_t, gs_n = sr(len_t[("spin bowler", "GOOD_LENGTH")]), sr(len_n[("spin bowler", "GOOD_LENGTH")])
    c2 = card("length", "pair_dumbbell", f"Off good-length spin he scores at {gs_n:.0f}, from {gs_t:.0f}. Against pace: {sr(len_t[('pace bowler', 'GOOD_LENGTH')]):.0f} to {sr(len_n[('pace bowler', 'GOOD_LENGTH')]):.0f}",
              {"series": ["2022-25", "2026"], "format": "int", "values": True, "full_labels": True, "no_diff": True, "rows": rows2},
              f"ODI strike rate · good length: {len_n[('spin bowler', 'GOOD_LENGTH')]['balls']} spin balls in 2026", kicker="Then and now")

    def zones(w, k):
        z = {int(r["wagon_zone"]): r["runs"] for r in by(["wagon_zone"], w, bowl_kind=[k]) if r.get("wagon_zone") and 1 <= int(r["wagon_zone"]) <= 8}
        t = sum(z.values())
        return {zz: round(100 * v / t) for zz, v in sorted(z.items())}
    zs_t, zs_n = zones(THEN, "spin bowler"), zones(NOW, "spin bowler")
    zp_t, zp_n = zones(THEN, "pace bowler"), zones(NOW, "pace bowler")
    straight = lambda z: z.get(4, 0) + z.get(5, 0)  # noqa: E731
    behind_off = lambda z: z.get(7, 0) + z.get(8, 0)  # noqa: E731
    leg = lambda z: sum(z.get(i, 0) for i in (1, 2, 3, 4))  # noqa: E731
    c3 = card("zones-spin", "zone_pair", f"Against spin he goes straighter: {straight(zs_n)}% of his runs down the ground, from {straight(zs_t)}%",
              {"hand": "RHB", "highlight": [4, 5], "note": "Share of runs v spin · outlined: long on and long off",
               "pair": [{"label": "2022-25", "zones": zs_t}, {"label": "2026", "zones": zs_n}]},
              "ODIs · v spin · share of runs by scoring zone", kicker="Where he scores v spin")
    c4 = card("zones-pace", "zone_pair", f"Off-side dab gone v pace: {behind_off(zp_n)}% of his runs behind square, from {behind_off(zp_t)}%",
              {"hand": "RHB", "highlight": [7, 8], "note": f"Share of runs v pace · leg side: {leg(zp_t)}% then, {leg(zp_n)}% now",
               "pair": [{"label": "2022-25", "zones": zp_t}, {"label": "2026", "zones": zp_n}]},
              "ODIs · v pace · share of runs by scoring zone", kicker="Where he scores v pace")

    def shares(w, k):
        rows = by(["shot"], w, bowl_kind=[k])
        tot = sum(r["balls"] for r in rows)
        return {r["shot"]: (100 * r["balls"] / tot, sr(r)) for r in rows if r.get("shot")}
    sh = {("pace", "t"): shares(THEN, "pace bowler"), ("pace", "n"): shares(NOW, "pace bowler"),
          ("spin", "t"): shares(THEN, "spin bowler"), ("spin", "n"): shares(NOW, "spin bowler")}
    picks = [("pace", "PULL", "Pull v pace"), ("spin", "ON_DRIVE", "On drive v spin"), ("spin", "DEFENDED", "Defended v spin"),
             ("pace", "STEERED", "Steer v pace")]
    rows5 = [{"label": lab, "a": round(sh[(k, "t")].get(s, (0, 0))[0], 1), "b": round(sh[(k, "n")].get(s, (0, 0))[0], 1),
              "highlight": s == "PULL"} for k, s, lab in picks]
    pull_n = sh[("pace", "n")]["PULL"]
    c5 = card("shots", "pair_dumbbell", f"The pull is back: {pull_n[0]:.0f}% of balls from pace, from {sh[('pace', 't')]['PULL'][0]:.0f}%, at a strike rate of {pull_n[1]:.0f}",
              {"series": ["2022-25", "2026"], "format": "pct1", "values": True, "full_labels": True, "no_diff": True, "rows": rows5},
              "ODIs · share of balls he plays each shot", kicker="The shots")

    ll_t = {(r["line"], r["length"]): r for r in by(["line", "length"], THEN) if r.get("line")}
    ll_n = {(r["line"], r["length"]): r for r in by(["line", "length"], NOW) if r.get("line")}
    cells = [{"line": k[0], "length": k[1], "value": round(sr(r) - sr(ll_t[k])), "balls": r["balls"]}
             for k, r in ll_n.items() if k[0] in LINES and k[1] in LENGTHS and r["balls"] >= 20 and ll_t.get(k, {}).get("balls", 0) >= 60]
    best = max(cells, key=lambda c: c["value"])
    LW = {"WIDE_OUTSIDE_OFFSTUMP": "wide outside off", "OUTSIDE_OFFSTUMP": "outside off", "ON_THE_STUMPS": "on the stumps", "DOWN_LEG": "down leg"}
    LN = {"YORKER": "yorker", "FULL": "full", "GOOD_LENGTH": "good length", "SHORT_OF_A_GOOD_LENGTH": "back of a length", "SHORT": "short"}
    c6 = card("pitch", "pitch_map", f"Biggest jump: {LN[best['length']]} {LW[best['line']]}, {sg(best['value'])} strike rate on 2022-25",
              # Only the lines and lengths with a cell: empty rows push the map out of its card.
              {"hand": "RHB", "lines": [l_ for l_ in LINES if any(c["line"] == l_ for c in cells)],
               "lengths": [l_ for l_ in LENGTHS if any(c["length"] == l_ for c in cells)], "min_balls": 20,
               "metric": {"label": "Strike rate, 2026 v 2022-25", "format": "signed0", "higher_better": True, "mid": 0},
               "legend": ["Faster in 2026", "Slower"], "cells": cells},
              "ODIs, pace and spin · 20+ balls a cell in 2026", kicker="Line and length")

    ctl = lambda r: 100 - r["control_percentage"]  # noqa: E731
    rows7 = [{"label": f"v {K[k]}", "a": round(ctl(kind_t[k])), "b": round(ctl(kind_n[k])), "highlight": k == "spin bowler"}
             for k in ("spin bowler", "pace bowler")]
    c7 = card("both", "pair_dumbbell",
              f"Both ways: it's {now_y['innings_count']} innings. But his false shots fell too: {ctl(kind_n['spin bowler']):.0f}% v spin, from {ctl(kind_t['spin bowler']):.0f}%",
              {"series": ["2022-25", "2026"], "format": "pct0", "values": True, "full_labels": True, "no_diff": True, "rows": rows7},
              f"Balls he edged, missed or mistimed · 2026: {now_y['balls']} balls", kicker="Both ways")
    return {"lead": lead, "cards": [c2, c3, c4, c5, c6, c7], "now": now_y, "prev": prev_best, "gs": (gs_t, gs_n),
            "zs": (straight(zs_t), straight(zs_n)), "zp": (behind_off(zp_t), behind_off(zp_n)), "pull": (sh[("pace", "t")]["PULL"], pull_n),
            "best": best, "LW": LW, "LN": LN, "ctl": (ctl(kind_t["spin bowler"]), ctl(kind_n["spin bowler"])), "years": years}


def copy(b):
    n, pv = b["now"], b["prev"]
    hook = f"Virat Kohli turns 38 today, and he's scoring faster than in any year of his ODI career: strike rate {sr(n):.0f} in 2026."
    caption = "\n\n".join([
        f"Virat Kohli turns 38 today. His ODI strike rate this year is {sr(n):.0f}, the highest of any year of his career "
        f"(before this: {sr(pv):.0f}, in {pv['year']}), and only {n['dot_percentage']:.0f}% of his balls have been dots, his fewest.",
        f"What changed, 2022-25 against 2026: off good-length spin he scores at {b['gs'][1]:.0f}, from {b['gs'][0]:.0f}. Against spin "
        f"he goes straighter: {b['zs'][1]}% of his runs down the ground, from {b['zs'][0]}%. Against pace the pull is back "
        f"({b['pull'][1][0]:.0f}% of balls, from {b['pull'][0][0]:.0f}%, at a strike rate of {b['pull'][1][1]:.0f}) and the off-side "
        f"dab has gone: {b['zp'][1]}% of his runs behind square on the off side, from {b['zp'][0]}%.",
        f"Both ways: 2026 is {n['innings_count']} innings and {n['balls']} balls. But it isn't riskier: his false shots against "
        f"spin fell to {b['ctl'][1]:.0f}%, from {b['ctl'][0]:.0f}%.",
        TODAY,
        "ODIs only, to 3 Nov 2026. Ball-by-ball data: Himanish Ganjoo & TechRadar, Cricsheet.",
        "Happy birthday, Virat. What's his best ODI innings?",
        "Free ball-by-ball cricket stats: link in bio.\n.\n#ViratKohli #HappyBirthdayViratKohli #King #TeamIndia #NZvIND",
    ])
    return hook, caption


def thread(b, link):
    n, pv = b["now"], b["prev"]
    texts = [
        f"Virat Kohli turns 38 today and is scoring faster than in any year of his ODI career: strike rate {sr(n):.0f} in 2026. "
        f"His best before: {sr(pv):.0f}, in {pv['year']}. 🧵",
        f"Off good-length spin: {b['gs'][1]:.0f}, from {b['gs'][0]:.0f} in 2022-25. And straighter: {b['zs'][1]}% of his runs v spin down the ground, from {b['zs'][0]}%.",
        f"Against pace the pull is back: {b['pull'][1][0]:.0f}% of balls, from {b['pull'][0][0]:.0f}%, at a strike rate of {b['pull'][1][1]:.0f}. "
        f"Off-side runs behind square: {b['zp'][1]}%, from {b['zp'][0]}%.",
        f"Both ways: {n['innings_count']} innings. But his false shots v spin fell to {b['ctl'][1]:.0f}%, from {b['ctl'][0]:.0f}%.",
        "At Eden Park yesterday, after these numbers: 74 off 51.",
        f"Happy birthday, Virat.\n\nEvery ball, free: {link}\nData: @himganj153 & @TechRadar9",
    ]
    from services.ig_x import hand_thread

    return hand_thread(texts, copy(b)[1], [P])


def reel_script(b):
    n, pv = b["now"], b["prev"]
    return {"hook": f"Virat Kohli turns 38 today, and he's scoring faster than ever: an ODI strike rate of {sr(n):.0f} this year.",
            "lines": [f"His best before was {sr(pv):.0f}, in {pv['year']}.",
                      f"Off good-length spin, he scores at {b['gs'][1]:.0f}, up from {b['gs'][0]:.0f}.",
                      "Against spin, more of his runs go straight down the ground.",
                      f"And against pace, the pull is back: {b['pull'][1][0]:.0f} percent of balls, at a strike rate of {b['pull'][1][1]:.0f}.",
                      f"He isn't riskier, either: fewer false shots against spin. Happy birthday, Virat."]}


def slides_of(b, hook):
    lead = b["lead"]
    cover = {"type": "hook", "text": hook, "cover": "hero",
             "hero": {"kind": "visual", "visual": lead["visual"], "payload": lead["payload"], "label": "", "card": lead}}
    return ([cover] + [{"type": "card", "card": c, "teams": ["India"]} for c in b["cards"]]
            + [{"type": "end", "heading": "Happy birthday, Virat", "body": "Every ODI ball since 2000, with line, length and scoring zones: free on Hindsight."}])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--base", default=SITE)
    ap.add_argument("--date", default="2026-11-05")
    args = ap.parse_args()
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
    problems, hp = findings(slides, "spotlight"), hook_problem(hook)
    print("lint:", problems or "clean", "| hook:", hp or "ok")
    print(caption)
    th = thread(b, "hindsightcricket.com")
    for t in th:
        print(f"--- tweet {t['n']} ({len(t['text'])})\n{t['text']}")
    tp = thread_problems(th, [P])
    print("thread:", tp or "ok")
    (HERE / "reel.json").write_text(json.dumps(reel_script(b), indent=1))
    (HERE / "slides.json").write_text(json.dumps({"slides": slides, "hook": hook, "caption": caption, "x": th}, default=str, indent=1))
    print("REEL:", json.dumps(reel_script(b)))
    if problems or hp or tp or not args.write:
        return 1 if (problems or hp or tp) else 0

    from database import engine
    from services import ig_backlog, ig_carousel, ig_slides
    from services.ig_links import post_link
    from services.ig_notes import youtube_copy

    carousel = ig_carousel.save(db, slides, hook, {"spotlight": KEY}, "ig-spotlight")
    n = len(slides)
    fact = {"kind": "spotlight", "title": hook, "hook": hook, "subject": P, "subject_role": "batter",
            "carousel_id": carousel["id"], "slides": n, "render": True, "post_time": "8 pm"}
    fact["x"] = thread(b, post_link(fact))
    fact["youtube"] = youtube_copy(fact, caption, hook)
    ist = timezone(timedelta(hours=5, minutes=30))
    day = date.fromisoformat(args.date)
    post = {"key": KEY, "pillar": "reactive", "fact": fact, "snapshot_id": carousel["id"], "warnings": [], "players": [P], "caption": caption}
    with engine.begin() as conn:
        ig_backlog.upsert_pack(conn, post, day, source="hand", post_by=datetime.combine(day, time.max, tzinfo=ist))
    print(f"queued ig:{KEY} for {day} · carousel {carousel['id']} ({n} slides)")
    r = ig_slides.render(carousel["id"], n, args.base)
    print(f"rendered {len(r['ok'])}/{n}" + (f", failed {r['failed']}" if r["failed"] else "") + f"; layout {r.get('layout') or 'clean'}")
    env = {**os.environ, "REEL_V2": "1", "REEL_AB": "0"}
    done = subprocess.run([sys.executable, str(ROOT / "scripts/make_reel_v2.py"), "--key", f"ig:{KEY}", "--beats", "1,2,3,5,7",
                           "--script", str(HERE / "reel.json"), "--close", "", "--base", args.base, "--store"],
                          env=env, capture_output=True, text=True)
    ok = "stored as the post's Reel" in done.stdout
    print("voiced Reel:", "stored" if ok else f"FAILED\n{done.stdout[-1500:]}\n{done.stderr[-1500:]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
