from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.llm_service import test_provider_key
from app.supported_models import SUPPORTED_MODELS

router = APIRouter()

class ValidateKeyRequest(BaseModel):
    provider: str
    api_key: str
    
@router.post("/validate-key")
async def validate_key(request: ValidateKeyRequest):
    if request.provider not in SUPPORTED_MODELS:
        raise HTTPException(status_code=400, detail="Unsupported model")

    if not request.api_key:
        raise HTTPException(status_code=422, detail="API key is required")
    
    is_valid = await test_provider_key(request.provider, request.api_key)
    
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return {"status": "valid", "provider": request.provider}
