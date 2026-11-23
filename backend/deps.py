"""Shared FastAPI dependencies and type aliases for the routers."""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from . import auth, demo, models
from .database import get_db

CurrentUser = Annotated[models.User, Depends(auth.get_current_user)]
DB = Annotated[Session, Depends(get_db)]


def writable_user(
    current_user: CurrentUser, token: Annotated[str, Depends(auth.oauth2_scheme)]
) -> models.User:
    """The signed-in user, unless this is a sample-workspace session (then 403).

    A token minted by /auth/demo carries demo=true and stays read-only even if DEMO_PUBLIC is
    later removed; the env check additionally protects the demo account against password logins.
    """
    if auth.token_is_demo(token) or demo.is_demo_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=demo.READ_ONLY_DETAIL)
    return current_user


# Use for every route that changes data or spends AI credits.
WritableUser = Annotated[models.User, Depends(writable_user)]


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
