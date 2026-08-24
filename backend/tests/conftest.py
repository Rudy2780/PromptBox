"""Test fixtures.

Every test in this suite runs against a dedicated SQLite file that is created,
truncated and deleted by these fixtures. The application's configured database
(``DATABASE_URL``) is never opened.

This used to be untrue: the cleanup fixture below called ``SessionLocal`` from
``app.database`` -- the *real* configured engine -- and deleted every row in
``prompt_versions`` and ``users`` before and after every single test. Running
the documented ``pytest tests`` command against a shared or production
``DATABASE_URL`` destroyed all data. The guard at module scope now makes that
failure mode impossible rather than merely unlikely.
"""

import os

# Must be set before ``app.config`` is imported anywhere: the application
# refuses to start without a JWT secret, by design (see app/config.py).
os.environ.setdefault(
    "JWT_SECRET", "test-only-secret-not-used-in-production-0123456789"
)

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_PATH = Path(__file__).parent / "test_promptbox.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"


def _assert_is_test_database(url: str) -> None:
    """Refuse to run against anything that isn't obviously a test database.

    Deliberately a raise and not an ``assert``: assertions are stripped under
    ``python -O``, and this is the one check that must never be optimised away.
    """
    if "test" not in str(url).lower():
        raise RuntimeError(
            f"Refusing to run the test suite against {url!r}: the database URL "
            "does not contain 'test'. The suite truncates every table it "
            "touches, so it must only ever point at a disposable database."
        )


# Checked at import time, i.e. during collection and before any test executes.
_assert_is_test_database(TEST_DATABASE_URL)

test_engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Re-checked against the engine's own resolved URL, in case the string above
# and what SQLAlchemy actually connected to ever diverge.
_assert_is_test_database(test_engine.url)

TestingSessionLocal = sessionmaker(
    bind=test_engine, autoflush=False, autocommit=False
)

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.rate_limit import limiter  # noqa: E402
from app.migrations import run_migrations  # noqa: E402
from app.models.prompt_version import PromptVersion  # noqa: E402
from app.models.user import UserInfo  # noqa: E402


# The session cookie is issued with Secure=True (required alongside
# SameSite=None). An HTTP cookie jar silently discards Secure cookies, so the
# test client must speak https for the real cookie attributes to be exercised
# rather than weakened just for tests.
TEST_BASE_URL = "https://testserver"


def _get_test_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Every route that depends on get_db now receives a session bound to the test
# engine instead of the application engine.
app.dependency_overrides[get_db] = _get_test_db


@pytest.fixture(scope="session", autouse=True)
def _test_schema():
    """Build the schema once per session, then remove the file entirely."""
    _assert_is_test_database(test_engine.url)
    run_migrations(test_engine)
    yield
    test_engine.dispose()
    for suffix in ("", "-wal", "-shm"):
        Path(str(TEST_DB_PATH) + suffix).unlink(missing_ok=True)


def _truncate() -> None:
    db = TestingSessionLocal()
    try:
        db.query(PromptVersion).delete(synchronize_session=False)
        db.query(UserInfo).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def clear_users():
    """Full cleanup for deterministic tests -- test database only."""
    _truncate()
    yield
    _truncate()


@pytest.fixture(autouse=True)
def _disable_rate_limiting():
    """Rate limits are off by default so unrelated tests don't trip them.

    The limiter uses in-process storage that persists across tests, so leaving
    it on would make results depend on test ordering and count. Tests that
    exercise limiting opt in with the `rate_limited` fixture below.
    """
    limiter.enabled = False
    limiter.reset()
    yield
    limiter.enabled = False
    limiter.reset()


@pytest.fixture
def rate_limited():
    """Opt in to real rate limiting for a single test, with clean storage."""
    limiter.reset()
    limiter.enabled = True
    yield limiter
    limiter.enabled = False
    limiter.reset()


@pytest.fixture
def authed_client(client):
    """A client authenticated as a freshly registered user.

    Tests use this rather than building an Authorization header by hand so the
    auth transport (bearer header vs. cookie) is defined in exactly one place.
    """
    credentials = {"email": "apiuser@example.com", "password": "password123"}
    client.post("/auth/register", json=credentials)
    res = client.post("/auth/login", json=credentials)
    assert res.status_code == 200, f"login failed in fixture: {res.text}"
    # The session rides in an httpOnly cookie that the TestClient cookie jar
    # stores and replays; only the CSRF header has to be set explicitly.
    client.headers.update({"X-Requested-With": "PromptBox"})
    return client


@pytest.fixture
def db_session():
    """A session bound to the test engine, for tests that seed rows directly."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app, base_url=TEST_BASE_URL)


@pytest.fixture
def make_authed_client():
    """Factory for independent signed-in clients.

    Each client gets its own cookie jar, which is what makes it possible to
    hold two distinct sessions at once -- needed by the cross-user isolation
    tests, where a single shared jar would silently overwrite the first
    session with the second.
    """

    def _make(email, password="password123"):
        c = TestClient(app, base_url=TEST_BASE_URL)
        c.post("/auth/register", json={"email": email, "password": password})
        res = c.post("/auth/login", json={"email": email, "password": password})
        assert res.status_code == 200, f"login failed: {res.text}"
        c.headers.update({"X-Requested-With": "PromptBox"})
        return c

    return _make
