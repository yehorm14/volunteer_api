from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import openai
import pytest

from backend import schemas
from backend.ai_client import AI_DISABLED_DETAIL, get_async_openai_client, get_openai_client


@pytest.fixture()
def task_id(client, auth_headers):
    r = client.post("/tasks", json={"title": "Call the shelter"}, headers=auth_headers)
    return r.json()["id"]


def test_app_starts_without_openai_key(client):
    # The fixture removes OPENAI_API_KEY before import; reaching here means startup worked.
    assert client.get("/").status_code == 200


def test_categorize_returns_503_without_key(client, auth_headers, task_id):
    r = client.post(f"/tasks/{task_id}/ai-categorize", headers=auth_headers)
    assert r.status_code == 503
    assert r.json()["detail"] == AI_DISABLED_DETAIL


def test_extract_returns_503_without_key(client, auth_headers):
    r = client.post("/tasks/extract", params={"notes": "call shelter"}, headers=auth_headers)
    assert r.status_code == 503
    assert r.json()["detail"] == AI_DISABLED_DETAIL


def test_categorize_with_mocked_client(client, auth_headers, task_id):
    fake = MagicMock()
    fake.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Outreach: contacting a partner organisation."))]
    )
    client.app.dependency_overrides[get_openai_client] = lambda: fake

    r = client.post(f"/tasks/{task_id}/ai-categorize", headers=auth_headers)

    assert r.status_code == 200
    assert r.json() == {"task_id": task_id, "ai_suggestion": "Outreach: contacting a partner organisation."}
    assert fake.chat.completions.create.call_args.kwargs["model"] == "gpt-4o-mini"


def test_categorize_other_users_task_is_404(client, other_headers, task_id):
    client.app.dependency_overrides[get_openai_client] = lambda: MagicMock()
    r = client.post(f"/tasks/{task_id}/ai-categorize", headers=other_headers)
    assert r.status_code == 404


def test_extract_with_mocked_client_creates_task(client, auth_headers):
    parsed = schemas.ParsedTask(title="Call shelter", description="Ask about food donations next Tuesday.")
    fake = MagicMock()
    fake.beta.chat.completions.parse = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(refusal=None, parsed=parsed))]
        )
    )
    client.app.dependency_overrides[get_async_openai_client] = lambda: fake

    r = client.post("/tasks/extract", params={"notes": "call shelter re food, tues"}, headers=auth_headers)

    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Call shelter"
    assert body["status"] == "pending"
    # The task was persisted for the caller.
    tasks = client.get("/tasks", headers=auth_headers).json()
    assert [t["title"] for t in tasks] == ["Call shelter"]


def test_extract_refusal_returns_400(client, auth_headers):
    fake = MagicMock()
    fake.beta.chat.completions.parse = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(refusal="no", parsed=None))]
        )
    )
    client.app.dependency_overrides[get_async_openai_client] = lambda: fake

    r = client.post("/tasks/extract", params={"notes": "x"}, headers=auth_headers)
    assert r.status_code == 400


# --- ordering: ownership is checked before AI availability -------------------

def test_categorize_missing_task_is_404_even_without_key(client, auth_headers):
    assert client.post("/tasks/999/ai-categorize", headers=auth_headers).status_code == 404


def test_categorize_foreign_task_is_404_even_without_key(client, other_headers, task_id):
    assert client.post(f"/tasks/{task_id}/ai-categorize", headers=other_headers).status_code == 404


# --- provider errors map to a generic 503 ------------------------------------

SECRET_TEXT = "provider-internal-detail-xyz"


def _connection_error():
    return openai.APIConnectionError(request=httpx.Request("POST", "http://openai.invalid"))


@pytest.mark.parametrize("exc", [_connection_error(), openai.OpenAIError(SECRET_TEXT)])
def test_categorize_provider_errors_are_503_and_generic(client, auth_headers, task_id, exc):
    fake = MagicMock()
    fake.chat.completions.create.side_effect = exc
    client.app.dependency_overrides[get_openai_client] = lambda: fake

    r = client.post(f"/tasks/{task_id}/ai-categorize", headers=auth_headers)

    assert r.status_code == 503
    assert SECRET_TEXT not in r.text


@pytest.mark.parametrize("exc", [_connection_error(), openai.OpenAIError(SECRET_TEXT)])
def test_extract_provider_errors_are_503_and_generic(client, auth_headers, monkeypatch, exc):
    monkeypatch.setattr("backend.routers.ai.asyncio.sleep", AsyncMock())
    fake = MagicMock()
    fake.beta.chat.completions.parse = AsyncMock(side_effect=exc)
    client.app.dependency_overrides[get_async_openai_client] = lambda: fake

    r = client.post("/tasks/extract", params={"notes": "x"}, headers=auth_headers)

    assert r.status_code == 503
    assert SECRET_TEXT not in r.text
