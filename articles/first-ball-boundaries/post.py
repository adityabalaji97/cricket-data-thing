"""
First balls, 27 Oct 2026: Vaibhav Sooryavanshi and Abhishek Sharma hit their first balls for four and six again in
Wellington. How often India's batters hit a boundary off the first ball they face, who does it most in all T20 cricket,
Abhishek's sixes, Virat Kohli's rise (always fours), and whether a boundary start leads to a better innings (Impact
over the rest of the innings).

Slides: cover (India's batters, first-ball boundary %); the deeper cut (every batter with 30+ first balls: boundary %
v out %); sixes; Kohli by period; Impact after a boundary start v any other start; end. Today's match isn't in our
data yet: its two first balls are credited text in the caption, never charted.

    python articles/first-ball-boundaries/post.py              # dry run: cards, titles, lint; nothing saved
    python articles/first-ball-boundaries/post.py --write      # queue for today and render (Reel + Short + X thread)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

KEY = "spotlight-first-ball-boundaries-2026-10-27"
SITE = "https://hindsightcricket.com"
SINCE = date(2024, 1, 1)
VS, AS, VK, SS = "Vaibhav Sooryavanshi", "Abhishek Sharma", "Virat Kohli", "Sanju Samson"
INDIA = [VS, AS, VK, SS, "Shubman Gill", "Yashasvi Jaiswal", "Rohit Sharma", "Suryakumar Yadav", "Tilak Varma",
         "Ishan Kishan", "Rinku Singh", "Hardik Pandya", "Priyansh Arya", "KL Rahul", "Ruturaj Gaikwad"]
COMMON_SURNAMES = {"Sharma", "Yadav", "Singh", "Kumar", "Patel", "Khan", "Iyer", "Pandya"}
ALL_T20 = {"include_international": False, "leagues": []}  # every men's T20
FB = ["batter_ball_number:eq:1"]
MIN_FB = 30          # first balls for the field
MIN_INDIA = 30       # first balls for an India batter on the cover
SCOPE = "every men's T20"


def sg(v, d=1):
    return f"{v:+.{d}f}".replace("-", "−")


def short(name):
    first, last = name.split()[0], name.split()[-1]
    return first if last in COMMON_SURNAMES else last


def card(cid, visual, title, payload, sample, help_=""):
    assert len(title) <= 80, (len(title), title)
    return {"id": cid, "visual": visual, "title": title, "help": help_, "sample": sample, "payload": payload}


def q(db, **kw):
    from services.query_builder_v2 import run_deliveries_query

    base = dict(fmt="T20", gender="male", limit=10000, metrics_perspective="batting", **ALL_T20)
    base.update(kw)
    return run_deliveries_query(db, **base)["data"]


def pct(n, d):
    return 100 * n / d if d else 0.0


# ---- data ----------------------------------------------------------------------------------------------------------

def first_balls(db, **kw):
    return {r["batter"]: r for r in q(db, group_by=["batter"], dimension_filters=FB, **kw)}


def field_rate(db):
    rows = q(db, group_by=["year"], dimension_filters=FB, start_date=SINCE)
    return pct(sum(r["boundaries"] for r in rows), sum(r["balls"] for r in rows))


# ---- slide 1: India's batters --------------------------------------------------------------------------------------

def cover_card(india, avg):
    rows = sorted((r for r in india.values() if r["balls"] >= MIN_INDIA), key=lambda r: -pct(r["boundaries"], r["balls"]))
    vs = india[VS]
    assert rows[0]["batter"] == VS, "Sooryavanshi no longer leads India's batters"
    c = card("india-first-ball", "metric_bars",
             f"Vaibhav Sooryavanshi hits a four or six off one first ball in three: "
             f"{vs['boundaries']} of {vs['balls']}",
             {"metric": {"label": "First balls hit for four or six (%)", "format": "dec1"}, "label_width": 178,
              "reference": {"value": round(avg, 1), "label": f"every batter {avg:.0f}%"},
              "rows": [{"name": short(r["batter"]), "value": round(pct(r["boundaries"], r["balls"]), 1),
                        "highlight": r["batter"] in (VS, AS),
                        "detail": f"{r['boundaries']} of {r['balls']}"} for r in rows]},
             f"India batters, {MIN_INDIA}+ innings · {SCOPE} since 2024, to 24 Oct",
             "The first ball each batter faced in an innings (wides aside).")
    return c, rows


# ---- slide 2: the field --------------------------------------------------------------------------------------------

def field_card(field):
    pool = [r for r in field.values() if r["balls"] >= MIN_FB]
    for r in pool:
        r["b_pct"], r["o_pct"] = pct(r["boundaries"], r["balls"]), pct(r["wickets"], r["balls"])
    ranked = sorted(pool, key=lambda r: -r["b_pct"])
    rank = {r["batter"]: i + 1 for i, r in enumerate(ranked)}
    named = [r["batter"] for r in ranked[:3]] + [n for n in (VS, AS, VK) if n not in [r["batter"] for r in ranked[:3]]]
    labels = {n: i + 1 for i, n in enumerate(named)}
    points = [{"name": r["batter"], "x": round(r["b_pct"], 1), "y": round(r["o_pct"], 1),
               **({"highlight": True} if r["batter"] in (VS, AS) else {}),
               **({"label": labels[r["batter"]], "short": short(r["batter"])} if r["batter"] in labels else {})}
              for r in pool]
    vr = rank[VS]
    head = "the highest" if vr == 1 else f"{vr}{'nd' if vr == 2 else 'rd' if vr == 3 else 'th'} highest"
    c = card("field", "scatter_plus",
             f"Sooryavanshi's {field[VS]['b_pct']:.0f}% is {head} of {len(pool)} batters with {MIN_FB}+ first balls",
             {"points": points, "box": True,
              "x": {"label": "first balls hit for four or six (%)", "format": "dec0", "higher_better": True},
              "y": {"label": "first balls out (%)", "format": "dec0", "higher_better": False}},
             f"{len(pool)} batters, {MIN_FB}+ innings · {SCOPE} since 2024, to 24 Oct",
             "Right: more first-ball boundaries. Down: out less often first ball.")
    c["kicker"] = "The deeper cut"
    return c, {"rank": vr, "n": len(pool), "top": ranked[:3], "rank_of": rank}


# ---- slide 3: sixes ------------------------------------------------------------------------------------------------

def sixes_card(india, field):
    pool = [r for r in field.values() if r["balls"] >= MIN_FB]
    most = max(pool, key=lambda r: r["sixes"])
    a = india[AS]
    rows = sorted((r for r in india.values() if r["balls"] >= MIN_INDIA and r["boundaries"]),
                  key=lambda r: (-r["sixes"], -r["fours"]))[:8]
    lead = "the most of any batter" if most["batter"] == AS else "the most by an India batter"
    c = card("sixes", "share_bars",
             f"Abhishek Sharma: {a['sixes']} first-ball sixes since 2024, {lead}",
             {"absolute": True, "format": "int", "label_width": 150,
              "groups": [{"key": "sixes", "label": "Sixes", "colour": "#b6f24a"},
                         {"key": "fours", "label": "Fours", "colour": "#5b8def"}],
              "rows": [{"name": r["batter"], "detail": f"of {r['balls']}",
                        "segments": [{"key": "sixes", "value": r["sixes"]}, {"key": "fours", "value": r["fours"]}]}
                       for r in rows]},
             f"India batters, {MIN_INDIA}+ innings · {SCOPE} since 2024, to 24 Oct",
             "First balls hit for six and for four.")
    return c, {"most": most}


# ---- slide 4: Kohli ------------------------------------------------------------------------------------------------

PERIODS = [("2008–15", date(2008, 1, 1), date(2015, 12, 31)), ("2016–19", date(2016, 1, 1), date(2019, 12, 31)),
           ("2020–23", date(2020, 1, 1), date(2023, 12, 31)), ("2024–", SINCE, None)]


def kohli_card(db):
    rows = []
    for label, a, b in PERIODS:
        r = q(db, group_by=["batter"], dimension_filters=FB, batters=[VK], start_date=a,
              **({"end_date": b} if b else {}))[0]
        rows.append((label, r))
    career = q(db, group_by=["batter"], dimension_filters=FB, batters=[VK])[0]
    before = [r for lab, r in rows[:-1]]
    pre = pct(sum(r["boundaries"] for r in before), sum(r["balls"] for r in before))
    now = pct(rows[-1][1]["boundaries"], rows[-1][1]["balls"])
    c = card("kohli", "metric_bars",
             f"Virat Kohli: first-ball boundaries up from {pre:.0f}% to {now:.0f}% since 2024. "
             f"{career['sixes']} six in {career['balls']}"
             if career["sixes"] == 1 else
             f"Virat Kohli: first-ball boundaries up from {pre:.0f}% to {now:.0f}% since 2024",
             {"metric": {"label": "First balls hit for four or six (%)", "format": "dec1"}, "label_width": 110,
              "rows": [{"name": lab, "value": round(pct(r["boundaries"], r["balls"]), 1), "highlight": lab == "2024–",
                        "detail": f"{r['fours']} fours, {r['sixes']} {'six' if r['sixes'] == 1 else 'sixes'} in {r['balls']}"}
                       for lab, r in rows]},
             f"{VK}'s first ball in each innings · {SCOPE}, 2008 to 24 Oct 2026",
             "")
    return c, {"pre": pre, "now": now, "career": career, "rows": rows}


# ---- slide 5: what a boundary start is worth -----------------------------------------------------------------------

def impact_card(db, names):
    fb = q(db, group_by=["batter", "match_id"], dimension_filters=FB, batters=names, start_date=SINCE)
    inn = {(r["batter"], r["match_id"]): r for r in
           q(db, group_by=["batter", "match_id"], batters=names, start_date=SINCE)}
    acc = defaultdict(lambda: {"b": [], "o": []})
    for r in fb:
        whole = inn.get((r["batter"], r["match_id"]))
        if not whole or whole.get("impact") is None or r.get("impact") is None:
            continue  # no Primer metrics (e.g. The Hundred)
        rest = whole["impact"] - r["impact"]
        acc[r["batter"]]["b" if r["boundaries"] else "o"].append(rest)
    mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
    rows = []
    for n in names:
        a = acc.get(n)
        if not a or len(a["b"]) < 5 or len(a["o"]) < 5:
            continue
        rows.append({"label": n, "a": round(mean(a["o"]), 1), "b": round(mean(a["b"]), 1),
                     "highlight": n in (VS, AS), "nb": len(a["b"]), "no": len(a["o"])})
    rows.sort(key=lambda r: -(r["b"] - r["a"]))
    by = {r["label"]: r for r in rows}
    # Six rows fit the card: the two leads, then the biggest gaps either way.
    keep = [r for r in rows if r["highlight"]]
    keep += [r for r in rows if not r["highlight"]][:6 - len(keep)]
    rows = sorted(keep, key=lambda r: -(r["b"] - r["a"]))
    v = by.get(AS) or rows[0]  # the steadier sample of the two (17 boundary starts to Sooryavanshi's 12)
    c = card("impact-after", "pair_dumbbell",
             f"After a first-ball boundary, {short(v['label'])} adds {sg(v['b'])} Impact. Other starts: {sg(v['a'])}",
             {"series": ["Any other start", "Four or six first ball"], "format": "signed1", "values": True,
              "full_labels": True,
              "rows": [{"label": r["label"], "a": r["a"], "b": r["b"], "highlight": r["highlight"]} for r in rows]},
             "5+ innings each way · men's T20s since 2024",
             "Impact: runs added to the team's projected total over the rest of the innings, first ball excluded "
             "(T20 Primer method).")
    if min(min(r["nb"], r["no"]) for r in rows) < 15:
        c["small_sample"] = True
    return c, {"rows": rows, "v": v, "by": by}


def build(db):
    india = first_balls(db, batters=INDIA, start_date=SINCE)
    field = first_balls(db, start_date=SINCE, min_balls=MIN_FB)
    for n, r in india.items():
        r["batter"] = n
    avg = field_rate(db)
    lead, cover_rows = cover_card(india, avg)
    fcard, fn = field_card(field)
    scard, sn = sixes_card(india, field)
    kcard, kn = kohli_card(db)
    icard, im = impact_card(db, [r["batter"] for r in cover_rows])
    return {"lead": lead, "cards": [fcard, scard, kcard, icard], "india": india, "avg": avg, "fn": fn, "sn": sn,
            "kn": kn, "im": im}


def copy(b):
    vs, a = b["india"][VS], b["india"][AS]
    kn, fn, im = b["kn"], b["fn"], b["im"]
    hook = f"Vaibhav Sooryavanshi: a four or six off {vs['boundaries']} of his {vs['balls']} first balls"
    vrow, arow = im["by"].get(VS), im["by"].get(AS)
    lines = [
        f"In Wellington today Vaibhav Sooryavanshi's first ball went for four and Abhishek Sharma's for six (ESPNcricinfo; "
        "not in our data yet, so the charts run to 24 Oct).",
        f"Since 2024 Sooryavanshi has hit {vs['boundaries']} of his {vs['balls']} first balls for four or six, "
        f"{pct(vs['boundaries'], vs['balls']):.0f}%. Across every T20 batter it's {b['avg']:.0f}%. Of {fn['n']} batters "
        f"with {MIN_FB}+ first balls, he ranks {'first' if fn['rank'] == 1 else fn['rank']}.",
        f"Abhishek Sharma has hit {a['sixes']} first-ball sixes and {a['fours']} fours in {a['balls']} innings, India's "
        f"most sixes; across all T20 it's {b['sn']['most']['batter']}, {b['sn']['most']['sixes']}.",
        f"Virat Kohli's first ball has gone for four or six {kn['now']:.0f}% of the time since 2024, up from {kn['pre']:.0f}% "
        f"before. In {kn['career']['balls']} first balls he has hit {kn['career']['fours']} fours and "
        f"{kn['career']['sixes']} six.",
    ]
    if vrow and arow:
        lines.append(f"Does the start carry on? After a first-ball boundary, Abhishek has added {sg(arow['b'])} Impact over "
                     f"the rest of his innings, against {sg(arow['a'])} after any other start. Sooryavanshi is the other "
                     f"way round: {sg(vrow['b'])} after a boundary start, {sg(vrow['a'])} after the rest. Small samples: "
                     f"{arow['nb']} and {vrow['nb']} boundary starts.")
    lines += [
        "Every men's T20 since 2024 (leagues and internationals). Impact: runs added to the team's projected total, "
        "ball by ball (T20 Primer method). Ball-by-ball data: Himanish Ganjoo & TechRadar, Cricsheet.",
        "Who would you rather have face the first ball?",
        "Free ball-by-ball cricket stats: link in bio.\n.\n#TeamIndia #NZvIND #VaibhavSooryavanshi #AbhishekSharma "
        "#ViratKohli #cricket",
    ]
    return hook, "\n\n".join(lines)


def slides_of(b, hook):
    from services.ig_cover import hero_from

    cover = {"type": "hook", "text": hook, "cover": "hero", "hero": {**hero_from(b["lead"]), "card": b["lead"]}}
    return ([cover] + [{"type": "card", "card": c, "teams": ["India"]} for c in b["cards"]]
            + [{"type": "end", "heading": "Every first ball, ball by ball",
                "body": "Ask Hindsight's query builder about any batter's first ball, or the first ten. Free."}])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--base", default=SITE)
    args = parser.parse_args()
    if args.write:
        assert "localhost" not in os.environ.get("DATABASE_URL", ""), "--write is production: leave DATABASE_URL unset"
    from database import get_session
    from services.ig_x import x_thread
    from services.social_rules import findings, hook_problem

    db = next(get_session())
    b = build(db)
    hook, caption = copy(b)
    slides = slides_of(b, hook)
    print("HOOK:", hook, f"({len(hook)})")
    for i, s in enumerate(slides, 1):
        c = s.get("card") or (s.get("hero") or {}).get("card") or {}
        print(f"  {i}. [{c.get('visual') or s['type']}] {c.get('title') or s.get('heading')} ({len(c.get('title') or '')})")
        if c:
            print("       ", json.dumps(c["payload"].get("rows") or c["payload"].get("points"), default=str)[:400])
    problems = findings(slides, "spotlight")
    hp = hook_problem(hook)
    print("lint:", problems or "clean", "| hook:", hp or "ok")
    print(caption)
    players = [VS, AS, VK]
    thread = x_thread(slides, caption, players=players)
    for t in thread:
        print(f"--- tweet {t['n']} (slide {t['slide']}, {len(t['text'])})\n{t['text']}")
    (HERE / "slides.json").write_text(json.dumps({"slides": slides, "hook": hook, "caption": caption, "x": thread},
                                                 default=str, indent=1))
    if problems or hp or not args.write:
        return 1 if (problems or hp) else 0

    from database import engine
    from services import ig_backlog, ig_carousel, ig_slides
    from services.ig_links import post_link
    from services.ig_notes import youtube_copy

    carousel = ig_carousel.save(db, slides, hook, {"spotlight": KEY}, "ig-spotlight")
    n = len(slides)
    fact = {"kind": "spotlight", "title": hook, "hook": hook, "subject": VS, "subject_role": "batter",
            "carousel_id": carousel["id"], "slides": n, "render": True, "post_time": "6 pm"}
    fact["x"] = x_thread(slides, caption, players=players, link=post_link(fact))
    fact["youtube"] = youtube_copy(fact, caption, hook)
    ist = timezone(timedelta(hours=5, minutes=30))
    today = datetime.now(ist).date()
    post = {"key": KEY, "pillar": "reactive", "fact": fact, "snapshot_id": carousel["id"], "warnings": [],
            "players": players, "caption": caption}
    with engine.begin() as conn:
        ig_backlog.upsert_pack(conn, post, today, source="hand", post_by=datetime.combine(today, time.max, tzinfo=ist))
    print(f"queued ig:{KEY} for {today} · carousel {carousel['id']} ({n} slides)")
    os.environ.pop("REEL_V2", None)
    r = ig_slides.render(carousel["id"], n, args.base)
    print(f"rendered {len(r['ok'])}/{n}" + (f", failed {r['failed']}" if r["failed"] else "") + f"; layout {r.get('layout') or 'clean'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
