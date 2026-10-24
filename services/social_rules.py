"""
The social rules (docs/social_rules.md: Instagram posts, Reels, X) for code: its sections as text for LLM prompts and
Jev, and the rules code can test, as checks on a post's slides and a Reel's script. The Reddit title rules are
services/content_rules.py.

    section("Reels")            -> the section's bullets, for a prompt
    findings(slides, kind)      -> [{rule, slide, visual, message}]: each broken rule, by its RULES id
    lint_slides(slides)         -> ["Slide n: what's wrong", ...] for a queued post (shown in the admin as warnings)
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
ONE_PLURAL = re.compile(r"(?<![\d.])\b(?:1|one) (overs|balls|runs|wickets|sixes|fours|matches|innings|games|spells|points)\b", re.I)

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


#: Every rule the lint checks, by id: what the audit (scripts/audit_social_rules.py) and the gate group findings by.
RULES = {
    "text_card": "a text card in the deck",
    "one_plural": "a count of one with a plural noun",
    "long_title": f"a title over {MAX_TITLE} characters",
    "title_list": "a list of more than three in a title",
    "long_help": "a long help line drawn on the card",
    "vocabulary": "a word the house vocabulary replaces",
    "lonely_ring": "a 'best' ring where only one row has a value",
    "bare_cover": "no chart on the cover, and none in the deck that can be one",
    "slide_count": f"more than {MAX_SLIDES} slides",
    "cover_repeat": "the cover's chart repeated in the deck",
    "deeper_cut_slot": "the deeper cut not on its slide",
}


#: What only the drawn slide shows, measured at render (scripts/lib/slide_layout.mjs, stored as facts.layout).
LAYOUT_RULES = {
    "title_lines": "a title over 2 lines, as drawn",
    "title_clipped": "a title cut off, as drawn",
    "footer_lines": "a scope line that wraps",
    "legend": "a legend chip that's a sentence",
    "text_clipped": "a label cut short with an ellipsis",
    "label_outside": "a chart label cut off at the edge",
    "label_overlap": "two chart labels on each other",
    "card_overflow": "a chart that doesn't fit its card",
    "small_chart": "a chart under 35% of the card",
}


def card_findings(card: Dict[str, Any]) -> List[Dict[str, str]]:
    """[{rule, message}] for one card (rule: a RULES id)."""
    out: List[Dict[str, str]] = []
    add = lambda rule, message: out.append({"rule": rule, "message": message})  # noqa: E731
    title = card.get("title") or ""
    if card.get("visual") in TEXT_VISUALS:
        add("text_card", "A text card: a slide is a claim and a picture; put the words in the caption")
    m = ONE_PLURAL.search(title)
    if m:
        add("one_plural", f"{m.group(0)!r} in the title: name the one instead")
    if len(title) > MAX_TITLE:
        add("long_title", f"Title over {MAX_TITLE} characters ({len(title)}): it won't fit the slide")
    for sentence in re.split(r"(?<=[.!?])\s+", title):
        if _list_too_long(sentence):
            add("title_list", "A list of more than three in the title")
            break
    # A help line is only drawn on the card with help_on_card (else it's in the info sheet): only a drawn one counts.
    if card.get("help") and card.get("help_on_card") and len(card["help"]) > 90:
        add("long_help", "A long help line drawn on the card: shorten it, or move it to the info sheet")
    seen = set()
    for where in (title, card.get("help") or "", card.get("sample") or "", str((card.get("payload") or {}).get("metric") or "")):
        for m in OFF_VOCAB_RE.finditer(where):
            k = m.group(0).lower()
            if k == "runs added" and re.search(r"\bimpact\b", where, re.I):
                continue  # "Impact: runs added to the projected total" defines Impact, it doesn't replace it
            if k not in seen:
                seen.add(k)
                add("vocabulary", f"Say {OFF_VOCAB[k]!r}, not {m.group(0)!r} (docs/social_rules.md, Vocabulary)")
    payload = card.get("payload") or {}
    if card.get("visual") == "scorecard" and payload.get("rows"):
        rows = payload["rows"]
        for m in payload.get("metrics") or []:
            k = m.get("key")
            have = [r for r in rows if (r.get("values") or {}).get(k) is not None]
            if len(have) == 1 and k in (have[0].get("leader") or []):
                add("lonely_ring", f"A 'best' ring on {k!r}, where only one row has a value")
    return out


def lint_card(card: Dict[str, Any]) -> List[str]:
    return [f["message"] for f in card_findings(card)]


def findings(slides: List[Dict[str, Any]], kind: Optional[str] = None) -> List[Dict[str, Any]]:
    """Every testable carousel rule broken by a post's slides: [{rule, slide (None for the deck), visual, message}].
    kind: the post's kind (a play-along keeps its deeper cut after the answer, on purpose)."""
    out: List[Dict[str, Any]] = []
    hero = ((slides[0].get("hero") or {}).get("card") if slides and isinstance(slides[0], dict) else None) or {}
    if slides and slides[0].get("type") == "hook" and slides[0].get("cover") == "text-no-chart":
        out.append({"rule": "bare_cover", "slide": 1, "visual": None,
                    "message": "no chart on the cover, and no card in the deck that can be one: lead with a chart "
                               "(services/ig_cover.hero_from lists the ones that fit)"})
    if len(slides or []) > MAX_SLIDES:
        out.append({"rule": "slide_count", "slide": None, "visual": None,
                    "message": f"{len(slides)} slides: keep a carousel to {MAX_SLIDES} (completion counts)"})
    for n, s in enumerate(slides or [], 1):
        c = s.get("card") if isinstance(s, dict) else None
        if not c:
            continue
        out += [{**f, "slide": n, "visual": c.get("visual")} for f in card_findings(c)]
        if hero and n > 1 and (c.get("id") == hero.get("id") or c.get("title") == hero.get("title")):
            out.append({"rule": "cover_repeat", "slide": n, "visual": c.get("visual"),
                        "message": "repeats the cover's chart; the cover already shows it, so drop it from the deck"})
        want = 2 if (slides[0].get("hero") if slides else None) else 3  # a hero cover takes the lead card off the deck
        if (c.get("kicker") or "").lower() == "the deeper cut" and n not in (want, 3) and kind != "play":
            out.append({"rule": "deeper_cut_slot", "slide": n, "visual": c.get("visual"),
                        "message": f"the deeper cut belongs on slide {want}"})
    return out


def lint_slides(slides: List[Dict[str, Any]], kind: Optional[str] = None) -> List[str]:
    """findings() as 'Slide n: ...' warnings, as the admin shows them."""
    return [f"Slide {f['slide']}: {f['message']}" if f["slide"] else f["message"] for f in findings(slides, kind)]


def hook_problem(hook: str) -> Optional[str]:
    """Why a Reel hook breaks the Reel rules (a number, no metric names), or None."""
    h = (hook or "").strip()
    if not re.search(r"\d", h):
        return "the hook has no number: open on one player and one plain number"
    m = JARGON.search(h)
    if m:
        return f"the hook uses a metric name ({m.group(0)!r}): say it in plain words, explain the metric later"
    return None
