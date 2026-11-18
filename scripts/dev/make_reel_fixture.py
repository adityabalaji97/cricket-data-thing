"""Write a motion-Reel spec for an IPL retention team from articles/ipl-retention/<team>/slides.json.

    python scripts/dev/make_reel_fixture.py mi [--out reel_mi.json]

MOTION_REEL_PLAN.md M1: the hero scene is real (the squad's top two by wins added, slide 2's metric_bars), and the rest
of the 30-second storyboard (docs/motion_reel_spec.md section 2) plays each carousel card's own visual with the
storyboard's timings: the board, batting, bowling, the calls, the template, the gaps, then the pick-one. Every number
is read from the slides by path, never typed. Captions come from the storyboard's voice lines, timed at the mockup's
three spoken words a second (no voice is generated: M4 replaces this with word timestamps).
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TEAMS = {"mi": ("MI", "Mumbai"), "csk": ("CSK", "Chennai"), "rcb": ("RCB", "Bengaluru"), "kkr": ("KKR", "Kolkata"),
         "dc": ("DC", "Delhi"), "gt": ("GT", "Gujarat"), "lsg": ("LSG", "Lucknow"), "pbks": ("PBKS", "Punjab"),
         "rr": ("RR", "Rajasthan"), "srh": ("SRH", "Hyderabad")}
CREDIT = "hindsightcricket.com · Data: Himanish Ganjoo & TechRadar, Cricsheet"


def slides_for(team: str) -> dict:
    for base in (REPO, REPO.parents[2] if ".claude" in REPO.parts else REPO):
        p = base / "articles" / "ipl-retention" / team / "slides.json"
        if p.exists():
            return json.loads(p.read_text())
    raise SystemExit(f"no slides.json for {team}")


def card(slides, card_id):
    for s in slides["slides"]:
        if s.get("type") == "card" and s["card"].get("id") == card_id:
            return s["card"]
    raise SystemExit(f"no card {card_id}")


def fmt(v, kind):
    sign = "+" if v > 0 else "−" if v < 0 else ""
    return f"{sign}{abs(v):.2f}" if kind == "signed2" else f"{sign}{abs(v):.1f}"


def reel_grid(slides, bowling, attack_file=None):
    """The bowling grid: the regular attack (owner's decision 5, services.squad_view.regular_attack). slides.json
    built since 18 Nov already has it (the carousel switched); for older slides.json (the six busiest) pass an --attack
    file of bowler and bowler-by-phase rows (query-builder output), cells computed exactly as squad_view does."""
    if not attack_file:
        if len(bowling["payload"]["rows"]) != 5:
            print("warning: this slides.json predates the regular-attack grid (18 Nov) and no --attack file was given: "
                  "the Reel shows the carousel's old six busiest", file=sys.stderr)
        return bowling["payload"]
    sys.path.insert(0, str(REPO))
    from services.squad_view import MIN_BOWL, MIN_CELL, regular_attack, sg  # noqa: E402
    q = json.loads(Path(attack_file).read_text())
    players = [{"name": b["name"], "bowl_balls": b["bowl_balls"], "bowl_raa": b["raa"], "bowl": {"innings_count": b["innings_count"]}}
               for b in q["bowlers"]]
    phase = {(r["bowler"], r["phase"]): r for r in q["phase"]}
    short = lambda n: n if len(n.split()) < 2 or n.split()[0].isupper() else f"{n.split()[0][0]} {n.split()[-1]}"  # noqa: E731
    rows = []
    for p in regular_attack(players, min_balls=MIN_BOWL):
        cells = []
        for ph in ("powerplay", "middle", "death"):
            r = phase.get((p["name"], ph))
            if not r or r["balls"] < MIN_CELL:
                cells.append(None)
                continue
            v = 24 * (r.get("raa") or 0) / r["balls"]
            cells.append({"value": round(v, 1), "text": sg(v, 1), "sub": f"{r['wickets']}w · {r['balls']}b"})
        rows.append({"name": short(p["name"]), "sub": f"{sg(p['bowl_raa'] or 0, 0)} runs saved", "cells": cells})
    return {**bowling["payload"], "rows": rows}


def timing(lines, starts):
    """Words evenly at 1/3 s from each line's start (three spoken words a second)."""
    words, lengths = [], []
    for line, st in zip(lines, starts):
        n = len(line.split())
        words.append([round(st + i / 3, 3) for i in range(n)])
        lengths.append(round(n / 3, 3))
    return {"lines": lines, "starts": starts, "lengths": lengths, "words": words}


def build(team: str, attack_file=None) -> dict:
    code, place = TEAMS[team]
    sl = slides_for(team)
    carried = card(sl, "carried")
    top = carried["payload"]["rows"][:2]
    fmt_w = carried["payload"]["metric"]["format"]
    board = sl["slides"][0]["hero"]["payload"]
    batting, bowling, cases = card(sl, "batting"), card(sl, "bowling"), card(sl, "cases")
    template, fits = card(sl, "template"), card(sl, "fits")
    rohit = cases["payload"]["cases"][0]
    grid = reel_grid(sl, bowling, attack_file)

    names = [p["name"] for g in board["groups"] for p in g["players"]]

    def chip(full):
        """The board's chip for a full name ("Suryakumar Yadav" -> "S Yadav")."""
        return next((n for n in names if n.split()[-1] == full.split()[-1] and n[0] == full[0]), full)

    def last(n):
        return n.split()[-1]

    lines = [
        f"{last(top[0]['name'])} added {fmt(top[0]['value'], fmt_w)[1:]} wins. {last(top[1]['name'])}, traded in: {fmt(top[1]['value'], fmt_w)[1:]}.",
        "Only three others clearly added wins.",
        f"{last(batting['payload']['rows'][0]['name'])} leads the batting.",
        f"{last(bowling['payload']['rows'][0]['name'])} at the death saves runs.",
        "Three calls, each with a case for and against.",
        f"{template['title'].split('.')[0]}.",
        f"{fits['payload']['rows'][0]['options'][0]['name']} is available.",
    ]
    starts = [0.0, 4.3, 8.1, 12.3, 16.5, 23.5, 27.1]
    scenes = [
        {"kind": "hero", "start": 0.0, "end": 4.2, "chapter": 0, "kicker": "Wins added since the 2025 auction",
         "data": {"name": top[0]["name"], "value": top[0]["value"], "format": fmt_w, "unit": "wins", "from": 0.4,
                  "gloss": top[0].get("detail"),
                  "second": {"name": top[1]["name"], "value": top[1]["value"], "unit": "wins", "tag": "traded in", "at": 1.4},
                  "scope": carried["sample"]}},
        {"kind": "squad_board", "start": 4.2, "end": 8.0, "chapter": 1, "kicker": "The squad · wins added", "payload": board,
         "scope": carried["sample"],
         # the ring follows the voice through the next three on the "carried" card (chip names as the board writes them)
         "beats": [{"at": at, "key": chip(row["name"])} for at, row in zip((5.6, 6.3, 7.0), carried["payload"]["rows"][2:5])]},
        {"kind": batting["visual"], "start": 8.0, "end": 12.2, "chapter": 1, "kicker": "Batting by role",
         "payload": batting["payload"], "scope": batting["sample"],
         "beats": [{"at": 8.1, "key": batting["payload"]["rows"][0]["name"]}]},
        {"kind": bowling["visual"], "start": 12.2, "end": 16.4, "chapter": 1, "kicker": "Bowling by phase",
         "payload": grid, "scope": "The regular attack: the five who bowl most per game · runs saved per 24 balls · IPL 2025-26",
         # the ring on the top row's last cell ("<row> · <column>"); box is only used if the kind plays the fallback
         "beats": [{"at": 14.4, "key": f"{max(grid['rows'], key=lambda r: (r['cells'][-1] or {}).get('value', -99))['name']} · {grid['cols'][-1]}",
                    "box": {"x": 0.755, "y": 0.11, "w": 0.245, "h": 0.09}}]},
        {"kind": cases["visual"], "start": 16.4, "end": 23.4, "chapter": 2, "kicker": "Three calls",
         "payload": cases["payload"], "scope": cases["sample"], "plan": {"case_every": 2.3},
         "pages": {"field": "cases", "size": 1, "zoom": 1.3},  # one call at a time, at a size a phone can read
         "beats": [{"at": 16.4 + 2.3 * i, "key": c["name"]} for i, c in enumerate(cases["payload"]["cases"])]},
        {"kind": template["visual"], "start": 23.4, "end": 27.0, "chapter": 3, "kicker": "Against the winners' template",
         "payload": template["payload"], "scope": template["sample"],
         "beats": [{"at": 25.8, "key": fits["payload"]["rows"][0]["label"]}]},
        {"kind": fits["visual"], "start": 27.0, "end": 29.4, "chapter": 3, "kicker": "Who fills the gaps",
         "payload": fits["payload"], "scope": fits["sample"],
         "beats": [{"at": 27.2, "key": fits["payload"]["rows"][0]["options"][0]["name"]}],
         "pages": {"field": "rows", "size": 1, "count": 1, "zoom": 1.12}},  # the gap the voice names; the rest stay in the carousel
        {"kind": "pick_one", "start": 29.4, "end": 32.4, "chapter": 3, "captions": False,
         "data": {"question": f"{rohit['name']}, {rohit['price']}:", "lit": "keep or release?",
                  "options": [{"label": "Keep", "line": rohit["for"]}, {"label": "Release", "line": rohit["against"].split(";")[0]}],
                  "send": {"text": f"Send this to a {place} fan", "at": 30.6},
                  "credit": [cases["sample"], CREDIT]}},
    ]
    return {
        "team": code, "fps": 30, "duration": 32.4,
        "chapters": [{"label": "The core", "start": 0, "end": 4.2}, {"label": "The squad", "start": 4.2, "end": 16.4},
                     {"label": "The calls", "start": 16.4, "end": 23.4}, {"label": "The gap", "start": 23.4, "end": 32.4}],
        "scenes": scenes,
        "timing": timing(lines, starts),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("team", choices=sorted(TEAMS))
    ap.add_argument("--out")
    ap.add_argument("--attack", help="bowler and bowler-by-phase rows for the Reel's regular-attack grid (see reel_grid)")
    a = ap.parse_args()
    out = json.dumps(build(a.team, a.attack), ensure_ascii=False, indent=1)
    if a.out:
        Path(a.out).write_text(out)
    else:
        print(out)
