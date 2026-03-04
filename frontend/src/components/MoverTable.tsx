import type { Mover } from "../types";

interface Props {
  movers: Mover[];
}

export function MoverTable({ movers }: Props) {
  if (movers.length === 0) {
    return <p className="empty">No mover data yet. Run the ingestion Lambda to populate.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Ticker</th>
          <th>% Change</th>
          <th>Close</th>
        </tr>
      </thead>
      <tbody>
        {movers.map((m) => (
          <tr key={m.date}>
            <td>{m.date}</td>
            <td className="ticker">{m.ticker}</td>
            <td className={m.percent_change >= 0 ? "gain" : "loss"}>
              {m.percent_change >= 0 ? "+" : ""}
              {m.percent_change.toFixed(2)}%
            </td>
            <td>${m.close_price.toFixed(2)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
