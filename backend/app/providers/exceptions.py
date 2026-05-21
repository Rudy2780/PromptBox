class ProviderError(Exception):
    """Base error for LLM provider failures."""


class ProviderAuthError(ProviderError):
    """Raised when authentication with the LLM provider fails (e.g., invalid API key)."""

