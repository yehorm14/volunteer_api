from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from .. import auth, demo, models, schemas
from ..deps import DB

DEMO_TOKEN_MINUTES = 15

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: schemas.UserCreate, db: DB):
    if db.query(models.User).filter(models.User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="A user with this email already exists.")

    new_user = models.User(
        email=user_in.email,
        hashed_password=auth.get_password_hash(user_in.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=schemas.Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DB,
):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()

    if not user or not auth.verify_password(form_data.password, user.hashed_password):  # type: ignore
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/demo", response_model=schemas.Token)
def login_to_sample_workspace(db: DB):
    """Passwordless sign-in to the shared read-only sample workspace (404 unless DEMO_PUBLIC=1)."""
    if not demo.is_public_demo_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    user = db.query(models.User).filter(models.User.email == demo.demo_email()).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The sample workspace is not ready yet.")
    # demo=true makes the token read-only on its own; the short expiry limits how long one stays valid.
    token = auth.create_access_token(data={"sub": user.email, "demo": True}, expires_minutes=DEMO_TOKEN_MINUTES)
    return {"access_token": token, "token_type": "bearer"}
