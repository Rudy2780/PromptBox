"""The interactive API documentation must not be served in production.

/docs offered a Try-It-Out button against every endpoint, which was
particularly unhelpful while three of them were unauthenticated.
"""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app

DOC_PATHS = ["/docs", "/redoc", "/openapi.json"]


@pytest.mark.parametrize("path", DOC_PATHS)
def test_docs_are_not_served_by_default(client, path):
    assert client.get(path).status_code == 404


def test_the_default_is_off(monkeypatch):
    """Fail-closed: an unset or misspelled variable must not publish the docs."""
    monkeypatch.delenv("ENABLE_API_DOCS", raising=False)
    from app.config import _env_flag

    assert _env_flag("ENABLE_API_DOCS", False) is False


@pytest.mark.parametrize("path", DOC_PATHS)
def test_docs_can_be_enabled_deliberately(monkeypatch, path):
    """The switch works, so local development can still opt in."""
    monkeypatch.setattr(settings, "ENABLE_API_DOCS", True)
    enabled_client = TestClient(create_app(), base_url="https://testserver")

    assert enabled_client.get(path).status_code == 200


def test_application_still_serves_its_routes_with_docs_off(client):
    """Disabling docs must not disturb the API itself."""
    assert client.get("/").status_code == 200
    assert client.get("/health/").status_code == 200
