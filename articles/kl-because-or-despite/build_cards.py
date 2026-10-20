"""
"KL: because of, or despite?" as Hindsight story cards (the app's own visuals: src/components/story/postVisuals.jsx).

Saves two carousel snapshots to the LOCAL database and prints their ids:
    article   one card per article chart, no hook/end (the Medium and site images)
    instagram hook, the cards, end (the IG/X post)
Render them with scripts/render_ig_slides.mjs against a local frontend (--base http://localhost:3000).

Every number below was copied from a Hindsight query-builder result (IPL, men's T20, batting view); the query for each
card is its `link`.

    DATABASE_URL=postgresql://localhost:5432/hindsight_local python articles/kl-because-or-despite/build_cards.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from services.snapshots import create_static_snapshot  # noqa: E402

Q = "https://hindsightcricket.com/query?"


def card(cid, visual, title, payload, sample, help_=""):
    return {"id": cid, "visual": visual, "title": title, "help": help_, "sample": sample, "payload": payload}


# 1. The trade. IPL 2019-23, 600+ balls in one top-order slot: (name, slot, RAA/100, WAA/100, Impact/innings).
SLOTS = [("Devon Conway", 2, -3.83, 2.33, 3.97), ("Mayank Agarwal", 2, 3.88, 1.45, 3.35),
         ("Suryakumar Yadav", 3, 9.64, 0.81, 2.39), ("KL Rahul", 1, -6.18, 2.80, 2.33),
         ("Quinton de Kock", 2, 0.66, 1.77, 2.31), ("Rishabh Pant", 4, 4.58, 1.03, 2.14),
         ("Ruturaj Gaikwad", 1, -0.53, 1.38, 1.70), ("Sanju Samson", 3, 4.88, 1.03, 1.20),
         ("Jos Buttler", 2, 5.78, 0.83, 0.86), ("Faf du Plessis", 2, -6.18, 1.74, 0.82),
         ("David Warner", 1, -3.07, 1.48, 0.76), ("Rahul Tripathi", 3, 11.08, -0.32, 0.52),
         ("Shikhar Dhawan", 2, -5.96, 1.50, 0.42), ("Shubman Gill", 2, -1.50, 1.29, 0.15),
         ("Prithvi Shaw", 1, 14.15, -1.07, -0.34), ("Manish Pandey", 3, -12.81, 2.05, -0.40),
         ("Shubman Gill", 1, -8.36, 1.48, -0.51), ("Shreyas Iyer", 3, -4.71, 0.68, -1.41),
         ("Virat Kohli", 1, -14.01, 1.30, -2.89), ("Rohit Sharma", 1, -6.73, -0.80, -3.83)]
SAMPLE_SLOTS = "IPL 2019–23 · 20 top-order regulars (600+ balls in one batting slot)"
LINK_SLOTS = Q + "start_date=2019-01-01&end_date=2023-12-31&leagues=IPL&min_balls=600&metrics_perspective=batting&group_by=batter&group_by=batting_position&fmt=mens-t20"


def slot_name(name, slot):
    twice = sum(1 for s in SLOTS if s[0] == name) > 1
    return f"{name} (#{slot})" if twice else name


KEYED = ["Prithvi Shaw", "Virat Kohli", "Devon Conway", "Suryakumar Yadav", "Manish Pandey", "Rohit Sharma"]
trade = card(
    "trade", "scatter_plus", "KL Rahul saved more wickets than any IPL top-order regular, and paid for it in runs",
    {"x": {"label": "Runs above average per 100", "format": "signed1", "higher_better": True},
     "y": {"label": "Wickets above average per 100", "format": "signed1", "higher_better": True},
     "z": None, "box": False,
     "points": [{"name": slot_name(n, s), "short": n.split()[-1] if n != "KL Rahul" else "KL Rahul", "x": raa, "y": waa,
                 "highlight": n == "KL Rahul", "label": (KEYED.index(n) + 1) if n in KEYED else None}
                for n, s, raa, waa, _ in SLOTS]},
    SAMPLE_SLOTS, "Against the average for the game state. Up: got out less often. Right: scored faster than the situation needed.")

verdict = card(
    "verdict", "metric_bars", "Put the two together and KL was 4th of 20 for Impact per innings",
    {"metric": {"label": "Impact per innings", "format": "signed1", "signed": True}, "label_width": 128,
     "rows": [{"name": slot_name(n, s), "value": imp, "highlight": n == "KL Rahul",
               "detail": f"#{i + 1} of 20" if i >= 8 else None}
              for i, (n, s, _, _, imp) in enumerate(SLOTS) if i < 8 or n in ("Prithvi Shaw", "Virat Kohli")]},
    SAMPLE_SLOTS, "Impact: runs added to the team's projected total while he batted (his runs, minus what his dismissals cost)")

# 2. Impact per innings by season.
SEASONS = [(2018, 11.12, "Punjab Kings", 14), (2019, 0.61, "Punjab Kings", 14), (2020, 0.87, "Punjab Kings", 14),
           (2021, 7.77, "Punjab Kings", 13), (2022, 1.72, "Lucknow Super Giants", 14),
           (2023, -4.14, "Lucknow Super Giants", 9), (2024, 1.51, "Lucknow Super Giants", 14),
           (2025, 2.63, "Delhi Capitals", 13), (2026, 4.74, "Delhi Capitals", 14)]
by_season = card(
    "seasons", "metric_bars", "KL Rahul's Impact has been positive in every IPL season since 2018 bar one",
    {"metric": {"label": "Impact per innings", "format": "signed1", "signed": True},
     "rows": [{"name": str(y), "value": v, "detail": f"{t.split()[0] if t != 'Lucknow Super Giants' else 'Lucknow'} · {n} inns"}
              for y, v, t, n in SEASONS]},
    "KL Rahul, IPL 2018–2026")

# 3. First ten balls, by season: (season, SR first 10, RAA/100 first 10, SR from ball 11).
FIRST10 = [(2018, 164.3, 39.08, 155.4), (2019, 96.8, -26.08, 150.8), (2020, 113.6, -8.10, 134.7),
           (2021, 113.0, -5.20, 148.5), (2022, 90.2, -28.81, 152.0), (2023, 101.2, -22.54, 119.4),
           (2024, 122.0, -5.52, 143.6), (2025, 126.7, -10.29, 160.7), (2026, 143.5, -0.04, 190.2)]
first10 = card(
    "first10", "metric_bars", "KL's slow starts cost runs every season from 2019 to 2025. In 2026 they were at par",
    {"metric": {"label": "Runs above average per 100, first 10 balls", "format": "signed1", "signed": True}, "label_width": 150,
     "rows": [{"name": str(y), "value": raa, "highlight": y == 2026, "detail": f"SR {sr:.0f} first 10 · {rest:.0f} after"}
              for y, sr, raa, rest in FIRST10]},
    "KL Rahul, IPL · his first 10 balls of each innings", "Runs above the average for the game state, per 100 balls")

# 4. Partners, with KL at the other end (PBKS and LSG, 2018-23).
partners = card(
    "partners", "metric_bars", "Batting with KL: partners below par in the powerplay, above it in the middle overs",
    {"metric": {"label": "Partners' runs above average per 100", "format": "signed1", "signed": True}, "label_width": 120,
     "rows": [{"name": "Powerplay", "value": -5.66, "detail": "1,202 balls"},
              {"name": "Middle overs", "value": 7.16, "detail": "1,105 balls"},
              {"name": "Death", "value": -19.91, "detail": "307 balls"}]},
    "Punjab and Lucknow, IPL 2018–23 · balls faced by KL's batting partners", "Runs above the average for the game state, per 100 balls")

# 5. IPL 2026 Impact leaders.
LEAD = [("Vaibhav Sooryavanshi", 242.9), ("Rajat Patidar", 110.9), ("Virat Kohli", 83.0), ("Ishan Kishan", 71.2),
        ("KL Rahul", 66.3), ("Shubman Gill", 61.8), ("Abhishek Sharma", 61.1), ("Mitchell Marsh", 58.3)]
season26 = card(
    "ipl2026", "metric_bars", "IPL 2026: KL Rahul 5th for Impact, at a strike rate of 174",
    {"metric": {"label": "Impact", "format": "signed0", "signed": False}, "label_width": 140,
     "rows": [{"name": n, "value": v, "highlight": n == "KL Rahul"} for n, v in LEAD]},
    "IPL 2026 · batters with 250+ balls", "Impact: runs added to the team's projected total")

ARTICLE = [trade, verdict, first10, partners, by_season, season26]
# The cover carries the Impact ranking's top rows (services/ig_cover: only a bar chart shrinks onto a cover); the full
# ranking stays in the deck as slide 3, so every tweet in the thread has a slide.
from services.ig_cover import hero_from  # noqa: E402

_hero = hero_from(verdict)
_hero["rows"] = [{**r, "name": {"Devon Conway": "Conway", "Mayank Agarwal": "Mayank", "Suryakumar Yadav": "SKY"}.get(r["name"], r["name"])}
                 for r in _hero["rows"]]  # the cover's name column is 108px

INSTAGRAM = ([{"type": "hook", "kicker": "KL Rahul · IPL",
               "text": "KL Rahul batted 42 balls per dismissal in 2019–23, the most of any IPL top-order regular. Did it help?",
               "sub": "Swipe through the data", "cover": "hero", "hero": {**_hero, "card": verdict}}]
             + [{"type": "card", "card": c, "teams": None} for c in (trade, verdict, first10, season26)]
             + [{"type": "end", "heading": "Run it yourself",
                 "body": "Every number comes from ball-by-ball data. Ask your own question on the query builder: it's free."}])

if __name__ == "__main__":
    assert "localhost" in os.environ.get("DATABASE_URL", ""), "run against the local database"
    out = {}
    for name, slides in (("article", [{"type": "card", "card": c, "teams": None} for c in ARTICLE]), ("instagram", INSTAGRAM)):
        snap = create_static_snapshot(None, "carousel", {"slides": slides, "title": f"KL: because of, or despite? ({name})"},
                                      f"KL: because of, or despite? ({name})", {"article": "kl-because-or-despite", "set": name, "slides": slides},
                                      created_by="article-kl")
        out[name] = (snap["id"], len(slides))
    print(out)
