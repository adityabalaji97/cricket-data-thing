"""
Hindsight Notes: bot and human posts with embedded charts (migrations 009/010, routers/notes.py).

A note's body is markdown. Charts are fenced blocks that name a chart snapshot:

    ```hindsight
    chart: Ab12Cd34E
    ```

The site renders each fence as the /embed/* iframe for that snapshot, and crawlers get the
snapshot's table as HTML (api/meta.mjs), so the numbers in a published note never change.

Workflow: everything is created as a draft. Only the admin publishes or rejects. Friends hold a
personal token (sha256-hashed in note_authors.token_hash) that can create and edit their own
drafts and nothing else.
"""
from __future__ import annotations

import hashlib
import re
import secrets
import unicodedata
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit

from sqlalchemy import text
from sqlalchemy.orm import Session

KINDS = ("recap", "preview", "analysis", "article")
STATUSES = ("draft", "published", "rejected")
AUTHOR_KINDS = ("article", "analysis")      # what a friend may write

CHART_FENCE = re.compile(r"^```hindsight[ \t]*\n[ \t]*chart:[ \t]*([A-Za-z0-9]{6,16})[ \t]*\n```[ \t]*$", re.M)
SNAPSHOT_ID = re.compile(r"^[A-Za-z0-9]{6,16}$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# Which /embed/* renderer shows a snapshot kind.
EMBED_KIND = {"query": "q", "ranking": "q", "win_prob": "wp", "recap": "recap"}
SITE_HOSTS = {"hindsightcricket.com", "www.hindsightcricket.com", "hindsight2020.vercel.app", "localhost", "127.0.0.1"}


class NoteError(ValueError):
    pass


# --------------------------------------------------------------------------------------------
# Markdown helpers
# --------------------------------------------------------------------------------------------

def chart_fence(snapshot_id: str) -> str:
    return f"```hindsight\nchart: {snapshot_id}\n```"


def chart_ids(body_md: str) -> List[str]:
    """Snapshot ids referenced by chart fences, in order, without repeats."""
    seen: List[str] = []
    for match in CHART_FENCE.finditer(body_md or ""):
        if match.group(1) not in seen:
            seen.append(match.group(1))
    return seen


def slugify(title: str, max_len: int = 70) -> str:
    ascii_ = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode()
    words = re.findall(r"[a-z0-9]+", ascii_.lower())
    slug = ""
    for word in words:
        if len(slug) + len(word) + 1 > max_len:
            break
        slug = f"{slug}-{word}" if slug else word
    return slug or "note"


def unique_slug(db: Session, base: str, note_id: Optional[int] = None) -> str:
    taken = {r[0] for r in db.execute(
        text("SELECT slug FROM notes WHERE (slug = :b OR slug LIKE :like) AND id IS DISTINCT FROM :id"),
        {"b": base, "like": f"{base}-%", "id": note_id},
    )}
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


# --------------------------------------------------------------------------------------------
# "Insert chart": a pasted Hindsight URL becomes a snapshot request
# --------------------------------------------------------------------------------------------

def _format_from_slug(slug: str) -> Dict[str, str]:
    from format_config import all_formats

    for spec in all_formats():
        if spec.slug == slug:
            return {"format": spec.format, "gender": spec.gender}
    return {}


def snapshot_request_from_url(url: str, kind: Optional[str] = None) -> Dict[str, Any]:
    """What to snapshot for a pasted site URL.

    Returns one of
      {"existing": id}                                  an /embed/* or /img/* link
      {"kind": "win_prob"|"recap", "params": {...}}     a /scorecard/<id> link
      {"kind": "query", "query_string": "..."}          a /query?... link (site params -> API params)
    """
    parts = urlsplit((url or "").strip())
    if parts.netloc and parts.hostname not in SITE_HOSTS:
        raise NoteError("That isn't a Hindsight link.")
    path = parts.path.rstrip("/") or "/"

    embed = re.match(r"^/(?:embed/(?:q|wp|recap)/([A-Za-z0-9]{6,16})|img/([A-Za-z0-9]{6,16})\.png)$", path)
    if embed:
        return {"existing": embed.group(1) or embed.group(2)}

    scorecard = re.match(r"^/scorecard/([A-Za-z0-9_-]+)$", path)
    if scorecard:
        if kind not in (None, "win_prob", "recap"):
            raise NoteError("A scorecard link makes a win-probability or recap chart.")
        return {"kind": kind or "win_prob", "params": {"match_id": scorecard.group(1)}}

    if path == "/query":
        pairs = [(k, v) for k, v in parse_qsl(parts.query) if k not in ("utm_source", "utm_campaign", "utm_medium")]
        if any(k == "nl" for k, _ in pairs):
            raise NoteError("That link is a plain-English search. Open it, let it run, then copy the URL again.")
        out: List[Tuple[str, str]] = []
        for key, value in pairs:
            if key == "fmt":
                out += list(_format_from_slug(value).items())
            elif key == "league":
                out.append(("leagues", value))
            else:
                out.append((key, value))
        if not any(k == "group_by" for k, _ in out):
            raise NoteError("A chart needs a grouped query (pick at least one Group by in the query builder).")
        return {"kind": "query", "query_string": urlencode(out)}

    raise NoteError("Paste a query builder, scorecard, embed or image link from Hindsight.")


def chart_from_url(db: Session, url: str, kind: Optional[str] = None, created_by: str = "notes") -> Dict[str, Any]:
    """Create (or find) the snapshot a pasted URL describes; returns {id, kind, title, fence}."""
    from services.snapshots import SnapshotError, create_snapshot, get_snapshot, params_from_query_string

    request = snapshot_request_from_url(url, kind)
    try:
        if "existing" in request:
            snap = get_snapshot(db, request["existing"])
            if not snap:
                raise NoteError("No chart with that id.")
        elif request["kind"] == "query":
            snap = create_snapshot(db, "query", params_from_query_string(request["query_string"]), created_by=created_by)
        else:
            snap = create_snapshot(db, request["kind"], request["params"], created_by=created_by)
    except SnapshotError as exc:
        raise NoteError(str(exc))
    return {"id": snap["id"], "kind": snap["kind"], "title": snap.get("title"), "fence": chart_fence(snap["id"])}


# --------------------------------------------------------------------------------------------
# Authors
# --------------------------------------------------------------------------------------------

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> str:
    return "hn_" + secrets.token_urlsafe(24)


def author_for_token(db: Session, token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not token or len(token) > 200:
        return None
    row = db.execute(text(
        "SELECT id, slug, name, bio, is_bot FROM note_authors WHERE token_hash = :h AND NOT is_bot"
    ), {"h": hash_token(token)}).mappings().first()
    return dict(row) if row else None


def owner_author_id(db: Session) -> int:
    """The admin's own byline (migration 010), else the first human author."""
    row = db.execute(text(
        "SELECT id FROM note_authors WHERE NOT is_bot ORDER BY (slug = 'aditya') DESC, id LIMIT 1"
    )).first()
    if not row:
        raise NoteError("No human author exists; run migration 010.")
    return row[0]


def bot_author_id(db: Session) -> int:
    return db.execute(text("SELECT id FROM note_authors WHERE slug = 'hindsight-bot'")).scalar_one()


def list_authors(db: Session) -> List[Dict[str, Any]]:
    rows = db.execute(text("""
        SELECT a.id, a.slug, a.name, a.bio, a.is_bot, a.token_hash IS NOT NULL AS has_token, a.created_at,
               COUNT(n.id) FILTER (WHERE n.status = 'published') AS published,
               COUNT(n.id) FILTER (WHERE n.status = 'draft') AS drafts
        FROM note_authors a LEFT JOIN notes n ON n.author_id = a.id
        GROUP BY a.id ORDER BY a.is_bot DESC, a.id
    """)).mappings()
    return [dict(r) for r in rows]


def create_author(name: str, bio: Optional[str] = None, slug: Optional[str] = None) -> Dict[str, Any]:
    """Add a friend. The token is returned once; only its hash is stored."""
    from database import engine

    name = (name or "").strip()
    if not name:
        raise NoteError("A name is required.")
    slug = slug or slugify(name, 40)
    if not SLUG.match(slug):
        raise NoteError("Slugs are lowercase letters, digits and hyphens.")
    token = new_token()
    with engine.begin() as conn:
        exists = conn.execute(text("SELECT 1 FROM note_authors WHERE slug = :s"), {"s": slug}).first()
        if exists:
            raise NoteError(f"An author with the slug '{slug}' already exists.")
        row = conn.execute(text("""
            INSERT INTO note_authors (slug, name, bio, is_bot, token_hash)
            VALUES (:slug, :name, :bio, FALSE, :h) RETURNING id, slug, name, bio
        """), {"slug": slug, "name": name, "bio": (bio or "").strip() or None, "h": hash_token(token)}).mappings().first()
    return {**dict(row), "token": token}


def rotate_token(author_id: int) -> str:
    from database import engine

    token = new_token()
    with engine.begin() as conn:
        updated = conn.execute(text(
            "UPDATE note_authors SET token_hash = :h WHERE id = :id AND NOT is_bot"
        ), {"h": hash_token(token), "id": author_id}).rowcount
    if not updated:
        raise NoteError("No such author.")
    return token


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------

_NOTE_COLUMNS = """
    n.id, n.slug, n.title, n.dek, n.kind, n.status, n.match_id, n.pack_id, n.created_at, n.updated_at,
    n.published_at, a.slug AS author_slug, a.name AS author_name, a.bio AS author_bio, a.is_bot AS author_is_bot
"""


def _shape(row: Dict[str, Any], with_body: bool) -> Dict[str, Any]:
    out = {k: row[k] for k in ("id", "slug", "title", "dek", "kind", "status", "match_id", "pack_id",
                               "created_at", "updated_at", "published_at")}
    out["author"] = {"slug": row["author_slug"], "name": row["author_name"], "bio": row["author_bio"],
                     "is_bot": row["author_is_bot"]}
    ids = chart_ids(row.get("body_md") or "")
    out["cover"] = ids[0] if ids else None
    if with_body:
        out["body_md"] = row["body_md"]
    return out


def charts_for(db: Session, ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Snapshot data for a note's fences, keyed by id (missing ids are left out)."""
    if not ids:
        return {}
    rows = db.execute(text(
        "SELECT id, kind, title, data, created_at FROM chart_snapshots WHERE id = ANY(:ids)"
    ), {"ids": ids}).mappings()
    return {r["id"]: {**dict(r), "embed": EMBED_KIND.get(r["kind"], "q")} for r in rows}


def list_notes(db: Session, status: Optional[str] = "published", kind: Optional[str] = None,
               author: Optional[str] = None, author_id: Optional[int] = None, limit: int = 20,
               offset: int = 0) -> List[Dict[str, Any]]:
    where, params = [], {"limit": max(1, min(limit, 100)), "offset": max(0, offset)}
    if status:
        where.append("n.status = :status")
        params["status"] = status
    if kind:
        where.append("n.kind = :kind")
        params["kind"] = kind
    if author:
        where.append("a.slug = :author")
        params["author"] = author
    if author_id is not None:
        where.append("n.author_id = :author_id")
        params["author_id"] = author_id
    order = "n.published_at DESC NULLS LAST, n.id DESC" if status == "published" else "n.updated_at DESC, n.id DESC"
    rows = db.execute(text(f"""
        SELECT {_NOTE_COLUMNS}, n.body_md
        FROM notes n JOIN note_authors a ON a.id = n.author_id
        {'WHERE ' + ' AND '.join(where) if where else ''}
        ORDER BY {order} LIMIT :limit OFFSET :offset
    """), params).mappings()
    return [_shape(r, with_body=False) for r in rows]


def _get(db: Session, where: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    row = db.execute(text(f"""
        SELECT {_NOTE_COLUMNS}, n.body_md, n.author_id
        FROM notes n JOIN note_authors a ON a.id = n.author_id WHERE {where}
    """), params).mappings().first()
    if not row:
        return None
    note = _shape(row, with_body=True)
    note["author_id"] = row["author_id"]
    note["charts"] = charts_for(db, chart_ids(note["body_md"]))
    return note


def get_published(db: Session, slug: str) -> Optional[Dict[str, Any]]:
    note = _get(db, "n.slug = :slug AND n.status = 'published'", {"slug": slug})
    if note:
        note.pop("author_id", None)
    return note


def get_note(db: Session, note_id: int) -> Optional[Dict[str, Any]]:
    return _get(db, "n.id = :id", {"id": note_id})


def _check_body(db: Session, body_md: str) -> None:
    ids = chart_ids(body_md)
    if ids:
        found = set(charts_for(db, ids))
        missing = [i for i in ids if i not in found]
        if missing:
            raise NoteError(f"Unknown chart id(s): {', '.join(missing)}")


def create_note(db: Session, *, title: str, author_id: int, body_md: str = "", dek: Optional[str] = None,
                kind: str = "article", match_id: Optional[str] = None, pack_id: Optional[int] = None,
                slug: Optional[str] = None) -> Dict[str, Any]:
    """Create a draft. Returns the full note."""
    from database import engine

    title = (title or "").strip()
    if not title:
        raise NoteError("A title is required.")
    if kind not in KINDS:
        raise NoteError(f"kind must be one of {KINDS}")
    if slug is not None and not SLUG.match(slug):
        raise NoteError("Slugs are lowercase letters, digits and hyphens.")
    _check_body(db, body_md)
    final_slug = unique_slug(db, slug or slugify(title))
    with engine.begin() as conn:
        note_id = conn.execute(text("""
            INSERT INTO notes (slug, title, dek, body_md, kind, author_id, status, match_id, pack_id)
            VALUES (:slug, :title, :dek, :body, :kind, :author, 'draft', :match_id, :pack_id) RETURNING id
        """), {"slug": final_slug, "title": title, "dek": (dek or "").strip() or None, "body": body_md or "",
               "kind": kind, "author": author_id, "match_id": match_id, "pack_id": pack_id}).scalar_one()
    return get_note(db, note_id)


def update_note(db: Session, note_id: int, changes: Dict[str, Any]) -> Dict[str, Any]:
    """Edit title / dek / body / slug / kind. A draft's slug follows its title until published."""
    from database import engine

    note = get_note(db, note_id)
    if not note:
        raise NoteError("Note not found.")
    sets, params = [], {"id": note_id}
    if changes.get("title") is not None:
        title = changes["title"].strip()
        if not title:
            raise NoteError("A title is required.")
        sets.append("title = :title")
        params["title"] = title
        if note["status"] != "published" and changes.get("slug") is None:
            changes["slug"] = slugify(title)
    if changes.get("slug") is not None:
        if not SLUG.match(changes["slug"]):
            raise NoteError("Slugs are lowercase letters, digits and hyphens.")
        if changes["slug"] != note["slug"]:
            sets.append("slug = :slug")
            params["slug"] = unique_slug(db, changes["slug"], note_id)
    if changes.get("dek") is not None:
        sets.append("dek = :dek")
        params["dek"] = changes["dek"].strip() or None
    if changes.get("body_md") is not None:
        _check_body(db, changes["body_md"])
        sets.append("body_md = :body")
        params["body"] = changes["body_md"]
    if changes.get("kind") is not None:
        if changes["kind"] not in KINDS:
            raise NoteError(f"kind must be one of {KINDS}")
        sets.append("kind = :kind")
        params["kind"] = changes["kind"]
    if sets:
        with engine.begin() as conn:
            conn.execute(text(f"UPDATE notes SET {', '.join(sets)}, updated_at = now() WHERE id = :id"), params)
    return get_note(db, note_id)


def set_status(db: Session, note_id: int, status: str) -> Dict[str, Any]:
    """Publish (stamps published_at the first time), reject, or send back to draft."""
    from database import engine

    if status not in STATUSES:
        raise NoteError(f"status must be one of {STATUSES}")
    note = get_note(db, note_id)
    if not note:
        raise NoteError("Note not found.")
    if status == "published":
        if not note["body_md"].strip():
            raise NoteError("An empty note can't be published.")
        _check_body(db, note["body_md"])
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE notes SET status = :status, updated_at = now(),
                published_at = CASE WHEN :status = 'published' THEN COALESCE(published_at, now()) ELSE published_at END
            WHERE id = :id
        """), {"status": status, "id": note_id})
    return get_note(db, note_id)


def sitemap_entries(db: Session) -> List[Dict[str, Any]]:
    rows = db.execute(text("""
        SELECT slug, GREATEST(updated_at, published_at) AS lastmod FROM notes
        WHERE status = 'published' ORDER BY published_at DESC LIMIT 5000
    """)).fetchall()
    return [{"slug": r.slug, "lastmod": r.lastmod.date().isoformat() if r.lastmod else None} for r in rows]
