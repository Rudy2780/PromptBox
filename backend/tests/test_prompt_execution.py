"""Tests for POST /api/prompt.

These were originally written against POST /api/execute, which has been
removed: the dashboard always sent a `models` array, so the single-model
endpoint was unreachable from the running app and /api/prompt already handles
a one-element list. The validation and error-mapping coverage is preserved
here against the endpoint that is actually used.

All provider calls are mocked -- no real API keys required.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.providers.exceptions import ProviderAuthError, ProviderError

from contextlib import contextmanager


@contextmanager
def mock_provider(name, *, returns=None, raises=None):
    """Swap one provider adapter in the registry.

    Patches app.providers.registry.PROVIDER_CLASSES rather than a name imported
    into the route module: the registry is now the single place adapters are
    resolved, so it is the only seam that needs mocking.
    """
    provider_cls = MagicMock()
    if raises is not None:
        provider_cls.return_value.run_prompt.side_effect = raises
    else:
        provider_cls.return_value.run_prompt.return_value = returns
    with patch.dict("app.providers.registry.PROVIDER_CLASSES", {name: provider_cls}):
        yield provider_cls



OPENAI_PAYLOAD = {
    "prompt": "Say hello",
    "models": ["gpt-4o"],
    "api_keys": {"openai": "sk-test-key"},
}

GEMINI_PAYLOAD = {
    "prompt": "Say hello",
    "models": ["gemini-2.5-flash"],
    "api_keys": {"gemini": "gemini-test-key"},
}


# ---------------------------------------------------------------------------
# 1. Valid inputs -> 200 with model, response_text, latency
# ---------------------------------------------------------------------------

def test_single_openai_model(authed_client):
    with mock_provider("openai", returns=("Hello from OpenAI!", 0.42)):
        response = authed_client.post("/api/prompt", json=OPENAI_PAYLOAD)

    assert response.status_code == 200
    results = response.json()["responses"]
    assert len(results) == 1
    assert results[0]["model"] == "gpt-4o"
    assert results[0]["response_text"] == "Hello from OpenAI!"
    assert results[0]["latency"] == pytest.approx(0.42)


def test_single_gemini_model(authed_client):
    with mock_provider("gemini", returns=("Hello from Gemini!", 0.75)):
        response = authed_client.post("/api/prompt", json=GEMINI_PAYLOAD)

    assert response.status_code == 200
    results = response.json()["responses"]
    assert results[0]["model"] == "gemini-2.5-flash"
    assert results[0]["response_text"] == "Hello from Gemini!"
    assert results[0]["latency"] == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# 2. Empty prompt -> 400
# ---------------------------------------------------------------------------

def test_empty_prompt(authed_client):
    response = authed_client.post("/api/prompt", json={**OPENAI_PAYLOAD, "prompt": ""})
    assert response.status_code == 400
    assert "prompt" in response.json()["detail"].lower()


def test_whitespace_only_prompt(authed_client):
    response = authed_client.post("/api/prompt", json={**OPENAI_PAYLOAD, "prompt": "   "})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 3. Missing / empty API key -> 400
# ---------------------------------------------------------------------------

def test_empty_api_key(authed_client):
    payload = {**OPENAI_PAYLOAD, "api_keys": {"openai": ""}}
    response = authed_client.post("/api/prompt", json=payload)
    assert response.status_code == 400
    assert "api key" in response.json()["detail"].lower()


def test_whitespace_only_api_key(authed_client):
    payload = {**OPENAI_PAYLOAD, "api_keys": {"openai": "   "}}
    response = authed_client.post("/api/prompt", json=payload)
    assert response.status_code == 400


def test_missing_key_for_requested_provider(authed_client):
    """A key for one provider does not authorise a model from another."""
    payload = {
        "prompt": "Say hello",
        "models": ["gemini-2.5-flash"],
        "api_keys": {"openai": "sk-test-key"},
    }
    response = authed_client.post("/api/prompt", json=payload)
    assert response.status_code == 400
    assert "gemini" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 4. Provider raises ProviderAuthError -> 401, ProviderError -> 502
# ---------------------------------------------------------------------------

def test_invalid_openai_api_key(authed_client):
    with mock_provider("openai", raises=ProviderAuthError("Invalid OpenAI API key")):
        payload = {**OPENAI_PAYLOAD, "api_keys": {"openai": "sk-invalid"}}
        response = authed_client.post("/api/prompt", json=payload)

    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_invalid_gemini_api_key(authed_client):
    with mock_provider("gemini", raises=ProviderAuthError("Invalid Gemini API key")):
        payload = {**GEMINI_PAYLOAD, "api_keys": {"gemini": "bad-key"}}
        response = authed_client.post("/api/prompt", json=payload)

    assert response.status_code == 401


def test_upstream_provider_failure_is_502(authed_client):
    with mock_provider("openai", raises=ProviderError("OpenAI provider error: rate limit")):
        response = authed_client.post("/api/prompt", json=OPENAI_PAYLOAD)

    assert response.status_code == 502


# ---------------------------------------------------------------------------
# 5. Unsupported model -> 400
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("model", ["claude-3-opus", "llama-3"])
def test_unsupported_model(authed_client, model):
    payload = {**OPENAI_PAYLOAD, "models": [model]}
    response = authed_client.post("/api/prompt", json=payload)
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()
