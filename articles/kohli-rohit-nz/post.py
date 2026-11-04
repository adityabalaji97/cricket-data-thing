"""
Kohli and Rohit in New Zealand, then and now (4 Nov 2026, the ODI series opener at Eden Park). Their ODI innings in New
Zealand before this tour (2009-2020) against 2026 so far: strike rate, how much New Zealand kept it on a good length,
what they scored off it, where their runs went (scoring zones), and false shots. Every number from the query builder:
their New Zealand innings by match id, everywhere else by window.

Shot names changed between eras (2014-20 "leg glance", "off-side drive on front foot"; now "flick", "on drive"), so
shot mixes aren't compared across years; scoring zones and lengths are recorded the same way throughout.

    python articles/kohli-rohit-nz/post.py                     # dry run, data to 3 Nov
    python articles/kohli-rohit-nz/post.py --through 2026-11-04 # with the Eden Park ODI, once it has landed
    python articles/kohli-rohit-nz/post.py --write [--base http://localhost:3000]
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

KEY = "spotlight-kohli-rohit-nz-2026-11-04"
SITE = "https://hindsightcricket.com"
ROHIT, KOHLI = "Rohit Sharma", "Virat Kohli"
PLAYERS = [ROHIT, KOHLI]
THREAD_PLAYERS = [ROHIT, KOHLI]
ODI = {"fmt": "ODI", "include_international": True, "leagues": [], "metrics_perspective": "batting", "limit": 1000}
ELSEWHERE = (date(2014, 1, 1), date(2020, 12, 31))
# The opener at Eden Park, 4 Nov 2026, before it reached the ball-by-ball data: credited text, never charted
# (docs/social_rules.md). ESPNcricinfo scorecard, match 1539437.
TODAY = ("Today at Eden Park: Rohit 0 off 6, caught off Jamieson in the first over; Kohli 74 off 51 with 13 fours as "
         "India chased 143 (DLS) to win by five wickets. Scorecard: ESPNcricinfo.")   # the years of their New Zealand tours with ball tracking
LEN_KEYS = ("YORKER", "FULL", "GOOD_LENGTH", "SHORT_OF_A_GOOD_LENGTH", "SHORT", "FULL_TOSS")


def sg(v, d=0):
    return f"{v:+.{d}f}".replace("-", "−")


def both(a, b):
    """"49% and 49%" reads oddly: one number when the two round the same."""
    return f"{a:.0f}% for both" if round(a) == round(b) else f"{a:.0f}% and {b:.0f}%"


def card(cid, visual, title, payload, sample, kicker=None):
    assert len(title) <= 80, (len(title), title)
    c = {"id": cid, "visual": visual, "title": title, "help": "", "sample": sample, "payload": payload}
    if kicker:
        c["kicker"] = kicker
    return c


def q(db, **kw):
    from services.query_builder_v2 import run_deliveries_query

    return run_deliveries_query(db, **{**ODI, **kw})["data"]


def nz_ids(db):
    """Their ODIs in New Zealand before this tour."""
    from sqlalchemy import text

    return [r[0] for r in db.execute(text("""
        SELECT DISTINCT p_match FROM delivery_details WHERE format = 'ODI' AND gender = 'male' AND country = 'New Zealand'
          AND year <= 2020 AND bat = ANY(:p)"""), {"p": PLAYERS})]


def windows(db, through: date):
    ids = nz_ids(db)
    return {"nz": dict(match_ids=ids, start_date=date(2008, 1, 1), end_date=date(2020, 12, 31)),
            "all": dict(start_date=ELSEWHERE[0], end_date=ELSEWHERE[1]),
            "now": dict(start_date=date(2026, 1, 1), end_date=through)}


def player(db, p, W):
    d = {}
    for w, f in W.items():
        o = q(db, batters=[p], group_by=["batter"], **f)[0]
        L = {r["length"]: r for r in q(db, batters=[p], group_by=["length"], **f) if r.get("length") in LEN_KEYS}
        tagged = sum(r["balls"] for r in L.values())
        good = L.get("GOOD_LENGTH", {"balls": 0, "runs": 0})
        Z = {int(r["wagon_zone"]): r["runs"] for r in q(db, batters=[p], group_by=["wagon_zone"], **f)
             if r.get("wagon_zone") and 1 <= int(r["wagon_zone"]) <= 8}
        zt = sum(Z.values())
        d[w] = {"innings": o["innings_count"], "runs": o["runs"], "balls": o["balls"], "sr": o["strike_rate"],
                "false_shots": 100 - o["control_percentage"], "good_share": 100 * good["balls"] / tagged if tagged else None,
                "good_sr": 100 * good["runs"] / good["balls"] if good["balls"] else None, "good_balls": good["balls"],
                "tagged": tagged, "zones": {z: round(100 * r / zt) for z, r in sorted(Z.items())}}
    return d


def hundreds_in_nz(db, p, ids):
    rows = q(db, batters=[p], match_ids=ids, start_date=date(2008, 1, 1), end_date=date(2020, 12, 31), group_by=["match_id"])
    return sum(1 for r in rows if (r.get("runs") or 0) >= 100), max(r["runs"] for r in rows)


# ---- slides -----------------------------------------------------------------------------------------------------

def build(db, through: date):
    W = windows(db, through)
    d = {p: player(db, p, W) for p in PLAYERS}
    r, k = d[ROHIT], d[KOHLI]
    ids = W["nz"]["match_ids"]
    r100, rbest = hundreds_in_nz(db, ROHIT, ids)
    k100, kbest = hundreds_in_nz(db, KOHLI, ids)
    assert r100 == 0, "Rohit has an ODI hundred in New Zealand now"
    yr = f"2026 to {through.day} {through.strftime('%b')}"

    lead = card("rates", "pair_dumbbell",
                f"In New Zealand they scored at {r['nz']['sr']:.0f} and {k['nz']['sr']:.0f}. This year: {r['now']['sr']:.0f} and {k['now']['sr']:.0f}",
                {"series": ["In New Zealand", "2026"], "format": "int", "values": True, "full_labels": True, "no_diff": True,
                 "rows": [{"label": "Rohit Sharma", "a": round(r["nz"]["sr"]), "b": round(r["now"]["sr"]), "highlight": True},
                          {"label": "Virat Kohli", "a": round(k["nz"]["sr"]), "b": round(k["now"]["sr"])}]},
                f"ODI strike rate · New Zealand: {r['nz']['innings']} innings each, 2009-20 · {yr}")

    good = card("good-length", "pair_dumbbell",
                f"New Zealand kept it on a good length: {k['nz']['good_share']:.0f}% of Kohli's balls, "
                f"{k['all']['good_share']:.0f}% everywhere",
                {"series": ["All ODIs 2014-20", "In New Zealand"], "format": "pct0", "values": True, "full_labels": True, "no_diff": True,
                 "rows": [{"label": "Rohit Sharma", "a": round(r["all"]["good_share"]), "b": round(r["nz"]["good_share"])},
                          {"label": "Virat Kohli", "a": round(k["all"]["good_share"]), "b": round(k["nz"]["good_share"]), "highlight": True}]},
                f"Good-length share of tracked balls · {r['nz']['tagged']} and {k['nz']['tagged']} in New Zealand",
                kicker="What they bowled")

    off_good = card("off-good", "pair_dumbbell",
                    f"Off a good length in New Zealand they scored at {r['nz']['good_sr']:.0f} and {k['nz']['good_sr']:.0f}. "
                    f"Now: {r['now']['good_sr']:.0f} and {k['now']['good_sr']:.0f}",
                    {"series": ["In New Zealand", "2026"], "format": "int", "values": True, "full_labels": True, "no_diff": True,
                     "rows": [{"label": "Rohit Sharma", "a": round(r["nz"]["good_sr"]), "b": round(r["now"]["good_sr"])},
                              {"label": "Virat Kohli", "a": round(k["nz"]["good_sr"]), "b": round(k["now"]["good_sr"]), "highlight": True}]},
                    f"Strike rate off good-length balls · {r['nz']['good_balls']} and {k['nz']['good_balls']} balls in New Zealand",
                    kicker="What they made of it")

    def zone_card(cid, name, pd, hi, title, kicker):
        named = " and ".join({7: "point", 8: "third man"}[z] for z in hi)
        return card(cid, "zone_pair", title,
                    {"hand": "RHB", "highlight": hi, "note": f"Share of runs · outlined: {named} · leg side on the right",
                     "pair": [{"label": "In New Zealand", "zones": pd["nz"]["zones"]}, {"label": "2026", "zones": pd["now"]["zones"]}]},
                    f"{name} · ODIs in New Zealand 2009-20 v {yr}", kicker=kicker)

    k_behind = (k["nz"]["zones"].get(7, 0) + k["nz"]["zones"].get(8, 0), k["now"]["zones"].get(7, 0) + k["now"]["zones"].get(8, 0))
    assert k_behind[0] > k_behind[1]
    kz = zone_card("kohli-zones", "Virat Kohli", k, [7, 8],
                   f"Kohli's runs behind square on the off side: {k_behind[0]}% in New Zealand, {k_behind[1]}% this year",
                   "Where Kohli scores")
    r_pt = (r["nz"]["zones"].get(7, 0), r["now"]["zones"].get(7, 0))
    assert r_pt[1] > r_pt[0]
    rz = zone_card("rohit-zones", "Rohit Sharma", r, [7],
                   f"Rohit now scores square: {r_pt[1]}% of his runs through point, {r_pt[0]}% in New Zealand",
                   "Where Rohit scores")

    fs = card("false-shots", "pair_dumbbell",
              f"Both ways: Rohit's false shots are still {r['now']['false_shots']:.0f}%, as in New Zealand. Kohli's: "
              f"{k['now']['false_shots']:.0f}%",
              {"series": ["In New Zealand", "2026"], "format": "pct0", "values": True, "full_labels": True, "no_diff": True,
               "rows": [{"label": "Rohit Sharma", "a": round(r["nz"]["false_shots"]), "b": round(r["now"]["false_shots"]), "highlight": True},
                        {"label": "Virat Kohli", "a": round(k["nz"]["false_shots"]), "b": round(k["now"]["false_shots"])}]},
              "Balls they edged, missed or mistimed · lower is better", kicker="Both ways")
    return {"lead": lead, "cards": [good, off_good, kz, rz, fs], "d": d, "r100": r100, "rbest": rbest, "k100": k100,
            "kbest": kbest, "through": through}


def copy(b):
    r, k = b["d"][ROHIT], b["d"][KOHLI]
    hook = (f"Rohit Sharma has never made an ODI hundred in New Zealand: {r['nz']['runs']} runs in {r['nz']['innings']} "
            f"innings, at a strike rate of {r['nz']['sr']:.0f}.")
    kb = (k["nz"]["zones"].get(7, 0) + k["nz"]["zones"].get(8, 0), k["now"]["zones"].get(7, 0) + k["now"]["zones"].get(8, 0))
    caption = "\n\n".join([
        f"India's ODI series in New Zealand starts at Eden Park. The last time Rohit Sharma and Virat Kohli batted in an ODI "
        f"there was 2019 and 2020. Rohit made {r['nz']['runs']} runs in {r['nz']['innings']} innings in New Zealand at a strike "
        f"rate of {r['nz']['sr']:.0f}, best {b['rbest']}; Kohli {k['nz']['runs']} at {k['nz']['sr']:.0f}, with "
        f"{'one hundred' if b['k100'] == 1 else str(b['k100']) + ' hundreds'}. This year they're scoring at {r['now']['sr']:.0f} and {k['now']['sr']:.0f}.",
        f"What New Zealand bowled: a good length. {r['nz']['good_share']:.0f}% of Rohit's balls and {k['nz']['good_share']:.0f}% "
        f"of Kohli's, against {both(r['all']['good_share'], k['all']['good_share'])} in all their ODIs from 2014 to 2020. "
        f"Off those balls they scored at {r['nz']['good_sr']:.0f} and {k['nz']['good_sr']:.0f}; this year, "
        f"{r['now']['good_sr']:.0f} and {k['now']['good_sr']:.0f}.",
        f"Where the runs go has changed. Kohli scored {kb[0]}% of his New Zealand runs behind square on the off side; this "
        f"year {kb[1]}%. Rohit has gone square: {r['now']['zones'].get(7, 0)}% of his runs now come through point, from "
        f"{r['nz']['zones'].get(7, 0)}%.",
        TODAY,
        f"Both ways: Rohit still edges, misses or mistimes {r['now']['false_shots']:.0f}% of balls, as he did in New Zealand "
        f"({r['nz']['false_shots']:.0f}%). He's scoring faster off the same risk. Kohli is down to {k['now']['false_shots']:.0f}%.",
        "ODIs only. New Zealand: their innings there from 2009 to 2020 (line and length tracked from 2015). Ball-by-ball "
        "data: Himanish Ganjoo & TechRadar, Cricsheet.",
        "Will it be different this time?",
        "Free ball-by-ball cricket stats: link in bio.\n.\n#NZvIND #ViratKohli #RohitSharma #TeamIndia #CricketTwitter",
    ])
    return hook, caption


def thread(b, link):
    r, k = b["d"][ROHIT], b["d"][KOHLI]
    kb = (k["nz"]["zones"].get(7, 0) + k["nz"]["zones"].get(8, 0), k["now"]["zones"].get(7, 0) + k["now"]["zones"].get(8, 0))
    texts = [
        f"Rohit Sharma has never made an ODI hundred in New Zealand: {r['nz']['runs']} runs in {r['nz']['innings']} innings, "
        f"strike rate {r['nz']['sr']:.0f}. Kohli: {k['nz']['runs']} at {k['nz']['sr']:.0f}. This year they score at "
        f"{r['now']['sr']:.0f} and {k['now']['sr']:.0f}. 🧵",
        f"New Zealand kept it on a good length: {r['nz']['good_share']:.0f}% of Rohit's balls, {k['nz']['good_share']:.0f}% of "
        f"Kohli's, against {both(r['all']['good_share'], k['all']['good_share'])} everywhere in 2014-20.",
        f"Off a good length there they scored at {r['nz']['good_sr']:.0f} and {k['nz']['good_sr']:.0f}. This year: "
        f"{r['now']['good_sr']:.0f} and {k['now']['good_sr']:.0f}.",
        f"Kohli's runs behind square on the off side: {kb[0]}% in New Zealand, {kb[1]}% this year. Rohit's through point: "
        f"{r['nz']['zones'].get(7, 0)}% then, {r['now']['zones'].get(7, 0)}% now.",
        f"Both ways: Rohit still edges, misses or mistimes {r['now']['false_shots']:.0f}% of balls, as in New Zealand. Kohli is "
        f"down to {k['now']['false_shots']:.0f}%.",
        "Today at Eden Park: Rohit 0 off 6, caught off Jamieson. Kohli 74 off 51, 13 fours, as India won by five wickets.",
        f"Will it be different this time?\n\nEvery ball, free: {link}\nData: @himganj153 & @TechRadar9",
    ]
    from services.ig_x import hand_thread

    return hand_thread(texts, copy(b)[1], THREAD_PLAYERS)


def reel_script(b):
    """One line per beat (slides 1 to 6); the hook rides the first."""
    r, k = b["d"][ROHIT], b["d"][KOHLI]
    return {"hook": f"Rohit Sharma has never made an ODI hundred in New Zealand.",
            "lines": [f"There, he scored at {r['nz']['sr']:.0f}, Kohli at {k['nz']['sr']:.0f}. This year, {r['now']['sr']:.0f} and {k['now']['sr']:.0f}.",
                      f"New Zealand kept it on a good length: {k['nz']['good_share']:.0f}% of Kohli's balls.",
                      f"Off it, Kohli scored at {k['nz']['good_sr']:.0f}. This year, {k['now']['good_sr']:.0f}.",
                      "Kohli has stopped scoring behind square on the off side.",
                      "And Rohit now scores square, through point.",
                      f"But he still edges or misses {r['now']['false_shots']:.0f}% of balls."]}


def slides_of(b, hook):
    lead = b["lead"]
    cover = {"type": "hook", "text": hook, "cover": "hero",
             "hero": {"kind": "visual", "visual": lead["visual"], "payload": lead["payload"], "label": "", "card": lead}}
    return ([cover] + [{"type": "card", "card": c, "teams": ["India", "New Zealand"]} for c in b["cards"]]
            + [{"type": "end", "heading": "Will it be different this time?",
                "body": "Every ODI ball since 2000, with line, length and scoring zones: free on Hindsight."}])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--base", default=SITE)
    parser.add_argument("--through", default="2026-11-03", help="last day of 2026 counted (pinned, so a rerun can't drift)")
    parser.add_argument("--thread-only", action="store_true", help="replace the queued pack's X thread, nothing else")
    args = parser.parse_args()
    if args.write:
        assert "localhost" not in os.environ.get("DATABASE_URL", ""), "--write is production: leave DATABASE_URL unset"
    from sqlalchemy import text

    from database import get_session
    from services.social_rules import findings, hook_problem, thread_problems

    db = next(get_session())
    b = build(db, date.fromisoformat(args.through))
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
    fact = {"kind": "spotlight", "title": hook, "hook": hook, "subject": ROHIT, "subject_role": "batter",
            "carousel_id": carousel["id"], "slides": n, "render": True, "post_time": "8 pm"}
    fact["x"] = thread(b, post_link(fact))
    fact["youtube"] = youtube_copy(fact, caption, hook)
    ist = timezone(timedelta(hours=5, minutes=30))
    today = datetime.now(ist).date()
    post = {"key": KEY, "pillar": "reactive", "fact": fact, "snapshot_id": carousel["id"], "warnings": [],
            "players": THREAD_PLAYERS, "caption": caption}
    with engine.begin() as conn:
        ig_backlog.upsert_pack(conn, post, today, source="hand", post_by=datetime.combine(today, time.max, tzinfo=ist))
    print(f"queued ig:{KEY} for {today} · carousel {carousel['id']} ({n} slides)")
    r = ig_slides.render(carousel["id"], n, args.base)
    print(f"rendered {len(r['ok'])}/{n}" + (f", failed {r['failed']}" if r["failed"] else "") + f"; layout {r.get('layout') or 'clean'}")
    # Always the voiced Reel (the user's rule). The first beat is the cover (the chart the hook is about); --close is
    # spoken at the end of the last line.
    env = {**os.environ, "REEL_V2": "1", "REEL_AB": "0"}
    done = subprocess.run([sys.executable, str(ROOT / "scripts/make_reel_v2.py"), "--key", f"ig:{KEY}", "--beats", "1,2,3,4,5,6",
                           "--script", str(HERE / "reel.json"), "--close", "Will it be different this time?", "--base", args.base,
                           "--store"], env=env, capture_output=True, text=True)
    ok = "stored as the post's Reel" in done.stdout
    print("voiced Reel:", "stored" if ok else f"FAILED\n{done.stdout[-1500:]}\n{done.stderr[-1500:]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
