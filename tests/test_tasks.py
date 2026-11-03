"""Tests for creating and listing tasks (SRS FR-01, FR-05 and its limits).

Every test replaces the ``db`` functions with stand-ins, so there are no AWS
calls. The rejection tests also check that the database was never reached.
"""

import pytest

from jira_lite import db


@pytest.fixture
def create_calls(monkeypatch):
    """Replace ``db.create_task`` with a stand-in and return its call log."""
    calls = []

    def fake_create_task(clean):
        calls.append(clean)
        return {"id": "task-1", "created_at": "2026-01-01T00:00:00.000000Z", **clean}

    monkeypatch.setattr(db, "create_task", fake_create_task)
    return calls


@pytest.mark.parametrize(
    "body",
    [
        {"title": "   "},
        {"title": "a" * 201},
        {"title": "ok", "description": "b" * 2001},
        {"title": "ok", "status": "Blocked"},
    ],
    ids=["blank-title", "title-too-long", "description-too-long", "bad-status"],
)
def test_create_rejects_invalid_input(client, create_calls, body):
    response = client.post("/api/tasks", json=body)

    assert response.status_code == 400
    assert response.get_json()["error"]
    assert create_calls == []


def test_create_accepts_values_at_the_limits(client, create_calls):
    body = {"title": "a" * 200, "description": "b" * 2000}

    response = client.post("/api/tasks", json=body)

    assert response.status_code == 201
    assert create_calls == [
        {"title": "a" * 200, "description": "b" * 2000, "status": "To Do"}
    ]
    created = response.get_json()
    assert created["id"] == "task-1"
    assert created["status"] == "To Do"


def test_list_returns_tasks(client, monkeypatch):
    tasks = [
        {
            "id": "task-1",
            "title": "First",
            "description": "",
            "status": "Done",
            "created_at": "2026-01-01T00:00:00.000000Z",
        }
    ]
    monkeypatch.setattr(db, "list_tasks", lambda: tasks)

    response = client.get("/api/tasks")

    assert response.status_code == 200
    assert response.get_json() == tasks
