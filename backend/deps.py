"""Shared FastAPI dependencies and type aliases for the routers."""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from . import auth, models
from .database import get_db

CurrentUser = Annotated[models.User, Depends(auth.get_current_user)]
DB = Annotated[Session, Depends(get_db)]


def get_owned_task(db: Session, task_id: int, user: models.User) -> models.Task:
    """Return the task if it exists and belongs to user, otherwise raise 404."""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task or task.owner_id != user.id:  # type: ignore
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


def owned_task(task_id: int, current_user: CurrentUser, db: DB) -> models.Task:
    return get_owned_task(db, task_id, current_user)


# Declare this before any AI-client dependency so a missing task is a 404, not a 503.
OwnedTask = Annotated[models.Task, Depends(owned_task)]
