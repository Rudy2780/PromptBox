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

from sqlalchemy import inspect

from app.migrations import run_migrations

EXPECTED_TABLES = {"users", "prompt_versions", "templates"}


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
