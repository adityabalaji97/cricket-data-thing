"""
Story-style match preview cards (MATCH_PREVIEW_VIZ_PLAN.md).

build_story(ctx) runs every registered CardSpec, drops cards with no data or below their sample
floor, adds the "At a glance" summary built from those cards, ranks the cards inside each chapter
(chapters keep a fixed order), and returns the JSON manifest the frontend renders. A card that fails to build is logged and left out; it never takes
the story down.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from services.preview_cards.context import PreviewContext
from services.preview_cards.existing import EXISTING
from services.preview_cards.fantasy import FANTASY
from services.preview_cards.glance import at_a_glance
from services.preview_cards.ground import GROUND
from services.preview_cards.spec import CHAPTERS, Card, CardSpec
from services.preview_cards.players import PLAYERS
from services.preview_cards.teams import TEAMS

logger = logging.getLogger(__name__)

REGISTRY: List[CardSpec] = [*EXISTING, *GROUND, *TEAMS, *PLAYERS, *FANTASY]


def build_story(ctx: PreviewContext, registry: List[CardSpec] = None) -> Dict[str, Any]:
    cards: List[Card] = []
    for spec in registry or REGISTRY:
        try:
            card = spec.make(ctx)
        except Exception as exc:  # pragma: no cover - one card never breaks the story
            logger.warning("preview card %s failed: %r", spec.id, exc)
            continue
        if card is not None:
            cards.append(card)
    try:
        glance = at_a_glance(ctx, cards)
    except Exception as exc:  # pragma: no cover
        logger.warning("preview card glance failed: %r", exc)
        glance = None
    if glance is not None:
        cards.append(glance)
    chapters = []
    for chapter_id, title in CHAPTERS:
        chapter_cards = sorted((c for c in cards if c.chapter == chapter_id), key=lambda c: -c.relevance)
        if chapter_cards:
            chapters.append({"id": chapter_id, "title": title, "cards": [c.to_json() for c in chapter_cards]})
    return {
        "fixture": {"venue": ctx.venue, "team1": ctx.t1, "team2": ctx.t2, "format": ctx.fmt, "gender": ctx.gender},
        "chapters": chapters,
    }


__all__ = ["PreviewContext", "build_story", "REGISTRY"]
