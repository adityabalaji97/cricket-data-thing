"""Usage endpoints: event validation and the admin report's access control (mocked DB)."""

import services.usage_log as usage_log


def test_events_accepts_a_valid_batch_and_drops_bad_names(client, monkeypatch):
    captured = []
    monkeypatch.setattr("routers.usage.enqueue", lambda kind, row: captured.append((kind, row)))
    r = client.post("/events", json={
        "anon_id": "anon-12345678",
        "events": [{"event": "page_view", "path": "/query"}, {"event": "Not Valid!"}],
    })
    assert r.status_code == 204
    assert [row["event"] for _, row in captured] == ["page_view"]


def test_events_rejects_empty_or_oversized_batches(client):
    assert client.post("/events", json={"anon_id": "anon-12345678", "events": []}).status_code == 422
    too_many = [{"event": "page_view"}] * 51
    assert client.post("/events", json={"anon_id": "anon-12345678", "events": too_many}).status_code == 422


def test_admin_usage_is_hidden_without_a_configured_token(client, monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    assert client.get("/admin/usage").status_code == 404


def test_admin_usage_needs_the_right_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret")
    assert client.get("/admin/usage", headers={"x-admin-token": "wrong"}).status_code == 403


def test_caller_hash_is_stable_and_short():
    assert usage_log.caller_hash("203.0.113.9, 10.0.0.1") == usage_log.caller_hash("203.0.113.9")
    assert len(usage_log.caller_hash("203.0.113.9")) == 16
    assert usage_log.caller_hash(None) is None
