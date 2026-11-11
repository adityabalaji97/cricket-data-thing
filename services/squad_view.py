"""
The squad view (XI_BUILDER_PLAN.md X1): an IPL squad's numbers and cards since the 2025 mega auction, built once for
the retention posts (articles/ipl-retention/post.py) and the team page. Every number is IPL 2025-26 at any side, from
the query builder; squads and trades come from the database (services/ipl_squads.py: the 2026 auction plus the moves
since); prices are the 2026 squad's, or the salary a traded player moved on.

    build(db, code, reported=True)  ->  {team, colour, lead, cards, players, under, bargain, big, top, trade, grade, ...}
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SITE = "https://hindsightcricket.com"
START, END = date(2025, 1, 1), date(2026, 10, 31)
TEMPLATE_START = date(2024, 1, 1)   # the template slide reads each player's last three IPL seasons
IPL = {"fmt": "T20", "include_international": False, "leagues": ["IPL"], "start_date": START, "end_date": END, "limit": 1000}
PALETTE = json.loads((ROOT / "src/utils/teamPalette.json").read_text())["teams"]
MIN_BAT, MIN_BOWL, MIN_CELL = 60, 60, 18

TEAMS = {
    "CSK": {"name": "Chennai Super Kings", "short": "Chennai", "tag": "#CSK", "big": "MS Dhoni"},
    "MI": {"name": "Mumbai Indians", "short": "Mumbai", "tag": "#MumbaiIndians", "big": "Rohit Sharma"},
    "RCB": {"name": "Royal Challengers Bengaluru", "short": "Bengaluru", "tag": "#RCB", "big": "Virat Kohli"},
    "KKR": {"name": "Kolkata Knight Riders", "short": "Kolkata", "tag": "#KKR", "big": "Andre Russell"},
    # A player just traded in isn't a retention call, so a side's big name is one it already had (Pant, Kuldeep moved).
    "DC": {"name": "Delhi Capitals", "short": "Delhi", "tag": "#DelhiCapitals", "big": "Axar Patel",  # captain
           "note": "Delhi say they've made their last trade: Axar Patel and Ashutosh Sharma stay (India Today, 10 Nov)."},
    "LSG": {"name": "Lucknow Super Giants", "short": "Lucknow", "tag": "#LSG", "big": "Nicholas Pooran", "hook": "big"},
    "SRH": {"name": "Sunrisers Hyderabad", "short": "Hyderabad", "tag": "#SRH", "big": "Pat Cummins"},
    "RR": {"name": "Rajasthan Royals", "short": "Rajasthan", "tag": "#RR", "big": "Yashasvi Jaiswal"},
    "PBKS": {"name": "Punjab Kings", "short": "Punjab", "tag": "#PBKS", "big": "Shreyas Iyer", "lead_trade": True},
    "GT": {"name": "Gujarat Titans", "short": "Gujarat", "tag": "#GT", "big": "Shubman Gill"},
}
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


def build(db, code, reported=True):
    """The squad's numbers and the six cards. `reported`: count deals agreed in reports but not yet official."""
    from services.ipl_squads import deals as squad_deals, squad

    T = TEAMS[code]
    team = T["name"]
    colour = readable_colour(PALETTE[team])
    sq = squad(db, code, reported=reported)
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
        if bb < 10 and wb < 12:  # the cover's note says "barely played (under 10 balls)": RR's Pretorius faced 8
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
    deals = squad_deals(db, code, reported=reported)
    out_names = [n for d in deals for n in d["outs"]]
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
            d_in, d_out = d["ins"], d["outs"]
            when = f"{d['when'].day} {d['when']:%b}" if d["when"] else None
            trade["deals"].append({"other": d["other"], "ins": d_in, "outs": d_out, "when": when, "source": d["source"]})
            for n in d_in:
                p = by_name.get(n)
                if p:
                    trade["lines"].append(since(n, p["bat"], p["bowl"]) + f" ({crore(p['price'])})")
                    trade["brief"].append(since(called(n), p["bat"], p["bowl"], one=True))
            for n in d_out:
                trade["lines"].append(since(n, o_bat.get(n), o_bowl.get(n)))
                trade["brief"].append(since(called(n), o_bat.get(n), o_bowl.get(n), one=True))
            # A deal that is the team's story (TEAMS "lead_trade"): the hook leads with who went and who came.
            if T.get("lead_trade") and "lead" not in trade and d_in and d_out and by_name.get(d_in[0]):
                o = d_out[0]
                trade["lead"] = {"out": o, "out_wpa": ((o_bat.get(o) or {}).get("wpa") or 0) + ((o_bowl.get(o) or {}).get("wpa") or 0),
                                 "in": d_in[0], "in_wpa": by_name[d_in[0]]["wpa"]}

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
    if len(board_title) > 80:  # RR, 9 Nov 2026: "Sooryavanshi" is 2 too many
        board_title = f"{T['short']}'s squad by wins added since 2025: {called(top['name'])} leads ({sg(top['wpa'])})"
    lead = card("board", "squad_board", board_title,
                # Ink on the strongest chips: dark on a light colour (GT gold, CSK yellow), white on a deep one (MI blue).
                {"colour": colour, "ink": BG if contrast(colour, BG) >= contrast(colour, "#ffffff") else "#ffffff",
                 "format": "signed2", "groups": groups,
                 "note": " · ".join(x for x in [
                     f"Traded in: {', '.join(short(p['name']) for p in ins)}" if ins else "",
                     f"Barely played since 2025 (under 10 balls): {len(unplayed)} ({', '.join(short(p['name']) for p in unplayed[:3])}{'…' if len(unplayed) > 3 else ''})" if unplayed else "",
                 ] if x) or None},
                f"Wins added (T20 Primer), batting and bowling · IPL 2025-26, any side · {len(played)} of {len(players)} played")

    # 2. Who carried them.
    carried = sorted(played, key=lambda p: -p["wpa"])[:8]
    pair = f"{short(carried[0]['name'])} {sg(carried[0]['wpa'])}, {short(carried[1]['name'])} {sg(carried[1]['wpa'])}"
    # Two lines at most on the slide (RR, 9 Nov 2026: "V Sooryavanshi" ran it to three).
    carried_title = (f"Most wins added in this squad since 2025: {pair}" if len(pair) <= 30
                     else f"Most wins added since 2025: {pair}")
    c2 = card("carried", "metric_bars",
              carried_title,
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
    # The big price: the dearest who added none; at equal prices the one who added least (RR, Nov 2026: Jadeja and
    # Jurel both ₹14 crore; the list's order used to decide).
    under = max([p for p in pool if p["wpa"] < 0] or pool, key=lambda p: (p["price"], -p["wpa"]))
    # The bargain: the most wins added for ₹1 crore or less; when nobody that cheap added any (GT, Nov 2026: Kushagra at
    # −0.07), the best for ₹4 crore or less, so "the bargain" is never a player the numbers argue against.
    # A bargain also needs a real sample and a real number (LSG, 8 Nov 2026: Akash Singh's +0.32 came from 109 balls,
    # Digvesh Rathi's +0.02 from 546): 300+ balls and +0.10 wins, else the ₹4 crore fallback.
    rest = [p for p in pool if p is not under]
    real = [p for p in rest if (p["bat_balls"] or 0) + (p["bowl_balls"] or 0) >= 300] or rest
    bargain = max([p for p in real if p["price"] <= 1.0] or real, key=lambda p: p["wpa"])
    if bargain["wpa"] < 0.1:
        bargain = max([p for p in real if p["price"] <= 4.0] or real, key=lambda p: p["wpa"])
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


# ---- the team page (XI_BUILDER_PLAN.md X3) -------------------------------------------------------------------------

def code_for(team: str):
    """The IPL code for a team's full name (or its code), or None for a side without an IPL squad."""
    t = (team or "").strip()
    if t.upper() in TEAMS:
        return t.upper()
    return next((c for c, v in TEAMS.items() if v["name"].lower() == t.lower()), None)


def team_squad(db, team: str):
    """The team page's Squad group: the squad board, against the winners' template, price v wins added and the three
    calls, as the retention post draws them; with the trades and how sure each is. Cached per team and day, and again
    whenever a squad move is added (its id and time are in the key). None for a side without an IPL squad."""
    from sqlalchemy import text

    from services.query_cache import cached_run

    code = code_for(team)
    if not code:
        return None
    moves = db.execute(text("SELECT COALESCE(MAX(id), 0), MAX(created_at) FROM squad_moves WHERE league = 'ipl'")).fetchone()
    key = {"kind": "team_squad", "v": 2, "code": code, "day": date.today(), "moves": [moves[0], str(moves[1])]}

    def run():
        b = build(db, code)
        by_id = {c["id"]: c for c in b["cards"]}
        cards = [b["lead"]] + [by_id[k] for k in ("template", "value", "cases") if k in by_id]
        tr = b.get("trade") or {}
        from services.fit import fits  # who fills the gaps (XI_BUILDER_PLAN.md X4)
        return {"team": b["team"], "code": code, "colour": b["colour"], "as_of": date.today().isoformat(),
                "window": "IPL 2025-26 at any side (the template: 2024-26)", "cards": cards,
                "deals": tr.get("deals") or [], "gaps": [{"key": g["key"], "label": g["label"], "status": g["status"]}
                                                       for g in b.get("gaps") or []],
                "fits": fits(db, code, b.get("gaps") or [])}
    return cached_run(db, key, run)
