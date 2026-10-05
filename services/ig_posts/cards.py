"""
Post cards: each answers the question from one angle, as the JSON a story card carries ({id, visual, title, help,
sample, payload}) so the app draws it (src/components/story/postVisuals.jsx, or visuals.jsx for boundary_zones).

Titles are sentences written here from the rows; every number in a title or payload comes from the context's rows
(one query-builder call) or, for zones, from one more call with the same scope.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.ig_posts.angles import Angle
from services.ig_posts.context import QuestionContext, usable

ZONES = {1: "Fine leg", 2: "Square leg", 3: "Midwicket", 4: "Long on", 5: "Long off", 6: "Cover", 7: "Point",
         8: "Third man"}
LEG_SIDE = (1, 2, 3, 4)

#: How the leader of each angle is described in a verdict ("Head scores fastest").
SUPERLATIVE = {
    ("batter", "sr"): "scores fastest", ("batter", "boundary"): "finds the rope most often",
    ("batter", "dot"): "gets stuck least", ("batter", "raa"): "adds the most runs above average",
    ("batter", "impact"): "has the most Impact", ("batter", "wpa"): "adds the most win probability",
    ("batter", "bpd"): "is the hardest to dismiss", ("batter", "average"): "averages the most",
    ("batter", "control"): "is the most in control", ("batter", "sixes"): "hits the most sixes",
    ("bowler", "economy"): "is the most economical", ("bowler", "dot"): "bowls the most dots",
    ("bowler", "raa"): "saves the most runs", ("bowler", "wpa"): "adds the most win probability",
    ("bowler", "strike"): "strikes most often", ("bowler", "wickets_inns"): "takes the most wickets an innings",
    ("bowler", "control"): "beats the bat most", ("partnership", "average"): "average the most together",
    ("partnership", "sr"): "score fastest", ("partnership", "control"): "are the most in control",
    ("partnership", "boundary"): "find the rope most often", ("partnership", "dot"): "get stuck least",
    ("partnership", "bpd"): "last the longest",
}


def fmt(value: Optional[float], kind: str) -> str:
    """Python twin of postVisuals fmt(), for titles."""
    if value is None:
        return "–"
    v = float(value)
    sign = lambda s: ("+" if v > 0 else "−" if v < 0 else "") + s  # noqa: E731
    return {
        "int": f"{round(v):,}", "pct1": f"{v:.1f}%", "pct0": f"{round(v)}%", "dec2": f"{v:.2f}",
        "signed0": sign(f"{abs(v):.0f}"), "signed1": sign(f"{abs(v):.1f}"), "signed2": sign(f"{abs(v):.2f}"),
    }.get(kind, f"{v:.1f}")


def short(name: str) -> str:
    parts = str(name).split()
    if len(parts) < 2:
        return name
    for i, p in enumerate(parts[1:], 1):
        if p.lower() in ("de", "du", "van", "von", "der", "ul", "al", "da", "di"):
            return " ".join(parts[i:])
    return parts[-1]


def pair_short(name: str) -> str:
    return " & ".join(short(n) for n in str(name).split(" & "))


def display(ctx: QuestionContext, name: str) -> str:
    """Surname, unless another player in the field shares it (three Sharmas in the IPL): then the full name."""
    if ctx.role == "partnership":
        return pair_short(name)
    clash = sum(1 for r in ctx.rows if short(r["name"]) == short(name)) > 1
    return name if clash else short(name)


def card(cid: str, visual: str, title: str, payload: Dict[str, Any], sample: str, help_: str = "") -> Dict[str, Any]:
    return {"id": cid, "visual": visual, "title": title, "help": help_, "sample": sample, "payload": payload}


def bars(ctx: QuestionContext, angle: Angle, sample: str, top: int = 8) -> Optional[Dict[str, Any]]:
    ranked = ctx.ranked(angle)
    if len(ranked) < 3:
        return None
    rows = ranked[:top]
    subj = ctx.find(ctx.subject) if ctx.subject else None
    if subj and subj not in rows and usable(subj, angle):
        rows = rows[: top - 1] + [subj]
    lead = ranked[0]
    rank_of = {r["name"]: i + 1 for i, r in enumerate(ranked)}
    payload = {
        "metric": {"label": angle.label, "format": angle.format, "signed": angle.format.startswith("signed")},
        "rows": [{"name": r["name"], "value": r[angle.metric], "highlight": r["name"] == ctx.subject,
                  "detail": f"#{rank_of[r['name']]} of {len(ranked)}" if r["name"] == ctx.subject and rank_of[r["name"]] > top - 1 else None}
                 for r in rows],
    }
    title = f"{lead['name']} leads on {angle.label}: {fmt(lead[angle.metric], angle.format)}"
    if subj and subj["name"] != lead["name"] and usable(subj, angle):
        title += f" ({display(ctx, subj['name'])}: #{rank_of[subj['name']]})"
    help_ = ("Lower is better" if not angle.higher_better else "Higher is better") + f" · {angle.description.split('. ')[0]}"
    return card(f"bars-{angle.id}", "metric_bars", title, payload, sample, help_)


def scatter(ctx: QuestionContext, ax: Angle, ay: Angle, sample: str, az: Optional[Angle] = None) -> Optional[Dict[str, Any]]:
    rows = [r for r in ctx.rows if usable(r, ax) and usable(r, ay)]
    if len(rows) < 8:
        return None
    pct = lambda r, a: ctx.percentile(r, a) or 0  # noqa: E731
    best = sorted(rows, key=lambda r: pct(r, ax) + pct(r, ay), reverse=True)
    labelled = {r["name"]: i + 1 for i, r in enumerate(best[:6])}  # numbered on the chart, best first
    subj = ctx.find(ctx.subject) if ctx.subject else None
    points = [{"name": r["name"], "x": r[ax.metric], "y": r[ay.metric], "highlight": bool(subj) and r["name"] == subj["name"],
               "short": display(ctx, r["name"]), "label": labelled.get(r["name"]),
               "zp": ctx.percentile(r, az) if az and usable(r, az) else None} for r in rows]
    payload = {"x": {"label": ax.label, "format": ax.format, "higher_better": ax.higher_better},
               "y": {"label": ay.label, "format": ay.format, "higher_better": ay.higher_better},
               "z": {"label": az.label} if az else None, "points": points, "box": bool(subj)}
    if subj and usable(subj, ax) and usable(subj, ay):
        beat = [r for r in rows if r["name"] != subj["name"]
                and (r[ax.metric] > subj[ax.metric]) == ax.higher_better and r[ax.metric] != subj[ax.metric]
                and (r[ay.metric] > subj[ay.metric]) == ay.higher_better and r[ay.metric] != subj[ay.metric]]
        who = display(ctx, subj["name"])
        title = (f"Only {len(beat)} of {len(rows) - 1} beat {who} on both {ay.label} and {ax.label}" if beat
                 else f"Nobody beats {who} on both {ay.label} and {ax.label}")
    else:
        top = best[0]
        title = f"{display(ctx, top['name'])} combines {ay.label} and {ax.label} best"
    help_ = "Up and right is better" + ("" if ax.higher_better and ay.higher_better else " (lower-is-better axes run backwards)")
    return card(f"scatter-{ax.id}-{ay.id}", "scatter_plus", title, payload, sample, help_)


def zones(ctx: QuestionContext, name: str, sample_scope: str) -> Optional[Dict[str, Any]]:
    """Where the named batter's boundaries go, against the field's (same scope)."""
    if ctx.role != "batter":
        return None
    def counts(rows):
        return {int(r["wagon_zone"]): (r.get("fours") or 0) + (r.get("sixes") or 0)
                for r in rows if r.get("wagon_zone") is not None and int(r["wagon_zone"]) in ZONES}
    mine = counts(ctx.query(group_by=["wagon_zone"], batters=[name], min_balls=1))
    field = counts(ctx.query(group_by=["wagon_zone"], min_balls=1))
    n, nf = sum(mine.values()), sum(field.values())
    if n < 40 or not nf:
        return None
    zones_ = [{"zone": z, "name": ZONES[z], "boundaries": mine.get(z, 0), "pct": round(100 * mine.get(z, 0) / n, 1),
               "usual_pct": round(100 * field.get(z, 0) / nf, 1)} for z in ZONES]
    top = max(zones_, key=lambda z: z["pct"])
    leg = round(100 * sum(mine.get(z, 0) for z in LEG_SIDE) / n)
    title = f"{display(ctx, name)} hits {top['pct']:.0f}% of boundaries to {top['name'].lower()} (field: {top['usual_pct']:.0f}%)"
    return card(f"zones-{short(name).lower()}", "boundary_zones", title, {"zones": zones_, "top": top["zone"], "leg_side_pct": leg},
                f"{n:,} boundaries with a direction · {sample_scope}", "Share of boundaries to each part of the ground, as a right-hander")


def scorecard(ctx: QuestionContext, angles: List[Angle], sample: str, top: int = 7) -> Optional[Dict[str, Any]]:
    """The split verdict: top rows by mean percentile across the angles, every cell shaded by its percentile."""
    ranked = ctx.composite(angles)
    if len(ranked) < 4:
        return None
    rows = ranked[:top]
    subj = next((r for r in ranked if r["name"] == ctx.subject), None) if ctx.subject else None
    if subj and subj not in rows:
        rows = rows[: top - 1] + [subj]
    leaders = {a.id: ctx.leader(a)["name"] for a in angles if ctx.leader(a)}
    payload = {
        "metrics": [{"key": a.id, "label": a.short, "format": a.format} for a in angles],
        "rows": [{"name": r["name"], "short": display(ctx, r["name"]), "values": {a.id: r[a.metric] for a in angles}, "pct": r["pcts"],
                  "leader": [k for k, v in leaders.items() if v == r["name"]], "highlight": r["name"] == ctx.subject}
                 for r in rows],
        "verdict": verdict(ctx, ranked[0], angles, leaders),
        "method": "Overall: average percentile across these measures in the whole field. Shade: percentile (brighter is "
                  "better). Ring: leads the field.",
    }
    verb = "lead" if ctx.role == "partnership" else "leads"
    title = f"{display(ctx, ranked[0]['name'])} {verb} overall, but not on everything"
    if len(set(leaders.values())) == 1:
        title = f"{display(ctx, ranked[0]['name'])} {verb} on every measure"
    return card("scorecard", "scorecard", title, payload, sample, "")


def verdict(ctx: QuestionContext, top: Dict[str, Any], angles: List[Angle], leaders: Dict[str, str]) -> str:
    """'Gill leads overall; Head scores fastest and Kohli is the hardest to dismiss.' Written from the leaders."""
    others: Dict[str, List[str]] = {}
    for a in angles:
        who = leaders.get(a.id)
        if who and who != top["name"]:
            others.setdefault(who, []).append(SUPERLATIVE.get((ctx.role, a.id), f"leads on {a.label}"))
    head = f"{display(ctx, top['name'])} {'lead' if ctx.role == 'partnership' else 'leads'} overall"
    if not others:
        return f"{head}, and on every measure."
    parts = [f"{display(ctx, who)} {' and '.join(phrases[:2])}" for who, phrases in list(others.items())[:3]]
    tail = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    return f"{head}; {tail}."
