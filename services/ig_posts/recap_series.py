"""
The series recap: a men's T20I played inside a bilateral series (the sides' 2nd+ meeting in SERIES_DAYS) gets a
carousel that reads the match against the series, built from what the match page's summary screen shows:

  how         "How it was won": the match page's recap card (services/match_recap.build_recap), headline and bullets
  wp          the loser's win probability through the chase, the overs that moved it most annotated with the bowler
              and the wickets (recap_special.Match; no record gate here)
  race        both innings' scores over by over (the summary's momentum worm): where the chase was level or ahead,
              and how the last overs split
  plan        the winners' top scorer against pace: how often this match's pacers landed each length, against how
              often pacers have landed it to him over PLAN_YEARS (the scorecard's Line/Length tab, with his history)
  attacks     both attacks by kind: economy, how often they landed their length (good length for spin; good length
              or yorker for pace) and full tosses, side by side (said with recap_special.LENGTH_NOTE)
  series      the series' batters by Impact, both sides (runs, balls and strike rate as detail)
  pace_spin   the winners' top three in the series: strike rate against pace and against spin (the scorecard's
              Pace / Spin tab, over the series)

Every number comes from delivery_details, the query builder or the scorecard service; nothing is typed in.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.ig_posts.cards import card, fmt
from services.ig_posts.recap_special import LENGTH_NOTE, Match, number, poss
from services.ig_posts.spotlight import short_name

SERIES_DAYS = 30
PLAN_YEARS = 3          # the batter's history against pace: this many years before the match
MIN_HISTORY = 150       # balls from pace in that history before the plan card is drawn
MIN_PLAN = 20           # balls from pace in this match
SWINGS = 3              # overs annotated on the win-probability line
MIN_SWING = 5           # points of win probability an annotated over must move
SERIES_TOP = 6
PACE_SPIN_MIN = 10      # balls of each kind for a batter's pace/spin row
LENGTHS = {"GOOD_LENGTH": "Good length", "FULL": "Full", "FULL_TOSS": "Full toss", "YORKER": "Yorker",
           "SHORT_OF_A_GOOD_LENGTH": "Back of a length", "SHORT": "Short"}


def series_matches(db: Session, m: Dict[str, Any]) -> List[str]:
    """This match and the sides' earlier men's T20s in the last SERIES_DAYS, oldest first."""
    rows = db.execute(text("""
        SELECT id FROM matches
        WHERE ((team1 = :a AND team2 = :b) OR (team1 = :b AND team2 = :a)) AND format = 'T20' AND gender = 'male'
          AND date > :since AND date <= :day
        ORDER BY date, id
    """), {"a": m["team1"], "b": m["team2"], "since": m["date"] - timedelta(days=SERIES_DAYS), "day": m["date"]})
    return [str(r[0]) for r in rows]


def series_score(db: Session, ids: List[str], a: str, b: str) -> str:
    wins = defaultdict(int)
    for (w,) in db.execute(text("SELECT winner FROM matches WHERE id = ANY(:ids)"), {"ids": ids}):
        if w:
            wins[w] += 1
    if wins[a] == wins[b]:
        return f"series level {wins[a]}-{wins[b]}"
    lead, trail = (a, b) if wins[a] > wins[b] else (b, a)
    return f"{lead} lead {wins[lead]}-{wins[trail]}"


# ---- cards ------------------------------------------------------------------------------------------------------

def mark_wickets(balls: List[Dict[str, Any]]) -> None:
    """b["wkt"]: the ball took a wicket, by the innings' wicket count (delivery_details.out is also 'True' for a
    batter retiring hurt, which the scorecard doesn't count)."""
    prev = {}
    for b in balls:
        b["wkt"] = (b["inns_wkts"] or 0) > prev.get(b["inns"], 0)
        prev[b["inns"]] = b["inns_wkts"] or 0


def how_it_was_won(db: Session, x: Match, sc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The match page's "How it was won" card, as it reads on the site."""
    from services.match_recap import build_recap

    if not (sc.get("summary") or {}).get("primer"):
        return None
    recap = build_recap(sc, db)
    if not recap.get("available"):
        return None
    return card("how", "recap_text", "How it was won", {"headline": recap["headline"], "bullets": recap["bullets"]},
                x.sample, "Impact: runs added to (or saved from) the expected total. Win probability: T20 Primer method.")


def wp_swings(x: Match, sc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The loser's chance through the chase, the SWINGS overs that cut it most annotated: bowler, wickets, runs.
    The win probability is the match page's (the scorecard's T20 Primer points, drawn for the side batting first),
    so the post and the site's chart agree."""
    wp_all = ((sc.get("summary") or {}).get("primer") or {}).get("win_probability")
    if not x.loser or not x.innings[2] or not wp_all:
        return None
    chase = x.innings[2]
    brk = wp_all["innings_break"]
    after = wp_all["points"][brk + 1:]
    if len(after) != len(chase) or len(wp_all["points"]) != brk + len(chase) + 1:
        return None  # the primer's balls don't line up with the feed's: no chart rather than a shifted one
    mine = (lambda p: 100 * p) if wp_all["team"] == x.loser else (lambda p: 100 * (1 - p))
    start = mine(wp_all["points"][brk])
    points, overs, prev, legal = [], {}, start, 0
    for b, p in zip(chase, after):
        wp = mine(p)
        legal += 0 if (b.get("wide") or b.get("noball")) else 1
        points.append({"wp": round(wp, 1), "label": f"{b['over']}.{max(1, legal - 6 * b['over'])}",
                       "score": f"{b['inns_runs']}/{b['inns_wkts']}", "over": b["over"]})
        o = overs.setdefault(b["over"], {"over": b["over"], "from": prev, "runs": 0, "outs": [], "bowl": b["bowl"],
                                         "i0": len(points) - 1})
        o["to"], o["i1"] = wp, len(points) - 1
        o["runs"] += b["score"] or 0
        if b["wkt"]:
            o["outs"].append(short_name(b["bat"]))
        prev = wp
    chasing = chase[0]["team_bat"]
    drops = sorted((o for o in overs.values() if o["from"] - o["to"] >= MIN_SWING),
                   key=lambda o: o["to"] - o["from"])[:SWINGS]
    if not drops:
        return None
    drops.sort(key=lambda o: o["over"])
    bands = []
    for o in drops:
        bowler = short_name(o["bowl"]) if o["bowl"] else "the bowler"
        what = (f"{bowler} removed {' & '.join(o['outs'])}" if o["outs"] else f"{bowler}, {o['runs']} runs")
        bands.append({"i0": o["i0"], "i1": o["i1"], "over": o["over"] + 1, "from": round(o["from"]),
                      "to": round(o["to"]), "bowler": bowler, "text": what})
    peak = max([start] + [p["wp"] for p in points])
    if chasing == x.loser:
        title = (f"{x.loser} never had better than a {round(peak)}% chance: {number(len(bands))} overs of wickets "
                 f"took it away" if peak < 50 else
                 f"{x.loser} peaked at {round(peak)}%, then {number(len(bands))} overs took it away")
    else:
        title = f"{poss(x.loser)} chance through the chase: {number(len(bands))} overs decided it"
    c = card("wp-swings", "win_prob_line", title, {
        "team": x.loser, "start": round(start, 1), "points": points, "bands": bands,
        "label": f"{poss(x.loser)} chance of winning",
    }, x.sample, f"{poss(x.loser)} win probability, ball by ball (T20 Primer method). Shaded: the overs that cut it most.")
    c["facts"] = {"peak": round(peak, 1), "swings": [(b["over"], b["from"], b["to"], b["text"]) for b in bands]}
    return c


def score_race(x: Match) -> Optional[Dict[str, Any]]:
    """Both innings' running scores by over (the summary's worm), with wickets; the title says where the chase stood."""
    lines = []
    for i in (1, 2):
        runs, wkts, by = 0, 0, {}
        for b in x.innings[i]:
            runs += b["score"] or 0
            wkts += 1 if b["wkt"] else 0
            by[b["over"]] = (runs, wkts)
        lines.append({"team": x.innings[i][0]["team_bat"], "values": [by[o][0] for o in sorted(by)],
                      "wickets": [by[o][1] for o in sorted(by)]})
    a, b = lines
    n = min(len(a["values"]), len(b["values"]))
    level = [o for o in range(n) if b["values"][o] >= a["values"][o]]
    if not level or n < 18:
        return None
    last = level[-1]  # the last over (0-based) where the chase was level or ahead
    if last >= n - 1:
        return None
    tail_a = a["values"][-1] - a["values"][last]
    tail_b = b["values"][n - 1] - b["values"][last]
    wk_a = a["wickets"][-1] - a["wickets"][last]
    wk_b = b["wickets"][n - 1] - b["wickets"][last]
    o = last + 1
    title = (f"{b['team']} were {'ahead' if b['values'][last] > a['values'][last] else 'level'} after {o} overs. "
             f"The last {len(a['values']) - o} went {tail_a}/{wk_a} to {tail_b}/{wk_b}")
    c = card("race", "score_race", title, {"series": lines, "mark": o},
             x.sample, "Score at the end of every over. Dots: wickets.")
    c["facts"] = {"over": o, "first": [a["values"][last], a["wickets"][last]], "chase": [b["values"][last],
                  b["wickets"][last]], "tail": [tail_a, wk_a, tail_b, wk_b]}
    return c


def _shares(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    total = sum(r["balls"] for r in rows) or 1
    by = defaultdict(int)
    for r in rows:
        by[r["length"]] += r["balls"]
    return {k: 100 * v / total for k, v in by.items()} | {"_n": total}


def length_plan(db: Session, x: Match) -> Optional[Dict[str, Any]]:
    """The winners' top scorer against pace: lengths this match against his history (PLAN_YEARS before it)."""
    from services.query_builder_v2 import run_deliveries_query

    if not x.winner:
        return None
    inns = 1 if x.innings[1][0]["team_bat"] == x.winner else 2
    runs = defaultdict(int)
    for b in x.innings[inns]:
        runs[b["bat"]] += b["score"] or 0
    if not runs:
        return None
    hero = max(runs, key=runs.get)
    here = defaultdict(lambda: {"balls": 0, "runs": 0})
    for b in x.innings[inns]:
        if b["bat"] == hero and b["bowl_kind"] == "pace bowler" and b["length"] and not b.get("wide"):
            here[b["length"]]["balls"] += 1
            here[b["length"]]["runs"] += b["score"] or 0
    now = _shares([{"length": k, "balls": v["balls"]} for k, v in here.items()])
    if now["_n"] < MIN_PLAN:
        return None
    hist = run_deliveries_query(db, fmt="T20", gender="male", group_by=["length"], batters=[hero],
                                bowl_kind=["pace bowler"], include_international=True,
                                start_date=x.day - timedelta(days=365 * PLAN_YEARS),
                                end_date=x.day - timedelta(days=1), limit=20).get("data") or []
    hist = [r for r in hist if r.get("length") in LENGTHS]
    then = _shares([{"length": r["length"], "balls": r["balls"]} for r in hist])
    if then["_n"] < MIN_HISTORY:
        return None
    sr = {r["length"]: r.get("strike_rate") for r in hist if (r.get("balls") or 0) >= 30}
    overall = 100 * sum(r["runs"] for r in hist) / max(1, sum(r["balls"] for r in hist))
    slow = [k for k in ("GOOD_LENGTH", "SHORT_OF_A_GOOD_LENGTH") if sr.get(k) and sr[k] < overall]
    order = ["GOOD_LENGTH", "SHORT_OF_A_GOOD_LENGTH", "FULL", "FULL_TOSS", "YORKER", "SHORT"]
    rows = [{"label": LENGTHS[k] + (f" (SR {round(sr[k])})" if k in sr else ""), "subject": round(now.get(k, 0)),
             "field": round(then.get(k, 0)), "highlight": k in slow} for k in order
            if max(now.get(k, 0), then.get(k, 0)) >= 10]
    full = sum(now.get(k, 0) for k in ("FULL", "FULL_TOSS", "YORKER"))
    full_then = sum(then.get(k, 0) for k in ("FULL", "FULL_TOSS", "YORKER"))
    slow_now, slow_then = sum(now.get(k, 0) for k in slow), sum(then.get(k, 0) for k in slow)
    bowling = x.innings[inns][0]["team_bowl"]
    name = short_name(hero)
    since = (x.day - timedelta(days=365 * PLAN_YEARS)).year
    if slow and slow_now < slow_then - 10:
        which = f"two slowest lengths" if len(slow) > 1 else "slowest length"
        title = (f"{poss(bowling)} pacers landed {round(slow_now)}% of balls on {poss(name)} {which}. Pacers usually "
                 f"land {round(slow_then)}%")
    else:
        title = f"{poss(bowling)} pacers went full to {name}: {round(full)}% of balls, against {round(full_then)}% usually"
    c = card("plan", "deep_compare", title, {
        "metric": {"label": f"% of balls from pace · {hero}", "format": "pct0", "signed": False},
        "series": ["This match", f"Since {since}"], "rows": rows,
    }, x.sample, f"{name} v pace: {int(now['_n'])} balls here, {int(then['_n'])} in T20s since {since} (SR: his "
                 f"strike rate there). Batters moving around the crease change the length, so a miss is partly theirs.")
    c["facts"] = {"batter": hero, "slow": slow, "sr": sr, "now": now, "then": then, "full_now": full,
                  "full_then": full_then}
    return c


def _overs(figures: str) -> float:
    o = str(figures).split("-")[0]
    whole, _, balls = o.partition(".")
    return int(whole) + int(balls or 0) / 6


def attacks(x: Match, sc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Both attacks by kind: economy (the scorecard's bowler figures, so byes and leg byes stay out), length landed,
    full tosses, wickets."""
    if not x.winner or not x.loser:
        return None
    agg = defaultdict(lambda: {"balls": 0, "runs": 0, "tagged": 0, "hit": 0, "ft": 0, "wkts": 0})
    for b in x.balls:
        kind = b["bowl_kind"]
        if kind not in ("pace bowler", "spin bowler"):
            continue
        a = agg[(b["team_bowl"], kind)]
        legal = not (b.get("wide") or b.get("noball"))
        a["balls"] += 1 if legal else 0
        a["runs"] += b["score"] or 0
        a["wkts"] += 1 if b["wkt"] else 0
        if legal and b["length"]:
            a["tagged"] += 1
            target = ("GOOD_LENGTH",) if kind == "spin bowler" else ("GOOD_LENGTH", "YORKER")
            a["hit"] += 1 if b["length"] in target else 0
            a["ft"] += 1 if b["length"] == "FULL_TOSS" else 0
    w, l = x.winner, x.loser
    need = [(w, "pace bowler"), (l, "pace bowler"), (w, "spin bowler"), (l, "spin bowler")]
    if any(agg[k]["balls"] < 12 or agg[k]["tagged"] < 0.8 * agg[k]["balls"] for k in need):
        return None
    kind_of = {(b["team_bowl"], b["bowl"]): b["bowl_kind"] for b in x.balls}
    conceded = defaultdict(lambda: [0, 0.0])
    for inn in sc.get("innings") or []:
        for r in inn["bowling"]:
            k = (inn["bowling_team"], kind_of.get((inn["bowling_team"], r["name"])))
            conceded[k][0] += int(str(r["figures"]).split("-")[2])
            conceded[k][1] += _overs(r["figures"])
    if any(not conceded[k][1] for k in need):
        return None
    pct = lambda k, f: round(100 * agg[k][f] / agg[k]["tagged"], 1)  # noqa: E731
    eco = lambda k: round(conceded[k][0] / conceded[k][1], 1)  # noqa: E731
    rows = [
        {"label": "Spin on a good length", "subject": pct((w, "spin bowler"), "hit"), "field": pct((l, "spin bowler"), "hit")},
        {"label": "Pace on a good length or yorker", "subject": pct((w, "pace bowler"), "hit"),
         "field": pct((l, "pace bowler"), "hit")},
        {"label": "Pace full tosses", "subject": pct((w, "pace bowler"), "ft"), "field": pct((l, "pace bowler"), "ft")},
    ]
    spin_gap = eco((l, "spin bowler")) - eco((w, "spin bowler"))
    pace_gap = eco((l, "pace bowler")) - eco((w, "pace bowler"))
    for r in rows:
        r["highlight"] = False
    if abs(spin_gap) >= abs(pace_gap):
        rows[0]["highlight"] = True
        title = (f"Spin was the gap: {poss(w)} spinners went at {eco((w, 'spin bowler'))} an over, {poss(l)} at "
                 f"{eco((l, 'spin bowler'))}. Pace: {eco((w, 'pace bowler'))} v {eco((l, 'pace bowler'))}, "
                 f"but {agg[(w, 'pace bowler')]['wkts']} wickets to {agg[(l, 'pace bowler')]['wkts']}")
    else:
        rows[1]["highlight"] = True
        title = (f"Pace was the gap: {poss(w)} pacers went at {eco((w, 'pace bowler'))} an over, {poss(l)} at "
                 f"{eco((l, 'pace bowler'))}")
    c = card("attacks", "deep_compare", title, {
        "metric": {"label": "% of each attack's balls", "format": "pct0", "signed": False},
        "series": [w, l], "rows": rows, "colours": [w, l],
    }, x.sample, LENGTH_NOTE)
    c["facts"] = {k[0] + "|" + k[1]: dict(v) for k, v in agg.items()}
    return c


def _series_batters(db: Session, ids: List[str]) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    rows = run_deliveries_query(db, fmt="T20", gender="male", group_by=["batter", "batting_team"], match_ids=ids,
                                include_international=True, limit=100).get("data") or []
    return [r for r in rows if r.get("impact") is not None]


def series_leaders(db: Session, ids: List[str], sample: str, a: str, b: str) -> Optional[Dict[str, Any]]:
    rows = sorted(_series_batters(db, ids), key=lambda r: r["impact"], reverse=True)[:SERIES_TOP]
    if len(rows) < 3:
        return None
    top = rows[0]
    second = rows[1]
    title = (f"{short_name(top['batter'])} and {short_name(second['batter'])}: the series' top two batters by Impact"
             if top["batting_team"] == second["batting_team"] else
             f"{top['batter']} has added the most in the series: {fmt(top['impact'], 'signed1')} runs of Impact")
    c = card("series", "metric_bars", title, {
        "metric": {"label": "Impact (runs added) in the series", "format": "signed1", "signed": True},
        "rows": [{"name": r["batter"], "value": round(r["impact"], 1), "team": r["batting_team"],
                  "detail": f"{r['runs']} off {r['balls']} · SR {round(r['strike_rate'])}"} for r in rows],
        "legend": sorted({a, b}), "label_width": 160,
    }, sample, f"{number(len(ids)).capitalize() if len(ids) < 4 else len(ids)} T20Is between the sides so far.")
    c["facts"] = {"rows": [(r["batter"], r["batting_team"], r["runs"], r["balls"], r["impact"]) for r in rows]}
    return c


def pace_spin(db: Session, ids: List[str], sample: str, team: str) -> Optional[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    leaders = [r["batter"] for r in sorted((r for r in _series_batters(db, ids) if r["batting_team"] == team),
                                            key=lambda r: r["runs"], reverse=True)[:3]]
    if len(leaders) < 2:
        return None
    rows = run_deliveries_query(db, fmt="T20", gender="male", group_by=["batter", "bowl_kind"], match_ids=ids,
                                batters=leaders, include_international=True, limit=50).get("data") or []
    by = defaultdict(dict)
    for r in rows:
        if r.get("bowl_kind") in ("pace bowler", "spin bowler"):
            by[r["batter"]][r["bowl_kind"]] = r
    out = []
    for name in leaders:
        p, s = by[name].get("pace bowler"), by[name].get("spin bowler")
        if not p or not s or p["balls"] < PACE_SPIN_MIN or s["balls"] < PACE_SPIN_MIN:
            continue
        out.append({"label": name, "a": round(p["strike_rate"]), "b": round(s["strike_rate"]),
                    "detail": f"{p['runs']} off {p['balls']} v pace · {s['runs']} off {s['balls']} v spin"})
    if len(out) < 2:
        return None
    faster = [r for r in out if r["b"] > r["a"]]
    if len(faster) == len(out):
        title = f"All {number(len(out))} of {poss(team)} top scorers have gone faster against spin this series"
    else:
        best = max(out, key=lambda r: r["b"] - r["a"])
        title = f"{short_name(best['label'])} has gone {best['b'] - best['a']} strike-rate points faster against spin"
    c = card("pace-spin", "pair_dumbbell", title, {"series": ["v pace", "v spin"], "format": "int", "rows": out,
                                                   "values": True},
             sample, "Strike rate in the series. " + " · ".join(f"{short_name(r['label'])}: {r['detail']}" for r in out))
    c["facts"] = {"rows": out}
    return c


# ---- the caption -------------------------------------------------------------------------------------------------

#: Each side's own fan tag (the board's), used beside the fixture tag; sides not here get none.
TEAM_TAGS = {"India": "#TeamIndia", "West Indies": "#Windies"}


def host_first(x: Match, a: str, b: str) -> List[str]:
    """The sides with the host first ("INDvWI" in India), from the feed's country column."""
    country = next((r.get("country") for r in x.totals if str(r["mid"]) == x.id and r.get("country")), None)
    return [b, a] if country == b else [a, b]


def caption(x: Match, cards: Dict[str, Dict[str, Any]], score: str, a: str, b: str) -> Dict[str, Any]:
    """Body lines (one finding each, at most four), the closing question and the hashtags for a series recap.
    Hashtags: the fixture (host first), the two players the post is about, then each side's fan tag."""
    from services.ig_posts.recap_special import abbr

    lines = []
    if cards.get("race"):
        f = cards["race"]["facts"]
        lines.append(f"After {f['over']} overs: {x.innings[2][0]['team_bat']} {f['chase'][0]}/{f['chase'][1]}, "
                     f"{x.innings[1][0]['team_bat']} {f['first'][0]}/{f['first'][1]}. The last "
                     f"{20 - f['over']}: {x.innings[1][0]['team_bat']} {f['tail'][0]}/{f['tail'][1]}, "
                     f"{x.innings[2][0]['team_bat']} {f['tail'][2]}/{f['tail'][3]}.")
    if cards.get("wp-swings"):
        sw = cards["wp-swings"]["facts"]["swings"]
        lines.append(f"{x.loser} never had better than a {round(cards['wp-swings']['facts']['peak'])}% chance. "
                     + "; ".join(f"Over {o}: {t}" for o, _, _, t in sw) + ".")
    if cards.get("plan"):
        lines.append(cards["plan"]["title"] + ".")
    if cards.get("attacks"):
        lines.append(cards["attacks"]["title"] + ".")
    hero = (cards.get("plan") or {}).get("facts", {}).get("batter")
    swing_bowler = None
    if cards.get("wp-swings"):
        first = cards["wp-swings"]["payload"]["bands"][0]["bowler"]
        swing_bowler = next((b["bowl"] for b in x.innings[2] if b["bowl"] and short_name(b["bowl"]) == first), None)
    sides = host_first(x, a, b)
    tags = [f"#{abbr(sides[0])}v{abbr(sides[1])}"] + [f"#{p.replace(' ', '')}" for p in (hero, swing_bowler) if p]
    tags += [TEAM_TAGS[t] for t in sides if t in TEAM_TAGS]
    prompt = f"{score[:1].upper() + score[1:]}. Who takes the series?" if "level" in score else "Who are you backing next?"
    return {"lines": lines[:4], "prompt": prompt, "tags": tags[:5], "players": [p for p in (hero, swing_bowler) if p]}


# ---- the post ---------------------------------------------------------------------------------------------------

def series_recap(db: Session, m: Dict[str, Any], label: str) -> Optional[Dict[str, Any]]:
    """The series recap's cards for a men's T20I inside a series, or None (the usual recap then)."""
    from services.ig_posts.match import innings_scorecards

    if m.get("format") != "T20" or not m.get("winner"):
        return None
    ids = series_matches(db, m)
    if len(ids) < 2:
        return None
    sample = f"{label} · {m['date']:%d %b %Y}"
    x = Match(db, m, sample)
    if not x.innings[1] or not x.innings[2]:
        return None
    mark_wickets(x.balls)
    from services.match_scorecard import get_match_scorecard_service

    sc = get_match_scorecard_service(match_id=x.id, min_balls=6, db=db)
    how = how_it_was_won(db, x, sc)
    wp, race = wp_swings(x, sc), score_race(x)
    if not how or not (wp or race):
        return None
    plan, att = length_plan(db, x), attacks(x, sc)
    series_sample = f"{label.split(' · ')[0].split(' ', 1)[1]} series · {series_score(db, ids, m['team1'], m['team2'])}"
    leaders = series_leaders(db, ids, series_sample, m["team1"], m["team2"])
    ps = pace_spin(db, ids, series_sample, x.winner)
    cards = [c for c in [how, race, wp, plan, att, leaders, ps] if c]
    cards += innings_scorecards(db, x.id, sample)
    first_total = x.innings[1][-1]["inns_runs"]
    margin_runs = x.winner == x.first_bat
    if race and margin_runs:
        f = race["facts"]
        hook = (f"{x.loser} were {'ahead' if f['chase'][0] > f['first'][0] else 'level'} after {f['over']} overs. "
                f"They lost by {first_total - x.innings[2][-1]['inns_runs']}.")
    else:
        hook = f"What decided {m['team1']} v {m['team2']}?"
    deep = plan or att
    deep_cut = {"probe": f"recap-{deep['id']}", "subject": (deep.get("facts") or {}).get("batter"),
                "sentence": deep["title"] + ".", "by": "recap"} if deep else None
    score = series_score(db, ids, m["team1"], m["team2"])
    cap = caption(x, {c["id"]: c for c in cards}, score, m["team1"], m["team2"])
    players = cap["players"]
    verdict = how["payload"]["headline"] + (f" {race['title']}." if race else "")
    return {"hook": hook, "sub": f"{series_score(db, ids, m['team1'], m['team2']).capitalize()}. What the ball-by-ball says",
            "kicker": label, "cards": cards, "title": how["payload"]["headline"].rstrip("."), "verdict": verdict,
            "players": players, "teams": [m["team1"], m["team2"]], "day": m["date"], "deep_cut": deep_cut,
            "series": True, "series_ids": ids, "caption": cap,
            "method": ("win probability and Impact are ball by ball (T20 Primer method); lengths are the feed's tags, "
                       "and a batter moving around the crease changes them.")}
