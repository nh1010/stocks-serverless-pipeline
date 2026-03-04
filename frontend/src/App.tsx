import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine,
} from "recharts";
import { useMovers } from "./hooks/useMovers";
import type { Mover, Stock } from "./types";

const TICKER_COLORS: Record<string, string> = {
  AAPL: "#a8b5a2",
  MSFT: "#7eb8da",
  GOOGL: "#e8c170",
  AMZN: "#d4956a",
  TSLA: "#c47a7a",
  NVDA: "#8fd4a4",
};

const TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"];

function formatDate(dateStr: string) {
  const d = new Date(dateStr + "T12:00:00");
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function PctBadge({ value }: { value: number }) {
  const isPos = value >= 0;
  return (
    <span className={`pct-badge ${isPos ? "pos" : "neg"}`}>
      {isPos ? "+" : ""}{value.toFixed(2)}%
    </span>
  );
}

function TopMoverChart({ data }: { data: Mover[] }) {
  const chartData = data.map((m) => ({
    date: formatDate(m.date),
    ticker: m.ticker,
    percent_change: m.percent_change,
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
        <XAxis
          dataKey="date"
          tick={{ fill: "#64748b", fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
          axisLine={{ stroke: "#1e293b" }}
          tickLine={false}
        />
        <YAxis
          tickFormatter={(v: number) => `${v > 0 ? "+" : ""}${v.toFixed(1)}%`}
          tick={{ fill: "#64748b", fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
          axisLine={false}
          tickLine={false}
          width={52}
        />
        <ReferenceLine y={0} stroke="#1e293b" />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
        <Bar dataKey="percent_change" radius={[4, 4, 0, 0]} maxBarSize={48}>
          {chartData.map((entry, i) => (
            <Cell
              key={i}
              fill={TICKER_COLORS[entry.ticker] || "#888"}
              fillOpacity={0.85}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function ChartTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: { date: string; ticker: string; percent_change: number } }> }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <span className="chart-tooltip-date">{d.date}</span>
      <span className="chart-tooltip-ticker">{d.ticker}</span>
      <PctBadge value={d.percent_change} />
    </div>
  );
}

function Sparkline({ data, ticker }: { data: Mover[]; ticker: string }) {
  const count = data.filter((d) => d.ticker === ticker).length;
  const values = [...data].reverse().map((d) => {
    const stock = d.all_stocks.find((s) => s.ticker === ticker);
    return stock ? stock.percent_change : 0;
  });
  const max = Math.max(...values.map(Math.abs), 1);
  const w = 80;
  const h = 28;
  const points = values
    .map((v, i) => {
      const x = values.length > 1 ? (i / (values.length - 1)) * w : w / 2;
      const y = h / 2 - (v / max) * (h / 2 - 2);
      return `${x},${y}`;
    })
    .join(" ");

  const color = TICKER_COLORS[ticker] || "#888";

  return (
    <div className="sparkline-card">
      <span className="spark-dot" style={{ background: color }} />
      <span className="spark-ticker">{ticker}</span>
      <svg width={w} height={h} className="spark-svg">
        <polyline
          points={points}
          fill="none"
          stroke={color}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity={0.8}
        />
      </svg>
      <span
        className="spark-count has-tooltip"
        style={{ color: count > 0 ? color : "#475569" }}
        data-tooltip={count > 0 ? `Top mover ${count}× in last ${data.length} days` : `Not the top mover in the last ${data.length} days`}
      >
        {count > 0 ? `${count}×` : "—"}
      </span>
    </div>
  );
}

function DayRow({ day, isExpanded, onToggle }: { day: Mover; isExpanded: boolean; onToggle: () => void }) {
  const stocks = day.all_stocks.length > 0 ? day.all_stocks : [{ ticker: day.ticker, percent_change: day.percent_change, close_price: day.close_price }];
  const isPos = day.percent_change >= 0;

  return (
    <div className={`day-row ${isExpanded ? "expanded" : ""}`}>
      <button className="day-row-btn" onClick={onToggle}>
        <span className="day-date">{formatDate(day.date)}</span>
        <TickerPill ticker={day.ticker} />
        <PctBadge value={day.percent_change} />
        <span className="day-close">${day.close_price.toFixed(2)}</span>
        <span className={`day-chevron ${isExpanded ? "open" : ""}`}>▾</span>
      </button>

      {isExpanded && (
        <div className="day-detail">
          <div className="detail-header">
            <span>Ticker</span>
            <span style={{ textAlign: "right" }}>% Change</span>
            <span style={{ textAlign: "right" }}>Close</span>
          </div>
          {stocks.map((s: Stock) => (
            <div
              key={s.ticker}
              className={`detail-row ${s.ticker === day.ticker ? "highlight" : ""}`}
            >
              <span className="detail-ticker">
                <span className="spark-dot" style={{ background: TICKER_COLORS[s.ticker] || "#888", opacity: s.ticker === day.ticker ? 1 : 0.4 }} />
                {s.ticker}
                {s.ticker === day.ticker && (
                  <span className={`top-badge ${isPos ? "green" : "red"}`}>TOP</span>
                )}
              </span>
              <span style={{ textAlign: "right" }}><PctBadge value={s.percent_change} /></span>
              <span className="detail-close">${s.close_price.toFixed(2)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TickerPill({ ticker }: { ticker: string }) {
  return (
    <span className="ticker-pill">
      <span className="spark-dot" style={{ background: TICKER_COLORS[ticker] || "#888" }} />
      {ticker}
    </span>
  );
}

function LoadingSkeleton() {
  return (
    <div className="skeleton-wrapper" aria-busy="true">
      <div className="skel-stats">
        {[0, 1, 2].map((i) => <div key={i} className="skel-stat"><div className="skel-line skel-sm" /><div className="skel-line skel-lg" /></div>)}
      </div>
      <div className="skel-chart"><div className="skel-line skel-sm" /><div className="skel-bars">{[65, 40, 80, 55, 30, 70, 50].map((h, i) => <div key={i} className="skel-bar" style={{ height: `${h}%` }} />)}</div></div>
      {[0, 1, 2].map((i) => <div key={i} className="skel-row"><div className="skel-line skel-sm" style={{ width: 80 }} /><div className="skel-line skel-sm" style={{ width: 50 }} /><div className="skel-line skel-sm" style={{ width: 60 }} /></div>)}
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="error-state">
      <div className="error-icon">!</div>
      <h3>Something went wrong</h3>
      <p>{message}</p>
      <button className="retry-btn" onClick={onRetry}>Try again</button>
    </div>
  );
}

export default function App() {
  const { movers, loading, error, retry } = useMovers();
  const [expanded, setExpanded] = useState<number | null>(null);

  const greenDays = movers.filter((d) => d.percent_change >= 0).length;
  const avgMove = movers.length > 0
    ? movers.reduce((s, d) => s + Math.abs(d.percent_change), 0) / movers.length
    : 0;

  return (
    <div className="app-shell">
      <div className="app-container">
        {/* Header */}
        <header className="app-header">
          <div className="header-title-row">
            <h1>Stock Movers</h1>
            <span className="header-tag">THE WATCHLIST</span>
          </div>
          <p className="header-sub">Daily top mover by absolute % change · updated after market close</p>
        </header>

        {loading && <LoadingSkeleton />}
        {error && <ErrorState message={error} onRetry={retry} />}

        {!loading && !error && movers.length === 0 && (
          <p className="empty-msg">No mover data yet. Run the ingestion Lambda to populate.</p>
        )}

        {!loading && !error && movers.length > 0 && (
          <>
            {/* Stats Row */}
            <div className="stats-row">
              {[
                { label: "Period", value: `${movers.length} days` },
                { label: "Avg move", value: `${avgMove.toFixed(1)}%` },
                { label: "Green days", value: `${greenDays}/${movers.length}` },
              ].map((s) => (
                <div key={s.label} className="stat-card">
                  <div className="stat-label">{s.label}</div>
                  <div className="stat-value">{s.value}</div>
                </div>
              ))}
            </div>

            {/* Chart */}
            <div className="chart-section">
              <div className="section-label">Top mover · last {movers.length} days</div>
              <TopMoverChart data={[...movers].reverse()} />
            </div>

            {/* Sparklines */}
            <div className="sparklines-grid">
              {TICKERS.map((t) => (
                <Sparkline key={t} data={movers} ticker={t} />
              ))}
            </div>

            {/* Day rows */}
            <div className="section-label" style={{ marginBottom: 10, paddingLeft: 4 }}>Daily results</div>
            <div className="day-list">
              {movers.map((day, i) => (
                <DayRow
                  key={day.date}
                  day={day}
                  isExpanded={expanded === i}
                  onToggle={() => setExpanded(expanded === i ? null : i)}
                />
              ))}
            </div>
          </>
        )}

        {/* Footer */}
        <footer className="app-footer">
          <span>AAPL · MSFT · GOOGL · AMZN · TSLA · NVDA</span>
          <span>powered by Massive API</span>
        </footer>
      </div>
    </div>
  );
}
