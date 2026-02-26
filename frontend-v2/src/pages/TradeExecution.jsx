import React, { useState, useCallback } from "react";
import {
  ShieldAlert,
  Target,
  CheckCircle2,
  XCircle,
  Lock,
  Activity,
  Send,
  RefreshCw,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";

export default function TradeExecution() {
  // Real API hooks
  const { data: signalData, loading: sigLoading } = useApi("signals", { pollIntervalMs: 5000 });
  const { data: portfolioData } = useApi("portfolio", { pollIntervalMs: 10000 });
  const { data: riskData } = useApi("risk", { pollIntervalMs: 10000 });
  const { data: settingsData } = useApi("settings", { pollIntervalMs: 60000 });

  const accountSize = portfolioData?.accountValue || settingsData?.accountSize || 0;
  const regimeRisk = riskData?.regimeRisk || 0.02;

  // Derive active signal from API (the top staged signal)
  const signals = Array.isArray(signalData) ? signalData : signalData?.signals || [];
  const stagedSignals = signals.filter((s) => s.status === "Staged" || s.tier === "SLAM DUNK");
  const [selectedIdx, setSelectedIdx] = useState(0);
  const activeSignal = stagedSignals[selectedIdx] || null;

  // Checklist state
  const [checklist, setChecklist] = useState({
    confirmEntry: false,
    confirmStop: false,
    confirmSize: false,
    confirmRegime: false,
    confirmRisk: false,
    confirmMental: false,
  });

  const allChecked = Object.values(checklist).every(Boolean);

  // Position sizing from API risk data
  const dollarRisk = accountSize * regimeRisk;
  const stopDist = activeSignal ? Math.abs((activeSignal.entry || 0) - (activeSignal.stop || 0)) : 0;
  const shares = stopDist > 0 ? Math.floor(dollarRisk / stopDist) : 0;
  const positionValue = shares * (activeSignal?.entry || 0);
  const pctOfAccount = accountSize > 0 ? ((positionValue / accountSize) * 100).toFixed(1) : 0;

  // Execute trade via API
  const [executing, setExecuting] = useState(false);
  const handleExecute = useCallback(async () => {
    if (!activeSignal || !allChecked) return;
    setExecuting(true);
    try {
      const url = getApiUrl("orders");
      await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: activeSignal.ticker || activeSignal.symbol,
          side: activeSignal.action || activeSignal.dir,
          qty: shares,
          type: "limit",
          limit_price: activeSignal.entry,
          stop_loss: activeSignal.stop,
          take_profit: activeSignal.target || activeSignal.target1,
        }),
      });
    } catch (err) {
      console.error("Order execution failed:", err);
    } finally {
      setExecuting(false);
    }
  }, [activeSignal, allChecked, shares]);

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <PageHeader
        icon={Send}
        title="Trade Execution"
        description="Bible v6.0 compliant order execution with risk governor"
      />

      {/* Loading */}
      {sigLoading && signals.length === 0 && (
        <div className="text-center py-8 text-cyan-500 animate-pulse">Loading staged signals...</div>
      )}

      {/* Signal Selector */}
      {stagedSignals.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-slate-500 mr-2">Staged signals:</span>
          {stagedSignals.map((s, i) => (
            <button
              key={s.id || i}
              onClick={() => setSelectedIdx(i)}
              className={`px-3 py-1.5 rounded text-xs font-bold border transition-colors ${
                selectedIdx === i
                  ? "bg-cyan-500/20 border-cyan-500/50 text-cyan-400"
                  : "bg-slate-800/40 border-slate-700/50 text-slate-400"
              }`}
            >
              {s.ticker || s.symbol} ({s.confidence || s.score}%)
            </button>
          ))}
        </div>
      )}

      {!activeSignal && !sigLoading && (
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-8 text-center text-slate-500">
          No staged signals available. Signals will appear when the agent swarm generates SLAM DUNK or Staged signals.
        </div>
      )}

      {activeSignal && (
        <div className="grid grid-cols-12 gap-6">
          {/* Signal Details */}
          <div className="col-span-5 bg-slate-800/40 border border-slate-700/50 rounded-lg p-6">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-cyan-400" />
              {activeSignal.ticker || activeSignal.symbol} — {activeSignal.action || activeSignal.dir}
            </h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-slate-400">Entry</span><span className="text-white font-bold">${activeSignal.entry?.toFixed(2) || "—"}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Stop Loss</span><span className="text-red-400 font-bold">${activeSignal.stop?.toFixed(2) || "—"}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Target 1</span><span className="text-emerald-400 font-bold">${(activeSignal.target || activeSignal.target1)?.toFixed(2) || "—"}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Confidence</span><span className="text-cyan-400 font-bold">{activeSignal.confidence || activeSignal.score}%</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Factors</span><span className="text-slate-300 text-xs">{Array.isArray(activeSignal.factors) ? activeSignal.factors.join(", ") : activeSignal.factors || "—"}</span></div>
            </div>
          </div>

          {/* Position Sizing */}
          <div className="col-span-4 bg-slate-800/40 border border-slate-700/50 rounded-lg p-6">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-purple-400" /> Position Sizing
            </h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-slate-400">Account Size</span><span className="text-white font-bold">${accountSize.toLocaleString()}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Risk Per Trade</span><span className="text-amber-400 font-bold">{(regimeRisk * 100).toFixed(1)}%</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Dollar Risk</span><span className="text-white font-bold">${dollarRisk.toLocaleString()}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Stop Distance</span><span className="text-red-400 font-bold">${stopDist.toFixed(2)}</span></div>
              <div className="flex justify-between border-t border-slate-700/50 pt-3"><span className="text-slate-400">Shares</span><span className="text-cyan-400 font-bold text-lg">{shares}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Position Value</span><span className="text-white font-bold">${positionValue.toLocaleString()}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">% of Account</span><span className="text-slate-300">{pctOfAccount}%</span></div>
            </div>
          </div>

          {/* Checklist + Execute */}
          <div className="col-span-3 bg-slate-800/40 border border-slate-700/50 rounded-lg p-6">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-amber-400" /> Pre-Flight
            </h2>
            <div className="space-y-2">
              {[
                { key: "confirmEntry", label: "Entry level verified" },
                { key: "confirmStop", label: "Stop placement valid" },
                { key: "confirmSize", label: "Position size within limits" },
                { key: "confirmRegime", label: "Regime alignment confirmed" },
                { key: "confirmRisk", label: "Portfolio heat acceptable" },
                { key: "confirmMental", label: "Mental state clear" },
              ].map((item) => (
                <label key={item.key} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={checklist[item.key]}
                    onChange={() => setChecklist((p) => ({ ...p, [item.key]: !p[item.key] }))}
                    className="accent-cyan-500"
                  />
                  <span className={`text-xs ${checklist[item.key] ? "text-emerald-400" : "text-slate-400"}`}>
                    {item.label}
                  </span>
                </label>
              ))}
            </div>
            <button
              onClick={handleExecute}
              disabled={!allChecked || executing}
              className={`w-full mt-4 py-3 rounded-lg text-sm font-bold transition-all ${
                allChecked
                  ? "bg-emerald-500 text-white hover:bg-emerald-400 shadow-lg shadow-emerald-500/30"
                  : "bg-slate-700 text-slate-500 cursor-not-allowed"
              }`}
            >
              {executing ? "Executing..." : allChecked ? "EXECUTE ORDER" : "Complete checklist"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
