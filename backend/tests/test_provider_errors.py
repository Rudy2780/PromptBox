"""Provider error mapping.

The Anthropic provider previously raised ProviderAuthError from its generic
fallthrough, so every rate limit, timeout, bad model id or network fault
surfaced to the user as 401 "Invalid Anthropic API key" -- prompting them to
rotate keys that were never broken. OpenAI and Gemini always mapped these to
ProviderError (502); this pins the Anthropic provider to the same contract.
"""

from unittest.mock import MagicMock, patch

import pytest

import app.providers.anthropic_provider as anthropic_module
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.exceptions import ProviderAuthError, ProviderError


class FakeAuthenticationError(Exception):
    """Stands in for anthropic.AuthenticationError, which must be a real class
    for the provider's isinstance() check."""


def _fake_sdk(side_effect):
    sdk = MagicMock()
    sdk.AuthenticationError = FakeAuthenticationError
    sdk.Anthropic.return_value.messages.create.side_effect = side_effect
    return sdk


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("rate limit exceeded"),
        TimeoutError("upstream timed out"),
        ValueError("unknown model id"),
    ],
)
def test_generic_failures_map_to_provider_error(error):
    with patch.object(anthropic_module, "anthropic", _fake_sdk(error)):
        provider = AnthropicProvider(api_key="sk-ant-valid", model="claude-opus-4-7")
        with pytest.raises(ProviderError) as excinfo:
            provider.run_prompt("hello")

    # ProviderAuthError SUBCLASSES ProviderError, so `pytest.raises(ProviderError)`
    # above would pass against the buggy code too. This exact-type assertion is
    # what actually pins the behaviour.
    assert type(excinfo.value) is ProviderError
    assert not isinstance(excinfo.value, ProviderAuthError)


def test_real_auth_failure_still_maps_to_provider_auth_error():
    """The genuine 401 path must keep working -- this is not a blanket change."""
    with patch.object(
        anthropic_module, "anthropic", _fake_sdk(FakeAuthenticationError("bad key"))
    ):
        provider = AnthropicProvider(api_key="sk-ant-bad", model="claude-opus-4-7")
        with pytest.raises(ProviderAuthError):
            provider.run_prompt("hello")


def test_generic_anthropic_failure_returns_502_not_401(authed_client):
    """End to end: the route maps the provider error to 502."""
    provider_cls = MagicMock()
    provider_cls.return_value.run_prompt.side_effect = ProviderError(
        "Anthropic provider error: rate limit exceeded"
    )
    with patch.dict(
        "app.providers.registry.PROVIDER_CLASSES", {"anthropic": provider_cls}
    ):
        res = authed_client.post(
            "/api/prompt",
            json={
                "prompt": "hello",
                "models": ["claude-opus-4-7"],
                "api_keys": {"anthropic": "sk-ant-valid"},
            },
        )

    assert res.status_code == 502, (
        f"expected 502 for an upstream failure, got {res.status_code}: {res.text}"
    )


def test_anthropic_auth_failure_still_returns_401(authed_client):
    provider_cls = MagicMock()
    provider_cls.return_value.run_prompt.side_effect = ProviderAuthError(
        "Invalid Anthropic API key"
    )
    with patch.dict(
        "app.providers.registry.PROVIDER_CLASSES", {"anthropic": provider_cls}
    ):
        res = authed_client.post(
            "/api/prompt",
            json={
                "prompt": "hello",
                "models": ["claude-opus-4-7"],
                "api_keys": {"anthropic": "sk-ant-bad"},
            },
        )

    assert res.status_code == 401
