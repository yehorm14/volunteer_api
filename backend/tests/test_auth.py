from jose import jwt

from backend import auth


def test_register_returns_user_without_password(client):
    r = client.post("/auth/register", json={"email": "a@example.com", "password": "pw12345"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "a@example.com"
    assert body["tasks"] == []
    assert "password" not in body and "hashed_password" not in body


def test_register_duplicate_email_rejected(client):
    payload = {"email": "a@example.com", "password": "pw12345"}
    assert client.post("/auth/register", json=payload).status_code == 201
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 400


def test_login_returns_valid_jwt(client):
    client.post("/auth/register", json={"email": "a@example.com", "password": "pw12345"})
    r = client.post("/auth/login", data={"username": "a@example.com", "password": "pw12345"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    claims = jwt.decode(body["access_token"], auth.get_secret_key(), algorithms=[auth._algorithm()])
    assert claims["sub"] == "a@example.com"


def test_login_wrong_password(client):
    client.post("/auth/register", json={"email": "a@example.com", "password": "pw12345"})
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
    assert client.post("/tasks/extract", params={"notes": "x"}).status_code == 401


def test_invalid_token_rejected(client):
    r = client.get("/tasks", headers={"Authorization": "Bearer not-a-token"})
    assert r.status_code == 401


def test_token_for_deleted_user_rejected(client):
    token = auth.create_access_token({"sub": "ghost@example.com"})
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
    client.post("/auth/register", json={"email": "a@example.com", "password": "pw12345"})
    r = client.post("/auth/login", data={"username": "a@example.com", "password": "x" * 100})
    assert r.status_code == 401
