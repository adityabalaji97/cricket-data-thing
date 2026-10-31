"""
Glenn Phillips, 31 Oct 2026: 82*, 70, 17 and 107 in the first four T20Is against India (all of New Zealand's innings
in the series are in the feed). His best four-innings stretch by runs, runs above par and wins added; what changed
(phases, lengths, control v dots, shots, scoring areas) against his T20Is before the series; and how to get him out
in the fifth game (spin on a good length, which India barely bowled him).

    python articles/glenn-phillips/post.py              # dry run
    python articles/glenn-phillips/post.py --write      # queue, render, voiced Reel (reel.json from the same numbers), thread
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from sqlalchemy import text  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

KEY = "spotlight-glenn-phillips-2026-10-31"
SITE = "https://hindsightcricket.com"
GP = "Glenn Phillips"
SERIES_START = date(2026, 10, 22)
T20I = {"fmt": "T20", "include_international": True}  # internationals only (no leagues named)
ALL_T20 = {"fmt": "T20", "include_international": False}  # every T20, leagues and T20Is
BEFORE = {**T20I, "end_date": SERIES_START - timedelta(days=1)}
SERIES = {**T20I, "start_date": SERIES_START}
SINCE_2024 = {**ALL_T20, "start_date": date(2024, 1, 1)}
TEAM_SHORT = {"India": "IND", "Australia": "AUS", "England": "ENG", "South Africa": "RSA", "New Zealand": "NZ",
              "Pakistan": "PAK", "Sri Lanka": "SL", "West Indies": "WI", "Afghanistan": "AFG", "Bangladesh": "BAN",
              "Canada": "CAN", "Scotland": "SCO", "Ireland": "IRE", "Netherlands": "NED", "Zimbabwe": "ZIM"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
LENGTH_NAMES = {"FULL": "Full", "GOOD_LENGTH": "Good length", "SHORT_OF_A_GOOD_LENGTH": "Back of length"}
LINES = ["WIDE_OUTSIDE_OFFSTUMP", "OUTSIDE_OFFSTUMP", "ON_THE_STUMPS", "DOWN_LEG"]
LENGTHS = ["FULL", "GOOD_LENGTH", "SHORT_OF_A_GOOD_LENGTH"]  # spinners rarely bowl him short
FAMILIES = [("DRIVE", "Drives"), ("PULL_HOOK", "Pulls"), ("CUT", "Cuts"), ("FLICK_GLANCE", "Flicks"),
            ("WORK_PUSH", "Pushes"), ("SLOG", "Slogs"), ("DEFENCE", "Defence")]
LONG_OFF = 5  # wagon zone, right-hander

THREAD_PLAYERS = [GP, "Axar Patel"]  # each one's first mention in the thread becomes a hashtag


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
    kw.setdefault("metrics_perspective", "batting")
    return run_deliveries_query(db, batters=[GP], **kw)["data"]


def one(db, **kw):
    rows = q(db, group_by=["batter"], **kw)
    return rows[0] if rows else None


def when(d):
    d = d if isinstance(d, date) else date.fromisoformat(str(d)[:10])
    return f"{MONTHS[d.month - 1]} {d.year}"


def innings(db, scope):
    """One row per innings in `scope`, oldest first, with its date and opponent."""
    from sqlalchemy import text

    rows = q(db, group_by=["match_id"], **scope)
    ids = [str(r["match_id"]) for r in rows]
    meta = {str(m["id"]): m for m in db.execute(text(
        "SELECT id, date, team1, team2 FROM matches WHERE id = ANY(:ids)"), {"ids": ids}).mappings()}
    out = []
    for r in rows:
        m = meta[str(r["match_id"])]
        out.append({**r, "date": m["date"], "opp": m["team2"] if m["team1"] == "New Zealand" else m["team1"]})
    return sorted(out, key=lambda r: r["date"])


def best_stretches(inns, key, n=4):
    """Every run of n straight innings, best first by `key`, overlapping runs dropped (the best of each overlap kept)."""
    runs = [{"end": i, key: sum(x[key] or 0 for x in inns[i - n + 1:i + 1]), "first": inns[i - n + 1], "last": inns[i],
             "runs": sum(x["runs"] for x in inns[i - n + 1:i + 1]), "balls": sum(x["balls"] for x in inns[i - n + 1:i + 1]),
             "wpa": sum(x["wpa"] or 0 for x in inns[i - n + 1:i + 1])} for i in range(n - 1, len(inns))]
    picked = []
    for r in sorted(runs, key=lambda r: -r[key]):
        if all(abs(r["end"] - p["end"]) >= n for p in picked):
            picked.append(r)
    return picked


# ---- slides -----------------------------------------------------------------------------------------------------

def stretch_card(db):
    t20i = innings(db, T20I)
    best = best_stretches(t20i, "raa")
    allt = innings(db, ALL_T20)
    by_runs = best_stretches(allt, "runs")
    lead, second = best[0], best[1]
    assert lead["last"]["date"] >= SERIES_START, "the series isn't his best stretch any more"
    assert by_runs[0]["last"]["date"] >= SERIES_START
    wpa_best = best_stretches(t20i, "wpa")
    assert wpa_best[0]["last"]["date"] >= SERIES_START

    def label(r):
        a, b = r["first"]["date"], r["last"]["date"]
        opps = {TEAM_SHORT.get(x["opp"], x["opp"][:3].upper()) for x in t20i[r["end"] - 3:r["end"] + 1]}
        span = when(b) if (a.year, a.month) == (b.year, b.month) else f"{MONTHS[a.month - 1]}-{when(b)}"
        return f"v {opps.pop()}, {span}" if len(opps) == 1 else span

    gap = lead["raa"] - second["raa"]
    c = card("stretch", "metric_bars",
             f"Glenn Phillips: {sg(lead['raa'], 0)} runs above par in 4 innings, his best T20I run by {gap:.0f}",
             {"metric": {"label": "Runs above par, 4 straight T20I innings", "format": "signed0"}, "label_width": 150,
              "rows": [{"name": label(r), "value": round(r["raa"], 1), "highlight": r is lead,
                        "detail": f"{r['runs']} runs off {r['balls']} balls"} for r in best[:5]]},
             "Runs above par: his runs against par for the match situation (T20 Primer) · T20Is")
    return c, {"lead": lead, "second": second, "gap": gap, "runs_best": by_runs[0], "runs_second": by_runs[1],
               "n_all": len(allt), "wpa_lead": wpa_best[0]["wpa"], "wpa_second": wpa_best[1]["wpa"], "t20i": t20i}


def hundred_card(db, t20i):
    top = sorted(t20i, key=lambda r: -(r["raa"] or 0))[:5]
    assert top[0]["date"] >= SERIES_START
    c = card("best", "metric_bars",
             f"The {top[0]['runs']} in Auckland: {sg(top[0]['raa'], 0)} runs above par, his best T20I innings",
             {"metric": {"label": "Runs above par, one innings", "format": "signed0"}, "label_width": 150,
              "rows": [{"name": f"{r['runs']} v {TEAM_SHORT.get(r['opp'], r['opp'][:3].upper())}", "value": round(r["raa"], 1),
                        "highlight": r is top[0], "detail": f"{r['balls']} balls · {when(r['date'])}"} for r in top]},
             "His 5 best T20I innings by runs above par", kicker="The hundred")
    return c, {"top": top}


def phase_card(db):
    def by(scope, col):
        return {r[col]: r for r in q(db, group_by=[col], **scope)}
    b, s = by(BEFORE, "phase"), by(SERIES, "phase")
    kb, ks = by(BEFORE, "bowl_kind"), by(SERIES, "bowl_kind")
    names = (("powerplay", "Powerplay"), ("middle", "Middle overs"), ("death", "Death"))
    rows = [{"label": f"{n} ({s[k]['balls']})", "a": round(b[k]["strike_rate"]), "b": round(s[k]["strike_rate"]),
             "highlight": True} for k, n in names]
    rows += [{"label": f"{n} ({ks[k]['balls']})", "a": round(kb[k]["strike_rate"]), "b": round(ks[k]["strike_rate"]),
              "highlight": True} for k, n in (("pace bowler", "v pace"), ("spin bowler", "v spin"))]
    assert all(r["b"] > r["a"] for r in rows), "not faster everywhere: the title no longer holds"
    c = card("phase", "pair_dumbbell",
             f"Faster in every phase and v pace and spin. Powerplay: {s['powerplay']['strike_rate']:.0f}, "
             f"from {b['powerplay']['strike_rate']:.0f}",
             {"series": ["T20Is before", "v India, Oct 2026"], "format": "int", "values": True, "full_labels": True,
              "no_diff": True, "rows": rows},
             "Strike rate (runs per 100 balls) · series balls in brackets", kicker="Everywhere")
    return c, {"b": b, "s": s, "kb": kb, "ks": ks}


def length_card(db):
    def by(scope):
        return {r["length"]: r for r in q(db, group_by=["length"], **scope) if r["length"]}
    b, s = by(BEFORE), by(SERIES)
    rows = [{"label": f"{n} ({s[k]['balls']})", "a": round(b[k]["strike_rate"]), "b": round(s[k]["strike_rate"]),
             "highlight": k == "GOOD_LENGTH"} for k, n in LENGTH_NAMES.items()]
    gl_b, gl_s = b["GOOD_LENGTH"], s["GOOD_LENGTH"]
    slowest = min(LENGTH_NAMES, key=lambda k: b[k]["strike_rate"])
    assert slowest == "GOOD_LENGTH"
    pace_b = one(db, length=["GOOD_LENGTH"], bowl_kind=["pace bowler"], **BEFORE)
    pace_s = one(db, length=["GOOD_LENGTH"], bowl_kind=["pace bowler"], **SERIES)
    c = card("length", "pair_dumbbell",
             f"Good length was his slowest ball in T20Is ({gl_b['strike_rate']:.0f}). This series: {gl_s['strike_rate']:.0f}",
             {"series": ["T20Is before", "v India, Oct 2026"], "format": "int", "values": True, "full_labels": True,
              "no_diff": True, "rows": rows},
             f"Strike rate by length · series balls in brackets · {gl_s['sixes']} sixes off good-length balls",
             kicker="The change")
    return c, {"gl_b": gl_b, "gl_s": gl_s, "pace_b": pace_b, "pace_s": pace_s}


def control_card(db):
    b, s = one(db, **BEFORE), one(db, **SERIES)
    rows = [{"label": "In control", "a": round(b["control_percentage"], 1), "b": round(s["control_percentage"], 1)},
            {"label": "Dots", "a": round(b["dot_percentage"], 1), "b": round(s["dot_percentage"], 1), "highlight": True},
            {"label": "Boundaries", "a": round(b["boundary_percentage"], 1), "b": round(s["boundary_percentage"], 1),
             "highlight": True}]
    assert abs(b["control_percentage"] - s["control_percentage"]) < 3, "control moved: the card's claim no longer holds"
    c = card("control", "pair_dumbbell",
             f"Same control as ever ({s['control_percentage']:.0f}%), but dots fell to {s['dot_percentage']:.0f}% "
             f"of balls, from {b['dot_percentage']:.0f}%",
             {"series": ["T20Is before", "v India, Oct 2026"], "format": "dec1", "values": True, "full_labels": True,
              "no_diff": True, "rows": rows},
             f"% of balls · {s['balls']} balls in the series", kicker="Fewer wasted balls")
    return c, {"b": b, "s": s}


def shots_card(db):
    def share(scope):
        rows = [r for r in q(db, group_by=["shot_family"], **scope) if r["shot_family"]]
        tot = sum(r["balls"] for r in rows)
        return {r["shot_family"]: 100 * r["balls"] / tot for r in rows}, {r["shot_family"]: r for r in rows}
    (b, braw), (s, sraw) = share(BEFORE), share(SERIES)
    rows = [{"label": n, "a": round(b.get(k, 0), 1), "b": round(s.get(k, 0), 1),
             "highlight": k in ("WORK_PUSH", "SLOG")} for k, n in FAMILIES]
    ps_b = b.get("WORK_PUSH", 0) + b.get("SLOG", 0)
    ps_s = s.get("WORK_PUSH", 0) + s.get("SLOG", 0)
    slog = braw["SLOG"]
    c = card("shots", "pair_dumbbell",
             f"Fewer pushes and slogs: {ps_s:.0f}% of his shots this series, from {ps_b:.0f}%",
             {"series": ["T20Is before", "v India, Oct 2026"], "format": "dec1", "values": True, "full_labels": True,
              "no_diff": True, "rows": rows},
             "% of balls, by shot · shot-tagged balls", kicker="The shots")
    return c, {"ps": (ps_b, ps_s), "slog_bpw": slog["balls"] / max(slog["wickets"], 1), "s": s, "b": b}


def wheel_card(db):
    from sqlalchemy import text

    ids = [str(r["match_id"]) for r in q(db, group_by=["match_id"], **SERIES)]
    shots = db.execute(text("""
        SELECT wagon_x AS x, wagon_y AS y, batruns AS runs, wagon_zone AS zone FROM delivery_details
        WHERE p_match = ANY(:ids) AND bat = :gp AND batruns >= 4 AND wagon_x IS NOT NULL"""), {"ids": ids, "gp": GP}).mappings().all()
    six_s = [s for s in shots if s["runs"] == 6]
    lo_s = sum(1 for s in six_s if s["zone"] == LONG_OFF)
    before = {r["wagon_zone"]: r for r in q(db, group_by=["wagon_zone"], **BEFORE) if r["wagon_zone"] is not None}
    six_b = sum(r["sixes"] for r in before.values())
    lo_b = before.get(LONG_OFF, {}).get("sixes", 0)
    c = card("wheel", "shot_wheel",
             f"{lo_s} of his {len(six_s)} sixes this series went over long-off. Before: {lo_b} of {six_b}",
             {"shots": [{"x": s["x"], "y": s["y"], "runs": s["runs"]} for s in shots]},
             f"His tracked boundaries v India, Oct 2026: sixes gold, fours lime",
             kicker="Where it went")
    return c, {"six_s": len(six_s), "lo_s": lo_s, "six_b": six_b, "lo_b": lo_b}


def plan_card(db):
    spin_cells = {(r["line"], r["length"]): r for r in q(db, group_by=["line", "length"], bowl_kind=["spin bowler"], **SINCE_2024)
                  if r["line"] and r["length"]}
    spin_all = one(db, bowl_kind=["spin bowler"], **SINCE_2024)
    gl = one(db, bowl_kind=["spin bowler"], length=["GOOD_LENGTH"], **SINCE_2024)
    cells = [{"line": k[0], "length": k[1], "value": round(r["strike_rate"]), "balls": r["balls"]}
             for k, r in spin_cells.items() if k[0] in LINES and k[1] in LENGTHS]
    for c_ in cells:
        c_["highlight"] = c_["length"] == "GOOD_LENGTH" and c_["line"] == "OUTSIDE_OFFSTUMP"
    share = lambda scope: 100 * (one(db, bowl_kind=["spin bowler"], **scope)["balls"] / one(db, **scope)["balls"])  # noqa: E731
    sh_s, sh_b = share(SERIES), share(BEFORE)
    early = one(db, dimension_filters=["batter_ball_number:lte:10"], **SINCE_2024)
    c = card("plan", "pitch_map",
             f"India bowled him spin {sh_s:.0f}% of the time. On a good length, spin holds him to {gl['strike_rate']:.0f}",
             {"hand": "RHB", "lines": LINES, "lengths": LENGTHS, "min_balls": 15,
              "metric": {"label": "Strike rate v spin", "format": "int", "higher_better": False,
                         "mid": round(spin_all["strike_rate"])},
              "legend": [f"Slower than his {spin_all['strike_rate']:.0f} v spin", "Faster"], "cells": cells},
             "Strike rate v spin · every T20 since 2024 · 15+ balls a cell",
             kicker="How to get him out")
    return c, {"sh_s": sh_s, "sh_b": sh_b, "gl": gl, "spin_all": spin_all, "early": early}


def build(db):
    lead, st = stretch_card(db)
    best, hn = hundred_card(db, st["t20i"])
    phase, ph = phase_card(db)
    length, ln = length_card(db)
    control, cn = control_card(db)
    shots, sh = shots_card(db)
    wheel, wh = wheel_card(db)
    plan, pl = plan_card(db)
    # 8 slides at most: the 107's card is in the caption and thread, not the carousel.
    return {"lead": lead, "cards": [phase, length, control, shots, wheel, plan],
            "st": st, "hn": hn, "ph": ph, "ln": ln, "cn": cn, "sh": sh, "wh": wh, "pl": pl}


def copy(b):
    st, hn, ph, ln, cn, sh, wh, pl = (b[k] for k in ("st", "hn", "ph", "ln", "cn", "sh", "wh", "pl"))
    lead, rb = st["lead"], st["runs_best"]
    hook = f"Glenn Phillips: {sg(lead['raa'], 0)} runs above par in 4 innings, his best T20I run by {st['gap']:.0f}"
    top = hn["top"]
    caption = "\n\n".join([
        f"82*, 70, 17, 107. Glenn Phillips has made {rb['runs']} runs in four T20Is against India, the most he has made in "
        f"any four straight innings in his T20 career, leagues included. By runs above par it's "
        f"{sg(lead['raa'], 0)}, his best T20I stretch by {st['gap']:.0f}, and {lead['wpa']:.2f} wins added, from a previous "
        f"best of {st['wpa_second']:.2f}.",
        f"The {top[0]['runs']} in Auckland was {sg(top[0]['raa'], 0)} runs above par, his best T20I innings; next is his "
        f"{top[1]['runs']} against {top[1]['opp']} in {when(top[1]['date'])}.",
        f"What changed? Not control: {cn['s']['control_percentage']:.0f}% of his shots were in control, as before. He "
        f"wasted fewer balls: dots on {cn['s']['dot_percentage']:.0f}% of balls, from {cn['b']['dot_percentage']:.0f}%, "
        f"boundaries on {cn['s']['boundary_percentage']:.0f}%, from {cn['b']['boundary_percentage']:.0f}%.",
        f"Good length used to be where he slowed down: {ln['gl_b']['strike_rate']:.0f} runs per 100 balls in his T20Is "
        f"before. This series: {ln['gl_s']['strike_rate']:.0f}, with {ln['gl_s']['sixes']} sixes. Fewer pushes and slogs "
        f"({sh['ps'][1]:.0f}% of his shots, from {sh['ps'][0]:.0f}%), and {wh['lo_s']} of his {wh['six_s']} sixes "
        f"went over long-off.",
        f"How to get him out? India bowled him spin {pl['sh_s']:.0f}% of the time; spin was {pl['sh_b']:.0f}% of his "
        f"T20I balls before. Since 2024, spin on a good length holds him to {pl['gl']['strike_rate']:.0f}, and his first "
        f"10 balls go at {pl['early']['strike_rate']:.0f}. Axar got him in game 3 with a good-length ball outside off.",
        "T20s to 30 Oct 2026. Runs above par and wins added: T20 Primer method. Ball-by-ball data: Himanish Ganjoo & "
        "TechRadar, Cricsheet.",
        "Spin, early, on a good length?",
        "Free ball-by-ball cricket stats: link in bio.\n.\n#NZvIND #GlennPhillips #BlackCaps #T20I #cricket",
    ])
    return hook, caption


def thread(b, link):
    st, hn, ph, ln, cn, sh, wh, pl = (b[k] for k in ("st", "hn", "ph", "ln", "cn", "sh", "wh", "pl"))
    lead, rb, top = st["lead"], st["runs_best"], hn["top"]
    texts = [
        f"82*, 70, 17, 107. Glenn Phillips has {rb['runs']} runs in 4 T20Is v India, the most he's made in any 4 straight "
        f"T20 innings. {sg(lead['raa'], 0)} runs above par: his best T20I run by {st['gap']:.0f}. 🧵",
        f"The {top[0]['runs']} in Auckland was {sg(top[0]['raa'], 0)} runs above par, his best T20I innings. Next best: "
        f"{top[1]['runs']} v {top[1]['opp']}, {when(top[1]['date'])} ({sg(top[1]['raa'], 0)}).",
        f"Faster in every phase. Powerplay: {ph['s']['powerplay']['strike_rate']:.0f} runs per 100 balls, from "
        f"{ph['b']['powerplay']['strike_rate']:.0f}. Death: {ph['s']['death']['strike_rate']:.0f}, from "
        f"{ph['b']['death']['strike_rate']:.0f}. V pace: {ph['ks']['pace bowler']['strike_rate']:.0f}, from "
        f"{ph['kb']['pace bowler']['strike_rate']:.0f}.",
        f"Good length was his slowest ball in T20Is: {ln['gl_b']['strike_rate']:.0f}. This series: "
        f"{ln['gl_s']['strike_rate']:.0f}, with {ln['gl_s']['sixes']} sixes off {ln['gl_s']['balls']} balls.",
        f"Not more control ({cn['s']['control_percentage']:.0f}%, as before). Fewer wasted balls: dots "
        f"{cn['s']['dot_percentage']:.0f}%, from {cn['b']['dot_percentage']:.0f}%. Boundaries "
        f"{cn['s']['boundary_percentage']:.0f}%, from {cn['b']['boundary_percentage']:.0f}%.",
        f"Fewer pushes and slogs: {sh['ps'][1]:.0f}% of his shots, from {sh['ps'][0]:.0f}%. Before this series he was out "
        f"every {sh['slog_bpw']:.0f} balls he slogged.",
        f"And a new area: {wh['lo_s']} of his {wh['six_s']} sixes went over long-off. Before: {wh['lo_b']} of {wh['six_b']}.",
        f"How to get him out? India bowled him spin {pl['sh_s']:.0f}% of the time ({pl['sh_b']:.0f}% in his T20Is before). "
        f"Since 2024, spin on a good length holds him to {pl['gl']['strike_rate']:.0f}. Axar got him that way in game 3.",
        f"Spin, early, on a good length?\n\nEvery ball, free: {link}\nData: @himganj153 & @TechRadar9",
    ]
    from services.ig_x import hand_thread

    return hand_thread(texts, copy(b)[1], THREAD_PLAYERS)


def reel_script(b):
    st, hn, ln, cn, pl = (b[k] for k in ("st", "hn", "ln", "cn", "pl"))
    return {"hook": f"{st['runs_best']['runs']} runs in 4 innings. Glenn Phillips has never been this good.",
            "lines": [f"That's {st['lead']['raa']:.0f} runs above par, his best T20I run by {st['gap']:.0f}.",
                      "Faster in every phase, against pace and spin.",
                      f"Good length used to slow him down. This series he's scoring at {ln['gl_s']['strike_rate']:.0f}.",
                      "Same control as always. Just far fewer dots.",
                      f"How to get him out? India bowled him spin a quarter of the time. "
                      f"On a good length, spin holds him to {pl['gl']['strike_rate']:.0f}."]}


def slides_of(b, hook):
    from services.ig_cover import hero_from

    cover = {"type": "hook", "text": hook, "cover": "hero", "hero": {**hero_from(b["lead"]), "card": b["lead"]}}
    return ([cover] + [{"type": "card", "card": c, "teams": ["New Zealand"]} for c in b["cards"]]
            + [{"type": "end", "heading": "Spin, early, on a good length?",
                "body": "Every T20I, ball by ball, with runs above par and win probability: free on Hindsight."}])


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
    fact = {"kind": "spotlight", "title": hook, "hook": hook, "subject": GP, "subject_role": "batter",
            "carousel_id": carousel["id"], "slides": n, "render": True, "post_time": "8 pm"}
    fact["x"] = thread(b, post_link(fact))
    fact["youtube"] = youtube_copy(fact, caption, hook)
    ist = timezone(timedelta(hours=5, minutes=30))
    today = datetime.now(ist).date()
    post = {"key": KEY, "pillar": "reactive", "fact": fact, "snapshot_id": carousel["id"], "warnings": [],
            "players": [GP], "caption": caption}
    with engine.begin() as conn:
        ig_backlog.upsert_pack(conn, post, today, source="hand", post_by=datetime.combine(today, time.max, tzinfo=ist))
    print(f"queued ig:{KEY} for {today} · carousel {carousel['id']} ({n} slides)")
    r = ig_slides.render(carousel["id"], n, args.base)
    print(f"rendered {len(r['ok'])}/{n}" + (f", failed {r['failed']}" if r["failed"] else "") + f"; layout {r.get('layout') or 'clean'}")
    # Reels are always voiced (the user's rule): the hand script replaces whatever the render stored.
    env = {**os.environ, "REEL_V2": "1", "REEL_AB": "0"}
    done = subprocess.run([sys.executable, str(ROOT / "scripts/make_reel_v2.py"), "--key", f"ig:{KEY}", "--beats", "1,2,3,4,7",
                           "--script", str(HERE / "reel.json"), "--close", "Spin, early, on a good length?", "--base", args.base,
                           "--store"], env=env, capture_output=True, text=True)
    ok = "stored as the post's Reel" in done.stdout
    print("voiced Reel:", "stored" if ok else f"FAILED\n{done.stderr[-800:]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
