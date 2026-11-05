"""
#TopRightKohli (his birthday, 5 Nov 2026): the meme that Kohli sits in the top-right corner of any batting scatter, put
to six of them across ODIs and T20s. Each plot is checked before it goes in: nobody in the field beats him on both axes
(asserted), so "top right" is never a stretch. Six that hold:

* ODI runs v average (4,000+ runs, since 2000): first on both;
* ODI average v strike rate (same field);
* ODI chasing, average v strike rate (2,000+ runs in chases);
* ODI v spin, average v strike rate (1,500+ runs off spin);
* T20I chasing, average v wins added (700+ runs in chases);
* T20I average v wins added (1,500+ runs);
* IPL runs v wins added (2,500+ runs).
Left out, and said so to the user: all T20s, runs v runs above par, where he is 2nd for runs and 98th of 108 for par
(his IPL strike rate). Wins added (WPA) and par follow Himanish Ganjoo's T20 Primer.

    python articles/top-right-kohli/post.py [--write --date 2026-11-05]
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

KEY = "spotlight-top-right-kohli-2026-11-05"
SITE = "https://hindsightcricket.com"
P = "Virat Kohli"
INTL = {"include_international": True, "leagues": []}
TOP12 = {"include_international": True, "leagues": [], "top_teams": 12}  # T20Is between top-12 sides, as the profiles
IPL = {"include_international": False, "leagues": ["Indian Premier League"]}
COMMON = {"Sharma", "Singh", "Khan", "Kumar", "Patel", "Ali", "Ahmed", "Yadav", "Iyer", "Malik", "Shah", "Hussain",
          "Smith", "Williams", "Jones", "Mohammad", "Rahman", "Islam", "Hasan", "Taylor", "Pandya"}
AX = {
    "runs": {"label": "Runs", "format": "int"},
    "average": {"label": "Average", "format": "dec1"},
    "strike_rate": {"label": "Strike rate", "format": "dec1"},
    "wpa": {"label": "Wins added", "format": "signed1"},
}


def short(name):
    """Surname, with its particle ("de Villiers"); the first name where the surname is shared by many ("Rohit")."""
    w = name.split()
    if len(w) > 1 and w[-1] in COMMON:
        return w[0]
    if len(w) > 2 and w[-2].lower() in {"de", "du", "van", "ul", "der", "le"}:
        return " ".join(w[-2:])
    return w[-1]


def sg(v, d=1):
    return f"{v:+.{d}f}".replace("-", "−")


def th(n):
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def card(cid, visual, title, payload, sample, kicker=None, help_=""):
    assert len(title) <= 80, (len(title), title)
    c = {"id": cid, "visual": visual, "title": title, "help": help_, "sample": sample, "payload": payload}
    if kicker:
        c["kicker"] = kicker
    return c


def field(db, fmt, scope, min_runs, **extra):
    from services.query_builder_v2 import run_deliveries_query

    rows = run_deliveries_query(db, fmt=fmt, group_by=["batter"], metrics_perspective="batting", limit=10000,
                                min_runs=min_runs, **scope, **extra)["data"]
    return [r for r in rows if r.get("batter")]


def plot(rows, xk, yk, cid, title_fn, sample, kicker):
    """The scatter, with the claim checked: nobody beats him on both. Numbered: the four nearest him on both ranks."""
    rows = [r for r in rows if r.get(xk) is not None and r.get(yk) is not None]
    k = next(r for r in rows if r["batter"] == P)
    both = [r["batter"] for r in rows if r[xk] > k[xk] and r[yk] > k[yk]]
    assert not both, (cid, both)
    rx = 1 + sum(r[xk] > k[xk] for r in rows)
    ry = 1 + sum(r[yk] > k[yk] for r in rows)
    rank = {r["batter"]: (sorted(rows, key=lambda s: -s[xk]).index(r) + sorted(rows, key=lambda s: -s[yk]).index(r))
            for r in rows if r["batter"] != P}
    near = sorted(rank, key=rank.get)[:4]
    nd = 0 if AX[xk]["format"] == "int" else 1
    points = [{"name": r["batter"], "x": round(r[xk], 2), "y": round(r[yk], 2),
               **({"highlight": True, "short": "Kohli"} if r["batter"] == P else {}),
               **({"label": near.index(r["batter"]) + 1, "short": short(r["batter"])} if r["batter"] in near else {})}
              for r in rows]
    info = {"k": k, "rx": rx, "ry": ry, "n": len(rows), "near": near, "nd": nd}
    c = card(cid, "scatter_plus", title_fn(info),
             {"points": points, "box": True, "x": {**AX[xk], "higher_better": True}, "y": {**AX[yk], "higher_better": True}},
             sample, kicker=kicker,
             help_="Each dot a batter. The shaded corner would hold anyone better than Kohli on both: it's empty.")
    return c, info


def last_day(db):
    from sqlalchemy import text

    return db.execute(text("SELECT max(match_date) FROM delivery_details WHERE format = 'ODI'")).scalar()


def build(db):
    d = last_day(db)
    end = f"{date.fromisoformat(str(d)[:10]).day} {date.fromisoformat(str(d)[:10]):%b %Y}" if d else "3 Nov 2026"
    odi = field(db, "ODI", INTL, 4000)
    c1, i1 = plot(odi, "average", "runs", "odi-runs",
                  lambda i: f"ODIs since 2000: most runs ({i['k']['runs']:,}) and the highest average ({i['k']['average']:.1f})",
                  f"{len(odi)} batters with 4,000+ ODI runs · since 2000, to {end}", "ODIs · runs v average")
    c2, i2 = plot(odi, "strike_rate", "average", "odi-sr",
                  lambda i: f"Average {i['k']['average']:.1f}, strike rate {i['k']['strike_rate']:.0f}: {i['rx'] - 1} score faster, none average more",
                  f"{len(odi)} batters with 4,000+ ODI runs · since 2000", "ODIs · average v strike rate")
    chase = field(db, "ODI", INTL, 2000, is_chase=True)
    c3, i3 = plot(chase, "strike_rate", "average", "odi-chase",
                  lambda i: f"Chasing in ODIs he averages {i['k']['average']:.1f}, the most of {i['n']} batters",
                  f"{len(chase)} batters with 2,000+ runs in ODI chases · since 2000", "ODIs · chasing")
    spin = field(db, "ODI", INTL, 1500, bowl_kind=["spin bowler"])
    c4, i4 = plot(spin, "strike_rate", "average", "odi-spin",
                  lambda i: f"Against spin in ODIs: an average of {i['k']['average']:.1f}, and nobody better on both counts",
                  f"{len(spin)} batters with 1,500+ ODI runs off spin · since 2000", "ODIs · v spin")
    tchase = field(db, "T20", TOP12, 700, is_chase=True)
    c5, i5 = plot(tchase, "average", "wpa", "t20i-chase",
                  lambda i: f"T20I chases: the highest average ({i['k']['average']:.1f}), {i['ry']}{th(i['ry'])} for wins added",
                  f"{len(tchase)} batters with 700+ runs in T20I chases · between top-12 sides", "T20Is · chasing")
    t20i = field(db, "T20", TOP12, 1500)
    c6, i6 = plot(t20i, "average", "wpa", "t20i",
                  lambda i: f"T20Is between top-12 sides: {i['rx']}{th(i['rx'])} of {i['n']} for average, {i['ry']}{th(i['ry'])} for wins added ({sg(i['k']['wpa'])})",
                  f"{len(t20i)} batters with 1,500+ T20I runs · between top-12 sides", "T20Is")
    ipl = field(db, "T20", IPL, 2500)
    c7, i7 = plot(ipl, "runs", "wpa", "ipl",
                  lambda i: f"IPL: the most runs ({i['k']['runs']:,}), and nobody beats him on both",
                  f"{len(ipl)} batters with 2,500+ IPL runs · 2008 to 2026", "IPL · runs v wins added")
    return {"cards": [c1, c2, c3, c4, c5, c6, c7], "i": [i1, i2, i3, i4, i5, i6, i7], "end": end}


def copy(b):
    i1, i2, i3, i4, i5, i6, i7 = b["i"]
    hook = (f"#TopRightKohli: Virat Kohli turns 38 today. {i1['k']['runs']:,} ODI runs at {i1['k']['average']:.1f}, "
            "and nobody since 2000 has more of either.")
    caption = "\n\n".join([
        "Virat Kohli turns 38 today, so we put the #TopRightKohli meme to the test: seven scatter plots across ODIs and T20s, "
        "and in every one, the corner that would hold anyone better than him on both counts is empty.",
        f"ODIs since 2000: the most runs ({i1['k']['runs']:,}) and the highest average ({i1['k']['average']:.1f}) of {i1['n']} batters "
        f"with 4,000+. Chasing, he averages {i3['k']['average']:.1f}. Against spin, {i4['k']['average']:.1f}.",
        f"T20Is: in chases, the highest average ({i5['k']['average']:.1f}) and {i5['ry']}{th(i5['ry'])} for wins added. "
        f"IPL: the most runs ({i7['k']['runs']:,}).",
        "Wins added: how much a batter moved his side's chance of winning, ball by ball (Himanish Ganjoo's T20 Primer).",
        f"Men's ODIs since 2000, T20Is between top-12 sides and the IPL, to {b['end']}. Ball-by-ball data: Himanish Ganjoo & TechRadar, Cricsheet.",
        "Happy birthday, Virat. Which plot would you put him on next?",
        "Free ball-by-ball cricket stats: link in bio.\n.\n#TopRightKohli #ViratKohli #HappyBirthdayViratKohli #King #TeamIndia #NZvIND",
    ])
    return hook, caption


def thread(b, link):
    i1, i2, i3, i4, i5, i6, i7 = b["i"]
    texts = [
        f"#TopRightKohli, tested on his 38th birthday: seven scatter plots, ODIs and T20s. In every one, nobody beats Virat Kohli "
        f"on both counts. 🧵",
        f"ODIs since 2000: most runs ({i1['k']['runs']:,}), highest average ({i1['k']['average']:.1f}). "
        f"Only {i2['rx'] - 1} of {i2['n']} batters with 4,000+ runs score faster, and none of them average more.",
        f"Chasing in ODIs: an average of {i3['k']['average']:.1f}, the most of {i3['n']}. Against spin: {i4['k']['average']:.1f}.",
        f"T20I chases: the highest average ({i5['k']['average']:.1f}), {i5['ry']}{th(i5['ry'])} for wins added. "
        f"IPL: the most runs ({i7['k']['runs']:,}), and nobody with more runs or more wins added.",
        f"Happy birthday, Virat.\n\nEvery ball, free: {link}\nData: @himganj153 & @TechRadar9",
    ]
    from services.ig_x import hand_thread

    return hand_thread(texts, copy(b)[1], [P])


def reel_script(b):
    i1, i2, i3, i4, i5, i6, i7 = b["i"]
    return {"hook": f"Top right Kohli. Virat Kohli turns 38 today, so we tested the meme on seven scatter plots.",
            "lines": [f"O.D.I. runs against average: nobody since 2000 has more of either.",
                      f"Average against strike rate: nobody is better on both.",
                      f"Chasing, he averages {i3['k']['average']:.0f}.",
                      f"T20 internationals, chasing: the highest average, and {i5['ry']}{th(i5['ry'])} for wins added.",
                      f"And the I.P.L.'s top run-scorer. Top right, every time. Happy birthday, Virat."]}


def slides_of(b, hook):
    lead = b["cards"][0]
    cover = {"type": "hook", "text": hook, "cover": "hero",
             "hero": {"kind": "visual", "visual": lead["visual"], "payload": lead["payload"], "label": "", "card": lead}}
    return ([cover] + [{"type": "card", "card": c, "teams": ["India"]} for c in b["cards"][1:]]
            + [{"type": "end", "heading": "Happy birthday, Virat",
                "body": "Put him on any scatter you like: every ball since 2000, free on Hindsight."}])


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
    for i in b["i"]:
        print("   ", i["n"], "rx", i["rx"], "ry", i["ry"], "near", i["near"])
    problems, hp = findings(slides, "spotlight"), hook_problem(hook)
    print("lint:", problems or "clean", "| hook:", hp or "ok")
    print(caption)
    th_ = thread(b, "hindsightcricket.com")
    for t in th_:
        print(f"--- tweet {t['n']} ({len(t['text'])})\n{t['text']}")
    tp = thread_problems(th_, [P])
    print("thread:", tp or "ok")
    (HERE / "reel.json").write_text(json.dumps(reel_script(b), indent=1))
    (HERE / "slides.json").write_text(json.dumps({"slides": slides, "hook": hook, "caption": caption, "x": th_}, default=str, indent=1))
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
