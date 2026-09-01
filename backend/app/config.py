import os
from dotenv import load_dotenv

load_dotenv()

# Minimum entropy we accept for the HS256 signing key. HS256 is symmetric, so a
# guessable secret means anyone can mint a token for any user id.
MIN_JWT_SECRET_LENGTH = 32


def _require_jwt_secret() -> str:
    """Return the configured JWT secret, or fail fast at import time.

    Deliberately raises rather than falling back to a default: a fallback secret
    that ships in source (or in the README) is equivalent to no authentication
    at all. RuntimeError rather than `assert` because assertions are stripped
    under `python -O`, which is exactly when you least want this check gone.
    """
    secret = os.environ.get("JWT_SECRET")

    if secret is None or not secret.strip():
        raise RuntimeError(
            "JWT_SECRET is not set. Generate one with "
            "`python -c \"import secrets; print(secrets.token_urlsafe(48))\"` "
            "and set it in the environment (backend/.env locally, the service "
            "environment in production). There is no default."
        )

    secret = secret.strip()

    if len(secret) < MIN_JWT_SECRET_LENGTH:
        raise RuntimeError(
            f"JWT_SECRET must be at least {MIN_JWT_SECRET_LENGTH} characters; "
            f"got {len(secret)}. Generate one with "
            "`python -c \"import secrets; print(secrets.token_urlsafe(48))\"`."
        )

    return secret


def _require_database_url() -> str:
    """Return the configured database URL, or fail fast at import time.

    Mirrors ``_require_jwt_secret``. The previous ``or "sqlite:///./promptbox.db"``
    fallback meant a missing or misspelled DATABASE_URL silently started the
    application against an empty local SQLite file rather than the real
    database -- a failure that surfaces much later as absent data instead of
    at startup, and one that looks identical to a working deployment.
    """
    url = os.environ.get("DATABASE_URL")

    if url is None or not url.strip():
        raise RuntimeError(
            "DATABASE_URL is not set. Set it in the environment (backend/.env "
            "locally, the service environment in production), e.g. "
            "postgresql://user:password@host/dbname?sslmode=require. "
            "There is no default."
        )

    return url.strip()


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    DATABASE_URL = _require_database_url()
    JWT_SECRET = _require_jwt_secret()

    # --- Rate limiting -----------------------------------------------------
    # The LLM endpoints spend real money per call, so they are limited on two
    # independent axes: per authenticated user (stops one account burning the
    # budget) and per source IP (stops one host cycling through accounts).
    RATE_LIMIT_ENABLED = _env_flag("RATE_LIMIT_ENABLED", True)
    LLM_RATE_LIMIT_PER_USER = os.getenv("LLM_RATE_LIMIT_PER_USER") or "30/minute"
    LLM_RATE_LIMIT_PER_IP = os.getenv("LLM_RATE_LIMIT_PER_IP") or "60/minute"
    # Key validation is cheap upstream but is the most abusable endpoint (it
    # answers "is this stolen key live?"), so it is held much tighter.
    VALIDATE_KEY_RATE_LIMIT_PER_USER = (
        os.getenv("VALIDATE_KEY_RATE_LIMIT_PER_USER") or "10/minute"
    )
    VALIDATE_KEY_RATE_LIMIT_PER_IP = (
        os.getenv("VALIDATE_KEY_RATE_LIMIT_PER_IP") or "20/minute"
    )
    # Auth endpoints are limited per IP: there is no authenticated identity to
    # key on yet, and the point is to slow credential stuffing and password
    # guessing. bcrypt at cost 12 also makes each attempt expensive to serve,
    # so an unthrottled login is a cheap CPU-exhaustion vector.
    LOGIN_RATE_LIMIT_PER_IP = os.getenv("LOGIN_RATE_LIMIT_PER_IP") or "10/minute"
    REGISTER_RATE_LIMIT_PER_IP = (
        os.getenv("REGISTER_RATE_LIMIT_PER_IP") or "5/minute"
    )

    # --- API documentation -------------------------------------------------
    # /docs, /redoc and /openapi.json are off unless explicitly switched on.
    # Defaulting to off rather than keying off an ENVIRONMENT string means a
    # missing or misspelled variable fails closed: the worst case is a
    # developer without Swagger, not a production deployment publishing an
    # interactive client for its own API.
    ENABLE_API_DOCS = _env_flag("ENABLE_API_DOCS", False)

    # --- Session cookie ----------------------------------------------------
    # The session JWT is delivered as an httpOnly cookie so page scripts cannot
    # read it. Because the SPA (vercel.app) and the API (onrender.com) are
    # different registrable domains, every API call is a *cross-site* request:
    #   - SameSite=Strict never sends the cookie cross-site at all.
    #   - SameSite=Lax sends it only on top-level navigations, not on fetch().
    # Both would break authentication outright, so SameSite=None is required
    # for this topology, and browsers only accept None together with Secure.
    # Losing SameSite as a CSRF defence is compensated for by the strict CORS
    # origin allowlist plus the custom-header check in dependencies/auth.py.
    # Deploying the API and the SPA on one domain would allow Lax; override
    # SESSION_COOKIE_SAMESITE=lax if that ever happens.
    SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME") or "promptbox_session"
    SESSION_COOKIE_SAMESITE = (os.getenv("SESSION_COOKIE_SAMESITE") or "none").lower()
    SESSION_COOKIE_SECURE = _env_flag("SESSION_COOKIE_SECURE", True)
    SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN") or None
    SESSION_COOKIE_PATH = "/"

    # --- Token claims ------------------------------------------------------
    ACCESS_TOKEN_TTL_HOURS = int(os.getenv("ACCESS_TOKEN_TTL_HOURS") or 24)
    JWT_AUDIENCE = os.getenv("JWT_AUDIENCE") or "promptbox-web"
    JWT_ISSUER = os.getenv("JWT_ISSUER") or "promptbox-api"

    # --- OAuth providers ---------------------------------------------------
    # Each provider is optional: PromptBox runs perfectly well with only
    # email/password, so a missing GOOGLE_CLIENT_ID must not stop the service
    # from booting the way a missing JWT_SECRET does. What *is* fail-fast is a
    # half-configured provider (see _validate_oauth_config): an id without a
    # secret is always a deployment mistake, and letting it through turns into
    # an opaque 401 from the provider during the token exchange instead of a
    # clear error at startup.
    #
    # The secrets below are read here and used in exactly one place -- the
    # server-side token exchange in services/oauth_service.py. They never reach
    # a response body, a redirect URL, or a cookie.
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID") or None
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET") or None
    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID") or None
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET") or None

    # Where the browser is sent once a provider callback has established a
    # session. Required as soon as any provider is configured: handing control
    # back to the SPA is the last thing the callback does, and there is no safe
    # default to guess.
    FRONTEND_URL = (os.getenv("FRONTEND_URL") or "").rstrip("/") or None

    # The API's own public origin, used to build the ``redirect_uri`` sent to
    # the provider. It has to match what is registered in the Google/GitHub
    # console character for character, so it is settable explicitly. When it is
    # unset the callback URL is derived from the incoming request instead (see
    # oauth_service.callback_url), which is what local development wants.
    OAUTH_REDIRECT_BASE_URL = (
        os.getenv("OAUTH_REDIRECT_BASE_URL") or ""
    ).rstrip("/") or None

    # The OAuth `state` value is carried in its own short-lived cookie and
    # compared against the one the provider echoes back. Ten minutes is the
    # length of a slow consent screen, not the length of a session.
    OAUTH_STATE_COOKIE_NAME = (
        os.getenv("OAUTH_STATE_COOKIE_NAME") or "promptbox_oauth_state"
    )
    OAUTH_STATE_TTL_SECONDS = int(os.getenv("OAUTH_STATE_TTL_SECONDS") or 600)
    # SameSite=Lax, not None: the callback arrives as a top-level navigation
    # from the provider, which Lax allows, and Lax is the tighter of the two.
    # (The session cookie cannot use Lax -- it has to ride on cross-site
    # fetch() calls from the SPA -- but this one never does.)
    OAUTH_STATE_COOKIE_SAMESITE = "lax"

    # How long to wait on Google/GitHub. A hung provider must not hold a worker
    # open indefinitely.
    OAUTH_HTTP_TIMEOUT_SECONDS = float(os.getenv("OAUTH_HTTP_TIMEOUT_SECONDS") or 10)

    # A sign-in that matched a password-protected account is parked in this
    # cookie until the user proves the password. Unlike the state cookie this
    # one MUST be SameSite=None: the confirmation is an ordinary cross-site
    # fetch() from the SPA, which Lax would not send. It therefore inherits the
    # session cookie's CSRF compensation -- the origin allowlist plus the
    # X-Requested-With check, which the confirm endpoint applies explicitly.
    OAUTH_LINK_COOKIE_NAME = (
        os.getenv("OAUTH_LINK_COOKIE_NAME") or "promptbox_oauth_link"
    )
    OAUTH_PENDING_LINK_TTL_SECONDS = int(
        os.getenv("OAUTH_PENDING_LINK_TTL_SECONDS") or 600
    )

    # Where the SPA asks for the password. Kept next to FRONTEND_URL because
    # they are pasted together into a redirect; both are paths on the SPA, not
    # on this API.
    FRONTEND_LOGIN_PATH = os.getenv("FRONTEND_LOGIN_PATH") or "/login"
    FRONTEND_LINK_PATH = os.getenv("FRONTEND_LINK_PATH") or "/link-account"

    # --- CORS --------------------------------------------------------------
    # Must stay an explicit allowlist: with credentialed cookies a wildcard
    # origin is both rejected by browsers and the thing standing between the
    # API and cross-site request forgery.
    CORS_ORIGINS = [
        origin.strip()
        for origin in (
            os.getenv("CORS_ORIGINS")
            or "http://localhost:5173,https://prompt-box-seven.vercel.app"
        ).split(",")
        if origin.strip()
    ]


settings = Settings()


def _validate_cookie_policy(config: Settings) -> None:
    """Reject cookie settings that browsers would silently discard."""
    allowed = {"strict", "lax", "none"}
    if config.SESSION_COOKIE_SAMESITE not in allowed:
        raise RuntimeError(
            f"SESSION_COOKIE_SAMESITE must be one of {sorted(allowed)}; "
            f"got {config.SESSION_COOKIE_SAMESITE!r}."
        )
    if config.SESSION_COOKIE_SAMESITE == "none" and not config.SESSION_COOKIE_SECURE:
        raise RuntimeError(
            "SESSION_COOKIE_SAMESITE=none requires SESSION_COOKIE_SECURE=true; "
            "browsers reject SameSite=None cookies that are not Secure, which "
            "would silently log every user out."
        )


_validate_cookie_policy(settings)

def _validate_oauth_config(config: Settings) -> None:
    """Reject half-configured OAuth providers at startup.

    A client id without its secret (or the reverse) is never intentional. The
    failure it produces at runtime is a generic ``invalid_client`` from the
    provider, mid-login, for a user who did nothing wrong -- so it is caught
    here instead, where the message can name the missing variable.

    Note what is *not* required: nothing at all. A deployment with no provider
    credentials simply has no OAuth buttons that work, which is the state this
    application shipped in before now.
    """
    pairs = (
        ("google", "GOOGLE_CLIENT_ID", config.GOOGLE_CLIENT_ID,
         "GOOGLE_CLIENT_SECRET", config.GOOGLE_CLIENT_SECRET),
        ("github", "GITHUB_CLIENT_ID", config.GITHUB_CLIENT_ID,
         "GITHUB_CLIENT_SECRET", config.GITHUB_CLIENT_SECRET),
    )

    configured = []
    for provider, id_name, id_value, secret_name, secret_value in pairs:
        if bool(id_value) != bool(secret_value):
            missing = id_name if id_value is None else secret_name
            present = secret_name if id_value is None else id_name
            raise RuntimeError(
                f"{provider} OAuth is half-configured: {present} is set but "
                f"{missing} is not. Set both, or neither to disable "
                f"{provider} sign-in."
            )
        if id_value:
            configured.append(provider)

    if configured and not config.FRONTEND_URL:
        raise RuntimeError(
            "FRONTEND_URL is not set, but OAuth is configured for "
            f"{', '.join(configured)}. The provider callback finishes by "
            "redirecting the browser back to the single-page app, e.g. "
            "FRONTEND_URL=https://prompt-box-seven.vercel.app. There is no "
            "default."
        )


_validate_oauth_config(settings)
