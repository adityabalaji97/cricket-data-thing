"""
The preview modules that already existed, as cards (chunk 2 of MATCH_PREVIEW_VIZ_PLAN.md).

Same numbers as the classic page; what changes is the framing: a title that states the finding,
the sample on the card, everything else in the info sheet. Chunk 4 made them correct: par is the
T20 Primer's, the chase record carries its likely range, and every ground card counts the same
matches (ctx.ground_matches), with rain-shortened innings left out of totals.
"""
from __future__ import annotations

from typing import Optional

from models import teams_mapping
from services.analytics_common import phase_bounds
from services.preview_cards.copy import leader_line, plural, short_venue, span
from services.preview_cards.spec import SMALL_SAMPLE, Card, CardSpec, Info, SampleRule
from services.preview_cards.stats import wilson


def _venue_sample(ctx, n: int, what: str = "match") -> str:
    return f"{plural(n, what)} at {short_venue(ctx.venue)} · {span(ctx.start, ctx.end)}"


def _num(value) -> Optional[float]:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------------------------
# At a glance
# --------------------------------------------------------------------------------------------

def _mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def _trend(series) -> Optional[str]:
    """'Up from 167 in 2022.' for a by-season series of {"year", "value"}; None with one season."""
    if len(series) < 2:
        return None
    first, last = series[0], series[-1]
    values = [r["value"] for r in series]
    gap = last["value"] - first["value"]
    if abs(gap) >= 6:
        return f"{'Up' if gap > 0 else 'Down'} from {first['value']} in {first['year']}."
    if max(values) - min(values) < 8:
        return f"Steady at around {last['value']} since {first['year']}."
    return f"Between {min(values)} and {max(values)} since {first['year']}."


def par(ctx) -> Optional[Card]:
    primer = ctx.primer_par
    if primer:
        series = [{"year": r["year"], "value": r["par"], "n": r["n"]} for r in primer["series"]][-6:]
        now = series[-1]
        if primer["international"]:
            title = f"Par for a T20I {primer['where']} is about {now['value']}"
            sample = f"T20Is {primer['where']} · {now['year']} · T20 Primer par"
            how = ("For internationals the Primer sets par by country and season, not by ground: there are "
                   "too few T20Is at any one ground to judge it alone.")
        else:
            title = f"Par here is about {now['value']}"
            sample = f"{primer['competition']} {now['year']} at {short_venue(ctx.venue)} · T20 Primer par"
            how = ("Par starts from this ground's first-innings totals that season and leans on the league's "
                   "and the season's when the ground has few matches, so one freak score doesn't swing it.")
        return Card(
            id="par", chapter="glance", visual="par",
            title=title, sample=sample, n=sum(r["n"] for r in series),
            payload={"value": now["value"], "caption": _trend(series), "series": series},
            info=Info(
                what="Par is the first-innings score an average side would expect to make here.",
                how_to_read=how + " The bars show par in each season.",
                definitions=[("Par (T20 Primer)", "Expected first-innings total, from nested shrinkage over "
                                                  "league, season and ground (Himanish Ganjoo's T20 Primer).")],
            ),
            query_url=ctx.query_url(query_mode="team_innings", innings=1, group_by="season"),
        )
    # No Primer par (ODIs): the average complete first innings, season by season.
    full = [m for m in ctx.ground_matches if m.full_first]
    if len(full) < 5:
        return None
    by_year = {}
    for m in full:
        by_year.setdefault(m.year, []).append(m.first["runs"])
    # Raw season averages are noisy, so only seasons with a few innings are drawn.
    series = [{"year": y, "value": round(_mean(v)), "n": len(v)} for y, v in sorted(by_year.items()) if len(v) >= 3][-6:]
    value = round(_mean([m.first["runs"] for m in full]))
    return Card(
        id="par", chapter="glance", visual="par",
        title=f"Par here is about {value}",
        sample=_venue_sample(ctx, len(full), "complete first innings"), n=len(full),
        small_sample=len(full) < SMALL_SAMPLE,
        payload={"value": value, "caption": _trend(series), "series": series},
        info=Info(
            what="The average first-innings total here, counting only innings that ran their full overs.",
            how_to_read="The bars show the average in each season, so you can see whether scores are rising.",
        ),
        query_url=ctx.query_url(query_mode="team_innings", innings=1, group_by="season",
                                dimension_filters="full_length:eq:1"),
    )


# --------------------------------------------------------------------------------------------
# The ground: every card counts ctx.ground_matches, so their numbers agree
# --------------------------------------------------------------------------------------------

_PHASE_WORDS = {
    "powerplay": "Winning sides here go hardest in the powerplay",
    "middle": "Winning sides here keep scoring through the middle overs",
    "death": "Winning sides here cut loose at the death",
}


def winning_phases(ctx) -> Optional[Card]:
    bounds = phase_bounds(ctx.fmt, ctx.gender)
    overs = {p.key: p.end_over - p.start_over + 1 for p in bounds}
    ms = [m for m in ctx.ground_matches if m.full_first]
    won = {
        "batting_first": [m.first for m in ms if m.result == "bat"],
        "chasing": [m.second for m in ms if m.result == "chase" and m.second],
    }
    phases = {}
    for kind, rows in won.items():
        if len(rows) >= 3:
            phases[kind] = {**{k: round(_mean([r.get(f"{k}_runs") for r in rows])) for k in overs},
                            "total": round(_mean([r["runs"] for r in rows]))}
    if not phases:
        return None
    n = sum(len(won[k]) for k in phases)
    rows = list(phases.values())
    # Runs per over in each phase, across both kinds of win: the phase that stands out names the card.
    rate = {k: sum(r[k] for r in rows) / (overs[k] * len(rows)) for k in overs}
    lead = max(rate, key=rate.get)
    spread = (max(rate.values()) - min(rate.values())) / max(1e-9, sum(rate.values()) / len(rate))
    return Card(
        id="winning-phases", chapter="ground", visual="phase_bars",
        title=_PHASE_WORDS[lead],
        sample=_venue_sample(ctx, n, "win"), n=n,
        payload={"phases": phases},
        info=Info(
            what="Average runs in each phase for sides that won here, batting first and chasing.",
            how_to_read="Each bar is one kind of winning innings, split into the powerplay, middle overs and "
                        "death overs. Rain-shortened matches are left out.",
            definitions=[("Phases", f"{ctx.fmt}: powerplay overs 1–{overs['powerplay']}, then middle overs, "
                                    f"then the last {overs['death']} overs.")],
        ),
        query_url=ctx.query_url(query_mode="team_innings", group_by=["innings", "match_outcome"],
                                dimension_filters="full_length:eq:1"),
        relevance=1.0 + min(spread, 1.0),
    )


def results_split(ctx) -> Optional[Card]:
    ms = ctx.ground_matches
    decided = [m for m in ms if m.result]
    d = len(decided)
    if not d:
        return None
    chased = sum(1 for m in decided if m.result == "chase")
    batted = d - chased
    lo, hi = wilson(chased, d)
    noise = lo <= 0.5 <= hi
    if noise:
        title = (f"Chasing is no clear edge here: {chased} of {d} won" if chased >= batted
                 else f"Batting first is no clear edge here: {batted} of {d} won")
    else:
        title = (f"Chasing sides win more here: {chased} of {d}" if chased > batted
                 else f"Sides batting first win more here: {batted} of {d}")
    notes = []
    years = sorted({m.year for m in decided})
    if len(years) > 2:
        since = years[-2]
        recent = [m for m in decided if m.year >= since]
        notes.append(f"Since {since}: chasing sides won {sum(1 for m in recent if m.result == 'chase')} "
                     f"of {len(recent)}.")
    toss = [m.toss_choice for m in ms if m.toss_choice]
    if toss:
        notes.append(f"Toss winners chose to chase {sum(1 for t in toss if t == 'field')} of {len(toss)} times.")
    return Card(
        id="results", chapter="ground", visual="chase_band",
        title=title, help="The band is the range the true chase rate probably sits in",
        sample=_venue_sample(ctx, d, "decided match"), n=d,
        payload={"chase_wins": chased, "decided": d, "lo": round(lo * 100), "hi": round(hi * 100),
                 "within_noise": noise, "notes": notes},
        info=Info(
            what="How often the side chasing has won here, and how sure we can be that it's a real edge.",
            how_to_read="The dot is the share of matches won by the chasing side. The band is the range the "
                        "true rate probably sits in, given how many matches there are. If the band crosses "
                        "the even line, the split could easily be luck.",
            definitions=[("Likely range", "A 95% Wilson interval for the chase win rate."),
                         ("Decided match", "A match with a winner; ties and no-results are left out.")],
        ),
        query_url=ctx.query_url(query_mode="team_innings", innings=1, group_by="match_outcome"),
        relevance=1.0 + (0.0 if noise else 0.8) + abs(chased - batted) / d * 0.5,
    )


def benchmarks(ctx) -> Optional[Card]:
    full = [m for m in ctx.ground_matches if m.full_first]
    defended = [m.first["runs"] for m in full if m.result == "bat"]
    chased = [m.second["runs"] for m in full if m.result == "chase" and m.second]
    if not defended or not chased:
        return None
    low, high = min(defended), max(chased)
    payload = {
        "total_matches": len(full),
        "lowest_total_defended": low,
        "highest_total_chased": high,
        "average_first_innings": round(_mean([m.first["runs"] for m in full])),
        "average_second_innings": round(_mean([m.second["runs"] for m in full if m.second])),
        "average_winning_score": round(_mean(defended)),
        "average_chasing_score": round(_mean(chased)),
    }
    return Card(
        id="totals", chapter="ground", visual="benchmarks",
        title=f"{low} has been defended here, and {high} chased",
        sample=_venue_sample(ctx, len(full), "match"), n=len(full),
        payload=payload,
        info=Info(
            what="First-innings benchmarks at this ground.",
            how_to_read="Blue dots are totals the batting side won with; orange dots are targets that were "
                        "chased down. Rain-shortened matches are left out.",
            definitions=[("Average total defended", "The average first-innings score of sides that won batting first.")],
        ),
        query_url=ctx.query_url(query_mode="team_innings", innings=1, group_by="match_outcome",
                                dimension_filters="full_length:eq:1"),
    )


def recent_results(ctx) -> Optional[Card]:
    matches = (ctx.history.get("venue_results") or [])[:5]
    if not matches:
        return None
    m = len(matches)
    decided = [x for x in matches if x.get("winner") not in (None, "", "-")]
    chased = sum(1 for x in decided if not x.get("won_batting_first"))
    batted = len(decided) - chased
    if not decided:
        title = f"Recent results at {short_venue(ctx.venue)}"
    elif chased > batted:
        title = f"Chasing sides won {chased} of the last {m} here"
    elif batted > chased:
        title = f"Sides batting first won {batted} of the last {m} here"
    else:
        title = f"Batting first and chasing won {chased} each of the last {m} here"
    return Card(
        id="recent-results", chapter="ground", visual="recent_results",
        title=title, sample=f"Last {plural(m, 'match')} at {short_venue(ctx.venue)}", n=m,
        payload={"matches": matches},
        info=Info(what="The most recent matches at this ground in the selected window; the winning side is "
                       "highlighted. Matches with no result count towards neither side."),
        relevance=0.8,
    )


# --------------------------------------------------------------------------------------------
# The teams
# --------------------------------------------------------------------------------------------

def head_to_head(ctx) -> Optional[Card]:
    h2h = ctx.history.get("h2h_stats") or {}
    a, b, nr = int(h2h.get("team1_wins") or 0), int(h2h.get("team2_wins") or 0), int(h2h.get("draws") or 0)
    n = a + b + nr
    if not n:
        return None
    line, leader = leader_line(ctx.t1, a, ctx.t2, b)
    if n == 1:
        title = f"{leader} won their only meeting" if leader else "Their only meeting had no winner"
    else:
        title = f"{line} in their last {n} meetings"
    return Card(
        id="head-to-head", chapter="teams", visual="h2h",
        title=title,
        sample=f"{plural(n, 'meeting')} · {span(ctx.start, ctx.end)} · any ground", n=n,
        payload={"stats": h2h, "team1": ctx.t1, "team2": ctx.t2},
        info=Info(what="Results of every meeting between the two sides in the selected window, at any ground."),
        relevance=1.0 + (abs(a - b) / n),
    )


def form(ctx) -> Optional[Card]:
    r1, r2 = ctx.history.get("team1_results") or [], ctx.history.get("team2_results") or []
    if not r1 and not r2:
        return None

    # Match rows name the winner by its abbreviation (main.get_match_history, teams_mapping).
    def wins(results, team_full):
        code = teams_mapping.get(team_full, team_full)
        return sum(1 for m in results[:5] if m.get("winner") in (code, team_full))

    w1, w2 = wins(r1, ctx.team1), wins(r2, ctx.team2)
    if w1 == w2:
        title = f"Both sides have won {w1} of their last 5"
    else:
        best, w = (ctx.t1, w1) if w1 > w2 else (ctx.t2, w2)
        title = f"{best} come in with {w} wins from their last 5"
    return Card(
        id="form", chapter="teams", visual="form",
        title=title, sample="Last 5 matches each · any opponent", n=min(len(r1), len(r2)) or max(len(r1), len(r2)),
        payload={"team1": ctx.t1, "team2": ctx.t2, "team1_matches": r1[:5], "team2_matches": r2[:5]},
        info=Info(what="Each side's last five results against anyone; tap a result for the match."),
        relevance=1.0 + abs(w1 - w2) / 5,
    )


GROUND_FLOOR = 10

EXISTING = (
    # Primer par is shrunk toward the league and season, so a thin ground still gets a fair number.
    CardSpec("par", "glance", "What total should we expect?", par, sample=SampleRule(flag_below=0), weight=2.0),
    # Ground records need GROUND_FLOOR matches: below that a split or an average says nothing.
    CardSpec("winning-phases", "ground", "How are winning innings built here?", winning_phases,
             sample=SampleRule(hide_below=GROUND_FLOOR)),
    CardSpec("results", "ground", "Does batting first or chasing win here?", results_split,
             sample=SampleRule(hide_below=GROUND_FLOOR), weight=1.2),
    CardSpec("totals", "ground", "What total wins here?", benchmarks, sample=SampleRule(hide_below=GROUND_FLOOR)),
    CardSpec("recent-results", "ground", "What happened here lately?", recent_results, sample=SampleRule(flag_below=0)),
    CardSpec("head-to-head", "teams", "Who wins when these two meet?", head_to_head),
    CardSpec("form", "teams", "Who's in form?", form, sample=SampleRule(flag_below=0)),
)
