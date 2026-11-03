"""All DynamoDB access for Jira Lite lives here.

Routes never touch boto3 directly. They call functions in this module, which
turn every AWS failure into one ``DatabaseError``. That keeps the routes small
and gives the tests one simple thing to replace.
"""

import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

TABLE_ENV_VAR = "JIRA_LITE_TABLE"
# Set only for DynamoDB Local on a laptop; unset on EC2.
ENDPOINT_ENV_VAR = "JIRA_LITE_DYNAMODB_ENDPOINT"
DEFAULT_TABLE_NAME = "jira-lite-tasks"

# Item id that /health looks up. It is not a UUID, so it never matches a real
# task, and a missing item is a normal empty result rather than an error.
HEALTH_CHECK_KEY = "__health_check__"

# boto3's defaults (60-second timeouts, retries) outlast a Gunicorn worker, so
# a database problem would surface as a generic Nginx error instead of a 503.
# Connect and read are separate limits, not one total deadline.
BOTO_CONFIG = Config(
    connect_timeout=2,
    read_timeout=2,
    retries={"total_max_attempts": 1},
)

# Created on first use so each Gunicorn worker builds its own. Do not run
# Gunicorn with ``--preload``: it would create this before the workers fork.
_table = None


class DatabaseError(Exception):
    """Raised when DynamoDB cannot be reached or refuses a request.

    The message is for the log only. Routes must never put it in a response.
    """


class TaskNotFound(Exception):
    """Raised when an edit targets a task that does not exist (any more)."""


def get_table():
    """Return this process's DynamoDB table handle, creating it on first use.

    Returns:
        The boto3 ``Table`` for the configured table name.

    Raises:
        botocore.exceptions.BotoCoreError: If boto3 cannot be configured, for
            example when no Region is set. Callers that need a
            ``DatabaseError`` should call this inside their own error handling.
    """
    global _table
    if _table is None:
        resource = boto3.resource(
            "dynamodb",
            endpoint_url=os.environ.get(ENDPOINT_ENV_VAR),
            config=BOTO_CONFIG,
        )
        _table = resource.Table(os.environ.get(TABLE_ENV_VAR, DEFAULT_TABLE_NAME))
    return _table


@contextmanager
def _translate_errors(action):
    """Turn any boto3 failure inside the block into a ``DatabaseError``.

    Args:
        action: Short description of the operation, used in the message.

    Raises:
        DatabaseError: On any ``BotoCoreError`` or ``ClientError``, such as a
            denied permission, a missing table, no Region, no credentials, or
            a timeout.
    """
    try:
        yield
    except (BotoCoreError, ClientError) as error:
        raise DatabaseError(f"DynamoDB {action} failed: {error}") from error


def check_connection():
    """Prove the app can read its DynamoDB table.

    Looks up a key that does not exist. This proves connectivity and read
    permission only; it deliberately does not write, so it never changes data.

    Raises:
        DatabaseError: If DynamoDB cannot be reached or refuses the read.
    """
    with _translate_errors("health check"):
        get_table().get_item(Key={"id": HEALTH_CHECK_KEY})


def create_task(fields):
    """Store a new task and return it.

    Args:
        fields: Validated ``title``, ``description`` and ``status`` values.

    Returns:
        The saved task: the fields plus a random ``id`` and a UTC
        ``created_at`` in a fixed format, so sorting the text sorts by time.

    Raises:
        DatabaseError: If DynamoDB cannot be reached or refuses the write.
    """
    task = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        **fields,
    }
    with _translate_errors("create task"):
        get_table().put_item(Item=task)
    return task


def update_task(task_id, fields):
    """Replace a task's title, description and status, and return the task.

    Args:
        task_id: The task's id.
        fields: Validated ``title``, ``description`` and ``status`` values.

    Returns:
        The task as stored after the update, including ``id`` and
        ``created_at``.

    Raises:
        TaskNotFound: If no task has this id. Without the condition below,
            DynamoDB would create a half-empty item with no ``created_at``,
            for example when someone edits a task another visitor just
            deleted, and that would break sorting for the whole board.
        DatabaseError: If DynamoDB cannot be reached or refuses the write.
    """
    with _translate_errors("update task"):
        try:
            response = get_table().update_item(
                Key={"id": task_id},
                # Every name goes through a placeholder: "status" is a DynamoDB
                # reserved word, and this keeps the others from depending on
                # that list.
                UpdateExpression=(
                    "SET #title = :title, #description = :description, "
                    "#status = :status"
                ),
                ExpressionAttributeNames={
                    "#title": "title",
                    "#description": "description",
                    "#status": "status",
                },
                ExpressionAttributeValues={
                    ":title": fields["title"],
                    ":description": fields["description"],
                    ":status": fields["status"],
                },
                ConditionExpression="attribute_exists(id)",
                ReturnValues="ALL_NEW",
            )
        except ClientError as error:
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise TaskNotFound(task_id) from error
            raise
    return response["Attributes"]


def delete_task(task_id):
    """Delete a task. Deleting one that is already gone is not an error.

    DynamoDB's delete does nothing for a missing item, which is the state the
    visitor asked for, so there is no not-found case to handle.

    Args:
        task_id: The task's id.

    Raises:
        DatabaseError: If DynamoDB cannot be reached or refuses the delete.
    """
    with _translate_errors("delete task"):
        get_table().delete_item(Key={"id": task_id})


def list_tasks():
    """Return every task, oldest first.

    A scan returns at most 1 MB per call, so this keeps reading until
    DynamoDB reports no more pages. Reads are consistent, so a task created a
    moment ago is included. DynamoDB promises no order, so the result is
    sorted here.

    Raises:
        DatabaseError: If DynamoDB cannot be reached or refuses the read.
    """
    tasks = []
    kwargs = {"ConsistentRead": True}
    with _translate_errors("list tasks"):
        while True:
            page = get_table().scan(**kwargs)
            tasks.extend(page["Items"])
            if "LastEvaluatedKey" not in page:
                break
            kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    return sorted(tasks, key=lambda task: task["created_at"])
