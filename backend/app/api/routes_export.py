import json
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import UserInfo
from app.models.prompt_version import PromptVersion

router = APIRouter(prefix="/api/export", tags=["export"])

def serialize_txt(version: PromptVersion) -> str:
    content = f"Name: {version.name}\n"
    content += f"Created At: {version.created_at}\n"
    content += f"\nPrompt:\n{version.prompt_text}\n"
    
    if version.response_text:
        content += f"\nResponse (Model: {version.response_model}):\n{version.response_text}\n"
        
    return content

def serialize_md(version: PromptVersion) -> str:
    content = f"# {version.name}\n\n"
    content += f"**Created At:** {version.created_at}\n\n"
    content += "## Prompt\n\n```text\n"
    content += f"{version.prompt_text}\n```\n\n"
    
    if version.response_text:
        content += f"## Response\n\n**Model:** {version.response_model}\n\n```text\n"
        content += f"{version.response_text}\n```\n"
        
    return content

@router.get("/{version_id}")
def export_version(
    version_id: int,
    format: str = Query(..., description="Format to export (txt, md, json)"),
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    version = db.query(PromptVersion).filter(
        PromptVersion.user_id == user.id, 
        PromptVersion.id == version_id
    ).first()
    
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
        
    if format == "txt":
        content = serialize_txt(version)
        media_type = "text/plain"
    elif format == "md":
        content = serialize_md(version)
        media_type = "text/markdown"
    elif format == "json":
        data = {
            "id": version.id,
            "name": version.name,
            "tag": version.tag,
            "prompt_text": version.prompt_text,
            "response_text": version.response_text,
            "response_model": version.response_model,
            "response_latency": version.response_latency,
            "created_at": str(version.created_at)
        }
        content = json.dumps(data, indent=2)
        media_type = "application/json"
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")
        
    filename = f"export-{version.id}.{format}"
    
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
