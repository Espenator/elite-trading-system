import { useEffect, useRef, useState, useCallback } from "react";
import { createChart, ColorType } from "lightweight-charts";
import { getApiUrl } from "../../config/api";

/**
 * Reusable mini price chart for a symbol. Fetches quote data from GET /api/v1/quotes/{symbol}
 * and renders a line chart using TradingView Lightweight Charts. Dark/cyan theme.
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
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);

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
        .map((row) => {
          const close = parseFloat(row.Close ?? row.close ?? 0);
          const val = Number.isFinite(close) ? close : lastClose;
          if (Number.isFinite(val)) lastClose = val;
          const dateStr = row.Date ?? row.date ?? "";
          // LW Charts needs time as unix timestamp (seconds)
          const ts = dateStr ? Math.floor(new Date(dateStr).getTime() / 1000) : null;
          return { time: ts, value: Number.isFinite(val) ? val : null };
        })
        .filter((d) => d.value != null && d.time != null)
        .sort((a, b) => a.time - b.time);
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

  // Create/update LW chart when data changes
  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;
    // Dispose previous chart
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#64748b",
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: "#1e293b" },
      },
      width: chartContainerRef.current.clientWidth,
      height,
      rightPriceScale: {
        borderVisible: false,
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: { borderVisible: false, visible: false },
      crosshair: {
        vertLine: { labelVisible: false },
        horzLine: { labelVisible: true },
      },
      handleScroll: false,
      handleScale: false,
    });
    const series = chart.addAreaSeries({
      topColor: "rgba(34, 211, 238, 0.3)",
      bottomColor: "rgba(34, 211, 238, 0.02)",
      lineColor: "#22d3ee",
      lineWidth: 2,
    });
    series.setData(data);
    chart.timeScale().fitContent();
    chartRef.current = chart;

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [data, height]);

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
          Loading...
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
      <div
        ref={chartContainerRef}
        className="w-full"
        style={{ height, visibility: hasData && !loading ? "visible" : "hidden" }}
      />
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
