import { useMovers } from "./hooks/useMovers";
import { MoverTable } from "./components/MoverTable";

export default function App() {
  const { movers, loading, error } = useMovers();

  return (
    <div className="app">
      <header>
        <h1>Stock Movers</h1>
        <p>Daily top mover from the TRE watchlist</p>
      </header>

      <main>
        {loading && <p className="status">Loading...</p>}
        {error && <p className="status error">Error: {error}</p>}
        {!loading && !error && <MoverTable movers={movers} />}
      </main>

      <footer>
        AAPL &middot; MSFT &middot; GOOGL &middot; AMZN &middot; TSLA &middot; NVDA
      </footer>
    </div>
  );
}
