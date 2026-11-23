import os
import tempfile

# Set the environment BEFORE importing the app. Tests never read a developer's .env:
# only the real entry point (backend.main.app) loads it.
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only-0123456789"
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ.pop("OPENAI_API_KEY", None)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import rate_limit
from backend.database import Base, get_db
from backend.main import create_app


@pytest.fixture(autouse=True)
def _fresh_rate_limits(monkeypatch):
    """Every test starts with empty per-IP counters and the proxy/limit env at its defaults."""
    for name in ("AUTH_RATE_LIMIT", "AUTH_RATE_WINDOW_SECONDS", "TRUST_PROXY_HEADERS", "TRUSTED_PROXY_HOPS", "AI_DAILY_LIMIT"):
        monkeypatch.delenv(name, raising=False)
    rate_limit.reset()
    yield
    rate_limit.reset()


class FakeClock:
    """Stands in for rate_limit.clock (seconds) and ai_quota.utc_now (datetime)."""

    def __init__(self):
        from datetime import datetime, timezone

        self.seconds = 1000.0
        self.start = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    def advance(self, seconds: float) -> None:
        self.seconds += seconds

    def monotonic(self) -> float:
        return self.seconds

    def now(self):
        from datetime import timedelta

        return self.start + timedelta(seconds=self.seconds - 1000.0)


@pytest.fixture()
def fake_clock(monkeypatch):
    from backend import ai_quota

    clock = FakeClock()
    monkeypatch.setattr(rate_limit, "clock", clock.monotonic)
    monkeypatch.setattr(ai_quota, "utc_now", clock.now)
    return clock


@pytest.fixture()
def client():
    """TestClient backed by a fresh in-memory SQLite database per test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from backend import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def register_and_login(client: TestClient, email: str, password: str = "pw123456") -> dict:
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
