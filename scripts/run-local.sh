#!/usr/bin/env bash
# Run Jira Lite locally against DynamoDB Local in Docker. Laptop only; never
# used on the server. Needs Docker and the .venv from requirements-dev.txt.
set -euo pipefail

# Work from the repository root no matter where the script is called from.
cd "$(dirname "$0")/.."

CONTAINER=jira-lite-dynamodb-local
LOCAL_DB_PORT=8001

# Start from a clean container each time so the script is safe to repeat.
# The "|| true" keeps set -e from stopping us when there is nothing to remove.
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker run -d --name "$CONTAINER" -p "127.0.0.1:${LOCAL_DB_PORT}:8000" \
  amazon/dynamodb-local >/dev/null

# Dummy credentials: DynamoDB Local requires some but never checks them, and
# real AWS rejects them.
export JIRA_LITE_DYNAMODB_ENDPOINT="http://localhost:${LOCAL_DB_PORT}"
export AWS_DEFAULT_REGION=us-east-2
export AWS_ACCESS_KEY_ID=local
export AWS_SECRET_ACCESS_KEY=local

.venv/bin/python scripts/create_local_table.py

# Same server settings as production: 2 workers, loopback only.
exec .venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 jira_lite.app:app
