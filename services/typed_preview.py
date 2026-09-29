"""
Typed match-preview narrative: code writes every sentence, Jev only chooses which to show.

build_candidate_facts() turns a preview context (services.match_preview.gather_preview_context)
into short, single-claim sentences whose numbers are all formatted here, so a shown stat can
never be invented. curate() asks Jev to score how much each fact matters for this match and
keeps the best per section, plus one headline for cards and share images. Without Jev (no key,
or a failed call) curate() returns None and the caller keeps its deterministic sections.
"""
from typing import Any, Dict, List, Optional, Tuple

from services import jev_client
from services.match_preview import (
    _best_bowling_threat,
    _best_edge,
    _classify_toss_bias,
    _phase_label,
    _phase_runs,
    _top_fantasy_pick,
    score_preview_lean,
)

SECTIONS: List[Tuple[str, str]] = [
    ("venue_profile", "Venue Profile"),
    ("form_guide", "Form Guide"),
    ("head_to_head", "Head-to-Head"),
    ("key_matchup_factor", "Key Matchup Factor"),
    ("preview_take", "Preview Take"),
]
MAX_PER_SECTION = 2
# Score levels (0..4); a fact below "relevant" is dropped unless its section would be empty.
RELEVANCE_CRITERIA = [
    "Trivia: true, but tells a fan nothing about how this match might go",
    "Background: general context about the teams or ground, with a thin link to this match",
    "Relevant: a clear signal about this match, such as a scoring pattern at this ground or a team's recent results",
    "Important: a strong, specific signal a pundit would lead with, such as a lopsided record or a standout player matchup",
    "Likely decisive: the single factor most likely to swing this match",
]
KEEP_THRESHOLD = 2.0
MIN_VENUE_MATCHES = 5


def _fact(facts: List[Dict[str, Any]], section: str, kind: str, text: str, fixed: bool = False) -> None:
    facts.append({"id": f"f{len(facts)}", "section": section, "kind": kind, "text": text, "fixed": fixed})


def _possessive(name: str) -> str:
    return f"{name}'" if name.endswith("s") else f"{name}'s"


def _plural(n: int, word: str) -> str:
    suffix = "es" if word.endswith(("ch", "s")) else "s"
    return f"{n} {word}{'' if n == 1 else suffix}"


def build_candidate_facts(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    team1, team2 = context.get("team1"), context.get("team2")
    venue = context.get("venue") or "this ground"
    story = context.get("screen_story") or {}
    history = context.get("match_history") or {}
    innings = story.get("innings_scores_analysis") or {}
    phase = story.get("phase_wise_strategy") or {}
    recent_venue = story.get("recent_matches_at_venue") or {}
    toss = (story.get("match_results_distribution") or {}).get("venue_toss_signal") or {}
    facts: List[Dict[str, Any]] = []

    # --- Venue Profile ---
    total = int(toss.get("total_matches") or 0)
    bf, ch = int(toss.get("batting_first_wins") or 0), int(toss.get("chasing_wins") or 0)
    if total >= MIN_VENUE_MATCHES:
        bias = _classify_toss_bias(bf, total).get("label")
        if bias == "chasing_edge":
            _fact(facts, "venue_profile", "venue_split", f"Chasing sides have won {ch} of {total} matches at {venue}.")
        elif bias == "bat_first_edge":
            _fact(facts, "venue_profile", "venue_split", f"Sides batting first have won {bf} of {total} matches at {venue}.")
        else:
            _fact(facts, "venue_profile", "venue_split", f"{venue} is evenly split: {bf} wins batting first, {ch} chasing, in {total} matches.")
    rv_n = int(recent_venue.get("sample_size") or 0)
    if rv_n >= 4:
        rv_bf, rv_ch = int(recent_venue.get("batting_first_wins") or 0), int(recent_venue.get("chasing_wins") or 0)
        _fact(facts, "venue_profile", "recent_venue", f"The last {rv_n} matches here went {rv_bf} bat-first wins to {rv_ch} chases.")
    # Scoring benchmarks mean nothing from a couple of matches (Barsapara ODIs gave "highest
    # chased 322, lowest defended 373"), so they need the same sample as the split above.
    venue_sample = total >= MIN_VENUE_MATCHES
    avg_win, avg_chase = innings.get("avg_winning_score_rounded"), innings.get("avg_chasing_score_rounded")
    if not venue_sample:
        avg_win = avg_chase = None
        _fact(facts, "venue_profile", "thin_venue",
              f"Only {_plural(total, 'match')} at {venue} in this window, too few for a reliable venue pattern.", fixed=True)
    if avg_win:
        _fact(facts, "venue_profile", "par", f"Winning first-innings totals here average {avg_win}.")
    if avg_chase:
        _fact(facts, "venue_profile", "chase_par", f"Chasing totals here average {avg_chase}.")
    hi_chased, lo_defended = innings.get("highest_total_chased"), innings.get("lowest_total_defended")
    if venue_sample and hi_chased and lo_defended:
        _fact(facts, "venue_profile", "extremes", f"The highest total chased here is {hi_chased}; the lowest defended is {lo_defended}.")
    dominant = phase.get("dominant_phase")
    runs = _phase_runs(phase.get("batting_first_wins_template") or {}, dominant or "powerplay")
    if venue_sample and dominant and runs:
        _fact(facts, "venue_profile", "phase", f"Winning sides here are built in the {_phase_label(dominant)}, averaging {runs} runs in that phase.")

    # --- Form Guide ---
    for team, key in ((team1, "team1_recent"), (team2, "team2_recent")):
        recent = history.get(key) or {}
        n = int(recent.get("sample_size") or 0)
        if not n:
            continue
        wins = int(recent.get("wins_batting_first") or 0) + int(recent.get("wins_chasing") or 0)
        _fact(facts, "form_guide", "record", f"{team} have won {wins} of their last {n} matches.")
        bf_scores = recent.get("batting_first_scores") or []
        if bf_scores and avg_win:
            reached = int(recent.get("reached_avg_winning_score_batting_first") or 0)
            _fact(facts, "form_guide", "bf_par", f"Batting first, {team} reached this ground's average winning total in {reached} of their last {len(bf_scores)} innings.")
        chases = recent.get("chasing_scores") or []
        if chases:
            won = sum(1 for c in chases if c.get("won"))
            _fact(facts, "form_guide", "chasing", f"{team} won {won} of their last {_plural(len(chases), 'chase')}.")
        restriction = recent.get("avg_restriction_when_bowling_first")
        if restriction:
            _fact(facts, "form_guide", "restriction", f"Bowling first, {team} have conceded {int(restriction)} on average recently.")

    # --- Head-to-Head ---
    h2h = story.get("head_to_head_stats") or {}
    overall = h2h.get("overall_window_summary") or {}
    n = int(overall.get("sample_size") or 0)
    if n:
        w1, w2 = int(overall.get("team1_wins") or 0), int(overall.get("team2_wins") or 0)
        if w1 == w2:
            _fact(facts, "head_to_head", "h2h", f"{team1} and {team2} are level at {w1}-{w2} in their last {n} meetings.")
        else:
            lead, trail = (team1, team2) if w1 > w2 else (team2, team1)
            _fact(facts, "head_to_head", "h2h", f"{lead} lead {trail} {max(w1, w2)}-{min(w1, w2)} in their last {n} meetings.")
        meetings = h2h.get("recent_matches") or []
        if meetings:
            last = meetings[0]
            winner = last.get("winner")
            if winner:
                _fact(facts, "head_to_head", "last_meeting", f"{winner} won the last meeting, on {last.get('date')} at {last.get('venue')}.")
            top3 = [m.get("winner") for m in meetings[:3]]
            if len(top3) == 3 and top3[0] and top3.count(top3[0]) == 3:
                _fact(facts, "head_to_head", "streak", f"{top3[0]} have won the last three meetings.")
        same_venue = int((h2h.get("relevance") or {}).get("same_venue_matches") or 0)
        if same_venue:
            _fact(facts, "head_to_head", "same_venue", f"They have met {_plural(same_venue, 'time')} at this ground in the window.")

    # --- Key Matchup Factor ---
    for team, other in ((team1, team2), (team2, team1)):
        edge = _best_edge(story, team)
        if edge and edge.get("balls"):
            _fact(facts, "key_matchup_factor", "edge",
                  f"{edge['batter']} has scored {edge.get('runs')} off {edge['balls']} balls against {edge['bowler']} "
                  f"(strike rate {round(float(edge.get('strike_rate') or 0))}).")
        threat = _best_bowling_threat(story, team)
        if threat and threat.get("balls"):
            _fact(facts, "key_matchup_factor", "threat",
                  f"{threat['bowler']} has {_plural(int(threat.get('wickets') or 0), 'wicket')} in {threat['balls']} balls "
                  f"against {_possessive(other)} likely batters, at {threat.get('economy')} an over.")
        pick = _top_fantasy_pick(story, team)
        if pick:
            _fact(facts, "key_matchup_factor", "fantasy",
                  f"{pick['player']} is {_possessive(team)} top projected fantasy pick ({round(float(pick.get('expected_points') or 0))} points).")

    # --- Preview Take (always shown: it is our model's lean, not a curated fact) ---
    lean = score_preview_lean(context)
    reasons = ", ".join(r.get("detail", "") for r in lean.get("top_reasons", []) if r.get("detail"))
    _fact(facts, "preview_take", "lean", f"{lean.get('label', 'Too close to call')}" + (f": {reasons}." if reasons else "."), fixed=True)
    elo = context.get("elo") or {}
    e1, e2 = elo.get(team1), elo.get(team2)
    if e1 and e2 and abs(e1 - e2) >= 25:
        higher = team1 if e1 > e2 else team2
        _fact(facts, "preview_take", "elo", f"{higher} are rated {abs(e1 - e2)} Elo points higher.")
    return facts


def _state(context: Dict[str, Any], facts: List[Dict[str, Any]]) -> Dict[str, Any]:
    filters = context.get("filters") or {}
    return {
        "match": f"{context.get('team1')} vs {context.get('team2')} at {context.get('venue')}",
        "format": context.get("format") or filters.get("format") or "T20",
        "task": "Each candidate is a verified fact for a pre-match preview. Judge how much it matters for this match.",
        "candidates": {f["id"]: f["text"] for f in facts},
    }


def curate(context: Dict[str, Any], facts: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    """Sections chosen by Jev, plus a headline; None when Jev is unavailable."""
    if not jev_client.enabled():
        return None
    facts = facts if facts is not None else build_candidate_facts(context)
    scored = [f for f in facts if not f["fixed"]]
    if not scored:
        return None
    questions = {
        f["id"]: {
            "type": "score",
            "instructions": f"How much does candidate {f['id']} (\"{f['text']}\") matter for the outcome of this match?",
            "criteria": RELEVANCE_CRITERIA,
        }
        for f in scored
    }
    answers = jev_client.ask(_state(context, scored), questions)
    if not answers:
        return None
    for f in scored:
        score = (answers.get(f["id"]) or {}).get("score")
        f["score"] = float(score) if isinstance(score, (int, float)) else None
    if all(f["score"] is None for f in scored):
        return None
    return assemble(facts)


def assemble(facts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pure selection from scored facts: top per section, one sentence per kind, a headline."""
    sections = []
    for section_id, title in SECTIONS:
        fixed = [f for f in facts if f["section"] == section_id and f["fixed"]]
        pool = sorted(
            (f for f in facts if f["section"] == section_id and not f["fixed"] and f.get("score") is not None),
            key=lambda f: f["score"], reverse=True,
        )
        chosen, kinds = [], set()
        for f in pool:
            if len(chosen) >= MAX_PER_SECTION or (chosen and f["score"] < KEEP_THRESHOLD):
                break
            if f["kind"] in kinds and f["kind"] not in ("record", "edge", "threat", "fantasy", "chasing", "bf_par", "restriction"):
                continue
            chosen.append(f)
            kinds.add(f["kind"])
        bullets = [f["text"] for f in fixed + chosen]
        if bullets:
            sections.append({"id": section_id, "title": title, "bullets": bullets, "evidence_tags": ["typed_preview"]})
    ranked = sorted((f for f in facts if not f["fixed"] and f.get("score") is not None), key=lambda f: f["score"], reverse=True)
    return {
        "sections": sections,
        "headline": ranked[0]["text"] if ranked else None,
        "scores": {f["id"]: {"text": f["text"], "score": round(f["score"], 2)} for f in ranked},
    }
