"""Gemini key validation and execution, over the real SDK with a mocked transport.

`GeminiProvider.validate_key` used to read:

    genai.Client(api_key=self.api_key).models.list()

Nothing references the `Client` once `.models` has been evaluated, so CPython
frees it mid-expression. `genai.Client.__del__` closes the shared httpx
transport that the `models` object still holds, and `.list()` then raises
"Cannot send a request, as the client has been closed" -- before any request is
sent. `validate_key`'s blanket except turned that into False, and
/api/validate-key turns False into 401, so every Gemini key was reported invalid
without ever being checked. Only the google-genai SDK closes its transport on
garbage collection; openai and anthropic do not, which is why the identical
chained style in those providers is harmless.

These tests therefore run the *real* SDK and stop at the transport layer.
Mocking `genai.Client`, `httpx.Client.request` or `httpx.Client.send` would all
skip the closed-transport check in `httpx.Client.send` and pass against the bug.
"""

from contextlib import contextmanager
from unittest.mock import patch

import httpx
import pytest

import app.providers.gemini_provider as gemini_module
from app.providers.gemini_provider import GeminiProvider

pytestmark = pytest.mark.skipif(
    gemini_module.genai is None,
    reason="google-genai is not installed; the provider degrades to False by design",
)

API_KEY = "AIzaSyTEST-not-a-real-key-000000000000"

MODELS_LIST_OK = {
    "models": [
        {
            "name": "models/gemini-2.5-flash",
            "version": "2.5",
            "displayName": "Gemini 2.5 Flash",
            "inputTokenLimit": 1048576,
            "outputTokenLimit": 65536,
            "supportedGenerationMethods": ["generateContent", "countTokens"],
        }
    ]
}

# What generativelanguage.googleapis.com actually returns for a rejected key:
# 400 INVALID_ARGUMENT with reason API_KEY_INVALID, not a 401.
API_KEY_INVALID = {
    "error": {
        "code": 400,
        "message": "API key not valid. Please pass a valid API key.",
        "status": "INVALID_ARGUMENT",
        "details": [
            {
                "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                "reason": "API_KEY_INVALID",
                "domain": "googleapis.com",
                "metadata": {"service": "generativelanguage.googleapis.com"},
            }
        ],
    }
}


@contextmanager
def mocked_google_api(status=200, payload=None):
    """Serve every httpx request from memory, recording what was sent.

    Patched at the transport layer so the whole SDK stack -- client
    construction, auth header assembly, URL building, response parsing, and
    httpx's own "is this client closed?" guard -- executes for real.

    Only clients constructed *inside* the block are affected; the TestClient
    used by the endpoint test is built by its fixture beforehand and keeps its
    own transport.
    """
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(status, json=payload)

    real_init = httpx.Client.__init__

    def init(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        real_init(self, *args, **kwargs)

    with patch.object(httpx.Client, "__init__", init):
        yield sent


# --- validation --------------------------------------------------------------


def test_valid_key_validates_successfully():
    """The regression: this returned False against the chained-call version."""
    with mocked_google_api(200, MODELS_LIST_OK) as sent:
        assert GeminiProvider(api_key=API_KEY).validate_key() is True

    assert len(sent) == 1, "validation must actually call the API exactly once"


def test_validation_authenticates_with_the_api_key_header():
    """Gemini takes ?key= or x-goog-api-key -- never an Authorization bearer."""
    with mocked_google_api(200, MODELS_LIST_OK) as sent:
        GeminiProvider(api_key=API_KEY).validate_key()

    request = sent[0]
    assert request.headers.get("x-goog-api-key") == API_KEY
    assert "authorization" not in request.headers, (
        "Bearer auth is the OpenAI/Anthropic convention; Google rejects it"
    )


def test_validation_calls_the_models_list_endpoint():
    with mocked_google_api(200, MODELS_LIST_OK) as sent:
        GeminiProvider(api_key=API_KEY).validate_key()

    request = sent[0]
    assert request.method == "GET"
    assert request.url.host == "generativelanguage.googleapis.com"
    assert request.url.path == "/v1beta/models"


def test_rejected_key_fails_validation():
    with mocked_google_api(400, API_KEY_INVALID) as sent:
        assert GeminiProvider(api_key="AIzaSy-revoked").validate_key() is False

    # Asserting the request happened is the point: the bug also produced False,
    # but by never reaching the network at all.
    assert sent, "a rejected key must be rejected *by Google*, not locally"
    assert sent[0].headers.get("x-goog-api-key") == "AIzaSy-revoked"


# --- execution ---------------------------------------------------------------


def test_run_prompt_uses_the_same_authenticated_path():
    """The execution path must not regress into the same dropped-reference bug."""
    payload = {
        "candidates": [
            {
                "content": {"role": "model", "parts": [{"text": "pong"}]},
                "finishReason": "STOP",
            }
        ]
    }

    with mocked_google_api(200, payload) as sent:
        text, latency = GeminiProvider(
            api_key=API_KEY, model="gemini-2.5-flash"
        ).run_prompt("ping")

    assert text == "pong"
    assert latency >= 0

    request = sent[0]
    assert request.headers.get("x-goog-api-key") == API_KEY
    assert "authorization" not in request.headers
    assert request.url.path == "/v1beta/models/gemini-2.5-flash:generateContent"


# --- endpoint ----------------------------------------------------------------


def test_validate_key_endpoint_accepts_a_working_gemini_key(authed_client):
    """End to end: a live key must come back 200, not 401."""
    with mocked_google_api(200, MODELS_LIST_OK):
        res = authed_client.post(
            "/api/validate-key", json={"provider": "gemini", "api_key": API_KEY}
        )

    assert res.status_code == 200, res.text
    assert res.json() == {"status": "valid", "provider": "gemini"}


def test_validate_key_endpoint_rejects_a_bad_gemini_key(authed_client):
    with mocked_google_api(400, API_KEY_INVALID):
        res = authed_client.post(
            "/api/validate-key", json={"provider": "gemini", "api_key": "AIzaSy-bad"}
        )

    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid API key"
