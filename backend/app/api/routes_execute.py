from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.config import settings
from app.dependencies.auth import get_current_user
from app.models.user import UserInfo
from app.rate_limit import ip_key, limiter, user_key
from app.schemas.execute_schema import (
    ExecuteResponse,
    PromptBatchRequest,
    PromptBatchResponse,
)
from app.providers.exceptions import ProviderAuthError, ProviderError
from app.providers.registry import provider_for_model, provider_name_for_model

router = APIRouter()


def _get_provider(model: str, api_key: str):
    """Resolve a model to its adapter. The name/model mapping lives in one
    place (app/providers/registry.py); this only turns "unsupported" into the
    HTTP error the API promises."""
    provider = provider_for_model(model, api_key)
    if provider is None:
        raise HTTPException(status_code=400, detail=f"Unsupported model: {model}")
    return provider


def _provider_for_model(model: str) -> str:
    name = provider_name_for_model(model)
    if name is None:
        raise HTTPException(status_code=400, detail=f"Unsupported model: {model}")
    return name


@router.post("/api/prompt", response_model=PromptBatchResponse)
@limiter.limit(settings.LLM_RATE_LIMIT_PER_USER, key_func=user_key)
@limiter.limit(settings.LLM_RATE_LIMIT_PER_IP, key_func=ip_key)
def prompt_batch(
    request: Request,
    response: Response,
    body: PromptBatchRequest,
    user: UserInfo = Depends(get_current_user),
) -> PromptBatchResponse:
    prompt = (body.prompt or "").strip()
    models = body.models or []
    api_keys = body.api_keys or {}
    single_key = (body.api_key or "").strip()

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

