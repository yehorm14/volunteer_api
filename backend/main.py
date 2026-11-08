import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from . import models  # noqa: E402
from .database import engine  # noqa: E402
from .routers import ai, auth, tasks  # noqa: E402

# Create tables on startup (no migrations in this project).
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Volunteer Task Manager API")

DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
origins = [o.strip() for o in (os.getenv("CORS_ORIGINS") or DEFAULT_ORIGINS).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(ai.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Volunteer Task Manager API!"}
