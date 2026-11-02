"""
India's lower order, 26 Oct 2026. A take on X (a locked account, so paraphrased, never quoted or tagged): India were
good for years "with one hand tied behind their back" (a weak lower middle order) because they had difference makers
with the ball; without them, they were pushed into fixing it. Tested on India's T20Is since 2025 in three periods:
up to the World Cup (Hardik Pandya at 5-7; Bumrah, Varun, Kuldeep), June to 9 Oct 2026 (Shivam Dube's last game), and
since 11 Oct (Tilak Varma, Naman Dhir, Nitish Kumar Reddy, Axar Patel at 5-8).

Slides: cover (Bumrah's economy, cheapest of India's bowlers up to the World Cup); who bowled since (Bumrah, Varun,
Kuldeep: share of India's games); the deeper cut (No. 5-8 Impact per game by period); the players at 5-8; Axar at 5 v
6-8; all-rounders' economy v the specialists' by period; end. Bowling is read by economy, not Impact (bowling Impact
doesn't hold up as a rating of a bowler: split-half r about 0).

    python articles/india-lower-order/post.py                 # dry run: titles, lint; nothing saved (writes slides.json)
    python articles/india-lower-order/post.py --write         # queue for today and render
"""
from __future__ import annotations

import argparse
import subprocess
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

KEY = "spotlight-india-lower-order-2026-11-03"
SITE = "https://hindsightcricket.com"
B = "Jasprit Bumrah"
SINCE = date(2025, 1, 1)
END = date(2026, 11, 1)  # pinned: the fifth NZ T20I, so a rerun draws the same numbers
#: The three periods: up to the World Cup final (8 Mar 2026); June to Shivam Dube's last game (9 Oct); since.
PERIODS = [("A", "Jan 2025 to the World Cup", date(2025, 1, 1), date(2026, 3, 31)),
           ("B", "June to 9 Oct 2026", date(2026, 6, 1), date(2026, 10, 9)),
           ("C", "Since 11 Oct", date(2026, 10, 10), END)]
SHORT = {"A": "To the World Cup", "B": "June to 9 Oct", "C": "Since 11 Oct"}
#: India's all-rounders in the window (bat in the top 8 and bowl their overs); part-time bowlers (top-order batters
#: who roll an over) are in neither bowling group.
ALL_ROUNDERS = {"Hardik Pandya", "Shivam Dube", "Axar Patel", "Washington Sundar", "Nitish Kumar Reddy", "Naman Dhir",
                "Suryansh Shedge"}
PART_TIME = {"Abhishek Sharma", "Tilak Varma", "Rinku Singh"}
STARS = [B, "Varun Chakravarthy", "Kuldeep Yadav"]
MIN_OVERS = 20       # an India bowler on the cover chart
MIN_BALLS_5_8 = 40   # an India batter on the 5-8 chart
REGULAR = 300        # balls at 5-8: India's regulars there
CREDIT = "Ball-by-ball data: Himanish Ganjoo & TechRadar, Cricsheet."
THREAD_PLAYERS = [B, "Naman Dhir", "Nitish Kumar Reddy", "Axar Patel"]


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

    base = dict(fmt="T20", gender="male", include_international=True, limit=10000, start_date=SINCE, end_date=END)
    base.update(kw)
    return run_deliveries_query(db, **base)["data"]


def period(d):
    d = date.fromisoformat(str(d)[:10])
    return next((k for k, _, a, b in PERIODS if a <= d and (b is None or d <= b)), None)


def _nth(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


#: First names where the surname is shared in this XI or the player goes by his first name.
FIRST_NAME = {"Yadav", "Singh", "Patel", "Pandya", "Sharma", "Kumar", "Chakaravarthy", "Rana", "Sundar", "Reddy"}


def short(name):
    first, *_, last = name.split()
    return first if last in FIRST_NAME else last


def econ(runs, balls):
    return round(6 * runs / balls, 2)


# ---- the data -----------------------------------------------------------------------------------------------------

def load(db):
    bat = q(db, group_by=["match_date", "match_id", "batting_position", "batter"], batting_teams=["India"],
            metrics_perspective="batting")
    bowl = q(db, group_by=["match_date", "match_id", "bowler"], bowling_teams=["India"], metrics_perspective="bowling")
    return bat, bowl


def bowling(bowl):
    """Per period: India's games (with ball-by-ball bowling), each star's games and runs/balls, and the all-rounders'
    and specialists' runs/balls."""
    games = defaultdict(set)
    star = defaultdict(lambda: {"games": set(), "runs": 0, "balls": 0, "wkts": 0})
    group = defaultdict(lambda: {"runs": 0, "balls": 0})
    per_bowler_a = defaultdict(lambda: {"games": set(), "runs": 0, "balls": 0})
    for r in bowl:
        p = period(r["match_date"])
        if not p:
            continue
        games[p].add(r["match_id"])
        if r["bowler"] in STARS:
            s = star[(p, r["bowler"])]
            s["games"].add(r["match_id"]); s["runs"] += r["runs"]; s["balls"] += r["balls"]; s["wkts"] += r["wickets"]
        g = "ar" if r["bowler"] in ALL_ROUNDERS else (None if r["bowler"] in PART_TIME else "spec")
        if g:
            group[(p, g)]["runs"] += r["runs"]; group[(p, g)]["balls"] += r["balls"]
        if p == "A":
            b = per_bowler_a[r["bowler"]]
            b["games"].add(r["match_id"]); b["runs"] += r["runs"]; b["balls"] += r["balls"]
    return games, star, group, per_bowler_a


def lower_order(bat):
    """Per period: India's No. 5-8 Impact per game (every game India batted; nobody at 5-8 counts as 0) and balls."""
    games = defaultdict(set)
    imp = defaultdict(float)
    balls = defaultdict(int)
    players = defaultdict(lambda: {"balls": 0, "runs": 0, "impact": 0.0})
    axar = defaultdict(lambda: {"balls": 0, "runs": 0, "impact": 0.0})
    for r in bat:
        p = period(r["match_date"])
        if p:
            games[p].add(r["match_id"])
        pos = r["batting_position"]
        if 5 <= pos <= 8:
            if p:
                imp[p] += r["impact"]; balls[p] += r["balls"]
            pl = players[r["batter"]]
            pl["balls"] += r["balls"]; pl["runs"] += r["runs"]; pl["impact"] += r["impact"]
            if r["batter"] == "Axar Patel":
                k = "No. 5" if pos == 5 else "No. 6 to 8"
                a = axar[k]
                a["balls"] += r["balls"]; a["runs"] += r["runs"]; a["impact"] += r["impact"]
    per_game = {p: round(imp[p] / len(games[p]), 1) for p in games}
    balls_pg = {p: round(balls[p] / len(games[p])) for p in games}
    return per_game, balls_pg, {p: len(g) for p, g in games.items()}, players, axar


# ---- the cards ----------------------------------------------------------------------------------------------------

def games_table(db, bat, bowl):
    """One row per India T20I in the periods, oldest first: India's runs an over, whether Bumrah bowled, No. 5-8 Impact."""
    from sqlalchemy import text

    g = defaultdict(lambda: {"runs": 0, "balls": 0, "bumrah": False, "lower": 0.0, "date": None, "bowled": False,
                             "ar_runs": 0, "ar_balls": 0, "sp_runs": 0, "sp_balls": 0})
    for r in bowl:
        m = g[r["match_id"]]
        m["date"] = str(r["match_date"])[:10]; m["runs"] += r["runs"]; m["balls"] += r["balls"]; m["bowled"] = True
        m["bumrah"] |= r["bowler"] == B
        grp = "ar" if r["bowler"] in ALL_ROUNDERS else (None if r["bowler"] in PART_TIME else "sp")
        if grp:
            m[f"{grp}_runs"] += r["runs"]; m[f"{grp}_balls"] += r["balls"]
    for r in bat:
        m = g[r["match_id"]]
        m["date"] = m["date"] or str(r["match_date"])[:10]
        if 5 <= r["batting_position"] <= 8:
            m["lower"] += r["impact"] or 0.0
    ids = [str(k) for k in g]
    opp = {str(o["id"]): (o["team2"] if o["team1"] == "India" else o["team1"]) for o in db.execute(text(
        "SELECT id, team1, team2 FROM matches WHERE id = ANY(:ids)"), {"ids": ids}).mappings()}
    rows = []
    for k, m in g.items():
        p = period(m["date"])
        if p and m["bowled"]:
            rows.append({**m, "id": str(k), "period": p, "opp": opp.get(str(k), "")})
    return sorted(rows, key=lambda r: r["date"])


def cover_card(games):
    w = [m for m in games if m["bumrah"]]; wo = [m for m in games if not m["bumrah"]]
    e = lambda ms: econ(sum(m["runs"] for m in ms), sum(m["balls"] for m in ms))  # noqa: E731
    ew, ewo = e(w), e(wo)
    assert ew < ewo
    c = card("with-without", "metric_bars",
             f"India concede {ew:.1f} an over with Jasprit Bumrah, {ewo:.1f} without him",
             {"metric": {"label": "India's runs an over", "format": "dec2"}, "label_width": 150,
              "rows": [{"name": "With Bumrah", "value": ew, "highlight": True, "detail": f"{len(w)} games"},
                       {"name": "Without him", "value": ewo, "detail": f"{len(wo)} games"}]},
             "India's T20Is, Jan 2025 to 1 Nov 2026 · runs an over, all bowlers")
    return c, {"with": ew, "without": ewo, "nw": len(w), "nwo": len(wo)}


def timeline_card(games):
    later = [m for m in games if m["period"] != "A"]
    a = [m for m in games if m["period"] == "A"]
    pc = lambda k: sum(m["lower"] for m in games if m["period"] == k) / max(1, sum(1 for m in games if m["period"] == k))  # noqa: E731
    c = card("timeline", "game_timeline",
             f"Without Bumrah, India's 5 to 8 still cost runs. Since 11 Oct: {sg(pc('C'))} a game",
             {"games": [{"label": f"v {m['opp']}, {m['date']}", "period": m["period"], "top": econ(m["runs"], m["balls"]),
                         "bottom": round(m["lower"], 1), "marked": m["bumrah"]} for m in games],
              "periods": [{"key": k, "label": SHORT[k]} for k, *_ in PERIODS],
              "top": {"label": "India's runs an over (bowling)", "format": "dec1"},
              "bottom": {"label": "No. 5 to 8, runs added (Impact)", "format": "signed1"},
              "marked_label": "Bumrah played", "unmarked_label": "He didn't"},
             "Every India T20I, Jan 2025 to 1 Nov 2026 · dashed: each period's average", kicker="Game by game")
    return c, {"a": (sum(m["bumrah"] for m in a), len(a)), "later": (sum(m["bumrah"] for m in later), len(later)),
               "lower": {k: pc(k) for k, *_ in PERIODS}}


def unit_card(games):
    """The 5-8 as a unit, bat and ball, per game: batting Impact, plus the all-rounders' runs saved (or cost) against
    the specialists' economy in the same games."""
    rows, raw = [], {}
    for k, label, _, _ in PERIODS:
        ms = [m for m in games if m["period"] == k]
        sp_e = sum(m["sp_runs"] for m in ms) / max(1, sum(m["sp_balls"] for m in ms))
        ar_runs = sum(m["ar_runs"] for m in ms); ar_balls = sum(m["ar_balls"] for m in ms)
        ball = (sp_e * ar_balls - ar_runs) / len(ms)
        bat = sum(m["lower"] for m in ms) / len(ms)
        raw[k] = (bat, ball, bat + ball, len(ms))
        rows.append({"name": SHORT[k], "value": round(bat + ball, 1), "highlight": k == "C",
                     "detail": f"bat {sg(bat)} · ball {sg(ball)} · {len(ms)} games"})
    c = card("unit", "metric_bars",
             f"Bat and ball together, India's 5 to 8 net {sg(raw['C'][2])} runs a game since 11 Oct",
             {"metric": {"label": "Runs a game: batting Impact + bowling runs saved v the specialists", "format": "signed1",
                         "signed": True}, "label_width": 170, "rows": rows},
             "Bowling: all-rounders' runs v the specialists' economy, same games", kicker="The deeper cut")
    return c, raw


def players_card(players):
    rows = sorted(((n, v) for n, v in players.items() if v["balls"] >= MIN_BALLS_5_8),
                  key=lambda x: -x[1]["impact"] / x[1]["balls"])
    top, top_v = rows[0]
    per = lambda v: round(100 * v["impact"] / v["balls"], 1)  # noqa: E731
    new = {"Naman Dhir", "Nitish Kumar Reddy"}
    c = card("players-5-8", "metric_bars",
             f"{top}: {sg(per(top_v), 0)} Impact per 100 balls at No. 5 to 8, India's best since 2025",
             {"metric": {"label": "Impact per 100 balls", "format": "signed1", "signed": True}, "label_width": 150,
              "rows": [{"name": n, "value": per(v), "highlight": n in new, "detail": f"{v['runs']} off {v['balls']}"}
                       for n, v in rows[:7]]},
             f"India batters, {MIN_BALLS_5_8}+ balls at No. 5 to 8 · T20Is since Jan 2025", kicker="Who")
    return c, {n: (per(v), v) for n, v in rows}


def axar_card(axar):
    per = {k: round(100 * v["impact"] / v["balls"], 1) for k, v in axar.items()}
    five, low = per["No. 5"], per["No. 6 to 8"]
    assert five > low
    c = card("axar-position", "metric_bars",
             f"Axar Patel at No. 5: {sg(five)} Impact per 100 balls. At 6 to 8: {sg(low)}",
             {"metric": {"label": "Impact per 100 balls", "format": "signed1", "signed": True}, "label_width": 130,
              "rows": [{"name": k, "value": per[k], "highlight": k == "No. 5",
                        "detail": f"{axar[k]['runs']} off {axar[k]['balls']}"} for k in ("No. 5", "No. 6 to 8")]},
             "Axar Patel for India · T20Is since Jan 2025", kicker="Where Axar fits")
    return c, {"five": five, "low": low, "b5": axar["No. 5"]["balls"], "b68": axar["No. 6 to 8"]["balls"]}


def bowling_card(group):
    rows, raw = [], {}
    for k, label, _, _ in PERIODS:
        ar, sp = group[(k, "ar")], group[(k, "spec")]
        raw[k] = (econ(ar["runs"], ar["balls"]), econ(sp["runs"], sp["balls"]))
        rows.append({"label": SHORT[k], "a": raw[k][1], "b": raw[k][0], "highlight": k == "C"})
    c = card("ar-v-specialists", "pair_dumbbell",
             f"Everyone got dearer: specialists {raw['C'][1]:.1f} an over since 11 Oct, from {raw['A'][1]:.1f}",
             {"series": ["Specialists", "All-rounders"], "format": "dec2", "values": True, "full_labels": True,
              "no_diff": True, "rows": rows},
             "India bowlers, runs an over · part-time bowlers not counted", kicker="Both ways")
    return c, {"raw": raw}


def build(db):
    bat, bowl = load(db)
    games_by, star, group, per_a = bowling(bowl)
    per_game, balls_pg, n_bat, players, axar = lower_order(bat)
    games = games_table(db, bat, bowl)
    lead, cv = cover_card(games)
    tl, tlv = timeline_card(games)
    un, unv = unit_card(games)
    pl, plv = players_card(players)
    ax, axv = axar_card(axar)
    bw, bwv = bowling_card(group)
    return {"lead": lead, "cards": [tl, un, pl, ax, bw], "cv": cv, "tl": tlv, "unit": unv, "players": plv,
            "axar": axv, "bw": bwv, "balls_pg": balls_pg, "n_bat": n_bat}


def copy(b):
    cv, tl, un, pl, ax, bw = b["cv"], b["tl"], b["unit"], b["players"], b["axar"], b["bw"]
    dhir, nkr = pl["Naman Dhir"], pl["Nitish Kumar Reddy"]
    hook = f"Jasprit Bumrah has played {tl['later'][0]} of India's {tl['later'][1]} T20Is since June. India's lower order had to step up"
    r = bw["raw"]
    caption = "\n\n".join([
        f"Jasprit Bumrah played {tl['a'][0]} of India's {tl['a'][1]} T20Is from January 2025 to the World Cup. Since June: "
        f"{tl['later'][0]} of {tl['later'][1]}. With him India concede {cv['with']:.1f} an over; without him, {cv['without']:.1f}.",
        "A take doing the rounds: India were winning with one hand tied behind their back, a lower middle order that "
        "didn't add much, because the bowlers made up for it. Without them, India had to fix it. We tested it.",
        f"India's No. 5 to 8 added {sg(tl['lower']['A'])} runs a game up to the World Cup (Impact: runs added to India's "
        f"projected total), {sg(tl['lower']['B'])} from June to 9 Oct, and {sg(tl['lower']['C'])} in the "
        f"{un['C'][3]} games since 11 Oct. Bat and ball together, the 5 to 8 net {sg(un['C'][2])} a game since 11 Oct.",
        f"Who: Naman Dhir, {sg(dhir[0])} per 100 balls at 5 to 8 ({dhir[1]['runs']} off {dhir[1]['balls']}), and Nitish "
        f"Kumar Reddy, {sg(nkr[0])}. Axar Patel costs less at No. 5 ({sg(ax['five'])} per 100 balls) than at 6 to 8 "
        f"({sg(ax['low'])}).",
        f"Both ways: everyone got dearer, in West Indies and New Zealand. India's specialists go at {r['C'][1]:.1f} an over "
        f"since 11 Oct, from {r['A'][1]:.1f} up to the World Cup. And {un['C'][3]} games against two sides is a small "
        "sample.",
        "Impact: T20 Primer method. " + CREDIT,
        "Who bats at 5 when Bumrah is back?",
        "Free ball-by-ball cricket stats: link in bio.\n.\n#NZvIND #JaspritBumrah #NamanDhir #TeamIndia #T20I",
    ])
    return hook, caption


def thread(b, link):
    cv, tl, un, pl, ax, bw = b["cv"], b["tl"], b["unit"], b["players"], b["axar"], b["bw"]
    dhir, nkr = pl["Naman Dhir"], pl["Nitish Kumar Reddy"]
    r = bw["raw"]
    texts = [
        f"Jasprit Bumrah has played {tl['later'][0]} of India's {tl['later'][1]} T20Is since June. With him India concede "
        f"{cv['with']:.1f} an over; without him, {cv['without']:.1f}. 🧵",
        f"Game by game: without Bumrah from June, India's No. 5 to 8 still cost runs ({sg(tl['lower']['B'])} a game to "
        f"9 Oct). Since 11 Oct: {sg(tl['lower']['C'])} a game.",
        f"Bat and ball together, the 5 to 8 net {sg(un['C'][2])} runs a game since 11 Oct, from {sg(un['A'][2])} up to the "
        "World Cup.",
        f"Who: Naman Dhir {sg(dhir[0])} Impact per 100 balls at 5 to 8 ({dhir[1]['runs']} off {dhir[1]['balls']}). "
        f"Nitish Kumar Reddy {sg(nkr[0])}.",
        f"Axar Patel costs less at No. 5 ({sg(ax['five'])} per 100 balls) than at 6 to 8 ({sg(ax['low'])}).",
        f"Both ways: everyone got dearer. Specialists {r['C'][1]:.1f} an over since 11 Oct, from {r['A'][1]:.1f}. And "
        f"{un['C'][3]} games is a small sample.",
        f"Who bats at 5 when Bumrah is back?\n\nEvery ball, free: {link}\nData: @himganj153 & @TechRadar9",
    ]
    from services.ig_x import hand_thread

    return hand_thread(texts, copy(b)[1], THREAD_PLAYERS)


def reel_script(b):
    cv, tl, un, pl = b["cv"], b["tl"], b["unit"], b["players"]
    dhir = pl["Naman Dhir"]
    return {"hook": f"Jasprit Bumrah has played {tl['later'][0]} of India's {tl['later'][1]} T20Is since June.",
            "lines": [f"Without him, the lower order still cost runs. Since mid-October, it's added {tl['lower']['C']:.0f} a game.",
                      f"Bat and ball together, numbers 5 to 8 are {un['C'][2]:.0f} runs a game up since mid-October.",
                      f"The difference: Naman Dhir, {dhir[0]:.0f} runs added per 100 balls.",
                      "Everyone's been expensive, so it's not all fixed. But it's a side nobody saw before."]}


def slides_of(b, hook):
    from services.ig_cover import hero_from

    cover = {"type": "hook", "text": hook, "cover": "hero", "hero": {**hero_from(b["lead"]), "card": b["lead"]}}
    return ([cover] + [{"type": "card", "card": c, "teams": ["India"]} for c in b["cards"]]
            + [{"type": "end", "heading": "Who bats at 5 when Bumrah is back?",
                "body": "Every T20I, ball by ball, with Impact and economy: free on Hindsight."}])


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
    fact = {"kind": "spotlight", "title": hook, "hook": hook, "subject": "India", "subject_role": "team",
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
    done = subprocess.run([sys.executable, str(ROOT / "scripts/make_reel_v2.py"), "--key", f"ig:{KEY}", "--beats", "2,3,4,6",
                           "--script", str(HERE / "reel.json"), "--close", "Who bats at 5 when Bumrah is back?", "--base", args.base,
                           "--store"], env=env, capture_output=True, text=True)
    ok = "stored as the post's Reel" in done.stdout
    print("voiced Reel:", "stored" if ok else f"FAILED\n{done.stdout[-1500:]}\n{done.stderr[-1500:]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
