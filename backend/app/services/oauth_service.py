"""Google and GitHub sign-in.

The shape of the flow is the same for both providers:

1. ``/auth/{provider}/login`` mints a random ``state``, stores it in a
   short-lived httpOnly cookie, and redirects to the provider's consent screen.
2. The provider sends the browser back to ``/auth/callback/{provider}`` with a
   ``code`` and the same ``state``.
3. The ``state`` is checked against the cookie *before anything else happens*.
4. The ``code`` is exchanged for an access token server-to-server. This is the
   only place the client secret is used; it never leaves this module.
5. The provider is asked who the user is, and the answer is only accepted if
   the provider says the email address is verified.
6. The identity is matched to an account (see ``resolve_account``) and the
   caller issues the ordinary session cookie.

What is deliberately *not* here: any trust in data the browser carried. The
code and state arrive via the user agent and are treated as untrusted; the
email and provider id come from a direct TLS call to the provider.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.oauth_identity import OAuthIdentity
from app.models.user import UserInfo
from app.utils.security import verify_password

GOOGLE = "google"
GITHUB = "github"


# --- error codes -----------------------------------------------------------
# Every OAuth failure resolves to one of these, and only these reach the
# browser. They travel in a query parameter on a redirect back to the SPA,
# which is precisely why they are a closed vocabulary of opaque slugs rather
# than exception text: a URL is written to browser history, sent in Referer
# headers, and logged by every proxy in between, so nothing that varies with
# user input, provider output or server state may appear in one.
#
# The SPA maps these to the sentences a person reads (frontend/src/oauthErrors.js).
ERROR_ACCESS_DENIED = "access_denied"
ERROR_INVALID_STATE = "invalid_state"
ERROR_EMAIL_UNVERIFIED = "email_unverified"
ERROR_PROVIDER_ERROR = "provider_error"
ERROR_PROVIDER_UNAVAILABLE = "provider_unavailable"
ERROR_LINK_EXPIRED = "link_expired"
ERROR_INVALID_PASSWORD = "invalid_password"

ERROR_CODES = frozenset(
    {
        ERROR_ACCESS_DENIED,
        ERROR_INVALID_STATE,
        ERROR_EMAIL_UNVERIFIED,
        ERROR_PROVIDER_ERROR,
        ERROR_PROVIDER_UNAVAILABLE,
        ERROR_LINK_EXPIRED,
        ERROR_INVALID_PASSWORD,
    }
)


class OAuthError(Exception):
    """A provider exchange that cannot be completed.

    ``code`` is the stable slug the browser is redirected with. ``detail`` is
    the longer server-side wording -- it is kept for logs and for the JSON
    responses of the XHR endpoints, and it never goes into a URL. Neither ever
    echoes what the provider sent back: provider error bodies have been known
    to quote the request parameters, and those include the authorization code.
    """

    def __init__(self, code: str, detail: str, status: int = 502):
        super().__init__(detail)
        # Guarded rather than trusted: this value ends up in a URL, so an
        # ad-hoc string introduced by a later edit must fail here and not
        # quietly become a query parameter.
        if code not in ERROR_CODES:
            raise ValueError(f"unknown OAuth error code: {code!r}")
        self.code = code
        self.detail = detail
        self.status = status


class ProviderNotConfigured(OAuthError):
    def __init__(self, provider: str):
        super().__init__(
            ERROR_PROVIDER_UNAVAILABLE,
            f"{provider} sign-in is not configured on this server.",
            status=503,
        )


class UnknownProvider(OAuthError):
    def __init__(self, provider: str):
        # Deliberately the same code as an unconfigured provider. Which of the
        # two it was is a fact about our deployment, not about the user, and
        # the distinction is only useful to somebody enumerating.
        super().__init__(
            ERROR_PROVIDER_UNAVAILABLE,
            f"Unknown sign-in provider: {provider!r}",
            status=404,
        )


@dataclass(frozen=True)
class ProviderIdentity:
    """Who the provider says this is.

    ``provider_user_id`` is the provider's own immutable identifier, which is
    what identities are keyed on. ``email`` is only ever populated when the
    provider reported it as verified -- an unverified address never reaches
    this object, so no caller has to remember to check a flag.
    """

    provider: str
    provider_user_id: str
    email: str


@dataclass(frozen=True)
class Provider:
    name: str
    authorize_url: str
    token_url: str
    scope: str
    client_id: str | None
    client_secret: str | None
    # Given an access token, return the verified identity. Provider-specific
    # because Google hands back an email in one call and GitHub does not.
    read_identity: Callable[[httpx.Client, str], ProviderIdentity]
    # Extra parameters for the consent screen URL.
    authorize_extras: dict[str, str]


def _http_client() -> httpx.Client:
    """The client used for every outbound provider call.

    A single seam, on purpose: the test suite swaps this for an
    ``httpx.MockTransport`` so that the URLs, form bodies and headers built
    below are exercised for real without a packet leaving the machine.
    """
    return httpx.Client(timeout=settings.OAUTH_HTTP_TIMEOUT_SECONDS)


def _json_or_error(response: httpx.Response, what: str) -> dict:
    if response.status_code >= 400:
        raise OAuthError(
            ERROR_PROVIDER_ERROR, f"The provider rejected the {what} request."
        )
    try:
        payload = response.json()
    except ValueError:
        raise OAuthError(
            ERROR_PROVIDER_ERROR,
            f"The provider returned an unreadable {what} response.",
        )
    if not isinstance(payload, (dict, list)):
        raise OAuthError(
            ERROR_PROVIDER_ERROR,
            f"The provider returned an unexpected {what} response.",
        )
    return payload


# --- Google ----------------------------------------------------------------


def _google_identity(client: httpx.Client, access_token: str) -> ProviderIdentity:
    """Read the OpenID Connect userinfo document.

    The token response also carries an ``id_token`` that could be verified
    against Google's JWKS instead. Calling userinfo directly is equivalent in
    trust -- it is our server talking to Google over TLS, not a token relayed
    through the browser -- and avoids shipping key-rotation handling for no
    additional guarantee.
    """
    response = client.get(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    profile = _json_or_error(response, "profile")

    subject = str(profile.get("sub") or "").strip()
    if not subject:
        raise OAuthError(
            ERROR_PROVIDER_ERROR, "Google did not return an account identifier."
        )

    email = str(profile.get("email") or "").strip()
    # Google sends this as a real boolean on the userinfo endpoint, but it has
    # historically been a string in some responses, so both are accepted -- and
    # anything else is treated as "not verified" rather than as truthy.
    verified = profile.get("email_verified")
    is_verified = verified is True or (
        isinstance(verified, str) and verified.strip().lower() == "true"
    )

    if not email or not is_verified:
        raise OAuthError(
            ERROR_EMAIL_UNVERIFIED,
            "Google did not report a verified email address for this account. "
            "PromptBox only links accounts by an email the provider has "
            "verified.",
            status=403,
        )

    return ProviderIdentity(GOOGLE, subject, email.lower())


# --- GitHub ----------------------------------------------------------------


def _github_identity(client: httpx.Client, access_token: str) -> ProviderIdentity:
    """Read the GitHub account id and its primary, verified email.

    Two calls, because ``/user`` is not enough. Its ``email`` field is the
    *public profile* email: it is null for most accounts, it is not necessarily
    verified, and the user can set it to anything. Linking on that would let
    someone claim another PromptBox account by typing its address into their
    GitHub profile. ``/user/emails`` (which is why the ``user:email`` scope is
    requested) is the authoritative list, and only the entry that is both
    ``primary`` and ``verified`` is accepted.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    account = _json_or_error(client.get("https://api.github.com/user", headers=headers), "profile")
    subject = str(account.get("id") or "").strip()
    if not subject:
        raise OAuthError(
            ERROR_PROVIDER_ERROR, "GitHub did not return an account identifier."
        )

    emails = _json_or_error(
        client.get("https://api.github.com/user/emails", headers=headers), "email"
    )
    if not isinstance(emails, list):
        raise OAuthError(
            ERROR_PROVIDER_ERROR, "GitHub returned an unexpected email response."
        )

    for entry in emails:
        if not isinstance(entry, dict):
            continue
        if entry.get("primary") is True and entry.get("verified") is True:
            address = str(entry.get("email") or "").strip()
            if address:
                return ProviderIdentity(GITHUB, subject, address.lower())

    raise OAuthError(
        ERROR_EMAIL_UNVERIFIED,
        "GitHub did not report a verified primary email address for this "
        "account. Verify your primary email address on GitHub and try again.",
        status=403,
    )


PROVIDERS: dict[str, Provider] = {
    GOOGLE: Provider(
        name=GOOGLE,
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        scope="openid email profile",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        read_identity=_google_identity,
        # No refresh token is wanted: PromptBox calls nothing on the user's
        # behalf after login, so it asks for the minimum and keeps nothing.
        authorize_extras={"access_type": "online", "prompt": "select_account"},
    ),
    GITHUB: Provider(
        name=GITHUB,
        authorize_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        # Required for /user/emails. Without it GitHub answers 403 there and
        # there is no verified address to link on.
        scope="user:email",
        client_id=settings.GITHUB_CLIENT_ID,
        client_secret=settings.GITHUB_CLIENT_SECRET,
        read_identity=_github_identity,
        authorize_extras={},
    ),
}


def get_provider(name: str) -> Provider:
    provider = PROVIDERS.get((name or "").strip().lower())
    if provider is None:
        raise UnknownProvider(name)
    if not provider.client_id or not provider.client_secret:
        raise ProviderNotConfigured(provider.name)
    return provider


def configured_providers() -> list[str]:
    return [
        name
        for name, provider in PROVIDERS.items()
        if provider.client_id and provider.client_secret
    ]


# --- state -----------------------------------------------------------------

STATE_TOKEN_TYPE = "oauth_state"


def issue_state(provider: str) -> tuple[str, str]:
    """Return ``(state, cookie_token)`` for a new authorization request.

    ``state`` goes to the provider in the URL; ``cookie_token`` goes to the
    browser in an httpOnly cookie. A forged callback needs both, and an
    attacker cannot set the cookie: it belongs to the API's origin and is not
    readable or writable from script.

    The cookie is a signed JWT rather than the raw value so that it also binds
    the provider and an expiry -- a state minted for Google cannot be replayed
    at the GitHub callback, and one left over from an abandoned login stops
    working after ``OAUTH_STATE_TTL_SECONDS``.

    It deliberately carries no ``sub`` claim. That is what stops this token
    from being presented as a session cookie: ``get_current_user`` rejects a
    token with no subject, so even though the signing key and audience are
    shared, a state token authenticates nobody.
    """
    state = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    cookie_token = jwt.encode(
        {
            "typ": STATE_TOKEN_TYPE,
            "state": state,
            "provider": provider,
            "iat": int(now.timestamp()),
            "exp": int(
                (now + timedelta(seconds=settings.OAUTH_STATE_TTL_SECONDS)).timestamp()
            ),
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    return state, cookie_token


def verify_state(cookie_token: str | None, returned_state: str | None, provider: str) -> None:
    """Raise unless the callback's ``state`` matches the one we issued.

    Every failure -- absent cookie, absent parameter, bad signature, expired,
    wrong provider, mismatched value -- is the same 400. Distinguishing them
    would tell whoever is probing which half of the check they got past.
    """
    rejected = OAuthError(
        ERROR_INVALID_STATE,
        "Sign-in could not be completed because the request could not be "
        "verified. Start again from the sign-in page.",
        status=400,
    )

    if not cookie_token or not returned_state:
        raise rejected

    try:
        claims = jwt.decode(
            cookie_token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
    except JWTError:
        raise rejected

    if claims.get("typ") != STATE_TOKEN_TYPE:
        raise rejected
    if claims.get("provider") != provider:
        raise rejected

    expected = claims.get("state")
    # Constant-time: the value is a secret being compared against attacker-
    # supplied input, which is the textbook case for it.
    if not isinstance(expected, str) or not secrets.compare_digest(
        expected, returned_state
    ):
        raise rejected


# --- the flow --------------------------------------------------------------


def authorization_url(provider: Provider, redirect_uri: str, state: str) -> str:
    params = {
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": provider.scope,
        "state": state,
        **provider.authorize_extras,
    }
    return f"{provider.authorize_url}?{urlencode(params)}"


def exchange_code(provider: Provider, code: str, redirect_uri: str) -> str:
    """Trade the authorization code for an access token, server to server.

    The client secret appears here and nowhere else in the request path. It is
    sent in the POST body to the provider's token endpoint over TLS, and the
    token that comes back is used within this request and discarded -- it is
    not stored, not logged, and not returned to the browser.
    """
    with _http_client() as client:
        response = client.post(
            provider.token_url,
            data={
                "client_id": provider.client_id,
                "client_secret": provider.client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            # GitHub answers form-encoded unless asked otherwise; Google
            # always answers JSON. Asking explicitly makes both the same.
            headers={"Accept": "application/json"},
        )
        payload = _json_or_error(response, "token")

    if not isinstance(payload, dict) or payload.get("error"):
        # The provider's own error text is not passed through: its body echoes
        # request parameters, and those include the authorization code.
        raise OAuthError(ERROR_PROVIDER_ERROR, "The provider declined to issue a token.")

    token = str(payload.get("access_token") or "").strip()
    if not token:
        raise OAuthError(
            ERROR_PROVIDER_ERROR, "The provider did not return an access token."
        )
    return token


def fetch_identity(provider: Provider, access_token: str) -> ProviderIdentity:
    with _http_client() as client:
        return provider.read_identity(client, access_token)


# --- account resolution ----------------------------------------------------


def find_identity(db: Session, identity: ProviderIdentity) -> OAuthIdentity | None:
    return (
        db.query(OAuthIdentity)
        .filter(
            OAuthIdentity.provider == identity.provider,
            OAuthIdentity.provider_user_id == identity.provider_user_id,
        )
        .first()
    )


def find_user_by_email(db: Session, email: str) -> UserInfo | None:
    """Look up an account by address, case-insensitively.

    Addresses are matched without regard to case because that is how mail
    works, and because the provider hands back a normalised address while a
    hand-typed registration may not have been. ``order_by(id)`` makes the
    result deterministic in the one case where several rows can match: the
    unique index on ``users.email`` is case-*sensitive*, so a database that
    predates this can hold both ``Ada@example.com`` and ``ada@example.com``.
    Linking to the older of the two is arbitrary but stable, which is what
    matters -- the same login must not land on a different account next time.
    """
    return (
        db.query(UserInfo)
        .filter(func.lower(UserInfo.email) == email.lower())
        .order_by(UserInfo.id)
        .first()
    )


def link_identity(db: Session, user: UserInfo, identity: ProviderIdentity) -> OAuthIdentity:
    row = OAuthIdentity(
        user_id=user.id,
        provider=identity.provider,
        provider_user_id=identity.provider_user_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@dataclass(frozen=True)
class SignedIn:
    """The identity resolved to an account outright. Issue a session."""

    user: UserInfo


@dataclass(frozen=True)
class PasswordConfirmationRequired:
    """The identity matches an account that is protected by a password.

    Nothing has been written: no identity row, no session. The caller must
    park the attempt behind a password check before either happens.
    """

    user: UserInfo
    identity: ProviderIdentity


AccountResolution = SignedIn | PasswordConfirmationRequired


def resolve_account(db: Session, identity: ProviderIdentity) -> AccountResolution:
    """Find, link, or create the account this provider identity belongs to.

    Four cases, in this order:

    1. **Known identity.** A row already exists for (provider, provider id) --
       sign that account in. Checked first so a login never depends on the
       email, which the user may since have changed at the provider.
    2. **Known email, no password.** An account already uses this address and
       has no password set, which means it exists only because some earlier
       verified OAuth login created it. Linking a second provider to it (Google
       today, GitHub tomorrow) joins two identities that the providers have
       both vouched for, and there is no password for the new identity to gain
       access *around* -- so it is done automatically.
    3. **Known email, password set.** Someone registered this address with a
       password. A verified email proves the person controls the mailbox, which
       is not the same as proving they are the account holder: mailboxes get
       recycled, corporate addresses change hands, and provider accounts get
       taken over. Linking here would hand the whole account to whoever holds
       the address today, so instead nothing is written and the caller is told
       to ask for the password first.
    4. **Neither.** Create an account with no password. It can sign in through
       this provider, and through any other it later links.
    """
    existing = find_identity(db, identity)
    if existing is not None:
        user = db.query(UserInfo).filter(UserInfo.id == existing.user_id).first()
        if user is not None:
            return SignedIn(user)
        # The identity outlived its user, which the FK's ON DELETE CASCADE is
        # supposed to prevent. Drop the orphan rather than 500, and fall
        # through to treat this as a first-time login.
        db.delete(existing)
        db.commit()

    user = find_user_by_email(db, identity.email)

    if user is not None:
        if user.hashed_password is not None:
            return PasswordConfirmationRequired(user, identity)
        link_identity(db, user, identity)
        return SignedIn(user)

    user = UserInfo(email=identity.email, hashed_password=None)
    db.add(user)
    db.commit()
    db.refresh(user)

    link_identity(db, user, identity)
    return SignedIn(user)


# --- pending link ----------------------------------------------------------

PENDING_LINK_TOKEN_TYPE = "oauth_pending_link"


def issue_pending_link(user: UserInfo, identity: ProviderIdentity) -> str:
    """Mint the token that stands for "this login is waiting on a password".

    Built exactly like the state token above, for the same reasons: signed with
    the application key, short-lived, and carrying no ``sub`` claim so it can
    never be presented as a session cookie.

    It names the target account by id as well as by provider identity. Checking
    the id again at confirmation time is what stops the window between the two
    requests from mattering -- if the address has been reassigned to a
    different account in the interim, the token no longer matches and the link
    does not happen.
    """
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "typ": PENDING_LINK_TOKEN_TYPE,
            "uid": int(user.id),
            "provider": identity.provider,
            "provider_user_id": identity.provider_user_id,
            "email": identity.email,
            "iat": int(now.timestamp()),
            "exp": int(
                (now + timedelta(seconds=settings.OAUTH_PENDING_LINK_TTL_SECONDS)).timestamp()
            ),
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )


@dataclass(frozen=True)
class PendingLink:
    user_id: int
    identity: ProviderIdentity
    email: str


def read_pending_link(token: str | None) -> PendingLink:
    """Decode a pending-link token, or raise ``link_expired``.

    Absent, tampered with, expired, or the wrong kind of token all produce the
    same outcome. The remedy is identical in every case -- start the sign-in
    again -- so there is nothing to gain from telling them apart, and something
    to lose in describing our token format to whoever is probing.
    """
    expired = OAuthError(
        ERROR_LINK_EXPIRED,
        "This sign-in is no longer waiting to be confirmed. Start again from "
        "the sign-in page.",
        status=400,
    )

    if not token:
        raise expired

    try:
        claims = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
    except JWTError:
        raise expired

    if claims.get("typ") != PENDING_LINK_TOKEN_TYPE:
        raise expired

    provider = claims.get("provider")
    provider_user_id = claims.get("provider_user_id")
    email = claims.get("email")
    user_id = claims.get("uid")

    if provider not in PROVIDERS or not provider_user_id or not email:
        raise expired
    if not isinstance(user_id, int):
        raise expired

    return PendingLink(
        user_id=user_id,
        identity=ProviderIdentity(provider, str(provider_user_id), str(email)),
        email=str(email),
    )


def confirm_pending_link(db: Session, pending: PendingLink, password: str) -> UserInfo:
    """Verify the password and, only then, write the identity row.

    Re-reads the account rather than trusting the token's copy of it, and
    re-checks every precondition that held when the token was issued. The token
    is a claim about a state of the world ten minutes ago; the row is the state
    of the world now.
    """
    user = db.query(UserInfo).filter(UserInfo.id == pending.user_id).first()

    # Gone, or since converted to an OAuth-only account -- either way this
    # token describes an account that no longer exists in the shape it named.
    if user is None or user.hashed_password is None:
        raise OAuthError(
            ERROR_LINK_EXPIRED,
            "This sign-in is no longer waiting to be confirmed. Start again "
            "from the sign-in page.",
            status=400,
        )

    # The address must still belong to this account. Without this a token
    # could outlive an email change and attach the identity to an account
    # whose owner never saw the provider consent screen.
    if user.email.lower() != pending.identity.email:
        raise OAuthError(
            ERROR_LINK_EXPIRED,
            "This sign-in is no longer waiting to be confirmed. Start again "
            "from the sign-in page.",
            status=400,
        )

    if not verify_password(password, user.hashed_password):
        raise OAuthError(
            ERROR_INVALID_PASSWORD,
            "That password is not correct.",
            status=401,
        )

    # Between issuing the token and confirming it, the same provider account
    # may have been linked by another tab. Treat that as done rather than
    # tripping the unique constraint.
    already = find_identity(db, pending.identity)
    if already is None:
        link_identity(db, user, pending.identity)

    return user
