"""
NZ v India, 1st T20I (Christchurch, 22 Oct 2026): a storyline-led preview post, built by hand ahead of the storylines
pipeline (MATCH_PREVIEW_STORYLINES_PLAN.md). The talking points come from the 21 Oct headlines (HEADLINES); every number
is copied from a Hindsight query-builder result (LINKS).

    python articles/storylines-nz-ind-t20i-1/post.py            # print the plan
    python articles/storylines-nz-ind-t20i-1/post.py --write    # PRODUCTION: carousel, slides, pack, X thread, Reel, YouTube

Nothing is posted: the pack waits in the admin queue for the day.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.update(REEL_V2="1", REEL_AB="0")  # the voiced Reel, recorded from the live site

KEY = "spotlight-nz-ind-storylines-2026-10-22"
DAY = date(2026, 10, 22)
Q = "https://hindsightcricket.com/query?"
LINKS = {
    "openers": Q + "start_date=2025-07-01&batters=Vaibhav+Sooryavanshi&batters=Abhishek+Sharma&batters=Sanju+Samson&bowl_kind=pace+bowler&over_max=5&metrics_perspective=batting&group_by=batter&group_by=competition&fmt=mens-t20",
    "newball": Q + "start_date=2025-01-01&bowlers=Jacob+Duffy&bowlers=Matt+Henry&bowlers=Kyle+Jamieson&bowlers=Lockie+Ferguson&bowlers=Bhuvneshwar+Kumar&bowlers=Arshdeep+Singh&over_max=5&min_balls=120&metrics_perspective=bowling&group_by=bowler&fmt=mens-t20",
    "hagley": Q + "venue=Hagley+Oval%2C+Christchurch&start_date=2019-01-01&query_mode=team_innings&group_by=innings&fmt=mens-t20",
    "hagley_kinds": Q + "venue=Hagley+Oval%2C+Christchurch&start_date=2019-01-01&metrics_perspective=bowling&group_by=bowl_kind&group_by=phase&fmt=mens-t20",
}
HEADLINES = [
    ("Sooryavanshi can't walk straight into the XI: Shreyas", "Cricbuzz"),
    ("We have plans for Sooryavanshi if he plays: Santner", "Cricbuzz"),
    ("Santner: 'Bhuvi will love these conditions in New Zealand'", "ESPNcricinfo"),
    ("The complicated truth: NZ pitches can be good for batting too", "Hindustan Times"),
]


def card(cid, visual, title, payload, sample, help_=""):
    return {"id": cid, "visual": visual, "title": title, "help": help_, "sample": sample, "payload": payload}


openers = card(
    "openers", "metric_bars", "Against new-ball pace in T20Is, Sooryavanshi has added 74 runs per 100 balls. Samson: −28",
    {"metric": {"label": "Runs added per 100 balls, powerplay v pace", "format": "signed0", "signed": True}, "label_width": 140,
     "rows": [{"name": "Sooryavanshi", "value": 74.35, "highlight": True, "detail": "71 balls · SR 213"},
              {"name": "Abhishek", "value": 59.03, "detail": "435 balls · SR 197"},
              {"name": "Samson", "value": -27.52, "detail": "191 balls · SR 162"}]},
    "Men's T20Is since 1 Jul 2025 · overs 1–6, pace bowling only",
    "Runs added: Impact, the runs a batter adds to the projected total. Sooryavanshi's 71 balls are seven innings")

newball = card(
    "newball", "metric_bars", "Santner is right about Bhuvneshwar: the best powerplay economy of either side's new-ball bowlers",
    {"metric": {"label": "Powerplay economy since 2025 (lower is better)", "format": "dec2", "signed": False}, "label_width": 130,
     "rows": [{"name": "Bhuvneshwar", "value": 7.46, "highlight": True, "detail": "India · 51% dots"},
              {"name": "Matt Henry", "value": 7.67, "team": "New Zealand", "detail": "NZ · 54% dots"},
              {"name": "Jamieson", "value": 7.81, "team": "New Zealand", "detail": "NZ · 51% dots"},
              {"name": "Ferguson", "value": 7.85, "team": "New Zealand", "detail": "NZ · 51% dots"},
              {"name": "Duffy", "value": 8.26, "team": "New Zealand", "detail": "NZ · 51% dots"},
              {"name": "Arshdeep", "value": 8.88, "team": "India", "detail": "India · 45% dots"}]},
    "All men's T20s since 1 Jan 2025 · overs 1–6 · 120+ balls each",
    "Runs per over with the new ball. Lower is better")

hagley = card(
    "hagley", "metric_bars", "At Hagley Oval, half of first innings reach 160. Only 5 of 57 have reached 200",
    {"metric": {"label": "First innings reaching the score", "format": "pct0", "signed": False}, "label_width": 110,
     "rows": [{"name": "160 or more", "value": 50.88, "highlight": True, "detail": "29 of 57"},
              {"name": "180 or more", "value": 22.81, "detail": "13 of 57"},
              {"name": "200 or more", "value": 8.77, "detail": "5 of 57"}]},
    "Men's T20s at Hagley Oval, Christchurch, since 2019",
    "Average first innings: 154. Pace bowled 63% of the balls")

HOOK = ("Shreyas Iyer says Vaibhav Sooryavanshi can't walk into India's XI. "
        "Against the new ball in T20Is, he's scored at 213.")
SLIDES = ([{"type": "hook", "kicker": "New Zealand v India · 1st T20I", "text": HOOK, "sub": "Swipe through the data",
            "cover": "hero",
            "hero": {"rows": [{"name": r["name"], "value": r["value"], "highlight": r.get("highlight", False)}
                              for r in openers["payload"]["rows"]],
                     "format": "signed0", "label": "Runs added per 100 balls v new-ball pace, T20Is", "card": openers}}]
          + [{"type": "card", "card": c, "teams": None} for c in (openers, newball, hagley)]
          + [{"type": "end", "heading": "Run it yourself",
              "body": "Every number comes from ball-by-ball data. The full match preview is free on hindsightcricket.com."}])
LINK = "/venue?" + urlencode({"venue": "Hagley Oval, Christchurch", "team1": "New Zealand", "team2": "India"})

TWEETS = [
    (1, "1/ Shreyas Iyer says #VaibhavSooryavanshi \"can't walk in\" to India's XI, with Abhishek and Samson to open.\n\n"
        "Against new-ball pace in T20Is since July 2025: Sooryavanshi strikes at 213, Abhishek 197, Samson 162. 🧵 #NZvIND #CricketTwitter"),
    (2, "2/ In runs added per 100 balls: Sooryavanshi +74, Abhishek +59, Samson −28.\n\n"
        "The case for patience: Sooryavanshi's is 71 balls, seven innings. Abhishek has done it over 435. #NZvIND #CricketTwitter"),
    (3, "3/ Santner: \"Bhuvi will love these conditions.\" The numbers agree: his powerplay economy since 2025 is 7.5, "
        "with half his balls dots, the best of either side's new-ball bowlers. #NZvIND #CricketTwitter"),
    (4, "4/ And the ground: at Hagley Oval half of first innings reach 160, and only 5 of 57 have reached 200. "
        "Pace bowled 63% of the balls.\n\nFull preview: [post link]\n\n"
        "Data: Hindsight · ball-by-ball @himganj153 & @TechRadar9, Cricsheet #NZvIND #CricketTwitter"),
]
CAPTION = """Shreyas Iyer says Vaibhav Sooryavanshi can't walk into India's XI. Against the new ball in T20Is, he's scored at 213.

Three storylines before the first T20I in Christchurch, tested against the data: India's openers against new-ball pace, Bhuvneshwar's return (Santner says he'll "love these conditions"), and what a par score looks like at Hagley Oval.

Full match preview: link in bio.

Data: Hindsight · ball-by-ball by Himanish Ganjoo & TechRadar, Cricsheet

#NZvIND #VaibhavSooryavanshi #Bhuvneshwar #TeamIndia #CricketStats"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    for n, t in TWEETS:
        print(f"slide {n} [{len(t)}] {t[:70]}…")
    if not args.write:
        print("dry run: nothing written")
        return 0
    assert "localhost" not in os.environ.get("DATABASE_URL", ""), "this writes to production"

    from sqlalchemy import text

    from database import engine, get_session
    from services import ig_backlog, ig_carousel, ig_slides
    from services.ig_links import post_link
    from services.ig_notes import youtube_copy

    db = next(get_session())
    deck = [dict(s) for s in SLIDES]
    ig = ig_carousel.save(db, deck, HOOK, {"storylines": KEY}, "storylines")
    r = ig_slides.render(ig["id"], len(deck))  # from the live site
    print(f"carousel {ig['id']}: rendered {len(r['ok'])}/{len(deck)} {r['failed'] or ''}")
    fact = {"kind": "preview", "title": HOOK, "hook": HOOK, "subject": "Vaibhav Sooryavanshi", "carousel_id": ig["id"],
            "slides": len(deck), "link": LINK, "render": False, "headlines": [{"title": t, "source": s} for t, s in HEADLINES],
            "fixture": {"venue": "Hagley Oval, Christchurch", "team1": "New Zealand", "team2": "India"}}
    link = post_link(fact)
    fact["x"] = [{"n": i + 1, "text": t.replace("[post link]", link), "slide": k} for i, (k, t) in enumerate(TWEETS)]
    post = {"key": KEY, "pillar": "reactive", "fact": fact, "snapshot_id": ig["id"], "warnings": [],
            "players": ["Vaibhav Sooryavanshi", "Bhuvneshwar Kumar"], "caption": CAPTION}
    with engine.begin() as conn:
        ig_backlog.upsert_pack(conn, post, DAY, source="storylines")
    print(f"queued ig:{KEY} for {DAY}")
    print(f"reel: {ig_slides.reel_from_stored(ig['id'], len(deck))}s")
    yt = youtube_copy(fact, CAPTION, "Iyer says Sooryavanshi can't walk in. Against the new ball in T20Is he's scored at 213")
    yt["description"] = yt["description"].replace("Full match preview: link in bio.", f"Full match preview: hindsightcricket.com{LINK}")
    with engine.begin() as conn:
        conn.execute(text("UPDATE content_packs SET facts = jsonb_set(facts, '{youtube}', CAST(:y AS jsonb)) WHERE angle_key = :k"),
                     {"y": json.dumps(yt), "k": f"ig:{KEY}"})
    print("youtube:", yt["title"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
