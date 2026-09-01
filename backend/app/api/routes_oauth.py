"""OAuth sign-in endpoints.

The provider legs (``/auth/{provider}/login`` and ``/auth/callback/{provider}``)
are browser navigations rather than XHR: the user is redirected away to the
provider and back. Neither ever returns JSON -- on success *or* on failure the
browser is sent to the SPA, with failures carrying a stable ``auth_error`` slug
in the query string. Serving a JSON error body to a top-level navigation shows
the user a page of raw JSON, which is not a sign-in screen and offers them
nowhere to go.

The link-confirmation endpoints (``/auth/link/pending`` and
``/auth/link/confirm``) are the opposite: ordinary XHR from the SPA, so they
answer in JSON. They carry the same ``auth_error`` slugs, and the SPA renders
them from the same message table, so the user-visible wording is identical no
matter which path produced it.
"""

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from starlette.status import HTTP_302_FOUND

from app.config import settings
from app.database import get_db
from app.dependencies.auth import require_csrf_header
from app.rate_limit import ip_key, limiter
from app.services.auth_service import create_access_token, set_session_cookie
from app.services.oauth_service import (
    ERROR_ACCESS_DENIED,
    ERROR_CODES,
    ERROR_INVALID_PASSWORD,
    OAuthError,
    PasswordConfirmationRequired,
    SignedIn,
    authorization_url,
    confirm_pending_link,
    exchange_code,
    fetch_identity,
    get_provider,
    issue_pending_link,
    issue_state,
    read_pending_link,
    resolve_account,
    verify_state,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# --- redirects -------------------------------------------------------------


def _frontend_url(path: str, **params: str) -> str:
    query = f"?{urlencode(params)}" if params else ""
    return f"{settings.FRONTEND_URL}{path}{query}"


def _error_redirect(code: str):
    """Send the browser back to the sign-in screen with a failure slug.

    Only codes from the closed set in oauth_service reach a URL -- asserted
    here rather than assumed, because this is the exact point where a string
    stops being a server-side value and becomes something written to browser
    history, Referer headers and every proxy log on the way.

    Falls back to JSON only when there is nowhere to send the browser, which
    happens when no provider is configured at all and FRONTEND_URL is
    consequently unset (see _validate_oauth_config).
    """
    if code not in ERROR_CODES:
        raise ValueError(f"refusing to put an unknown code in a URL: {code!r}")

    if not settings.FRONTEND_URL:
        return JSONResponse({"auth_error": code}, status_code=503)

    return RedirectResponse(
        _frontend_url(settings.FRONTEND_LOGIN_PATH, auth_error=code),
        status_code=HTTP_302_FOUND,
    )


def callback_url(request: Request, provider: str) -> str:
    """The ``redirect_uri`` handed to the provider.

    This string has to be byte-identical to one registered in the provider's
    console, at both the authorize step and the token exchange, or the login
    fails with ``redirect_uri_mismatch``. Hence the explicit
    ``OAUTH_REDIRECT_BASE_URL`` override.

    Without it the URL is derived from the incoming request, which is right for
    local development. The scheme is forced to https when the deployment is
    running with Secure cookies, because a reverse proxy that terminates TLS
    without forwarding ``X-Forwarded-Proto`` would otherwise make us build an
    ``http://`` redirect_uri for an https site -- a mismatch that is tedious to
    diagnose from the provider's error alone.
    """
    if settings.OAUTH_REDIRECT_BASE_URL:
        return f"{settings.OAUTH_REDIRECT_BASE_URL}/auth/callback/{provider}"

    url = request.url_for("oauth_callback", provider=provider)
    if settings.SESSION_COOKIE_SECURE and url.scheme == "http":
        url = url.replace(scheme="https")
    return str(url)


# --- cookies ---------------------------------------------------------------


def _set_state_cookie(response, token: str) -> None:
    response.set_cookie(
        key=settings.OAUTH_STATE_COOKIE_NAME,
        value=token,
        max_age=settings.OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        # Lax rather than the session cookie's None: the only request that
        # needs to carry this is the top-level navigation the provider sends
        # the browser on, and Lax allows exactly that and nothing else.
        samesite=settings.OAUTH_STATE_COOKIE_SAMESITE,
        domain=settings.SESSION_COOKIE_DOMAIN,
        path=settings.SESSION_COOKIE_PATH,
    )


def _clear_state_cookie(response) -> None:
    """Single-use: the state is spent whether or not the callback succeeded."""
    response.delete_cookie(
        key=settings.OAUTH_STATE_COOKIE_NAME,
        path=settings.SESSION_COOKIE_PATH,
        domain=settings.SESSION_COOKIE_DOMAIN,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.OAUTH_STATE_COOKIE_SAMESITE,
    )


def _set_link_cookie(response, token: str) -> None:
    """Park a pending link in an httpOnly cookie.

    A cookie and not a query parameter, even though the redirect that follows
    would carry one perfectly well: this token names a specific account and
    authorises attaching an identity to it once a password is produced. In a
    URL it would be written to history and to every log between here and the
    browser. SameSite=None because the SPA fetches with it cross-site.
    """
    response.set_cookie(
        key=settings.OAUTH_LINK_COOKIE_NAME,
        value=token,
        max_age=settings.OAUTH_PENDING_LINK_TTL_SECONDS,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        domain=settings.SESSION_COOKIE_DOMAIN,
        path=settings.SESSION_COOKIE_PATH,
    )


def _clear_link_cookie(response) -> None:
    response.delete_cookie(
        key=settings.OAUTH_LINK_COOKIE_NAME,
        path=settings.SESSION_COOKIE_PATH,
        domain=settings.SESSION_COOKIE_DOMAIN,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
    )


# --- provider legs ---------------------------------------------------------


@router.get("/{provider}/login", name="oauth_login")
@limiter.limit(settings.LOGIN_RATE_LIMIT_PER_IP, key_func=ip_key)
def oauth_login(provider: str, request: Request):
    """Send the browser to the provider's consent screen."""
    try:
        config = get_provider(provider)
    except OAuthError as error:
        return _error_redirect(error.code)

    state, state_token = issue_state(config.name)
    redirect_uri = callback_url(request, config.name)

    response = RedirectResponse(
        authorization_url(config, redirect_uri, state), status_code=HTTP_302_FOUND
    )
    _set_state_cookie(response, state_token)
    return response


@router.get("/callback/{provider}", name="oauth_callback")
@limiter.limit(settings.LOGIN_RATE_LIMIT_PER_IP, key_func=ip_key)
def oauth_callback(
    provider: str,
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db=Depends(get_db),
):
    """Complete the flow: sign in, or park the attempt behind a password."""
    try:
        config = get_provider(provider)
    except OAuthError as oauth_error:
        return _error_redirect(oauth_error.code)

    try:
        # CSRF first, before the code is spent or any lookup happens. A
        # callback we did not initiate gets no further than this line.
        verify_state(
            request.cookies.get(settings.OAUTH_STATE_COOKIE_NAME), state, config.name
        )

        if error:
            # The user declined at the consent screen, or the provider refused.
            # Their own wording is not passed on -- only that it did not happen.
            raise OAuthError(
                ERROR_ACCESS_DENIED, "Sign-in was not completed.", status=400
            )
        if not code:
            raise OAuthError(
                ERROR_ACCESS_DENIED, "Sign-in was not completed.", status=400
            )

        access_token = exchange_code(config, code, callback_url(request, config.name))
        identity = fetch_identity(config, access_token)
        resolution = resolve_account(db, identity)
    except OAuthError as oauth_error:
        # The state is spent by being *used*, not by succeeding: leaving a
        # valid one in the browser after a failure would keep a second callback
        # attempt viable for the rest of its ten minutes.
        failed = _error_redirect(oauth_error.code)
        _clear_state_cookie(failed)
        return failed

    if isinstance(resolution, PasswordConfirmationRequired):
        # Nothing has been written and no session exists. The browser goes to
        # the SPA's confirmation step carrying only the httpOnly cookie.
        response = RedirectResponse(
            _frontend_url(settings.FRONTEND_LINK_PATH), status_code=HTTP_302_FOUND
        )
        _set_link_cookie(
            response, issue_pending_link(resolution.user, resolution.identity)
        )
        _clear_state_cookie(response)
        return response

    # The same cookie the email/password flow issues, from the same helper.
    # An OAuth session is not a second kind of session.
    response = RedirectResponse(settings.FRONTEND_URL, status_code=HTTP_302_FOUND)
    set_session_cookie(response, create_access_token(resolution.user.id))
    _clear_state_cookie(response)
    return response


# --- link confirmation -----------------------------------------------------


class LinkConfirmation(BaseModel):
    password: str


@router.get("/link/pending", name="oauth_link_pending")
def oauth_link_pending(request: Request):
    """Describe the sign-in that is waiting on a password.

    The SPA cannot read the httpOnly cookie, so this is how the confirmation
    screen learns which account and which provider it is asking about. It
    returns only what that screen has to render, and only to a browser already
    holding the cookie -- which the provider callback is the sole issuer of.
    """
    try:
        pending = read_pending_link(request.cookies.get(settings.OAUTH_LINK_COOKIE_NAME))
    except OAuthError as error:
        return JSONResponse(
            {"detail": error.detail, "auth_error": error.code},
            status_code=error.status,
        )

    return {"provider": pending.identity.provider, "email": pending.email}


@router.post("/link/confirm", name="oauth_link_confirm")
@limiter.limit(settings.LOGIN_RATE_LIMIT_PER_IP, key_func=ip_key)
def oauth_link_confirm(
    body: LinkConfirmation,
    request: Request,
    db=Depends(get_db),
):
    """Verify the password, then link the identity and open the session.

    This is the only place an OAuth identity is attached to a password-
    protected account. It is rate limited per IP for the same reason
    ``/auth/login`` is -- it takes a password and says whether it was right,
    which makes it a guessing oracle otherwise.
    """
    # Cookie-driven POST, so it needs the same custom-header check every other
    # cookie-driven write gets. There is no signed-in user here to hang it off.
    require_csrf_header(request)

    try:
        pending = read_pending_link(request.cookies.get(settings.OAUTH_LINK_COOKIE_NAME))
        user = confirm_pending_link(db, pending, body.password)
    except OAuthError as error:
        failed = JSONResponse(
            {"detail": error.detail, "auth_error": error.code},
            status_code=error.status,
        )
        # A wrong password leaves the pending link in place so the user can
        # simply try again; anything else has spent it, so it is cleared.
        if error.code != ERROR_INVALID_PASSWORD:
            _clear_link_cookie(failed)
        return failed

    response = JSONResponse({"status": "ok", "email": user.email})
    set_session_cookie(response, create_access_token(user.id))
    _clear_link_cookie(response)
    return response


@router.post("/link/cancel", name="oauth_link_cancel")
def oauth_link_cancel(request: Request):
    """Abandon a pending link. Nothing was written, so nothing is undone."""
    require_csrf_header(request)
    response = JSONResponse({"status": "cancelled"})
    _clear_link_cookie(response)
    return response
