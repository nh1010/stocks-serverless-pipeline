import type { Mover } from "../types";

interface Props {
  movers: Mover[];
}

export function MoverTable({ movers }: Props) {
  if (movers.length === 0) {
    return <p className="empty">No mover data yet. Run the ingestion Lambda to populate.</p>;
  }

  return (
    <div className="days">
      {movers.map((day) => (
        <div key={day.date} className="day-card">
          <h2>{day.date}</h2>
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>% Change</th>
                <th>Close</th>
              </tr>
            </thead>
            <tbody>
              {(day.all_stocks.length > 0 ? day.all_stocks : [day]).map((s) => (
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
        </div>
      ))}
    </div>
  );
}
