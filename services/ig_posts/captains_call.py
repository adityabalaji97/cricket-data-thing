"""
"The captain's call": the over that swung a chase, read against the bowling plan around it, without hindsight blame.

    post(db, match_id, over=None)  ->  {slides, title, verdict, players, kicker, deep_cut, method, over} or None
    plan_card(db, match_id, mark)  ->  the bowling-plan card alone (services/ig_posts/recap_special.py uses it)

The post (the chase's second innings; `over` is 1-based, default the over that moved the bowling side's win probability
most): hook; the bowling plan (each bowler's overs, the over ringed, and what each still had left); how 200+ totals are
bowled when they're defended (spin's share by over band, against this innings); how often this bowler bowls this over;
the deeper cut, spin against pace at the death to set and new strikers; the batters at the crease against this bowler
and their kind; a pacer's unbowled 4th over, when there was one; the verdict, written from the numbers.

Norms: the IPL and men's T20Is between full members over NORM_YEARS before the match; a bowler's and batters' history:
every T20 in the data. Set striker: SET_BALLS balls faced before the ball. What the data can't see (injuries, plans,
dew) is said, not guessed.
"""
from __future__ import annotations

from collections import OrderedDict, defaultdict
from datetime import timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.ig_posts.cards import card
from services.ig_posts.spotlight import short_name

NORM_YEARS = 3
SET_BALLS = 20
BIG_TOTAL = 200
MIN_MATCHUP = 6       # balls for a batter-v-bowler row
LEGAL = "COALESCE(wide, 0) = 0 AND COALESCE(noball, 0) = 0"
SCOPE = ("(competition = 'IPL' OR (competition = 'T20I' AND team_bat = ANY(:full) AND team_bowl = ANY(:full)))"
         " AND match_date >= :since AND match_date < :day")
STYLES = {"LWS": "left-arm wrist spin", "SLA": "left-arm orthodox", "OB": "off-spin", "LB": "leg-spin",
          "LBG": "leg-spin", "RF": "right-arm fast", "RFM": "right-arm fast-medium", "RM": "right-arm medium",
          "LF": "left-arm fast", "LFM": "left-arm fast-medium", "LMF": "left-arm medium-fast", "LM": "left-arm medium",
          "RMF": "right-arm medium-fast"}
#: Short forms for a narrow detail line.
STYLES_SHORT = {"LWS": "wrist spin", "SLA": "left-arm spin", "OB": "off-spin", "LB": "leg-spin", "LBG": "leg-spin"}
KIND = {"pace bowler": "pace", "spin bowler": "spin"}
WIDE_LABELS = 196     # px: the name column of a metric_bars card whose detail lines are long


def ordinal(n: int) -> str:
    from services.ig_posts.match import ordinal as o

    return o(n)


def _params(day) -> Dict[str, Any]:
    from services.ig_posts.recap_special import full_members

    return {"full": full_members(), "since": (day - timedelta(days=365 * NORM_YEARS)).isoformat(), "day": day.isoformat()}


def _cached(db: Session, params: Dict[str, Any], run):
    from services import query_cache

    return query_cache.cached_run(db, params, lambda: {"rows": run()})["rows"]


# ---- the match ----------------------------------------------------------------------------------------------------

def overs(db: Session, match_id: str, inns: int = 2) -> List[Dict[str, Any]]:
    """The innings over by over: bowler, kind, style, runs, the batters, and the bowling side's win probability at the
    start and end of the over."""
    balls = [dict(r) for r in db.execute(text("""
        SELECT over, bowl, bowl_kind, bowl_style, bat, cur_bat_bf, cur_bat_runs, score, batruns, win_prob, team_bat,
               team_bowl, wide, noball
        FROM delivery_details WHERE p_match = :m AND inns = :i ORDER BY id
    """), {"m": str(match_id), "i": inns}).mappings().all()]
    out: "OrderedDict[int, Dict[str, Any]]" = OrderedDict()
    prev = None
    for b in balls:
        wp = None if b["win_prob"] is None else 100.0 - float(b["win_prob"])  # the bowling side's
        o = out.setdefault(b["over"], {"over": b["over"] + 1, "bowler": b["bowl"], "kind": b["bowl_kind"],
                                       "style": b["bowl_style"], "runs": 0, "team": b["team_bowl"],
                                       "batting": b["team_bat"], "wp_from": prev, "batters": OrderedDict()})
        o["runs"] += b["score"] or 0
        if b["bat"] not in o["batters"]:  # state when they first faced in the over: balls and runs before this ball
            legal = not (b["wide"] or b["noball"])
            o["batters"][b["bat"]] = {"balls": (b["cur_bat_bf"] or 0) - (1 if legal else 0),
                                      "runs": (b["cur_bat_runs"] or 0) - (b["batruns"] or 0)}
        if wp is not None:
            o["wp_to"] = wp
            prev = wp
    return list(out.values())


def swing_over(ov: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The over that cost the bowling side the most win probability."""
    moved = [o for o in ov if o.get("wp_from") is not None and o.get("wp_to") is not None]
    return max(moved, key=lambda o: o["wp_from"] - o["wp_to"], default=None)


def plan(ov: List[Dict[str, Any]], mark: int) -> List[Dict[str, Any]]:
    """Each bowler in order of first over: kind, overs (1-based, runs), and overs left before `mark`."""
    rows: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
    for o in ov:
        r = rows.setdefault(o["bowler"], {"name": o["bowler"], "short": short_name(o["bowler"]),
                                          "kind": KIND.get(o["kind"], "other"), "cells": []})
        r["cells"].append({"o": o["over"], "runs": o["runs"]})
    for r in rows.values():
        r["left"] = max(0, 4 - sum(1 for c in r["cells"] if c["o"] < mark))
    return list(rows.values())


def plan_card(db: Session, match_id: str, mark: Optional[int] = None, sample: str = "") -> Optional[Dict[str, Any]]:
    ov = overs(db, match_id)
    if not ov:
        return None
    if mark is None:
        s = swing_over(ov)
        mark = s["over"] if s else None
    at = next((o for o in ov if o["over"] == mark), None)
    if not at:
        return None
    rows = plan(ov, mark)
    other = "pace" if KIND.get(at["kind"]) == "spin" else "spin"
    left = [r for r in rows if r["kind"] == other and r["left"] > 0]
    n = sum(r["left"] for r in left)
    team = at["team"]
    if left:
        title = (f"By the {ordinal(mark)}, {team} had {n} {other} over{'s' if n != 1 else ''} left: "
                 + ", ".join(f"{short_name(r['name'])} {r['left']}" for r in left))
    else:
        title = f"By the {ordinal(mark)}, {team} had no {other} overs left"
    death = [o for o in ov if o["over"] >= 16]
    spin_death = sum(1 for o in death if KIND.get(o["kind"]) == "spin")
    never = sum(4 - len(r["cells"]) for r in left)
    help_ = (f"{team}'s bowling, over by over, with runs. Ringed: the {ordinal(mark)}. "
             f"Spin bowled {spin_death} of the last {len(death)} overs"
             + (f"; {never} of those {other} overs were never bowled." if never else "."))
    c = card("bowling-plan", "bowling_plan", title, {"team": team, "mark": mark, "rows": rows, "overs": len(ov)},
             sample, help_)
    c["facts"] = {"mark": mark, "other": other, "other_left": n, "never": never, "spin_death": spin_death, "death": len(death),
                  "bowler": at["bowler"], "kind": KIND.get(at["kind"]), "runs": at["runs"]}
    return c


# ---- the norms ----------------------------------------------------------------------------------------------------

def mix_norm(db: Session, day, mark: int) -> Dict[str, Any]:
    """Spin's share of overs 11-15, 16-20 and the `mark` over in chases of BIG_TOTAL+, defended v chased."""
    def run():
        return [dict(r) for r in db.execute(text(f"""
            WITH big AS (SELECT p_match FROM delivery_details WHERE {SCOPE} AND inns = 1
                         GROUP BY 1 HAVING MAX(inns_runs) >= :big),
            ch AS (SELECT d.over, d.bowl_kind, CASE WHEN d.winner = d.team_bowl THEN 'defended'
                                                    WHEN d.winner = d.team_bat THEN 'chased' END AS res, d.p_match
                   FROM delivery_details d JOIN big USING (p_match) WHERE d.inns = 2)
            SELECT res, COUNT(DISTINCT p_match) AS n,
                   AVG(CASE WHEN over BETWEEN 10 AND 14 THEN (bowl_kind = 'spin bowler')::int END) AS mid,
                   AVG(CASE WHEN over BETWEEN 15 AND 19 THEN (bowl_kind = 'spin bowler')::int END) AS death,
                   AVG(CASE WHEN over = :mo THEN (bowl_kind = 'spin bowler')::int END) AS mark
            FROM ch WHERE res IS NOT NULL GROUP BY 1
        """), {**_params(day), "big": BIG_TOTAL, "mo": mark - 1}).mappings().all()]
    rows = _cached(db, {"kind": "captains-mix", "day": str(day), "mark": mark, "v": 1}, run)
    return {r["res"]: {k: (float(v) * 100 if k != "n" and v is not None else v) for k, v in r.items() if k != "res"}
            for r in rows}


def set_v_new(db: Session, day) -> Dict[tuple, Dict[str, float]]:
    """Runs an over at the death (16-20) by kind and the striker's state (set: SET_BALLS+ balls before the ball)."""
    def run():
        return [dict(r) for r in db.execute(text(f"""
            SELECT bowl_kind AS kind, (cur_bat_bf - CASE WHEN {LEGAL} THEN 1 ELSE 0 END) >= :set AS set,
                   COUNT(*) FILTER (WHERE {LEGAL}) AS balls, SUM(score) AS runs
            FROM delivery_details WHERE {SCOPE} AND over BETWEEN 15 AND 19 AND bowl_kind IN ('spin bowler', 'pace bowler')
            GROUP BY 1, 2
        """), {**_params(day), "set": SET_BALLS}).mappings().all()]
    rows = _cached(db, {"kind": "captains-set-v-new", "day": str(day), "v": 1}, run)
    return {(KIND[r["kind"]], bool(r["set"])): {"rpo": 6 * r["runs"] / r["balls"], "balls": r["balls"]}
            for r in rows if r["balls"]}


def slot_history(db: Session, bowler: str, mark: int, day) -> Dict[str, Any]:
    """The bowler's IPL and T20I overs by phase, and their `mark` overs (runs each), up to `day`."""
    rows = [dict(r) for r in db.execute(text(f"""
        SELECT p_match, over, SUM(score) AS runs FROM delivery_details
        WHERE bowl = :b AND competition IN ('IPL', 'T20I') AND match_date <= :day GROUP BY 1, 2
    """), {"b": bowler, "day": day.isoformat()}).mappings().all()]
    buckets = OrderedDict([("1-6", 0), ("7-15", 0), (str(mark), 0), ("other 16-20", 0)])
    for r in rows:
        o = r["over"] + 1
        key = str(mark) if o == mark else "1-6" if o <= 6 else "7-15" if o <= 15 else "other 16-20"
        buckets[key] += 1
    at = [r["runs"] for r in rows if r["over"] + 1 == mark]
    return {"buckets": buckets, "total": len(rows), "mark_runs": at}


def matchup(db: Session, batter: str, bowler: Optional[str] = None, style: Optional[str] = None) -> Dict[str, Any]:
    where, args = ("bowl = :w", {"w": bowler}) if bowler else ("bowl_style = :w", {"w": style})
    r = db.execute(text(f"""
        SELECT COUNT(*) FILTER (WHERE {LEGAL}) AS balls, COALESCE(SUM(batruns), 0) AS runs,
               COUNT(*) FILTER (WHERE out = 'true' AND p_out = p_bat) AS outs
        FROM delivery_details WHERE format = 'T20' AND bat = :bat AND {where}
    """), {"bat": batter, **args}).mappings().first()
    return dict(r)


def last_over_usage(db: Session, day) -> Dict[str, Dict[str, int]]:
    """In BIG_TOTAL+ chases: pacers with 3 overs by the end of the 10th, and how many bowled a 4th (and at the death)."""
    def run():
        return [dict(r) for r in db.execute(text(f"""
            WITH big AS (SELECT p_match FROM delivery_details WHERE {SCOPE} AND inns = 1
                         GROUP BY 1 HAVING MAX(inns_runs) >= :big),
            ov AS (SELECT d.p_match, d.bowl, d.over, MAX(d.bowl_kind) AS kind,
                          MAX(CASE WHEN d.winner = d.team_bowl THEN 'defended' WHEN d.winner = d.team_bat THEN 'chased' END) AS res
                   FROM delivery_details d JOIN big USING (p_match) WHERE d.inns = 2 GROUP BY 1, 2, 3),
            b AS (SELECT p_match, bowl, MAX(res) AS res, MAX(kind) AS kind, COUNT(*) FILTER (WHERE over <= 9) AS by10,
                         COUNT(*) AS n, MAX(over) AS last FROM ov GROUP BY 1, 2)
            SELECT res, COUNT(*) AS pacers, COUNT(*) FILTER (WHERE n >= 4) AS fourth,
                   COUNT(*) FILTER (WHERE n >= 4 AND last >= 15) AS at_death
            FROM b WHERE kind = 'pace bowler' AND by10 >= 3 AND res IS NOT NULL GROUP BY 1
        """), {**_params(day), "big": BIG_TOTAL}).mappings().all()]
    return {r["res"]: r for r in _cached(db, {"kind": "captains-fourth", "day": str(day), "v": 1}, run)}


# ---- the post -----------------------------------------------------------------------------------------------------

def _kicker() -> str:
    from services.ig_posts.deep_cut import KICKER

    return KICKER


def post(db: Session, match_id: str, over: Optional[int] = None) -> Optional[Dict[str, Any]]:
    from services.ig_posts.match import series_label

    m = db.execute(text("SELECT id, date, venue, team1, team2, format, winner FROM matches WHERE id = :i"),
                   {"i": str(match_id)}).mappings().first()
    if not m or m["format"] != "T20":
        return None
    day = m["date"]
    label = series_label(db, m["team1"], m["team2"], m["format"], day, m["venue"], played=True)
    sample = f"{label} · {day:%d %b %Y}"
    ov = overs(db, match_id)
    if not ov:
        return None
    at = next((o for o in ov if o["over"] == over), None) if over else swing_over(ov)
    if not at:
        return None
    mark, bowler, team = at["over"], at["bowler"], at["team"]
    kind = KIND.get(at["kind"], "other")
    who = short_name(bowler)
    cards: List[Dict[str, Any]] = []

    pc = plan_card(db, match_id, mark, sample)
    cards.append(pc)
    rows = pc["payload"]["rows"]

    norm = mix_norm(db, day, mark)
    d = norm.get("defended") or {}
    ch = norm.get("chased") or {}
    mid_ov = [o for o in ov if 11 <= o["over"] <= 15]
    death_ov = [o for o in ov if o["over"] >= 16]
    share = lambda os_: 100 * sum(1 for o in os_ if KIND.get(o["kind"]) == "spin") / len(os_) if os_ else None  # noqa: E731
    mix_rows = [r for r in [
        {"label": "Overs 11-15", "subject": share(mid_ov), "field": d.get("mid")},
        {"label": "Overs 16-20", "subject": share(death_ov), "field": d.get("death"), "highlight": True},
        {"label": f"The {ordinal(mark)}", "subject": 100.0 if kind == "spin" else 0.0, "field": d.get("mark")},
    ] if r["subject"] is not None and r["field"] is not None]
    spin_death = pc["facts"]["spin_death"]
    since = (day - timedelta(days=365 * NORM_YEARS)).year
    if d.get("death") is not None:
        cards.append(card("mix", "deep_compare",
                          f"Defending {BIG_TOTAL}, teams bowl spin in {round(d['death'])}% of the death overs. "
                          f"{team}: {spin_death} of {len(death_ov)}",
                          {"metric": {"label": "% of overs bowled by spin", "format": "pct0", "signed": False},
                           "series": [team, f"Teams defending {BIG_TOTAL}+"],
                           "rows": [{**r, "subject": round(r["subject"]), "field": round(r["field"])} for r in mix_rows]},
                          sample,
                          f"When {BIG_TOTAL}+ was chased down, spin bowled {round(ch.get('death') or 0)}% of the last five "
                          f"overs. {d.get('n')} defended and {ch.get('n')} chased, IPL and full-member T20Is since {since}."))

    hist = slot_history(db, bowler, mark, day)
    if hist["total"] and hist["mark_runs"]:
        pct = 100 * hist["buckets"][str(mark)] / hist["total"]
        runs_here = at["runs"]
        worst = runs_here >= max(hist["mark_runs"])
        avg = sum(hist["mark_runs"]) / len(hist["mark_runs"])
        title = f"The {ordinal(mark)} is {round(pct)}% of {who}'s overs"
        title += (f". This {runs_here} was the most expensive of the {len(hist['mark_runs'])}" if worst
                  else f". This one cost {runs_here}")
        cards.append(card("slot", "bucket_bars", title, {
            "metric": {"label": f"% of {who}'s IPL and T20I overs, by over", "format": "pct0"},
            "buckets": [{"label": k if k != str(mark) else f"the {ordinal(mark)}", "value": round(100 * v / hist["total"], 1),
                         "n": v} for k, v in hist["buckets"].items()],
        }, sample, f"{hist['total']} overs in all. Their {ordinal(mark)} overs cost {avg:.1f} on average."))

    sv = set_v_new(db, day)
    first = next(iter(at["batters"].values()), None)
    striker_set = bool(first and first["balls"] >= SET_BALLS)
    if all(k in sv for k in [("spin", True), ("pace", True), ("spin", False), ("pace", False)]):
        s, p = sv[("spin", True)]["rpo"], sv[("pace", True)]["rpo"]
        verdict = "spin isn't the costlier option" if s <= p else "spin is the costlier option"
        c = card("set-v-new", "deep_compare",
                 f"At the death, spin costs {s:.1f} an over to set batters and pace {p:.1f}: {verdict}", {
                     "metric": {"label": f"runs an over, overs 16-20 (set: {SET_BALLS}+ balls faced)", "format": "dec1",
                                "signed": False},
                     "series": ["Spin", "Pace"],
                     "rows": [{"label": "Set striker", "subject": round(s, 1), "field": round(p, 1), "highlight": striker_set},
                              {"label": "New striker", "subject": round(sv[("spin", False)]["rpo"], 1),
                               "field": round(sv[("pace", False)]["rpo"], 1), "highlight": not striker_set}],
                 }, sample, f"IPL and full-member T20Is since {since}. Spinners bowl the death when captains like the "
                            "match-up, which flatters their numbers.")
        c["kicker"] = _kicker()
        cards.append(c)

    style = STYLES.get(at["style"] or "", at["style"] or kind)
    style_short = STYLES_SHORT.get(at["style"] or "", style)
    mrows = []
    for bat, state in at["batters"].items():
        vs = matchup(db, bat, style=at["style"]) if at["style"] else None
        vb = matchup(db, bat, bowler=bowler)
        name = short_name(bat)
        for r, against, brief in ((vs, style, style_short), (vb, who, who)):
            if r and r["balls"] >= MIN_MATCHUP:
                outs = {0: "no outs", 1: "1 out"}.get(r["outs"], f"{r['outs']} outs")
                mrows.append({"name": name, "value": round(100 * r["runs"] / r["balls"]), "team": at["batting"],
                              "detail": f"v {brief}, {r['runs']} off {r['balls']}, {outs}", "against": against,
                              "state": state})
    by_style = sorted([r for r in mrows if r["against"] == style], key=lambda r: r["value"])
    if len(by_style) >= 2:
        lo, hi = by_style[0], by_style[-1]
        hi_state = (f", set on {hi['state']['runs']}," if hi["state"]["balls"] >= SET_BALLS else "")
        title = (f"{lo['name']} scores {lo['value']} per 100 balls off {style}. "
                 f"{hi['name']}{hi_state} scores {hi['value']}")
        for r in mrows:
            r["highlight"] = r is lo
        cards.append(card("matchup", "metric_bars", title, {
            "metric": {"label": "strike rate, every T20 in the data", "format": "int", "signed": False},
            "rows": [{k: v for k, v in r.items() if k not in ("against", "state")} for r in mrows],
            "label_width": WIDE_LABELS,
        }, sample, "At the crease for the " + ordinal(mark) + ": "
                   + "; ".join(f"{short_name(b)} {s['runs']} off {s['balls']}" for b, s in at["batters"].items()) + "."))

    unbowled = [r for r in rows if r["kind"] == "pace" and r["left"] > 0
                and sum(1 for c in r["cells"] if c["o"] <= 10) >= 3 and len(r["cells"]) < 4]
    usage = last_over_usage(db, day)
    if unbowled and usage.get("defended"):
        u = unbowled[0]
        rate = lambda r: 100 * r["fourth"] / r["pacers"]  # noqa: E731
        dd_, cc = usage["defended"], usage.get("chased")
        last3 = max(c["o"] for c in u["cells"])
        runs3 = sum(c["runs"] for c in u["cells"])
        bars = [{"name": "Defended", "value": round(rate(dd_)), "detail": f"{dd_['fourth']} of {dd_['pacers']}, {dd_['at_death']} at the death"}]
        if cc:
            bars.append({"name": "Chased", "value": round(rate(cc)), "detail": f"{cc['fourth']} of {cc['pacers']}, {cc['at_death']} at the death"})
        cards.append(card("fourth", "metric_bars",
                          f"In {BIG_TOTAL}+ chases, a pacer with 3 overs by the 10th bowls a 4th {round(rate(dd_) / 10)} "
                          f"times in 10 when the total is defended",
                          {"metric": {"label": "% who bowled their 4th over", "format": "pct0", "signed": False}, "rows": bars,
                           "label_width": WIDE_LABELS},
                          sample, f"{short_name(u['name'])} had bowled 3 by the {ordinal(last3)} ({runs3} runs); the 4th "
                                  "went unbowled. Why (an injury, a plan or the runs) isn't in the data."))

    lines = []
    if by_style and by_style[0]["value"] < 100:
        lines.append(f"A defensible call: {by_style[0]['name']} scores {by_style[0]['value']} per 100 balls off {style}.")
    other_left = pc["facts"]["other_left"]
    lines.append(f"Inside a tough plan: {team} bowled spin in {spin_death} of the last {len(death_ov)} overs"
                 + (f", where teams defending {BIG_TOTAL} bowl about {round(d['death'])}%" if d.get("death") is not None else "")
                 + (f", with {other_left} {pc['facts']['other']} over{'s' if other_left != 1 else ''} still in hand at the "
                    f"{ordinal(mark)}" + (f" ({pc['facts']['never']} never bowled)." if pc["facts"]["never"] else ".")
                    if other_left else "."))
    lines.append("What the data can't see: injuries, the dressing room, and the dew.")
    slides = ([{"type": "hook", "kicker": label,
                "text": f"{who}'s {ordinal(mark)} went for {at['runs']} and swung the chase. A mistake, or what was left "
                        "of the plan?",
                "sub": f"{team}'s bowling from the 10th over, and what usually happens"}]
              + [{"type": "card", "card": c, "teams": [m["team1"], m["team2"]]} for c in cards]
              + [{"type": "text", "heading": "The verdict", "body": "\n".join(lines)},
                 {"type": "end", "heading": "Every ball, every over",
                  "body": "Win probability, bowling plans and match-ups: free on Hindsight."}])
    # The deeper cut sits at slide 3 (after the hook and the plan).
    deep = next((c for c in cards if c.get("kicker")), None)
    if deep:
        slides.remove(next(s for s in slides if s.get("card") is deep))
        slides.insert(2, {"type": "card", "card": deep, "teams": [m["team1"], m["team2"]]})
    return {"slides": slides, "cards": cards, "title": slides[0]["text"], "verdict": " ".join(lines[:2]),
            "players": [bowler, *at["batters"].keys()], "kicker": label, "over": mark, "match_id": str(match_id),
            "teams": [m["team1"], m["team2"]],
            "deep_cut": {"probe": "captains-set-v-new", "subject": None, "sentence": deep["title"] + ".", "by": "recap"}
            if deep else None,
            "method": f"norms from the IPL and full-member T20Is since {since}; match-ups from every T20 in the data; "
                      "win probability ball by ball (T20 Primer method)."}


def make_post(db: Session, match_id: str, over: Optional[int] = None, built: Optional[Dict[str, Any]] = None):
    """The queueable post (key spotlight-captains-call-<match>), or None."""
    from services import ig_captions, ig_carousel

    built = built or post(db, match_id, over)
    if not built:
        return None
    key = f"spotlight-captains-call-{match_id}"
    carousel = ig_carousel.save(db, built["slides"], built["title"], {"captains_call": str(match_id)}, "ig-spotlight")
    fact = {"kind": "spotlight", "subject": None, "title": built["title"], "verdict": built["verdict"],
            "kicker": built["kicker"], "carousel_id": carousel["id"], "slides": len(built["slides"]), "render": True,
            "captains_call": {"match_id": str(match_id), "over": built["over"]}}
    a, b = built["teams"]
    occasion = [ig_captions.tag(f"{a}v{b}")] + (["#TeamIndia"] if "India" in (a, b) else [])
    caption = ig_captions.build(built["title"], built["verdict"], "debate", built["method"], built["players"],
                                built["kicker"], occasion)
    if built.get("deep_cut"):
        fact["deep_cut"] = built["deep_cut"]
        caption = ig_captions.with_deep_cut(caption, built["deep_cut"]["sentence"])
    return {"key": key, "pillar": "reactive", "fact": fact, "snapshot_id": carousel["id"], "warnings": [],
            "caption": caption, "players": built["players"]}
