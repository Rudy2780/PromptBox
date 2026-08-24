"""
Tests for POST /api/execute endpoint.
All provider calls are mocked — no real API keys required.
"""
import pytest
from unittest.mock import patch

from app.providers.exceptions import ProviderAuthError

# `authed_client` comes from conftest.py. /api/execute now requires
# authentication, so these tests act as a signed-in user.

VALID_OPENAI_PAYLOAD = {
    "prompt": "Say hello",
    "model": "gpt-4o",
    "api_key": "sk-test-key",
}

VALID_GEMINI_PAYLOAD = {
    "prompt": "Say hello",
    "model": "gemini-2.5-flash",
    "api_key": "gemini-test-key",
}


# ---------------------------------------------------------------------------
# 1. Valid inputs → 200 with model, response_text, latency
# ---------------------------------------------------------------------------

def test_execute_valid_openai(authed_client):
    with patch("app.api.routes_execute.OpenAIProvider") as MockProvider:
        instance = MockProvider.return_value
        instance.run_prompt.return_value = ("Hello from OpenAI!", 0.42)

        response = authed_client.post("/api/execute", json=VALID_OPENAI_PAYLOAD)

    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "gpt-4o"
    assert data["response_text"] == "Hello from OpenAI!"
    assert data["latency"] == pytest.approx(0.42)


def test_execute_valid_gemini(authed_client):
    with patch("app.api.routes_execute.GeminiProvider") as MockProvider:
        instance = MockProvider.return_value
        instance.run_prompt.return_value = ("Hello from Gemini!", 0.75)

        response = authed_client.post("/api/execute", json=VALID_GEMINI_PAYLOAD)

    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "gemini-2.5-flash"
    assert data["response_text"] == "Hello from Gemini!"
    assert data["latency"] == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# 2. Empty prompt → 400
# ---------------------------------------------------------------------------

def test_execute_empty_prompt(authed_client):
    payload = {**VALID_OPENAI_PAYLOAD, "prompt": ""}
    response = authed_client.post("/api/execute", json=payload)

    assert response.status_code == 400
    assert "prompt" in response.json()["detail"].lower()


def test_execute_whitespace_only_prompt(authed_client):
    payload = {**VALID_OPENAI_PAYLOAD, "prompt": "   "}
    response = authed_client.post("/api/execute", json=payload)

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 3. Missing / empty API key → 400
# ---------------------------------------------------------------------------

def test_execute_empty_api_key(authed_client):
    payload = {**VALID_OPENAI_PAYLOAD, "api_key": ""}
    response = authed_client.post("/api/execute", json=payload)

    assert response.status_code == 400
    assert "api key" in response.json()["detail"].lower()


def test_execute_whitespace_only_api_key(authed_client):
    payload = {**VALID_OPENAI_PAYLOAD, "api_key": "   "}
    response = authed_client.post("/api/execute", json=payload)

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 4. Invalid API key — provider raises ProviderAuthError → 401
# ---------------------------------------------------------------------------

def test_execute_invalid_openai_api_key(authed_client):
    with patch("app.api.routes_execute.OpenAIProvider") as MockProvider:
        instance = MockProvider.return_value
        instance.run_prompt.side_effect = ProviderAuthError("Invalid OpenAI API key")

        payload = {**VALID_OPENAI_PAYLOAD, "api_key": "sk-invalid"}
        response = authed_client.post("/api/execute", json=payload)

    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_execute_invalid_gemini_api_key(authed_client):
    with patch("app.api.routes_execute.GeminiProvider") as MockProvider:
        instance = MockProvider.return_value
        instance.run_prompt.side_effect = ProviderAuthError("Invalid Gemini API key")

        payload = {**VALID_GEMINI_PAYLOAD, "api_key": "bad-key"}
        response = authed_client.post("/api/execute", json=payload)

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# 5. Unsupported model → 400
# ---------------------------------------------------------------------------

def test_execute_unsupported_model(authed_client):
    payload = {**VALID_OPENAI_PAYLOAD, "model": "claude-3-opus"}
    response = authed_client.post("/api/execute", json=payload)

    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


def test_execute_another_unsupported_model(authed_client):
    payload = {**VALID_OPENAI_PAYLOAD, "model": "llama-3"}
    response = authed_client.post("/api/execute", json=payload)

    assert response.status_code == 400
