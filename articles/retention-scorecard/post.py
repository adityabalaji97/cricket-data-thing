"""
Retention day, the morning after (18 Nov 2026): all ten 2027 squads against the winners' template, role by role, with the
purse each side takes to the 16 Dec auction. Not "who won last year" (wins added summed over a squad is last season's
table again): the grade asks whether the squad is built like a playoff side, on each player's IPL record at any side.

Squads: the official retained lists (data/auction_raw/ipl/2027/retained_official.csv, trades included). Purses: the
post-retention figures (data/auction_raw/ipl/2027/purses.csv). Grade: services/squad_grade.py over IPL 2024-26, the same
window and benchmarks as the retention posts' template slide. Labels as cards say them: playoff level, close, behind.

    DATABASE_URL=postgresql://localhost:5432/hindsight_local python articles/retention-scorecard/post.py   # dry run
    python articles/retention-scorecard/post.py --write --base http://localhost:3000                      # queue, render, Reel
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

KEY = "retention-scorecard-2026-11-18"
RAW = ROOT / "data/auction_raw/ipl/2027"
START, END = date(2024, 1, 1), date(2026, 12, 31)
SAMPLE = "IPL 2024-26 at any side · v playoff sides 2023-26 · squads as retained 17 Nov"
COLS = [("openers", "Open"), ("top", "3-4"), ("finishers", "5-7"), ("pp_pace", "PP"), ("mid_spin", "Spin"),
        ("death_pace", "Death"), ("depth", "Depth")]
WORD = {"playoff level": "playoff level", "short": "close", "gap": "behind"}
FMT = {"average": "{:.0f}", "strike_rate": "{:.0f}", "wickets_per_24": "{:.2f}", "economy": "{:.1f}", "regular_bowlers": "{:.0f}"}
UNIT = {"average": "avg", "strike_rate": "SR", "wickets_per_24": "wkts/4 ov", "economy": "an over", "regular_bowlers": "bowlers"}
THREAD_PLAYERS = ["Sanju Samson", "Ruturaj Gaikwad", "Rishabh Pant"]


def card(cid, visual, title, payload, sample, kicker=None):
    assert len(title) <= 80, (len(title), title)
    c = {"id": cid, "visual": visual, "title": title, "help": "", "sample": sample, "payload": payload}
    if kicker:
        c["kicker"] = kicker
    return c


def short(n):
    return n if len(n.split()) < 2 or n.split()[0].isupper() else f"{n.split()[0][0]} {n.split()[-1]}"


def crore(v):
    return f"₹{v:.2f}".rstrip("0").rstrip(".") + " cr"


# ---- data ---------------------------------------------------------------------------------------------------------

def known_names(db):
    from sqlalchemy import text

    return {r[0] for r in db.execute(text("""
        SELECT DISTINCT bat FROM delivery_details WHERE p_match IN (SELECT id FROM matches
          WHERE competition IN ('IPL', 'Indian Premier League') AND date >= :a)
        UNION SELECT DISTINCT bowl FROM delivery_details WHERE p_match IN (SELECT id FROM matches
          WHERE competition IN ('IPL', 'Indian Premier League') AND date >= :a)"""), {"a": START}) if r[0]}


def matcher(names):
    """The ball-by-ball name for a list's name: exact, then surname + first name (or an initial), then a suffix
    ('Ravisrinivasan Sai Kishore' -> 'Sai Kishore'). None when it's ambiguous or he has no IPL record in the window."""
    def match(*cands):
        for c in cands:
            if c in names:
                return c
        for c in cands:
            p = c.replace(".", " ").split()
            tests = [
                lambda x: x.split()[-1].lower() == p[-1].lower() and x[0].lower() == c[0].lower()
                and (len(x.split()[0]) <= 2 or len(p[0]) <= 2 or x.split()[0].lower() == p[0].lower()),
                lambda x: x.split()[0].lower() == p[0].lower() and x.split()[-1][:4].lower() == p[-1][:4].lower(),
                lambda x: len(x.split()) >= 2 and c.lower().endswith(x.lower()),
            ]
            for t in tests:
                hits = [x for x in names if t(x)]
                if len(hits) == 1:
                    return hits[0]
        return None
    return match


def squads(db):
    match = matcher(known_names(db))
    out, missing = {}, []
    for r in csv.DictReader(open(RAW / "retained_official.csv")):
        m = match(r["name_2026"] or r["player"], r["player"])
        (out.setdefault(r["team"], []).append(m) if m else missing.append((r["team"], r["player"])))
    return out, missing


def purses():
    return {r["team"]: {"purse": float(r["purse_cr"]), "slots": int(r["slots"]), "overseas": int(r["overseas_slots"])}
            for r in csv.DictReader(open(RAW / "purses.csv"))}


def grades(db, sq):
    from services.squad_grade import grade, load_template, squad_players

    tmpl = load_template("IPL")
    return {t: grade(squad_players(db, "IPL", pl, START, END), tmpl["benchmarks"], tmpl["weights"]) for t, pl in sq.items()}


def wins_2026(db):
    from sqlalchemy import text
    from services.squad_view import code_for

    rows = db.execute(text("""SELECT winner, COUNT(*) FROM matches WHERE competition IN ('IPL', 'Indian Premier League')
        AND date BETWEEN '2026-03-01' AND '2026-06-30' AND winner IS NOT NULL GROUP BY 1""")).all()
    return {code_for(w): n for w, n in rows}


# ---- cards --------------------------------------------------------------------------------------------------------

def value_text(r):
    if r["value"] is None:
        return "–"
    return FMT[r["measure"]].format(r["value"])


def order(g):
    return sorted(g, key=lambda t: (-g[t]["at_level"], -g[t]["fit"]))


def league_grid(g, p):
    rows = []
    for t in order(g):
        by = {r["key"]: r for r in g[t]["roles"]}
        rows.append({"name": t, "sub": f"{g[t]['at_level']}/7 · {crore(p[t]['purse'])}",
                     "cells": [{"value": 0, "text": value_text(by[k]), "status": by[k]["status"]} for k, _ in COLS]})
    return card("league", "grid_heat", "All ten squads against playoff sides, role by role",
                {"cols": [c for _, c in COLS], "rows": rows, "format": "int", "legend": ["playoff level", "close", "behind"],
                 "dense": True, "name_fr": 1.7},
                SAMPLE + " · cell: the role's number", kicker="Built like a playoff side?")


def board(team, g, colour, title, kicker):
    rows = []
    for r in g["roles"]:
        held = ("nobody in the squad has done it" if not r["holders"] else ", ".join(short(h) for h in r["holders"][:3]))
        rows.append({"label": r["label"], "holders": held, "place": round(r["place"]), "playoff_place": round(r["playoff_place"]),
                     "status": r["status"],
                     "value_text": f"{value_text(r)} {UNIT[r['measure']]} · playoff {FMT[r['measure']].format(r['playoff_level'])}"})
    return card(f"board-{team.lower()}", "template_board", title,
                {"colour": colour, "rows": rows, "scale_label": "Place among IPL sides, 2023-26"}, SAMPLE, kicker=kicker)


def money_card(g, p):
    pts = [{"name": t, "short": t, "x": p[t]["purse"], "y": g[t]["at_level"], "label": t,
            "highlight": t in ("DC", "KKR", "LSG")} for t in g]
    return card("money", "scatter_plus", "Most money, fewest roles at playoff level: Delhi, Kolkata, Lucknow",
                {"x": {"label": "Purse left (₹ cr)", "format": "dec1", "higher_better": True},
                 "y": {"label": "Roles at playoff level", "format": "int", "higher_better": True},
                 "points": pts, "box": None},
                "Purses after retentions, 17 Nov · roles of 7 at playoff level, IPL 2024-26", kicker="The money and the holes")


def finishers_card(g, bench_po):
    rows = []
    for t in order(g):
        r = next(x for x in g[t]["roles"] if x["key"] == "finishers")
        if r["value"] is not None:
            rows.append({"name": f"{t} · SR {r['value']:.0f}", "value": round(r["value"] - bench_po, 1)})
    rows.sort(key=lambda x: -x["value"])
    behind = sum(1 for t in g if next(x for x in g[t]["roles"] if x["key"] == "finishers")["status"] == "gap")
    return card("finishers", "metric_bars", f"Batting 5-7: {behind} of 10 squads are behind playoff sides",
                {"metric": {"label": f"Strike rate v playoff sides ({bench_po:.0f})", "format": "signed1", "signed": True},
                 "rows": rows}, "IPL 2024-26 at any side · each squad's busiest 5-7s", kicker="The league's shared hole"), behind


# ---- the post -----------------------------------------------------------------------------------------------------

def build(db):
    from services.squad_view import PALETTE, TEAMS

    sq, missing = squads(db)
    g, p, w = grades(db, sq), purses(), wins_2026(db)
    rank = order(g)
    po_fin = next(r for r in g["RCB"]["roles"] if r["key"] == "finishers")["playoff_level"]
    colour = lambda t: (PALETTE.get(TEAMS[t]["name"]) or {}).get("primary", "#b6f24a")  # noqa: E731
    csk, dc, rcb = g["CSK"], g["DC"], g["RCB"]
    worst = lambda gg: next((r for r in sorted(gg["roles"], key=lambda r: (r["status"] != "gap", -r["weight"]))  # noqa: E731
                             if r["status"] != "playoff level"), None)
    cards = [
        league_grid(g, p),
        board("CSK", csk, colour("CSK"),
              f"Chennai won {w.get('CSK', 0)} games last season. Now: {csk['at_level']} of 7 roles at playoff level",
              "Dhoni's gone. The rebuild isn't"),
        board("DC", dc, colour("DC"),
              f"Delhi: {dc['at_level']} of 7 at playoff level, {crore(p['DC']['purse'])} for {p['DC']['slots']} slots",
              "The auction's biggest job"),
        board("RCB", rcb, colour("RCB"),
              f"The champions, {rcb['at_level']} of 7: {worst(rcb)['label'].lower()} is behind",
              f"{crore(p['RCB']['purse'])} to fix it"),
        money_card(g, p),
    ]
    fc, behind = finishers_card(g, po_fin)
    cards.append(fc)
    return {"g": g, "p": p, "w": w, "rank": rank, "cards": cards, "missing": missing, "behind": behind, "po_fin": po_fin,
            "csk_place": rank.index("CSK") + 1, "worst_rcb": worst(rcb)}


def holders(g, key):
    return next(r for r in g["roles"] if r["key"] == key)["holders"]


def copy(b):
    g, p, w = b["g"], b["p"], b["w"]
    csk, dc, rcb = g["CSK"], g["DC"], g["RCB"]
    op = holders(csk, "openers")
    more = [t for t in g if g[t]["at_level"] > csk["at_level"]]
    hook = (f"Dhoni's gone. Chennai's squad has {csk['at_level']} of 7 roles at playoff level. "
            + (f"Only {' and '.join(more)} {'have' if len(more) > 1 else 'has'} more." if len(more) <= 2 else ""))
    caption = "\n\n".join([
        "Retention day is done. We graded all ten 2027 squads the way playoff sides are built: seven roles, each "
        "player's IPL record wherever he played it (2024-26), set against what playoff sides have had since 2023.",
        "Green is playoff level. Amber is close: a good season from the players in it gets them there. Red is behind: "
        "below what the sides who missed out had.",
        f"Chennai won {w.get('CSK', 0)} games last season and lost Dhoni. The squad they've kept and traded for is "
        f"{csk['at_level']} of 7: {' and '.join(op)} open at playoff level, and so does the spin. The hole is batting 5-7.",
        f"Delhi have the auction's biggest job: {dc['at_level']} of 7 at playoff level, {crore(p['DC']['purse'])} for "
        f"{p['DC']['slots']} slots.",
        f"The champions are {rcb['at_level']} of 7, with {b['worst_rcb']['label'].lower()} behind and "
        f"{crore(p['RCB']['purse'])} to fix it.",
        f"And the league's shared hole: {b['behind']} of 10 squads are behind playoff sides at 5-7.",
        "A guide, not a forecast: it says how a squad is built, not where it finishes. Players without an IPL game since "
        "2024 aren't counted yet.",
        "Which role does your team buy first?",
        "Free ball-by-ball cricket stats: link in bio.\n.\n#IPL2027 #IPLRetention #CSK #RCB #DelhiCapitals",
    ])
    return hook, caption


def thread(b, link):
    from services.ig_x import hand_thread

    g, p = b["g"], b["p"]
    grid = b["cards"][0]["payload"]["rows"]
    texts = [
        copy(b)[0] + " All ten squads, role by role 🧵",
        "Green: playoff level. Amber: close (a good season gets them there). Red: behind. "
        "Each player's IPL record since 2024, wherever he played.",
        f"Chennai: Samson and Gaikwad open at playoff level, Noor and Hosein spin at it. The hole is 5-7.",
        f"Delhi: {g['DC']['at_level']} of 7 at playoff level, {crore(p['DC']['purse'])} for {p['DC']['slots']} slots. "
        "The biggest job on 16 Dec.",
        f"RCB, the champions: {g['RCB']['at_level']} of 7. {b['worst_rcb']['label']} is behind, {crore(p['RCB']['purse'])} to fix it.",
        f"Most money, most holes: Lucknow {crore(p['LSG']['purse'])}, Kolkata {crore(p['KKR']['purse'])}, Delhi "
        f"{crore(p['DC']['purse'])}.",
        f"{b['behind']} of 10 squads are behind playoff sides at 5-7. Finishers are the auction's shortage.",
        f"Which role does your team buy first?\n\nEvery squad, free: {link}\nData: @himganj153 & @TechRadar9",
    ]
    return hand_thread(texts, copy(b)[1], THREAD_PLAYERS)


def reel_script(b):
    g, p, w = b["g"], b["p"], b["w"]
    return {"hook": copy(b)[0],
            "lines": [f"They won {w.get('CSK', 0)} games last season. Samson and Gaikwad now open at playoff level.",
                      f"Delhi are {g['DC']['at_level']} of 7, with {p['DC']['purse']:.1f} crore for {p['DC']['slots']} players.",
                      f"The champions RCB are {g['RCB']['at_level']} of 7, but {b['worst_rcb']['label'].lower()} is behind.",
                      f"And {b['behind']} of 10 squads are behind at five to seven. Finishers are the shortage."]}


def slides_of(b, hook):
    lead = b["cards"][0]
    cover = {"type": "hook", "text": hook, "cover": "hero",
             "hero": {"kind": "visual", "visual": lead["visual"], "payload": lead["payload"], "label": "", "card": lead}}
    return ([cover] + [{"type": "card", "card": c} for c in b["cards"][1:]]
            + [{"type": "end", "heading": "Which role does your team buy first?",
                "body": "Every squad's grade, role by role, and who in the pool fits: free on Hindsight, team pages and "
                        "Fix my team."}])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--base", default="https://hindsightcricket.com")
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
    for t in b["rank"]:
        print(f"  {t:5} {b['g'][t]['at_level']}/7  " + " ".join(f"{k}:{WORD[r['status']]}" for k, r in
                                                            zip([c[0] for c in COLS], b["g"][t]["roles"])))
    print("not counted (no IPL game 2024-26 or ambiguous):", b["missing"])
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
    fact = {"kind": "spotlight", "title": hook, "hook": hook, "subject": "Sanju Samson", "subject_role": "batter",
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
    done = subprocess.run([sys.executable, str(ROOT / "scripts/make_reel_v2.py"), "--key", f"ig:{KEY}", "--beats", "1,2,3,4,6",
                           "--script", str(HERE / "reel.json"), "--close", "Which role does your team buy first?",
                           "--base", args.base, "--store"], env=env, capture_output=True, text=True)
    ok = "stored as the post's Reel" in done.stdout
    print("voiced Reel:", "stored" if ok else f"FAILED\n{done.stdout[-1500:]}\n{done.stderr[-1500:]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
