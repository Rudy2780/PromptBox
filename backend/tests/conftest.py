"""Test fixtures.

Every test in this suite runs against the Postgres database named by
``TEST_DATABASE_URL`` -- a dedicated Neon branch, and within it a database of
the suite's own -- whose tables these fixtures truncate between tests. The
application's configured database (``DATABASE_URL``) is never opened, and the
settings the suite asserts against are pinned below for the same reason: so
results do not vary with local config.

This used to be untrue: the cleanup fixture below called ``SessionLocal`` from
``app.database`` -- the *real* configured engine -- and deleted every row in
``prompt_versions`` and ``users`` before and after every single test. Running
the documented ``pytest tests`` command against a shared or production
``DATABASE_URL`` destroyed all data. The guard at module scope now makes that
failure mode impossible rather than merely unlikely.
"""

import os

from dotenv import load_dotenv

# Must be set before ``app.config`` is imported anywhere: the application
# refuses to start without a JWT secret, by design (see app/config.py).
os.environ.setdefault(
    "JWT_SECRET", "test-only-secret-not-used-in-production-0123456789"
)

# Config the suite makes assertions about is pinned outright rather than with
# ``setdefault``: these tests assert the behaviour these values drive -- the
# docs endpoints return 404, and the session cookie carries Secure with
# SameSite=None -- so the result must not depend on the machine running them.
# A developer's backend/.env legitimately sets ENABLE_API_DOCS=true and a lax,
# non-Secure cookie so the app works over plain HTTP locally, and that used to
# fail four tests. ``load_dotenv`` never overwrites a variable already in
# os.environ, and this module is imported before ``app.config``, so assigning
# here wins over both .env and any exported shell variable.
os.environ["ENABLE_API_DOCS"] = "false"
os.environ["SESSION_COOKIE_SAMESITE"] = "none"
os.environ["SESSION_COOKIE_SECURE"] = "true"

# TEST_DATABASE_URL is read below, before anything imports ``app.config`` and
# runs this for us. Loading it here rather than relying on that import keeps
# the ordering explicit -- and it must come *after* the pins above, because
# load_dotenv leaves variables that are already set alone.
load_dotenv()

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

# The database the suite runs in, inside whatever branch TEST_DATABASE_URL
# names. Neon generates branch endpoint hostnames (ep-<word>-<word>-<id>) and a
# branch inherits its parent's database name, so a branch URL on its own says
# nothing about being a test target. Selecting a database of our own is what
# makes the guard below able to tell the difference -- and means that even a
# TEST_DATABASE_URL misaimed at production would land in a database the
# application never opens.
TEST_DATABASE_NAME = "promptbox_test"


def _safe_url(url) -> str:
    """A URL reduced to the parts that are safe to put in a message.

    The test connection string is a credentialed Postgres URL that must not
    reach a traceback, a log or CI output, so nothing here ever renders the
    host, user or password.
    """
    safe = make_url(str(url))
    return f"{safe.drivername}:///{safe.database}"


def _test_database_url():
    """Build the suite's URL from the environment. Never hardcoded."""
    raw = os.environ.get("TEST_DATABASE_URL")

    if raw is None or not raw.strip():
        raise RuntimeError(
            "TEST_DATABASE_URL is not set. The suite needs a disposable "
            "Postgres database of its own -- set TEST_DATABASE_URL in "
            "backend/.env to a dedicated branch. There is no default, and it "
            "must never point at the same database as DATABASE_URL."
        )

    return _direct_endpoint(make_url(raw.strip())).set(database=TEST_DATABASE_NAME)


def _direct_endpoint(url):
    """Route around Neon's connection pooler.

    Neon offers each branch a pooled host (``-pooler``) and a direct one. The
    pooler is PgBouncer in transaction mode, which is wrong for a test suite in
    two ways: it refuses ``search_path`` as a startup parameter, and it does not
    reset session GUCs between checkouts, so a setting left behind by one
    connection turns up on an unrelated one later. Both bite during schema
    setup. Tests open few connections and want a session to themselves, so they
    take the direct endpoint. Production keeps the pooler -- this rewrites only
    the URL the suite uses, and is a no-op on a URL that is already direct.
    """
    if url.host and "-pooler" in url.host:
        return url.set(host=url.host.replace("-pooler", "", 1))
    return url


def _assert_is_test_database(url) -> None:
    """Refuse to run against anything that isn't obviously a test database.

    Deliberately a raise and not an ``assert``: assertions are stripped under
    ``python -O``, and this is the one check that must never be optimised away.
    The URL itself is deliberately kept out of the message -- see ``_safe_url``.
    """
    if "test" not in str(url).lower():
        raise RuntimeError(
            f"Refusing to run the test suite against {_safe_url(url)}: the "
            "database URL does not contain 'test'. The suite truncates every "
            "table it touches, so it must only ever point at a disposable "
            "database."
        )


def _assert_is_not_the_application_database(url) -> None:
    """The suite must never share a database with the running application."""
    configured = os.environ.get("DATABASE_URL")
    if not configured:
        return
    app_url = make_url(configured.strip())
    if (app_url.host, app_url.database) == (url.host, url.database):
        raise RuntimeError(
            "TEST_DATABASE_URL resolves to the same host and database as "
            "DATABASE_URL. The suite truncates every table it touches; it must "
            "have a database of its own."
        )


TEST_DATABASE_URL = _test_database_url()

# Checked at import time, i.e. during collection and before any test executes.
_assert_is_test_database(TEST_DATABASE_URL)
_assert_is_not_the_application_database(TEST_DATABASE_URL)

# ``check_same_thread`` is gone with SQLite: it is a sqlite3 driver argument and
# psycopg2 rejects it. ``pool_pre_ping`` matters here for the same reason it
# does in the application -- Neon suspends idle compute mid-run.
test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)

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
    """Build the schema once per session, and leave the database empty.

    The SQLite file this replaced was deleted outright at the end of a run. A
    Neon branch persists, so teardown truncates instead: the tables stay, the
    rows do not.
    """
    _assert_is_test_database(test_engine.url)
    run_migrations(test_engine)
    yield
    _truncate()
    test_engine.dispose()


# Every table the suite writes to. ``templates`` is included where the old
# DELETE-based cleanup left it alone: on a fresh-per-run SQLite file seeded rows
# vanished by themselves, but on a persistent branch they would accumulate
# across runs and make the template tests depend on run order.
_TABLES_TO_CLEAR = ("prompt_versions", "users", "templates")


def _truncate() -> None:
    """Reset the tables to empty between tests.

    One ``TRUNCATE`` rather than a ``DELETE`` per table: a single round trip to
    a database that is now across a network, and ``RESTART IDENTITY`` puts the
    sequences back to the start. That last part restores something SQLite gave
    away for free -- a brand new file each run meant ids always began at 1,
    whereas Postgres sequences would otherwise climb for the life of the branch.
    ``CASCADE`` covers the prompt_versions -> users foreign key.
    """
    with test_engine.begin() as conn:
        conn.exec_driver_sql(
            "TRUNCATE TABLE {} RESTART IDENTITY CASCADE".format(
                ", ".join(_TABLES_TO_CLEAR)
            )
        )


@pytest.fixture(autouse=True)
def clear_users():
    """Full cleanup for deterministic tests -- test database only.

    Truncating before each test (rather than before *and* after, as the SQLite
    version did) is what guarantees a clean slate; the trailing pass was doing
    the same work twice, which is free on a local file and is not on a remote
    branch. The session fixture above empties the tables once at the end.
    """
    _truncate()
    yield


@pytest.fixture
def migration_database():
    """Factory for engines pointed at a private, empty Postgres database.

    ``run_migrations`` is about building a schema out of nothing, which under
    SQLite meant handing it a brand new file per test. The Postgres equivalent
    here is a database of its own per test: created on the same branch, dropped
    on teardown, and never sharing tables with the rest of the suite.

    A private *schema* would be the lighter option, but it needs ``search_path``
    to be set, and Neon's pooled endpoint refuses ``search_path`` as a libpq
    startup parameter while its transaction pooling makes a session-level
    ``SET`` unreliable. A separate database needs no session state at all, so it
    works through the pooler. ``WITH (FORCE)`` on the drop matters for the same
    reason: the pooler can be holding idle server connections to the database,
    which would otherwise block it.
    """
    admin = create_engine(TEST_DATABASE_URL, isolation_level="AUTOCOMMIT")
    created = []

    def _make(name):
        database = f"migtest_{name}"
        with admin.connect() as conn:
            conn.exec_driver_sql(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
            conn.exec_driver_sql(f'CREATE DATABASE "{database}"')

        url = TEST_DATABASE_URL.set(database=database)
        # Same guard as the main engine: these are disposable by construction,
        # but nothing should ever get a connection here without proving it.
        _assert_is_test_database(url)
        _assert_is_not_the_application_database(url)

        engine = create_engine(url, pool_pre_ping=True)
        created.append((database, engine))
        return engine

    yield _make

    for database, engine in created:
        engine.dispose()
        with admin.connect() as conn:
            conn.exec_driver_sql(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
    admin.dispose()

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
