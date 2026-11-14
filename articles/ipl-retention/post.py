"""
IPL 2027 retention series (RETENTION_SERIES_PLAN.md): one franchise a day, one format. Every number is IPL 2025-26 (since
the 2025 mega auction), counting a player's record at any side, from the query builder; prices are the 2026 squad's
(data/auction_raw/ipl/2026, Cricbuzz), adjusted for this window's trades.

    python articles/ipl-retention/post.py --team CSK              # dry run
    python articles/ipl-retention/post.py --team CSK --write [--base http://localhost:3000]
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


from services.squad_view import (  # noqa: E402  the squad's numbers and cards, shared with the team page
    SITE, START, END, TEMPLATE_START, IPL, PALETTE, MIN_BAT, MIN_BOWL, MIN_CELL, TEAMS, called, BG, contrast, readable_colour, sg, crore, card, q, numbers, build, SAY, gap_text,
)



# From CSK (13 Nov 2026) the value slide makes way for "who fills the gaps" (the team page's fits card, services/fit.py):
# what fits each gap, and who is actually available today. Teams posted before then kept the value slide.
FITS_FROM = {"CSK", "RCB", "KKR", "MI"}
UNIT = {"strike_rate": ("{:.0f}", "SR"), "wickets_per_24": ("{:.2f}", "wkts/4 ov"), "economy": ("{:.2f}", "an over"),
        "average": ("{:.1f}", "avg")}
SHORT_LABEL = {"finishers": "5-7 finishers", "pp_pace": "Powerplay pace", "death_pace": "Death pace", "openers": "Openers",
               "top": "No. 3-4", "mid_spin": "Middle-overs spin"}


def fits_card(db, b):
    """Each template gap (depth aside, three at most): the squad's number against playoff sides', two proven holders
    elsewhere as the profile ("like ..."), and who is available today: unsold at the last auction (released players
    join on 17 Nov) on IPL numbers where they have enough, else on every T20 we hold, unadjusted and labelled so."""
    from services import xi_engine as x
    from services.fit import fits

    gaps = [g for g in b["gaps"] if g["key"] != "depth"][:3]
    if not gaps:
        return None, []
    found = fits(db, b["code"], gaps)
    overseas = {p["name"]: p["overseas"] for p in x.payload(db, b["code"])["pool"]}
    status = {g["key"]: g["status"] for g in gaps}
    rows = []
    for f in found:
        fmt, unit = UNIT[f["measure"]]
        v = lambda n: fmt.format(n)  # noqa: E731
        opts = ([{"name": o["name"], "value": f"{v(o['value'])}", "overseas": overseas.get(o["name"], False), "source": "IPL"}
                 for o in f["free"][:2]]
                + [{"name": o["name"], "value": f"{v(o['value'])}", "overseas": overseas.get(o["name"], False),
                    "source": "all T20s"} for o in f["outside"]
                   # only those who'd lift the squad's number (Bracewell's 144 matched CSK's 144: 13 Nov 2026)
                   if (float(v(o["value"])) < float(v(f["squad_value"])) if f["lower_is_better"]
                       else float(v(o["value"])) > float(v(f["squad_value"])))])[:2]
        rows.append({"key": f["key"], "label": SHORT_LABEL.get(f["key"], f["label"]), "status": status[f["key"]],
                     "now": f"{v(f['squad_value'])} {unit}", "playoff": v(f["playoff_level"]),
                     "like": [{"name": called(e["name"]), "value": v(e["value"])} for e in f["examples"]], "options": opts})
    T = TEAMS[b["code"]]
    n_os = sum(1 for r in rows for o in r["options"] if o["overseas"])
    n_opt = sum(len(r["options"]) for r in rows)
    title = (f"Who fills {T['short']}'s gaps? All {n_opt} available today are overseas" if n_os == n_opt else
             f"Who fills {T['short']}'s gaps? {n_os} of the {n_opt} available today are overseas" if n_os else f"Who fills {T['short']}'s gaps? The best available today")
    c = card("fits", "gap_fits", title,
             {"rows": rows, "note": "Available: unsold in 2026 · released players join 17 Nov"},
             "Fits: IPL 2024-26 at any side · all T20s: unadjusted, since 2024", kicker="Who fills the gaps")
    return c, rows


def bowling_hook(b):
    """The only bowler above par, as a sentence (TEAMS "hook": "bowling"); None unless the bowling slide says so."""
    if TEAMS[b["code"]].get("hook") != "bowling":
        return None
    c4 = next(c for c in b["cards"] if c["id"] == "bowling")
    if "is the only one of" not in c4["title"]:
        return None
    # Checked on every bowler, not just the slide's six (CSK: R Ghosh is +3 from 3 overs), so the claim carries a floor.
    bowled = [x for x in b["players"] if x.get("bowl_raa") is not None and (x["bowl_balls"] or 0) >= 60]
    p = max(bowled, key=lambda x: x["bowl_raa"])
    if p["bowl_raa"] <= 0 or any(x["bowl_raa"] > 0 for x in bowled if x is not p):
        return None
    return (f"{p['name']} saved {p['bowl_raa']:.0f} runs against par since the mega auction. Every other "
            f"{TEAMS[b['code']]['short']} bowler with 10+ overs is below it.")


def copy(b):
    T = TEAMS[b["code"]]
    u, g, big = b["under"], b["bargain"], b["big"]
    # The hook's player: the big price, or the big name where the big price's number rests on a small sample
    # (TEAMS "hook": "big"; LSG, 8 Nov 2026: Mayank Yadav's −0.60 came from 144 balls).
    h = big if T.get("hook") == "big" else u
    hook = (f"{h['name']}: {crore(h['price'])}, {sg(h['wpa'])} wins since the mega auction. "
            f"{g['name']}: {crore(g['price'])}, {sg(g['wpa'])}.")
    lead = (b.get("trade") or {}).get("lead")
    if lead:
        did = f"added {abs(lead['out_wpa']):.2f}" if lead["out_wpa"] > 0 else f"was down {abs(lead['out_wpa']):.2f}"
        hook = (f"{lead['out']} {did} wins for {T['short']} since the mega auction. "
                f"{lead['in']}, coming in: {sg(lead['in_wpa'])}.")
    hook = bowling_hook(b) or hook
    PH = {"powerplay": "powerplay", "middle": "middle overs", "death": "death"}
    tr = b.get("trade")
    def deal_text(d):
        when = f", {d['when']}" if d["when"] else ""
        verb = "agreed to trade" if "awaiting" in d["source"] else "traded"
        return (f"{T['short']} {verb} {' and '.join(d['outs'])} to {TEAMS[d['other']]['short']} for {' and '.join(d['ins'])} "
                f"({d['source']}{when})")
    news = (["News first: " + "; ".join(deal_text(d) for d in tr["deals"]) + ". In the IPL since 2025: "
             + "; ".join(tr["lines"]) + "."] if tr else []) + ([T["note"]] if T.get("note") else [])
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
        *([fits_text(b)] if b.get("fits") else []),
        "Wins added, runs above par and Impact: T20 Primer method. IPL 2025-26, counting each player's record at any side. "
        "Prices: 2026 squad (Cricbuzz). Ball-by-ball data: Himanish Ganjoo & TechRadar, Cricsheet.",
        "Who would you keep?",
        f"Free ball-by-ball cricket stats: link in bio.\n.\n#IPL2027 #IPLRetention {T['tag']} #IPL",
    ])
    return hook, caption


def fits_text(b):
    """The fits slide in words, for the caption."""
    parts = []
    for r in b["fits"]:
        like = " and ".join(e["name"] for e in r["like"])
        opts = ", ".join(f"{o['name']} ({o['value']}{', ' + o['source'] if o['source'] != 'IPL' else ''})" for o in r["options"])
        parts.append(f"{r['label']} ({r['now']}; playoff sides {r['playoff']}): think {like}. Available today: {opts or 'nobody yet'}")
    os_ = sum(1 for p in b["players"] if p.get("overseas"))
    return ("Who fills the gaps? " + ". ".join(parts) + ". \"All T20s\" numbers come from outside the IPL and aren't "
            "adjusted for the standard of the league. Released players join the pool on 17 November."
            + (f" {TEAMS[b['code']]['short']} also have {os_} overseas players for 8 spots." if os_ > 8 else ""))


def team_link(team):
    from urllib.parse import quote

    return f"https://hindsightcricket.com/team?team={quote(team)}"


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
    lead = (tr or {}).get("lead")
    opener = (f"{T['short']} have until 17 November to name who they keep for IPL 2027. {h['name']} cost {crore(h['price'])} "
              f"and added {sg(h['wpa'])} wins since the mega auction. The case, player by player 🧵")
    if bowling_hook(b):
        opener = (f"{T['short']} have until 17 November to name who they keep for IPL 2027. {bowling_hook(b)} "
                  "The case, player by player 🧵")
    if lead:
        did = f"added {abs(lead['out_wpa']):.2f}" if lead["out_wpa"] > 0 else f"was down {abs(lead['out_wpa']):.2f}"
        opener = (f"{T['short']} have agreed to trade {lead['out']} for {lead['in']} (awaiting BCCI ratification). Since the mega auction, {called(lead['out'])} {did} "
                  f"wins for them; {called(lead['in'])}: {sg(lead['in_wpa'])}. The retention case, player by player 🧵")
    texts = [
        (1, opener),
        (2, wins),
        (3, f"Batting by role, in runs above par per 100 balls: {bb['name']} the best at {sg(bb['bat_raa100'], 0)}, "
            f"{wb['name']} the furthest below at {sg(wb['bat_raa100'], 0)}."),
        (4, (f"Bowling by phase: {bc[0]} saves {bc[2]:.1f} runs every four overs {'at the death' if bc[1] == 'death' else 'in the ' + PH[bc[1]]}, "
             f"the most by anyone in any phase." if bc else "Bowling by phase: runs saved against par, every four overs.")),
        *([] if b.get("fits") else [(5, f"Price against wins added. The bargain: {g['name']}, {sg(g['wpa'])} for {crore(g['price'])}. "
            f"The big price: {u['name']}, {sg(u['wpa'])} for {crore(u['price'])}.")]),
        (6 - bool(b.get("fits")), f"Three calls: {big['name']} ({crore(big['price'])}, {sg(big['wpa'])} wins), {u['name']} ({crore(u['price'])}, "
            f"{sg(u['wpa'])}) and {g['name']} ({crore(g['price'])}, {sg(g['wpa'])}). The case for and against each."),
        (7 - bool(b.get("fits")), f"Against what playoff sides have had since 2023: {b['grade']['at_level']} of {b['grade']['of']} roles at their level."
            + (f" Furthest short: {gap_text(b['gaps'][0])}." if b["gaps"] else "")),
        *([(7, fits_tweet(b))] if b.get("fits") else []),
        (8, f"Who would you keep?\n\nEvery ball, free: {link}\nData: @himganj153 & @TechRadar9"),
    ]
    from services.ig_x import hand_thread

    return hand_thread(texts, copy(b)[1], list(dict.fromkeys([u["name"], g["name"], big["name"], top["name"], bb["name"],
                                                              wb["name"]] + ([bc[0]] if bc else [])
                                                             # The traded players too, so "Arshdeep Singh" is tagged as
                                                             # himself, not read as another Singh (PBKS, 10 Nov 2026).
                                                             + [n for d in (tr or {}).get("deals", []) for n in d["ins"] + d["outs"]])))


def fits_tweet(b):
    r = b["fits"][0]
    opts = ", ".join(f"{o['name']} {o['value']}" for o in r["options"][:3])
    n_os = sum(1 for x in b["fits"] for o in x["options"] if o["overseas"])
    n = sum(len(x["options"]) for x in b["fits"])
    t = (f"Who fills the gaps? {r['label']}: think {' and '.join(e['name'] for e in r['like'])}. Available today: {opts}."
         + (f" All {n} names across the gaps are overseas." if n_os == n else f" {n_os} of the {n} names across the gaps are overseas." if n_os else ""))
    return t if len(t) <= 250 else t.split(" Available today")[0] + f". Available today: {opts}."


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
    lead = (b.get("trade") or {}).get("lead")
    hook = (f"{lead['out']} {spoken(lead['out_wpa'])} for {T['short']} since the mega auction. {lead['in']}, who replaces him, "
            f"{spoken(lead['in_wpa'])}." if lead else f"{h['name']} cost {T['short']} {say(h)}. Since the mega auction, he {spoken(h['wpa'])}.")
    hook = bowling_hook(b) or hook
    if b.get("fits"):
        r = b["fits"][0]
        o = r["options"][0] if r["options"] else None
        return {"hook": hook,
                "lines": ["Here's the whole squad, with this window's trades in, by wins added since 2025." if b.get("trade")
                          else "Here's the whole squad, by wins added since 2025.",
                          f"Most in the squad: {b['top']['name']}, who {spoken(b['top']['wpa'])}.",
                          # The big name already opened the Reel when he's the hook (RCB, 14 Nov 2026): say the big price.
                          (f"{u['name']}, the big price, {spoken(u['wpa'])}, from a small sample. " if h is big
                           else f"{big['name']}, the big name, {spoken(big['wpa'])}. ")
                          + f"{g['name']} cost {say(g)} and {spoken(g['wpa'])}.",
                          (f"Against playoff sides, the biggest gap: {SAY[b['gaps'][0]['key']]}." if b["gaps"]
                           else "Against playoff sides, every role is at their level."),
                          (f"Who's available? {o['name']}, among others{', on numbers from outside the IPL' if o['source'] != 'IPL' else ''}."
                           if o else "And nobody's available to fill it yet.")]}
    return {"hook": hook,
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
    if args.team in FITS_FROM:
        fc, rows = fits_card(db, b)
        if fc:
            b["fits"] = rows
            b["cards"] = [c for c in b["cards"] if c["id"] != "value"] + [fc]
    hook, caption = copy(b)
    slides = slides_of(b, hook)
    print("HOOK:", hook, f"({len(hook)})")
    for n_, s in enumerate(slides, 1):
        c = s.get("card") or (s.get("hero") or {}).get("card") or {}
        print(f"  {n_}. [{c.get('visual') or s['type']}] {c.get('title') or s.get('heading')} ({len(c.get('title') or '')})")
    problems, hp = findings(slides, "spotlight"), hook_problem(hook)
    print("lint:", problems or "clean", "| hook:", hp or "ok")
    print(caption)
    th = thread(b, team_link(b["team"]))
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
    # The last tweet links to the team's page (it unfurls with the team preview card, api/og.mjs), not the post.
    fact["x"] = thread(b, team_link(b["team"]))
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
