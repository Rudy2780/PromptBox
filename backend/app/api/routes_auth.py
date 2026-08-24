import re
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import UserInfo
from app.schemas.auth import Credentials
from app.services.auth_service import (
    clear_session_cookie,
    create_access_token,
    create_user,
    get_user_by_email,
    set_session_cookie,
)
from app.rate_limit import ip_key, limiter
from app.utils.security import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate(creds: Credentials):
    if not EMAIL_RE.match(creds.email or ""):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if len(creds.password or "") < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")


# Returned verbatim whether or not the address was already taken, so the
# response cannot be used to enumerate registered accounts.
REGISTRATION_ACCEPTED = {
    "status": "ok",
    "detail": (
        "If that email address is available, your account has been created. "
        "You can now sign in."
    ),
}


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.REGISTER_RATE_LIMIT_PER_IP, key_func=ip_key)
def register(creds: Credentials, request: Request, response: Response, db=Depends(get_db)):
    _validate(creds)

    if get_user_by_email(db, creds.email):
        # Previously a 409 "Email already registered", which let anyone test an
        # address for membership. Burn an equivalent amount of time hashing so
        # the fast path and the slow path are not distinguishable by latency
        # either -- bcrypt at cost 12 is the dominant cost of a real signup.
        hash_password(creds.password)
        return REGISTRATION_ACCEPTED

    create_user(db, creds.email, creds.password)
    return REGISTRATION_ACCEPTED


@router.post("/login")
@limiter.limit(settings.LOGIN_RATE_LIMIT_PER_IP, key_func=ip_key)
def login(creds: Credentials, request: Request, response: Response, db=Depends(get_db)):
    _validate(creds)
    user = get_user_by_email(db, creds.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(creds.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    set_session_cookie(response, create_access_token(user.id))
    # The token is deliberately NOT in the response body. Returning it would
    # hand it straight back to page scripts and defeat the httpOnly cookie.
    return {"status": "ok", "email": user.email}


@router.post("/logout")
def logout(response: Response):
    """Clear the session cookie.

    Unauthenticated on purpose: logging out with an already-expired or
    malformed session must still clear the cookie rather than 401.
    """
    clear_session_cookie(response)
    return {"status": "logged_out"}


@router.get("/me")
def me(user: UserInfo = Depends(get_current_user)):
    """Who is this session? The SPA cannot read the httpOnly cookie, so this is
    how it restores sign-in state after a page reload."""
    return {"id": user.id, "email": user.email}
