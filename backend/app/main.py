from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.config import settings
from app.rate_limit import limiter

# NOTE: schema creation deliberately does NOT happen here. Importing this module
# must not touch the database. Run migrations explicitly before starting the
# server:  python -m app.migrations   (see app/migrations.py)

app = FastAPI(title="PromptBox API")

# slowapi reads the limiter off app.state and needs a handler registered to
# turn RateLimitExceeded into a 429 rather than an unhandled 500.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# allow_credentials=True is required for the session cookie to be sent on
# cross-site requests. It also means allow_origins must stay an explicit
# allowlist -- with credentials, a wildcard is rejected by browsers, and the
# allowlist is what stops another origin from passing the preflight that the
# CSRF header check depends on.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

app.include_router(api_router)

@app.get("/")
def root():
    return {"status": "PromptBox backend running"}
