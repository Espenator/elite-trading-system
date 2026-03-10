// frontend-v2/src/pages/MarketRegime.jsx
// Market Regime — AI Brain's Macro Intelligence Center (Page 10/15)
// Route: /market-regime

import React, { useState, useCallback, useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import clsx from "clsx";
import { format } from "date-fns";
import {
  useRegimeState,
  useMacroState,
  useRegimeParams,
  useRegimePerformance,
  useSectorRotation,
  useRegimeTransitions,
  postBiasOverride,
} from "../hooks/useApi";
import { useApi } from "../hooks/useApi";
import { getApiUrl, getAuthHeaders } from "../config/api";
import log from "@/utils/logger";

// ============================================================
// CONSTANTS
// ============================================================
const REGIME_COLORS = {
  GREEN: {
    bg: "bg-emerald-500",
    text: "text-emerald-400",
    hex: "#10B981",
    hexBright: "#34D399",
    bgFaint: "bg-emerald-500/10",
    border: "border-emerald-500/40",
    badgeBg: "bg-emerald-600",
  },
  YELLOW: {
    bg: "bg-amber-500",
    text: "text-amber-400",
    hex: "#F59E0B",
    hexBright: "#FBBF24",
    bgFaint: "bg-amber-500/10",
    border: "border-amber-500/40",
    badgeBg: "bg-amber-600",
  },
  RED: {
    bg: "bg-red-500",
    text: "text-red-400",
    hex: "#EF4444",
    hexBright: "#F87171",
    bgFaint: "bg-red-500/10",
    border: "border-red-500/40",
    badgeBg: "bg-red-600",
  },
  RED_RECOVERY: {
    bg: "bg-orange-500",
    text: "text-orange-400",
    hex: "#F97316",
    hexBright: "#FB923C",
    bgFaint: "bg-orange-500/10",
    border: "border-orange-500/40",
    badgeBg: "bg-orange-600",
  },
};

const REGIME_PARAMS_DEFAULT = {
  GREEN: { risk_pct: 2.0, max_positions: 6, kelly_mult: 1.5, signal_mult: 1.1 },
  YELLOW: {
    risk_pct: 1.5,
    max_positions: 5,
    kelly_mult: 1.0,
    signal_mult: 1.0,
  },
  RED: { risk_pct: 5.0, max_positions: 0, kelly_mult: 0.0, signal_mult: 0.0 },
  RED_RECOVERY: {
    risk_pct: 1.0,
    max_positions: 4,
    kelly_mult: 0.75,
    signal_mult: 0.95,
  },
};

const TIMEFRAMES = ["1D", "1W", "1M", "3M", "1Y"];

// ============================================================
// PANEL WRAPPER
// ============================================================
function Panel({ children, className }) {
  return (
    <div
      className={clsx(
        "bg-[#111827] rounded-lg border border-gray-700/30 p-3",
        className,
      )}
    >
      {children}
    </div>
  );
}

function PanelTitle({ children, right }) {
  return (
    <div className="flex items-center justify-between mb-2">
      <div className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
        {children}
      </div>
      {right && <div>{right}</div>}
    </div>
  );
}

// ============================================================
// KPI CARD
// ============================================================
function KpiCard({ label, value, unit, color, alert }) {
  return (
    <div
      className={clsx(
        "bg-[#111827] rounded px-2 py-1.5 border",
        alert ? "border-red-500/50 animate-pulse" : "border-gray-700/30",
      )}
    >
      <div className="text-[9px] text-gray-500 uppercase tracking-wider truncate">
        {label}
      </div>
      <div
        className={clsx(
          "text-sm font-mono font-bold leading-tight",
          color || "text-cyan-400",
        )}
      >
        {value ?? "\u2014"}
        {unit && (
          <span className="text-[9px] text-gray-500 ml-0.5">{unit}</span>
        )}
      </div>
    </div>
  );
}

// ============================================================
// REGIME BADGE
// ============================================================
function RegimeBadge({ state, confidence }) {
  const rc = REGIME_COLORS[state] || REGIME_COLORS.YELLOW;
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded px-3 py-1 text-sm font-black tracking-wider text-white",
        rc.badgeBg,
      )}
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

// ============================================================
// REGIME STATE MACHINE (mockup: 4 large rectangular buttons in a row)
// ============================================================
function RegimeStateMachine({ currentState, regimeData }) {
  const states = ["GREEN", "YELLOW", "RED", "RED_RECOVERY"];

  return (
    <Panel className="h-full">
      <PanelTitle>Regime State Machine</PanelTitle>
      <div className="relative">
        <div className="grid grid-cols-4 gap-1.5">
          {states.map((s) => {
            const rc = REGIME_COLORS[s];
            const isCurrent = currentState === s;
            return (
              <div
                key={s}
                className={clsx(
                  "rounded-lg px-2 py-3 border text-center transition-all",
                  isCurrent
                    ? clsx(rc.bg, "text-white border-transparent")
                    : "border-gray-700/30 bg-gray-800/30 text-gray-500",
                )}
              >
                <div className="text-[10px] font-bold font-mono leading-tight">
                  {s === "RED_RECOVERY" ? (
                    <>
                      RED
                      <br />
                      <span className="text-[8px]">RECOVERY</span>
                    </>
                  ) : (
                    s
                  )}
                </div>
              </div>
            );
          })}
        </div>
        <div className="flex items-center justify-center gap-0.5 mt-2 text-gray-600">
          <span className="text-[10px]">{"\u2193"}</span>
          <span className="text-[10px]">{"\u2191"}</span>
        </div>
      </div>
      {regimeData?.time_in_state && (
        <div className="mt-1.5 text-[10px] text-gray-400">
          Time in state:{" "}
          <span className="text-cyan-400 font-mono">
            {regimeData.time_in_state}
          </span>
        </div>
      )}
    </Panel>
  );
}

// ============================================================
// VIX+MACRO CHART (Recharts)
// ============================================================
function VixMacroChart({ macroData, regimeData, timeframe }) {
  const chartData = useMemo(() => {
    if (macroData?.vix_history) {
      return macroData.vix_history.map((d) => ({
        time:
          typeof d.time === "string"
            ? d.time
            : format(new Date(d.time * 1000), "MM/dd"),
        vix: d.value,
        spy: d.spy,
      }));
    }
    const now = Date.now();
    return Array.from({ length: 30 }, (_, i) => ({
      time: format(new Date(now - (29 - i) * 86400000), "MM/dd"),
      vix: 0,
      spy: 0,
    }));
  }, [macroData, timeframe]);

  return (
    <Panel className="h-full">
      <PanelTitle
        right={
          <div className="flex items-center gap-3 text-[9px] text-gray-500">
            <span className="flex items-center gap-1">
              <span className="w-3 h-0.5 bg-red-500 inline-block" />
              VIX
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-0.5 bg-[#60A5FA] inline-block" />
              SPY
            </span>
          </div>
        }
      >
        VIX{"\u00D7"}Macro Chart
      </PanelTitle>
      <ResponsiveContainer width="100%" height={170}>
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 5, left: -10, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
          <XAxis
            dataKey="time"
            tick={{ fontSize: 9, fill: "#6B7280" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 9, fill: "#6B7280" }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1F2937",
              border: "1px solid #374151",
              borderRadius: 6,
              fontSize: 10,
            }}
            labelStyle={{ color: "#9CA3AF" }}
          />
          <ReferenceLine y={14} stroke="#6B7280" strokeDasharray="4 4" />
          <ReferenceLine y={18} stroke="#6B7280" strokeDasharray="4 4" />
          <ReferenceLine
            y={25}
            stroke="#F59E0B"
            strokeDasharray="4 4"
            label={{
              value: "Threshold",
              fill: "#F59E0B",
              fontSize: 8,
              position: "right",
            }}
          />
          <ReferenceLine
            y={40}
            stroke="#A855F7"
            strokeDasharray="4 4"
            label={{
              value: "Threshold",
              fill: "#A855F7",
              fontSize: 8,
              position: "right",
            }}
          />
          <Line
            type="monotone"
            dataKey="vix"
            stroke="#EF4444"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="spy"
            stroke="#60A5FA"
            strokeWidth={1}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </Panel>
  );
}

// ============================================================
// REGIME PARAMETER PANEL
// ============================================================
function RegimeParamPanel({ paramsData, regimeState, onOverride }) {
  const [editMode, setEditMode] = useState(false);
  const [localParams, setLocalParams] = useState({});
  const [overrideState, setOverrideState] = useState("AUTO");
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);

  const currentParams = REGIME_PARAMS_DEFAULT[regimeState] || {};

  const handleSaveParams = async () => {
    setSaving(true);
    setSaveStatus(null);
    const payload = {
      regime: regimeState,
      risk_pct:
        localParams.risk_pct ?? paramsData?.risk_pct ?? currentParams.risk_pct,
      max_positions:
        localParams.max_positions ??
        paramsData?.max_positions ??
        currentParams.max_positions,
      kelly_mult:
        localParams.kelly_mult ??
        paramsData?.kelly_mult ??
        currentParams.kelly_mult,
      signal_mult:
        localParams.signal_mult ??
        paramsData?.signal_mult ??
        currentParams.signal_mult,
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

  const riskVal = paramsData?.risk_pct ?? currentParams.risk_pct;
  const maxPosVal = paramsData?.max_positions ?? currentParams.max_positions;
  const kellyVal = paramsData?.kelly_mult ?? currentParams.kelly_mult;
  const signalVal = paramsData?.signal_mult ?? currentParams.signal_mult;

  const paramRows = [
    { label: "Risk%", key: "risk_pct", val: riskVal },
    { label: "Max Positions", key: "max_positions", val: maxPosVal },
    { label: "Kelly Mult", key: "kelly_mult", val: kellyVal },
    { label: "Signal Mult", key: "signal_mult", val: signalVal },
  ];

  return (
    <Panel className="h-full">
      <PanelTitle>Regime Parameter Panel</PanelTitle>
      {/* Override row */}
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-[10px] text-gray-500">Override</span>
        <div className="flex bg-gray-800 rounded overflow-hidden border border-gray-700/50">
          {["AUTO", "MAN"].map((m) => (
            <button
              key={m}
              onClick={() => {
                setOverrideState(m === "MAN" ? regimeState : "AUTO");
                setEditMode(m === "MAN");
              }}
              className={clsx(
                "px-2 py-0.5 text-[9px] font-bold",
                (m === "AUTO" && overrideState === "AUTO") ||
                  (m === "MAN" && overrideState !== "AUTO")
                  ? "bg-cyan-600 text-white"
                  : "text-gray-400",
              )}
            >
              {m}
            </button>
          ))}
        </div>
        <button
          onClick={() => setEditMode(!editMode)}
          className={clsx(
            "ml-auto text-[9px] px-2 py-0.5 rounded font-bold",
            editMode
              ? "bg-amber-500/20 text-amber-400"
              : "bg-gray-700/50 text-gray-500",
          )}
        >
          {editMode ? "ON" : "OFF"}
        </button>
      </div>
      {/* Compact params - matching mockup layout */}
      {editMode ? (
        <div className="space-y-1.5">
          {paramRows.map((p) => (
            <div key={p.key} className="flex items-center justify-between">
              <span className="text-[10px] text-gray-500">{p.label}</span>
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
            </div>
          ))}
          <div className="mt-1.5 flex items-center gap-2">
            <button
              onClick={handleSaveParams}
              disabled={saving}
              className={clsx(
                "flex-1 text-[9px] font-bold py-1 rounded transition-colors",
                saving
                  ? "bg-gray-700 text-gray-500 cursor-wait"
                  : "bg-cyan-600 hover:bg-cyan-500 text-white",
              )}
            >
              {saving ? "SAVING..." : "SAVE PARAMS"}
            </button>
            {saveStatus === "ok" && (
              <span className="text-[9px] text-emerald-400 font-bold">
                SAVED
              </span>
            )}
            {saveStatus === "err" && (
              <span className="text-[9px] text-red-400 font-bold">FAILED</span>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-gray-500">Risk%</span>
            <span className="text-white font-mono">{riskVal}</span>
          </div>
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-gray-500">Max Positions</span>
            <div className="flex items-center gap-2">
              <span className="text-white font-mono">{maxPosVal}</span>
              <span className="text-gray-600 text-[9px]">Fuel</span>
              <div className="flex gap-0.5">
                {[...Array(6)].map((_, i) => (
                  <div
                    key={i}
                    className={clsx(
                      "w-1.5 h-2.5 rounded-sm",
                      i < maxPosVal
                        ? REGIME_COLORS[regimeState]?.bg || "bg-cyan-500"
                        : "bg-gray-700",
                    )}
                  />
                ))}
              </div>
            </div>
          </div>
          <div className="flex items-center text-[10px] gap-3">
            <div className="flex items-center gap-1">
              <span className="text-gray-500">Kelly</span>
              <span className="text-white font-mono">{kellyVal}</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-gray-500">Signal Mult</span>
              <span className="text-white font-mono">{signalVal}</span>
            </div>
          </div>
        </div>
      )}
    </Panel>
  );
}

// ============================================================
// PERFORMANCE MATRIX
// ============================================================
function PerformanceMatrix({ backtestData }) {
  const regimes = ["GREEN", "YELLOW", "RED"];
  const metrics = [
    { key: "win_rate", label: "Win Rate", fmt: (v) => `${v}%` },
    {
      key: "avg_pnl",
      label: "Avg P&L",
      fmt: (v) => (v >= 0 ? `$${v}` : `-$${Math.abs(v)}`),
    },
    { key: "sharpe", label: "Sharpe", fmt: (v) => v },
  ];

  // Fallback data — mockup values when API empty
  const fallbackData = {
    GREEN: { win_rate: 72, avg_pnl: 245, sharpe: 2.1 },
    YELLOW: { win_rate: 58, avg_pnl: 82, sharpe: 0.8 },
    RED: { win_rate: 31, avg_pnl: -156, sharpe: -0.3 },
  };

  const getColor = (key, val) => {
    if (key === "win_rate")
      return val > 60
        ? "text-emerald-400"
        : val > 50
          ? "text-amber-400"
          : "text-red-400";
    if (key === "avg_pnl") return val > 0 ? "text-emerald-400" : "text-red-400";
    if (key === "sharpe")
      return val > 1.5
        ? "text-emerald-400"
        : val > 0.5
          ? "text-amber-400"
          : "text-red-400";
    return "text-gray-300";
  };

  return (
    <Panel className="h-full">
      <PanelTitle>Performance Matrix</PanelTitle>
      <table className="w-full text-[10px]">
        <thead>
          <tr className="border-b border-gray-700/30">
            <th className="text-left text-gray-500 pb-1" />
            {regimes.map((r) => (
              <th
                key={r}
                className={clsx(
                  "text-right pb-1 font-bold",
                  REGIME_COLORS[r].text,
                )}
              >
                {r}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {metrics.map((m) => (
            <tr key={m.key} className="border-b border-gray-800/30">
              <td className="text-gray-500 py-1 pr-2">{m.label}</td>
              {regimes.map((r) => {
                const val =
                  backtestData?.[r]?.[m.key] ?? fallbackData[r]?.[m.key];
                return (
                  <td
                    key={r}
                    className={clsx(
                      "text-right font-mono py-1",
                      getColor(m.key, val),
                    )}
                  >
                    {val != null ? m.fmt(val) : "\u2014"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}

// ============================================================
// REGIME FLOW DIAGRAM
// ============================================================
function RegimeFlowDiagram({ regimeState, paramsData }) {
  const defaults = REGIME_PARAMS_DEFAULT[regimeState] || {};
  const kellyMult = paramsData?.kelly_mult ?? defaults.kelly_mult ?? "?";
  const signalMult = paramsData?.signal_mult ?? defaults.signal_mult ?? "?";
  const riskPct = paramsData?.risk_pct ?? defaults.risk_pct;
  const isRed = regimeState === "RED";
  const maxPos = paramsData?.max_positions ?? defaults.max_positions ?? 0;

  const nodes = [
    { id: "regime", label: "REGIME", value: regimeState },
    { id: "sizer", label: "Sizer", value: `${riskPct ?? 2}x` },
    { id: "kelly", label: "Kelly", value: `${kellyMult}x` },
    { id: "signal", label: "Signal", value: maxPos === 0 ? "CLOSED" : "OPEN" },
    { id: "engine", label: "Engine", value: maxPos === 0 ? "OFF" : "ON" },
    {
      id: "risk",
      label: "Risk Governor",
      value: maxPos === 0 ? "BLOCKED" : "OPEN",
    },
    { id: "pos", label: "Position Mgr", value: "ATR x1.0" },
    { id: "exec", label: "Execution", value: isRed ? "HALTED" : "ACTIVE" },
  ];

  const rc = REGIME_COLORS[regimeState] || REGIME_COLORS.YELLOW;

  return (
    <Panel className="h-full">
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
          Regime Flow
        </div>
        {isRed && (
          <span className="text-[9px] text-red-400 font-mono">*New Box+</span>
        )}
      </div>
      <div className="flex items-center gap-0.5 overflow-x-auto">
        {nodes.map((n, i) => (
          <React.Fragment key={n.id}>
            <div
              className={clsx(
                "rounded px-1.5 py-1 text-center border shrink-0 min-w-0",
                i === 0
                  ? `${rc.bgFaint} ${rc.border}`
                  : "bg-gray-800/50 border-gray-700/30",
              )}
            >
              <div className="text-[8px] text-gray-500 leading-tight">
                {n.label}
              </div>
              <div
                className={clsx(
                  "text-[9px] font-mono font-bold leading-tight",
                  i === 0
                    ? rc.text
                    : n.value === "BLOCKED" ||
                        n.value === "HALTED" ||
                        n.value === "HALT" ||
                        n.value === "OFF"
                      ? "text-red-400"
                      : "text-white",
                )}
              >
                {n.value}
              </div>
            </div>
            {i < nodes.length - 1 && (
              <span className="text-gray-600 text-[9px] shrink-0">
                {"\u2192"}
              </span>
            )}
          </React.Fragment>
        ))}
      </div>
    </Panel>
  );
}

// ============================================================
// TRANSITION HISTORY (mockup: Time, FROM->TO, trigger, confidence, duration, P&L)
// ============================================================
const FALLBACK_TRANSITIONS = [
  {
    timestamp: "23.03.23 00:33:00",
    from: "GREEN",
    to: "YELLOW",
    trigger: "trigger",
    confidence: 92,
    duration: "10 min",
    pnl_impact: 1335,
  },
  {
    timestamp: "23.03.23 10:32:00",
    from: "GREEN",
    to: "YELLOW",
    trigger: "trigger",
    confidence: 92,
    duration: "13 min",
    pnl_impact: 2455,
  },
  {
    timestamp: "23.03.23 10:33:00",
    from: "GREEN",
    to: "YELLOW",
    trigger: "trigger",
    confidence: 92,
    duration: "10 min",
    pnl_impact: 3455,
  },
  {
    timestamp: "23.03.22 10:03:00",
    from: "GREEN",
    to: "YELLOW",
    trigger: "trigger",
    confidence: 93,
    duration: "10 min",
    pnl_impact: -5156,
  },
  {
    timestamp: "23.03.23 10:27:00",
    from: "RED",
    to: "RED",
    trigger: "trigger",
    confidence: 95,
    duration: "20 min",
    pnl_impact: -12030,
  },
];

function TransitionHistory({ transitionData, regimeData }) {
  const raw = transitionData?.transitions || regimeData?.transitions || [];
  const transitions = raw.length ? raw : FALLBACK_TRANSITIONS;

  return (
    <Panel>
      <PanelTitle>Regime Transition History</PanelTitle>
      <div className="overflow-x-auto">
        <table className="w-full text-[9px]">
          <thead>
            <tr className="border-b border-gray-700/30 text-gray-500">
              <th className="text-left py-1 pr-2">Time</th>
              <th className="text-left py-1 pr-2">FROM→TO</th>
              <th className="text-left py-1 pr-2">trigger</th>
              <th className="text-right py-1 pr-2">confidence</th>
              <th className="text-right py-1 pr-2">duration</th>
              <th className="text-right py-1">P&L</th>
            </tr>
          </thead>
          <tbody>
            {transitions.slice(0, 6).map((t, i) => (
              <tr
                key={i}
                className="border-b border-gray-800/20 hover:bg-gray-800/20"
              >
                <td className="py-1 pr-2 text-gray-500 font-mono">
                  {t.timestamp}
                </td>
                <td className="py-1 pr-2">
                  <span
                    className={clsx(
                      "font-bold",
                      REGIME_COLORS[t.from]?.text || "text-gray-400",
                    )}
                  >
                    {t.from}
                  </span>
                  <span className="text-gray-600">{" → "}</span>
                  <span
                    className={clsx(
                      "font-bold",
                      REGIME_COLORS[t.to]?.text || "text-gray-400",
                    )}
                  >
                    {t.to}
                  </span>
                </td>
                <td className="py-1 pr-2 text-gray-500">
                  {t.trigger ?? "trigger"}
                </td>
                <td className="py-1 pr-2 text-right text-gray-400 font-mono">
                  {t.confidence}%
                </td>
                <td className="py-1 pr-2 text-right text-gray-500 font-mono">
                  {t.duration}
                </td>
                <td
                  className={clsx(
                    "py-1 text-right font-mono",
                    t.pnl_impact != null
                      ? (t.pnl_impact || 0) >= 0
                        ? "text-emerald-400"
                        : "text-red-400"
                      : "text-gray-500",
                  )}
                >
                  {t.pnl_impact != null
                    ? (t.pnl_impact >= 0 ? "+$" : "-$") +
                      Math.abs(t.pnl_impact).toLocaleString()
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

// ============================================================
// SECTOR ROTATION (mockup: horizontal bar chart - Tech, Healthcare, Energy, Financials)
// ============================================================
const FALLBACK_SECTORS = [
  { sector: "Tech", score: 85 },
  { sector: "Healthcare", score: 72 },
  { sector: "Energy", score: 45 },
  { sector: "Financials", score: 38 },
];

function SectorRotation({ sectorsData }) {
  const sectors = sectorsData?.sectors?.length
    ? sectorsData.sectors
    : sectorsData?.rankings?.length
      ? sectorsData.rankings
      : FALLBACK_SECTORS;

  return (
    <Panel className="h-full">
      <PanelTitle>Sector Rotation</PanelTitle>
      <div className="space-y-2">
        {sectors.map((s, i) => (
          <div key={s.sector || i} className="flex items-center gap-2">
            <span className="text-[10px] text-gray-400 w-20 truncate shrink-0">
              {s.sector}
            </span>
            <div className="flex-1 h-4 bg-gray-800 rounded overflow-hidden min-w-0">
              <div
                className={clsx(
                  "h-full rounded transition-all",
                  (s.score || 0) > 70
                    ? "bg-emerald-500"
                    : (s.score || 0) > 40
                      ? "bg-amber-500/80"
                      : "bg-gray-600",
                )}
                style={{ width: `${Math.min(s.score || 0, 100)}%` }}
              />
            </div>
            <span className="text-[10px] font-mono text-gray-300 w-8 text-right shrink-0">
              {s.score ?? 0}
            </span>
          </div>
        ))}
      </div>
    </Panel>
  );
}

// ============================================================
// CRASH PROTOCOL
// ============================================================
function CrashProtocol({ macroData }) {
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

  const handleToggle = async (key) => {
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
    <Panel className="h-full">
      <PanelTitle>Crash Protocol</PanelTitle>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[9px] text-gray-500">
          {armedCount} armed triggers
        </span>
        <span
          className={clsx(
            "ml-auto text-[9px] px-1.5 py-0.5 rounded font-mono font-bold",
            isTriggered
              ? "bg-red-500/20 text-red-400 animate-pulse"
              : "bg-emerald-500/20 text-emerald-400",
          )}
        >
          {isTriggered ? "TRIGGERED" : "CLEAR"}
        </span>
      </div>
      <div className="text-[9px] text-gray-500 mb-1.5">
        protocol {isTriggered ? "ACTIVE" : "STANDBY"}
      </div>
      <div className="space-y-1.5">
        {triggers.map((t) => (
          <div key={t.key} className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <div
                className={clsx(
                  "w-1.5 h-1.5 rounded-full",
                  t.active && armed[t.key]
                    ? "bg-red-500 animate-pulse"
                    : armed[t.key]
                      ? "bg-emerald-500"
                      : "bg-gray-600",
                )}
              />
              <span
                className={clsx(
                  "text-[9px]",
                  t.active && armed[t.key]
                    ? "text-red-400 font-bold"
                    : "text-gray-400",
                )}
              >
                {t.active && armed[t.key] ? `\u25B6 ${t.label}` : t.label}
              </span>
            </div>
            <span
              className={clsx(
                "text-[8px] px-1 py-0.5 rounded font-bold font-mono",
                t.active && armed[t.key]
                  ? "bg-red-500/20 text-red-400"
                  : armed[t.key]
                    ? "text-emerald-400"
                    : "text-gray-600",
              )}
            >
              {t.active && armed[t.key]
                ? "TRIGGERED"
                : armed[t.key]
                  ? "CLEAR"
                  : "OFF"}
            </span>
          </div>
        ))}
      </div>
    </Panel>
  );
}

// ============================================================
// AGENT CONSENSUS (mockup: Scanner, Analyst, Risk Mgr, Strategist, Memory IQ)
// ============================================================
function getFallbackAgents(regimeState) {
  const r =
    regimeState === "RED"
      ? "RED"
      : regimeState === "GREEN"
        ? "GREEN"
        : "YELLOW";
  return [
    { name: "Scanner", vote: r, confidence: 92 },
    { name: "Analyst", vote: r, confidence: 88 },
    { name: "Risk Mgr", vote: r, confidence: 85 },
    {
      name: "Strategist",
      vote: r === "RED" ? "RED" : "YELLOW",
      confidence: 72,
    },
  ];
}

function AgentConsensus({ memoryData, regimeState }) {
  const raw =
    memoryData?.data?.agent_rankings || memoryData?.agent_rankings || [];
  const agents = raw.length ? raw : getFallbackAgents(regimeState);
  const memoryIq = memoryData?.data?.memory_iq ?? memoryData?.memory_iq ?? 847;

  return (
    <Panel className="h-full">
      <PanelTitle>Agent Consensus</PanelTitle>
      <div className="space-y-1.5">
        {agents.map((a, i) => (
          <div
            key={a.name || i}
            className="flex items-center justify-between text-[10px]"
          >
            <span className="text-gray-400 w-16 truncate">{a.name}</span>
            <span
              className={clsx(
                "font-mono font-bold",
                a.vote === "GREEN"
                  ? "text-emerald-400"
                  : REGIME_COLORS[a.vote]?.text || "text-gray-400",
              )}
            >
              {a.vote} {a.confidence ?? ""}
              {a.confidence != null ? "%" : ""}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-2 pt-1.5 border-t border-gray-700/30 text-[10px] text-gray-500">
        Memory IQ{" "}
        <span className="text-emerald-400 font-mono font-bold">
          {memoryIq} (G)
        </span>
      </div>
    </Panel>
  );
}

// ============================================================
// FOOTER TICKER
// ============================================================
function FooterTicker({
  marketData,
  regimeState,
  biasMultiplier,
  onBiasChange,
}) {
  const tickers = ["SPY", "QQQ", "DIA", "VIX", "IWM"];
  const rc = REGIME_COLORS[regimeState] || REGIME_COLORS.YELLOW;
  const fallbackPrices = {
    SPY: 598.42,
    QQQ: 518.73,
    DIA: 441.2,
    VIX: 14.2,
    IWM: 226.84,
  };
  const fallbackChanges = {
    SPY: 0.34,
    QQQ: 0.52,
    DIA: 0.18,
    VIX: -2.31,
    IWM: 0.67,
  };

  return (
    <div className="bg-[#0B0E14] border-t border-gray-800/50 px-4 py-2 flex items-center justify-between gap-4 shrink-0">
      <div className="flex items-center gap-3 shrink-0">
        <div className="flex items-center gap-2 min-w-[140px]">
          <span className="text-[10px] text-gray-500 font-semibold whitespace-nowrap">
            Bias Multiplier
          </span>
          <input
            type="range"
            min="0"
            max="5"
            step="0.1"
            value={biasMultiplier ?? 1.5}
            onChange={(e) => onBiasChange?.(parseFloat(e.target.value))}
            className="flex-1 h-1.5 accent-cyan-500 min-w-[60px] max-w-[80px]"
          />
          <span className="text-[10px] font-mono text-cyan-400 w-8 text-right">
            {(biasMultiplier ?? 1.5).toFixed(1)}
          </span>
        </div>
        <div className="w-px h-4 bg-gray-700/50" />
      </div>
      <div className="flex items-center gap-4 overflow-x-auto">
        {tickers.map((t) => {
          const d = marketData?.indices?.[t] || marketData?.[t] || {};
          const price = d.price ?? fallbackPrices[t];
          const change = d.change_pct ?? d.change ?? fallbackChanges[t] ?? 0;
          return (
            <div
              key={t}
              className="flex items-center gap-1 text-[10px] shrink-0"
            >
              <span className="text-gray-500 font-semibold">{t}</span>
              <span className="text-white font-mono">
                {price != null ? price.toFixed(2) : "—"}
              </span>
              <span
                className={clsx(
                  "font-mono",
                  change >= 0 ? "text-emerald-400" : "text-red-400",
                )}
              >
                {change >= 0 ? "+" : ""}
                {change?.toFixed(2)}%
              </span>
            </div>
          );
        })}
      </div>
      <span
        className={clsx("text-[10px] font-bold font-mono shrink-0", rc.text)}
      >
        REGIME: {regimeState}
      </span>
    </div>
  );
}

// ============================================================
// MAIN PAGE COMPONENT
// ============================================================
export default function MarketRegime() {
  // --- Specialized API Hooks ---
  const {
    data: regimeData,
    loading: regimeLoading,
    error: regimeError,
  } = useRegimeState();
  const { data: macroData } = useMacroState();
  const { data: paramsData, refetch: refetchParams } = useRegimeParams();
  const { data: backtestData } = useRegimePerformance();
  const { data: sectorsData } = useSectorRotation();
  const { data: transitionData } = useRegimeTransitions();

  // --- Additional API Hooks ---
  const { data: scanData } = useApi("openclaw/scan", { pollIntervalMs: 30000 });
  const { data: memoryData } = useApi("openclaw/memory", {
    pollIntervalMs: 30000,
  });
  const { data: marketData } = useApi("market", { pollIntervalMs: 5000 });
  const { data: riskScore } = useApi("risk/risk-score", {
    pollIntervalMs: 15000,
  });
  const { data: whaleFlow } = useApi("openclaw/whale-flow", {
    pollIntervalMs: 20000,
  });

  // --- Local State ---
  const [timeframe, setTimeframe] = useState("1D");
  const [biasMultiplier, setBiasMultiplier] = useState(1.5);

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

  // Risk score calculations
  const riskScoreVal = riskScore?.score || 0;
  const riskColor =
    riskScoreVal > 70
      ? "text-red-400"
      : riskScoreVal > 40
        ? "text-amber-400"
        : "text-emerald-400";
  const riskLabel =
    riskScoreVal > 70
      ? "critical risk"
      : riskScoreVal > 40
        ? "elevated"
        : "healthy";
  const riskLabelColor =
    riskScoreVal > 70
      ? "bg-red-500/20 text-red-400"
      : riskScoreVal > 40
        ? "bg-amber-500/20 text-amber-400"
        : "bg-emerald-500/20 text-emerald-400";

  // Crash proto status
  const crashTriggered = (macroData?.vix || 0) > 25;

  // --- Loading ---
  if (regimeLoading && !regimeData) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-cyan-400 animate-pulse text-lg font-mono">
          Loading Regime Intelligence...
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full -m-6">
      {/* ============ HEADER BAR (mockup: center title, regime badge, Risk Score, timeframes) ============ */}
      <div className="px-6 py-3 border-b border-gray-800/50 flex items-center justify-between flex-wrap gap-2 bg-[#0A0E17]">
        <div className="flex-1" />
        <div className="flex items-center gap-3 flex-1 justify-center">
          <h1 className="text-xl font-bold text-white tracking-tight">
            Market Regime
          </h1>
          <span
            className={clsx(
              "inline-flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-sm font-black tracking-wider text-white",
              currentRegime === "GREEN"
                ? "bg-emerald-600"
                : currentRegime === "RED"
                  ? "bg-red-600"
                  : currentRegime === "RED_RECOVERY"
                    ? "bg-orange-600"
                    : "bg-amber-600",
            )}
          >
            {currentRegime}
            <span className="text-xs font-mono opacity-90">
              {(regimeData?.hmm_confidence != null
                ? regimeData.hmm_confidence * 100
                : 87
              ).toFixed(0)}
              %
            </span>
          </span>
        </div>
        <div className="flex items-center gap-3 flex-1 justify-end">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-400 font-medium">Risk Score:</span>
            <span className={clsx("font-mono font-bold", riskColor)}>
              {riskScore?.score ?? 34}
            </span>
            <span
              className={clsx(
                "px-2 py-0.5 rounded text-[10px] font-medium",
                riskLabelColor,
              )}
            >
              {riskLabel}
            </span>
          </div>
          <div className="flex bg-gray-800/50 rounded border border-gray-700/30 overflow-hidden">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={clsx(
                  "px-3 py-1 text-[10px] font-bold transition-colors",
                  timeframe === tf
                    ? "bg-[#00D9FF]/20 text-[#00D9FF]"
                    : "text-gray-500 hover:text-white",
                )}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ============ KPI STRIP ============ */}
      <div className="px-4 py-2 border-b border-gray-800/30 bg-[#0A0E17]">
        <div className="grid grid-cols-10 gap-1.5">
          <KpiCard
            label="VIX"
            value={
              macroData?.vix?.toFixed(1) ??
              regimeData?.vix?.toFixed(1) ??
              "14.2"
            }
            color={
              (macroData?.vix ?? 14.2) > 25
                ? "text-red-400"
                : (macroData?.vix ?? 14.2) > 18
                  ? "text-amber-400"
                  : "text-emerald-400"
            }
          />
          <KpiCard
            label="HY Spread"
            value={macroData?.hy_spread?.toFixed(2) ?? "3.45"}
            unit="bps"
            color={
              (macroData?.hy_spread ?? 3.45) > 5
                ? "text-red-400"
                : "text-emerald-400"
            }
          />
          <KpiCard
            label="Yield Curve"
            value={
              macroData?.yield_curve?.toFixed(2) ??
              regimeData?.macro_context?.yield_curve?.toFixed(2) ??
              "0.82"
            }
            unit="%"
            color={
              (macroData?.yield_curve ?? 0.82) < 0
                ? "text-red-400"
                : "text-emerald-400"
            }
          />
          <KpiCard
            label="Fear & Greed"
            value={macroData?.fear_greed_index ?? 68}
            color={
              (macroData?.fear_greed_index ?? 68) < 25
                ? "text-red-400"
                : (macroData?.fear_greed_index ?? 68) > 75
                  ? "text-emerald-400"
                  : "text-amber-400"
            }
          />
          <KpiCard
            label="Hurst"
            value={regimeData?.hurst?.toFixed(3) ?? "0.623"}
            color={
              (regimeData?.hurst ?? 0.623) > 0.5
                ? "text-cyan-400"
                : "text-purple-400"
            }
          />
          <KpiCard
            label="VELEZ SLAM"
            value={macroData?.velez_score ?? scanData?.velez_breadth ?? "—"}
            color="text-purple-400"
          />
          <KpiCard
            label="Oscillator"
            value={macroData?.oscillator?.toFixed(2) ?? "0.74"}
            color="text-purple-400"
          />
          <KpiCard
            label="Bias Mult"
            value={macroData?.bias?.toFixed(2) ?? biasMultiplier.toFixed(2)}
            color="text-amber-400"
          />
          <KpiCard
            label="Risk Score"
            value={riskScore?.score ?? 34}
            color={
              (riskScore?.score ?? 34) > 70
                ? "text-red-400"
                : (riskScore?.score ?? 34) > 40
                  ? "text-amber-400"
                  : "text-emerald-400"
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
      <div className="flex-1 px-4 py-2 overflow-y-auto bg-[#0A0E17]">
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
              macroData={macroData}
              regimeData={regimeData}
              timeframe={timeframe}
            />
          </div>

          {/* ROW 2: Params (4 cols) + Performance (4 cols) + Sector (4 cols) */}
          <div className="col-span-4">
            <RegimeParamPanel
              paramsData={paramsData}
              regimeState={currentRegime}
              onOverride={() => refetchParams()}
            />
          </div>
          <div className="col-span-4">
            <PerformanceMatrix backtestData={backtestData} />
          </div>
          <div className="col-span-4">
            <SectorRotation sectorsData={sectorsData} />
          </div>

          {/* ROW 3: Regime Flow (6 cols) + Crash Protocol (3 cols) + Agent Consensus (3 cols) */}
          <div className="col-span-6">
            <RegimeFlowDiagram
              regimeState={currentRegime}
              paramsData={paramsData}
            />
          </div>
          <div className="col-span-3">
            <CrashProtocol macroData={macroData} />
          </div>
          <div className="col-span-3">
            <AgentConsensus
              memoryData={memoryData}
              regimeState={currentRegime}
            />
          </div>

          {/* ROW 4: Transition History (full width) */}
          <div className="col-span-12">
            <TransitionHistory
              transitionData={transitionData}
              regimeData={regimeData}
            />
          </div>
        </div>
      </div>

      {/* ============ FOOTER TICKER (mockup: Bias slider + ticker in same strip) ============ */}
      <FooterTicker
        marketData={marketData}
        regimeState={currentRegime}
        biasMultiplier={biasMultiplier}
        onBiasChange={handleBiasChange}
      />

      {/* Error toast */}
      {regimeError && (
        <div className="fixed bottom-12 right-4 bg-red-900/90 border border-red-500/50 text-red-200 text-xs px-4 py-2 rounded-lg shadow-lg z-50">
          Regime API error: {regimeError.message || "Connection failed"}
        </div>
      )}
    </div>
  );
}
