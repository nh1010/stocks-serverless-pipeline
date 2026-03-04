"""
API Lambda — serves GET /movers via API Gateway.

Returns the last 7 days of top movers from DynamoDB,
sorted by date descending.
"""

import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


def build_response(status_code: int, body: dict | list) -> dict:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, default=str),
    }


def handler(event, context):
    logger.info("Event: %s", json.dumps(event))

    table_name = os.environ["TABLE_NAME"]
    dynamo = boto3.resource("dynamodb")
    table = dynamo.Table(table_name)

    try:
        response = table.scan(Limit=50)
        items = response.get("Items", [])
    except Exception:
        logger.exception("DynamoDB scan failed")
        return build_response(500, {"error": "Failed to retrieve movers"})

    items.sort(key=lambda x: x["date"], reverse=True)
    latest = items[:7]

    movers = []
    for item in latest:
        entry = {
            "date": item["date"],
            "ticker": item["ticker"],
            "percent_change": float(item["percent_change"]),
            "close_price": float(item["close_price"]),
            "all_stocks": [
                {
                    "ticker": s["ticker"],
                    "percent_change": float(s["percent_change"]),
                    "close_price": float(s["close_price"]),
                }
                for s in item.get("all_stocks", [])
            ],
        }
        movers.append(entry)

    logger.info("Returning %d movers", len(movers))
    return build_response(200, movers)
