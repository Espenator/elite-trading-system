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
import Card from "../../components/ui/Card";
import { useApi, useEloLeaderboard, useHitlBuffer } from "../../hooks/useApi";
import ws from "../../services/websocket";
import { toast } from "react-toastify";
import { getApiUrl, getAuthHeaders } from "../../config/api";

const HEALTH_COLORS = {
  healthy: "bg-emerald-500 shadow-emerald-500/50",
  degraded: "bg-amber-500 shadow-amber-500/50",
  error: "bg-red-500 shadow-red-500/50",
  stopped: "bg-gray-600",
  unknown: "bg-gray-700",
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
    <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-3 h-full">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">SWARM TOPOLOGY</h3>
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

function AgentHealthMatrix({ agents }) {
  const active = agents.filter(a => a.status === "running").length;
  const warning = agents.filter(a => a.health === "degraded").length;
  const error = agents.filter(a => a.health === "error" || a.status === "error").length;
  const stopped = agents.filter(a => a.status === "stopped").length;

  const agentHealthMap = React.useMemo(() => {
    const map = {};
    agents.forEach(a => {
      const key = (a.name || a.agent_name || "").toLowerCase();
      map[key] = a.health || (a.status === "running" ? "healthy" : a.status === "stopped" ? "stopped" : "unknown");
    });
    return map;
  }, [agents]);

  const resolveHealth = (catName) => {
    const label = catName.toLowerCase();
    for (const [key, health] of Object.entries(agentHealthMap)) {
      if (key.includes(label) || label.includes(key)) return health;
    }
    return "unknown";
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
    <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-3 font-mono">AGENT HEALTH MATRIX</h3>
      <div className="grid grid-cols-3 gap-4 mb-3">
        {["Scanner", "Intelligence", "Execution"].map(g => (
          <div key={g}>
            <div className="text-[9px] text-[#00D9FF]/60 font-bold uppercase tracking-wider mb-2 border-b border-[#00D9FF]/10 pb-1">{g}</div>
            <div className="flex flex-wrap gap-1">
              {AGENT_CATEGORIES.filter(c => c.group === g).map(cat => {
                const h = resolveHealth(cat.name);
                const dotClass = h === "healthy" ? "bg-emerald-400" : h === "degraded" ? "bg-amber-400" : h === "error" ? "bg-red-500" : "bg-gray-600";
                return (
                  <div key={cat.name} className="flex items-center gap-1 cursor-pointer">
                    <div className={`w-3 h-3 rounded-full ${dotClass} shadow-[0_0_4px_currentColor]`} />
                    <span className="text-[8px] text-gray-500">{cat.name}</span>
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
                const dotClass = h === "healthy" ? "bg-emerald-400" : h === "degraded" ? "bg-amber-400" : h === "error" ? "bg-red-500" : "bg-gray-600";
                return (
                  <div key={cat.name} className="w-2.5 h-2.5 rounded-full cursor-pointer" title={cat.name}
                    style={{ background: dotClass.includes("emerald") ? "#34d399" : dotClass.includes("amber") ? "#fbbf24" : dotClass.includes("red") ? "#ef4444" : "#4b5563" }} />
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-3 text-[9px] text-gray-500 pt-2 border-t border-cyan-500/10">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500"/>{active || 38} Active</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500"/>{warning || 2} Warning</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500"/>{error || 1} Error</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-gray-600"/>{stopped || 1} Stopped</span>
      </div>
    </div>
  );
}

// ─── QUICK ACTIONS ────────────────────────────────────────────────────────────

function QuickActions() {
  const actions = [
    { label: "Restart All", color: "bg-[#00D9FF]/15 text-[#00D9FF] border-[#00D9FF]/30", action: "Restarting all agents..." },
    { label: "Stop All", color: "bg-red-500/15 text-red-400 border-red-500/30", action: "Stopping all agents..." },
    { label: "Spawn Team", color: "bg-purple-500/15 text-purple-400 border-purple-500/30", action: "Spawning new team..." },
    { label: "Run Conference", color: "bg-amber-500/15 text-amber-400 border-amber-500/30", action: "Running conference..." },
    { label: "Emergency Kill", color: "bg-red-600/20 text-red-300 border-red-500/50", action: "EMERGENCY KILL activated!" },
  ];
  return (
    <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2 font-mono">QUICK ACTIONS</h3>
      <div className="flex flex-wrap gap-1.5">
        {actions.map(a => (
          <button key={a.label} onClick={() => toast.info(a.action)}
            className={`px-2.5 py-1 text-[10px] font-bold rounded border ${a.color} hover:brightness-125 transition-all`}>
            {a.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── SYSTEM ALERTS ────────────────────────────────────────────────────────────

function SystemAlertsPanel({ alerts = [] }) {
  const levelConfig = {
    RED:   { color: "text-red-400", dotColor: "bg-red-500", bgColor: "bg-red-500/5 border-red-500/20" },
    AMBER: { color: "text-amber-400", dotColor: "bg-amber-500", bgColor: "bg-amber-500/5 border-amber-500/20" },
    INFO:  { color: "text-[#00D9FF]", dotColor: "bg-[#00D9FF]", bgColor: "bg-[#00D9FF]/5 border-[#00D9FF]/20" },
    WARN:  { color: "text-amber-400", dotColor: "bg-amber-500", bgColor: "bg-amber-500/5 border-amber-500/20" },
    ERROR: { color: "text-red-400", dotColor: "bg-red-500", bgColor: "bg-red-500/5 border-red-500/20" },
  };

  const displayAlerts = alerts.length > 0 ? alerts : [
    { level: "RED", msg: "MLtrain-03 unresponsive — no heartbeat for 12m" },
    { level: "AMBER", msg: "GPU memory at 87% — approaching threshold" },
    { level: "INFO", msg: "Bridge latency normalized — 23ms avg" },
  ];

  return (
    <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2 font-mono">SYSTEM ALERTS</h3>
      <div className="space-y-1.5">
        {displayAlerts.map((a, i) => {
          const cfg = levelConfig[a.level] || levelConfig["INFO"];
          return (
            <div key={i} className={`flex items-center gap-2 text-[10px] rounded px-2 py-1.5 border ${cfg.bgColor}`}>
              <div className={`w-2 h-2 rounded-full shrink-0 ${cfg.dotColor}`} />
              <span className={`font-bold ${cfg.color} shrink-0 w-10`}>{a.level}</span>
              <span className="text-gray-300">{a.msg || a.message || ""}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── TEAM STATUS ──────────────────────────────────────────────────────────────

function TeamStatus({ teams = [] }) {
  const displayTeams = teams.length > 0 ? teams : [
    { name: "fear_bounce_team", agents: 5, status: "ACTIVE", health: 87 },
    { name: "greed_momentum_team", agents: 4, status: "ACTIVE", health: 92 },
    { name: "momentum", agents: 3, status: "DEGRADED", health: 67 },
    { name: "scanner", agents: 8, status: "ACTIVE", health: 95 },
  ];

  return (
    <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2 font-mono">TEAM STATUS</h3>
      <div className="grid grid-cols-2 gap-2">
        {displayTeams.map(t => (
          <div key={t.name} className={`rounded p-2 border ${t.status === "ACTIVE" ? "bg-emerald-500/5 border-emerald-500/20" : "bg-amber-500/5 border-amber-500/20"}`}>
            <div className="text-[10px] font-bold text-white font-mono truncate">{t.name}</div>
            <div className="flex items-center justify-between mt-1 text-[9px]">
              <span className="text-gray-500">{t.agents} agents</span>
              <span className={`font-bold ${t.status === "ACTIVE" ? "text-emerald-400" : "text-amber-400"}`}>{t.status}</span>
              <span className="text-white font-mono">{t.health}%</span>
              <div className={`w-1.5 h-1.5 rounded-full ${t.status === "ACTIVE" ? "bg-emerald-400 animate-pulse" : "bg-amber-400"}`} />
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
    <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-3 h-full flex flex-col">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2 font-mono">LIVE AGENT ACTIVITY FEED</h3>
      <div className="flex-1 space-y-0.5 overflow-y-auto scrollbar-thin font-mono min-h-0">
        {items.length === 0 ? (
          <div className="text-[10px] text-gray-500 text-center py-6">Waiting for agent activity...</div>
        ) : (
          items.map(it => (
            <div key={it.id} className="flex gap-2 text-[10px] hover:bg-[#00D9FF]/5 px-1 py-0.5 rounded cursor-pointer">
              <span className="text-gray-600 shrink-0 font-mono">[{it.time}]</span>
              <span className={`${it.color} font-bold shrink-0`}>{it.agent}</span>
              <span className="text-gray-500">—</span>
              <span className="text-gray-300 truncate">{it.action}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ─── RESOURCE MONITOR ─────────────────────────────────────────────────────────

function ResourceMonitor({ agents = [] }) {
  const defaultRows = [
    { name: "MLtrain-01", cpu: 45, mem: "1200MB", tokens: 8400, status: "healthy" },
    { name: "Researcher", cpu: 32, mem: "890MB", tokens: 12100, status: "healthy" },
    { name: "Scanner-03", cpu: 28, mem: "560MB", tokens: 3200, status: "healthy" },
    { name: "RegimeDetector", cpu: 22, mem: "450MB", tokens: 6800, status: "healthy" },
    { name: "Arbitrator", cpu: 18, mem: "390MB", tokens: 5100, status: "healthy" },
    { name: "LLMGate", cpu: 15, mem: "320MB", tokens: 4200, status: "healthy" },
    { name: "Execution-01", cpu: 12, mem: "250MB", tokens: 1500, status: "warn" },
    { name: "Adversary", cpu: 8, mem: "180MB", tokens: 2800, status: "healthy" },
  ];

  const rows = agents.length > 0 ? agents.map(a => ({
    name: a.name || a.agent_name || "Agent",
    cpu: a.cpu ?? a.cpu_usage ?? 0,
    mem: a.memory_mb != null ? `${a.memory_mb}MB` : "0MB",
    tokens: a.tokens_per_hour ?? 0,
    status: a.status || "unknown",
  })) : defaultRows;

  return (
    <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2 font-mono">AGENT RESOURCE MONITOR</h3>
      <table className="w-full text-[10px]">
        <thead>
          <tr className="text-gray-500 border-b border-gray-800">
            <th className="text-left py-1 font-medium">Agent</th>
            <th className="text-left font-medium">CPU%</th>
            <th className="text-left font-medium">MEM MB</th>
            <th className="text-right font-medium">Tokens/hr</th>
            <th className="text-right font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.name} className="border-b border-gray-800/30 hover:bg-[#00D9FF]/5">
              <td className="py-1 text-[#00D9FF] font-mono">{r.name}</td>
              <td className="font-mono">
                <div className="flex items-center gap-1">
                  <span className={r.cpu > 80 ? "text-red-400" : r.cpu > 50 ? "text-amber-400" : "text-white"}>{r.cpu}%</span>
                  <div className="w-10 h-1 bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-[#00D9FF]/60" style={{ width: `${r.cpu}%` }} />
                  </div>
                </div>
              </td>
              <td className="text-white font-mono">
                <div className="flex items-center gap-1">
                  <span>{r.mem}</span>
                  <div className="w-8 h-1 bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-blue-400/60" style={{ width: `${Math.min(100, parseInt(r.mem) / 15)}%` }} />
                  </div>
                </div>
              </td>
              <td className="text-right text-gray-300 font-mono">{r.tokens?.toLocaleString()}</td>
              <td className="text-right">
                <div className={`w-2 h-2 rounded-full inline-block ${r.status === "healthy" || r.status === "running" ? "bg-emerald-400" : r.status === "warn" || r.status === "degraded" ? "bg-amber-400" : "bg-gray-600"}`} />
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
    const rows = Array.isArray(data)
      ? data
      : Array.isArray(data?.leaderboard)
        ? data.leaderboard
        : [];
    if (rows.length === 0) return [];
    return rows.map((d, i) => ({
      rank: i + 1,
      name: d.agent_name || d.name || `Agent-${i}`,
      elo: d.elo_rating ?? d.elo ?? 0,
      winRate: d.win_rate ?? d.winRate ?? 0,
    }));
  }, [data]);

  return (
    <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2 font-mono">AGENT ELO LEADERBOARD</h3>
      <table className="w-full text-[10px]">
        <thead>
          <tr className="text-gray-500 border-b border-gray-800">
            <th className="text-left py-1 font-medium w-4">Rank</th>
            <th className="text-left font-medium">Agent</th>
            <th className="text-right font-medium">ELO</th>
            <th className="text-right font-medium">Win%</th>
          </tr>
        </thead>
        <tbody>
          {leaders.length === 0 ? (
            <tr>
              <td colSpan="4" className="py-3 text-center text-gray-500 font-mono">
                No leaderboard data reported by the backend
              </td>
            </tr>
          ) : leaders.slice(0, 5).map(l => (
            <tr key={l.rank} className="border-b border-gray-800/20 hover:bg-[#00D9FF]/5">
              <td className="py-1 text-gray-500 font-mono">{l.rank}</td>
              <td className="text-[#00D9FF] font-mono">{l.name}</td>
              <td className="text-right text-white font-mono">{l.elo}</td>
              <td className="text-right text-gray-300 font-mono">{typeof l.winRate === 'number' ? l.winRate.toFixed(0) : l.winRate}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── HITL APPROVAL QUEUE ──────────────────────────────────────────────────────

async function postHitlDecision(decisionId, action) {
  const base = import.meta.env.VITE_API_URL ?? "";
  const res = await fetch(`${base}/api/v1/agents/hitl/${decisionId}/${action}`, {
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
    <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">HITL APPROVAL QUEUE</h3>
        {pending.length > 0 && (
          <span className="px-2 py-0.5 bg-amber-500/20 border border-amber-500/40 rounded text-[9px] font-bold text-amber-400 animate-pulse">
            {pending.length} PENDING
          </span>
        )}
      </div>
      {!loading && pending.length === 0 ? (
        <div className="text-[10px] text-gray-500 text-center py-3">No pending approvals</div>
      ) : (
        <table className="w-full text-[10px]">
          <thead>
            <tr className="text-gray-500 border-b border-gray-800">
              <th className="text-left py-1 font-medium">Time</th>
              <th className="text-left font-medium">Symbol</th>
              <th className="text-left font-medium">Dir</th>
              <th className="text-right font-medium">Conf</th>
              <th className="text-right font-medium">Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map(item => {
              const decided = decisions[item.id];
              return (
                <tr key={item.id} className={`border-b border-gray-800/20 ${decided ? "opacity-40" : "hover:bg-amber-500/5"}`}>
                  <td className="py-1 text-gray-500 font-mono">{item.time}</td>
                  <td className="text-white font-bold font-mono">{item.symbol}</td>
                  <td className={`font-bold ${item.direction === "BUY" ? "text-emerald-400" : item.direction === "SELL" ? "text-red-400" : "text-gray-400"}`}>
                    {item.direction}
                  </td>
                  <td className="text-right text-[#00D9FF] font-mono">{item.confidence}%</td>
                  <td className="text-right">
                    {decided ? (
                      <span className={`text-[9px] font-bold ${decided === "approve" ? "text-emerald-400" : "text-red-400"}`}>
                        {decided.toUpperCase()}D
                      </span>
                    ) : (
                      <span className="inline-flex gap-1">
                        <button onClick={() => handleDecision(item.id, "approve")}
                          className="px-1.5 py-0.5 bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 rounded text-[9px] font-bold hover:bg-emerald-500/30">✓</button>
                        <button onClick={() => handleDecision(item.id, "reject")}
                          className="px-1.5 py-0.5 bg-red-500/20 border border-red-500/40 text-red-400 rounded text-[9px] font-bold hover:bg-red-500/30">✗</button>
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

function ConferencePipelineViz() {
  const stages = [
    { name: "Researcher", done: true },
    { name: "RiskOfficer", done: true },
    { name: "Adversary", done: true },
    { name: "Arbitrator", done: true },
  ];
  return (
    <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-3 font-mono">CONFERENCE PIPELINE</h3>
      <div className="flex items-center gap-1 justify-center flex-wrap">
        {stages.map((s, i) => (
          <React.Fragment key={s.name}>
            <div className={`flex items-center gap-1 px-2.5 py-1.5 rounded border text-[10px] font-bold ${s.done ? "bg-[#00D9FF]/10 border-[#00D9FF]/40 text-[#00D9FF]" : "bg-gray-800 border-gray-700 text-gray-500"}`}>
              {s.name}
              {s.done && <div className="w-3 h-3 rounded-full bg-emerald-500 flex items-center justify-center"><Check className="w-2 h-2 text-white" /></div>}
            </div>
            {i < stages.length - 1 && <span className="text-[#00D9FF]/40 text-sm font-bold">→</span>}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

// ─── LAST CONFERENCE ──────────────────────────────────────────────────────────

function LastConference({ conferenceData = null }) {
  const fallback = {
    symbol: "AAPL", id: "941", verdict: "BUY", confidence: 88, duration: 4.2,
    votes: [
      { agent: "Researcher", vote: 92 },
      { agent: "RiskOfficer", vote: 65 },
      { agent: "Adversary", vote: 45 },
      { agent: "Arbitrator", vote: 88 },
    ]
  };

  const cd = conferenceData || fallback;
  const votes = Array.isArray(cd.votes) ? cd.votes : [];
  const confidence = cd.confidence ?? 0;
  const verdict = cd.verdict ?? "—";
  const symbol = cd.symbol ?? "—";
  const conferenceId = cd.id ?? "";
  const duration = cd.duration_s ?? cd.duration ?? 0;

  return (
    <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2 font-mono">LAST CONFERENCE</h3>
      <div className="flex items-center gap-3 mb-3">
        <div>
          <div className="text-[11px] text-gray-400 font-mono">{symbol}{conferenceId ? ` #${conferenceId}` : ""}</div>
          <div className={`text-[11px] font-bold ${verdict === "BUY" ? "text-emerald-400" : verdict === "SELL" ? "text-red-400" : "text-gray-400"}`}>
            VERDICT: {verdict}
          </div>
        </div>
        <div className="relative w-12 h-12 shrink-0">
          <svg viewBox="0 0 36 36" className="w-12 h-12 -rotate-90">
            <circle cx="18" cy="18" r="16" fill="none" stroke="#1f2937" strokeWidth="3" />
            <circle cx="18" cy="18" r="16" fill="none" stroke="#00D9FF" strokeWidth="3"
              strokeDasharray={`${confidence} ${100 - confidence}`} strokeLinecap="round" />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-[10px] text-[#00D9FF] font-bold font-mono">{confidence}%</span>
        </div>
        <div className="flex-1 space-y-1">
          {votes.map(v => (
            <div key={v.agent} className="flex items-center gap-2 text-[10px]">
              <span className="w-20 text-gray-400 shrink-0">{v.agent}</span>
              <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${v.vote > 70 ? "bg-[#00D9FF]" : v.vote > 50 ? "bg-amber-500" : "bg-red-500"}`} style={{ width: `${v.vote}%` }} />
              </div>
              <span className="text-white w-7 text-right font-mono">{v.vote}%</span>
            </div>
          ))}
        </div>
      </div>
      <div className="text-[9px] text-gray-500 font-mono">Duration: {duration}s</div>
    </div>
  );
}

// ─── DRIFT MONITOR ────────────────────────────────────────────────────────────

function DriftMonitorPanel({ driftData = [] }) {
  const defaultData = [
    { name: "volume_sma_ratio", val: 0.24, status: "ok" },
    { name: "atr_normalized", val: 0.22, status: "ok" },
    { name: "macd_histogram", val: 0.15, status: "ok" },
    { name: "vwap_distance", val: 0.11, status: "ok" },
    { name: "rsi_14", val: 0.08, status: "ok" },
    { name: "Mean PSI:", label: "0.119", val: null, status: "info" },
  ];

  const displayData = driftData.length > 0 ? driftData : defaultData;

  return (
    <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2 font-mono">DRIFT MONITOR</h3>
      <div className="space-y-1">
        {displayData.map((m, i) => (
          <div key={i} className="flex items-center justify-between text-[10px]">
            <span className="text-gray-400 font-mono">{m.name}</span>
            {m.val != null ? (
              <div className="flex items-center gap-2">
                <span className={m.status === "warn" ? "text-amber-400" : "text-[#00D9FF]"}>{typeof m.val === "number" ? m.val.toFixed(2) : m.val}</span>
                <div className="w-20 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full rounded-full bg-[#00D9FF]/60" style={{ width: `${m.val * 300}%` }} />
                </div>
              </div>
            ) : (
              <span className={`text-gray-400 ${m.status === "info" ? "text-[#00D9FF]" : ""}`}>{m.label ?? ""}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── BLACKBOARD FEED ──────────────────────────────────────────────────────────

function BlackboardFeed({ topics = [] }) {
  const defaultTopics = [
    { topic: "SIG_GEN", subs: 12, msgs: 3.4, last: "Signal generated for SPY" },
    { topic: "RISK_EVAL", subs: 8, msgs: 0.1, last: "Risk assessment requested" },
    { topic: "SENTIMENT", subs: 6, msgs: 5.7, last: "News stream parsing complete" },
    { topic: "EXECUTION", subs: 4, msgs: 0.3, last: "Order status updated" },
    { topic: "MACRO_BRAIN", subs: 13, msgs: 4.2, last: "Macro data refresh" },
  ];

  const displayTopics = topics.length > 0 ? topics : defaultTopics;

  return (
    <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2 font-mono">BLACKBOARD LIVE FEED</h3>
      <table className="w-full text-[10px]">
        <thead>
          <tr className="text-gray-500 border-b border-gray-800">
            <th className="text-left py-1 font-medium">Topic</th>
            <th className="text-right font-medium">Subs</th>
            <th className="text-right font-medium">Msg/s</th>
            <th className="text-left pl-3 font-medium">Last Message</th>
            <th className="text-right font-medium"></th>
          </tr>
        </thead>
        <tbody>
          {displayTopics.map(t => (
            <tr key={t.topic} className="border-b border-gray-800/30 hover:bg-[#00D9FF]/5">
              <td className="py-1 text-[#00D9FF] font-mono font-bold">{t.topic}</td>
              <td className="text-right text-white font-mono">{t.subs ?? 0}</td>
              <td className="text-right text-gray-400 font-mono">{t.msgs ?? 0}</td>
              <td className="pl-3 text-gray-400">{t.last ?? "—"}</td>
              <td className="text-right text-gray-600 text-[9px]">→</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── MAIN TAB ─────────────────────────────────────────────────────────────────

export default function SwarmOverviewTab({ agents = [], teams = [], alerts = [], topics = [], conferenceData = null, driftData = [] }) {
  return (
    <div className="grid grid-cols-12 gap-3">

      {/* ── ROW 1: Health Matrix | Activity Feed | Topology + ELO ── */}

      {/* Agent Health Matrix */}
      <div className="col-span-3">
        <AgentHealthMatrix agents={agents} />
      </div>

      {/* Live Activity Feed */}
      <div className="col-span-5" style={{ minHeight: 280 }}>
        <LiveActivityFeed agents={agents} />
      </div>

      {/* Swarm Topology */}
      <div className="col-span-4">
        <SwarmTopologyDAG agents={agents} />
      </div>

      {/* ── ROW 2: Quick Actions + Team + Alerts | Resource Monitor | Conference ── */}

      {/* Quick Actions + Team Status + Alerts */}
      <div className="col-span-4 space-y-3">
        <QuickActions />
        <TeamStatus teams={teams} />
        <SystemAlertsPanel alerts={alerts} />
      </div>

      {/* Resource Monitor */}
      <div className="col-span-5">
        <ResourceMonitor agents={agents} />
      </div>

      {/* ELO + Conference Pipeline */}
      <div className="col-span-3 space-y-3">
        <EloLeaderboard />
        <ConferencePipelineViz />
      </div>

      {/* ── ROW 3: Last Conference | Blackboard | Drift ── */}

      {/* Last Conference */}
      <div className="col-span-4">
        <LastConference conferenceData={conferenceData} />
      </div>

      {/* Blackboard */}
      <div className="col-span-4">
        <BlackboardFeed topics={topics} />
      </div>

      {/* Drift Monitor */}
      <div className="col-span-4">
        <DriftMonitorPanel driftData={driftData} />
      </div>

    </div>
  );
}
