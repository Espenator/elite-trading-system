// PERFORMANCE ANALYTICS - Embodier Trader
// Real API endpoints used:
// GET /api/v1/performance/summary - KPI metrics from DB trades
// GET /api/v1/performance/equity - equity curve from realized PnL
// GET /api/v1/performance/trades - recent trade list
// GET /api/v1/flywheel - ML accuracy metrics
// GET /api/v1/agents/consensus - agent voting

import { useState, useEffect, useRef } from "react";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
  Zap,
  Shield,
  Brain,
  BarChart3,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";

const CONSENSUS_COLORS = ["#10b981", "#f43f5e", "#64748b"];
const KPI_ICONS = [Activity, Target, Zap, TrendingUp, Shield, BarChart3, Brain];

// === Lightweight Charts Equity Curve ===
function EquityCurveLC({ data, height = 220 }) {
  const containerRef = useRef(null);
  useEffect(() => {
    let chart;
    const init = async () => {
      try {
        const mod = await import("lightweight-charts");
        const createChart = mod.createChart;
        if (!containerRef.current) return;
        chart = createChart(containerRef.current, {
          width: containerRef.current.clientWidth,
          height,
          layout: {
            background: { color: "transparent" },
            textColor: "#94a3b8",
          },
          grid: {
            vertLines: { color: "#1e293b" },
            horzLines: { color: "#1e293b" },
          },
          crosshair: { mode: 0 },
          timeScale: { borderColor: "#334155", timeVisible: true },
          rightPriceScale: { borderColor: "#334155" },
        });
        const series = chart.addAreaSeries({
          lineColor: "#10b981",
          topColor: "rgba(16,185,129,0.4)",
          bottomColor: "rgba(16,185,129,0.0)",
          lineWidth: 2,
        });
        if (Array.isArray(data) && data.length > 0) {
          const mapped = data
            .map((d) => ({
              time: d.date || d.time || d.t,
              value: d.equity || d.value || d.v,
            }))
            .filter((d) => d.time && d.value != null);
          if (mapped.length) series.setData(mapped);
        }
        const ro = new ResizeObserver(() => {
          if (containerRef.current)
            chart.applyOptions({ width: containerRef.current.clientWidth });
        });
        ro.observe(containerRef.current);
        return () => ro.disconnect();
      } catch (e) {
        console.warn("lightweight-charts not available:", e);
      }
    };
    init();
    return () => {
      if (chart) chart.remove();
    };
  }, [data, height]);
  return <div ref={containerRef} style={{ width: "100%", height }} />;
}

// === Drawdown Lightweight Chart ===
function DrawdownLC({ data, height = 60 }) {
  const containerRef = useRef(null);
  useEffect(() => {
    let chart;
    const init = async () => {
      try {
        const mod = await import("lightweight-charts");
        const createChart = mod.createChart;
        if (!containerRef.current) return;
        chart = createChart(containerRef.current, {
          width: containerRef.current.clientWidth,
          height,
          layout: {
            background: { color: "transparent" },
            textColor: "#94a3b8",
          },
          grid: {
            vertLines: { visible: false },
            horzLines: { color: "#1e293b" },
          },
          timeScale: { visible: false },
          rightPriceScale: { borderColor: "#334155" },
        });
        const series = chart.addAreaSeries({
          lineColor: "#f43f5e",
          topColor: "rgba(244,63,94,0.0)",
          bottomColor: "rgba(244,63,94,0.3)",
          lineWidth: 1,
        });
        if (Array.isArray(data) && data.length > 0) {
          // Build drawdown from equity points
          let peak = 0;
          const mapped = data
            .map((d) => {
              const eq = d.equity || d.value || 0;
              if (eq > peak) peak = eq;
              const dd = peak > 0 ? ((eq - peak) / peak) * 100 : 0;
              return { time: d.date || d.time, value: dd };
            })
            .filter((d) => d.time && d.value != null);
          if (mapped.length) series.setData(mapped);
        }
        const ro = new ResizeObserver(() => {
          if (containerRef.current)
            chart.applyOptions({ width: containerRef.current.clientWidth });
        });
        ro.observe(containerRef.current);
        return () => ro.disconnect();
      } catch (e) {
        console.warn("DrawdownLC not available:", e);
      }
    };
    init();
    return () => {
      if (chart) chart.remove();
    };
  }, [data, height]);
  return <div ref={containerRef} style={{ width: "100%", height }} />;
}

// === KPI Stat Card ===
function KpiCard({ label, value, sub, icon: Icon }) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3">
      <div className="flex items-center gap-1 mb-1">
        {Icon && <Icon className="w-3 h-3 text-emerald-500" />}
        <span className="text-[10px] text-slate-400 truncate">{label}</span>
      </div>
      <div className="text-lg font-bold text-white">{value ?? "\u2014"}</div>
      {sub && <div className="text-[9px] text-slate-500">{sub}</div>}
    </div>
  );
}

// === Main Component ===
export default function PerformanceAnalytics() {
  // Real API calls only - no fake endpoints
  const {
    data: summaryData,
    loading: summaryLoading,
    error: summaryError,
    refetch,
  } = useApi("performance", {
    endpoint: "/summary",
    pollIntervalMs: 60000,
  });
  const { data: equityData, loading: equityLoading } = useApi("performance", {
    endpoint: "/equity",
    pollIntervalMs: 60000,
  });
  const { data: tradesData } = useApi("performance", {
    endpoint: "/trades",
    pollIntervalMs: 60000,
  });
  const { data: flywheelData } = useApi("flywheel", {
    pollIntervalMs: 120000,
  });
  const { data: consensusData } = useApi("agents", {
    endpoint: "/consensus",
    pollIntervalMs: 30000,
  });

  // Extract real data - NO fallbacks to fake values
  const hasData = summaryData?.hasData === true;
  const metrics = summaryData?.metrics || {};
  const equityPoints = Array.isArray(equityData?.points)
    ? equityData.points
    : [];
  const trades = Array.isArray(tradesData?.trades) ? tradesData.trades : [];
  const consensus = Array.isArray(consensusData?.votes)
    ? consensusData.votes
    : [];
  const mlAccuracy = flywheelData?.accuracyPd ?? flywheelData?.accuracy ?? null;

  // Derive KPIs from real metrics only
  const kpis = [
    {
      label: "Total Trades",
      value: metrics.totalTrades ?? null,
      sub: hasData ? "Realized" : "No data",
    },
    {
      label: "Net P&L",
      value:
        metrics.netPnl != null
          ? `$${metrics.netPnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
          : null,
      sub:
        metrics.netPnl != null
          ? metrics.netPnl >= 0
            ? "Profit"
            : "Loss"
          : "No data",
    },
    {
      label: "Win Rate",
      value:
        metrics.winRate != null
          ? `${(metrics.winRate * 100).toFixed(1)}%`
          : null,
      sub: hasData ? "Of closed trades" : "No data",
    },
    {
      label: "Avg Win",
      value: metrics.avgWin != null ? `$${metrics.avgWin.toFixed(2)}` : null,
      sub: hasData ? "Per winning trade" : "No data",
    },
    {
      label: "Avg Loss",
      value: metrics.avgLoss != null ? `$${metrics.avgLoss.toFixed(2)}` : null,
      sub: hasData ? "Per losing trade" : "No data",
    },
    {
      label: "Profit Factor",
      value:
        metrics.profitFactor != null ? metrics.profitFactor.toFixed(2) : null,
      sub:
        metrics.profitFactor != null
          ? metrics.profitFactor >= 2
            ? "Excellent"
            : metrics.profitFactor >= 1.5
              ? "Good"
              : metrics.profitFactor >= 1
                ? "Marginal"
                : "Negative"
          : "No data",
    },
    {
      label: "Max Drawdown",
      value:
        metrics.maxDrawdown != null
          ? `$${metrics.maxDrawdown.toFixed(2)}`
          : null,
      sub: hasData ? "Peak to trough" : "No data",
    },
  ];

  // Build P&L distribution from real trades
  const tradeDist = (() => {
    if (!trades.length) return [];
    const pnls = trades.map((t) => t.pnl).filter((p) => p != null);
    if (!pnls.length) return [];
    const min = Math.min(...pnls);
    const max = Math.max(...pnls);
    const range = max - min || 1;
    const bucketCount = Math.min(15, Math.max(5, Math.ceil(pnls.length / 5)));
    const bucketSize = range / bucketCount;
    const buckets = Array.from({ length: bucketCount }, (_, i) => ({
      range: `${(min + i * bucketSize).toFixed(0)}`,
      count: 0,
      min: min + i * bucketSize,
      max: min + (i + 1) * bucketSize,
    }));
    pnls.forEach((p) => {
      const idx = Math.min(Math.floor((p - min) / bucketSize), bucketCount - 1);
      buckets[idx].count++;
    });
    return buckets;
  })();

  const isLoading = summaryLoading && !hasData;

  return (
    <div className="space-y-4">
      <PageHeader
        icon={TrendingUp}
        title="Performance Analytics"
        description="Real-time portfolio performance from trade data"
      >
        {summaryError && (
          <span className="text-red-400 text-xs">Failed to load</span>
        )}
        <Button
          onClick={refetch}
          variant="outline"
          size="sm"
          leftIcon={RefreshCw}
          className="text-xs"
        >
          Refresh
        </Button>
      </PageHeader>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <Activity className="w-8 h-8 text-cyan-400 animate-pulse mx-auto mb-2" />
            <p className="text-gray-400">Loading performance data...</p>
          </div>
        </div>
      )}

      {/* Error state */}
      {summaryError && !hasData && !isLoading && (
        <Card className="p-6 text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-gray-400 mb-4">
            Could not load performance data. Check backend API.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={refetch}
            leftIcon={RefreshCw}
          >
            Retry
          </Button>
        </Card>
      )}

      {/* No data state */}
      {!isLoading && !summaryError && !hasData && summaryData && (
        <Card className="p-8 text-center">
          <AlertCircle className="w-12 h-12 text-secondary mx-auto mb-4" />
          <p className="text-white text-lg font-medium mb-2">
            No Trade Data Yet
          </p>
          <p className="text-secondary text-sm">
            {summaryData?.message ||
              "No realized trades found in the database. Execute some trades to see performance metrics."}
          </p>
        </Card>
      )}

      {/* Data display - only when we have real data or at least a response */}
      {!isLoading && (hasData || summaryData) && (
        <>
          {/* === ROW 1: KPI Strip === */}
          <div className="grid grid-cols-7 gap-2">
            {kpis.map((k, i) => (
              <KpiCard
                key={i}
                label={k.label}
                value={k.value}
                sub={k.sub}
                icon={KPI_ICONS[i % KPI_ICONS.length]}
              />
            ))}
          </div>

          {/* === ROW 2: Equity Curve + Agent Consensus === */}
          <div className="grid grid-cols-6 gap-3">
            {/* Equity Curve */}
            <div className="col-span-4">
              <Card title="Equity Curve">
                {equityPoints.length > 0 ? (
                  <>
                    <EquityCurveLC data={equityPoints} height={220} />
                    <div className="mt-1">
                      <DrawdownLC data={equityPoints} height={60} />
                    </div>
                    {equityData?.note && (
                      <p className="text-[9px] text-slate-500 mt-1">
                        {equityData.note}
                      </p>
                    )}
                  </>
                ) : (
                  <div
                    className="flex items-center justify-center"
                    style={{ height: 280 }}
                  >
                    <p className="text-slate-500 text-sm">
                      No equity data available yet
                    </p>
                  </div>
                )}
              </Card>
            </div>

            {/* Agent Consensus */}
            <div className="col-span-2">
              <Card title="Agent Consensus">
                {consensus.length > 0 ? (
                  <>
                    <div className="relative" style={{ height: 200 }}>
                      <div
                        className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none"
                        style={{ zIndex: 10 }}
                      >
                        <span className="text-xl font-bold text-white">
                          {consensus[0]?.value || 0}%
                        </span>
                        <span className="text-[9px] text-emerald-500 font-bold uppercase tracking-widest">
                          {consensus[0]?.name || "Bull"} Bias
                        </span>
                      </div>
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={consensus}
                            innerRadius={45}
                            outerRadius={65}
                            paddingAngle={5}
                            dataKey="value"
                            stroke="none"
                          >
                            {consensus.map((_, i) => (
                              <Cell
                                key={i}
                                fill={
                                  CONSENSUS_COLORS[i % CONSENSUS_COLORS.length]
                                }
                              />
                            ))}
                          </Pie>
                          <Tooltip
                            contentStyle={{
                              background: "#0f172a",
                              border: "1px solid #334155",
                              borderRadius: 8,
                            }}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="flex justify-center gap-3 text-[9px]">
                      {consensus.map((c, i) => (
                        <span key={i} className="flex items-center gap-1">
                          <div
                            className="w-2 h-2 rounded-full"
                            style={{
                              background: CONSENSUS_COLORS[i],
                            }}
                          />
                          {c.name}
                        </span>
                      ))}
                    </div>
                  </>
                ) : (
                  <div
                    className="flex items-center justify-center"
                    style={{ height: 200 }}
                  >
                    <p className="text-slate-500 text-sm">No consensus data</p>
                  </div>
                )}

                {/* ML Accuracy from Flywheel */}
                {mlAccuracy != null && (
                  <div className="mt-4 pt-4 border-t border-slate-700/50">
                    <div className="text-[10px] text-slate-400 mb-2">
                      ML Model Accuracy
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="relative w-16 h-16">
                        <svg viewBox="0 0 120 120" className="w-full h-full">
                          <circle
                            cx="60"
                            cy="60"
                            r="50"
                            fill="none"
                            stroke="#1e293b"
                            strokeWidth="10"
                          />
                          <circle
                            cx="60"
                            cy="60"
                            r="50"
                            fill="none"
                            stroke="#10b981"
                            strokeWidth="10"
                            strokeDasharray={`${(mlAccuracy / 100) * 314} 314`}
                            strokeLinecap="round"
                            transform="rotate(-90 60 60)"
                          />
                        </svg>
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                          <span className="text-sm font-bold text-emerald-400">
                            {typeof mlAccuracy === "number"
                              ? `${mlAccuracy.toFixed(1)}%`
                              : "\u2014"}
                          </span>
                        </div>
                      </div>
                      <div className="text-[9px] text-slate-400">
                        From flywheel pipeline
                      </div>
                    </div>
                  </div>
                )}
              </Card>
            </div>
          </div>

          {/* === ROW 3: P&L Distribution + Recent Trades === */}
          <div className="grid grid-cols-6 gap-3">
            {/* P&L Distribution */}
            <div className="col-span-2">
              <Card title="Trade P&L Distribution">
                {tradeDist.length > 0 ? (
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={tradeDist}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis
                        dataKey="range"
                        tick={{ fontSize: 7, fill: "#64748b" }}
                      />
                      <YAxis tick={{ fontSize: 8, fill: "#64748b" }} />
                      <Tooltip
                        contentStyle={{
                          background: "#0f172a",
                          border: "1px solid #1e293b",
                          borderRadius: 8,
                          fontSize: 11,
                        }}
                      />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {tradeDist.map((d, i) => (
                          <Cell
                            key={i}
                            fill={
                              parseFloat(d.range) >= 0 ? "#10b981" : "#f43f5e"
                            }
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div
                    className="flex items-center justify-center"
                    style={{ height: 240 }}
                  >
                    <p className="text-slate-500 text-sm">
                      No trade data for distribution
                    </p>
                  </div>
                )}
              </Card>
            </div>

            {/* Recent Trades Table */}
            <div className="col-span-4">
              <Card title="Recent Trades">
                {trades.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-[10px]">
                      <thead>
                        <tr className="border-b border-slate-700">
                          <th className="text-left text-slate-400 p-2">
                            Symbol
                          </th>
                          <th className="text-left text-slate-400 p-2">Side</th>
                          <th className="text-right text-slate-400 p-2">Qty</th>
                          <th className="text-right text-slate-400 p-2">
                            Entry
                          </th>
                          <th className="text-right text-slate-400 p-2">
                            Exit
                          </th>
                          <th className="text-right text-slate-400 p-2">P&L</th>
                          <th className="text-right text-slate-400 p-2">
                            Date
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {trades.slice(0, 20).map((t, i) => (
                          <tr
                            key={i}
                            className="border-b border-slate-800 hover:bg-slate-800/50 transition-colors"
                          >
                            <td className="p-2 text-white font-medium">
                              {t.symbol || "\u2014"}
                            </td>
                            <td
                              className={`p-2 ${
                                t.side?.toLowerCase() === "buy"
                                  ? "text-emerald-400"
                                  : "text-red-400"
                              }`}
                            >
                              {t.side || "\u2014"}
                            </td>
                            <td className="p-2 text-right text-white">
                              {t.qty != null ? t.qty : "\u2014"}
                            </td>
                            <td className="p-2 text-right text-white">
                              {t.entry != null
                                ? `$${t.entry.toFixed(2)}`
                                : "\u2014"}
                            </td>
                            <td className="p-2 text-right text-white">
                              {t.exit != null
                                ? `$${t.exit.toFixed(2)}`
                                : "\u2014"}
                            </td>
                            <td
                              className={`p-2 text-right font-medium ${
                                t.pnl != null && t.pnl >= 0
                                  ? "text-emerald-400"
                                  : "text-red-400"
                              }`}
                            >
                              {t.pnl != null
                                ? `$${t.pnl.toFixed(2)}`
                                : "\u2014"}
                            </td>
                            <td className="p-2 text-right text-slate-400">
                              {t.closed_at
                                ? t.closed_at.slice(0, 10)
                                : "\u2014"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {trades.length > 20 && (
                      <p className="text-[9px] text-slate-500 mt-2 text-center">
                        Showing 20 of {trades.length} trades
                      </p>
                    )}
                  </div>
                ) : (
                  <div
                    className="flex items-center justify-center"
                    style={{ height: 240 }}
                  >
                    <p className="text-slate-500 text-sm">No recent trades</p>
                  </div>
                )}
              </Card>
            </div>
          </div>

          {/* Last updated */}
          {summaryData?.lastUpdated && (
            <p className="text-[9px] text-slate-600 text-right">
              Last trade: {summaryData.lastUpdated}
            </p>
          )}
        </>
      )}
    </div>
  );
}
