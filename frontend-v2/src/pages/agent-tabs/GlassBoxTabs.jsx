// Glass Box Cockpit Tabs — Council Transparency, Operator Controls, Event Feed, Learning Summary
import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Eye, Shield, Brain, Activity, Settings, RefreshCw, Play, Pause,
  CheckCircle, XCircle, AlertTriangle, ChevronRight, Clock, Zap,
  TrendingUp, TrendingDown, Minus, BarChart3, Target, Lock, Unlock,
  Sliders, ToggleLeft, ToggleRight, Radio, Search, BookOpen,
} from "lucide-react";
import { useApi } from "../../hooks/useApi";
import { getApiUrl, getAuthHeaders } from "../../config/api";
import ws from "../../services/websocket";
import { toast } from "react-toastify";


// ═══════════════════════════════════════════════════════════════════
// COUNCIL TRANSPARENCY TAB — Decision Header, Why Panel, Agent Matrix
// ═══════════════════════════════════════════════════════════════════
export function CouncilTransparencyTab() {
  const { data: latestDecision, refetch: refetchDecision } = useApi("council/latest-decision", { pollIntervalMs: 10000 });
  const { data: agentHealth, refetch: refetchHealth } = useApi("council/agent-health", { pollIntervalMs: 15000 });
  const { data: gateStatus } = useApi("council/gate-status", { pollIntervalMs: 15000 });
  const { data: cogMode } = useApi("cognitive/mode", { pollIntervalMs: 20000 });

  const decision = latestDecision?.decision;
  const agents = agentHealth?.agents || [];
  const gate = gateStatus?.gate || {};

  const directionColors = {
    buy: "text-emerald-400",
    sell: "text-red-400",
    hold: "text-amber-400",
  };
  const directionBg = {
    buy: "bg-emerald-500/10 border-emerald-500/30",
    sell: "bg-red-500/10 border-red-500/30",
    hold: "bg-amber-500/10 border-amber-500/30",
  };

  return (
    <div className="space-y-3">
      {/* ── Decision Header Strip ── */}
      {decision ? (
        <div className={`aurora-card p-3 border ${directionBg[decision.final_direction] || "border-gray-700"}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Target className="w-5 h-5 text-cyan-400" />
                <span className="text-lg font-bold text-white">{decision.symbol}</span>
              </div>
              <span className={`text-xl font-black uppercase ${directionColors[decision.final_direction]}`}>
                {decision.final_direction}
              </span>
              <div className="flex items-center gap-1.5">
                <div className="w-24 h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${decision.final_confidence > 0.75 ? "bg-emerald-500" : decision.final_confidence > 0.5 ? "bg-cyan-500" : "bg-amber-500"}`}
                    style={{ width: `${(decision.final_confidence || 0) * 100}%` }}
                  />
                </div>
                <span className="text-sm font-bold text-white">{((decision.final_confidence || 0) * 100).toFixed(0)}%</span>
              </div>
            </div>

            <div className="flex items-center gap-4 text-[10px]">
              <div className="flex items-center gap-3">
                <span className="text-emerald-400">BUY {decision.vote_summary?.buy || 0}</span>
                <span className="text-red-400">SELL {decision.vote_summary?.sell || 0}</span>
                <span className="text-amber-400">HOLD {decision.vote_summary?.hold || 0}</span>
              </div>
              <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${decision.execution_ready ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-gray-700 text-gray-400 border border-gray-600"}`}>
                {decision.execution_ready ? "EXEC READY" : "NO EXEC"}
              </span>
              {decision.vetoed && (
                <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-red-500/20 text-red-400 border border-red-500/30">
                  VETOED
                </span>
              )}
              <span className="text-gray-500">
                {decision.total_latency_ms ? `${Math.round(decision.total_latency_ms)}ms` : ""}
              </span>
            </div>
          </div>
          {decision.council_reasoning && (
            <div className="mt-2 text-[10px] text-gray-400 border-t border-gray-700/50 pt-2">
              <Eye className="w-3 h-3 inline mr-1 text-cyan-400" />
              {decision.council_reasoning}
            </div>
          )}
        </div>
      ) : (
        <div className="aurora-card p-4 text-center text-gray-500 text-xs">
          No council decision yet. Waiting for first evaluation...
        </div>
      )}

      <div className="grid grid-cols-12 gap-3">
        {/* ── Agent Consensus Matrix ── */}
        <div className="col-span-8 aurora-card p-3">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">Agent Consensus Matrix</h3>
            <button onClick={() => { refetchHealth(); refetchDecision(); }} className="p-1 text-gray-500 hover:text-cyan-400">
              <RefreshCw className="w-3 h-3" />
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
              <thead>
                <tr className="text-gray-500 border-b border-gray-800">
                  <th className="text-left py-1 pr-2">Agent</th>
                  <th className="text-center">Vote</th>
                  <th className="text-right">Conf</th>
                  <th className="text-right">Weight</th>
                  <th className="text-right">Accuracy</th>
                  <th className="text-center">Streak</th>
                  <th className="text-center">Health</th>
                  <th className="text-center">Enabled</th>
                </tr>
              </thead>
              <tbody>
                {agents.map(a => (
                  <tr key={a.agent_name} className="border-b border-gray-800/30 hover:bg-cyan-500/5">
                    <td className="py-1 pr-2 text-cyan-400 font-mono">{a.agent_name}</td>
                    <td className="text-center">
                      {a.latest_vote ? (
                        <span className={`font-bold ${directionColors[a.latest_vote.direction] || "text-gray-500"}`}>
                          {(a.latest_vote.direction || "—").toUpperCase()}
                        </span>
                      ) : <span className="text-gray-600">—</span>}
                    </td>
                    <td className="text-right text-white">
                      {a.latest_vote ? `${(a.latest_vote.confidence * 100).toFixed(0)}%` : "—"}
                    </td>
                    <td className="text-right">
                      <span className={a.weight > 1.2 ? "text-emerald-400" : a.weight < 0.8 ? "text-red-400" : "text-white"}>
                        {a.weight?.toFixed(2)}
                      </span>
                    </td>
                    <td className="text-right">
                      {a.accuracy != null ? (
                        <span className={a.accuracy > 0.6 ? "text-emerald-400" : a.accuracy < 0.4 ? "text-red-400" : "text-amber-400"}>
                          {(a.accuracy * 100).toFixed(0)}%
                        </span>
                      ) : <span className="text-gray-600">—</span>}
                    </td>
                    <td className="text-center">
                      <span className={`text-[9px] px-1 py-0.5 rounded ${
                        a.streak_status === "ACTIVE" ? "bg-emerald-500/10 text-emerald-400" :
                        a.streak_status === "PROBATION" ? "bg-amber-500/10 text-amber-400" :
                        "bg-red-500/10 text-red-400"
                      }`}>
                        {a.streak_status}
                      </span>
                    </td>
                    <td className="text-center">
                      <span className={`w-2 h-2 rounded-full inline-block ${a.healthy ? "bg-emerald-500" : "bg-red-500"}`} />
                    </td>
                    <td className="text-center">
                      <span className={`w-2 h-2 rounded-full inline-block ${a.enabled ? "bg-emerald-500" : "bg-gray-600"}`} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── Right sidebar: Gate Status + Cognitive Mode ── */}
        <div className="col-span-4 space-y-3">
          {/* Council Gate Metrics */}
          <div className="aurora-card p-3">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Council Gate</h3>
            <div className="space-y-1.5 text-[10px]">
              {[
                ["Signals Received", gate.signals_received, "text-cyan-400"],
                ["Councils Invoked", gate.councils_invoked, "text-white"],
                ["Councils Passed", gate.councils_passed, "text-emerald-400"],
                ["Councils Vetoed", gate.councils_vetoed, "text-red-400"],
                ["Councils Held", gate.councils_held, "text-amber-400"],
                ["Pass Rate", gate.pass_rate != null ? `${(gate.pass_rate * 100).toFixed(1)}%` : "—", "text-white"],
              ].map(([label, val, color]) => (
                <div key={label} className="flex justify-between">
                  <span className="text-gray-500">{label}</span>
                  <span className={`font-mono ${color}`}>{val ?? "—"}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Cognitive Mode */}
          <div className="aurora-card p-3">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Cognitive Mode</h3>
            <div className="flex items-center gap-2 mb-2">
              <Brain className="w-4 h-4 text-purple-400" />
              <span className={`text-sm font-bold uppercase ${
                cogMode?.mode === "explore" ? "text-purple-400" :
                cogMode?.mode === "defensive" ? "text-red-400" : "text-cyan-400"
              }`}>
                {cogMode?.mode || "exploit"}
              </span>
            </div>
            <div className="space-y-1 text-[10px]">
              <div className="flex justify-between">
                <span className="text-gray-500">Exploration Rate</span>
                <span className="text-white">{((cogMode?.exploration_rate || 0) * 100).toFixed(0)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Diversity</span>
                <span className="text-white">{(cogMode?.hypothesis_diversity || 0).toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Agreement</span>
                <span className="text-white">{((cogMode?.agent_agreement || 0) * 100).toFixed(0)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Mode Switches (24h)</span>
                <span className="text-white">{cogMode?.mode_switches_24h || 0}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════
// OPERATOR CONTROLS TAB — System Mode, Risk Caps, Agent Toggles, Learning
// ═══════════════════════════════════════════════════════════════════
export function OperatorControlsTab() {
  const { data: systemMode, refetch: refetchMode } = useApi("system/mode", { pollIntervalMs: 10000 });
  const { data: agentConfig, refetch: refetchConfig } = useApi("council/agent-config", { pollIntervalMs: 15000 });
  const { data: settings } = useApi("settings/risk");

  const [mode, setMode] = useState("SHADOW");
  const [riskLimits, setRiskLimits] = useState({
    max_portfolio_heat: 0.25,
    max_single_position: 0.10,
    max_daily_trades: 10,
    max_drawdown_pct: 5.0,
    kelly_fraction: 0.25,
  });
  const [learningConfig, setLearningConfig] = useState({
    writeback_enabled: true,
    exploration_rate: 0.10,
    learning_rate: 0.05,
  });

  useEffect(() => {
    if (systemMode?.mode) setMode(systemMode.mode);
  }, [systemMode]);

  useEffect(() => {
    if (settings) {
      setRiskLimits(prev => ({
        ...prev,
        ...Object.fromEntries(Object.entries(settings).filter(([k]) => k in prev)),
      }));
    }
  }, [settings]);

  const setSystemMode = async (newMode) => {
    try {
      const res = await fetch(getApiUrl("system/mode"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ mode: newMode }),
      });
      if (res.ok) {
        setMode(newMode);
        toast.success(`System mode: ${newMode}`);
        refetchMode();
      } else {
        toast.error("Failed to set mode");
      }
    } catch (e) {
      toast.error("Network error");
    }
  };

  const saveRiskLimits = async () => {
    try {
      const res = await fetch(getApiUrl("settings/risk-limits"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify(riskLimits),
      });
      if (res.ok) toast.success("Risk limits saved");
      else toast.error("Failed to save risk limits");
    } catch (e) {
      toast.error("Network error");
    }
  };

  const saveLearning = async () => {
    try {
      const res = await fetch(getApiUrl("settings/learning"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify(learningConfig),
      });
      if (res.ok) toast.success("Learning config saved");
      else toast.error("Failed to save learning config");
    } catch (e) {
      toast.error("Network error");
    }
  };

  const toggleAgent = async (agentName, enabled) => {
    try {
      const res = await fetch(getApiUrl("council/agent-config"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ agent_name: agentName, enabled }),
      });
      if (res.ok) {
        toast.success(`${agentName} ${enabled ? "enabled" : "disabled"}`);
        refetchConfig();
      }
    } catch (e) {
      toast.error("Network error");
    }
  };

  const overrides = agentConfig?.overrides || {};
  const allAgents = [
    "market_perception", "flow_perception", "regime", "intermarket",
    "rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing",
    "hypothesis", "strategy", "risk", "execution", "critic",
    "bull_debater", "bear_debater", "red_team",
  ];

  const modeButtons = [
    { key: "AUTO", label: "AUTO", desc: "Full autonomous trading", color: "emerald" },
    { key: "SHADOW", label: "SHADOW", desc: "Signals run, no orders", color: "cyan" },
    { key: "PAUSED", label: "PAUSED", desc: "Pipeline halted", color: "amber" },
    { key: "LEARNING_ONLY", label: "LEARN", desc: "Council runs for learning", color: "purple" },
  ];

  return (
    <div className="grid grid-cols-12 gap-3">
      {/* ── System Mode ── */}
      <div className="col-span-4 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-3">Master System Mode</h3>
        <div className="grid grid-cols-2 gap-2">
          {modeButtons.map(m => (
            <button
              key={m.key}
              onClick={() => setSystemMode(m.key)}
              className={`p-3 rounded border text-center transition-all ${
                mode === m.key
                  ? `bg-${m.color}-500/20 border-${m.color}-500/50 text-${m.color}-400`
                  : "bg-gray-800/30 border-gray-700 text-gray-500 hover:border-gray-500"
              }`}
            >
              <div className="text-sm font-bold">{m.label}</div>
              <div className="text-[8px] mt-0.5">{m.desc}</div>
            </button>
          ))}
        </div>
        <div className="mt-3 text-[9px] text-gray-500">
          Current: <span className="text-white font-bold">{mode}</span>
        </div>
      </div>

      {/* ── Risk Cap Sliders ── */}
      <div className="col-span-4 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-3">Risk Caps</h3>
        <div className="space-y-3">
          {[
            { key: "max_portfolio_heat", label: "Max Portfolio Heat", min: 0.05, max: 0.50, step: 0.05, fmt: v => `${(v*100).toFixed(0)}%` },
            { key: "max_single_position", label: "Max Single Position", min: 0.02, max: 0.25, step: 0.01, fmt: v => `${(v*100).toFixed(0)}%` },
            { key: "max_daily_trades", label: "Max Daily Trades", min: 1, max: 50, step: 1, fmt: v => v },
            { key: "max_drawdown_pct", label: "Max Drawdown %", min: 1, max: 20, step: 0.5, fmt: v => `${v}%` },
            { key: "kelly_fraction", label: "Kelly Fraction", min: 0.05, max: 1.0, step: 0.05, fmt: v => `${(v*100).toFixed(0)}%` },
          ].map(s => (
            <div key={s.key}>
              <div className="flex justify-between text-[10px] mb-0.5">
                <span className="text-gray-400">{s.label}</span>
                <span className="text-white font-mono">{s.fmt(riskLimits[s.key])}</span>
              </div>
              <input
                type="range" min={s.min} max={s.max} step={s.step}
                value={riskLimits[s.key]}
                onChange={e => setRiskLimits(prev => ({ ...prev, [s.key]: parseFloat(e.target.value) }))}
                className="w-full h-1.5 bg-gray-800 rounded-full appearance-none cursor-pointer accent-cyan-500"
              />
            </div>
          ))}
          <button onClick={saveRiskLimits}
            className="w-full py-1.5 text-[10px] font-bold bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded hover:bg-cyan-500/30 transition-all">
            SAVE RISK CAPS
          </button>
        </div>
      </div>

      {/* ── Agent Toggles ── */}
      <div className="col-span-4 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-3">Agent Enable/Disable</h3>
        <div className="space-y-1 max-h-[300px] overflow-y-auto scrollbar-thin">
          {allAgents.map(name => {
            const enabled = overrides[name] !== false;
            return (
              <div key={name} className="flex items-center justify-between py-1 border-b border-gray-800/30">
                <span className="text-[10px] text-gray-300 font-mono">{name}</span>
                <button
                  onClick={() => toggleAgent(name, !enabled)}
                  className={`p-0.5 rounded transition-all ${enabled ? "text-emerald-400" : "text-gray-600"}`}
                >
                  {enabled ? <ToggleRight className="w-5 h-3" /> : <ToggleLeft className="w-5 h-3" />}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Learning Config ── */}
      <div className="col-span-6 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-3">Learning Configuration</h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <div className="flex justify-between text-[10px] mb-1">
              <span className="text-gray-400">Writeback</span>
              <button
                onClick={() => setLearningConfig(prev => ({ ...prev, writeback_enabled: !prev.writeback_enabled }))}
                className={learningConfig.writeback_enabled ? "text-emerald-400" : "text-gray-600"}
              >
                {learningConfig.writeback_enabled ? <ToggleRight className="w-5 h-3" /> : <ToggleLeft className="w-5 h-3" />}
              </button>
            </div>
            <div className="text-[8px] text-gray-600">Enable outcome → weight updates</div>
          </div>
          <div>
            <div className="flex justify-between text-[10px] mb-0.5">
              <span className="text-gray-400">Exploration</span>
              <span className="text-white font-mono">{(learningConfig.exploration_rate * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range" min={0} max={0.5} step={0.01}
              value={learningConfig.exploration_rate}
              onChange={e => setLearningConfig(prev => ({ ...prev, exploration_rate: parseFloat(e.target.value) }))}
              className="w-full h-1 bg-gray-800 rounded-full appearance-none cursor-pointer accent-purple-500"
            />
          </div>
          <div>
            <div className="flex justify-between text-[10px] mb-0.5">
              <span className="text-gray-400">Learning Rate</span>
              <span className="text-white font-mono">{(learningConfig.learning_rate * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range" min={0.01} max={0.2} step={0.01}
              value={learningConfig.learning_rate}
              onChange={e => setLearningConfig(prev => ({ ...prev, learning_rate: parseFloat(e.target.value) }))}
              className="w-full h-1 bg-gray-800 rounded-full appearance-none cursor-pointer accent-purple-500"
            />
          </div>
        </div>
        <button onClick={saveLearning}
          className="mt-3 w-full py-1.5 text-[10px] font-bold bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded hover:bg-purple-500/30 transition-all">
          SAVE LEARNING CONFIG
        </button>
      </div>

      {/* ── Data Source Weights ── */}
      <DataSourceWeights />
    </div>
  );
}

function DataSourceWeights() {
  const [sources, setSources] = useState({
    alpaca: { weight: 1.0, muted: false },
    unusual_whales: { weight: 0.8, muted: false },
    finviz: { weight: 0.6, muted: false },
    fred: { weight: 0.7, muted: false },
    ollama: { weight: 1.0, muted: false },
    youtube: { weight: 0.4, muted: false },
    discord: { weight: 0.5, muted: false },
    rss_news: { weight: 0.6, muted: false },
  });

  const save = async () => {
    try {
      const res = await fetch(getApiUrl("settings/data-sources"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ sources }),
      });
      if (res.ok) toast.success("Data source weights saved");
      else toast.error("Failed to save");
    } catch { toast.error("Network error"); }
  };

  return (
    <div className="col-span-6 aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-3">Data Source Weights</h3>
      <div className="space-y-1.5">
        {Object.entries(sources).map(([name, cfg]) => (
          <div key={name} className="flex items-center gap-2">
            <button
              onClick={() => setSources(prev => ({ ...prev, [name]: { ...prev[name], muted: !prev[name].muted } }))}
              className={`w-4 h-4 flex items-center justify-center rounded ${cfg.muted ? "text-red-400" : "text-emerald-400"}`}
            >
              {cfg.muted ? <XCircle className="w-3 h-3" /> : <CheckCircle className="w-3 h-3" />}
            </button>
            <span className={`text-[10px] font-mono w-24 ${cfg.muted ? "text-gray-600 line-through" : "text-gray-300"}`}>{name}</span>
            <input
              type="range" min={0} max={1} step={0.1}
              value={cfg.weight}
              onChange={e => setSources(prev => ({ ...prev, [name]: { ...prev[name], weight: parseFloat(e.target.value) } }))}
              className="flex-1 h-1 bg-gray-800 rounded-full appearance-none cursor-pointer accent-cyan-500"
              disabled={cfg.muted}
            />
            <span className="text-[10px] text-white font-mono w-8 text-right">{cfg.weight.toFixed(1)}</span>
          </div>
        ))}
      </div>
      <button onClick={save}
        className="mt-2 w-full py-1.5 text-[10px] font-bold bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded hover:bg-cyan-500/30 transition-all">
        SAVE DATA SOURCE WEIGHTS
      </button>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════
// LIVE EVENT FEED TAB — Real-time council verdicts, trades, circuit breaks
// ═══════════════════════════════════════════════════════════════════
export function LiveEventFeedTab() {
  const [events, setEvents] = useState([]);
  const eventsRef = useRef([]);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    const addEvent = (type, icon) => (data) => {
      const now = new Date();
      const ts = `${String(now.getHours()).padStart(2,"0")}:${String(now.getMinutes()).padStart(2,"0")}:${String(now.getSeconds()).padStart(2,"0")}.${String(now.getMilliseconds()).padStart(3,"0")}`;
      const evt = {
        id: Date.now() + Math.random(),
        ts,
        type,
        icon,
        data: typeof data === "object" ? data : { message: data },
      };
      eventsRef.current = [evt, ...eventsRef.current].slice(0, 200);
      setEvents([...eventsRef.current]);
    };

    const unsubs = [
      ws.on?.("council", addEvent("council.verdict", "gavel")) || (() => {}),
      ws.on?.("trades", addEvent("trade.executed", "trending-up")) || (() => {}),
      ws.on?.("risk", addEvent("risk.alert", "shield")) || (() => {}),
      ws.on?.("agents", addEvent("agent.update", "cpu")) || (() => {}),
      ws.on?.("signal", addEvent("signal.generated", "zap")) || (() => {}),
    ];

    return () => unsubs.forEach(u => typeof u === "function" && u());
  }, []);

  const typeColors = {
    "council.verdict": "text-cyan-400",
    "trade.executed": "text-emerald-400",
    "risk.alert": "text-red-400",
    "agent.update": "text-purple-400",
    "signal.generated": "text-amber-400",
  };

  const filtered = filter === "all" ? events : events.filter(e => e.type === filter);

  return (
    <div className="space-y-3">
      <div className="aurora-card p-3">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider">Live Event Feed</h3>
          <div className="flex gap-1 text-[9px]">
            {["all", "council.verdict", "trade.executed", "risk.alert", "signal.generated"].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2 py-0.5 rounded border ${filter === f ? "bg-cyan-500/20 text-cyan-400 border-cyan-500/30" : "text-gray-600 border-gray-700"}`}
              >
                {f === "all" ? "ALL" : f.split(".")[1]?.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div className="max-h-[500px] overflow-y-auto scrollbar-thin space-y-0 font-mono">
          {filtered.length === 0 ? (
            <div className="text-gray-500 text-[10px] text-center py-8">
              <Radio className="w-4 h-4 mx-auto mb-2 animate-pulse" />
              Listening for events... Connect WebSocket for live data
            </div>
          ) : filtered.map(e => (
            <div key={e.id} className="flex gap-2 text-[10px] hover:bg-cyan-500/5 px-2 py-1 rounded border-b border-gray-800/20">
              <span className="text-gray-600 shrink-0 w-20">{e.ts}</span>
              <span className={`shrink-0 w-32 font-bold ${typeColors[e.type] || "text-gray-400"}`}>{e.type}</span>
              <span className="text-gray-300 flex-1 truncate">
                {e.data?.verdict?.symbol || e.data?.symbol || ""}{" "}
                {e.data?.verdict?.final_direction || e.data?.type || ""}{" "}
                {e.data?.verdict?.final_confidence != null ? `${(e.data.verdict.final_confidence * 100).toFixed(0)}%` : ""}
                {e.data?.message || JSON.stringify(e.data).slice(0, 120)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-5 gap-3">
        {[
          ["Total Events", events.length, "text-cyan-400"],
          ["Council Verdicts", events.filter(e => e.type === "council.verdict").length, "text-cyan-400"],
          ["Trades", events.filter(e => e.type === "trade.executed").length, "text-emerald-400"],
          ["Risk Alerts", events.filter(e => e.type === "risk.alert").length, "text-red-400"],
          ["Signals", events.filter(e => e.type === "signal.generated").length, "text-amber-400"],
        ].map(([label, val, color]) => (
          <div key={label} className="aurora-card p-2 text-center">
            <div className={`text-sm font-bold ${color}`}>{val}</div>
            <div className="text-[8px] text-gray-500 uppercase">{label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════
// LEARNING SUMMARY TAB — Learning Since Yesterday, Pattern Memory, Drift
// ═══════════════════════════════════════════════════════════════════
export function LearningSummaryTab() {
  const { data: weights } = useApi("council/weights", { pollIntervalMs: 30000 });
  const { data: brainHealth } = useApi("cognitive/brain-health", { pollIntervalMs: 30000 });
  const { data: heuristics } = useApi("cognitive/heuristics", { pollIntervalMs: 60000 });
  const { data: driftData } = useApi("cognitive/drift-status", { pollIntervalMs: 60000 });
  const { data: calibration } = useApi("cognitive/calibration", { pollIntervalMs: 60000 });
  const { data: feedbackPerf } = useApi("council/agent-health", { pollIntervalMs: 30000 });

  const weightData = weights?.weights || {};
  const brain = brainHealth || {};
  const heuristicList = heuristics?.heuristics || [];
  const drift = driftData?.drift || {};
  const agents = feedbackPerf?.agents || [];

  return (
    <div className="space-y-3">
      {/* ── Top: Brain Health Cards ── */}
      <div className="grid grid-cols-6 gap-3">
        {[
          ["ML Models", brain.ml_models?.status || "unknown", brain.ml_models?.status === "ok" || brain.ml_models?.status === "loaded" ? "text-emerald-400" : "text-amber-400"],
          ["Drift Monitor", brain.drift_monitor?.status || "unknown", "text-cyan-400"],
          ["Brier Score", brain.calibration?.brier_score != null ? brain.calibration.brier_score.toFixed(4) : "—", "text-white"],
          ["Memory Bank", brain.memory_bank?.status || "unknown", brain.memory_bank?.status === "ok" ? "text-emerald-400" : "text-amber-400"],
          ["Heuristics", `${brain.heuristic_engine?.active_heuristics || 0} active`, "text-purple-400"],
          ["Council Gate", brain.council_gate?.status || "unknown", brain.council_gate?.running ? "text-emerald-400" : "text-amber-400"],
        ].map(([label, val, color]) => (
          <div key={label} className="aurora-card p-2 text-center">
            <div className={`text-xs font-bold ${color}`}>{val}</div>
            <div className="text-[8px] text-gray-500 uppercase">{label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-12 gap-3">
        {/* ── Bayesian Weight Changes ── */}
        <div className="col-span-4 aurora-card p-3">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Bayesian Agent Weights</h3>
          <div className="text-[9px] text-gray-500 mb-2">
            Updates: {weights?.update_count || 0} | Last: {weights?.last_update || "never"}
          </div>
          <div className="space-y-1">
            {Object.entries(weightData).sort((a, b) => b[1] - a[1]).map(([name, w]) => (
              <div key={name} className="flex items-center gap-2 text-[10px]">
                <span className="w-28 text-gray-400 font-mono truncate">{name}</span>
                <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${w > 1.2 ? "bg-emerald-500" : w < 0.8 ? "bg-red-500" : "bg-cyan-500"}`}
                    style={{ width: `${Math.min((w / 2.5) * 100, 100)}%` }}
                  />
                </div>
                <span className={`w-8 text-right font-mono ${w > 1.2 ? "text-emerald-400" : w < 0.8 ? "text-red-400" : "text-white"}`}>
                  {w.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* ── Pattern Memory (Heuristics) ── */}
        <div className="col-span-4 aurora-card p-3">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Pattern Memory</h3>
          <div className="space-y-1.5 max-h-[300px] overflow-y-auto scrollbar-thin">
            {heuristicList.length === 0 ? (
              <div className="text-gray-500 text-[10px] text-center py-4">No active heuristics</div>
            ) : heuristicList.slice(0, 20).map((h, i) => (
              <div key={h.heuristic_id || i} className="bg-[#0B0E14] rounded p-2 border border-gray-800">
                <div className="flex items-center justify-between text-[10px] mb-0.5">
                  <span className="text-cyan-400 font-mono">{h.pattern_name || h.agent_name}</span>
                  <span className={`font-bold ${h.win_rate > 0.6 ? "text-emerald-400" : "text-amber-400"}`}>
                    {((h.win_rate || 0) * 100).toFixed(0)}% WR
                  </span>
                </div>
                <div className="text-[9px] text-gray-500 truncate">{h.description || "—"}</div>
                <div className="flex gap-2 mt-0.5 text-[8px] text-gray-600">
                  <span>n={h.sample_size || 0}</span>
                  <span>R={h.avg_r_multiple?.toFixed(2) || "—"}</span>
                  <span>conf={((h.bayesian_confidence || 0) * 100).toFixed(0)}%</span>
                  <span className={h.active ? "text-emerald-400" : "text-gray-600"}>{h.active ? "ACTIVE" : "INACTIVE"}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Drift Detection + Calibration ── */}
        <div className="col-span-4 space-y-3">
          <div className="aurora-card p-3">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Drift Detection</h3>
            {drift.reference_set ? (
              <div className="space-y-1.5 text-[10px]">
                <div className="flex justify-between">
                  <span className="text-gray-500">Data Drift</span>
                  <span className={drift.data_drift ? "text-red-400" : "text-emerald-400"}>
                    {drift.data_drift ? "DETECTED" : "OK"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Perf Drift</span>
                  <span className={drift.performance_drift ? "text-red-400" : "text-emerald-400"}>
                    {drift.performance_drift ? "DETECTED" : "OK"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Last Check</span>
                  <span className="text-white">{drift.last_check || "—"}</span>
                </div>
              </div>
            ) : (
              <div className="text-[10px] text-gray-500">No drift reference set</div>
            )}
          </div>

          <div className="aurora-card p-3">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Confidence Calibration</h3>
            <div className="space-y-1.5 text-[10px]">
              <div className="flex justify-between">
                <span className="text-gray-500">Brier Score</span>
                <span className={`font-mono ${calibration?.brier_score < 0.1 ? "text-emerald-400" : calibration?.brier_score < 0.2 ? "text-amber-400" : "text-red-400"}`}>
                  {calibration?.brier_score?.toFixed(4) || "—"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Predictions</span>
                <span className="text-white">{calibration?.total_predictions || 0}</span>
              </div>
            </div>
          </div>

          {/* Agent accuracy ranking */}
          <div className="aurora-card p-3">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Top Agent Accuracy</h3>
            <div className="space-y-1">
              {agents
                .filter(a => a.accuracy != null && a.total_decisions > 0)
                .sort((a, b) => (b.accuracy || 0) - (a.accuracy || 0))
                .slice(0, 8)
                .map(a => (
                  <div key={a.agent_name} className="flex items-center gap-2 text-[10px]">
                    <span className="w-24 text-gray-400 font-mono truncate">{a.agent_name}</span>
                    <div className="flex-1 h-1 bg-gray-800 rounded-full overflow-hidden">
                      <div className="h-full bg-cyan-500 rounded-full" style={{ width: `${(a.accuracy || 0) * 100}%` }} />
                    </div>
                    <span className="text-white w-8 text-right">{((a.accuracy || 0) * 100).toFixed(0)}%</span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════
// DECISION REPLAY TAB — Browse and replay past council decisions
// ═══════════════════════════════════════════════════════════════════
export function DecisionReplayTab() {
  const { data: decisionList } = useApi("council/decisions", { pollIntervalMs: 30000 });
  const [selectedId, setSelectedId] = useState(null);
  const [replayData, setReplayData] = useState(null);
  const [loading, setLoading] = useState(false);

  const decisions = decisionList?.decisions || [];

  const loadReplay = async (id) => {
    setSelectedId(id);
    setLoading(true);
    try {
      const res = await fetch(getApiUrl(`council/decision/${id}`));
      if (res.ok) {
        const data = await res.json();
        setReplayData(data.decision);
      } else {
        toast.error("Failed to load decision");
      }
    } catch {
      toast.error("Network error");
    }
    setLoading(false);
  };

  const dirColors = { buy: "text-emerald-400", sell: "text-red-400", hold: "text-amber-400" };

  return (
    <div className="grid grid-cols-12 gap-3">
      {/* ── Decision List ── */}
      <div className="col-span-4 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Decision History</h3>
        <div className="space-y-1 max-h-[500px] overflow-y-auto scrollbar-thin">
          {decisions.length === 0 ? (
            <div className="text-gray-500 text-[10px] text-center py-8">No decisions recorded yet</div>
          ) : decisions.map(d => (
            <button
              key={d.council_decision_id}
              onClick={() => loadReplay(d.council_decision_id)}
              className={`w-full text-left p-2 rounded border transition-all ${
                selectedId === d.council_decision_id
                  ? "bg-cyan-500/10 border-cyan-500/30"
                  : "bg-[#0B0E14] border-gray-800 hover:border-gray-600"
              }`}
            >
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-cyan-400 font-bold">{d.symbol}</span>
                <span className={`font-bold ${dirColors[d.final_direction]}`}>{(d.final_direction || "").toUpperCase()}</span>
              </div>
              <div className="flex items-center justify-between text-[9px] mt-0.5">
                <span className="text-gray-500">{d.timestamp ? new Date(d.timestamp).toLocaleString() : "—"}</span>
                <span className="text-white">{((d.final_confidence || 0) * 100).toFixed(0)}%</span>
              </div>
              <div className="flex gap-1 mt-0.5">
                {d.execution_ready && <span className="text-[8px] text-emerald-400">EXEC</span>}
                {d.vetoed && <span className="text-[8px] text-red-400">VETO</span>}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* ── Replay Detail ── */}
      <div className="col-span-8">
        {loading ? (
          <div className="aurora-card p-8 text-center text-gray-500 text-xs">Loading decision replay...</div>
        ) : replayData ? (
          <div className="space-y-3">
            {/* Header */}
            <div className="aurora-card p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-lg font-bold text-white">{replayData.symbol}</span>
                  <span className={`text-lg font-black uppercase ${dirColors[replayData.final_direction]}`}>
                    {replayData.final_direction}
                  </span>
                  <span className="text-sm text-white">{((replayData.final_confidence || 0) * 100).toFixed(0)}% confidence</span>
                </div>
                <span className="text-[10px] text-gray-500">{replayData.timestamp}</span>
              </div>
              {replayData.council_reasoning && (
                <div className="mt-2 text-[10px] text-gray-400">{replayData.council_reasoning}</div>
              )}
            </div>

            {/* Vote Grid */}
            <div className="aurora-card p-3">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Full Vote Reconstruction</h3>
              <div className="grid grid-cols-3 gap-2">
                {(replayData.votes || []).map((v, i) => (
                  <div key={v.agent_name || i} className={`p-2 rounded border ${
                    v.direction === "buy" ? "border-emerald-500/20 bg-emerald-500/5" :
                    v.direction === "sell" ? "border-red-500/20 bg-red-500/5" :
                    "border-gray-700 bg-gray-800/20"
                  }`}>
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-cyan-400 font-mono">{v.agent_name}</span>
                      <span className={`font-bold ${dirColors[v.direction]}`}>{(v.direction || "").toUpperCase()}</span>
                    </div>
                    <div className="flex items-center justify-between text-[9px] mt-0.5">
                      <span className="text-gray-500">conf: {((v.confidence || 0) * 100).toFixed(0)}%</span>
                      <span className="text-gray-500">w: {(v.weight || 1).toFixed(2)}</span>
                    </div>
                    {v.reasoning && (
                      <div className="text-[8px] text-gray-600 mt-1 truncate">{v.reasoning}</div>
                    )}
                    {v.veto && <span className="text-[8px] text-red-400 font-bold">VETO: {v.veto_reason}</span>}
                  </div>
                ))}
              </div>
            </div>

            {/* Cognitive Meta */}
            {replayData.cognitive && (
              <div className="aurora-card p-3">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Cognitive Telemetry</h3>
                <div className="grid grid-cols-6 gap-2 text-[10px]">
                  {[
                    ["Mode", replayData.cognitive.mode],
                    ["Diversity", replayData.cognitive.hypothesis_diversity?.toFixed(2)],
                    ["Agreement", `${((replayData.cognitive.agent_agreement || 0) * 100).toFixed(0)}%`],
                    ["Memory Precision", replayData.cognitive.memory_precision?.toFixed(2)],
                    ["Latency", `${Math.round(replayData.cognitive.total_latency_ms || 0)}ms`],
                    ["Switches (24h)", replayData.cognitive.mode_switches_24h],
                  ].map(([label, val]) => (
                    <div key={label} className="text-center">
                      <div className="text-white font-mono">{val || "—"}</div>
                      <div className="text-[8px] text-gray-500">{label}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="aurora-card p-8 text-center text-gray-500 text-xs">
            <BookOpen className="w-6 h-6 mx-auto mb-2 opacity-50" />
            Select a decision from the list to view its full replay
          </div>
        )}
      </div>
    </div>
  );
}
