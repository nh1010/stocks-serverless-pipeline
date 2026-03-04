"""
Ingestion Lambda — runs daily via EventBridge.

Fetches the Massive Grouped Daily endpoint, finds the top mover
from the watchlist, and writes the result to DynamoDB.
"""

import json
import logging
import os
import time
from datetime import date, timedelta
from decimal import Decimal
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

WATCHLIST = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]
MASSIVE_BASE_URL = "https://api.massive.com"
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds


def get_api_key() -> str:
    ssm = boto3.client("ssm")
    param = ssm.get_parameter(
        Name=os.environ["SSM_API_KEY_NAME"], WithDecryption=True
    )
    return param["Parameter"]["Value"]


def get_trading_date() -> date:
    """Return the most recent weekday (today if weekday, else Friday)."""
    d = date.today()
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def fetch_grouped_daily(api_key: str, trading_date: date) -> list[dict]:
    """
    Call the Massive Grouped Daily endpoint with retry logic for
    rate limits (429) and transient server errors (5xx).
    """
    url = (
        f"{MASSIVE_BASE_URL}/v2/aggs/grouped/locale/us/market/stocks/"
        f"{trading_date.isoformat()}?adjusted=true&apiKey={api_key}"
    )
    safe_url = url.replace(api_key, "***")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("Attempt %d: GET %s", attempt, safe_url)
            req = Request(url)
            resp = urlopen(req, timeout=15)
            data = json.loads(resp.read())
            results = data.get("results", [])
            logger.info("Received %d tickers", len(results))
            return results
        except HTTPError as exc:
            body = exc.read().decode() if exc.fp else ""
            logger.warning("HTTP %d on attempt %d: %s", exc.code, attempt, body)

            if exc.code == 429 and attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF * attempt
                logger.info("Rate limited — retrying in %ds", wait)
                time.sleep(wait)
                continue
            if 500 <= exc.code < 600 and attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF * attempt
                logger.info("Server error — retrying in %ds", wait)
                time.sleep(wait)
                continue
            raise

    return []


def calculate_movers(results: list[dict]) -> list[dict]:
    watchlist_stocks = [r for r in results if r.get("T") in WATCHLIST]
    if not watchlist_stocks:
        logger.warning("No watchlist tickers found in API response")
        return []

    movers = []
    for stock in watchlist_stocks:
        ticker = stock["T"]
        open_price = stock["o"]
        close_price = stock["c"]
        if open_price == 0:
            logger.warning("Skipping %s — open price is 0", ticker)
            continue
        pct_change = ((close_price - open_price) / open_price) * 100
        movers.append({
            "ticker": ticker,
            "open_price": open_price,
            "close_price": close_price,
            "percent_change": pct_change,
        })
        logger.info("%s  open=%.2f  close=%.2f  change=%+.2f%%",
                     ticker, open_price, close_price, pct_change)

    movers.sort(key=lambda m: abs(m["percent_change"]), reverse=True)
    return movers


def write_to_dynamo(table_name: str, trading_date: date, movers: list[dict]) -> None:
    dynamo = boto3.resource("dynamodb")
    table = dynamo.Table(table_name)
    top = movers[0]
    item = {
        "date": trading_date.isoformat(),
        "ticker": top["ticker"],
        "percent_change": Decimal(str(round(top["percent_change"], 4))),
        "close_price": Decimal(str(round(top["close_price"], 2))),
        "all_stocks": [
            {
                "ticker": m["ticker"],
                "percent_change": Decimal(str(round(m["percent_change"], 4))),
                "close_price": Decimal(str(round(m["close_price"], 2))),
            }
            for m in movers
        ],
    }
    table.put_item(Item=item)
    logger.info("Wrote to DynamoDB: %s", json.dumps(item, default=str))


def handler(event, context):
    logger.info("Event: %s", json.dumps(event))

    table_name = os.environ["TABLE_NAME"]

    if event.get("date"):
        trading_date = date.fromisoformat(event["date"])
    else:
        trading_date = get_trading_date()

    logger.info("Trading date: %s", trading_date.isoformat())

    api_key = get_api_key()

    try:
        results = fetch_grouped_daily(api_key, trading_date)
    except HTTPError as exc:
        if exc.code == 403 and trading_date == date.today():
            prev = trading_date - timedelta(days=1)
            while prev.weekday() >= 5:
                prev -= timedelta(days=1)
            logger.info("Today's data not ready — falling back to %s", prev)
            results = fetch_grouped_daily(api_key, prev)
            trading_date = prev
        else:
            logger.error("Massive API failed: HTTP %d", exc.code)
            raise

    movers = calculate_movers(results)
    if not movers:
        msg = f"No mover data available for {trading_date.isoformat()}"
        logger.error(msg)
        return {"statusCode": 200, "body": json.dumps({"message": msg})}

    write_to_dynamo(table_name, trading_date, movers)

    top = movers[0]
    return {
        "statusCode": 200,
        "body": json.dumps({
            "date": trading_date.isoformat(),
            "top_mover": top["ticker"],
            "percent_change": round(top["percent_change"], 4),
            "close_price": round(top["close_price"], 2),
        }),
    }
