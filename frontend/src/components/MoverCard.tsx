import type { Mover } from "../types";

interface Props {
  mover: Mover;
  isLatest?: boolean;
}

export function MoverCard({ mover, isLatest }: Props) {
  const isPositive = mover.percent_change >= 0;

  return (
    <div
      className={`rounded-xl border p-6 transition-shadow hover:shadow-md ${
        isLatest ? "border-2 border-indigo-400 shadow-md" : "border-gray-200"
      }`}
    >
      {isLatest && (
        <span className="mb-2 inline-block rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-semibold text-indigo-700">
          Latest
        </span>
      )}
      <div className="flex items-baseline justify-between">
        <h3 className="text-2xl font-bold text-gray-900">{mover.ticker}</h3>
        <span
          className={`text-xl font-semibold ${
            isPositive ? "text-green-600" : "text-red-600"
          }`}
        >
          {isPositive ? "+" : ""}
          {mover.percent_change.toFixed(2)}%
        </span>
      </div>
      <div className="mt-2 flex items-baseline justify-between text-sm text-gray-500">
        <span>{mover.date}</span>
        <span>Close: ${mover.close_price.toFixed(2)}</span>
      </div>
    </div>
  );
}
