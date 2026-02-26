// frontend-v2/src/pages/RiskIntelligence.jsx
import React, { useState } from "react";
import {
  Shield,
  TrendingDown,
  Target,
  Activity,
  Zap,
  AlertTriangle,
  ArrowUpRight,
  RefreshCw,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";
import RiskEquityLC from "../components/charts/RiskEquityLC";
import MonteCarloLC from "../components/charts/MonteCarloLC";

const RiskIntelligence = () => {
  const [timeframe, setTimeframe] = useState("3M");

  // Real API hooks
  const { data: riskData, loading, error, refetch } = useApi("risk", { pollIntervalMs: 10000 });
  const { data: perfData } = useApi("performance", { pollIntervalMs: 30000 });
  const { data: portfolioData } = useApi("portfolio", { pollIntervalMs: 10000 });

  const risk = riskData || {};
  const perf = perfData || {};
  const portfolio = portfolioData || {};

  const metrics = [
    {
      title: "Current Drawdown",
      value: risk.drawdown != null ? `${risk.drawdown.toFixed(1)}%` : "—",
      icon: TrendingDown,
      color: "text-red-400",
    },
    {
      title: "Algo Win Rate",
      value: perf.winRate != null ? `${perf.winRate.toFixed(1)}%` : "—",
      icon: Target,
      color: "text-emerald-400",
      sub: perf.winRateDelta != null ? `${perf.winRateDelta > 0 ? "+" : ""}${perf.winRateDelta.toFixed(1)}%` : null,
    },
    {
      title: "Daily VaR (95%)",
      value: risk.var95 != null ? `$${risk.var95.toLocaleString()}` : "—",
      icon: AlertTriangle,
      color: "text-yellow-400",
      sub: risk.varPct != null ? `${risk.varPct.toFixed(1)}% Cap` : null,
    },
    {
      title: "Sharpe Ratio",
      value: perf.sharpe != null ? perf.sharpe.toFixed(2) : "—",
      icon: Activity,
      color: "text-cyan-400",
      sub: perf.sharpe >= 2 ? "Excellent" : perf.sharpe >= 1 ? "Good" : "Below avg",
    },
  ];

  const limits = risk.limits || [];

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <PageHeader
        icon={Shield}
        title="Risk Intelligence"
        description="System survivability and exposure monitoring"
      >
        <div className="flex items-center gap-3">
          <div className="flex bg-slate-800/50 p-1 rounded-lg border border-slate-700/50">
            {["1W", "1M", "3M", "YTD", "1Y"].map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-3 py-1.5 text-xs font-bold rounded transition-colors ${
                  timeframe === tf
                    ? "bg-red-500/20 text-red-400"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
          <button
            onClick={refetch}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-500/15 border border-cyan-500/50 rounded text-cyan-400 text-xs font-bold hover:bg-cyan-500/25 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>
      </PageHeader>

      {/* Loading / Error */}
      {loading && !riskData && (
        <div className="text-center py-8 text-cyan-500 animate-pulse">Loading risk data...</div>
      )}
      {error && (
        <div className="bg-red-500/15 border border-red-500/50 text-red-400 p-4 rounded-lg text-sm">
          API Error: {error.message}
        </div>
      )}

      {/* TOP METRICS GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((m, i) => (
          <div key={i} className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4">
            <div className="flex justify-between items-start mb-2">
              <span className="text-slate-400 text-xs font-bold uppercase tracking-wider">{m.title}</span>
              <m.icon className={`w-4 h-4 ${m.color}`} />
            </div>
            <div className="flex items-end gap-2">
              <span className="text-2xl font-bold text-white">{m.value}</span>
              {m.sub && <span className={`text-xs ${m.color} mb-1`}>{m.sub}</span>}
            </div>
          </div>
        ))}
      </div>

      {/* CHARTS SECTION */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg flex flex-col h-[400px]">
          <div className="px-4 py-3 border-b border-slate-700/50 bg-slate-900/40 flex justify-between items-center">
            <h3 className="text-white text-sm font-bold uppercase tracking-wider flex items-center gap-2">
              <Zap className="w-4 h-4 text-cyan-400" /> Equity Curve vs Benchmark
            </h3>
          </div>
          <div className="flex-1 p-2">
            <RiskEquityLC data={perf.equityCurve || []} />
          </div>
        </div>
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg flex flex-col h-[400px]">
          <div className="px-4 py-3 border-b border-slate-700/50 bg-slate-900/40 flex justify-between items-center">
            <h3 className="text-white text-sm font-bold uppercase tracking-wider flex items-center gap-2">
              <ArrowUpRight className="w-4 h-4 text-emerald-400" /> Monte Carlo Distribution (N=100)
            </h3>
          </div>
          <div className="flex-1 p-2">
            <MonteCarloLC data={perf.monteCarlo || []} />
          </div>
        </div>
      </div>

      {/* ACTIVE RISK LIMITS TABLE */}
      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg min-h-[250px]">
        <div className="px-4 py-3 border-b border-slate-700/50 bg-slate-900/40">
          <h3 className="text-white text-sm font-bold uppercase tracking-wider">Active Risk Limits & Guardrails</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/80">
              <tr>
                {["Parameter", "Current Value", "Hard Limit", "Status"].map((h) => (
                  <th key={h} className="px-4 py-3 text-slate-400 text-xs font-bold uppercase tracking-wider border-b border-slate-700/50">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {limits.map((lim, i) => (
                <tr key={i} className="hover:bg-slate-700/30">
                  <td className="px-4 py-3 text-slate-300">{lim.parameter}</td>
                  <td className={`px-4 py-3 font-bold ${lim.status === "WARNING" ? "text-yellow-400" : lim.status === "BREACH" ? "text-red-400" : "text-white"}`}>{lim.currentValue}</td>
                  <td className="px-4 py-3 text-slate-400">{lim.hardLimit}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-[10px] font-bold ${
                      lim.status === "NORMAL" ? "bg-emerald-500/20 text-emerald-400" :
                      lim.status === "WARNING" ? "bg-yellow-500/20 text-yellow-400" :
                      "bg-red-500/20 text-red-400"
                    }`}>{lim.status}</span>
                  </td>
                </tr>
              ))}
              {limits.length === 0 && (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-slate-500">No risk limits loaded. Waiting for API...</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default RiskIntelligence;
