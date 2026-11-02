"""Tests for GET /health (SRS FR-06, NFR-03; ADR-018).

Both tests replace ``db.check_connection`` with a stand-in, so they make no
AWS calls. They cover the two outcomes the SRS requires: database available
and database unavailable. A Flask-only success response is not enough.
"""

from jira_lite import db


def test_health_returns_200_when_database_responds(client, monkeypatch):
    monkeypatch.setattr(db, "check_connection", lambda: None)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_without_leaking_error_when_database_fails(
    client, monkeypatch
):
    def fail():
        raise db.DatabaseError("AccessDeniedException on table secret-table-name")

    monkeypatch.setattr(db, "check_connection", fail)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.get_json() == {"status": "error", "database": "unavailable"}
    # The real error belongs in the log only, never in the response body.
    assert "AccessDenied" not in response.get_data(as_text=True)
    assert "secret-table-name" not in response.get_data(as_text=True)
