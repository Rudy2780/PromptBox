from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import UserInfo
from app.models.prompt_version import PromptVersion
from app.schemas.version_schema import VersionCreateRequest, VersionResponse, VersionUpdateRequest
from app.services.version_service import get_owned_version_or_404

router = APIRouter(prefix="/api/versions", tags=["versions"])

LIKE_ESCAPE_CHAR = "\\"


def _escape_like(value: str) -> str:
    """Neutralise LIKE metacharacters in user-supplied search text.

    Not an injection fix -- the value is already a bound parameter -- but
    without it a search for "%" matches every row and "_" matches any single
    character, so the search silently does the wrong thing. The escape
    character itself must be escaped first.
    """
    for char in (LIKE_ESCAPE_CHAR, "%", "_"):
        value = value.replace(char, LIKE_ESCAPE_CHAR + char)
    return value


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
        pattern = f"%{_escape_like(search.lower())}%"
        filters = [
            func.lower(PromptVersion.name).like(pattern, escape="\\"),
            func.lower(PromptVersion.tag).like(pattern, escape="\\"),
        ]
        query = query.filter(or_(*filters))
    
    return query.all()

@router.get("/{version_id}", response_model=VersionResponse)
def get_version(
    version_id: int,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> VersionResponse:
    return get_owned_version_or_404(db, user, version_id)


@router.patch("/{version_id}", response_model=VersionResponse)
def update_version(
    version_id: int,
    body: VersionUpdateRequest,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VersionResponse:
    version = get_owned_version_or_404(db, user, version_id)

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
    version = get_owned_version_or_404(db, user, version_id)

    db.delete(version)
    db.commit()
