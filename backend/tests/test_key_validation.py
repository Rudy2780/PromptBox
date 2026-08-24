"""Key validation goes through the provider adapters.

llm_service used to import openai / anthropic / genai and build its own
clients, giving every provider two construction paths that drifted apart.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

# Aliased: pytest would otherwise collect the imported function itself
# as a test case, because its name begins with `test_`.
from app.services.llm_service import test_provider_key as validate_provider_key


@pytest.mark.parametrize("provider", ["openai", "gemini", "anthropic"])
def test_validation_delegates_to_the_provider_adapter(provider):
    provider_cls = MagicMock()
    provider_cls.return_value.validate_key.return_value = True

    with patch.dict(
        "app.providers.registry.PROVIDER_CLASSES", {provider: provider_cls}
    ):
        result = asyncio.run(validate_provider_key(provider, "some-key"))

    assert result is True
    provider_cls.assert_called_once_with(api_key="some-key")
    provider_cls.return_value.validate_key.assert_called_once()


def test_rejected_key_returns_false():
    provider_cls = MagicMock()
    provider_cls.return_value.validate_key.return_value = False

    with patch.dict("app.providers.registry.PROVIDER_CLASSES", {"openai": provider_cls}):
        assert asyncio.run(validate_provider_key("openai", "bad-key")) is False


def test_unknown_provider_returns_false():
    assert asyncio.run(validate_provider_key("not-a-provider", "k")) is False


def test_llm_service_no_longer_imports_the_vendor_sdks():
    """The point of the collapse: exactly one place builds SDK clients."""
    import app.services.llm_service as module

    for sdk in ("openai", "anthropic", "genai"):
        assert not hasattr(module, sdk), (
            f"llm_service still imports {sdk}; SDK construction belongs in "
            "app/providers/*"
        )


@pytest.mark.parametrize(
    "provider,expected",
    [
        ("openai", "gpt-4o-mini"),
        ("gemini", "gemini-2.5-flash"),
        ("anthropic", "claude-haiku-4-5-20251001"),
    ],
)
def test_validation_uses_the_cheapest_model(provider, expected):
    """Validation must not depend on the caller having chosen a model."""
    from app.providers.registry import provider_for_name

    assert provider_for_name(provider, "k").model == expected
