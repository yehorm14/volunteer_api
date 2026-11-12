import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import auth
from .database import init_db
from .seed_demo import seed_demo_from_env
from .routers import ai, auth as auth_router, tasks

DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"


def parse_origins(raw: str | None) -> list[str]:
    """Split a comma-separated CORS_ORIGINS value; browsers send origins without a trailing slash."""
    value = raw or DEFAULT_ORIGINS
    return [o.strip().rstrip("/") for o in value.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    seed_demo_from_env()
    yield


def create_app(load_env: bool = False) -> FastAPI:
    """Build the app. Only the real entry point (`app` below) loads .env; tests never do."""
    if load_env:
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    auth.get_secret_key()  # fail fast with a clear error if SECRET_KEY is missing

    application = FastAPI(title="Volunteer Task Manager API", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=parse_origins(os.getenv("CORS_ORIGINS")),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(auth_router.router)
    application.include_router(tasks.router)
    application.include_router(ai.router)

    @application.get("/")
    def read_root():
        return {"message": "Welcome to the Volunteer Task Manager API!"}

    return application


def __getattr__(name: str):
    # `uvicorn backend.main:app` resolves `app` here, so importing this module
    # (as the tests do) neither reads .env nor needs SECRET_KEY.
    if name == "app":
        application = create_app(load_env=True)
        globals()["app"] = application
        return application
    raise AttributeError(name)
