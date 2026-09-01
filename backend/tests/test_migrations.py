"""Schema creation covers every model.

`create_all` only builds tables for models that have been imported, and the
Template model was previously missing -- so a fresh deployment served a broken
template library unless the seed script happened to have been run first.

These tests need an empty database to build into. Under SQLite that was a new
file per test; on Postgres it is a private database per test, supplied by the
``migration_database`` fixture in conftest, which creates it and drops it afterwards.
connections at it and drops it afterwards. Nothing here touches the tables the
rest of the suite is using, and the connection string is never written down --
it comes from TEST_DATABASE_URL via the fixture.
"""

from sqlalchemy import inspect, text

from app.migrations import run_migrations

EXPECTED_TABLES = {"users", "prompt_versions", "templates", "oauth_identities"}


def test_migrations_create_every_table(migration_database):
    engine = migration_database("fresh")

    run_migrations(engine)

    tables = set(inspect(engine).get_table_names())
    missing = EXPECTED_TABLES - tables
    assert not missing, f"fresh database is missing tables: {sorted(missing)}"


def test_migrations_are_idempotent(migration_database):
    """Safe to run on every deploy, not just the first."""
    engine = migration_database("twice")

    run_migrations(engine)
    run_migrations(engine)

    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())


def test_prompt_versions_has_the_tag_column(migration_database):
    engine = migration_database("tag")

    run_migrations(engine)

    columns = {c["name"] for c in inspect(engine).get_columns("prompt_versions")}
    assert "tag" in columns


def test_users_password_is_nullable(migration_database):
    """OAuth accounts have no password to store.

    A database built before OAuth landed carries NOT NULL here, and
    ``create_all`` will not alter an existing table -- so this asserts the
    explicit ALTER in ``ensure_users_password_is_optional`` actually ran.
    """
    engine = migration_database("nullable")

    run_migrations(engine)

    password = next(
        c for c in inspect(engine).get_columns("users") if c["name"] == "hashed_password"
    )
    assert password["nullable"] is True


def test_users_password_alter_runs_on_a_pre_oauth_database(migration_database):
    """The interesting case: the table already exists with the old constraint."""
    engine = migration_database("preoauth")

    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE users ("
                " id SERIAL PRIMARY KEY,"
                " email VARCHAR UNIQUE NOT NULL,"
                " hashed_password VARCHAR NOT NULL,"
                " created_at TIMESTAMP)"
            )
        )

    run_migrations(engine)

    password = next(
        c for c in inspect(engine).get_columns("users") if c["name"] == "hashed_password"
    )
    assert password["nullable"] is True


def test_oauth_identities_are_unique_per_provider_account(migration_database):
    """Two PromptBox accounts must not be able to claim one provider account."""
    engine = migration_database("oauthunique")

    run_migrations(engine)

    constraints = inspect(engine).get_unique_constraints("oauth_identities")
    pairs = [set(c["column_names"]) for c in constraints]
    assert {"provider", "provider_user_id"} in pairs
