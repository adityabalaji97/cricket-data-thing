"""
Hindsight Notes endpoints (services/notes.py).

  Public       GET  /notes?kind&author&limit&offset     published notes, newest first
               GET  /notes/{slug}                         one published note, its author and chart data
  Admin        GET  /admin/notes?status=                  the queue (X-Admin-Token)
               GET  /admin/notes/{id}                     any note, for preview and editing
               POST /admin/notes                          new article (signed by the owner by default)
               PATCH /admin/notes/{id}                    edit title, dek, body, slug, kind
               POST /admin/notes/{id}/publish | /reject | /draft
               POST /admin/notes/charts                   pasted Hindsight URL -> snapshot + fence
               GET/POST /admin/authors, POST /admin/authors/{id}/token
  Authors      GET  /author/me                            who the token is, and their notes
  (X-Author-Token)  POST /author/notes, PATCH /author/notes/{id}   their own drafts only
               POST /author/charts                        as above
"""
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_session
from routers._auth import require_admin
from services import notes as svc
from services.notes import NoteError

public = APIRouter(prefix="/notes", tags=["notes"])
admin = APIRouter(tags=["admin"], dependencies=[Depends(require_admin)])
author = APIRouter(prefix="/author", tags=["notes"])


def _bad(exc: NoteError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


# ------------------------------------------------------------------------------------ public

@public.get("")
def list_published(response: Response, kind: Optional[str] = None, author: Optional[str] = None,
                   limit: int = 20, offset: int = 0, db: Session = Depends(get_session)):
    response.headers["Cache-Control"] = "public, max-age=60"
    return {"notes": svc.list_notes(db, status="published", kind=kind, author=author, limit=limit, offset=offset)}


@public.get("/{slug}")
def read_published(slug: str, response: Response, db: Session = Depends(get_session)):
    note = svc.get_published(db, slug) if svc.SLUG.match(slug) else None
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    response.headers["Cache-Control"] = "public, max-age=60"
    return note


# ------------------------------------------------------------------------------------- admin

class NoteBody(BaseModel):
    title: str = Field(max_length=300)
    dek: Optional[str] = Field(default=None, max_length=500)
    body_md: str = Field(default="", max_length=60000)
    kind: str = "article"
    slug: Optional[str] = Field(default=None, max_length=90)
    author_slug: Optional[str] = Field(default=None, max_length=60)


class NoteChanges(BaseModel):
    title: Optional[str] = Field(default=None, max_length=300)
    dek: Optional[str] = Field(default=None, max_length=500)
    body_md: Optional[str] = Field(default=None, max_length=60000)
    kind: Optional[str] = None
    slug: Optional[str] = Field(default=None, max_length=90)


class ChartRequest(BaseModel):
    url: str = Field(max_length=4000)
    kind: Optional[str] = None      # scorecard links: win_prob (default) or recap


class AuthorBody(BaseModel):
    name: str = Field(max_length=80)
    bio: Optional[str] = Field(default=None, max_length=300)
    slug: Optional[str] = Field(default=None, max_length=40)


@admin.get("/admin/notes")
def admin_list(status: str = "draft", limit: int = 50, offset: int = 0, db: Session = Depends(get_session)):
    if status != "all" and status not in svc.STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {svc.STATUSES} or all")
    return {"notes": svc.list_notes(db, status=None if status == "all" else status, limit=limit, offset=offset)}


@admin.get("/admin/notes/{note_id}")
def admin_get(note_id: int, db: Session = Depends(get_session)):
    note = svc.get_note(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@admin.post("/admin/notes", status_code=201)
def admin_create(body: NoteBody, db: Session = Depends(get_session)):
    try:
        if body.author_slug:
            match = [a for a in svc.list_authors(db) if a["slug"] == body.author_slug]
            if not match:
                raise NoteError(f"No author '{body.author_slug}'.")
            author_id = match[0]["id"]
        else:
            author_id = svc.owner_author_id(db)
        return svc.create_note(db, title=body.title, dek=body.dek, body_md=body.body_md, kind=body.kind,
                               slug=body.slug, author_id=author_id)
    except NoteError as exc:
        raise _bad(exc)


@admin.patch("/admin/notes/{note_id}")
def admin_update(note_id: int, body: NoteChanges, db: Session = Depends(get_session)):
    try:
        return svc.update_note(db, note_id, body.model_dump(exclude_none=True))
    except NoteError as exc:
        raise _bad(exc)


def _status(note_id: int, status: str, db: Session):
    try:
        return svc.set_status(db, note_id, status)
    except NoteError as exc:
        raise _bad(exc)


@admin.post("/admin/notes/{note_id}/publish")
def admin_publish(note_id: int, db: Session = Depends(get_session)):
    return _status(note_id, "published", db)


@admin.post("/admin/notes/{note_id}/reject")
def admin_reject(note_id: int, db: Session = Depends(get_session)):
    return _status(note_id, "rejected", db)


@admin.post("/admin/notes/{note_id}/draft")
def admin_to_draft(note_id: int, db: Session = Depends(get_session)):
    return _status(note_id, "draft", db)


@admin.post("/admin/notes/charts")
def admin_chart(body: ChartRequest, db: Session = Depends(get_session)):
    try:
        return svc.chart_from_url(db, body.url, body.kind, created_by="admin")
    except NoteError as exc:
        raise _bad(exc)


@admin.get("/admin/authors")
def admin_authors(db: Session = Depends(get_session)):
    return {"authors": svc.list_authors(db)}


@admin.post("/admin/authors", status_code=201)
def admin_add_author(body: AuthorBody):
    """Adds a friend and returns their token ONCE; only its hash is stored."""
    try:
        return svc.create_author(body.name, body.bio, body.slug)
    except NoteError as exc:
        raise _bad(exc)


@admin.post("/admin/authors/{author_id}/token")
def admin_rotate_token(author_id: int):
    try:
        return {"token": svc.rotate_token(author_id)}
    except NoteError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ------------------------------------------------------------------------------------ author

def current_author(x_author_token: Optional[str] = Header(default=None), db: Session = Depends(get_session)):
    found = svc.author_for_token(db, x_author_token)
    if not found:
        raise HTTPException(status_code=403, detail="Forbidden")
    return found


def _own_draft(db: Session, note_id: int, who: dict) -> dict:
    note = svc.get_note(db, note_id)
    # Someone else's note reads as missing, not forbidden: a token can't probe other ids.
    if not note or note["author_id"] != who["id"]:
        raise HTTPException(status_code=404, detail="Note not found")
    if note["status"] != "draft":
        raise HTTPException(status_code=409, detail=f"This note is {note['status']}; only drafts can be edited.")
    return note


@author.get("/me")
def author_me(who: dict = Depends(current_author), db: Session = Depends(get_session)):
    return {"author": who, "notes": svc.list_notes(db, status=None, author_id=who["id"], limit=100)}


@author.get("/notes/{note_id}")
def author_get(note_id: int, who: dict = Depends(current_author), db: Session = Depends(get_session)):
    note = svc.get_note(db, note_id)
    if not note or note["author_id"] != who["id"]:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@author.post("/notes", status_code=201)
def author_create(body: NoteBody, who: dict = Depends(current_author), db: Session = Depends(get_session)):
    if body.kind not in svc.AUTHOR_KINDS:
        raise HTTPException(status_code=400, detail=f"kind must be one of {svc.AUTHOR_KINDS}")
    try:
        return svc.create_note(db, title=body.title, dek=body.dek, body_md=body.body_md, kind=body.kind,
                               slug=body.slug, author_id=who["id"])
    except NoteError as exc:
        raise _bad(exc)


@author.patch("/notes/{note_id}")
def author_update(note_id: int, body: NoteChanges, who: dict = Depends(current_author),
                  db: Session = Depends(get_session)):
    _own_draft(db, note_id, who)
    changes = body.model_dump(exclude_none=True)
    if "kind" in changes and changes["kind"] not in svc.AUTHOR_KINDS:
        raise HTTPException(status_code=400, detail=f"kind must be one of {svc.AUTHOR_KINDS}")
    try:
        return svc.update_note(db, note_id, changes)
    except NoteError as exc:
        raise _bad(exc)


@author.post("/charts")
def author_chart(body: ChartRequest, who: dict = Depends(current_author), db: Session = Depends(get_session)):
    try:
        return svc.chart_from_url(db, body.url, body.kind, created_by=f"author:{who['slug']}")
    except NoteError as exc:
        raise _bad(exc)
