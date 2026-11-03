"""
The Rishabh Pant - Kuldeep Yadav trade, 3 Nov 2026: Delhi Capitals got Pant back from Lucknow Super Giants and Kuldeep
went the other way (news 2 Nov; Delhi also sent T Natarajan to Sunrisers for Zeeshan Ansari, the wrist spinner who
now stands in for Kuldeep). Every number is IPL data to the end of the 2026 season, plus the 2025 auction (Cricbuzz,
data/auction_raw): Pant's ₹27 crore and his 81-bid trail, Kuldeep's ₹13.25 crore retention.

    python articles/pant-kuldeep/post.py              # dry run
    python articles/pant-kuldeep/post.py --write      # queue, render, voiced Reel (reel.json), thread
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

KEY = "spotlight-pant-kuldeep-trade-2026-11-03"
SITE = "https://hindsightcricket.com"
PANT, KULDEEP, ANSARI = "Rishabh Pant", "Kuldeep Yadav", "Zeeshan Ansari"
THREAD_PLAYERS = [KULDEEP, PANT, ANSARI]
IPL = {"fmt": "T20", "include_international": False, "leagues": ["IPL"], "start_date": date(2022, 1, 1),
       "end_date": date(2026, 10, 31)}
SEASONS = [2022, 2023, 2024, 2025, 2026]
TEAM = {"Delhi Capitals": "Delhi", "Lucknow Super Giants": "Lucknow", "Sunrisers Hyderabad": "Hyderabad",
        "Royal Challengers Bengaluru": "Bengaluru"}
TRAIL = ROOT / "data/auction_raw/ipl/2025/completed_trail.csv"
BIDDERS = [("LSG", "Lucknow", "#b6f24a"), ("DC", "Delhi", "#4f7fe0"), ("RCB", "Bengaluru", "#e5484d"),
           ("SRH", "Hyderabad", "#F26522")]
GROUNDS = [("Feroz Shah Kotla", "Delhi (Kotla)"), ("Ekana Cricket Stadium", "Lucknow (Ekana)")]
LINES = ["WIDE_OUTSIDE_OFFSTUMP", "OUTSIDE_OFFSTUMP", "ON_THE_STUMPS", "DOWN_LEG"]
LENGTHS = ["FULL", "GOOD_LENGTH", "SHORT_OF_A_GOOD_LENGTH"]


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
    base = {**IPL, **{k: kw.pop(k) for k in list(kw) if k in IPL}}
    return run_deliveries_query(db, **base, **kw)["data"]


def econ(r):
    return 6 * r["runs"] / r["balls"]


# ---- slides -----------------------------------------------------------------------------------------------------

def seasons_card(db):
    p = {r["year"]: r for r in q(db, batters=[PANT], group_by=["year", "batting_team"], metrics_perspective="batting")}
    k = {r["year"]: r for r in q(db, bowlers=[KULDEEP], group_by=["year", "bowling_team"], metrics_perspective="bowling")}
    both = [y for y in SEASONS if y in p and y in k]
    assert all(k[y]["wpa"] > p[y]["wpa"] for y in both), "Kuldeep no longer ahead every season"
    rows = [{"label": f"{y}", "a": round(k[y]["wpa"], 2), "b": round(p[y]["wpa"], 2), "highlight": y >= 2025} for y in both]
    c = card("seasons", "pair_dumbbell",
             f"Kuldeep added more IPL wins than Pant in all {len(both)} seasons they both played",
             {"series": ["Kuldeep Yadav", "Rishabh Pant"], "format": "signed2", "values": True, "full_labels": True,
              "no_diff": True, "rows": rows},
             "Wins added (T20 Primer): win probability added, summed over a season · IPL 2022-26")
    tot_k = sum(k[y]["wpa"] for y in both)
    tot_p = sum(p[y]["wpa"] for y in both)
    return c, {"p": p, "k": k, "both": both, "tot_k": tot_k, "tot_p": tot_p}


def money_card():
    rows = [r for r in csv.DictReader(open(TRAIL)) if r["playerName"] == PANT]
    price = lambda s: float(s.replace(" Cr", "")) if "Cr" in s else float(s.replace(" L", "")) / 100  # noqa: E731
    bids = sorted(({"n": 0, "seq": int(r["seq"]), "team": r["team"], "price": price(r["price"]), "status": r["status"]}
                   for r in rows), key=lambda b: -b["seq"])  # the trail is newest first
    for i, b in enumerate(bids, 1):
        b["n"] = i
    rtm = next(b for b in bids if b["status"] == "rtm")
    # Who Lucknow were bidding against, stretch by stretch (the other side changes when a new franchise comes in).
    phases, cur = [], None
    for b in bids[:-2]:
        if b["team"] != "LSG" and b["team"] != cur:
            if phases:
                phases[-1]["to"] = b["n"] - 1
            cur = b["team"]
            phases.append({"from": max(1, b["n"] - 1), "to": b["n"], "label": f"v {dict((k_, l_) for k_, l_, _ in BIDDERS)[cur]}"})
    phases[-1]["to"] = rtm["n"] - 1
    final = bids[-1]
    assert final["team"] == "LSG" and final["price"] == 27.0
    c = card("money", "bid_trail",
             f"Lucknow paid ₹{final['price']:.0f} crore for Pant after {len(bids)} bids. Delhi had matched at ₹{rtm['price']:.2f}",
             {"bids": [{"n": b["n"], "team": b["team"], "price": b["price"]} for b in bids],
              "teams": [{"key": k_, "label": l_, "colour": c_} for k_, l_, c_ in BIDDERS], "unit": "₹ crore",
              "phases": phases,
              "marks": [{"n": rtm["n"], "text": f"Delhi match ₹{rtm['price']:.2f}"},
                        {"n": final["n"], "text": f"Lucknow ₹{final['price']:.0f}"}]},
             "IPL 2025 auction, every bid for Pant · bids by franchise in the key", kicker="The money")
    return c, {"bids": len(bids), "rtm": rtm["price"], "final": final["price"]}


def pant_card(db, sc):
    p = sc["p"]
    rows = [{"name": f"{y} · {TEAM.get(p[y]['batting_team'], p[y]['batting_team'])}", "value": round(p[y]["raa_per_100"], 1),
             "highlight": p[y]["batting_team"] == "Lucknow Super Giants",
             "detail": f"{p[y]['runs']} runs, strike rate {p[y]['strike_rate']:.0f}"} for y in SEASONS if y in p]
    l25, l26 = p[2025]["raa_per_100"], p[2026]["raa_per_100"]
    assert l25 < 0 and l26 < 0
    h2h = q(db, batters=[PANT], bowlers=[KULDEEP], group_by=["batter"], metrics_perspective="batting",
            start_date=date(2008, 1, 1), leagues=[])
    h = h2h[0] if h2h else None
    c = card("pant", "metric_bars",
             f"Pant at Lucknow: {abs(l25):.0f} and {abs(l26):.0f} runs below par per 100 balls",
             {"metric": {"label": "Runs above par per 100 balls", "format": "signed1", "signed": True}, "label_width": 160,
              "rows": rows},
             "Rishabh Pant, IPL by season · didn't play 2023", kicker="Pant's two years")
    return c, {"l25": l25, "l26": l26, "h2h": h}


def innings_card(db):
    """Pant's highs among the lows: every IPL innings since 2022, runs on top and runs above par below, a season a band."""
    rows = sorted(q(db, batters=[PANT], group_by=["match_id", "year", "batting_team", "bowling_team"],
                    metrics_perspective="batting"), key=lambda r: (r["year"], r["match_id"]))
    side = lambda r: TEAM.get(r["batting_team"], r["batting_team"])  # noqa: E731
    luck = [r for r in rows if r["batting_team"] == "Lucknow Super Giants"]
    below = sum(1 for r in luck if r["raa"] < 0)
    highs = sorted((r for r in luck if r["raa"] >= 10), key=lambda r: -r["runs"])
    assert len(highs) == 2 and below > len(luck) / 2, (len(highs), below, len(luck))
    note = lambda r: f"{r['runs']} off {r['balls']}"  # noqa: E731
    games = [{"label": f"{r['year']} v {TEAM.get(r['bowling_team'], r['bowling_team'].split()[0])}: {note(r)}",
              "period": f"{side(r)} {r['year']}", "top": r["runs"], "bottom": round(r["raa"], 1),
              "marked": r in highs, **({"note": note(r)} if r in highs else {})} for r in rows]
    periods = list(dict.fromkeys(g["period"] for g in games))
    c = card("innings", "game_timeline",
             f"Pant at Lucknow: below par in {below} of {len(luck)} innings, with {note(highs[0])} and {note(highs[1])}",
             {"games": games, "periods": [{"key": k_, "label": k_} for k_ in periods],
              "top": {"label": "Runs, each innings", "format": "int"},
              "bottom": {"label": "Runs above par", "format": "signed1"}},
             "Rishabh Pant, every IPL innings 2022-26 · didn't play 2023 · dashed: each season's average",
             kicker="Highs among the lows")
    opp = {TEAM.get(r["bowling_team"], r["bowling_team"]) for r in highs}
    both = (f"{note(highs[0])} and {note(highs[1])}, both against {opp.pop()}" if len(opp) == 1
            else " and ".join(f"{note(r)} v {TEAM.get(r['bowling_team'], r['bowling_team'])}" for r in highs))
    return c, {"below": below, "luck": len(luck), "top": note(highs[0]), "both": both}


PANT_GROUNDS = {"Feroz Shah Kotla": "Delhi (Kotla)", "Ekana Cricket Stadium": "Lucknow (Ekana)",
                "Dubai International": "Dubai", "Wankhede": "Mumbai (Wankhede)", "M Chinnaswamy": "Bengaluru",
                "Maharashtra Cricket": "Pune", "Zayed": "Abu Dhabi", "Sharjah": "Sharjah"}


def pant_grounds_card(db):
    """Pant at each IPL ground he's batted 90+ balls on since 2016: his old home against his last one."""
    short = lambda v: next((l_ for k_, l_ in PANT_GROUNDS.items() if v.startswith(k_)), None)  # noqa: E731
    rows = [r for r in q(db, batters=[PANT], group_by=["venue"], metrics_perspective="batting", start_date=date(2016, 1, 1))
            if r["balls"] >= 90 and short(r["venue"])]
    by = {short(r["venue"]): r for r in rows}
    kot, ek = by["Delhi (Kotla)"], by["Lucknow (Ekana)"]
    assert kot["raa_per_100"] > 0 > ek["raa_per_100"]
    bars = [{"name": short(r["venue"]), "value": round(r["raa_per_100"], 1), "highlight": r in (kot, ek),
             "detail": f"{r['balls']} balls, strike rate {r['strike_rate']:.0f}"}
            for r in sorted(rows, key=lambda r: -r["raa_per_100"])]
    c = card("pant-grounds", "metric_bars",
             f"Pant at the Kotla: {kot['raa_per_100']:.0f} runs above par per 100 balls. At the Ekana: {abs(ek['raa_per_100']):.0f} below",
             {"metric": {"label": "Runs above par per 100 balls", "format": "signed1", "signed": True}, "label_width": 160,
              "rows": bars},
             "Rishabh Pant, IPL since 2016 · grounds where he's faced 90+ balls", kicker="Coming home")
    return c, {"kot": kot, "ek": ek}


def delhi_slot(db):
    """Who batted where for Delhi once Pant left (2025-26), by runs above par per 100 balls, top six."""
    rows = {int(r["batting_position"]): r for r in q(db, batting_teams=["Delhi Capitals"], group_by=["batting_position"],
                                                      metrics_perspective="batting", start_date=date(2025, 1, 1))}
    below = [n for n in range(1, 7) if rows[n]["raa_per_100"] < 0]
    assert below == [4], below
    pd = q(db, batters=[PANT], batting_teams=["Delhi Capitals"], group_by=["batter"], metrics_perspective="batting")[0]
    return {"no4": rows[4]["raa_per_100"], "no4_sr": rows[4]["strike_rate"], "pant_dc": pd["raa_per_100"],
            "pant_dc_sr": pd["strike_rate"]}


def grounds_card(db):
    k = {r["venue"]: r for r in q(db, bowlers=[KULDEEP], group_by=["venue"], metrics_perspective="bowling")}
    allspin = {r["venue"]: r for r in q(db, group_by=["venue"], bowl_kind=["spin bowler"], metrics_perspective="bowling",
                                         start_date=date(2024, 1, 1))}
    rows = [{"label": label, "a": round(econ(allspin[v]), 2), "b": round(econ(k[v]), 2), "highlight": "Ekana" in v}
            for v, label in GROUNDS]
    kd, kl = econ(k[GROUNDS[0][0]]), econ(k[GROUNDS[1][0]])
    c = card("grounds", "pair_dumbbell",
             f"Kuldeep at Delhi's ground: {kd:.1f} an over. At Lucknow's: {kl:.1f}",
             {"series": ["All spinners, 2024-26", "Kuldeep, 2022-26"], "format": "dec2", "values": True, "full_labels": True,
              "no_diff": True, "rows": rows},
             f"IPL, runs an over · Kuldeep {k[GROUNDS[0][0]]['balls'] // 6} overs at Kotla, "
             f"{k[GROUNDS[1][0]]['balls'] // 6} at Ekana", kicker="The new home")
    return c, {"kd": kd, "kl": kl, "ko": k[GROUNDS[1][0]]["balls"] // 6,
               "sd": econ(allspin[GROUNDS[0][0]]), "sl": econ(allspin[GROUNDS[1][0]])}


def dip_card(db):
    def cells(a, b):
        rows = q(db, bowlers=[KULDEEP], group_by=["line", "length"], bat_hand="RHB", metrics_perspective="bowling",
                 start_date=a, end_date=b)
        return {(r["line"], r["length"]): r for r in rows if r["line"] and r["length"]}
    before, now = cells(date(2022, 1, 1), date(2025, 12, 31)), cells(date(2026, 1, 1), date(2026, 10, 31))
    out = [{"line": k_[0], "length": k_[1], "value": round(econ(r) - econ(before[k_]), 1), "balls": r["balls"]}
           for k_, r in now.items() if k_ in before and k_[0] in LINES and k_[1] in LENGTHS and r["balls"] >= 12
           and before[k_]["balls"] >= 30]
    seas = {r["year"]: r for r in q(db, bowlers=[KULDEEP], group_by=["year"], metrics_perspective="bowling")}
    e26 = econ(seas[2026])
    c = card("dip", "pitch_map",
             f"Both ways: Kuldeep went at {e26:.1f} an over in 2026, his worst IPL season",
             {"hand": "RHB", "lines": LINES, "lengths": LENGTHS, "min_balls": 12,
              "metric": {"label": "Runs an over, 2026 v 2022-25", "format": "signed1", "higher_better": False, "mid": 0},
              "legend": ["Cheaper in 2026", "Dearer in 2026"], "cells": out},
             "Change in runs an over, to right-handers · 12+ balls a cell in 2026", kicker="Both ways")
    return c, {"e26": e26, "cells": len(out), "seas": seas}


def twins_card(db, player, role, sample, kicker):
    from services import twins

    t = twins.twins_for(db, player, unit="career", role=role, n=8)
    assert t.get("qualified")
    near = t["twins"]
    short = lambda n: n.split()[-1]  # noqa: E731
    me = player.split()[-1]
    c = card(f"twins-{role}", "distance_star",
             f"{me}'s closest statistical twins: {near[0]['player']} ({near[0]['gap_points']} points), "
             f"{short(near[1]['player'])} ({near[1]['gap_points']})",
             {"center": player, "center_label": me,
              "spokes": [{"name": x["player"], "distance": x["gap_points"], "label": short(x["player"]),
                          "highlight": i < 2} for i, x in enumerate(near)]},
             sample, kicker=kicker)
    return c, {"near": near}


def ansari_card(db):
    rows = []
    for p in (KULDEEP, ANSARI):
        r = q(db, bowlers=[p], group_by=["bowler"], metrics_perspective="bowling", start_date=date(2025, 1, 1),
              end_date=date(2025, 12, 31))[0]
        rows.append((p, r))
    ws = q(db, group_by=["bowl_kind"], bowl_style=["LB", "LBG", "LWS"], metrics_perspective="bowling",
           start_date=date(2025, 1, 1), end_date=date(2025, 12, 31))[0]
    (kp, k), (ap, a) = rows
    bars = [{"name": "Kuldeep Yadav", "value": round(econ(k), 2), "detail": f"{k['balls'] // 6} overs, {k['wickets']} wickets"},
            {"name": "Zeeshan Ansari", "value": round(econ(a), 2), "highlight": True,
             "detail": f"{a['balls'] // 6} overs, {a['wickets']} wickets"},
            {"name": "All wrist spinners", "value": round(econ(ws), 2), "detail": "IPL 2025"}]
    c = card("ansari", "metric_bars",
             f"Delhi's new wrist spinner, Zeeshan Ansari: {econ(a):.1f} an over in 2025. Kuldeep: {econ(k):.1f}",
             {"metric": {"label": "Runs an over, IPL 2025", "format": "dec2"}, "label_width": 160, "rows": bars},
             "IPL 2025 · Ansari came from Hyderabad in the Natarajan trade", kicker="Who replaces him")
    return c, {"a": econ(a), "k": econ(k), "ws": econ(ws), "a_overs": a["balls"] // 6}


def build(db):
    lead, sc = seasons_card(db)
    money, mn = money_card()
    _, pn = pant_card(db, sc)  # its numbers feed the copy; the innings card draws his seasons now
    inn, iv = innings_card(db)
    pg, pgv = pant_grounds_card(db)
    ptw, ptv = twins_card(db, PANT, "bat", "T20 batters since 2015 v strong sides · points apart, lower is closer",
                          "Who bats like him")
    grounds, gr = grounds_card(db)
    _, dp = dip_card(db)
    _, tv = twins_card(db, KULDEEP, "bowl", "", "")
    an, av = ansari_card(db)
    ds = delhi_slot(db)
    # Pant's half (the money, his innings, his old home, his twins), then Kuldeep's (his new home, his replacement).
    return {"lead": lead, "cards": [money, inn, pg, ptw, grounds, an], "sc": sc, "mn": mn, "pn": pn, "gr": gr,
            "dp": dp, "tv": tv, "av": av, "iv": iv, "pgv": pgv, "ptv": ptv, "ds": ds}


def copy(b):
    sc, mn, pn, gr, dp, tv, av, iv, pgv, ptv, ds = (b[k] for k in ("sc", "mn", "pn", "gr", "dp", "tv", "av", "iv", "pgv",
                                                                   "ptv", "ds"))
    n = len(sc["both"])
    hook = (f"Kuldeep Yadav added more IPL wins than Rishabh Pant in all {n} seasons they both played since 2022. "
            "Delhi just swapped one for the other.")
    h = pn["h2h"]
    kot, ek = pgv["kot"], pgv["ek"]
    caption = "\n\n".join([
        f"Delhi Capitals have traded Kuldeep Yadav to Lucknow Super Giants to bring Rishabh Pant home. By wins added "
        f"(how much each player moved his side's chance of winning), Kuldeep was ahead of Pant in all {n} IPL seasons "
        f"they both played since 2022: {sg(sc['tot_k'], 1)} wins across those seasons, against {sg(sc['tot_p'], 1)}.",
        f"The money: Lucknow paid ₹{mn['final']:.0f} crore for Pant at the 2025 auction, after {mn['bids']} bids and a "
        f"Delhi right-to-match at ₹{mn['rtm']:.2f} crore. Delhi had retained Kuldeep at ₹13.25 crore.",
        f"Pant at Lucknow: below par in {iv['below']} of {iv['luck']} innings, {abs(pn['l25']):.0f} and "
        f"{abs(pn['l26']):.0f} runs below par per 100 balls across the two seasons. The highs were still there: "
        f"{iv['both']}.",
        f"What he brings home: at the Kotla he's {kot['raa_per_100']:.0f} runs above par per 100 balls since 2016 "
        f"({kot['balls']} balls, strike rate {kot['strike_rate']:.0f}); at the Ekana, {abs(ek['raa_per_100']):.0f} below. "
        f"Delhi's No. 4 since he left has been their only top-six slot below par ({sg(ds['no4'])} per 100 balls); Pant "
        f"for Delhi in 2022 and 2024: {sg(ds['pant_dc'])}.",
        f"Who bats like him? His closest statistical twins are {ptv['near'][0]['player']} and {ptv['near'][1]['player']}.",
        f"Lucknow's ground suits Kuldeep: he's gone at {gr['kl']:.1f} an over at the Ekana ({gr['ko']} overs) and "
        f"{gr['kd']:.1f} at the Kotla. All spinners since 2024: {gr['sl']:.1f} at Lucknow, {gr['sd']:.1f} at Delhi."
        + (f" Against Kuldeep in T20s Pant has made {h['runs']} off {h['balls']} balls and been out {h['wickets']} times." if h else ""),
        f"Who replaces him? Kuldeep's closest twins are {tv['near'][0]['player']} and {tv['near'][1]['player']}. "
        f"Delhi's new wrist spinner is Zeeshan Ansari, from Sunrisers in the T Natarajan trade: {av['a']:.1f} an over "
        f"in IPL 2025 ({av['a_overs']} overs), against Kuldeep's {av['k']:.1f}.",
        f"Both ways: 2026 was Kuldeep's worst IPL season ({dp['e26']:.1f} an over), and wins added doesn't count Pant's "
        "keeping or captaincy.",
        "IPL to the end of the 2026 season; 2025 auction from Cricbuzz. Wins added and runs above par: T20 Primer method. "
        "Ball-by-ball data: Himanish Ganjoo & TechRadar, Cricsheet.",
        "Who won the trade?",
        "Free ball-by-ball cricket stats: link in bio.\n.\n#IPL2027 #RishabhPant #KuldeepYadav #DelhiCapitals #LSG",
    ])
    return hook, caption


def thread(b, link):
    sc, mn, gr, dp, av, iv, pgv, ptv, ds = (b[k] for k in ("sc", "mn", "gr", "dp", "av", "iv", "pgv", "ptv", "ds"))
    n = len(sc["both"])
    kot, ek = pgv["kot"], pgv["ek"]
    texts = [
        f"Kuldeep Yadav added more IPL wins than Rishabh Pant in all {n} seasons they both played since 2022. Delhi just "
        "traded one for the other. 🧵",
        f"The money: Lucknow paid ₹{mn['final']:.0f} crore for Pant in 2025, after {mn['bids']} bids and a Delhi "
        f"right-to-match at ₹{mn['rtm']:.2f} crore. Kuldeep was retained at ₹13.25 crore.",
        f"Pant at Lucknow: below par in {iv['below']} of {iv['luck']} innings. The highs were still there: "
        f"{iv['both']}.",
        f"What he brings home: {kot['raa_per_100']:.0f} runs above par per 100 balls at the Kotla, "
        f"{abs(ek['raa_per_100']):.0f} below at the Ekana. Delhi's No. 4 since he left: {sg(ds['no4'])}, their only "
        "top-six slot below par.",
        f"Who bats like Pant? {ptv['near'][0]['player']} and {ptv['near'][1]['player']}.",
        f"Lucknow's ground suits Kuldeep: {gr['kl']:.1f} an over at the Ekana, {gr['kd']:.1f} at the Kotla. Delhi's new "
        f"wrist spinner, Zeeshan Ansari: {av['a']:.1f} an over in IPL 2025.",
        f"Both ways: 2026 was Kuldeep's worst IPL season, {dp['e26']:.1f} an over. And wins added doesn't count Pant's "
        "keeping or captaincy.",
        f"Who won the trade?\n\nEvery ball, free: {link}\nData: @himganj153 & @TechRadar9",
    ]
    from services.ig_x import hand_thread

    return hand_thread(texts, copy(b)[1], THREAD_PLAYERS)


def reel_script(b):
    sc, mn, gr, av, iv, pgv = (b[k] for k in ("sc", "mn", "gr", "av", "iv", "pgv"))
    n = len(sc["both"])
    return {"hook": f"Kuldeep Yadav added more IPL wins than Rishabh Pant in all {n} seasons they both played. "
                    "Delhi just swapped them.",
            "lines": [f"Lucknow paid {mn['final']:.0f} crore for Pant after {mn['bids']} bids.",
                      f"He was below par in {iv['below']} of his {iv['luck']} innings there, but still made "
                      f"{iv['top']}.",
                      f"At the Kotla he's {pgv['kot']['raa_per_100']:.0f} runs above par per 100 balls.",
                      f"And Lucknow's ground suits Kuldeep: {gr['kl']:.1f} an over there, {gr['kd']:.1f} at Delhi.",
                      f"Delhi's new wrist spinner, Zeeshan Ansari, went at {av['a']:.1f} an over last season.",
                      ]}


def slides_of(b, hook):
    lead = b["lead"]
    cover = {"type": "hook", "text": hook, "cover": "hero",
             "hero": {"kind": "visual", "visual": lead["visual"], "payload": lead["payload"], "label": "", "card": lead}}
    return ([cover] + [{"type": "card", "card": c, "teams": ["Delhi Capitals", "Lucknow Super Giants"]} for c in b["cards"]]
            + [{"type": "end", "heading": "Who won the trade?",
                "body": "Every IPL ball since 2008, with wins added and runs above par: free on Hindsight."}])


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
    fact = {"kind": "spotlight", "title": hook, "hook": hook, "subject": PANT, "subject_role": "batter",
            "carousel_id": carousel["id"], "slides": n, "render": True, "post_time": "8 pm"}
    fact["x"] = thread(b, post_link(fact))
    fact["youtube"] = youtube_copy(fact, caption, hook)
    ist = timezone(timedelta(hours=5, minutes=30))
    today = datetime.now(ist).date()
    post = {"key": KEY, "pillar": "reactive", "fact": fact, "snapshot_id": carousel["id"], "warnings": [],
            "players": THREAD_PLAYERS, "caption": caption}
    with engine.begin() as conn:
        ig_backlog.upsert_pack(conn, post, today, source="hand", post_by=datetime.combine(today, time.max, tzinfo=ist))
    print(f"queued ig:{KEY} for {today} · carousel {carousel['id']} ({n} slides)")
    r = ig_slides.render(carousel["id"], n, args.base)
    print(f"rendered {len(r['ok'])}/{n}" + (f", failed {r['failed']}" if r["failed"] else "") + f"; layout {r.get('layout') or 'clean'}")
    # Reels are always voiced (the user's rule): the hand script replaces whatever the render stored.
    env = {**os.environ, "REEL_V2": "1", "REEL_AB": "0"}
    done = subprocess.run([sys.executable, str(ROOT / "scripts/make_reel_v2.py"), "--key", f"ig:{KEY}", "--beats", "2,3,4,6,7",
                           "--script", str(HERE / "reel.json"), "--close", "Who won the trade?", "--base", args.base,
                           "--store"], env=env, capture_output=True, text=True)
    ok = "stored as the post's Reel" in done.stdout
    print("voiced Reel:", "stored" if ok else f"FAILED\n{done.stdout[-1500:]}\n{done.stderr[-1500:]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
