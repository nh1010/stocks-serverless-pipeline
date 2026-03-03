export function Header() {
  return (
    <header className="text-center py-10">
      <h1 className="text-4xl font-bold tracking-tight text-gray-900">
        Top Mover Dashboard
      </h1>
      <p className="mt-2 text-lg text-gray-500">
        The single stock from our watchlist that moved the most each day
      </p>
      <div className="mt-4 flex justify-center gap-2">
        {["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"].map((ticker) => (
          <span
            key={ticker}
            className="inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-gray-700"
          >
            {ticker}
          </span>
        ))}
      </div>
    </header>
  );
}
