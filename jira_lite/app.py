"""The Flask application and its HTTP routes.

Gunicorn runs this module's ``app`` object (``jira_lite.app:app``). Routes stay
thin: they call ``jira_lite.db`` for anything that touches DynamoDB.
"""

import logging

from flask import Flask, jsonify

from jira_lite import db

app = Flask(__name__)
logger = logging.getLogger(__name__)


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
