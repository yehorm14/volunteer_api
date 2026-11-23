from sqlalchemy import Column, Index, func, Integer, String, Boolean, Date, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from .database import Base
from .task_status import DEFAULT_STATUS, TASK_STATUSES

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    # Emails are stored lower-cased; this index also stops a differently-cased duplicate slipping in
    # through any other path. Kept in step with migration 0004.
    __table_args__ = (Index("uq_users_email_lower", func.lower(email), unique=True),)

    # The relationship tells SQLAlchemy to fetch all tasks owned by this user
    tasks = relationship("Task", back_populates="owner")

class Task(Base):
    __tablename__ = "tasks"
    # Kept in step with migration 0002 (test_migrations checks the schemas match).
    __table_args__ = (
        CheckConstraint(
            "status IN (" + ", ".join(f"'{s}'" for s in TASK_STATUSES) + ")",
            name="ck_tasks_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, index=True)
    status = Column(String, default=DEFAULT_STATUS, nullable=False)
    
    # The ForeignKey links this column directly to the 'id' column in the 'users' table
    owner_id = Column(Integer, ForeignKey("users.id"))

    # The relationship tells SQLAlchemy to fetch the specific user who owns this task
    owner = relationship("User", back_populates="tasks")


class AiUsage(Base):
    """AI calls a user has made on one UTC day (see backend/ai_quota.py). Migration 0003."""
    __tablename__ = "ai_usage"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    day = Column(Date, primary_key=True)
    count = Column(Integer, nullable=False, default=0)
