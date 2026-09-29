"""
Match recap: a headline and three bullets for a finished men's T20, from the scorecard's
T20 Primer metrics (Impact, WPA, win-probability path, par).

Code writes every sentence from the scorecard payload (services.match_scorecard); Jev ranks how
much each explains how the match was won. Without Jev the order is by size of the effect.
Finished matches don't change, so recaps are cached per match.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from services import jev_client
from services.fact_curation import score_facts, top

RECAP_CRITERIA = [
    "Irrelevant: true, but says nothing about how this match was won or lost",
    "Minor: a small contribution that did not change the course of the match",
    "Notable: a clear contribution a match report would mention",
    "Major: one of the two or three biggest reasons for the result",
    "Decisive: the single moment or performance that most decided the result",
]
BIG_PICTURE_KINDS = {"par", "phase_swing", "comeback"}
_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_MAX = 500


def _pct(x: float) -> str:
    return f"{round(abs(x) * 100)}%"


def _poss(name: str) -> str:
    return f"{name}'" if name.endswith("s") else f"{name}'s"


def _overs(overs: Any) -> str:
    text_ = str(overs or "").removesuffix(".0")
    return f"{text_} over{'' if text_ == '1' else 's'}"


def _signed_pct(x: float) -> str:
    return f"{'+' if x >= 0 else '-'}{round(abs(x) * 100)}%"


def _fact(facts: List[Dict[str, Any]], kind: str, text_: str, weight: float) -> None:
    # `weight` orders the no-Jev fallback: the size of the effect in runs (or WPA x 100).
    facts.append({"id": f"r{len(facts)}", "kind": kind, "text": text_, "weight": abs(weight)})


def _turning_point(db: Session, match_id: str) -> Optional[Dict[str, Any]]:
    return db.execute(text("""
        SELECT dd.inns, dd.over, dd.ball, dd.bat, dd.bowl, dd.team_bat, dd.team_bowl,
               COALESCE(dd.batruns, 0) AS runs, COALESCE(dd.out, '') AS out, dd.dismissal,
               bm.wpa, bm.wp_before, bm.wp_after
        FROM delivery_details dd
        JOIN ball_metrics bm ON bm.delivery_id = dd.id
        WHERE dd.p_match = :match_id AND bm.wpa IS NOT NULL
        ORDER BY ABS(bm.wpa) DESC, dd.id
        LIMIT 1
    """), {"match_id": match_id}).mappings().first()


def _par(db: Session, match_id: str) -> Optional[float]:
    row = db.execute(text("SELECT par FROM match_par WHERE p_match = :m LIMIT 1"), {"m": match_id}).first()
    return float(row[0]) if row and row[0] is not None else None


def build_recap_facts(scorecard: Dict[str, Any], db: Session) -> List[Dict[str, Any]]:
    match = scorecard.get("match") or {}
    summary = scorecard.get("summary") or {}
    primer = summary.get("primer") or {}
    match_id = str(match.get("id"))
    winner = match.get("winner")
    facts: List[Dict[str, Any]] = []

    batting, bowling = [], []
    for inn in scorecard.get("innings") or []:
        batting += [r for r in inn.get("batting") or [] if r.get("impact") is not None]
        bowling += [r for r in inn.get("bowling") or [] if r.get("impact") is not None]
    for r in sorted(batting, key=lambda r: r["impact"], reverse=True)[:3]:
        if r["impact"] >= 5:
            _fact(facts, "bat", f"{_poss(r['name'])} {r['runs']}{'*' if r.get('not_out') else ''} off {r['balls']} added "
                  f"{r['impact']:.1f} runs to {_poss(r['team'])} expected total (Impact; win probability {_signed_pct(r.get('wpa') or 0)}).",
                  r["impact"])
    for r in sorted(batting, key=lambda r: r["impact"])[:1]:
        if r["impact"] <= -10:
            _fact(facts, "bat_cost", f"{_poss(r['name'])} {r['runs']} off {r['balls']} cost {r['team']} {abs(r['impact']):.1f} runs against expected (Impact).",
                  r["impact"])
    for r in sorted(bowling, key=lambda r: r["impact"], reverse=True)[:2]:
        if r["impact"] >= 5:
            _fact(facts, "bowl", f"{_poss(r['name'])} {r.get('wickets', 0)}/{r.get('runs')} in {_overs(r.get('overs'))} saved "
                  f"{r['impact']:.1f} runs (Impact) for {r['team']}.", r["impact"])

    scores = summary.get("innings_scores") or []
    par = _par(db, match_id)
    if par and scores:
        first = scores[0]
        diff = first["runs"] - par
        side = "above" if diff >= 0 else "below"
        # Only a real gap is big-picture; "3 above par" is a detail.
        _fact(facts, "par" if abs(diff) >= 10 else "par_close", f"{_poss(first['batting_team'])} {first['runs']}/{first['wickets']} was {abs(diff):.0f} {side} par ({par:.0f}).", diff)

    tp = _turning_point(db, match_id)
    if tp and abs(float(tp["wpa"])) >= 0.08:
        wpa = float(tp["wpa"])
        event = (f"{tp['bowl']} dismissed {tp['bat']}" if str(tp["out"]).lower() == "true"
                 else f"{tp['bat']} hit {tp['bowl']} for {tp['runs']}" if tp["runs"] >= 4
                 else f"{tp['bat']} faced {tp['bowl']}")
        gainer = tp["team_bat"] if wpa > 0 else tp["team_bowl"]
        _fact(facts, "turning_point", f"The biggest swing came in over {int(tp['over']) + 1} of innings {tp['inns']}: {event}, "
              f"swinging win probability {round(abs(wpa) * 100)} points to {gainer}.", wpa * 100)

    wp = primer.get("win_probability") or {}
    points, first_team = wp.get("points") or [], wp.get("team")
    if winner and points and first_team:
        winner_path = points if winner == first_team else [1 - p for p in points]
        low = min(winner_path)
        if low <= 0.3:
            _fact(facts, "comeback", f"{winner} won from as low as {_pct(low)} win probability.", (0.5 - low) * 100)

    # Which phase decided it: the biggest gap in batting Impact between the two innings.
    innings_primer = primer.get("innings") or []
    if len(innings_primer) == 2:
        phases = (("powerplay", 1, 6), ("middle overs", 7, 15), ("death overs", 16, 20))
        gaps = []
        for label, lo, hi in phases:
            vals = [sum(o["impact"] for o in inn.get("by_over") or [] if lo <= o["over"] <= hi) for inn in innings_primer]
            gaps.append((vals[0] - vals[1], label, vals))
        gap, label, vals = max(gaps, key=lambda g: abs(g[0]))
        if abs(gap) >= 10:
            better, worse = (innings_primer[0], innings_primer[1]) if gap > 0 else (innings_primer[1], innings_primer[0])
            b_val, w_val = (vals[0], vals[1]) if gap > 0 else (vals[1], vals[0])
            _fact(facts, "phase_swing", f"The {label} decided it: {better['team']} batted {abs(gap):.0f} runs better than "
                  f"{worse['team']} there by Impact ({b_val:+.0f} v {w_val:+.0f}).", gap)

    result = match.get("result_text")
    if result:
        facts.append({"id": "result", "kind": "result", "text": result + (f" ({match['chase_note']})" if match.get("chase_note") else "") + ".",
                      "weight": 0, "fixed": True})
    return facts


def build_recap(scorecard: Dict[str, Any], db: Session) -> Dict[str, Any]:
    match = scorecard.get("match") or {}
    match_id = str(match.get("id"))
    if match_id in _CACHE:
        return _CACHE[match_id]
    facts = build_recap_facts(scorecard, db)
    fixed = [f for f in facts if f.get("fixed")]
    ranked = [f for f in facts if not f.get("fixed")]
    if not ranked:
        return {"available": False}
    state = {
        "match": f"{match.get('team1')} vs {match.get('team2')}, {match.get('competition')} {str(match.get('date'))[:4]}",
        "result": match.get("result_text"),
        "task": "Each candidate is a verified fact about a finished T20. Judge how much it explains the result.",
    }
    jev = score_facts(ranked, state, "How much does this fact explain how the match was won?", RECAP_CRITERIA)
    if not jev:
        for f in ranked:
            f["score"] = f["weight"]
    # Big-picture facts (par, the deciding phase, a comeback) lead; Jev orders within each group.
    big = sorted((f for f in ranked if f["kind"] in BIG_PICTURE_KINDS), key=lambda f: f["score"] or 0, reverse=True)
    detail = [f for f in ranked if f["kind"] not in BIG_PICTURE_KINDS]
    chosen = big[:2] + top(detail, max(2, 4 - len(big[:2])), threshold=2.0 if jev else 0.0, minimum=2)
    chosen = chosen[:4]
    recap = {
        "available": True,
        "source": "typed" if jev else "deterministic",
        "headline": chosen[0]["text"],
        "bullets": [f["text"] for f in chosen[1:]] + [f["text"] for f in fixed],
    }
    if not jev and jev_client.enabled():
        return recap  # Jev hiccup: serve the fallback but try Jev again next time
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[match_id] = recap
    return recap
