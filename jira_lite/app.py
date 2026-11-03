"""The Flask application and its HTTP routes.

Gunicorn runs this module's ``app`` object (``jira_lite.app:app``). Routes stay
thin: they call ``jira_lite.db`` for anything that touches DynamoDB.
"""

import logging

from flask import Flask, jsonify, request

from jira_lite import db
from jira_lite.validation import ValidationError, validate_task

app = Flask(__name__)
logger = logging.getLogger(__name__)


@app.errorhandler(ValidationError)
def handle_validation_error(error):
    """Return 400 with the rule that was broken, in words the page can show."""
    return jsonify(error=str(error)), 400


@app.errorhandler(db.DatabaseError)
def handle_database_error(error):
    """Return 503 with a generic message. The real error goes to the log only."""
    logger.error("Database request failed", exc_info=error)
    return jsonify(error="The database is unavailable. Try again later."), 503


@app.get("/health")
def health():
    """Report whether the app can reach its database.

    Returns:
        200 with ``{"status": "ok", "database": "ok"}`` when DynamoDB answers,
        or 503 with ``{"status": "error", "database": "unavailable"}`` when it
        does not. The real error goes to the log, never into the response.
    """
    try:
        db.check_connection()
    except db.DatabaseError:
        logger.exception("Health check failed")
        return jsonify(status="error", database="unavailable"), 503
    return jsonify(status="ok", database="ok")


@app.post("/api/tasks")
def create_task():
    """Create a task from the JSON body.

    Returns:
        201 with the saved task, or 400 if the body breaks a task rule
        (handled by ``handle_validation_error``).
    """
    return jsonify(db.create_task(validate_task(request.get_json(silent=True)))), 201


@app.get("/api/tasks")
def list_tasks():
    """Return every task as a JSON list, oldest first."""
    return jsonify(db.list_tasks())
