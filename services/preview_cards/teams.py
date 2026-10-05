"""
The teams chapter's new cards (chunk 6 of MATCH_PREVIEW_VIZ_PLAN.md): C1 where the game will be
won, C2 phase strength against the league, C3 rating, C4 last meeting, C6 likely XIs. Head to
head (C5) and form live in existing.py.

C1 and C2 read every side in the fixture's competition over the last two seasons, by phase. In
men's T20 the measure is the T20 Primer's RAA per 100 balls (runs above an average side in the
same game states), batting and bowling (runs saved). RAA is measured against all men's T20, so an
IPL side looks good with the bat and bad with the ball simply for being in the IPL; the cards
subtract the competition's own average, so 0 is an average side in this competition and higher
is better on both sides of the ball. ODIs use plain runs per 100 balls the same way.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from services.analytics_common import phase_bounds
from services.preview_cards.copy import has_primer, plural, short_venue
from services.preview_cards.spec import Card, CardSpec, Info, SampleRule

PHASE_WORDS = {"powerplay": "powerplay", "middle": "middle-overs", "death": "death"}
MIN_PHASE_BALLS = 60


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _seasons(ctx) -> str:
    w = ctx.team_window
    return f"{w['start'].year}–{str(w['end'].year)[2:]}"


def _phase_table(ctx) -> Optional[Dict[str, Dict[str, Dict[str, Dict[str, float]]]]]:
    """
    {"bat"|"bowl": {phase: {team: {"value", "balls", "innings"}}}}, value per 100 balls with higher
    better, before centring. RAA in men's T20, plain runs elsewhere.
    """
    primer = has_primer(ctx.fmt, ctx.gender)
    data = ctx.team_phases
    out: Dict[str, Dict] = {"bat": {}, "bowl": {}}
    for side, team_col in (("bat", "batting_team"), ("bowl", "bowling_team")):
        for r in data[side]:
            balls = r.get("balls") or 0
            if not balls or r.get("phase") is None:
                continue
            if primer:
                if r.get("raa_per_100") is None:
                    continue
                value = r["raa_per_100"]
            else:
                per100 = 100.0 * (r.get("runs") or 0) / balls
                value = per100 if side == "bat" else -per100
            out[side].setdefault(r["phase"], {})[r[team_col]] = {
                "value": value, "balls": balls, "innings": r.get("innings_count") or 0}
    return out


def _centred(ctx):
    """Phase table with each value minus the competition's balls-weighted average."""
    table = _phase_table(ctx)
    for side in table.values():
        for teams in side.values():
            balls = sum(t["balls"] for t in teams.values())
            mean = sum(t["value"] * t["balls"] for t in teams.values()) / balls if balls else 0.0
            for t in teams.values():
                t["vs_avg"] = t["value"] - mean
    return table


def _team_row(ctx, teams: Dict[str, Dict], label: str) -> Optional[Dict]:
    for name in ctx.team_names[label]:
        if name in teams and teams[name]["balls"] >= MIN_PHASE_BALLS:
            return teams[name]
    return None


def _measure_words(ctx) -> str:
    return ("Runs above an average side in the same situations (T20 Primer RAA), per 100 balls."
            if has_primer(ctx.fmt, ctx.gender) else "Runs per 100 balls.")


# --------------------------------------------------------------------------------------------
# C1: where the game will be won
# --------------------------------------------------------------------------------------------

def where_won(ctx) -> Optional[Card]:
    if not ctx.team_window:
        return None
    table = _centred(ctx)
    keys = [p.key for p in phase_bounds(ctx.fmt, ctx.gender)]
    rows = []
    for side, group in (("bat", "Batting"), ("bowl", "Bowling")):
        for k in keys:
            teams = table[side].get(k, {})
            a, b = _team_row(ctx, teams, ctx.t1), _team_row(ctx, teams, ctx.t2)
            if not a or not b:
                return None
            rows.append({"group": group, "phase": k, "team1": round(a["vs_avg"], 1), "team2": round(b["vs_avg"], 1)})
    big = max(rows, key=lambda r: abs(r["team1"] - r["team2"]))
    gap = abs(big["team1"] - big["team2"])
    leader = ctx.t1 if big["team1"] > big["team2"] else ctx.t2
    comp = ctx.team_window["label"]
    innings = min(_team_row(ctx, table["bat"][keys[0]], t)["innings"] for t in (ctx.t1, ctx.t2))
    return Card(
        id="where-won", chapter="teams", visual="dumbbell",
        # "MI death bowling", not "MI's": a possessive on a short code ("AUS's") reads badly.
        title=f"{leader} {PHASE_WORDS[big['phase']]} {big['group'].lower()} is the biggest edge: "
              f"{gap:.0f} runs per 100 balls",
        help=f"Further right is better: runs per 100 balls against the {comp} average",
        sample=f"Both sides · {comp} {_seasons(ctx)}", n=innings,
        payload={"rows": rows, "team1": ctx.t1, "team2": ctx.t2, "comparison": comp},
        info=Info(
            what=f"How each side has batted and bowled in each phase, against an average {comp} side.",
            how_to_read="Each row is a phase. The dot further right belongs to the side that did better: more "
                        "runs with the bat, or fewer conceded with the ball. The gap between the dots is the edge.",
            definitions=[("Measure", _measure_words(ctx)),
                         ("Average", f"0 is the average of every {comp} side over the same seasons.")],
        ),
        query_url=ctx.query_url(args=ctx.team_query_args(["batting_team", "phase"], "batting")),
        relevance=1.0 + min(gap / 20.0, 1.0),
    )


# --------------------------------------------------------------------------------------------
# C2: phase strength, as a rank in the competition
# --------------------------------------------------------------------------------------------

def phase_strength(ctx) -> Optional[Card]:
    if not ctx.team_window:
        return None
    table = _phase_table(ctx)
    keys = [p.key for p in phase_bounds(ctx.fmt, ctx.gender)]
    rows, of_all = [], set()
    for side, group in (("bat", "batting"), ("bowl", "bowling")):
        for k in keys:
            ranked = sorted(((name, t) for name, t in table[side].get(k, {}).items() if t["balls"] >= MIN_PHASE_BALLS),
                            key=lambda x: -x[1]["value"])
            names = [n for n, _ in ranked]
            of = len(names)
            row = {"group": group, "phase": k, "of": of}
            for key, label in (("team1", ctx.t1), ("team2", ctx.t2)):
                rank = next((i + 1 for i, n in enumerate(names) if n in ctx.team_names[label]), None)
                if rank is None:
                    return None
                row[key] = rank
            of_all.add(of)
            rows.append(row)
    if not rows or min(of_all) < 4:
        return None  # a rank among three sides says nothing
    # The rank furthest from the middle names the card.
    def extremeness(r, key):
        return abs(r[key] - (r["of"] + 1) / 2) / r["of"]
    best = max(((r, key) for r in rows for key in ("team1", "team2")), key=lambda x: extremeness(*x))
    r, key = best
    team = ctx.t1 if key == "team1" else ctx.t2
    comp = ctx.team_window["label"]
    return Card(
        id="phase-strength", chapter="teams", visual="rank_bars",
        title=f"{team} {PHASE_WORDS[r['phase']]} {r['group']} ranks {_ordinal(r[key])} of {r['of']}",
        help="Longer bar = higher in the league",
        sample=f"{plural(max(of_all), 'side')} · {comp} {_seasons(ctx)}", n=max(of_all),
        payload={"rows": rows, "team1": ctx.t1, "team2": ctx.t2},
        info=Info(
            what=f"Where each side ranks among every {comp} side, phase by phase, with bat and ball.",
            how_to_read="A full bar is first in the league; a short one is near the bottom. The numbers are the "
                        "ranks (1 is best).",
            definitions=[("Measure", _measure_words(ctx))],
        ),
        query_url=ctx.query_url(args=ctx.team_query_args(["bowling_team", "phase"], "bowling")),
        relevance=1.0 + 2 * extremeness(r, key),
    )


# --------------------------------------------------------------------------------------------
# C3: rating through the last year
# --------------------------------------------------------------------------------------------

def rating(ctx) -> Optional[Card]:
    series = ctx.elo_series
    if not series or any(len(series.get(t, [])) < 3 for t in (ctx.t1, ctx.t2)):
        return None
    a, b = series[ctx.t1][-1]["elo"], series[ctx.t2][-1]["elo"]
    if abs(a - b) < 15:
        title = f"Evenly rated: {ctx.t1} {a}, {ctx.t2} {b}"
    else:
        (hi, hv), (lo, lv) = sorted(((ctx.t1, a), (ctx.t2, b)), key=lambda x: -x[1])
        title = f"{hi} come in rated higher: {hv} to {lo}'s {lv}"
    comp = ctx.fixture_competition
    n = len(series[ctx.t1]) + len(series[ctx.t2])
    return Card(
        id="rating", chapter="teams", visual="elo_lines",
        title=title, help="Team strength rating; higher is stronger",
        sample=f"Every {comp} match for both sides · last 12 months", n=n,
        payload={"series": [{"team": t, "points": series[t]} for t in (ctx.t1, ctx.t2)]},
        info=Info(
            what="Each side's Elo rating going into every match over the last year.",
            how_to_read="Elo rises after a win and falls after a defeat, by more when the result is a surprise. "
                        "Two sides 100 points apart: the higher-rated one wins about 64% of the time.",
            definitions=[("Elo", "A strength rating built from results alone; the average side sits near 1500.")],
        ),
        relevance=1.0 + min(abs(a - b) / 100.0, 1.0),
    )


# --------------------------------------------------------------------------------------------
# C4: last meeting
# --------------------------------------------------------------------------------------------

def last_meeting(ctx) -> Optional[Card]:
    m = ctx.last_meeting
    if not m or len(m["innings"]) < 1:
        return None
    first = m["innings"][0]
    second = m["innings"][1] if len(m["innings"]) > 1 else None
    w = m["winner"]
    if not w:
        title = "Last time: no result"
    elif second and w == second["side"]:
        left = 10 - second["wickets"]
        title = f"Last time: {w} chased {first['runs'] + 1} with {plural(left, 'wicket')} in hand"
    elif second:
        title = f"Last time: {w} defended {first['runs']} and won by {plural(first['runs'] - second['runs'], 'run')}"
    else:
        title = f"Last time: {w} won"
    d = m["date"]
    when = f"{d.day} {d.strftime('%b')} {d.year}"
    from services.competition_aliases import canonical_competition
    path = m["path"]
    return Card(
        id="last-meeting", chapter="teams", visual="last_meeting",
        title=title, help=f"{ctx.t1}'s chance of winning after every ball" if path else None,
        sample=f"{canonical_competition(m['competition'])} · {short_venue(m['venue'])} · {when}", n=1,
        payload={"path": path, "innings": m["innings"], "team1": ctx.t1, "team2": ctx.t2, "match_id": m["id"]},
        info=Info(
            what="The last time these sides met, and how the result swung ball by ball.",
            how_to_read="The line is the side's chance of winning after each ball, from the T20 Primer's win "
                        "probability model; above the middle line it was ahead." if path else
                        "Both innings of the last meeting.",
        ),
        query_url=None,
        relevance=1.2,
    )


# --------------------------------------------------------------------------------------------
# C6: likely XIs
# --------------------------------------------------------------------------------------------

def likely_xis(ctx) -> Optional[Card]:
    xis = ctx.last_xis
    if len(xis) < 2:
        return None
    sides = [{"team": t, "date": xis[t]["date"].isoformat(), "opponent": xis[t]["opponent"],
              "players": xis[t]["players"]} for t in (ctx.t1, ctx.t2)]
    return Card(
        id="xis", chapter="lineups", visual="xis",
        title="Likely XIs, from their last matches", help=None,
        sample=f"Each side's last {ctx.fmt} match · batting order", n=11,
        payload={"sides": sides},
        info=Info(what="The players each side used last time, in batting order, then anyone who only bowled. "
                       "Teams change; this is a starting point, not a prediction.",
                  how_to_read="A twelfth name is a substitute who batted or bowled (the IPL's Impact Player rule)."),
        relevance=0.6,
    )


TEAMS = (
    CardSpec("where-won", "teams", "Where will this game be won?", where_won, sample=SampleRule(flag_below=10)),
    CardSpec("phase-strength", "teams", "How strong is each side in each phase?", phase_strength,
             sample=SampleRule(flag_below=0)),
    CardSpec("rating", "teams", "Who's stronger on current rating?", rating, sample=SampleRule(flag_below=0)),
    CardSpec("last-meeting", "teams", "What happened last time?", last_meeting, sample=SampleRule(flag_below=0),
             scale_by_sample=False),
    CardSpec("xis", "lineups", "Who's likely to play?", likely_xis, sample=SampleRule(flag_below=0),
             scale_by_sample=False),
)
