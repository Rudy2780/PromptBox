from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.prompt_version import PromptVersion
from app.models.user import UserInfo


def get_owned_version_or_404(db: Session, user: UserInfo, version_id: int) -> PromptVersion:
    '''Fetch a prompt version owned by the given user, or raise 404.'''
    version = db.query(PromptVersion).filter(
        PromptVersion.user_id == user.id,
        PromptVersion.id == version_id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version
