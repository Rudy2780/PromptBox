from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional

# Bounds exist to stop a single request from consuming unbounded work. Each
# model in `models` is a separate blocking upstream call, so an uncapped list
# holds a worker for as long as the list is long.
MAX_PROMPT_CHARS = 32_000
MAX_MODELS_PER_REQUEST = 4


def _dedupe_preserving_order(models: List[str]) -> List[str]:
    seen: List[str] = []
    for model in models or []:
        if model not in seen:
            seen.append(model)
    return seen


class ExecuteRequest(BaseModel):
    # No min_length: an empty or whitespace-only prompt is rejected in the
    # route with a 400 and a readable message, which the API already promises.
    prompt: str = Field(max_length=MAX_PROMPT_CHARS)
    model: str
    api_key: str


class ExecuteResponse(BaseModel):
    model: str
    response_text: str
    latency: float


class PromptBatchRequest(BaseModel):
    prompt: str = Field(max_length=MAX_PROMPT_CHARS)
    models: List[str]
    api_key: Optional[str] = None  # fallback for single-key use
    api_keys: Optional[Dict[str, str]] = None  # provider -> key

    @field_validator("models")
    @classmethod
    def _bound_models(cls, value: List[str]) -> List[str]:
        """Drop duplicates, then cap the list length.

        Deduplicating first means asking for the same model twice is treated as
        the user error it is rather than counting against the cap. An empty list
        is left alone so the route can return its existing 400.
        """
        models = _dedupe_preserving_order(value)
        if len(models) > MAX_MODELS_PER_REQUEST:
            raise ValueError(
                f"At most {MAX_MODELS_PER_REQUEST} distinct models may be "
                f"requested at once; got {len(models)}."
            )
        return models


class PromptBatchResponse(BaseModel):
    responses: List[ExecuteResponse]
