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


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./promptbox.db"
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
