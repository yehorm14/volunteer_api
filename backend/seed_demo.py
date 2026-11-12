"""Create a demo user with a few sample tasks. Safe to run repeatedly.

    DEMO_USER_EMAIL=demo@example.com DEMO_USER_PASSWORD=demo-password python -m backend.seed_demo

The API also calls seed_demo_from_env() at startup, so setting both variables is enough.
"""
import os
import sys

from sqlalchemy.orm import Session

from . import auth, models, schemas
from .database import _session_factory, init_db

SAMPLE_TASKS = [
    ("Call the food bank about Saturday's collection", "Confirm volunteer numbers and the drop-off time.", "pending"),
    ("Print sign-in sheets for the community garden", "Twenty copies, one per table.", "in_progress"),
    ("Send thank-you emails to last month's volunteers", None, "completed"),
]


def seed_demo(db: Session, email: str, password: str) -> bool:
    """Create the demo user and sample tasks if the user does not exist. Returns True if anything was created."""
    if len(password) < schemas.MIN_PASSWORD_LENGTH:
        raise ValueError(f"Demo password must be at least {schemas.MIN_PASSWORD_LENGTH} characters.")
    if db.query(models.User).filter(models.User.email == email).first():
        return False
    user = models.User(email=email, hashed_password=auth.get_password_hash(password))
    db.add(user)
    db.flush()
    for title, description, status in SAMPLE_TASKS:
        db.add(models.Task(title=title, description=description, status=status, owner_id=user.id))
    db.commit()
    return True


def seed_demo_from_env() -> bool:
    """Seed from DEMO_USER_EMAIL and DEMO_USER_PASSWORD. Does nothing unless both are set."""
    email = os.getenv("DEMO_USER_EMAIL", "").strip()
    password = os.getenv("DEMO_USER_PASSWORD", "")
    if not email or not password:
        return False
    init_db()
    db = _session_factory()()
    try:
        return seed_demo(db, email, password)
    finally:
        db.close()


if __name__ == "__main__":
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    if not (os.getenv("DEMO_USER_EMAIL") and os.getenv("DEMO_USER_PASSWORD")):
        sys.exit("Set DEMO_USER_EMAIL and DEMO_USER_PASSWORD first.")
    print("Demo user created." if seed_demo_from_env() else "Demo user already exists.")
