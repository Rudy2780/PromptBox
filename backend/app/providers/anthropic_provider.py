import time
from typing import Tuple

from .exceptions import ProviderAuthError, ProviderError

try:
    import anthropic
except Exception:
    anthropic = None
    
class AnthropicProvider:
    
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model
        
    def run_prompt(self, prompt: str) -> Tuple[str, float]:
        
        if anthropic is None:
            raise ProviderError("Anthropic SDK is not installed.")
        
        start = time.perf_counter()
        
        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            message = client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            message_content = ""
            for block in message.content:
                if getattr(block, "type", None) == "text":
                    message_content = block.text
                    break
            if not message_content:
                message_content = str(message)
        except Exception as exc:
            auth_error_cls = getattr(anthropic, "AuthenticationError", None) if anthropic is not None else None
            if auth_error_cls is not None and isinstance(exc, auth_error_cls):
                raise ProviderAuthError("Invalid Anthropic API key") from exc
            # Only a genuine AuthenticationError above maps to 401. Everything
            # else -- rate limits, timeouts, bad model ids, network faults --
            # is an upstream failure (502), matching the OpenAI and Gemini
            # providers. Reporting them as "invalid API key" made users rotate
            # keys that were never broken.
            raise ProviderError(f"Anthropic provider error: {exc}") from exc
        
        latency = time.perf_counter() - start
        return str(message_content), float(latency)
