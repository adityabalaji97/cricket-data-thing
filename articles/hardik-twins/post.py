"""
"There's no one quite like Hardik", 29 Oct 2026 (trade talk around him): the IPL double, his statistical twins over his
whole career (2015 on, when Impact and tracking start), how teams use him (every phase with the ball), the value with
bat and ball for India, and the arc both ways.

Twins: careers 2015 to today against strong sides (major leagues + top-12 T20Is), all-rounders matched on bat and ball,
pace with pace, shot-tracked with shot-tracked (services/twins.py), from career_vectors.pkl (build_career.py).

    python articles/hardik-twins/post.py              # dry run
    python articles/hardik-twins/post.py --write      # queue, render, voiced Reel (reel.json), hand-written thread
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import subprocess
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

KEY = "spotlight-hardik-twins-2026-10-29"
SITE = "https://hindsightcricket.com"
HP = "Hardik Pandya"
PERIOD = "career"
SINCE = date(2015, 1, 1)
COMMON_SURNAMES = {"Sharma", "Yadav", "Singh", "Kumar", "Patel", "Khan", "Iyer", "Pandya"}
IPL = {"fmt": "T20", "leagues": ["IPL"]}
BOTH = {"fmt": "T20", "leagues": ["IPL"], "include_international": True}   # IPL + every T20I
SCOPE = "IPL and T20Is"
INDIA_SINCE = {"fmt": "T20", "include_international": True, "start_date": SINCE}


NICK = {"Nitish Kumar Reddy": "Nitish", "Marcus Stoinis": "Stoinis"}


def short(name):
    if name in NICK:
        return NICK[name]
    first, last = name.split()[0], name.split()[-1]
    return first if last in COMMON_SURNAMES else last


def sg(v, d=1):
    return f"{v:+.{d}f}".replace("-", "\u2212")


def card(cid, visual, title, payload, sample, help_=""):
    assert len(title) <= 80, (len(title), title)
    return {"id": cid, "visual": visual, "title": title, "help": help_, "sample": sample, "payload": payload}


def q(db, **kw):
    from services.query_builder_v2 import run_deliveries_query

    kw.setdefault("limit", 10000)
    return run_deliveries_query(db, **kw)["data"]


def sides(db):
    from sqlalchemy import text

    return {n: s for n, s in db.execute(text(
        "SELECT DISTINCT ON (name) name, main_side FROM player_identity ORDER BY name, balls DESC")).all()}


# ---- twins over the whole career --------------------------------------------------------------------------------

def career_pool():
    """All-rounder rows (the services/twins.pool('allround') shape) from the pickled 2015-now career vectors."""
    from services.twins import percentiles

    vec = pickle.load(open(HERE / "career_vectors.pkl", "rb"))
    roles = {}
    for role in ("bat", "bowl"):
        rows = [{"period": PERIOD, "player": n, "balls": v["balls"], "innings": v["innings"], "kind": v["kind"],
                 "tracked_share": v["tracked_share"], "features": v["features"]}
                for n, v in vec[role].items() if v["qualified"] and n]
        percentiles(rows)
        roles[role] = {r["player"]: r for r in rows}
    out = []
    for name in roles["bat"].keys() & roles["bowl"].keys():
        a, b = roles["bat"][name], roles["bowl"][name]
        if min(a["innings"], b["innings"]) < 0.4 * max(a["innings"], b["innings"]):
            continue  # services/twins: a second role in under 40% of the main role's innings isn't all-rounding
        out.append({"period": PERIOD, "player": name, "balls": a["balls"] + b["balls"], "kind": b["kind"],
                    "bat_weight": a["innings"] / (a["innings"] + b["innings"]),
                    "tracked": {"bat": a["tracked_share"], "bowl": b["tracked_share"]},
                    "p": {**{f"bat:{k}": v for k, v in a["p"].items()}, **{f"bowl:{k}": v for k, v in b["p"].items()}},
                    "features": {"bat": a["features"], "bowl": b["features"]}})
    return out


def twins(db):
    from services.twins import find_in, twin_map

    rows = career_pool()
    side = sides(db)
    near = find_in(rows, HP, PERIOD, "allround", "style", len(rows), same_period=True)["twins"]
    me = next(r for r in rows if r["player"] == HP)
    by = {r["player"]: r for r in rows}
    gap = {t["player"]: round(100 * t["distance"]) for t in near}
    gaps_all = sorted(round(100 * (find_in(rows, r["player"], PERIOD, "allround", "style", 1, same_period=True)["twins"]
                                    or [{"distance": 0}])[0]["distance"]) for r in rows)
    typical = gaps_all[len(gaps_all) // 2]
    indians = [t["player"] for t in near if side.get(t["player"]) == "India"]
    placed = twin_map(me, [(t["distance"], by[t["player"]]) for t in near], "allround")
    return {"near": near, "gap": gap, "pool": len(near) + 1, "typical": typical, "indians": indians, "placed": placed,
            "side": side, "closest": {t["player"]: [c["label"] for c in t["closest"][:2]] for t in near[:6]}}


# ---- the slides -------------------------------------------------------------------------------------------------

def cover_card(db):
    bat = {r["batter"]: r for r in q(db, group_by=["batter"], metrics_perspective="batting", min_runs=500, **BOTH)}
    bowl = {r["bowler"]: r for r in q(db, group_by=["bowler"], metrics_perspective="bowling", min_wickets=20, **BOTH)}
    both = {n: (bat[n]["runs"], bowl[n]["wickets"]) for n in bat if n in bowl}
    elite = sorted((n for n, (r, w) in both.items() if r >= 4000 and w >= 150), key=lambda n: -both[n][0])
    assert HP in elite, elite
    named_list = [HP] + [n for n in elite if n != HP] + ["Shane Watson", "Andre Russell", "Axar Patel", "Shakib Al Hasan"]
    named = {n: i + 1 for i, n in enumerate(dict.fromkeys(named_list)) if n in both}
    pts = [{"name": n, "x": r, "y": w, **({"highlight": True} if n == HP else {}),
            **({"label": named[n], "short": short(n)} if n in named else {})} for n, (r, w) in both.items()]
    runs, wkts = both[HP]
    others = [n for n in elite if n != HP]
    c = card("double", "scatter_plus",
             f"{SCOPE}: only Hardik and {short(others[0])} have 4,000+ runs and 150+ wickets"
             if len(others) == 1 else f"{SCOPE}: {len(elite)} players have 4,000+ runs and 150+ wickets",
             {"points": pts, "box": False, "x": {"label": "runs", "format": "int"}, "y": {"label": "wickets", "format": "int"}},
             f"Every player with 500+ runs and 20+ wickets · {SCOPE}, 2008 to Oct 2026")
    return c, {"runs": runs, "wkts": wkts, "elite": elite, "others": others, "both": both}


def star_card(t):
    near = t["near"][:12]
    c = card("twins", "distance_star",
             f"His closest statistical twins: {near[0]['player']} ({t['gap'][near[0]['player']]} points), "
             f"{short(near[1]['player'])} ({t['gap'][near[1]['player']]})",
             {"center": HP, "center_label": "Hardik",
              "spokes": [{"name": x["player"], "distance": t["gap"][x["player"]], "label": short(x["player"]),
                          "highlight": x["player"] in (near[0]["player"], near[1]["player"])} for x in near]},
             f"Pace-bowling all-rounders · careers since 2015 v strong sides")
    return c


def india_card(t):
    ind = t["indians"]
    labelled = {n: short(n) for n in ind[:3]}
    c = card("india", "twin_cloud",
             f"The nearest Indian is {short(ind[0])}, {t['gap'][ind[0]]} points away. Next: {short(ind[1])}, {t['gap'][ind[1]]}",
             {"center": HP, "center_label": "Hardik", "ring_step": 10, "label_rings_to": 30,
              "points": [{"name": p["player"], "distance": round(100 * p["distance"], 1), "angle": p["angle"],
                          "highlight": p["player"] in labelled, "label": labelled.get(p["player"])} for p in t["placed"]]},
             f"{t['pool']} pace all-rounders · most have a twin within {t['typical']} points")
    c["kicker"] = "In India"
    return c


def usage_card(db, players):
    overall = {r["bowler"]: r for r in q(db, group_by=["bowler"], bowlers=players, metrics_perspective="bowling", **BOTH)}
    phase = q(db, group_by=["bowler", "phase"], bowlers=players, metrics_perspective="bowling", **BOTH)
    per = {}
    for r in phase:
        inns = overall[r["bowler"]]["innings_count"] or 1
        per.setdefault(r["bowler"], {})[r["phase"]] = round(r["balls"] / inns, 1)
    rows = [p for p in players if p in per]
    hp = per[HP]
    c = card("usage", "share_bars",
             f"Hardik bowls {sum(hp.values()):.0f} balls a game, in all three phases",
             {"absolute": True, "format": "dec1", "label_width": 150,
              "groups": [{"key": "powerplay", "label": "Powerplay", "colour": "#5b8def"},
                         {"key": "middle", "label": "Middle overs", "colour": "#b6f24a"},
                         {"key": "death", "label": "Death", "colour": "#e66767"}],
              "rows": [{"name": p, "detail": f"{overall[p]['innings_count']} games",
                        "segments": [{"key": k, "value": per[p].get(k, 0)} for k in ("powerplay", "middle", "death")]}
                       for p in rows]},
             f"Balls bowled per game, by phase · {SCOPE}, 2008 to Oct 2026")
    c["kicker"] = "How he's used"
    return c, {"per": per}


def value_card(db, side):
    """Wins added since 2015 split by competition: for India he's above par with both; in the IPL below par with both.
    Combined (−0.7 bat, −0.8 ball) would hide the India role that makes teams want him."""
    def one(**sc):
        bt = q(db, group_by=["batter"], batters=[HP], metrics_perspective="batting", start_date=SINCE, **sc)[0]
        sc_b = dict(sc)
        if "batting_teams" in sc_b:
            sc_b["bowling_teams"] = sc_b.pop("batting_teams")
        bw = q(db, group_by=["bowler"], bowlers=[HP], metrics_perspective="bowling", start_date=SINCE, **sc_b)[0]
        return bt["wpa"] or 0, bw["wpa"] or 0
    ib, iw = one(fmt="T20", include_international=True, batting_teams=["India"])
    pb, pw = one(**IPL)
    rows = [{"name": "India, batting", "value": round(ib, 2), "highlight": True},
            {"name": "India, bowling", "value": round(iw, 2), "highlight": True},
            {"name": "IPL, batting", "value": round(pb, 2)},
            {"name": "IPL, bowling", "value": round(pw, 2)}]
    c = card("value", "metric_bars",
             f"For India: {sg(ib)} bat, {sg(iw)} ball. In the IPL, below par with both",
             {"metric": {"label": "Wins added", "format": "signed2", "signed": True}, "label_width": 130, "rows": rows},
             "Wins added since 2015 (T20 Primer method) · India T20Is and the IPL")
    c["kicker"] = "The value"
    return c, {"hb": ib, "hw": iw, "pb": pb, "pw": pw}


PERIODS = [("2015-16", 2015, 2016), ("2017-19", 2017, 2019), ("2020-22", 2020, 2022), ("2023-26", 2023, 2026)]


def arc_card(db):
    """Wins added over four stretches of his IPL career, bat and ball together (a line chart of single seasons dropped
    below its axis; one bar per stretch reads in a glance and carries the split in its detail)."""
    bat = {r["year"]: r for r in q(db, group_by=["year"], batters=[HP], metrics_perspective="batting", **BOTH)}
    bowl = {r["year"]: r for r in q(db, group_by=["year"], bowlers=[HP], metrics_perspective="bowling", **BOTH)}
    rows = []
    for label, a, b_ in PERIODS:
        wb = sum((bat[y]["wpa"] or 0) for y in bat if a <= y <= b_)
        ww = sum((bowl[y]["wpa"] or 0) for y in bowl if a <= y <= b_)
        rows.append({"name": label, "value": round(wb + ww, 2), "detail": f"bat {sg(wb, 2)}, ball {sg(ww, 2)}"})
    best = max(rows, key=lambda r: r["value"])
    best["highlight"] = True
    c = card("arc", "metric_bars",
             f"His best: {sg(best['value'])} wins added in {best['name']}. Since 2023: {sg(rows[-1]['value'])}",
             {"metric": {"label": "Wins added, bat and ball", "format": "signed2", "signed": True}, "label_width": 110,
              "rows": rows},
             f"{SCOPE} by season, grouped")
    c["kicker"] = "Both ways"
    return c, {"rows": rows, "best": best}


def build(db):
    lead, cn = cover_card(db)
    t = twins(db)
    star = star_card(t)
    india = india_card(t)
    usage_players = [HP] + [p for p in [t["near"][0]["player"], t["indians"][0], t["near"][1]["player"],
                                        t["near"][2]["player"]] if p != HP]
    usage_players = list(dict.fromkeys(usage_players))
    usage, un = usage_card(db, usage_players)
    value, vn = value_card(db, t["side"])
    arc, an = arc_card(db)
    return {"lead": lead, "cards": [star, india, usage, value, arc], "cn": cn, "t": t, "un": un, "vn": vn, "an": an}


def copy(b):
    cn, t, un, vn, an = b["cn"], b["t"], b["un"], b["vn"], b["an"]
    n0, n1 = t["near"][0]["player"], t["near"][1]["player"]
    i0, i1 = t["indians"][0], t["indians"][1]
    o = cn["others"][0]
    hook = f"Hardik Pandya: {cn['runs']:,} runs, {cn['wkts']} wickets in IPL and T20Is. Anyone like him?"
    caption = "\n\n".join([
        f"Hardik Pandya has {cn['runs']:,} runs and {cn['wkts']} wickets in the IPL and T20Is. Only {o} has also passed "
        f"4,000 runs and 150 wickets ({cn['both'][o][0]:,} and {cn['both'][o][1]}). With trade talk around him, here's "
        "what makes him hard to replace.",
        f"His statistical twins, careers since 2015 against strong sides: {n0} ({t['gap'][n0]} points) and {n1} "
        f"({t['gap'][n1]}). The nearest Indian is {i0} ({t['gap'][i0]}), then {i1} ({t['gap'][i1]}). Most pace-bowling "
        f"all-rounders have a twin within {t['typical']} points.",
        f"How teams use him: {sum(un['per'][HP].values()):.0f} balls a game, in the powerplay, the middle overs and at "
        "the death.",
        f"The value, since 2015: for India he has added {sg(vn['hb'], 2)} wins with the bat and {sg(vn['hw'], 2)} with "
        f"the ball. In the IPL, {sg(vn['pb'], 2)} and {sg(vn['pw'], 2)}.",
        f"Both ways: his best stretch was {an['best']['name']} ({sg(an['best']['value'])} wins added); since 2023, "
        f"{sg(an['rows'][-1]['value'])}.",
        "How it works: each player's game (when he bats and bowls, how he scores and what he concedes, his shots, lengths "
        "and lines) as percentiles of every pace-bowling all-rounder, then the typical gap between two players. "
        "Wins added: T20 Primer method. Ball-by-ball data: Himanish Ganjoo & TechRadar, Cricsheet.",
        "Who's the next Hardik?",
        "Free ball-by-ball cricket stats: link in bio.\n.\n#HardikPandya #IPL #IPL2027 #TeamIndia #cricket",
    ])
    return hook, caption


def thread(b, link):
    """Hand-written, one tweet per slide (services/ig_x.x_thread garbles method posts)."""
    cn, t, un, vn, an = b["cn"], b["t"], b["un"], b["vn"], b["an"]
    n0, n1 = t["near"][0]["player"], t["near"][1]["player"]
    i0, i1 = t["indians"][0], t["indians"][1]
    o = cn["others"][0]
    hp = un["per"][HP]
    texts = [
        f"Hardik Pandya: {cn['runs']:,} runs and {cn['wkts']} wickets in the IPL and T20Is. Only {o} has also passed "
        f"4,000 and 150.\n\nIs there anyone like him? 🧵\n#HardikPandya #IPL",
        f"His closest statistical twins over his whole career: {n0}, {t['gap'][n0]} points away, and {n1}, "
        f"{t['gap'][n1]}.\n\nPace-bowling all-rounders, careers since 2015 v strong sides, matched on how they bat and bowl.",
        f"In India, the nearest is {i0} ({t['gap'][i0]} points). The next, {i1}, is {t['gap'][i1]} away. Most all-rounders "
        f"have a twin within {t['typical']}.",
        f"How he's used: {sum(hp.values()):.0f} balls a game across the IPL and T20Is: {hp.get('powerplay', 0)} in the "
        f"powerplay, {hp.get('middle', 0)} in the middle overs, {hp.get('death', 0)} at the death.",
        f"The value since 2015: for India {sg(vn['hb'], 2)} wins added with the bat, {sg(vn['hw'], 2)} with the ball. In "
        f"the IPL, below par with both: {sg(vn['pb'], 2)} and {sg(vn['pw'], 2)}.",
        f"Both ways: his best stretch was {an['best']['name']}, {sg(an['best']['value'])} wins added. Since 2023: "
        f"{sg(an['rows'][-1]['value'])}.",
        f"Who's the next Hardik?\n\nEvery player's doppelgängers, free: {link}\nData: @himganj153 & @TechRadar9",
    ]
    out = []
    for i, x in enumerate(texts, 1):
        assert len(x) <= 280, (i, len(x), x)
        out.append({"n": i, "slide": i, "text": x})
    return out


def reel_script(b):
    """The voiced Reel's lines, from the same numbers as the slides (beats 1, 2, 4, 5, 6)."""
    cn, t, un, vn, an = b["cn"], b["t"], b["un"], b["vn"], b["an"]
    n0 = t["near"][0]["player"]
    return {"hook": f"Hardik Pandya: {cn['runs']:,} runs and {cn['wkts']} wickets in the IPL and T20Is. Is there anyone like him?",
            "lines": [f"Only {cn['others'][0]} has also passed 4,000 runs and 150 wickets.",
                      f"Over his whole career, his closest statistical twin is {n0}, {t['gap'][n0]} points away.",
                      f"He bowls {sum(un['per'][HP].values()):.0f} balls a game, in the powerplay, the middle overs and at the death.",
                      "For India, he adds wins with the bat and the ball. In the IPL, he's below par with both.",
                      f"His best stretch was {an['best']['name'].replace('-', ' to 20')}. Since 2023, the numbers have dipped."]}


def slides_of(b, hook):
    from services.ig_cover import hero_from

    cover = {"type": "hook", "text": hook, "cover": "hero", "hero": {**hero_from(b["lead"]), "card": b["lead"]}}
    return ([cover] + [{"type": "card", "card": c, "teams": ["India"]} for c in b["cards"]]
            + [{"type": "end", "heading": "Who's the next Hardik?",
                "body": "Every player's doppelgängers, with the map: hindsightcricket.com/doppelgangers. Free."}])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--base", default=SITE)
    args = parser.parse_args()
    if args.write:
        assert "localhost" not in os.environ.get("DATABASE_URL", ""), "--write is production: leave DATABASE_URL unset"
    from database import get_session
    from services.social_rules import findings, hook_problem

    db = next(get_session())
    b = build(db)
    hook, caption = copy(b)
    slides = slides_of(b, hook)
    print("HOOK:", hook, f"({len(hook)})")
    for i, s in enumerate(slides, 1):
        c = s.get("card") or (s.get("hero") or {}).get("card") or {}
        print(f"  {i}. [{c.get('visual') or s['type']}] {c.get('title') or s.get('heading')} ({len(c.get('title') or '')})")
    problems = findings(slides, "spotlight")
    hp = hook_problem(hook)
    print("lint:", problems or "clean", "| hook:", hp or "ok")
    print(caption)
    th = thread(b, "hindsightcricket.com/doppelgangers")
    for t in th:
        print(f"--- tweet {t['n']} ({len(t['text'])})\n{t['text']}")
    (HERE / "reel.json").write_text(json.dumps(reel_script(b), indent=1))
    print("REEL:", json.dumps(reel_script(b)))
    (HERE / "slides.json").write_text(json.dumps({"slides": slides, "hook": hook, "caption": caption, "x": th},
                                                 default=str, indent=1))
    if problems or hp or not args.write:
        return 1 if (problems or hp) else 0

    from database import engine
    from services import ig_backlog, ig_carousel, ig_slides
    from services.ig_links import post_link
    from services.ig_notes import youtube_copy

    carousel = ig_carousel.save(db, slides, hook, {"spotlight": KEY}, "ig-spotlight")
    n = len(slides)
    fact = {"kind": "spotlight", "title": hook, "hook": hook, "subject": HP, "subject_role": "allrounder",
            "carousel_id": carousel["id"], "slides": n, "render": True, "post_time": "6 pm"}
    fact["x"] = thread(b, post_link(fact))
    fact["youtube"] = youtube_copy(fact, caption, hook)
    ist = timezone(timedelta(hours=5, minutes=30))
    today = datetime.now(ist).date()
    post = {"key": KEY, "pillar": "reactive", "fact": fact, "snapshot_id": carousel["id"], "warnings": [],
            "players": [HP], "caption": caption}
    with engine.begin() as conn:
        ig_backlog.upsert_pack(conn, post, today, source="hand", post_by=datetime.combine(today, time.max, tzinfo=ist))
    print(f"queued ig:{KEY} for {today} · carousel {carousel['id']} ({n} slides)")
    r = ig_slides.render(carousel["id"], n, args.base)
    print(f"rendered {len(r['ok'])}/{n}" + (f", failed {r['failed']}" if r["failed"] else "") + f"; layout {r.get('layout') or 'clean'}")
    # Reels are always voiced (the user's rule): the hand script replaces whatever the render stored.
    env = {**os.environ, "REEL_V2": "1", "REEL_AB": "0"}
    done = subprocess.run([sys.executable, str(ROOT / "scripts/make_reel_v2.py"), "--key", f"ig:{KEY}", "--beats", "1,2,4,5,6",
                           "--script", str(HERE / "reel.json"), "--close", "Who's the next Hardik?", "--base", args.base,
                           "--store"], env=env, capture_output=True, text=True)
    ok = "stored as the post's Reel" in done.stdout
    print("voiced Reel:", "stored" if ok else f"FAILED\n{done.stderr[-800:]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
