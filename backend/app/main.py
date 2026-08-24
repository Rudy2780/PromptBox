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

def create_app() -> FastAPI:
    """Build the application.

    A factory rather than module-level construction so the documentation
    switch can actually be tested at both settings.
    """
    docs_enabled = settings.ENABLE_API_DOCS

    application = FastAPI(
        title="PromptBox API",
        # Passing None removes the route entirely (404), rather than leaving it
        # served but empty. Disabling openapi_url alone would also disable the
        # UIs, but all three are named explicitly so the intent is legible.
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    # slowapi reads the limiter off app.state and needs a handler registered to
    # turn RateLimitExceeded into a 429 rather than an unhandled 500.
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # allow_credentials=True is required for the session cookie to be sent on
    # cross-site requests. It also means allow_origins must stay an explicit
    # allowlist -- with credentials, a wildcard is rejected by browsers, and the
    # allowlist is what stops another origin from passing the preflight that the
    # CSRF header check depends on.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    )

    application.include_router(api_router)

    @application.get("/")
    def root():
        return {"status": "PromptBox backend running"}

    return application


# Module-level instance for `uvicorn app.main:app`.
app = create_app()
