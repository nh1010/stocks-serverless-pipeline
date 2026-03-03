"""Ingestion Lambda — triggered daily by EventBridge.

Fetches the Massive Grouped Daily endpoint, filters to the watchlist,
calculates percentage change for each ticker, and writes the top mover
to DynamoDB.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal

import boto3
import requests
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

WATCHLIST = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]
TABLE_NAME = os.environ["TABLE_NAME"]
SSM_PARAM_NAME = os.environ["SSM_PARAM_NAME"]
MASSIVE_BASE_URL = "https://api.massive.com"

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)
ssm = boto3.client("ssm")

_api_key: str | None = None


def _get_api_key() -> str:
    global _api_key
    if _api_key is None:
        resp = ssm.get_parameter(Name=SSM_PARAM_NAME, WithDecryption=True)
        _api_key = resp["Parameter"]["Value"]
    return _api_key


def _fetch_grouped_daily(date_str: str) -> list[dict]:
    """Fetch all US stock data for a given date from Massive grouped daily endpoint."""
    url = f"{MASSIVE_BASE_URL}/v2/aggs/grouped/locale/us/market/stocks/{date_str}"
    params = {"adjusted": "true", "apiKey": _get_api_key()}

    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data.get("resultsCount", 0) == 0:
                logger.warning("No results for %s (market holiday?)", date_str)
                return []

            return data.get("results", [])

        except requests.exceptions.RequestException as exc:
            logger.error("Attempt %d failed: %s", attempt + 1, exc)
            if attempt == 2:
                raise

    return []


def _find_top_mover(results: list[dict]) -> dict | None:
    """Filter to watchlist and return the stock with the highest absolute % change."""
    watchlist_data = [r for r in results if r.get("T") in WATCHLIST]

    if not watchlist_data:
        logger.warning("No watchlist tickers found in results")
        return None

    top = max(watchlist_data, key=lambda r: abs((r["c"] - r["o"]) / r["o"]))
    pct_change = ((top["c"] - top["o"]) / top["o"]) * 100

    return {
        "ticker": top["T"],
        "percent_change": round(pct_change, 4),
        "close_price": top["c"],
    }


def handler(event, context):
    logger.info("Ingestion triggered: %s", json.dumps(event))

    target_date = (datetime.utcnow() - timedelta(hours=5)).strftime("%Y-%m-%d")
    logger.info("Fetching data for %s", target_date)

    results = _fetch_grouped_daily(target_date)
    if not results:
        logger.info("No data for %s — skipping", target_date)
        return {"statusCode": 200, "body": "No data (likely market holiday)"}

    top_mover = _find_top_mover(results)
    if not top_mover:
        logger.info("No watchlist matches for %s — skipping", target_date)
        return {"statusCode": 200, "body": "No watchlist matches"}

    item = {
        "date": target_date,
        "ticker": top_mover["ticker"],
        "percent_change": Decimal(str(top_mover["percent_change"])),
        "close_price": Decimal(str(top_mover["close_price"])),
    }

    try:
        table.put_item(Item=item)
        logger.info("Stored top mover: %s", item)
    except ClientError as exc:
        logger.error("DynamoDB write failed: %s", exc)
        raise

    return {"statusCode": 200, "body": json.dumps({"date": target_date, **top_mover})}
