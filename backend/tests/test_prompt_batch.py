import pytest

from app.api import routes_execute


class FakeProvider:
    def __init__(self, model: str):
        self.model = model

    def run_prompt(self, prompt: str):
        return f"resp-{self.model}", 0.05


def fake_provider(model, api_key):
    return FakeProvider(model)


@pytest.fixture(autouse=True)
def patch_provider(monkeypatch):
    # Prevent real network calls during tests
    monkeypatch.setattr(routes_execute, "_get_provider", fake_provider)
    yield


def test_prompt_two_models_returns_two_responses(authed_client):
    payload = {
        "prompt": "test prompt",
        "models": ["gpt-4o", "gemini-2.5-flash"],
        "api_keys": {"openai": "k-openai", "gemini": "k-gemini"},
    }
    res = authed_client.post("/api/prompt", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert "responses" in body
    assert len(body["responses"]) == 2
    assert {r["model"] for r in body["responses"]} == set(payload["models"])


def test_prompt_no_models_returns_400(authed_client):
    payload = {"prompt": "hello", "models": [], "api_keys": {"openai": "k-openai"}}
    res = authed_client.post("/api/prompt", json=payload)
    assert res.status_code == 400


def test_prompt_empty_prompt_returns_400(authed_client):
    payload = {"prompt": " ", "models": ["gpt-4o"], "api_keys": {"openai": "k-openai"}}
    res = authed_client.post("/api/prompt", json=payload)
    assert res.status_code == 400
