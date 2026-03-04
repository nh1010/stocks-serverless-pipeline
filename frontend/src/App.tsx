import { useMovers } from "./hooks/useMovers";
import { MoverTable } from "./components/MoverTable";
import { TopMoverChart } from "./components/TopMoverChart";
import { LoadingSkeleton } from "./components/LoadingSkeleton";
import { ErrorState } from "./components/ErrorState";

export default function App() {
  const { movers, loading, error, retry } = useMovers();

  return (
    <div className="app">
      <header>
        <h1>Stock Movers</h1>
      </header>

      <main>
        {loading && <LoadingSkeleton />}
        {error && <ErrorState message={error} onRetry={retry} />}
        {!loading && !error && (
          <>
            <TopMoverChart movers={movers} />
            <MoverTable movers={movers} />
          </>
        )}
      </main>

      <footer>
        AAPL &middot; MSFT &middot; GOOGL &middot; AMZN &middot; TSLA &middot; NVDA
      </footer>
    </div>
  );
}
