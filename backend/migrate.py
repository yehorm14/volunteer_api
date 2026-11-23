"""Apply database migrations.

    python -m backend.migrate            # upgrade to the latest revision
    python -m backend.migrate --check    # exit 1 if the database is not at the latest revision

Databases created by the old create_all() startup have the tables but no alembic_version
table. They are recognised, checked against the initial schema and stamped as 0001
(no data is touched) before the remaining migrations run.
"""
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect
from sqlalchemy.engine import Connection

from .database import get_engine

BASELINE = "0001"
_EXPECTED_BASELINE = {
    "users": {"id", "email", "hashed_password", "is_active"},
    "tasks": {"id", "title", "description", "status", "owner_id"},
}


def _config(connection: Connection) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parent / "migrations"))
    cfg.attributes["connection"] = connection
    return cfg


def _needs_baseline_stamp(connection: Connection) -> bool:
    """True for a pre-migration installation: app tables exist but alembic has never run."""
    insp = inspect(connection)
    tables = set(insp.get_table_names())
    if "alembic_version" in tables or not tables & set(_EXPECTED_BASELINE):
        return False
    for table, expected in _EXPECTED_BASELINE.items():
        if table not in tables:
            raise RuntimeError(f"Existing database has no '{table}' table; refusing to guess its schema.")
        missing = expected - {c["name"] for c in insp.get_columns(table)}
        if missing:
            raise RuntimeError(f"Existing '{table}' table is missing columns {sorted(missing)}; back it up and fix it by hand.")
    return True


def upgrade_to_head() -> None:
    engine = get_engine()
    with engine.connect() as connection:
        cfg = _config(connection)
        if _needs_baseline_stamp(connection):
            command.stamp(cfg, BASELINE)
        command.upgrade(cfg, "head")
        connection.commit()


def is_up_to_date() -> bool:
    with get_engine().connect() as connection:
        head = ScriptDirectory.from_config(_config(connection)).get_current_head()
        return MigrationContext.configure(connection).get_current_revision() == head


def main(argv: list[str]) -> int:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    if "--check" in argv:
        ok = is_up_to_date()
        print("Database is up to date." if ok else "Database needs migrating: run python -m backend.migrate")
        return 0 if ok else 1
    upgrade_to_head()
    print("Database is at the latest revision.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
