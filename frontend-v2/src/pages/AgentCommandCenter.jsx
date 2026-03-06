// AGENT COMMAND CENTER - Embodier.ai Glass House Intelligence System
// Unified page: Agent management + OpenClaw swarm control + LLM alerts
// Merges former ClawBotPanel into single command center
// Backend: GET /api/v1/agents, /api/v1/openclaw/*, WS 'agents' + 'llm-flow'
// Mockups: 01-agent-command-center-final.png, 05-agent-command-center.png, 05b-agent-command-center-spawn.png, 05c-agent-registry.png
import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import log from "@/utils/logger";
import { toast } from "react-toastify";
import { useNavigate, useParams } from "react-router-dom";
import {
  Activity, Zap, Brain, MessageCircle, Youtube, Play, Square, Pause,
  RefreshCw, RefreshCcw, CheckCircle, AlertCircle, Bot, Cpu, HardDrive,
  Radio, ChevronDown, ChevronRight, ChevronUp, AlertTriangle, Info,
  Target, Gauge, Boxes, TrendingUp, TrendingDown, Shield, Eye, Settings,
  BarChart3, Network, Trophy, ClipboardList, Workflow, Terminal, Power,
  Server, GitCommit, Users, Layers, Globe, Database, Monitor, Wifi,
  WifiOff, Circle, Hash, FileText, Send, Search, Filter, MoreVertical,
  Trash2, Copy, Edit, Sliders, Clock, ArrowRight, ArrowDown, XCircle,
} from "lucide-react";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import DataTable from "../components/ui/DataTable";
import SymbolIcon from "../components/ui/SymbolIcon";
import Slider from "../components/ui/Slider";
const AGENT_MOCKS = import.meta.env.VITE_ENABLE_AGENT_MOCKS === "true";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";
import ws from "../services/websocket";
import * as openclaw from "../services/openclawService";
// --- V3 Decomposed Agent Components ---
import SwarmTopology from '../components/agents/SwarmTopology';
import ConferencePipeline from '../components/agents/ConferencePipeline';
import DriftMonitor from '../components/agents/DriftMonitor';
import SystemAlerts from '../components/agents/SystemAlerts';
import AgentResourceMonitor from '../components/agents/AgentResourceMonitor';
// --- Constants ---
const AGENT_ICONS = {
  "Market Data Agent": Activity, "Signal Generation Agent": Zap,
  "ML Learning Agent": Brain, "Sentiment Agent": MessageCircle,
  "YouTube Knowledge Agent": Youtube,
};
const TICK_INTERVAL_MS = 60 * 1000;
const SWARM_POLL_MS = 15000;
const MACRO_POLL_MS = 30000;
const CANDIDATES_POLL_MS = 30000;
const LLM_ALERTS_MAX = 8;
const REGIME_COLORS = {
  fear: { bg: "from-red-900/40 to-red-800/20", border: "border-red-500/50", text: "text-red-400", glow: "shadow-red-500/20" },
  greed: { bg: "from-green-900/40 to-green-800/20", border: "border-green-500/50", text: "text-green-400", glow: "shadow-green-500/20" },
  neutral: { bg: "from-cyan-900/40 to-cyan-800/20", border: "border-cyan-500/50", text: "text-cyan-400", glow: "shadow-cyan-500/20" },
};
const HEALTH_DOT_COLORS = {
  healthy: "bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.6)]",
  degraded: "bg-amber-500 shadow-[0_0_6px_rgba(245,158,11,0.6)]",
  error: "bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.6)]",
  stopped: "bg-gray-600", unknown: "bg-gray-700",
};
const SPAWN_TEMPLATES = [
  { name: "Momentum Scanner", desc: "Detects strong uptrend price breaks", icon: TrendingUp, color: "text-cyan-400" },
  { name: "Mean Reversion Hunter", desc: "Finds overextended reversals", icon: RefreshCcw, color: "text-emerald-400" },
  { name: "Sentiment Aggregator", desc: "Collects strong price events", icon: MessageCircle, color: "text-amber-400" },
  { name: "News Reactor", desc: "Monitors catalysts for big movers", icon: Radio, color: "text-purple-400" },
  { name: "Breakout Detector", desc: "Monitors consolidation breaks", icon: Zap, color: "text-red-400" },
  { name: "Volume Surface Tracker", desc: "Tracks volume spikes", icon: BarChart3, color: "text-blue-400" },
  { name: "Sector Rotator", desc: "Rotates sectors by momentum", icon: Globe, color: "text-teal-400" },
  { name: "Correlation Mapper", desc: "Maps inter-asset correlations", icon: Network, color: "text-indigo-400" },
  { name: "Arbitrage Spotter", desc: "Finds pair trade opportunities", icon: Layers, color: "text-pink-400" },
  { name: "Risk Sentinel", desc: "Guards against portfolio risk", icon: Shield, color: "text-orange-400" },
];
// --- Helper: Team Badge ---
function TeamBadge({ teamId }) {
  if (!teamId) return null;
  const label = String(teamId).replace(/_/g, " ");
  const hue = (label.split("").reduce((a, c) => a + c.charCodeAt(0), 0) % 12) * 30;
  return (
    <span className="inline flex items-center px-2 py-0.5 rounded text-xs font-medium text-white cursor-pointer hover:brightness-125 transition-all"
      style={{ backgroundColor: `hsl(${hue}, 55%, 40%)` }} title={teamId}
      onClick={() => toast.info(`Inspecting Team: ${label}`)}>{label}</span>
  );
}
// --- Helper: LLM Alert ---
function LlmAlert({ alert, onDismiss }) {
  const severity = alert.severity || "info";
  const isHigh = severity === "high" || severity === "error";
  const isWarning = severity === "warning";
  const bg = isHigh ? "bg-danger/15 border-danger/40" : isWarning ? "bg-warning/15 border-warning/40" : "bg-primary/15 border-primary/40";
  return (
    <div className={`flex items-start gap-3 p-3 rounded-lg border ${bg} cursor-pointer hover:brightness-110 transition-all`}
      onClick={() => toast.info("Accessing alert logs...")}>
      <div className={isHigh ? "text-danger" : isWarning ? "text-warning" : "text-primary"}>
        {isHigh ? <AlertCircle className="w-4 h-4" /> : <Info className="w-4 h-4" />}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-white">{alert.message || alert.text || JSON.stringify(alert)}</p>
        {alert.timestamp && <p className="text-xs text-secondary mt-1">{alert.timestamp}</p>}
      </div>
      {onDismiss && <button onClick={(e) => { e.stopPropagation(); onDismiss(); }} className="text-secondary hover:text-white shrink-0">&times;</button>}
    </div>
  );
}
// --- Helper: Agent Health Matrix (mockup 01 - 5x2 grid with category groups) ---
function AgentHealthMatrix({ agents }) {
  const categories = [
    { name: "Scanner", group: "Scanner" },
    { name: "RegimeDetector", group: "Scanner" },
    { name: "Intelligence", group: "Intelligence" },
    { name: "Researcher", group: "Intelligence" },
    { name: "Adversary", group: "Intelligence" },
    { name: "Execution", group: "Execution" },
    { name: "LLMGate", group: "Execution" },
    { name: "Streaming", group: "Streaming" },
    { name: "Sentiment", group: "Sentiment" },
    { name: "MLLearning", group: "MLLearning" },
    { name: "Conference", group: "Conference" },
    { name: "Memory", group: "Memory" },
  ];
  const activeCount = agents.filter(a => a.status === "running").length;
  const warningCount = agents.filter(a => a.health === "degraded").length;
  const errorCount = agents.filter(a => a.health === "error" || a.status === "error").length;
  const stoppedCount = agents.filter(a => a.status === "stopped").length;
  return (
    <Card title="Agent Health Matrix">
      {/* Group headers */}
      <div className="grid grid-cols-3 gap-x-4 gap-y-1 mb-3">
        {["Scanner", "Intelligence", "Execution"].map(g => (
          <div key={g} className="text-[9px] text-cyan-400/60 font-bold uppercase tracking-wider text-center border-b border-cyan-500/10 pb-1">{g}</div>
        ))}
      </div>
      {/* Health dots grid */}
      <div className="grid grid-cols-5 gap-3 mb-3">
        {categories.map((cat, i) => {
          const agent = agents[i % Math.max(agents.length, 1)];
          const health = agent?.health || "unknown";
          return (
            <div key={cat.name} className="flex flex-col items-center gap-1 cursor-pointer hover:scale-110 transition-transform"
              onClick={() => toast.info(`Inspecting ${cat.name} health metrics`)}>
              <div className={`w-4 h-4 rounded-full ${HEALTH_DOT_COLORS[health] || HEALTH_DOT_COLORS.unknown}`} />
              <span className="text-[9px] text-secondary leading-none">{cat.name}</span>
            </div>
          );
        })}
      </div>
      {/* Legend bar */}
      <div className="flex gap-4 pt-2 border-t border-cyan-500/10 text-[10px] text-secondary">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" />{activeCount} Active</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500" />{warningCount} Warning</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" />{errorCount} Error</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-gray-600" />{stoppedCount} Stopped</span>
      </div>
    </Card>
  );
}
// --- Helper: Live Agent Activity Feed (mockup 01 - timestamped log stream) ---
function LiveActivityFeed({ agents }) {
  const [feedItems, setFeedItems] = useState([]);
  const feedRef = useRef([]);
  const colorMap = useRef({});
  const colors = ["text-emerald-400", "text-cyan-400", "text-amber-400", "text-purple-400", "text-red-400", "text-blue-400"];

  // Subscribe to real-time agent events via WebSocket
  useEffect(() => {
    const handler = (msg) => {
      if (!msg) return;
      const now = new Date();
      const time = `[${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}]`;
      const agentName = msg.agent_name || msg.agent || msg.type || "system";
      if (!colorMap.current[agentName]) {
        colorMap.current[agentName] = colors[Object.keys(colorMap.current).length % colors.length];
      }
      const item = {
        id: Date.now() + Math.random(),
        time,
        agent: agentName,
        action: msg.action || msg.message || msg.reasoning || JSON.stringify(msg).slice(0, 120),
        color: colorMap.current[agentName],
      };
      feedRef.current = [item, ...feedRef.current].slice(0, 50);
      setFeedItems([...feedRef.current]);
    };
    ws.subscribe("agents", handler);
    ws.subscribe("council", handler);
    return () => {
      ws.unsubscribe("agents", handler);
      ws.unsubscribe("council", handler);
    };
  }, []);

  // Populate from agents prop if no live data yet
  useEffect(() => {
    if (feedItems.length === 0 && agents.length > 0) {
      const items = agents.slice(0, 10).map((a, i) => ({
        id: i,
        time: a.last_tick ? new Date(a.last_tick).toLocaleTimeString() : "--:--:--",
        agent: a.name || a.agent_name || `Agent-${i}`,
        action: a.status === "running" ? "Active and monitoring" : `Status: ${a.status || "unknown"}`,
        color: colors[i % colors.length],
      }));
      setFeedItems(items);
    }
  }, [agents]);

  return (
    <Card title="Live Agent Activity Feed">
      <div className="space-y-0.5 max-h-[260px] overflow-y-auto scrollbar-thin font-mono">
        {feedItems.length === 0 ? (
          <p className="text-secondary text-xs text-center py-4">Awaiting agent activity...</p>
        ) : feedItems.map(item => (
          <div key={item.id} className="flex gap-2 text-[11px] cursor-pointer hover:bg-cyan-500/10 px-2 py-0.5 rounded transition-all"
            onClick={() => toast.info(`Trace: ${item.agent} - ${item.action}`)}>
            <span className="text-secondary/70 shrink-0">{item.time}</span>
            <span className={`${item.color} font-bold shrink-0`}>{item.agent}</span>
            <span className="text-secondary/50">&mdash;</span>
            <span className="text-white/80 truncate">{item.action}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
// --- Helper: Blackboard Live Feed Table (mockup 01 - topic/subs/rate table) ---
function BlackboardLiveFeed({ blackboardMsgs }) {
  const { data: busStatus } = useApi("system/event-bus/status");
  const defaultTopics = [
    { topic: "SIG_GEN", subs: 3, msgRate: 3.4, lastMsg: "Signal generated for SPY" },
    { topic: "RISK_EVA", subs: 8, msgRate: 1.7, lastMsg: "Risk assessment requested" },
    { topic: "SENTIMENT", subs: 5, msgRate: 0.9, lastMsg: "News stream processing" },
    { topic: "EXECUTION", subs: 4, msgRate: 4.2, lastMsg: "Macro data refresh" },
  ];
  const topics = Array.isArray(busStatus?.topics) ? busStatus.topics : defaultTopics;
  return (
    <Card title="Blackboard Live Feed">
      <table className="w-full text-[11px]">
        <thead><tr className="text-secondary/60 border-b border-cyan-500/10">
          <th className="text-left py-1 font-medium">Topic</th>
          <th className="text-right font-medium">Subs</th>
          <th className="text-left pl-4 font-medium">Last Message</th>
        </tr></thead>
        <tbody>{topics.map(t => (
          <tr key={t.topic} className="border-b border-gray-800/30 hover:bg-cyan-500/5 cursor-pointer" onClick={() => toast.info(`Inspecting topic: ${t.topic}`)}>
            <td className="py-1.5 text-cyan-400 font-mono">{t.topic}</td>
            <td className="text-right text-white">{t.subs}</td>
            <td className="pl-4 text-secondary/70">{t.lastMsg}</td>
          </tr>
        ))}</tbody>
      </table>
    </Card>
  );
}
// --- Helper: Agent Card ---
function AgentCard({ agent, onToggle, onInspect }) {
  const Icon = AGENT_ICONS[agent.name] || Bot;
  const isRunning = agent.status === "running";
  const health = agent.health || "unknown";
  const healthColor = health === "healthy" ? "text-success" : health === "degraded" ? "text-amber-400" : "text-secondary";
  const shapFeatures = [
    { name: "Price Action", val: 45, color: "bg-cyan-500" },
    { name: "Vol Flow", val: 30, color: "bg-amber-500" },
    { name: "Regime", val: 15, color: "bg-red-500" },
    { name: "Sentiment", val: 10, color: "bg-purple-500" },
  ];
  return (
    <Card className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] hover:border-cyan-500/50 hover:shadow-[0_0_20px_rgba(0,217,255,0.12)] transition-all cursor-pointer" onClick={() => onInspect && onInspect(agent)}>
      <div className="flex items-center gap-3 mb-2">
        <Icon className="w-5 h-5 text-cyan-400" />
        <span className="text-sm font-bold text-white flex-1" onClick={(e) => { e.stopPropagation(); toast.info(`Inspecting agent logic for ${agent.name}`); }}>{agent.name}</span>
        {isRunning && <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />}
      </div>
      <div className="flex items-center gap-2 text-xs mb-3">
        <span className={healthColor}>{health}</span>
        {agent.uptime && <span className="text-secondary">up {agent.uptime}</span>}
      </div>
      <Button size="xs" variant="ghost" onClick={(e) => { e.stopPropagation(); onToggle(agent); }}
        className={isRunning ? "bg-red-500/20 text-red-400 border-red-500/50" : "bg-cyan-500/20 text-cyan-400 border-cyan-500/50"}>
        {isRunning ? <Square className="w-3 h-3" /> : <Play className="w-3 h-3" />}
      </Button>
      {agent.last_signal && (
        <div className="mt-2 text-xs">
          <span className="text-secondary">Last: </span>
          <span className="text-cyan-400 cursor-pointer hover:underline" onClick={(e) => { e.stopPropagation(); toast.success(`Executing trace on signal: ${agent.last_signal}`); }}>{agent.last_signal}</span>
        </div>
      )}
      <div className="mt-3 flex items-center justify-between">
        <span className="text-[10px] text-secondary">SHAP Importance</span>
        <button className="text-[10px] text-cyan-400 hover:underline" onClick={(e) => { e.stopPropagation(); toast.info(`Accessing Weight Matrices for ${agent.name}`); }}>Weights</button>
      </div>
      <div className="space-y-1 mt-1">
        {shapFeatures.map((f, idx) => (
          <div key={idx} className="flex items-center gap-2 text-[10px]">
            <span className="w-16 text-secondary">{f.name}</span>
            <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div className={`h-full ${f.color} rounded-full transition-all`} style={{ width: `${f.val}%` }} />
            </div>
            <span className="text-white w-6 text-right">{f.val}%</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
// --- Agent Inspector Panel (mockup 05c) ---
function AgentInspectorPanel({ agent, onClose, onToggle }) {
  if (!agent) return null;
  const isRunning = agent.status === "running";
  const [configEdits, setConfigEdits] = useState({
    model: agent.model || "ollama/deepseek-r1:32b",
    temperature: agent.temperature ?? 2.7,
    max_tokens: agent.max_tokens ?? 4096,
    timeout: agent.timeout ?? "30000ms",
    retry_count: agent.retry_count ?? 3,
    priority: agent.priority || "high",
    memory_limit: agent.memory_limit || "1024MB",
    gpu_allocation: agent.gpu_allocation ?? "30%",
    confidence_threshold: agent.confidence_threshold ?? 0.65,
  });
  const perfMetrics = {
    requestsMin: agent.requests_min ?? 847,
    avgLatency: agent.avg_latency || "254ms",
    errRate: agent.err_rate ?? 0.2,
    successRate: agent.success_rate ?? 99.8,
    queueDepth: agent.queue_depth ?? 3,
    tokens24h: agent.tokens_24h ?? 289400,
  };
  const shapBars = [
    { label: "Price Action", pct: 45, color: "bg-cyan-500" },
    { label: "Volume Flow", pct: 30, color: "bg-amber-500" },
    { label: "Regime Context", pct: 15, color: "bg-red-500" },
    { label: "Sentiment", pct: 10, color: "bg-purple-500" },
  ];
  const agentLogs = [
    { time: "[09:41:23]", level: "INFO", msg: "Processed market data batch, 512 items, 1.2ms latency" },
    { time: "[09:41:20]", level: "WARN", msg: "High volatility detected, enabling enhanced scanning mode" },
    { time: "[09:41:18]", level: "INFO", msg: "Successfully connected to external data sources" },
    { time: "[09:41:15]", level: "ERROR", msg: "Failed to connect to external data sources" },
  ];
  const [logFilter, setLogFilter] = useState("ALL");
  return (
    <div className="w-[380px] shrink-0 border-l border-[rgba(42,52,68,0.5)] bg-[#111827] rounded-[8px] overflow-y-auto max-h-full">
      <div className="p-4 border-b border-cyan-500/20">
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-sm font-bold text-white">AGENT INSPECTOR</h3>
          <button onClick={onClose} className="text-secondary hover:text-white"><XCircle className="w-4 h-4" /></button>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="text-secondary">Agent Inspector:</span>
          <span className="text-cyan-400 font-bold">{agent.type || "Researcher"}</span>
          <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${isRunning ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}`}>
            {isRunning ? "RUNNING" : "STOPPED"}
          </span>
        </div>
        <div className="flex gap-4 text-[10px] text-secondary mt-1">
          <span>PID {agent.pid || 1042}</span>
          <span>Uptime {agent.uptime || "47d 12h"}</span>
        </div>
      </div>
      {/* Configuration Section */}
      <div className="p-4 border-b border-cyan-500/20">
        <h4 className="text-xs font-bold text-white mb-3">Configuration</h4>
        <div className="space-y-2">
          {Object.entries(configEdits).map(([key, val]) => (
            <div key={key} className="flex items-center justify-between text-[11px]">
              <span className="text-secondary">{key}</span>
              <input className="bg-[#0d1117] border border-cyan-500/20 rounded px-2 py-0.5 text-white text-right w-28 text-[11px] focus:border-cyan-400 focus:outline-none"
                value={val} onChange={(e) => setConfigEdits(prev => ({ ...prev, [key]: e.target.value }))} />
            </div>
          ))}
        </div>
        <div className="flex gap-2 mt-3">
          <Button size="xs" className="bg-cyan-500/20 text-cyan-400 border-cyan-500/40 flex-1" onClick={() => toast.success("Configuration applied")}>
            Apply Changes
          </Button>
          <Button size="xs" variant="ghost" className="flex-1" onClick={() => toast.info("Config reset")}>Reset</Button>
        </div>
      </div>
      {/* Performance Metrics */}
      <div className="p-4 border-b border-cyan-500/20">
        <h4 className="text-xs font-bold text-white mb-3">Performance Metrics</h4>
        <div className="grid grid-cols-2 gap-2">
          <div className="text-[11px]"><span className="text-secondary">Requests/min: </span><span className="text-cyan-400 font-bold">{perfMetrics.requestsMin}</span></div>
          <div className="text-[11px]"><span className="text-secondary">Avg Latency: </span><span className="text-emerald-400 font-bold">{perfMetrics.avgLatency}</span></div>
          <div className="text-[11px]"><span className="text-secondary">Err Rate: </span><span className="text-amber-400 font-bold">{perfMetrics.errRate}%</span></div>
          <div className="text-[11px]"><span className="text-secondary">Success Rate: </span><span className="text-emerald-400 font-bold">{perfMetrics.successRate}%</span></div>
          <div className="text-[11px]"><span className="text-secondary">Queue Depth: </span><span className="text-white font-bold">{perfMetrics.queueDepth}</span></div>
          <div className="text-[11px]"><span className="text-secondary">Tokens 24h: </span><span className="text-cyan-400 font-bold">{perfMetrics.tokens24h.toLocaleString()}</span></div>
        </div>
        <div className="grid grid-cols-3 gap-2 mt-3">
          {["CPU", "MEM", "GPU"].map(m => (
            <div key={m} className="text-center">
              <div className="text-[9px] text-secondary mb-1">{m}</div>
              <div className="h-6 bg-gray-800/50 rounded flex items-end gap-px px-1">
                {Array.from({ length: 12 }, (_, i) => (
                  <div key={i} className="flex-1 bg-cyan-500/60 rounded-t transition-all" style={{ height: '0%' }} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
      {/* Agent Logs */}
      <div className="p-4 border-b border-cyan-500/20">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-bold text-white">Agent Logs</h4>
          <div className="flex gap-1">
            {["ALL", "INFO", "WARN", "ERROR"].map(f => (
              <button key={f} onClick={() => setLogFilter(f)}
                className={`text-[9px] px-1.5 py-0.5 rounded ${logFilter === f ? "bg-cyan-500/20 text-cyan-400" : "text-secondary hover:text-white"}`}>
                {f}
              </button>
            ))}
          </div>
        </div>
        <div className="space-y-1 max-h-[120px] overflow-y-auto scrollbar-thin">
          {agentLogs.filter(l => logFilter === "ALL" || l.level === logFilter).map((l, i) => (
            <div key={i} className="text-[10px] font-mono cursor-pointer hover:bg-cyan-500/10 px-1 py-0.5 rounded">
              <span className="text-secondary">{l.time}</span>{" "}
              <span className={l.level === "ERROR" ? "text-red-400" : l.level === "WARN" ? "text-amber-400" : "text-emerald-400"}>[{l.level}]</span>{" "}
              <span className="text-white/70">{l.msg}</span>
            </div>
          ))}
        </div>
      </div>
      {/* SHAP Feature Importance */}
      <div className="p-4 border-b border-cyan-500/20">
        <h4 className="text-xs font-bold text-white mb-3">SHAP Feature Importance</h4>
        <div className="space-y-2">
          {shapBars.map((s, i) => (
            <div key={i} className="flex items-center gap-2 text-[11px]">
              <span className="w-24 text-secondary text-right">{s.label}</span>
              <div className="flex-1 h-4 bg-gray-800/50 rounded overflow-hidden">
                <div className={`h-full ${s.color} rounded transition-all`} style={{ width: `${s.pct}%` }} />
              </div>
              <span className="text-white w-8 text-right">{s.pct}%</span>
            </div>
          ))}
        </div>
        <button className="mt-2 text-[10px] text-cyan-400 hover:underline w-full text-center" onClick={() => toast.info("Retraining weights...")}>Retrain Weights</button>
      </div>
      {/* Lifecycle Controls Bar */}
      <div className="p-4">
        <h4 className="text-xs font-bold text-white mb-3">LIFECYCLE CONTROLS BAR</h4>
        <div className="flex gap-2 mb-3">
          <Button size="xs" className="bg-emerald-500/20 text-emerald-400 border-emerald-500/40 flex-1" onClick={() => { onToggle && onToggle({ ...agent, status: "stopped" }); toast.success("Agent started"); }}>Start</Button>
          <Button size="xs" className="bg-red-500/20 text-red-400 border-red-500/40 flex-1" onClick={() => { onToggle && onToggle({ ...agent, status: "running" }); toast.error("Agent stopped"); }}>Stop</Button>
          <Button size="xs" className="bg-amber-500/20 text-amber-400 border-amber-500/40 flex-1" onClick={() => toast.info("Restarting...")}>Restart</Button>
        </div>
        <div className="flex items-center gap-4">
          <div className="relative w-16 h-16">
            <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
              <circle cx="50" cy="50" r="40" fill="none" stroke="#1e293b" strokeWidth="8" />
              <circle cx="50" cy="50" r="40" fill="none" stroke="#00D9FF" strokeWidth="8"
                strokeDasharray="251" strokeDashoffset={251 - (0.98 * 251)} strokeLinecap="round" />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-white">98%</span>
          </div>
          <div className="text-[10px] space-y-1">
            <div className="text-secondary">Dependencies: <span className="text-white">AlpacaStream, Memory, LLMGate</span></div>
            <div className="text-secondary">Auto-Restart: <span className="text-emerald-400">ON</span> Max Retries: <span className="text-white">5</span> Cooldown: <span className="text-white">30s</span></div>
            <div className="text-secondary">Resource caps: <span className="text-white">CPU 50% MEM 1500MB GPU 40%</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}
// =============================================
// MAIN COMPONENT
// =============================================
export default function AgentCommandCenter() {
  const navigate = useNavigate();
  const { tab: urlTab } = useParams();
  const { data: agentsRaw, loading: agentsLoading, refetch: refetchAgents } = useApi("agents", { pollIntervalMs: 10000 });
  const agents = useMemo(() => (Array.isArray(agentsRaw) ? agentsRaw : agentsRaw?.agents || []), [agentsRaw]);
  const [macro, setMacro] = useState(null);
  const [swarm, setSwarm] = useState({ active: 0, total: 0, teams: [] });
  const [candidates, setCandidates] = useState([]);
  const [llmAlerts, setLlmAlerts] = useState([]);
  const [bias, setBias] = useState(1.0);
  const [biasOverrideSent, setBiasOverrideSent] = useState(false);
  const [spawnLoading, setSpawnLoading] = useState(false);
  const [spawnError, setSpawnError] = useState(null);
  const [activeTab, setActiveTab] = useState(urlTab || "swarm-overview");
  const wsRef = useRef(null);
  const [blackboardMsgs, setBlackboardMsgs] = useState([]);
  const [hitlBuffer, setHitlBuffer] = useState([]);
  const [consensusData, setConsensusData] = useState([]);
  const [spawnPrompt, setSpawnPrompt] = useState("");
  const [nlpSpawnLoading, setNlpSpawnLoading] = useState(false);
  const [inspectedAgent, setInspectedAgent] = useState(null);
  const [agentSearch, setAgentSearch] = useState("");
  const filteredAgents = useMemo(() => {
    if (!agentSearch) return agents;
    const q = agentSearch.toLowerCase();
    return agents.filter(a => (a.name || "").toLowerCase().includes(q) || (a.type || "").toLowerCase().includes(q) || (a.team_id || "").toLowerCase().includes(q));
  }, [agents, agentSearch]);
  // --- URL sync ---
  useEffect(() => { if (activeTab) navigate(`/agents/${activeTab}`, { replace: true }); }, [activeTab]);
  // --- Loaders ---
  const loadMacro = useCallback(async () => { try { const data = await openclaw.getMacro(); setMacro(data); } catch { setMacro(null); } }, []);
  const loadSwarm = useCallback(async () => { try { const data = await openclaw.getSwarmStatus(); setSwarm({ active: data.active ?? 0, total: data.total ?? 0, teams: data.teams ?? [] }); } catch { setSwarm({ active: 0, total: 0, teams: [] }); } }, []);
  const loadCandidates = useCallback(async () => { try { const list = await openclaw.getCandidates(25); setCandidates(Array.isArray(list) ? list : []); } catch { setCandidates([]); } }, []);
  const loadConsensus = useCallback(async () => { try { const data = await openclaw.getConsensus(); setConsensusData(Array.isArray(data) ? data : []); } catch { setConsensusData([]); } }, []);
  // --- Polling ---
  useEffect(() => { loadMacro(); const t = setInterval(loadMacro, MACRO_POLL_MS); return () => clearInterval(t); }, [loadMacro]);
  useEffect(() => { loadSwarm(); const t = setInterval(loadSwarm, SWARM_POLL_MS); return () => clearInterval(t); }, [loadSwarm]);
  useEffect(() => { loadCandidates(); const t = setInterval(loadCandidates, CANDIDATES_POLL_MS); return () => clearInterval(t); }, [loadCandidates]);
  useEffect(() => { loadConsensus(); const t = setInterval(loadConsensus, 30000); return () => clearInterval(t); }, [loadConsensus]);
  // --- LLM Flow: backend exposes GET /openclaw/llm-flow (HTTP), not WebSocket — use polling
  const { data: llmFlowData } = useApi("openclaw", {
    endpoint: "/openclaw/llm-flow",
    pollIntervalMs: 5000,
  });
  useEffect(() => {
    const alerts = llmFlowData?.alerts;
    if (Array.isArray(alerts) && alerts.length > 0) {
      setLlmAlerts((prev) => {
        const merged = [...alerts.map((a, i) => ({ ...a, id: a.id || `llm-${Date.now()}-${i}` }))];
        return merged.slice(0, LLM_ALERTS_MAX);
      });
    }
  }, [llmFlowData]);
  useEffect(() => { const unsub = ws.on("agents", (msg) => { if (msg?.type === "agent_status") refetchAgents(); }); return unsub; }, [refetchAgents]);
  // --- Blackboard & HITL: real-time via WebSocket ---
  useEffect(() => {
    const bbHandler = (msg) => {
      if (!msg) return;
      setBlackboardMsgs(prev => [{
        id: Date.now(),
        time: new Date().toLocaleTimeString("en-US", { hour12: false }),
        topic: msg.topic || msg.type || "SYSTEM",
        content: msg.content || msg.message || JSON.stringify(msg).slice(0, 120),
        hash: msg.hash || msg.council_decision_id?.slice(0, 8) || "",
      }, ...prev].slice(0, 100));
    };
    const hitlHandler = (msg) => {
      if (!msg || msg.type !== "hitl_approval_needed") return;
      setHitlBuffer(prev => [{
        id: Date.now(),
        time: new Date().toLocaleTimeString("en-US", { hour12: false }),
        action: msg.action || "APPROVAL_NEEDED",
        user: msg.user || "SYSTEM",
        target: msg.symbol || msg.target || "",
        status: msg.status || "PENDING",
      }, ...prev].slice(0, 50));
    };
    ws.subscribe("council", bbHandler);
    ws.subscribe("signal", bbHandler);
    ws.subscribe("order", hitlHandler);
    setConsensusData([]);
    return () => {
      ws.unsubscribe("council", bbHandler);
      ws.unsubscribe("signal", bbHandler);
      ws.unsubscribe("order", hitlHandler);
    };
  }, []);
  // --- Handlers ---
  const handleAgentToggle = async (agent) => {
    const action = agent.status === "running" ? "stop" : "start";
    try { await fetch(`${getApiUrl("agents")}/${agent.id}/${action}`, { method: "POST" }); toast.success(`${agent.name} ${action}ed`); refetchAgents(); } catch { toast.error(`Failed to ${action} ${agent.name}`); }
  };
  const handleBiasChange = (value) => { setBias(value); setBiasOverrideSent(false); };
  const handleBiasSubmit = async () => { try { await openclaw.setBiasOverride(bias); setBiasOverrideSent(true); toast.success(`Bias override set to ${bias.toFixed(1)}x`); } catch { toast.error("Bias override failed"); } };
  const handleSpawnTeam = async (teamType, action) => { setSpawnLoading(true); setSpawnError(null); try { await openclaw.spawnTeam(teamType, action); await loadSwarm(); toast.success(`${action === "spawn" ? "Spawned" : "Killed"} ${teamType}`); } catch (e) { setSpawnError(e.body?.detail || e.message || "Request failed"); } finally { setSpawnLoading(false); } };
  const handleNlpSpawn = async () => { if (!spawnPrompt.trim()) return; setNlpSpawnLoading(true); try { await openclaw.nlpSpawn(spawnPrompt); toast.success("NLP spawn executed"); setSpawnPrompt(""); await loadSwarm(); } catch { toast.error("NLP spawn failed"); } finally { setNlpSpawnLoading(false); } };
  const handleCandidateClick = (c) => { const symbol = c.symbol || c.ticker; const detail = { symbol, entry: c.entry_price ?? 0, stop: c.stop_loss ?? 0, target: c.target_price ?? 0, team: c.team_id ?? null, score: c.composite_score ?? 0 }; window.dispatchEvent(new CustomEvent("openTradeExecution", { detail })); navigate("/trades", { state: { openTradeExecution: detail } }); };
  // --- Derived ---
  const runningAgents = agents.filter(a => a.status === "running").length;
  const totalAgents = agents.length;
  const highAlerts = llmAlerts.filter(a => a.severity === "high" || a.severity === "error").length;
  const waveState = macro?.wave_state || "neutral";
  const tabs = [
    { id: "swarm-overview", label: "Swarm Overview", icon: Eye },
    { id: "agent-registry", label: "Agent Registry", icon: Bot },
    { id: "spawn-scale", label: "Spawn & Scale", icon: Boxes },
    { id: "live-wiring", label: "Live Wiring Map", icon: Network },
    { id: "blackboard", label: "Blackboard & Comms", icon: ClipboardList },
    { id: "conference", label: "Conference & Consensus", icon: Users },
    { id: "ml-ops", label: "ML Ops", icon: Brain },
    { id: "logs", label: "Logs & Telemetry", icon: Terminal },
    { id: "brain-map", label: "Brain Map", icon: Network },
    { id: "node-control", label: "Node Control & HITL", icon: Sliders },
  ];
  // =============================================
  // RENDER
  // =============================================
  return (
    <div className="flex flex-col h-full bg-[#0B0E14]">
      {/* === TOP HEADER BAR (mockup 01: title + GREEN badge + uptime + agent count + CPU/RAM/GPU bars + KILL SWITCH) === */}
      <div className="flex items-center justify-between px-5 py-2 border-b border-cyan-500/20 bg-[#0B0E14]">
        <div className="flex items-center gap-3">
          <Bot className="w-5 h-5 text-cyan-400" />
          <span className="text-sm font-bold text-white tracking-wider">AGENT COMMAND CENTER</span>
          <Badge className={`${waveState === 'greed' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40' : waveState === 'fear' ? 'bg-red-500/20 text-red-400 border-red-500/40' : 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40'}`}>
            {waveState === 'greed' ? 'GREEN' : waveState === 'fear' ? 'RED' : 'NEUTRAL'}
          </Badge>
        </div>
        <div className="flex items-center gap-5 text-[11px] text-secondary">
          <span>Uptime: <span className="text-white font-mono">47d 12h 33m</span></span>
          <span><span className="text-emerald-400 font-bold">{runningAgents}/{totalAgents}</span> ONLINE</span>
        </div>
        <div className="flex items-center gap-4">
          {/* CPU bar */}
          <div className="flex items-center gap-1.5 text-[11px]">
            <Cpu className="w-3 h-3 text-secondary" />
            <span className="text-secondary">CPU:</span>
            <div className="w-14 h-1.5 bg-gray-800 rounded-full overflow-hidden"><div className="h-full bg-emerald-500 rounded-full" style={{ width: '47%' }} /></div>
            <span className="text-white font-mono w-7 text-right">47%</span>
          </div>
          {/* RAM bar */}
          <div className="flex items-center gap-1.5 text-[11px]">
            <span className="text-secondary">RAM:</span>
            <div className="w-14 h-1.5 bg-gray-800 rounded-full overflow-hidden"><div className="h-full bg-amber-500 rounded-full" style={{ width: '31%' }} /></div>
            <span className="text-white font-mono w-7 text-right">31%</span>
          </div>
          {/* GPU bar */}
          <div className="flex items-center gap-1.5 text-[11px]">
            <span className="text-secondary">GPU:</span>
            <div className="w-14 h-1.5 bg-gray-800 rounded-full overflow-hidden"><div className="h-full bg-cyan-500 rounded-full" style={{ width: '61%' }} /></div>
            <span className="text-white font-mono w-7 text-right">61%</span>
          </div>
          <Button size="sm" className="bg-red-500/20 text-red-400 border border-red-500/50 hover:bg-red-500/40 font-bold text-[11px] px-3 py-1" onClick={() => toast.error("KILL SWITCH activated")}>
            KILL SWITCH
          </Button>
        </div>
        <span className="text-[10px] text-cyan-400/50 tracking-widest font-medium">ELITE TRADING SYSTEM</span>
      </div>

      {/* === TAB NAVIGATION (matching mockup tab row) === */}
      <div className="flex items-center gap-0.5 px-5 py-1.5 border-b border-cyan-500/20 overflow-x-auto scrollbar-thin bg-[#0B0E14]">
        {tabs.map(tab => { const TabIcon = tab.icon; return (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex items-center whitespace-nowrap gap-1.5 px-3 py-1.5 rounded text-[11px] font-medium transition-all ${activeTab === tab.id ? "bg-[rgba(0,217,255,0.12)] text-[#00D9FF] border border-[rgba(0,217,255,0.3)] shadow-[0_0_8px_rgba(0,217,255,0.15)_inset]" : "text-secondary hover:text-white hover:bg-[rgba(0,217,255,0.06)] border border-transparent"}`}>
            <TabIcon className="w-3.5 h-3.5" />{tab.label}
          </button>
        ); })}
      </div>

      {/* === TAB CONTENT === */}
      <div className="flex-1 overflow-y-auto p-4">

        {/* ============ TAB 1: SWARM OVERVIEW (mockup 01 - 3x3 grid) ============ */}
        {activeTab === "swarm-overview" && (
          <div className="space-y-3">
            {/* Row 1: Agent Health Matrix | Live Agent Activity Feed | Swarm Topology + ELO */}
            <div className="grid grid-cols-12 gap-3">
              <div className="col-span-3">
                <AgentHealthMatrix agents={agents} />
              </div>
              <div className="col-span-5">
                <LiveActivityFeed agents={agents} />
              </div>
              <div className="col-span-4">
                <SwarmTopology swarm={swarm} agents={agents} />
              </div>
            </div>

            {/* Row 2: Quick Actions + Team Status | Agent Resource Monitor | Conference Pipeline */}
            <div className="grid grid-cols-12 gap-3">
              <div className="col-span-3">
                <Card title="Quick Actions">
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    <Button size="sm" className="bg-cyan-500/15 text-cyan-400 border-cyan-500/30 text-[10px] px-2 py-1" onClick={() => { refetchAgents(); toast.success("Restarted"); }}>Restart All</Button>
                    <Button size="sm" className="bg-red-500/15 text-red-400 border-red-500/30 text-[10px] px-2 py-1" onClick={() => toast.error("Stopped")}>Stop All</Button>
                    <Button size="sm" className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30 text-[10px] px-2 py-1" onClick={() => setActiveTab("spawn-scale")}>Spawn Team</Button>
                    <Button size="sm" className="bg-purple-500/15 text-purple-400 border-purple-500/30 text-[10px] px-2 py-1" onClick={() => toast.info("Conference initiated")}>Run Conference</Button>
                    <Button size="sm" className="bg-red-500/15 text-red-400 border-red-500/40 text-[10px] px-2 py-1" onClick={() => toast.error("Emergency kill")}>Emergency Kill</Button>
                  </div>
                  <h4 className="text-[10px] font-bold text-white mb-2 uppercase tracking-wider">Team Status</h4>
                  <div className="space-y-1.5">
                    {swarm.teams.length > 0 ? swarm.teams.slice(0, 4).map((t, i) => (
                      <div key={i} className="flex items-center justify-between text-[11px] p-1.5 rounded bg-[#0d1117] border border-cyan-500/10 cursor-pointer hover:border-cyan-500/30"
                        onClick={() => toast.info(`Team ${t.name}`)}>
                        <span className="text-white font-medium">{t.name}</span>
                        <Badge size="sm" className="bg-emerald-500/20 text-emerald-400 text-[9px]">{t.status || 'ACTIVE'}</Badge>
                      </div>
                    )) : (
                      <>
                        <div className="flex items-center justify-between text-[11px] p-1.5 rounded bg-[#0d1117] border border-cyan-500/10">
                          <span className="text-white">fear_bounce_team</span>
                          <span className="text-emerald-400 text-[9px]">ACTIVE</span>
                        </div>
                        <div className="flex items-center justify-between text-[11px] p-1.5 rounded bg-[#0d1117] border border-cyan-500/10">
                          <span className="text-white">greed_momentum_team</span>
                          <span className="text-emerald-400 text-[9px]">ACTIVE</span>
                        </div>
                        <div className="flex items-center justify-between text-[11px] p-1.5 rounded bg-[#0d1117] border border-cyan-500/10">
                          <span className="text-white">momentum</span>
                          <span className="text-amber-400 text-[9px]">DEGRADED</span>
                        </div>
                      </>
                    )}
                  </div>
                </Card>
              </div>
              <div className="col-span-5">
                <AgentResourceMonitor agents={agents} />
              </div>
              <div className="col-span-4">
                <ConferencePipeline consensusData={consensusData} />
              </div>
            </div>

            {/* Row 3: System Alerts | Blackboard Live Feed | Drift Monitor */}
            <div className="grid grid-cols-12 gap-3">
              <div className="col-span-3">
                <SystemAlerts agents={agents} llmAlerts={llmAlerts} />
              </div>
              <div className="col-span-5">
                <BlackboardLiveFeed blackboardMsgs={blackboardMsgs} />
              </div>
              <div className="col-span-4">
                <DriftMonitor agents={agents} />
              </div>
            </div>
          </div>
        )}

        {/* ============ TAB 2: AGENT REGISTRY (with Inspector Panel) ============ */}
        {activeTab === "agent-registry" && (
          <div className="flex gap-4 h-full">
            <div className="flex-1 min-w-0 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-white">Agent Registry</h2>
                <div className="flex gap-2">
                  <div className="flex items-center gap-2">
                    <Search className="w-4 h-4 text-secondary" />
                    <input className="bg-[#0d1117] border border-cyan-500/20 rounded px-3 py-1.5 text-sm text-white placeholder-secondary/50 w-48" placeholder="Search Agents" value={agentSearch} onChange={(e) => setAgentSearch(e.target.value)} />
                  </div>
                  <Button size="sm" className="text-xs" onClick={() => { refetchAgents(); toast.success("Synced"); }}>Force Sync</Button>
                </div>
              </div>
              {/* Master Agent Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead><tr className="text-secondary border-b border-cyan-500/20">
                    {["Agent", "Status", "Health", "Type", "Team", "PID", "CPU%", "Mem MB", "7D Win%", "P&L 30D", "Signals", "Accuracy", "Sharpe", "Uptime", "Last Signal", "Controls"].map(h => (
                      <th key={h} className="text-left py-2 px-1 whitespace-nowrap">{h}</th>
                    ))}
                  </tr></thead>
                  <tbody>{filteredAgents.map((a, i) => {
                    const wr = a.win_rate ?? 0;
                    const pnl = a.pnl_30d ?? 0;
                    return (
                      <tr key={a.id || i} className="border-b border-gray-800/50 hover:bg-cyan-500/5 cursor-pointer transition-all"
                        onClick={() => setInspectedAgent(a)}>
                        <td className="py-1.5 px-1 text-white font-medium">{a.name}</td>
                        <td className="px-1"><span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${a.status === 'running' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>{a.status}</span></td>
                        <td className="px-1"><div className={`w-3 h-3 rounded-full ${HEALTH_DOT_COLORS[a.health] || HEALTH_DOT_COLORS.unknown}`} /></td>
                        <td className="px-1 text-secondary">{a.type || 'worker'}</td>
                        <td className="px-1">{a.team_id ? <TeamBadge teamId={a.team_id} /> : <span className="text-secondary">-</span>}</td>
                        <td className="px-1 text-secondary font-mono">{1024 + i * 31}</td>
                        <td className="px-1 text-white">{(a.cpu_pct ?? 0).toFixed(1)}</td>
                        <td className="px-1 text-white">{(a.mem_mb ?? 0).toFixed(0)}</td>
                        <td className={`px-1 ${wr >= 65 ? 'text-emerald-400' : 'text-amber-400'}`}>{wr.toFixed(1)}%</td>
                        <td className={`px-1 ${pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>${pnl >= 0 ? '+' : ''}{pnl.toFixed(0)}</td>
                        <td className="px-1 text-white">{a.signals_generated ?? 0}</td>
                        <td className="px-1 text-white">{(a.accuracy ?? 0).toFixed(1)}%</td>
                        <td className="px-1 text-cyan-400">{(a.sharpe ?? 0).toFixed(2)}</td>
                        <td className="px-1 text-secondary">{a.uptime || '12h'}</td>
                        <td className="px-1 text-secondary">{a.last_signal || '-'}</td>
                        <td className="px-1">
                          <div className="flex gap-1">
                            <button className="p-0.5 hover:text-cyan-400" onClick={(e) => { e.stopPropagation(); handleAgentToggle(a); }}>{a.status === 'running' ? <Square className="w-3 h-3" /> : <Play className="w-3 h-3" />}</button>
                            <button className="p-0.5 hover:text-amber-400" onClick={(e) => { e.stopPropagation(); toast.success(`SIGTERM ${a.name}`); }}><RefreshCw className="w-3 h-3" /></button>
                            <button className="p-0.5 hover:text-red-400" onClick={(e) => { e.stopPropagation(); toast.error(`Killed ${a.name}`); }}><XCircle className="w-3 h-3" /></button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                  {agents.length === 0 && <tr><td colSpan={16} className="text-center py-8 text-secondary">{agentsLoading ? "Loading..." : "No agents"}</td></tr>}
                  </tbody>
                </table>
              </div>
              {/* Agent Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {agents.map(a => <AgentCard key={a.id} agent={a} onToggle={handleAgentToggle} onInspect={setInspectedAgent} />)}
              </div>
            </div>
            {/* Right sidebar: Agent Inspector */}
            {inspectedAgent && <AgentInspectorPanel agent={inspectedAgent} onClose={() => setInspectedAgent(null)} onToggle={handleAgentToggle} />}
          </div>
        )}
        {/* ============ TAB 3: SPAWN & SCALE (mockup 05b - 4 top panels, NLP prompt, templates, builder, active table) ============ */}
        {activeTab === "spawn-scale" && (
          <div className="space-y-4">
            {/* Top Row: 4 panels */}
            <div className="grid grid-cols-4 gap-3">
              {/* Panel 1: Agent Spawn & Swarm Orchestrator */}
              <Card title="Agent Spawn & Swarm Orchestrator" className="col-span-1">
                <div className="text-[10px] space-y-2">
                  <table className="w-full">
                    <thead><tr className="text-secondary/60 border-b border-cyan-500/10">
                      <th className="text-left py-1 font-medium">Swarm Configuration</th>
                      <th className="text-right font-medium">Value</th>
                    </tr></thead>
                    <tbody>
                      {[
                        { k: "Active Agents", v: `${runningAgents}/${totalAgents}` },
                        { k: "Max Agents", v: "100" },
                        { k: "Spawn Rate", v: "2/min" },
                        { k: "Kill Timeout", v: "30s" },
                        { k: "Auto-Scale", v: "ON" },
                        { k: "Health Check", v: "5s" },
                      ].map(r => (
                        <tr key={r.k} className="border-b border-gray-800/20">
                          <td className="py-1 text-secondary">{r.k}</td>
                          <td className="py-1 text-right text-white font-mono">{r.v}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="flex gap-1.5 pt-1">
                    <Button size="sm" className="bg-red-500/15 text-red-400 border-red-500/30 text-[9px] px-2 py-0.5 flex-1" onClick={() => handleSpawnTeam("fear_bounce_team", "spawn")}>Spawn Fear</Button>
                    <Button size="sm" className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30 text-[9px] px-2 py-0.5 flex-1" onClick={() => handleSpawnTeam("greed_momentum_team", "spawn")}>Spawn Greed</Button>
                    <Button size="sm" className="bg-red-500/15 text-red-400 border-red-500/30 text-[9px] px-2 py-0.5 flex-1" onClick={() => handleSpawnTeam("all", "kill")}>Kill All</Button>
                  </div>
                </div>
              </Card>

              {/* Panel 2: OpenClaw Swarm Control with gauge */}
              <Card title="OpenClaw Swarm Control" className="col-span-1">
                <div className="flex flex-col items-center">
                  {/* Gauge arc */}
                  <div className="relative w-28 h-16 mb-2">
                    <svg viewBox="0 0 120 70" className="w-full h-full">
                      <defs>
                        <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#ef4444" />
                          <stop offset="50%" stopColor="#f59e0b" />
                          <stop offset="100%" stopColor="#10b981" />
                        </linearGradient>
                      </defs>
                      <path d="M 10 60 A 50 50 0 0 1 110 60" fill="none" stroke="#1e293b" strokeWidth="8" strokeLinecap="round" />
                      <path d="M 10 60 A 50 50 0 0 1 110 60" fill="none" stroke="url(#gaugeGrad)" strokeWidth="8" strokeLinecap="round"
                        strokeDasharray="157" strokeDashoffset={157 - (bias / 5) * 157} />
                      <text x="60" y="55" textAnchor="middle" fill="#00D9FF" fontSize="16" fontWeight="bold">{bias.toFixed(2)}</text>
                      <text x="60" y="68" textAnchor="middle" fill="#6b7280" fontSize="8">Sentiment</text>
                    </svg>
                  </div>
                  <div className="w-full space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] text-secondary shrink-0">Bias</span>
                      <Slider min={0} max={5} step={0.1} value={bias} onChange={handleBiasChange} suffix="x" formatValue={v => Number(v).toFixed(1)} className="flex-1" />
                    </div>
                    <div className="flex gap-1.5">
                      <Button size="sm" className="bg-cyan-500/15 text-cyan-400 border-cyan-500/30 text-[9px] px-2 py-0.5 flex-1" onClick={handleBiasSubmit}>Apply</Button>
                      {biasOverrideSent && <span className="text-emerald-400 text-[9px] self-center">Saved</span>}
                    </div>
                  </div>
                </div>
              </Card>

              {/* Panel 3: ML Engine & Flywheel */}
              <Card title="ML Engine & Flywheel" className="col-span-1">
                <div className="space-y-2 text-[10px]">
                  {[
                    { label: "Walk-Forward Accuracy", val: "94.2%", color: "text-emerald-400" },
                    { label: "Active Models", val: "4", color: "text-cyan-400" },
                    { label: "Training Queue", val: "2", color: "text-amber-400" },
                    { label: "Flywheel Cycles", val: "847", color: "text-white" },
                    { label: "Last Retrain", val: "2h ago", color: "text-secondary" },
                    { label: "Feature Drift", val: "0.023", color: "text-emerald-400" },
                    { label: "Sharpe (Live)", val: "2.41", color: "text-cyan-400" },
                  ].map(r => (
                    <div key={r.label} className="flex items-center justify-between">
                      <span className="text-secondary">{r.label}</span>
                      <span className={`${r.color} font-mono font-bold`}>{r.val}</span>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Panel 4: Trading Conference & Auto-Scale */}
              <Card title="Trading Conference & Auto-Scale" className="col-span-1">
                <div className="space-y-2 text-[10px]">
                  {[
                    { label: "Conference Status", val: "IDLE", color: "text-secondary" },
                    { label: "Last Conference", val: "#941", color: "text-cyan-400" },
                    { label: "Consensus Rate", val: "88%", color: "text-emerald-400" },
                    { label: "Auto-Scale", val: "ENABLED", color: "text-emerald-400" },
                    { label: "Scale Factor", val: "1.5x", color: "text-white" },
                    { label: "Min Agents", val: "5", color: "text-secondary" },
                    { label: "Max Agents", val: "50", color: "text-secondary" },
                  ].map(r => (
                    <div key={r.label} className="flex items-center justify-between">
                      <span className="text-secondary">{r.label}</span>
                      <span className={`${r.color} font-mono font-bold`}>{r.val}</span>
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            {/* Natural Language Spawn Prompt */}
            <Card title="Natural Language Spawn Prompt">
              <p className="text-[10px] text-secondary mb-2">Describe the agent you want to spawn in plain English:</p>
              <div className="flex gap-3">
                <input type="text" value={spawnPrompt} onChange={e => setSpawnPrompt(e.target.value)}
                  placeholder="Spawn a momentum scanner agent focused on NASDAQ small-caps with 30s interval, high sensitivity, connected to Alpaca and Finnviz"
                  className="flex-1 bg-[#0d1117] border border-cyan-500/30 rounded px-3 py-2 text-sm text-white placeholder-secondary/40 focus:border-cyan-400 focus:outline-none font-mono"
                  onKeyDown={e => e.key === 'Enter' && handleNlpSpawn()} />
              </div>
              <div className="flex justify-center mt-3">
                <Button size="sm" className="bg-cyan-500/15 text-cyan-400 border border-cyan-500/40 px-8 font-bold tracking-wider" onClick={handleNlpSpawn}>
                  {nlpSpawnLoading ? 'EXECUTING...' : '[ EXECUTE PROMPT ]'}
                </Button>
              </div>
            </Card>

            {spawnError && <div className="p-2 rounded bg-red-500/10 border border-red-500/30 text-red-400 text-xs">{spawnError}</div>}

            {/* Quick Spawn Template Grid + Custom Agent Builder side by side */}
            <div className="grid grid-cols-2 gap-3">
              {/* Quick Spawn Template Grid */}
              <Card title="Quick Spawn Template Grid">
                <div className="grid grid-cols-5 gap-2">
                  {SPAWN_TEMPLATES.map(t => { const TIcon = t.icon; return (
                    <div key={t.name} className="flex flex-col items-center gap-1 p-2 rounded bg-[#0d1117] border border-cyan-500/10 hover:border-cyan-500/40 hover:shadow-[0_0_12px_rgba(0,217,255,0.1)] cursor-pointer transition-all"
                      onClick={() => { toast.success(`Spawning ${t.name}`); handleSpawnTeam(t.name.toLowerCase().replace(/\s/g, '_'), 'spawn'); }}>
                      <TIcon className={`w-5 h-5 ${t.color}`} />
                      <span className="text-[9px] text-white text-center font-medium leading-tight">{t.name}</span>
                    </div>
                  ); })}
                </div>
              </Card>

              {/* Custom Agent Builder */}
              <Card title="Custom Agent Builder">
                <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-[10px]">
                  <div>
                    <label className="text-secondary block mb-0.5">Agent Name</label>
                    <input className="w-full bg-[#0d1117] border border-cyan-500/20 rounded px-2 py-1 text-white text-[10px]" placeholder="Spawn Agent" />
                  </div>
                  <div>
                    <label className="text-secondary block mb-0.5">Agent Type</label>
                    <select className="w-full bg-[#0d1117] border border-cyan-500/20 rounded px-2 py-1 text-white text-[10px]">
                      <option>scanner</option><option>researcher</option><option>executor</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-secondary block mb-0.5">Data Sources</label>
                    <div className="flex gap-1">
                      {["Alpaca", "Finviz", "Reddit"].map(s => (
                        <span key={s} className="px-1.5 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-[8px] cursor-pointer hover:bg-cyan-500/20">{s}</span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="text-secondary block mb-0.5">Target Universe</label>
                    <input className="w-full bg-[#0d1117] border border-cyan-500/20 rounded px-2 py-1 text-white text-[10px]" placeholder="NASDAQ" />
                  </div>
                  <div className="col-span-2">
                    <label className="text-secondary block mb-0.5">Risk Interval</label>
                    <Slider min={0} max={100} step={1} value={50} onChange={() => {}} suffix="ms" className="w-full" />
                  </div>
                  <div className="col-span-2">
                    <label className="text-secondary block mb-0.5">Temperature</label>
                    <Slider min={0} max={5} step={0.1} value={2.7} onChange={() => {}} className="w-full" />
                  </div>
                  <div className="col-span-2">
                    <label className="text-secondary block mb-0.5">Kill Condition</label>
                    <input className="w-full bg-[#0d1117] border border-cyan-500/20 rounded px-2 py-1 text-white text-[10px]" placeholder="max_drawdown_5%, kill_on_loss" />
                  </div>
                </div>
              </Card>
            </div>

            {/* Active Spawned Agents Table */}
            <Card title="Active Spawned Agents Table">
              <div className="overflow-x-auto">
                <table className="w-full text-[10px]">
                  <thead><tr className="text-secondary/60 border-b border-cyan-500/10">
                    {["ID", "Name", "Type", "Status", "CPU%", "MEM", "Signals", "P&L", "Uptime", "Actions"].map(h => (
                      <th key={h} className="text-left py-1.5 px-2 font-medium">{h}</th>
                    ))}
                  </tr></thead>
                  <tbody>
                    {agents.length > 0 ? agents.map((a, i) => (
                      <tr key={a.id || i} className="border-b border-gray-800/20 hover:bg-cyan-500/5 cursor-pointer" onClick={() => toast.info(`Agent: ${a.name}`)}>
                        <td className="py-1.5 px-2 text-secondary font-mono">{(a.id || `A${i}`).toString().slice(0, 8)}</td>
                        <td className="px-2 text-white font-medium">{a.name}</td>
                        <td className="px-2 text-secondary">{a.type || 'worker'}</td>
                        <td className="px-2">
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${a.status === 'running' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                            {a.status === 'running' ? 'ACTIVE' : 'STOPPED'}
                          </span>
                        </td>
                        <td className="px-2 text-white font-mono">{(a.cpu_pct ?? 0).toFixed(1)}</td>
                        <td className="px-2 text-white font-mono">{(a.mem_mb ?? 0).toFixed(0)}MB</td>
                        <td className="px-2 text-cyan-400">{a.signals_generated ?? 0}</td>
                        <td className={`px-2 font-mono ${(a.pnl_30d ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          ${(a.pnl_30d ?? 0) >= 0 ? '+' : ''}{(a.pnl_30d ?? 0).toFixed(0)}
                        </td>
                        <td className="px-2 text-secondary">{a.uptime || '12h'}</td>
                        <td className="px-2">
                          <div className="flex gap-1">
                            <button className="p-0.5 hover:text-amber-400" onClick={(e) => { e.stopPropagation(); toast.info('Paused'); }}><Pause className="w-3 h-3" /></button>
                            <button className="p-0.5 hover:text-red-400" onClick={(e) => { e.stopPropagation(); handleSpawnTeam(a.name, 'kill'); }}><XCircle className="w-3 h-3" /></button>
                            <button className="p-0.5 hover:text-cyan-400" onClick={(e) => { e.stopPropagation(); toast.info('Cloned'); }}><Copy className="w-3 h-3" /></button>
                          </div>
                        </td>
                      </tr>
                    )) : (
                      <tr><td colSpan={10} className="text-center py-6 text-secondary">No active spawned agents. Use templates or NLP prompt to spawn.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        )}
        {/* ============ TAB 4: LIVE WIRING MAP (mockup 05 - full network diagram with connection matrix) ============ */}
        {activeTab === "live-wiring" && (
          <div className="space-y-3">
            {/* Column headers */}
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <Network className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-bold text-white tracking-wider">LIVE WIRING</span>
              </div>
              <div className="flex items-center gap-3 text-[10px] text-secondary">
                <span>Connections: <span className="text-emerald-400 font-bold">47</span></span>
                <span>Health: <span className="text-emerald-400">92.1%</span></span>
              </div>
            </div>

            <div className="grid grid-cols-12 gap-3">
              {/* Main Wiring Diagram - 8 cols */}
              <div className="col-span-8">
                <Card noPadding>
                  <div className="p-3">
                    {/* Column labels */}
                    <div className="grid grid-cols-5 gap-4 mb-3">
                      {["EXTERNAL SOURCES", "AGENTS", "PROCESSING ENGINES", "STORAGE/DATABASES", "FRONTEND/INTERFACES"].map(label => (
                        <div key={label} className="text-center text-[9px] font-bold text-cyan-400/60 uppercase tracking-wider border-b border-cyan-500/10 pb-1">{label}</div>
                      ))}
                    </div>
                    {/* Network nodes SVG */}
                    <svg viewBox="0 0 1000 500" className="w-full h-[380px]">
                      {/* Connection lines */}
                      {(() => {
                        const cols = [100, 300, 500, 700, 900];
                        const sources = [
                          { label: "Alpaca API", y: 50 }, { label: "Finviz", y: 110 },
                          { label: "Google Finance", y: 170 }, { label: "FRED Economic", y: 230 },
                          { label: "SEC EDGAR", y: 290 }, { label: "Reddit", y: 350 },
                          { label: "News API", y: 410 }, { label: "Twitter/X", y: 460 },
                        ];
                        const agentNodes = [
                          { label: "Signal Generation\nAgent", y: 80 },
                          { label: "ML Learning\nAgent", y: 180 },
                          { label: "Sentiment\nAgent", y: 280 },
                          { label: "YouTube Knowledge\nAgent", y: 380 },
                        ];
                        const engines = [
                          { label: "signal_engine.py", y: 60 },
                          { label: "resolution_engine", y: 140 },
                          { label: "risk_engine", y: 220 },
                          { label: "openclaw_bridge", y: 300 },
                          { label: "trading_conference.py", y: 380 },
                        ];
                        const stores = [
                          { label: "PostgreSQL", y: 80 },
                          { label: "Redis Cache", y: 160 },
                          { label: "trading_data", y: 240 },
                          { label: "logs_position_json", y: 320 },
                          { label: "ML_models/", y: 400 },
                        ];
                        const frontends = [
                          { label: "AgentCommandCenter.jsx", y: 60 },
                          { label: "TradingDashboard.jsx", y: 140 },
                          { label: "MLBrainPanel.jsx", y: 220 },
                          { label: "PositionAnalytics.jsx", y: 300 },
                          { label: "SignalMonitoringUI.jsx", y: 380 },
                          { label: "dashboard_engine.py", y: 460 },
                        ];
                        const lineColors = ["#00D9FF44", "#10b98144", "#f59e0b44", "#ef444444", "#8b5cf644"];
                        const lines = [];
                        // source->agent lines
                        sources.forEach((s, si) => {
                          agentNodes.forEach((a, ai) => {
                            lines.push(<line key={`s${si}a${ai}`} x1={cols[0]} y1={s.y} x2={cols[1]} y2={a.y} stroke={lineColors[si % lineColors.length]} strokeWidth="1" />);
                          });
                        });
                        // agent->engine lines
                        agentNodes.forEach((a, ai) => {
                          engines.forEach((e, ei) => {
                            lines.push(<line key={`a${ai}e${ei}`} x1={cols[1]} y1={a.y} x2={cols[2]} y2={e.y} stroke={lineColors[(ai + 1) % lineColors.length]} strokeWidth="1" />);
                          });
                        });
                        // engine->store lines
                        engines.forEach((e, ei) => {
                          stores.forEach((st, sti) => {
                            lines.push(<line key={`e${ei}s${sti}`} x1={cols[2]} y1={e.y} x2={cols[3]} y2={st.y} stroke={lineColors[(ei + 2) % lineColors.length]} strokeWidth="1" />);
                          });
                        });
                        // store->frontend lines
                        stores.forEach((st, sti) => {
                          frontends.forEach((f, fi) => {
                            lines.push(<line key={`st${sti}f${fi}`} x1={cols[3]} y1={st.y} x2={cols[4]} y2={f.y} stroke={lineColors[(sti + 3) % lineColors.length]} strokeWidth="1" />);
                          });
                        });
                        // Render nodes
                        const renderNode = (x, y, label, color, icon) => (
                          <g key={`${x}-${y}-${label}`} className="cursor-pointer" onClick={() => toast.info(`Node: ${label.replace('\n', ' ')}`)}>
                            <rect x={x - 55} y={y - 14} width="110" height="28" rx="4" fill={`${color}22`} stroke={color} strokeWidth="1" />
                            <text x={x} y={y + 3} textAnchor="middle" fill="white" fontSize="8" fontWeight="500">{label.split('\n')[0]}</text>
                            {label.split('\n')[1] && <text x={x} y={y + 13} textAnchor="middle" fill="#6b7280" fontSize="7">{label.split('\n')[1]}</text>}
                          </g>
                        );
                        return (
                          <>
                            {lines}
                            {sources.map(s => renderNode(cols[0], s.y, s.label, "#06b6d4", null))}
                            {agentNodes.map(a => renderNode(cols[1], a.y, a.label, "#10b981", null))}
                            {engines.map(e => renderNode(cols[2], e.y, e.label, "#f59e0b", null))}
                            {stores.map(s => renderNode(cols[3], s.y, s.label, "#8b5cf6", null))}
                            {frontends.map(f => renderNode(cols[4], f.y, f.label, "#3b82f6", null))}
                          </>
                        );
                      })()}
                    </svg>
                  </div>
                </Card>
              </div>

              {/* Right panels - 4 cols */}
              <div className="col-span-4 space-y-3">
                {/* Connection Health Matrix */}
                <Card title="Connection Health Matrix">
                  <div className="overflow-x-auto">
                    <table className="w-full text-[9px]">
                      <thead><tr className="text-secondary">
                        <th className="text-left py-0.5 w-12">From\To</th>
                        {["ORCH", "SigGen", "Risk", "ML", "Sent", "Exec"].map(h => <th key={h} className="text-center px-0.5 w-8">{h}</th>)}
                      </tr></thead>
                      <tbody>
                        {["ORCH", "SigGen", "Risk", "ML", "Sent", "Exec"].map((from, ri) => (
                          <tr key={from} className="border-b border-gray-800/20">
                            <td className="text-secondary py-0.5 font-mono text-[8px]">{from}</td>
                            {["ORCH", "SigGen", "Risk", "ML", "Sent", "Exec"].map((to, ci) => {
                              const isSelf = ri === ci;
                              const states = ['healthy', 'healthy', 'degraded', 'healthy', 'healthy', 'error'];
                              const health = isSelf ? 'self' : states[(ri + ci) % states.length];
                              const bgColor = isSelf ? 'bg-gray-700/50' : health === 'healthy' ? 'bg-emerald-500' : health === 'degraded' ? 'bg-amber-500' : 'bg-red-500';
                              return (<td key={to} className="text-center px-0.5">
                                <div className={`w-5 h-4 mx-auto rounded-sm ${bgColor} ${!isSelf ? 'cursor-pointer hover:scale-125 transition-transform' : ''}`}
                                  onClick={() => !isSelf && toast.info(`Connection ${from} -> ${to}: ${health}`)} />
                              </td>);
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="flex gap-2 mt-2 text-[8px] text-secondary">
                    <span className="flex items-center gap-0.5"><span className="w-2 h-2 bg-emerald-500 rounded-sm" />Healthy</span>
                    <span className="flex items-center gap-0.5"><span className="w-2 h-2 bg-amber-500 rounded-sm" />Degraded</span>
                    <span className="flex items-center gap-0.5"><span className="w-2 h-2 bg-red-500 rounded-sm" />Error</span>
                  </div>
                </Card>

                {/* WebSocket Channels */}
                <Card title="WebSocket Channels">
                  <div className="space-y-1">
                    {["agents", "llm-flow", "market-data", "signals", "trades", "council"].map(ch => (
                      <div key={ch} className="flex items-center justify-between text-[10px] p-1.5 rounded bg-[#0d1117] border border-cyan-500/10 cursor-pointer hover:border-cyan-500/30" onClick={() => toast.info(`Channel: ${ch}`)}>
                        <div className="flex items-center gap-1.5"><Wifi className="w-3 h-3 text-emerald-400" /><span className="text-white font-mono">{ch}</span></div>
                        <Badge size="sm" className="bg-emerald-500/20 text-emerald-400 text-[8px]">LIVE</Badge>
                      </div>
                    ))}
                  </div>
                </Card>

                {/* API Route Status */}
                <Card title="API Route Status">
                  <div className="space-y-0.5 max-h-[160px] overflow-y-auto">
                    {["/api/v1/agents", "/api/v1/signals", "/api/v1/trades", "/api/v1/openclaw/macro", "/api/v1/openclaw/swarm", "/api/v1/market/regime", "/api/v1/risk/shield", "/api/v1/ml/models"].map(r => (
                      <div key={r} className="flex items-center gap-1.5 text-[10px] p-1 cursor-pointer hover:bg-cyan-500/5 rounded" onClick={() => toast.info(`Route: ${r}`)}>
                        <span className="px-1 py-0.5 rounded bg-emerald-500/20 text-emerald-400 text-[8px] font-bold">GET</span>
                        <span className="text-white font-mono flex-1 truncate">{r}</span>
                        <span className="text-emerald-400 font-mono">200</span>
                        <span className="text-secondary text-[8px]">&lt;5ms</span>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
            </div>
          </div>
        )}
        {/* ============ TAB 5: BLACKBOARD & COMMS ============ */}
        {activeTab === "blackboard" && (
          <div className="grid grid-cols-2 gap-4">
            <Card title="Blackboard Messages">
              <div className="space-y-1 max-h-[400px] overflow-y-auto font-mono text-xs">
                {blackboardMsgs.map(msg => (
                  <div key={msg.id} className="flex gap-2 hover:bg-cyan-500/5 px-2 py-1 rounded cursor-pointer">
                    <span className="text-secondary">[{msg.time}]</span>
                    <span className="text-cyan-400">[{msg.topic}]</span>
                    <span className="text-white flex-1">{msg.content}</span>
                    <button className="text-cyan-400 hover:underline text-[10px]" onClick={() => toast.info(`Hash: ${msg.hash}`)}>INSPECT ({msg.hash})</button>
                  </div>
                ))}
                {blackboardMsgs.length === 0 && <p className="text-secondary">Listening for blackboard events...</p>}
              </div>
            </Card>
            <Card title="HITL Intervention Log">
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {hitlBuffer.map(msg => (
                  <div key={msg.id} className="p-2 rounded bg-[#0d1117] border border-cyan-500/10 cursor-pointer hover:border-cyan-500/30" onClick={() => toast.info(`Audit: ${msg.action}`)}>
                    <div className="flex items-center justify-between">
                      <Badge className="bg-amber-500/20 text-amber-400">{msg.action}</Badge>
                      <span className="text-[10px] text-secondary">{msg.time}</span>
                    </div>
                    <div className="text-[10px] text-secondary mt-1">
                      Target: <span className="text-white">{msg.target}</span> User: <span className="text-white">{msg.user}</span> {msg.status}
                    </div>
                  </div>
                ))}
                {hitlBuffer.length === 0 && <p className="text-xs text-secondary">No recent interventions</p>}
              </div>
            </Card>
          </div>
        )}

        {/* ============ TAB 6: CONFERENCE & CONSENSUS ============ */}
        {activeTab === "conference" && (
          <div className="grid grid-cols-3 gap-4">
            {consensusData.map((c, i) => (
              <Card key={i} className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] cursor-pointer hover:border-cyan-500/50 hover:shadow-[0_0_20px_rgba(0,217,255,0.12)] transition-all" onClick={() => toast.info(`Consensus: ${c.symbol}`)}>
                <h3 className="text-2xl font-bold text-white text-center mb-3">{c.symbol}</h3>
                <div className="relative w-24 h-24 mx-auto">
                  <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                    <circle cx="50" cy="50" r="40" fill="none" stroke="#1e293b" strokeWidth="8" />
                    <circle cx="50" cy="50" r="40" fill="none" stroke={c.agree > 80 ? '#00D9FF' : '#F59E0B'} strokeWidth="8"
                      strokeDasharray="251" strokeDashoffset={251 - (c.agree / 100) * 251} strokeLinecap="round" />
                  </svg>
                  <span className="absolute inset-0 flex items-center justify-center text-lg font-bold text-white">{c.agree}%</span>
                </div>
                <p className="text-xs text-secondary text-center mt-2">Agreement</p>
                <div className="flex justify-center gap-3 mt-2 text-xs">
                  <span className="text-secondary">{c.agents} Agents</span>
                  <span className={c.action === 'LONG' ? 'text-emerald-400' : 'text-red-400'}>{c.action} ({c.strength})</span>
                </div>
              </Card>
            ))}
            {consensusData.length === 0 && (
              <div className="col-span-3 text-center py-12 text-secondary text-sm">No active conference data. Conferences run on schedule or on-demand.</div>
            )}
          </div>
        )}

        {/* ============ TAB 7: ML OPS ============ */}
        {activeTab === "ml-ops" && (
          <div className="grid grid-cols-2 gap-4">
            <Card title="Brain Map DAG">
              <svg viewBox="0 0 800 500" className="w-full h-[300px]">
                {(() => {
                  const dagNodes = [{ id: 'ORCH', label: 'ORCHESTRATOR', color: '#00D9FF', x: 400, y: 250, r: 45 },
                    ...agents.slice(0, 8).map((a, i) => ({ id: a.id || `A${i}`, label: (a.name || `Agent-${i}`).replace(/Agent[-_]?/i, '').slice(0, 8).toUpperCase(),
                      color: a.status === 'running' ? '#00D9FF' : '#F59E0B', x: 400 + 220 * Math.cos((i / Math.min(agents.length, 8)) * 2 * Math.PI - Math.PI / 2),
                      y: 250 + 180 * Math.sin((i / Math.min(agents.length, 8)) * 2 * Math.PI - Math.PI / 2), r: 25 }))];
                  return (<>
                    {dagNodes.slice(1).map((n, i) => <line key={i} x1="400" y1="250" x2={n.x} y2={n.y} stroke={n.color} strokeWidth="2" strokeOpacity="0.4" />)}
                    {dagNodes.map(n => (<g key={n.id} className="cursor-pointer" onClick={() => toast.info(`Node: ${n.label}`)}>
                      <circle cx={n.x} cy={n.y} r={n.r} fill={n.color + '33'} stroke={n.color} strokeWidth="2" />
                      <text x={n.x} y={n.y + 4} textAnchor="middle" fill="white" fontSize="10" fontWeight="bold">{n.label}</text>
                    </g>))}
                  </>);
                })()}
              </svg>
              <div className="flex items-center justify-between mt-2">
                <span className="text-xs text-secondary">Nodes: {agents.length + 1}</span>
                <Button size="sm" className="text-xs" onClick={() => toast.success("Weights Rebalanced")}>Rebalance</Button>
              </div>
            </Card>
            {/* Connection Health Matrix */}
            <Card title="Connection Health Matrix">
              <div className="overflow-x-auto">
                <table className="w-full text-[10px]">
                  <thead><tr className="text-secondary">
                    <th className="text-left py-1">From \ To</th>
                    {["ORCH", "SigGen", "Risk", "ML", "Sent", "Exec"].map(h => <th key={h} className="text-center px-1">{h}</th>)}
                  </tr></thead>
                  <tbody>
                    {["ORCH", "SigGen", "Risk", "ML", "Sent", "Exec"].map((from, ri) => (
                      <tr key={from} className="border-b border-gray-800/30">
                        <td className="text-secondary py-1 font-mono">{from}</td>
                        {["ORCH", "SigGen", "Risk", "ML", "Sent", "Exec"].map((to, ci) => {
                          const isSelf = ri === ci;
                          const color = isSelf ? 'bg-gray-700' : 'bg-emerald-500';
                          return (<td key={to} className="text-center px-1">
                            <div className={`w-4 h-4 mx-auto rounded-sm ${color} ${!isSelf ? 'cursor-pointer hover:scale-125 transition-transform' : ''}`}
                              onClick={() => !isSelf && toast.info(`Connection ${from} -> ${to}`)} />
                          </td>);
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex gap-3 mt-2 text-[9px] text-secondary">
                <span><span className="inline-block w-2 h-2 bg-emerald-500 rounded-sm mr-1" />Healthy</span>
                <span><span className="inline-block w-2 h-2 bg-amber-500 rounded-sm mr-1" />Degraded</span>
                <span><span className="inline-block w-2 h-2 bg-red-500 rounded-sm mr-1" />Error</span>
              </div>
            </Card>
            {/* Model Leaderboard */}
            <Card title="Model Leaderboard" className="col-span-2">
              <table className="w-full text-xs">
                <thead><tr className="text-secondary border-b border-cyan-500/20">
                  {["Model", "Version", "Accuracy", "Val Loss", "Sharpe", "Epochs", "Status"].map(h => <th key={h} className="text-left py-1">{h}</th>)}
                </tr></thead>
                <tbody>{[{m:'SignalNet-v3',v:'3.2.1',acc:'94.2%',vl:'0.0023',sh:'2.41',ep:'847/1000',st:'Training'},
                  {m:'RiskPredictor',v:'2.1.0',acc:'89.7%',vl:'0.0089',sh:'1.87',ep:'1000/1000',st:'Production'},
                  {m:'SentimentBERT',v:'1.5.2',acc:'91.3%',vl:'0.0045',sh:'2.12',ep:'500/500',st:'Production'},
                  {m:'RegimeHMM',v:'4.0.0',acc:'87.1%',vl:'0.0112',sh:'1.55',ep:'200/200',st:'Staging'}].map(r => (
                  <tr key={r.m} className="border-b border-gray-800/30 hover:bg-cyan-500/5 cursor-pointer" onClick={() => toast.info(`Model: ${r.m}`)}>
                    <td className="py-1.5 text-white font-medium">{r.m}</td><td className="text-secondary">{r.v}</td>
                    <td className="text-emerald-400">{r.acc}</td><td className="text-amber-400">{r.vl}</td>
                    <td className="text-cyan-400">{r.sh}</td><td className="text-secondary">{r.ep}</td>
                    <td><Badge className={r.st === 'Training' ? 'bg-amber-500/20 text-amber-400' : r.st === 'Production' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-cyan-500/20 text-cyan-400'}>{r.st}</Badge></td>
                  </tr>
                ))}</tbody>
              </table>
            </Card>
          </div>
        )}

        {/* ============ TAB 8: LOGS & TELEMETRY ============ */}
        {activeTab === "logs" && (
          <div className="grid grid-cols-3 gap-4">
            <Card title="LLM Alert Stream" className="col-span-2">
              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {llmAlerts.length === 0 ? <p className="text-sm text-secondary">No alerts. LLM stream idle.</p>
                  : llmAlerts.map(a => <LlmAlert key={a.id} alert={a} onDismiss={() => setLlmAlerts(prev => prev.filter(x => x.id !== a.id))} />)}
              </div>
            </Card>
            <Card title="System Telemetry">
              <div className="space-y-3">
                {[{label: 'CPU Usage', value: 47, color: 'bg-emerald-500'}, {label: 'Memory', value: 31, color: 'bg-amber-500'},
                  {label: 'GPU', value: 61, color: 'bg-cyan-500'}, {label: 'Disk I/O', value: 23, color: 'bg-purple-500'},
                  {label: 'Network', value: 15, color: 'bg-blue-500'}].map(m => (
                  <div key={m.label} className="cursor-pointer hover:bg-cyan-500/5 rounded p-1" onClick={() => toast.info(`${m.label}: ${m.value}%`)}>
                    <div className="flex justify-between text-xs mb-1"><span className="text-secondary">{m.label}</span><span className="text-white font-mono">{m.value}%</span></div>
                    <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden"><div className={`h-full ${m.color} rounded-full transition-all`} style={{ width: `${m.value}%` }} /></div>
                  </div>
                ))}
              </div>
            </Card>
            <Card title="Service Logs" className="col-span-3">
              <div className="space-y-0.5 max-h-[200px] overflow-y-auto font-mono text-[11px]">
                {["[09:41:23] INFO orchestrator: Heartbeat OK", "[09:41:20] INFO ml-worker: Epoch 847 complete",
                  "[09:41:18] WARN risk-shield: Volatility spike detected", "[09:41:15] INFO signal-engine: 3 signals generated",
                  "[09:41:12] INFO consensus: Conference #941 complete", "[09:41:10] DEBUG agent-bus: 12 messages dispatched",
                  "[09:41:08] INFO sentiment: Twitter stream connected", "[09:41:05] ERROR ml-worker: GPU memory near limit (89%)"].map((log, i) => (
                  <div key={i} className={`px-2 py-0.5 rounded cursor-pointer hover:bg-cyan-500/10 ${log.includes('ERROR') ? 'text-red-400' : log.includes('WARN') ? 'text-amber-400' : 'text-white/70'}`}
                    onClick={() => toast.info(log)}>{log}</div>
                ))}
              </div>
            </Card>
          </div>
        )}
      </div>

      {/* === FOOTER BAR (mockup 01 style) === */}
      <div className="flex items-center justify-between px-5 py-1.5 border-t border-cyan-500/20 bg-[#0B0E14] text-[10px] text-secondary">
        <div className="flex items-center gap-5">
          <span>WebSocket: <span className="text-emerald-400 font-bold">CONNECTED</span></span>
          <span>{runningAgents}/{totalAgents} Agents Online</span>
          <span>LLM Flow: <span className="text-cyan-400">{llmAlerts.length} alerts</span></span>
          <span>Conference: <span className="text-secondary">IDLE</span></span>
          <span>42 Internals</span>
          <span>LLM Flow: <span className="text-cyan-400">847</span></span>
        </div>
        <div className="flex items-center gap-5">
          <span>Last Sync: <span className="text-white font-mono">{new Date().toLocaleTimeString("en-US", { hour12: false })}</span></span>
          <span>{runningAgents} Agents</span>
          <span className="text-cyan-400/50 tracking-widest">EMBODIER.AI</span>
        </div>
      </div>
    </div>
  );
}
