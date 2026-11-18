import os

# Usage logging writes from a background thread to whatever DATABASE_URL points at -- in this
# repo .env is production. Tests must never add rows there.
os.environ["USAGE_LOGGING"] = "0"
# Tests must never read or write the production query cache.
os.environ["QUERY_CACHE"] = "0"

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from database import get_session


@pytest.fixture
def client():
    """TestClient with mocked DB session."""
    from main import app

    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_db():
    """Standalone mock DB session for service-level tests."""
    return MagicMock()


@pytest.fixture(autouse=True)
def no_paid_reel_calls(monkeypatch):
    """Motion Reel tests never voice, transcribe, open a browser or call a model (MOTION_REEL_PLAN.md M4-M6): the live
    functions raise if a test reaches them. A test that needs one passes or patches its own fake, which wins."""
    import sys

    def refuse(*_a, **_k):
        raise AssertionError("a test reached a paid or live call (voice, transcription, model or recorder)")
    if "services.ig_reel_v2" in sys.modules:
        r = sys.modules["services.ig_reel_v2"]
        for name in ("record_motion", "_client", "record"):  # voice_lines goes through _client (its own tests fake that)
            monkeypatch.setattr(r, name, refuse)
    if "services.reel_timing" in sys.modules:
        monkeypatch.setattr(sys.modules["services.reel_timing"], "transcribe_words", refuse)
