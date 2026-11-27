from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from .. import auth, demo, models, schemas
from ..deps import DB
from ..rate_limit import limit_auth_attempts

DEMO_TOKEN_MINUTES = 15

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_auth_attempts)],
)
def register_user(user_in: schemas.UserCreate, db: DB):
    # user_in.email is already validated and lower-cased by the schema.
    if db.query(models.User).filter(func.lower(models.User.email) == user_in.email).first():
        raise HTTPException(status_code=400, detail="A user with this email already exists.")

    new_user = models.User(
        email=user_in.email,
        hashed_password=auth.get_password_hash(user_in.password),
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        # Lost a race with a concurrent registration of the same address.
        db.rollback()
        raise HTTPException(status_code=400, detail="A user with this email already exists.")
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=schemas.Token, dependencies=[Depends(limit_auth_attempts)])
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DB,
):
    user = db.query(models.User).filter(models.User.email == schemas.normalize_email(form_data.username)).first()

    if not user or not user.is_active or not auth.verify_password(form_data.password, user.hashed_password):  # type: ignore
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(data={"sub": user.email, "uid": user.id})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/demo", response_model=schemas.Token)
def login_to_sample_workspace(db: DB):
    """Passwordless sign-in to the shared read-only sample workspace (404 unless DEMO_PUBLIC=1)."""
    if not demo.is_public_demo_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    user = db.query(models.User).filter(models.User.email == demo.demo_email()).first()
    if user is None or not demo.is_demo_user(user):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The sample workspace is not ready yet.")
    # demo=true makes the token read-only on its own; the short expiry limits how long one stays valid.
    token = auth.create_access_token(data={"sub": user.email, "uid": user.id, "demo": True}, expires_minutes=DEMO_TOKEN_MINUTES)
    return {"access_token": token, "token_type": "bearer"}
