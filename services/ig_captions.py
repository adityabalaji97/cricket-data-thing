"""
Instagram captions for the queued posts (services/ig_backlog.py).

    Who owns the pull shot in ODIs?                       <- the hook (slide 1's question)

    Rohit Sharma ranks 1st of 1,593 ODI batters ...       <- the answer: the fact's own sentence

    How: Ranked by sixes among 1,593 ODI batters ...      <- the method, one line

    Agree, or is someone missing?                         <- a question, so people comment

    Free ball-by-ball cricket stats: link in bio.
    .
    #RohitSharma #ODI #cricket #cricketstats              <- 3-5 specific hashtags

Every number is in the fact or the card titles the caption repeats; nothing here writes one. Instagram search reads
captions, so players are named in full and as hashtags.
"""
from __future__ import annotations

import re
from typing import Iterable, List, Optional

#: The closing question by pillar: something a fan can answer in a comment.
PROMPTS = {
    "debate": "Agree, or is someone missing?",
    "weird": "Did you know this one?",
    "myth": "Did the verdict surprise you?",
    "reactive": "Who are you backing?",
    "play": "Comment your answer before you swipe.",
}
FORMAT_TAGS = {"IPL": "#IPL", "ODI": "#ODI", "T20I": "#T20I", "T20": "#T20"}
BASE_TAGS = ["#cricket", "#cricketstats"]
MAX_TAGS = 5
LINK_LINE = "Free ball-by-ball cricket stats: link in bio."


def tag(text: str) -> str:
    """'Virat Kohli' -> '#ViratKohli' (letters and digits only)."""
    return "#" + re.sub(r"[^A-Za-z0-9]", "", text or "")


def hashtags(players: Iterable[str] = (), kicker: str = "", extra: Iterable[str] = ()) -> List[str]:
    """Up to MAX_TAGS: the occasion (extra), up to two players, the format or league, then the general ones."""
    out: List[str] = []
    fmt = next((t for k, t in FORMAT_TAGS.items() if re.search(rf"\b{k}\b", kicker or "")), None)
    for t in [*extra, *[tag(p) for p in list(players)[:2]], fmt, *BASE_TAGS]:
        if t and len(t) > 1 and t.lower() not in {o.lower() for o in out}:
            out.append(t)
    return out[:MAX_TAGS]


def _one_line(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


def build(hook: str, answer: str, pillar: str, method: Optional[str] = None, players: Iterable[str] = (),
          kicker: str = "", extra_tags: Iterable[str] = (), body: Iterable[str] = ()) -> str:
    """A caption: hook, answer (or body lines), method, a question, the link line, hashtags."""
    parts = [hook.strip()]
    if answer:
        parts.append(answer.strip())
    lines = [b for b in body if b]
    if lines:
        parts.append("\n".join(lines))
    if method:
        parts.append(f"How: {_one_line(method)}")
    parts.append(PROMPTS.get(pillar, PROMPTS["debate"]))
    # Instagram collapses blank lines unless something sits on them; a lone "." keeps the tags apart from the text.
    parts.append(f"{LINK_LINE}\n.\n{' '.join(hashtags(players, kicker, extra_tags))}")
    return "\n\n".join(parts)
