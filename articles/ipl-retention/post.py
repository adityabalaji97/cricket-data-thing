"""
IPL 2027 retention series (RETENTION_SERIES_PLAN.md): one franchise a day, one format. Every number is IPL 2025-26 (since
the 2025 mega auction), counting a player's record at any side, from the query builder; prices are the 2026 squad's
(data/auction_raw/ipl/2026, Cricbuzz), adjusted for this window's trades.

    python articles/ipl-retention/post.py --team CSK              # dry run
    python articles/ipl-retention/post.py --team CSK --write [--base http://localhost:3000]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

SITE = "https://hindsightcricket.com"
START, END = date(2025, 1, 1), date(2026, 10, 31)
TEMPLATE_START = date(2024, 1, 1)   # the template slide reads each player's last three IPL seasons
IPL = {"fmt": "T20", "include_international": False, "leagues": ["IPL"], "start_date": START, "end_date": END, "limit": 1000}
SQUADS = ROOT / "data/auction_raw/ipl/2026/completed_all_players.csv"
PALETTE = json.loads((ROOT / "src/utils/teamPalette.json").read_text())["teams"]
MIN_BAT, MIN_BOWL, MIN_CELL = 60, 60, 18

TEAMS = {
    "CSK": {"name": "Chennai Super Kings", "short": "Chennai", "tag": "#CSK", "big": "MS Dhoni"},
    "MI": {"name": "Mumbai Indians", "short": "Mumbai", "tag": "#MumbaiIndians", "big": "Rohit Sharma"},
    "RCB": {"name": "Royal Challengers Bengaluru", "short": "Bengaluru", "tag": "#RCB", "big": "Virat Kohli"},
    "KKR": {"name": "Kolkata Knight Riders", "short": "Kolkata", "tag": "#KKR", "big": "Andre Russell"},
    # A player just traded in isn't a retention call, so a side's big name is one it already had (Pant, Kuldeep moved).
    "DC": {"name": "Delhi Capitals", "short": "Delhi", "tag": "#DelhiCapitals", "big": "Axar Patel"},  # captain
    "LSG": {"name": "Lucknow Super Giants", "short": "Lucknow", "tag": "#LSG", "big": "Nicholas Pooran", "hook": "big"},
    "SRH": {"name": "Sunrisers Hyderabad", "short": "Hyderabad", "tag": "#SRH", "big": "Pat Cummins"},
    "RR": {"name": "Rajasthan Royals", "short": "Rajasthan", "tag": "#RR", "big": "Yashasvi Jaiswal"},
    "PBKS": {"name": "Punjab Kings", "short": "Punjab", "tag": "#PBKS", "big": "Shreyas Iyer"},
    "GT": {"name": "Gujarat Titans", "short": "Gujarat", "tag": "#GT", "big": "Shubman Gill"},
}
# This window's trades (Cricinfo / trade tracker, 5 Nov 2026; CSK's announcement, 5 Nov 2026): (player, from, to,
# salary in crore).
TRADES = [("Rishabh Pant", "LSG", "DC", 15.0), ("Kuldeep Yadav", "DC", "LSG", 13.5),
          ("T Natarajan", "DC", "SRH", 5.0), ("Zeeshan Ansari", "SRH", "DC", 0.4),
          ("Liam Livingstone", "SRH", "CSK", 6.0), ("Jack Edwards", "SRH", "CSK", 3.0),
          ("Khaleel Ahmed", "CSK", "SRH", 4.8), ("Nathan Ellis", "CSK", "SRH", 2.0)]


# The day's trade news, led with in the copy: (team, the date it was announced, source).
# The window's trades as news, deal by deal: who it involved, when it was announced and on whose word. A team's post
# leads with every deal it was part of.
DEALS = [
    {"sides": ("CSK", "SRH"), "when": "5 Nov", "source": "Chennai Super Kings' announcement",
     "players": ["Liam Livingstone", "Jack Edwards", "Khaleel Ahmed", "Nathan Ellis"]},
    {"sides": ("DC", "SRH"), "when": None, "source": "IPL trade tracker", "players": ["T Natarajan", "Zeeshan Ansari"]},
    {"sides": ("LSG", "DC"), "when": None, "source": "IPL trade tracker", "players": ["Rishabh Pant", "Kuldeep Yadav"]},
]


COMMON_SURNAMES = {"Ahmed", "Ahmad", "Khan", "Singh", "Sharma", "Kumar", "Yadav", "Patel", "Pandya", "Iyer"}


def called(name):
    """What a tweet calls him: the surname, or the first name where the surname is shared by many (Khaleel)."""
    w = name.split()
    return w[0] if len(w) > 1 and w[-1] in COMMON_SURNAMES else w[-1]


BG = "#0a0c11"  # the slides' background (theme bg)


def _lum(hex_):
    """WCAG relative luminance."""
    c = [int(hex_.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b=BG):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _lighten(hex_, target=3.0):
    """Mix towards white until it reads on the background."""
    r, g, b = (int(hex_.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    for k in range(0, 101, 2):
        mix = "#%02x%02x%02x" % tuple(round(x + (255 - x) * k / 100) for x in (r, g, b))
        if contrast(mix) >= target:
            return mix
    return "#ffffff"


def readable_colour(team_palette):
    """The team's colour for the dark slides, kept theirs (GT's navy disappeared on our background, 7 Nov 2026):
    the primary if it reads (3:1 against the background); a mid-tone primary lightened just enough (MI's, DC's blue);
    a very dark one swapped for the team's own second colour when that reads (GT and KKR gold, LSG orange)."""
    p, s2 = team_palette["primary"], team_palette.get("secondary")
    if contrast(p) >= 3:
        return p
    if contrast(p) >= 2 or not s2 or contrast(s2) < 3:
        return _lighten(p)
    return s2


def sg(v, d=2):
    return f"{v:+.{d}f}".replace("-", "−")


def crore(v):
    return f"₹{v:.2f} crore".replace(".00 crore", " crore") if v >= 1 else f"₹{round(v * 100)} lakh"


def card(cid, visual, title, payload, sample, kicker=None):
    assert len(title) <= 80, (len(title), title)
    c = {"id": cid, "visual": visual, "title": title, "help": "", "sample": sample, "payload": payload}
    if kicker:
        c["kicker"] = kicker
    return c


def price_cr(s):
    s = (s or "").strip()
    if s.endswith("Cr"):
        return float(s.replace("Cr", "").strip())
    if s.endswith("L"):
        return float(s.replace("L", "").strip()) / 100
    return 0.0


def resolve(db, name):
    """The name the ball-by-ball knows a squad player by. The auction file's spelling can be one the alias groups only
    reach in two hops ("Ravisrinivasan Sai Kishore" -> "R Sai Kishore" -> "Sai Kishore"), and a query on the first
    spelling finds no balls, which left GT's spinner off every slide."""
    if db is None:
        return name
    from sqlalchemy import text

    from services.player_aliases import expand_name_group

    names = set(expand_name_group([name], db))
    names |= set(expand_name_group(sorted(names), db))
    known = db.execute(text("SELECT display_name FROM player_identity WHERE display_name = ANY(:n)"), {"n": sorted(names)}).scalars().all()
    if name in known:
        return name
    # Two hops through initials can reach a different player ("Smaran Ravichandran" -> "S Ravichandran" ->
    # "Sabaorish Ravichandran"), so a match must be the same name spelt another way: every word of the shorter name
    # close to a word of the other (Mohammed/Mohammad Shami, Sai Kishore in Ravisrinivasan Sai Kishore).
    from difflib import SequenceMatcher

    def same(a, b):
        wa, wb = a.lower().split(), b.lower().split()
        short_, long_ = (wa, wb) if len(wa) <= len(wb) else (wb, wa)
        return all(max(SequenceMatcher(None, w, x).ratio() for x in long_) >= 0.75 for w in short_)

    fits = sorted(k for k in known if same(name, k))
    return fits[0] if len(fits) == 1 else name


def squad(code, db=None):
    rows = [r for r in csv.DictReader(open(SQUADS)) if r["auctionStatus"] != "unsold"]
    out = {}
    for r in rows:
        if r["playsForTeam"] != code:
            continue
        n = resolve(db, r["playerName"])
        out[n] = {"name": n, "role": r["role"], "price": price_cr(r["auctionPrice"]), "overseas": r["isPlayerOverseas"] == "True"}
    for name, frm, to, sal in TRADES:
        if frm == code:
            out.pop(resolve(db, name), None)
        if to == code:
            base = next((r for r in rows if r["playerName"] == name), {})
            name = resolve(db, name)
            out[name] = {"name": name, "role": base.get("role", ""), "price": sal, "overseas": base.get("isPlayerOverseas") == "True", "traded_in": frm}
    return out


def q(db, **kw):
    from services.query_builder_v2 import run_deliveries_query

    return run_deliveries_query(db, **{**IPL, **kw})["data"]


def numbers(db, names):
    bat = {r["batter"]: r for r in q(db, batters=names, group_by=["batter"], metrics_perspective="batting")}
    bowl = {r["bowler"]: r for r in q(db, bowlers=names, group_by=["bowler"], metrics_perspective="bowling")}
    pos = Counter()
    for r in q(db, batters=names, group_by=["batter", "batting_position"], metrics_perspective="batting"):
        pos[(r["batter"], int(r["batting_position"] or 0))] += r.get("innings_count") or 0
    kind = Counter()
    for r in q(db, bowlers=names, group_by=["bowler", "bowl_kind"], metrics_perspective="bowling"):
        kind[(r["bowler"], r["bowl_kind"])] += r["balls"]
    phase = {(r["bowler"], r["phase"]): r for r in q(db, bowlers=names, group_by=["bowler", "phase"], metrics_perspective="bowling")}
    return bat, bowl, pos, kind, phase


def build(db, code):
    T = TEAMS[code]
    team = T["name"]
    colour = readable_colour(PALETTE[team])
    sq = squad(code, db)
    names = list(sq)
    bat, bowl, pos, kind, phase = numbers(db, names)
    players = []
    for n, p in sq.items():
        b, w = bat.get(n), bowl.get(n)
        bb = (b or {}).get("balls") or 0
        wb = (w or {}).get("balls") or 0
        wpa = ((b or {}).get("wpa") or 0) + ((w or {}).get("wpa") or 0)
        spots = [(k[1], v) for k, v in pos.items() if k[0] == n and k[1] > 0]
        spot = max(spots, key=lambda kv: kv[1])[0] if spots else None
        kinds = {k[1]: v for k, v in kind.items() if k[0] == n}
        spin = kinds.get("spin bowler", 0) > kinds.get("pace bowler", 0)
        if bb < 10 and wb < 12:
            group = "Yet to play since 2025"
        elif bb >= MIN_BAT and wb >= MIN_BOWL:
            group = "All-rounders"
        elif wb >= max(bb, 12):
            group = "Spin" if spin else "Pace"
        else:
            group = "Openers" if spot and spot <= 2 else "Middle order" if spot and spot <= 5 else "Finishers"
        players.append({**p, "bat": b, "bowl": w, "bat_balls": bb, "bowl_balls": wb, "wpa": wpa, "group": group, "spot": spot,
                        "bat_raa": (b or {}).get("raa"), "bat_raa100": (b or {}).get("raa_per_100"),
                        "imp_inns": (b or {}).get("impact_per_innings"), "bowl_raa": (w or {}).get("raa"),
                        "wkts": (w or {}).get("wickets") or 0})
    played = [p for p in players if p["group"] != "Yet to play since 2025"]
    # An initial and the surname ("U Patel", "N Ahmad"): a surname alone is often two players.
    short = lambda n: n if len(n.split()) < 2 or n.split()[0].isupper() else f"{n.split()[0][0]} {n.split()[-1]}"  # noqa: E731

    # This window's trades, deal by deal: who came and went, with each one's IPL since 2025 (read like the squad's).
    ins = [p for p in players if p.get("traded_in")]
    deals = [d for d in DEALS if code in d["sides"]]
    moved = {n: (frm, to) for n, frm, to, _ in TRADES}
    out_names = [n for d in deals for n in d["players"] if moved.get(n, ("", ""))[0] == code]
    o_bat, o_bowl, *_ = numbers(db, out_names) if out_names else ({}, {})

    def since(name, b, w, one=False):
        """His IPL since 2025 in words; one=True keeps only the main thing he does (for a tweet)."""
        bb, wb = (b or {}).get("balls") or 0, (w or {}).get("balls") or 0
        bits = []
        if bb >= 30:
            bits.append((bb, f"{b['runs']} runs at a strike rate of {b['strike_rate']:.0f}"))
        if wb >= 30:
            bits.append((wb, f"{w['wickets']} wickets at {6 * w['runs'] / w['balls']:.2f} an over"))
        if not bits:
            games = max((b or {}).get("innings_count") or 0, (w or {}).get("innings_count") or 0)
            return (f"{name}: " + ("yet to play an IPL game" if not games else f"{games} IPL game{'s' if games > 1 else ''}")
                    + ("" if one else " since 2025"))
        if one:
            bits = [max(bits)]
        return f"{name}: " + " and ".join(t for _, t in bits)

    by_name = {p["name"]: p for p in ins}
    trade = None
    if deals:
        trade = {"deals": [], "lines": [], "brief": []}
        for d in deals:
            other = next(t for t in d["sides"] if t != code)
            d_in = [n for n in d["players"] if moved.get(n, ("", ""))[1] == code]
            d_out = [n for n in d["players"] if moved.get(n, ("", ""))[0] == code]
            trade["deals"].append({"other": other, "ins": d_in, "outs": d_out, "when": d["when"], "source": d["source"]})
            for n in d_in:
                p = by_name.get(n)
                if p:
                    trade["lines"].append(since(n, p["bat"], p["bowl"]) + f" ({crore(p['price'])})")
                    trade["brief"].append(since(called(n), p["bat"], p["bowl"], one=True))
            for n in d_out:
                trade["lines"].append(since(n, o_bat.get(n), o_bowl.get(n)))
                trade["brief"].append(since(called(n), o_bat.get(n), o_bowl.get(n), one=True))

    # 1. Cover: the squad board.
    order = ["Openers", "Middle order", "Finishers", "All-rounders", "Pace", "Spin"]
    groups = [{"label": g.replace("Middle order", "Middle"), "players": [{"name": short(p["name"]), "value": round(p["wpa"], 2)}
                                       for p in sorted([x for x in players if x["group"] == g], key=lambda x: -x["wpa"])]} for g in order]
    unplayed = [p for p in players if p["group"] == "Yet to play since 2025"]
    top = max(played, key=lambda p: p["wpa"])
    below = sum(1 for p in played if p["wpa"] <= 0)
    board_title = f"{T['short']}'s squad by wins added since the mega auction: {top['name']} leads ({sg(top['wpa'])})"
    if len(board_title) > 80:
        board_title = f"{T['short']}'s squad by wins added since the mega auction: {called(top['name'])} leads ({sg(top['wpa'])})"
    lead = card("board", "squad_board", board_title,
                # Ink on the strongest chips: dark on a light colour (GT gold, CSK yellow), white on a deep one (MI blue).
                {"colour": colour, "ink": BG if contrast(colour, BG) >= contrast(colour, "#ffffff") else "#ffffff",
                 "format": "signed2", "groups": groups,
                 "note": " · ".join(x for x in [
                     f"Traded in: {', '.join(short(p['name']) for p in ins)}" if ins else "",
                     f"Yet to play since 2025: {len(unplayed)} ({', '.join(short(p['name']) for p in unplayed[:3])}{'…' if len(unplayed) > 3 else ''})" if unplayed else "",
                 ] if x) or None},
                f"Wins added (T20 Primer), batting and bowling · IPL 2025-26, any side · {len(played)} of {len(players)} played")

    # 2. Who carried them.
    carried = sorted(played, key=lambda p: -p["wpa"])[:8]
    c2 = card("carried", "metric_bars",
              f"Most wins added in this squad since 2025: {short(carried[0]['name'])} {sg(carried[0]['wpa'])}, {short(carried[1]['name'])} {sg(carried[1]['wpa'])}",
              {"metric": {"label": "Wins added since the 2025 auction", "format": "signed2", "signed": True}, "label_width": 150,
               "rows": [{"name": p["name"], "value": round(p["wpa"], 2), "highlight": i == 0,
                         "detail": " · ".join(x for x in [f"bat RAA {sg(p['bat_raa'], 0)}" if p["bat_balls"] >= MIN_BAT else "",
                                                          f"{p['wkts']} wkts" if p["bowl_balls"] >= MIN_BOWL else ""] if x)}
                        for i, p in enumerate(carried)]},
              "Wins added: batting and bowling together · IPL 2025-26, at any side", kicker="Who carried them")

    # 3. Batting by role.
    batters = sorted([p for p in players if p["bat_balls"] >= MIN_BAT], key=lambda p: -p["bat_balls"])[:9]  # the nine busiest
    role_of = lambda p: "Opener" if p["spot"] and p["spot"] <= 2 else "Middle" if p["spot"] and p["spot"] <= 5 else "Finisher"  # noqa: E731
    rank = {"Opener": 0, "Middle": 1, "Finisher": 2}
    batters.sort(key=lambda p: (rank[role_of(p)], -(p["bat_raa100"] or 0)))
    best_b = max(batters, key=lambda p: p["bat_raa100"] or -99)
    worst_b = min(batters, key=lambda p: p["bat_raa100"] or 99)
    c3 = card("batting", "metric_bars",
              f"Batting: {short(best_b['name'])} {sg(best_b['bat_raa100'], 0)} runs above par per 100 balls, {short(worst_b['name'])} {sg(worst_b['bat_raa100'], 0)}",
              {"metric": {"label": "Runs above par per 100 balls", "format": "signed1", "signed": True}, "label_width": 160,
               "rows": [{"name": f"{role_of(p)} · {short(p['name'])}", "value": round(p["bat_raa100"] or 0, 1),
                         "highlight": p is best_b,
                         "detail": f"{p['bat_balls']} balls · Impact {sg(p['imp_inns'] or 0, 1)}/inns"} for p in batters]},
              f"IPL 2025-26, any side · {MIN_BAT}+ balls · role: his most common batting position", kicker="Batting by role")

    # 4. Bowling by phase: runs saved against par per 24 balls (four overs).
    bowlers = sorted(sorted([p for p in players if p["bowl_balls"] >= MIN_BOWL], key=lambda p: -p["bowl_balls"])[:6],
                     key=lambda p: -(p["bowl_raa"] or 0))  # the six busiest, best first
    rows4, cells_all = [], []
    for p in bowlers:
        cells = []
        for ph in ("powerplay", "middle", "death"):
            r = phase.get((p["name"], ph))
            if not r or r["balls"] < MIN_CELL:
                cells.append(None)
                continue
            v = 24 * (r.get("raa") or 0) / r["balls"]
            cells.append({"value": round(v, 1), "text": sg(v, 1), "sub": f"{r['wickets']}w · {r['balls']}b"})
            cells_all.append((p["name"], ph, v, r["balls"]))
        rows4.append({"name": short(p["name"]), "sub": f"{sg(p['bowl_raa'] or 0, 0)} runs saved", "cells": cells})
    best_c = max((c for c in cells_all if c[3] >= 48), key=lambda c: c[2], default=None)
    PH = {"powerplay": "powerplay", "middle": "middle overs", "death": "death"}
    c4 = card("bowling", "grid_heat",
              f"Bowling: {short(best_c[0])} saves {best_c[2]:.1f} runs every four overs in the {PH[best_c[1]]}" if best_c else "Bowling by phase",
              {"cols": ["Powerplay", "Middle", "Death"], "rows": rows4, "format": "signed1", "higher_better": True, "mid": 0,
               "legend": ["Saves runs against par", "Costs runs"]},
              f"Runs saved against par per 24 balls (T20 Primer) · IPL 2025-26 · {MIN_CELL}+ balls a cell", kicker="Bowling by phase")

    # 5. Value for money; and the three cases.
    big = next((p for p in played if p["name"] == T["big"]), max(played, key=lambda p: p["price"]))
    pool = [p for p in played if p is not big and not p.get("traded_in")]  # a player just traded in isn't a retention call
    under = max([p for p in pool if p["wpa"] < 0] or pool, key=lambda p: p["price"])
    # The bargain: the most wins added for ₹1 crore or less; when nobody that cheap added any (GT, Nov 2026: Kushagra at
    # −0.07), the best for ₹4 crore or less, so "the bargain" is never a player the numbers argue against.
    rest = [p for p in pool if p is not under]
    bargain = max([p for p in rest if p["price"] <= 1.0] or rest, key=lambda p: p["wpa"])
    if bargain["wpa"] <= 0:
        bargain = max([p for p in rest if p["price"] <= 4.0] or rest, key=lambda p: p["wpa"])
    trio = [big, under, bargain]
    c5 = card("value", "scatter_plus",
              f"{short(under['name'])} cost {crore(under['price'])} for {sg(under['wpa'])} wins. {short(bargain['name'])}: {crore(bargain['price'])}, {sg(bargain['wpa'])}",
              {"x": {"label": "2026 price, ₹ crore", "format": "dec1", "higher_better": False},
               "y": {"label": "Wins added since 2025", "format": "signed2", "higher_better": True},
               "points": [{"name": p["name"], "short": short(p["name"]), "x": round(p["price"], 2), "y": round(p["wpa"], 2),
                           "highlight": p in trio, "label": p in trio or p["price"] >= 8} for p in played]},
              "2026 squad prices (Cricbuzz) · wins added, IPL 2025-26", kicker="Value for money")

    # His IPL record before the window (2021-24): the case for a player the last two seasons don't make.
    before = {"start_date": date(2021, 1, 1), "end_date": date(2024, 12, 31)}
    names3 = [x["name"] for x in (big, under, bargain)]
    rec_bat = {r["batter"]: r for r in q(db, batters=names3, group_by=["batter"], metrics_perspective="batting", **before)}
    rec_bowl = {r["bowler"]: r for r in q(db, bowlers=names3, group_by=["bowler"], metrics_perspective="bowling", **before)}

    def record(p):
        r, w = rec_bat.get(p["name"]), rec_bowl.get(p["name"])
        if r and r["balls"] >= 120:
            par = f", {sg(r['raa_per_100'], 0)} v par per 100" if (r.get("raa_per_100") or 0) >= 1 else ""
            return f"IPL 2021-24: {r['runs']:,} runs at a strike rate of {r['strike_rate']:.0f}{par}"
        if w and w["balls"] >= 120:
            return f"IPL 2021-24: {w['wickets']} wickets at {6 * w['runs'] / w['balls']:.2f} an over"
        return None

    def case(tag, p):
        bits_for, bits_against = [], []
        if p["bat_balls"] >= MIN_BAT:
            (bits_for if (p["bat_raa"] or 0) > 0 else bits_against).append(f"{sg(p['bat_raa'], 0)} runs above par off {p['bat_balls']} balls")
        if p["bowl_balls"] >= MIN_BOWL:
            (bits_for if (p["bowl_raa"] or 0) > 0 else bits_against).append(f"{sg(p['bowl_raa'], 0)} runs saved, {p['wkts']} wickets")
        balls = (p["bat_balls"] or 0) + (p["bowl_balls"] or 0)
        small = f" off {balls} balls (a small sample)" if balls < 300 else ""
        (bits_for if p["wpa"] > 0 else bits_against).append(f"{sg(p['wpa'])} wins added{small}")
        if p["price"] >= 8:
            bits_against.append(f"costs {crore(p['price'])}")
        elif p["price"] <= 1:
            bits_for.append(f"costs {crore(p['price'])}")
        return {"tag": tag, "name": p["name"], "price": crore(p["price"]),
                "for": "; ".join(bits_for) or record(p) or "no number since 2025 makes it",
                "against": "; ".join(bits_against) or "little: the numbers back him"}
    cases = [case("The big name", big), case("The big price", under), case("The bargain", bargain)]
    c6 = card("cases", "case_board", f"Three calls for {T['short']}: {short(big['name'])}, {short(under['name'])} and {short(bargain['name'])}",
              {"colour": colour, "cases": cases}, "IPL 2025-26, any side · prices: 2026 squad", kicker="The case for and against")

    # 7. Against the winners' template (TEAM_TEMPLATE_PLAN.md): each role filled by the squad's busiest players in it,
    # on their IPL 2024-26 at any side, placed among IPL sides since 2023 against where playoff sides sit.
    from services.squad_grade import grade, load_template, squad_players

    tmpl = load_template("IPL")
    g = grade(squad_players(db, "IPL", names, TEMPLATE_START, END), tmpl["benchmarks"], tmpl["weights"])
    bill = sum(p["price"] for p in players)
    freed = under["price"] + (big["price"] if big["wpa"] <= 0 else 0)
    num = {"average": lambda v: f"{v:.1f}", "strike_rate": lambda v: f"{v:.0f}", "wickets_per_24": lambda v: f"{v:.2f}",
           "economy": lambda v: f"{v:.2f}", "regular_bowlers": lambda v: f"{v:.0f}"}
    unit = {"average": "avg", "strike_rate": "SR", "wickets_per_24": "wkts/4 ov", "economy": "an over", "regular_bowlers": "bowlers"}
    rows7 = []
    for r in g["roles"]:
        f = num[r["measure"]]
        held = (f"{len(r['holders'])} with a season's worth of overs since 2024" if r["key"] == "depth"
                else ", ".join(short(h) for h in r["holders"]) or "nobody in the squad has done it")
        rows7.append({"label": r["label"], "holders": held, "place": round(r["place"]), "playoff_place": round(r["playoff_place"]),
                      "status": r["status"],
                      "value_text": f"{f(r['value']) if r['value'] is not None else '–'} {unit[r['measure']]} · playoff {f(r['playoff_level'])}"})
    gaps = sorted([r for r in g["roles"] if r["status"] != "playoff level"], key=lambda r: (r["status"] != "gap", -r["weight"]))
    top_gap = gaps[0] if gaps else None
    c7 = card("template", "template_board",
              f"{g['at_level']} of {g['of']} roles at playoff-side level" + (f". The biggest gap: {SAY[top_gap['key']]}" if top_gap else ""),
              {"colour": colour, "rows": rows7, "scale_label": "Place among IPL sides, 2023-26"},
              "IPL 2024-26 at any side · recent seasons first · v playoff sides 2023-26",
              kicker="Against the winners' template")
    return {"team": team, "code": code, "colour": colour, "lead": lead, "cards": [c2, c3, c4, c5, c6, c7],
            "players": players, "trio": trio, "under": under, "bargain": bargain, "big": big, "top": top, "below": below,
            "bill": bill, "freed": freed, "played": played, "trade": trade, "grade": g, "gaps": gaps,
            "best_b": best_b, "worst_b": worst_b, "best_c": best_c}


# A role as copy says it.
SAY = {"openers": "openers", "top": "the 3-4s", "finishers": "the 5-7 finishers", "pp_pace": "powerplay pace",
       "mid_spin": "middle-overs spin", "death_pace": "death pace", "depth": "bowling depth"}


def gap_text(r):
    """A template gap in words: 'death pace (11.79 an over; playoff sides 9.85)'."""
    f = {"average": "{:.1f}", "strike_rate": "{:.0f}", "wickets_per_24": "{:.2f}", "economy": "{:.2f}", "regular_bowlers": "{:.0f}"}[r["measure"]]
    unit = {"average": "average", "strike_rate": "strike rate", "wickets_per_24": "wickets per 4 overs", "economy": "an over",
            "regular_bowlers": "regular bowlers"}[r["measure"]]
    v = "nobody in the role" if r["value"] is None else (f.format(r["value"]) + (f" {unit}" if unit == "an over" else f" {unit}"))
    return f"{SAY[r['key']]} ({v}; playoff sides {f.format(r['playoff_level'])})"


def copy(b):
    T = TEAMS[b["code"]]
    u, g, big = b["under"], b["bargain"], b["big"]
    # The hook's player: the big price, or the big name where the big price's number rests on a small sample
    # (TEAMS "hook": "big"; LSG, 8 Nov 2026: Mayank Yadav's −0.60 came from 144 balls).
    h = big if T.get("hook") == "big" else u
    hook = (f"{h['name']}: {crore(h['price'])}, {sg(h['wpa'])} wins since the mega auction. "
            f"{g['name']}: {crore(g['price'])}, {sg(g['wpa'])}.")
    PH = {"powerplay": "powerplay", "middle": "middle overs", "death": "death"}
    tr = b.get("trade")
    def deal_text(d):
        when = f", {d['when']}" if d["when"] else ""
        return (f"{T['short']} traded {' and '.join(d['outs'])} to {TEAMS[d['other']]['short']} for {' and '.join(d['ins'])} "
                f"({d['source']}{when})")
    news = (["News first: " + "; ".join(deal_text(d) for d in tr["deals"]) + ". In the IPL since 2025: "
             + "; ".join(tr["lines"]) + "."] if tr else [])
    caption = "\n\n".join(news + [
        f"{b['team']} have until 17 November to name who they keep for IPL 2027. Here's the case, player by player, from "
        f"every IPL ball since the 2025 mega auction.",
        f"Most wins added in this squad: {b['top']['name']}, {sg(b['top']['wpa'])}. {b['below']} of the {len(b['played'])} who "
        f"played added none or less.",
        f"The big price: {u['name']} ({crore(u['price'])}), {sg(u['wpa'])} wins. The bargain: {g['name']} ({crore(g['price'])}), "
        f"{sg(g['wpa'])}. The big name: {big['name']} ({crore(big['price'])}), {sg(big['wpa'])}.",
        f"Against the winners' template (what IPL playoff sides have had since 2023, role by role, on each player's IPL "
        f"2024-26 at any side): {b['grade']['at_level']} of {b['grade']['of']} roles at their level."
        + (f" Short of playoff level, biggest first: " + "; ".join(gap_text(r) for r in b["gaps"][:3]) + "." if b["gaps"] else "")
        + f" Squad cost: ₹{b['bill']:.1f} crore.",
        "Wins added, runs above par and Impact: T20 Primer method. IPL 2025-26, counting each player's record at any side. "
        "Prices: 2026 squad (Cricbuzz). Ball-by-ball data: Himanish Ganjoo & TechRadar, Cricsheet.",
        "Who would you keep?",
        f"Free ball-by-ball cricket stats: link in bio.\n.\n#IPL2027 #IPLRetention {T['tag']} #IPL",
    ])
    return hook, caption


def thread(b, link):
    """One tweet per carousel slide, in slide order, each written about its own image (the tweets reuse the
    Instagram slides: 1 cover, 2 wins added, 3 batting, 4 bowling, 5 value, 6 three calls, 7 template, 8 end)."""
    T = TEAMS[b["code"]]
    u, g, big, top = b["under"], b["bargain"], b["big"], b["top"]
    bb, wb, bc = b["best_b"], b["worst_b"], b["best_c"]
    h = big if T.get("hook") == "big" else u
    PH = {"powerplay": "powerplay", "middle": "middle overs", "death": "death"}
    wins = f"Most wins added in this squad since 2025: {top['name']}, {sg(top['wpa'])}. {b['below']} of {len(b['played'])} added none or less."
    tr = b.get("trade")
    if tr:
        full, head = trade_tweet(tr), trade_tweet(tr).split(" Since 2025:")[0]
        wins = next((f"{t}\n\n{wins}" for t in (full, head) if len(f"{t}\n\n{wins}") <= 230), wins)
    texts = [
        (1, f"{T['short']} have until 17 November to name who they keep for IPL 2027. {h['name']} cost {crore(h['price'])} "
            f"and added {sg(h['wpa'])} wins since the mega auction. The case, player by player 🧵"),
        (2, wins),
        (3, f"Batting by role, in runs above par per 100 balls: {bb['name']} the best at {sg(bb['bat_raa100'], 0)}, "
            f"{wb['name']} the furthest below at {sg(wb['bat_raa100'], 0)}."),
        (4, (f"Bowling by phase: {bc[0]} saves {bc[2]:.1f} runs every four overs {'at the death' if bc[1] == 'death' else 'in the ' + PH[bc[1]]}, "
             f"the most by anyone in any phase." if bc else "Bowling by phase: runs saved against par, every four overs.")),
        (5, f"Price against wins added. The bargain: {g['name']}, {sg(g['wpa'])} for {crore(g['price'])}. "
            f"The big price: {u['name']}, {sg(u['wpa'])} for {crore(u['price'])}."),
        (6, f"Three calls: {big['name']} ({crore(big['price'])}, {sg(big['wpa'])} wins), {u['name']} ({crore(u['price'])}, "
            f"{sg(u['wpa'])}) and {g['name']} ({crore(g['price'])}, {sg(g['wpa'])}). The case for and against each."),
        (7, f"Against what playoff sides have had since 2023: {b['grade']['at_level']} of {b['grade']['of']} roles at their level."
            + (f" Furthest short: {gap_text(b['gaps'][0])}." if b["gaps"] else "")),
        (8, f"Who would you keep?\n\nEvery ball, free: {link}\nData: @himganj153 & @TechRadar9"),
    ]
    from services.ig_x import hand_thread

    return hand_thread(texts, copy(b)[1], list(dict.fromkeys([u["name"], g["name"], big["name"], top["name"], bb["name"],
                                                              wb["name"]] + ([bc[0]] if bc else []))))


def trade_tweet(tr):
    """The window's trades in one tweet: who came in and went out, with a number each when it fits."""
    ins = [called(n) for d in tr["deals"] for n in d["ins"]]
    outs = [called(n) for d in tr["deals"] for n in d["outs"]]
    head = f"This window's trades: {', '.join(ins)} in; {', '.join(outs)} out."
    full = head + " Since 2025: " + "; ".join(tr["brief"]) + "."
    return full if len(full) <= 245 else head


def spoken(v):
    """Wins added, as the voice says it."""
    return f"added {abs(v):.2f} wins" if v > 0 else f"is down {abs(v):.2f} wins" if v < 0 else "added nothing"


def reel_script(b):
    """One line per beat (slides 1, 2, 5, 6, 7); the hook rides the first."""
    T = TEAMS[b["code"]]
    u, g, big = b["under"], b["bargain"], b["big"]
    say = lambda p: crore(p["price"]).replace("₹", "")  # noqa: E731
    h = big if T.get("hook") == "big" else u
    return {"hook": f"{h['name']} cost {T['short']} {say(h)}. Since the mega auction, he {spoken(h['wpa'])}.",
            "lines": ["Here's the whole squad, with this window's trades in, by wins added since 2025." if b.get("trade")
                      else "Here's the whole squad, by wins added since 2025.",
                      f"Most in the squad: {b['top']['name']}, who {spoken(b['top']['wpa'])}.",
                      (f"And he cost just {say(g)}." if g is b["top"] else f"{g['name']} cost {say(g)} and {spoken(g['wpa'])}."),
                      (f"{u['name']}, the big price, {spoken(u['wpa'])}, from a small sample." if h is big
                       else f"{big['name']}, the big name, {spoken(big['wpa'])}."),
                      (f"Against playoff sides, the biggest gap: {SAY[b['gaps'][0]['key']]}."
                       if b["gaps"] else "Against playoff sides, every role is at their level.")]}


def slides_of(b, hook):
    lead = b["lead"]
    cover = {"type": "hook", "text": hook, "cover": "hero",
             "hero": {"kind": "visual", "visual": lead["visual"], "payload": lead["payload"], "label": "", "card": lead}}
    return ([cover] + [{"type": "card", "card": c, "teams": [b["team"]]} for c in b["cards"]]
            + [{"type": "end", "heading": "Who would you keep?", "body": "Every IPL ball since 2008, with wins added and runs above par: free on Hindsight."}])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", required=True, choices=sorted(TEAMS))
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--base", default=SITE)
    ap.add_argument("--x-only", action="store_true", help="production: rewrite only the queued post's X thread (no render, no Reel)")
    ap.add_argument("--date", help="the day it posts (RETENTION_SERIES_PLAN.md schedule), YYYY-MM-DD; default today")
    args = ap.parse_args()
    if args.write or args.x_only:
        assert "localhost" not in os.environ.get("DATABASE_URL", ""), "--write is production: leave DATABASE_URL unset"
    from database import get_session
    from services.social_rules import findings, hook_problem, thread_problems

    db = next(get_session())
    b = build(db, args.team)
    hook, caption = copy(b)
    slides = slides_of(b, hook)
    print("HOOK:", hook, f"({len(hook)})")
    for n_, s in enumerate(slides, 1):
        c = s.get("card") or (s.get("hero") or {}).get("card") or {}
        print(f"  {n_}. [{c.get('visual') or s['type']}] {c.get('title') or s.get('heading')} ({len(c.get('title') or '')})")
    problems, hp = findings(slides, "spotlight"), hook_problem(hook)
    print("lint:", problems or "clean", "| hook:", hp or "ok")
    print(caption)
    th = thread(b, "hindsightcricket.com")
    for t in th:
        print(f"--- tweet {t['n']} ({len(t['text'])})\n{t['text']}")
    tp = thread_problems(th, [b["under"]["name"], b["bargain"]["name"], b["big"]["name"]])
    print("thread:", tp or "ok")
    out = HERE / args.team.lower()
    out.mkdir(exist_ok=True)
    (out / "reel.json").write_text(json.dumps(reel_script(b), indent=1))
    (out / "slides.json").write_text(json.dumps({"slides": slides, "hook": hook, "caption": caption, "x": th}, default=str, indent=1))
    print("REEL:", json.dumps(reel_script(b)))
    if args.x_only and not tp:
        from sqlalchemy import text

        from database import engine
        from services.ig_links import post_link

        key = f"ig:retention-{args.team.lower()}-2027"
        with engine.begin() as conn:
            fact = conn.execute(text("SELECT facts FROM content_packs WHERE angle_key = :k"), {"k": key}).scalar()
            assert fact, f"{key} isn't queued"
            x = thread(b, post_link(fact))
            conn.execute(text("UPDATE content_packs SET facts = jsonb_set(facts, '{x}', CAST(:x AS jsonb)) WHERE angle_key = :k"),
                         {"x": json.dumps(x), "k": key})
        print(f"rewrote the X thread of {key}: {len(x)} tweets, slides {[t['slide'] for t in x]}")
        return 0
    if problems or hp or tp or not args.write:
        return 1 if (problems or hp or tp) else 0

    from database import engine
    from services import ig_backlog, ig_carousel, ig_slides
    from services.ig_links import post_link
    from services.ig_notes import youtube_copy

    key = f"retention-{args.team.lower()}-2027"
    carousel = ig_carousel.save(db, slides, hook, {"spotlight": key}, "ig-spotlight")
    n = len(slides)
    fact = {"kind": "spotlight", "title": hook, "hook": hook, "subject": b["under"]["name"], "subject_role": "batter",
            "carousel_id": carousel["id"], "slides": n, "render": True, "post_time": "8 pm"}
    fact["x"] = thread(b, post_link(fact))
    fact["youtube"] = youtube_copy(fact, caption, hook)
    ist = timezone(timedelta(hours=5, minutes=30))
    today = date.fromisoformat(args.date) if args.date else datetime.now(ist).date()
    post = {"key": key, "pillar": "reactive", "fact": fact, "snapshot_id": carousel["id"], "warnings": [],
            "players": [b["under"]["name"], b["bargain"]["name"], b["big"]["name"]], "caption": caption}
    with engine.begin() as conn:
        ig_backlog.upsert_pack(conn, post, today, source="hand", post_by=datetime.combine(today, time.max, tzinfo=ist))
    print(f"queued ig:{key} for {today} · carousel {carousel['id']} ({n} slides)")
    r = ig_slides.render(carousel["id"], n, args.base)
    print(f"rendered {len(r['ok'])}/{n}" + (f", failed {r['failed']}" if r["failed"] else "") + f"; layout {r.get('layout') or 'clean'}")
    env = {**os.environ, "REEL_V2": "1", "REEL_AB": "0"}
    done = subprocess.run([sys.executable, str(ROOT / "scripts/make_reel_v2.py"), "--key", f"ig:{key}", "--beats", "1,2,5,6,7",
                           "--script", str(out / "reel.json"), "--close", "Who would you keep?", "--base", args.base, "--store"],
                          env=env, capture_output=True, text=True)
    ok = "stored as the post's Reel" in done.stdout
    print("voiced Reel:", "stored" if ok else f"FAILED\n{done.stdout[-1500:]}\n{done.stderr[-1500:]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
