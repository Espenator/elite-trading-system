// frontend-v2/src/pages/MarketRegime.jsx
// Market Regime — AI Brain's Macro Intelligence Center (Page 10/15)
// Route: /market-regime

import React, { useState, useCallback, useMemo, useEffect } from "react";
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
  useMemoryIntelligence,
  useWhaleFlow,
  useRiskGauges,
  useBridgeHealth,
  postBiasOverride,
} from "../hooks/useApi";
import { useApi } from "../hooks/useApi";
import { getApiUrl, getAuthHeaders, WS_CHANNELS } from "../config/api";
import ws from "../services/websocket";
import log from "@/utils/logger";

// ============================================================
// CONSTANTS — Aurora theme; GREEN #00FF00 / RED #FF4444 per spec
// ============================================================
const REGIME_COLORS = {
  GREEN: {
    bg: "bg-[#00FF00]/90",
    text: "text-[#00FF00]",
    hex: "#00FF00",
    hexBright: "#00FF00",
    bgFaint: "bg-[#00FF00]/10",
    border: "border-[#00FF00]/40",
    badgeBg: "bg-[#00CC00]",
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
    bg: "bg-[#FF4444]/90",
    text: "text-[#FF4444]",
    hex: "#FF4444",
    hexBright: "#FF4444",
    bgFaint: "bg-[#FF4444]/10",
    border: "border-[#FF4444]/40",
    badgeBg: "bg-[#CC3333]",
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
// REGIME STATE MACHINE — cells clickable to show details for that regime period
// ============================================================
function RegimeStateMachine({ currentState, regimeData, selectedState, onSelectState }) {
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
              <button
                type="button"
                key={s}
                onClick={() => onSelectState?.(s)}
                className={clsx(
                  "rounded-lg px-2 py-3 border text-center transition-all cursor-pointer hover:opacity-90",
                  isCurrent
                    ? clsx(rc.bg, "text-white border-transparent")
                    : "border-gray-700/30 bg-gray-800/30 text-gray-500",
                  selectedState === s && "ring-2 ring-cyan-400 ring-offset-1 ring-offset-[#111827]",
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
              </button>
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
      {selectedState && (
        <div className="mt-2 pt-2 border-t border-gray-700/30 text-[10px] text-gray-400">
          <span className="text-slate-500">Details for </span>
          <span className={clsx("font-bold", REGIME_COLORS[selectedState]?.text || "text-gray-400")}>
            {selectedState}
          </span>
          {regimeData?.transitions && (
            <div className="mt-1">
              Last transition:{" "}
              {regimeData.transitions.find((t) => t.to === selectedState)?.timestamp ?? "\u2014"}
            </div>
          )}
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
    if (macroData?.vix_history?.length) {
      return macroData.vix_history.map((d) => ({
        time:
          typeof d.time === "string"
            ? d.time
            : format(new Date(d.time * 1000), "MM/dd"),
        vix: d.value,
        spy: d.spy,
      }));
    }
    return [];
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
        {chartData.length ? (
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
        ) : (
          <div className="h-full flex items-center justify-center text-gray-500 text-sm font-mono">
            No VIX/macro history
          </div>
        )}
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

  const currentParams = paramsData ?? {};

  const handleSaveParams = async () => {
    setSaving(true);
    setSaveStatus(null);
    const payload = {
      regime: regimeState,
      risk_pct:
        localParams.risk_pct ?? paramsData?.risk_pct,
      max_positions:
        localParams.max_positions ?? paramsData?.max_positions,
      kelly_mult:
        localParams.kelly_mult ?? paramsData?.kelly_mult,
      signal_mult:
        localParams.signal_mult ?? paramsData?.signal_mult,
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

  const riskVal = paramsData?.risk_pct ?? localParams.risk_pct;
  const maxPosVal = paramsData?.max_positions ?? localParams.max_positions;
  const kellyVal = paramsData?.kelly_mult ?? localParams.kelly_mult;
  const signalVal = paramsData?.signal_mult ?? localParams.signal_mult;

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
                value={localParams[p.key] ?? p.val ?? ""}
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
              <span className="text-white font-mono">{riskVal ?? "\u2014"}</span>
          </div>
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-gray-500">Max Positions</span>
            <div className="flex items-center gap-2">
              <span className="text-white font-mono">{maxPosVal ?? "\u2014"}</span>
              <span className="text-gray-600 text-[9px]">Fuel</span>
              <div className="flex gap-0.5">
                {[...Array(6)].map((_, i) => (
                  <div
                    key={i}
                    className={clsx(
                      "w-1.5 h-2.5 rounded-sm",
                      typeof maxPosVal === "number" && i < maxPosVal
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
              <span className="text-white font-mono">{kellyVal ?? "\u2014"}</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-gray-500">Signal Mult</span>
              <span className="text-white font-mono">{signalVal ?? "\u2014"}</span>
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
                const val = backtestData?.[r]?.[m.key];
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
  const kellyMult = paramsData?.kelly_mult ?? "\u2014";
  const signalMult = paramsData?.signal_mult ?? "\u2014";
  const riskPct = paramsData?.risk_pct;
  const isRed = regimeState === "RED";
  const maxPos = paramsData?.max_positions ?? 0;

  const nodes = [
    { id: "regime", label: "REGIME", value: regimeState },
    { id: "sizer", label: "Sizer", value: riskPct != null ? `${riskPct}x` : "\u2014" },
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
// TRANSITION HISTORY (Time, FROM->TO, trigger, confidence, duration, P&L)
// ============================================================
function TransitionHistory({ transitionData, regimeData }) {
  const raw = transitionData?.transitions || regimeData?.transitions || [];
  const transitions = raw.slice(0, 8);

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
            {transitions.length ? transitions.map((t, i) => (
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
            )) : (
              <tr>
                <td colSpan={6} className="py-4 text-center text-gray-500 text-[10px]">
                  No transition history
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

// ============================================================
// SECTOR ROTATION — horizontal bars; clickable for drill-down
// ============================================================
function SectorRotation({ sectorsData, selectedSector, onSelectSector }) {
  const sectors = sectorsData?.sectors?.length
    ? sectorsData.sectors
    : sectorsData?.rankings?.length
      ? sectorsData.rankings
      : [];

  return (
    <Panel className="h-full">
      <PanelTitle>Sector Rotation</PanelTitle>
      <div className="space-y-2">
        {sectors.length ? sectors.map((s, i) => (
          <button
            type="button"
            key={s.sector || i}
            onClick={() => onSelectSector?.(s.sector)}
            className={clsx(
              "w-full flex items-center gap-2 rounded px-1 py-0.5 transition-colors text-left",
              selectedSector === s.sector ? "bg-cyan-500/10 ring-1 ring-cyan-400/50" : "hover:bg-gray-800/50",
            )}
          >
            <span className="text-[10px] text-gray-400 w-20 truncate shrink-0">
              {s.sector}
            </span>
            <div className="flex-1 h-4 bg-gray-800 rounded overflow-hidden min-w-0">
              <div
                className={clsx(
                  "h-full rounded transition-all",
                  (s.score || 0) > 70
                    ? "bg-[#00FF00]/80"
                    : (s.score || 0) > 40
                      ? "bg-amber-500/80"
                      : "bg-gray-600",
                )}
                style={{ width: `${Math.min(s.score ?? 0, 100)}%` }}
              />
            </div>
            <span className="text-[10px] font-mono text-gray-300 w-8 text-right shrink-0">
              {s.score != null ? s.score : "\u2014"}
            </span>
          </button>
        )) : (
          <div className="text-[10px] text-gray-500 py-2">No sector data</div>
        )}
      </div>
      {selectedSector && (
        <div className="mt-2 pt-2 border-t border-gray-700/30 text-[10px] text-gray-400">
          Sector: <span className="text-cyan-400 font-mono">{selectedSector}</span>
          <div className="text-[9px] text-gray-500 mt-0.5">Drill-down from sectors API</div>
        </div>
      )}
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
          <button
            type="button"
            key={t.key}
            onClick={() => handleToggle(t.key)}
            className="w-full flex items-center justify-between text-left rounded px-1 py-0.5 hover:bg-gray-800/50 transition-colors"
          >
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
          </button>
        ))}
      </div>
    </Panel>
  );
}

// ============================================================
// AGENT CONSENSUS — from useMemoryIntelligence
// ============================================================
function AgentConsensus({ memoryData, regimeState }) {
  const raw =
    memoryData?.data?.agent_rankings || memoryData?.agent_rankings || [];
  const agents = raw.slice(0, 8);
  const memoryIq = memoryData?.data?.memory_iq ?? memoryData?.memory_iq;

  return (
    <Panel className="h-full">
      <PanelTitle>Agent Consensus</PanelTitle>
      <div className="space-y-1.5">
        {agents.length ? agents.map((a, i) => (
          <div
            key={a.name || i}
            className="flex items-center justify-between text-[10px]"
          >
            <span className="text-gray-400 w-16 truncate">{a.name}</span>
            <span
              className={clsx(
                "font-mono font-bold",
                a.vote === "GREEN"
                  ? "text-[#00FF00]"
                  : a.vote === "RED"
                    ? "text-[#FF4444]"
                    : REGIME_COLORS[a.vote]?.text || "text-gray-400",
              )}
            >
              {a.vote} {a.confidence != null ? `${a.confidence}%` : ""}
            </span>
          </div>
        )) : (
          <div className="text-[10px] text-gray-500 py-1">No agent data</div>
        )}
      </div>
      <div className="mt-2 pt-1.5 border-t border-gray-700/30 text-[10px] text-gray-500">
        Memory IQ{" "}
        <span className="text-[#00FF00] font-mono font-bold">
          {memoryIq != null ? `${memoryIq} (G)` : "\u2014"}
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
            value={biasMultiplier ?? 1}
            onChange={(e) => onBiasChange?.(parseFloat(e.target.value))}
            className="flex-1 h-1.5 accent-cyan-500 min-w-[60px] max-w-[80px]"
          />
          <span className="text-[10px] font-mono text-cyan-400 w-8 text-right">
            {(biasMultiplier ?? 1).toFixed(1)}
          </span>
        </div>
        <div className="w-px h-4 bg-gray-700/50" />
      </div>
      <div className="flex items-center gap-4 overflow-x-auto">
        {tickers.map((t) => {
          const d = marketData?.indices?.[t] || marketData?.[t] || {};
          const price = d.price;
          const change = d.change_pct ?? d.change ?? null;
          return (
            <div
              key={t}
              className="flex items-center gap-1 text-[10px] shrink-0"
            >
              <span className="text-gray-500 font-semibold">{t}</span>
              <span className="text-white font-mono">
                {price != null ? price.toFixed(2) : "\u2014"}
              </span>
              <span
                className={clsx(
                  "font-mono",
                  change != null
                    ? change >= 0
                      ? "text-[#00FF00]"
                      : "text-[#FF4444]"
                    : "text-gray-500",
                )}
              >
                {change != null
                  ? `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`
                  : "\u2014"}
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
  // --- All 10 specialized hooks (spec) ---
  const {
    data: regimeData,
    loading: regimeLoading,
    error: regimeError,
    refetch: refetchRegime,
  } = useRegimeState();
  const { data: macroData, refetch: refetchMacro } = useMacroState();
  const { data: paramsData, refetch: refetchParams } = useRegimeParams();
  const { data: backtestData } = useRegimePerformance();
  const { data: sectorsData } = useSectorRotation();
  const { data: transitionData } = useRegimeTransitions();
  const { data: memoryData } = useMemoryIntelligence(30000);
  const { data: whaleFlow } = useWhaleFlow(20000);
  const { data: riskGauges } = useRiskGauges(15000);
  const { data: bridgeHealth } = useBridgeHealth(30000);

  // --- Additional ---
  const { data: scanData } = useApi("openclaw/scan", { pollIntervalMs: 30000 });
  const { data: marketData, refetch: refetchMarket } = useApi("market", { pollIntervalMs: 5000 });
  const { data: riskScore } = useApi("risk/risk-score", { pollIntervalMs: 15000 });

  // --- WebSocket live updates for regime changes ---
  useEffect(() => {
    const unsubs = [
      ws.on(WS_CHANNELS.macro, () => { refetchRegime(); refetchMacro(); }),
      ws.on(WS_CHANNELS.market, () => refetchMarket()),
    ];
    return () => unsubs.forEach((fn) => fn());
  }, [refetchRegime, refetchMacro, refetchMarket]);

  // --- Local State ---
  const [timeframe, setTimeframe] = useState("1D");
  const [biasMultiplier, setBiasMultiplier] = useState(1);
  const [selectedState, setSelectedState] = useState(null);
  const [selectedSector, setSelectedSector] = useState(null);
  const [overrideActive, setOverrideActive] = useState(false);
  const [overrideExpiresAt, setOverrideExpiresAt] = useState(null);
  const [overrideCountdown, setOverrideCountdown] = useState(null);

  useEffect(() => {
    if (!overrideExpiresAt) {
      setOverrideCountdown(null);
      return;
    }
    const tick = () => {
      const left = Math.max(0, Math.ceil((overrideExpiresAt - Date.now()) / 1000));
      setOverrideCountdown(left);
      if (left <= 0) setOverrideActive(false);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [overrideExpiresAt]);

  // Derived
  const currentRegime = regimeData?.state || paramsData?.regime || "YELLOW";
  const rc = REGIME_COLORS[currentRegime] || REGIME_COLORS.YELLOW;

  // --- Bias Override Handler — Manual Regime Override + 15 min countdown ---
  const OVERRIDE_DURATION_MS = 15 * 60 * 1000;
  const handleBiasChange = useCallback(async (val) => {
    setBiasMultiplier(val);
    try {
      await postBiasOverride(val);
      setOverrideActive(true);
      setOverrideExpiresAt(Date.now() + OVERRIDE_DURATION_MS);
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
                ? "bg-[#00CC00]"
                : currentRegime === "RED"
                  ? "bg-[#CC3333]"
                  : currentRegime === "RED_RECOVERY"
                    ? "bg-orange-600"
                    : "bg-amber-600",
            )}
          >
            {currentRegime}
            <span className="text-xs font-mono opacity-90">
              {regimeData?.hmm_confidence != null
                ? `${(regimeData.hmm_confidence * 100).toFixed(0)}%`
                : "\u2014"}
            </span>
          </span>
        </div>
        <div className="flex items-center gap-3 flex-1 justify-end">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-400 font-medium">Risk Score:</span>
            <span className={clsx("font-mono font-bold", riskColor)}>
              {riskScore?.score ?? "\u2014"}
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

      {/* Manual Regime Override banner + countdown */}
      {overrideActive && (
        <div className="px-6 py-2 bg-[#00FF00]/10 border-b border-[#00FF00]/30 flex items-center justify-between">
          <span className="text-sm font-bold text-[#00FF00]">
            Manual Regime Override
          </span>
          <span className="text-xs font-mono text-gray-300">
            {overrideCountdown != null && overrideCountdown > 0
              ? `Expires in ${Math.floor(overrideCountdown / 60)}:${String(overrideCountdown % 60).padStart(2, "0")}`
              : "Active"}
          </span>
        </div>
      )}

      {/* ============ KPI STRIP ============ */}
      <div className="px-4 py-2 border-b border-gray-800/30 bg-[#0A0E17]">
        <div className="grid grid-cols-10 gap-1.5">
          <KpiCard
            label="VIX"
            value={
              macroData?.vix != null
                ? macroData.vix.toFixed(1)
                : regimeData?.vix != null
                  ? regimeData.vix.toFixed(1)
                  : "\u2014"
            }
            color={
              (macroData?.vix ?? regimeData?.vix) != null
                ? (macroData?.vix ?? regimeData?.vix) > 25
                  ? "text-[#FF4444]"
                  : (macroData?.vix ?? regimeData?.vix) > 18
                    ? "text-amber-400"
                    : "text-[#00FF00]"
                : "text-gray-400"
            }
          />
          <KpiCard
            label="HY Spread"
            value={macroData?.hy_spread != null ? macroData.hy_spread.toFixed(2) : "\u2014"}
            unit="bps"
            color={
              macroData?.hy_spread != null
                ? macroData.hy_spread > 5
                  ? "text-[#FF4444]"
                  : "text-[#00FF00]"
                : "text-gray-400"
            }
          />
          <KpiCard
            label="Yield Curve"
            value={
              macroData?.yield_curve != null
                ? macroData.yield_curve.toFixed(2)
                : regimeData?.macro_context?.yield_curve != null
                  ? regimeData.macro_context.yield_curve.toFixed(2)
                  : "\u2014"
            }
            unit="%"
            color={
              (macroData?.yield_curve ?? regimeData?.macro_context?.yield_curve) != null
                ? (macroData?.yield_curve ?? regimeData?.macro_context?.yield_curve) < 0
                  ? "text-[#FF4444]"
                  : "text-[#00FF00]"
                : "text-gray-400"
            }
          />
          <KpiCard
            label="Fear & Greed"
            value={macroData?.fear_greed_index ?? "\u2014"}
            color={
              macroData?.fear_greed_index != null
                ? macroData.fear_greed_index < 25
                  ? "text-[#FF4444]"
                  : macroData.fear_greed_index > 75
                    ? "text-[#00FF00]"
                    : "text-amber-400"
                : "text-gray-400"
            }
          />
          <KpiCard
            label="Hurst"
            value={regimeData?.hurst != null ? regimeData.hurst.toFixed(3) : "\u2014"}
            color="text-cyan-400"
          />
          <KpiCard
            label="VELEZ SLAM"
            value={macroData?.velez_score ?? scanData?.velez_breadth ?? "\u2014"}
            color="text-purple-400"
          />
          <KpiCard
            label="Oscillator"
            value={macroData?.oscillator != null ? macroData.oscillator.toFixed(2) : "\u2014"}
            color="text-purple-400"
          />
          <KpiCard
            label="Bias Mult"
            value={
              macroData?.bias != null
                ? macroData.bias.toFixed(2)
                : biasMultiplier != null
                  ? biasMultiplier.toFixed(2)
                  : "\u2014"
            }
            color="text-amber-400"
          />
          <KpiCard
            label="Risk Score"
            value={riskScore?.score ?? "\u2014"}
            color={
              riskScore?.score != null
                ? riskScore.score > 70
                  ? "text-[#FF4444]"
                  : riskScore.score > 40
                    ? "text-amber-400"
                    : "text-[#00FF00]"
                : "text-gray-400"
            }
          />
          <KpiCard
            label="Crash Proto"
            value={crashTriggered ? "TRIGGERED" : "CLEAR"}
            color={crashTriggered ? "text-[#FF4444]" : "text-[#00FF00]"}
            alert={(macroData?.vix ?? 0) > 40}
          />
        </div>
        {/* Risk Gauges & Bridge Health from hooks */}
        {(riskGauges != null || bridgeHealth != null) && (
          <div className="mt-2 pt-2 border-t border-gray-700/30 flex flex-wrap gap-2 text-[9px] text-gray-500">
            {riskGauges != null && (
              <span className="font-mono">
                Gauges: {typeof riskGauges === "object" ? JSON.stringify(riskGauges).slice(0, 60) + "…" : String(riskGauges)}
              </span>
            )}
            {bridgeHealth != null && (
              <span className="font-mono">
                Bridge: {typeof bridgeHealth === "object" ? (bridgeHealth.ok ? "OK" : "Degraded") : String(bridgeHealth)}
              </span>
            )}
          </div>
        )}
      </div>

      {/* ============ MAIN GRID — 3-col layout: 20% | 40% | 40% = 2 | 5 | 5 (of 12) ============ */}
      <div className="flex-1 px-4 py-2 overflow-y-auto bg-[#0A0E17]">
        <div className="grid grid-cols-12 gap-2">
          {/* LEFT (20%): State Machine + Params */}
          <div className="col-span-2 flex flex-col gap-2">
            <RegimeStateMachine
              currentState={currentRegime}
              regimeData={regimeData}
              selectedState={selectedState}
              onSelectState={setSelectedState}
            />
            <RegimeParamPanel
              paramsData={paramsData}
              regimeState={currentRegime}
              onOverride={() => refetchParams()}
            />
          </div>
          {/* CENTER (40%): VIX Chart, Regime Flow, Transition History */}
          <div className="col-span-5 flex flex-col gap-2">
            <VixMacroChart
              macroData={macroData}
              regimeData={regimeData}
              timeframe={timeframe}
            />
            <RegimeFlowDiagram
              regimeState={currentRegime}
              paramsData={paramsData}
            />
            <TransitionHistory
              transitionData={transitionData}
              regimeData={regimeData}
            />
          </div>
          {/* RIGHT (40%): Performance, Sector, Crash, Agent Consensus */}
          <div className="col-span-5 flex flex-col gap-2">
            <PerformanceMatrix backtestData={backtestData} />
            <SectorRotation
              sectorsData={sectorsData}
              selectedSector={selectedSector}
              onSelectSector={setSelectedSector}
            />
            <CrashProtocol macroData={macroData} />
            <AgentConsensus
              memoryData={memoryData}
              regimeState={currentRegime}
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
