"""
Reply cards, v2: pitch maps (postVisuals pitch_map) for Finn Allen and Tim Seifert v pace, plus Allen's dismissals by
shot. All men's T20s, 1 Jan 2023 to 25 Feb 2026 (the tweet's date); numbers copied from the queries in LINKS.

    DATABASE_URL=postgresql://localhost:5432/hindsight_local python articles/replies/allen-seifert/pitch.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
Q = "https://hindsightcricket.com/query?start_date=2023-01-01&end_date=2026-02-25&bowl_kind=pace+bowler&metrics_perspective=batting&fmt=mens-t20&"
LINKS = {"allen": Q + "batters=Finn+Allen&over_max=5&group_by=line&group_by=length",
         "allen_shot": Q + "batters=Finn+Allen&over_max=5&group_by=shot_family",
         "seifert": Q + "batters=Tim+Seifert&min_balls=15&group_by=line&group_by=length"}
LINES = ["WIDE_OUTSIDE_OFFSTUMP", "OUTSIDE_OFFSTUMP", "ON_THE_STUMPS", "DOWN_LEG"]
LENGTHS = ["FULL", "GOOD_LENGTH", "SHORT_OF_A_GOOD_LENGTH", "SHORT"]
W, O, S, L = LINES
F, G, B, SH = LENGTHS


def card(cid, visual, title, payload, sample, help_=""):
    return {"id": cid, "visual": visual, "title": title, "help": help_, "sample": sample, "payload": payload}


def cells(rows, highlight=()):
    return [{"line": ln, "length": le, "value": v, "balls": b, "outs": o, "highlight": (ln, le) in highlight}
            for ln, le, v, b, o in rows]


# Finn Allen v pace, overs 1-6: (line, length, strike rate, balls, outs). His overall SR on these balls: 164.
ALLEN = [(O, F, 217.05, 88, 2), (O, G, 162.28, 167, 4), (O, B, 132.12, 165, 9), (O, SH, 219.35, 31, 4),
         (S, F, 235.35, 99, 11), (S, G, 118.26, 115, 9), (S, B, 137.18, 78, 1), (S, SH, 254.55, 22, 1),
         (L, F, 145.45, 11, 2), (L, G, 69.57, 23, 1), (L, B, 92.00, 25, 3),
         (W, F, 176.92, 13, 0), (W, G, 211.11, 9, 1), (W, B, 150.00, 8, 0)]
allen = card(
    "allen-pitch", "pitch_map", "Down leg, Finn Allen's SR drops to 70 and 92",
    {"hand": "RHB", "lines": LINES, "lengths": LENGTHS, "min_balls": 10,
     "metric": {"label": "SR", "format": "int", "higher_better": True, "mid": 164}, "legend": ["Above his SR of 164", "Below"],
     "cells": cells(ALLEN, {(L, G), (L, B)})},
    "Finn Allen v pace · powerplay · men's T20s, Jan 2023–Feb 2026")

allen_shot = card(
    "allen-shot", "metric_bars", "Finn Allen has fallen 11 times flicking pace in the powerplay",
    {"metric": {"label": "Wickets", "format": "int", "signed": False}, "label_width": 150,
     "rows": [{"name": "Drive", "value": 17, "detail": "19 balls per wicket"},
              {"name": "Flick or glance", "value": 11, "highlight": True, "detail": "12 balls per wicket"},
              {"name": "Pull or hook", "value": 7, "detail": "17 balls per wicket"},
              {"name": "Slog", "value": 6, "detail": "12 balls per wicket"},
              {"name": "Work or push", "value": 4, "detail": "27 balls per wicket"}]},
    "Finn Allen v pace · powerplay · men's T20s, Jan 2023–Feb 2026")

# Tim Seifert v pace, all overs: (line, length, % of balls played in control, balls, outs); cells with 15+ balls.
SEIFERT = [(W, G, 47.83, 23, 3), (W, B, 59.26, 27, 2), (W, F, 62.07, 29, 1),
           (O, SH, 63.37, 101, 4), (O, G, 63.58, 302, 16), (O, B, 63.64, 232, 8), (O, F, 69.57, 115, 2),
           (S, B, 63.58, 151, 8), (S, G, 69.09, 220, 12), (S, SH, 74.07, 27, 1), (S, F, 84.68, 124, 6),
           (L, SH, 61.54, 26, 2), (L, B, 63.83, 47, 1), (L, G, 65.96, 47, 1)]
_mid = round(sum(v * b for *_, v, b, _o in SEIFERT) / sum(b for *_, b, _o in SEIFERT))
seifert = card(
    "seifert-pitch", "pitch_map", "Tim Seifert's lowest control %: wide outside off, good length (48%)",
    {"hand": "RHB", "lines": LINES, "lengths": LENGTHS, "min_balls": 15,
     "metric": {"label": "Control %", "format": "pct0", "higher_better": True, "mid": _mid}, "legend": [f"Above his {_mid}%", "Below"],
     "cells": cells(SEIFERT, {(W, G)})},
    "Tim Seifert v pace · men's T20s, Jan 2023–Feb 2026")

CARDS = [allen, allen_shot, seifert]

if __name__ == "__main__":
    assert "localhost" in os.environ.get("DATABASE_URL", ""), "run against the local database"
    from services.snapshots import create_static_snapshot

    slides = [{"type": "card", "card": c, "teams": None} for c in CARDS]
    snap = create_static_snapshot(None, "carousel", {"slides": slides, "title": "Allen & Seifert reply (pitch)", "counter": False},
                                  "Allen & Seifert reply (pitch)", {"reply": "allen-seifert-pitch-v3", "slides": slides},
                                  created_by="reply")
    print(snap["id"], len(slides))
