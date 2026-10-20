"""
"Dube, revisited" as Hindsight story cards. Every number is copied from a Hindsight query-builder result (men's T20,
batting view unless noted); the query behind each card is in LINKS.

    DATABASE_URL=postgresql://localhost:5432/hindsight_local python articles/dube-revisited/build_cards.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

Q = "https://hindsightcricket.com/query?"
LINKS = {
    "seasons": Q + "start_date=2022-01-01&leagues=IPL&batters=Shivam+Dube&metrics_perspective=batting&group_by=season&fmt=mens-t20",
    "india": Q + "start_date=2024-07-27&batters=Shivam+Dube&include_international=true&metrics_perspective=batting&group_by=batter&fmt=mens-t20",
    "india_bowl": Q + "start_date=2024-07-27&bowlers=Shivam+Dube&include_international=true&metrics_perspective=bowling&group_by=bowler&fmt=mens-t20",
    "kind": Q + "start_date=2022-01-01&leagues=IPL&batters=Shivam+Dube&metrics_perspective=batting&group_by=season&group_by=bowl_kind&fmt=mens-t20",
    "style": Q + "start_date=2022-01-01&leagues=IPL&batters=Shivam+Dube&bowl_kind=spin+bowler&metrics_perspective=batting&group_by=season&group_by=bowl_style&fmt=mens-t20",
    "shots": Q + "start_date=2023-01-01&end_date=2025-12-31&leagues=IPL&batters=Shivam+Dube&bowl_kind=spin+bowler&metrics_perspective=batting&group_by=season&group_by=shot_family&fmt=mens-t20",
    "positions": Q + "start_date=2025-01-01&leagues=IPL&batters=Shivam+Dube&batters=Dewald+Brevis&metrics_perspective=batting&group_by=batter&group_by=season&group_by=batting_position&fmt=mens-t20",
}

#: IPL by season: (season, innings, SR, Impact per innings, WPA, average leverage, % of balls from spin)
SEASONS = [(2022, 11, 156.2, 1.97, -0.16, 0.08, 40.5), (2023, 14, 158.3, 1.73, -0.33, 0.09, 45.1),
           (2024, 14, 162.3, 0.95, 0.08, 0.08, 23.0), (2025, 14, 132.2, 1.80, 0.65, 0.16, 43.3),
           (2026, 12, 158.8, -1.39, -0.46, 0.10, 19.4)]
INDIA = {"innings": 38, "runs": 743, "sr": 158.8, "impact_inn": 2.20, "wpa": 0.48}


def card(cid, visual, title, payload, sample, help_=""):
    return {"id": cid, "visual": visual, "title": title, "help": help_, "sample": sample, "payload": payload}


impact = card(
    "impact", "metric_bars", "Dube's strike rate fell in 2025. His Impact didn't",
    {"metric": {"label": "Impact per innings", "format": "signed1", "signed": True}, "label_width": 130,
     "rows": [{"name": f"IPL {y}", "value": imp, "highlight": y == 2025, "detail": f"SR {sr:.0f} · {n} inns"}
              for y, n, sr, imp, *_ in SEASONS]
             + [{"name": "India T20Is", "value": INDIA["impact_inn"], "detail": f"since Jul 2024 · SR {INDIA['sr']:.0f}"}]},
    "Shivam Dube, IPL 2022–26 and T20Is under Gambhir",
    "Impact: runs added to the team's projected total while he batted (his runs, minus what his dismissals cost)")

pressure = card(
    "pressure", "metric_bars", "In 2025 Dube batted under nearly twice the pressure of 2023, and added the most win probability",
    {"metric": {"label": "Average leverage of his balls", "format": "dec2", "signed": False}, "label_width": 130,
     "rows": [{"name": f"IPL {y}", "value": lev, "highlight": y == 2025, "detail": f"win prob. added {wpa:+.2f}"}
              for y, n, sr, imp, wpa, lev, _ in SEASONS]},
    "Shivam Dube, IPL 2022–26",
    "Leverage: how much a ball can swing the result (the game's average is about 0.1). Win prob. added: in whole games")

spin = card(
    "spin", "pair_dumbbell", "Against off-spin, the ball turning away from him, Dube went from 39 runs above par to 17 below",
    {"series": ["2023", "2025"], "format": "signed1", "values": True,
     "rows": [{"label": "Off-spin", "a": 38.84, "b": -17.10, "highlight": True},
              {"label": "Wrist-spin", "a": 42.17, "b": -14.08},
              {"label": "All·spin", "a": 34.37, "b": -1.20},
              {"label": "Pace", "a": -16.51, "b": 2.61}]},
    "Shivam Dube, IPL 2023 v 2025 · runs above par per 100 balls",
    "Runs above the average for the game state. Wrist-spin: leg-spinners with a googly. Off-spin: 45 balls in 2023, 44 in 2025")

spin_share = card(
    "spin_share", "metric_bars", "When Dube hits spin, teams stop bowling it to him",
    {"metric": {"label": "Share of his balls bowled by spinners", "format": "pct0", "signed": False}, "label_width": 130,
     "rows": [{"name": f"IPL {y}", "value": sp, "highlight": y in (2024, 2026), "detail": None}
              for y, n, sr, imp, wpa, lev, sp in SEASONS]},
    "Shivam Dube, IPL 2022–26 · balls faced")

order = card(
    "order", "metric_bars", "CSK 2026: Dube batted at 4 in three innings of twelve. Brevis at 5 struggled",
    {"metric": {"label": "Impact per innings", "format": "signed1", "signed": True}, "label_width": 140,
     "rows": [{"name": "Dube at 4", "value": -5.82, "highlight": True, "detail": "3 inns · SR 156"},
              {"name": "Dube at 6", "value": -2.74, "highlight": True, "detail": "5 inns · SR 137"},
              {"name": "Dube at 7", "value": 3.62, "highlight": True, "detail": "4 inns · SR 202"},
              {"name": "Brevis at 5", "value": -2.82, "detail": "5 inns · SR 136"},
              {"name": "Brevis at 5, 2025", "value": 8.28, "detail": "3 inns · SR 202"}]},
    "IPL 2026 (Brevis also 2025) · small samples: a few innings each")

ARTICLE = [impact, pressure, spin, spin_share, order]
HOOK = "Shivam Dube's strike rate fell to 132 in 2025, from 162. His win probability added was the best of his CSK career."
_hero = {"rows": [{"name": f"IPL {y}", "value": imp, "highlight": y == 2025} for y, n, sr, imp, *_ in SEASONS[1:4]],
         "format": "signed1", "label": "Impact per innings", "card": impact}
INSTAGRAM = ([{"type": "hook", "kicker": "Shivam Dube · IPL", "text": HOOK, "sub": "Swipe through the data",
               "cover": "hero", "hero": _hero}]
             + [{"type": "card", "card": c, "teams": None} for c in (impact, pressure, spin, spin_share, order)]
             + [{"type": "end", "heading": "Run it yourself",
                 "body": "Every number comes from ball-by-ball data. Ask your own question on the query builder: it's free."}])

if __name__ == "__main__":
    assert "localhost" in os.environ.get("DATABASE_URL", ""), "run against the local database"
    from services.snapshots import create_static_snapshot

    out = {}
    for name, slides in (("article", [{"type": "card", "card": c, "teams": None} for c in ARTICLE]), ("instagram", INSTAGRAM)):
        snap = create_static_snapshot(None, "carousel", {"slides": slides, "title": f"Dube, revisited ({name})"},
                                      f"Dube, revisited ({name})", {"article": "dube-revisited", "set": name, "slides": slides},
                                      created_by="article-dube")
        out[name] = (snap["id"], len(slides))
    print(out)
