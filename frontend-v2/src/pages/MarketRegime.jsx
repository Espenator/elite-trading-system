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
import { getApiUrl } from "../config/api";

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
      className={`bg-[#111827] rounded px-3 py-2 border ${alert ? "border-red-500/50 animate-pulse" : "border-gray-700/30"}`}
    >
      <div className="text-[10px] text-gray-500 uppercase tracking-wider truncate">
        {label}
      </div>
      <div
        className={`text-lg font-mono font-bold ${color || "text-cyan-400"} leading-tight`}
      >
        {value ?? "\u2014"}
        {unit && <span className="text-xs text-gray-500 ml-0.5">{unit}</span>}
      </div>
    </div>
  );
}

// --- Regime Badge ---
function RegimeBadge({ state, confidence, size = "lg" }) {
  const rc = REGIME_COLORS[state] || REGIME_COLORS.YELLOW;
  const sizeClasses =
    size === "lg" ? "px-6 py-2 text-2xl" : "px-3 py-1 text-sm";
  return (
    <div
      className={`inline-flex items-center gap-2 rounded-lg font-black tracking-widest ${rc.bg} text-white ${sizeClasses} animate-pulse`}
    >
      <span className="w-3 h-3 rounded-full bg-white/40 animate-ping" />
      {state}
      {confidence != null && (
        <span className="text-sm font-mono opacity-80">
          {(confidence * 100).toFixed(0)}%
        </span>
      )}
    </div>
  );
}

// --- Regime State Machine Diagram ---
function RegimeStateMachine({ currentState, regimeData }) {
  const states = ["GREEN", "YELLOW", "RED", "RED_RECOVERY"];
  const transitions = [
    { from: "GREEN", to: "YELLOW", condition: "VIX > 18" },
    { from: "YELLOW", to: "RED", condition: "VIX > 25" },
    { from: "RED", to: "RED_RECOVERY", condition: "VIX declining" },
    { from: "RED_RECOVERY", to: "GREEN", condition: "VIX < 18 sustained" },
    { from: "YELLOW", to: "GREEN", condition: "VIX < 18" },
    { from: "RED_RECOVERY", to: "RED", condition: "VIX spike" },
  ];

  return (
    <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-4 h-full">
      <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Regime State Machine
      </div>
      <div className="grid grid-cols-2 gap-3">
        {states.map((s) => {
          const rc = REGIME_COLORS[s];
          const isCurrent = currentState === s;
          return (
            <div
              key={s}
              className={`rounded-lg p-3 border-2 transition-all ${isCurrent ? `${rc.border} ${rc.bgFaint} shadow-lg shadow-${rc.hex}/20` : "border-gray-700/20 bg-gray-800/30"}`}
            >
              <div
                className={`text-xs font-bold ${isCurrent ? rc.text : "text-gray-500"}`}
              >
                {s}
              </div>
              <div className="text-[10px] text-gray-500 mt-1">
                {REGIME_PARAMS_DEFAULT[s]?.label}
              </div>
              <div className="text-[10px] text-gray-600 mt-1">
                Risk: {REGIME_PARAMS_DEFAULT[s]?.risk_pct}% | Max:{" "}
                {REGIME_PARAMS_DEFAULT[s]?.max_positions}
              </div>
              {isCurrent && (
                <div className={`mt-1 text-[10px] ${rc.text} font-semibold`}>
                  \u25CF CURRENT
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-3 space-y-1">
        <div className="text-[10px] text-gray-500 font-semibold uppercase">
          Transitions
        </div>
        {transitions.map((t, i) => (
          <div
            key={i}
            className="flex items-center gap-1 text-[10px] text-gray-500"
          >
            <span className={REGIME_COLORS[t.from]?.text}>{t.from}</span>
            <span>\u2192</span>
            <span className={REGIME_COLORS[t.to]?.text}>{t.to}</span>
            <span className="text-gray-600 ml-1">({t.condition})</span>
          </div>
        ))}
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
      height: 360,
      layout: { background: { color: "#111827" }, textColor: "#9CA3AF" },
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
      title: "GREEN",
    });
    vixSeries.createPriceLine({
      price: 25,
      color: "#F59E0B",
      lineWidth: 1,
      lineStyle: 2,
      title: "YELLOW",
    });
    vixSeries.createPriceLine({
      price: 40,
      color: "#EF4444",
      lineWidth: 1,
      lineStyle: 2,
      title: "EXTREME",
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
    <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-4 h-full">
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          VIX + Macro Overlay
        </div>
        <div className="flex items-center gap-3 text-[10px]">
          <span className="flex items-center gap-1">
            <span className="w-2 h-0.5 bg-red-500 inline-block" />
            VIX
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-0.5 bg-cyan-500 inline-block" />
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

  useEffect(() => {
    if (paramsData) setLocalParams(paramsData);
  }, [paramsData]);

  const currentParams = REGIME_PARAMS_DEFAULT[regimeState] || {};

  return (
    <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-4 h-full">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Regime Params
        </div>
        <button
          onClick={() => setEditMode(!editMode)}
          className={`text-[10px] px-2 py-0.5 rounded ${editMode ? "bg-cyan-500/20 text-cyan-400" : "bg-gray-700/50 text-gray-400"}`}
        >
          {editMode ? "EDITING" : "EDIT"}
        </button>
      </div>
      <div className="mb-3">
        <label className="text-[10px] text-gray-500 block mb-1">Override</label>
        <select
          value={overrideState}
          onChange={(e) => {
            setOverrideState(e.target.value);
            if (onOverride) onOverride(e.target.value);
          }}
          className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white"
        >
          <option value="AUTO">AUTO (HMM)</option>
          <option value="GREEN">GREEN</option>
          <option value="YELLOW">YELLOW</option>
          <option value="RED">RED</option>
        </select>
      </div>
      <div className="space-y-2">
        {[
          {
            label: "Risk %",
            key: "risk_pct",
            val: paramsData?.risk_pct ?? currentParams.risk_pct,
          },
          {
            label: "Max Positions",
            key: "max_positions",
            val: paramsData?.max_positions ?? currentParams.max_positions,
          },
          {
            label: "Kelly Mult",
            key: "kelly_mult",
            val: paramsData?.kelly_mult ?? currentParams.kelly_mult,
          },
          {
            label: "Signal Mult",
            key: "signal_mult",
            val: paramsData?.signal_mult ?? currentParams.signal_mult,
          },
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
                className="w-20 bg-gray-800 border border-gray-600 rounded px-2 py-0.5 text-xs text-white text-right font-mono"
              />
            ) : (
              <span className="text-sm font-mono text-white">{p.val}</span>
            )}
          </div>
        ))}
      </div>
      {editMode && (
        <button className="mt-3 w-full bg-cyan-600 hover:bg-cyan-700 text-white text-xs py-1.5 rounded font-semibold transition-colors">
          Save Params
        </button>
      )}
    </div>
  );
}

// --- Performance Matrix ---
function RegimePerformanceMatrix({ backtestData }) {
  const regimes = ["GREEN", "YELLOW", "RED"];
  const metrics = ["win_rate", "avg_pnl", "sharpe", "trade_count"];
  const labels = {
    win_rate: "Win Rate",
    avg_pnl: "Avg P&L",
    sharpe: "Sharpe",
    trade_count: "Trades",
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
    <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-4 h-full">
      <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Performance by Regime
      </div>
      <table className="w-full text-[11px]">
        <thead>
          <tr className="border-b border-gray-700/30">
            <th className="text-left text-gray-500 pb-1 pr-2">Metric</th>
            {regimes.map((r) => (
              <th
                key={r}
                className={`text-right pb-1 ${REGIME_COLORS[r].text}`}
              >
                {r}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {metrics.map((m) => (
            <tr key={m} className="border-b border-gray-800/50">
              <td className="text-gray-400 py-1.5 pr-2">{labels[m]}</td>
              {regimes.map((r) => {
                const val = backtestData?.[r]?.[m];
                return (
                  <td
                    key={r}
                    className={`text-right font-mono py-1.5 ${getColor(m, val)}`}
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
    <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-4 h-full">
      <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Sector Rotation
      </div>
      <div className="space-y-1.5">
        {sectors.map((s, i) => (
          <div key={s.sector || i} className="flex items-center gap-2">
            <span className="text-[10px] text-gray-400 w-16 truncate">
              {s.sector}
            </span>
            <div className="flex-1 h-4 bg-gray-800 rounded overflow-hidden">
              <div
                className={`h-full rounded ${s.score > 70 ? "bg-emerald-500" : s.score > 40 ? "bg-amber-500" : "bg-red-500"}`}
                style={{ width: `${Math.min(s.score || 0, 100)}%` }}
              />
            </div>
            <span className="text-[10px] font-mono text-gray-300 w-8 text-right">
              {s.score}
            </span>
          </div>
        ))}
        {sectors.length === 0 && (
          <div className="text-[10px] text-gray-600 text-center py-4">
            Loading sectors...
          </div>
        )}
      </div>
    </div>
  );
}

// --- Regime Flow Diagram ---
function RegimeFlowDiagram({ regimeState, paramsData }) {
  const nodes = [
    { id: "regime", label: "REGIME", value: regimeState },
    {
      id: "kelly",
      label: "Kelly Sizer",
      value: `${REGIME_PARAMS_DEFAULT[regimeState]?.kelly_mult || "?"}x`,
    },
    {
      id: "signal",
      label: "Signal Engine",
      value: `${REGIME_PARAMS_DEFAULT[regimeState]?.signal_mult || "?"}x`,
    },
    {
      id: "risk",
      label: "Risk Governor",
      value: regimeState === "RED" ? "BLOCKED" : "OPEN",
    },
    {
      id: "position",
      label: "Position Mgr",
      value: `ATR x${regimeState === "GREEN" ? "1.0" : regimeState === "YELLOW" ? "1.2" : "1.5"}`,
    },
    {
      id: "exec",
      label: "Execution",
      value: regimeState === "RED" ? "HALTED" : "ACTIVE",
    },
  ];
  const rc = REGIME_COLORS[regimeState] || REGIME_COLORS.YELLOW;

  return (
    <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-4 h-full">
      <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Regime Flow
      </div>
      <div className="flex flex-wrap items-center gap-1">
        {nodes.map((n, i) => (
          <React.Fragment key={n.id}>
            <div
              className={`rounded px-3 py-2 text-center border ${i === 0 ? `${rc.bgFaint} ${rc.border}` : "bg-gray-800/50 border-gray-700/30"}`}
            >
              <div className="text-[10px] text-gray-500">{n.label}</div>
              <div
                className={`text-xs font-mono font-bold ${i === 0 ? rc.text : n.value === "BLOCKED" || n.value === "HALTED" ? "text-red-400" : "text-white"}`}
              >
                {n.value}
              </div>
            </div>
            {i < nodes.length - 1 && (
              <span className="text-gray-600 text-xs">\u2192</span>
            )}
          </React.Fragment>
        ))}
      </div>
      <div className="mt-3 text-[10px] text-gray-500">
        Composite Scorer: Pillar 1 REGIME ={" "}
        <span className="text-cyan-400 font-mono">20/100 pts</span>
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
      label: "VIX Spike > 25",
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
    { key: "breadth_collapse", label: "Breadth Collapse", active: false },
    { key: "spy_drop", label: "SPY Drop > 2%", active: false },
  ];

  return (
    <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-4 h-full">
      <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Crash Protocol
        <span
          className={`ml-2 px-1.5 py-0.5 rounded text-[10px] font-mono ${triggers.some((t) => t.active && armed[t.key]) ? "bg-red-500/20 text-red-400 animate-pulse" : "bg-emerald-500/20 text-emerald-400"}`}
        >
          {triggers.some((t) => t.active && armed[t.key])
            ? "TRIGGERED"
            : "CLEAR"}
        </span>
      </div>
      <div className="space-y-2">
        {triggers.map((t) => (
          <div key={t.key} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${t.active && armed[t.key] ? "bg-red-500 animate-pulse" : armed[t.key] ? "bg-emerald-500" : "bg-gray-600"}`}
              />
              <span className="text-[10px] text-gray-400">{t.label}</span>
            </div>
            <button
              onClick={() => setArmed({ ...armed, [t.key]: !armed[t.key] })}
              className={`text-[9px] px-1.5 py-0.5 rounded font-semibold ${armed[t.key] ? "bg-emerald-500/20 text-emerald-400" : "bg-gray-700/50 text-gray-500"}`}
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
function AgentConsensusPanel({ memoryData }) {
  const agents =
    memoryData?.data?.agent_rankings || memoryData?.agent_rankings || [];
  return (
    <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-4 h-full">
      <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Agent Consensus
      </div>
      {(memoryData?.data?.memory_iq || memoryData?.memory_iq) && (
        <div className="mb-2 text-[10px] text-gray-500">
          Memory IQ:{" "}
          <span className="text-purple-400 font-mono">
            {memoryData.memory_iq}
          </span>
        </div>
      )}
      <div className="space-y-1.5">
        {agents.map((a, i) => (
          <div
            key={a.name || i}
            className="flex items-center justify-between text-[10px]"
          >
            <span className="text-gray-400 truncate w-20">{a.name}</span>
            <span
              className={`font-mono ${REGIME_COLORS[a.vote]?.text || "text-gray-400"}`}
            >
              {a.vote}
            </span>
            <span className="text-gray-500 font-mono w-10 text-right">
              {a.confidence}%
            </span>
          </div>
        ))}
        {agents.length === 0 && (
          <div className="text-[10px] text-gray-600 text-center py-2">
            No agent data
          </div>
        )}
      </div>
    </div>
  );
}

// --- Transition History ---
function TransitionHistory({ regimeData }) {
  const transitions = regimeData?.transitions || [];
  return (
    <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-4">
      <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Regime Transition History
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px]">
          <thead>
            <tr className="border-b border-gray-700/30 text-gray-500">
              <th className="text-left py-1 pr-3">Time</th>
              <th className="text-left py-1 pr-3">From</th>
              <th className="text-left py-1 pr-3">To</th>
              <th className="text-left py-1 pr-3">Trigger</th>
              <th className="text-right py-1 pr-3">Conf</th>
              <th className="text-right py-1 pr-3">Duration</th>
              <th className="text-right py-1">P&L Impact</th>
            </tr>
          </thead>
          <tbody>
            {transitions.slice(0, 30).map((t, i) => (
              <tr
                key={i}
                className="border-b border-gray-800/30 hover:bg-gray-800/20"
              >
                <td className="py-1.5 pr-3 text-gray-400 font-mono">
                  {t.timestamp}
                </td>
                <td
                  className={`py-1.5 pr-3 font-semibold ${REGIME_COLORS[t.from]?.text || "text-gray-400"}`}
                >
                  {t.from}
                </td>
                <td
                  className={`py-1.5 pr-3 font-semibold ${REGIME_COLORS[t.to]?.text || "text-gray-400"}`}
                >
                  {t.to}
                </td>
                <td className="py-1.5 pr-3 text-gray-400">{t.trigger}</td>
                <td className="py-1.5 pr-3 text-right text-gray-300 font-mono">
                  {t.confidence}%
                </td>
                <td className="py-1.5 pr-3 text-right text-gray-400 font-mono">
                  {t.duration}
                </td>
                <td
                  className={`py-1.5 text-right font-mono ${(t.pnl_impact || 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}
                >
                  {t.pnl_impact != null ? `$${t.pnl_impact}` : "\u2014"}
                </td>
              </tr>
            ))}
            {transitions.length === 0 && (
              <tr>
                <td colSpan={7} className="text-center py-4 text-gray-600">
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
    <div className="bg-[#0D1117] border-t border-gray-800/50 px-4 py-1.5 flex items-center justify-between">
      <div className="flex items-center gap-6">
        {tickers.map((t) => {
          const d = marketData?.indices?.[t] || marketData?.[t] || {};
          const change = d.change_pct || d.change || 0;
          return (
            <div key={t} className="flex items-center gap-2 text-[11px]">
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
      <span className={`text-[10px] font-bold ${rc.text}`}>
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
  const { data: paramsData } = useApi("strategy/regime-params", {
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
      await fetch(getApiUrl("openclaw/macro/override"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bias_multiplier: val }),
      });
    } catch (e) {
      console.error("Failed to POST bias override:", e);
    }
  }, []);

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
      {/* ============ PANEL 1: HEADER ============ */}
      <div className="px-4 py-3 border-b border-gray-800/50 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-bold text-white tracking-tight">
            Market Regime
          </h1>
          <RegimeBadge
            state={currentRegime}
            confidence={regimeData?.hmm_confidence}
          />
        </div>
        <div className="flex items-center gap-3">
          <div className="text-[10px] text-gray-500">
            Risk Score:
            <span
              className={`font-mono text-sm ${(riskScore?.score || 0) > 70 ? "text-red-400" : (riskScore?.score || 0) > 40 ? "text-amber-400" : "text-emerald-400"}`}
            >
              {riskScore?.score ?? "\u2014"}
            </span>
          </div>
          <span
            className={`text-[10px] px-2 py-0.5 rounded ${healthData?.status === "healthy" ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}`}
          >
            {healthData?.status || "unknown"}
          </span>
          <div className="flex bg-gray-800/50 rounded overflow-hidden">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-2 py-0.5 text-[10px] font-semibold transition-colors ${timeframe === tf ? "bg-cyan-600 text-white" : "text-gray-400 hover:text-white"}`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ============ PANEL 2: 10-KPI STRIP ============ */}
      <div className="px-4 py-2 border-b border-gray-800/30">
        <div className="grid grid-cols-10 gap-2">
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
            label="VELEZ"
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
            value={(macroData?.vix || 0) > 25 ? "ALERT" : "CLEAR"}
            color={
              (macroData?.vix || 0) > 25 ? "text-red-400" : "text-emerald-400"
            }
            alert={(macroData?.vix || 0) > 40}
          />
        </div>
      </div>

      {/* ============ MAIN GRID ============ */}
      <div className="flex-1 px-4 py-3 overflow-y-auto">
        <div className="grid grid-cols-12 gap-3">
          {/* PANEL 3: State Machine (4 cols) */}
          <div className="col-span-4">
            <RegimeStateMachine
              currentState={currentRegime}
              regimeData={regimeData}
            />
          </div>

          {/* PANEL 4: VIX Macro Chart (8 cols) */}
          <div className="col-span-8">
            <VixMacroChart
              marketData={marketData}
              macroData={macroData}
              regimeData={regimeData}
              timeframe={timeframe}
            />
          </div>

          {/* PANEL 5: Regime Params (4 cols) */}
          <div className="col-span-4">
            <RegimeParamPanel
              paramsData={paramsData}
              regimeState={currentRegime}
            />
          </div>

          {/* PANEL 6: Performance Matrix (4 cols) */}
          <div className="col-span-4">
            <RegimePerformanceMatrix backtestData={backtestData} />
          </div>

          {/* PANEL 7: Sector Heatmap (4 cols) */}
          <div className="col-span-4">
            <SectorHeatmap sectorsData={sectorsData} />
          </div>

          {/* PANEL 8: Regime Flow Diagram (6 cols) */}
          <div className="col-span-6">
            <RegimeFlowDiagram
              regimeState={currentRegime}
              paramsData={paramsData}
            />
          </div>

          {/* PANEL 9: Crash Protocol (3 cols) */}
          <div className="col-span-3">
            <CrashProtocolPanel riskGauges={riskGauges} macroData={macroData} />
          </div>

          {/* PANEL 10: Agent Consensus (3 cols) */}
          <div className="col-span-3">
            <AgentConsensusPanel memoryData={memoryData} />
          </div>

          {/* PANEL 11: Transition History (12 cols) */}
          <div className="col-span-12">
            <TransitionHistory regimeData={transitionData || regimeData} />
          </div>

          {/* Bias Multiplier + Whale Flow strip (12 cols) */}
          <div className="col-span-12">
            <div className="bg-[#111827] rounded-lg border border-gray-700/30 p-3 flex items-center gap-4">
              <span className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">Bias Multiplier</span>
              <input type="range" min="0" max="5" step="0.1" value={biasMultiplier} onChange={(e) => handleBiasChange(parseFloat(e.target.value))} className="flex-1 h-1 accent-cyan-500" />
              <span className="text-sm font-mono text-cyan-400 w-10 text-right">{biasMultiplier.toFixed(1)}</span>
              {whaleFlow?.alerts?.length > 0 && (
                <div className="ml-4 flex items-center gap-2 text-[10px]">
                  <span className="text-purple-400 font-semibold">WHALE:</span>
                  <span className="text-gray-300">{whaleFlow.alerts[0]?.symbol} - {whaleFlow.alerts[0]?.type}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ============ PANEL 12: FOOTER TICKER ============ */}
      <FooterTicker marketData={marketData} regimeState={currentRegime} />

      {/* Error toast */}
      {regimeError && (
        <div className="fixed bottom-16 right-4 bg-red-900/90 border border-red-500/50 text-red-200 text-xs px-4 py-2 rounded-lg">
          Regime API error: {regimeError.message || "Connection failed"}
        </div>
      )}
    </div>
  );
}
