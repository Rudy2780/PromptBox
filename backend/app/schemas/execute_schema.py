from pydantic import BaseModel
from typing import List, Dict, Optional


class ExecuteRequest(BaseModel):
    prompt: str
    model: str
    api_key: str


class ExecuteResponse(BaseModel):
    model: str
    response_text: str
    latency: float


class PromptBatchRequest(BaseModel):
    prompt: str
    models: List[str]
    api_key: Optional[str] = None  # fallback for single-key use
    api_keys: Optional[Dict[str, str]] = None  # provider -> key


class PromptBatchResponse(BaseModel):
    responses: List[ExecuteResponse]

