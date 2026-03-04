import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import type { Mover } from "../types";

interface Props {
  movers: Mover[];
}

export function TopMoverChart({ movers }: Props) {
  const data = movers
    .slice(0, 7)
    .map((m) => ({
      date: formatDate(m.date),
      ticker: m.ticker,
      percent_change: m.percent_change,
    }))
    .reverse();

  if (data.length === 0) return null;

  return (
    <div className="chart-card">
      <h2>Top Mover — Last {data.length} Days</h2>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
          <XAxis
            dataKey="date"
            tick={{ fill: "#8b949e", fontSize: 11 }}
            axisLine={{ stroke: "#21262d" }}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(v: number) => `${v > 0 ? "+" : ""}${v.toFixed(1)}%`}
            tick={{ fill: "#8b949e", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={52}
          />
          <ReferenceLine y={0} stroke="#21262d" />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
          <Bar dataKey="percent_change" radius={[4, 4, 0, 0]} maxBarSize={40}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={entry.percent_change >= 0 ? "#3fb950" : "#f85149"}
                fillOpacity={0.85}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: { date: string; ticker: string; percent_change: number } }> }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <span className="chart-tooltip-date">{d.date}</span>
      <span className="chart-tooltip-ticker">{d.ticker}</span>
      <span className={d.percent_change >= 0 ? "gain" : "loss"}>
        {d.percent_change >= 0 ? "+" : ""}{d.percent_change.toFixed(2)}%
      </span>
    </div>
  );
}

function formatDate(iso: string) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
