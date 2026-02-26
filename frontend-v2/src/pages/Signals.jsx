import React, { useState, useEffect } from "react";
import {
  Zap,
  Activity,
  TrendingUp,
  TrendingDown,
  Target,
  Filter,
  Layers,
  BarChart2,
  ShieldAlert,
  Clock,
  RefreshCw,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";
import ws from "../services/websocket";

export default function Signals() {
  const [activeFilter, setActiveFilter] = useState("ALL");
  const [lastScan, setLastScan] = useState(new Date());

  // Real API hook - fetches from /api/v1/signals
  const { data: apiSignals, loading, error, refetch } = useApi("signals", { pollIntervalMs: 5000 });

  // WebSocket for real-time signal updates
  useEffect(() => {
    ws.connect();
    const unsub = ws.on("signals", (msg) => {
      if (msg?.type === "signals_updated") {
        refetch();
        setLastScan(new Date());
      }
    });
    return () => unsub();
  }, [refetch]);

  // Derive signals list from API response
  const signals = Array.isArray(apiSignals)
    ? apiSignals
    : apiSignals?.signals ?? [];

  const filtered =
    activeFilter === "ALL"
      ? signals
      : signals.filter((s) => s.action === activeFilter);

  const tierColor = (tier) => {
    if (tier === "SLAM DUNK") return "text-emerald-400 bg-emerald-500/15";
    if (tier === "STRONG GO") return "text-cyan-400 bg-cyan-500/15";
    if (tier === "WATCH") return "text-amber-400 bg-amber-500/15";
    return "text-slate-400 bg-slate-500/15";
  };

  const confColor = (c) => {
    if (c >= 85) return "text-emerald-400";
    if (c >= 60) return "text-cyan-400";
    return "text-amber-400";
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <PageHeader
        icon={Zap}
        title="Signals"
        description="Real-time trading signals from the OpenClaw agent swarm"
      >
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500">
            Last scan: {lastScan.toLocaleTimeString()}
          </span>
          <button
            onClick={refetch}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-500/15 border border-cyan-500/50 rounded text-cyan-400 text-xs font-bold hover:bg-cyan-500/25 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>
      </PageHeader>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 flex-wrap">
        {["ALL", "LONG", "SHORT"].map((f) => (
          <button
            key={f}
            onClick={() => setActiveFilter(f)}
            className={`px-4 py-2 rounded-lg text-xs font-bold border transition-colors ${
              activeFilter === f
                ? "bg-cyan-500/20 border-cyan-500/50 text-cyan-400"
                : "bg-slate-800/40 border-slate-700/50 text-slate-400 hover:text-slate-200"
            }`}
          >
            {f}
          </button>
        ))}
        <div className="ml-auto text-xs text-slate-500">
          {filtered.length} signal{filtered.length !== 1 ? "s" : ""}
        </div>
      </div>

      {/* Loading / Error States */}
      {loading && signals.length === 0 && (
        <div className="text-center py-12 text-cyan-500 animate-pulse">
          Loading signals...
        </div>
      )}
      {error && (
        <div className="bg-red-500/15 border border-red-500/50 text-red-400 p-4 rounded-lg text-sm">
          API Error: {error.message} — Retrying...
        </div>
      )}

      {/* Signals Table */}
      {!loading || signals.length > 0 ? (
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-900/80">
                <tr>
                  {["Ticker", "Action", "Type", "Confidence", "Tier", "Entry", "Target", "Stop", "R:R", "Factors", "Time"].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-4 py-3 text-slate-400 text-xs font-bold uppercase tracking-wider border-b border-slate-700/50"
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {filtered.map((sig, i) => (
                  <tr
                    key={sig.id || i}
                    className="hover:bg-slate-700/30 transition-colors"
                  >
                    <td className="px-4 py-3 text-white font-bold text-lg">
                      {sig.ticker || sig.symbol}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-1 rounded text-xs font-bold ${
                          sig.action === "LONG" || sig.dir === "LONG"
                            ? "bg-emerald-500/15 text-emerald-400"
                            : "bg-red-500/15 text-red-400"
                        }`}
                      >
                        {sig.action || sig.dir}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs">
                      {sig.type || "—"}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`font-bold ${confColor(sig.confidence || sig.score || 0)}`}>
                        {sig.confidence || sig.score || 0}%
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-1 rounded text-[10px] font-bold ${tierColor(sig.tier)}`}
                      >
                        {sig.tier || "—"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-300">
                      ${typeof sig.entry === "number" ? sig.entry.toFixed(2) : sig.entry || "—"}
                    </td>
                    <td className="px-4 py-3 text-emerald-400">
                      ${typeof sig.target === "number" ? sig.target.toFixed(2) : sig.target || sig.target1 || "—"}
                    </td>
                    <td className="px-4 py-3 text-red-400">
                      ${typeof sig.stop === "number" ? sig.stop.toFixed(2) : sig.stop || "—"}
                    </td>
                    <td className="px-4 py-3 text-cyan-400 font-bold">
                      {sig.rr || (sig.entry && sig.target && sig.stop
                        ? ((sig.target - sig.entry) / (sig.entry - sig.stop)).toFixed(1)
                        : "—")}
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs max-w-[200px] truncate">
                      {Array.isArray(sig.factors) ? sig.factors.join(", ") : sig.factors || "—"}
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs">
                      {sig.timestamp
                        ? new Date(sig.timestamp).toLocaleTimeString()
                        : sig.time || "—"}
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && !loading && (
                  <tr>
                    <td colSpan={11} className="px-4 py-8 text-center text-slate-500">
                      No signals available. Waiting for agent scan...
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </div>
  );
}
