from pydantic import BaseModel, EmailStr, Field, field_validator

from .task_status import DEFAULT_STATUS, TaskStatus

MAX_TITLE_LENGTH = 200


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _clean_title(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("Title must not be blank")
    if len(v) > MAX_TITLE_LENGTH:
        raise ValueError(f"Title must be at most {MAX_TITLE_LENGTH} characters")
    return v


# Task Schemas
class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    status: TaskStatus = DEFAULT_STATUS

    _check_title = field_validator("title")(_clean_title)


class TaskUpdate(BaseModel):
    """PATCH body. An omitted field is left alone; title and status may not be null.

    description may be null, which clears it.
    """

    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None

    @field_validator("title", "status", mode="before")
    @classmethod
    def not_null(cls, v):
        # Validators only run for fields that were sent, so this rejects an explicit null.
        if v is None:
            raise ValueError("This field cannot be null; omit it to leave it unchanged")
        return v

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: str) -> str:
        return _clean_title(v)


class Task(BaseModel):
    id: int
    title: str
    description: str | None = None
    # str, not TaskStatus: rows that predate the contract must still be listable
    # so the UI can show them as "Unknown" instead of failing the whole response.
    status: str
    owner_id: int

    model_config = {"from_attributes": True}

# User Schemas
class UserBase(BaseModel):
    email: EmailStr

    @field_validator("email", mode="after")
    @classmethod
    def lower_case_email(cls, v: str) -> str:
        # Accounts are case-insensitive: A@x.com and a@x.com are the same account.
        return normalize_email(v)

MIN_PASSWORD_LENGTH = 8


class UserCreate(UserBase):
    password: str = Field(min_length=MIN_PASSWORD_LENGTH)

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

class ExtractRequest(BaseModel):
    notes: str = Field(min_length=1, max_length=10_000)


class ParsedTask(BaseModel):
    title: str
    description: str

    model_config = {"from_attributes": True}

