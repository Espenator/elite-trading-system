import { useEffect, useRef, useState, useCallback } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { getApiUrl } from "../../config/api";

/**
 * Reusable mini price chart for a symbol. Fetches quote data from GET /api/v1/quotes/{symbol}
 * and renders a simple line chart (recharts). Dark/cyan theme.
 *
 * @param {string|null} symbol - Ticker symbol (e.g. "AAPL")
 * @param {string} [className] - Wrapper class
 * @param {number} [height=128] - Chart height in px
 * @param {string} [timeframe] - p param: d, w, m (default d)
 * @param {string} [range] - r param: m1, m3, y1 (default m1)
 */
export default function MiniChart({
  symbol,
  className = "",
  height = 128,
  timeframe = "d",
  range = "m1",
}) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);

  const fetchData = useCallback(async () => {
    if (!symbol?.trim()) {
      setData([]);
      return;
    }
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();
    setError(null);
    setLoading(true);
    try {
      const url = `${getApiUrl("quotes")}/${encodeURIComponent(symbol.trim())}?p=${timeframe}&r=${range}`;
      const res = await fetch(url, { signal: abortRef.current.signal });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const raw = await res.json();
      if (!Array.isArray(raw) || raw.length === 0) {
        setData([]);
        setLoading(false);
        return;
      }
      let lastClose = null;
      const chartData = raw
        .map((row, i) => {
          const close = parseFloat(row.Close ?? row.close ?? 0);
          const open = parseFloat(row.Open ?? row.open ?? 0);
          const val = Number.isFinite(close) ? close : lastClose;
          if (Number.isFinite(val)) lastClose = val;
          const dateStr = row.Date ?? row.date ?? "";
          return {
            name: dateStr || `#${i + 1}`,
            value: Number.isFinite(val) ? val : null,
          };
        })
        .filter((d) => d.value != null);
      setData(chartData);
    } catch (e) {
      if (e.name === "AbortError") return;
      setError(e.message || "Failed to load chart");
      setData([]);
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }, [symbol, timeframe, range]);

  useEffect(() => {
    fetchData();
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, [fetchData]);

  if (!symbol?.trim()) {
    return (
      <div
        className={`flex items-center justify-center text-secondary text-sm ${className}`}
        style={{ minHeight: height }}
      >
        Select a stock
      </div>
    );
  }

  const hasData = data.length > 0;
  const strokeColor = "#22d3ee"; // cyan-400

  return (
    <div
      className={`relative ${className}`}
      style={{ minHeight: height, width: "100%" }}
    >
      {loading && (
        <div
          className="absolute inset-0 flex items-center justify-center rounded-xl bg-dark z-10 text-cyan-400 text-xs"
          style={{ minHeight: height }}
        >
          Loading…
        </div>
      )}
      {error && !loading && (
        <div
          className="absolute inset-0 flex items-center justify-center rounded-xl bg-dark z-10 text-red-400 text-xs"
          style={{ minHeight: height }}
        >
          {error}
        </div>
      )}
      {!loading && hasData && (
        <ResponsiveContainer width="100%" height={height}>
          <LineChart
            data={data}
            margin={{ top: 4, right: 4, left: 4, bottom: 4 }}
          >
            <XAxis
              dataKey="name"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#64748b", fontSize: 10 }}
              tickFormatter={(v) => (v.startsWith("#") ? v : v.slice(0, 6))}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#64748b", fontSize: 10 }}
              tickFormatter={(v) =>
                v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v
              }
              domain={["auto", "auto"]}
              width={36}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(15, 23, 42, 0.95)",
                border: "1px solid rgba(34, 211, 238, 0.3)",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              labelStyle={{ color: "#94a3b8" }}
              formatter={(value) => [`$${Number(value).toFixed(2)}`, "Price"]}
              labelFormatter={(label) =>
                label.startsWith("#") ? label : label
              }
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={strokeColor}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 3, fill: strokeColor }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
      {!loading && !error && !hasData && (
        <div
          className="flex items-center justify-center text-secondary text-xs"
          style={{ minHeight: height }}
        >
          No chart data
        </div>
      )}
    </div>
  );
}
