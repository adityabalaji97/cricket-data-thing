"""
The Hardik Pandya - Arshdeep Singh trade, 12 Nov 2026: Mumbai Indians sent Hardik to Punjab Kings for Arshdeep (in
squad_moves, as the retention posts and Fix my team have it). A slow-news-day deep dive that shows the site: the two
profiles, The XI card's over-by-over strips, the grounds each now calls home, the winners' template before and after.
Every number is IPL 2025-26 from the query builder unless a slide says otherwise (the profiles: since Jan 2024, major
leagues and top-12 T20Is; Arshdeep at the Wankhede: IPL since 2019).

    python articles/hardik-arshdeep/post.py                                   # dry run
    python articles/hardik-arshdeep/post.py --write --base http://localhost:3000   # queue, render, Reel, thread
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

KEY = "spotlight-hardik-arshdeep-trade-2026-11-12"
SITE = "https://hindsightcricket.com"
HARDIK, ARSH, BUMRAH, BOULT, CHAHAR = "Hardik Pandya", "Arshdeep Singh", "Jasprit Bumrah", "Trent Boult", "Deepak Chahar"
THREAD_PLAYERS = [ARSH, HARDIK, BUMRAH]
IPL = {"fmt": "T20", "include_international": False, "leagues": ["IPL"], "start_date": date(2025, 1, 1),
       "end_date": date(2026, 10, 31)}
WANKHEDE = "Wankhede Stadium"
MULLANPUR = "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur"
DHARAMSALA = "Himachal Pradesh Cricket Association Stadium"
MI_COLOUR = "#005DA0"


def ordinal(n):
    return f"{n}{'th' if 10 < n % 100 < 14 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


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


# ---- numbers ----------------------------------------------------------------------------------------------------

def wins(db):
    """Wins added in IPL 2025-26, bat and ball, for both."""
    out = {}
    for p in (HARDIK, ARSH):
        b = q(db, batters=[p], group_by=["batter"], metrics_perspective="batting")
        w = q(db, bowlers=[p], group_by=["bowler"], metrics_perspective="bowling")
        out[p] = {"bat": b[0] if b else None, "bowl": w[0] if w else None,
                  "wpa": (b[0]["wpa"] if b else 0) + (w[0]["wpa"] if w else 0)}
    assert out[ARSH]["wpa"] > 1.5 and out[HARDIK]["wpa"] < -1, {p: out[p]["wpa"] for p in out}
    return out


def strips(db, player):
    """His share of each over's balls in his games: batting (faced) and bowling (bowled), overs 1-20."""
    bat = q(db, batters=[player], group_by=["match_id", "over"], metrics_perspective="batting")
    bowl = q(db, bowlers=[player], group_by=["match_id", "over"], metrics_perspective="bowling")
    n = len({r["match_id"] for r in bat} | {r["match_id"] for r in bowl})
    sb, sw = [0] * 20, [0] * 20
    for r in bat:
        sb[int(r["over"])] += r["balls"]
    for r in bowl:
        sw[int(r["over"])] += r["balls"]
    return {"games": n, "bat": [round(x / (6 * n), 3) for x in sb], "bowl": [round(x / (6 * n), 3) for x in sw]}


def death_share(db, team, player):
    rows = q(db, bowling_teams=[team], over_min=15, over_max=19, group_by=["bowler"], metrics_perspective="bowling")
    tot = sum(r["balls"] for r in rows)
    return sum(r["balls"] for r in rows if r["bowler"] == player) / tot


# ---- slides -----------------------------------------------------------------------------------------------------

def lead_card(db):
    h, a = strips(db, HARDIK), strips(db, ARSH)
    first = a["bowl"][0]
    assert first > 0.85, first
    peak = max(range(20), key=lambda i: h["bat"][i])
    assert 12 <= peak <= 16, peak
    c = card("strips", "over_strips",
             f"Arshdeep bowled the first over in {round(first * 100)}% of his IPL games. Hardik bats overs 13-16",
             {"rows": [{"name": "Hardik Pandya", "sub": f"to Punjab · {h['games']} games", "bat": h["bat"], "bowl": h["bowl"]},
                       {"name": "Arshdeep Singh", "sub": f"to Mumbai · {a['games']} games", "bowl": a["bowl"], "highlight": True}]},
             "IPL 2025-26 · his share of each over's balls in his games, faced and bowled")
    return c, {"h": h, "a": a, "first": first}


def profile_card(db, player, roles, kicker):
    from services.player_verdict import get_summary

    s = get_summary(db, player)
    rows, ranks = [], {}
    for role in roles:
        b = s["roles"][role]
        pool = b["peers"]["pool"]
        for m in b["peers"]["metrics"]:
            pct = round(100 * (pool - m["rank"]) / (pool - 1))
            rows.append({"label": m["label"], "group": "Batting" if role == "bat" else "Bowling", "value": pct})
            ranks[(role, m["key"])] = (m["rank"], pool, m["value"])
    return rows, ranks, s


def arsh_profile(db):
    rows, r, _ = profile_card(db, ARSH, ["bowl"], "")
    wr, pool, _ = r[("bowl", "wpa")]
    dr = r[("bowl", "dot_percentage")][0]
    assert wr <= 15, wr
    c = card("arsh", "percentile_strip",
             f"Arshdeep since 2024: {ordinal(wr)} of {pool} bowlers for wins added, {ordinal(dr)} for dot balls",
             {"rows": rows, "pool": f"{pool} bowlers"},
             "Percentile among bowlers · since 2024, major leagues and top-12 T20Is",
             kicker="His profile")
    return c, {"wr": wr, "pool": pool, "dr": dr, "er": r[("bowl", "economy")][0], "ev": r[("bowl", "economy")][2]}


def hardik_profile(db):
    rows, r, s = profile_card(db, HARDIK, ["bat", "bowl"], "")
    sr, bpool, srv = r[("bat", "strike_rate")]
    wr = r[("bat", "wpa")][0]
    assert sr <= 80 and wr >= 300, (sr, wr)
    c = card("hardik", "percentile_strip",
             f"Hardik since 2024: {ordinal(sr)} of {bpool} batters for strike rate, {ordinal(wr)} for wins added",
             {"rows": rows, "pool": f"{bpool} batters, 331 bowlers"},
             "Percentile · since Jan 2024, major leagues and T20Is between top-12 sides", kicker="His profile")
    return c, {"sr": sr, "srv": srv, "wr": wr, "bpool": bpool, "verdict": s.get("verdict") or ""}


def arsh_grounds(db):
    """Arshdeep by phase at the Wankhede (IPL since 2019) and at Mullanpur (2025-26), against all pace there (2025-26)."""
    me = {}
    for v, start in ((WANKHEDE, date(2019, 1, 1)), (MULLANPUR, date(2025, 1, 1))):
        rows = q(db, venue=v, bowlers=[ARSH], group_by=["phase"], metrics_perspective="bowling", start_date=start)
        me[v] = {r["phase"]: r for r in rows}
        me[v]["all"] = {"balls": sum(r["balls"] for r in rows), "runs": sum(r["runs"] for r in rows),
                        "wickets": sum(r["wickets"] for r in rows)}
    pace = {v: {r["phase"]: r for r in q(db, venue=v, bowl_kind=["pace bowler"], group_by=["phase"], metrics_perspective="bowling")}
            for v in (WANKHEDE, MULLANPUR)}
    w, m = econ(me[WANKHEDE]["all"]), econ(me[MULLANPUR]["all"])
    assert w < 8 < m, (w, m)
    rows = []
    for v, label in ((WANKHEDE, "Wankhede"), (MULLANPUR, "Mullanpur")):
        for ph, pl in (("powerplay", "1-6"), ("death", "16-20")):
            rows.append({"label": f"{label} {pl}", "a": round(econ(pace[v][ph]), 2), "b": round(econ(me[v][ph]), 2),
                         "highlight": v == WANKHEDE})
    c = card("arsh-grounds", "pair_dumbbell",
             f"Arshdeep at the Wankhede: {w:.1f} an over. At Mullanpur, his home since 2025: {m:.1f}",
             {"series": ["All pace there, IPL 2025-26", "Arshdeep"], "format": "dec2", "values": True, "full_labels": True,
              "no_diff": True, "rows": rows},
             "Runs an over · Arshdeep: Wankhede IPL since 2019, Mullanpur 2025-26",
             kicker="His new home")
    return c, {"w": w, "m": m, "ww": me[WANKHEDE]["all"]["wickets"], "wb": me[WANKHEDE]["all"]["balls"],
               "mw": me[MULLANPUR]["all"]["wickets"], "pp_m": econ(pace[MULLANPUR]["powerplay"]),
               "pp_w": econ(pace[WANKHEDE]["powerplay"]), "a_pp_w": econ(me[WANKHEDE]["powerplay"])}


def hardik_grounds(db):
    """The death overs at PBKS's two homes and the Wankhede (IPL 2025-26, all bowlers), against the league."""
    def death(v=None):
        kw = {"venue": v} if v else {}
        rows = q(db, over_min=15, over_max=19, group_by=["phase"], metrics_perspective="batting", **kw)
        return {"rr": 6 * sum(r["runs"] for r in rows) / sum(r["balls"] for r in rows), "balls": sum(r["balls"] for r in rows)}
    d, m, w, ipl = death(DHARAMSALA), death(MULLANPUR), death(WANKHEDE), death()
    assert d["rr"] > ipl["rr"] + 1.5, (d, ipl)
    rows = [{"name": "Dharamsala", "value": round(d["rr"], 2), "highlight": True, "detail": f"{d['balls']} balls · PBKS home"},
            {"name": "Wankhede", "value": round(w["rr"], 2), "detail": f"{w['balls']} balls · MI home"},
            {"name": "Mullanpur", "value": round(m["rr"], 2), "detail": f"{m['balls']} balls · PBKS home"},
            {"name": "All IPL grounds", "value": round(ipl["rr"], 2), "detail": f"{ipl['balls']:,} balls"}]
    hb = q(db, venue=DHARAMSALA, bowlers=[HARDIK], group_by=["bowler"], metrics_perspective="bowling", start_date=date(2019, 1, 1),
           leagues=[], include_international=True)
    c = card("hardik-grounds", "metric_bars",
             f"Hardik's new homes: the death has gone for {d['rr']:.1f} an over at Dharamsala. IPL: {ipl['rr']:.1f}",
             {"metric": {"label": "Runs an over, overs 16-20", "format": "dec2"}, "label_width": 150, "rows": rows},
             "IPL 2025-26, all bowlers · Dharamsala: about three games",
             kicker="His new homes")
    return c, {"d": d["rr"], "db": d["balls"], "m": m["rr"], "w": w["rr"], "ipl": ipl["rr"]}


def attack_card(db):
    a, b, bo, ch = strips(db, ARSH), strips(db, BUMRAH), strips(db, BOULT), strips(db, CHAHAR)
    sa, sb = death_share(db, "Punjab Kings", ARSH), death_share(db, "Mumbai Indians", BUMRAH)
    assert 0.2 < sa < 0.32 and 0.2 < sb < 0.32, (sa, sb)
    c = card("attack", "over_strips",
             f"Bumrah bowled {round(sb * 100)}% of MI's death balls, Arshdeep {round(sa * 100)}% of Punjab's",
             {"rows": [{"name": "Arshdeep Singh", "sub": "joins · Punjab 2025-26", "bowl": a["bowl"], "highlight": True},
                       {"name": "Jasprit Bumrah", "sub": "Mumbai", "bowl": b["bowl"]},
                       {"name": "Trent Boult", "sub": "Mumbai", "bowl": bo["bowl"]},
                       {"name": "Deepak Chahar", "sub": "Mumbai", "bowl": ch["bowl"]}]},
             "IPL 2025-26 · each bowler's share of each over's balls in his games", kicker="Mumbai's attack")
    return c, {"sa": sa, "sb": sb, "bo1": bo["bowl"][0], "ch1": ch["bowl"][0]}


def template(db):
    from services.xi_engine import score_link

    out = {}
    for code, add, drop, k in (("MI", [], [], "mi_now"), ("MI", [HARDIK], [ARSH], "mi_was"),
                               ("PBKS", [], [], "pk_now"), ("PBKS", [ARSH], [HARDIK], "pk_was")):
        s = score_link(db, code, add, drop, [])
        out[k] = {"at": s["at_level"], "of": s["of"], "roles": {r["label"]: r["status"] for r in s["roles"]}}
    return out


PK_COLOUR = "#DD1F2D"
UNIT = {"average": ("{:.1f}", "avg"), "strike_rate": ("{:.0f}", "SR"), "wickets_per_24": ("{:.2f}", "wkts/4 ov"),
        "economy": ("{:.2f}", "an over"), "regular_bowlers": ("{:.0f}", "bowlers")}


def template_card(db, t):
    """Punjab's squad against the winners' template now Hardik is in (squad_moves has the trade), as Fix my team scores
    it; the title carries the count with Arshdeep instead."""
    from services import xi_engine as x
    from services.squad_grade import ROLES, place

    d = x.payload(db, "PBKS")
    g = x.score(d["squad"], d["bench"])
    lower = {k: lw for k, _l, _s, _sl, _m, _n, lw, _f in ROLES}
    measure = {k: m for k, _l, _s, _sl, m, _n, _lw, _f in ROLES}
    rows = []
    for r in g["roles"]:
        b = d["bench"][r["key"]]
        f, u = UNIT[measure[r["key"]]]
        held = (f"{len(r['holders'])} with a season's worth of overs" if r["key"] == "depth"
                else ", ".join(h if h.split()[-1] == "Singh" else h.split()[-1] for h in r["holders"]) or "nobody yet")
        rows.append({"label": r["label"], "holders": held, "place": round(r["place"]),
                     "playoff_place": round(place(b["values"], b["playoff"], lower[r["key"]])), "status": r["status"],
                     "value_text": f"{f.format(r['value']) if r['value'] is not None else '–'} {u} · playoff {f.format(b['playoff'])}"})
    fin = next(r for r in g["roles"] if r["key"] == "finishers")
    assert fin["holders"][0] == HARDIK and fin["status"] != "playoff level", fin
    assert g["at_level"] == t["pk_now"]["at"] < t["pk_was"]["at"], (g["at_level"], t)
    c = card("template", "template_board",
             f"Punjab with Hardik: {g['at_level']} of 7 roles at playoff level. With Arshdeep: {t['pk_was']['at']}",
             {"colour": PK_COLOUR, "rows": rows, "scale_label": "Place among IPL sides, 2023-26"},
             "Fix my team's scoring · IPL 2024-26 at any side · v playoff sides 2023-26",
             kicker="Against the winners' template")
    return c, {"fin_sr": fin["value"], "fin_po": d["bench"]["finishers"]["playoff"]}


def case_card(w, ap, hp, t):
    ab, aw = w[ARSH]["bowl"], w[HARDIK]
    hb = w[HARDIK]["bat"]
    cases = [{"tag": "To Mumbai", "name": "Arshdeep Singh", "price": "₹18 crore",
              "for": f"{sg(w[ARSH]['wpa'], 2)} wins added in IPL 2025-26; {ordinal(ap['wr'])} of {ap['pool']} bowlers since 2024",
              "against": f"{econ(ab):.2f} an over in the IPL since 2025; {ordinal(ap['er'])} of {ap['pool']} for economy"},
             {"tag": "To Punjab", "name": "Hardik Pandya", "price": "₹16.35 crore",
              "for": f"strike rate {hb['strike_rate']:.0f} in the IPL since 2025; four overs as well",
              "against": f"{sg(hb['raa'], 0)} runs above par and {sg(hb['wpa'], 2)} wins with the bat since 2025"}]
    c = card("cases", "case_board", "The case for each side: a powerplay bowler, a finisher who bowls",
             {"colour": MI_COLOUR, "cases": cases},
             "IPL 2025-26 unless noted · prices: 2025 auction (Arshdeep) and retention (Hardik)", kicker="Both ways")
    return c


def build(db):
    w = wins(db)
    lead, lv = lead_card(db)
    ac, ap = arsh_profile(db)
    hc, hp = hardik_profile(db)
    ag, agv = arsh_grounds(db)
    hg, hgv = hardik_grounds(db)
    at, atv = attack_card(db)
    t = template(db)
    tc, tv = template_card(db, t)
    cs = case_card(w, ap, hp, t)
    return {"tv": tv, "lead": lead, "cards": [ac, hc, ag, hg, at, tc], "w": w, "lv": lv, "ap": ap, "hp": hp, "agv": agv, "hgv": hgv,
            "atv": atv, "t": t}


# ---- words ------------------------------------------------------------------------------------------------------

def copy(b):
    w, lv, ap, hp, agv, hgv, atv, t = (b[k] for k in ("w", "lv", "ap", "hp", "agv", "hgv", "atv", "t"))
    hw, aw = w[HARDIK]["wpa"], w[ARSH]["wpa"]
    hook = (f"Arshdeep Singh added {sg(aw, 1)} IPL wins since the 2025 auction. Hardik Pandya: {sg(hw, 1)}. "
            "Mumbai and Punjab just swapped them.")
    hb, hbw = w[HARDIK]["bat"], w[HARDIK]["bowl"]
    caption = "\n\n".join([
        f"Mumbai Indians have traded Hardik Pandya to Punjab Kings for Arshdeep Singh. By wins added (how much each player "
        f"moved his side's chance of winning), Arshdeep was worth {sg(aw, 2)} wins across IPL 2025 and 2026; Hardik "
        f"{sg(hw, 2)}, bat and ball together.",
        f"When they're in the game: Arshdeep bowled the first over in {round(lv['first'] * 100)}% of his IPL games and a "
        f"third of the 19th and 20th. Hardik bats overs 13 to 16 and bowls the middle.",
        f"Their profiles (since 2024, major leagues and top-12 T20Is): Arshdeep is {ordinal(ap['wr'])} of {ap['pool']} bowlers for "
        f"wins added and {ordinal(ap['dr'])} for dot balls, though {ordinal(ap['er'])} for economy. Hardik is {ordinal(hp['sr'])} of "
        f"{hp['bpool']} batters for strike rate and {ordinal(hp['wr'])} for wins added. His standout: false shots forced at the "
        "death, the best of 138 bowlers there.",
        f"Arshdeep's best ground is his new home: {agv['w']:.1f} an over and {agv['ww']} wickets in {agv['wb']} balls at the "
        f"Wankhede, against {agv['m']:.1f} at Mullanpur, where powerplay pace has gone for {agv['pp_m']:.1f} an over since "
        f"2025 (Wankhede: {agv['pp_w']:.1f}). That's the ground as much as the bowler.",
        f"Hardik's new homes: Punjab split their games between Mullanpur and Dharamsala, where the death overs have gone "
        f"for {hgv['d']:.1f} an over since 2025 against {hgv['ipl']:.1f} across the IPL (a small sample: about three games). "
        "Good for a finisher; harder for a death bowler.",
        f"Mumbai's attack: Bumrah bowled {round(atv['sb'] * 100)}% of their death balls, Arshdeep {round(atv['sa'] * 100)}% "
        f"of Punjab's. Their powerplay pace was Trent Boult and Deepak Chahar.",
        f"Against the winners' template (Fix my team): Mumbai have {t['mi_now']['at']} of 7 roles at playoff level either "
        f"way, with powerplay pace up from a gap to short. Punjab go from {t['pk_was']['at']} to {t['pk_now']['at']}: Hardik "
        f"becomes their busiest batter at 5-7, where the three of them strike at {b['tv']['fin_sr']:.0f} against "
        f"{b['tv']['fin_po']:.0f} for playoff sides.",
        "Both ways: wins added barely repeats season to season, and it doesn't count Hardik's captaincy or four overs of "
        "middle-overs control.",
        "IPL 2025-26 unless noted. Wins added and runs above par: T20 Primer method. Ball-by-ball data: Himanish Ganjoo & "
        "TechRadar, Cricsheet.",
        "Who won the trade?",
        "Free ball-by-ball cricket stats: link in bio.\n.\n#IPL2027 #HardikPandya #ArshdeepSingh #MumbaiIndians #PBKS",
    ])
    return hook, caption


def thread(b, link):
    w, lv, ap, hp, agv, hgv, atv, t = (b[k] for k in ("w", "lv", "ap", "hp", "agv", "hgv", "atv", "t"))
    texts = [
        f"Arshdeep Singh added {sg(w[ARSH]['wpa'], 1)} IPL wins since the 2025 auction. Hardik Pandya: "
        f"{sg(w[HARDIK]['wpa'], 1)}. Mumbai and Punjab just swapped them. 🧵",
        f"Arshdeep since 2024: {ordinal(ap['wr'])} of {ap['pool']} bowlers for wins added, {ordinal(ap['dr'])} for dot balls. The catch: "
        f"{ordinal(ap['er'])} for economy.",
        f"Hardik since 2024: {ordinal(hp['sr'])} of {hp['bpool']} batters for strike rate, {ordinal(hp['wr'])} for wins added. And the best "
        "of 138 bowlers at forcing false shots at the death.",
        f"Arshdeep's best ground is his new home: {agv['w']:.1f} an over at the Wankhede, {agv['m']:.1f} at Mullanpur, where "
        f"all powerplay pace has gone for {agv['pp_m']:.1f}.",
        f"Hardik's new homes: the death has gone for {hgv['d']:.1f} an over at Dharamsala since 2025 (about three games), "
        f"{hgv['ipl']:.1f} across the IPL. Good for a finisher.",
        f"Mumbai's attack: Bumrah bowled {round(atv['sb'] * 100)}% of their death balls; Arshdeep {round(atv['sa'] * 100)}% "
        "of Punjab's, and the first over in nine games of ten.",
        f"The case both ways. Arshdeep: {sg(w[ARSH]['wpa'], 2)} wins, but {econ(w[ARSH]['bowl']):.2f} an over. Hardik: "
        f"strike rate {w[HARDIK]['bat']['strike_rate']:.0f}, but {sg(w[HARDIK]['bat']['raa'], 0)} runs above par with the bat.",
        f"Who won the trade?\n\nEvery ball, free: {link}\nData: @himganj153 & @TechRadar9",
    ]
    from services.ig_x import hand_thread

    return hand_thread(texts, copy(b)[1], THREAD_PLAYERS)


def reel_script(b):
    w, lv, agv, hgv, atv = (b[k] for k in ("w", "lv", "agv", "hgv", "atv"))
    return {"hook": f"Arshdeep Singh added {abs(w[ARSH]['wpa']):.1f} IPL wins since the 2025 auction. Mumbai just traded "
                    "Hardik Pandya for him.",
            "lines": [f"He bowled the first over in {round(lv['first'] * 100)} percent of his games.",
                      f"Tenth of 331 bowlers for wins added since 2024.",
                      f"His best ground is his new home: {agv['w']:.1f} an over at the Wankhede.",
                      f"Hardik goes to Dharamsala, where the death has gone for {hgv['d']:.1f} an over.",
                      f"And Bumrah and Arshdeep each bowled a quarter of their side's death overs."]}


def slides_of(b, hook):
    lead = b["lead"]
    cover = {"type": "hook", "text": hook, "cover": "hero",
             "hero": {"kind": "visual", "visual": lead["visual"], "payload": lead["payload"], "label": "", "card": lead}}
    return ([cover] + [{"type": "card", "card": c, "teams": ["Mumbai Indians", "Punjab Kings"]} for c in b["cards"]]
            + [{"type": "end", "heading": "Who won the trade?",
                "body": (f"Arshdeep: {sg(b['w'][ARSH]['wpa'], 2)} wins, at {econ(b['w'][ARSH]['bowl']):.2f} an over. Hardik: strike "
                         f"rate {b['w'][HARDIK]['bat']['strike_rate']:.0f}, {sg(b['w'][HARDIK]['bat']['raa'], 0)} runs above par. "
                         "Both team pages, The XI and Fix my team: free on Hindsight.")}])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--base", default=SITE)
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
    fact = {"kind": "spotlight", "title": hook, "hook": hook, "subject": ARSH, "subject_role": "bowler",
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
    env = {**os.environ, "REEL_V2": "1", "REEL_AB": "0"}
    done = subprocess.run([sys.executable, str(ROOT / "scripts/make_reel_v2.py"), "--key", f"ig:{KEY}", "--beats", "1,2,4,5,6",
                           "--script", str(HERE / "reel.json"), "--close", "Who won the trade?", "--base", args.base,
                           "--store"], env=env, capture_output=True, text=True)
    ok = "stored as the post's Reel" in done.stdout
    print("voiced Reel:", "stored" if ok else f"FAILED\n{done.stdout[-1500:]}\n{done.stderr[-1500:]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
