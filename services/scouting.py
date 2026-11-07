"""
Scouting templates (7 Nov 2026): "how to bowl to X" for a batter, "how to bat against X" for a bowler, as post cards.

What we can say from our ball-by-ball (and what we can't): the bowler's TYPE (right-arm fast, left-arm orthodox...) but
not the delivery's variation (slower ball, googly, cutter) or its speed; line and length; the shot; where it went
(wagon zone); control. So the bowling-type card stands in for a variations chart, and every number is against the
player's own baseline or the average player in the same window.

Window: all men's T20s (leagues and internationals) from `start`, the tracked balls where a card needs tags.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

STYLE_FAMILIES = [
    ("Right-arm fast", ["RF"]), ("Right-arm fast-medium", ["RFM", "RMF"]), ("Right-arm medium", ["RM"]),
    ("Left-arm pace", ["LF", "LFM", "LMF", "LM"]), ("Off-spin", ["OB"]), ("Leg-spin", ["LB", "LBG"]),
    ("Left-arm orthodox", ["SLA"]), ("Left-arm wrist spin", ["LWS"]),
]
STYLE_WORDS = {"RF": "right-arm fast bowler", "RFM": "right-arm fast-medium bowler", "RMF": "right-arm medium-fast bowler",
               "RM": "right-arm medium pacer", "LF": "left-arm fast bowler", "LFM": "left-arm fast-medium bowler",
               "LMF": "left-arm medium-fast bowler", "LM": "left-arm medium pacer", "OB": "off-spinner", "LB": "leg-spinner",
               "LBG": "leg-spinner", "SLA": "left-arm orthodox spinner", "LWS": "left-arm wrist-spinner"}
# Short enough for a wheel's label.
STYLE_SHORT = {"OB": "off-spinner", "LB": "leg-spinner", "LBG": "leg-spinner", "SLA": "orthodox spinner", "LWS": "wrist-spinner"}
LINES = ["WIDE_OUTSIDE_OFFSTUMP", "OUTSIDE_OFFSTUMP", "ON_THE_STUMPS", "DOWN_LEG"]
LENGTHS = ["YORKER", "FULL", "GOOD_LENGTH", "SHORT_OF_A_GOOD_LENGTH", "SHORT"]
LINE_WORDS = {"WIDE_OUTSIDE_OFFSTUMP": "wide outside off", "OUTSIDE_OFFSTUMP": "outside off", "ON_THE_STUMPS": "on the stumps",
              "DOWN_LEG": "down leg"}
LENGTH_WORDS = {"YORKER": "yorkers", "FULL": "full", "GOOD_LENGTH": "good length", "SHORT_OF_A_GOOD_LENGTH": "back of a length",
                "SHORT": "short"}
ZONES_RHB = {1: "fine leg", 2: "square leg", 3: "midwicket", 4: "long on", 5: "long off", 6: "cover", 7: "point", 8: "third man"}
MIRROR = {1: 7, 2: 6, 3: 5, 4: 4, 5: 3, 6: 2, 7: 1, 8: 8}
FAMILY_WORDS = {"DRIVE": "Drives", "FLICK_GLANCE": "Flicks and glances", "PULL_HOOK": "Pulls and hooks", "WORK_PUSH": "Works and pushes",
                "CUT": "Cuts", "SLOG": "Slogs", "DEFENCE": "Defence", "SWEEP": "Sweeps", "RAMP_SCOOP": "Ramps and scoops",
                "REVERSE": "Reverse sweeps", "LEAVE": "Leaves"}
MIN_STYLE, MIN_CELL, MIN_FAMILY = 60, 20, 30


def zone_name(zone: int, hand: str) -> str:
    return ZONES_RHB[MIRROR[zone] if hand == "LHB" else zone]


def card(cid, visual, title, payload, sample, kicker=None):
    assert len(title) <= 80, (len(title), title)
    c = {"id": cid, "visual": visual, "title": title, "help": "", "sample": sample, "payload": payload}
    if kicker:
        c["kicker"] = kicker
    return c


def surname(name: str) -> str:
    w = name.split()
    common = {"Sharma", "Singh", "Khan", "Kumar", "Patel", "Yadav", "Ahmed", "Ahmad", "Iyer", "Pandya"}
    return w[0] if len(w) > 1 and w[-1] in common else w[-1]


class Scout:
    def __init__(self, db, start: date, end: Optional[date] = None):
        self.db, self.start, self.end = db, start, end or date.today()

    def q(self, **kw) -> List[Dict[str, Any]]:
        from services.query_builder_v2 import run_deliveries_query

        base = dict(fmt="T20", include_international=False, leagues=[], start_date=self.start, end_date=self.end, limit=5000)
        return run_deliveries_query(self.db, **{**base, **kw})["data"]

    def scope(self) -> str:
        return f"T20s since {self.start:%b %Y}"

    # ---- how to bowl to a batter ----------------------------------------------------------------------------------

    def bowl_to(self, batter: str) -> Dict[str, Any]:
        bat = dict(batters=[batter], metrics_perspective="batting")
        me = self.q(group_by=["batter"], **bat)[0]
        name, sn = me["batter"], surname(me["batter"])
        hand = max(self.q(group_by=["bat_hand"], **bat), key=lambda r: r["balls"])["bat_hand"]
        sr = me["strike_rate"]
        cards = []

        # 1. Bowling types: his strike rate against each, against his own.
        styles = {r["bowl_style"]: r for r in self.q(group_by=["bowl_style"], **bat)}
        rows = []
        for fam, codes in STYLE_FAMILIES:
            rs = [styles[c] for c in codes if c in styles]
            b = sum(r["balls"] for r in rs)
            if b < MIN_STYLE:
                continue
            runs, outs = sum(r["runs"] for r in rs), sum(r["wickets"] for r in rs)
            fsr = 100 * runs / b
            rows.append({"name": fam, "value": round(100 * (fsr / sr - 1), 1),
                         "detail": f"SR {fsr:.0f} · {b} balls · {outs} out" + ("" if outs == 1 else "s"), "sr": fsr, "balls": b})
        rows.sort(key=lambda r: r["value"])
        worst, best = rows[0], rows[-1]
        for r in rows:
            r["highlight"] = r is worst
        cards.append(card("types", "metric_bars",
                          f"{sn} v {worst['name'].lower()}: strike rate {worst['sr']:.0f}, against his {sr:.0f}",
                          {"metric": {"label": f"Strike rate against his {sr:.0f}, %", "format": "signed1", "signed": True},
                           "label_width": 150, "rows": [{k: v for k, v in r.items() if k not in ("sr", "balls")} for r in rows]},
                          f"{self.scope()} · {MIN_STYLE}+ balls a type · bowler's type, not the variation",
                          kicker="Who to bowl"))

        # 2. Pace by line and length: his strike rate in each cell against his strike rate against pace.
        pace = dict(bowl_kind=["pace bowler"], **bat)
        base = self.q(group_by=["batter"], **pace)[0]
        cells = [r for r in self.q(group_by=["line", "length"], **pace) if r.get("line") in LINES and r.get("length") in LENGTHS
                 and r["balls"] >= MIN_CELL]
        pm = [{"line": r["line"], "length": r["length"], "value": round(r["strike_rate"] - base["strike_rate"]), "balls": r["balls"]}
              for r in cells]
        tight = min([c for c in pm if c["balls"] >= 2 * MIN_CELL] or pm, key=lambda c: c["value"])  # the headline: 40+ balls
        # A length with one cell (often the short ball) costs a row of mostly blanks: drop it unless it's the headline.
        pm = [c for c in pm if sum(1 for x in pm if x["length"] == c["length"]) > 1 or c is tight]
        tight["highlight"] = True
        tcell = next(r for r in cells if r["line"] == tight["line"] and r["length"] == tight["length"])
        cards.append(card("pace-map", "pitch_map",
                          f"Pace, {LENGTH_WORDS[tight['length']]} {LINE_WORDS[tight['line']]}: SR {tcell['strike_rate']:.0f}, "
                          f"his {base['strike_rate']:.0f} v pace",
                          {"hand": hand, "lines": [l for l in LINES if any(c["line"] == l for c in pm)],
                           "lengths": [l for l in LENGTHS if any(c["length"] == l for c in pm)], "min_balls": MIN_CELL,
                           "metric": {"label": f"Strike rate against his {base['strike_rate']:.0f} v pace", "format": "signed0",
                                      "higher_better": True, "mid": 0},
                           "legend": ["He scores faster", "Slower"], "cells": pm},
                          f"{self.scope()} · pace · {MIN_CELL}+ balls a cell", kicker="Where to bowl"))

        # 3. Where his boundaries go off pace on a good length or back of one, against the average batter of his hand.
        gs = dict(bowl_kind=["pace bowler"], length=["GOOD_LENGTH", "SHORT_OF_A_GOOD_LENGTH"])

        def boundary_shares(rows_):
            got = {int(r["wagon_zone"]): 4 * (r.get("fours") or 0) + 6 * (r.get("sixes") or 0)
                   for r in rows_ if r.get("wagon_zone") is not None and 1 <= int(r["wagon_zone"]) <= 8}
            t = sum(got.values()) or 1
            return {z: round(100 * v / t) for z, v in got.items()}, sum(got.values())

        mine, total = boundary_shares(self.q(group_by=["wagon_zone"], **gs, **bat))
        avg, _ = boundary_shares(self.q(group_by=["wagon_zone"], bat_hand=hand, metrics_perspective="batting", **gs))
        key_zone = max(mine, key=mine.get)
        leg = [7, 6, 5] if hand == "LHB" else [1, 2, 3]
        cards.append(card("zones", "zone_pair",
                          f"Pace short of full: {sum(mine.get(z, 0) for z in leg)}% of his boundary runs square on the leg "
                          f"side ({sum(avg.get(z, 0) for z in leg)}% avg)",
                          {"hand": hand, "highlight": [key_zone],
                           "note": f"The fielder who matters: {zone_name(key_zone, hand)}, {mine[key_zone]}% of his boundary runs",
                           "pair": [{"label": sn, "zones": mine}, {"label": f"Average {'left' if hand == 'LHB' else 'right'}-hander", "zones": avg}]},
                          f"{self.scope()} · pace, good and back of a length · {total} boundary runs",
                          kicker="Where to field"))

        # 4. The shots he scores with, against the average batter of his hand.
        def family_shares(rows_):
            got = {r["shot_family"]: r["runs"] for r in rows_ if r.get("shot_family")}
            t = sum(got.values()) or 1
            return {k: 100 * v / t for k, v in got.items()}

        fm = family_shares(self.q(group_by=["shot_family"], **bat))
        fa = family_shares(self.q(group_by=["shot_family"], bat_hand=hand, metrics_perspective="batting"))
        top = sorted((k for k in fm if k not in ("LEAVE", "DEFENCE")), key=lambda k: -fm[k])[:6]   # his main scoring shots
        lead = max(top, key=lambda k: fm[k] - fa.get(k, 0))
        cards.append(card("shots", "pair_dumbbell",
                          f"{FAMILY_WORDS.get(lead, lead)}: {fm[lead]:.0f}% of his runs, against {fa.get(lead, 0):.0f}% for the "
                          f"average batter",
                          {"series": [f"Average {'left' if hand == 'LHB' else 'right'}-hander", sn], "format": "pct0", "values": True,
                           "full_labels": True, "no_diff": True,
                           "rows": [{"label": FAMILY_WORDS.get(k, k), "a": round(fa.get(k, 0), 1), "b": round(fm[k], 1), "highlight": k == lead}
                                    for k in top]},
                          f"{self.scope()} · share of runs off the bat, balls with a shot tagged", kicker="How he scores"))
        return {"name": name, "hand": hand, "cards": cards,
                "facts": {"sr": sr, "worst": worst, "best": best, "tight": tcell, "pace_sr": base["strike_rate"],
                          "key_zone": zone_name(key_zone, hand), "key_share": mine[key_zone], "lead_family": lead,
                          "lead_share": fm[lead], "lead_avg": fa.get(lead, 0)}}

    # ---- how to bat against a bowler ------------------------------------------------------------------------------

    def bat_against(self, bowler: str) -> Dict[str, Any]:
        bw = dict(bowlers=[bowler], metrics_perspective="bowling")
        me = self.q(group_by=["bowler"], **bw)[0]
        name, sn = me["bowler"], surname(me["bowler"])
        econ = 6 * me["runs"] / me["balls"]
        style = max(self.q(group_by=["bowl_style"], **bw), key=lambda r: r["balls"])["bowl_style"]
        cards = []

        # 1. Line and length: economy in each cell against his own.
        cells = [r for r in self.q(group_by=["line", "length"], **bw) if r.get("line") in LINES and r.get("length") in LENGTHS
                 and r["balls"] >= MIN_CELL]
        pm = [{"line": r["line"], "length": r["length"], "value": round(6 * r["runs"] / r["balls"] - econ, 1), "balls": r["balls"]}
              for r in cells]
        soft = max([c for c in pm if c["balls"] >= 2 * MIN_CELL] or pm, key=lambda c: c["value"])  # the headline: 40+ balls
        soft["highlight"] = True
        scell = next(r for r in cells if r["line"] == soft["line"] and r["length"] == soft["length"])
        cards.append(card("map", "pitch_map",
                          f"Where to attack {sn}: {LENGTH_WORDS[soft['length']]} {LINE_WORDS[soft['line']]}, "
                          f"{6 * scell['runs'] / scell['balls']:.1f} an over",
                          {"hand": "RHB", "lines": [l for l in LINES if any(c["line"] == l for c in pm)],
                           "lengths": [l for l in LENGTHS if any(c["length"] == l for c in pm)], "min_balls": MIN_CELL,
                           "metric": {"label": f"Runs an over against his {econ:.1f}", "format": "signed1", "higher_better": True, "mid": 0},
                           "legend": ["Batters score faster", "Slower"], "cells": pm},
                          f"{self.scope()} · {MIN_CELL}+ balls a cell", kicker="Where he's hittable"))

        # 2. The shots that work: batters' strike rate by shot family against him, against their strike rate off him.
        sr_all = 100 * me["runs"] / me["balls"]
        fams = [r for r in self.q(group_by=["shot_family"], **bw) if r.get("shot_family") and r["balls"] >= MIN_FAMILY
                and r["shot_family"] not in ("LEAVE", "DEFENCE")]
        rows = sorted(({"name": FAMILY_WORDS.get(r["shot_family"], r["shot_family"]),
                        "value": round(100 * r["runs"] / r["balls"] - sr_all), "detail": f"{r['balls']} balls · {r['wickets']} out"
                        + ("" if r["wickets"] == 1 else "s"), "fam": r} for r in fams), key=lambda x: -x["value"])
        for i, r in enumerate(rows):
            r["highlight"] = i == 0
        top = rows[0]["fam"]
        cards.append(card("shots", "metric_bars",
                          f"{FAMILY_WORDS.get(top['shot_family'], top['shot_family'])} off {sn}: strike rate "
                          f"{100 * top['runs'] / top['balls']:.0f}, but {top['balls'] / max(top['wickets'], 1):.0f} balls per wicket",
                          {"metric": {"label": f"Batters' strike rate against their {sr_all:.0f} off him", "format": "signed0", "signed": True},
                           "label_width": 150, "rows": [{k: v for k, v in r.items() if k != "fam"} for r in rows]},
                          f"{self.scope()} · {MIN_FAMILY}+ balls a shot", kicker="What works"))

        # 3. Right- and left-handers by phase.
        grid = {(r["bat_hand"], r["phase"]): r for r in self.q(group_by=["bat_hand", "phase"], **bw) if r.get("bat_hand") and r.get("phase")}
        hands = {h: self.q(group_by=["bowler"], bat_hand=h, **bw) for h in ("RHB", "LHB")}
        he = {h: 6 * rs[0]["runs"] / rs[0]["balls"] for h, rs in hands.items() if rs and rs[0]["balls"] >= 60}
        rows3 = []
        for h, label in (("RHB", "Right-handers"), ("LHB", "Left-handers")):
            cs = []
            for ph in ("powerplay", "middle", "death"):
                r = grid.get((h, ph))
                cs.append(None if not r or r["balls"] < MIN_CELL else
                          {"value": round(6 * r["runs"] / r["balls"], 2), "text": f"{6 * r['runs'] / r['balls']:.1f}",
                           "sub": f"{r['wickets']}w · {r['balls']}b"})
            rows3.append({"name": label, "sub": f"{he[h]:.1f} an over" if h in he else "", "cells": cs})
        cards.append(card("hands", "grid_heat",
                          (f"Right-handers {he['RHB']:.1f} an over off {sn}, left-handers {he['LHB']:.1f}" if len(he) == 2
                           else f"{sn} by phase and batter's hand"),
                          {"cols": ["Powerplay", "Middle", "Death"], "rows": rows3, "format": "dec1", "higher_better": True,
                           "mid": round(econ, 2), "legend": ["Batters score faster", "Slower"]},
                          f"{self.scope()} · runs an over · {MIN_CELL}+ balls a cell", kicker="Who and when"))

        # 4. Where right-handers score off him, against the average bowler of his type.
        def run_shares(rows_):
            got = {int(r["wagon_zone"]): r["runs"] for r in rows_ if r.get("wagon_zone") is not None and 1 <= int(r["wagon_zone"]) <= 8}
            t = sum(got.values()) or 1
            return {z: round(100 * v / t) for z, v in got.items()}, sum(got.values())

        mine, total = run_shares(self.q(group_by=["wagon_zone"], bat_hand="RHB", **bw))
        avg, _ = run_shares(self.q(group_by=["wagon_zone"], bat_hand="RHB", bowl_style=[style], metrics_perspective="bowling"))
        key = max(mine, key=lambda z: mine[z] - avg.get(z, 0))
        words = STYLE_WORDS.get(style, style)
        title4 = (f"Right-handers score {mine[key]}% of their runs off {sn} at {zone_name(key, 'RHB')}: "
                  f"{avg.get(key, 0)}% off the average {words}" if mine[key] - avg.get(key, 0) >= 4
                  else f"No zone stands out: right-handers hit {sn} like any {words}")
        cards.append(card("zones", "zone_pair", title4,
                          {"hand": "RHB", "highlight": [key] if mine[key] - avg.get(key, 0) >= 4 else [],
                           "pair": [{"label": sn, "zones": mine}, {"label": f"Average {STYLE_SHORT.get(style, 'pacer')}", "zones": avg}]},
                          f"{self.scope()} · right-handers · {total} runs off the bat", kicker="Where they score"))
        return {"name": name, "style": style, "cards": cards,
                "facts": {"econ": econ, "soft": scell, "shot": top, "hands": he, "zone": zone_name(key, "RHB"), "zone_share": mine[key],
                          "zone_avg": avg.get(key, 0)}}
