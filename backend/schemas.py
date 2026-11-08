from pydantic import BaseModel, field_validator

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

# User Schemas
class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, v: str) -> str:
        # bcrypt limit is in bytes, not characters.
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes")
        return v

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

