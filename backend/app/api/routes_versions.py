from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import UserInfo
from app.models.prompt_version import PromptVersion
from app.schemas.version_schema import VersionCreateRequest, VersionResponse, VersionUpdateRequest

router = APIRouter(prefix="/api/versions", tags=["versions"])

@router.post("/", response_model=VersionResponse, status_code=status.HTTP_201_CREATED)
def save_version(
    body: VersionCreateRequest,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> VersionResponse:
    
    version = PromptVersion(
        user_id=user.id,
        name=body.name,
        tag=body.tag,
        prompt_text=body.prompt_text,
        response_text=body.response_text,
        response_model=body.response_model,
        response_latency=body.response_latency,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version

@router.get("/", response_model=List[VersionResponse])
def get_versions(
    search: Optional[str] = Query(None, max_length=255),
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[VersionResponse]:
    query = db.query(PromptVersion).filter(PromptVersion.user_id == user.id)
    
    if search:
        pattern = f"%{search.lower()}%"
        filters = [
            func.lower(PromptVersion.name).like(pattern),
            func.lower(PromptVersion.tag).like(pattern),
        ]
        query = query.filter(or_(*filters))
    
    return query.all()

@router.get("/{version_id}", response_model=VersionResponse)
def get_version(
    version_id: int,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> VersionResponse:
    version = db.query(PromptVersion).filter(PromptVersion.user_id == user.id, PromptVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@router.patch("/{version_id}", response_model=VersionResponse)
def update_version(
    version_id: int,
    body: VersionUpdateRequest,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VersionResponse:
    version = db.query(PromptVersion).filter(
        PromptVersion.user_id == user.id,
        PromptVersion.id == version_id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    version.name = body.name
    version.tag = body.tag
    db.commit()
    db.refresh(version)
    return version


@router.delete("/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_version(
    version_id: int,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    version = db.query(PromptVersion).filter(
        PromptVersion.user_id == user.id,
        PromptVersion.id == version_id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    db.delete(version)
    db.commit()
