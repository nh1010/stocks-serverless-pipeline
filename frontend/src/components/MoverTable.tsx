import { useState } from "react";
import type { Mover } from "../types";

interface Props {
  movers: Mover[];
}

export function MoverTable({ movers }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  if (movers.length === 0) {
    return <p className="empty">No mover data yet. Run the ingestion Lambda to populate.</p>;
  }

  function toggle(date: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(date) ? next.delete(date) : next.add(date);
      return next;
    });
  }

  return (
    <div className="days">
      {movers.map((day) => {
        const isOpen = expanded.has(day.date);
        const stocks = day.all_stocks.length > 0 ? day.all_stocks : [day];

        return (
          <div key={day.date} className={`day-card ${isOpen ? "expanded" : ""}`}>
            <button className="day-header" onClick={() => toggle(day.date)}>
              <div className="day-header-left">
                <h2>{day.date}</h2>
                <span className="day-winner">
                  <span className="ticker">{day.ticker}</span>
                  <span className={day.percent_change >= 0 ? "gain" : "loss"}>
                    {day.percent_change >= 0 ? "+" : ""}
                    {day.percent_change.toFixed(2)}%
                  </span>
                </span>
              </div>
              <span className={`chevron ${isOpen ? "open" : ""}`}>&#9662;</span>
            </button>

            {isOpen && (
              <table>
                <thead>
                  <tr>
                    <th>Ticker</th>
                    <th>% Change</th>
                    <th>Close</th>
                  </tr>
                </thead>
                <tbody>
                  {stocks.map((s) => (
                    <tr
                      key={s.ticker}
                      className={s.ticker === day.ticker ? "top-mover" : ""}
                    >
                      <td className="ticker">
                        {s.ticker}
                        {s.ticker === day.ticker && <span className="badge">TOP</span>}
                      </td>
                      <td className={s.percent_change >= 0 ? "gain" : "loss"}>
                        {s.percent_change >= 0 ? "+" : ""}
                        {s.percent_change.toFixed(2)}%
                      </td>
                      <td>${s.close_price.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        );
      })}
    </div>
  );
}
