"""
"The case for ..." in ODIs: a spotlight post arguing a bowler back into India's ODI side, from a spec
(services/ig_posts/spotlight.SPECS, type "case_odi"). ODIs have no Impact or runs-saved numbers, so the case is made
from wickets, averages, economy and ball tracking, phase by phase.

Slides: hook; India's ODI pace since the bowler's last game (with their own last games for comparison); the deeper cut
(balls per wicket by phase against the team's pacers); the cost (economy by phase); the skill behind it (length and
false shots, only if it favours them); domestic one-day form from elsewhere (credited, confirmed figures from the spec:
Cricsheet has no Indian one-day domestic data); the doubts; the series grounds; end.

Every number on a chart comes from the query builder and every title is written from those numbers. The external
figures are text, never charted, and the post isn't made until the spec marks them confirmed.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from services.ig_posts.cards import card
from services.ig_posts.spotlight import _pct, heat, short_name

PHASES = [("New ball", 0, 9), ("Middle", 10, 39), ("Death", 40, 49)]
MIN_PHASE_BALLS = 150   # a bowler's phase needs this many balls for a number
PEER_MIN_BALLS = 240    # ODI balls since `since` to be one of the team's pacers
MIN_TRACKED = 300       # tracked balls for the length / false-shot table
STRENGTH_POINTS = 3     # percentage points above the others' median for the skill slide


def _q(db, **args) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    base = {"fmt": "ODI", "gender": "male", "limit": 2000, "metrics_perspective": "bowling"}
    return run_deliveries_query(db, **{**base, **args}).get("data") or []


def _names(names: List[str]) -> str:
    return ", ".join(names[:-1]) + f" and {names[-1]}" if len(names) > 1 else "".join(names)


def peers(db, spec) -> List[str]:
    """The team's pacers of today (ODIs since `peers_since`), measured over the longer `since` window."""
    rows = _q(db, group_by=["bowler"], bowling_teams=[spec["team"]], bowl_kind=[spec["bowl_kind"]],
              start_date=spec.get("peers_since") or spec["since"], min_balls=PEER_MIN_BALLS)
    rows = [r for r in rows if r["bowler"] != spec["player"] and (r.get("balls") or 0) >= 15 * (r.get("innings_count") or 1)]
    return [r["bowler"] for r in sorted(rows, key=lambda r: -(r.get("balls") or 0))][:7]


def since_card(db, spec) -> Optional[Dict[str, Any]]:
    """India's ODI pacers since the subject's last game, and the subject's own last games for comparison."""
    p, last = spec["player"], spec["last_game"]
    rows = _q(db, group_by=["bowler"], bowling_teams=[spec["team"]], bowl_kind=[spec["bowl_kind"]],
              start_date=date.fromordinal(last.toordinal() + 1), min_balls=150)
    rows = [r for r in rows if r.get("wickets")]
    mine = _q(db, group_by=["bowler"], bowlers=[p], bowling_teams=[spec["team"]], start_date=spec["own_from"], end_date=last)
    if len(rows) < 3 or not mine:
        return None
    me = mine[0]
    out = [{"name": short_name(r["bowler"]), "value": r["runs"] / r["wickets"],
            "detail": f"{r['wickets']} wkts · {6 * r['runs'] / r['balls']:.1f} an over"} for r in sorted(rows, key=lambda r: r["runs"] / r["wickets"])]
    out.append({"name": f"{short_name(p)} ({spec['own_from'].year})", "value": me["runs"] / me["wickets"],
                "detail": f"{me['wickets']} wkts · {6 * me['runs'] / me['balls']:.1f} an over", "highlight": True})
    used = len(rows)
    title = f"India have tried {used} pace bowlers in ODIs since {short_name(p)}'s last game"
    best = out[0]
    help_ = f"Bowling average (runs per wicket, lower is better); best since: {best['name']} {best['value']:.1f}"
    payload = {"metric": {"label": "runs per wicket", "format": "dec1", "signed": False}, "rows": out}
    return card("since", "metric_bars", title, payload,
                f"India pace bowlers with 150+ ODI balls since {last:%-d %b %Y} · his own: {spec['own_label']}", help_)


def phase_table(db, spec, bowlers: List[str]) -> Dict[str, Dict[str, Dict[str, Optional[float]]]]:
    """{bowler: {phase: {bpw, econ, balls, wickets}}} for ODIs since `since`."""
    out: Dict[str, Dict[str, Dict[str, Optional[float]]]] = {b: {} for b in bowlers}
    for label, a, b in PHASES:
        for r in _q(db, group_by=["bowler"], bowlers=bowlers, start_date=spec["since"], over_min=a, over_max=b):
            balls, wkts = r.get("balls") or 0, r.get("wickets") or 0
            ok = balls >= MIN_PHASE_BALLS
            out.setdefault(r["bowler"], {})[label] = {
                "bpw": balls / wkts if ok and wkts else None, "econ": 6 * r["runs"] / balls if ok else None,
                "balls": balls, "wickets": wkts}
    return out


def _lower_is_better(payload, table, cols, order):
    """Shading and rings for measures where fewer is better (balls per wicket, economy)."""
    for c in cols:
        flipped = _pct({b: (-table[b][c] if table[b].get(c) is not None else None) for b in order})
        have = [b for b in order if table[b].get(c) is not None]
        best = min(have, key=lambda b: table[b][c]) if have else None
        for r in payload["rows"]:
            r["pct"][c] = flipped[r["name"]]
            r["leader"] = [x for x in r["leader"] if x != c] + ([c] if r["name"] == best else [])


def phase_card(spec, phases, bowlers: List[str], measure: str) -> Optional[Dict[str, Any]]:
    p = spec["player"]
    cols = [label for label, _a, _b in PHASES]
    table = {b: {c: (phases.get(b, {}).get(c) or {}).get(measure) for c in cols} for b in bowlers}
    order = [b for b in bowlers if any(v is not None for v in table[b].values())]
    if p not in order or len(order) < 4:
        return None
    payload = heat(table, cols, p, order)
    _lower_is_better(payload, table, cols, order)
    for m in payload["metrics"]:
        m["format"] = "int" if measure == "bpw" else "dec1"
    leads = [c for c in cols if table[p].get(c) is not None
             and table[p][c] == min(table[b][c] for b in order if table[b].get(c) is not None)]
    since = spec["since"].year
    nm = short_name(p)
    if measure == "bpw":
        words = {"Middle": "in the middle overs", "Death": "at the death", "New ball": "with the new ball"}
        if leads:
            where = " or ".join([", ".join(words[c] for c in leads[:-1]), words[leads[-1]]]) if len(leads) > 1 else words[leads[0]]
            title = f"No India pacer takes ODI wickets {where} as often as {nm}"
        else:
            title = f"Where {nm} takes his ODI wickets, against India's pacers"
        bits = [f"every {table[p][c]:.0f} balls {words[c]}" for c in cols
                if table[p].get(c) is not None]
        help_ = f"Balls per wicket since {since}, fewer is better: {nm} takes one " + _names(bits)
        payload["method"] = f"Overs 1-10, 11-40, 41-50; – under {MIN_PHASE_BALLS} balls. Ring: best in the column."
        out = card("phase-wickets", "scorecard", title, payload, f"India's pacers, every ODI since {since}", help_)
        out["kicker"] = "The deeper cut"
        return out
    death = table[p].get("Death")
    cheapest = min((b for b in order if table[b].get("Death") is not None), key=lambda b: table[b]["Death"], default=None)
    title = (f"The cost: {nm} goes for {death:.1f} an over at the death" + (
        f", {short_name(cheapest)} {table[cheapest]['Death']:.1f}" if cheapest and cheapest != p else "")) if death else f"{nm}'s economy by phase"
    payload["method"] = "Runs an over by phase. Ring: cheapest in the column."
    return card("phase-economy", "scorecard", title, payload, f"India's pacers, every ODI since {since}",
                "Runs an over, fewer is better")


def skill_card(db, spec, bowlers: List[str]) -> Optional[Dict[str, Any]]:
    """Good length and false shots drawn in ODIs; only shown when the subject is in the top three on either."""
    p = spec["player"]
    lengths = _q(db, group_by=["bowler", "length"], bowlers=bowlers, start_date=spec["since"])
    control = _q(db, group_by=["bowler", "control"], bowlers=bowlers, start_date=spec["since"])
    table: Dict[str, Dict[str, Optional[float]]] = {}
    for b in bowlers:
        lr = [r for r in lengths if r["bowler"] == b and r.get("length")]
        cr = [r for r in control if r["bowler"] == b and r.get("control") is not None]
        lt, ct = sum(r["balls"] for r in lr), sum(r["balls"] for r in cr)
        if lt < MIN_TRACKED or ct < MIN_TRACKED:
            continue
        table[b] = {"Good length": 100 * sum(r["balls"] for r in lr if r["length"] == "GOOD_LENGTH") / lt,
                    "False shots": 100 * sum(r["balls"] for r in cr if r["control"] == 0) / ct}
    if p not in table or len(table) < 4:
        return None
    import statistics

    rank = {c: sorted(table, key=lambda b: -table[b][c]).index(p) + 1 for c in ("Good length", "False shots")}
    # A strength only if they lead it, or clear the others' median by STRENGTH_POINTS: "second" by half a point is a tie.
    edge = {c: table[p][c] - statistics.median(table[b][c] for b in table if b != p) for c in rank}
    strong = [c for c in rank if rank[c] == 1 or edge[c] >= STRENGTH_POINTS]
    if not strong:
        return None  # not a strength: left out rather than spun
    best = min(strong, key=lambda c: rank[c])
    order = sorted(table, key=lambda b: -table[b][best])
    payload = heat(table, ["Good length", "False shots"], p, order)
    for m in payload["metrics"]:
        m["format"] = "pct0"
    nm, me = short_name(p), table[p]
    title = (f"{nm} draws a false shot from {me['False shots']:.0f}% of his ODI balls" if best == "False shots"
             else f"{nm} lands {me['Good length']:.0f}% of his ODI balls on a good length")
    title += ", the most of India's pacers" if rank[best] == 1 else f", {['', '', 'second', 'third'][rank[best]]} among India's pacers"
    payload["method"] = "Share of tracked balls. False shot: a ball the batter didn't control (a miss, an edge, a mis-hit). Ring: best."
    return card("skill", "scorecard", title, payload, f"India's pacers, every ODI since {spec['since'].year}",
                "The skill behind the wickets")


def external_slide(spec) -> Optional[Dict[str, Any]]:
    ext = spec.get("external")
    if not ext:
        return None
    if not ext.get("confirmed"):
        raise ValueError("external figures not confirmed: set external.confirmed after checking the source")
    return {"type": "text", "heading": ext["heading"], "body": "\n".join([*ext["lines"], f"Source: {ext['source']} (not Hindsight data)"])}


def doubts_slide(db, spec) -> Dict[str, Any]:
    """What counts against: written from the numbers (IPL seasons since the last game, the time away)."""
    p = spec["player"]
    lines = []
    for r in sorted(_q(db, fmt="T20", group_by=["year"], bowlers=[p], leagues=["IPL"], include_international=False,
                       start_date=date(spec["last_game"].year, 1, 1)), key=lambda r: r["year"]):
        if r.get("balls"):
            lines.append(f"IPL {r['year']}: {r['wickets']} wickets at {6 * r['runs'] / r['balls']:.1f} an over")
    months = (spec["series_start"].year - spec["last_game"].year) * 12 + spec["series_start"].month - spec["last_game"].month
    lines.append(f"{months} months without an India game by the first ODI in New Zealand")
    lines.append("T20Is? His IPL numbers above don't make that case")
    return {"type": "text", "heading": "The doubts", "body": "\n".join(lines)}


def grounds_card(db, spec) -> Optional[Dict[str, Any]]:
    p = spec["player"]
    rows = _q(db, group_by=["venue", "year"], bowlers=[p])
    label = {v: lab for lab, names in spec["venues"] for v in names}
    mine = [r for r in rows if r["venue"] in label and r.get("balls")]
    if not mine:
        return None

    grounds: Dict[str, Dict[str, Any]] = {}
    for r in mine:  # one row a ground, all its years together
        g = grounds.setdefault(label[r["venue"]], {"balls": 0, "runs": 0, "wickets": 0, "years": set()})
        g["balls"] += r["balls"]; g["runs"] += r["runs"]; g["wickets"] += r["wickets"]; g["years"].add(int(r["year"]))
    out = [{"name": name, "value": 6 * g["runs"] / g["balls"], "highlight": True,
            "detail": f"{g['wickets']} wkts · {', '.join(str(y) for y in sorted(g['years']))}"}
           for name, g in sorted(grounds.items(), key=lambda kv: 6 * kv[1]["runs"] / kv[1]["balls"])]
    wkts = sum(r["wickets"] for r in mine)
    balls = sum(r["balls"] for r in mine)
    title = f"At this series' grounds, {short_name(p)} has {wkts} ODI wickets at {6 * sum(r['runs'] for r in mine) / balls:.1f} an over"
    c = card("grounds", "metric_bars", title, {"metric": {"label": "runs an over", "format": "dec1", "signed": False}, "rows": out[:7]},
             f"{p} · ODIs at {', '.join(dict.fromkeys(label.values()))}", "Economy by ground and year")
    c["small_sample"] = True
    return c


def build(db, spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    p = spec["player"]
    bowlers = [p] + peers(db, spec)
    phases = phase_table(db, spec, bowlers)
    deep = phase_card(spec, phases, bowlers, "bpw")
    cards_before = [c for c in (since_card(db, spec), deep) if c]
    cards_after = [c for c in (phase_card(spec, phases, bowlers, "econ"), skill_card(db, spec, bowlers)) if c]
    if not deep or len(cards_before) < 2:
        return None
    slides = ([{"type": "hook", "text": spec["hook"], "kicker": spec["kicker"], "sub": spec.get("sub", "")}]
              + [{"type": "card", "card": c, "teams": None} for c in cards_before + cards_after]
              + [s for s in (external_slide(spec), doubts_slide(db, spec)) if s]
              + [{"type": "card", "card": c, "teams": None} for c in [grounds_card(db, spec)] if c]
              + [{"type": "end", "heading": "Make your own case",
                  "body": "Every phase of every bowler, free: hindsightcricket.com"}])
    told = [c for c in cards_before + cards_after if c is not deep]  # the deeper cut has its own caption line
    verdict = " ".join(f"{c['title']}." for c in told[:2])
    return {"slides": slides, "cards": cards_before + cards_after, "title": spec["hook"], "verdict": verdict,
            "players": bowlers, "deep_cut": {"probe": "phase-wickets", "subject": p, "sentence": deep["title"], "by": "spotlight"}}
