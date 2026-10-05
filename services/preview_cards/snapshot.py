"""
A preview card as a share image (chunk 9 of MATCH_PREVIEW_VIZ_PLAN.md).

`card_image_data(card, fixture)` turns a built card into the data api/img.mjs draws at 1080x1350:
one of its existing layouts (bars, stat, line, scatter, diverging, dumbbell, stacked, field, list,
win probability), or a new one where none fits (donut for dismissals, strips for form, grid for the
pitch map). The headline is the card's own title, so the image says what the card says; the
footer carries the card's sample line.

Kept to plain data on purpose: the snapshot stores this dict and never changes, so a shared image
or embed shows exactly what the story showed on the day it was made.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

PHASE = {"powerplay": "Powerplay", "middle": "Middle overs", "death": "Death overs"}


def _signed(v: float, digits: int = 0) -> str:
    return f"{'+' if v > 0 else '−' if v < 0 else ''}{abs(v):.{digits}f}"


def _bars(rows: List[Dict[str, Any]], label: str, display: Callable[[Dict[str, Any]], str] = None,
          highlight_first: bool = True) -> Dict[str, Any]:
    out = [{"name": r["name"], "value": r["value"], "display": display(r) if display else None,
            "highlight": highlight_first and i == 0} for i, r in enumerate(rows)]
    return {"layout": "bars", "rows": out, "chart": {"label_key": "name", "metric": "value"}, "metric_label": label}


# --------------------------------------------------------------------------------------------
# one converter per visual
# --------------------------------------------------------------------------------------------

def _tiles(p, f):
    return {"layout": "list", "rows": [{"label": t["label"], "sub": "", "details": [f"{t['value']} · {t['sub']}"]}
                                       for t in p["tiles"]]}


def _par(p, f):
    series = p.get("series") or []
    if len(series) < 2:
        return {"layout": "stat", "metric_label": "Par", "value_display": str(p["value"]), "subject": p.get("caption") or ""}
    return {"layout": "line", "metric_label": "Par, season by season",
            "points": [{"x": str(r["year"]), "y": r["value"], "display": str(r["value"]),
                        "highlight": i == len(series) - 1} for i, r in enumerate(series)]}


def _chase(p, f):
    pct = round(100 * p["chase_wins"] / max(1, p["decided"]))
    verdict = "Within noise: could easily be luck" if p["within_noise"] else "A real edge, not luck"
    return {"layout": "stat", "metric_label": "Chases won", "value_display": f"{p['chase_wins']}/{p['decided']}",
            "subject": f"{pct}% · likely range {p['lo']}–{p['hi']}%",
            "rank_text": " · ".join([verdict, *(p.get("notes") or [])[:1]])}


def _phase_bars(p, f):
    phases = p.get("phases") or {}
    rows = [{"label": label, "values": {PHASE[k]: v.get(k) or 0 for k in PHASE}, "display": f"{v.get('total')} total"}
            for key, label in (("batting_first", "Won batting first"), ("chasing", "Won chasing")) if (v := phases.get(key))]
    return {"layout": "stacked", "parts": list(PHASE.values()), "rows": rows}


def _benchmarks(p, f):
    items = [("Lowest total defended", "lowest_total_defended"), ("Average target chased down", "average_chasing_score"),
             ("Average first innings", "average_first_innings"), ("Average total defended", "average_winning_score"),
             ("Highest total chased", "highest_total_chased")]
    return {"layout": "bars", "metric_label": "First-innings benchmarks", "chart": {"label_key": "name", "metric": "value"},
            "rows": [{"name": label, "value": p.get(key) or 0, "display": str(p.get(key))} for label, key in items]}


def _totals_scatter(p, f):
    # The scatter's message as a stat: how often the line has been defended, with the extremes.
    pts = [q for q in p["points"] if q["recent"]] or p["points"]
    above = [q for q in pts if q["total"] >= p["line"]]
    won = sum(1 for q in above if q["won"])
    defended = [q["total"] for q in p["points"] if q["won"]]
    chased = [q["total"] for q in p["points"] if not q["won"]]
    when = f" since {p['since']}" if p.get("since") else ""
    extremes = []
    if defended:
        extremes.append(f"lowest defended {min(defended)}")
    if chased:
        extremes.append(f"highest chased down {max(chased)}")
    return {"layout": "stat", "metric_label": "First innings", "value_display": f"{won}/{len(above)}",
            "subject": f"times {p['line']}+ was defended{when}", "rank_text": " · ".join(extremes)}


def _worm(p, f):
    overs = p["overs"]
    keep = sorted({i for i in range(len(overs)) if overs[i] in (6, 10, 15, 20, 30, 40, 50)} | {len(overs) - 1})
    return {"layout": "dumbbell", "metric_label": "Average score at the end of the over",
            "series": [p["here_label"], p["all_label"]], "metric": "runs",
            "rows": [{"label": f"After {overs[i]} overs", "a": p["here"][i], "b": p["all"][i]} for i in keep]}


def _phase_diverging(p, f):
    return {"layout": "diverging", "metric": "diff", "metric_label": f"Runs per over v the {p['comparison']} average",
            "rows": [{"label": f"{PHASE[r['phase']]} · {r['here']:.1f} v {r['all']:.1f}", "diff": r["diff"],
                      "display": _signed(r["diff"], 1)} for r in p["rows"]]}


def _pace_spin(p, f):
    return {"layout": "stacked", "parts": ["Spin", "Pace"],
            "rows": [{"label": PHASE[r["phase"]], "values": {"Spin": r["spin_pct"], "Pace": 100 - r["spin_pct"]},
                      "display": f"spin {r['spin_pct']}% (usually {r['spin_pct_all']}%)"} for r in p["rows"]]}


def _zones(p, f):
    return {"layout": "field", "metric_label": "boundaries",
            "zones": [{"zone": z["zone"], "label": z["name"], "value": z["boundaries"]} for z in p["zones"]]}


def _dismissals(p, f):
    return {"layout": "donut", "slices": [{"label": r["label"], "value": r["n"], "pct": r["pct"],
                                           "usual": r["usual_pct"]} for r in p["rows"]]}


def _recent(p, f):
    return {"layout": "list", "rows": [
        {"label": f"{m.get('team1')} v {m.get('team2')}", "sub": m.get("date") or "",
         "details": [f"{m.get('score1')} · {m.get('score2')}",
                     f"{m.get('winner')} won {'batting first' if m.get('won_batting_first') else 'chasing'}"
                     if m.get("winner") not in (None, "", "-") else "No result"]} for m in p["matches"]]}


def _h2h(p, f):
    s = p["stats"]
    recent = s.get("recent_matches") or []
    last = recent[0] if recent else None
    return {"layout": "stat", "metric_label": "Head to head",
            "value_display": f"{s.get('team1_wins', 0)}–{s.get('team2_wins', 0)}", "subject": f"{p['team1']} v {p['team2']}",
            "rank_text": (f"Last meeting {last.get('date')}: {last.get('winner')} won" if last else None)}


def _form(p, f):
    def chips(team, matches):
        return " ".join("W" if m.get("winner") in (team,) else "L" if m.get("winner") not in (None, "", "-") else "–"
                        for m in matches)
    return {"layout": "list", "rows": [
        {"label": p["team1"], "sub": f"{p['wins'][0]} wins", "details": [chips(p["team1"], p["team1_matches"])]},
        {"label": p["team2"], "sub": f"{p['wins'][1]} wins", "details": [chips(p["team2"], p["team2_matches"])]}]}


def _dumbbell(p, f):
    return {"layout": "dumbbell", "metric": "raa", "series": [p["team1"], p["team2"]],
            "metric_label": f"Runs per 100 balls v the {p['comparison']} average; right is better",
            "rows": [{"label": f"{r['group']} · {PHASE[r['phase']].replace(' overs', '')}", "a": r["team1"], "b": r["team2"]}
                     for r in p["rows"]]}


def _ranks(p, f):
    return {"layout": "dumbbell", "metric": "rank", "series": [p["team1"], p["team2"]],
            "metric_label": f"Rank among {p['rows'][0]['of']} sides (1 is best)",
            "rows": [{"label": f"{r['group'].capitalize()} · {PHASE[r['phase']].replace(' overs', '')}",
                      "a": r["team1"], "b": r["team2"]} for r in p["rows"]]}


def _elo(p, f):
    return {"layout": "list", "rows": [
        {"label": s["team"], "sub": f"Elo {s['points'][-1]['elo']}",
         "details": [" → ".join(str(pt["elo"]) for pt in s["points"][-6:])]} for s in p["series"]]}


def _last_meeting(p, f):
    path = p.get("path") or []
    scores = [{"team": i["side"], "runs": i["runs"], "wickets": i["wickets"],
               "overs": f"{i['balls'] // 6}.{i['balls'] % 6}"} for i in p["innings"]]
    if len(path) < 2:
        return {"layout": "list", "rows": [{"label": s["team"], "sub": "", "details": [f"{s['runs']}/{s['wickets']} ({s['overs']})"]}
                                           for s in scores]}
    brk = next((i for i, q in enumerate(path) if q["innings"] == 2), None)
    return {"layout": "win_prob", "scores": scores, "teams": [{"name": p["team1"]}, {"name": p["team2"]}],
            "primer": {"win_probability": {"points": [q["wp"] for q in path], "team": p["team1"],
                                           "innings_break": brk, "wickets": []}}}


def _xis(p, f):
    return {"layout": "list", "rows": [{"label": s["team"], "sub": f"v {s['opponent']}", "details": s["players"]}
                                       for s in p["sides"]]}


def _battles(p, f):
    return {"layout": "diverging", "metric": "edge", "metric_label": "Likely edge, runs per 100 balls (right: batter)",
            "rows": [{"label": f"{r['batter']} v {r['bowler']}", "edge": r["edge"],
                      "display": f"{r['runs']} off {r['balls']}"} for r in p["rows"]]}


def _player_bars(p, f):
    unit = p.get("unit") or ""
    digits = p.get("decimals") or 0
    fmt = (lambda r: f"{_signed(r['value'], digits)}{unit}") if p.get("signed") else (lambda r: f"{r['value']:.{digits}f}{unit}")
    return _bars(p["rows"], "", fmt)


def _strips(p, f):
    return {"layout": "strips", "strips": [{"name": s["name"], "runs": [i["runs"] for i in s["innings"]]} for s in p["strips"]]}


def _suits(p, f):
    # One highlighted batter, the one the title names (the largest gap either way).
    top = max(p["rows"], key=lambda r: abs(r["here"] - r["elsewhere"]))
    return {"layout": "scatter", "x_metric": "raa", "y_metric": "raa", "x_label": "Elsewhere (runs above average per 100)",
            "y_label": f"At {p['ground']}", "unit": "batters",
            "points": [{"x": r["elsewhere"], "y": r["here"], "label": r["name"], "highlight": r is top}
                       for r in p["rows"]]}


def _milestones(p, f):
    return {"layout": "list", "rows": [{"label": r["player"], "sub": r["side"] or "", "details": [r["text"]]} for r in p["rows"]]}


def _pitch(p, f):
    return {"layout": "grid", "lines": p["lines"], "lengths": p["lengths"],
            "cells": [{"line": g["line"], "length": g["length"], "pct": g["pct"], "usual": g["usual_pct"]} for g in p["grid"]]}


def _captaincy(p, f):
    return {"layout": "list", "rows": [{"label": f"{x['role']}: {x['name']}", "sub": x["multiplier"], "details": [x["reason"]]}
                                       for x in p["picks"]]}


CONVERTERS: Dict[str, Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]] = {
    "tiles": _tiles, "par": _par, "stat": lambda p, f: {"layout": "stat", "value_display": str(p.get("value")),
                                                         "subject": p.get("caption") or "", "metric_label": ""},
    "chase_band": _chase, "phase_bars": _phase_bars, "benchmarks": _benchmarks, "totals_scatter": _totals_scatter,
    "worm": _worm, "phase_diverging": _phase_diverging, "pace_spin": _pace_spin, "boundary_zones": _zones,
    "dismissals": _dismissals, "recent_results": _recent, "h2h": _h2h, "form": _form, "dumbbell": _dumbbell,
    "rank_bars": _ranks, "elo_lines": _elo, "last_meeting": _last_meeting, "xis": _xis, "battles": _battles,
    "player_bars": _player_bars, "form_strips": _strips, "suits_scatter": _suits, "milestones": _milestones,
    "pitch_usage": _pitch, "captaincy": _captaincy,
}


def card_image_data(card: Dict[str, Any], fixture: Dict[str, Any], chapter_title: str = "",
                    url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """The snapshot data for one built card (its to_json()), or None if its visual has no image form."""
    convert = CONVERTERS.get(card.get("visual"))
    if not convert:
        return None
    data = convert(card["payload"], fixture)
    if data.get("layout") == "bars" and not data.get("metric_label"):
        data["metric_label"] = (card.get("help") or "").split(";")[0]
    venue = (fixture.get("venue") or "").split(",")[0]
    data.update({
        "title": card["title"],
        "kicker": " · ".join(x for x in (f"{fixture.get('team1')} v {fixture.get('team2')}", venue, chapter_title) if x),
        "source": card.get("sample") or "",
        "card_id": card["id"],
        "hindsight_url": url,
    })
    return data
