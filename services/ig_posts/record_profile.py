"""
The record holder's profile: what a "fastest to X runs" post (services/ig_posts/records.py) adds after the races, so the
post doubles as a profile of the batter who set the record. Men's T20 batting races.

    deep_cards(db, scope, spec, pool, words)  ->  {"deep": card or None, "profile": [cards], "opposition": card or None}

pool: the fastest few by balls, [{name, date (of the milestone), team}], the leader first. Each player is measured over
their career up to the day they reached the milestone (the query builder, end_date = that day), so the five are compared
at the same point.

  deep         the deeper cut: the leader on runs above average against the leader on win probability added, by phase
               (dropped when one player leads both)
  phase        RAA per 100 balls in each phase, and the share of balls in the powerplay, for the pool
  start        strike rate in the first 10 balls of an innings, for the pool, against the average batter in the scope
  boom         the spread of innings: 30+, out for under 10, for the pool (batting_stats)
  types        the leader against pace, spin and the bowling styles they've faced most, against the average batter
  zones        where the leader's boundaries go, against the field
  outs         how the leader gets out: caught in the deep or the ring (from where the catch was plotted), bowled, lbw,
               stumped, against the field; balls per dismissal against pace and spin
  opposition   strike rate against full members only, for the pool

Associate-nation players stay in (the record is the record) and are flagged: † in the tables, named in the help lines.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.ig_posts.cards import card
from services.ig_posts.spotlight import short_name as short  # "Suryakumar", not "Yadav" (a surname many share)

MIN_CELL = 60        # balls for a phase or bowling-style cell
MIN_STYLES = 4       # bowling styles shown beyond pace and spin
MIN_BOUNDARIES = 40
DEEP = 0.6           # a catch this far out (share of the boundary radius) is in the deep
TILT = 5             # win-probability points a batter's powerplay must add to call a later phase "already tilted"
OFF_PLOT = 1.1       # beyond this, the plotted point isn't a catch position
PHASES = (("powerplay", "Powerplay"), ("middle", "Middle"), ("death", "Death"))
DISMISSALS = (("caught", "Caught"), ("bowled", "Bowled"), ("leg before wicket", "LBW"), ("stumped", "Stumped"))


def full_members() -> List[str]:
    from services.ig_posts.recap_special import full_members as f

    return f()


def associate(team: Optional[str]) -> bool:
    return bool(team) and team not in full_members()


def label(r: Dict[str, Any]) -> str:
    return short(r["name"]) + ("†" if associate(r.get("team")) else "")


def _qb(db: Session, name: Optional[str], until: date, group_by: List[str], **extra) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    args = {"fmt": "T20", "gender": "male", "include_international": True, "leagues": [], "group_by": group_by,
            "end_date": until, "limit": 200, **extra}
    if name:
        args["batters"] = [name]
    return run_deliveries_query(db, **args).get("data") or []


def _wpa100(r: Dict[str, Any]) -> Optional[float]:
    mb = r.get("metric_balls") or 0
    return round(100 * r["wpa"] / mb, 2) if r.get("wpa") is not None and mb else None


def _heat(pool, metrics, values, lower_better=()):
    """The scorecard visual's rows: each column shaded by rank among the pool, the best ringed."""
    rows = [{"name": p["name"], "short": label(p), "values": values[p["name"]], "highlight": i == 0, "pct": {}, "leader": []}
            for i, p in enumerate(pool)]
    for key, *_ in metrics:
        have = [r for r in rows if r["values"].get(key) is not None]
        low = key in lower_better
        for r in have:
            v = r["values"][key]
            better = sum(1 for o in have if (o["values"][key] > v if low else o["values"][key] < v))
            r["pct"][key] = round(100 * better / max(1, len(have) - 1), 1)
        if have:
            best = (min if low else max)(have, key=lambda r: r["values"][key])
            best["leader"].append(key)
    return rows


def _associates_line(pool, full_runs: Dict[str, Optional[int]]) -> str:
    named = [p for p in pool if associate(p.get("team"))]
    if not named:
        return ""
    bits = [f"{p['name']} ({p['team']}, {full_runs.get(p['name']) or 0:,} runs against full members)" for p in named]
    return "†: plays for an associate nation: " + "; ".join(bits) + "."


# ---- the cards ------------------------------------------------------------------------------------------------------

def phase_card(db, pool, sample):
    metrics = [("powerplay", "PP RAA", "signed1"), ("middle", "Mid RAA", "signed1"), ("death", "Death RAA", "signed1"),
               ("pp_share", "PP balls", "pct0")]
    values, by = {}, {}
    for p in pool:
        rows = {r["phase"]: r for r in _qb(db, p["name"], p["date"], ["phase"])}
        total = sum(r["balls"] for r in rows.values()) or 1
        values[p["name"]] = {k: (rows[k]["raa_per_100"] if k in rows and rows[k]["balls"] >= MIN_CELL else None)
                             for k, *_ in metrics[:3]}
        values[p["name"]]["pp_share"] = round(100 * (rows.get("powerplay") or {}).get("balls", 0) / total)
        by[p["name"]] = rows
    lead = pool[0]["name"]
    v = values[lead]

    def top_of(k):
        return max(values[p["name"]][k] for p in pool if values[p["name"]].get(k) is not None)
    # The phase where they lead the five, if any (the biggest lead); else their best phase.
    phases = [k for k, *_ in metrics[:3] if v.get(k) is not None]
    leads = [k for k in phases if v[k] >= top_of(k)]
    best = max(leads or phases, key=lambda k: v[k], default=None)
    if not best:
        return None, by
    top = top_of(best)
    word = dict(PHASES)[best].lower() + (" overs" if best != "powerplay" else "")
    title = (f"{short(lead)} adds {v[best]:.0f} runs above par per 100 balls in the {word}"
             + (", the most of the five" if v[best] >= top else ""))
    rows = _heat(pool, metrics, values)
    return card("phase", "scorecard", title, {
        "metrics": [{"key": k, "label": l, "format": f} for k, l, f in metrics],
        "rows": rows,
        "method": f"Runs above average per 100 balls in each phase (–: under {MIN_CELL} balls); PP balls: share of their "
                  "balls faced in the powerplay. Up to each player's milestone. Brighter: better among these five.",
    }, sample, f"{v['pp_share']}% of {short(lead)}'s balls come in the powerplay." if v.get("pp_share") is not None else ""), by


def start_card(db, pool, since, until, sample):
    def early(rows):
        r = next((r for r in rows if str(r.get("batter_ball_number_bucket")) == "1-10"), None)
        return r if r and r["balls"] >= MIN_CELL else None
    rows = []
    for p in pool:
        e = early(_qb(db, p["name"], p["date"], ["batter_ball_number_bucket"]))
        if e:
            rows.append({"name": label(p), "value": round(e["strike_rate"]), "team": p.get("team"),
                         "highlight": p is pool[0], "detail": f"{e['runs']} off {e['balls']} balls"})
    field = early(_qb(db, None, until, ["batter_ball_number_bucket"], start_date=since))
    if len(rows) < 3 or not field:
        return None
    rows.append({"name": "Average batter", "value": round(field["strike_rate"]), "detail": f"T20Is since {since.year}"})
    lead = rows[0]
    rank = 1 + sum(1 for r in rows[1:-1] if r["value"] > lead["value"])
    title = (f"{short(pool[0]['name'])} strikes at {lead['value']} in the first 10 balls of an innings"
             + (", the fastest start of the five" if rank == 1 else f", the {['', '', '2nd', '3rd', '4th', '5th'][rank]}-fastest of the five")
             + f". The average batter: {rows[-1]['value']}")
    return card("start", "metric_bars", title, {
        "metric": {"label": "strike rate in the first 10 balls of an innings", "format": "int", "signed": False},
        "rows": rows, "label_width": 130}, sample, "Up to each player's milestone.")


def boom_card(db, scope, pool, sample):
    from services import idea_stats as S

    metrics = [("thirty", "30+", "pct0"), ("cheap", "Out <10", "pct0"), ("bpi", "Balls/inns", "dec1")]
    values = {}
    for p in pool:
        where, params = S._where({**scope, "start": None, "end": p["date"].isoformat()}, "s.batting_team", S._opp("s.batting_team"))
        r = db.execute(text(f"""
            SELECT COUNT(*) AS inns, COUNT(*) FILTER (WHERE s.runs >= 30) AS thirty,
                   COUNT(*) FILTER (WHERE s.runs < 10 AND s.wickets > 0) AS cheap, AVG(s.balls_faced) AS bpi
            FROM batting_stats s JOIN matches m ON m.id = s.match_id
            WHERE s.striker = :n AND {where}
        """), {**params, "n": p["name"]}).mappings().first()
        if not r or not r["inns"]:
            continue
        values[p["name"]] = {"thirty": round(100 * r["thirty"] / r["inns"]), "cheap": round(100 * r["cheap"] / r["inns"]),
                             "bpi": round(float(r["bpi"] or 0), 1), "inns": r["inns"]}
    if pool[0]["name"] not in values:
        return None
    pool = [p for p in pool if p["name"] in values]
    if len(pool) < 3:
        return None
    lead = values[pool[0]["name"]]
    most_thirty = lead["thirty"] >= max(v["thirty"] for v in values.values())
    most_cheap = lead["cheap"] >= max(v["cheap"] for v in values.values())
    tail = (", the most of the five on both" if most_thirty and most_cheap else
            ": the most 30s of the five" if most_thirty else ": the most cheap dismissals of the five" if most_cheap else "")
    title = (f"{short(pool[0]['name'])} passes 30 in {lead['thirty']}% of innings and is out for under 10 in "
             f"{lead['cheap']}%{tail}")
    rows = _heat(pool, metrics, values, lower_better=("cheap",))
    return card("boom", "scorecard", title, {
        "metrics": [{"key": k, "label": l, "format": f} for k, l, f in metrics], "rows": rows,
        "method": "Share of innings with 30 or more, and dismissed for under 10; balls faced per innings. Up to each "
                  "player's milestone. Brighter: better among these five (fewer cheap dismissals is better).",
    }, sample)


def types_card(db, lead, since, sample):
    from services.ig_posts.captains_call import STYLES

    kinds = {r["bowl_kind"]: r for r in _qb(db, lead["name"], lead["date"], ["bowl_kind"])}
    fkinds = {r["bowl_kind"]: r for r in _qb(db, None, lead["date"], ["bowl_kind"], start_date=since)}
    styles = sorted([r for r in _qb(db, lead["name"], lead["date"], ["bowl_style"]) if r["balls"] >= MIN_CELL],
                    key=lambda r: -r["balls"])[:MIN_STYLES]
    fstyles = {r["bowl_style"]: r for r in _qb(db, None, lead["date"], ["bowl_style"], start_date=since)}
    rows = []
    for k, lbl in (("pace bowler", "Pace"), ("spin bowler", "Spin")):
        if k in kinds and kinds[k]["balls"] >= MIN_CELL and k in fkinds:
            rows.append({"label": f"v {lbl}", "subject": round(kinds[k]["strike_rate"]), "field": round(fkinds[k]["strike_rate"])})
    for r in styles:
        if r["bowl_style"] in fstyles:
            rows.append({"label": f"v {STYLES.get(r['bowl_style'], r['bowl_style'])}", "subject": round(r["strike_rate"]),
                         "field": round(fstyles[r["bowl_style"]]["strike_rate"])})
    if len(rows) < 3:
        return None
    # The headline: pace or spin (the big samples), whichever they beat the average batter by more.
    gap = max(rows[:2], key=lambda r: r["subject"] - r["field"])
    gap["highlight"] = True
    pace, spin = kinds.get("pace bowler") or {}, kinds.get("spin bowler") or {}
    who = short(lead["name"])
    return card("types", "deep_compare",
                f"{who} strikes at {gap['subject']} {gap['label'].replace('v ', 'against ').lower()}, {gap['subject'] - gap['field']} "
                f"above the average batter", {
                    "metric": {"label": "strike rate", "format": "int", "signed": False},
                    "series": [who, "Average T20I batter"], "rows": rows},
                sample, (f"Runs above average per 100 balls: {pace.get('raa_per_100') or 0:+.0f} against pace, "
                         f"{spin.get('raa_per_100') or 0:+.0f} against spin. Styles faced 60+ balls; T20Is since {since.year}."))


def zones_card(db, lead, since, sample):
    from services.ig_posts.cards import LEG_SIDE, ZONES, batter_hand, zones_help

    hand = batter_hand(db, lead["name"])

    def counts(rows):
        return {int(r["wagon_zone"]): (r.get("fours") or 0) + (r.get("sixes") or 0)
                for r in rows if r.get("wagon_zone") is not None and int(r["wagon_zone"]) in ZONES}
    mine = counts(_qb(db, lead["name"], lead["date"], ["wagon_zone"]))
    field = counts(_qb(db, None, lead["date"], ["wagon_zone"], start_date=since))
    n, nf = sum(mine.values()), sum(field.values())
    if n < MIN_BOUNDARIES or not nf:
        return None
    zones_ = [{"zone": z, "name": ZONES[z], "boundaries": mine.get(z, 0), "pct": round(100 * mine.get(z, 0) / n, 1),
               "usual_pct": round(100 * field.get(z, 0) / nf, 1)} for z in ZONES]
    top = max(zones_, key=lambda z: z["pct"])
    leg = round(100 * sum(mine.get(z, 0) for z in LEG_SIDE) / n)
    return card("zones", "boundary_zones",
                f"{short(lead['name'])} hits {top['pct']:.0f}% of boundaries to {top['name'].lower()} (T20I batters: "
                f"{top['usual_pct']:.0f}%)",
                {"zones": zones_, "top": top["zone"], "leg_side_pct": leg, "hand": hand},
                f"{n:,} boundaries with a direction · {sample}", zones_help(hand))


def _ground(db, since, until) -> Optional[Dict[str, float]]:
    """The plot's centre and boundary radius, from where T20I fours landed in the window."""
    r = db.execute(text("""
        SELECT AVG(wagon_x) AS cx, AVG(wagon_y) AS cy FROM delivery_details
        WHERE competition = 'T20I' AND batruns = 4 AND wagon_x > 0 AND match_date >= :a AND match_date <= :b
    """), {"a": since.isoformat(), "b": until.isoformat()}).mappings().first()
    if not r or r["cx"] is None:
        return None
    rad = db.execute(text("""
        SELECT AVG(SQRT(POWER(wagon_x - :cx, 2) + POWER(wagon_y - :cy, 2))) FROM delivery_details
        WHERE competition = 'T20I' AND batruns = 4 AND wagon_x > 0 AND match_date >= :a AND match_date <= :b
    """), {"cx": r["cx"], "cy": r["cy"], "a": since.isoformat(), "b": until.isoformat()}).scalar()
    return {"cx": float(r["cx"]), "cy": float(r["cy"]), "r": float(rad)}


def outs_card(db, lead, since, sample):
    g = _ground(db, since, lead["date"])
    if not g:
        return None
    dist = "SQRT(POWER(wagon_x - :cx, 2) + POWER(wagon_y - :cy, 2)) / :r"
    sql = f"""
        SELECT LOWER(dismissal) AS how,
               CASE WHEN LOWER(dismissal) <> 'caught' OR wagon_x IS NULL OR wagon_x <= 0 OR {dist} > :off THEN NULL
                    WHEN {dist} >= :deep THEN 'deep' ELSE 'ring' END AS where_,
               COUNT(*) AS n
        FROM delivery_details
        WHERE competition = 'T20I' AND out = 'true' AND p_out = p_bat AND match_date <= :b {{who}}
        GROUP BY 1, 2"""
    # The field: batters in T20Is between full members over the same years (associate games are rarely plotted).
    args = {**g, "off": OFF_PLOT, "deep": DEEP, "b": lead["date"].isoformat()}
    mine = db.execute(text(sql.format(who="AND bat = :n")), {**args, "n": lead["name"]}).mappings().all()
    field = db.execute(text(sql.format(who="AND match_date >= :a AND team_bat = ANY(:full) AND team_bowl = ANY(:full)")),
                       {**args, "a": since.isoformat(), "full": full_members()}).mappings().all()

    def shares(rows):
        # Catches without a plotted position are left out of the count altogether, so the shares add up.
        rows = [r for r in rows if r["how"] != "caught" or r["where_"]]
        total = sum(r["n"] for r in rows) or 1
        out = {"deep": 0, "ring": 0, **{k: 0 for k, _ in DISMISSALS[1:]}}
        for r in rows:
            if r["how"] == "caught":
                out[r["where_"]] += r["n"]
            elif r["how"] in out:
                out[r["how"]] += r["n"]
        return {k: round(100 * v / total) for k, v in out.items()}, sum(r["n"] for r in rows)
    m, n = shares(mine)
    f, _ = shares(field)
    if n < 15:
        return None
    labels = [("deep", "Caught in the deep"), ("ring", "Caught in the ring"), ("bowled", "Bowled"),
              ("leg before wicket", "LBW"), ("stumped", "Stumped")]
    rows = [{"label": lbl, "subject": m[k], "field": f[k], "highlight": k == "deep"} for k, lbl in labels]
    kinds = {r["bowl_kind"]: r for r in _qb(db, lead["name"], lead["date"], ["bowl_kind"])}
    bpd = "; ".join(f"one every {round(kinds[k]['balls_per_dismissal'])} balls against {w}"
                    for k, w in (("pace bowler", "pace"), ("spin bowler", "spin"))
                    if kinds.get(k) and kinds[k].get("balls_per_dismissal"))
    who = short(lead["name"])
    return card("outs", "deep_compare",
                f"{m['deep']}% of {who}'s dismissals are catches in the deep. The usual T20I batter: {f['deep']}%", {
                    "metric": {"label": "% of dismissals", "format": "pct0", "signed": False},
                    "series": [who, "T20I batters (full members)"], "rows": rows},
                sample, (f"Where the catch was taken, from the wagon-wheel plot (the deep: beyond {round(DEEP * 100)}% of the "
                         f"way to the rope); {n} dismissals with a known position."
                         + (f" Out {bpd}." if bpd else "")))


def past_powerplay(db: Session, name: str, until: date) -> Optional[Dict[str, Any]]:
    """In T20I innings where `name` batted on past the powerplay: his powerplay runs and balls, and his side's win
    probability (delivery_details.win_prob is the batting side's, in %) at the first ball and at the end of the powerplay.
    A quiet phase after that is often one his own start decided."""
    r = db.execute(text("""
        WITH his AS (
            SELECT p_match, inns, MAX(over) AS last_over,
                   SUM(CASE WHEN over < 6 THEN COALESCE(batruns, 0) ELSE 0 END) AS runs,
                   COUNT(*) FILTER (WHERE over < 6 AND COALESCE(wide, 0) = 0) AS balls
            FROM delivery_details WHERE bat = :n AND competition = 'T20I' AND match_date <= :d
            GROUP BY p_match, inns
        ), wp AS (
            SELECT dd.p_match, dd.inns,
                   (ARRAY_AGG(dd.win_prob ORDER BY dd.over, dd.ball))[1] AS wp0,
                   (ARRAY_AGG(dd.win_prob ORDER BY dd.over DESC, dd.ball DESC) FILTER (WHERE dd.over < 6))[1] AS wp6
            FROM delivery_details dd JOIN his h ON h.p_match = dd.p_match AND h.inns = dd.inns
            WHERE h.last_over >= 6 GROUP BY dd.p_match, dd.inns
        )
        SELECT COUNT(*) AS innings, SUM(h.runs) AS runs, SUM(h.balls) AS balls, AVG(wp.wp0) AS wp0, AVG(wp.wp6) AS wp6
        FROM his h JOIN wp ON wp.p_match = h.p_match AND wp.inns = h.inns
        WHERE wp.wp0 IS NOT NULL AND wp.wp6 IS NOT NULL
    """), {"n": name, "d": until.isoformat()}).mappings().first()
    if not r or not r["innings"] or not r["balls"]:
        return None
    return {"innings": r["innings"], "runs": int(r["runs"]), "balls": int(r["balls"]),
            "sr": round(100 * r["runs"] / r["balls"]), "wp0": round(r["wp0"]), "wp6": round(r["wp6"])}


def deep_card(db, pool, by_phase, sample):
    """The deeper cut: the RAA leader against the WPA leader, win probability added by phase."""
    from services.ig_posts.deep_cut import KICKER

    totals = {}
    for p in pool:
        r = (_qb(db, p["name"], p["date"], ["batter"]) or [None])[0]
        if r:
            totals[p["name"]] = {"raa": r.get("raa_per_100"), "wpa": _wpa100(r)}
    # Full members only: an associate player's runs mostly come against associates, so his rates don't compare.
    have = [p for p in pool if not associate(p.get("team"))
            and totals.get(p["name"], {}).get("raa") is not None and totals[p["name"]].get("wpa") is not None]
    if len(have) < 2:
        return None
    raa_lead = max(have, key=lambda p: totals[p["name"]]["raa"])
    wpa_lead = max(have, key=lambda p: totals[p["name"]]["wpa"])
    if raa_lead is wpa_lead:
        return None
    a, b = raa_lead["name"], wpa_lead["name"]
    a_date = raa_lead["date"]
    pa, pb = by_phase.get(a) or {}, by_phase.get(b) or {}
    rows = []
    for k, lbl in PHASES:
        ra, rb = pa.get(k), pb.get(k)
        if ra and rb and ra["balls"] >= MIN_CELL and rb["balls"] >= MIN_CELL:
            rows.append({"label": lbl, "subject": _wpa100(ra), "field": _wpa100(rb)})
    if len(rows) < 2:
        return None
    edge = max(rows, key=lambda r: (r["field"] or 0) - (r["subject"] or 0))
    edge["highlight"] = True
    ta, tb = totals[a], totals[b]
    phase = edge["label"].lower() + (" overs" if edge["label"] != "Powerplay" else "")
    # A later phase where the RAA leader adds little win probability is often one his own powerplay already decided:
    # when his starts in those innings lifted his side by TILT points or more, say that, not that his runs matter less.
    early = past_powerplay(db, a, a_date) if edge["label"] != "Powerplay" else None
    tilted = early and early["wp6"] - early["wp0"] >= TILT
    if tilted:
        title = f"{short(a)} adds the most runs above average, and he does it up front"
        edge.pop("highlight", None)  # the chart points where the title does: his powerplay
        next(r for r in rows if r["label"] == "Powerplay")["highlight"] = True
        why = (f" The gap comes from the {phase}: when {short(a)} bats past the powerplay ({early['innings']} innings), "
               f"he has already scored at {early['sr']} and lifted his side from {early['wp0']}% to {early['wp6']}%.")
    else:
        title = f"{short(a)} adds the most runs above average. {short(b)}'s runs move more matches, most of all in the {phase}"
        why = ""
    c = card("raa-v-wpa", "deep_compare", title, {
        "metric": {"label": "win probability added per 100 balls (percentage points)", "format": "dec2", "signed": False},
        "series": [short(a), short(b)], "rows": rows,
    }, sample, (f"Runs above average per 100 balls: {short(a)} {ta['raa']:.0f}, {short(b)} {tb['raa']:.0f}. Win probability "
                f"added per 100 balls: {short(b)} {tb['wpa']:.2f}, {short(a)} {ta['wpa']:.2f}." + why
                + " RAA: runs beyond an average batter's from the same balls; WPA: how much the runs moved the chance of winning."))
    c["kicker"] = KICKER
    c["facts"] = {"raa_lead": a, "wpa_lead": b, "past_powerplay": early if tilted else None}
    return c


def opposition_card(db, pool, full_runs_balls, sample):
    """Strike rate against full members only, for the pool: associate players without enough such balls drop out."""
    rows = []
    for p in pool:
        r = full_runs_balls.get(p["name"]) or {}
        if (r.get("balls") or 0) >= MIN_CELL:
            rows.append({"name": label(p), "value": round(r["strike_rate"]), "team": p.get("team"), "highlight": p is pool[0],
                         "detail": f"{r['runs']:,} off {r['balls']:,}"})
    out = [p for p in pool if (full_runs_balls.get(p["name"]) or {}).get("balls", 0) < MIN_CELL]
    if len(rows) < 3 or not rows[0]["highlight"]:
        return None
    ranked = sorted(rows, key=lambda r: -r["value"])
    lead = rows[0]
    rank = ranked.index(lead) + 1
    others = [r for r in ranked if r is not lead]
    title = (f"Against full members only, {short(pool[0]['name'])} strikes at {lead['value']}"
             + (f", ahead of {others[0]['name'].rstrip('†')} ({others[0]['value']})" if rank == 1
                else f": {['', '', '2nd', '3rd', '4th', '5th'][rank]} of the five"))
    help_ = "Runs and balls against the 12 full members, up to each player's milestone."
    if out:
        help_ += " Not enough balls against them: " + ", ".join(p["name"] for p in out) + "."
    return card("opposition", "metric_bars", title, {
        "metric": {"label": "strike rate against full members (runs off balls)", "format": "int", "signed": False},
        "rows": rows, "label_width": 130}, sample, help_)


def deep_cards(db: Session, scope: Dict[str, Any], spec: Dict[str, Any], pool: List[Dict[str, Any]],
               words: Dict[str, str], sample: str) -> Dict[str, Any]:
    if spec["subject"] != "batter" or scope["fmt"] != "T20" or not pool:
        return {"deep": None, "profile": [], "opposition": None, "associates": ""}
    lead = pool[0]
    debut = db.execute(text("""
        SELECT MIN(match_date) FROM delivery_details WHERE bat = :n AND competition = 'T20I'
    """), {"n": lead["name"]}).scalar()
    since = date.fromisoformat(debut) if isinstance(debut, str) else (debut or date(lead["date"].year - 3, 1, 1))
    phase, by_phase = phase_card(db, pool, sample)
    full_runs, full_rb = {}, {}
    for p in pool:
        r = (_qb(db, p["name"], p["date"], ["batter"], bowling_teams=full_members()) or [{}])[0]
        full_runs[p["name"]] = r.get("runs")
        full_rb[p["name"]] = r
    profile = [c for c in [phase, start_card(db, pool, since, lead["date"], sample), boom_card(db, scope, pool, sample),
                           types_card(db, lead, since, sample), zones_card(db, lead, since, sample),
                           outs_card(db, lead, since, sample)] if c]
    return {"deep": deep_card(db, pool, by_phase, sample), "profile": profile,
            "opposition": opposition_card(db, pool, full_rb, sample),
            "associates": _associates_line(pool, full_runs), "full_runs": full_runs}
