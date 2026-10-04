"""
The card contract for the story-style match preview (MATCH_PREVIEW_VIZ_PLAN.md, section 3).

A CardSpec declares one pre-match question: which chapter it belongs to, which formats it
supports, how to build it from the preview context, and its sample rule. Building returns a Card
(or None when the data is missing or below the sample floor, so the story leaves it out rather
than showing an empty card).

What reaches the screen is deliberately small: a title that states the finding in plain words, at
most one help line ("Higher is better"), the sample/context line, and the payload the visual
draws. Everything else goes in `info`, which the card's info sheet shows.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

CHAPTERS: Tuple[Tuple[str, str], ...] = (
    ("glance", "At a glance"),
    ("ground", "The ground"),
    ("teams", "The teams"),
    ("players", "The players"),
    ("fantasy", "Fantasy"),
)

SMALL_SAMPLE = 15  # flagged on the card under this many matches / innings


@dataclass(frozen=True)
class SampleRule:
    flag_below: int = SMALL_SAMPLE  # "small sample" on the card
    hide_below: int = 1             # left out of the story below this


@dataclass
class Info:
    """The info sheet: what the chart shows, how to read it, definitions, method."""
    what: str
    how_to_read: Optional[str] = None
    definitions: List[Tuple[str, str]] = field(default_factory=list)
    method: Optional[str] = None


@dataclass
class Card:
    id: str
    chapter: str
    visual: str                 # the frontend renderer (src/components/story/visuals)
    title: str                  # the takeaway, in plain words
    sample: str                 # "21 matches at Wankhede Stadium · 2022–26"
    payload: Dict[str, Any]
    n: int                      # the sample size the rule is applied to
    info: Info
    help: Optional[str] = None  # "Higher is better", only when direction isn't obvious
    small_sample: bool = False
    query_url: Optional[str] = None
    relevance: float = 1.0      # order inside the chapter (higher first)

    def to_json(self) -> Dict[str, Any]:
        out = asdict(self)
        out["info"]["definitions"] = [{"term": t, "meaning": m} for t, m in self.info.definitions]
        return out


@dataclass(frozen=True)
class CardSpec:
    id: str
    chapter: str
    question: str
    build: Callable[[Any], Optional[Card]]
    formats: Tuple[str, ...] = ("T20", "ODI")
    sample: SampleRule = SampleRule()
    weight: float = 1.0  # default importance inside the chapter

    def make(self, ctx: Any) -> Optional[Card]:
        if ctx.fmt not in self.formats:
            return None
        card = self.build(ctx)
        if card is None or card.n < self.sample.hide_below:
            return None
        card.small_sample = card.small_sample or card.n < self.sample.flag_below
        # Thin samples sink within the chapter; distinctiveness is set by the builder.
        card.relevance = round(self.weight * card.relevance * min(1.0, 0.4 + card.n / 50.0), 4)
        return card
