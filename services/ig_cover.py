"""
The carousel cover's hero: the lead chart's top rows drawn on the hook slide, so the cover shows a number worth
stopping for, not just words (the feed shows only slide 1; strangers decide there). A two-week A/B from 19 Oct 2026:
half the carousels get the hero, half keep the text cover, picked by the post's title so a rebuild keeps its side.
The variant is stored on the hook slide ("cover") and on the pack (facts.cover) to compare against Instagram's numbers.

    COVER_HERO=ab (default) | on | off
"""
from __future__ import annotations

import hashlib
import os
from copy import deepcopy
from typing import Any, Dict, List, Optional

ROWS = 4


def variant(title: str) -> str:
    mode = os.getenv("COVER_HERO", "ab").lower()
    if mode == "on":
        return "hero"
    if mode == "off":
        return "text"
    return "hero" if int(hashlib.sha1(title.encode()).hexdigest(), 16) % 2 == 0 else "text"



def hero_from(card: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The top rows of a bar chart (metric_bars), the highlighted row kept: {rows: [{name, value, highlight}], format,
    label}; or a stacked-share chart (share_bars) whole: {kind: "share", groups, rows}. Other visuals don't shrink to
    a cover well, so they give none."""
    p = card.get("payload") or {}
    if card.get("visual") == "share_bars":  # stacked shares: every row (a handful), drawn as on the card
        rows = p.get("rows") or []
        if not 2 <= len(rows) <= 5:
            return None
        return {"kind": "share", "groups": p.get("groups") or [], "label": "",
                "rows": [{"name": r.get("name"), "segments": r.get("segments") or []} for r in rows]}
    if card.get("visual") != "metric_bars":
        return None
    rows = [r for r in p.get("rows") or [] if isinstance(r.get("value"), (int, float))]
    if len(rows) < 2:
        return None
    top = rows[:ROWS]
    mine = next((r for r in rows if r.get("highlight")), None)
    if mine and mine not in top:
        top = top[: ROWS - 1] + [mine]
    metric = p.get("metric") or {}
    return {"rows": [{"name": r.get("name"), "value": r["value"], "highlight": bool(r.get("highlight"))} for r in top],
            "format": metric.get("format", "dec1"), "label": metric.get("label", "")}


def without_hero_card(slides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The slides without any deck card that repeats the cover's hero chart: the cover already shows it, and slide 2
    (the one Instagram re-shows to people who scrolled past) must be new."""
    hero = (slides[0].get("hero") or {}).get("card") if slides else None
    if not hero:
        return slides
    same = lambda c: c and (c.get("id") == hero.get("id") or c.get("title") == hero.get("title"))  # noqa: E731
    return [slides[0]] + [s for s in slides[1:] if not (s.get("type") == "card" and same(s.get("card")))]


def with_hero(slides: List[Dict[str, Any]], title: str) -> List[Dict[str, Any]]:
    """The slides, the hook marked with its cover variant. On the hero side the lead bar chart moves onto the cover
    (its top rows) and leaves the deck, so slide 2, the one Instagram re-shows to people who scrolled past, is new;
    the card rides along on the hero for the X thread's first tweet."""
    if not slides or slides[0].get("type") != "hook":
        return slides
    if "cover" in slides[0]:  # chosen by hand (a hand-built post): still never repeat the cover's chart in the deck
        return without_hero_card(slides)
    out = deepcopy(slides)
    v = variant(title)
    at = next((i for i, s in enumerate(out[1:], 1) if s.get("type") == "card" and hero_from(s.get("card") or {})), None)
    if v == "hero" and at is not None and at == 1:  # only the lead card: a later chart would leave slide 2 as is
        lead = out.pop(at)["card"]
        out[0]["hero"] = {**hero_from(lead), "card": lead}
        out[0]["cover"] = "hero"
    else:
        out[0]["cover"] = "text" if v == "text" else "text-no-chart"
    return out
