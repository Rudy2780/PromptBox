from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.config import settings
from app.dependencies.auth import get_current_user
from app.models.user import UserInfo
from app.rate_limit import ip_key, limiter, user_key
from app.services.llm_service import test_provider_key
from app.supported_models import SUPPORTED_MODELS

router = APIRouter()

class ValidateKeyRequest(BaseModel):
    provider: str
    api_key: str
    
@router.post("/validate-key")
@limiter.limit(settings.VALIDATE_KEY_RATE_LIMIT_PER_USER, key_func=user_key)
@limiter.limit(settings.VALIDATE_KEY_RATE_LIMIT_PER_IP, key_func=ip_key)
async def validate_key(
    request: Request,
    response: Response,
    body: ValidateKeyRequest,
    user: UserInfo = Depends(get_current_user),
):
    if body.provider not in SUPPORTED_MODELS:
        raise HTTPException(status_code=400, detail="Unsupported model")

    if not body.api_key:
        raise HTTPException(status_code=422, detail="API key is required")

    is_valid = await test_provider_key(body.provider, body.api_key)

    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return {"status": "valid", "provider": body.provider}
