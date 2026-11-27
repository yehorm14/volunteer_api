import jwt
import pytest

from backend import models
from backend.database import get_db

from backend import auth


def test_register_returns_user_without_password(client):
    r = client.post("/auth/register", json={"email": "a@example.com", "password": "pw123456"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "a@example.com"
    assert body["tasks"] == []
    assert "password" not in body and "hashed_password" not in body


def test_register_duplicate_email_rejected(client):
    payload = {"email": "a@example.com", "password": "pw123456"}
    assert client.post("/auth/register", json=payload).status_code == 201
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 400


def test_login_returns_valid_jwt(client):
    client.post("/auth/register", json={"email": "a@example.com", "password": "pw123456"})
    r = client.post("/auth/login", data={"username": "a@example.com", "password": "pw123456"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    claims = jwt.decode(body["access_token"], auth.get_secret_key(), algorithms=[auth._algorithm()])
    assert claims["sub"] == "a@example.com"
    assert isinstance(claims["uid"], int)


def test_login_wrong_password(client):
    client.post("/auth/register", json={"email": "a@example.com", "password": "pw123456"})
    r = client.post("/auth/login", data={"username": "a@example.com", "password": "wrong"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/auth/login", data={"username": "nobody@example.com", "password": "x"})
    assert r.status_code == 401


def test_protected_routes_require_token(client):
    assert client.get("/tasks").status_code == 401
    assert client.post("/tasks", json={"title": "x"}).status_code == 401
    assert client.get("/tasks/1").status_code == 401
    assert client.patch("/tasks/1", json={"title": "x"}).status_code == 401
    assert client.delete("/tasks/1").status_code == 401
    assert client.post("/tasks/1/ai-categorize").status_code == 401
    assert client.post("/tasks/extract", json={"notes": "x"}).status_code == 401


def test_invalid_token_rejected(client):
    r = client.get("/tasks", headers={"Authorization": "Bearer not-a-token"})
    assert r.status_code == 401


def test_token_for_deleted_user_rejected(client):
    token = auth.create_access_token({"sub": "ghost@example.com", "uid": 9999})
    r = client.get("/tasks", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_register_rejects_password_over_72_bytes(client):
    r = client.post("/auth/register", json={"email": "a@example.com", "password": "x" * 73})
    assert r.status_code == 422


def test_register_counts_bytes_not_characters(client):
    # 37 two-byte characters = 74 bytes, but only 37 characters.
    r = client.post("/auth/register", json={"email": "a@example.com", "password": "é" * 37})
    assert r.status_code == 422


def test_register_accepts_72_byte_password(client):
    r = client.post("/auth/register", json={"email": "a@example.com", "password": "x" * 72})
    assert r.status_code == 201


def test_login_with_over_long_password_is_401_not_500(client):
    client.post("/auth/register", json={"email": "a@example.com", "password": "pw123456"})
    r = client.post("/auth/login", data={"username": "a@example.com", "password": "x" * 100})
    assert r.status_code == 401


def test_register_rejects_short_password(client):
    r = client.post("/auth/register", json={"email": "a@example.com", "password": "x" * 7})
    assert r.status_code == 422
    assert "at least 8" in r.text


def test_register_accepts_8_character_password(client):
    r = client.post("/auth/register", json={"email": "a@example.com", "password": "x" * 8})
    assert r.status_code == 201


@pytest.mark.parametrize("bad", ["not-an-email", "a@", "@example.com", "a b@example.com", "User <a@example.com>", ""])
def test_register_invalid_email_rejected(client, bad):
    response = client.post("/auth/register", json={"email": bad, "password": "pw123456"})
    assert response.status_code == 422


def test_login_accepts_the_international_domain_spelling_used_at_registration(client):
    email = "volunteer@xn--bcher-kva.de"
    response = client.post("/auth/register", json={"email": email, "password": "pw123456"})
    assert response.status_code == 201
    assert response.json()["email"] == email
    assert _login_headers(client, email.upper())


def test_register_stores_lower_case_email(client):
    r = client.post("/auth/register", json={"email": "  Mixed.Case@Example.COM ", "password": "pw123456"})
    assert r.status_code == 201
    assert r.json()["email"] == "mixed.case@example.com"


def test_register_mixed_case_duplicate_rejected(client):
    assert client.post("/auth/register", json={"email": "a@example.com", "password": "pw123456"}).status_code == 201
    r = client.post("/auth/register", json={"email": "A@Example.com", "password": "pw123456"})
    assert r.status_code == 400


def test_login_is_case_insensitive(client):
    client.post("/auth/register", json={"email": "Vol@Example.com", "password": "pw123456"})
    for username in ["vol@example.com", "VOL@EXAMPLE.COM", "Vol@Example.com"]:
        r = client.post("/auth/login", data={"username": username, "password": "pw123456"})
        assert r.status_code == 200, username
        token = r.json()["access_token"]
        assert client.get("/tasks", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def _db(client):
    return next(client.app.dependency_overrides[get_db]())


def _login_headers(client, email, password="pw123456"):
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _deactivate(client, email):
    db = _db(client)
    user = db.query(models.User).filter(models.User.email == email).one()
    user.is_active = False
    db.commit()
    db.close()


def test_inactive_user_cannot_log_in(client):
    client.post("/auth/register", json={"email": "a@example.com", "password": "pw123456"})
    _deactivate(client, "a@example.com")
    bad = client.post("/auth/login", data={"username": "a@example.com", "password": "wrong"})
    r = client.post("/auth/login", data={"username": "a@example.com", "password": "pw123456"})
    assert r.status_code == 401
    assert r.json() == bad.json()


def test_token_of_user_deactivated_later_is_rejected(client):
    client.post("/auth/register", json={"email": "a@example.com", "password": "pw123456"})
    headers = _login_headers(client, "a@example.com")
    assert client.get("/tasks", headers=headers).status_code == 200
    _deactivate(client, "a@example.com")
    assert client.get("/tasks", headers=headers).status_code == 401


def test_legacy_email_subject_token_is_rejected(client):
    client.post("/auth/register", json={"email": "a@example.com", "password": "pw123456"})
    legacy = auth.create_access_token({"sub": "a@example.com"})
    assert client.get("/tasks", headers={"Authorization": f"Bearer {legacy}"}).status_code == 401
    bad_uid = auth.create_access_token({"sub": "a@example.com", "uid": "1"})
    assert client.get("/tasks", headers={"Authorization": f"Bearer {bad_uid}"}).status_code == 401


def test_renamed_duplicate_token_cannot_read_keeper_tasks(client):
    """After migration 0004 an old token whose subject was the duplicate's original email must not reach the keeper."""
    client.post("/auth/register", json={"email": "a@x.com", "password": "pw123456"})
    keeper = _login_headers(client, "a@x.com")
    assert client.post("/tasks", json={"title": "secret"}, headers=keeper).status_code in (200, 201)
    client.post("/auth/register", json={"email": "dup@x.com", "password": "pw123456"})
    db = _db(client)
    dup = db.query(models.User).filter(models.User.email == "dup@x.com").one()
    dup.email, dup.is_active = f"a+duplicate-{dup.id}@x.com", False
    db.commit()
    dup_id = dup.id
    db.close()
    # Legacy token (subject was the duplicate's old, now lower-cased, email) and a uid token for the renamed account.
    legacy = auth.create_access_token({"sub": "a@x.com"})
    renamed = auth.create_access_token({"sub": f"a+duplicate-{dup_id}@x.com", "uid": dup_id})
    for token in (legacy, renamed):
        r = client.get("/tasks", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401
