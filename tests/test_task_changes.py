"""Tests for editing and deleting tasks (SRS FR-03, FR-04).

Every test replaces the ``db`` functions with stand-ins, so there are no AWS
calls. The rejection test also checks that the database was never reached.
"""

from jira_lite import db

TASK_ID = "6f1d6a0e-3b9c-4c53-8d2b-0a7b1f4f9e11"


def test_edit_updates_the_task(client, monkeypatch):
    calls = []

    def fake_update_task(task_id, clean):
        calls.append((task_id, clean))
        return {"id": task_id, "created_at": "2026-01-01T00:00:00.000000Z", **clean}

    monkeypatch.setattr(db, "update_task", fake_update_task)
    body = {"title": "  New title ", "description": "New", "status": "Done"}

    response = client.put(f"/api/tasks/{TASK_ID}", json=body)

    assert response.status_code == 200
    assert calls == [
        (TASK_ID, {"title": "New title", "description": "New", "status": "Done"})
    ]
    assert response.get_json()["status"] == "Done"


def test_edit_rejects_invalid_input(client, monkeypatch):
    calls = []
    monkeypatch.setattr(db, "update_task", lambda *args: calls.append(args))

    response = client.put(f"/api/tasks/{TASK_ID}", json={"title": "   "})

    assert response.status_code == 400
    assert response.get_json()["error"]
    assert calls == []


def test_delete_removes_the_task(client, monkeypatch):
    calls = []
    monkeypatch.setattr(db, "delete_task", calls.append)

    response = client.delete(f"/api/tasks/{TASK_ID}")

    assert response.status_code == 204
    assert response.get_data() == b""
    assert calls == [TASK_ID]
