from fastapi import APIRouter, HTTPException

from app.schemas.execute_schema import (
    ExecuteRequest,
    ExecuteResponse,
    PromptBatchRequest,
    PromptBatchResponse,
)
from app.providers.exceptions import ProviderAuthError, ProviderError
from app.providers.openai_provider import OpenAIProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.anthropic_provider import AnthropicProvider
from app.supported_models import (
    SUPPORTED_OPENAI_MODELS,
    SUPPORTED_GEMINI_MODELS,
    SUPPORTED_ANTHROPIC_MODELS,
)

router = APIRouter()


def _get_provider(model: str, api_key: str):
    if model in SUPPORTED_OPENAI_MODELS:
        return OpenAIProvider(api_key=api_key, model=model)
    if model in SUPPORTED_GEMINI_MODELS:
        return GeminiProvider(api_key=api_key, model=model)
    if model in SUPPORTED_ANTHROPIC_MODELS:
        return AnthropicProvider(api_key=api_key, model=model)
    raise HTTPException(status_code=400, detail=f"Unsupported model: {model}")


def _provider_for_model(model: str) -> str:
    if model in SUPPORTED_OPENAI_MODELS:
        return "openai"
    if model in SUPPORTED_GEMINI_MODELS:
        return "gemini"
    if model in SUPPORTED_ANTHROPIC_MODELS:
        return "anthropic"
    raise HTTPException(status_code=400, detail=f"Unsupported model: {model}")


@router.post("/api/execute", response_model=ExecuteResponse)
def execute(request: ExecuteRequest) -> ExecuteResponse:
    prompt = (request.prompt or "").strip()
    api_key = (request.api_key or "").strip()

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")

    if not api_key:
        raise HTTPException(status_code=400, detail="API key must not be empty.")

    provider = _get_provider(request.model, api_key)

    try:
        response_text, latency = provider.run_prompt(prompt)
    except ProviderAuthError as exc:
        # Authentication failures should map to 401 Unauthorized.
        raise HTTPException(status_code=401, detail=str(exc))
    except ProviderError as exc:
        # Other provider issues become generic upstream errors.
        raise HTTPException(status_code=502, detail=str(exc))

    return ExecuteResponse(model=request.model, response_text=response_text, latency=latency)


@router.post("/api/prompt", response_model=PromptBatchResponse)
def prompt_batch(request: PromptBatchRequest) -> PromptBatchResponse:
    prompt = (request.prompt or "").strip()
    models = request.models or []
    api_keys = request.api_keys or {}
    single_key = (request.api_key or "").strip()

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")
    if not models:
        raise HTTPException(status_code=400, detail="At least one model must be provided.")

    responses: list[ExecuteResponse] = []
    for model in models:
        provider_name = _provider_for_model(model)
        api_key = (api_keys.get(provider_name) or single_key or "").strip()
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail=f"API key must be provided for provider '{provider_name}'.",
            )
        provider = _get_provider(model, api_key)
        try:
            response_text, latency = provider.run_prompt(prompt)
        except ProviderAuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc))
        except ProviderError as exc:
            raise HTTPException(status_code=502, detail=str(exc))

        responses.append(
            ExecuteResponse(model=model, response_text=response_text, latency=latency)
        )

    return PromptBatchResponse(responses=responses)

