import os

# Must be set before the app modules are imported (auth.py requires SECRET_KEY).
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.pop("OPENAI_API_KEY", None)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import models
from backend.database import Base, get_db
from backend.main import app


@pytest.fixture()
def client():
    """TestClient backed by a fresh in-memory SQLite database per test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def register_and_login(client: TestClient, email: str, password: str = "pw12345") -> dict:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def auth_headers(client):
    return register_and_login(client, "alice@example.com")


@pytest.fixture()
def other_headers(client):
    return register_and_login(client, "bob@example.com")
