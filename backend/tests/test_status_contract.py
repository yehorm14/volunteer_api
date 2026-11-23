"""Keep the backend, database and TypeScript status contracts in step."""
import re
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from backend import models
from backend.database import Base
from backend.task_status import TASK_STATUSES, normalize_legacy_status, normalize_task_statuses

REPO = Path(__file__).resolve().parents[2]


def test_status_values():
    assert TASK_STATUSES == ("pending", "in_progress", "completed")


def test_openapi_enum_matches(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert tuple(schemas["TaskCreate"]["properties"]["status"]["enum"]) == TASK_STATUSES


def test_typescript_union_matches():
    ts = (REPO / "frontend/src/types/index.ts").read_text()
    union = re.search(r"export type TaskStatus =([^\n]+)", ts).group(1)
    assert tuple(re.findall(r"'([a-z_]+)'", union)) == TASK_STATUSES


def test_frontend_labels_cover_every_status():
    src = (REPO / "frontend/src/components/tasks/TaskStatusBadge.tsx").read_text()
    for status in TASK_STATUSES:
        assert re.search(rf"\b{status}:\s*\{{\s*label:", src), status


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("pending", "pending"), ("In Progress", "in_progress"), ("in-progress", "in_progress"),
        ("  DONE ", "completed"), ("To Do", "pending"), ("", "pending"), (None, "pending"),
        ("something else", "pending"),
    ],
)
def test_normalize_legacy_status(raw, expected):
    assert normalize_legacy_status(raw) == expected


def _legacy_engine():
    """A database as the app created it before the contract: no CHECK constraint, free-text status."""
    engine = create_engine("sqlite://")
    with engine.begin() as c:
        c.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR, hashed_password VARCHAR, is_active BOOLEAN)"))
        c.execute(text("CREATE TABLE tasks (id INTEGER PRIMARY KEY, title VARCHAR, description VARCHAR, status VARCHAR, owner_id INTEGER)"))
        c.execute(text("INSERT INTO users VALUES (1, 'a@example.com', 'x', 1)"))
        for i, st in enumerate(["pending", "In Progress", "done", None, "weird"], start=1):
            c.execute(text("INSERT INTO tasks VALUES (:i, :t, NULL, :s, 1)"), {"i": i, "t": f"task {i}", "s": st})
    return engine


def _normalize(engine):
    with engine.begin() as conn:
        return normalize_task_statuses(conn)


def test_normalisation_keeps_every_task():
    engine = _legacy_engine()
    assert _normalize(engine) == 4
    with engine.connect() as c:
        rows = c.execute(text("SELECT title, status FROM tasks ORDER BY id")).all()
    assert [r[1] for r in rows] == ["pending", "in_progress", "completed", "pending", "pending"]
    assert _normalize(engine) == 0  # idempotent


def test_database_constraint_rejects_bad_status():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    with engine.begin() as c:
        c.execute(text("INSERT INTO users (id, email) VALUES (1, 'a@example.com')"))
        with pytest.raises(IntegrityError):
            c.execute(text("INSERT INTO tasks (title, status, owner_id) VALUES ('t', 'bogus', 1)"))
    assert models.Task.__table__.c.status.nullable is False


def test_legacy_status_is_still_listed(client, auth_headers):
    """A row that slipped past normalisation must not break GET /tasks."""
    from backend.database import get_db

    task = client.post("/tasks", json={"title": "x"}, headers=auth_headers).json()
    session = next(client.app.dependency_overrides[get_db]())
    session.execute(text("PRAGMA ignore_check_constraints = ON"))
    session.execute(text("UPDATE tasks SET status = 'In Progress' WHERE id = :i"), {"i": task["id"]})
    session.commit()
    r = client.get("/tasks", headers=auth_headers)
    assert r.status_code == 200 and r.json()[0]["status"] == "In Progress"
