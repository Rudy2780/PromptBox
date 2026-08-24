from abc import ABC, abstractmethod
from typing import Tuple


class LLMProvider(ABC):
    """Contract for a provider adapter.

    Every construction of a vendor SDK client belongs behind this interface.
    Before, `services/llm_service.py` built its own `openai.OpenAI`,
    `anthropic.Anthropic` and `genai.Client` instances for key validation while
    these classes built their own for execution -- two layers per provider,
    drifting independently. (That is how the Anthropic adapter came to map every
    failure to 401 while OpenAI and Gemini mapped them to 502.)
    """

    #: Cheapest model to talk to when only checking whether a key is live.
    #: Key validation must not depend on the caller having chosen a model.
    VALIDATION_MODEL: str = ""

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self.api_key = api_key
        self.model = model or self.VALIDATION_MODEL

    @abstractmethod
    def run_prompt(self, prompt: str) -> Tuple[str, float]:
        """Execute a prompt, returning (response_text, latency_seconds).

        Raises ProviderAuthError for a rejected key and ProviderError for any
        other upstream failure.
        """

    @abstractmethod
    def validate_key(self) -> bool:
        """Return whether the key is accepted. Must not raise."""
