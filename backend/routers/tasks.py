from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db

router = APIRouter(prefix="/tasks", tags=["tasks"])

CurrentUser = Annotated[models.User, Depends(auth.get_current_user)]
DB = Annotated[Session, Depends(get_db)]


def get_owned_task(db: Session, task_id: int, user: models.User) -> models.Task:
    """Return the task if it exists and belongs to user, otherwise raise 404."""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task or task.owner_id != user.id:  # type: ignore
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.post("", response_model=schemas.Task, status_code=status.HTTP_201_CREATED)
def create_task(task_in: schemas.TaskCreate, current_user: CurrentUser, db: DB):
    new_task = models.Task(**task_in.model_dump(), owner_id=current_user.id)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@router.get("", response_model=list[schemas.Task])
def read_tasks(current_user: CurrentUser, db: DB):
    return db.query(models.Task).filter(models.Task.owner_id == current_user.id).all()


@router.get("/{task_id}", response_model=schemas.Task)
def read_task(task_id: int, current_user: CurrentUser, db: DB):
    return get_owned_task(db, task_id, current_user)


@router.patch("/{task_id}", response_model=schemas.Task)
def update_task(task_id: int, task_in: schemas.TaskUpdate, current_user: CurrentUser, db: DB):
    task = get_owned_task(db, task_id, current_user)
    for key, value in task_in.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, current_user: CurrentUser, db: DB):
    task = get_owned_task(db, task_id, current_user)
    db.delete(task)
    db.commit()
    return None
