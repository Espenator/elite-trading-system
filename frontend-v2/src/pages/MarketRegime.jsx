import React, { useState, useEffect, useRef } from "react";
import { createChart, ColorType } from "lightweight-charts";
import {
  ShieldAlert,
  TrendingUp,
  AlertTriangle,
  Activity,
  BarChart2,
  CheckCircle,
  AlertOctagon,
  RefreshCw,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";

// --- Lightweight Chart Component for VIX/RSI ---
const VixRegimeChart = ({ data }) => {
  const chartContainerRef = useRef();

  useEffect(() => {
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#94a3b8",
      },
      grid: {
        vertLines: { color: "#1e293b", style: 3 },
        horzLines: { color: "#1e293b", style: 3 },
      },
      rightPriceScale: { borderColor: "#334155" },
      timeScale: { borderColor: "#334155", timeVisible: true },
    });

    const vixSeries = chart.addLineSeries({
      color: "#ef4444",
      lineWidth: 2,
      title: "VIX",
    });

    if (data?.vix?.length) {
      vixSeries.setData(
        data.vix.map((d) => ({
          time: Math.floor(new Date(d.time).getTime() / 1000),
          value: d.value,
        }))
      );
    }

    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data]);

  return <div ref={chartContainerRef} className="w-full h-full" />;
};

// --- Main Component ---
export default function MarketRegime() {
  // Real API hooks
  const { data: regimeData, loading, error, refetch } = useApi("openclaw", { pollIntervalMs: 10000 });
  const { data: marketData } = useApi("market", { pollIntervalMs: 5000 });

  const regime = regimeData?.regime || {};
  const regimeState = regime.state || "UNKNOWN";
  const regimeConf = regime.conf || 0;

  const stateColor = (state) => {
    if (state?.includes("BULL")) return "emerald";
    if (state?.includes("BEAR")) return "red";
    return "amber";
  };

  const color = stateColor(regimeState);

  const metrics = [
    {
      title: "HMM Regime State",
      value: regimeState,
      icon: ShieldAlert,
      color: `text-${color}-400`,
      bg: `bg-${color}-500/15`,
      sub: `Confidence: ${regimeConf}%`,
    },
    {
      title: "VIX Level",
      value: marketData?.vix?.toFixed(1) || "—",
      icon: Activity,
      color: "text-amber-400",
      bg: "bg-amber-500/15",
      sub: marketData?.vix > 20 ? "Elevated" : "Normal",
    },
    {
      title: "Hurst Exponent",
      value: regime.hurst?.toFixed(2) || "—",
      icon: BarChart2,
      color: "text-cyan-400",
      bg: "bg-cyan-500/15",
      sub: regime.hurst > 0.5 ? "Trending" : "Mean-reverting",
    },
    {
      title: "HY Spread",
      value: regime.hySpread ? `${regime.hySpread}bps` : "—",
      icon: AlertTriangle,
      color: "text-purple-400",
      bg: "bg-purple-500/15",
      sub: regime.hySpread > 400 ? "Stress" : "Normal",
    },
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <PageHeader
        icon={ShieldAlert}
        title="Market Regime"
        description="Hidden Markov Model regime detection and macro context"
      >
        <button
          onClick={refetch}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-500/15 border border-cyan-500/50 rounded text-cyan-400 text-xs font-bold hover:bg-cyan-500/25 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </PageHeader>

      {/* Regime Banner */}
      <div className={`flex items-center justify-between px-6 py-4 bg-${color}-500/10 border border-${color}-500/30 rounded-lg`}>
        <div className="flex items-center gap-4">
          <span className={`w-3 h-3 rounded-full bg-${color}-500 shadow-[0_0_12px] shadow-${color}-500/50 animate-pulse`} />
          <span className={`text-lg font-bold text-${color}-400 tracking-wider`}>
            {regimeState} REGIME
          </span>
        </div>
        <div className="flex items-center gap-6">
          <div className="text-right">
            <div className="text-xs text-slate-500">HMM Confidence</div>
            <div className={`text-xl font-bold text-${color}-400`}>{regimeConf}%</div>
          </div>
        </div>
      </div>

      {/* Loading / Error */}
      {loading && !regimeData && (
        <div className="text-center py-8 text-cyan-500 animate-pulse">Loading regime data...</div>
      )}
      {error && (
        <div className="bg-red-500/15 border border-red-500/50 text-red-400 p-4 rounded-lg text-sm">
          API Error: {error.message}
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((m, i) => (
          <div key={i} className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4">
            <div className="flex justify-between items-start mb-2">
              <span className="text-slate-400 text-xs font-bold uppercase tracking-wider">{m.title}</span>
              <m.icon className={`w-4 h-4 ${m.color}`} />
            </div>
            <div className="flex items-end gap-2">
              <span className="text-2xl font-bold text-white">{m.value}</span>
            </div>
            <p className={`text-xs ${m.color} mt-1`}>{m.sub}</p>
          </div>
        ))}
      </div>

      {/* VIX Chart */}
      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg flex flex-col h-[400px]">
        <div className="px-4 py-3 border-b border-slate-700/50 bg-slate-900/40">
          <h3 className="text-white text-sm font-bold uppercase tracking-wider flex items-center gap-2">
            <Activity className="w-4 h-4 text-red-400" /> VIX Regime Chart
          </h3>
        </div>
        <div className="flex-1 p-2">
          <VixRegimeChart data={marketData} />
        </div>
      </div>

      {/* Regime Transitions Table */}
      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg">
        <div className="px-4 py-3 border-b border-slate-700/50 bg-slate-900/40">
          <h3 className="text-white text-sm font-bold uppercase tracking-wider">Regime Transition History</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/80">
              <tr>
                {["Timestamp", "From", "To", "Confidence", "Trigger"].map((h) => (
                  <th key={h} className="px-4 py-3 text-slate-400 text-xs font-bold uppercase tracking-wider border-b border-slate-700/50">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {(regime.transitions || []).map((t, i) => (
                <tr key={i} className="hover:bg-slate-700/30">
                  <td className="px-4 py-3 text-slate-500 text-xs">{t.timestamp ? new Date(t.timestamp).toLocaleString() : "—"}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs font-bold bg-${stateColor(t.from)}-500/15 text-${stateColor(t.from)}-400`}>{t.from}</span></td>
                  <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs font-bold bg-${stateColor(t.to)}-500/15 text-${stateColor(t.to)}-400`}>{t.to}</span></td>
                  <td className="px-4 py-3 text-white font-bold">{t.confidence}%</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{t.trigger || "—"}</td>
                </tr>
              ))}
              {(!regime.transitions || regime.transitions.length === 0) && (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-500">No transitions recorded yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
