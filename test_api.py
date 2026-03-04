"""
Phase 1: Validate the Massive Grouped Daily endpoint.
Run: python3 test_api.py
"""

import os
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from datetime import date, timedelta

API_KEY = os.environ.get("MASSIVE_API_KEY", "wkscUwKrxikg99eGg_qwd2YccQwPktE_")
BASE_URL = "https://api.massive.com"
WATCHLIST = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]


def get_last_weekday(ref: date = None) -> date:
    d = ref or date.today()
    while d.weekday() >= 5:  # Saturday=5, Sunday=6
        d -= timedelta(days=1)
    return d


def fetch_grouped_daily(trading_date: date) -> dict:
    url = (
        f"{BASE_URL}/v2/aggs/grouped/locale/us/market/stocks/"
        f"{trading_date.isoformat()}?adjusted=true&apiKey={API_KEY}"
    )
    print(f"GET {url.replace(API_KEY, '***')}")
    req = Request(url)
    resp = urlopen(req, timeout=15)
    return json.loads(resp.read())


def main():
    trading_date = get_last_weekday()
    print(f"\nTrading date: {trading_date.isoformat()}")
    print(f"Watchlist:    {WATCHLIST}\n")

    try:
        data = fetch_grouped_daily(trading_date)
    except HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"HTTP {e.code}: {body}")
        if trading_date == date.today():
            prev = get_last_weekday(trading_date - timedelta(days=1))
            print(f"Retrying with previous trading day: {prev.isoformat()}")
            data = fetch_grouped_daily(prev)
            trading_date = prev
        else:
            raise

    results = data.get("results", [])
    print(f"Total tickers returned: {len(results)}")

    watchlist_data = [r for r in results if r.get("T") in WATCHLIST]
    print(f"Watchlist matches:      {len(watchlist_data)}\n")

    if not watchlist_data:
        print("No watchlist tickers found — check the date or API plan.")
        return

    print(f"{'Ticker':<8} {'Open':>10} {'Close':>10} {'% Change':>10}")
    print("-" * 42)

    movers = []
    for stock in watchlist_data:
        ticker = stock["T"]
        open_price = stock["o"]
        close_price = stock["c"]
        pct_change = ((close_price - open_price) / open_price) * 100
        movers.append((ticker, open_price, close_price, pct_change))
        print(f"{ticker:<8} {open_price:>10.2f} {close_price:>10.2f} {pct_change:>+10.2f}%")

    top = max(movers, key=lambda m: abs(m[3]))
    print(f"\n*** TOP MOVER: {top[0]}  {top[3]:+.2f}%  (close ${top[2]:.2f}) ***")

    print("\nDynamoDB record would be:")
    print(json.dumps({
        "date": trading_date.isoformat(),
        "ticker": top[0],
        "percent_change": round(top[3], 4),
        "close_price": round(top[2], 2),
    }, indent=2))


if __name__ == "__main__":
    main()
