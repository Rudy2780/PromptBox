import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Response
from jose import jwt

from app.config import settings
from app.models.user import UserInfo
from app.utils.security import hash_password


def get_user_by_email(db, email):       # This will return a matched email between user input and DB query

    return db.query(UserInfo).filter(UserInfo.email == email).first()

def create_user(db, email, password):       # this will create the new user and put users info as an object in class UserInfo

    hashed = hash_password(password)
    new_user = UserInfo(email = email, hashed_password = hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def create_access_token(user_id) -> str:
    """Mint a session token.

    Carries `jti`, `iat`, `aud` and `iss` in addition to `sub`/`exp`. `jti` is
    the piece that makes revocation possible later: a denylist needs a stable
    per-token identifier to key on. Nothing consumes the denylist yet, but
    tokens issued from now on can be individually revoked once one exists.
    """
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=settings.ACCESS_TOKEN_TTL_HOURS)
    payload = {
        "sub": str(user_id),
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "aud": settings.JWT_AUDIENCE,
        "iss": settings.JWT_ISSUER,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def set_session_cookie(response: Response, token: str) -> None:
    """Attach the session token as an httpOnly cookie.

    httpOnly means page scripts cannot read it, so an XSS bug cannot exfiltrate
    the session the way a token held in localStorage could.
    """
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.ACCESS_TOKEN_TTL_HOURS * 3600,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        domain=settings.SESSION_COOKIE_DOMAIN,
        path=settings.SESSION_COOKIE_PATH,
    )


def clear_session_cookie(response: Response) -> None:
    """Expire the session cookie.

    The attributes must match those used when setting it or the browser treats
    it as a different cookie and leaves the original in place.
    """
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path=settings.SESSION_COOKIE_PATH,
        domain=settings.SESSION_COOKIE_DOMAIN,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
    )
