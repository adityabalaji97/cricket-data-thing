"""
"Series so far" (SERIES_PREVIEW_PLAN.md): from the second meeting of two sides on, the preview opens with what the
games so far say. Chunks 1-2: the games, how the last one turned, each side's phases against par, pace and spin, and
whether batters were used where their record is strongest.

The games so far are the sides' earlier meetings in the same competition in an unbroken run: a bilateral series (games
at most SERIES_GAP_DAYS apart) or a tournament or league season (the same competition and year). The latest has to be
recent (RECENT_DAYS before the fixture), so last year's series never counts as this one. Every number comes from the
query builder over those games' match ids; the cards say how few balls one game is.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from services.preview_cards.copy import has_primer, plural, short_venue
from services.preview_cards.spec import Card, CardSpec, Info, SampleRule

SERIES_GAP_DAYS = 14      # a bilateral series: consecutive games at most this far apart
RECENT_DAYS = 21          # the latest game at most this long before the fixture
RECORD_YEARS = 3          # a batter's record by phase and bowling: this many years, every men's T20
RECORD_MIN_BALLS = 30     # ... a cell needs this many balls
USAGE_MIN_GAP = 25        # runs above par per 100 balls between where he batted and his best
USAGE_MIN_FACED = 6       # balls in the last game to count as having batted there
PHASES = ("powerplay", "middle", "death")
PHASE_WORDS = {"powerplay": "the powerplay", "middle": "the middle overs", "death": "the death"}
KIND_WORDS = {"pace bowler": "pace", "spin bowler": "spin"}


def _memo(ctx, key, build):
    store = ctx.__dict__.setdefault("_series", {})
    if key not in store:
        store[key] = build()
    return store[key]


def _fixture_day(ctx) -> date:
    return ctx.end or date.today()


def games(ctx) -> List[Dict[str, Any]]:
    """The games so far, oldest first (PreviewContext.series_games): [] for a first meeting."""
    return ctx.series_games


def find_games(ctx) -> List[Dict[str, Any]]:
    """The sides' earlier meetings in this series or season, oldest first: {id, date, venue, competition, winner, n}."""
    a, b = ctx.team_names[ctx.t1], ctx.team_names[ctx.t2]
    day = _fixture_day(ctx)
    rows = ctx.db.execute(text("""
        SELECT id, date, venue, competition, winner FROM matches
        WHERE ((team1 = ANY(:a) AND team2 = ANY(:b)) OR (team1 = ANY(:b) AND team2 = ANY(:a)))
          AND format = :fmt AND gender = :gender AND date < :day AND date >= :since
          AND (winner IS NOT NULL OR outcome IS NOT NULL)  -- finished (a no result has an outcome), not cut off mid-match
        ORDER BY date DESC, id DESC
    """), {"a": a, "b": b, "fmt": ctx.fmt, "gender": ctx.gender, "day": day,
           "since": day - timedelta(days=200)}).mappings().all()
    if not rows or (day - rows[0]["date"]).days > RECENT_DAYS:
        return []
    from services.competition_normalizer import international_competitions

    comp = rows[0]["competition"]
    bilateral = comp in international_competitions(ctx.fmt)
    run = [rows[0]]
    for r in rows[1:]:
        if r["competition"] != comp:
            break
        if bilateral and (run[-1]["date"] - r["date"]).days > SERIES_GAP_DAYS:
            break
        if not bilateral and r["date"].year != rows[0]["date"].year:
            break
        run.append(r)
    run.reverse()
    return [{"id": str(r["id"]), "date": r["date"], "venue": r["venue"], "competition": comp,
             "winner": ctx.side_of(r["winner"]), "n": i + 1} for i, r in enumerate(run)]


def _q(ctx, ids: List[str], group_by: List[str], perspective: str = "batting", **extra) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    return run_deliveries_query(ctx.db, fmt=ctx.fmt, gender=ctx.gender, match_ids=ids, group_by=group_by,
                                metrics_perspective=perspective, limit=10000, **extra)["data"]


def _ids(ctx) -> List[str]:
    return [g["id"] for g in games(ctx)]


def _so_far(ctx) -> str:
    """'Game 1' or 'Games 1-3', and the score: 'India 2, New Zealand 1'."""
    gs = games(ctx)
    wins = {ctx.t1: 0, ctx.t2: 0}
    for g in gs:
        if g["winner"] in wins:
            wins[g["winner"]] += 1
    span = f"Game {gs[0]['n']}" if len(gs) == 1 else f"Games 1–{len(gs)}"
    return f"{span} · {ctx.t1} {wins[ctx.t1]}, {ctx.t2} {wins[ctx.t2]}"


def _url(ctx, **params) -> str:
    return ctx.query_url(args={"match_ids": _ids(ctx), "metrics_perspective": "batting", **params})


def _pos(side: str) -> str:
    """'India's', 'West Indies''."""
    return f"{side}'" if side.endswith("s") else f"{side}'s"


def _pp(wpa: float) -> str:
    """Win probability added, said as percentage points (content rules)."""
    return f"{'+' if wpa >= 0 else '−'}{abs(round(100 * wpa))} points"


# --------------------------------------------------------------------------------------------
# 1: how the last game turned
# --------------------------------------------------------------------------------------------

def series_turn(ctx) -> Optional[Card]:
    gs = games(ctx)
    if not gs or not has_primer(ctx.fmt, ctx.gender):
        return None
    last = gs[-1]
    bat = _q(ctx, [last["id"]], ["batter", "batting_team"])
    bowl = _q(ctx, [last["id"]], ["bowler", "bowling_team"], "bowling")
    best = [{"name": r["batter"], "side": ctx.side_of(r["batting_team"]), "wpa": r["wpa"] or 0,
             "line": f"{r['runs']} ({r['balls']})"} for r in bat]
    best += [{"name": r["bowler"], "side": ctx.side_of(r["bowling_team"]), "wpa": r["wpa"] or 0,
              "line": f"{r['wickets']}/{r['runs']}"} for r in bowl]
    if not best:
        return None
    top = max(best, key=lambda r: r["wpa"])
    m = ctx.last_meeting  # the latest meeting is the last game: its innings and win-probability path
    if not m or m["id"] != last["id"]:
        return None
    by_side = {}
    for r in sorted(best, key=lambda r: -r["wpa"]):
        by_side.setdefault(r["side"], r)
    d = last["date"]
    result = f"{last['winner']} won" if last["winner"] else "no result"
    return Card(
        id="series-turn", chapter="series", visual="last_meeting",
        title=f"Game {last['n']}: {top['name']}'s {top['line']} added {_pp(top['wpa'])} of win probability",
        help=f"{ctx.t1}'s chance of winning after every ball" if m["path"] else None,
        sample=f"{_so_far(ctx)} · game {last['n']} at {short_venue(last['venue'])}, {d.day} {d.strftime('%b')} ({result})",
        n=1,
        payload={"path": m["path"], "innings": m["innings"], "team1": ctx.t1, "team2": ctx.t2, "match_id": last["id"]},
        info=Info(
            what=f"The last game of the series, ball by ball, and who moved it most. The best for each side: " +
                 "; ".join(f"{s}: {r['name']} {r['line']} ({_pp(r['wpa'])})" for s, r in by_side.items() if s) + ".",
            how_to_read="The line is the side's chance of winning after each ball (the T20 Primer's model); above "
                        "the middle line it was ahead.",
            definitions=[("Win probability added", "How much a player's balls moved his side's chance of winning, "
                                                   "in percentage points.")],
        ),
        query_url=_url(ctx, group_by=["batter"]),
        relevance=2.0,
    )


# --------------------------------------------------------------------------------------------
# 2: phase by phase against par
# --------------------------------------------------------------------------------------------

def series_phases(ctx) -> Optional[Card]:
    ids = _ids(ctx)
    if not ids or not has_primer(ctx.fmt, ctx.gender):
        return None
    rows = _q(ctx, ids, ["batting_team", "phase"])
    cells = {(ctx.side_of(r["batting_team"]), r["phase"]): r for r in rows}
    out = []
    for p in PHASES:
        a, b = cells.get((ctx.t1, p)), cells.get((ctx.t2, p))
        if not a or not b or a.get("raa_per_100") is None or b.get("raa_per_100") is None:
            return None
        out.append({"group": "Batting", "phase": p, "team1": round(a["raa_per_100"], 1), "team2": round(b["raa_per_100"], 1),
                    "balls1": a["balls"], "balls2": b["balls"]})
    big = max(out, key=lambda r: abs(r["team1"] - r["team2"]))
    lead, trail = (ctx.t1, ctx.t2) if big["team1"] >= big["team2"] else (ctx.t2, ctx.t1)
    hi, lo = max(big["team1"], big["team2"]), min(big["team1"], big["team2"])
    balls = sum(r["balls"] for r in rows)
    return Card(
        id="series-phases", chapter="series", visual="dumbbell",
        title=f"In {PHASE_WORDS[big['phase']]}, {lead} batted {hi:+.0f} runs above par per 100 balls; {trail} {lo:+.0f}",
        help="Right of par is better for the batting side",
        sample=f"{_so_far(ctx)} · {balls:,} balls", n=len(ids),
        payload={"rows": out, "team1": ctx.t1, "team2": ctx.t2, "comparison": "par", "zero_label": "par"},
        info=Info(
            what="Each side's batting in every phase of the games so far, against par for the game state. One side's "
                 "batting is the other's bowling, so this is the whole contest phase by phase.",
            how_to_read="Each dot is a side's runs above par per 100 balls in that phase. A phase is 24-54 balls a "
                        "game, so one game swings these a lot.",
            definitions=[("Runs above par", "Runs scored beyond what an average batter would score in the same game "
                                            "states (the T20 Primer's RAA).")],
        ),
        query_url=_url(ctx, group_by=["batting_team", "phase"]),
        relevance=1.6,
    )


# --------------------------------------------------------------------------------------------
# 4: pace and spin
# --------------------------------------------------------------------------------------------

def _ground_spin_share(ctx) -> Optional[int]:
    rows = (ctx.over_profile or {}).get("ground") or []
    spin = sum(r["balls"] or 0 for r in rows if r.get("bowl_kind") == "spin bowler")
    pace = sum(r["balls"] or 0 for r in rows if r.get("bowl_kind") == "pace bowler")
    return round(100 * spin / (spin + pace)) if spin + pace else None


def series_pace_spin(ctx) -> Optional[Card]:
    ids = _ids(ctx)
    if not ids:
        return None
    rows = _q(ctx, ids, ["bowling_team", "bowl_kind"], "bowling")
    by = defaultdict(lambda: {"pace": {"balls": 0, "runs": 0, "wickets": 0}, "spin": {"balls": 0, "runs": 0, "wickets": 0}})
    for r in rows:
        kind = KIND_WORDS.get(r.get("bowl_kind"))
        side = ctx.side_of(r["bowling_team"])
        if kind and side:
            for k in ("balls", "runs", "wickets"):
                by[side][kind][k] += r[k] or 0
    if set(by) != {ctx.t1, ctx.t2}:
        return None
    usual = _ground_spin_share(ctx)
    econ = lambda d: round(6 * d["runs"] / d["balls"], 1) if d["balls"] else None  # noqa: E731
    out = []
    for side in (ctx.t1, ctx.t2):
        s, p = by[side]["spin"], by[side]["pace"]
        total = s["balls"] + p["balls"]
        out.append({"label": f"{side} bowling", "side": side, "spin_pct": round(100 * s["balls"] / total) if total else 0,
                    "spin_pct_all": usual, "spin_econ": econ(s), "pace_econ": econ(p),
                    "spin_balls": s["balls"], "pace_balls": p["balls"], "spin_wickets": s["wickets"], "pace_wickets": p["wickets"]})
    # The title: the biggest gap in economy between the sides' spinners or their seamers (12+ balls each).
    gaps = []
    for kind in ("spin", "pace"):
        a, b = out
        if a[f"{kind}_balls"] >= 12 and b[f"{kind}_balls"] >= 12:
            gaps.append((abs(a[f"{kind}_econ"] - b[f"{kind}_econ"]), kind))
    if not gaps:
        return None
    _, kind = max(gaps)
    lo, hi = sorted(out, key=lambda r: r[f"{kind}_econ"])
    who = "spinners" if kind == "spin" else "seamers"
    return Card(
        id="series-pace-spin", chapter="series", visual="pace_spin",
        title=f"{_pos(hi['side'])} {who} went at {hi[f'{kind}_econ']} an over; {_pos(lo['side'])} at {lo[f'{kind}_econ']}",
        help="Share of each side's balls bowled by spin" + (", the tick is the next ground's usual" if usual is not None else ""),
        sample=f"{_so_far(ctx)}", n=len(ids),
        payload={"rows": out, "comparison": f"{short_venue(ctx.venue)} usually" if usual is not None else "usual",
                 "by_side": True},
        info=Info(
            what="How much each side bowled spin and pace in the games so far, and what each cost. The tick is how "
                 "much spin the next game's ground usually sees.",
            how_to_read="A longer spin bar means more of the side's overs went to spinners.",
        ),
        query_url=ctx.query_url(args={"match_ids": ids, "metrics_perspective": "bowling", "group_by": ["bowling_team", "bowl_kind"]}),
        relevance=1.3,
    )


# --------------------------------------------------------------------------------------------
# 6: used where their record is strongest?
# --------------------------------------------------------------------------------------------

CELL_PHASE = {"powerplay": "in the powerplay", "middle": "in the middle overs", "death": "at the death"}


def _cell_words(phase: str, kind: str) -> str:
    return f"{KIND_WORDS[kind]} {CELL_PHASE[phase]}"


def _usage_candidates(ctx) -> List[Dict[str, Any]]:
    """Batters (at 3 or lower) who batted below par last game in a cell well below their best: [{name, side, cell,
    best, gap, game, total, mine}]."""
    gs = games(ctx)
    if not gs or not has_primer(ctx.fmt, ctx.gender):
        return []
    last = gs[-1]
    faced = [r for r in _q(ctx, [last["id"]], ["batter", "batting_team", "phase", "bowl_kind"])
             if r.get("bowl_kind") in KIND_WORDS and r.get("phase") in PHASES]
    if not faced:
        return []
    per = defaultdict(list)
    for r in faced:
        per[r["batter"]].append(r)
    # Openers face pace in the powerplay by job, not by choice: only batters at 3 or lower, where the order is a choice.
    order = {r["batter"]: r["batting_position"] for r in _q(ctx, [last["id"]], ["batter", "batting_position"])
             if r.get("batting_position") is not None}
    names = [n for n, rs in per.items() if sum(r["balls"] for r in rs) >= USAGE_MIN_FACED and order.get(n, 0) >= 3]
    if not names:
        return []
    day = _fixture_day(ctx)
    record = _q(ctx, None, ["batter", "phase", "bowl_kind"], batters=names, leagues=[], include_international=False,
                start_date=date(day.year - RECORD_YEARS, day.month, min(day.day, 28)), end_date=day)
    rec = defaultdict(dict)
    for r in record:
        if r.get("bowl_kind") in KIND_WORDS and r.get("phase") in PHASES and (r["balls"] or 0) >= RECORD_MIN_BALLS \
                and r.get("raa_per_100") is not None:
            rec[r["batter"]][(r["phase"], r["bowl_kind"])] = r
    found = []
    for name in names:
        mine = rec.get(name) or {}
        if len(mine) < 2:
            continue
        main = max(per[name], key=lambda r: r["balls"])  # where most of his balls in the last game came
        cell = (main["phase"], main["bowl_kind"])
        best_cell = max(mine, key=lambda c: mine[c]["raa_per_100"])
        if cell == best_cell or cell not in mine:
            continue
        gap = mine[best_cell]["raa_per_100"] - mine[cell]["raa_per_100"]
        if gap < USAGE_MIN_GAP or (main.get("raa_per_100") or 0) >= 0:
            continue  # a real gap in his record, and it showed: he scored below par there last game
        total = {"runs": sum(r["runs"] for r in per[name]), "balls": sum(r["balls"] for r in per[name])}
        found.append({"name": name, "side": ctx.side_of(per[name][0]["batting_team"]), "cell": cell, "best": best_cell,
                      "gap": gap, "game": main, "total": total, "mine": mine})
    return found


def series_usage(ctx) -> Optional[Card]:
    found = _memo(ctx, "usage", lambda: _usage_candidates(ctx))
    if not found:
        return None
    last = games(ctx)[-1]
    f = max(found, key=lambda x: x["gap"])
    rows = [{"name": _cell_words(*c).capitalize(), "value": round(r["raa_per_100"]),
             "highlight": c == f["cell"],
             "detail": f"{r['balls']} balls" + (f" · game {last['n']}: {f['game']['runs']} ({f['game']['balls']})" if c == f["cell"] else "")}
            for c, r in sorted(f["mine"].items(), key=lambda x: -x[1]["raa_per_100"])]
    title = (f"{f['name']} faced {_cell_words(*f['cell'])} in game {last['n']}. "
             f"His record is best against {_cell_words(*f['best'])}")
    return Card(
        id="series-usage", chapter="series", visual="metric_bars",
        title=title,
        help="His runs above par per 100 balls, by phase and bowling; lime is where he batted last game",
        sample=f"{f['name']} · every men's T20, last {RECORD_YEARS} years · {RECORD_MIN_BALLS}+ balls a cell",
        n=sum(r["balls"] for r in f["mine"].values()),
        payload={"metric": {"label": "Runs above par per 100 balls", "format": "signed0", "signed": True},
                 "rows": rows, "label_width": 150},
        info=Info(
            what=f"Where {f['name']} batted in the last game against where his record is strongest. A batter used "
                 "away from his strengths is an option for the next game, not a verdict on one innings.",
            how_to_read="Each bar is his runs above par per 100 balls against pace or spin in one phase over the "
                        "last three years; lime marks where most of his balls came last game.",
            definitions=[("Runs above par", "Runs beyond what an average batter would score in the same game states "
                                            "(the T20 Primer's RAA).")],
        ),
        query_url=ctx.query_url(args={"batters": [f["name"]], "leagues": [], "group_by": ["phase", "bowl_kind"],
                                      "metrics_perspective": "batting"}),
        relevance=1.5,
    )


# --------------------------------------------------------------------------------------------
# 3: bowling to the conditions (line and length; only once tracking has landed)
# --------------------------------------------------------------------------------------------

PITCH_LINES = ["WIDE_OUTSIDE_OFFSTUMP", "OUTSIDE_OFFSTUMP", "ON_THE_STUMPS", "DOWN_LEG"]
PITCH_LENGTHS = ["FULL", "GOOD_LENGTH", "SHORT_OF_A_GOOD_LENGTH", "SHORT"]
LINE_MERGE = {"WIDE_DOWN_LEG": "DOWN_LEG"}
LENGTH_MERGE = {"YORKER": "FULL", "FULL_TOSS": "FULL"}
LINE_SAY = {"WIDE_OUTSIDE_OFFSTUMP": "wide outside off", "OUTSIDE_OFFSTUMP": "outside off",
            "ON_THE_STUMPS": "at the stumps", "DOWN_LEG": "down leg"}
LENGTH_SAY = {"FULL": "full", "GOOD_LENGTH": "on a good length", "SHORT_OF_A_GOOD_LENGTH": "back of a length",
              "SHORT": "short"}
PITCH_MIN_SIDE = 60       # tracked pace balls a side needs for its map
PITCH_MIN_CELL = 6        # balls for a cell to be shaded
PITCH_BEST_CELL = 12      # balls for a cell to count as what worked


def _pace_cells(ctx) -> Dict[str, Dict[tuple, Dict[str, int]]]:
    def build():
        rows = _q(ctx, _ids(ctx), ["bowling_team", "line", "length"], "bowling", bowl_kind=["pace bowler"])
        out: Dict[str, Dict[tuple, Dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: {"balls": 0, "runs": 0, "wickets": 0}))
        for r in rows:
            side = ctx.side_of(r["bowling_team"])
            line = LINE_MERGE.get(r.get("line"), r.get("line"))
            length = LENGTH_MERGE.get(r.get("length"), r.get("length"))
            if side and line in PITCH_LINES and length in PITCH_LENGTHS:
                c = out[side][(line, length)]
                for k in ("balls", "runs", "wickets"):
                    c[k] += r[k] or 0
        return out
    return _memo(ctx, "pace_cells", build)


def _econ(c: Dict[str, int]) -> float:
    return round(6 * c["runs"] / c["balls"], 1)


def _lengths_card(ctx, side: str, other: str) -> Optional[Card]:
    if not _ids(ctx):
        return None
    cells = _pace_cells(ctx)
    # Cells with no legal balls (only wides) carry runs but no rate.
    mine = {k: c for k, c in (cells.get(side) or {}).items() if c["balls"]}
    theirs = {k: c for k, c in (cells.get(other) or {}).items() if c["balls"]}
    n_mine, n_theirs = sum(c["balls"] for c in mine.values()), sum(c["balls"] for c in theirs.values())
    if n_mine < PITCH_MIN_SIDE or n_theirs < PITCH_MIN_SIDE:
        return None
    every = [c for side_cells in (mine, theirs) for c in side_cells.values()]
    mid = round(6 * sum(c["runs"] for c in every) / sum(c["balls"] for c in every), 1)
    # What worked for the other side: its cheapest cells with enough balls, outlined on this side's map.
    worked = sorted((k for k, c in theirs.items() if c["balls"] >= PITCH_BEST_CELL), key=lambda k: _econ(theirs[k]))[:2]
    used = max(mine, key=lambda k: mine[k]["balls"])
    say = lambda k: f"{LENGTH_SAY[k[1]]} {LINE_SAY[k[0]]}"  # noqa: E731
    # Their most-used ball and what it cost; then the other side's cheapest, when that was something else.
    title = f"{_pos(side)} seamers went {_econ(mine[used])} an over {say(used)}"
    if worked and worked[0] != used:
        title += f"; {_pos(other)} {_econ(theirs[worked[0]])} {say(worked[0])}"
    return Card(
        id=f"series-lengths-{'1' if side == ctx.t1 else '2'}", chapter="series", visual="pitch_map",
        title=title,
        help="Runs per over from each line and length; outlined: where the other side's seamers went cheapest",
        sample=f"{_so_far(ctx)} · {n_mine} pace balls tracked · most-used: {say(used)}",
        n=n_mine,
        payload={"hand": "RHB", "lines": PITCH_LINES, "lengths": PITCH_LENGTHS, "min_balls": PITCH_MIN_CELL,
                 "metric": {"label": "Runs per over", "format": "dec1", "higher_better": False, "mid": mid},
                 "legend": [f"Cheaper than the series' {mid}", "Dearer"],
                 "cells": [{"line": k[0], "length": k[1], "value": _econ(c), "balls": c["balls"], "outs": c["wickets"],
                            "highlight": k in worked} for k, c in mine.items()]},
        info=Info(
            what=f"Where {_pos(side)} seamers pitched the ball in the games so far, and what each line and length cost. "
                 f"The outlined cells are where {_pos(other)} seamers went cheapest on the same pitches: the lengths "
                 "the conditions rewarded.",
            how_to_read="Viewed from the bowler's end, drawn for a right-hander (lines are relative to the batter). "
                        f"Lime cells cost less than the series' pace average of {mid} an over, red ones more; cells "
                        f"under {PITCH_MIN_CELL} balls are blank. One game is about 70 pace balls a side, so a cell is "
                        "a handful of overs.",
        ),
        query_url=ctx.query_url(args={"match_ids": _ids(ctx), "bowl_kind": ["pace bowler"], "metrics_perspective": "bowling",
                                      "group_by": ["bowling_team", "line", "length"]}),
        relevance=1.55,
    )


def series_lengths_1(ctx) -> Optional[Card]:
    return _lengths_card(ctx, ctx.t1, ctx.t2)


def series_lengths_2(ctx) -> Optional[Card]:
    return _lengths_card(ctx, ctx.t2, ctx.t1)


# --------------------------------------------------------------------------------------------
# 9: a new ground (does the last game's lesson carry over?)
# --------------------------------------------------------------------------------------------

GROUND_YEARS = 5
GROUND_MIN_BALLS = 1200   # ~5 matches of history at each ground


def _ground_profile(ctx, venue: str) -> Optional[Dict[str, Any]]:
    day = _fixture_day(ctx)
    rows = _q(ctx, None, ["phase", "bowl_kind"], "bowling", venue=venue, leagues=[], include_international=False,
              start_date=date(day.year - GROUND_YEARS, day.month, min(day.day, 28)), end_date=day)
    balls = sum(r["balls"] or 0 for r in rows)
    if balls < GROUND_MIN_BALLS:
        return None

    def rate(sel):
        b = sum(r["balls"] or 0 for r in sel)
        return round(6 * sum(r["runs"] or 0 for r in sel) / b, 2) if b else None

    kind = lambda k: [r for r in rows if r.get("bowl_kind") == k]  # noqa: E731
    phase = lambda p: [r for r in rows if r.get("phase") == p]  # noqa: E731
    spin_balls = sum(r["balls"] or 0 for r in kind("spin bowler"))
    return {"balls": balls, "Run rate": rate(rows), "Powerplay": rate(phase("powerplay")), "Death overs": rate(phase("death")),
            "Pace": rate(kind("pace bowler")), "Spin": rate(kind("spin bowler")), "spin_share": round(100 * spin_balls / balls)}


GROUND_WORDS = {"International", "Cricket", "Stadium", "Ground", "Complex", "Association"}


def _ground(venue: str) -> str:
    """'Rajiv Gandhi International Stadium' -> 'Rajiv Gandhi'; 'Hagley Oval, Christchurch' -> 'Hagley Oval'."""
    words = [w for w in venue.split(",")[0].split() if w not in GROUND_WORDS]
    return " ".join(words) or venue


def series_new_ground(ctx) -> Optional[Card]:
    gs = games(ctx)
    if not gs:
        return None
    last = gs[-1]["venue"]
    if last in (ctx.venue_aliases or [ctx.venue]):
        return None  # same ground: the games so far already are the evidence
    old, new = _ground_profile(ctx, last), _ground_profile(ctx, ctx.venue)
    if not old or not new:
        return None
    labels = ["Run rate", "Powerplay", "Death overs", "Pace", "Spin"]
    rows = [{"label": k, "a": old[k], "b": new[k]} for k in labels if old[k] is not None and new[k] is not None]
    if len(rows) < 3:
        return None
    # The title: pace or spin, whichever differs more between the grounds.
    big = max((r for r in rows if r["label"] in ("Pace", "Spin")), key=lambda r: abs(r["b"] - r["a"]), default=None)
    if big is None:
        return None
    for r in rows:
        r["highlight"] = r is big
    a, b = _ground(last), _ground(ctx.venue)
    word = "seamers" if big["label"] == "Pace" else "spinners"
    return Card(
        id="series-new-ground", chapter="series", visual="pair_dumbbell",
        title=f"{word.capitalize()} go at {big['b']:.1f} an over at {b}, {big['a']:.1f} at {a}, where game {gs[-1]['n']} was",
        help="Runs per over at each ground, every men's T20 there",
        sample=f"{b} v {a} · all men's T20s, last {GROUND_YEARS} years · spin bowls {new['spin_share']}% there, "
               f"{old['spin_share']}% at {a}",
        n=min(old["balls"], new["balls"]) // 120,
        payload={"series": [a, b], "format": "dec1", "values": True, "full_labels": True, "rows": rows},
        info=Info(
            what=f"The next game moves from {a} to {b}. How the two grounds play, from every men's T20 at each over "
                 f"the last {GROUND_YEARS} years, so a lesson from {a} is weighed against conditions that may differ.",
            how_to_read="Each row is runs per over at the two grounds; the number on the right is the next ground "
                        "minus the last.",
        ),
        query_url=ctx.query_url(args={"venue": ctx.venue, "leagues": [], "group_by": ["phase", "bowl_kind"],
                                      "metrics_perspective": "bowling"}),
        relevance=1.45,
    )


# --------------------------------------------------------------------------------------------
# 8: keep / try (rules over the cards above; options, never verdicts)
# --------------------------------------------------------------------------------------------

KEEP_BALLS = 12
KEEP_MARGIN = 1.0         # a keep is at least this many runs an over cheaper than the series' pace average


def _cell_say(k) -> str:
    return f"{LENGTH_SAY[k[1]]} {LINE_SAY[k[0]]}"


def series_keep_try(ctx) -> Optional[Card]:
    if not _ids(ctx):
        return None
    cells = _pace_cells(ctx)
    sides = []
    for side, other in ((ctx.t1, ctx.t2), (ctx.t2, ctx.t1)):
        mine = {k: c for k, c in (cells.get(side) or {}).items() if c["balls"]}
        theirs = {k: c for k, c in (cells.get(other) or {}).items() if c["balls"]}
        keep, try_ = [], []
        n_mine = sum(c["balls"] for c in mine.values())
        if n_mine >= PITCH_MIN_SIDE and sum(c["balls"] for c in theirs.values()) >= PITCH_MIN_SIDE:
            every = list(mine.values()) + list(theirs.values())
            avg = 6 * sum(c["runs"] for c in every) / sum(c["balls"] for c in every)
            own = 6 * sum(c["runs"] for c in mine.values()) / n_mine
            # Keep: a length that beat the series' and the side's own pace average, with enough balls.
            for k in sorted((k for k, c in mine.items() if c["balls"] >= KEEP_BALLS and _econ(c) < min(avg, own)),
                            key=lambda k: _econ(mine[k]))[:2]:
                if _econ(mine[k]) > avg - KEEP_MARGIN:
                    break
                keep.append({"text": f"Seamers {_cell_say(k)}", "detail": f"{_econ(mine[k])} an over · {mine[k]['balls']} balls",
                             "num": f"{_econ(mine[k])} an over", "rank": (2, _econ(mine[k]))})
            # Try: the other side's cheapest lengths that this side used under half as much.
            for k in sorted((k for k, c in theirs.items() if c["balls"] >= KEEP_BALLS and _econ(c) <= avg - KEEP_MARGIN),
                            key=lambda k: _econ(theirs[k])):
                share_them = theirs[k]["balls"] / sum(c["balls"] for c in theirs.values())
                share_me = (mine.get(k) or {"balls": 0})["balls"] / n_mine
                if share_me < share_them / 2 and len(try_) < 2:
                    try_.append({"text": f"Seamers {_cell_say(k)}",
                                 "detail": f"{_pos(other)} went {_econ(theirs[k])} there · {side} bowled {round(100 * share_me)}% of balls there",
                                 "num": f"{_pos(other)} went {_econ(theirs[k])}", "rank": (1, _econ(theirs[k]))})
        w = _batting_weak(ctx)
        if w and w["side"] == other and len(try_) < 2:
            c = w["cells"][other][w["cell"]]
            try_.insert(0, {"text": f"Seamers {_cell_say(w['cell'])} to {_pos(other)} batters",
                            "detail": f"they were in control of {w['pct']:.0f}% there, {round(w['side_avg'][other])}% overall · "
                                      f"{int(c['tagged'])} balls, {c['outs']} {'wicket' if c['outs'] == 1 else 'wickets'}",
                            "num": f"{w['pct']:.0f}% in control", "rank": (1, -100)})
        for u in _memo(ctx, "usage", lambda: _usage_candidates(ctx)):
            if u["side"] == side and len(try_) < 2:
                best = u["mine"][u["best"]]
                try_.append({"text": f"{u['name']} against {_cell_words(*u['best'])}",
                             "detail": f"his best: {best['raa_per_100']:+.0f} runs above par per 100 balls",
                             "num": f"{best['raa_per_100']:+.0f} per 100 there", "rank": (0, -u["gap"])})
        if keep or try_:
            sides.append({"team": side, "keep": keep, "try": try_})
    if not sides:
        return None
    # The title: a batter to move first, then a length the other side proved, then the cheapest length to keep.
    team, kind, first = min(((sd["team"], kind, it) for sd in sides for kind in ("try", "keep") for it in sd[kind]),
                            key=lambda x: x[2]["rank"])
    for sd in sides:
        for kind_ in ("keep", "try"):
            for it in sd[kind_]:
                it.pop("rank", None)
    return Card(
        id="series-keep-try", chapter="series", visual="keep_try",
        title=f"{team} could {kind}: {first['text'].replace('Seamers ', 'seamers ', 1)} ({first['num']})",
        help="Options from the games so far, not verdicts",
        sample=f"{_so_far(ctx)} · {KEEP_BALLS}+ balls behind each",
        n=len(_ids(ctx)),
        payload={"sides": sides, "team1": ctx.t1, "team2": ctx.t2},
        info=Info(
            what="What the games so far suggest each side keeps doing or tries, by fixed rules: keep a length its "
                 "seamers went cheaper with than both the series' and their own average; try a length that worked for "
                 "the other side and they used less than half as often; try a batter where his record is strongest.",
            how_to_read=f"Each line has the evidence under it. A length needs {KEEP_BALLS}+ balls; one game is a "
                        "handful of overs per length, so these are options to weigh, not verdicts.",
        ),
        relevance=1.4,
    )


# --------------------------------------------------------------------------------------------
# 5: batting to the conditions (control % against pace by line and length)
# --------------------------------------------------------------------------------------------

BAT_MIN_CELL = 8          # balls for a cell to be shaded and to name the weak spot


def _batting_weak(ctx) -> Optional[Dict[str, Any]]:
    """The side with the starkest weak spot against pace: {side, cell, pct, cells, side_avg}, or None."""
    def build():
        ids = _ids(ctx)
        if not ids:
            return None
        rows = _q(ctx, ids, ["batting_team", "line", "length"], bowl_kind=["pace bowler"])
        cells: Dict[str, Dict[tuple, Dict[str, float]]] = defaultdict(lambda: defaultdict(lambda: {"balls": 0, "ctl": 0.0, "tagged": 0, "runs": 0, "outs": 0}))
        for r in rows:
            side = ctx.side_of(r["batting_team"])
            line = LINE_MERGE.get(r.get("line"), r.get("line"))
            length = LENGTH_MERGE.get(r.get("length"), r.get("length"))
            tagged = r.get("control_tagged") or 0
            if side and line in PITCH_LINES and length in PITCH_LENGTHS and tagged:
                c = cells[side][(line, length)]
                c["balls"] += r["balls"] or 0
                c["tagged"] += tagged
                c["ctl"] += (r.get("control_percentage") or 0) * tagged / 100
                c["runs"] += r["runs"] or 0
                c["outs"] += r.get("wickets") or 0
        if set(cells) != {ctx.t1, ctx.t2}:
            return None
        if min(sum(c["tagged"] for c in cs.values()) for cs in cells.values()) < PITCH_MIN_SIDE:
            return None
        side_avg = {s: 100 * sum(c["ctl"] for c in cs.values()) / sum(c["tagged"] for c in cs.values()) for s, cs in cells.items()}
        # The weak spot: the cell furthest below its side's own control, with enough balls.
        weak = [(s, k, 100 * c["ctl"] / c["tagged"]) for s, cs in cells.items() for k, c in cs.items() if c["tagged"] >= BAT_MIN_CELL]
        if not weak:
            return None
        side, cell, pct = min(weak, key=lambda w: w[2] - side_avg[w[0]])
        return {"side": side, "cell": cell, "pct": pct, "cells": cells, "side_avg": side_avg}
    return _memo(ctx, "batting_weak", build)


def series_batting(ctx) -> Optional[Card]:
    w = _batting_weak(ctx)
    if not w:
        return None
    ids = _ids(ctx)
    side, cell, pct, cells, side_avg = w["side"], w["cell"], w["pct"], w["cells"], w["side_avg"]
    mine = cells[side]
    mid = round(side_avg[side])
    other = ctx.t2 if side == ctx.t1 else ctx.t1
    c = mine[cell]
    return Card(
        id="series-batting", chapter="series", visual="pitch_map",
        title=f"{_pos(side)} batters were in control of {pct:.0f}% of pace balls {_cell_say(cell)}; {mid}% overall",
        help="Control % against pace by line and length; outlined: the weak spot",
        sample=f"{_so_far(ctx)} · {int(sum(x['tagged'] for x in mine.values()))} pace balls to {_pos(side)} batters tracked",
        n=int(sum(x["tagged"] for x in mine.values())),
        payload={"hand": "RHB", "lines": PITCH_LINES, "lengths": PITCH_LENGTHS, "min_balls": BAT_MIN_CELL,
                 "metric": {"label": "Control %", "format": "pct0", "higher_better": True, "mid": mid},
                 "legend": [f"Above their {mid}%", "Below"], "show_outs": True,
                 "cells": [{"line": k[0], "length": k[1], "value": round(100 * x["ctl"] / x["tagged"]), "balls": int(x["tagged"]),
                            "outs": x["outs"], "highlight": k == cell} for k, x in mine.items() if x["tagged"]]},
        info=Info(
            what=f"How often {_pos(side)} batters played pace in control in the games so far, by line and length. The "
                 f"outlined cell is where they were least in control against their own average: the length {other} "
                 f"could keep bowling ({c['outs']} wickets there so far).",
            how_to_read="Viewed from the bowler's end, drawn for a right-hander (lines are relative to the batter). "
                        f"Lime cells are above the side's {mid}%, red below; cells under {BAT_MIN_CELL} balls are blank; "
                        "the small number is wickets.",
            definitions=[("Control %", "The share of balls the batter middled or left well, rather than edging, "
                                       "missing or mistiming (ball-by-ball tracking).")],
        ),
        query_url=ctx.query_url(args={"match_ids": ids, "bowl_kind": ["pace bowler"], "metrics_perspective": "batting",
                                      "group_by": ["batting_team", "line", "length"]}),
        relevance=1.5,
    )


SERIES = (
    CardSpec("series-turn", "series", "How did the last game turn?", series_turn, formats=("T20",),
             sample=SampleRule(flag_below=0), scale_by_sample=False),
    CardSpec("series-phases", "series", "Where has the series been won and lost?", series_phases, formats=("T20",),
             sample=SampleRule(flag_below=0), scale_by_sample=False),
    CardSpec("series-pace-spin", "series", "How have pace and spin gone?", series_pace_spin, formats=("T20",),
             sample=SampleRule(flag_below=0), scale_by_sample=False),
    CardSpec("series-lengths-1", "series", "Did the first side bowl to the conditions?", series_lengths_1,
             formats=("T20",), sample=SampleRule(flag_below=0), scale_by_sample=False),
    CardSpec("series-lengths-2", "series", "Did the second side bowl to the conditions?", series_lengths_2,
             formats=("T20",), sample=SampleRule(flag_below=0), scale_by_sample=False),
    CardSpec("series-new-ground", "series", "Does the last game carry over to this ground?", series_new_ground,
             formats=("T20",), sample=SampleRule(flag_below=0), scale_by_sample=False),
    CardSpec("series-keep-try", "series", "What should each side keep or try?", series_keep_try, formats=("T20",),
             sample=SampleRule(flag_below=0), scale_by_sample=False),
    CardSpec("series-batting", "series", "Did the batters play the conditions?", series_batting, formats=("T20",),
             sample=SampleRule(flag_below=0), scale_by_sample=False),
    CardSpec("series-usage", "series", "Is anyone batting away from his strengths?", series_usage, formats=("T20",),
             sample=SampleRule(flag_below=0), scale_by_sample=False),
)
