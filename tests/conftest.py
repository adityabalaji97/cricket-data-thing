import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from main import app
from database import get_session


@pytest.fixture
def client():
    """TestClient with mocked DB session."""
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_db():
    """Standalone mock DB session for service-level tests."""
    return MagicMock()
