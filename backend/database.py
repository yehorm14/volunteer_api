import os
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

# Default: a SQLite file next to this module, independent of the working directory.
_DEFAULT_DB_PATH = Path(__file__).resolve().parent / "volunteer.db"


def normalize_database_url(url: str) -> str:
    """Make Postgres URLs usable with the installed driver.

    Hosts hand out postgres:// URLs, which SQLAlchemy 2 no longer accepts, and a bare
    postgresql:// URL makes SQLAlchemy 2.1 look for psycopg (v3) while requirements.txt
    ships psycopg2. Pin both to psycopg2 unless the URL names a driver explicitly.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


def get_database_url() -> str:
    """Read DATABASE_URL at call time so importing this module has no side effects."""
    return normalize_database_url(os.getenv("DATABASE_URL") or f"sqlite:///{_DEFAULT_DB_PATH}")


@lru_cache
def get_engine() -> Engine:
    url = get_database_url()
    # check_same_thread is SQLite-only; FastAPI uses connections across threads.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


@lru_cache
def _session_factory() -> sessionmaker:
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def init_db() -> None:
    """Bring the database to the latest migration. Called from app startup.

    Set AUTO_MIGRATE=0 to skip this and run `python -m backend.migrate` yourself (see docs/DEPLOY.md).
    """
    if os.getenv("AUTO_MIGRATE", "1").strip().lower() in {"0", "false", "no", "off"}:
        return
    from .migrate import upgrade_to_head

    upgrade_to_head()


def get_db():
    db = _session_factory()()
    try:
        yield db
    finally:
        db.close()
