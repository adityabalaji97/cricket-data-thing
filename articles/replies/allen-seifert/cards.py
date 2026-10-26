"""
Reply cards: does @_cricketsparsh's 25 Feb 2026 plan for bowling at Finn Allen and Tim Seifert hold up?
All men's T20s, 1 Jan 2023 to 25 Feb 2026 (the tweet's date); numbers copied from the queries in LINKS.

    DATABASE_URL=postgresql://localhost:5432/hindsight_local python articles/replies/allen-seifert/cards.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
Q = "https://hindsightcricket.com/query?start_date=2023-01-01&end_date=2026-02-25&bowl_kind=pace+bowler&metrics_perspective=batting&fmt=mens-t20&"
LINKS = {"allen_line": Q + "batters=Finn+Allen&over_max=5&group_by=line",
         "allen_shot": Q + "batters=Finn+Allen&over_max=5&group_by=shot_family",
         "seifert": Q + "batters=Tim+Seifert&min_balls=15&group_by=line&group_by=length"}
SAMPLE_ALLEN = "Finn Allen v pace, overs 1–6 · all men's T20s, Jan 2023 to 25 Feb 2026 · balls with line tracked"
TRACKED = "Line, length and shot are hand-tagged on about 40% of balls"


def card(cid, visual, title, payload, sample, help_=""):
    return {"id": cid, "visual": visual, "title": title, "help": help_, "sample": sample, "payload": payload}


allen_line = card(
    "allen-line", "metric_bars", "Finn Allen v new-ball pace: strike rate 106 down leg, 167 on the stumps or outside off",
    {"metric": {"label": "Strike rate", "format": "int", "signed": False}, "label_width": 150,
     "rows": [{"name": "Wide outside off", "value": 194.29, "detail": "35 balls · out every 35"},
              {"name": "Outside off", "value": 167.38, "detail": "466 balls · out every 25"},
              {"name": "On the stumps", "value": 167.37, "detail": "334 balls · out every 15"},
              {"name": "Down leg", "value": 105.71, "highlight": True, "detail": "70 balls · out every 10"}]},
    SAMPLE_ALLEN, TRACKED)

allen_share = card(
    "allen-share", "metric_bars", "Yet only 8% of the new-ball pace Allen faces goes down leg",
    {"metric": {"label": "Share of balls", "format": "pct0", "signed": False}, "label_width": 150,
     "rows": [{"name": "Outside off", "value": 50.49}, {"name": "On the stumps", "value": 36.19},
              {"name": "Down leg", "value": 7.58, "highlight": True}, {"name": "Wide outside off", "value": 3.79}]},
    SAMPLE_ALLEN, "Where pace bowlers have bowled to him in the powerplay")

allen_shot = card(
    "allen-shot", "metric_bars", "Allen has been out 11 times flicking new-ball pace: once every 12 balls",
    {"metric": {"label": "Dismissals", "format": "int", "signed": False}, "label_width": 150,
     "rows": [{"name": "Drive", "value": 17, "detail": "316 balls · SR 203 · out every 19"},
              {"name": "Flick or glance", "value": 11, "highlight": True, "detail": "133 balls · SR 171 · out every 12"},
              {"name": "Pull or hook", "value": 7, "detail": "116 balls · SR 242 · out every 17"},
              {"name": "Slog", "value": 6, "detail": "70 balls · SR 184 · out every 12"},
              {"name": "Work or push", "value": 4, "detail": "106 balls · SR 68"}]},
    "Finn Allen v pace, overs 1–6 · all men's T20s, Jan 2023 to 25 Feb 2026 · balls with the shot tracked",
    "His drives add 59 runs per 100 balls to the projected total; his flicks, about zero")

seifert = card(
    "seifert", "metric_bars", "Tim Seifert v pace: wide outside off on a good length is his least controlled ball, 48%",
    {"metric": {"label": "Balls played in control", "format": "pct0", "signed": False}, "label_width": 170,
     "rows": [{"name": "Wide off · good length", "value": 47.83, "highlight": True, "detail": "23 balls · SR 113 · 3 outs"},
              {"name": "Wide off · back of length", "value": 59.26, "detail": "27 balls · SR 126"},
              {"name": "Down leg · short", "value": 61.54, "detail": "26 balls · SR 242"},
              {"name": "Wide off · full", "value": 62.07, "detail": "29 balls · SR 190"},
              {"name": "Outside off · good length", "value": 63.58, "detail": "302 balls · SR 145"},
              {"name": "On the stumps · full", "value": 84.68, "detail": "124 balls · SR 143"}]},
    "Tim Seifert v pace, all overs · men's T20s, Jan 2023 to 25 Feb 2026 · 17 line-and-length cells with 15+ balls",
    "The lowest of all 17, and the highest for comparison. " + TRACKED)

CARDS = [allen_line, allen_share, allen_shot, seifert]

if __name__ == "__main__":
    assert "localhost" in os.environ.get("DATABASE_URL", ""), "run against the local database"
    from services.snapshots import create_static_snapshot

    slides = [{"type": "card", "card": c, "teams": None} for c in CARDS]
    snap = create_static_snapshot(None, "carousel", {"slides": slides, "title": "Allen & Seifert reply"},
                                  "Allen & Seifert reply", {"reply": "allen-seifert", "slides": slides}, created_by="reply")
    print(snap["id"], len(slides))
