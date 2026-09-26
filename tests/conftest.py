import os

# Usage logging writes from a background thread to whatever DATABASE_URL points at -- in this
# repo .env is production. Tests must never add rows there.
os.environ["USAGE_LOGGING"] = "0"

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
