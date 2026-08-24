"""Explicit schema setup.

Nothing in this module runs on import. Previously ``create_all`` and an
``ALTER TABLE`` executed at ``app.main`` module scope, which meant *importing*
the application mutated whatever database ``DATABASE_URL`` pointed at --
including from the test suite. Schema changes are now an intentional act:

    python -m app.migrations

This is a placeholder for real Alembic migrations, not a substitute for them.
``run_migrations`` is idempotent, so it is safe to run repeatedly.
"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.database import Base, ENGINE

# Importing the model modules is what registers them on ``Base.metadata``.
# Every model must be imported here or ``create_all`` silently skips its table.
# (``template`` was previously missing, so a fresh deployment had no
# ``templates`` table unless the seed script happened to run.)
from app.models import user as _user  # noqa: F401
from app.models import prompt_version as _prompt_version  # noqa: F401
from app.models import template as _template  # noqa: F401


def ensure_prompt_versions_tag_column(engine: Engine) -> None:
    """Add prompt_versions.tag to databases created before the column existed."""
    inspector = inspect(engine)
    if "prompt_versions" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("prompt_versions")}
    if "tag" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE prompt_versions ADD COLUMN tag VARCHAR(32)"))


def run_migrations(engine: Engine | None = None) -> None:
    """Create any missing tables and apply pending column additions."""
    target = engine if engine is not None else ENGINE
    Base.metadata.create_all(bind=target)
    ensure_prompt_versions_tag_column(target)


if __name__ == "__main__":
    run_migrations()
    print(f"Schema up to date: {ENGINE.url}")
