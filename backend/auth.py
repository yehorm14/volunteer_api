import os
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session

from . import models
from .database import get_db

# bcrypt only uses the first 72 bytes and bcrypt 5 raises on longer input.
MAX_PASSWORD_BYTES = 72

# The value shipped in .env.example, and the shortest key accepted at startup.
PLACEHOLDER_SECRET_KEY = "change-me"
MIN_SECRET_KEY_LENGTH = 16


def get_secret_key() -> str:
    """Read SECRET_KEY at call time; there is deliberately no fallback value."""
    key = os.getenv("SECRET_KEY", "")
    if not key:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )
    if key == PLACEHOLDER_SECRET_KEY or len(key) < MIN_SECRET_KEY_LENGTH:
        raise RuntimeError(
            f"SECRET_KEY is the placeholder value or shorter than {MIN_SECRET_KEY_LENGTH} characters. "
            'Generate a real one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )
    return key


def _algorithm() -> str:
    return os.getenv("ALGORITHM", "HS256")


def _expire_minutes() -> int:
    return int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


# This tells FastAPI where the frontend should send the login data
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        return False  # cannot match any stored hash; avoids a bcrypt ValueError
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))

def get_password_hash(password: str) -> str:
    # Generate a random salt and hash the password
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), salt)
    # Convert the bytes back to a standard string for the database
    return hashed_bytes.decode('utf-8')

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=_expire_minutes())
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, get_secret_key(), algorithm=_algorithm())
    return encoded_jwt

# This is the dependency we will attach to any protected route
def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], 
    db: Annotated[Session, Depends(get_db)]
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the token to extract the user email
        payload = jwt.decode(token, get_secret_key(), algorithms=[_algorithm()])
        # The | None satisfies the Pylance type checker for dictionary get methods
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    # Check the database to make sure the user actually exists
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
        
    return user