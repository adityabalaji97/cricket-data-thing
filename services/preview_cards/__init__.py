"""
Story-style match preview cards (MATCH_PREVIEW_VIZ_PLAN.md).

build_story(ctx) runs every registered CardSpec, drops cards with no data or below their sample
floor, adds the "At a glance" summary built from those cards, ranks the cards inside each chapter
(chapters keep a fixed order), and returns the JSON manifest the frontend renders. A card that fails to build is logged and left out; it never takes
the story down.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

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
        "fixture": {"venue": ctx.venue, "team1": ctx.t1, "team2": ctx.t2, "format": ctx.fmt, "gender": ctx.gender,
                    # Everything needed to rebuild this story: a card's graphic (snapshot kind
                    # preview_card) is made server-side from these, never from client data.
                    "params": context_params(ctx)},
        "chapters": chapters,
    }


PARAM_KEYS = ("venue", "team1", "team2", "team1_short", "team2_short", "format", "start_date", "end_date",
              "include_international", "top_teams", "day_or_night")


def context_params(ctx: PreviewContext) -> Dict[str, Any]:
    return {"venue": ctx.venue, "team1": ctx.team1, "team2": ctx.team2, "team1_short": ctx.team1_short,
            "team2_short": ctx.team2_short, "format": ctx.fmt,
            "start_date": ctx.start.isoformat() if ctx.start else None,
            "end_date": ctx.end.isoformat() if ctx.end else None,
            "include_international": ctx.include_international, "top_teams": ctx.top_teams,
            "day_or_night": ctx.day_or_night}


def context_from_params(db, params: Dict[str, Any]) -> PreviewContext:
    """The PreviewContext a story was built with, from context_params (validated here)."""
    def day(v):
        return date.fromisoformat(v) if v else None
    fmt = params.get("format") or "T20"
    if fmt not in ("T20", "ODI"):
        raise ValueError("format must be T20 or ODI")
    if not params.get("venue") or not params.get("team1") or not params.get("team2"):
        raise ValueError("venue, team1 and team2 are required")
    if params.get("day_or_night") not in (None, "day", "night"):
        raise ValueError("day_or_night must be day or night")
    return PreviewContext(
        db=db, venue=str(params["venue"]), team1=str(params["team1"]), team2=str(params["team2"]), fmt=fmt,
        gender="male", start=day(params.get("start_date")), end=day(params.get("end_date")),
        include_international=bool(params.get("include_international", True)),
        top_teams=max(1, min(50, int(params.get("top_teams") or 20))), day_or_night=params.get("day_or_night"),
        team1_short=params.get("team1_short"), team2_short=params.get("team2_short"),
    )


def build_card(ctx: PreviewContext, card_id: str) -> Optional[Tuple[Dict[str, Any], str]]:
    """One card (its JSON) and its chapter title, building only what it needs."""
    titles = dict(CHAPTERS)
    if card_id == "glance":  # the summary is made from every other card
        story = build_story(ctx)
        for chapter in story["chapters"]:
            for card in chapter["cards"]:
                if card["id"] == card_id:
                    return card, chapter["title"]
        return None
    spec = next((s for s in REGISTRY if s.id == card_id), None)
    if spec is None:
        return None
    card = spec.make(ctx)
    return (card.to_json(), titles[card.chapter]) if card else None


__all__ = ["PreviewContext", "build_story", "build_card", "context_from_params", "context_params", "REGISTRY"]
