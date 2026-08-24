"""Tests for the auth, rate limiting and input bounds added to the LLM endpoints.

These three endpoints were previously unauthenticated and unbounded on a public
URL: /api/validate-key answered "is this stolen key live?" for three providers,
/api/execute relayed arbitrary LLM traffic, and /api/prompt looped an uncapped
model list of blocking calls.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.api import routes_execute
from app.schemas.execute_schema import MAX_MODELS_PER_REQUEST, MAX_PROMPT_CHARS

EXECUTE_PAYLOAD = {"prompt": "Say hello", "model": "gpt-4o", "api_key": "sk-test-key"}
BATCH_PAYLOAD = {
    "prompt": "Say hello",
    "models": ["gpt-4o"],
    "api_keys": {"openai": "k-openai"},
}
VALIDATE_PAYLOAD = {"provider": "openai", "api_key": "sk-test-key"}


class FakeProvider:
    def __init__(self, model: str):
        self.model = model

    def run_prompt(self, prompt: str):
        return f"resp-{self.model}", 0.05


@pytest.fixture
def fake_providers(monkeypatch):
    monkeypatch.setattr(
        routes_execute, "_get_provider", lambda model, api_key: FakeProvider(model)
    )


# ---------------------------------------------------------------------------
# Authentication is required
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path,payload",
    [
        ("/api/execute", EXECUTE_PAYLOAD),
        ("/api/prompt", BATCH_PAYLOAD),
        ("/api/validate-key", VALIDATE_PAYLOAD),
    ],
)
def test_endpoint_rejects_unauthenticated_request(client, path, payload):
    res = client.post(path, json=payload)
    assert res.status_code == 401, (
        f"{path} did not reject an unauthenticated request "
        f"(got {res.status_code}, expected 401)"
    )


@pytest.mark.parametrize(
    "path,payload",
    [
        ("/api/execute", EXECUTE_PAYLOAD),
        ("/api/prompt", BATCH_PAYLOAD),
        ("/api/validate-key", VALIDATE_PAYLOAD),
    ],
)
def test_endpoint_rejects_garbage_token(client, path, payload):
    client.headers.update({"Authorization": "Bearer not-a-real-token"})
    res = client.post(path, json=payload)
    assert res.status_code == 401


def test_execute_allows_authenticated_request(authed_client, fake_providers):
    res = authed_client.post("/api/execute", json=EXECUTE_PAYLOAD)
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# Input bounds
# ---------------------------------------------------------------------------


def test_prompt_over_length_limit_rejected(authed_client):
    payload = {**EXECUTE_PAYLOAD, "prompt": "x" * (MAX_PROMPT_CHARS + 1)}
    res = authed_client.post("/api/execute", json=payload)
    assert res.status_code == 422


def test_prompt_at_length_limit_accepted(authed_client, fake_providers):
    payload = {**EXECUTE_PAYLOAD, "prompt": "x" * MAX_PROMPT_CHARS}
    res = authed_client.post("/api/execute", json=payload)
    assert res.status_code == 200


def test_too_many_distinct_models_rejected(authed_client, fake_providers):
    payload = {
        **BATCH_PAYLOAD,
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "claude-opus-4-7",
        ],
    }
    assert len(payload["models"]) > MAX_MODELS_PER_REQUEST
    res = authed_client.post("/api/prompt", json=payload)
    assert res.status_code == 422


def test_duplicate_models_are_deduplicated(authed_client, fake_providers):
    """Duplicates collapse rather than counting against the cap or being run twice."""
    payload = {**BATCH_PAYLOAD, "models": ["gpt-4o", "gpt-4o", "gpt-4o", "gpt-4o"]}
    res = authed_client.post("/api/prompt", json=payload)
    assert res.status_code == 200
    assert len(res.json()["responses"]) == 1


def test_dedupe_happens_before_the_cap(authed_client, fake_providers):
    """Six entries, two distinct -> accepted, because the cap applies after dedupe."""
    payload = {**BATCH_PAYLOAD, "models": ["gpt-4o"] * 3 + ["gpt-4o-mini"] * 3}
    payload["api_keys"] = {"openai": "k-openai"}
    res = authed_client.post("/api/prompt", json=payload)
    assert res.status_code == 200
    assert len(res.json()["responses"]) == 2


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


def test_validate_key_is_rate_limited(authed_client, rate_limited):
    """The stolen-key oracle stops answering well before it is useful."""
    with patch(
        "app.api.routes_validate_key.test_provider_key",
        new_callable=AsyncMock,
        return_value=True,
    ):
        statuses = [
            authed_client.post("/api/validate-key", json=VALIDATE_PAYLOAD).status_code
            for _ in range(15)
        ]

    assert 429 in statuses, f"never rate limited: {statuses}"
    assert statuses[0] == 200, "the first request should still succeed"
    # Once tripped it stays tripped for the window.
    assert statuses[-1] == 429


def test_execute_is_rate_limited(authed_client, rate_limited, fake_providers):
    statuses = [
        authed_client.post("/api/execute", json=EXECUTE_PAYLOAD).status_code
        for _ in range(40)
    ]
    assert 429 in statuses, f"never rate limited: {statuses}"


def test_rate_limit_response_is_429_not_500(authed_client, rate_limited, fake_providers):
    for _ in range(40):
        res = authed_client.post("/api/execute", json=EXECUTE_PAYLOAD)
        if res.status_code == 429:
            break
    assert res.status_code == 429
