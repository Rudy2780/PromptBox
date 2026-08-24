"""Rate limiting for the endpoints that cost money to serve.

Two independent limits are applied to each protected endpoint:

* **per user** - one authenticated account cannot burn the provider budget or
  monopolise workers, regardless of how many hosts it calls from.
* **per IP** - one host cannot sidestep the per-user limit by registering
  several accounts.

Both must pass. ``user_key`` reads ``request.state.user_id``, which
``get_current_user`` sets while resolving the route's auth dependency -- that
runs before the endpoint body, and therefore before the limiter check.

Storage is in-process. That is correct for a single web instance; running more
than one instance means each enforces the limit separately, so a shared backend
(``storage_uri="redis://..."``) is required before scaling out.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import settings


def user_key(request: Request) -> str:
    """Rate limit bucket for the authenticated caller.

    Falls back to the source address for unauthenticated requests so that a
    misconfigured route can never silently share one unlimited bucket.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        return f"anon-ip:{get_remote_address(request)}"
    return f"user:{user_id}"


def ip_key(request: Request) -> str:
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=ip_key,
    enabled=settings.RATE_LIMIT_ENABLED,
    headers_enabled=True,
)
