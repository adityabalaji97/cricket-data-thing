"""
Search routing: when a search is not an exact name match, decide in one fast Jev call whether
it is really a lookup of one player/team/venue (and which suggestion) or a stats question for
the natural-language query builder. Only a confident lookup is routed; everything else, and any
Jev failure, falls through to the query builder as before.
"""
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from services import jev_client
from services.search import search_entities

MIN_INTENT = 0.7
MIN_ENTITY = 0.6


def route_search(query: str, db: Session) -> Dict[str, Any]:
    q = (query or "").strip()
    if len(q) < 2 or not jev_client.enabled():
        return {"route": "query"}
    suggestions: List[Dict[str, Any]] = search_entities(q, db, limit=8)
    if not suggestions:
        return {"route": "query"}
    options = {f"c{i}": f"{s.get('display_name') or s.get('name')} ({s.get('type')})" for i, s in enumerate(suggestions)}
    answers = jev_client.ask(
        {"search": q, "site": "a cricket stats site with player, team and venue pages and a stats query builder"},
        {
            "intent": {
                "type": "choice",
                "instructions": "What does this search want?",
                "criteria": {
                    "lookup": "The page for one specific player, team or venue, e.g. 'kohli', 'abhishek sharma batting', 'wankhede', 'mumbai indians'",
                    "question": "A stats question, ranking, comparison or filtered query, e.g. 'best death bowlers 2025', 'kohli vs spin', 'kohli vs bumrah', 'highest totals at eden'",
                },
            },
            "entity": {
                "type": "choice",
                "instructions": "Which of these is the player, team or venue the search refers to?",
                "criteria": options,
            },
        },
        timeout=2.5,
    ) or {}
    intent, entity = answers.get("intent") or {}, answers.get("entity") or {}
    lookup_p = (intent.get("probabilities") or {}).get("lookup") or 0
    choice = entity.get("choice")
    entity_p = (entity.get("probabilities") or {}).get(choice) or 0
    if lookup_p >= MIN_INTENT and choice in options and entity_p >= MIN_ENTITY:
        return {"route": "entity", "item": suggestions[int(choice[1:])], "confidence": round(min(lookup_p, entity_p), 2)}
    return {"route": "query", "confidence": round(1 - lookup_p, 2)}
