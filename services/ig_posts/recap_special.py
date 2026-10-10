"""
The special recap: a men's T20I that broke a record gets a carousel about the record, and about why, told fairly.
recap_post (services/ig_posts/match.py) tries it first; a match that doesn't clear the bars keeps the usual recap.

    special(db, m, label)  ->  {hook, sub, kicker, cards, title, verdict, players, teams, day, deep_cut, method} or None

It fires when a record card (the chase, or the total that lost) fires along with the win-probability card. Cards, each
None when the match doesn't clear its bar:
  chase_record   a top-TOP successful chase, the highest ever against the loser, or the highest in the host country
  total_lost     a top-TOP first-innings total that lost
  execution      the deeper cut: how often each attack landed a good length or yorker, against the T20I norm for the
                 same bowler type and phase
  expected       the deeper cut: what each attack's balls usually cost (expected runs) against what they went for
  wp_line        the loser's win probability through the chase, the overs that moved it most annotated with the batters
                 and what those balls usually cost (the over, not the bowler: the post doesn't blame bowlers)
  conditions     the deeper cut: both innings and both bowler types against expected (a spin gap is a possible dew
                 sign, said as such), the ground's previous highest; it always says what can't be measured
  death_pace     a top-TOP finish (overs 16-20) in a successful chase, framed as batting

Expected runs: each ball gets the average runs (and control %) of men's T20I balls of the same bowler type, phase, line
and length over BASE_YEARS before the match (coarser keys when a ball isn't tagged). Records: men's T20Is between full
members (INTERNATIONAL_TEAMS_RANKED[:12]); ball-by-ball totals from 2015 (delivery_details) and the older scorecards
before that (deliveries); host-country records only from 2015 (where the data has the country).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.ig_posts.cards import card, short

TOP = 10            # a record card needs a top-10 place (or a record against the loser / in the country)
SHOW = 8            # rows on a record chart
BASE_YEARS = 3      # expected runs: men's T20Is in the years before the match
MIN_CELL = 12       # balls for an execution cell
SWING = 15          # an over that moved the loser's win probability this much is annotated (at most MAX_SWINGS)
MAX_SWINGS = 3
BIG_SWING = 30      # the win-probability card fires on an over this big, or ...
PEAK = 80           # ... a loser who was at least this likely to win
TAGGED = 0.8        # share of balls with line and length needed for the expected-runs cards
CLOSE = 0.5         # runs an over: a finish this close to the fastest is "level with" it, not ahead
DEW_GAP = 0.2       # spin's runs-to-expected ratio this much higher in the chase reads as a possible dew sign
GOOD = ("GOOD_LENGTH", "YORKER")
KINDS = (("pace bowler", "Pace"), ("spin bowler", "Spin"))
PHASES = (("pp", "PP"), ("mid", "middle"), ("death", "death"))
DEW_LINE = "We can't measure dew or the pitch. This is what the ball-by-ball shows."
LENGTH_NOTE = ("Length is where the ball pitched: batters moving around the crease turn good lengths into full ones, "
               "so a missed length is partly the batter's doing.")


def full_members() -> List[str]:
    from models import INTERNATIONAL_TEAMS_RANKED

    return list(INTERNATIONAL_TEAMS_RANKED[:12])


def phase(over: int) -> str:
    return "pp" if over < 6 else "mid" if over < 15 else "death"


def poss(team: str) -> str:
    """"West Indies'", "India's"."""
    return f"{team}'" if team.endswith("s") else f"{team}'s"


def abbr(team: str) -> str:
    """"WI" for West Indies (a row's detail line is narrow)."""
    from services.match_preview import INTERNATIONAL_ABBR_TO_NAME

    return next((a for a, n in INTERNATIONAL_ABBR_TO_NAME.items() if n == team), team)


def words(n: int) -> str:
    return {1: "once", 2: "twice"}.get(n, f"{n} times")


def number(n: int) -> str:
    return {2: "two", 3: "three"}.get(n, str(n))


def ordinal(n: int) -> str:
    from services.ig_posts.match import ordinal as o

    return o(n)


def _cached(db: Session, params: Dict[str, Any], run):
    from services import query_cache

    return query_cache.cached_run(db, params, lambda: {"rows": run()})["rows"]


# ---- data -------------------------------------------------------------------------------------------------------

def innings_totals(db: Session) -> List[Dict[str, Any]]:
    """Every men's T20I innings (1 and 2) between full members: match, date, venue, country, teams, runs, wickets,
    winner, plus the death overs (runs, legal balls) of each."""
    def run():
        rows = db.execute(text("""
            WITH dd AS (
                SELECT p_match AS mid, inns, MAX(team_bat) AS bat, MAX(team_bowl) AS bowl, MAX(inns_runs) AS runs,
                       MAX(inns_wkts) AS wkts, MAX(country) AS country,
                       SUM(CASE WHEN over >= 15 THEN score ELSE 0 END) AS death_runs,
                       SUM(CASE WHEN over >= 15 AND COALESCE(wide, 0) = 0 AND COALESCE(noball, 0) = 0 THEN 1 ELSE 0 END)
                           AS death_balls
                FROM delivery_details WHERE competition = 'T20I' AND gender = 'male' AND inns IN (1, 2)
                GROUP BY 1, 2),
            old AS (
                SELECT d.match_id AS mid, d.innings AS inns, MAX(d.batting_team) AS bat, MAX(d.bowling_team) AS bowl,
                       SUM(d.runs_off_bat + d.extras) AS runs, COUNT(d.wicket_type) AS wkts, NULL AS country,
                       NULL::bigint AS death_runs, NULL::bigint AS death_balls
                FROM deliveries d JOIN matches m ON m.id = d.match_id
                WHERE m.format = 'T20' AND m.match_type = 'international' AND m.gender = 'male' AND d.innings IN (1, 2)
                  AND m.date < (SELECT MIN(match_date)::date FROM delivery_details WHERE competition = 'T20I')
                GROUP BY 1, 2)
            SELECT t.*, m.date, m.venue, m.winner FROM (SELECT * FROM dd UNION ALL SELECT * FROM old) t
            JOIN matches m ON m.id = t.mid
            WHERE t.bat = ANY(:full) AND t.bowl = ANY(:full)
        """), {"full": full_members()}).mappings().all()
        return [{**dict(r), "date": str(r["date"])} for r in rows]
    return _cached(db, {"kind": "recap-special-totals", "v": 1}, run)


def match_balls(db: Session, match_id: str) -> List[Dict[str, Any]]:
    return [dict(r) for r in db.execute(text("""
        SELECT inns, over, bat, bowl, team_bat, team_bowl, score, out, bowl_kind, line, length, control, win_prob,
               inns_runs, inns_wkts, wide, noball
        FROM delivery_details WHERE p_match = :m AND inns IN (1, 2) ORDER BY id
    """), {"m": str(match_id)}).mappings().all()]


def baseline(db: Session, match_id: str, day) -> Dict[tuple, Dict[str, float]]:
    """{key: {rpb, ctl, n, good}} for (kind, phase, line, length), (kind, phase) and (phase,): men's T20I balls in the
    BASE_YEARS before `day` (good: share of good-length or yorker balls)."""
    since = day - timedelta(days=365 * BASE_YEARS)

    def run():
        return [dict(r) for r in db.execute(text("""
            SELECT bowl_kind AS kind, CASE WHEN over < 6 THEN 'pp' WHEN over < 15 THEN 'mid' ELSE 'death' END AS ph,
                   line, length, COUNT(*) AS n, SUM(score) AS runs, COUNT(control) AS nc, SUM(control) AS ctl
            FROM delivery_details
            WHERE competition = 'T20I' AND gender = 'male' AND match_date >= :a AND match_date < :b AND p_match <> :m
            GROUP BY 1, 2, 3, 4
        """), {"a": since.isoformat(), "b": day.isoformat(), "m": str(match_id)}).mappings().all()]
    rows = _cached(db, {"kind": "recap-special-baseline", "day": str(day), "m": str(match_id), "v": 1}, run)
    acc: Dict[tuple, Dict[str, float]] = defaultdict(lambda: {"n": 0, "runs": 0, "nc": 0, "ctl": 0, "nl": 0, "good": 0})
    for r in rows:
        tagged = bool(r["line"] and r["length"])
        for key in ((r["kind"], r["ph"], r["line"], r["length"]), (r["kind"], r["ph"]), (r["ph"],)):
            if len(key) == 4 and not tagged:
                continue
            a = acc[key]
            a["n"] += r["n"]; a["runs"] += r["runs"] or 0; a["nc"] += r["nc"]; a["ctl"] += r["ctl"] or 0
            if r["length"]:
                a["nl"] += r["n"]; a["good"] += r["n"] if r["length"] in GOOD else 0
    return {k: {"rpb": a["runs"] / a["n"], "ctl": a["ctl"] / a["nc"] if a["nc"] else None,
                "good": a["good"] / a["nl"] if a["nl"] else None, "n": a["n"]} for k, a in acc.items() if a["n"]}


def expect(base: Dict[tuple, Dict[str, float]], b: Dict[str, Any]) -> Dict[str, float]:
    ph = phase(b["over"])
    for key in ((b["bowl_kind"], ph, b["line"], b["length"]), (b["bowl_kind"], ph), (ph,)):
        if key in base:
            return base[key]
    return {"rpb": 0.0, "ctl": None}


# ---- the match --------------------------------------------------------------------------------------------------

class Match:
    """The match's balls, the records around it and its expected runs, read once for every card."""

    def __init__(self, db: Session, m: Dict[str, Any], sample: str):
        self.db, self.m, self.sample = db, m, sample
        self.id, self.day = str(m["id"]), m["date"]
        self.balls = match_balls(db, self.id)
        self.innings = {i: [b for b in self.balls if b["inns"] == i] for i in (1, 2)}
        first = self.innings[1][0] if self.innings[1] else {}
        self.first_bat, self.first_bowl = first.get("team_bat"), first.get("team_bowl")
        self.winner = m.get("winner")
        self.loser = next((t for t in (m["team1"], m["team2"]) if t != self.winner), None)
        self.totals = [t for t in innings_totals(db) if t["date"] <= str(self.day)]
        self.mine = {t["inns"]: t for t in self.totals if str(t["mid"]) == self.id}
        tagged = sum(1 for b in self.balls if b["line"] and b["length"])
        self.base = baseline(db, self.id, self.day) if self.balls and tagged >= TAGGED * len(self.balls) else None
        for b in self.balls:
            e = expect(self.base, b) if self.base else {"rpb": None, "ctl": None}
            b["x_runs"], b["x_ctl"] = e["rpb"], e["ctl"]

    @property
    def chased(self) -> bool:
        return self.winner is not None and self.winner != self.first_bat

    def others(self, inns: int):
        return [t for t in self.totals if t["inns"] == inns and str(t["mid"]) != self.id]

    def loser_wp(self, b: Dict[str, Any]) -> Optional[float]:
        if b["win_prob"] is None:
            return None
        return float(b["win_prob"]) if b["team_bat"] == self.loser else 100.0 - float(b["win_prob"])


def _record_rows(rows: List[Dict[str, Any]], mine: Dict[str, Any], against: str) -> List[Dict[str, Any]]:
    top = sorted(rows + [mine], key=lambda t: (-t["runs"], t["date"]))[:SHOW]
    if mine not in top:
        top = top[:SHOW - 1] + [mine]
    return [{"name": t["bat"], "value": t["runs"], "team": t["bat"], "highlight": t is mine,
             "detail": f"{t['runs']}/{t['wkts']} v {abbr(t[against])}, {t['date'][:4]}"} for t in top]


def chase_record(x: Match) -> Optional[Dict[str, Any]]:
    mine = x.mine.get(2)
    if not mine or not x.chased:
        return None
    chases = [t for t in x.others(2) if t["winner"] == t["bat"]]
    rank = 1 + sum(1 for t in chases if t["runs"] > mine["runs"])
    v_loser = max((t for t in chases if t["bowl"] == x.loser), key=lambda t: t["runs"], default=None)
    home = mine.get("country")
    in_country = max((t for t in chases if home and t.get("country") == home), key=lambda t: t["runs"], default=None)
    beat_loser = v_loser is None or mine["runs"] > v_loser["runs"]
    beat_home = in_country is not None and mine["runs"] > in_country["runs"]
    if rank > TOP and not beat_loser and not beat_home:
        return None
    bits = []
    if rank <= TOP:
        bits.append("the highest chase in T20I history" if rank == 1 else f"the {ordinal(rank)}-highest chase in T20I history")
    if beat_loser:
        bits.append(f"the highest ever against {x.loser}")
    elif beat_home:
        bits.append(f"the highest in {home}")
    title = f"{poss(x.winner)} {mine['runs']}: " + ", and ".join(bits)
    helps = []
    if beat_loser and v_loser:
        helps.append(f"Previous best against {x.loser}: {poss(v_loser['bat'])} {v_loser['runs']} ({v_loser['date'][:4]})")
    if beat_home:
        helps.append(f"In {home}: {poss(in_country['bat'])} {in_country['runs']} ({in_country['date'][:4]})")
    c = card("chase-record", "metric_bars", title, {
        "metric": {"label": "runs, successful T20I chases", "format": "int", "signed": False},
        "rows": _record_rows(chases, mine, "bowl"),
    }, x.sample, (". ".join(helps) + ". " if helps else "") + "Full members, men's T20Is.")
    c["facts"] = {"rank": rank, "previous_v_loser": v_loser and v_loser["runs"], "beat_loser": beat_loser,
                  "previous_in_country": in_country and in_country["runs"], "beat_home": beat_home}
    return c


def total_lost(x: Match) -> Optional[Dict[str, Any]]:
    mine = x.mine.get(1)
    if not mine or x.winner is None or x.winner == x.first_bat:
        return None
    lost = [t for t in x.others(1) if t["winner"] and t["winner"] == t["bowl"]]
    rank = 1 + sum(1 for t in lost if t["runs"] > mine["runs"])
    if rank > TOP:
        return None
    big = [t for t in x.others(1) if t["bat"] == x.loser and t["runs"] >= 220]
    beaten = sum(1 for t in big if t["winner"] and t["winner"] != x.loser)
    where = "the highest total ever lost in a T20I" if rank == 1 else f"the {ordinal(rank)}-highest total ever lost in a T20I"
    help_ = (f"Before this, {x.loser} had lost {words(beaten)} in {len(big)} innings of 220 or more batting first. "
             if big else "") + "Full members, men's T20Is."
    if big and beaten == 0:
        help_ = f"Before this, {x.loser} had never lost after making 220 or more batting first ({len(big)} innings). Full members, men's T20Is."
    c = card("total-lost", "metric_bars", f"{poss(x.loser)} {mine['runs']} is {where}", {
        "metric": {"label": "runs batting first, in a defeat", "format": "int", "signed": False},
        "rows": _record_rows(lost, mine, "bowl"),
    }, x.sample, help_)
    c["facts"] = {"rank": rank, "big": len(big), "lost_big": beaten}
    return c


def death_pace(x: Match) -> Optional[Dict[str, Any]]:
    mine = x.mine.get(2)
    if not mine or not x.chased or not mine.get("death_balls"):
        return None
    rate = lambda t: 6 * t["death_runs"] / t["death_balls"]  # noqa: E731
    field = [t for t in x.others(2) if t["winner"] == t["bat"] and (t.get("death_balls") or 0) >= MIN_CELL]
    if mine["death_balls"] < MIN_CELL:
        return None
    rank = 1 + sum(1 for t in field if rate(t) > rate(mine))
    if rank > TOP:
        return None
    top = sorted(field + [mine], key=lambda t: -rate(t))[:SHOW]
    if mine not in top:
        top = top[:SHOW - 1] + [mine]
    rows = [{"name": t["bat"], "value": round(rate(t), 1), "team": t["bat"], "highlight": t is mine,
             "detail": f"{t['death_runs']} off {t['death_balls']} v {abbr(t['bowl'])}, {t['date'][:4]}"} for t in top]
    lead = "the fastest finish" if rank == 1 else f"the {ordinal(rank)}-fastest finish"
    title = f"{x.winner} scored {mine['death_runs']} off their last {mine['death_balls']} balls: {lead} to a T20I chase"
    near = [t for t in top if t is not mine and abs(rate(t) - rate(mine)) < CLOSE]
    if rank == 1 and near:  # a lead this small isn't a record to shout about
        n = near[0]
        title = (f"{x.winner} scored {mine['death_runs']} off their last {mine['death_balls']} balls, level with the "
                 f"fastest finish to a T20I chase ({poss(n['bat'])} {n['death_runs']} off {n['death_balls']}, {n['date'][:4]})")
    return card("death-pace", "metric_bars", title,
                {"metric": {"label": "runs an over, overs 16-20 of a successful chase", "format": "dec1", "signed": False},
                 "rows": rows}, x.sample, f"Full members, men's T20Is since 2015, at least {MIN_CELL} balls.")


def execution(x: Match) -> Optional[Dict[str, Any]]:
    """Good length or yorker share, bowler type x phase (rows), each attack and the T20I norm (columns)."""
    if not x.base:
        return None
    teams = [x.m["team1"], x.m["team2"]]
    cell: Dict[tuple, List[int]] = defaultdict(lambda: [0, 0])
    for b in x.balls:
        if b["length"] and b["bowl_kind"] in dict(KINDS):
            c = cell[(b["team_bowl"], b["bowl_kind"], phase(b["over"]))]
            c[0] += 1; c[1] += b["length"] in GOOD
    rows, gaps = [], []
    for kind, kname in KINDS:
        for ph, pname in PHASES:
            usual = (x.base.get((kind, ph)) or {}).get("good")
            got = {t: cell.get((t, kind, ph), [0, 0]) for t in teams}
            if usual is None or all(n < MIN_CELL for n, _ in got.values()):
                continue
            values, pct = {"usual": round(100 * usual)}, {"usual": 50}
            for i, t in enumerate(teams):
                n, good = got[t]
                v = 100 * good / n if n >= MIN_CELL else None
                values[f"t{i}"] = None if v is None else round(v)
                pct[f"t{i}"] = None if v is None else min(100, round(50 * v / (100 * usual)))
                if v is not None:
                    gaps.append((v - 100 * usual, n))
            rows.append({"name": f"{kname} · {pname}", "short": f"{kname} · {pname}", "values": values, "pct": pct})
    if len(rows) < 2 or not gaps:
        return None
    below = sum(1 for g, _ in gaps if g < -5)
    mean_gap = sum(g * n for g, n in gaps) / sum(n for _, n in gaps)
    if below == len(gaps):
        title = ("Both attacks landed a good length or yorker far less often than T20I bowlers usually do"
                 if mean_gap <= -15 else "Both attacks landed a good length or yorker less often than T20I bowlers usually do")
    elif below == 0:
        title = "Both attacks landed a good length or yorker as often as T20I bowlers usually do"
    else:
        title = f"In {below} of {len(gaps)} spells, the bowlers landed a good length or yorker less often than usual"
    since = (x.day - timedelta(days=365 * BASE_YEARS)).year
    c = card("execution", "scorecard", title, {
        "metrics": [{"key": "t0", "label": teams[0], "format": "pct0"}, {"key": "t1", "label": teams[1], "format": "pct0"},
                    {"key": "usual", "label": "T20I usual", "format": "pct0"}],
        "rows": rows,
        "method": f"% of balls on a good length or yorker. Brighter: nearer the T20I norm (since {since}). –: under {MIN_CELL} balls.",
    }, x.sample, LENGTH_NOTE)
    c["kicker"] = _kicker()
    c["facts"] = {"mean_gap": round(mean_gap, 1), "below": below, "cells": len(gaps)}
    return c


def _sums(balls: List[Dict[str, Any]]) -> Dict[str, float]:
    ctl = [b for b in balls if b["control"] is not None and b["x_ctl"] is not None]
    legal = sum(1 for b in balls if not (b.get("wide") or 0) and not (b.get("noball") or 0))
    return {"runs": sum(b["score"] or 0 for b in balls), "x": sum(b["x_runs"] or 0 for b in balls), "balls": legal,
            "ctl": 100 * sum(b["control"] for b in ctl) / len(ctl) if ctl else None,
            "x_ctl": 100 * sum(b["x_ctl"] for b in ctl) / len(ctl) if ctl else None}


def expected(x: Match) -> Optional[Dict[str, Any]]:
    """Each attack: what its balls usually cost in T20Is against what they went for."""
    if not x.base or not x.innings[1] or not x.innings[2]:
        return None
    by = {b[0]["team_bowl"]: _sums(b) for b in (x.innings[1], x.innings[2])}
    order = [x.loser, x.winner] if x.loser in by else list(by)
    rows = [{"label": f"{poss(t)} bowling", "subject": by[t]["runs"], "field": round(by[t]["x"]),
             "highlight": t == order[0]} for t in order]
    L, W = order[0], order[1]
    title = f"What {L} bowled usually goes for {round(by[L]['x'])}. It went for {by[L]['runs']}"
    ctl = [by[t]["ctl"] for t in order]
    xc = [by[t]["x_ctl"] for t in order]
    help_ = (f"{poss(W)} usually goes for {round(by[W]['x'])}; it went for {by[W]['runs']}. "
             + (f"{poss(L)} batters were in control of {round(ctl[1])}% of balls, {poss(W)} {round(ctl[0])}%; on the same "
                f"deliveries T20I batters manage {round(sum(xc) / 2)}%." if None not in ctl + xc else ""))
    c = card("expected", "deep_compare", title, {
        "metric": {"label": "runs: what they went for, and what the same balls (type, phase, line, length) usually cost",
                   "format": "int", "signed": False},
        "series": ["Went for", "Usually cost"], "rows": rows,
    }, x.sample, help_)
    c["kicker"] = _kicker()
    c["facts"] = {t: {k: (round(v, 1) if isinstance(v, float) else v) for k, v in by[t].items()} for t in order}
    return c


def conditions(x: Match) -> Optional[Dict[str, Any]]:
    """Both innings, both bowler types, against expected; a spin gap is a possible dew sign, said as such."""
    if not x.base:
        return None
    rows, ratio = [], {}
    for kind, kname in KINDS:
        for i in (1, 2):
            balls = [b for b in x.innings[i] if b["bowl_kind"] == kind]
            s = _sums(balls)
            if s["balls"] < MIN_CELL or not s["x"]:
                continue
            ratio[(kind, i)] = s["runs"] / s["x"]
            rows.append({"label": f"{kname}, {x.innings[i][0]['team_bat']} batting", "subject": round(6 * s["runs"] / s["balls"], 1),
                         "field": round(6 * s["x"] / s["balls"], 1), "highlight": False})
    if len(rows) < 2:
        return None
    venue = x.m["venue"]
    before = max((t["runs"] for t in x.totals if t["venue"] == venue and str(t["mid"]) != x.id), default=None)
    place = venue.split(",")[-1].strip() if "," in venue else venue
    s1, s2 = ratio.get(("spin bowler", 1)), ratio.get(("spin bowler", 2))
    p1, p2 = ratio.get(("pace bowler", 1)), ratio.get(("pace bowler", 2))
    chaser = x.innings[2][0]["team_bat"]
    if s1 and s2 and s2 - s1 >= DEW_GAP:
        title = f"Spin went for {s2:.1f} times its usual cost in the chase, {s1:.1f} times in {poss(x.first_bat)} innings"
        lead = "A gap like that fits dew, which the data can't see."
        for r in rows:
            r["highlight"] = r["label"] == f"Spin, {chaser} batting"
    else:
        r1 = _sums(x.innings[1]); r2 = _sums(x.innings[2])
        title = (f"Both innings went for more than the balls usually cost: {r1['runs'] / r1['x']:.1f} and "
                 f"{r2['runs'] / r2['x']:.1f} times")
        lead = "It was the night as much as either attack."
    pace = f" Pace went for {p1:.1f} and {p2:.1f} times its usual." if p1 and p2 else ""
    ground = (f" Before this match, {poss(place)} highest men's T20I score was {before}." if before else "")
    c = card("conditions", "deep_compare", title, {
        "metric": {"label": "runs an over: what each type went for, and what the same balls usually cost",
                   "format": "dec1", "signed": False},
        "series": ["Went for", "Usually cost"], "rows": rows,
    }, x.sample, f"{lead}{pace}{ground} {DEW_LINE}")
    c["kicker"] = _kicker()
    c["facts"] = {"ratios": {f"{k[0]}-{k[1]}": round(v, 2) for k, v in ratio.items()}, "ground_before": before}
    return c


def wp_line(x: Match) -> Optional[Dict[str, Any]]:
    """The loser's win probability through the second innings, the overs that moved it most annotated."""
    if not x.loser or not x.innings[2]:
        return None
    chase = x.innings[2]
    if sum(1 for b in chase if b["win_prob"] is not None) < 0.9 * len(chase):
        return None
    start = next((x.loser_wp(b) for b in reversed(x.innings[1]) if b["win_prob"] is not None), None)
    points, overs = [], {}
    prev, legal = start, 0
    for b in chase:
        wp = x.loser_wp(b)
        wp = prev if wp is None else wp
        legal += 0 if (b.get("wide") or b.get("noball")) else 1
        points.append({"wp": round(wp, 1), "label": f"{b['over']}.{max(1, legal - 6 * b['over'])}",
                       "score": f"{b['inns_runs']}/{b['inns_wkts']}", "over": b["over"]})
        o = overs.setdefault(b["over"], {"over": b["over"], "from": prev, "runs": 0, "x": 0.0, "bat": defaultdict(int),
                                         "i0": len(points) - 1})
        o["to"], o["i1"] = wp, len(points) - 1
        o["runs"] += b["score"] or 0
        o["x"] += b["x_runs"] or 0
        o["bat"][b["bat"]] += b["score"] or 0
        prev = wp
    if start is None or not points:
        return None
    drops = sorted((o for o in overs.values() if o["from"] - o["to"] >= SWING), key=lambda o: o["to"] - o["from"])[:MAX_SWINGS]
    biggest = max((o["from"] - o["to"] for o in overs.values()), default=0)
    peak = max([start] + [p["wp"] for p in points])
    if biggest < BIG_SWING and peak < PEAK:
        return None
    drops.sort(key=lambda o: o["over"])
    bands = []
    for o in drops:
        hitters = [short(n) for n, r in sorted(o["bat"].items(), key=lambda kv: -kv[1]) if r > 0][:2]
        who = " & ".join(hitters) or "the batters"
        usual = f" off balls that usually go for {round(o['x'])}" if x.base else ""
        bands.append({"i0": o["i0"], "i1": o["i1"], "over": o["over"] + 1, "from": round(o["from"]), "to": round(o["to"]),
                      "text": f"Over {o['over'] + 1}: {who} hit {o['runs']}{usual}"})
    first = drops[0] if drops else None
    if first:
        before = round(first["from"])
        title = (f"{x.loser} were {before}% favourites after {first['over']} overs, until "
                 f"{number(len(drops))} overs swung it" if len(drops) > 1 else
                 f"{x.loser} were {before}% favourites after {first['over']} overs, until one over swung it")
    else:
        title = f"{x.loser} were {round(peak)}% favourites at one point of the chase"
    c = card("wp-line", "win_prob_line", title, {
        "team": x.loser, "start": round(start, 1), "points": points, "bands": bands,
        "label": f"{x.loser}'s chance of winning",
    }, x.sample, f"{x.loser}'s win probability, ball by ball (T20 Primer method). Shaded: the overs that moved it most,"
                 " and who did it.")
    c["facts"] = {"peak": round(peak, 1), "biggest": round(biggest, 1), "swings": [(b["over"], b["from"], b["to"]) for b in bands]}
    return c


def _kicker() -> str:
    from services.ig_posts.deep_cut import KICKER

    return KICKER


# ---- the post ---------------------------------------------------------------------------------------------------

def special(db: Session, m: Dict[str, Any], label: str) -> Optional[Dict[str, Any]]:
    """The special recap's cards for a men's T20I, or None (the usual recap then)."""
    from services.ig_posts.match import innings_scorecards

    if m.get("format") != "T20" or not m.get("winner"):
        return None
    sample = f"{label} · {m['date']:%d %b %Y}"
    x = Match(db, m, sample)
    if not x.innings[1] or not x.innings[2]:
        return None
    chase, lost, wp = chase_record(x), total_lost(x), wp_line(x)
    if not (chase or lost) or not wp:
        return None
    deep = [c for c in (execution(x), expected(x)) if c]
    cond = conditions(x)
    cards = [c for c in [chase or lost, *deep, wp, cond, death_pace(x), lost if chase else None] if c]
    cards += innings_scorecards(db, x.id, sample)
    target = x.mine[1]["runs"] + 1 if 1 in x.mine else None
    if chase and chase["facts"]["beat_loser"] and chase["facts"]["previous_v_loser"]:
        hook = (f"Nobody had chased more than {chase['facts']['previous_v_loser']} against {x.loser} in a T20I. "
                f"{x.winner} just chased {target}.")
    elif chase:
        hook = f"{x.winner} just chased {target}: {chase['title'].split(': ', 1)[1]}."
    else:
        hook = f"{x.loser} made {x.mine[1]['runs']} and lost."
    exp = next((c for c in deep if c["id"] == "expected"), None)
    lead = deep[0] if deep else None
    deep_cut = ({"probe": f"recap-{lead['id']}", "subject": None, "sentence": lead["title"] + ".", "by": "recap"}
                if lead else None)
    players = []
    for i in (1, 2):
        runs = defaultdict(int)
        for b in x.innings[i]:
            runs[b["bat"]] += b["score"] or 0
        if runs:
            players.append(max(runs, key=runs.get))
    verdict = (chase or lost)["title"] + "." + (f" {exp['title']}." if exp else "")
    since = (x.day - timedelta(days=365 * BASE_YEARS)).year
    return {"hook": hook, "sub": "Was it the bowling? What the ball-by-ball says", "kicker": label, "cards": cards,
            "title": (chase or lost)["title"], "verdict": verdict, "players": players,
            "teams": [m["team1"], m["team2"]], "day": m["date"], "deep_cut": deep_cut, "special": True,
            "method": (f"expected runs give each ball the average of men's T20I balls of the same bowler type, phase, "
                       f"line and length since {since}; win probability is ball by ball (T20 Primer method).")}
