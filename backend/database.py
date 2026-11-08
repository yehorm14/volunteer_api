import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

# Default: a SQLite file next to this module, independent of the working directory.
_DEFAULT_DB_PATH = Path(__file__).resolve().parent / "volunteer.db"
DATABASE_URL: str = os.getenv("DATABASE_URL") or f"sqlite:///{_DEFAULT_DB_PATH}"

# check_same_thread is a SQLite-only option; FastAPI uses connections across threads.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
