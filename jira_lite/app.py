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


@app.errorhandler(db.TaskNotFound)
def handle_task_not_found(error):
    """Return 404 when an edit targets a task that no longer exists."""
    return jsonify(error="Task not found. It may have been deleted."), 404


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


@app.put("/api/tasks/<uuid:task_id>")
def update_task(task_id):
    """Replace a task's title, description and status from the JSON body.

    The body is checked by the same rules as create, so an omitted status
    becomes "To Do" and an omitted description becomes empty. A malformed id
    never reaches this function: Flask's ``uuid`` converter returns 404.

    Returns:
        200 with the updated task, 400 if the body breaks a task rule, or 404
        if the task does not exist (both handled by the error handlers).
    """
    clean = validate_task(request.get_json(silent=True))
    return jsonify(db.update_task(str(task_id), clean))


@app.delete("/api/tasks/<uuid:task_id>")
def delete_task(task_id):
    """Delete a task.

    Returns:
        204 with no body, also when the task was already gone.
    """
    db.delete_task(str(task_id))
    return "", 204
