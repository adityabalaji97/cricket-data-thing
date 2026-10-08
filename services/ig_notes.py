"""
Instagram posts on two more channels: a note on the site (for Google) and a YouTube Short (the Reel's video).

    note_body(...)      a debate or record carousel as a note: the search-phrased title, the verdict as the dek, each
                        card as a heading, its slide (image, the card title as alt text) and its data as a table, so
                        search engines index real text and numbers, not just pictures
    youtube_copy(...)   the Short's title (the search wording, under 100 characters, #shorts) and description
    extras_pending(db)  makes both for queued posts that lack them: notes as drafts for the admin to publish
                        (/admin/notes), YouTube copy into the pack's facts (shown on the admin card)

Titles come from services/search_titles (Google's autocomplete); every number comes from the post's own cards.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from services import search_titles as T

logger = logging.getLogger(__name__)

#: Measures as people say them, for titles ("Impact, win probability and strike rate compared").
MEASURE_WORDS = {"raa": "runs above average", "impact": "Impact", "wpa": "win probability", "sr": "strike rate",
                 "bpd": "balls per dismissal", "average": "average", "control": "control", "boundary": "boundaries",
                 "dot": "dot balls", "sixes": "sixes", "economy": "economy", "strike": "wicket-taking",
                 "wickets_inns": "wickets"}
FORMAT_TAG = {"IPL": "#IPL", "ODIs": "#ODI", "T20Is": "#T20I", "ODI": "#ODI", "T20": "#T20"}


def _fmt(v: Any, kind: str = "dec1") -> str:
    from services.ig_posts.cards import fmt

    try:
        return fmt(float(v), kind)
    except (TypeError, ValueError):
        return "–"


def card_table(card: Dict[str, Any]) -> str:
    """A card's data as a markdown table (the numbers the slide draws), or '' for visuals without one."""
    p, v = card.get("payload") or {}, card.get("visual")
    rows: List[List[str]] = []
    if v == "metric_bars":
        m = p.get("metric") or {}
        head = ["#", "Player", m.get("label", "value").capitalize()]
        rows = [[str(i + 1), r["name"], _fmt(r["value"], m.get("format", "dec1"))] for i, r in enumerate(p.get("rows", []))]
    elif v == "scorecard":
        metrics = p.get("metrics", [])
        head = ["Player"] + [m["label"] for m in metrics]
        rows = [[r["name"]] + [_fmt((r.get("values") or {}).get(m["key"]), m["format"]) for m in metrics] for r in p.get("rows", [])]
    elif v == "race_lines":
        head = ["Player", f"Reached it in ({p.get('unit', '')})"]
        rows = [[s["name"], f"{s['reached_at']:,}"] for s in p.get("series", [])]
    elif v == "scatter_plus":
        x, y = p.get("x") or {}, p.get("y") or {}
        head = ["Player", y.get("label", "y").capitalize(), x.get("label", "x").capitalize()]
        pts = sorted((q for q in p.get("points", []) if q.get("label") or q.get("highlight")), key=lambda q: q.get("label") or 99)
        rows = [[q["name"], _fmt(q["y"], y.get("format", "dec1")), _fmt(q["x"], x.get("format", "dec1"))] for q in pts]
    elif v == "boundary_zones":
        head = ["Zone", "Share of boundaries", "Field"]
        rows = [[z["name"], f"{z['pct']:.0f}%", f"{z.get('usual_pct', 0):.0f}%"] for z in sorted(p.get("zones", []), key=lambda z: -z["pct"])]
    else:
        return ""
    if not rows:
        return ""
    esc = lambda c: str(c).replace("|", "/")  # noqa: E731
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows])


def note_body(slides: List[Dict[str, Any]], carousel_id: str, intro: str, method: str) -> str:
    parts = [intro]
    for n, s in enumerate(slides, 1):
        c = s.get("card")
        if s.get("type") != "card" or not c:
            continue
        parts.append(f"## {c['title']}")
        parts.append(f"![{c['title']}](/img/{carousel_id}.png?slide={n})")
        table = card_table(c)
        if table:
            parts.append(table)
        if c.get("sample"):
            parts.append(f"*{c['sample']}*")
    parts.append(f"**How we measured it.** {method}")
    parts.append("[Ask your own question on the query builder](/query)")
    return "\n\n".join(parts) + "\n"


def _with_question(fact: Dict[str, Any]) -> Dict[str, Any]:
    """Posts made before facts carried noun / kicker / scope: recover them from the generator's question key."""
    if fact.get("kind") != "debate" or fact.get("noun") or not fact.get("question"):
        return fact
    from services.ig_posts.questions import candidates

    q = next((c for c in candidates() if c.key == fact["question"]), None)
    return {**fact, "noun": q.noun, "kicker": q.kicker, "scope_label": q.scope_label} if q else fact


def note_title(fact: Dict[str, Any]) -> Optional[str]:
    fact = _with_question(fact)
    if fact.get("kind") == "record" and not fact.get("hook"):
        m = re.search(r"got to (.+?) in [\d,]+ (?:balls|innings)", fact.get("title") or "")
        fact = {**fact, "hook": f"Who is the fastest to {m.group(1)}?"} if m else fact
    if fact.get("kind") == "debate" and fact.get("noun"):
        since = re.search(r"since (?:the \d{4} World Cup|\d{4})", fact.get("scope_label") or "")
        measures = [MEASURE_WORDS.get(a, a) for a in (fact.get("angles") or [])][:3]
        return T.debate_title(fact["noun"], fact.get("kicker") or "", since.group(0) if since else "", measures)
    if fact.get("kind") == "record":
        m = re.search(r"fastest to (.+)\?", (fact.get("hook") or "").lower())
        return T.record_title(m.group(1), fact.get("kicker") or "") if m else None
    return None


def youtube_copy(fact: Dict[str, Any], caption: str, search_title: Optional[str]) -> Dict[str, str]:
    """{title, description} for the Short. Hashtags: the first three show above the title on YouTube."""
    base = search_title or fact.get("title") or ""
    title = base if len(base) <= 90 else base[:87].rsplit(" ", 1)[0] + "…"
    tags = ["#cricket", FORMAT_TAG.get(fact.get("kicker") or "", "#cricketstats"), "#shorts"]
    body = re.sub(r"\n?\.\n#.*$", "", caption or "", flags=re.S)  # the Instagram caption without its hashtags
    body = re.sub(r"\n*Free ball-by-ball cricket stats: link in bio\.?", "", body)  # Instagram's line; YouTube gets its own
    return {"title": f"{title} #shorts", "description": f"{body.strip()}\n\nFull data, free: hindsightcricket.com\n\n{' '.join(tags)}"}


def x_copy(db: Session, carousel_id: str, caption: str) -> List[Dict[str, Any]]:
    """The carousel as an X thread (services/ig_x.py), one tweet per slide; chart slides take their chart's title."""
    from services.ig_x import x_thread

    snap = db.execute(text("SELECT data FROM chart_snapshots WHERE id = :i"), {"i": carousel_id}).scalar()
    slides = (snap or {}).get("slides", [])
    chart_ids = [s["snapshot_id"] for s in slides if s.get("type") == "chart" and s.get("snapshot_id")]
    titles = dict(db.execute(text("SELECT id, title FROM chart_snapshots WHERE id = ANY(:ids)"),
                             {"ids": chart_ids}).all()) if chart_ids else {}
    return x_thread(slides, caption, titles)


def extras_pending(db: Session) -> Dict[str, int]:
    """Draft notes for debate and record posts without one; YouTube copy and an X thread for every post without them."""
    from database import engine
    from services.notes import bot_author_id, create_note

    rows = db.execute(text("""
        SELECT id, title, caption, facts FROM content_packs
        WHERE channel = 'instagram' AND status IN ('ready', 'posted') AND facts->>'carousel_id' IS NOT NULL
          AND (facts->'youtube' IS NULL OR facts->'x' IS NULL
               OR (facts->>'kind' IN ('debate', 'record') AND facts->>'note_id' IS NULL
                                            AND COALESCE(facts->>'trending', 'false') <> 'true'))
    """)).mappings().all()
    made = {"notes": 0, "youtube": 0, "x": 0}
    for r in rows:
        fact = _with_question(dict(r["facts"] or {}))
        title = note_title(fact)
        if fact.get("kind") in ("debate", "record") and not fact.get("trending") and not fact.get("note_id") and title:
            snap = db.execute(text("SELECT data FROM chart_snapshots WHERE id = :i"), {"i": fact["carousel_id"]}).scalar()
            slides = (snap or {}).get("slides", [])
            intro = f"{fact.get('hook') or r['title']}\n\n{fact.get('verdict') or ''}".strip()
            try:
                note = create_note(db, title=title, author_id=bot_author_id(db), dek=fact.get("verdict"), kind="analysis",
                                   body_md=note_body(slides, fact["carousel_id"], intro, fact.get("method") or ""),
                                   pack_id=r["id"])
                fact["note_id"], fact["note_slug"] = note["id"], note["slug"]
                made["notes"] += 1
            except Exception:  # a note that can't be made never blocks the post
                logger.exception("note for pack %s failed", r["id"])
                db.rollback()
        if not fact.get("youtube"):
            fact["youtube"] = youtube_copy(fact, r["caption"] or "", title)
            made["youtube"] += 1
        if not fact.get("x"):
            fact["x"] = x_copy(db, fact["carousel_id"], r["caption"] or "")
            made["x"] += 1
        with engine.begin() as conn:
            conn.execute(text("UPDATE content_packs SET facts = CAST(:f AS jsonb) WHERE id = :i"),
                         {"f": json.dumps(fact, default=str), "i": r["id"]})
    return made
