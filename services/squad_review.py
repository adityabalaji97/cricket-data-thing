"""
Squad reviews: rate a T20 squad as a team that has to fill an XI, not as a list of names.

    review(db, league, squad, as_of)  ->  {score, bat, bowl, xi, overs, depth, unproven, values}

1. Each player's value by phase from every men's T20 in the two years before `as_of` (leagues, domestic and
   T20Is): batting Impact per 100 balls, bowling Impact per over (bowling view). Each is pulled toward zero (the
   average ball) by its sample, so 40 balls can't top a table: value = impact / (balls + K).
2. The best XI under the league's overseas cap: the batting order gets the league's typical balls per slot and
   phase; the 20 overs go 6 powerplay / 9 middle / 5 death, at most 4 a bowler. Overs no one in the XI has bowled
   are a part-timer's, at PART_TIMER runs an over.
3. Score = projected runs above the average ball per match (values are measured against the average ball in each
   phase, batting and bowling view: raw Impact leans toward the bowler): batting slots plus bowling overs.
4. Depth: what the score loses when each of the XI's best few is missing.

Every number comes from the query builder (services.query_builder_v2.run_deliveries_query).
"""
from __future__ import annotations

import itertools
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

PHASES = ("powerplay", "middle", "death")
OVERS = {"powerplay": 6, "middle": 9, "death": 5}
MAX_OVERS = 4
K_BAT = 120          # balls of evidence before a batter's own rate counts for half
K_BOWL = 120         # same, bowling
PART_TIMER = -1.5    # runs an over (Impact, bowling view) for overs nobody in the XI has bowled
# A player starts below average and earns his way up: the prior a thin record is pulled toward, per ball above the
# average ball. Unknown players were being picked as exactly average over known, slightly-below-average ones.
PRIOR_BAT = -0.05    # -5 runs per 100 balls
PRIOR_BOWL = -0.05   # -0.3 runs an over (bowling view)
UNPROVEN_BALLS = 150 # fewer balls batting and bowling than this in the window: "unproven"
WINDOW_DAYS = 730

LEAGUES: Dict[str, Dict[str, Any]] = {
    "SA20": {"comps": ["SA20"], "overseas_max": 4, "home": "South Africa",
             "home_domestic": ["CSA T20 Challenge", "CSA T20", "CSA Pro20 Cup", "CSA Provincial T20 Challenge",
                               "Ram Slam T20", "Ram Slam T20 Challenge", "Africa T20 Cup"]},
    "IPL": {"comps": ["IPL", "Indian Premier League"], "overseas_max": 4, "home": "India",
            "home_domestic": ["SMAT", "Syed Mushtaq Ali Trophy", "SMA TROPHY", "SMA TROPHY FINAL"]},
}


def _q(db, **args) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    base = {"fmt": "T20", "gender": "male", "limit": 10000, "leagues": [], "include_international": False}
    return run_deliveries_query(db, **{**base, **args}).get("data") or []


# ---- inputs -----------------------------------------------------------------------------------------------------------

def baselines(db, as_of: date) -> Dict[str, Dict[str, float]]:
    """Impact of the average ball by phase, batting and bowling view, in the window: raw Impact leans toward the
    bowler (an average ball is below zero for the batter), so every value is measured against these."""
    start, end = as_of - timedelta(days=WINDOW_DAYS), as_of - timedelta(days=1)
    out: Dict[str, Dict[str, float]] = {"bat": {}, "bowl": {}}
    for side, view in (("bat", "batting"), ("bowl", "bowling")):
        for r in _q(db, group_by=["phase"], start_date=start, end_date=end, metrics_perspective=view):
            if r.get("balls"):
                out[side][r["phase"]] = (r.get("impact") or 0) / r["balls"]
    return out


def player_values(db, players: List[str], as_of: date) -> Dict[str, Dict[str, Any]]:
    """{player: {bat: {phase: (impact above the average ball, balls)}, bowl: {...}, bat_balls, bowl_balls, pos}} from
    the window."""
    start, end = as_of - timedelta(days=WINDOW_DAYS), as_of - timedelta(days=1)
    base = baselines(db, as_of)
    out: Dict[str, Dict[str, Any]] = {p: {"bat": {}, "bowl": {}, "bat_balls": 0, "bowl_balls": 0, "pos": None, "kind": None}
                                      for p in players}
    bat = _q(db, batters=players, group_by=["batter", "phase"], start_date=start, end_date=end, metrics_perspective="batting")
    bowl = _q(db, bowlers=players, group_by=["bowler", "phase"], start_date=start, end_date=end, metrics_perspective="bowling")
    pos = _q(db, batters=players, group_by=["batter", "batting_position"], start_date=start, end_date=end)
    kinds = _q(db, bowlers=players, group_by=["bowler", "bowl_kind"], start_date=start, end_date=end, metrics_perspective="bowling")
    canon = _canon(db, players)
    most: Dict[str, Tuple[int, str]] = {}
    for r in kinds:
        p = canon.get(r["bowler"], r["bowler"])
        if p in out and r.get("bowl_kind") in ("pace bowler", "spin bowler") and (r.get("balls") or 0) > most.get(p, (0, ""))[0]:
            most[p] = (r["balls"], "pace" if r["bowl_kind"] == "pace bowler" else "spin")
    for p, (_b, k) in most.items():
        out[p]["kind"] = k
    for r in bat:
        p = canon.get(r["batter"], r["batter"])
        if p in out:
            b = r.get("balls") or 0
            out[p]["bat"][r["phase"]] = ((r.get("impact") or 0) - base["bat"].get(r["phase"], 0) * b, b)
            out[p]["bat_balls"] += r.get("balls") or 0
    for r in bowl:
        p = canon.get(r["bowler"], r["bowler"])
        if p in out:
            b = r.get("balls") or 0
            out[p]["bowl"][r["phase"]] = ((r.get("impact") or 0) - base["bowl"].get(r["phase"], 0) * b, b)
            out[p]["bowl_balls"] += r.get("balls") or 0
    inns: Dict[str, Dict[int, int]] = {}
    for r in pos:
        p = canon.get(r["batter"], r["batter"])
        if p in out and r.get("batting_position"):
            inns.setdefault(p, {})[int(r["batting_position"])] = r.get("innings_count") or 0
    for p, d in inns.items():
        total = sum(d.values())
        out[p]["pos"] = sum(k * v for k, v in d.items()) / total if total else None
    return out


def _canon(db, asked: List[str]) -> Dict[str, str]:
    """The ball-by-ball name of each player asked for, back to the name asked (a squad list may spell it otherwise)."""
    from services.player_aliases import resolve_to_details_name

    out = {}
    for a in asked:
        try:
            out[resolve_to_details_name(a, db)] = a
        except Exception:  # pragma: no cover - unknown name: as asked
            out[a] = a
    return out


def slot_balls(db, league: str, as_of: date) -> Dict[int, Dict[str, float]]:
    """{batting position: {phase: average balls an innings}} across every men's T20 in the three years before: how
    balls fall by position is much the same everywhere, and a league's first season has no history of its own."""
    rows = _q(db, group_by=["batting_position", "phase"], start_date=as_of - timedelta(days=3 * 365),
              end_date=as_of - timedelta(days=1))
    innings = max((r.get("innings_count") or 0) for r in rows if r.get("batting_position") == 1) if rows else 0
    out: Dict[int, Dict[str, float]] = {}
    for r in rows:
        if r.get("batting_position") and innings:
            out.setdefault(int(r["batting_position"]), {})[r["phase"]] = (r.get("balls") or 0) / innings
    return out


# ---- the model --------------------------------------------------------------------------------------------------------

def bat_value(v: Dict[str, Any], phase: str) -> float:
    """Impact per ball above the average ball in a phase, from the phase's own record, pulled toward PRIOR_BAT."""
    imp, balls = v["bat"].get(phase, (0.0, 0))
    return (imp + PRIOR_BAT * K_BAT) / (balls + K_BAT)


def bowl_value(v: Dict[str, Any], phase: str) -> Optional[float]:
    """Impact an over in a phase, pulled toward 0; None if he hasn't bowled (overs go to those who have)."""
    if not v["bowl_balls"]:
        return None
    imp, balls = v["bowl"].get(phase, (0.0, 0))  # the phase on its own: a spinner who never bowls at the death isn't
    return 6 * (imp + PRIOR_BOWL * K_BOWL) / (balls + K_BOWL)  # handed death overs on his middle-overs record


def bowling(xi: List[str], values: Dict[str, Dict[str, Any]]) -> Tuple[float, Dict[str, Dict[str, int]]]:
    """The 20 overs, greedily to the best (bowler, phase) pairs: (runs, {bowler: {phase: overs}})."""
    left = dict(OVERS)
    cap = {p: MAX_OVERS for p in xi}
    pairs = sorted(((bowl_value(values[p], ph), p, ph) for p in xi for ph in PHASES if bowl_value(values[p], ph) is not None),
                   key=lambda x: -x[0])
    plan: Dict[str, Dict[str, int]] = {}
    total = 0.0
    for val, p, ph in pairs:
        n = min(left[ph], cap[p])
        if n <= 0:
            continue
        left[ph] -= n
        cap[p] -= n
        plan.setdefault(p, {})[ph] = plan.get(p, {}).get(ph, 0) + n
        total += n * val
    total += sum(left.values()) * PART_TIMER
    return total, plan


def batting(xi: List[str], values: Dict[str, Dict[str, Any]], slots: Dict[int, Dict[str, float]]) -> Tuple[float, List[str]]:
    """The XI in batting order (usual position; bowlers with no batting record last): (runs, order)."""
    order = sorted(xi, key=lambda p: (values[p]["pos"] if values[p]["pos"] is not None else 9.5,
                                      -values[p]["bat_balls"]))
    total = 0.0
    for i, p in enumerate(order, 1):
        for ph, b in slots.get(i, {}).items():
            total += b * bat_value(values[p], ph)
    return total, order


def evaluate(xi, values, slots) -> Tuple[float, float, float, List[str], Dict[str, Dict[str, int]]]:
    b, order = batting(xi, values, slots)
    w, plan = bowling(xi, values)
    return b + w, b, w, order, plan


def best_xi(squad: List[str], overseas: set, values, slots, cap: int) -> Tuple[List[str], Tuple]:
    """A hill-climb over swaps from a sensible start, keeping at most `cap` overseas players."""
    def ok(xi):
        return sum(1 for p in xi if p in overseas) <= cap

    def solo(p):  # a rough individual worth, for the start
        v = values[p]
        bat = sum(b * bat_value(v, ph) for ph, b in {"powerplay": 9, "middle": 9, "death": 4}.items())
        bw = max((bowl_value(v, ph) or 0) for ph in PHASES) * 4 if v["bowl_balls"] else 0
        return bat + bw

    ranked = sorted(squad, key=lambda p: -solo(p))
    xi: List[str] = []
    for p in ranked:
        if len(xi) < 11 and ok(xi + [p]):
            xi.append(p)
    if len(xi) < 11:
        xi += [p for p in ranked if p not in xi][: 11 - len(xi)]
    best = evaluate(xi, values, slots)
    improved = True
    while improved:
        improved = False
        for out_p, in_p in itertools.product(list(xi), [p for p in squad if p not in xi]):
            cand = [p for p in xi if p != out_p] + [in_p]
            if not ok(cand):
                continue
            got = evaluate(cand, values, slots)
            if got[0] > best[0] + 1e-9:
                xi, best, improved = cand, got, True
                break
    return xi, best


def review(db, league: str, squad: List[str], as_of: date, overseas: Optional[Iterable[str]] = None,
           values: Optional[Dict[str, Dict[str, Any]]] = None, slots: Optional[Dict[int, Dict[str, float]]] = None,
           depth_n: int = 3) -> Dict[str, Any]:
    cfg = LEAGUES[league]
    values = values or player_values(db, squad, as_of)
    slots = slots or slot_balls(db, league, as_of)
    over = set(overseas if overseas is not None else [])
    xi, (score, bat, bowl, order, plan) = best_xi(squad, over, values, slots, cfg["overseas_max"])
    # Depth: the score without each of the XI's most valuable players, re-picked.
    worth = {p: score - best_xi([q for q in squad if q != p], over, values, slots, cfg["overseas_max"])[1][0] for p in xi}
    depth = sorted(worth.items(), key=lambda kv: -kv[1])[:depth_n]
    unproven = [p for p in squad if values[p]["bat_balls"] < UNPROVEN_BALLS and values[p]["bowl_balls"] < UNPROVEN_BALLS]
    return {"score": score, "bat": bat, "bowl": bowl, "xi": order, "overs": plan, "depth": depth,
            "unproven": unproven, "values": values, "phases": phase_split(order, plan, values, slots),
            "kinds": kind_split(plan, values)}


# ---- describing a squad (no ranking: the backtest showed the total doesn't order a table) ------------------------------

def phase_split(xi_order: List[str], plan: Dict[str, Dict[str, int]], values, slots) -> Dict[str, Dict[str, float]]:
    """The XI's projected runs above average by phase: batting (slots) and bowling (the overs plan)."""
    bat = {ph: 0.0 for ph in PHASES}
    for i, p in enumerate(xi_order, 1):
        for ph, b in slots.get(i, {}).items():
            bat[ph] += b * bat_value(values[p], ph)
    bowl = {ph: 0.0 for ph in PHASES}
    for p, by in plan.items():
        for ph, n in by.items():
            bowl[ph] += n * (bowl_value(values[p], ph) or 0)
    return {"bat": bat, "bowl": bowl}


def kind_split(plan: Dict[str, Dict[str, int]], values) -> Dict[str, Dict[str, float]]:
    """Overs and projected runs above average by pace and spin in the XI's plan."""
    out = {"pace": {"overs": 0, "runs": 0.0}, "spin": {"overs": 0, "runs": 0.0}}
    for p, by in plan.items():
        k = values[p].get("kind") or "pace"
        for ph, n in by.items():
            out[k]["overs"] += n
            out[k]["runs"] += n * (bowl_value(values[p], ph) or 0)
    return out


def ground_profile(db, names: List[str], since: date) -> Dict[str, Any]:
    """Pace and spin at a ground (every men's T20 since `since`, all its names): runs an over, balls a wicket, share
    of the balls."""
    rows = []
    for n in names:
        rows += _q(db, venue=n, group_by=["bowl_kind"], start_date=since, metrics_perspective="bowling")
    out: Dict[str, Any] = {}
    total = sum(r.get("balls") or 0 for r in rows if r.get("bowl_kind") in ("pace bowler", "spin bowler"))
    for k, key in (("pace", "pace bowler"), ("spin", "spin bowler")):
        rs = [r for r in rows if r.get("bowl_kind") == key]
        b = sum(r.get("balls") or 0 for r in rs)
        w = sum(r.get("wickets") or 0 for r in rs)
        out[k] = {"econ": 6 * sum(r.get("runs") or 0 for r in rs) / b if b else None, "bpw": b / w if w else None,
                  "share": b / total if total else None, "balls": b}
    return out


# ---- the likely XI: what the team did, not what an optimiser would do ---------------------------------------------------
# A best-XI search over small samples left Rashid Khan without an over (19 Oct 2026). The XI is the team's own: its most
# used players last season, with the gaps filled by its new buys; overs follow how each bowler is actually used.

def appearances(db, comps: List[str], team: str, start: date, end: date) -> Dict[str, int]:
    """Games each player played for `team` in [start, end] (match_players, the scorecard XIs)."""
    from sqlalchemy import text

    rows = db.execute(text("""
        SELECT mp.player, COUNT(*) FROM match_players mp JOIN matches m ON m.id = mp.match_id
        WHERE m.competition = ANY(:c) AND mp.team = :t AND m.date BETWEEN :a AND :b GROUP BY 1
    """), {"c": comps, "t": team, "a": start, "b": end}).all()
    return {p: n for p, n in rows}


def role(v: Dict[str, Any]) -> str:
    """batter / bowler / all-rounder from the window's balls (a bowler who bats little is a bowler)."""
    bat, bowl = v["bat_balls"], v["bowl_balls"]
    if bowl >= 120 and bat >= 120 and (v["pos"] or 9) <= 7.5:
        return "all-rounder"
    return "bowler" if bowl >= max(bat, 60) else "batter"


REGULAR_APPS = 4     # games last season to count as a regular (about a third of a season)


def likely_xi(squad: List[str], overseas: set, values, apps: Dict[str, int], cap: int) -> List[str]:
    """Last season's regulars still in the squad (REGULAR_APPS+ games, most first), then the most established of the
    rest (T20 balls in the window: a marquee buy over a fringe player), keeping at most `cap` overseas and at least
    five who bowl."""
    proven = lambda p: values[p]["bat_balls"] + values[p]["bowl_balls"]  # noqa: E731
    order = sorted(squad, key=lambda p: (apps.get(p, 0) < REGULAR_APPS, -apps.get(p, 0) if apps.get(p, 0) >= REGULAR_APPS else 0,
                                         -proven(p)))
    xi: List[str] = []
    for p in order:
        if len(xi) == 11:
            break
        if p in overseas and sum(1 for q in xi if q in overseas) >= cap:
            continue
        xi.append(p)
    bowlers = [p for p in xi if role(values[p]) in ("bowler", "all-rounder")]
    for p in [q for q in order if q not in xi and role(values[q]) == "bowler"]:
        if len(bowlers) >= 5:
            break
        drop = next((q for q in reversed(xi) if role(values[q]) == "batter"), None)
        if drop is None or (p in overseas and drop not in overseas and sum(1 for q in xi if q in overseas) >= cap):
            continue
        xi[xi.index(drop)] = p
        bowlers.append(p)
    return xi


def usage_overs(xi: List[str], values) -> Dict[str, Dict[str, int]]:
    """The 20 overs shared as the XI's bowlers are used: each gets overs in each phase in proportion to the balls he
    has bowled there, at most 4 a bowler and the phase's overs in all."""
    left = dict(OVERS)
    cap = {p: MAX_OVERS for p in xi}
    weight = {(p, ph): values[p]["bowl"].get(ph, (0, 0))[1] for p in xi for ph in PHASES}
    plan: Dict[str, Dict[str, int]] = {}
    for ph in PHASES:
        while left[ph] > 0:
            cands = [(weight[(p, ph)] / (1 + plan.get(p, {}).get(ph, 0)), p) for p in xi if cap[p] > 0 and weight[(p, ph)] > 0]
            if not cands:
                break
            _w, p = max(cands)
            plan.setdefault(p, {})[ph] = plan.get(p, {}).get(ph, 0) + 1
            cap[p] -= 1
            left[ph] -= 1
    return plan


def identity_flags(db, names: List[str], as_of: date, home: str, overseas: Iterable[str] = ()) -> Dict[str, List[str]]:
    """Names that look like two players under one name (the data has no player ids): a local who has played for a
    foreign national side, or anyone who has played for two national sides."""
    from models import INTERNATIONAL_TEAMS_RANKED

    nations = set(INTERNATIONAL_TEAMS_RANKED) | {"Philippines", "Hong Kong", "Japan", "Cayman Islands", "Bermuda"}
    start = as_of - timedelta(days=WINDOW_DAYS)
    teams: Dict[str, set] = {n: set() for n in names}
    for r in _q(db, batters=names, group_by=["batter", "batting_team"], start_date=start, end_date=as_of):
        teams.setdefault(r["batter"], set()).add(r["batting_team"])
    for r in _q(db, bowlers=names, group_by=["bowler", "bowling_team"], start_date=start, end_date=as_of,
                metrics_perspective="bowling"):
        teams.setdefault(r["bowler"], set()).add(r["bowling_team"])
    over = set(overseas)
    out = {}
    for n, ts in teams.items():
        nat = {t for t in ts if t in nations}
        if len(nat) > 1 or (n not in over and nat - {home}):
            out[n] = sorted(ts)
    return out


def describe(db, league: str, team: str, squad: List[str], overseas: Iterable[str], as_of: date, last: Tuple[date, date],
             values, slots) -> Dict[str, Any]:
    """The team's likely XI with each player's role and value by phase, its overs, phase totals and pace/spin split."""
    cfg = LEAGUES[league]
    over = set(overseas)
    apps = appearances(db, cfg["comps"], team, *last)
    xi = likely_xi(squad, over, values, apps, cfg["overseas_max"])
    _b, order = batting(xi, values, slots)
    plan = usage_overs(xi, values)
    players = [{"name": p, "role": role(values[p]), "overseas": p in over, "apps_last": apps.get(p, 0),
                "bat_balls": values[p]["bat_balls"], "bowl_balls": values[p]["bowl_balls"],
                "bat": {ph: 100 * bat_value(values[p], ph) for ph in PHASES},
                "bowl": {ph: bowl_value(values[p], ph) for ph in PHASES} if values[p]["bowl_balls"] else None}
               for p in order]
    return {"xi": order, "players": players, "overs": plan, "phases": phase_split(order, plan, values, slots),
            "kinds": kind_split(plan, values),
            "unproven": [p for p in squad if values[p]["bat_balls"] < UNPROVEN_BALLS and values[p]["bowl_balls"] < UNPROVEN_BALLS]}
