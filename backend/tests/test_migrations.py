"""Migrations and the app restart flow, on SQLite always and on Postgres when TEST_DATABASE_URL is set.

TEST_DATABASE_URL must point at a server where the user may CREATE/DROP DATABASE, e.g.
postgresql://postgres:postgres@localhost:5432/postgres. Each test gets its own uniquely named
database, so repeated or concurrent runs never share state.
"""
import os
import uuid

import pytest
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Boolean, Table, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from backend import auth, database, migrate
from backend.database import Base, normalize_database_url
from backend.main import create_app

ADMIN_URL = os.getenv("TEST_DATABASE_URL")
BACKENDS = ["sqlite"] + (["postgres"] if ADMIN_URL else [])


@pytest.fixture(params=BACKENDS)
def db_url(request, tmp_path):
    if request.param == "sqlite":
        yield f"sqlite:///{tmp_path}/mig.db"
        return
    admin = create_engine(normalize_database_url(ADMIN_URL), isolation_level="AUTOCOMMIT")
    name = f"vt_{uuid.uuid4().hex[:12]}"
    with admin.connect() as c:
        c.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        yield make_url(normalize_database_url(ADMIN_URL)).set(database=name).render_as_string(hide_password=False)
    finally:
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


def _reset_engine():
    if database.get_engine.cache_info().currsize:
        database.get_engine().dispose()
    database.get_engine.cache_clear()
    database._session_factory.cache_clear()


@pytest.fixture()
def use_db(db_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", db_url)
    _reset_engine()
    yield db_url
    _reset_engine()


def _legacy_tables(url):
    """The schema create_all() produced before migrations existed, plus untidy rows."""
    meta = MetaData()
    Table("users", meta,
          Column("id", Integer, primary_key=True, index=True),
          Column("email", String, unique=True, index=True),
          Column("hashed_password", String), Column("is_active", Boolean))
    Table("tasks", meta,
          Column("id", Integer, primary_key=True, index=True),
          Column("title", String, index=True), Column("description", String, index=True),
          Column("status", String), Column("owner_id", Integer, ForeignKey("users.id")))
    engine = create_engine(normalize_database_url(url))
    meta.create_all(engine)
    with engine.begin() as c:
        c.execute(meta.tables["users"].insert().values(id=1, email="a@example.com", hashed_password="x", is_active=True))
        c.execute(meta.tables["tasks"].insert(), [
            {"id": 1, "title": "keep me", "description": "d", "status": "In Progress", "owner_id": 1},
            {"id": 2, "title": None, "description": None, "status": None, "owner_id": 1},
            {"id": 3, "title": "done one", "description": None, "status": "done", "owner_id": 1},
            {"id": 4, "title": "fine", "description": None, "status": "pending", "owner_id": 1},
        ])
    engine.dispose()


def _revision():
    with database.get_engine().connect() as c:
        return c.execute(text("SELECT version_num FROM alembic_version")).scalar()


# NOTE: compare_metadata only checks the lower(email) expression index meaningfully on Postgres;
# SQLite reflection ignores expression indexes, so the postgres CI job is the real check.
def test_empty_database_reaches_target_schema(use_db):
    migrate.upgrade_to_head()
    assert migrate.is_up_to_date()
    with database.get_engine().connect() as c:
        # The migrated schema is exactly what the models describe.
        assert compare_metadata(MigrationContext.configure(c), Base.metadata) == []
    with pytest.raises(IntegrityError), database.get_engine().begin() as c:
        c.execute(text("INSERT INTO users (id, email) VALUES (1, 'a@example.com')"))
        c.execute(text("INSERT INTO tasks (title, status, owner_id) VALUES ('t', 'bogus', 1)"))


def test_existing_database_is_adopted_without_losing_tasks(use_db):
    _legacy_tables(use_db)
    assert not migrate.is_up_to_date()
    migrate.upgrade_to_head()
    with database.get_engine().connect() as c:
        rows = c.execute(text("SELECT id, title, status FROM tasks ORDER BY id")).all()
        assert compare_metadata(MigrationContext.configure(c), Base.metadata) == []
    assert rows == [
        (1, "keep me", "in_progress"),
        (2, "(untitled)", "pending"),
        (3, "done one", "completed"),
        (4, "fine", "pending"),
    ]
    assert migrate.is_up_to_date()


def test_upgrade_is_repeatable(use_db):
    _legacy_tables(use_db)
    migrate.upgrade_to_head()
    rev = _revision()
    migrate.upgrade_to_head()
    migrate.upgrade_to_head()
    assert _revision() == rev
    with database.get_engine().connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM tasks")).scalar() == 4


def test_unrecognised_existing_schema_is_refused_untouched(use_db):
    engine = create_engine(normalize_database_url(use_db))
    with engine.begin() as c:
        c.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR)"))
    engine.dispose()
    with pytest.raises(RuntimeError, match="missing"):
        migrate.upgrade_to_head()
    with database.get_engine().connect() as c:
        assert "alembic_version" not in {r[0] for r in c.execute(text(
            "SELECT name FROM sqlite_master" if use_db.startswith("sqlite")
            else "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))}


def test_auth_task_flow_survives_an_app_restart(use_db):
    """Register, create and edit tasks, 'restart' the app (new engine, new app), and find them again."""
    creds = {"email": "vol@example.com", "password": "pw123456"}

    def login(client):
        r = client.post("/auth/login", data={"username": creds["email"], "password": creds["password"]})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    with TestClient(create_app()) as client:  # startup applies the migrations
        assert client.post("/auth/register", json=creds).status_code == 201
        h = login(client)
        t = client.post("/tasks", json={"title": "Pack boxes", "description": "10am"}, headers=h).json()
        assert client.patch(f"/tasks/{t['id']}", json={"status": "in_progress"}, headers=h).status_code == 200
        assert client.patch(f"/tasks/{t['id']}", json={"status": "nope"}, headers=h).status_code == 422
        client.post("/tasks", json={"title": "second", "status": "completed"}, headers=h)

    _reset_engine()  # everything in process memory is gone; only the database remains

    with TestClient(create_app()) as client:
        h = login(client)
        tasks = {x["title"]: x for x in client.get("/tasks", headers=h).json()}
        assert tasks["Pack boxes"]["status"] == "in_progress"
        assert tasks["Pack boxes"]["description"] == "10am"
        assert tasks["second"]["status"] == "completed"
        assert client.delete(f"/tasks/{t['id']}", headers=h).status_code == 204


def test_email_migration_normalises_and_resolves_duplicates(use_db):
    """0004 trims whitespace and lower-cases emails, then renames and deactivates duplicates."""
    from alembic import command

    with database.get_engine().connect() as c:
        cfg = migrate._config(c)
        command.upgrade(cfg, "0003")
        c.execute(text("INSERT INTO users (id, email, hashed_password, is_active) VALUES "
                       "(1, 'Alice@Example.com', 'x', true), (2, 'alice@example.com', 'x', true), "
                       "(3, 'ALICE@example.com', 'x', true), (4, 'Bob@Example.com', 'x', true), (5, NULL, 'x', true), "
                       "(6, 'alice+duplicate-2@example.com', 'x', true), "
                       "(7, 'ALICE+DUPLICATE-2-2@EXAMPLE.COM', 'x', true), "
                       "(8, :padded, 'x', true), (9, 'ånne@example.com', 'x', true), "
                       "(10, ' ånne+duplicate-9@example.com ', 'x', true)"),
                  {"padded": "\u2003ÅNNE@Example.com\t"})
        c.execute(text("INSERT INTO tasks (title, status, owner_id) VALUES ('mine', 'pending', 2)"))
        c.commit()
    migrate.upgrade_to_head()
    with database.get_engine().connect() as c:
        rows = c.execute(text("SELECT id, email, is_active FROM users ORDER BY id")).all()
        assert [(r[0], r[1], bool(r[2])) for r in rows] == [
            (1, "alice@example.com", True),
            (2, "alice+duplicate-2-3@example.com", False),
            (3, "alice+duplicate-3@example.com", False),
            (4, "bob@example.com", True),
            (5, None, True),
            (6, "alice+duplicate-2@example.com", True),
            (7, "alice+duplicate-2-2@example.com", True),
            (8, "ånne@example.com", True),
            (9, "ånne+duplicate-9-2@example.com", False),
            (10, "ånne+duplicate-9@example.com", True),
        ]
        assert c.execute(text("SELECT owner_id FROM tasks")).scalar() == 2  # no data lost
    with pytest.raises(IntegrityError), database.get_engine().begin() as c:
        c.execute(text("INSERT INTO users (email) VALUES ('BOB@example.com')"))


def test_legacy_email_whitespace_and_unicode_case_do_not_break_login(use_db):
    from alembic import command

    password = "pw123456"
    legacy_email = "\u2003Øystein@Example.com\t"
    with database.get_engine().connect() as c:
        command.upgrade(migrate._config(c), "0003")
        c.execute(text("INSERT INTO users (id, email, hashed_password, is_active) VALUES (1, :email, :password, true)"),
                  {"email": legacy_email, "password": auth.get_password_hash(password)})
        c.execute(text("INSERT INTO tasks (title, status, owner_id) VALUES ('keep my task', 'pending', 1)"))
        c.commit()

    with TestClient(create_app()) as client:
        for email in (legacy_email, "øystein@example.com"):
            response = client.post("/auth/login", data={"username": email, "password": password})
            assert response.status_code == 200, response.text
            headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
            tasks = client.get("/tasks", headers=headers)
            assert tasks.status_code == 200
            assert [task["title"] for task in tasks.json()] == ["keep my task"]


@pytest.mark.parametrize("demo_email, expected_demo_id", [
    ("Sample@Example.com", 1),
    ("SAMPLE@example.com", None),
    ("sample@example.com", None),
    ("Other@Example.com", None),
])
def test_email_migration_retains_only_the_configured_demo_identity(use_db, monkeypatch, demo_email, expected_demo_id):
    from alembic import command

    monkeypatch.setenv("DEMO_PUBLIC", "1")
    monkeypatch.setenv("DEMO_USER_EMAIL", demo_email)
    with database.get_engine().connect() as c:
        command.upgrade(migrate._config(c), "0003")
        c.execute(text("INSERT INTO users (id, email, is_active) VALUES "
                       "(1, 'Sample@Example.com', true), (2, 'SAMPLE@example.com', true), "
                       "(3, ' Other@Example.com ', true), (4, 'Other@Example.com', true)"))
        c.commit()

    migrate.upgrade_to_head()

    with database.get_engine().connect() as c:
        demo_ids = c.execute(text("SELECT id FROM users WHERE is_demo AND is_active")).scalars().all()
        assert demo_ids == ([expected_demo_id] if expected_demo_id is not None else [])
