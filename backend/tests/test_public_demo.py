import pytest

from backend import models
from backend.seed_demo import SAMPLE_TASKS, seed_demo, seed_demo_from_env
from backend.task_status import TASK_STATUSES

from .conftest import register_and_login

DEMO_EMAIL = "demo@example.com"


@pytest.fixture()
def db(client):
    from backend.database import get_db

    gen = client.app.dependency_overrides[get_db]()
    session = next(gen)
    yield session
    gen.close()


@pytest.fixture()
def public_demo(client, db, monkeypatch):
    monkeypatch.setenv("DEMO_USER_EMAIL", DEMO_EMAIL)
    monkeypatch.setenv("DEMO_PUBLIC", "1")
    seed_demo(db, DEMO_EMAIL, "never-shared-password")


def demo_headers(client):
    r = client.post("/auth/demo")
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_demo_endpoint_is_404_by_default(client, db, monkeypatch):
    monkeypatch.setenv("DEMO_USER_EMAIL", DEMO_EMAIL)  # a demo user alone does not make it public
    seed_demo(db, DEMO_EMAIL, "never-shared-password")
    assert client.post("/auth/demo").status_code == 404


def test_demo_endpoint_is_404_without_a_demo_email(client, monkeypatch):
    monkeypatch.delenv("DEMO_USER_EMAIL", raising=False)
    monkeypatch.setenv("DEMO_PUBLIC", "1")
    assert client.post("/auth/demo").status_code == 404


def test_visitor_sees_sample_tasks_in_all_three_statuses_without_credentials(client, public_demo):
    headers = demo_headers(client)
    tasks = client.get("/tasks", headers=headers).json()
    assert len(tasks) == len(SAMPLE_TASKS)
    assert {t["status"] for t in tasks} == set(TASK_STATUSES)


def test_sample_workspace_is_read_only(client, public_demo):
    headers = demo_headers(client)
    task = client.get("/tasks", headers=headers).json()[0]
    url = f"/tasks/{task['id']}"
    for r in (
        client.post("/tasks", json={"title": "x"}, headers=headers),
        client.patch(url, json={"status": "completed"}, headers=headers),
        client.delete(url, headers=headers),
    ):
        assert r.status_code == 403
        assert "read-only" in r.json()["detail"]
    assert client.get(url, headers=headers).json() == task  # unchanged
    assert len(client.get("/tasks", headers=headers).json()) == len(SAMPLE_TASKS)


def test_ai_is_disabled_in_the_sample_workspace(client, public_demo):
    headers = demo_headers(client)
    task = client.get("/tasks", headers=headers).json()[0]
    assert client.post(f"/tasks/{task['id']}/ai-categorize", headers=headers).status_code == 403
    assert client.post("/tasks/extract", json={"notes": "call Sam"}, headers=headers).status_code == 403


def test_the_demo_password_login_is_read_only_too(client, public_demo):
    r = client.post("/auth/login", data={"username": DEMO_EMAIL, "password": "never-shared-password"})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.post("/tasks", json={"title": "x"}, headers=headers).status_code == 403


def test_real_accounts_are_unaffected_and_cannot_see_sample_data(client, public_demo):
    headers = register_and_login(client, "real@example.com")
    assert client.get("/tasks", headers=headers).json() == []
    assert client.post("/tasks", json={"title": "mine"}, headers=headers).status_code == 201


def test_public_demo_is_not_ready_until_seeded(client, monkeypatch):
    monkeypatch.setenv("DEMO_USER_EMAIL", DEMO_EMAIL)
    monkeypatch.setenv("DEMO_PUBLIC", "1")
    assert client.post("/auth/demo").status_code == 503


def test_public_demo_seeds_without_a_password(monkeypatch):
    from backend.database import _session_factory

    monkeypatch.setenv("DEMO_USER_EMAIL", "nopw-demo@example.com")
    monkeypatch.delenv("DEMO_USER_PASSWORD", raising=False)
    monkeypatch.setenv("DEMO_PUBLIC", "1")
    assert seed_demo_from_env() is True
    db = _session_factory()()
    try:
        user = db.query(models.User).filter_by(email="nopw-demo@example.com").one()
        assert len(user.tasks) == len(SAMPLE_TASKS)
    finally:
        db.close()
    monkeypatch.delenv("DEMO_PUBLIC")
    assert seed_demo_from_env() is False  # without public mode a password is still required


def test_demo_token_stays_read_only_after_demo_public_is_removed(client, public_demo, monkeypatch):
    headers = demo_headers(client)
    monkeypatch.delenv("DEMO_PUBLIC")
    monkeypatch.delenv("DEMO_USER_EMAIL")
    assert client.get("/tasks", headers=headers).status_code == 200
    assert client.post("/tasks", json={"title": "x"}, headers=headers).status_code == 403
    assert client.post("/auth/demo").status_code == 404


def test_demo_token_is_short_lived(client, public_demo):
    import jwt, os
    from datetime import datetime, timezone

    token = client.post("/auth/demo").json()["access_token"]
    payload = jwt.decode(token, os.environ["SECRET_KEY"], algorithms=["HS256"])
    assert payload["demo"] is True
    assert payload["exp"] - datetime.now(timezone.utc).timestamp() <= 15 * 60 + 5


def test_ordinary_account_cannot_become_the_public_demo_through_configuration(client, db, monkeypatch):
    headers = register_and_login(client, DEMO_EMAIL)
    monkeypatch.setenv("DEMO_USER_EMAIL", DEMO_EMAIL.upper())
    monkeypatch.setenv("DEMO_PUBLIC", "1")

    assert seed_demo(db, DEMO_EMAIL, "unused-password") is False
    response = client.post("/auth/demo")
    assert response.status_code == 503
    assert "access_token" not in response.json()
    assert client.post("/tasks", headers=headers, json={"title": "My task"}).status_code == 201
