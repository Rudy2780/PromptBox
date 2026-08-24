import time
from typing import Tuple

from .exceptions import ProviderAuthError, ProviderError
from .llm_provider_base import LLMProvider

try:  # Optional dependency; tests mock this provider.
    from google import genai  # type: ignore[import]
except Exception:  # pragma: no cover - handled at runtime if actually used
    genai = None  # type: ignore[assignment]


class GeminiProvider(LLMProvider):
    """Concrete provider for Google Gemini models."""

    VALIDATION_MODEL = "gemini-2.5-flash"

    def run_prompt(self, prompt: str) -> Tuple[str, float]:
        """
        Execute the prompt against a Gemini model.

        Returns a tuple of (response_text, latency_seconds).
        """
        if genai is None:
            raise ProviderError("Google GenAI SDK is not installed.")

        start = time.perf_counter()

        try:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            # `text` is available on standard responses; fall back to stringifying otherwise.
            message_content = getattr(response, "text", None) or str(response)
        except Exception as exc:  # pragma: no cover - exercised via higher-level tests/mocks
            # The Gemini SDK does not expose a stable auth error type across all versions,
            # so we treat all failures as generic provider errors here.
            message = str(exc)
            # Heuristic: if the message clearly indicates an auth problem, surface as auth error.
            lowered = message.lower()
            if "api key" in lowered and ("invalid" in lowered or "unauthorized" in lowered):
                raise ProviderAuthError("Invalid Gemini API key") from exc

            raise ProviderError(f"Gemini provider error: {exc}") from exc

        latency = time.perf_counter() - start
        return str(message_content), float(latency)

    def validate_key(self) -> bool:
        """Cheapest possible call: list models rather than generate anything."""
        if genai is None:
            return False
        try:
            genai.Client(api_key=self.api_key).models.list()
            return True
        except Exception:
            return False
