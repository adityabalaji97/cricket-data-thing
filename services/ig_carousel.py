"""
Instagram carousels: one post, several 4:5 slides, stored as a 'carousel' snapshot (api/img.mjs draws slide n at
/img/{id}.png?slide=n).

Slide types: hook (the question, big), chart (another snapshot: a ranking, scatter or preview card), text (a heading
and a paragraph or two), verdict (a hypothesis-lab verdict) and end (where to run it yourself). Three builders:

    for_fact(fact, chart_id, hook)        a debate or record post: hook, the chart, how it was measured, end
    for_note(note, hook)                  a myth post from a hypothesis-lab note: hook, claim, verdict, end
    for_preview(db, params, cards, hook)  a match-day post: hook, the chosen preview-story cards, end

Text comes from the fact or note it summarises, never written here, so the numbers on a slide are the ones the data
produced. Hooks are written by hand (services/ig_backlog.IDEAS) and carry no numbers.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

#: The longest a text slide's body may be (characters); longer text is cut at a sentence.
TEXT_LIMIT = 330
END_BODY = "Every number here comes from ball-by-ball data. Ask your own question on the query builder: it's free."


def _plain(md: str) -> str:
    """Markdown to plain text: links keep their words, emphasis and code marks go."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md or "")
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_`]+", "", text)
    text = re.sub(r"^\s*[-•]\s+", "", text, flags=re.M)
    return re.sub(r"[ \t]+", " ", text).strip()


def clip(text: str, limit: int = TEXT_LIMIT) -> str:
    """Whole sentences up to `limit` characters (at least one sentence, cut with an ellipsis if even that is long)."""
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    out = ""
    for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text):
        if len(out) + len(sentence) + 1 > limit:
            break
        out = f"{out} {sentence}".strip()
    return out or text[: limit - 1].rsplit(" ", 1)[0] + "…"


def note_sections(body_md: str) -> Dict[str, str]:
    """{'the claim': ..., 'verdict': 'Partly', 'verdict body': ...} from a hypothesis note's '## ' sections."""
    out: Dict[str, str] = {}
    for block in re.split(r"^## ", body_md or "", flags=re.M)[1:]:
        heading, _, body = block.partition("\n")
        heading = heading.strip()
        if heading.lower().startswith("verdict:"):
            out["verdict"] = heading.split(":", 1)[1].strip()
            out["verdict body"] = body.strip()
        else:
            out[heading.lower()] = body.strip()
    return out


def _first_paragraph(md: str) -> str:
    """The first paragraph of prose (skipping tables, lists of links, and headings)."""
    for para in re.split(r"\n\s*\n", md or ""):
        para = para.strip()
        if para and not para.startswith(("|", "#", "```")):
            return _plain(para)
    return ""


def _verdict_lines(md: str, limit: int = 4) -> str:
    """A verdict's parts, one per line ("a. ...: Inconclusive"), else its first paragraph; at most `limit` lines."""
    para = next((p for p in re.split(r"\n\s*\n", md or "") if p.strip()), "")
    lines = [_plain(l) for l in para.splitlines() if l.strip()]
    if len(lines) > 1:
        return "\n".join(clip(l, 120) for l in lines[:limit])
    return clip(_plain(para), 260)


def for_fact(fact: Dict[str, Any], chart_id: str, hook: str, kicker: str = "") -> List[Dict[str, Any]]:
    """Hook, the chart, how it was measured, end."""
    method = fact.get("method") or ""
    return [
        {"type": "hook", "text": hook, "kicker": kicker, "sub": "Swipe for the answer"},
        {"type": "chart", "snapshot_id": chart_id},
        {"type": "text", "heading": "How we measured it", "body": clip(method, TEXT_LIMIT)},
        {"type": "end", "heading": "Run it yourself", "body": END_BODY},
    ]


def for_note(note: Dict[str, Any], hook: Optional[str] = None) -> List[Dict[str, Any]]:
    """Hook, the claim, how it was tested, what the numbers say, the verdict, end."""
    sections = note_sections(note.get("body_md") or "")
    slides = [{"type": "hook", "text": hook or note["title"], "kicker": "Myth or fact?", "sub": "We tested it on ball-by-ball data"}]
    # Only the parts that read on a phone: the claim and the verdict. The method paragraph is the same
    # pre-registration line in every note, and the note's charts are analysis charts (bucket labels, sample
    # warnings in the title); both stay one tap away in the full write-up.
    claim = clip(_first_paragraph(sections.get("the claim", "")))
    if claim:
        slides.append({"type": "text", "heading": "The claim", "body": claim})
    if sections.get("verdict"):
        slides.append({"type": "verdict", "verdict": sections["verdict"],
                       "body": _verdict_lines(sections.get("verdict body", ""))})
    slides.append({"type": "end", "heading": "Read the full test",
                   "body": "Every threshold was written down before the analysis ran. The full write-up, charts and "
                           "data are on Hindsight."})
    return slides


def for_preview(chart_ids: List[str], hook: str, kicker: str, sub: str = "") -> List[Dict[str, Any]]:
    """Hook, the chosen preview cards (already frozen as preview_card snapshots), end."""
    return ([{"type": "hook", "text": hook, "kicker": kicker, "sub": sub or "Swipe through before the toss"}]
            + [{"type": "chart", "snapshot_id": cid} for cid in chart_ids]
            + [{"type": "end", "heading": "The full preview", "body": "Every card in the match preview story, "
                                                                     "free on Hindsight."}])


def save(db: Session, slides: List[Dict[str, Any]], title: str, key: Dict[str, Any], created_by: str) -> Dict[str, Any]:
    """Store the slides as a carousel snapshot. Snapshots are frozen and de-duplicated by key, so the slides are part
    of the key: the same slides give back the same snapshot, changed slides a new one."""
    from services.snapshots import create_static_snapshot

    return create_static_snapshot(db, "carousel", {"slides": slides, "title": title}, title,
                                  {"carousel": key, "slides": slides}, created_by=created_by)
