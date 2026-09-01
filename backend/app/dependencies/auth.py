from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import UserInfo

# auto_error=False: the header is now a fallback for non-browser clients, not
# the primary transport, so a missing header is not by itself an error.
bearer_scheme = HTTPBearer(auto_error=False)

# Requests authenticated by cookie must carry this header on state-changing
# methods. Browsers refuse to attach custom headers to a cross-origin request
# without a successful CORS preflight, and the preflight is gated by the origin
# allowlist in main.py -- so a page on another domain cannot forge one. This
# replaces the CSRF protection that SameSite would have provided if the SPA and
# the API shared a domain (see the note in config.py).
CSRF_HEADER = "X-Requested-With"
CSRF_HEADER_VALUE = "PromptBox"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def require_csrf_header(request: Request) -> None:
    """Enforce the custom-header check on a cookie-authenticated write.

    Factored out of ``get_current_user`` so that endpoints which act on a
    cookie *without* resolving a signed-in user can apply the same rule --
    ``/auth/link/confirm`` is one: it is unauthenticated by definition (the
    session is what it is trying to create) but it acts on the pending-link
    cookie, so a cross-site page must not be able to drive it either.
    """
    if request.method not in UNSAFE_METHODS:
        return
    if request.headers.get(CSRF_HEADER) != CSRF_HEADER_VALUE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing or invalid {CSRF_HEADER} header",
        )


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> UserInfo:
    cookie_token = request.cookies.get(settings.SESSION_COOKIE_NAME)

    if cookie_token:
        token, from_cookie = cookie_token, True
    elif credentials is not None:
        token, from_cookie = credentials.credentials, False
    else:
        raise _unauthorized("Not authenticated")

    if from_cookie:
        require_csrf_header(request)

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise _unauthorized("Invalid token: missing subject")
        # Inside the try: a non-numeric `sub` is a malformed token, not a
        # server error. Previously this raised ValueError and surfaced as 500.
        user_pk = int(user_id)
    except (JWTError, ValueError):
        raise _unauthorized("Invalid or expired token")

    user = db.query(UserInfo).filter(UserInfo.id == user_pk).first()
    if user is None:
        raise _unauthorized("User not found")

    # Published for the rate limiter, which needs the caller identity before
    # the endpoint body runs. See app/rate_limit.py.
    request.state.user_id = user.id
    return user
