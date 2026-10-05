"""
The closing card (MATCH_PREVIEW_VIZ_PLAN.md, E2): "Ask your own question", up to four one-tap
query-builder links, each the question a card answered and the query behind it. Built after every
other card, from their own query links, so each link reproduces a card the reader has just seen.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from services.preview_cards.spec import Card, Info

MAX_LINKS = 4


def closing_card(cards: List[Card], questions: Dict[str, str]) -> Optional[Card]:
    links, chapters_used = [], set()
    # One link per chapter first, best card first, then fill up.
    ranked = sorted((c for c in cards if c.query_url and c.id in questions), key=lambda c: -c.relevance)
    for pass_ in (0, 1):
        for c in ranked:
            if len(links) >= MAX_LINKS:
                break
            if any(l["card"] == c.id for l in links) or (pass_ == 0 and c.chapter in chapters_used):
                continue
            links.append({"card": c.id, "label": questions[c.id], "url": c.query_url})
            chapters_used.add(c.chapter)
    if len(links) < 2:
        return None
    return Card(
        id="ask", chapter="more", visual="links",
        title="Ask your own question", help="Each opens the data behind a card, ready to change",
        sample="Hindsight query builder · ball-by-ball data", n=len(links),
        payload={"links": links},
        info=Info(what="Every card is a query-builder query. These open the ones behind this story's standout "
                       "cards, so you can change the filters and ask the next question yourself."),
        relevance=0.1,
    )
