from pydantic import BaseModel, Field
from datetime import datetime

class VersionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    tag: str | None = Field(None, max_length=32)
    prompt_text: str = Field(...,min_length=1)
    
    response_text: str | None = None
    response_model: str | None = None
    response_latency: float | None = None
    
class VersionResponse(BaseModel):
    id: int
    name: str
    tag: str | None = None
    prompt_text: str
    response_text: str | None = None
    response_model: str | None = None
    response_latency: float | None = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class VersionUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    tag: str | None = Field(None, max_length=32)
