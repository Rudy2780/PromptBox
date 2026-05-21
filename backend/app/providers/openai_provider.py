import time
from typing import Tuple

from .exceptions import ProviderAuthError, ProviderError

try:  # Optional dependency; tests mock this provider.
    import openai  # type: ignore[import]
except Exception:  # pragma: no cover - handled at runtime if actually used
    openai = None  # type: ignore[assignment]


class OpenAIProvider:
    """Concrete provider for OpenAI chat models."""

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def run_prompt(self, prompt: str) -> Tuple[str, float]:
        """
        Execute the prompt against an OpenAI chat model.

        Returns a tuple of (response_text, latency_seconds).
        """
        if openai is None:
            raise ProviderError("OpenAI SDK is not installed.")

        start = time.perf_counter()

        try:
            # Support both legacy and newer OpenAI Python SDKs.
            if hasattr(openai, "OpenAI"):
                client = openai.OpenAI(api_key=self.api_key)  # type: ignore[attr-defined]
                completion = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                )
                message_content = completion.choices[0].message.content  # type: ignore[assignment]
            else:
                # Fallback for older SDKs that use global api_key and openai.ChatCompletion
                openai.api_key = self.api_key  # type: ignore[attr-defined]
                completion = openai.ChatCompletion.create(  # type: ignore[attr-defined]
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                )
                message_content = completion["choices"][0]["message"]["content"]

        except Exception as exc:  # pragma: no cover - exercised via higher-level tests/mocks
            # Best-effort mapping of auth errors without tightly coupling to SDK versions.
            auth_error_cls = getattr(openai, "AuthenticationError", None) if openai is not None else None
            if auth_error_cls is not None and isinstance(exc, auth_error_cls):
                raise ProviderAuthError("Invalid OpenAI API key") from exc

            raise ProviderError(f"OpenAI provider error: {exc}") from exc

        latency = time.perf_counter() - start
        return str(message_content), float(latency)

