import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";

const MAX_DAILY_LOSS_COLOR = "#22d3ee"; // cyan-400
const VAR_COLOR = "#ec4899"; // pink-500

/**
 * Historical Risk Metrics: Max Daily Loss (%) and VaR ($) over time.
 * Expects data from API: { date, maxDailyLoss, var }[].
 * Shows empty state when data is missing or empty.
 */
export default function RiskHistoryChart({ data = [], className = "" }) {
  const hasData = Array.isArray(data) && data.length > 0;

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-800 border border-cyan-500/40 rounded-lg p-3 shadow-xl min-w-[140px]">
          <p className="text-xs text-slate-300 mb-2 font-medium">{label}</p>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <div
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: MAX_DAILY_LOSS_COLOR }}
              />
              <span className="text-sm text-slate-200">Max Daily Loss:</span>
              <span className="text-sm font-semibold text-cyan-300">
                {payload[0]?.value != null ? `${payload[0].value}%` : "—"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: VAR_COLOR }}
              />
              <span className="text-sm text-slate-200">VaR:</span>
              <span className="text-sm font-semibold text-pink-300">
                {payload[1]?.value != null
                  ? `$${Number(payload[1].value).toLocaleString()}`
                  : "—"}
              </span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  if (!hasData) {
    return (
      <div
        className={`flex flex-col items-center justify-center rounded-xl border border-cyan-500/10 bg-secondary/10 ${className}`}
        style={{ minHeight: 256 }}
      >
        <p className="text-sm text-secondary">No risk history data</p>
        <p className="text-xs text-secondary/80 mt-1">
          Max Daily Loss and VaR over time
        </p>
      </div>
    );
  }

  return (
    <div className={`overflow-hidden ${className}`}>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 5, right: 5, left: 5, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="date"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              tickMargin={8}
            />
            <YAxis
              yAxisId="left"
              orientation="left"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              tickFormatter={(v) => `${v}%`}
              domain={["auto", "auto"]}
              width={36}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              tickFormatter={(v) =>
                `$${v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v}`
              }
              domain={["auto", "auto"]}
              width={40}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ paddingTop: "8px" }}
              formatter={(value) => (
                <span className="text-secondary text-xs">{value}</span>
              )}
            />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="maxDailyLoss"
              name="Max Daily Loss (%)"
              stroke={MAX_DAILY_LOSS_COLOR}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: MAX_DAILY_LOSS_COLOR }}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="var"
              name="VaR ($)"
              stroke={VAR_COLOR}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: VAR_COLOR }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
