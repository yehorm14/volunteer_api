from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

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

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, index=True)
    status = Column(String, default="pending")
    
    # The ForeignKey links this column directly to the 'id' column in the 'users' table
    owner_id = Column(Integer, ForeignKey("users.id"))

    # The relationship tells SQLAlchemy to fetch the specific user who owns this task
    owner = relationship("User", back_populates="tasks")
