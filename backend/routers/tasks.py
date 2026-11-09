from fastapi import APIRouter, status

from .. import schemas, models
from ..deps import DB, CurrentUser, get_owned_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


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
