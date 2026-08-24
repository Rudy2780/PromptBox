"""Provider lookup.

One place that maps a provider name or a model id to the adapter class, so
callers never construct a vendor SDK client themselves.
"""

from typing import Optional, Type

from app.supported_models import (
    SUPPORTED_ANTHROPIC_MODELS,
    SUPPORTED_GEMINI_MODELS,
    SUPPORTED_OPENAI_MODELS,
)

from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider
from .llm_provider_base import LLMProvider
from .openai_provider import OpenAIProvider

PROVIDER_CLASSES: dict[str, Type[LLMProvider]] = {
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "anthropic": AnthropicProvider,
}

_MODEL_SETS = {
    "openai": SUPPORTED_OPENAI_MODELS,
    "gemini": SUPPORTED_GEMINI_MODELS,
    "anthropic": SUPPORTED_ANTHROPIC_MODELS,
}


def provider_name_for_model(model: str) -> Optional[str]:
    """Return the provider that serves `model`, or None if unsupported."""
    for name, models in _MODEL_SETS.items():
        if model in models:
            return name
    return None


def provider_for_name(provider: str, api_key: str) -> Optional[LLMProvider]:
    """Build an adapter for key validation, where no model has been chosen."""
    provider_class = PROVIDER_CLASSES.get(provider)
    if provider_class is None:
        return None
    return provider_class(api_key=api_key)


def provider_for_model(model: str, api_key: str) -> Optional[LLMProvider]:
    """Build an adapter for a specific model, or None if it is unsupported."""
    name = provider_name_for_model(model)
    if name is None:
        return None
    return PROVIDER_CLASSES[name](api_key=api_key, model=model)
