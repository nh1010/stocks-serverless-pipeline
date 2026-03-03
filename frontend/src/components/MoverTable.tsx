import type { Mover } from "../types";

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function ChangeCell({ value }: { value: number }) {
  const isPositive = value >= 0;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-sm font-semibold ${
        isPositive
          ? "bg-green-100 text-green-700"
          : "bg-red-100 text-red-700"
      }`}
    >
      {isPositive ? "\u25B2" : "\u25BC"} {Math.abs(value).toFixed(2)}%
    </span>
  );
}

interface Props {
  movers: Mover[];
}

export function MoverTable({ movers }: Props) {
  if (movers.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        No data yet. The pipeline runs at 4:30 PM ET on weekdays.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 shadow-sm">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
              Date
            </th>
            <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
              Ticker
            </th>
            <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
              % Change
            </th>
            <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
              Close Price
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {movers.map((m) => (
            <tr key={m.date} className="hover:bg-gray-50 transition-colors">
              <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                {formatDate(m.date)}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm font-bold text-gray-900">
                {m.ticker}
              </td>
              <td className="whitespace-nowrap px-6 py-4">
                <ChangeCell value={m.percent_change} />
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-right text-sm text-gray-700">
                ${m.close_price.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
