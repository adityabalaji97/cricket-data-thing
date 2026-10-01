"""
Hindsight Bot drafts Notes (Notes plan step 7): recaps of newly loaded matches and previews of the
next day's fixtures, queued as drafts in /admin/notes. Nothing publishes without a person.

No LLM prose: every sentence comes from code that already writes verified facts --
  recaps    services/match_recap.build_recap (how it was won) + the match's content packs
            (records, firsts and standout angles, already ranked by Jev and checked by
            services/content_rules) and their ranking charts
  previews  services/typed_preview.build_candidate_facts on the preview context, curated by Jev
            when it is configured, plus a query chart of the venue's leading batters
Titles are the top fact as a statement with its numbers (docs/content_guidelines.md).

One recap and one preview per match (migration 010's unique index); re-runs are no-ops.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services import content_rules
from services.notes import bot_author_id, chart_fence, create_note

logger = logging.getLogger(__name__)

PREVIEW_HORIZON_HOURS = 36
# Previews below this many code-written facts are too thin to publish (no venue or head-to-head
# sample): the deterministic fallback would read "0 matches ... N/A".
MIN_PREVIEW_FACTS = 5
VENUE_CHART_MIN_BALLS = {"T20": 60, "ODI": 150}
IST = timezone(timedelta(hours=5, minutes=30))
FORMAT_SLUG = {"T20": "mens-t20", "ODI": "mens-odi"}


def _ground(venue: Optional[str]) -> str:
    return (venue or "").split(",")[0].strip()


def _long_date(d: Any) -> str:
    if isinstance(d, str):
        d = date.fromisoformat(d[:10])
    return f"{d.day} {d:%b %Y}" if d else ""


def _title_ok(title: str, known: List[Dict[str, Any]], subject: Optional[str]) -> bool:
    errors, _ = content_rules.check_title(title, known, subject)
    return not errors


# ------------------------------------------------------------------------------------- recaps

def compose_recap(match: Dict[str, Any], result: Optional[str], recap: Optional[Dict[str, Any]],
                  packs: List[Dict[str, Any]], win_prob_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Title, dek and markdown body for a recap note; None when there is nothing to say.

    `packs` are the match's content packs ({title, facts, snapshot_id, source}); the 'recap'
    source pack is the win-probability series post and is covered by `recap` + `win_prob_id`.
    """
    records = [p for p in packs if p.get("source") != "recap" and p.get("snapshot_id")]
    has_recap = bool(recap and recap.get("available"))
    if not has_recap and not records:
        return None
    t1, t2 = match["team1"], match["team2"]

    candidates = [p["title"] for p in records]
    if has_recap:
        candidates.append(f"{t1} v {t2}: {recap['headline'].rstrip('.')}")
    known = [{"headline": recap.get("headline"), "bullets": recap.get("bullets")}] if has_recap else []
    known += [p.get("facts") or {} for p in records]
    title = next((c for c in candidates if _title_ok(c, known, None)), None)
    if not title:
        title = f"{t1} v {t2}: {result}" if result else f"{t1} v {t2} recap"

    where = ", ".join(x for x in [match.get("competition"), _long_date(match.get("date"))] if x)
    dek = " · ".join(x for x in [result, where] if x)

    parts: List[str] = []
    if has_recap:
        lead = recap["headline"]
        if not title.endswith(lead.rstrip(".")):
            parts.append(lead)
        bullets = [b for b in recap.get("bullets") or []]
        if bullets:
            parts.append("## How it was won\n\n" + "\n".join(f"- {b}" for b in bullets))
    elif result:
        parts.append(f"{result}.")
    if win_prob_id:
        parts.append(chart_fence(win_prob_id))
    if records:
        parts.append("## The numbers that stood out")
        for p in records:
            method = ((p.get("facts") or {}).get("method") or "").strip()
            # The title fact is already the headline; under it, say only how it was measured.
            lead = "" if p["title"] == title else f"**{p['title'].rstrip('.')}.**"
            if lead or method:
                parts.append(" ".join(x for x in [lead, method] if x))
            parts.append(chart_fence(p["snapshot_id"]))
    parts.append(f"[Full scorecard](/scorecard/{match['id']})")
    return {"title": title, "dek": dek or None, "body_md": "\n\n".join(parts) + "\n"}


def recap_candidates(db: Session, days: int = 10, match_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """In-scope matches loaded in the last `days` days with a result and no recap note yet."""
    if match_ids:
        rows = db.execute(text("""
            SELECT m.* FROM matches m WHERE m.id = ANY(:ids)
              AND NOT EXISTS (SELECT 1 FROM notes n WHERE n.kind = 'recap' AND n.match_id = m.id)
        """), {"ids": [str(m) for m in match_ids]})
    else:
        rows = db.execute(text("""
            SELECT m.* FROM matches m
            WHERE m.date >= :since AND m.format IN ('T20', 'ODI')
              AND NOT EXISTS (SELECT 1 FROM notes n WHERE n.kind = 'recap' AND n.match_id = m.id)
            ORDER BY m.date DESC
        """), {"since": date.today() - timedelta(days=days)})
    return [dict(r) for r in rows.mappings() if content_rules.in_scope(dict(r))]


def _match_packs(db: Session, match_id: str) -> List[Dict[str, Any]]:
    rows = db.execute(text("""
        SELECT id, title, facts, snapshot_id, source FROM content_packs
        WHERE match_id = :m ORDER BY (source = 'recap'), created_at, id
    """), {"m": match_id}).mappings()
    return [dict(r) for r in rows]


def draft_recap(db: Session, match: Dict[str, Any], dry_run: bool = False) -> Optional[Dict[str, Any]]:
    from services.match_recap import build_recap
    from services.match_scorecard import get_match_scorecard_service
    from services.snapshots import SnapshotError, create_snapshot

    match_id = str(match["id"])
    scorecard = get_match_scorecard_service(match_id=match_id, min_balls=6, db=db)
    info = scorecard.get("match") or {}
    result = info.get("result_text")
    if not result:
        return None  # not finished, or no result recorded yet
    primer = (scorecard.get("summary") or {}).get("primer")
    recap = build_recap(scorecard, db) if primer else None
    packs = _match_packs(db, match_id)
    win_prob_id = None
    if primer and not dry_run:
        try:
            win_prob_id = create_snapshot(db, "win_prob", {"match_id": match_id}, created_by="draft_notes")["id"]
        except SnapshotError as exc:
            logger.info("no win-probability chart for %s: %s", match_id, exc)
    draft = compose_recap(match, result, recap, packs, win_prob_id or ("WINPROB" if primer and dry_run else None))
    if not draft or dry_run:
        return draft
    return _save(db, draft, kind="recap", match_id=match_id)


# ------------------------------------------------------------------------------------- previews

def fixture_scope(fixture: Dict[str, Any]) -> Dict[str, Any]:
    """A fixture shaped like a matches row, for content_rules.in_scope."""
    fmt = fixture.get("format") or "T20"
    series = fixture.get("series") or ""
    international = fmt == "ODI" or fixture.get("event_type") in ("T20I", "ODI") or not _is_league(series)
    return {
        "gender": "male", "team1": fixture.get("team1"), "team2": fixture.get("team2"), "format": fmt,
        "competition": ("ODI" if fmt == "ODI" else "T20I") if international else series,
        "match_type": "international" if international else "league",
    }


def _is_league(series: str) -> bool:
    from services.competition_aliases import canonical_competition

    return canonical_competition(series) in content_rules.MAIN_LEAGUES


def preview_candidates(db: Session, fixtures: List[Dict[str, Any]], now: Optional[datetime] = None,
                       horizon_hours: int = PREVIEW_HORIZON_HOURS) -> List[Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    out = []
    for f in fixtures:
        start = f.get("start_utc")
        if not start or not f.get("match_id") or f.get("is_live") or f.get("format") not in FORMAT_SLUG:
            continue
        start_dt = datetime.fromisoformat(start)
        if not (now < start_dt <= now + timedelta(hours=horizon_hours)):
            continue
        if not content_rules.in_scope(fixture_scope(f)):
            continue
        exists = db.execute(text("SELECT 1 FROM notes WHERE kind = 'preview' AND match_id = :m"),
                            {"m": str(f["match_id"])}).first()
        if not exists:
            out.append(f)
    return out


def _when(start_utc: str) -> str:
    dt = datetime.fromisoformat(start_utc)
    ist = dt.astimezone(IST)
    return f"{ist:%a} {ist.day} {ist:%b}, {ist:%H:%M} IST ({dt.astimezone(timezone.utc):%H:%M} GMT)"


def preview_url(fixture: Dict[str, Any]) -> str:
    return "/venue?" + urlencode([
        ("venue", fixture["venue"]), ("team1", fixture["team1"]), ("team2", fixture["team2"]),
        ("includeInternational", "true"), ("autoload", "true"), ("fmt", FORMAT_SLUG[fixture["format"]]),
    ])


def compose_preview(fixture: Dict[str, Any], sections: List[Dict[str, Any]], headline: Optional[str],
                    known: List[Dict[str, Any]], chart: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    t1, t2, ground = fixture["team1"], fixture["team2"], _ground(fixture.get("venue"))
    title = f"{t1} v {t2} preview: {headline.rstrip('.')}" if headline else ""
    if not title or not _title_ok(title, known, None):
        title = f"{t1} v {t2} at {ground}: match preview"
    series = (fixture.get("series") or "").title()
    dek = " · ".join(x for x in [series, fixture["format"], ground, _when(fixture["start_utc"])] if x)

    parts = [f"{t1} play {t2} at {fixture['venue']}, {_when(fixture['start_utc'])}."]
    for section in sections:
        parts.append(f"## {section['title']}\n\n" + "\n".join(f"- {b}" for b in section["bullets"]))
        if section.get("id") == "venue_profile" and chart:
            parts.append(chart["lead"])
            parts.append(chart_fence(chart["id"]))
    if chart and not any(s.get("id") == "venue_profile" for s in sections):
        parts += [chart["lead"], chart_fence(chart["id"])]
    parts.append(f"[Open the full preview, with batter-v-bowler matchups]({preview_url(fixture)})")
    return {"title": title, "dek": dek, "body_md": "\n\n".join(parts) + "\n"}


def _preview_facts(db: Session, fixture: Dict[str, Any]) -> Dict[str, Any]:
    from mcp_server.server import _default_window
    from routers.match_preview import _inject_form_flags
    from services import typed_preview
    from services.match_preview import gather_preview_context

    fmt = fixture["format"]
    start, end = _default_window(fmt)
    context = gather_preview_context(
        venue=fixture["venue"], team1_identifier=fixture["team1"], team2_identifier=fixture["team2"], db=db,
        start_date=start, end_date=end, include_international=True, top_teams=20, day_or_night=None,
        fmt=fmt, gender="male",
    )
    try:
        _inject_form_flags(context, db)
    except Exception as exc:  # optional enrichment, as on the site
        logger.warning("form flags failed for preview: %r", exc)
    facts = typed_preview.build_candidate_facts(context)
    curated = None
    try:
        curated = typed_preview.curate(context, facts)
    except Exception as exc:
        logger.warning("Jev curation failed; keeping fact order: %r", exc)
    if not curated:
        # Without Jev every fact is "relevant"; sections keep the order code wrote them in.
        for f in facts:
            f.setdefault("score", None)
            if not f["fixed"]:
                f["score"] = typed_preview.KEEP_THRESHOLD
        curated = typed_preview.assemble(facts)
        curated["headline"] = None   # no ranking, so no claim that one fact leads
    return {"start": start, "facts": facts, **curated}


def _venue_chart(db: Session, fixture: Dict[str, Any], start: date) -> Optional[Dict[str, Any]]:
    """The venue's leading batters (Impact for men's T20, runs for ODIs) as a query snapshot."""
    from services.snapshots import SnapshotError, create_snapshot

    fmt = fixture["format"]
    base = {"venue": fixture["venue"], "fmt": fmt, "gender": "male", "start_date": start.isoformat(),
            "group_by": ["batter"], "min_balls": VENUE_CHART_MIN_BALLS[fmt], "limit": 8}
    for metric in (["impact", "runs"] if fmt == "T20" else ["runs"]):
        try:
            snap = create_snapshot(db, "query", {**base, "sort_by": metric}, created_by="draft_notes")
        except SnapshotError as exc:
            logger.info("no venue chart: %s", exc)
            return None
        rows = (snap.get("data") or {}).get("rows") or []
        if len([r for r in rows if isinstance(r.get(metric), (int, float))]) >= 3:
            label = "Impact" if metric == "impact" else "runs"
            return {"id": snap["id"], "lead": f"The leading batters at {_ground(fixture['venue'])} since {start.year}, by {label}:"}
    return None


def draft_preview(db: Session, fixture: Dict[str, Any], dry_run: bool = False) -> Optional[Dict[str, Any]]:
    built = _preview_facts(db, fixture)
    scored = [f for f in built["facts"] if not f["fixed"]]
    if len(scored) < MIN_PREVIEW_FACTS:
        logger.info("preview too thin (%s facts): %s v %s", len(scored), fixture["team1"], fixture["team2"])
        return None
    chart = None if dry_run else _venue_chart(db, fixture, built["start"])
    known = [{"facts": [f["text"] for f in built["facts"]]}]
    draft = compose_preview(fixture, built["sections"], built.get("headline"), known, chart)
    if dry_run:
        return draft
    return _save(db, draft, kind="preview", match_id=str(fixture["match_id"]))


def retire_stale_previews(db: Session) -> int:
    """Preview drafts nobody published before the match are rejected (the match has started)."""
    from database import engine

    with engine.begin() as conn:
        return conn.execute(text("""
            UPDATE notes n SET status = 'rejected', updated_at = now()
            WHERE n.kind = 'preview' AND n.status = 'draft' AND n.author_id = :bot
              AND (n.created_at < now() - interval '2 days' OR EXISTS (SELECT 1 FROM matches m WHERE m.id = n.match_id))
        """), {"bot": bot_author_id(db)}).rowcount


# ------------------------------------------------------------------------------------- packs

def note_from_pack(db: Session, pack_id: int) -> Dict[str, Any]:
    """"Make note" in the Social queue: a short analysis draft from one content pack, so the
    pack's first-comment link can land on a real post. Signed by the bot (its facts are code-written);
    the admin edits and publishes it like any draft."""
    from services.notes import NoteError

    pack = db.execute(text("""
        SELECT p.id, p.match_id, p.title, p.facts, p.snapshot_id, m.team1, m.team2, m.competition, m.date
        FROM content_packs p LEFT JOIN matches m ON m.id = p.match_id WHERE p.id = :id
    """), {"id": pack_id}).mappings().first()
    if not pack:
        raise NoteError("Pack not found.")
    existing = db.execute(text("SELECT id FROM notes WHERE pack_id = :id ORDER BY id LIMIT 1"), {"id": pack_id}).first()
    if existing:
        from services.notes import get_note

        return get_note(db, existing[0])
    facts = pack["facts"] or {}
    method = (facts.get("method") or "").strip()
    bullets = (facts.get("numbers") or {}).get("bullets") or [] if facts.get("kind") == "win_prob" else []
    if bullets:
        # The series post's method is an intro followed by the recap bullets: list them.
        method = method.replace(" ".join(bullets), "").strip()
    parts = [x for x in [method, "\n".join(f"- {b}" for b in bullets)] if x]
    if pack["snapshot_id"]:
        parts.append(chart_fence(pack["snapshot_id"]))
    if pack["match_id"]:
        parts.append(f"[Full scorecard](/scorecard/{pack['match_id']})")
    where = ", ".join(x for x in [pack["competition"], _long_date(pack["date"]) if pack["date"] else None] if x)
    dek = f"{pack['team1']} v {pack['team2']}" + (f" · {where}" if where else "") if pack["team1"] else None
    return create_note(db, title=pack["title"], dek=dek, body_md="\n\n".join(parts) + "\n", kind="analysis",
                       author_id=bot_author_id(db), pack_id=pack_id)


# ------------------------------------------------------------------------------------- shared

def _save(db: Session, draft: Dict[str, Any], kind: str, match_id: str) -> Optional[Dict[str, Any]]:
    try:
        return create_note(db, title=draft["title"], dek=draft["dek"], body_md=draft["body_md"], kind=kind,
                           author_id=bot_author_id(db), match_id=match_id)
    except IntegrityError:
        return None  # another run drafted this match first


def run(db: Session, days: int = 10, match_ids: Optional[List[str]] = None, recaps: bool = True,
        previews: bool = True, dry_run: bool = False) -> Dict[str, Any]:
    summary: Dict[str, Any] = {"recaps": [], "previews": [], "skipped": [], "errors": [], "retired": 0}
    if recaps:
        for match in recap_candidates(db, days, match_ids):
            label = f"{match['team1']} v {match['team2']} ({match['id']})"
            try:
                note = draft_recap(db, match, dry_run)
                (summary["recaps"] if note else summary["skipped"]).append(note or f"recap {label}")
            except Exception as exc:
                db.rollback()
                logger.exception("recap draft failed for %s", label)
                summary["errors"].append(f"recap {label}: {exc!r}")
    if previews and not match_ids:
        from services.fixture_scraper import fetch_upcoming_fixtures

        for fixture in preview_candidates(db, fetch_upcoming_fixtures(20)):
            label = f"{fixture['team1']} v {fixture['team2']} ({fixture['match_id']})"
            try:
                note = draft_preview(db, fixture, dry_run)
                (summary["previews"] if note else summary["skipped"]).append(note or f"preview {label}")
            except Exception as exc:
                db.rollback()
                logger.exception("preview draft failed for %s", label)
                summary["errors"].append(f"preview {label}: {exc!r}")
        if not dry_run:
            summary["retired"] = retire_stale_previews(db)
    return summary
