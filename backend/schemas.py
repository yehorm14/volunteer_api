from pydantic import BaseModel

# Task Schemas
class TaskBase(BaseModel):
    title: str
    description: str | None = None
    status: str = "pending"

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None

class Task(TaskBase):
    id: int
    owner_id: int

    model_config = {"from_attributes": True}

class TaskPublicView(TaskBase):
    owner_id: int
    
    class Config:
        from_attributes = True

# User Schemas
class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    tasks: list[Task] = []

    model_config = {"from_attributes": True}

# Security Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None

class ParsedTask(BaseModel):
    title: str
    description: str

    model_config = {"from_attributes": True}

