"""
Ingestion Lambda — runs daily via EventBridge.

Fetches the Massive Grouped Daily endpoint, finds the top mover
from the watchlist, and writes the result to DynamoDB.

Free-tier constraint: data is available one calendar day after close.
On 403, the handler schedules a retry via EventBridge Scheduler (max 8 attempts,
30 min apart).
"""

import json
import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
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
MAX_SCHEDULED_RETRIES = 8
RETRY_DELAY_MINUTES = 30


def get_api_key() -> str:
    ssm = boto3.client("ssm")
    param = ssm.get_parameter(
        Name=os.environ["SSM_API_KEY_NAME"], WithDecryption=True
    )
    return param["Parameter"]["Value"]


def get_trading_date() -> date:
    """Return the previous trading day (free tier is always one day behind)."""
    d = date.today() - timedelta(days=1)
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


def schedule_retry(context, trading_date: date, retry_count: int) -> None:
    """Create a one-time EventBridge Scheduler schedule to re-invoke this Lambda."""
    scheduler = boto3.client("scheduler")
    run_at = datetime.now(timezone.utc) + timedelta(minutes=RETRY_DELAY_MINUTES)
    schedule_name = f"ingestion-retry-{trading_date.isoformat()}"

    scheduler.create_schedule(
        Name=schedule_name,
        GroupName="default",
        FlexibleTimeWindow={"Mode": "OFF"},
        ScheduleExpression=f"at({run_at.strftime('%Y-%m-%dT%H:%M:%S')})",
        Target={
            "Arn": context.invoked_function_arn,
            "RoleArn": os.environ["SCHEDULER_ROLE_ARN"],
            "Input": json.dumps({
                "date": trading_date.isoformat(),
                "retry": retry_count + 1,
            }),
        },
        ActionAfterCompletion="DELETE",
    )
    logger.info(
        "Scheduled retry %d/%d for %s at %s",
        retry_count + 1, MAX_SCHEDULED_RETRIES,
        trading_date.isoformat(), run_at.isoformat(),
    )


def handler(event, context):
    logger.info("Event: %s", json.dumps(event))

    table_name = os.environ["TABLE_NAME"]
    retry_count = event.get("retry", 0)
    manual_date = event.get("date")

    if manual_date and retry_count == 0:
        trading_date = date.fromisoformat(manual_date)
    elif manual_date:
        trading_date = date.fromisoformat(manual_date)
    else:
        trading_date = get_trading_date()

    logger.info("Trading date: %s (retry %d/%d)", trading_date.isoformat(), retry_count, MAX_SCHEDULED_RETRIES)

    api_key = get_api_key()

    try:
        results = fetch_grouped_daily(api_key, trading_date)
    except HTTPError as exc:
        if exc.code == 403:
            if retry_count < MAX_SCHEDULED_RETRIES and "SCHEDULER_ROLE_ARN" in os.environ:
                schedule_retry(context, trading_date, retry_count)
                msg = f"Data not available for {trading_date} — retry {retry_count + 1}/{MAX_SCHEDULED_RETRIES} in {RETRY_DELAY_MINUTES} min"
                logger.info(msg)
                return {"statusCode": 200, "body": json.dumps({"message": msg})}

            logger.error("Data unavailable for %s after %d retries — giving up", trading_date, retry_count)
            raise

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
