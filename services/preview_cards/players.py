"""
The players chapter (chunk 7 of MATCH_PREVIEW_VIZ_PLAN.md): D1 key battles, D2 death hitters and
death bowlers, D3 form, D4 who suits this ground, D5 milestones, D6 how the key pace bowler bowls.

The players are each side's last XI (ctx.last_xis). Measures, men's T20: batters on the T20 Primer's
RAA per 100 balls (runs above an average batter in the same game states; Impact drifts negative at
the death, -12 per 100 on average, which reads wrongly on a card), bowlers on leverage-weighted RAA
per 100 (runs saved, high-pressure balls counting for more). ODIs use strike rate and economy.

D1's evidence rule: a battle is the pair doing better or worse than both players' own levels
predict. Expected RAA for the pair = the batter's RAA against everyone + the bowler's RAA conceded
to everyone; the raw edge is the pair's RAA minus that. Real edges are small next to the noise in
20-40 balls (analysis/preview/matchup_edges.py: true spread 15 runs per 100, noise 32), so each raw
edge is shrunk toward zero, x n / (n + 120), and the card ranks and shows that likely edge. "Good
batter scores off average bowler" is not a battle, and handedness is never the explanation offered.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from services.milestones import careers, within_reach
from services.preview_cards.copy import has_primer, short_venue
from services.preview_cards.spec import Card, CardSpec, Info, SampleRule

BASELINES = json.loads((Path(__file__).parent / "baselines.json").read_text())

RAA_SD_PER_BALL = 1.62
BATTLE_MIN_BALLS = 18
BATTLE_SHRINK_BALLS = 120   # 162^2 / 14.8^2, analysis/preview/matchup_edges.py
BATTLE_MIN_EDGE = 5         # likely edge, runs per 100 balls
BATTLE_SINCE_YEARS = 8
DEATH_BAT_BALLS = 30
DEATH_BOWL_BALLS = 60
HERE_BALLS, ELSEWHERE_BALLS = 60, 120
PITCH_FLOOR = 600  # line-and-length balls, all men's T20, four years (sign-off decision 4)

LINES = ["DOWN_LEG", "ON_THE_STUMPS", "OUTSIDE_OFFSTUMP", "WIDE_OUTSIDE_OFFSTUMP"]
LENGTHS = ["FULL_TOSS", "YORKER", "FULL", "GOOD_LENGTH", "SHORT_OF_A_GOOD_LENGTH", "SHORT"]
LINE_WORDS = {"DOWN_LEG": "down leg", "ON_THE_STUMPS": "on the stumps", "OUTSIDE_OFFSTUMP": "outside off",
              "WIDE_OUTSIDE_OFFSTUMP": "wide outside off"}
LENGTH_WORDS = {"FULL_TOSS": "full tosses", "YORKER": "yorkers", "FULL": "full balls", "GOOD_LENGTH": "good-length balls",
                "SHORT_OF_A_GOOD_LENGTH": "back-of-a-length balls", "SHORT": "short balls"}


# --------------------------------------------------------------------------------------------
# shared data
# --------------------------------------------------------------------------------------------

def _memo(ctx, key: str, build: Callable[[], Any]) -> Any:
    store = ctx.__dict__.setdefault("_players", {})
    if key not in store:
        store[key] = build()
    return store[key]


def _end(ctx) -> date:
    return ctx.end or date.today()


def _sides(ctx) -> Dict[str, str]:
    """Player -> side label, from the last XIs."""
    out = {}
    for label, xi in (ctx.last_xis or {}).items():
        for name in xi["players"]:
            out.setdefault(name, label)
    return out


def _args(ctx, start: date, **extra) -> Dict[str, Any]:
    return {"fmt": ctx.fmt, "gender": ctx.gender, "start_date": start, "end_date": _end(ctx), **extra}


def _run(ctx, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    return run_deliveries_query(ctx.db, **args, limit=10000)["data"]


def _bat_value(ctx, r) -> Optional[float]:
    if has_primer(ctx.fmt, ctx.gender):
        return r.get("raa_per_100")
    return r.get("strike_rate")


def _bowl_value(ctx, r) -> Optional[float]:
    if has_primer(ctx.fmt, ctx.gender):
        return r.get("raa_lw_per_100") if r.get("raa_lw_per_100") is not None else r.get("raa_per_100")
    balls = r.get("balls") or 0
    return -6.0 * (r.get("runs") or 0) / balls if balls else None  # economy, negated: higher is better


# --------------------------------------------------------------------------------------------
# D1: key battles
# --------------------------------------------------------------------------------------------

def _battle_args(ctx, group_by, players, bowlers):
    end = _end(ctx)
    return _args(ctx, date(end.year - BATTLE_SINCE_YEARS, 1, 1), batters=players, bowlers=bowlers, group_by=group_by,
                 metrics_perspective="batting")


def battles(ctx) -> List[Dict[str, Any]]:
    def build():
        sides = _sides(ctx)
        players = sorted(sides)
        if not players or not has_primer(ctx.fmt, ctx.gender):
            return []
        pairs = _run(ctx, {**_battle_args(ctx, ["batter", "bowler"], players, players), "min_balls": BATTLE_MIN_BALLS})
        bat_base = {r["batter"]: r for r in _run(ctx, _battle_args(ctx, ["batter"], players, None))}
        bowl_base = {r["bowler"]: r for r in _run(ctx, _battle_args(ctx, ["bowler"], None, players))}
        out = []
        for r in pairs:
            bat, bowl = r["batter"], r["bowler"]
            if sides.get(bat) is None or sides.get(bowl) is None or sides[bat] == sides[bowl]:
                continue
            if r.get("raa_per_100") is None or bat not in bat_base or bowl not in bowl_base:
                continue
            expected = (bat_base[bat].get("raa_per_100") or 0) + (bowl_base[bowl].get("raa_per_100") or 0)
            raw = r["raa_per_100"] - expected
            balls = r.get("metric_balls") or r["balls"]
            likely = raw * balls / (balls + BATTLE_SHRINK_BALLS)
            if abs(likely) < BATTLE_MIN_EDGE:
                continue
            out.append({"batter": bat, "bowler": bowl, "bat_side": sides[bat], "balls": r["balls"],
                        "runs": r["runs"], "outs": r.get("wickets") or 0, "edge": round(likely), "raw": round(raw)})
        return sorted(out, key=lambda b: -abs(b["edge"]))[:8]
    return _memo(ctx, "battles", build)


def key_battles(ctx) -> Optional[Card]:
    rows = battles(ctx)
    if not rows:
        return None
    top = rows[0]
    if top["edge"] > 0:
        title = f"{top['batter']} has the edge on {top['bowler']}: {top['runs']} off {top['balls']}"
    elif top["outs"]:
        title = (f"{top['bowler']} has the edge on {top['batter']}: {top['runs']} off {top['balls']}, "
                 f"out {top['outs']} {'time' if top['outs'] == 1 else 'times'}")
    else:
        title = f"{top['bowler']} has kept {top['batter']} quiet: {top['runs']} off {top['balls']}"
    end = _end(ctx)
    sides = _sides(ctx)
    return Card(
        id="key-battles", chapter="players", visual="battles",
        title=title, help="Right: the batter has the edge. Left: the bowler does",
        sample=f"Both XIs · all men's T20 since {end.year - BATTLE_SINCE_YEARS} · {BATTLE_MIN_BALLS}+ balls", n=len(rows),
        payload={"rows": rows},
        info=Info(
            what="Batter against bowler, between these two XIs, where one of them has clearly had the better of it.",
            how_to_read="A bar is the batter's likely edge, in runs per 100 balls: right, the batter has had the "
                        "better of it; left, the bowler has. The scoreline beside it is what actually happened.",
            definitions=[("Expected", "The batter's runs above average against all bowlers, plus the bowler's "
                                      "runs above average conceded to all batters (T20 Primer RAA)."),
                         ("Likely edge", "The gap between what happened and what was expected, shrunk toward zero "
                                         "for small samples: real match-up edges are about 15 runs per 100 balls, "
                                         "while 30 balls of luck can swing one by 30. A 30-ball record keeps a "
                                         "fifth of its gap; a 120-ball record half."),
                         ("Shown", f"{BATTLE_MIN_BALLS}+ balls and a likely edge of {BATTLE_MIN_EDGE}+ runs per 100.")],
        ),
        query_url=ctx.query_url(args={**_battle_args(ctx, ["batter", "bowler"], sorted(sides), sorted(sides)),
                                      "min_balls": BATTLE_MIN_BALLS}),
        relevance=1.6 + min(abs(top["edge"]) / 20.0, 1.0),
    )


# --------------------------------------------------------------------------------------------
# D2: death overs, bat and ball
# --------------------------------------------------------------------------------------------

def _two_seasons(ctx) -> date:
    return date(_end(ctx).year - 1, 1, 1)


def _phase_rows(ctx, who: str) -> List[Dict[str, Any]]:
    def build():
        players = sorted(_sides(ctx))
        if not players:
            return []
        col = "batter" if who == "bat" else "bowler"
        return _run(ctx, _args(ctx, _two_seasons(ctx), **{"batters" if who == "bat" else "bowlers": players},
                               group_by=[col, "phase"], metrics_perspective="batting" if who == "bat" else "bowling"))
    return _memo(ctx, f"phase_{who}", build)


def death_hitters(ctx) -> Optional[Card]:
    sides = _sides(ctx)
    rows = [{"name": r["batter"], "side": sides.get(r["batter"]), "value": _bat_value(ctx, r), "balls": r["balls"],
             "sr": round(r.get("strike_rate") or 0)}
            for r in _phase_rows(ctx, "bat") if r.get("phase") == "death" and r["balls"] >= DEATH_BAT_BALLS]
    rows = sorted((r for r in rows if r["value"] is not None and r["side"]), key=lambda r: -r["value"])[:7]
    if len(rows) < 3:
        return None
    primer = has_primer(ctx.fmt, ctx.gender)
    top = rows[0]
    for r in rows:
        r["value"] = round(r["value"], 1)
    title = (f"{top['name']} adds the most at the death: {top['value']:+.0f} runs per 100 balls" if primer
             else f"{top['name']} scores fastest at the death: strike rate {top['sr']}")
    return Card(
        id="death-hitters", chapter="players", visual="player_bars",
        title=title,
        help="Runs above an average batter, per 100 balls; higher is better" if primer else "Strike rate; higher is better",
        sample=f"Both XIs · all men's {ctx.fmt} {_two_seasons(ctx).year}–{str(_end(ctx).year)[2:]} · {DEATH_BAT_BALLS}+ death balls",
        n=len(rows),
        payload={"rows": rows, "signed": primer, "extra": "sr"},
        info=Info(
            what="Who in either XI has scored best in the death overs over the last two seasons, in any team.",
            how_to_read="Longer bars to the right are better. The figure beside each name is the strike rate.",
            definitions=[("Runs above average", "T20 Primer RAA: runs compared with an average batter facing the "
                                                "same game situations, per 100 balls.")] if primer else [],
        ),
        query_url=ctx.query_url(args=_args(ctx, _two_seasons(ctx), batters=sorted(sides), group_by=["batter", "phase"],
                                           metrics_perspective="batting")),
        relevance=1.2 + min(abs(top["value"]) / 40.0, 0.6),
    )


def death_bowlers(ctx) -> Optional[Card]:
    sides = _sides(ctx)
    rows = []
    for r in _phase_rows(ctx, "bowl"):
        if r.get("phase") != "death" or r["balls"] < DEATH_BOWL_BALLS:
            continue
        v = _bowl_value(ctx, r)
        if v is None or not sides.get(r["bowler"]):
            continue
        rows.append({"name": r["bowler"], "side": sides[r["bowler"]], "value": round(v, 1), "balls": r["balls"],
                     "econ": round(6.0 * (r.get("runs") or 0) / r["balls"], 1)})
    rows = sorted(rows, key=lambda r: -r["value"])[:7]
    if len(rows) < 3:
        return None
    primer = has_primer(ctx.fmt, ctx.gender)
    top = rows[0]
    title = (f"{top['name']} saves the most at the death: {top['value']:+.0f} runs per 100 balls" if primer
             else f"{top['name']} is the tightest at the death: {top['econ']} an over")
    return Card(
        id="death-bowlers", chapter="players", visual="player_bars",
        title=title,
        help="Runs saved per 100 balls, weighted by pressure; higher is better" if primer else "Economy; lower is better",
        sample=f"Both XIs · all men's {ctx.fmt} {_two_seasons(ctx).year}–{str(_end(ctx).year)[2:]} · {DEATH_BOWL_BALLS}+ death balls",
        n=len(rows),
        payload={"rows": rows, "signed": primer, "extra": "econ"},
        info=Info(
            what="Who in either XI has bowled best in the death overs over the last two seasons, in any team.",
            how_to_read="Longer bars to the right are better. The figure beside each name is the economy rate.",
            definitions=[("Runs saved, weighted by pressure", "T20 Primer RAA for bowlers with each ball weighted by "
                                                              "its leverage, so a tight over in a close finish counts "
                                                              "for more than one in a dead game.")] if primer else [],
        ),
        query_url=ctx.query_url(args=_args(ctx, _two_seasons(ctx), bowlers=sorted(sides), group_by=["bowler", "phase"],
                                           metrics_perspective="bowling")),
        relevance=1.2 + min(abs(top["value"]) / 40.0, 0.6),
    )


# --------------------------------------------------------------------------------------------
# D3: form
# --------------------------------------------------------------------------------------------

def form_strips(ctx) -> Optional[Card]:
    sides = _sides(ctx)
    balls = defaultdict(int)
    for r in _phase_rows(ctx, "bat"):
        balls[r["batter"]] += r["balls"] or 0
    top = []
    for label in (ctx.t1, ctx.t2):
        top += [n for n in sorted((n for n in balls if sides.get(n) == label), key=lambda n: -balls[n])[:3]]
    if len(top) < 2:
        return None
    end = _end(ctx)
    args = _args(ctx, end - timedelta(days=365), batters=top, group_by=["batter", "match_id", "match_date"])
    inns = _memo(ctx, "recent_innings", lambda: _run(ctx, args))
    strips = []
    for name in top:
        mine = sorted((r for r in inns if r["batter"] == name), key=lambda r: str(r["match_date"]))[-10:]
        if len(mine) < 3:
            continue
        strips.append({"name": name, "side": sides[name],
                       "innings": [{"date": str(r["match_date"]), "runs": r["runs"], "balls": r["balls"],
                                    "out": bool(r.get("wickets"))} for r in mine]})
    if len(strips) < 2:
        return None

    def heat(s):
        runs = [i["runs"] for i in s["innings"]]
        return (sum(1 for r in runs if r >= 50), sum(runs))
    best = max(strips, key=heat)
    fifties, runs = heat(best)
    k = len(best["innings"])
    title = (f"{best['name']} arrives in form: {fifties} fifties in the last {k} innings" if fifties >= 2
             else f"{best['name']} has {runs} runs in the last {k} innings")
    return Card(
        id="form-strips", chapter="players", visual="form_strips",
        title=title, help="Runs in each of the last 10 innings, oldest first",
        sample=f"Each side's 3 busiest batters · any men's {ctx.fmt} · last 12 months", n=len(strips),
        payload={"strips": strips},
        info=Info(what="Each side's three most-used batters and their scores in their last ten innings, for any team.",
                  how_to_read="Taller bars are bigger scores; bright bars are 50 or more. A star in the tooltip "
                              "means not out."),
        query_url=ctx.query_url(args=args),
        relevance=1.0 + min(fifties / 4.0, 0.6),
    )


# --------------------------------------------------------------------------------------------
# D4: who suits this ground
# --------------------------------------------------------------------------------------------

def suits_ground(ctx) -> Optional[Card]:
    if not has_primer(ctx.fmt, ctx.gender):
        return None
    sides = _sides(ctx)
    players = sorted(sides)
    if not players:
        return None
    start = ctx.start or date(_end(ctx).year - 4, 1, 1)
    here_args = _args(ctx, start, batters=players, venue=ctx.venue, group_by=["batter"])
    every_args = _args(ctx, start, batters=players, group_by=["batter"])
    here = {r["batter"]: r for r in _memo(ctx, "here", lambda: _run(ctx, here_args))}
    every = {r["batter"]: r for r in _memo(ctx, "every", lambda: _run(ctx, every_args))}
    rows = []
    for name, h in here.items():
        a = every.get(name)
        if not a or not sides.get(name) or h["balls"] < HERE_BALLS or a["balls"] - h["balls"] < ELSEWHERE_BALLS:
            continue
        mb_h, mb_a = h.get("metric_balls") or 0, a.get("metric_balls") or 0
        if not mb_h or mb_a - mb_h <= 0 or h.get("raa") is None or a.get("raa") is None:
            continue
        elsewhere = (a["raa"] - h["raa"]) * 100.0 / (mb_a - mb_h)
        rows.append({"name": name, "side": sides[name], "here": round(h["raa"] * 100.0 / mb_h, 1),
                     "elsewhere": round(elsewhere, 1), "balls_here": h["balls"]})
    if len(rows) < 3:
        return None
    best = max(rows, key=lambda r: r["here"] - r["elsewhere"])
    worst = min(rows, key=lambda r: r["here"] - r["elsewhere"])
    lift = best["here"] - best["elsewhere"]
    drop = worst["here"] - worst["elsewhere"]
    ground = short_venue(ctx.venue)
    if lift >= -drop:
        title = f"{best['name']} lifts at {ground}: {lift:+.0f} runs per 100 balls over their record elsewhere"
    else:
        title = f"{worst['name']} struggles at {ground}: {drop:+.0f} runs per 100 balls against their record elsewhere"
    return Card(
        id="suits-ground", chapter="players", visual="suits_scatter",
        title=title, help=f"Above the line: better at {ground} than elsewhere",
        sample=f"Both XIs · all men's T20 since {start.year} · {HERE_BALLS}+ balls here", n=len(rows),
        payload={"rows": rows, "ground": ground},
        info=Info(
            what=f"Each batter's record at {ground} against their record everywhere else, same seasons.",
            how_to_read="Each dot is a batter. Dots above the diagonal have done better here than elsewhere.",
            definitions=[("Measure", "T20 Primer RAA per 100 balls: runs above an average batter in the same "
                                     "situations.")],
        ),
        query_url=ctx.query_url(args=here_args),
        relevance=1.0 + min(max(lift, -drop) / 40.0, 0.8),
    )


# --------------------------------------------------------------------------------------------
# D5: milestones
# --------------------------------------------------------------------------------------------

def milestones(ctx) -> Optional[Card]:
    from services.competition_aliases import variants_for
    from services.competition_normalizer import international_competitions

    sides = _sides(ctx)
    comp = ctx.fixture_competition
    if not sides or not comp:
        return None
    intl = comp in international_competitions(ctx.fmt)
    comps = international_competitions(ctx.fmt) if intl else (variants_for(comp) or [comp])
    where = ("T20I" if ctx.fmt == "T20" else ctx.fmt) if intl else comp
    totals = _memo(ctx, "careers", lambda: careers(ctx.db, sorted(sides), comps, ctx.fmt, ctx.gender, ctx.end))
    found = within_reach(totals, sides, ctx.fmt)[:6]
    if not found:
        return None
    rows = [{"player": m.player, "side": m.side, "text": m.phrase(where), "stat": m.stat, "total": m.total,
             "target": m.target} for m in found]
    return Card(
        id="milestones", chapter="players", visual="milestones",
        title=f"{found[0].player} {found[0].phrase(where)}", help=None,
        sample=f"Both XIs · {where} careers to date", n=len(rows),
        payload={"rows": rows},
        info=Info(what=f"Round numbers either XI could pass in this match, from {where} careers to date.",
                  how_to_read="Runs within 60 of the next 500, wickets and sixes within 4 of the next 50, and "
                              "50th or 100th matches (ODIs: runs within 80 of the next 1,000).",
                  method="Careers from every season on record, counting older seasons stored under another "
                         "spelling of the player's name."),
        relevance=1.1,
    )


# --------------------------------------------------------------------------------------------
# D6: how the key pace bowler bowls
# --------------------------------------------------------------------------------------------

def how_they_bowl(ctx) -> Optional[Card]:
    if ctx.fmt != "T20" or ctx.gender != "male":
        return None  # the baseline is men's T20 pace bowling
    sides = _sides(ctx)
    if not sides:
        return None
    end = _end(ctx)
    start = date(end.year - 4, end.month, min(end.day, 28))
    args = _args(ctx, start, bowlers=sorted(sides), bowl_kind=["pace bowler"], group_by=["bowler", "line", "length"])
    rows = _memo(ctx, "pitch", lambda: _run(ctx, args))
    cells: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        line = "DOWN_LEG" if r.get("line") == "WIDE_DOWN_LEG" else r.get("line")
        if line in LINES and r.get("length") in LENGTHS and sides.get(r["bowler"]):
            cells[r["bowler"]][f"{line}|{r['length']}"] += r["balls"] or 0
    qualified = {b: c for b, c in cells.items() if sum(c.values()) >= PITCH_FLOOR}
    if not qualified:
        return None
    bowler = max(qualified, key=lambda b: sum(qualified[b].values()))
    mine = qualified[bowler]
    n = sum(mine.values())
    base = BASELINES["pace_line_length"]["share"]
    grid = []
    for line in LINES:
        for length in LENGTHS:
            key = f"{line}|{length}"
            share, usual = mine.get(key, 0) / n, base.get(key, 0.0)
            grid.append({"line": line, "length": length, "pct": round(100 * share, 1), "usual_pct": round(100 * usual, 1)})
    # The standout: the cell bowled most above its usual share (at least 4% of the bowler's balls).
    big = [g for g in grid if g["pct"] >= 4 and g["usual_pct"] > 0]
    top = max(big, key=lambda g: g["pct"] / g["usual_pct"]) if big else max(grid, key=lambda g: g["pct"])
    ratio = top["pct"] / top["usual_pct"] if top["usual_pct"] else None
    what = f"{LENGTH_WORDS[top['length']]} {LINE_WORDS[top['line']]}"
    title = (f"{bowler} bowls {what} {ratio:.1f}× as often as an average pace bowler" if ratio and ratio >= 1.2
             else f"{bowler} bowls {what} most often: {top['pct']:.0f}% of balls")
    return Card(
        id="how-they-bowl", chapter="players", visual="pitch_usage",
        title=title, help="Share of balls in each line and length; a dot marks 1.5× an average pace bowler",
        sample=f"{n:,} balls with line and length · all men's T20 since {start.year}", n=n,
        payload={"bowler": bowler, "side": sides[bowler], "grid": grid, "lines": LINES, "lengths": LENGTHS},
        info=Info(
            what=f"Where {bowler} pitches the ball, against every pace bowler over the same four years.",
            how_to_read="Darker cells get more of the bowler's balls. Cells marked with a dot are bowled at least "
                        "1.5× as often as an average pace bowler bowls them.",
            definitions=[("Floor", f"{PITCH_FLOOR}+ balls with line and length recorded: below that a bowler's "
                                   "pattern isn't stable (analysis/preview/bowler_pitch_reliability.py).")],
        ),
        query_url=ctx.query_url(args=args),
        relevance=1.0,
    )


PLAYERS = (
    CardSpec("key-battles", "players", "Which match-ups decide it?", key_battles, formats=("T20",),
             sample=SampleRule(flag_below=0), scale_by_sample=False),
    CardSpec("death-hitters", "players", "Who adds the most at the death?", death_hitters, sample=SampleRule(flag_below=0), scale_by_sample=False),
    CardSpec("death-bowlers", "players", "Who's best with the ball at the death?", death_bowlers,
             sample=SampleRule(flag_below=0), scale_by_sample=False),
    CardSpec("form-strips", "players", "Who's hot?", form_strips, sample=SampleRule(flag_below=0), scale_by_sample=False),
    CardSpec("suits-ground", "players", "Who suits this ground?", suits_ground, formats=("T20",),
             sample=SampleRule(flag_below=0), scale_by_sample=False),
    CardSpec("milestones", "players", "Any records in play?", milestones, sample=SampleRule(flag_below=0), scale_by_sample=False),
    CardSpec("how-they-bowl", "players", "How does the key bowler work?", how_they_bowl, formats=("T20",),
             sample=SampleRule(flag_below=0), scale_by_sample=False),
)
