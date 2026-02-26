import React, { useState } from "react";
import {
  Briefcase,
  Activity,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Crosshair,
  Clock,
  Shield,
  XCircle,
  RefreshCw,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";
import ws from "../services/websocket";

export default function Trades() {
  const [activeTab, setActiveTab] = useState("OPEN");

  // Real API hooks
  const { data: portfolioData, loading, error, refetch } = useApi("portfolio", { pollIntervalMs: 5000 });
  const { data: perfData } = useApi("performanceTrades", { pollIntervalMs: 30000 });
  const { data: riskData } = useApi("risk", { pollIntervalMs: 10000 });

  const openPositions = portfolioData?.positions || [];
  const closedTrades = perfData?.trades || [];
  const totalRisk = riskData?.portfolioHeat || 0;

  const displayList = activeTab === "OPEN" ? openPositions : closedTrades;

  const calcPnl = (pos) => {
    if (pos.pnl != null) return pos.pnl;
    if (pos.currentPrice && pos.entryPrice) {
      const diff = pos.direction === "LONG"
        ? pos.currentPrice - pos.entryPrice
        : pos.entryPrice - pos.currentPrice;
      return diff * (pos.shares || pos.qty || 0);
    }
    return 0;
  };

  const calcPnlPct = (pos) => {
    if (pos.pnlPct != null) return pos.pnlPct;
    if (pos.entryPrice && pos.currentPrice) {
      return pos.direction === "LONG"
        ? ((pos.currentPrice - pos.entryPrice) / pos.entryPrice * 100)
        : ((pos.entryPrice - pos.currentPrice) / pos.entryPrice * 100);
    }
    return 0;
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <PageHeader
        icon={Briefcase}
        title="Trades"
        description="Open positions and closed trade history"
      >
        <div className="flex items-center gap-3">
          <div className="flex bg-slate-800/50 p-1 rounded-lg border border-slate-700/50">
            {["OPEN", "CLOSED"].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-1.5 text-xs font-bold rounded transition-colors ${
                  activeTab === tab
                    ? "bg-cyan-500/20 text-cyan-400"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {tab}
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

      {/* Portfolio Heat Bar */}
      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">Portfolio Heat</span>
          <span className={`text-sm font-bold ${totalRisk > 5 ? "text-red-400" : totalRisk > 3 ? "text-amber-400" : "text-emerald-400"}`}>
            {totalRisk.toFixed(1)}% at risk
          </span>
        </div>
        <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${totalRisk > 5 ? "bg-red-500" : totalRisk > 3 ? "bg-amber-500" : "bg-emerald-500"}`}
            style={{ width: `${Math.min(totalRisk * 5, 100)}%` }}
          />
        </div>
      </div>

      {/* Loading / Error */}
      {loading && openPositions.length === 0 && (
        <div className="text-center py-8 text-cyan-500 animate-pulse">Loading positions...</div>
      )}
      {error && (
        <div className="bg-red-500/15 border border-red-500/50 text-red-400 p-4 rounded-lg text-sm">
          API Error: {error.message}
        </div>
      )}

      {/* Trades Table */}
      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/80">
              <tr>
                {(activeTab === "OPEN"
                  ? ["Ticker", "Direction", "Entry", "Current", "Stop", "Target", "Shares", "P&L", "P&L %", "Status"]
                  : ["Ticker", "Direction", "Entry", "Exit", "Shares", "P&L", "P&L %", "Duration", "Date"]
                ).map((h) => (
                  <th key={h} className="px-4 py-3 text-slate-400 text-xs font-bold uppercase tracking-wider border-b border-slate-700/50">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {displayList.map((pos, i) => {
                const pnl = calcPnl(pos);
                const pnlPct = calcPnlPct(pos);
                const isPositive = pnl >= 0;
                return (
                  <tr key={pos.id || i} className="hover:bg-slate-700/30 transition-colors">
                    <td className="px-4 py-3 text-white font-bold">{pos.ticker || pos.symbol}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-bold ${pos.direction === "LONG" ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"}`}>
                        {pos.direction || pos.side}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-300">${pos.entryPrice?.toFixed(2) || pos.entry?.toFixed(2) || "—"}</td>
                    {activeTab === "OPEN" ? (
                      <>
                        <td className="px-4 py-3 text-white font-bold">${pos.currentPrice?.toFixed(2) || "—"}</td>
                        <td className="px-4 py-3 text-red-400">${pos.stopLoss?.toFixed(2) || pos.stop?.toFixed(2) || "—"}</td>
                        <td className="px-4 py-3 text-emerald-400">${pos.target1?.toFixed(2) || pos.target?.toFixed(2) || "—"}</td>
                      </>
                    ) : (
                      <td className="px-4 py-3 text-slate-300">${pos.exitPrice?.toFixed(2) || "—"}</td>
                    )}
                    <td className="px-4 py-3 text-slate-300">{pos.shares || pos.qty || "—"}</td>
                    <td className={`px-4 py-3 font-bold ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
                      {isPositive ? "+" : ""}{typeof pnl === "number" ? `$${pnl.toFixed(0)}` : "—"}
                    </td>
                    <td className={`px-4 py-3 font-bold ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
                      {isPositive ? "+" : ""}{typeof pnlPct === "number" ? `${pnlPct.toFixed(1)}%` : "—"}
                    </td>
                    {activeTab === "OPEN" ? (
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded text-[10px] font-bold ${
                          pos.status === "ACTIVE" ? "bg-emerald-500/20 text-emerald-400" :
                          pos.status === "TRAILING" ? "bg-cyan-500/20 text-cyan-400" :
                          "bg-slate-500/20 text-slate-400"
                        }`}>{pos.status || "ACTIVE"}</span>
                      </td>
                    ) : (
                      <>
                        <td className="px-4 py-3 text-slate-500 text-xs">{pos.duration || "—"}</td>
                        <td className="px-4 py-3 text-slate-500 text-xs">{pos.closedAt ? new Date(pos.closedAt).toLocaleDateString() : "—"}</td>
                      </>
                    )}
                  </tr>
                );
              })}
              {displayList.length === 0 && !loading && (
                <tr><td colSpan={10} className="px-4 py-8 text-center text-slate-500">
                  {activeTab === "OPEN" ? "No open positions." : "No closed trades yet."}
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
