"""
Tests for POST /api/execute endpoint.
All provider calls are mocked — no real API keys required.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.providers.exceptions import ProviderAuthError, ProviderError

client = TestClient(app)

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

def test_execute_valid_openai():
    with patch("app.api.routes_execute.OpenAIProvider") as MockProvider:
        instance = MockProvider.return_value
        instance.run_prompt.return_value = ("Hello from OpenAI!", 0.42)

        response = client.post("/api/execute", json=VALID_OPENAI_PAYLOAD)

    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "gpt-4o"
    assert data["response_text"] == "Hello from OpenAI!"
    assert data["latency"] == pytest.approx(0.42)


def test_execute_valid_gemini():
    with patch("app.api.routes_execute.GeminiProvider") as MockProvider:
        instance = MockProvider.return_value
        instance.run_prompt.return_value = ("Hello from Gemini!", 0.75)

        response = client.post("/api/execute", json=VALID_GEMINI_PAYLOAD)

    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "gemini-2.5-flash"
    assert data["response_text"] == "Hello from Gemini!"
    assert data["latency"] == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# 2. Empty prompt → 400
# ---------------------------------------------------------------------------

def test_execute_empty_prompt():
    payload = {**VALID_OPENAI_PAYLOAD, "prompt": ""}
    response = client.post("/api/execute", json=payload)

    assert response.status_code == 400
    assert "prompt" in response.json()["detail"].lower()


def test_execute_whitespace_only_prompt():
    payload = {**VALID_OPENAI_PAYLOAD, "prompt": "   "}
    response = client.post("/api/execute", json=payload)

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 3. Missing / empty API key → 400
# ---------------------------------------------------------------------------

def test_execute_empty_api_key():
    payload = {**VALID_OPENAI_PAYLOAD, "api_key": ""}
    response = client.post("/api/execute", json=payload)

    assert response.status_code == 400
    assert "api key" in response.json()["detail"].lower()


def test_execute_whitespace_only_api_key():
    payload = {**VALID_OPENAI_PAYLOAD, "api_key": "   "}
    response = client.post("/api/execute", json=payload)

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 4. Invalid API key — provider raises ProviderAuthError → 401
# ---------------------------------------------------------------------------

def test_execute_invalid_openai_api_key():
    with patch("app.api.routes_execute.OpenAIProvider") as MockProvider:
        instance = MockProvider.return_value
        instance.run_prompt.side_effect = ProviderAuthError("Invalid OpenAI API key")

        payload = {**VALID_OPENAI_PAYLOAD, "api_key": "sk-invalid"}
        response = client.post("/api/execute", json=payload)

    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_execute_invalid_gemini_api_key():
    with patch("app.api.routes_execute.GeminiProvider") as MockProvider:
        instance = MockProvider.return_value
        instance.run_prompt.side_effect = ProviderAuthError("Invalid Gemini API key")

        payload = {**VALID_GEMINI_PAYLOAD, "api_key": "bad-key"}
        response = client.post("/api/execute", json=payload)

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# 5. Unsupported model → 400
# ---------------------------------------------------------------------------

def test_execute_unsupported_model():
    payload = {**VALID_OPENAI_PAYLOAD, "model": "claude-3-opus"}
    response = client.post("/api/execute", json=payload)

    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


def test_execute_another_unsupported_model():
    payload = {**VALID_OPENAI_PAYLOAD, "model": "llama-3"}
    response = client.post("/api/execute", json=payload)

    assert response.status_code == 400
