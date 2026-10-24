"""
Tilak Varma, 24 Oct 2026: the finisher streak being shared on X ("not out in 26 T20 chases, won all 26"), tested on
the T20s we have ball by ball, then why it works (pace at the death) and where it doesn't (spin in the middle overs),
and what that says about where he bats. T20Is and the IPL.

Slides: cover (the streak, with not out v out as its chart); the deeper cut (how rare a perfect record is); India's
batters against pace at the death; the IPL field on both (scatter); spin by type; batting position; the case both
ways (control %); end. Today's 51* off 26 isn't in our data yet: it's credited text in the caption, never charted.

    python articles/tilak-chases/post.py                      # dry run: cards, titles, lint; nothing saved
    python articles/tilak-chases/post.py --local              # save to the local database (DATABASE_URL), to render
    python articles/tilak-chases/post.py --write              # queue for today, render, voiced Reel from reel.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

T = "Tilak Varma"
KEY = "spotlight-tilak-chases-2026-10-24"
SITE = "https://hindsightcricket.com"
SINCE = date(2023, 1, 1)
NOT_OUT_MIN = 15  # not-out chases for the rarity comparison
MIDDLE_SPIN = dict(bowl_kind=["spin bowler"], over_min=6, over_max=14)
DEATH_PACE = dict(bowl_kind=["pace bowler"], over_min=15)
CREDIT = "Ball-by-ball data: Himanish Ganjoo & TechRadar, Cricsheet."


def sg(v, d=1):
    """A signed number as the cards print it: +34.2, −25.6 (a minus sign, not a hyphen)."""
    return f"{v:+.{d}f}".replace("-", "−")


def card(cid, visual, title, payload, sample, help_=""):
    return {"id": cid, "visual": visual, "title": title, "help": help_, "sample": sample, "payload": payload}


def q(db, scope, **kw):
    from services.query_builder_v2 import run_deliveries_query

    base = dict(fmt="T20", gender="male", metrics_perspective="batting", limit=10000)
    base.update({"include_international": True} if scope == "T20I" else {"include_international": False, "leagues": ["IPL"]})
    return run_deliveries_query(db, **base, **kw)["data"]


def one(db, scope, **kw):
    rows = q(db, scope, group_by=["format"], **kw)
    return rows[0] if rows else None


# ---- the streak ---------------------------------------------------------------------------------------------------

def chases(db):
    """Every men's T20 chase each batter batted in (a ball faced), with whether he was out and whether his side won.
    Out: a ball where he's the dismissed batter (delivery_details.p_out is on every ball; `out` marks the wicket)."""
    from sqlalchemy import text

    return [dict(r) for r in db.execute(text("""
        SELECT pi.display_name AS name, b.match_id, m.date, m.competition, b.batting_team, b.runs, b.balls_faced,
               (m.winner = b.batting_team) AS won,
               NOT EXISTS (SELECT 1 FROM delivery_details d WHERE d.p_match = b.match_id::text AND d.inns = 2
                           AND d.p_out = b.pid AND d.out::text = 'true') AS not_out
        FROM batting_stats b JOIN matches m ON m.id::text = b.match_id::text
        JOIN player_identity pi ON pi.pid = b.pid
        WHERE b.innings = 2 AND m.format = 'T20' AND m.gender = 'male' AND m.winner IS NOT NULL
          AND b.balls_faced > 0 AND b.pid IS NOT NULL
    """)).mappings()]


def streak_cards(rows):
    mine = [r for r in rows if r["name"] == T]
    no = [r for r in mine if r["not_out"]]
    out = [r for r in mine if not r["not_out"]]
    won_no, won_out = sum(r["won"] for r in no), sum(r["won"] for r in out)
    assert won_no == len(no), "the streak has a loss in it now"
    pct = lambda w, n: round(100 * w / n, 1)  # noqa: E731
    lead = card("not-out-v-out", "share_bars",
                f"Not out: won {won_no} of {len(no)}. Out: won {won_out} of {len(out)}",
                {"groups": [{"key": "won", "label": "Won"}, {"key": "lost", "label": "Lost"}], "format": "pct0",
                 "rows": [{"name": "Not out", "detail": f"{len(no)} chases",
                           "segments": [{"key": "won", "value": pct(won_no, len(no))}, {"key": "lost", "value": pct(len(no) - won_no, len(no))}]},
                          {"name": "Out", "detail": f"{len(out)} chases",
                           "segments": [{"key": "won", "value": pct(won_out, len(out))}, {"key": "lost", "value": pct(len(out) - won_out, len(out))}]}]},
                f"{T}'s chases with a result · every men's T20 we have ball by ball",
                "A chase he batted in (faced a ball); not out: never dismissed in it. Domestic T20s without ball-by-ball "
                "data aren't counted.")

    # How rare: every batter with NOT_OUT_MIN+ not-out chases; the perfect records, Kohli for reference.
    by = {}
    for r in rows:
        if r["not_out"]:
            b = by.setdefault(r["name"], [0, 0])
            b[0] += 1
            b[1] += r["won"]
    field = {n: v for n, v in by.items() if v[0] >= NOT_OUT_MIN}
    pooled = round(100 * sum(v[1] for v in field.values()) / sum(v[0] for v in field.values()))
    perfect = sorted((n for n, v in field.items() if v[0] == v[1]), key=lambda n: -field[n][0])
    assert T in perfect
    shown = perfect + (["Virat Kohli"] if "Virat Kohli" in field and "Virat Kohli" not in perfect else [])
    rare = card("perfect-records", "metric_bars",
                f"{T}: one of {len(perfect)} batters with {NOT_OUT_MIN}+ not-out chases never to lose one",
                {"metric": {"label": "Not-out chases", "format": "int"}, "label_width": 120,
                 "rows": [{"name": n, "value": field[n][0], "highlight": n == T,
                           "detail": f"won {field[n][1]} of {field[n][0]}"} for n in shown]},
                f"{len(field)} batters with {NOT_OUT_MIN}+ not-out chases · every men's T20 we have ball by ball",
                f"Across all {len(field)}, sides won {pooled}% of the chases their batter finished not out.")
    rare["kicker"] = "The deeper cut"
    return lead, rare, {"no": no, "out": out, "won_out": won_out, "perfect": perfect, "field": len(field),
                        "pooled": pooled, "kohli": field.get("Virat Kohli")}


# ---- the batting ----------------------------------------------------------------------------------------------------

def india_death_pace(db):
    rows = q(db, "T20I", group_by=["batter"], batting_teams=["India"], start_date=SINCE, min_balls=100, **DEATH_PACE)
    rows = sorted(rows, key=lambda r: -r["impact_per_100"])
    assert rows[0]["batter"] == T, "no longer India's best"
    me = rows[0]
    return card("india-death-pace", "metric_bars",
                f"{T}: {sg(me['impact_per_100'])} Impact per 100 balls against pace at the death, India's best",
                {"metric": {"label": "Impact per 100 balls", "format": "signed1", "signed": True},
                 "rows": [{"name": r["batter"], "value": round(r["impact_per_100"], 1), "highlight": r["batter"] == T,
                           "detail": f"scores at {r['strike_rate']:.0f}"} for r in rows]},
                "India batters, 100+ balls v pace at the death · T20Is since 2023",
                "Impact: runs added to India's projected total, ball by ball (T20 Primer method)."), me


def ipl_scatter(db):
    death = {r["batter"]: r for r in q(db, "IPL", group_by=["batter"], start_date=SINCE, min_balls=100, **DEATH_PACE)}
    spin = {r["batter"]: r for r in q(db, "IPL", group_by=["batter"], start_date=SINCE, min_balls=150, **MIDDLE_SPIN)}
    rank = lambda d: {n: i + 1 for i, n in enumerate(sorted(d, key=lambda n: -d[n]["impact_per_100"]))}  # noqa: E731
    rd, rs = rank(death), rank(spin)
    both = sorted(set(death) & set(spin))
    # Tilak, and anyone better than him on both, named (numbered, with a key under the chart).
    mx, my = spin[T]["impact_per_100"], death[T]["impact_per_100"]
    better = sorted((n for n in both if n != T and spin[n]["impact_per_100"] > mx and death[n]["impact_per_100"] > my),
                    key=lambda n: -death[n]["impact_per_100"])
    names = {T: (1, "Tilak")} | {n: (i + 2, n.split()[-1]) for i, n in enumerate(better)}
    points = [{"name": n, "x": round(spin[n]["impact_per_100"], 1), "y": round(death[n]["impact_per_100"], 1),
               **({"highlight": True} if n == T else {}),
               **({"label": names[n][0], "short": names[n][1]} if n in names else {})} for n in both]
    c = card("ipl-both", "scatter_plus",
             f"IPL: {rd[T]}{_th(rd[T])} of {len(death)} against pace at the death; "
             f"{rs[T]}{_th(rs[T])} of {len(spin)} against spin, middle overs",
             {"points": points, "box": True,
              "x": {"label": "v spin, middle overs", "format": "signed0", "higher_better": True},
              "y": {"label": "v pace at the death", "format": "signed0"}},
             f"{len(both)} batters with 100+ and 150+ balls · IPL since 2023",
             "Impact per 100 balls, each axis. Up: better against pace at the death; right: better against spin in "
             "the middle overs.")
    return c, {"rd": rd[T], "nd": len(death), "rs": rs[T], "ns": len(spin)}


def _th(n):
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


SPIN_TYPES = [("leg-spin", ["LB", "LBG"]), ("off-spin", ["OB"]), ("left-arm orthodox", ["SLA"])]


def spin_types(db):
    rows, raw = [], {}
    for label, styles in SPIN_TYPES:
        a = one(db, "T20I", batters=[T], bowl_style=styles, over_min=6, over_max=14)
        b = one(db, "IPL", batters=[T], bowl_style=styles, over_min=6, over_max=14)
        raw[label] = (a, b)
        rows.append({"label": label.capitalize(), "a": round(a["impact_per_100"], 1), "b": round(b["impact_per_100"], 1),
                     "highlight": label == "leg-spin"})
    worst = min(raw, key=lambda k: raw[k][0]["impact_per_100"])
    assert worst == "leg-spin"
    lt = raw["leg-spin"][0]
    return card("spin-types", "pair_dumbbell",
                f"Leg-spin is the one he hasn't solved: {sg(lt['impact_per_100'])} Impact per 100 balls in T20Is",
                {"series": ["T20Is", "IPL"], "format": "signed1", "values": True, "full_labels": True, "no_diff": True,
                 "rows": rows},
                f"{T} v spin in the middle overs · T20Is and IPL",
                "Impact per 100 balls. Leg-spin includes googly bowlers."), raw


def positions(db):
    rows, raw = [], {}
    for pos in (3, 4, 5):
        a = next((r for r in q(db, "T20I", batters=[T], group_by=["batting_position"]) if r["batting_position"] == pos), None)
        b = next((r for r in q(db, "IPL", batters=[T], group_by=["batting_position"]) if r["batting_position"] == pos), None)
        raw[pos] = (a, b)
        rows.append({"label": f"No. {pos}", "a": round(a["impact_per_100"], 1), "b": round(b["impact_per_100"], 1),
                     "highlight": pos == 3})
    a3, a4, a5 = (raw[p][0]["impact_per_100"] for p in (3, 4, 5))
    small = min(r["balls"] for pair in raw.values() for r in pair) < 100  # IPL No. 3: 78 balls
    c = card("positions", "pair_dumbbell",
                f"At No. 3: {sg(a3)} Impact per 100 balls in T20Is. At 4 and 5: {sg(a4)} and {sg(a5)}",
                {"series": ["T20Is", "IPL"], "format": "signed1", "values": True, "full_labels": True, "no_diff": True,
                 "rows": rows},
                f"{T} by batting position · T20Is and IPL",
                "Impact per 100 balls. Positions with fewer than 100 balls in both aren't shown (No. 6: 90 in T20Is).")
    if small:
        c["small_sample"] = True
    return c, raw


def control(db):
    me_s, me_d = one(db, "T20I", batters=[T], **MIDDLE_SPIN), one(db, "T20I", batters=[T], **DEATH_PACE)
    f_s, f_d = one(db, "T20I", start_date=SINCE, **MIDDLE_SPIN), one(db, "T20I", start_date=SINCE, **DEATH_PACE)
    c = card("control", "deep_compare",
             f"Spin isn't beating him: {me_s['control_percentage']:.0f}% control in the middle overs "
             f"(average {f_s['control_percentage']:.0f}%)",
             {"metric": {"label": "control %", "format": "pct0", "signed": False}, "series": [T, "Average T20I batter"],
              "rows": [{"label": "Spin, middle overs", "subject": round(me_s["control_percentage"], 1),
                        "field": round(f_s["control_percentage"], 1), "highlight": True},
                       {"label": "Pace, death", "subject": round(me_d["control_percentage"], 1),
                        "field": round(f_d["control_percentage"], 1)}]},
             f"{T} v every batter · T20Is since Jan 2023",
             "Control %: balls he played in control (no miss, edge or mis-hit), from the ball-by-ball tracking.")
    return c, {"me_s": me_s, "me_d": me_d, "f_s": f_s, "f_d": f_d}


def build(db):
    lead, rare, st = streak_cards(chases(db))
    death, me_death = india_death_pace(db)
    scatter, ipl = ipl_scatter(db)
    spin, raw_spin = spin_types(db)
    pos, raw_pos = positions(db)
    ctrl, cn = control(db)
    return {"lead": lead, "cards": [rare, death, scatter, spin, pos, ctrl], "st": st, "me_death": me_death, "ipl": ipl,
            "spin": raw_spin, "pos": raw_pos, "ctrl": cn}


def copy(b):
    st, d, ipl, cn = b["st"], b["me_death"], b["ipl"], b["ctrl"]
    n, kohli = len(st["no"]), st["kohli"]
    t20i = sum(r["competition"] == "T20I" for r in st["no"])
    ipl_n = sum(r["competition"] in ("IPL", "Indian Premier League") for r in st["no"])
    leg, pos = b["spin"]["leg-spin"][0], b["pos"]
    hook = f"Tilak Varma has been not out in {n} T20 chases. His side won all {n}"
    caption = "\n\n".join([
        f"Tilak Varma has been not out in {n} T20 chases we have ball by ball ({t20i} T20Is, {ipl_n} in the IPL, "
        f"{n - t20i - ipl_n} more). His side won all {n}. When he was out, they won {st['won_out']} of {len(st['out'])}.",
        "Today's 51* off 26 in Christchurch (ESPNcricinfo) isn't in our data yet; the 26 being shared also counts domestic "
        "games we don't have ball by ball.",
        f"Of {st['field']} batters with {NOT_OUT_MIN}+ not-out chases, {len(st['perfect'])} have never lost one. Across "
        f"all {st['field']}, sides won {st['pooled']}% of the chases their batter finished." + (f" Virat Kohli: {kohli[1]} of {kohli[0]}." if kohli else ""),
        f"Why it works: against pace at the death he scores at {d['strike_rate']:.0f} in T20Is, {sg(d['impact_per_100'])} "
        f"Impact per 100 balls, India's best since 2023. IPL: {ipl['rd']}{_th(ipl['rd'])} of {ipl['nd']}.",
        f"The other side: against spin in the middle overs he's at par, and leg-spin is the hardest "
        f"({sg(leg['impact_per_100'])} per 100 balls in T20Is). He isn't beaten, though: in control on "
        f"{cn['me_s']['control_percentage']:.0f}% of those balls (average {cn['f_s']['control_percentage']:.0f}%).",
        f"Where he bats: at No. 3 {sg(pos[3][0]['impact_per_100'])} Impact per 100 balls in T20Is; at 4 and 5 "
        f"{sg(pos[4][0]['impact_per_100'])} and {sg(pos[5][0]['impact_per_100'])}. (IPL at No. 3 is only "
        f"{pos[3][1]['balls']} balls.)",
        "Impact: runs added to the team's projected total, ball by ball (T20 Primer method). " + CREDIT,
        "Where would you bat him?",
        "Free ball-by-ball cricket stats: link in bio.\n.\n#TilakVarma #NZvIND #TeamIndia #cricket #T20I",
    ])
    reply = (f"In the T20s we have ball by ball: not out in {n} chases ({t20i} T20Is, {ipl_n} IPL, {n - t20i - ipl_n} more), "
             f"won all {n}. Out: won {st['won_out']} of {len(st['out'])}. {len(st['perfect'])} of {st['field']} batters "
             f"with {NOT_OUT_MIN}+ not-out chases never lost one; Kohli {kohli[1]}/{kohli[0]}. Today's 51* not in yet.\n"
             "Data: Hindsight · @himganj153 & @TechRadar9, Cricsheet")
    return hook, caption, reply


def slides_of(b, hook):
    from services.ig_cover import hero_from

    cover = {"type": "hook", "text": hook, "kicker": "Not out in the chase", "cover": "hero",
             "hero": {**hero_from(b["lead"]), "card": b["lead"]}}
    return ([cover] + [{"type": "card", "card": c, "teams": ["India"]} for c in b["cards"]]
            + [{"type": "end", "heading": "Every innings, ball by ball", "body": "Impact and control for every T20I and IPL batter: free on Hindsight."}])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--local", action="store_true", help="save the carousel to the database in DATABASE_URL only")
    parser.add_argument("--base", default=SITE)
    args = parser.parse_args()
    if args.write:
        assert "localhost" not in os.environ.get("DATABASE_URL", ""), "--write is production: leave DATABASE_URL unset"
    from database import get_session
    from services.social_rules import findings

    data_db = next(get_session())
    b = build(data_db)
    hook, caption, reply = copy(b)
    slides = slides_of(b, hook)
    print("HOOK:", hook, f"({len(hook)})")
    for i, s in enumerate(slides, 1):
        c = s.get("card") or {}
        print(f"  {i}. [{c.get('visual') or s['type']}] {c.get('title') or s.get('text') or s.get('heading')} ({len(c.get('title') or '')})")
    problems = findings(slides, "spotlight")
    print("lint:", problems or "clean")
    print(f"reply [{len(reply)}]:", reply)
    print(caption)
    out = HERE / "slides.json"
    out.write_text(json.dumps({"slides": slides, "hook": hook, "caption": caption, "reply": reply}, default=str, indent=1))
    if problems or not (args.write or args.local):
        return 1 if problems else 0

    from services import ig_backlog, ig_carousel, ig_slides

    if args.local:
        c = ig_carousel.save(data_db, slides, hook, {"spotlight": KEY, "local": 1}, "ig-spotlight")
        print("local carousel", c["id"], len(slides))
        return 0
    from database import engine
    from services.ig_links import post_link
    from services.ig_notes import youtube_copy

    carousel = ig_carousel.save(data_db, slides, hook, {"spotlight": KEY}, "ig-spotlight")
    n = len(slides)
    fact = {"kind": "spotlight", "title": hook, "hook": hook, "subject": T, "subject_role": "batter",
            "carousel_id": carousel["id"], "slides": n, "render": True, "post_time": "6 pm"}
    link = post_link(fact)
    fact["x"] = [{"n": 1, "text": reply.replace("Data: Hindsight", f"{link}\nData: Hindsight") if len(reply) + len(link) < 270 else reply,
                  "slide": 1, "reply_to": "https://x.com/exceedingxpuns", "cards": [1, 2, 3, 5]}]
    fact["youtube"] = youtube_copy(fact, caption, hook)
    ist = timezone(timedelta(hours=5, minutes=30))
    today = datetime.now(ist).date()
    post = {"key": KEY, "pillar": "reactive", "fact": fact, "snapshot_id": carousel["id"], "warnings": [],
            "players": [T], "caption": caption}
    with engine.begin() as conn:
        ig_backlog.upsert_pack(conn, post, today, source="hand", post_by=datetime.combine(today, time.max, tzinfo=ist))
    print(f"queued ig:{KEY} for {today} · carousel {carousel['id']} ({n} slides)")
    os.environ.pop("REEL_V2", None)  # the voiced Reel is the hand script below, not the writer's
    r = ig_slides.render(carousel["id"], n, args.base)
    print(f"rendered {len(r['ok'])}/{n}" + (f", failed {r['failed']}" if r["failed"] else "") + f"; layout {r.get('layout') or 'clean'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
