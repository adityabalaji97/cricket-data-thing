import threading

import pytest

from services import jev_client


def test_jev_is_off_inside_suppress(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "x")
    assert jev_client.enabled()
    with jev_client.suppress():
        assert not jev_client.enabled() and jev_client.suppressed()
        assert jev_client.ask({"s": 1}, {"q": {"type": "score"}}) is None  # no network call is attempted
    assert jev_client.enabled() and not jev_client.suppressed()


def test_suppress_is_per_thread(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "x")
    seen = {}
    with jev_client.suppress():
        t = threading.Thread(target=lambda: seen.setdefault("other", jev_client.enabled()))
        t.start(); t.join()
    assert seen["other"] is True  # another request on another thread still has Jev


def test_busy_slots_give_the_busy_message(monkeypatch):
    srv = pytest.importorskip("mcp_server.server")
    monkeypatch.setattr(srv, "_slots", threading.BoundedSemaphore(1))
    monkeypatch.setattr(srv, "MCP_QUEUE_SECONDS", 0.05)
    assert srv._slots.acquire()
    try:
        with pytest.raises(srv._Busy):
            with srv._read_only_session():
                pass
    finally:
        srv._slots.release()
    assert "busy" in srv._user_message(srv._Busy("x"), "fallback").lower()


def test_tracking_columns_are_the_licensed_ones():
    srv = pytest.importorskip("mcp_server.server")
    assert {"line", "length", "shot", "wagon_zone", "control"} <= srv.TAGGED_COLUMNS
    assert srv.MIN_TAGGED_GROUP_BALLS >= 6
