"""Notes: fences, slugs, pasted-URL charts, auth, and the draft -> publish workflow.

The workflow tests write real rows, so they run only against a local database:
    DATABASE_URL=postgresql://localhost:5432/hindsight_local pytest tests/test_notes.py
(.env is production; without the export those tests skip.)
"""
import uuid

import pytest
from fastapi.testclient import TestClient

import database
from services import notes as svc

LOCAL_DB = any(h in database.DATABASE_URL for h in ("@localhost", "//localhost", "127.0.0.1"))


# ---------------------------------------------------------------------------------- pure

def test_chart_fences_parse_in_order_without_repeats():
    body = "Intro\n\n" + svc.chart_fence("Abc123XYZ") + "\n\nMore\n\n```hindsight\nchart:  Zzz999\n```\n\n" + svc.chart_fence("Abc123XYZ")
    assert svc.chart_ids(body) == ["Abc123XYZ", "Zzz999"]


def test_other_code_fences_and_inline_mentions_are_not_charts():
    body = "```python\nchart: Abc123XYZ\n```\n\nSee `chart: Zzz999` and ```hindsight chart: Qqq111```"
    assert svc.chart_ids(body) == []


def test_slugify():
    assert svc.slugify("Gill & Kohli: 92% control — best ODI stand since 2015!") == "gill-kohli-92-control-best-odi-stand-since-2015"
    assert svc.slugify("Ünïcödé  title") == "unicode-title"
    assert svc.slugify("???") == "note"
    assert len(svc.slugify("word " * 40)) <= 70


@pytest.mark.parametrize("url,expected", [
    ("https://hindsightcricket.com/embed/q/Abc123XYZ", {"existing": "Abc123XYZ"}),
    ("https://hindsightcricket.com/img/Abc123XYZ.png?size=card", {"existing": "Abc123XYZ"}),
    ("https://hindsightcricket.com/scorecard/1491742", {"kind": "win_prob", "params": {"match_id": "1491742"}}),
    ("/scorecard/1491742/", {"kind": "win_prob", "params": {"match_id": "1491742"}}),
])
def test_url_to_snapshot_request(url, expected):
    assert svc.snapshot_request_from_url(url) == expected


def test_scorecard_url_can_ask_for_a_recap():
    assert svc.snapshot_request_from_url("https://hindsightcricket.com/scorecard/1", "recap")["kind"] == "recap"


def test_query_url_maps_site_params_to_api_params():
    req = svc.snapshot_request_from_url(
        "https://hindsightcricket.com/query?fmt=mens-odi&batters=V+Kohli&league=IPL&group_by=year&utm_source=x"
    )
    assert req["kind"] == "query"
    from services.snapshots import params_from_query_string

    params = params_from_query_string(req["query_string"])
    assert params["format"] == "ODI" and params["gender"] == "male"
    assert params["batters"] == ["V Kohli"] and params["leagues"] == ["IPL"] and params["group_by"] == ["year"]
    assert "utm_source" not in params


@pytest.mark.parametrize("url", [
    "https://evil.example.com/query?group_by=batter",
    "https://hindsightcricket.com/player?name=V%20Kohli",
    "https://hindsightcricket.com/query?nl=kohli+in+2024",
    "https://hindsightcricket.com/query?batters=V+Kohli",
])
def test_bad_urls_are_refused_with_a_reason(url):
    with pytest.raises(svc.NoteError):
        svc.snapshot_request_from_url(url)


def test_token_hash_is_stable_and_not_the_token():
    token = svc.new_token()
    assert token.startswith("hn_") and svc.hash_token(token) == svc.hash_token(token) != token


# ---------------------------------------------------------------------------------- auth (no DB)

def test_admin_queue_needs_the_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret-admin")
    assert client.get("/admin/notes").status_code == 403
    assert client.get("/admin/notes", headers={"X-Admin-Token": "wrong"}).status_code == 403
    assert client.post("/admin/notes/1/publish").status_code == 403
    assert client.post("/admin/authors", json={"name": "X"}).status_code == 403


def test_admin_queue_is_hidden_when_no_admin_token_is_configured(client, monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    assert client.get("/admin/notes", headers={"X-Admin-Token": "anything"}).status_code == 404


def test_author_routes_need_a_token(client):
    assert client.get("/author/me").status_code == 403
    assert client.post("/author/notes", json={"title": "x"}).status_code == 403


# ---------------------------------------------------------------------------------- workflow (local DB)

local_only = pytest.mark.skipif(not LOCAL_DB, reason="writes rows; run with DATABASE_URL pointing at hindsight_local")


@pytest.fixture
def live(monkeypatch):
    """TestClient on the real (local) database, and cleanup of everything the test created."""
    from main import app

    monkeypatch.setenv("ADMIN_TOKEN", "test-admin")
    tag = uuid.uuid4().hex[:8]
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c, tag
    from sqlalchemy import text

    with database.engine.begin() as conn:
        conn.execute(text("DELETE FROM notes WHERE title LIKE :t"), {"t": f"%{tag}%"})
        conn.execute(text("DELETE FROM note_authors WHERE name LIKE :t"), {"t": f"%{tag}%"})


ADMIN = {"X-Admin-Token": "test-admin"}


@local_only
def test_only_published_notes_are_public(live):
    c, tag = live
    note = c.post("/admin/notes", headers=ADMIN, json={"title": f"Draft {tag}", "body_md": "Hello"}).json()
    assert note["status"] == "draft" and note["author"]["slug"] == "aditya"
    assert c.get(f"/notes/{note['slug']}").status_code == 404
    assert note["slug"] not in [n["slug"] for n in c.get("/notes").json()["notes"]]

    published = c.post(f"/admin/notes/{note['id']}/publish", headers=ADMIN).json()
    assert published["status"] == "published" and published["published_at"]
    public = c.get(f"/notes/{note['slug']}").json()
    assert public["body_md"] == "Hello" and "author_id" not in public
    assert note["slug"] in [n["slug"] for n in c.get("/notes").json()["notes"]]

    c.post(f"/admin/notes/{note['id']}/reject", headers=ADMIN)
    assert c.get(f"/notes/{note['slug']}").status_code == 404


@local_only
def test_draft_slug_follows_title_until_published_and_stays_unique(live):
    c, tag = live
    a = c.post("/admin/notes", headers=ADMIN, json={"title": f"Same title {tag}", "body_md": "x"}).json()
    b = c.post("/admin/notes", headers=ADMIN, json={"title": f"Same title {tag}", "body_md": "x"}).json()
    assert b["slug"] == f"{a['slug']}-2"
    renamed = c.patch(f"/admin/notes/{a['id']}", headers=ADMIN, json={"title": f"New title {tag}"}).json()
    assert renamed["slug"] == f"new-title-{tag}"
    c.post(f"/admin/notes/{a['id']}/publish", headers=ADMIN)
    again = c.patch(f"/admin/notes/{a['id']}", headers=ADMIN, json={"title": f"Typo fixed {tag}"}).json()
    assert again["slug"] == f"new-title-{tag}"   # a published URL never moves by itself


@local_only
def test_unknown_chart_ids_are_refused(live):
    c, tag = live
    r = c.post("/admin/notes", headers=ADMIN, json={"title": f"Chart {tag}", "body_md": svc.chart_fence("NoSuch123")})
    assert r.status_code == 400 and "NoSuch123" in r.json()["detail"]


@local_only
def test_author_tokens_only_reach_their_own_drafts(live):
    c, tag = live
    friend = c.post("/admin/authors", headers=ADMIN, json={"name": f"Friend {tag}"}).json()
    other = c.post("/admin/authors", headers=ADMIN, json={"name": f"Other {tag}"}).json()
    me = {"X-Author-Token": friend["token"]}
    assert "token" not in c.get("/admin/authors", headers=ADMIN).json()["authors"][0]

    mine = c.post("/author/notes", headers=me, json={"title": f"Mine {tag}", "body_md": "a"}).json()
    assert mine["status"] == "draft" and mine["author"]["slug"] == friend["slug"]
    assert c.post("/author/notes", headers=me, json={"title": f"Recap {tag}", "kind": "recap"}).status_code == 400

    theirs = c.post("/author/notes", headers={"X-Author-Token": other["token"]}, json={"title": f"Theirs {tag}"}).json()
    assert c.patch(f"/author/notes/{theirs['id']}", headers=me, json={"title": "hijack"}).status_code == 404
    assert c.get(f"/author/notes/{theirs['id']}", headers=me).status_code == 404
    # No publish route for authors; the admin token is something else entirely.
    assert c.post(f"/admin/notes/{mine['id']}/publish", headers={"X-Admin-Token": friend["token"]}).status_code == 403

    assert c.patch(f"/author/notes/{mine['id']}", headers=me, json={"dek": "edited"}).json()["dek"] == "edited"
    c.post(f"/admin/notes/{mine['id']}/publish", headers=ADMIN)
    assert c.patch(f"/author/notes/{mine['id']}", headers=me, json={"dek": "after"}).status_code == 409
    assert [n["id"] for n in c.get("/author/me", headers=me).json()["notes"]] == [mine["id"]]

    rotated = c.post(f"/admin/authors/{friend['id']}/token", headers=ADMIN).json()["token"]
    assert c.get("/author/me", headers=me).status_code == 403
    assert c.get("/author/me", headers={"X-Author-Token": rotated}).status_code == 200
