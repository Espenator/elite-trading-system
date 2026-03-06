// frontend-v2/src/pages/MarketRegime.jsx
// Market Regime — AI Brain's Macro Intelligence Center (Page 10/15)
// Route: /market-regime

import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  useMemo,
} from "react";
import { createChart } from "lightweight-charts";
import { useApi } from "../hooks/useApi";
import { getApiUrl, getAuthHeaders } from "../config/api";
import { postBiasOverride } from "../hooks/useApi";
import log from "@/utils/logger";

// ============================================================
// CONSTANTS
// ============================================================
const REGIME_COLORS = {
  GREEN: {
    bg: "bg-emerald-500",
    text: "text-emerald-400",
    hex: "#10B981",
    bgFaint: "bg-emerald-500/10",
    border: "border-emerald-500/30",
  },
  YELLOW: {
    bg: "bg-amber-500",
    text: "text-amber-400",
    hex: "#F59E0B",
    bgFaint: "bg-amber-500/10",
    border: "border-amber-500/30",
  },
  RED: {
    bg: "bg-red-500",
    text: "text-red-400",
    hex: "#EF4444",
    bgFaint: "bg-red-500/10",
    border: "border-red-500/30",
  },
  RED_RECOVERY: {
    bg: "bg-orange-500",
    text: "text-orange-400",
    hex: "#F97316",
    bgFaint: "bg-orange-500/10",
    border: "border-orange-500/30",
  },
};

const REGIME_PARAMS_DEFAULT = {
  GREEN: {
    risk_pct: 2.0,
    max_positions: 6,
    kelly_mult: 1.5,
    signal_mult: 1.1,
    label: "Momentum",
  },
  YELLOW: {
    risk_pct: 1.5,
    max_positions: 5,
    kelly_mult: 1.0,
    signal_mult: 1.0,
    label: "Cautious",
  },
  RED: {
    risk_pct: 0.0,
    max_positions: 0,
    kelly_mult: 0.25,
    signal_mult: 0.85,
    label: "Defensive",
  },
  RED_RECOVERY: {
    risk_pct: 1.0,
    max_positions: 4,
    kelly_mult: 0.75,
    signal_mult: 0.95,
    label: "Re-entry",
  },
};

const TIMEFRAMES = ["1D", "1W", "1M", "3M", "1Y"];

// ============================================================
// SUB-COMPONENTS
// ============================================================

// --- KPI Card ---
function KpiCard({ label, value, unit, color, alert }) {
  return (
    <div
      className={`bg-[#111827] rounded px-2 py-1.5 border ${alert ? "border-red-500/50 animate-pulse" : "border-gray-700/30"}`}
    >
      <div className="text-[9px] text-gray-500 uppercase tracking-wider truncate">
        {label}
      </div>
      <div
        className={`text-sm font-mono font-bold ${color || "text-cyan-400"} leading-tight`}
      >
        {value ?? "\u2014"}
        {unit && <span className="text-[9px] text-gray-500 ml-0.5">{unit}</span>}
      </div>
    </div>
  );
}

// --- Regime Badge ---
function RegimeBadge({ state, confidence, size = "lg" }) {
  const rc = REGIME_COLORS[state] || REGIME_COLORS.YELLOW;
  const sizeClasses =
    size === "lg" ? "px-3 py-1 text-sm" : "px-2 py-0.5 text-xs";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded font-black tracking-wider ${rc.bg} text-white ${sizeClasses}`}
    >
      {state}
      {confidence != null && (
        <span className="text-xs font-mono opacity-90">
          {(confidence * 100).toFixed(0)}%
        </span>
      )}
    </span>
  );
}

// --- Regime State Machine Diagram ---
function RegimeStateMachine({ currentState, regimeData }) {
  const states = ["GREEN", "YELLOW", "RED", "RED_RECOVERY"];

  return (
    <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-3 h-full">
      <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
        Regime State Machine
      </div>
      <div className="grid grid-cols-2 gap-2">
        {states.map((s) => {
          const rc = REGIME_COLORS[s];
          const isCurrent = currentState === s;
          return (
            <div
              key={s}
              className={`rounded px-3 py-2 border text-center transition-all cursor-default ${
                isCurrent
                  ? `${rc.border} ${rc.bgFaint} border-2`
                  : "border-gray-700/30 bg-gray-800/30"
              }`}
            >
              <div
                className={`text-xs font-bold font-mono ${isCurrent ? rc.text : "text-gray-500"}`}
              >
                {s}
              </div>
              {isCurrent && (
                <div className={`mt-0.5 text-[9px] ${rc.text} font-semibold`}>
                  ● ACTIVE
                </div>
              )}
            </div>
          );
        })}
      </div>
      {regimeData?.time_in_state && (
        <div className="mt-2 text-[10px] text-gray-400">
          Time in state:{" "}
          <span className="text-cyan-400 font-mono">
            {regimeData.time_in_state}
          </span>
        </div>
      )}
    </div>
  );
}

// --- VIX Macro Chart ---
function VixMacroChart({ marketData, macroData, regimeData, timeframe }) {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 180,
      layout: { background: { color: "#111827" }, textColor: "#6B7280" },
      grid: {
        vertLines: { color: "#1F2937" },
        horzLines: { color: "#1F2937" },
      },
      timeScale: { borderColor: "#374151", timeVisible: true },
      rightPriceScale: { borderColor: "#374151" },
      crosshair: { mode: 0 },
    });

    const vixSeries = chart.addLineSeries({
      color: "#EF4444",
      lineWidth: 2,
      title: "VIX",
    });
    const spySeries = chart.addLineSeries({
      color: "#06B6D4",
      lineWidth: 1,
      title: "SPY",
      priceScaleId: "right",
    });

    if (macroData?.vix_history) {
      vixSeries.setData(
        macroData.vix_history.map((d) => ({ time: d.time, value: d.value })),
      );
    }
    if (marketData?.spy_history) {
      spySeries.setData(
        marketData.spy_history.map((d) => ({ time: d.time, value: d.value })),
      );
    }

    // VIX threshold lines
    vixSeries.createPriceLine({
      price: 18,
      color: "#10B981",
      lineWidth: 1,
      lineStyle: 2,
      title: "Threshold 18",
    });
    vixSeries.createPriceLine({
      price: 25,
      color: "#F59E0B",
      lineWidth: 1,
      lineStyle: 2,
      title: "Threshold 25",
    });

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
    };
  }, [marketData, macroData, timeframe]);

  return (
    <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-3 h-full">
      <div className="flex items-center justify-between mb-1">
        <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
          VIX+Macro Chart
        </div>
        <div className="flex items-center gap-3 text-[9px] text-gray-500">
          <span className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-red-500 inline-block" />
            VIX
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-cyan-500 inline-block" />
            SPY
          </span>
        </div>
      </div>
      <div ref={chartContainerRef} className="w-full" />
    </div>
  );
}

// --- Regime Parameter Panel ---
function RegimeParamPanel({ paramsData, regimeState, onOverride }) {
  const [editMode, setEditMode] = useState(false);
  const [localParams, setLocalParams] = useState({});
  const [overrideState, setOverrideState] = useState("AUTO");
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null); // "ok" | "err" | null

  useEffect(() => {
    if (paramsData) setLocalParams(paramsData);
  }, [paramsData]);

  const currentParams = REGIME_PARAMS_DEFAULT[regimeState] || {};

  const handleSaveParams = async () => {
    setSaving(true);
    setSaveStatus(null);
    const payload = {
      regime: regimeState,
      risk_pct: localParams.risk_pct ?? currentParams.risk_pct,
      max_positions: localParams.max_positions ?? currentParams.max_positions,
      kelly_mult: localParams.kelly_mult ?? currentParams.kelly_mult,
      signal_mult: localParams.signal_mult ?? currentParams.signal_mult,
      override: overrideState !== "AUTO",
    };
    try {
      const res = await fetch(getApiUrl("strategy/regime-params"), {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setSaveStatus("ok");
      if (onOverride) onOverride(payload);
      log.info("Regime params saved", payload);
    } catch (e) {
      setSaveStatus("err");
      log.error("Failed to save regime params:", e);
    } finally {
      setSaving(false);
      setTimeout(() => setSaveStatus(null), 3000);
    }
  };

  return (
    <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-3 h-full">
      <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
        Regime Parameter Panel
      </div>
      {/* Override row */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[10px] text-gray-500">Override</span>
        <div className="flex bg-gray-800 rounded overflow-hidden border border-gray-700/50">
          {["AUTO", "MAN"].map((m) => (
            <button
              key={m}
              onClick={() => {
                setOverrideState(m === "MAN" ? regimeState : "AUTO");
                setEditMode(m === "MAN");
              }}
              className={`px-2 py-0.5 text-[9px] font-bold ${
                (m === "AUTO" && overrideState === "AUTO") ||
                (m === "MAN" && overrideState !== "AUTO")
                  ? "bg-cyan-600 text-white"
                  : "text-gray-400"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
        <button
          onClick={() => setEditMode(!editMode)}
          className={`ml-auto text-[9px] px-2 py-0.5 rounded font-bold ${editMode ? "bg-amber-500/20 text-amber-400" : "bg-gray-700/50 text-gray-500"}`}
        >
          {editMode ? "ON" : "OFF"}
        </button>
      </div>
      {/* Params grid */}
      <div className="space-y-1.5">
        {[
          { label: "Risk %", key: "risk_pct", val: paramsData?.risk_pct ?? currentParams.risk_pct },
          { label: "Max Positions", key: "max_positions", val: paramsData?.max_positions ?? currentParams.max_positions },
          { label: "Kelly Mult", key: "kelly_mult", val: paramsData?.kelly_mult ?? currentParams.kelly_mult },
          { label: "Signal Mult", key: "signal_mult", val: paramsData?.signal_mult ?? currentParams.signal_mult },
        ].map((p) => (
          <div key={p.key} className="flex items-center justify-between">
            <span className="text-[10px] text-gray-500">{p.label}</span>
            {editMode ? (
              <input
                type="number"
                step="0.1"
                value={localParams[p.key] ?? p.val}
                onChange={(e) =>
                  setLocalParams({
                    ...localParams,
                    [p.key]: parseFloat(e.target.value),
                  })
                }
                className="w-16 bg-gray-800 border border-gray-600 rounded px-1.5 py-0.5 text-[11px] text-white text-right font-mono"
              />
            ) : (
              <span className="text-xs font-mono text-white">{p.val}</span>
            )}
          </div>
        ))}
      </div>
      {/* Save button (visible in edit mode) */}
      {editMode && (
        <div className="mt-2 flex items-center gap-2">
          <button
            onClick={handleSaveParams}
            disabled={saving}
            className={`flex-1 text-[9px] font-bold py-1 rounded transition-colors ${
              saving
                ? "bg-gray-700 text-gray-500 cursor-wait"
                : "bg-cyan-600 hover:bg-cyan-500 text-white"
            }`}
          >
            {saving ? "SAVING..." : "SAVE PARAMS"}
          </button>
          {saveStatus === "ok" && (
            <span className="text-[9px] text-emerald-400 font-bold">SAVED</span>
          )}
          {saveStatus === "err" && (
            <span className="text-[9px] text-red-400 font-bold">FAILED</span>
          )}
        </div>
      )}
      {/* Fuel indicator */}
      <div className="mt-2 flex items-center justify-between text-[10px]">
        <span className="text-gray-500">Fuel</span>
        <div className="flex gap-0.5">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className={`w-2 h-3 rounded-sm ${
                i < (localParams.max_positions ?? currentParams.max_positions ?? 0)
                  ? REGIME_COLORS[regimeState]?.bg || "bg-cyan-500"
                  : "bg-gray-700"
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// --- Performance Matrix ---
function RegimePerformanceMatrix({ backtestData }) {
  const regimes = ["GREEN", "YELLOW", "RED"];
  const metrics = ["win_rate", "avg_pnl", "sharpe"];
  const labels = {
    win_rate: "Win Rate",
    avg_pnl: "Avg P&L",
    sharpe: "Sharpe",
  };

  const getColor = (metric, val) => {
    if (metric === "win_rate")
      return val > 60
        ? "text-emerald-400"
        : val > 50
          ? "text-amber-400"
          : "text-red-400";
    if (metric === "avg_pnl")
      return val > 0 ? "text-emerald-400" : "text-red-400";
    if (metric === "sharpe")
      return val > 1.5
        ? "text-emerald-400"
        : val > 0.5
          ? "text-amber-400"
          : "text-red-400";
    return "text-gray-300";
  };

  return (
    <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-3 h-full">
      <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
        Performance Matrix
      </div>
      <table className="w-full text-[10px]">
        <thead>
          <tr className="border-b border-gray-700/30">
            <th className="text-left text-gray-500 pb-1"></th>
            {regimes.map((r) => (
              <th
                key={r}
                className={`text-right pb-1 font-bold ${REGIME_COLORS[r].text}`}
              >
                {r}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {metrics.map((m) => (
            <tr key={m} className="border-b border-gray-800/30">
              <td className="text-gray-500 py-1 pr-2">{labels[m]}</td>
              {regimes.map((r) => {
                const val = backtestData?.[r]?.[m];
                return (
                  <td
                    key={r}
                    className={`text-right font-mono py-1 ${getColor(m, val)}`}
                  >
                    {val != null
                      ? m === "win_rate"
                        ? `${val}%`
                        : m === "avg_pnl"
                          ? `$${val}`
                          : val
                      : "\u2014"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --- Sector Rotation Heatmap ---
function SectorHeatmap({ sectorsData }) {
  const sectors = sectorsData?.sectors || sectorsData?.rankings || [];
  return (
    <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-3 h-full">
      <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
        Sector Rotation
      </div>
      <div className="space-y-1">
        {sectors.map((s, i) => (
          <div key={s.sector || i} className="flex items-center gap-2">
            <span className="text-[9px] text-gray-400 w-20 truncate">
              {s.sector}
            </span>
            <div className="flex-1 h-3 bg-gray-800 rounded-sm overflow-hidden">
              <div
                className={`h-full rounded-sm ${s.score > 70 ? "bg-emerald-500" : s.score > 40 ? "bg-amber-500" : "bg-red-500"}`}
                style={{ width: `${Math.min(s.score || 0, 100)}%` }}
              />
            </div>
            <span className="text-[9px] font-mono text-gray-300 w-6 text-right">
              {s.score}
            </span>
          </div>
        ))}
        {sectors.length === 0 && (
          <div className="text-[9px] text-gray-600 text-center py-2">
            Loading sectors...
          </div>
        )}
      </div>
    </div>
  );
}

// --- Regime Flow Diagram ---
function RegimeFlowDiagram({ regimeState, paramsData }) {
  const defaults = REGIME_PARAMS_DEFAULT[regimeState] || {};
  const kellyMult = paramsData?.kelly_mult ?? defaults.kelly_mult ?? "?";
  const signalMult = paramsData?.signal_mult ?? defaults.signal_mult ?? "?";
  const riskPct = paramsData?.risk_pct ?? defaults.risk_pct;

  const nodes = [
    { id: "regime", label: "REGIME", value: regimeState },
    {
      id: "kelly",
      label: "Kelly",
      value: `${kellyMult}x`,
    },
    {
      id: "signal",
      label: "Signal",
      value: `${signalMult}x`,
    },
    {
      id: "risk",
      label: "Risk",
      value: riskPct === 0 ? "BLOCKED" : "OPEN",
    },
    {
      id: "position",
      label: "Position",
      value: `ATR x${regimeState === "GREEN" ? "1.0" : regimeState === "YELLOW" ? "1.2" : "1.5"}`,
    },
    {
      id: "exec",
      label: "Execution",
      value: riskPct === 0 ? "HALTED" : "ACTIVE",
    },
  ];
  const rc = REGIME_COLORS[regimeState] || REGIME_COLORS.YELLOW;

  return (
    <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-3 h-full">
      <div className="flex items-center justify-between mb-2">
        <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
          Regime Flow
        </div>
        {regimeState === "RED" && (
          <span className="text-[9px] text-red-400 font-mono">*New Boxe</span>
        )}
      </div>
      <div className="flex items-center gap-0.5 overflow-x-auto">
        {nodes.map((n, i) => (
          <React.Fragment key={n.id}>
            <div
              className={`rounded px-2 py-1.5 text-center border shrink-0 ${
                i === 0
                  ? `${rc.bgFaint} ${rc.border}`
                  : "bg-gray-800/50 border-gray-700/30"
              }`}
            >
              <div className="text-[9px] text-gray-500 leading-tight">{n.label}</div>
              <div
                className={`text-[10px] font-mono font-bold leading-tight ${
                  i === 0
                    ? rc.text
                    : n.value === "BLOCKED" || n.value === "HALTED"
                      ? "text-red-400"
                      : "text-white"
                }`}
              >
                {n.value}
              </div>
            </div>
            {i < nodes.length - 1 && (
              <span className="text-gray-600 text-[10px] shrink-0">{"\u2192"}</span>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

// --- Crash Protocol Panel ---
function CrashProtocolPanel({ riskGauges, macroData }) {
  const [armed, setArmed] = useState({
    vix_spike: true,
    hy_spread: true,
    yield_curve: true,
    breadth_collapse: true,
    spy_drop: true,
  });

  const triggers = [
    {
      key: "vix_spike",
      label: "VIX Breakout",
      active: (macroData?.vix || 0) > 25,
    },
    {
      key: "hy_spread",
      label: "HY Spread Wide",
      active: (macroData?.hy_spread || 0) > 5,
    },
    {
      key: "yield_curve",
      label: "Yield Curve Inv",
      active: (macroData?.yield_curve || 0) < 0,
    },
    { key: "breadth_collapse", label: "SPY Collapse", active: false },
    { key: "spy_drop", label: "SPY Drop > 2%", active: false },
  ];

  const armedCount = Object.values(armed).filter(Boolean).length;
  const isTriggered = triggers.some((t) => t.active && armed[t.key]);

  const handleToggleTrigger = async (key) => {
    const updated = { ...armed, [key]: !armed[key] };
    setArmed(updated);
    try {
      await fetch(getApiUrl("risk/config"), {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ crash_triggers: updated }),
      });
    } catch (e) {
      log.error("Failed to update crash trigger config:", e);
    }
  };

  return (
    <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-3 h-full">
      <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">
        Crash Protocol
      </div>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[9px] text-gray-500">{armedCount} armed triggers</span>
        <span
          className={`ml-auto text-[9px] px-1.5 py-0.5 rounded font-mono font-bold ${
            isTriggered
              ? "bg-red-500/20 text-red-400 animate-pulse"
              : "bg-emerald-500/20 text-emerald-400"
          }`}
        >
          {isTriggered ? "TRIGGERED" : "CLEAR"}
        </span>
      </div>
      <div className="text-[9px] text-gray-500 mb-1.5">protocol {isTriggered ? "ACTIVE" : "STANDBY"}</div>
      <div className="space-y-1.5">
        {triggers.map((t) => (
          <div key={t.key} className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <div
                className={`w-1.5 h-1.5 rounded-full ${
                  t.active && armed[t.key]
                    ? "bg-red-500 animate-pulse"
                    : armed[t.key]
                      ? "bg-emerald-500"
                      : "bg-gray-600"
                }`}
              />
              <span className={`text-[9px] ${t.active && armed[t.key] ? "text-red-400" : "text-gray-400"}`}>
                {t.label}
              </span>
            </div>
            <button
              onClick={() => handleToggleTrigger(t.key)}
              className={`text-[8px] px-1 py-0.5 rounded font-bold ${
                armed[t.key]
                  ? "bg-emerald-500/20 text-emerald-400"
                  : "bg-gray-700/50 text-gray-500"
              }`}
            >
              {armed[t.key] ? "ARMED" : "OFF"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- Agent Consensus Panel ---
function AgentConsensusPanel({ memoryData, regimeState }) {
  const agents =
    memoryData?.data?.agent_rankings || memoryData?.agent_rankings || [];

  const rc = REGIME_COLORS[regimeState] || REGIME_COLORS.YELLOW;

  const displayAgents = agents;

  return (
    <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-3 h-full">
      <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
        Agent Consensus
      </div>
      <div className="space-y-1.5">
        {displayAgents.map((a, i) => (
          <div
            key={a.name || i}
            className="flex items-center justify-between text-[10px]"
          >
            <span className="text-gray-400 w-16 truncate">{a.name}</span>
            <span
              className={`font-mono font-bold ${REGIME_COLORS[a.vote]?.text || "text-gray-400"}`}
            >
              {a.vote} {a.confidence}%
            </span>
          </div>
        ))}
        {displayAgents.length === 0 && (
          <div className="text-[9px] text-gray-600 text-center py-2">
            Awaiting agent consensus...
          </div>
        )}
      </div>
      {(memoryData?.data?.memory_iq || memoryData?.memory_iq) && (
        <div className="mt-2 pt-1.5 border-t border-gray-700/30 text-[10px] text-gray-500">
          Memory IQ{" "}
          <span className="text-purple-400 font-mono font-bold">
            {memoryData.data?.memory_iq || memoryData.memory_iq}
          </span>
        </div>
      )}
    </div>
  );
}

// --- Transition History ---
function TransitionHistory({ regimeData }) {
  const transitions = regimeData?.transitions || [];
  return (
    <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-3">
      <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
        Regime Transition History
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[9px]">
          <thead>
            <tr className="border-b border-gray-700/30 text-gray-500">
              <th className="text-left py-1 pr-2">Time</th>
              <th className="text-left py-1 pr-2">From → To</th>
              <th className="text-left py-1 pr-2">Trigger</th>
              <th className="text-right py-1 pr-2">confidence</th>
              <th className="text-right py-1 pr-2">duration</th>
              <th className="text-right py-1">P&L</th>
            </tr>
          </thead>
          <tbody>
            {transitions.slice(0, 10).map((t, i) => (
              <tr
                key={i}
                className="border-b border-gray-800/20 hover:bg-gray-800/20"
              >
                <td className="py-1 pr-2 text-gray-500 font-mono">
                  {t.timestamp}
                </td>
                <td className="py-1 pr-2">
                  <span className={`font-bold ${REGIME_COLORS[t.from]?.text || "text-gray-400"}`}>
                    {t.from}
                  </span>
                  <span className="text-gray-600"> → </span>
                  <span className={`font-bold ${REGIME_COLORS[t.to]?.text || "text-gray-400"}`}>
                    {t.to}
                  </span>
                </td>
                <td className="py-1 pr-2 text-gray-400">{t.trigger}</td>
                <td className="py-1 pr-2 text-right text-gray-400 font-mono">
                  {t.confidence}%
                </td>
                <td className="py-1 pr-2 text-right text-gray-500 font-mono">
                  {t.duration}
                </td>
                <td
                  className={`py-1 text-right font-mono ${(t.pnl_impact || 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}
                >
                  {t.pnl_impact != null ? `$${t.pnl_impact}` : "\u2014"}
                </td>
              </tr>
            ))}
            {transitions.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-3 text-gray-600">
                  No transitions recorded
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// --- Footer Ticker ---
function FooterTicker({ marketData, regimeState }) {
  const tickers = ["SPY", "QQQ", "DIA", "VIX", "IWM"];
  const rc = REGIME_COLORS[regimeState] || REGIME_COLORS.YELLOW;
  return (
    <div className="bg-[#0D1117] border-t border-gray-800/50 px-4 py-1 flex items-center justify-between">
      <div className="flex items-center gap-5">
        {tickers.map((t) => {
          const d = marketData?.indices?.[t] || marketData?.[t] || {};
          const change = d.change_pct || d.change || 0;
          return (
            <div key={t} className="flex items-center gap-1.5 text-[10px]">
              <span className="text-gray-500 font-semibold">{t}</span>
              <span className="text-white font-mono">
                {d.price?.toFixed(2) ?? "\u2014"}
              </span>
              <span
                className={`font-mono ${change >= 0 ? "text-emerald-400" : "text-red-400"}`}
              >
                {change >= 0 ? "+" : ""}
                {change?.toFixed(2)}%
              </span>
            </div>
          );
        })}
      </div>
      <span className={`text-[9px] font-bold font-mono ${rc.text}`}>
        REGIME: {regimeState}
      </span>
    </div>
  );
}

// ============================================================
// MAIN PAGE COMPONENT
// ============================================================
export default function MarketRegime() {
  // --- API Hooks ---
  const {
    data: regimeData,
    loading: regimeLoading,
    error: regimeError,
  } = useApi("openclaw/regime", { pollIntervalMs: 10000 });
  const { data: macroData, loading: macroLoading } = useApi("openclaw/macro", {
    pollIntervalMs: 10000,
  });
  const { data: paramsData, refetch: refetchParams } = useApi("strategy/regime-params", {
    pollIntervalMs: 30000,
  });
  const { data: backtestData } = useApi("backtest/regime", {
    pollIntervalMs: 60000,
  });
  const { data: sectorsData } = useApi("openclaw/sectors", {
    pollIntervalMs: 30000,
  });
  const { data: scanData } = useApi("openclaw/scan", { pollIntervalMs: 30000 });
  const { data: memoryData } = useApi("openclaw/memory", {
    pollIntervalMs: 30000,
  });
  const { data: marketData } = useApi("market", { pollIntervalMs: 5000 });
  const { data: riskGauges } = useApi("risk/risk-gauges", {
    pollIntervalMs: 15000,
  });
  const { data: healthData } = useApi("openclaw/health", {
    pollIntervalMs: 30000,
  });
  const { data: riskScore } = useApi("risk/risk-score", {
    pollIntervalMs: 15000,
  });
  const { data: whaleFlow } = useApi("openclaw/whale-flow", {
    pollIntervalMs: 20000,
  });
  const { data: transitionData } = useApi("openclaw/regime/transitions", {
    pollIntervalMs: 30000,
  });

  // --- Local State ---
  const [timeframe, setTimeframe] = useState("1M");
  const [biasMultiplier, setBiasMultiplier] = useState(1.0);

  // Derived
  const currentRegime = regimeData?.state || paramsData?.regime || "YELLOW";
  const rc = REGIME_COLORS[currentRegime] || REGIME_COLORS.YELLOW;

  // --- Bias Override Handler ---
  const handleBiasChange = useCallback(async (val) => {
    setBiasMultiplier(val);
    try {
      await postBiasOverride(val);
    } catch (e) {
      log.error("Failed to POST bias override:", e);
    }
  }, []);

  // Risk score color
  const riskScoreVal = riskScore?.score || 0;
  const riskColor =
    riskScoreVal > 70 ? "text-red-400" : riskScoreVal > 40 ? "text-amber-400" : "text-emerald-400";
  const riskLabel =
    riskScoreVal > 70 ? "critical risk" : riskScoreVal > 40 ? "elevated" : "healthy";
  const riskLabelColor =
    riskScoreVal > 70 ? "bg-red-500/20 text-red-400" : riskScoreVal > 40 ? "bg-amber-500/20 text-amber-400" : "bg-emerald-500/20 text-emerald-400";

  // Crash proto status
  const crashTriggered = (macroData?.vix || 0) > 25;

  // --- Loading / Error ---
  if (regimeLoading && !regimeData) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0A0E17]">
        <div className="text-cyan-400 animate-pulse text-lg font-mono">
          Loading Regime Intelligence...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0E17] text-white flex flex-col">
      {/* ============ HEADER BAR ============ */}
      <div className="px-4 py-2 border-b border-gray-800/50 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <h1 className="text-base font-bold text-white tracking-tight">
            Market Regime
          </h1>
          <RegimeBadge
            state={currentRegime}
            confidence={regimeData?.hmm_confidence}
          />
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-[10px]">
            <span className="text-gray-500">Risk Score:</span>
            <span className={`font-mono text-sm font-bold ${riskColor}`}>
              {riskScore?.score ?? "\u2014"}
            </span>
            <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${riskLabelColor}`}>
              {riskLabel}
            </span>
          </div>
          <div className="flex bg-gray-800/50 rounded overflow-hidden border border-gray-700/30">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-2 py-0.5 text-[9px] font-semibold transition-colors ${
                  timeframe === tf
                    ? "bg-cyan-600 text-white"
                    : "text-gray-500 hover:text-white"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ============ KPI STRIP ============ */}
      <div className="px-4 py-1.5 border-b border-gray-800/30">
        <div className="grid grid-cols-10 gap-1.5">
          <KpiCard
            label="VIX"
            value={macroData?.vix?.toFixed(1) ?? regimeData?.vix?.toFixed(1)}
            color={
              (macroData?.vix || 0) > 25
                ? "text-red-400"
                : (macroData?.vix || 0) > 18
                  ? "text-amber-400"
                  : "text-emerald-400"
            }
          />
          <KpiCard
            label="HY Spread"
            value={macroData?.hy_spread?.toFixed(2)}
            unit="bps"
            color={
              (macroData?.hy_spread || 0) > 5 ? "text-red-400" : "text-cyan-400"
            }
          />
          <KpiCard
            label="Yield Curve"
            value={
              macroData?.yield_curve?.toFixed(2) ??
              regimeData?.macro_context?.yield_curve?.toFixed(2)
            }
            unit="%"
            color={
              (macroData?.yield_curve || 0) < 0
                ? "text-red-400"
                : "text-emerald-400"
            }
          />
          <KpiCard
            label="Fear & Greed"
            value={macroData?.fear_greed_index}
            color={
              (macroData?.fear_greed_index || 50) < 25
                ? "text-red-400"
                : (macroData?.fear_greed_index || 50) > 75
                  ? "text-emerald-400"
                  : "text-amber-400"
            }
          />
          <KpiCard
            label="Hurst"
            value={regimeData?.hurst?.toFixed(3)}
            color={
              (regimeData?.hurst || 0.5) > 0.5
                ? "text-cyan-400"
                : "text-purple-400"
            }
          />
          <KpiCard
            label="VELEZ SLAM"
            value={macroData?.velez_score ?? scanData?.velez_breadth}
            color="text-cyan-400"
          />
          <KpiCard
            label="Oscillator"
            value={macroData?.oscillator?.toFixed(2)}
            color="text-purple-400"
          />
          <KpiCard
            label="Bias Mult"
            value={macroData?.bias?.toFixed(2) ?? biasMultiplier.toFixed(2)}
            color="text-amber-400"
          />
          <KpiCard
            label="Risk Score"
            value={riskScore?.score}
            color={
              (riskScore?.score || 0) > 70 ? "text-red-400" : "text-cyan-400"
            }
          />
          <KpiCard
            label="Crash Proto"
            value={crashTriggered ? "TRIGGERED" : "CLEAR"}
            color={crashTriggered ? "text-red-400" : "text-emerald-400"}
            alert={(macroData?.vix || 0) > 40}
          />
        </div>
      </div>

      {/* ============ MAIN GRID ============ */}
      <div className="flex-1 px-4 py-2 overflow-y-auto">
        <div className="grid grid-cols-12 gap-2">
          {/* ROW 1: State Machine (4 cols) + VIX Chart (8 cols) */}
          <div className="col-span-4">
            <RegimeStateMachine
              currentState={currentRegime}
              regimeData={regimeData}
            />
          </div>
          <div className="col-span-8">
            <VixMacroChart
              marketData={marketData}
              macroData={macroData}
              regimeData={regimeData}
              timeframe={timeframe}
            />
          </div>

          {/* ROW 2: Params (3 cols) + Performance (3 cols) + Sector (3 cols) -- spans 9, remaining 3 empty or filled */}
          <div className="col-span-4">
            <RegimeParamPanel
              paramsData={paramsData}
              regimeState={currentRegime}
              onOverride={() => refetchParams()}
            />
          </div>
          <div className="col-span-4">
            <RegimePerformanceMatrix backtestData={backtestData} />
          </div>
          <div className="col-span-4">
            <SectorHeatmap sectorsData={sectorsData} />
          </div>

          {/* ROW 3: Regime Flow (6 cols) + Crash Protocol (3 cols) + Agent Consensus (3 cols) */}
          <div className="col-span-6">
            <RegimeFlowDiagram
              regimeState={currentRegime}
              paramsData={paramsData}
            />
          </div>
          <div className="col-span-3">
            <CrashProtocolPanel riskGauges={riskGauges} macroData={macroData} />
          </div>
          <div className="col-span-3">
            <AgentConsensusPanel memoryData={memoryData} regimeState={currentRegime} />
          </div>

          {/* ROW 4: Transition History (full width) */}
          <div className="col-span-12">
            <TransitionHistory regimeData={transitionData || regimeData} />
          </div>

          {/* ROW 5: Bias Multiplier Slider */}
          <div className="col-span-12">
            <div className="bg-[#111827] rounded-lg border border-gray-700/30 px-3 py-1.5 flex items-center gap-3">
              <span className="text-[9px] text-gray-500 uppercase tracking-wider font-semibold whitespace-nowrap">
                Bias Multiplier
              </span>
              <input
                type="range"
                min="0"
                max="5"
                step="0.1"
                value={biasMultiplier}
                onChange={(e) => handleBiasChange(parseFloat(e.target.value))}
                className="flex-1 h-1 accent-cyan-500"
              />
              <span className="text-xs font-mono text-cyan-400 w-8 text-right">
                {biasMultiplier.toFixed(1)}
              </span>
              {whaleFlow?.alerts?.length > 0 && (
                <div className="ml-3 flex items-center gap-1.5 text-[9px]">
                  <span className="text-purple-400 font-semibold">WHALE:</span>
                  <span className="text-gray-300">
                    {whaleFlow.alerts[0]?.symbol} - {whaleFlow.alerts[0]?.type}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ============ FOOTER TICKER ============ */}
      <FooterTicker marketData={marketData} regimeState={currentRegime} />

      {/* Error toast */}
      {regimeError && (
        <div className="fixed bottom-12 right-4 bg-red-900/90 border border-red-500/50 text-red-200 text-xs px-4 py-2 rounded-lg shadow-lg">
          Regime API error: {regimeError.message || "Connection failed"}
        </div>
      )}
    </div>
  );
}
