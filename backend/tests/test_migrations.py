"""Schema creation covers every model.

`create_all` only builds tables for models that have been imported, and the
Template model was previously missing -- so a fresh deployment served a broken
template library unless the seed script happened to have been run first.
"""

from pathlib import Path

from sqlalchemy import create_engine, inspect

from app.migrations import run_migrations

EXPECTED_TABLES = {"users", "prompt_versions", "templates"}


def test_migrations_create_every_table(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test_fresh.db'}")

    run_migrations(engine)

    tables = set(inspect(engine).get_table_names())
    missing = EXPECTED_TABLES - tables
    assert not missing, f"fresh database is missing tables: {sorted(missing)}"


def test_migrations_are_idempotent(tmp_path):
    """Safe to run on every deploy, not just the first."""
    engine = create_engine(f"sqlite:///{tmp_path / 'test_twice.db'}")

    run_migrations(engine)
    run_migrations(engine)

    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())


def test_prompt_versions_has_the_tag_column(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test_tag.db'}")

    run_migrations(engine)

    columns = {c["name"] for c in inspect(engine).get_columns("prompt_versions")}
    assert "tag" in columns
