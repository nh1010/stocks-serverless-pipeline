import { Header } from "./components/Header";
import { MoverCard } from "./components/MoverCard";
import { MoverTable } from "./components/MoverTable";
import { useMovers } from "./hooks/useMovers";

export default function App() {
  const { data, isLoading, isError, error } = useMovers();

  const movers = data?.movers ?? [];
  const latest = movers[0];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-3xl px-4 pb-16">
        <Header />

        {isLoading && (
          <div className="flex justify-center py-20">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-indigo-600" />
          </div>
        )}

        {isError && (
          <div className="rounded-lg bg-red-50 p-4 text-center text-red-700">
            Failed to load data: {error.message}
          </div>
        )}

        {!isLoading && !isError && (
          <>
            {latest && (
              <div className="mb-8">
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-400">
                  Today&apos;s Top Mover
                </h2>
                <MoverCard mover={latest} isLatest />
              </div>
            )}

            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-400">
              Last 7 Days
            </h2>
            <MoverTable movers={movers} />
          </>
        )}
      </div>
    </div>
  );
}
