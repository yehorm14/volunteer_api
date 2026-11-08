def make_task(client, headers, **overrides):
    payload = {"title": "Pack food boxes", "description": "Saturday, 10am"} | overrides
    r = client.post("/tasks", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_task_defaults(client, auth_headers):
    task = make_task(client, auth_headers)
    assert task["title"] == "Pack food boxes"
    assert task["status"] == "pending"
    assert task["id"] > 0


def test_list_tasks(client, auth_headers):
    assert client.get("/tasks", headers=auth_headers).json() == []
    make_task(client, auth_headers, title="one")
    make_task(client, auth_headers, title="two")
    titles = [t["title"] for t in client.get("/tasks", headers=auth_headers).json()]
    assert sorted(titles) == ["one", "two"]


def test_get_task(client, auth_headers):
    task = make_task(client, auth_headers)
    r = client.get(f"/tasks/{task['id']}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == task


def test_get_missing_task_404(client, auth_headers):
    assert client.get("/tasks/999", headers=auth_headers).status_code == 404


def test_patch_updates_only_given_fields(client, auth_headers):
    task = make_task(client, auth_headers)
    r = client.patch(f"/tasks/{task['id']}", json={"status": "completed"}, headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["title"] == task["title"]
    assert body["description"] == task["description"]


def test_delete_task(client, auth_headers):
    task = make_task(client, auth_headers)
    assert client.delete(f"/tasks/{task['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/tasks/{task['id']}", headers=auth_headers).status_code == 404


def test_create_requires_title(client, auth_headers):
    r = client.post("/tasks", json={"description": "no title"}, headers=auth_headers)
    assert r.status_code == 422


def test_users_only_see_their_own_tasks(client, auth_headers, other_headers):
    make_task(client, auth_headers, title="alice task")
    assert client.get("/tasks", headers=other_headers).json() == []


def test_user_cannot_read_update_or_delete_others_task(client, auth_headers, other_headers):
    task = make_task(client, auth_headers)
    url = f"/tasks/{task['id']}"
    assert client.get(url, headers=other_headers).status_code == 404
    assert client.patch(url, json={"title": "hijacked"}, headers=other_headers).status_code == 404
    assert client.delete(url, headers=other_headers).status_code == 404
    # Owner's task is untouched.
    assert client.get(url, headers=auth_headers).json()["title"] == task["title"]
