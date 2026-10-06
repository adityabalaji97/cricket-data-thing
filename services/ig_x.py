"""
An Instagram carousel as an X thread: one slide per tweet, each with its own line of text and the post's hashtags.

    x_thread(slides, caption, chart_titles)  ->  [{"n": 1, "text": "...", "slide": 1}, ...]

Tweet 1 is the hook slide (marked as a thread), each reply is the next slide with the sentence it shows (a card's
title is its takeaway), and the last carries the link (hindsightcricket.com/links?utm_source=x, counted by the usage
report). Every tweet fits X's 280 characters, counting a link as 23 as X does. Posting is by hand from the admin page.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

LIMIT = 280
LINK = "hindsightcricket.com/links?utm_source=x"
LINK_WEIGHT = 23  # X counts every link as 23 characters, whatever its length
MAX_TAGS = 2      # more than two reads as spam on X
DEFAULT_TAGS = ["#cricket"]


def tags_from_caption(caption: str) -> List[str]:
    """The post's first hashtags, from the Instagram caption's last line (occasion tags lead, e.g. #INDvWI)."""
    tags = re.findall(r"#\w+", (caption or "").strip().splitlines()[-1] if caption else "")
    return tags[:MAX_TAGS] or DEFAULT_TAGS


def _weight(text: str) -> int:
    text = text.replace(LINK, "x" * LINK_WEIGHT)
    return len(text) + sum(1 for ch in text if ord(ch) > 0xFFFF)  # emoji count twice


def _fit(body: str, suffix: str) -> str:
    """body + suffix within LIMIT: the body is cut at a word, never the suffix (numbering, tags, link)."""
    room = LIMIT - _weight(suffix)
    body = body.strip()
    if len(body) > room:
        body = body[:room - 1].rsplit(" ", 1)[0].rstrip(" ,;:·—-") + "…"
    return body + suffix


def _lines(text: Optional[str]) -> str:
    return " ".join(line.strip() for line in str(text or "").splitlines() if line.strip())


def slide_text(slide: Dict[str, Any], chart_titles: Dict[str, str]) -> str:
    kind = slide.get("type")
    if kind == "hook":
        kicker = slide.get("kicker")
        return f"{kicker}: {slide.get('text')}" if kicker else str(slide.get("text") or "")
    if kind == "card":
        card = slide.get("card") or {}
        return str(card.get("title") or "")
    if kind == "chart":
        return chart_titles.get(slide.get("snapshot_id") or "", "")
    if kind == "verdict":
        return f"Verdict: {slide.get('verdict')}. {_lines(slide.get('body'))}".strip()
    if kind == "end":
        return f"{slide.get('heading') or 'Run it yourself'}: {_lines(slide.get('body'))}".strip()
    heading = slide.get("heading")
    return f"{heading}: {_lines(slide.get('body'))}" if heading else _lines(slide.get("body"))


def x_thread(slides: List[Dict[str, Any]], caption: str, chart_titles: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    tags = " ".join(tags_from_caption(caption))
    total = len(slides)
    tweets = []
    for i, slide in enumerate(slides, start=1):
        body = slide_text(slide, chart_titles or {})
        if i == 1:
            suffix = f"\n\nA thread 🧵 1/{total}\n{tags}"
        elif i == total:
            suffix = f"\n\nFull data, free: {LINK}\n{i}/{total} {tags}"
        else:
            suffix = f"\n\n{i}/{total} {tags}"
        tweets.append({"n": i, "slide": i, "text": _fit(body, suffix)})
    return tweets


def weight(text: str) -> int:
    """A tweet's length as X counts it (links as 23)."""
    return _weight(text)
