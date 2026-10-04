"""
The preview modules that already existed, as cards (chunk 2 of MATCH_PREVIEW_VIZ_PLAN.md).

Same numbers as the classic page; what changes is the framing: a title that states the finding,
the sample on the card, everything else in the info sheet. Statistical framing (intervals on the
chase record, era-aware par) arrives in chunk 4.
"""
from __future__ import annotations

from typing import Optional

from models import teams_mapping
from services.analytics_common import phase_bounds
from services.preview_cards.copy import leader_line, plural, short_venue, span
from services.preview_cards.spec import Card, CardSpec, Info, SampleRule


def _venue_sample(ctx, n: int) -> str:
    return f"{plural(n, 'match')} at {short_venue(ctx.venue)} · {span(ctx.start, ctx.end)}"


def _num(value) -> Optional[float]:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------------------------
# At a glance
# --------------------------------------------------------------------------------------------

def par(ctx) -> Optional[Card]:
    venue = (ctx.expect or {}).get("venue") or {}
    value = venue.get("avg_winning_score") or venue.get("avg_first_innings")
    n = int(venue.get("total_matches") or 0)
    if not value:
        return None
    by_winners = bool(venue.get("avg_winning_score"))
    caption = (f"The average first innings here is {venue['avg_first_innings']}."
               if by_winners and venue.get("avg_first_innings") else None)
    return Card(
        id="par", chapter="glance", visual="stat",
        title=f"Par here is about {round(value)}",
        sample=_venue_sample(ctx, n), n=n,
        payload={"value": round(value), "caption": caption},
        info=Info(
            what="The first-innings total that has tended to win at this ground.",
            how_to_read="Par is the average first-innings score of sides that went on to win batting first here."
                        + (" Too few sides won batting first, so this is the average first innings." if not by_winners else ""),
        ),
        query_url=ctx.query_url(query_mode="team_innings", innings=1, group_by="match_outcome"),
    )


# --------------------------------------------------------------------------------------------
# The ground
# --------------------------------------------------------------------------------------------

_PHASE_WORDS = {
    "powerplay": "Winning sides here go hardest in the powerplay",
    "middle": "Winning sides here keep scoring through the middle overs",
    "death": "Winning sides here cut loose at the death",
}


def winning_phases(ctx) -> Optional[Card]:
    phases = (ctx.expect or {}).get("winning_phases") or {}
    rows = [p for p in (phases.get("batting_first"), phases.get("chasing")) if p]
    n = int(((ctx.expect or {}).get("venue") or {}).get("total_matches") or 0)
    if not rows:
        return None
    overs = {p.key: p.end_over - p.start_over + 1 for p in phase_bounds(ctx.fmt, ctx.gender)}
    # Runs per over in each phase, across both kinds of win: the phase that stands out names the card.
    rate = {k: sum(_num(r.get(k)) or 0 for r in rows) / (overs.get(k, 1) * len(rows)) for k in ("powerplay", "middle", "death")}
    lead = max(rate, key=rate.get)
    spread = (max(rate.values()) - min(rate.values())) / max(1e-9, sum(rate.values()) / 3)
    return Card(
        id="winning-phases", chapter="ground", visual="phase_bars",
        title=_PHASE_WORDS[lead],
        sample=_venue_sample(ctx, n), n=n,
        payload={"phases": phases},
        info=Info(
            what="Average runs in each phase for sides that won here, batting first and chasing.",
            how_to_read="Each bar is one winning innings, split into the powerplay, middle overs and death overs.",
            definitions=[("Phases", f"{ctx.fmt}: powerplay overs 1–{overs['powerplay']}, then middle overs, then the last {overs['death']} overs.")],
        ),
        relevance=1.0 + min(spread, 1.0),
    )


def results_split(ctx) -> Optional[Card]:
    rec = ctx.venue_record
    n = int(rec.get("total_matches") or 0)
    if not n:
        return None
    bat, chase = int(rec.get("batting_first_wins") or 0), int(rec.get("batting_second_wins") or 0)
    decided = bat + chase
    if bat == chase:
        title = f"Batting first and chasing have won {bat} each here"
    elif chase > bat:
        title = f"Chasing sides have won {chase} of {decided} here"
    else:
        title = f"Sides batting first have won {bat} of {decided} here"
    return Card(
        id="results", chapter="ground", visual="results_split",
        title=title, sample=_venue_sample(ctx, n), n=n,
        payload={k: rec.get(k) for k in ("total_matches", "batting_first_wins", "batting_second_wins")},
        info=Info(
            what="Matches won by the side batting first and by the side chasing at this ground.",
            how_to_read="The bar splits every match with a result; no-results are shown separately.",
        ),
        query_url=ctx.query_url(query_mode="team_innings", innings=1, group_by="match_outcome"),
        relevance=1.0 + (abs(chase - bat) / decided if decided else 0),
    )


def benchmarks(ctx) -> Optional[Card]:
    rec = ctx.venue_record
    n = int(rec.get("total_matches") or 0)
    low, high = _num(rec.get("lowest_total_defended")), _num(rec.get("highest_total_chased"))
    if not n or low is None or high is None:
        return None
    return Card(
        id="totals", chapter="ground", visual="benchmarks",
        title=f"{round(low)} has been defended here, and {round(high)} chased",
        sample=_venue_sample(ctx, n), n=n,
        payload={k: rec.get(k) for k in (
            "total_matches", "lowest_total_defended", "average_chasing_score", "average_first_innings",
            "average_winning_score", "highest_total_chased", "average_second_innings")},
        info=Info(
            what="First-innings benchmarks at this ground.",
            how_to_read="Blue dots are totals the batting side won with; orange dots are targets that were chased down.",
            definitions=[("Average total defended", "The average first-innings score of sides that won batting first.")],
        ),
        query_url=ctx.query_url(query_mode="team_innings", innings=1, group_by="match_outcome"),
    )


def recent_results(ctx) -> Optional[Card]:
    matches = (ctx.history.get("venue_results") or [])[:5]
    if not matches:
        return None
    decided = [m for m in matches if m.get("winner") not in (None, "", "-")]
    chased = sum(1 for m in decided if not m.get("won_batting_first"))
    if not decided:
        title = f"Recent results at {short_venue(ctx.venue)}"
    elif chased * 2 > len(decided):
        title = f"Chasing sides won {chased} of the last {len(decided)} here"
    elif chased * 2 < len(decided):
        title = f"Sides batting first won {len(decided) - chased} of the last {len(decided)} here"
    else:
        title = f"An even split over the last {len(decided)} here"
    return Card(
        id="recent-results", chapter="ground", visual="recent_results",
        title=title, sample=f"Last {len(matches)} matches at {short_venue(ctx.venue)}", n=len(matches),
        payload={"matches": matches},
        info=Info(what="The most recent matches at this ground in the selected window; the winning side is highlighted."),
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
    line, _ = leader_line(ctx.t1, a, ctx.t2, b)
    return Card(
        id="head-to-head", chapter="teams", visual="h2h",
        title=f"{line} in their last {plural(n, 'meeting')}",
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


EXISTING = (
    CardSpec("par", "glance", "What total should we expect?", par, sample=SampleRule(hide_below=3), weight=2.0),
    CardSpec("winning-phases", "ground", "How are winning innings built here?", winning_phases, sample=SampleRule(hide_below=3)),
    CardSpec("results", "ground", "Does batting first or chasing win here?", results_split, sample=SampleRule(hide_below=3), weight=1.2),
    CardSpec("totals", "ground", "What total wins here?", benchmarks, sample=SampleRule(hide_below=3)),
    CardSpec("recent-results", "ground", "What happened here lately?", recent_results, sample=SampleRule(flag_below=0)),
    CardSpec("head-to-head", "teams", "Who wins when these two meet?", head_to_head),
    CardSpec("form", "teams", "Who's in form?", form, sample=SampleRule(flag_below=0)),
)
