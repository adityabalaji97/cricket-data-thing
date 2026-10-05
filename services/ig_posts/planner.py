"""
Which angles answer a question: Jev scores them, code applies the rules ("code writes, Jev ranks", as in
services/fact_curation.py). Jev never sees or writes a number.

Rules, whatever Jev says:
  - T20 posts include a value angle (RAA or Impact) and WPA: the metrics that say what a performance was worth;
  - at most MAX_PER_FAMILY angles from one family, so five versions of "how fast" can't crowd out the rest;
  - an angle the field can't support (fewer than MIN_FIELD rows with it, e.g. thin control tags) is left out;
  - between MIN_ANGLES and MAX_ANGLES angles.
Without Jev (no key, or a failure) the role's DEFAULT order is used under the same rules, and the plan says so.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from services import jev_client
from services.ig_posts.angles import Angle
from services.ig_posts.context import QuestionContext, usable

MIN_ANGLES, MAX_ANGLES, MAX_PER_FAMILY, MIN_FIELD = 4, 6, 2, 8

CRITERIA = [
    "Irrelevant: says nothing about this question",
    "Background: loosely related, a fan would skip it",
    "Useful: a fair way to look at the question",
    "Important: an expert would want to see this",
    "Essential: you can't answer the question without it",
]

DEFAULT = {
    "batter": ["raa", "wpa", "sr", "bpd", "control", "boundary", "impact", "dot", "average", "sixes"],
    "bowler": ["raa", "wpa", "economy", "strike", "dot", "control", "wickets_inns"],
    "partnership": ["average", "sr", "control", "bpd", "boundary", "dot"],
}


def score(question: str, role: str, angles: List[Angle]) -> Optional[Dict[str, float]]:
    """Jev's 0..4 score per angle for this question, or None without Jev."""
    if not jev_client.enabled():
        return None
    answers = jev_client.ask(
        {"question": question, "subject_type": role, "audience": "cricket fans on Instagram, swiping a carousel",
         "angles": {a.id: a.description for a in angles}},
        {a.id: {"type": "score",
                "instructions": f"How much does the angle '{a.id}' ({a.description}) help a cricket fan judge this "
                                f"question: \"{question}\"?",
                "criteria": CRITERIA}
         for a in angles},
        timeout=8.0,
    )
    if not answers:
        return None
    out = {a.id: float((answers.get(a.id) or {}).get("score")) for a in angles
           if isinstance((answers.get(a.id) or {}).get("score"), (int, float))}
    return out or None


def plan(ctx: QuestionContext, question: str, angles: List[Angle]) -> Dict[str, Any]:
    """{'angles': [Angle...] best first, 'scores': {id: score}, 'by': 'jev'|'default'}."""
    supported = [a for a in angles if sum(1 for r in ctx.rows if usable(r, a)) >= MIN_FIELD]
    scores = score(question, ctx.role, supported)
    order = DEFAULT[ctx.role]
    if scores:
        ranked = sorted(supported, key=lambda a: (-scores.get(a.id, 0.0), order.index(a.id) if a.id in order else 99))
    else:
        ranked = sorted(supported, key=lambda a: order.index(a.id) if a.id in order else 99)
    chosen: List[Angle] = []
    families: Dict[str, int] = {}

    def take(a: Angle) -> None:
        if a not in chosen and families.get(a.family, 0) < MAX_PER_FAMILY and len(chosen) < MAX_ANGLES:
            chosen.append(a)
            families[a.family] = families.get(a.family, 0) + 1

    if ctx.fmt == "T20":  # the mandatory value angles first: the best-scored of RAA/Impact, then WPA
        value = [a for a in ranked if a.id in ("raa", "impact")]
        if value:
            take(value[0])
        wpa = next((a for a in ranked if a.id == "wpa"), None)
        if wpa:
            take(wpa)
    for a in ranked:
        if scores and scores.get(a.id, 0) < 1 and len(chosen) >= MIN_ANGLES:
            break  # Jev called it irrelevant and there are enough already
        take(a)
    # Present in Jev's order (the mandatory ones were only guaranteed a place).
    chosen.sort(key=lambda a: ranked.index(a))
    return {"angles": chosen, "scores": {k: round(v, 2) for k, v in (scores or {}).items()},
            "by": "jev" if scores else "default"}


def scatter_axes(chosen: List[Angle]) -> Optional[tuple]:
    """(x, y, z): the two best angles from different families, and the next as the dots' brightness."""
    if len(chosen) < 2:
        return None
    y = chosen[0]
    x = next((a for a in chosen[1:] if a.family != y.family), chosen[1])
    z = next((a for a in chosen if a not in (x, y)), None)
    return x, y, z
