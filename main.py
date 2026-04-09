from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

import models, schemas, auth
from database import engine, get_db

#Command SQLAlchemy to physically build the tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title = "Volunteer Task Manager API")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Volunteer Task Manager API!"}

@app.post("/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: schemas.UserCreate, 
    db: Annotated[Session, Depends(get_db)]
):
    # Check if the email is already taken
    db_user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if db_user:
        raise HTTPException(
            status_code=400, 
            detail="A user with this email already exists."
        )
    
    # Hash the password
    hashed_pw = auth.get_password_hash(user_in.password)
    
    # Create the database model instance
    new_user = models.User(
        email=user_in.email,
        hashed_password=hashed_pw
    )
    
    # Save to database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@app.post("/auth/login", response_model=schemas.Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)]
):
    #  Find the user in the database
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    #  Verify the password hash
    if not auth.verify_password(form_data.password, user.hashed_password): # type: ignore
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    #  Generate the JWT token
    access_token = auth.create_access_token(data={"sub": user.email})

    # Return the token 
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/tasks", response_model=schemas.Task, status_code=status.HTTP_201_CREATED)
def create_task(
    task_in: schemas.TaskCreate,
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    # Convert the Pydantic schema into a dictionary
    task_data = task_in.model_dump()
    
    # Create the database model and explicitly set the owner_id
    new_task = models.Task(**task_data, owner_id=current_user.id)
    
    # Save it to the database
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    return new_task

@app.get("/tasks", response_model=list[schemas.Task])
def read_tasks(
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    # Fetch only the tasks that belong to the authenticated user
    tasks = db.query(models.Task).filter(models.Task.owner_id == current_user.id).all()
    return tasks

@app.get("/tasks/{task_id}", response_model=schemas.Task)
def read_task(
    task_id: int,
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    # Search for the task by its ID
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    
    # If it does not exist or if someone else owns it return a 404 Not Found
    if not task or task.owner_id != current_user.id: # type: ignore
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
        
    return task

@app.patch("/tasks/{task_id}", response_model=schemas.Task)
def update_task(
    task_id: int,
    task_in: schemas.TaskUpdate,
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    # Find the task and verify ownership just like the GET route
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    
    if not task or task.owner_id != current_user.id: # type: ignore
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
        
    # Extract only the fields the user actually wants to change
    update_data = task_in.model_dump(exclude_unset=True)
    
    # Apply the changes to the database object
    for key, value in update_data.items():
        setattr(task, key, value)
        
    # Save the changes to the hard drive
    db.commit()
    db.refresh(task)
    
    return task

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    # Find the task in the database
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    
    # Check existence and ownership
    if not task or task.owner_id != current_user.id: # type: ignore
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
        
    # Physically remove the record from the database
    db.delete(task)
    db.commit()
    
    return None

@app.get("/tasks", response_model=list[schemas.TaskPublicView])
def read_tasks(
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    tasks = db.query(models.Task).filter(models.Task.owner_id == current_user.id).all()
    return tasks