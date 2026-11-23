from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from .database import Base
from .task_status import DEFAULT_STATUS, TASK_STATUSES

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

    # The relationship tells SQLAlchemy to fetch all tasks owned by this user
    tasks = relationship("Task", back_populates="owner")

class Task(Base):
    __tablename__ = "tasks"
    # Only applied to newly created tables; existing databases keep working through
    # API validation plus the startup normalisation in init_db().
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
