"""
Shared "code writes, Jev ranks" helper: score code-written facts with one fan-out Jev call.

Every fact is a dict with at least {"id", "text"}; score_facts() adds a 0..(levels-1) "score"
to each. Nothing here writes a number: callers format all numbers themselves, so a shown
sentence can never contain an invented stat. Returns False when Jev is off or fails, and the
caller falls back to its deterministic order.
"""
from typing import Any, Dict, List, Sequence

from services import jev_client


def score_facts(facts: List[Dict[str, Any]], state: Dict[str, Any], question: str, criteria: Sequence[str]) -> bool:
    if not facts or not jev_client.enabled():
        return False
    questions = {
        f["id"]: {
            "type": "score",
            "instructions": f"{question} Candidate {f['id']}: \"{f['text']}\"",
            "criteria": list(criteria),
        }
        for f in facts
    }
    answers = jev_client.ask({**state, "candidates": {f["id"]: f["text"] for f in facts}}, questions)
    if not answers:
        return False
    scored = False
    for f in facts:
        value = (answers.get(f["id"]) or {}).get("score")
        f["score"] = float(value) if isinstance(value, (int, float)) else None
        scored = scored or f["score"] is not None
    return scored


def top(facts: List[Dict[str, Any]], n: int, threshold: float = 0.0, minimum: int = 3) -> List[Dict[str, Any]]:
    """Best n by score (unscored last): always the best `minimum`, then only those at/above threshold."""
    ranked = sorted(facts, key=lambda f: (f.get("score") is not None, f.get("score") or 0), reverse=True)
    chosen = ranked[:minimum]
    for f in ranked[minimum:]:
        if len(chosen) >= n or (f.get("score") or 0) < threshold:
            break
        chosen.append(f)
    return chosen
