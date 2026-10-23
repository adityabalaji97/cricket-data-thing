"""
The social rules (docs/social_rules.md: Instagram posts, Reels, X) for code: its sections as text for LLM prompts and
Jev, and the rules code can test, as checks on a post's slides and a Reel's script. The Reddit title rules are
services/content_rules.py.

    section("Reels")            -> the section's bullets, for a prompt
    lint_slides(slides)         -> ["rule: what's wrong", ...] for a queued post (shown in the admin as warnings)
    hook_problem(hook)          -> why a Reel hook breaks the rules, or None (the Reel writer's guard rejects it)
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

RULES_FILE = Path(__file__).resolve().parents[1] / "docs" / "social_rules.md"
MAX_TITLE = 80  # two lines on a 4:5 card (docs/social_rules.md, Card anatomy)
MAX_SLIDES = 8
#: Metric names that lose a stranger in the first seconds of a Reel.
#: Words the house vocabulary replaces (docs/social_rules.md, Vocabulary): the term to use instead.
OFF_VOCAB = {"runs added": "Impact", "win chances": "win probability added", "new ball": "a phase name (powerplay)",
             "new-ball": "a phase name (powerplay)", "balls per dismissal": "balls per wicket", "out every": "balls per wicket",
             "runs above an average": "runs above par", "runs saved vs an average": "runs below par"}
OFF_VOCAB_RE = re.compile("|".join(re.escape(k) for k in OFF_VOCAB), re.I)

#: Cards that are words, not a picture: a carousel slide is a claim and a chart (docs/social_rules.md, Card anatomy).
TEXT_VISUALS = {"recap_text"}
#: A count of one with a plural noun ("1 overs"): name the one instead ("the 19th over").
ONE_PLURAL = re.compile(r"\b(?:1|one) (overs|balls|runs|wickets|sixes|fours|matches|innings|games|spells|points)\b", re.I)

JARGON = re.compile(r"\b(impact|wpa|raa|waa|win probability|runs above average|per 100|per hundred)\b", re.I)


@lru_cache(maxsize=1)
def _sections() -> Dict[str, str]:
    try:
        text = RULES_FILE.read_text(encoding="utf-8")
    except OSError:  # pragma: no cover - the rules are guidance; a missing file never stops a post
        return {}
    out: Dict[str, str] = {}
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        head, _, body = block.partition("\n")
        out[head.strip()] = body.strip()
    return out


def section(name: str) -> str:
    """A section's bullets as written ('' when it's missing)."""
    return _sections().get(name, "")


def _list_too_long(sentence: str) -> bool:
    """More than three items: four or more comma-separated parts, the last joined by "and"/"or" ("A, B, C and D").
    Commas in brackets and in numbers ("2,000") don't count, nor clauses that aren't a list."""
    flat = re.sub(r"(?<=\d),(?=\d)", "", re.sub(r"\([^)]*\)", "", sentence))
    parts = [p for p in flat.split(", ") if p.strip()]
    return len(parts) >= 4 and bool(re.search(r"\b(and|or)\b", parts[-1]))


def lint_card(card: Dict[str, Any]) -> List[str]:
    out = []
    title = card.get("title") or ""
    if card.get("visual") in TEXT_VISUALS:
        out.append("A text card: a slide is a claim and a picture; put the words in the caption")
    m = ONE_PLURAL.search(title)
    if m:
        out.append(f"{m.group(0)!r} in the title: name the one instead")
    if len(title) > MAX_TITLE:
        out.append(f"Title over {MAX_TITLE} characters ({len(title)}): it won't fit the slide")
    for sentence in re.split(r"(?<=[.!?])\s+", title):
        if _list_too_long(sentence):
            out.append("A list of more than three in the title")
            break
    if card.get("help") and not card.get("help_on_card") and len(card["help"]) > 90:
        out.append("A long help line: on the card it's only for a chart that can't be read without it (help_on_card)")
    seen = set()
    for where in (title, card.get("help") or "", card.get("sample") or "", str((card.get("payload") or {}).get("metric") or "")):
        for m in OFF_VOCAB_RE.finditer(where):
            k = m.group(0).lower()
            if k not in seen:
                seen.add(k)
                out.append(f"Say {OFF_VOCAB[k]!r}, not {m.group(0)!r} (docs/social_rules.md, Vocabulary)")
    payload = card.get("payload") or {}
    if card.get("visual") == "scorecard" and payload.get("rows"):
        rows = payload["rows"]
        for m in payload.get("metrics") or []:
            k = m.get("key")
            have = [r for r in rows if (r.get("values") or {}).get(k) is not None]
            if len(have) == 1 and k in (have[0].get("leader") or []):
                out.append(f"A 'best' ring on {k!r}, where only one row has a value")
    return out


def lint_slides(slides: List[Dict[str, Any]], kind: Optional[str] = None) -> List[str]:
    """Every testable carousel rule broken by a post's slides, as 'Slide n: ...' warnings. kind: the post's kind (a
    play-along keeps its deeper cut after the answer, on purpose)."""
    out = []
    hero = ((slides[0].get("hero") or {}).get("card") if slides and isinstance(slides[0], dict) else None) or {}
    if slides and slides[0].get("type") == "hook" and slides[0].get("cover") == "text-no-chart":
        out.append("Slide 1: no chart on the cover, and no card in the deck that can be one: lead with a chart "
                   "(services/ig_cover.hero_from lists the ones that fit)")
    if len(slides or []) > MAX_SLIDES:
        out.append(f"{len(slides)} slides: keep a carousel to {MAX_SLIDES} (completion counts)")
    for n, s in enumerate(slides or [], 1):
        c = s.get("card") if isinstance(s, dict) else None
        if not c:
            continue
        out += [f"Slide {n}: {w}" for w in lint_card(c)]
        if hero and n > 1 and (c.get("id") == hero.get("id") or c.get("title") == hero.get("title")):
            out.append(f"Slide {n}: repeats the cover's chart; the cover already shows it, so drop it from the deck")
        want = 2 if (slides[0].get("hero") if slides else None) else 3  # a hero cover takes the lead card off the deck
        if (c.get("kicker") or "").lower() == "the deeper cut" and n not in (want, 3) and kind != "play":
            out.append(f"Slide {n}: the deeper cut belongs on slide {want}")
    return out


def hook_problem(hook: str) -> Optional[str]:
    """Why a Reel hook breaks the Reel rules (a number, no metric names), or None."""
    h = (hook or "").strip()
    if not re.search(r"\d", h):
        return "the hook has no number: open on one player and one plain number"
    m = JARGON.search(h)
    if m:
        return f"the hook uses a metric name ({m.group(0)!r}): say it in plain words, explain the metric later"
    return None
