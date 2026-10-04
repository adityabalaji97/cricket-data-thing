"""
The ground chapter's new cards (chunk 5 of MATCH_PREVIEW_VIZ_PLAN.md): B1 what wins, B2 the
shape of an innings, B3 phases against the competition, B5 pace and spin, B6 boundary zones and
B8 dismissals. B4 (the chase band) and the kept cards live in existing.py.

Comparison cards (B2, B3, B5) set the ground against every ground in its main competition, same
window ("v all IPL grounds"). Boundary zones and dismissals follow the ground rule from the
data analysis (analysis/preview/ground_zone_differences.py, ground_dismissal_differences.py): they
appear only where the ground really differs from all grounds, and their titles name the
difference. A share that is true everywhere is not a ground trait.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from scipy import stats

from services.analytics_common import phase_bounds
from services.preview_cards.copy import plural, short_venue, span
from services.preview_cards.spec import Card, CardSpec, Info, SampleRule

BASELINES = json.loads((Path(__file__).parent / "baselines.json").read_text())

ZONES = {1: "Fine leg", 2: "Square leg", 3: "Midwicket", 4: "Long on",
         5: "Long off", 6: "Cover", 7: "Point", 8: "Third man"}
LEG_SIDE = (1, 2, 3, 4)
DISMISSALS = {"caught": "Caught", "bowled": "Bowled", "lbw": "LBW", "other": "Stumped and other"}
DISMISSAL_KIND = {"caught": "caught", "caught and bowled": "caught", "bowled": "bowled",
                  "leg before wicket": "lbw", "stumped": "other", "hit wicket": "other"}
PHASE_NAMES = {"powerplay": "powerplay", "middle": "middle overs", "death": "death overs"}

# The ground rule (MATCH_PREVIEW_VIZ_PLAN.md, sign-off decision 4).
ZONE_FLOOR = 400        # zoned boundaries, all seasons
DISMISSAL_FLOOR = 300   # bowler wickets, all seasons
RULE_P = 0.01
RULE_RATIO = 1.25
RULE_POINTS = 2.5   # and that share at least 2.5 points above usual: 3% -> 4% is real but no trait


def _phase_of(fmt: str, gender: str):
    bounds = phase_bounds(fmt, gender)
    return lambda over: next((p.key for p in bounds if p.start_over <= over <= p.end_over), None)


def _comparison_sample(ctx, what: str) -> str:
    comp = ctx.comparison_scope["label"]
    return f"{what} at {short_venue(ctx.venue)} v all {comp} grounds · {span(ctx.start, ctx.end)}"


def _sum(rows, key, **match):
    return sum(r.get(key) or 0 for r in rows if all(r.get(k) == v for k, v in match.items()))


# --------------------------------------------------------------------------------------------
# B1: what total wins here (scatter); the benchmark strip is its thin-sample fallback
# --------------------------------------------------------------------------------------------

SCATTER_FLOOR = 20


def what_wins(ctx) -> Optional[Card]:
    full = [m for m in ctx.ground_matches if m.full_first and m.result]
    if len(full) < SCATTER_FLOOR:
        from services.preview_cards.existing import benchmarks
        return benchmarks(ctx)  # 10-19 matches: the five benchmarks read better than a sparse scatter
    years = sorted({m.year for m in full})
    ipl = ctx.main_competition == "IPL"
    since = 2023 if ipl and years[0] < 2023 <= years[-1] else (years[-3] if len(years) > 3 else None)
    recent = [m for m in full if since is None or m.year >= since]
    primer = ctx.primer_par
    if primer and not primer["international"]:
        anchor = primer["series"][-1]["par"]
    else:
        totals = sorted(m.first["runs"] for m in recent)
        anchor = totals[len(totals) // 2]
    line = int(round(anchor / 10.0) * 10)
    above = [m for m in recent if m.first["runs"] >= line]
    won = sum(1 for m in above if m.result == "bat")
    when = f" since {since}" if since else ""
    if above:
        title = f"{line} has won {won} of {len(above)} times here{when}"
    else:
        title = f"Nobody has posted {line} here{when}"
    points = [{"year": m.year, "total": m.first["runs"], "won": m.result == "bat",
               "recent": since is None or m.year >= since} for m in full]
    return Card(
        id="totals", chapter="ground", visual="totals_scatter",
        title=title, help=f"Each dot is one first innings; the dashed line is {line}",
        sample=f"{plural(len(full), 'first innings')} at {short_venue(ctx.venue)} · {span(ctx.start, ctx.end)}",
        n=len(full),
        payload={"points": points, "line": line, "since": since,
                 "years": [years[0], years[-1]], "faded_label": f"before {since}" if since else None},
        info=Info(
            what="Every first-innings total here, and whether the side batting first went on to win.",
            how_to_read=f"Blue dots were defended, orange dots were chased down. The dashed line at {line} is "
                        "close to today's par."
                        + (f" Faded dots are from before {since}" + (", when the IPL's Impact Player rule "
                           "came in and totals rose." if ipl and since == 2023 else ".") if since else ""),
            definitions=[("First innings", "Only innings that ran their full overs; rain-shortened ones are left out.")],
        ),
        query_url=ctx.query_url(query_mode="team_innings", group_by=["match_id", "innings", "match_outcome"],
                                innings=1, dimension_filters="full_length:eq:1"),
        relevance=1.2,
    )


# --------------------------------------------------------------------------------------------
# B2 and B3: the ground against its competition
# --------------------------------------------------------------------------------------------

def _innings_n(rows) -> int:
    """Innings in an over-by-bowler-kind profile: every innings has a first over, bowled by one kind."""
    return sum(r.get("innings_count") or 0 for r in rows if r.get("over") == 0)


def _per_over(rows) -> Dict[int, Dict[str, float]]:
    """Average runs and wickets per innings in each over (both innings, every bowler)."""
    out = {}
    for over in sorted({r["over"] for r in rows if r.get("over") is not None}):
        sel = [r for r in rows if r.get("over") == over]
        # One bowler per over, so the over's innings split across the pace/spin rows: add them.
        innings = sum(r.get("innings_count") or 0 for r in sel)
        if innings:
            out[over] = {"runs": sum(r["runs"] or 0 for r in sel) / innings,
                         "wickets": sum(r["wickets"] or 0 for r in sel) / innings,
                         "balls": sum(r["balls"] or 0 for r in sel), "innings": innings}
    return out


def innings_shape(ctx) -> Optional[Card]:
    prof = ctx.over_profile
    here, everywhere = _per_over(prof["ground"]), _per_over(prof["all"])
    overs = [o for o in sorted(here) if o in everywhere]
    if len(overs) < 10:
        return None
    n = _innings_n(prof["ground"])
    cum_here, cum_all, a, b = [], [], 0.0, 0.0
    for o in overs:
        a += here[o]["runs"]
        b += everywhere[o]["runs"]
        cum_here.append(round(a, 1))
        cum_all.append(round(b, 1))
    gap = round(cum_here[-1] - cum_all[-1])
    comp = ctx.comparison_scope["label"]
    last = overs[-1] + 1
    if abs(gap) < 5:
        title = f"An innings here tracks the {comp} average, over by over"
    else:
        title = (f"An innings here is about {abs(gap)} runs {'ahead of' if gap > 0 else 'behind'} "
                 f"the {comp} by the {last}th over")
    return Card(
        id="innings-shape", chapter="ground", visual="worm",
        title=title, help="Average runs scored by the end of each over",
        sample=_comparison_sample(ctx, plural(n, "innings")), n=n,
        payload={"overs": [o + 1 for o in overs], "here": cum_here, "all": cum_all,
                 "here_label": short_venue(ctx.venue), "all_label": f"All {comp}"},
        info=Info(
            what=f"How quickly runs come here, compared with every {comp} ground in the same seasons.",
            how_to_read="Each line is the average score at the end of each over, both innings together. A line "
                        "that pulls away early means fast starts; one that bends up late means big finishes.",
            definitions=[("Both innings", "Chases that finish early stop adding overs, so the last overs rest "
                                          "on fewer innings.")],
        ),
        query_url=ctx.query_url(args=ctx.query_args(["over"], comparison=True)),
        relevance=1.0 + min(abs(gap) / 30.0, 1.0),
    )


def phases_vs_competition(ctx) -> Optional[Card]:
    prof = ctx.over_profile
    if not prof["ground"] or not prof["all"]:
        return None
    phase = _phase_of(ctx.fmt, ctx.gender)
    keys = [p.key for p in phase_bounds(ctx.fmt, ctx.gender)]

    def rates(rows):
        out = {}
        for k in keys:
            sel = [r for r in rows if phase(r["over"]) == k]
            balls = sum(r["balls"] or 0 for r in sel)
            if balls:
                out[k] = {"rpo": 6.0 * sum(r["runs"] or 0 for r in sel) / balls,
                          "wpo": 6.0 * sum(r["wickets"] or 0 for r in sel) / balls, "balls": balls}
        return out

    here, everywhere = rates(prof["ground"]), rates(prof["all"])
    # Rounded once, here, so the title and the bars print the same number.
    rows = [{"phase": k, "here": round(here[k]["rpo"], 1), "all": round(everywhere[k]["rpo"], 1),
             "diff": round(here[k]["rpo"] - everywhere[k]["rpo"], 1) + 0.0,
             "wickets_here": round(here[k]["wpo"], 2), "wickets_all": round(everywhere[k]["wpo"], 2)}
            for k in keys if k in here and k in everywhere]
    if len(rows) < len(keys):
        return None
    for r in rows:
        r["diff"] = 0.0 if r["diff"] == 0 else r["diff"]  # no "-0.0"
    big = max(rows, key=lambda r: abs(r["diff"]))
    signs = {r["diff"] > 0 for r in rows if abs(r["diff"]) >= 0.2}
    name = PHASE_NAMES[big["phase"]]
    if abs(big["diff"]) < 0.3:
        title = "Runs come at the usual rate here in every phase"
    elif len(signs) == 1 and all(abs(r["diff"]) >= 0.2 for r in rows):
        title = (f"Runs come {'faster' if big['diff'] > 0 else 'slower'} here in every phase, most in the "
                 f"{name} ({big['diff']:+.1f} an over)")
    else:
        title = f"Runs come {'faster' if big['diff'] > 0 else 'slower'} here in the {name} ({big['diff']:+.1f} an over)"
    comp = ctx.comparison_scope["label"]
    n = _innings_n(prof["ground"])
    return Card(
        id="phases", chapter="ground", visual="phase_diverging",
        title=title, help=f"Bars to the right: more runs an over than the {comp} average",
        sample=_comparison_sample(ctx, plural(n, "innings")), n=n,
        payload={"rows": rows, "comparison": comp},
        info=Info(
            what=f"Runs per over in each phase here, minus the average across every {comp} ground.",
            how_to_read="Right of the line, runs come faster here than usual; left, slower. The numbers beside "
                        "each phase are the run rates here and across the competition.",
            definitions=[("Phases", "Powerplay, middle overs and death overs, as on the other cards.")],
            method="Wickets per over, here v the competition: " + ", ".join(
                f"{PHASE_NAMES[r['phase']]} {r['wickets_here']:.2f} v {r['wickets_all']:.2f}" for r in rows) + ".",
        ),
        query_url=ctx.query_url(args=ctx.query_args(["phase"], comparison=True)),
        relevance=1.0 + min(abs(big["diff"]) / 2.0, 1.0),
    )


# --------------------------------------------------------------------------------------------
# B5: pace and spin
# --------------------------------------------------------------------------------------------

def pace_spin(ctx) -> Optional[Card]:
    prof = ctx.over_profile
    if not prof["ground"] or not prof["all"]:
        return None
    phase = _phase_of(ctx.fmt, ctx.gender)
    keys = [p.key for p in phase_bounds(ctx.fmt, ctx.gender)]

    def split(rows):
        out = {}
        for k in keys:
            sel = [r for r in rows if phase(r["over"]) == k]
            kinds = {}
            for kind, label in (("spin bowler", "spin"), ("pace bowler", "pace")):
                part = [r for r in sel if r.get("bowl_kind") == kind]
                balls = sum(r["balls"] or 0 for r in part)
                kinds[label] = {"balls": balls, "runs": sum(r["runs"] or 0 for r in part),
                                "wickets": sum(r["wickets"] or 0 for r in part)}
            total = kinds["spin"]["balls"] + kinds["pace"]["balls"]
            if total:
                out[k] = {**kinds, "spin_share": kinds["spin"]["balls"] / total}
        return out

    here, everywhere = split(prof["ground"]), split(prof["all"])
    if any(k not in here or k not in everywhere for k in keys):
        return None
    rows = []
    for k in keys:
        h = here[k]
        rows.append({
            "phase": k,
            "spin_pct": round(100 * h["spin_share"]),
            "spin_pct_all": round(100 * everywhere[k]["spin_share"]),
            "spin_econ": round(6 * h["spin"]["runs"] / h["spin"]["balls"], 1) if h["spin"]["balls"] else None,
            "pace_econ": round(6 * h["pace"]["runs"] / h["pace"]["balls"], 1) if h["pace"]["balls"] else None,
            "spin_balls": h["spin"]["balls"], "pace_balls": h["pace"]["balls"],
            "spin_wickets": h["spin"]["wickets"], "pace_wickets": h["pace"]["wickets"],
        })
    big = max(rows, key=lambda r: abs(r["spin_pct"] - r["spin_pct_all"]))
    gap = big["spin_pct"] - big["spin_pct_all"]
    comp = ctx.comparison_scope["label"]
    name = PHASE_NAMES[big["phase"]]
    if abs(gap) < 5:
        mid = next(r for r in rows if r["phase"] == "middle")
        title = f"Spin bowls {mid['spin_pct']}% of the middle overs here, about the {comp} norm"
    else:
        title = f"Spin bowls {big['spin_pct']}% of the {name} here, against {big['spin_pct_all']}% across the {comp}"
    balls = sum(r["spin_balls"] + r["pace_balls"] for r in rows)
    innings = _innings_n(prof["ground"])
    return Card(
        id="pace-spin", chapter="ground", visual="pace_spin",
        title=title, help=None,
        sample=_comparison_sample(ctx, f"{balls:,} balls"), n=innings,
        payload={"rows": rows, "comparison": comp},
        info=Info(
            what="How the overs are shared between spin and pace in each phase here, and what each conceded.",
            how_to_read=f"Each bar splits a phase's balls between spin (blue) and pace (orange). The tick shows "
                        f"spin's share across every {comp} ground. Economy is runs per over.",
        ),
        query_url=ctx.query_url(args=ctx.query_args(["phase", "bowl_kind"], comparison=True)),
        relevance=1.0 + min(abs(gap) / 20.0, 1.0),
    )


# --------------------------------------------------------------------------------------------
# B6 and B8: shown only where the ground differs from all grounds
# --------------------------------------------------------------------------------------------

def _differs(counts: Dict, baseline: Dict[str, float]):
    """
    The ground rule: (top key, its share ratio) when the counts clearly differ from the baseline
    shares, else None. Clearly = chi-square p < RULE_P, and some key at RULE_RATIO× its usual
    share and RULE_POINTS above it.
    """
    n = sum(counts.values())
    keys = list(baseline)
    _, p = stats.chisquare([counts.get(k, 0) for k in keys], [baseline[k] * n for k in keys])
    if p >= RULE_P:
        return None
    standouts = {k: (counts.get(k, 0) / n) / baseline[k] for k in keys
                 if baseline[k] > 0 and 100 * (counts.get(k, 0) / n - baseline[k]) >= RULE_POINTS}
    if not standouts:
        return None
    top = max(standouts, key=standouts.get)
    return (top, standouts[top]) if standouts[top] >= RULE_RATIO else None


def boundary_zones(ctx) -> Optional[Card]:
    if ctx.gender != "male":
        return None  # the baseline is men's T20
    counts = {str(r["wagon_zone"]): (r.get("fours") or 0) + (r.get("sixes") or 0)
              for r in ctx.ground_zones if r.get("wagon_zone") in ZONES}
    n = sum(counts.values())
    if n < ZONE_FLOOR:
        return None
    base = BASELINES["boundary_zones"]["share"]
    found = _differs(counts, base)
    if not found:
        return None
    top, ratio = found
    zones = [{"zone": int(z), "name": ZONES[int(z)], "boundaries": counts.get(z, 0),
              "pct": round(100 * counts.get(z, 0) / n, 1), "usual_pct": round(100 * base[z], 1)} for z in base]
    leg = round(100 * sum(counts.get(str(z), 0) for z in LEG_SIDE) / n)
    return Card(
        id="boundary-zones", chapter="ground", visual="boundary_zones",
        title=f"{ZONES[int(top)]} gets {ratio:.1f}× its usual share of boundaries here",
        help="Share of boundaries hit to each part of the ground, for a right-hander",
        sample=f"{n:,} boundaries with a direction at {short_venue(ctx.venue)} · every season", n=n,
        payload={"zones": zones, "top": int(top), "leg_side_pct": leg},
        info=Info(
            what="Where the fours and sixes go at this ground, against every men's T20 ground.",
            how_to_read="Darker wedges take more of the boundaries. This card only appears where a ground's "
                        "pattern clearly differs from the usual one; most grounds look alike.",
            definitions=[("Ground rule", "400+ boundaries with a direction (all seasons), a chi-square test "
                                         "against all grounds at p < 0.01, and one zone at 1.25× its usual "
                                         "share and 2.5 points above it."),
                         ("Direction", "Recorded relative to the batter; left-handers' shots are mirrored.")],
            method="Baseline: every men's T20 ground, 2015 on (services/preview_cards/baselines.json).",
        ),
        query_url=ctx.query_url(args=ctx.query_args(["wagon_zone"], all_time=True)),
        relevance=1.5 + min(ratio - 1.0, 1.0),
    )


def dismissals(ctx) -> Optional[Card]:
    if ctx.gender != "male":
        return None  # the baseline is men's T20
    counts: Dict[str, int] = {}
    for r in ctx.ground_dismissals:
        kind = DISMISSAL_KIND.get(r.get("dismissal"))
        if kind:
            counts[kind] = counts.get(kind, 0) + (r.get("wickets") or 0)
    n = sum(counts.values())
    if n < DISMISSAL_FLOOR:
        return None
    base = BASELINES["dismissals"]["share"]
    found = _differs(counts, base)
    if not found:
        return None
    top, ratio = found
    rows = sorted(({"kind": k, "label": DISMISSALS[k], "n": counts.get(k, 0),
                    "pct": round(100 * counts.get(k, 0) / n), "usual_pct": round(100 * base[k])} for k in base),
                  key=lambda r: -r["n"])
    label = DISMISSALS[top].lower()
    title = (f"{DISMISSALS[top]} takes {ratio:.1f}× its usual share of wickets here"
             if top == "other" else f"Batters are {label} {ratio:.1f}× as often as usual here")
    return Card(
        id="dismissals", chapter="ground", visual="dismissals",
        title=title, help=None,
        sample=f"{n:,} bowler wickets at {short_venue(ctx.venue)} · every season", n=n,
        payload={"rows": rows, "top": top},
        info=Info(
            what="How batters get out at this ground, against every men's T20 ground.",
            how_to_read="Each slice is a way of getting out; the small figure beside it is the usual share. "
                        "This card only appears where a ground clearly differs: caught is about 68% everywhere.",
            definitions=[("Bowler wickets", "Run-outs and retirements are left out."),
                         ("Ground rule", "300+ bowler wickets (all seasons), a chi-square test against all "
                                         "grounds at p < 0.01, and one kind at 1.25× its usual share and 2.5 "
                                         "points above it.")],
            method="Baseline: every men's T20 ground, 2015 on (services/preview_cards/baselines.json).",
        ),
        query_url=ctx.query_url(args=ctx.query_args(["dismissal"], all_time=True)),
        relevance=1.4 + min(ratio - 1.0, 1.0),
    )


GROUND = (
    # B1 replaces the benchmark strip ("totals") from 20 matches; below that the strip stays.
    CardSpec("totals", "ground", "What total wins here?", what_wins, sample=SampleRule(hide_below=10)),
    CardSpec("innings-shape", "ground", "How does an innings unfold here?", innings_shape,
             sample=SampleRule(hide_below=10)),
    CardSpec("phases", "ground", "Which phase is unusual here?", phases_vs_competition,
             sample=SampleRule(hide_below=10)),
    CardSpec("pace-spin", "ground", "Pace or spin here?", pace_spin, sample=SampleRule(hide_below=10)),
    CardSpec("boundary-zones", "ground", "Where do the boundaries go?", boundary_zones, formats=("T20",),
             sample=SampleRule(flag_below=0)),
    CardSpec("dismissals", "ground", "How do batters get out here?", dismissals, formats=("T20",),
             sample=SampleRule(flag_below=0)),
)
