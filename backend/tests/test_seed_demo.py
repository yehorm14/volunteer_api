import pytest
from fastapi.testclient import TestClient

from backend import models
from backend.main import create_app
from backend.seed_demo import SAMPLE_TASKS, seed_demo, seed_demo_from_env


@pytest.fixture()
def db(client):
    from backend.database import get_db

    gen = client.app.dependency_overrides[get_db]()
    session = next(gen)
    yield session
    gen.close()


def test_seed_creates_user_with_sample_tasks(db):
    assert seed_demo(db, "demo@example.com", "demo-password") is True
    user = db.query(models.User).filter_by(email="demo@example.com").one()
    assert len(user.tasks) == len(SAMPLE_TASKS)


def test_seed_is_idempotent(db):
    seed_demo(db, "demo@example.com", "demo-password")
    assert seed_demo(db, "demo@example.com", "demo-password") is False
    assert db.query(models.User).count() == 1
    assert db.query(models.Task).count() == len(SAMPLE_TASKS)


def test_seed_rejects_short_password(db):
    with pytest.raises(ValueError):
        seed_demo(db, "demo@example.com", "short")


def test_seed_from_env_does_nothing_when_unset(monkeypatch):
    monkeypatch.delenv("DEMO_USER_EMAIL", raising=False)
    monkeypatch.delenv("DEMO_USER_PASSWORD", raising=False)
    assert seed_demo_from_env() is False


def test_startup_seeds_demo_user_and_login_works(monkeypatch):
    monkeypatch.setenv("DEMO_USER_EMAIL", "startup-demo@example.com")
    monkeypatch.setenv("DEMO_USER_PASSWORD", "demo-password")
    with TestClient(create_app()) as c:  # uses the temporary DATABASE_URL set in conftest
        r = c.post("/auth/login", data={"username": "startup-demo@example.com", "password": "demo-password"})
        assert r.status_code == 200
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        assert len(c.get("/tasks", headers=headers).json()) == len(SAMPLE_TASKS)
