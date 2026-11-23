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


# ── Status contract ─────────────────────────────────────────

import pytest


@pytest.mark.parametrize("status", ["pending", "in_progress", "completed"])
def test_create_and_change_status_for_all_states(client, auth_headers, status):
    task = make_task(client, auth_headers, status=status)
    assert task["status"] == status
    for target in ["pending", "in_progress", "completed"]:
        r = client.patch(f"/tasks/{task['id']}", json={"status": target}, headers=auth_headers)
        assert r.status_code == 200 and r.json()["status"] == target
    listed = client.get("/tasks", headers=auth_headers).json()
    assert [t["status"] for t in listed] == ["completed"]


@pytest.mark.parametrize("bad", ["Pending", "In Progress", "done", "", "archived", 3, None])
def test_create_rejects_invalid_status(client, auth_headers, bad):
    r = client.post("/tasks", json={"title": "x", "status": bad}, headers=auth_headers)
    assert r.status_code == 422
    assert client.get("/tasks", headers=auth_headers).json() == []


@pytest.mark.parametrize("bad", ["Pending", "done", "", None])
def test_patch_rejects_invalid_status_and_leaves_task_unchanged(client, auth_headers, bad):
    task = make_task(client, auth_headers)
    r = client.patch(f"/tasks/{task['id']}", json={"status": bad}, headers=auth_headers)
    assert r.status_code == 422
    assert client.get(f"/tasks/{task['id']}", headers=auth_headers).json() == task


@pytest.mark.parametrize("bad", [None, "", "   "])
def test_title_must_be_present_and_not_blank(client, auth_headers, bad):
    assert client.post("/tasks", json={"title": bad}, headers=auth_headers).status_code == 422
    task = make_task(client, auth_headers)
    r = client.patch(f"/tasks/{task['id']}", json={"title": bad}, headers=auth_headers)
    assert r.status_code == 422
    assert client.get(f"/tasks/{task['id']}", headers=auth_headers).json()["title"] == task["title"]


def test_title_is_trimmed(client, auth_headers):
    assert make_task(client, auth_headers, title="  Hello  ")["title"] == "Hello"


def test_patch_null_description_clears_it(client, auth_headers):
    task = make_task(client, auth_headers)
    r = client.patch(f"/tasks/{task['id']}", json={"description": None}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["description"] is None
    assert r.json()["title"] == task["title"]


def test_patch_empty_body_changes_nothing(client, auth_headers):
    task = make_task(client, auth_headers)
    r = client.patch(f"/tasks/{task['id']}", json={}, headers=auth_headers)
    assert r.status_code == 200 and r.json() == task
