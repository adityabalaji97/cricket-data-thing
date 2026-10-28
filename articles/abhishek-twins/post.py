"""
Abhishek Sharma's statistical twins, 28 Oct 2026: the two closest batters to his game are both in the NZ v India
series, Finn Allen and Vaibhav Sooryavanshi. The method walked through in steps (after the hoopers_stats Kobe Reel's
structure, in our own look): the inputs, the distance, the map, then the twin side by side and the value twist.

Careers since Jan 2024 (the profile's window), major leagues + T20Is between top-12 sides, only batters with 70%+ of
their balls shot-tracked, so the shot mix counts for everyone compared (services/twins.py, DOPPELGANGER_PLAN.md).

    python articles/abhishek-twins/post.py                 # dry run: cards, titles, lint; nothing saved
    python articles/abhishek-twins/post.py --write --base http://localhost:3005   # queue, render (new visuals)
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

KEY = "spotlight-abhishek-twins-2026-10-28"
SITE = "https://hindsightcricket.com"
AS, FA, VS = "Abhishek Sharma", "Finn Allen", "Vaibhav Sooryavanshi"
SHOWN = 6        # nearest on the cover
SPOKES = 12      # nearest on the method star
GROUP_NAMES = {"usage": "Usage", "scoring": "Scoring shape", "shots": "Shot mix", "matchups": "Pace and spin"}
SCOPE = "major leagues + top-12 T20Is since Jan 2024"
SHORT_SCOPE = "since 2024 v strong sides"
STRIP_SHOWN = 13  # of the features: the furthest from the median (23 rows overflow the card)
SURNAMES = {AS: "Abhishek", VS: "Sooryavanshi"}


def short(name):
    return SURNAMES.get(name, name.split()[-1])


def card(cid, visual, title, payload, sample, help_=""):
    assert len(title) <= 80, (len(title), title)
    return {"id": cid, "visual": visual, "title": title, "help": help_, "sample": sample, "payload": payload}


def build(db):
    from services.twins import TRACKED_MIN, compare_rows, find_in, pool, twin_map

    rows = [r for r in pool(db, "window", "bat") if (r["tracked_share"] or 0) >= TRACKED_MIN]
    me = next(r for r in rows if r["player"] == AS)
    period = me["period"]
    near = find_in(rows, AS, period, "bat", "style", len(rows), same_period=True)["twins"]
    by = {r["player"]: r for r in rows}
    gap = {t["player"]: round(100 * t["distance"]) for t in near}
    assert [t["player"] for t in near[:2]] == [FA, VS], [t["player"] for t in near[:3]]
    n = len(rows)
    inputs = compare_rows(me, me, "bat")
    nf = len(inputs)
    extreme = sorted(inputs, key=lambda r: -abs(r["player"] - 50))[:STRIP_SHOWN]
    shown_inputs = [r for r in inputs if r in extreme]  # keep group order
    sample = f"{n} shot-tracked batters · {SHORT_SCOPE}"

    lead = card("nearest", "metric_bars",
                f"Abhishek Sharma's statistical twins: {FA} and {VS}",
                {"metric": {"label": "Points apart (lower is closer)", "format": "int"}, "label_width": 150,
                 "rows": [{"name": "Sooryavanshi" if t["player"] == VS else t["player"], "value": gap[t["player"]],
                           "highlight": t["player"] in (FA, VS),
                           "detail": ", ".join(c["label"] for c in t["closest"][:2])} for t in near[:SHOWN]]},
                sample)

    strip = card("inputs", "percentile_strip",
                 f"Step 1: Abhishek on {nf} features, each a percentile of {n} batters",
                 {"pool": n, "rows": [{"label": r["label"], "group": GROUP_NAMES[r["group"]], "value": r["player"]}
                                      for r in inputs if r in shown_inputs]},
                 f"His {STRIP_SHOWN} most distinctive of {nf} · {n} batters since 2024")
    strip["kicker"] = "How it works"

    star = card("method", "distance_star",
                f"Step 2: how far every batter sits from him, across all {nf} features",
                {"center": AS, "center_label": "Abhishek",
                 "spokes": [{"name": t["player"], "distance": gap[t["player"]], "highlight": t["player"] in (FA, VS),
                             "label": short(t["player"])} for t in near[:SPOKES]]},
                "Distance: typical percentile-point gap, groups weighted equally")

    placed = twin_map(me, [(t["distance"], by[t["player"]]) for t in near], "bat")
    labelled = {FA: "Allen", VS: "Sooryavanshi"}
    cloud = card("map", "twin_cloud",
                 f"Step 3: all {n} batters around Abhishek. The closest two play in this series",
                 {"center": AS, "center_label": "Abhishek", "ring_step": 10, "label_rings_to": 30,
                  "points": [{"name": p["player"], "distance": round(100 * p["distance"], 1), "angle": p["angle"],
                              "highlight": p["player"] in labelled, "label": labelled.get(p["player"])} for p in placed]},
                 sample)

    pairs = compare_rows(me, by[FA], "bat")
    # "Alike" only on something notable (services/twins.NOTABLE): both near nothing (15 and 15 for reverse sweeps)
    # isn't a likeness.
    close = sorted((r for r in pairs if max(r["player"], r["twin"]) >= 25), key=lambda r: abs(r["player"] - r["twin"]))[:4]
    far = sorted(pairs, key=lambda r: -abs(r["player"] - r["twin"]))[:4]
    allen = card("allen", "pair_dumbbell",
                 "Same boundary %, same powerplay role. Abhishek leaves far more than Allen",
                 {"series": ["Abhishek", "Allen"], "format": "int", "values": True, "full_labels": True, "no_diff": True,
                  "rows": [{"label": r["label"][:1].upper() + r["label"][1:], "a": r["player"], "b": r["twin"],
                            "highlight": r in close} for r in close + far]},
                 f"Percentiles of {n} batters · 4 closest features, then 4 furthest")

    value = [AS, FA, VS, "Phil Salt", "Travis Head"]
    vrow = lambda p: by[p]["features"]["value"]  # noqa: E731
    worth = card("worth", "metric_bars",
                 f"Allen is worth what Abhishek is: {vrow(FA)['raa_per_100']:+.1f} and {vrow(AS)['raa_per_100']:+.1f} "
                 "runs above par per 100",
                 {"metric": {"label": "Runs above par per 100 balls", "format": "signed1", "signed": True}, "label_width": 150,
                  "rows": [{"name": p, "value": round(vrow(p)["raa_per_100"], 1), "highlight": p in (AS, FA),
                            "detail": f"Impact {vrow(p)['impact_per_innings']:+.1f} an innings"} for p in value]},
                 f"T20 Primer method · {SHORT_SCOPE}")
    worth["kicker"] = "Plays alike, worth?"
    return {"lead": lead, "cards": [strip, star, cloud, allen, worth], "gap": gap, "n": n, "nf": nf,
            "value": {p: vrow(p) for p in value}, "near": near}


def copy(b):
    g, v, n, nf = b["gap"], b["value"], b["n"], b["nf"]
    hook = f"Abhishek Sharma's statistical twins: both in this series, both {g[FA]} points away"
    caption = "\n\n".join([
        f"Who plays most like Abhishek Sharma? Out of {n} batters, the two closest are Finn Allen and Vaibhav "
        f"Sooryavanshi, {f'each {g[FA]}' if g[FA] == g[VS] else f'{g[FA]} and {g[VS]}'} points away. All three are in this New Zealand v India series.",
        f"How: {nf} features for every batter, in four groups: when he bats (powerplay, middle overs, death; balls an "
        "innings; position), how he scores (dot %, boundary %, sixes among boundaries, strike rate by phase), the "
        "shots he plays (shot mix, control %), and pace against spin. Each feature becomes a percentile among the "
        f"{n} batters. The distance between two batters is the typical percentile-point gap across the four groups, "
        "each group weighted equally. Smallest distance: the twin.",
        f"Only batters with 70%+ of their balls shot-tracked are compared, so the shot mix counts for everyone. Most "
        f"batters' nearest twin is about 13 points away.",
        f"Plays alike, worth the same: Allen adds {v[FA]['raa_per_100']:+.1f} runs above par per 100 balls, Abhishek "
        f"{v[AS]['raa_per_100']:+.1f}. Sooryavanshi, just as close in style, adds {v[VS]['raa_per_100']:+.1f}. "
        f"Phil Salt and Travis Head play alike too ({g['Phil Salt']} and {g['Travis Head']} points) but add "
        f"{v['Phil Salt']['raa_per_100']:+.1f} and {v['Travis Head']['raa_per_100']:+.1f}.",
        f"Careers since January 2024 in the major leagues and T20Is between top-12 sides. Impact and runs above par: "
        "T20 Primer method. Ball-by-ball data: Himanish Ganjoo & TechRadar, Cricsheet.",
        "Who plays like your favourite batter? Every profile on Hindsight now shows it.",
        "Free ball-by-ball cricket stats: link in bio.\n.\n#AbhishekSharma #FinnAllen #VaibhavSooryavanshi #NZvIND "
        "#TeamIndia #cricket",
    ])
    return hook, caption


def slides_of(b, hook):
    from services.ig_cover import hero_from

    cover = {"type": "hook", "text": hook, "cover": "hero", "hero": {**hero_from(b["lead"]), "card": b["lead"]}}
    return ([cover] + [{"type": "card", "card": c, "teams": ["India", "New Zealand"]} for c in b["cards"]]
            + [{"type": "end", "heading": "Who plays like your favourite batter?",
                "body": "Every profile on Hindsight shows it: Plays like, under DNA & Similar. Free."}])


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
    problems = findings(slides, "spotlight")
    hp = hook_problem(hook)
    print("lint:", problems or "clean", "| hook:", hp or "ok")
    print(caption)
    players = [AS, FA, VS]
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
    fact = {"kind": "spotlight", "title": hook, "hook": hook, "subject": AS, "subject_role": "batter",
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
    r = ig_slides.render(carousel["id"], n, args.base)
    print(f"rendered {len(r['ok'])}/{n}" + (f", failed {r['failed']}" if r["failed"] else "") + f"; layout {r.get('layout') or 'clean'}")
    # Reels are always voiced (the user's rule): the hand script replaces whatever the render stored.
    import subprocess
    env = {**os.environ, "REEL_V2": "1", "REEL_AB": "0"}
    done = subprocess.run([sys.executable, str(ROOT / "scripts/make_reel_v2.py"), "--key", f"ig:{KEY}", "--beats", "1,2,3,4,6",
                           "--script", str(HERE / "reel.json"), "--close", "Who plays like your favourite batter?",
                           "--base", args.base, "--store"], env=env, capture_output=True, text=True)
    print("voiced Reel:", "stored" if "stored as the post's Reel" in done.stdout else f"FAILED\n{done.stderr[-800:]}")
    return 0 if "stored as the post's Reel" in done.stdout else 1


if __name__ == "__main__":
    sys.exit(main())
