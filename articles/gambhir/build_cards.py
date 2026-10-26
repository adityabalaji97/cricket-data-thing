"""
"Gambhir's XI" as Hindsight story cards. Every number comes from data/regimes.csv (regimes.py) or the two figures
computed below from data/lr_innings.csv; nothing is typed in by hand except the KKR 2011-17 with/without-Gambhir split,
which came from one read-only query (see GAMBHIR_AT_CREASE).

Saves two carousel snapshots (article, instagram) to the LOCAL database; prepare.py does production.

    DATABASE_URL=postgresql://localhost:5432/hindsight_local python articles/gambhir/build_cards.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

R = pd.read_csv(HERE / "data" / "regimes.csv").set_index("label")
G_STINTS = ["KKR, captain 2011–17", "LSG, mentor 2022–23", "KKR, mentor 2024"]
AFTER = {"KKR, captain 2011–17": "KKR 2018–23", "LSG, mentor 2022–23": "LSG 2024–26", "KKR, mentor 2024": "KKR 2025–26"}
OTHERS = ["CSK under Dhoni 2008–23", "MI under Rohit 2013–23"]
INTL = ["India, coach Jul 2024–", "India under Dravid, Nov 2021–Jun 2024", "England, Jul 2024–", "Australia, Jul 2024–",
        "South Africa, Jul 2024–", "New Zealand, Jul 2024–"]
SHORT = {"KKR, captain 2011–17": "KKR 2011–17", "LSG, mentor 2022–23": "LSG 2022–23", "KKR, mentor 2024": "KKR 2024",
         "Delhi, captain 2018 (6 games)": "Delhi 2018", "CSK under Dhoni 2008–23": "CSK, Dhoni", "MI under Rohit 2013–23": "MI, Rohit",
         "India, coach Jul 2024–": "India, Gambhir", "India under Dravid, Nov 2021–Jun 2024": "India, Dravid",
         "England, Jul 2024–": "England", "Australia, Jul 2024–": "Australia", "South Africa, Jul 2024–": "South Africa",
         "New Zealand, Jul 2024–": "New Zealand"}
DETAIL = {"KKR, captain 2011–17": "captain", "LSG, mentor 2022–23": "mentor", "KKR, mentor 2024": "mentor",
          "Delhi, captain 2018 (6 games)": "captain, 6 games", "KKR 2018–23": "after him", "LSG 2024–26": "after him",
          "KKR 2025–26": "after him"}
#: KKR's IPL batting 2011-17, legal balls with both hands known (deliveries + delivery_details): 12,039 balls, 6,573 of
#: them left-right; Gambhir at the crease for 5,037, of which 4,689 left-right.
GAMBHIR_AT_CREASE = {"with": 4689 / 5037, "without": (6573 - 4689) / (12039 - 5037)}
IPL_LR = {"2011–17": 47.2, "2024": 54.9}  # the IPL's own left-right share of balls, from data/lr_innings.csv


def card(cid, visual, title, payload, sample, help_=""):
    return {"id": cid, "visual": visual, "title": title, "help": help_, "sample": sample, "payload": payload}


def bars(labels, col, fmt, signed, highlight=()):
    return [{"name": SHORT.get(l, l), "value": float(R.loc[l, col]), "highlight": l in highlight,
             "detail": DETAIL.get(l)} for l in labels]


ipl_rows = G_STINTS + ["Delhi, captain 2018 (6 games)"] + OTHERS + list(AFTER.values())
allrounders = card(
    "allrounders", "metric_bars", "Gambhir's IPL teams picked more all-rounders than the league, and fewer once he'd gone",
    {"metric": {"label": "All-rounders per XI, against the IPL that season", "format": "signed1", "signed": True}, "label_width": 120,
     "rows": bars(ipl_rows, "all_rounders_vs_ipl", "signed1", True, G_STINTS + ["Delhi, captain 2018 (6 games)"])},
    "IPL 2008–2026 · playing XIs, against the league average in the same seasons",
    "All-rounder: had batted in the top 7 and bowled in 40%+ of his previous 20 T20s (or 1,500 runs and 150 overs)")

lr_ipl = card(
    "lr_ipl", "metric_bars", f"KKR 2024 batted with a left-right pair for {R.loc['KKR, mentor 2024', 'lr_share']:.0f}% of balls, "
                             f"{R.loc['KKR, mentor 2024', 'lr_vs_ipl']:.0f} points above the IPL",
    {"metric": {"label": "Left-right pair at the crease, % of balls, against the IPL", "format": "signed1", "signed": True},
     "label_width": 120, "rows": bars(G_STINTS + OTHERS + list(AFTER.values()), "lr_vs_ipl", "signed1", True, G_STINTS)},
    "IPL · legal balls with both batters' hands known, against the league in the same seasons")

g = GAMBHIR_AT_CREASE
gambhir_self = card(
    "gambhir_self", "metric_bars",
    f"Captain Gambhir was KKR's left-right pair: {100 * g['with']:.0f}% of balls with him in, {100 * g['without']:.0f}% without",
    {"metric": {"label": "Left-right pair at the crease, % of balls", "format": "pct0", "signed": False}, "label_width": 150,
     "rows": [{"name": "Gambhir batting", "value": round(100 * g["with"], 1), "highlight": True, "detail": "5,037 balls"},
              {"name": "IPL, 2011–17", "value": IPL_LR["2011–17"], "detail": "every team"},
              {"name": "KKR, Gambhir out", "value": round(100 * g["without"], 1), "detail": "7,002 balls"}]},
    "KKR batting, IPL 2011–17 · legal balls with both batters' hands known")

india_lhb = card(
    "india_lhb", "metric_bars", "India pick more left-handed batters under Gambhir than any of their rivals",
    {"metric": {"label": "Left-handed batting options per XI", "format": "dec1", "signed": False}, "label_width": 120,
     "rows": sorted(bars(INTL, "lhb_bat_options", "dec1", False, ["India, coach Jul 2024–"]), key=lambda r: -r["value"])},
    "Men's T20Is since 27 Jul 2024 (India under Dravid: Nov 2021–Jun 2024)",
    "Batting option: batted in the top 7 in 40%+ of his previous 20 T20s, or had 1,500 career runs")

india_lr = card(
    "india_lr", "metric_bars", f"India bat with a left-right pair for {R.loc['India, coach Jul 2024–', 'lr_share']:.0f}% of balls, "
                               f"from {R.loc['India under Dravid, Nov 2021–Jun 2024', 'lr_share']:.0f}% under Dravid",
    {"metric": {"label": "Left-right pair at the crease, % of balls", "format": "pct0", "signed": False}, "label_width": 120,
     "rows": sorted(bars(INTL, "lr_share", "pct0", False, ["India, coach Jul 2024–"]), key=lambda r: -r["value"])},
    "Men's T20Is since 27 Jul 2024 (India under Dravid: Nov 2021–Jun 2024)")

india_ar = card(
    "india_ar", "metric_bars", "More all-rounders than under Dravid, but fewer than England, Australia or New Zealand",
    {"metric": {"label": "All-rounders per XI", "format": "dec1", "signed": False}, "label_width": 120,
     "rows": sorted(bars(INTL, "all_rounders", "dec1", False, ["India, coach Jul 2024–"]), key=lambda r: -r["value"])},
    "Men's T20Is since 27 Jul 2024 (India under Dravid: Nov 2021–Jun 2024)",
    "All-rounder: had batted in the top 7 and bowled in 40%+ of his previous 20 T20s (or 1,500 runs and 150 overs)")

after = card(
    "after", "pair_dumbbell", "Every IPL team won less once Gambhir had gone. India win as often as they did under Dravid",
    {"series": ["With Gambhir", "Without him"], "format": "pct0", "values": True,
     "rows": [{"label": "KKR·2011–17", "a": float(R.loc["KKR, captain 2011–17", "win_pct"]), "b": float(R.loc["KKR 2018–23", "win_pct"])},
              {"label": "LSG·2022–23", "a": float(R.loc["LSG, mentor 2022–23", "win_pct"]), "b": float(R.loc["LSG 2024–26", "win_pct"])},
              {"label": "KKR·2024", "a": float(R.loc["KKR, mentor 2024", "win_pct"]), "b": float(R.loc["KKR 2025–26", "win_pct"])},
              {"label": "India", "a": float(R.loc["India, coach Jul 2024–", "win_pct"]),
               "b": float(R.loc["India under Dravid, Nov 2021–Jun 2024", "win_pct"])}]},
    "Win % of decided games · without him: the seasons after he left; India: Dravid's 2021–24",
    "Squads change too: auctions rebuild a team, so this is what happened, not why")

ARTICLE = [gambhir_self, lr_ipl, allrounders, india_lhb, india_lr, india_ar, after]

HOOK = (f"Gambhir's 2024 KKR batted with a left-right pair for {R.loc['KKR, mentor 2024', 'lr_share']:.0f}% of balls. "
        f"The IPL as a whole: {IPL_LR['2024']:.0f}%.")
INSTAGRAM = ([{"type": "hook", "kicker": "Gautam Gambhir · IPL & India", "text": HOOK, "sub": "Swipe through the data",
               "cover": "hero",
               "hero": {"rows": [{"name": "KKR 2024", "value": float(R.loc["KKR, mentor 2024", "lr_share"]), "highlight": True},
                                 {"name": "IPL 2024", "value": IPL_LR["2024"], "highlight": False},
                                 {"name": "KKR 2025–26", "value": float(R.loc["KKR 2025–26", "lr_share"]), "highlight": False}],
                        "format": "pct0", "label": "Left-right pair at the crease, % of balls", "card": lr_ipl}}]
             + [{"type": "card", "card": c, "teams": None} for c in (lr_ipl, gambhir_self, allrounders, india_lhb, india_ar, after)]
             + [{"type": "end", "heading": "Run it yourself",
                 "body": "Every number comes from ball-by-ball data and the playing XIs. Ask your own question on the query builder: it's free."}])

if __name__ == "__main__":
    assert "localhost" in os.environ.get("DATABASE_URL", ""), "run against the local database"
    from services.snapshots import create_static_snapshot

    out = {}
    for name, slides in (("article", [{"type": "card", "card": c, "teams": None} for c in ARTICLE]), ("instagram", INSTAGRAM)):
        snap = create_static_snapshot(None, "carousel", {"slides": slides, "title": f"Gambhir's XI ({name})"},
                                      f"Gambhir's XI ({name})", {"article": "gambhirs-xi", "set": name, "slides": slides},
                                      created_by="article-gambhir")
        out[name] = (snap["id"], len(slides))
    print(out)
