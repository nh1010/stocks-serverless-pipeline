"""API Lambda — serves GET /movers via API Gateway.

Returns the last 7 days of top movers from DynamoDB, sorted by date descending.
"""

import json
import logging
import os
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ["TABLE_NAME"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


class _DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def handler(event, context):
    logger.info("API request: %s", json.dumps(event))

    try:
        response = table.scan(Limit=50)
        items = response.get("Items", [])

        items.sort(key=lambda x: x["date"], reverse=True)
        movers = items[:7]

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"movers": movers}, cls=_DecimalEncoder),
        }

    except ClientError as exc:
        logger.error("DynamoDB scan failed: %s", exc)
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": "Failed to fetch movers"}),
        }
