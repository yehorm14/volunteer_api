"""Alembic environment. The database URL comes from DATABASE_URL via backend.database,
and a connection passed in through config.attributes["connection"] is reused if present."""
from alembic import context

from backend import models  # noqa: F401  (registers the tables on Base)
from backend.database import Base, get_engine

target_metadata = Base.metadata


def run_migrations_online() -> None:
    connection = context.config.attributes.get("connection")
    if connection is not None:
        _run(connection)
    else:
        with get_engine().connect() as connection:
            _run(connection)
            connection.commit()


def _run(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite",
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


run_migrations_online()
