"""The task rules from the SRS, checked before anything reaches the database."""

TITLE_MAX_LENGTH = 200
DESCRIPTION_MAX_LENGTH = 2000
STATUSES = ("To Do", "In Progress", "Done")
DEFAULT_STATUS = STATUSES[0]


class ValidationError(Exception):
    """Raised when a request body breaks a task rule.

    The message is written for the person using the board, so routes may put
    it in the response.
    """


def validate_task(data):
    """Check a request body and return the task fields it is allowed to set.

    Only ``title``, ``description`` and ``status`` are read. Other fields,
    such as ``id`` or ``created_at``, are ignored so a visitor cannot set them.

    Args:
        data: The parsed JSON body. ``None`` means the body was missing or was
            not valid JSON.

    Returns:
        A dict with a trimmed ``title``, a ``description`` (empty if omitted)
        and a ``status`` (``"To Do"`` if omitted).

    Raises:
        ValidationError: If the body is not a JSON object, the title is not
            text, blank, or over 200 characters, the description is not text
            or is over 2,000 characters, or the status is not one of the
            allowed values.
    """
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")

    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValidationError("Title is required.")
    title = title.strip()
    if len(title) > TITLE_MAX_LENGTH:
        raise ValidationError(f"Title must be {TITLE_MAX_LENGTH} characters or fewer.")

    description = data.get("description", "")
    if not isinstance(description, str):
        raise ValidationError("Description must be text.")
    if len(description) > DESCRIPTION_MAX_LENGTH:
        raise ValidationError(
            f"Description must be {DESCRIPTION_MAX_LENGTH} characters or fewer."
        )

    status = data.get("status", DEFAULT_STATUS)
    if status not in STATUSES:
        raise ValidationError(f"Status must be one of: {', '.join(STATUSES)}.")

    return {"title": title, "description": description, "status": status}
