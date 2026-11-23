"""Login/register per-IP throttle and the per-user daily AI quota. No test sleeps: time is faked."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend import schemas
from backend.ai_client import get_async_openai_client, get_openai_client

BAD = {"username": "nobody@example.com", "password": "wrong-password"}


def _login(client, headers=None):
    return client.post("/auth/login", data=BAD, headers=headers or {})


def test_sixth_login_in_a_minute_is_429(client, fake_clock):
    assert [_login(client).status_code for _ in range(5)] == [401] * 5
    r = _login(client)
    assert r.status_code == 429
    assert "Too many attempts" in r.json()["detail"]
    assert int(r.headers["Retry-After"]) >= 1


def test_login_allowed_again_after_the_window(client, fake_clock):
    for _ in range(5):
        _login(client)
    assert _login(client).status_code == 429
    fake_clock.advance(61)
    assert _login(client).status_code == 401


def test_register_is_limited_separately_from_login(client, fake_clock):
    for _ in range(5):
        _login(client)
    assert _login(client).status_code == 429
    r = client.post("/auth/register", json={"email": "a@example.com", "password": "pw123456"})
    assert r.status_code == 201
    for i in range(4):
        client.post("/auth/register", json={"email": f"b{i}@example.com", "password": "pw123456"})
    r = client.post("/auth/register", json={"email": "c@example.com", "password": "pw123456"})
    assert r.status_code == 429


def test_limit_is_configurable(client, fake_clock, monkeypatch):
    monkeypatch.setenv("AUTH_RATE_LIMIT", "2")
    monkeypatch.setenv("AUTH_RATE_WINDOW_SECONDS", "10")
    assert [_login(client).status_code for _ in range(3)] == [401, 401, 429]
    fake_clock.advance(11)
    assert _login(client).status_code == 401


def test_invalid_limit_value_fails_clearly(client, monkeypatch):
    monkeypatch.setenv("AUTH_RATE_LIMIT", "lots")
    with pytest.raises(RuntimeError, match="AUTH_RATE_LIMIT"):
        _login(client)


def test_forwarded_for_is_ignored_unless_trusted(client, fake_clock):
    for i in range(5):
        _login(client, {"X-Forwarded-For": f"203.0.113.{i}"})
    assert _login(client, {"X-Forwarded-For": "203.0.113.99"}).status_code == 429


def test_trusted_forwarded_for_separates_clients(client, fake_clock, monkeypatch):
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
    for _ in range(5):
        _login(client, {"X-Forwarded-For": "198.51.100.7"})
    assert _login(client, {"X-Forwarded-For": "198.51.100.7"}).status_code == 429
    assert _login(client, {"X-Forwarded-For": "198.51.100.8"}).status_code == 401


def test_trusted_forwarded_for_cannot_be_spoofed_from_the_left(client, fake_clock, monkeypatch):
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
    for i in range(5):  # the client prepends fake addresses; the proxy appends the real one
        _login(client, {"X-Forwarded-For": f"10.0.0.{i}, 198.51.100.7"})
    assert _login(client, {"X-Forwarded-For": "10.0.0.250, 198.51.100.7"}).status_code == 429


def test_trusted_proxy_hops_picks_the_entry_from_the_right(client, fake_clock, monkeypatch):
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "2")
    for i in range(5):  # real client, then one proxy hop (e.g. a CDN) in front of the platform proxy
        _login(client, {"X-Forwarded-For": f"198.51.100.7, 192.0.2.{i}"})
    assert _login(client, {"X-Forwarded-For": "198.51.100.7, 192.0.2.250"}).status_code == 429


def test_tracked_ips_are_capped_and_expired_keys_pruned(client, fake_clock, monkeypatch):
    from backend import rate_limit

    monkeypatch.setattr(rate_limit, "MAX_TRACKED_KEYS", 5)
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
    for i in range(20):
        _login(client, {"X-Forwarded-For": f"198.51.100.{i}"})
    assert len(rate_limit._hits) == 5  # least recently seen evicted
    assert ("/auth/login", "198.51.100.19") in rate_limit._hits
    fake_clock.advance(61)
    _login(client, {"X-Forwarded-For": "203.0.113.1"})
    assert list(rate_limit._hits) == [("/auth/login", "203.0.113.1")]  # expired keys dropped


# --- AI quota ---------------------------------------------------------------------------------

@pytest.fixture()
def fake_ai(client):
    sync = MagicMock()
    sync.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Outreach: x."))]
    )
    parsed = schemas.ParsedTask(title="T", description="D")
    asyn = MagicMock()
    asyn.beta.chat.completions.parse = AsyncMock(
        return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(refusal=None, parsed=parsed))])
    )
    client.app.dependency_overrides[get_openai_client] = lambda: sync
    client.app.dependency_overrides[get_async_openai_client] = lambda: asyn
    return sync, asyn


def _categorize(client, headers, task_id):
    return client.post(f"/tasks/{task_id}/ai-categorize", headers=headers)


def _extract(client, headers):
    return client.post("/tasks/extract", json={"notes": "call shelter"}, headers=headers)


def test_quota_is_shared_by_both_endpoints_and_resets_next_utc_day(client, auth_headers, fake_ai, fake_clock, monkeypatch):
    monkeypatch.setenv("AI_DAILY_LIMIT", "3")
    task_id = client.post("/tasks", json={"title": "t"}, headers=auth_headers).json()["id"]
    assert _categorize(client, auth_headers, task_id).status_code == 200
    assert _extract(client, auth_headers).status_code == 201
    assert _categorize(client, auth_headers, task_id).status_code == 200
    r = _extract(client, auth_headers)
    assert r.status_code == 429
    assert "Daily AI limit reached (3 per day)" in r.json()["detail"]
    assert _categorize(client, auth_headers, task_id).status_code == 429
    assert fake_ai[1].beta.chat.completions.parse.await_count == 1  # no provider call once over quota

    fake_clock.advance(11 * 3600 + 59 * 60)  # 23:59 UTC, still the same day
    assert _extract(client, auth_headers).status_code == 429
    fake_clock.advance(2 * 60)  # past midnight UTC
    assert _extract(client, auth_headers).status_code == 201


def test_quota_is_per_user(client, auth_headers, other_headers, fake_ai, fake_clock, monkeypatch):
    monkeypatch.setenv("AI_DAILY_LIMIT", "1")
    assert _extract(client, auth_headers).status_code == 201
    assert _extract(client, auth_headers).status_code == 429
    assert _extract(client, other_headers).status_code == 201


def test_default_quota_is_20(client, auth_headers, fake_ai, fake_clock):
    assert [_extract(client, auth_headers).status_code for _ in range(21)] == [201] * 20 + [429]


def test_failed_requests_do_not_use_the_quota(client, auth_headers, fake_clock, monkeypatch):
    monkeypatch.setenv("AI_DAILY_LIMIT", "1")
    task_id = client.post("/tasks", json={"title": "t"}, headers=auth_headers).json()["id"]
    assert _categorize(client, auth_headers, task_id).status_code == 503  # no OPENAI_API_KEY
    assert _categorize(client, auth_headers, 9999).status_code == 404
    sync = MagicMock()
    sync.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
    )
    client.app.dependency_overrides[get_openai_client] = lambda: sync
    assert _categorize(client, auth_headers, task_id).status_code == 200  # the quota is still intact


def test_provider_failure_refunds_the_call(client, auth_headers, fake_clock, monkeypatch):
    import httpx
    import openai

    monkeypatch.setenv("AI_DAILY_LIMIT", "1")
    task_id = client.post("/tasks", json={"title": "t"}, headers=auth_headers).json()["id"]
    broken = MagicMock()
    broken.chat.completions.create.side_effect = openai.APIConnectionError(
        request=httpx.Request("POST", "https://api.openai.com")
    )
    client.app.dependency_overrides[get_openai_client] = lambda: broken
    assert _categorize(client, auth_headers, task_id).status_code == 503
    ok = MagicMock()
    ok.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
    )
    client.app.dependency_overrides[get_openai_client] = lambda: ok
    assert _categorize(client, auth_headers, task_id).status_code == 200


def test_invalid_quota_value_fails_clearly(client, auth_headers, fake_ai, monkeypatch):
    monkeypatch.setenv("AI_DAILY_LIMIT", "0")
    with pytest.raises(RuntimeError, match="AI_DAILY_LIMIT"):
        _extract(client, auth_headers)
