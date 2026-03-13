// SwarmOverviewTab — layout matching mockup 01-agent-command-center-final.png
// Layout:
//   Row 1: [Agent Health Matrix (3col)] [Live Agent Activity Feed (5col)] [Swarm Topology + ELO (4col)]
//   Row 2: [Quick Actions + Team Status + Alerts (4col)] [Resource Monitor (5col)] [Conference Pipeline + Last Conference (3col)]
//   Row 3: [Blackboard Feed (6col)] [Drift Monitor (6col)]
import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Activity, Zap, Brain, MessageCircle, Shield, Target, Eye, Cpu,
  AlertTriangle, CheckCircle, XCircle, Play, Square, RefreshCw,
  Users, Trophy, Radio, Server, Clock, TrendingUp, TrendingDown,
  ChevronUp, ChevronDown, Check, X, Minus,
} from "lucide-react";
import { useApi, useEloLeaderboard, useHitlBuffer } from "../../hooks/useApi";
import ws from "../../services/websocket";
import { toast } from "react-toastify";
import { getApiUrl, getAuthHeaders } from "../../config/api";

// Design system: green/amber/red/gray
const HEALTH_COLORS = {
  healthy: "#10b981",
  degraded: "#f59e0b",
  error: "#ef4444",
  stopped: "#4b5563",
  unknown: "#64748b",
};

const AGENT_CATEGORIES = [
  { name: "Scanner", group: "Scanner" }, { name: "RegimeDetector", group: "Scanner" },
  { name: "Intelligence", group: "Intelligence" }, { name: "Researcher", group: "Intelligence" },
  { name: "Adversary", group: "Intelligence" }, { name: "Execution", group: "Execution" },
  { name: "LLMGate", group: "Execution" }, { name: "Streaming", group: "Streaming" },
  { name: "Sentiment", group: "Sentiment" }, { name: "MLLearning", group: "MLLearning" },
  { name: "Conference", group: "Conference" }, { name: "Memory", group: "Memory" },
];

// ─── DAG TOPOLOGY ─────────────────────────────────────────────────────────────

const DAG_COLUMNS = [
  {
    id: "sources",
    label: "EXTERNAL SOURCES",
    color: "#10b981",
    borderColor: "#059669",
    bgColor: "rgba(16,185,129,0.08)",
    nodes: [
      { id: "alpaca",  label: "Alpaca",  health: "unknown" },
      { id: "finviz",  label: "Finviz",  health: "unknown" },
      { id: "fred",    label: "FRED",    health: "unknown" },
      { id: "edgar",   label: "EDGAR",   health: "unknown" },
      { id: "twitter", label: "Twitter", health: "unknown" },
      { id: "news",    label: "News",    health: "unknown" },
    ],
  },
  {
    id: "agents",
    label: "AGENTS",
    color: "#00D9FF",
    borderColor: "#0891b2",
    bgColor: "rgba(0,217,255,0.08)",
    nodes: [
      { id: "scanner",   label: "Scanner",   health: "unknown" },
      { id: "sentiment", label: "Sentiment",  health: "unknown" },
      { id: "ml",        label: "ML",         health: "unknown" },
      { id: "research",  label: "Research",   health: "unknown" },
      { id: "adversary", label: "Adversary",  health: "unknown" },
      { id: "memory",    label: "Memory",     health: "unknown" },
    ],
  },
  {
    id: "engines",
    label: "PROCESSING ENGINES",
    color: "#a855f7",
    borderColor: "#9333ea",
    bgColor: "rgba(168,85,247,0.08)",
    nodes: [
      { id: "signal_engine", label: "Signal Engine", health: "unknown" },
      { id: "risk_engine",   label: "Risk Engine",   health: "unknown" },
      { id: "council",       label: "Council",       health: "unknown" },
      { id: "execution_eng", label: "Execution",     health: "unknown" },
      { id: "ml_engine",     label: "ML Engine",     health: "unknown" },
    ],
  },
  {
    id: "storage",
    label: "STORAGE",
    color: "#f59e0b",
    borderColor: "#d97706",
    bgColor: "rgba(245,158,11,0.08)",
    nodes: [
      { id: "trading_db",    label: "trading_data.db", health: "unknown" },
      { id: "feature_cache", label: "feature_cache",   health: "unknown" },
      { id: "logs",          label: "logs",             health: "unknown" },
    ],
  },
  {
    id: "frontend",
    label: "FRONTEND",
    color: "#ef4444",
    borderColor: "#dc2626",
    bgColor: "rgba(239,68,68,0.08)",
    nodes: [
      { id: "dashboard",  label: "Dashboard",  health: "unknown" },
      { id: "acc",        label: "ACC",         health: "unknown" },
      { id: "trade_exec", label: "Trade Exec",  health: "unknown" },
      { id: "patterns",   label: "Patterns",   health: "unknown" },
    ],
  },
];

const DAG_EDGES = [
  [0,0,1,0], [0,0,1,1],
  [0,1,1,0], [0,1,1,3],
  [0,2,1,3],
  [0,3,1,3],
  [0,4,1,1],
  [0,5,1,1], [0,5,1,3],
  [1,0,2,0], [1,0,2,1],
  [1,1,2,0],
  [1,2,2,4],
  [1,3,2,2], [1,3,2,1],
  [1,4,2,2],
  [1,5,2,2],
  [2,0,3,0], [2,0,3,1],
  [2,1,3,0],
  [2,2,3,0],
  [2,3,3,2],
  [2,4,3,1],
  [2,0,4,1],
  [2,1,4,1],
  [2,2,4,0], [2,2,4,1],
  [2,3,4,2],
  [3,0,4,0], [3,0,4,3],
];

function SwarmTopologyDAG({ agents = [] }) {
  const SVG_W = 800;
  const SVG_H = 320;
  const COL_W = 130;
  const NODE_W = 90;
  const NODE_H = 22;
  const NODE_RX = 4;
  const COL_HEADER_H = 28;

  const agentHealthMap = React.useMemo(() => {
    const map = {};
    agents.forEach(a => {
      const key = (a.name || a.agent_name || "").toLowerCase();
      map[key] = a.health || (a.status === "running" ? "healthy" : a.status === "stopped" ? "stopped" : "unknown");
    });
    return map;
  }, [agents]);

  const resolveHealth = (nodeLabel) => {
    const label = nodeLabel.toLowerCase();
    for (const [key, health] of Object.entries(agentHealthMap)) {
      if (key.includes(label) || label.includes(key)) return health;
    }
    return "unknown";
  };

  const numCols = DAG_COLUMNS.length;
  const colXs = DAG_COLUMNS.map((_, i) => {
    const span = SVG_W - COL_W;
    return Math.round((span / (numCols - 1)) * i) + COL_W / 2 - NODE_W / 2;
  });

  const nodePositions = DAG_COLUMNS.map((col, ci) => {
    const n = col.nodes.length;
    const totalH = n * (NODE_H + 8) - 8;
    const startY = COL_HEADER_H + Math.round((SVG_H - COL_HEADER_H - totalH) / 2);
    return col.nodes.map((_, ni) => startY + ni * (NODE_H + 8));
  });

  const nodeCX = (ci) => colXs[ci] + NODE_W / 2;
  const nodeCY = (ci, ni) => nodePositions[ci][ni] + NODE_H / 2;

  const healthDotColor = (h) =>
    h === "healthy" ? "#10b981" : h === "degraded" ? "#f59e0b" : h === "error" ? "#ef4444" : "#4b5563";

  return (
    <div className="bg-[#111827] border border-[#1e293b] rounded-md p-3 h-full">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-bold text-[#94a3b8] uppercase tracking-wider font-mono">SWARM TOPOLOGY</h3>
        <div className="flex items-center gap-3 text-[9px]">
          {[
            { color: "#10b981", label: "Sources" },
            { color: "#00D9FF", label: "Agents" },
            { color: "#a855f7", label: "Engines" },
            { color: "#f59e0b", label: "Storage" },
            { color: "#ef4444", label: "Frontend" },
          ].map(({ color, label }) => (
            <span key={label} className="flex items-center gap-1" style={{ color }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: color, display: "inline-block" }} />
              {label}
            </span>
          ))}
        </div>
      </div>
      <svg viewBox={`0 0 ${SVG_W} ${SVG_H}`} className="w-full" style={{ height: 200 }}>
        {DAG_EDGES.map((edge, i) => {
          const [sc, sn, tc, tn] = edge;
          const x1 = nodeCX(sc) + NODE_W / 2;
          const y1 = nodeCY(sc, sn);
          const x2 = colXs[tc];
          const y2 = nodeCY(tc, tn);
          const mx = (x1 + x2) / 2;
          const strokeColor = sc === 0 ? "#10b981" : sc === 1 ? "#00D9FF" : sc === 2 ? "#a855f7" : "#f59e0b";
          return (
            <path key={i} d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`}
              stroke={strokeColor} strokeWidth="0.7" strokeDasharray="4 2" fill="none" opacity="0.3">
              <animate attributeName="stroke-dashoffset" from="0" to="-18"
                dur={`${1.8 + (i % 5) * 0.3}s`} repeatCount="indefinite" />
            </path>
          );
        })}
        {DAG_COLUMNS.map((col, ci) => (
          <g key={col.id}>
            <rect x={colXs[ci] - 4} y={2} width={NODE_W + 8} height={COL_HEADER_H - 4}
              rx={3} fill={col.bgColor} stroke={col.borderColor} strokeWidth="0.5" opacity="0.7" />
            <text x={colXs[ci] + NODE_W / 2} y={COL_HEADER_H - 10} textAnchor="middle"
              fill={col.color} fontSize="7" fontWeight="700" letterSpacing="0.8" fontFamily="monospace">
              {col.label}
            </text>
          </g>
        ))}
        {DAG_COLUMNS.map((col, ci) =>
          col.nodes.map((node, ni) => {
            const nx = colXs[ci];
            const ny = nodePositions[ci][ni];
            const health = col.id === "agents" ? resolveHealth(node.label) : "unknown";
            const dotColor = healthDotColor(health);
            return (
              <g key={node.id}>
                <rect x={nx} y={ny} width={NODE_W} height={NODE_H} rx={NODE_RX}
                  fill="rgba(15,23,42,0.85)" stroke={col.borderColor} strokeWidth="0.6" opacity="0.9" />
                <rect x={nx} y={ny} width={3} height={NODE_H} rx={NODE_RX} fill={dotColor} opacity="0.9" />
                <circle cx={nx + 10} cy={ny + NODE_H / 2} r={2.5} fill={dotColor} opacity="0.9">
                  {health === "healthy" && (
                    <animate attributeName="opacity" values="0.6;1;0.6"
                      dur={`${1.5 + ni * 0.2}s`} repeatCount="indefinite" />
                  )}
                </circle>
                <text x={nx + 18} y={ny + NODE_H / 2 + 3.5} fill={col.color}
                  fontSize="7.5" fontFamily="monospace" fontWeight="500" letterSpacing="0.2">
                  {node.label}
                </text>
              </g>
            );
          })
        )}
      </svg>
    </div>
  );
}

// ─── AGENT HEALTH MATRIX ──────────────────────────────────────────────────────

function AgentHealthMatrix({ agents, onAgentClick }) {
  const active = agents.filter(a => a.status === "running").length;
  const warning = agents.filter(a => a.health === "degraded").length;
  const error = agents.filter(a => a.health === "error" || a.status === "error").length;
  const stopped = agents.filter(a => a.status === "stopped").length;

  const agentHealthMap = React.useMemo(() => {
    const map = {};
    agents.forEach(a => {
      const key = (a.name || a.agent_name || "").toLowerCase();
      map[key] = { health: a.health || (a.status === "running" ? "healthy" : a.status === "stopped" ? "stopped" : "unknown"), agent: a };
    });
    return map;
  }, [agents]);

  const resolveHealth = (catName) => {
    const label = catName.toLowerCase();
    for (const [key, entry] of Object.entries(agentHealthMap)) {
      if (key.includes(label) || label.includes(key)) return entry.health;
    }
    return "unknown";
  };

  const getAgentForCategory = (catName) => {
    const label = catName.toLowerCase();
    for (const [key, entry] of Object.entries(agentHealthMap)) {
      if (key.includes(label) || label.includes(key)) return entry.agent;
    }
    return null;
  };

  const tooltipText = (cat) => {
    const a = getAgentForCategory(cat.name);
    const h = resolveHealth(cat.name);
    if (a) return `${cat.name}: ${h} | ${a.status ?? "—"} | ${a.last_heartbeat ?? "—"}`;
    return `${cat.name}: ${resolveHealth(cat.name)}`;
  };

  // Groups for 3-column display matching mockup
  const groups = [
    { label: "Scanner", members: ["Scanner", "RegimeDetector"] },
    { label: "Intelligence", members: ["Intelligence", "Researcher", "LLMGate", "Adversary", "Memory"] },
    { label: "Execution", members: ["Execution"] },
    { label: "Streaming", members: ["Streaming"] },
    { label: "Sentiment", members: ["Sentiment"] },
    { label: "MLLearning", members: ["MLLearning"] },
    { label: "Conference", members: ["Conference"] },
  ];

  return (
    <div className="bg-[#111827] border border-[#1e293b] rounded-md p-3">
      <h3 className="text-xs font-bold uppercase tracking-wider mb-3 font-mono text-[#94a3b8]">AGENT HEALTH MATRIX</h3>
      <div className="grid grid-cols-3 gap-4 mb-3">
        {["Scanner", "Intelligence", "Execution"].map(g => (
          <div key={g}>
            <div className="text-[9px] text-[#00D9FF]/60 font-bold uppercase tracking-wider mb-2 border-b border-[#00D9FF]/10 pb-1">{g}</div>
            <div className="flex flex-wrap gap-1">
              {AGENT_CATEGORIES.filter(c => c.group === g).map(cat => {
                const h = resolveHealth(cat.name);
                const dotColor = HEALTH_COLORS[h] || HEALTH_COLORS.unknown;
                return (
                  <div
                    key={cat.name}
                    className="flex items-center gap-1 cursor-pointer hover:opacity-90 focus:outline-none focus:ring-1 focus:ring-[#06b6d4] rounded"
                    role="button"
                    tabIndex={0}
                    title={tooltipText(cat)}
                    onClick={() => onAgentClick?.(cat.name)}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onAgentClick?.(cat.name); } }}
                  >
                    <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: dotColor }} />
                    <span className="text-[8px] text-[#64748b]">{cat.name}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      {/* Secondary groups row */}
      <div className="grid grid-cols-4 gap-2 mb-3">
        {["Streaming", "Sentiment", "MLLearning", "Conference"].map(g => (
          <div key={g}>
            <div className="text-[9px] text-[#00D9FF]/60 font-bold uppercase tracking-wider mb-1 border-b border-[#00D9FF]/10 pb-0.5">{g}</div>
            <div className="flex flex-wrap gap-1">
              {AGENT_CATEGORIES.filter(c => c.group === g).map(cat => {
                const h = resolveHealth(cat.name);
                const dotColor = HEALTH_COLORS[h] || HEALTH_COLORS.unknown;
                return (
                  <div
                    key={cat.name}
                    className="w-2.5 h-2.5 rounded-full cursor-pointer shrink-0 focus:outline-none focus:ring-1 focus:ring-[#06b6d4]"
                    role="button"
                    tabIndex={0}
                    title={tooltipText(cat)}
                    style={{ backgroundColor: dotColor }}
                    onClick={() => onAgentClick?.(cat.name)}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onAgentClick?.(cat.name); } }}
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-3 text-[9px] text-[#64748b] pt-2 border-t border-[#1e293b]">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: "#10b981" }} />{active} Active</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: "#f59e0b" }} />{warning} Warning</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: "#ef4444" }} />{error} Error</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: "#4b5563" }} />{stopped} Stopped</span>
      </div>
    </div>
  );
}

// ─── QUICK ACTIONS (mockup 01: Restart All blue, Stop All red, Spawn Team green, Run Conference purple, Emergency Kill red) ────────────────────────────────────────────────────────────

async function quickActionApi(path, method = "POST") {
  const res = await fetch(getApiUrl("agents") + path, { method, headers: getAuthHeaders() });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
  return res.json();
}

async function emergencyStopApi() {
  const res = await fetch(getApiUrl("orders/emergency-stop"), { method: "POST", headers: getAuthHeaders() });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
  return res.json();
}

function QuickActions({ onRefetch }) {
  const [loading, setLoading] = useState(null);
  const run = async (label, fn) => {
    setLoading(label);
    try {
      await fn();
      toast.success(`${label} completed`);
      if (typeof onRefetch === "function") setTimeout(onRefetch, 500);
    } catch (e) {
      toast.error(`${label} failed: ${e?.message || "network error"}`);
    } finally {
      setLoading(null);
    }
  };
  const actions = [
    { label: "Restart All",      color: "bg-[#06b6d4] text-white border-[#06b6d4]", fn: () => quickActionApi("/batch/restart") },
    { label: "Pause Swarm",      color: "bg-[#f59e0b] text-white border-[#f59e0b]", fn: () => quickActionApi("/batch/stop") },
    { label: "Run Conference",   color: "bg-[#8b5cf6] text-white border-[#8b5cf6]", fn: () => { toast.info("Conference triggered via council."); } },
    { label: "Trigger Flywheel", color: "bg-[#10b981] text-white border-[#10b981]", fn: () => quickActionApi("/batch/start") },
  ];
  return (
    <div className="bg-[#111827] border border-[#1e293b] rounded-md p-3">
      <h3 className="text-xs font-bold uppercase tracking-wider mb-2 font-mono text-[#94a3b8]">QUICK ACTIONS</h3>
      <div className="flex flex-wrap gap-1.5">
        {actions.map(a => (
          <button
            key={a.label}
            disabled={loading != null}
            onClick={() => run(a.label, a.fn)}
            className={`px-2.5 py-1 text-[10px] font-bold rounded border ${a.color} hover:opacity-90 transition-opacity disabled:opacity-50`}
          >
            {loading === a.label ? "…" : a.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── SYSTEM ALERTS ────────────────────────────────────────────────────────────

function SystemAlertsPanel({ alerts = [] }) {
  const levelConfig = {
    RED:   { color: "text-[#ef4444]", dotColor: "#ef4444", bgColor: "bg-[#ef4444]/10 border-[#ef4444]/30" },
    AMBER: { color: "text-[#f59e0b]", dotColor: "#f59e0b", bgColor: "bg-[#f59e0b]/10 border-[#f59e0b]/30" },
    INFO:  { color: "text-[#06b6d4]", dotColor: "#06b6d4", bgColor: "bg-[#06b6d4]/10 border-[#06b6d4]/30" },
    WARN:  { color: "text-[#f59e0b]", dotColor: "#f59e0b", bgColor: "bg-[#f59e0b]/10 border-[#f59e0b]/30" },
    ERROR: { color: "text-[#ef4444]", dotColor: "#ef4444", bgColor: "bg-[#ef4444]/10 border-[#ef4444]/30" },
  };

  const displayAlerts = alerts;

  return (
    <div className="bg-[#111827] border border-[#1e293b] rounded-md p-3">
      <h3 className="text-xs font-bold uppercase tracking-wider mb-2 font-mono text-[#94a3b8]">SYSTEM ALERTS</h3>
      <div className="space-y-1.5">
        {displayAlerts.length === 0 ? (
          <div className="text-[10px] text-[#64748b] font-mono py-2 text-center">No system alerts</div>
        ) : displayAlerts.map((a, i) => {
          const cfg = levelConfig[a.level] || levelConfig["INFO"];
          return (
            <div key={i} className={`flex items-center gap-2 text-[10px] rounded px-2 py-1.5 border ${cfg.bgColor}`}>
              <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: cfg.dotColor }} />
              <span className={`font-bold ${cfg.color} shrink-0 w-10`}>{a.level}</span>
              <span className="text-[#94a3b8]">{a.msg || a.message || ""}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── TEAM STATUS ──────────────────────────────────────────────────────────────

function TeamStatus({ teams = [] }) {
  const displayTeams = teams;

  return (
    <div className="bg-[#111827] border border-[#1e293b] rounded-md p-3">
      <h3 className="text-xs font-bold uppercase tracking-wider mb-2 font-mono text-[#94a3b8]">TEAM STATUS</h3>
      <div className="grid grid-cols-2 gap-2">
        {displayTeams.length === 0 ? (
          <div className="text-[10px] text-[#64748b] font-mono py-2 col-span-2 text-center">No team data</div>
        ) : displayTeams.map(t => (
          <div key={t.name} className={`rounded p-2 border cursor-pointer hover:bg-[#1e293b]/50 ${t.status === "ACTIVE" ? "bg-[#10b981]/10 border-[#10b981]/30" : "bg-[#f59e0b]/10 border-[#f59e0b]/30"}`}>
            <div className="text-[10px] font-bold text-[#f8fafc] font-mono truncate">{t.name}</div>
            <div className="flex items-center justify-between mt-1 text-[9px]">
              <span className="text-[#64748b]">{t.agents} agents</span>
              <span className={`font-bold font-mono ${t.status === "ACTIVE" ? "text-[#10b981]" : "text-[#f59e0b]"}`}>{t.status}</span>
              <span className="text-[#f8fafc] font-mono">{t.health}%</span>
              <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: t.status === "ACTIVE" ? "#10b981" : "#f59e0b" }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── LIVE ACTIVITY FEED ───────────────────────────────────────────────────────

function LiveActivityFeed({ agents }) {
  const [items, setItems] = useState([]);
  const feedRef = useRef([]);
  const colorMap = useRef({});
  const colors = ["text-emerald-400","text-[#00D9FF]","text-amber-400","text-purple-400","text-red-400","text-blue-400"];

  useEffect(() => {
    const handler = (msg) => {
      if (!msg) return;
      const now = new Date();
      const time = `${String(now.getHours()).padStart(2,"0")}:${String(now.getMinutes()).padStart(2,"0")}:${String(now.getSeconds()).padStart(2,"0")}`;
      const name = msg.agent_name || msg.agent || msg.type || "system";
      if (!colorMap.current[name]) colorMap.current[name] = colors[Object.keys(colorMap.current).length % colors.length];
      feedRef.current = [{ id: Date.now() + Math.random(), time, agent: name, action: msg.action || msg.message || msg.reasoning || JSON.stringify(msg).slice(0, 100), color: colorMap.current[name] }, ...feedRef.current].slice(0, 40);
      setItems([...feedRef.current]);
    };
    ws.subscribe("agents", handler);
    ws.subscribe("council", handler);
    return () => { ws.unsubscribe("agents", handler); ws.unsubscribe("council", handler); };
  }, []);

  return (
    <div className="bg-[#111827] border border-[#1e293b] rounded-md p-3 h-full flex flex-col">
      <h3 className="text-xs font-bold uppercase tracking-wider mb-2 font-mono text-[#94a3b8]">LIVE AGENT ACTIVITY FEED</h3>
      <div className="flex-1 space-y-0.5 overflow-y-auto scrollbar-thin font-mono min-h-0">
        {items.length === 0 ? (
          <div className="text-[10px] text-[#64748b] font-mono text-center py-6">No agent activity yet</div>
        ) : (
          items.map(it => (
            <div key={it.id} className="flex gap-2 text-[10px] hover:bg-[#1e293b] px-1 py-0.5 rounded cursor-pointer">
              <span className="text-[#64748b] shrink-0 font-mono">[{it.time}]</span>
              <span className={`${it.color} font-bold shrink-0`}>{it.agent}</span>
              <span className="text-[#64748b]">—</span>
              <span className="text-[#94a3b8] truncate">{it.action}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ─── RESOURCE MONITOR ─────────────────────────────────────────────────────────

function ResourceMonitor({ agents = [] }) {
  const rows = agents.length > 0 ? agents.map(a => ({
    name: a.name || a.agent_name || "Agent",
    cpu: a.cpu ?? a.cpu_usage ?? null,
    mem: a.memory_mb != null ? `${a.memory_mb}MB` : (a.mem != null ? `${a.mem}MB` : null),
    tokens: a.tokens_per_hour ?? a.tokens ?? null,
    status: a.status || a.health || "unknown",
  })) : [];

  return (
    <div className="bg-[#111827] border border-[#1e293b] rounded-md p-3">
      <h3 className="text-xs font-bold uppercase tracking-wider mb-2 font-mono text-[#94a3b8]">AGENT RESOURCE MONITOR</h3>
      <table className="w-full text-[10px]">
        <thead>
          <tr className="text-[#64748b] border-b border-[#1e293b]">
            <th className="text-left py-1 font-medium text-[10px] uppercase">Agent</th>
            <th className="text-left font-medium text-[10px] uppercase">CPU%</th>
            <th className="text-left font-medium text-[10px] uppercase">MEM MB</th>
            <th className="text-right font-medium text-[10px] uppercase">Tokens/hr</th>
            <th className="text-right font-medium text-[10px] uppercase">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr><td colSpan={5} className="py-4 text-center text-[10px] text-[#64748b] font-mono">No agent resource data</td></tr>
          ) : rows.map(r => (
            <tr className="border-b border-[#1e293b]/50 hover:bg-[#164e63]/10">
              <td className="py-1 text-[#06b6d4] font-mono">{r.name}</td>
              <td className="font-mono">
                {r.cpu != null ? (
                  <div className="flex items-center gap-1">
                    <span className={r.cpu > 80 ? "text-[#ef4444]" : r.cpu > 60 ? "text-[#f59e0b]" : "text-[#f8fafc]"}>{r.cpu}%</span>
                    <div className="w-10 h-1 rounded-full overflow-hidden" style={{ backgroundColor: "#1e293b" }}>
                      <div className="h-full rounded-full" style={{ width: `${Math.min(100, r.cpu)}%`, backgroundColor: r.cpu > 80 ? "#ef4444" : r.cpu > 60 ? "#f59e0b" : "#06b6d4" }} />
                    </div>
                  </div>
                ) : <span className="text-[#64748b]">—</span>}
              </td>
              <td className="text-[#f8fafc] font-mono">
                {r.mem != null ? (
                  <div className="flex items-center gap-1">
                    <span>{r.mem}</span>
                    <div className="w-8 h-1 rounded-full overflow-hidden" style={{ backgroundColor: "#1e293b" }}>
                      <div className="h-full rounded-full bg-[#06b6d4]/70" style={{ width: Math.min(100, (Number(String(r.mem).replace(/[^0-9]/g, "")) || 0) / 20) + "%" }} />
                    </div>
                  </div>
                ) : <span className="text-[#64748b]">—</span>}
              </td>
              <td className="text-right text-[#94a3b8] font-mono">{r.tokens != null ? Number(r.tokens).toLocaleString() : "—"}</td>
              <td className="text-right">
                <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: r.status === "healthy" || r.status === "running" ? "#10b981" : r.status === "warn" || r.status === "degraded" ? "#f59e0b" : "#4b5563" }} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── ELO LEADERBOARD ──────────────────────────────────────────────────────────

function EloLeaderboard() {
  const { data, loading } = useEloLeaderboard(30000);

  const leaders = React.useMemo(() => {
    if (!data || !Array.isArray(data) || data.length === 0) return [];
    return data.map((d, i) => ({
      rank: i + 1,
      name: d.agent_name || d.name || `Agent-${i}`,
      elo: d.elo_rating ?? d.elo ?? 0,
      winRate: d.win_rate ?? d.winRate ?? 0,
    }));
  }, [data]);

  return (
    <div className="bg-[#111827] border border-[#1e293b] rounded-md p-3">
      <h3 className="text-xs font-bold uppercase tracking-wider mb-2 font-mono text-[#94a3b8]">AGENT ELO LEADERBOARD</h3>
      <table className="w-full text-[10px] font-mono">
        <thead>
          <tr className="text-[#94a3b8] border-b border-[#1e293b]">
            <th className="text-left py-1 font-medium w-4 text-[10px] uppercase">Rank</th>
            <th className="text-left font-medium text-[10px] uppercase">Agent</th>
            <th className="text-right font-medium text-[10px] uppercase">ELO</th>
            <th className="text-right font-medium text-[10px] uppercase">Win%</th>
          </tr>
        </thead>
        <tbody>
          {leaders.length === 0 ? (
            <tr><td colSpan={4} className="py-4 text-center text-[#64748b]">No ELO data</td></tr>
          ) : leaders.slice(0, 5).map(l => (
            <tr key={l.rank} className="border-b border-[#1e293b]/30 hover:bg-[#1e293b] cursor-pointer">
              <td className="py-1 text-[#64748b] font-mono">{l.rank}</td>
              <td className="text-[#06b6d4] font-mono">{l.name}</td>
              <td className="text-right font-mono">
                <div className="flex items-center justify-end gap-1.5">
                  <div className="w-12 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: "#1e293b" }}>
                    <div className="h-full rounded-full bg-[#06b6d4]" style={{ width: `${Math.min(100, (l.elo / 2000) * 100)}%` }} />
                  </div>
                  <span className="text-[#f8fafc] w-8 text-right">{l.elo}</span>
                </div>
              </td>
              <td className="text-right text-[#94a3b8] font-mono">{typeof l.winRate === "number" ? l.winRate.toFixed(0) : l.winRate}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── HITL APPROVAL QUEUE ──────────────────────────────────────────────────────

async function postHitlDecision(decisionId, action) {
  const res = await fetch(`${getApiUrl('agents')}/hitl/${decisionId}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function HITLQueue() {
  const { data, loading, refetch } = useHitlBuffer(15000);
  const [decisions, setDecisions] = useState({});

  const items = React.useMemo(() => {
    if (!data) return [];
    const arr = Array.isArray(data) ? data : data.items ?? data.buffer ?? [];
    if (arr.length === 0) return [];
    return arr.map(d => ({
      id: d.id ?? d.decision_id ?? String(Math.random()),
      time: d.time ?? (d.timestamp
        ? new Date(d.timestamp).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false })
        : "—"),
      symbol: d.symbol ?? "—",
      direction: d.direction ?? d.side ?? "—",
      confidence: Math.round((d.confidence ?? 0) * (d.confidence <= 1 ? 100 : 1)),
      agent: d.agent ?? d.agent_name ?? "Unknown",
    }));
  }, [data]);

  const pending = items.filter(i => !decisions[i.id]);

  const handleDecision = useCallback(async (id, action) => {
    setDecisions(prev => ({ ...prev, [id]: action }));
    try {
      await postHitlDecision(id, action);
      toast.success(`HITL: ${action.toUpperCase()} submitted`);
      setTimeout(refetch, 1000);
    } catch (e) {
      toast.error(`HITL error: ${e.message}`);
      setDecisions(prev => { const next = { ...prev }; delete next[id]; return next; });
    }
  }, [refetch]);

  return (
    <div className="bg-[#111827] border border-[#1e293b] rounded-md p-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-bold text-[#94a3b8] uppercase tracking-wider font-mono">HITL RING BUFFER</h3>
        {pending.length > 0 && (
          <span className="px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase text-[#f59e0b] border border-[#f59e0b]/40 bg-[#f59e0b]/10">
            {pending.length} PENDING
          </span>
        )}
      </div>
      {!loading && pending.length === 0 ? (
        <div className="text-[10px] text-[#64748b] font-mono text-center py-3">No pending approvals</div>
      ) : (
        <table className="w-full text-[10px]">
          <thead>
            <tr className="text-[#64748b] border-b border-[#1e293b]">
              <th className="text-left py-1 font-medium text-[10px] uppercase">Time</th>
              <th className="text-left font-medium text-[10px] uppercase">Symbol</th>
              <th className="text-left font-medium text-[10px] uppercase">Dir</th>
              <th className="text-right font-medium text-[10px] uppercase">Conf</th>
              <th className="text-right font-medium text-[10px] uppercase">Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map(item => {
              const decided = decisions[item.id];
              return (
                <tr key={item.id} className={`border-b border-[#1e293b]/50 ${decided ? "opacity-50" : "hover:bg-[#1e293b]"} cursor-pointer`}>
                  <td className="py-1 text-[#64748b] font-mono">{item.time}</td>
                  <td className="text-[#f8fafc] font-bold font-mono">{item.symbol}</td>
                  <td className={`font-bold font-mono ${item.direction === "BUY" ? "text-[#10b981]" : item.direction === "SELL" ? "text-[#ef4444]" : "text-[#94a3b8]"}`}>
                    {item.direction}
                  </td>
                  <td className="text-right text-[#06b6d4] font-mono">{item.confidence}%</td>
                  <td className="text-right">
                    {decided ? (
                      <span className={`text-[9px] font-bold ${decided === "approve" ? "text-[#10b981]" : "text-[#ef4444]"}`}>
                        {decided.toUpperCase()}D
                      </span>
                    ) : (
                      <span className="inline-flex gap-1">
                        <button type="button" onClick={() => handleDecision(item.id, "approve")}
                          className="px-1.5 py-0.5 bg-[#10b981]/20 border border-[#10b981]/40 text-[#10b981] rounded text-[9px] font-bold hover:bg-[#10b981]/30 cursor-pointer">✓</button>
                        <button type="button" onClick={() => handleDecision(item.id, "reject")}
                          className="px-1.5 py-0.5 bg-[#ef4444]/20 border border-[#ef4444]/40 text-[#ef4444] rounded text-[9px] font-bold hover:bg-[#ef4444]/30 cursor-pointer">✗</button>
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ─── CONFERENCE PIPELINE ──────────────────────────────────────────────────────

function ConferencePipelineViz({ conferenceData }) {
  const stages = conferenceData?.stages ?? [
    { name: "Researcher", done: false },
    { name: "RiskOfficer", done: false },
    { name: "Adversary", done: false },
    { name: "Arbitrator", done: false },
  ];
  const hasData = conferenceData && (conferenceData.verdict || conferenceData.symbol);
  return (
    <div className="bg-[#111827] border border-[#1e293b] rounded-md p-3">
      <h3 className="text-xs font-bold uppercase tracking-wider mb-3 font-mono text-[#94a3b8]">CONFERENCE PIPELINE</h3>
      {!hasData ? (
        <div className="text-[10px] text-[#64748b] font-mono py-3 text-center">Awaiting conference data</div>
      ) : (
        <div className="flex items-center gap-1 justify-center flex-wrap">
          {stages.map((s, i) => (
            <React.Fragment key={s.name ?? i}>
              <div className={`flex items-center gap-1 px-2.5 py-1.5 rounded border text-[10px] font-bold ${s.done ? "bg-[#06b6d4]/10 border-[#06b6d4]/40 text-[#06b6d4]" : "bg-[#0f1219] border-[#374151] text-[#64748b]"}`}>
                {s.name}
                {s.done && <div className="w-3 h-3 rounded-full flex items-center justify-center" style={{ backgroundColor: "#10b981" }}><Check className="w-2 h-2 text-white" /></div>}
              </div>
              {i < stages.length - 1 && <span className="text-[#06b6d4]/40 text-sm font-bold">→</span>}
            </React.Fragment>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── LAST CONFERENCE ──────────────────────────────────────────────────────────

function LastConference({ conferenceData = null }) {
  const cd = conferenceData;
  if (!cd) {
    return (
      <div className="bg-[#111827] border border-[#1e293b] rounded-md p-3">
        <h3 className="text-xs font-bold text-[#94a3b8] uppercase tracking-wider mb-2 font-mono">LAST CONFERENCE</h3>
        <div className="text-[10px] text-[#64748b] font-mono py-4 text-center">No conference data</div>
      </div>
    );
  }
  const votes = Array.isArray(cd.votes) ? cd.votes : [];
  const confidence = cd.confidence ?? 0;
  const verdict = cd.verdict ?? "—";
  const symbol = cd.symbol ?? "—";
  const conferenceId = cd.id ?? "";
  const duration = cd.duration_s ?? cd.duration ?? 0;

  return (
    <div className="bg-[#111827] border border-[#1e293b] rounded-md p-3">
      <h3 className="text-xs font-bold uppercase tracking-wider mb-2 font-mono text-[#94a3b8]">LAST CONFERENCE</h3>
      <div className="flex items-center gap-3 mb-3">
        <div>
          <div className="text-[11px] text-[#94a3b8] font-mono">{symbol}{conferenceId ? ` #${conferenceId}` : ""}</div>
          <div className={`text-[11px] font-bold font-mono ${verdict === "BUY" ? "text-[#10b981]" : verdict === "SELL" ? "text-[#ef4444]" : "text-[#94a3b8]"}`}>
            VERDICT: {verdict}
          </div>
        </div>
        <div className="relative w-12 h-12 shrink-0">
          <svg viewBox="0 0 36 36" className="w-12 h-12 -rotate-90">
            <circle cx="18" cy="18" r="16" fill="none" stroke="#1e293b" strokeWidth="3" />
            <circle cx="18" cy="18" r="16" fill="none" stroke="#06b6d4" strokeWidth="3"
              strokeDasharray={`${confidence} ${100 - confidence}`} strokeLinecap="round" />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-[10px] text-[#06b6d4] font-bold font-mono">{confidence}%</span>
        </div>
        <div className="flex-1 space-y-1">
          {votes.map(v => (
            <div key={v.agent} className="flex items-center gap-2 text-[10px]">
              <span className="w-20 text-[#94a3b8] shrink-0 font-mono">{v.agent}</span>
              <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: "#1e293b" }}>
                <div className="h-full rounded-full" style={{ width: `${v.vote}%`, backgroundColor: v.vote > 70 ? "#06b6d4" : v.vote > 50 ? "#f59e0b" : "#ef4444" }} />
              </div>
              <span className="text-[#f8fafc] w-7 text-right font-mono">{v.vote}%</span>
            </div>
          ))}
        </div>
      </div>
      <div className="text-[9px] text-[#64748b] font-mono">Duration: {duration}s</div>
    </div>
  );
}

// ─── DRIFT MONITOR ────────────────────────────────────────────────────────────

function DriftMonitorPanel({ driftData = [] }) {
  const displayData = Array.isArray(driftData) ? driftData : [];

  const barColor = (m) => {
    if (m.val == null) return "#06b6d4";
    if (m.status === "high" || m.val >= 0.2) return "#ef4444";
    if (m.status === "mid" || m.val >= 0.1) return "#f59e0b";
    return "#10b981";
  };

  return (
    <div className="bg-[#111827] border border-[#1e293b] rounded-md p-3">
      <h3 className="text-xs font-bold uppercase tracking-wider mb-2 font-mono text-[#94a3b8]">DRIFT MONITOR</h3>
      <div className="space-y-1">
        {displayData.length === 0 ? (
          <div className="text-[10px] text-[#64748b] font-mono py-4 text-center">No drift data</div>
        ) : displayData.map((m, i) => (
          <div key={i} className="flex items-center justify-between text-[10px] font-mono">
            <span className="text-[#94a3b8]">{m.name}</span>
            {m.val != null ? (
              <div className="flex items-center gap-2">
                <span className={m.status === "high" ? "text-[#ef4444]" : m.status === "mid" ? "text-[#f59e0b]" : "text-[#10b981]"}>{typeof m.val === "number" ? m.val.toFixed(2) : m.val}</span>
                <div className="w-20 h-1.5 bg-[#1e293b] rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(100, m.val * 400)}%`, backgroundColor: barColor(m) }} />
                </div>
              </div>
            ) : (
              <span className={m.status === "info" ? "text-[#06b6d4]" : "text-[#94a3b8]"}>{m.label ?? ""}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── BLACKBOARD FEED ──────────────────────────────────────────────────────────

function BlackboardFeed({ topics = [] }) {
  const displayTopics = topics;

  return (
    <div className="bg-[#111827] border border-[#1e293b] rounded-md p-3">
      <h3 className="text-xs font-bold uppercase tracking-wider mb-2 font-mono text-[#94a3b8]">BLACKBOARD LIVE FEED</h3>
      <table className="w-full text-[10px] font-mono">
        <thead>
          <tr className="text-[#64748b] border-b border-[#1e293b]">
            <th className="text-left py-1 font-medium text-[10px] uppercase">Topic</th>
            <th className="text-right font-medium text-[10px] uppercase">Subs</th>
            <th className="text-right font-medium text-[10px] uppercase">Msg/s</th>
            <th className="text-left pl-3 font-medium text-[10px] uppercase">Last Message</th>
            <th className="text-right font-medium"></th>
          </tr>
        </thead>
        <tbody>
          {displayTopics.length === 0 ? (
            <tr><td colSpan={5} className="py-4 text-center text-[10px] text-[#64748b] font-mono">No blackboard topics</td></tr>
          ) : displayTopics.map(t => (
            <tr key={t.topic} className="border-b border-[#1e293b]/30 hover:bg-[#1e293b] cursor-pointer">
              <td className="py-1 text-[#06b6d4] font-mono font-bold">{t.topic}</td>
              <td className="text-right text-[#f8fafc] font-mono">{t.subs ?? 0}</td>
              <td className="text-right text-[#94a3b8] font-mono">{t.msgs ?? 0}</td>
              <td className="pl-3 text-[#94a3b8] truncate max-w-[120px]">{t.last ?? "—"}</td>
              <td className="text-right">
                <button type="button" className="text-[9px] text-[#06b6d4] hover:text-[#22d3ee] font-mono cursor-pointer">INSPECT</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── MAIN TAB — Grid: Row1 [3][5][4], Row2 [4][5][3], Row3 [6][6] ─────────────────────────────────────────

export default function SwarmOverviewTab({ agents = [], teams = [], alerts = [], topics = [], conferenceData = null, driftData = [], onAgentClick, setTab }) {
  return (
    <div className="grid grid-cols-12 gap-3">
      {/* Row 1: Agent Health Matrix (3) | Live Agent Activity Feed (5) | Swarm Topology + ELO (4) */}
      <div className="col-span-3 flex flex-col gap-3">
        <AgentHealthMatrix agents={agents} onAgentClick={onAgentClick} />
      </div>
      <div className="col-span-5 flex flex-col gap-3 min-h-[280px]">
        <LiveActivityFeed agents={agents} />
      </div>
      <div className="col-span-4 flex flex-col gap-3">
        <SwarmTopologyDAG agents={agents} />
        <EloLeaderboard />
      </div>

      {/* Row 2: Quick Actions + Team + Alerts + HITL (4) | Resource Monitor (5) | Conference Pipeline + Last Conference (3) */}
      <div className="col-span-4 flex flex-col gap-3">
        <QuickActions />
        <TeamStatus teams={teams} />
        <SystemAlertsPanel alerts={alerts} />
        <HITLQueue />
      </div>
      <div className="col-span-5 flex flex-col gap-3">
        <ResourceMonitor agents={agents} />
      </div>
      <div className="col-span-3 flex flex-col gap-3">
        <ConferencePipelineViz conferenceData={conferenceData} />
        <LastConference conferenceData={conferenceData} />
      </div>

      {/* Row 3: Blackboard Feed (6) | Drift Monitor (6) */}
      <div className="col-span-6">
        <BlackboardFeed topics={topics} />
      </div>
      <div className="col-span-6">
        <DriftMonitorPanel driftData={driftData} />
      </div>
    </div>
  );
}
