"""
API Lambda — serves GET /movers via API Gateway.

Supports ?days=N (default 7, max 30).
Returns 200 with data, 204 when no data exists, 500 on failure.
"""

import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DEFAULT_DAYS = 7
MAX_DAYS = 30

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}

CACHE_HEADERS = {
    "Cache-Control": "public, max-age=3600",
}


def build_response(status_code: int, body: dict | list | None = None) -> dict:
    headers = {**CORS_HEADERS, **CACHE_HEADERS}
    resp: dict = {"statusCode": status_code, "headers": headers}
    if body is not None:
        resp["body"] = json.dumps(body, default=str)
    return resp


def parse_days(event: dict) -> int:
    params = event.get("queryStringParameters") or {}
    raw = params.get("days", str(DEFAULT_DAYS))
    try:
        days = int(raw)
    except (ValueError, TypeError):
        return DEFAULT_DAYS
    return max(1, min(days, MAX_DAYS))


def handler(event, context):
    logger.info("Event: %s", json.dumps(event))

    days = parse_days(event)
    table_name = os.environ["TABLE_NAME"]
    dynamo = boto3.resource("dynamodb")
    table = dynamo.Table(table_name)

    try:
        response = table.scan(Limit=max(days * 2, 50))
        items = response.get("Items", [])
    except Exception:
        logger.exception("DynamoDB scan failed")
        return build_response(500, {"error": "Internal server error", "message": "Failed to retrieve movers from database"})

    items.sort(key=lambda x: x["date"], reverse=True)
    latest = items[:days]

    if not latest:
        return build_response(204)

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

    logger.info("Returning %d movers (days=%d)", len(movers), days)
    return build_response(200, movers)
