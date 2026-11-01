"""
Sanju Samson or Vaibhav Sooryavanshi, 1 Nov 2026: Sanju made 4 off 10 opening in the fifth T20I in Hamilton today (the
user's figure; the match isn't in our ball-by-ball yet, so it's in the hook only, never charted). Every chart is our
data to 31 Oct. Story: 97, 89 and 89 in his last three World Cup innings; since the final, single figures in 8 of 18,
+25 runs above par per 100 balls against Vaibhav's +60, slow first 10 balls, and wins added below zero. Both ways: the
World Cup innings were the biggest of India's year.

    python articles/sanju-vaibhav/post.py              # dry run
    python articles/sanju-vaibhav/post.py --write      # queue, render, voiced Reel (reel.json from the same numbers), thread
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from sqlalchemy import text  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

KEY = "spotlight-sanju-vaibhav-2026-11-01"
SITE = "https://hindsightcricket.com"
SANJU, VAIBHAV, ABHISHEK, ISHAN = "Sanju Samson", "Vaibhav Sooryavanshi", "Abhishek Sharma", "Ishan Kishan"
OPENERS = [SANJU, VAIBHAV, ABHISHEK, ISHAN]
T20I = {"fmt": "T20", "include_international": True}  # internationals only (no leagues named)
YEAR_START = date(2026, 1, 1)
FINAL = date(2026, 3, 8)  # the World Cup final, Ahmedabad
SINCE = {**T20I, "start_date": FINAL + timedelta(days=1), "end_date": date(2026, 10, 31)}
UP_TO = {**T20I, "start_date": YEAR_START, "end_date": FINAL}
TODAY = "4 off 10"  # Sanju in Hamilton today (user, 1 Nov 2026): text only
THREAD_PLAYERS = OPENERS  # each one's first mention in the thread becomes a hashtag
TEAM_SHORT = {"India": "IND", "England": "ENG", "New Zealand": "NZ", "West Indies": "WI", "Australia": "AUS",
              "South Africa": "RSA", "Pakistan": "PAK", "Sri Lanka": "SL", "Afghanistan": "AFG"}
CITY = {"Eden Gardens": "Kolkata", "Wankhede Stadium": "Mumbai", "Narendra Modi Stadium": "Ahmedabad"}


def sg(v, d=1):
    return f"{v:+.{d}f}".replace("-", "−")


def card(cid, visual, title, payload, sample, kicker=None):
    assert len(title) <= 80, (len(title), title)
    c = {"id": cid, "visual": visual, "title": title, "help": "", "sample": sample, "payload": payload}
    if kicker:
        c["kicker"] = kicker
    return c


def q(db, **kw):
    from services.query_builder_v2 import run_deliveries_query

    kw.setdefault("limit", 10000)
    kw.setdefault("metrics_perspective", "batting")
    return run_deliveries_query(db, **kw)["data"]


def one(db, player, **kw):
    rows = q(db, batters=[player], group_by=["batter"], **kw)
    return rows[0] if rows else None


def short(name):
    return {SANJU: "Sanju", VAIBHAV: "Vaibhav", ABHISHEK: "Abhishek", ISHAN: "Ishan"}.get(name, name.split()[-1])


# ---- slides -----------------------------------------------------------------------------------------------------

def after10_card(db):
    """Each opener's typical (median) innings after 10 balls since the World Cup final: his running Impact (runs against
    par for the match situation, the wicket's cost included) at his 10th ball, or at the end of a shorter innings.
    Per-ball Impact is ball_metrics', the same numbers the query builder sums."""
    import statistics

    rows_ = db.execute(text("""
        SELECT d.bat, d.p_match, d.inns, d.ball_id, b.impact
        FROM delivery_details d JOIN ball_metrics b ON b.delivery_id = d.id
        WHERE d.bat = ANY(:p) AND d.competition = 'T20I' AND d.ballfaced = 1
          AND d.match_date >= :a AND d.match_date <= :b
        ORDER BY d.bat, d.p_match, d.inns, d.ball_id"""),
        {"p": OPENERS, "a": str(SINCE["start_date"]), "b": str(SINCE["end_date"])}).mappings().all()
    run = {}
    for r in rows_:
        key = (r["bat"], r["p_match"], r["inns"])
        balls = run.setdefault(key, [])
        balls.append((balls[-1] if balls else 0.0) + (r["impact"] or 0.0))
    raw = {}
    for p in OPENERS:
        at10 = [b[min(9, len(b) - 1)] for (who, _m, _i), b in run.items() if who == p]
        raw[p] = {"median": statistics.median(at10), "n": len(at10), "ahead": sum(1 for v in at10 if v > 0)}
    rows = [{"name": short(p), "value": round(raw[p]["median"], 1), "highlight": p == SANJU,
             "detail": f"{raw[p]['n']} innings"} for p in sorted(OPENERS, key=lambda p: -raw[p]["median"])]
    s, a = raw[SANJU]["median"], raw[ABHISHEK]["median"]
    assert s < 0 < a, "the comparison the cover makes no longer holds"
    c = card("after10", "metric_bars",
             f"After 10 balls, Sanju's typical innings has cost India {abs(s):.0f} runs; Abhishek's adds {a:.0f}",
             {"metric": {"label": "Runs against par after 10 balls, typical innings", "format": "signed1"},
              "label_width": 150, "rows": rows},
             "T20Is since the World Cup final · median innings · runs against par, wicket cost included")
    return c, raw


def worldcup_card(db):
    from services.query_builder_v2 import run_deliveries_query  # noqa: F401

    inns = q(db, batters=[SANJU], group_by=["match_id"], **{**T20I, "start_date": YEAR_START, "end_date": date(2026, 10, 31)})
    ids = [str(r["match_id"]) for r in inns]
    meta = {str(m["id"]): m for m in db.execute(text(
        "SELECT id, date, team1, team2, venue FROM matches WHERE id = ANY(:ids)"), {"ids": ids}).mappings()}
    top = sorted((r for r in inns if r["runs"] >= 50), key=lambda r: -(r["raa"] or 0))
    rows, wc_raa = [], 0.0
    for r in top:
        m = meta[str(r["match_id"])]
        opp = m["team2"] if m["team1"] == "India" else m["team1"]
        wc = date(2026, 3, 1) <= m["date"] <= FINAL
        wc_raa += (r["raa"] or 0) if wc else 0
        rows.append({"name": f"{r['runs']} v {TEAM_SHORT.get(opp, opp[:3].upper())}", "value": round(r["raa"], 1),
                     "highlight": wc, "detail": f"{r['balls']} balls · " + (f"World Cup, {CITY.get(m['venue'], '')}" if wc
                                                                           else m["date"].strftime("%b %Y"))})
    assert sum(1 for r in rows if r["highlight"]) == 3, "expected his three World Cup fifties"
    total = sum(r["raa"] or 0 for r in inns)
    share = 100 * wc_raa / total
    c = card("worldcup", "metric_bars",
             f"97, 89, 89 at the World Cup: {share:.0f}% of his runs above par this year",
             {"metric": {"label": "Runs above par, one innings", "format": "signed0"}, "label_width": 210, "rows": rows},
             "Sanju's 50+ scores in T20Is in 2026, by runs above par · World Cup in lime", kicker="The case for")
    return c, {"share": share, "total": total}


def par_card(db):
    since = {p: one(db, p, **SINCE) for p in OPENERS}
    up = one(db, SANJU, **UP_TO)
    rows = [{"name": short(p), "value": round(since[p]["raa_per_100"], 1), "highlight": p == SANJU,
             "detail": f"{since[p]['runs']} runs, {since[p]['balls']} balls"}
            for p in sorted(OPENERS, key=lambda p: -since[p]["raa_per_100"])]
    s, v = since[SANJU], since[VAIBHAV]
    c = card("par", "metric_bars",
             f"Since the final: Sanju {sg(s['raa_per_100'], 0)} runs above par per 100 balls, Vaibhav {sg(v['raa_per_100'], 0)}",
             {"metric": {"label": "Runs above par per 100 balls", "format": "signed1"}, "label_width": 150, "rows": rows},
             f"T20Is, 9 Mar to 31 Oct 2026 · Sanju was {sg(up['raa_per_100'], 0)} up to the final", kicker="Since the World Cup")
    return c, {"since": since, "up": up}


def wins_card(db, since):
    rows = [{"name": short(p), "value": round(since[p]["wpa"], 2), "highlight": p == SANJU} for p in
            sorted(OPENERS, key=lambda p: -since[p]["wpa"])]
    s, v = since[SANJU]["wpa"], since[VAIBHAV]["wpa"]
    assert s < 0 < v
    c = card("wins", "metric_bars",
             f"Wins added since the final: Vaibhav {sg(v, 2)}, Sanju {sg(s, 2)}",
             {"metric": {"label": "Wins added (change in India's win chance from his balls)", "format": "signed2"},
              "label_width": 150, "rows": rows},
             "Wins added: win probability his balls added (T20 Primer) · since 9 Mar",
             kicker="What it cost")
    return c, {"s": s, "v": v}


def build(db):
    lead, a10 = after10_card(db)
    wc, wn = worldcup_card(db)
    par, pr = par_card(db)
    wins, wi = wins_card(db, pr["since"])
    return {"lead": lead, "cards": [wc, par, wins], "a10": a10, "wn": wn, "pr": pr, "wi": wi}


def _r(v):
    return f"{abs(v):.0f}"


def copy(b):
    a10, wn, pr, wi = (b[k] for k in ("a10", "wn", "pr", "wi"))
    s, v, a = pr["since"][SANJU], pr["since"][VAIBHAV], pr["since"][ABHISHEK]
    t = {p: a10[p]["median"] for p in OPENERS}
    hook = f"After 10 balls, Sanju's typical innings has cost India {_r(t[SANJU])} runs. Abhishek's has added {_r(t[ABHISHEK])}."
    caption = "\n\n".join([
        f"Sanju Samson made {TODAY} opening in Hamilton today. Since the World Cup final, his typical T20I innings has "
        f"cost India {_r(t[SANJU])} runs by the time he's faced 10 balls. Abhishek Sharma's has added {_r(t[ABHISHEK])}, "
        f"Ishan Kishan's {_r(t[ISHAN])}, and Vaibhav Sooryavanshi's has about broken even.",
        "(Runs against par for the match situation, with the cost of a wicket included; the typical innings is the "
        "middle one. Today's match isn't in our ball-by-ball yet: the charts run to 31 Oct.)",
        f"The case for him: 97, 89 and 89 in his last three World Cup innings, {wn['share']:.0f}% of his runs above par "
        f"this year. India won all three.",
        f"Since the final he's {sg(s['raa_per_100'], 0)} runs above par per 100 balls (he was "
        f"{sg(pr['up']['raa_per_100'], 0)} up to it). Vaibhav, in {v['innings_count']} T20Is, is "
        f"{sg(v['raa_per_100'], 0)}; Abhishek {sg(a['raa_per_100'], 0)}. Sanju's batting has taken "
        f"{abs(wi['s']) * 100:.0f} percentage points off India's win chances since the final; Vaibhav's has added "
        f"{wi['v'] * 100:.0f}.",
        "T20Is to 31 Oct 2026. Runs above par and wins added: T20 Primer method. Ball-by-ball data: Himanish Ganjoo & "
        "TechRadar, Cricsheet.",
        "Sanju or Vaibhav at the top?",
        "Free ball-by-ball cricket stats: link in bio.\n.\n#NZvIND #SanjuSamson #VaibhavSooryavanshi #TeamIndia #T20I",
    ])
    return hook, caption


def thread(b, link):
    a10, wn, pr, wi = (b[k] for k in ("a10", "wn", "pr", "wi"))
    s, v, a = pr["since"][SANJU], pr["since"][VAIBHAV], pr["since"][ABHISHEK]
    t = {p: a10[p]["median"] for p in OPENERS}
    texts = [
        f"Sanju Samson made {TODAY} today. After 10 balls, his typical innings since the World Cup final has cost India "
        f"{_r(t[SANJU])} runs. Abhishek Sharma's has added {_r(t[ABHISHEK])}. 🧵",
        f"Runs against par for the match situation, wicket cost included. Ishan Kishan: {sg(t[ISHAN], 0)}. Vaibhav "
        f"Sooryavanshi: about even ({a10[VAIBHAV]['n']} innings).",
        f"The case for Sanju: 97, 89 and 89 in his last three World Cup innings, {wn['share']:.0f}% of his runs above par "
        f"this year. India won all three.",
        f"Since the final: Sanju {sg(s['raa_per_100'], 0)} runs above par per 100 balls (from "
        f"{sg(pr['up']['raa_per_100'], 0)}). Vaibhav {sg(v['raa_per_100'], 0)}. Abhishek {sg(a['raa_per_100'], 0)}.",
        f"Wins added since the final: Vaibhav {sg(wi['v'], 2)}, Sanju {sg(wi['s'], 2)}. His batting has taken "
        f"{abs(wi['s']) * 100:.0f} percentage points off India's win chances.",
        f"Sanju or Vaibhav at the top?\n\nEvery ball, free: {link}\nData: @himganj153 & @TechRadar9",
    ]
    from services.ig_x import hand_thread

    return hand_thread(texts, copy(b)[1], THREAD_PLAYERS)


def reel_script(b):
    a10, wn, pr, wi = (b[k] for k in ("a10", "wn", "pr", "wi"))
    s, v = pr["since"][SANJU], pr["since"][VAIBHAV]
    t = {p: a10[p]["median"] for p in OPENERS}
    return {"hook": f"Sanju Samson made 4 off 10 today. After 10 balls, his typical innings costs India {_r(t[SANJU])} runs. "
                    f"Abhishek's adds {_r(t[ABHISHEK])}.",
            "lines": ["Ishan adds one. Vaibhav Sooryavanshi breaks about even.",
                      "The case for Sanju: 97, 89 and 89 in his last three World Cup innings. India won all three.",
                      f"But since the final, he's {s['raa_per_100']:.0f} runs above par per 100 balls. "
                      f"Vaibhav is {v['raa_per_100']:.0f}.",
                      f"And his batting has taken {abs(wi['s']) * 100:.0f} percentage points off India's win chances. "
                      f"Vaibhav's has added {wi['v'] * 100:.0f}."]}


def slides_of(b, hook):
    from services.ig_cover import hero_from

    cover = {"type": "hook", "text": hook, "cover": "hero", "hero": {**hero_from(b["lead"]), "card": b["lead"]}}
    return ([cover] + [{"type": "card", "card": c, "teams": ["India"]} for c in b["cards"]]
            + [{"type": "end", "heading": "Sanju or Vaibhav at the top?",
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
    fact = {"kind": "spotlight", "title": hook, "hook": hook, "subject": SANJU, "subject_role": "batter",
            "carousel_id": carousel["id"], "slides": n, "render": True, "post_time": "8 pm"}
    fact["x"] = thread(b, post_link(fact))
    fact["youtube"] = youtube_copy(fact, caption, hook)
    ist = timezone(timedelta(hours=5, minutes=30))
    today = datetime.now(ist).date()
    post = {"key": KEY, "pillar": "reactive", "fact": fact, "snapshot_id": carousel["id"], "warnings": [],
            "players": OPENERS, "caption": caption}
    with engine.begin() as conn:
        ig_backlog.upsert_pack(conn, post, today, source="hand", post_by=datetime.combine(today, time.max, tzinfo=ist))
    print(f"queued ig:{KEY} for {today} · carousel {carousel['id']} ({n} slides)")
    r = ig_slides.render(carousel["id"], n, args.base)
    print(f"rendered {len(r['ok'])}/{n}" + (f", failed {r['failed']}" if r["failed"] else "") + f"; layout {r.get('layout') or 'clean'}")
    # Reels are always voiced (the user's rule): the hand script replaces whatever the render stored.
    env = {**os.environ, "REEL_V2": "1", "REEL_AB": "0"}
    done = subprocess.run([sys.executable, str(ROOT / "scripts/make_reel_v2.py"), "--key", f"ig:{KEY}", "--beats", "1,2,3,4",
                           "--script", str(HERE / "reel.json"), "--close", "Sanju or Vaibhav at the top?", "--base", args.base,
                           "--store"], env=env, capture_output=True, text=True)
    ok = "stored as the post's Reel" in done.stdout
    print("voiced Reel:", "stored" if ok else f"FAILED\n{done.stdout[-1500:]}\n{done.stderr[-1500:]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
