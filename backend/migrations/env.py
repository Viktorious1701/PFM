"""Alembic environment. Reads the URL from app settings, not alembic.ini."""

from logging.config import fileConfig

from alembic import context

# Models must be imported for autogenerate to see their tables. Importing the
# package is enough — app/models/__init__.py registers every model on
# Base.metadata. DOD-02: every model change ships a migration.
import app.models  # noqa: F401
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import build_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    # -x db_url=... wins, so CI or a one-off can point elsewhere.
    override = context.get_x_argument(as_dictionary=True).get("db_url")
    return override or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # SQLite cannot ALTER most things in place; batch mode rewrites the table.
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = build_engine(_database_url())
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
