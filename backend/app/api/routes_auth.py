import re
from fastapi import APIRouter, HTTPException, status
from app.schemas.auth import Credentials
from app.services.auth_service import create_access_token, get_user_by_email, create_user
from app.utils.security import verify_password
from app.database import get_db
from fastapi import Depends

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate(creds: Credentials):
    if not EMAIL_RE.match(creds.email or ""):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if len(creds.password or "") < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(creds: Credentials, db=Depends(get_db)):
    _validate(creds)
    if get_user_by_email(db, creds.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    create_user(db, creds.email, creds.password)
    return {"status": "created", "email": creds.email}


@router.post("/login")
def login(creds: Credentials, db=Depends(get_db)):
    _validate(creds)
    user = get_user_by_email(db, creds.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(creds.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user_token = create_access_token(user.id)
    return {"status": "ok", "token": user_token, "email": user.email}
