"""Shared test setup: a Flask test client that makes no network calls."""

import pytest

from jira_lite.app import app


@pytest.fixture
def client():
    """Return an in-memory Flask test client (no network, no AWS)."""
    app.config["TESTING"] = True
    return app.test_client()
