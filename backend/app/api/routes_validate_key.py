from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.llm_service import test_provider_key

router = APIRouter()

SUPPORTED_MODELS = {
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        ], 
    "anthropic": [
        "claude-opus-4-7",
        "claude-opus-4-6",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
    ],
    "gemini": [
        "gemini-2.5-flash",
        "gemini-2.5-pro"
    ]
}

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
