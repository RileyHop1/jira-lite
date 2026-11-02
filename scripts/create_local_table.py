"""Create the Jira Lite table in DynamoDB Local, for laptop testing only.

Refuses to run unless the endpoint is on this machine, so it can never create
or touch a table in real AWS. Safe to run repeatedly: an existing table is
left alone.

Usage:
    export JIRA_LITE_DYNAMODB_ENDPOINT=http://localhost:8001
    python scripts/create_local_table.py

Raises:
    SystemExit: If the endpoint is missing or is not localhost.
"""

import os
import sys
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

# The only endpoints this script will use, so it can never reach real AWS.
LOCAL_HOSTS = {"localhost", "127.0.0.1"}
TABLE_NAME = os.environ.get("JIRA_LITE_TABLE", "jira-lite-tasks")


def main():
    """Create the table with the same key schema as the real one.

    Raises:
        SystemExit: If the endpoint is unset or not a local address.
    """
    endpoint = os.environ.get("JIRA_LITE_DYNAMODB_ENDPOINT", "")
    if urlparse(endpoint).hostname not in LOCAL_HOSTS:
        sys.exit(
            "Refusing to run: JIRA_LITE_DYNAMODB_ENDPOINT must point at "
            f"localhost, got {endpoint!r}."
        )

    client = boto3.client("dynamodb", endpoint_url=endpoint)
    try:
        client.create_table(
            TableName=TABLE_NAME,
            # Same key as the real table: a string partition key named "id".
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
        print(f"Created local table {TABLE_NAME}")
    except ClientError as error:
        if error.response["Error"]["Code"] != "ResourceInUseException":
            raise
        print(f"Local table {TABLE_NAME} already exists")


if __name__ == "__main__":
    main()
