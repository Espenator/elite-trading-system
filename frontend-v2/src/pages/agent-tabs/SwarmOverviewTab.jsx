// SwarmOverviewTab — upgraded layout matching mockup
// Row 1: Full-width Swarm Topology DAG
// Row 2: [Health + Actions + Alerts (3)] [Activity + Resources (5)] [ELO + HITL (4)]
// Row 3: [Conference Pipeline + Last Conference (6)] [Drift + Blackboard (3)] [Team Status (3)]
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
    color: "#10b981",      // emerald
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
    color: "#06b6d4",      // cyan
    borderColor: "#0891b2",
    bgColor: "rgba(6,182,212,0.08)",
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
    color: "#a855f7",      // purple
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
    color: "#f59e0b",      // amber
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
    color: "#ef4444",      // red
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

// Edges: [sourceColIdx, sourceNodeIdx, targetColIdx, targetNodeIdx]
const DAG_EDGES = [
  // Sources → Agents
  [0,0,1,0], [0,0,1,1], // Alpaca → Scanner, Sentiment
  [0,1,1,0], [0,1,1,3], // Finviz → Scanner, Research
  [0,2,1,3],             // FRED → Research
  [0,3,1,3],             // EDGAR → Research
  [0,4,1,1],             // Twitter → Sentiment
  [0,5,1,1], [0,5,1,3], // News → Sentiment, Research
  // Agents → Engines
  [1,0,2,0], [1,0,2,1], // Scanner → Signal, Risk
  [1,1,2,0],             // Sentiment → Signal
  [1,2,2,4],             // ML → ML Engine
  [1,3,2,2], [1,3,2,1], // Research → Council, Risk
  [1,4,2,2],             // Adversary → Council
  [1,5,2,2],             // Memory → Council
  // Engines → Storage
  [2,0,3,0], [2,0,3,1], // Signal → db, cache
  [2,1,3,0],             // Risk → db
  [2,2,3,0],             // Council → db
  [2,3,3,2],             // Execution → logs
  [2,4,3,1],             // ML Engine → cache
  // Engines → Frontend
  [2,0,4,1],             // Signal → ACC
  [2,1,4,1],             // Risk → ACC
  [2,2,4,0], [2,2,4,1], // Council → Dashboard, ACC
  [2,3,4,2],             // Execution → Trade Exec
  // Storage → Frontend
  [3,0,4,0], [3,0,4,3], // db → Dashboard, Patterns
];

function SwarmTopologyDAG({ agents = [] }) {
  const SVG_W = 800;
  const SVG_H = 400;
  const COL_W = 130;
  const NODE_W = 90;
  const NODE_H = 22;
  const NODE_RX = 4;
  const COL_HEADER_H = 28;

  // Build a health lookup from real agent data keyed by lowercase name fragments
  const agentHealthMap = React.useMemo(() => {
    const map = {};
    agents.forEach(a => {
      const key = (a.name || a.agent_name || "").toLowerCase();
      map[key] = a.health || (a.status === "running" ? "healthy" : a.status === "stopped" ? "stopped" : "unknown");
    });
    return map;
  }, [agents]);

  // Resolve health for a node by matching its label against agent data
  const resolveHealth = (nodeLabel) => {
    const label = nodeLabel.toLowerCase();
    for (const [key, health] of Object.entries(agentHealthMap)) {
      if (key.includes(label) || label.includes(key)) return health;
    }
    return "unknown";
  };

  // Compute column x positions (evenly spaced)
  const numCols = DAG_COLUMNS.length;
  const colXs = DAG_COLUMNS.map((_, i) => {
    const span = SVG_W - COL_W;
    return Math.round((span / (numCols - 1)) * i) + COL_W / 2 - NODE_W / 2;
  });

  // For each column, compute node y positions
  const nodePositions = DAG_COLUMNS.map((col, ci) => {
    const n = col.nodes.length;
    const totalH = n * (NODE_H + 8) - 8;
    const startY = COL_HEADER_H + Math.round((SVG_H - COL_HEADER_H - totalH) / 2);
    return col.nodes.map((_, ni) => startY + ni * (NODE_H + 8));
  });

  // Center x of a node
  const nodeCX = (ci) => colXs[ci] + NODE_W / 2;
  const nodeCY = (ci, ni) => nodePositions[ci][ni] + NODE_H / 2;

  const healthDotColor = (h) =>
    h === "healthy" ? "#10b981" : h === "degraded" ? "#f59e0b" : h === "error" ? "#ef4444" : "#4b5563";

  return (
    <div className="aurora-card p-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider">Swarm Topology</h3>
        <div className="flex items-center gap-3 text-[9px]">
          {[
            { color: "#10b981", label: "External Sources" },
            { color: "#06b6d4", label: "Agents" },
            { color: "#a855f7", label: "Engines" },
            { color: "#f59e0b", label: "Storage" },
            { color: "#ef4444", label: "Frontend" },
          ].map(({ color, label }) => (
            <span key={label} className="flex items-center gap-1" style={{ color }}>
              <span
                style={{ width: 8, height: 8, borderRadius: 2, background: color, display: "inline-block" }}
              />
              {label}
            </span>
          ))}
        </div>
      </div>
      <svg
        viewBox={`0 0 ${SVG_W} ${SVG_H}`}
        className="w-full"
        style={{ height: 220 }}
        aria-label="Swarm topology DAG"
      >
        <defs>
          {/* Animated dash styles per column color */}
          {["#10b981","#06b6d4","#a855f7","#f59e0b"].map((color, idx) => (
            <style key={idx}>{`
              .dash-${idx} {
                stroke: ${color};
                stroke-width: 0.8;
                stroke-dasharray: 4 2;
                fill: none;
                opacity: 0.35;
              }
            `}</style>
          ))}
        </defs>

        {/* Draw edges */}
        {DAG_EDGES.map((edge, i) => {
          const [sc, sn, tc, tn] = edge;
          const x1 = nodeCX(sc) + NODE_W / 2;
          const y1 = nodeCY(sc, sn);
          const x2 = colXs[tc];
          const y2 = nodeCY(tc, tn);
          const mx = (x1 + x2) / 2;
          const strokeColor =
            sc === 0 ? "#10b981" :
            sc === 1 ? "#06b6d4" :
            sc === 2 ? "#a855f7" : "#f59e0b";
          return (
            <path
              key={i}
              d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`}
              stroke={strokeColor}
              strokeWidth="0.7"
              strokeDasharray="4 2"
              fill="none"
              opacity="0.3"
            >
              <animate
                attributeName="stroke-dashoffset"
                from="0"
                to="-18"
                dur={`${1.8 + (i % 5) * 0.3}s`}
                repeatCount="indefinite"
              />
            </path>
          );
        })}

        {/* Draw column header backgrounds */}
        {DAG_COLUMNS.map((col, ci) => (
          <g key={col.id}>
            <rect
              x={colXs[ci] - 4}
              y={2}
              width={NODE_W + 8}
              height={COL_HEADER_H - 4}
              rx={3}
              fill={col.bgColor}
              stroke={col.borderColor}
              strokeWidth="0.5"
              opacity="0.7"
            />
            <text
              x={colXs[ci] + NODE_W / 2}
              y={COL_HEADER_H - 10}
              textAnchor="middle"
              fill={col.color}
              fontSize="7"
              fontWeight="700"
              letterSpacing="0.8"
              fontFamily="monospace"
            >
              {col.label}
            </text>
          </g>
        ))}

        {/* Draw nodes */}
        {DAG_COLUMNS.map((col, ci) =>
          col.nodes.map((node, ni) => {
            const nx = colXs[ci];
            const ny = nodePositions[ci][ni];
            // For agent column nodes, try to resolve health from real agent data
            const health = col.id === "agents" ? resolveHealth(node.label) : "unknown";
            const dotColor = healthDotColor(health);
            return (
              <g key={node.id}>
                {/* Node background */}
                <rect
                  x={nx}
                  y={ny}
                  width={NODE_W}
                  height={NODE_H}
                  rx={NODE_RX}
                  fill="rgba(15,23,42,0.85)"
                  stroke={col.borderColor}
                  strokeWidth="0.6"
                  opacity="0.9"
                />
                {/* Left health border */}
                <rect
                  x={nx}
                  y={ny}
                  width={3}
                  height={NODE_H}
                  rx={NODE_RX}
                  fill={dotColor}
                  opacity="0.9"
                />
                {/* Health dot */}
                <circle
                  cx={nx + 10}
                  cy={ny + NODE_H / 2}
                  r={2.5}
                  fill={dotColor}
                  opacity="0.9"
                >
                  {health === "healthy" && (
                    <animate
                      attributeName="opacity"
                      values="0.6;1;0.6"
                      dur={`${1.5 + ni * 0.2}s`}
                      repeatCount="indefinite"
                    />
                  )}
                </circle>
                {/* Label */}
                <text
                  x={nx + 18}
                  y={ny + NODE_H / 2 + 3.5}
                  fill={col.color}
                  fontSize="7.5"
                  fontFamily="monospace"
                  fontWeight="500"
                  letterSpacing="0.2"
                >
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

  // Build a lookup map from category name to agent health
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

  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-3">Agent Health Matrix</h3>
      <div className="grid grid-cols-3 gap-x-4 mb-2">
        {["Scanner", "Intelligence", "Execution"].map(g => (
          <div key={g} className="text-[9px] text-cyan-400/60 font-bold uppercase tracking-wider text-center border-b border-cyan-500/10 pb-1">{g}</div>
        ))}
      </div>
      <div className="grid grid-cols-5 gap-3 mb-3">
        {AGENT_CATEGORIES.map((cat) => {
          const h = resolveHealth(cat.name);
          return (
            <div key={cat.name} className="flex flex-col items-center gap-1 cursor-pointer hover:scale-110 transition-transform">
              <div className={`w-4 h-4 rounded-full shadow-[0_0_6px] ${HEALTH_COLORS[h] || HEALTH_COLORS.unknown}`} />
              <span className="text-[8px] text-gray-500 leading-none">{cat.name}</span>
            </div>
          );
        })}
      </div>
      <div className="grid grid-cols-4 gap-2 text-[9px] text-gray-500 pt-2 border-t border-cyan-500/10">
        {[["bg-emerald-500", active, "Active"],["bg-amber-500", warning, "Warning"],["bg-red-500", error, "Error"],["bg-gray-600", stopped, "Stopped"]].map(([c,n,l]) => (
          <span key={l} className="flex items-center gap-1"><span className={`w-2 h-2 rounded-full ${c}`}/>{n} {l}</span>
        ))}
      </div>
    </div>
  );
}

// ─── QUICK ACTIONS ────────────────────────────────────────────────────────────

function QuickActions() {
  const actions = [
    { label: "Restart All", color: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30", action: "Restarting all agents..." },
    { label: "Stop All", color: "bg-red-500/20 text-red-400 border-red-500/30", action: "Stopping all agents..." },
    { label: "Spawn Team", color: "bg-purple-500/20 text-purple-400 border-purple-500/30", action: "Spawning new team..." },
    { label: "Run Conference", color: "bg-amber-500/20 text-amber-400 border-amber-500/30", action: "Running conference..." },
    { label: "Emergency Kill", color: "bg-red-600/30 text-red-300 border-red-500/50", action: "EMERGENCY KILL activated!" },
  ];
  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Quick Actions</h3>
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
    RED:   { icon: XCircle,       color: "text-red-400"     },
    AMBER: { icon: AlertTriangle, color: "text-amber-400"   },
    INFO:  { icon: CheckCircle,   color: "text-emerald-400" },
    WARN:  { icon: AlertTriangle, color: "text-amber-400"   },
    ERROR: { icon: XCircle,       color: "text-red-400"     },
  };

  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">System Alerts</h3>
      {alerts.length === 0 ? (
        <div className="text-[10px] text-gray-500 text-center py-3">No alerts</div>
      ) : (
        <div className="space-y-1.5">
          {alerts.map((a, i) => {
            const cfg = levelConfig[a.level] || levelConfig["INFO"];
            const Icon = cfg.icon;
            return (
              <div key={i} className="flex items-start gap-2 text-[10px]">
                <Icon className={`w-3.5 h-3.5 shrink-0 mt-0.5 ${cfg.color}`} />
                <div>
                  <span className={`font-bold ${cfg.color}`}>{a.level}</span>
                  <span className="text-gray-400 ml-2">{a.msg || a.message || ""}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── LIVE ACTIVITY FEED ───────────────────────────────────────────────────────

function LiveActivityFeed({ agents }) {
  const [items, setItems] = useState([]);
  const feedRef = useRef([]);
  const colorMap = useRef({});
  const colors = ["text-emerald-400","text-cyan-400","text-amber-400","text-purple-400","text-red-400","text-blue-400"];

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
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Live Agent Activity Feed</h3>
      <div className="space-y-0.5 max-h-[200px] overflow-y-auto scrollbar-thin font-mono">
        {items.length === 0 ? (
          <div className="text-[10px] text-gray-500 text-center py-6">Waiting for agent activity...</div>
        ) : (
          items.map(it => (
            <div key={it.id} className="flex gap-2 text-[10px] hover:bg-cyan-500/5 px-1 py-0.5 rounded cursor-pointer">
              <span className="text-gray-600 shrink-0">{it.time}</span>
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
  const rows = agents.map(a => ({
    name: a.name || a.agent_name || "Agent",
    cpu: a.cpu ?? a.cpu_usage ?? 0,
    mem: a.mem != null ? a.mem : (a.memory_mb != null ? `${a.memory_mb}MB` : "0MB"),
    gpu: a.gpu ?? a.gpu_usage ?? 0,
    status: a.status || "unknown",
  }));

  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Agent Resource Monitor</h3>
      {rows.length === 0 ? (
        <div className="text-[10px] text-gray-500 text-center py-3">No data</div>
      ) : (
        <table className="w-full text-[10px]">
          <thead><tr className="text-gray-500 border-b border-gray-800">
            <th className="text-left py-1 font-medium">Agent</th>
            <th className="text-right font-medium">CPU</th>
            <th className="text-right font-medium">MEM</th>
            <th className="text-right font-medium">GPU</th>
            <th className="text-right font-medium">Status</th>
          </tr></thead>
          <tbody>{rows.map(r => (
            <tr key={r.name} className="border-b border-gray-800/30 hover:bg-cyan-500/5">
              <td className="py-1 text-cyan-400 font-mono">{r.name}</td>
              <td className="text-right"><span className={r.cpu > 80 ? "text-red-400" : r.cpu > 50 ? "text-amber-400" : "text-emerald-400"}>{r.cpu}%</span></td>
              <td className="text-right text-white">{r.mem}</td>
              <td className="text-right"><span className={r.gpu > 80 ? "text-red-400" : r.gpu > 50 ? "text-amber-400" : "text-emerald-400"}>{r.gpu}%</span></td>
              <td className="text-right text-gray-400">{r.status}</td>
            </tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}

// ─── ELO LEADERBOARD (UPGRADED) ───────────────────────────────────────────────

function EloLeaderboard() {
  const { data, loading } = useEloLeaderboard(30000);

  const leaders = React.useMemo(() => {
    if (!data || !Array.isArray(data) || data.length === 0) return [];
    return data.map((d, i) => ({
      rank: i + 1,
      name: d.agent_name || d.name || `Agent-${i}`,
      elo: d.elo_rating ?? d.elo ?? 0,
      delta7d: d.delta_7d ?? d.change_7d ?? 0,
      winRate: d.win_rate ?? d.winRate ?? 0,
      trades: d.total_trades ?? d.trades ?? 0,
    }));
  }, [data]);

  const maxElo = Math.max(...leaders.map(l => l.elo), 1);

  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Agent ELO Leaderboard</h3>
      {loading && <div className="text-[10px] text-gray-500 mb-1">Loading...</div>}
      {!loading && leaders.length === 0 ? (
        <div className="text-[10px] text-gray-500 text-center py-3">No ELO data</div>
      ) : (
        <table className="w-full text-[10px]">
          <thead>
            <tr className="text-gray-500 border-b border-gray-800">
              <th className="text-left py-1 font-medium w-4">#</th>
              <th className="text-left font-medium">Agent</th>
              <th className="text-right font-medium">ELO</th>
              <th className="text-right font-medium">Δ7d</th>
              <th className="text-right font-medium">Win%</th>
              <th className="text-right font-medium">Trades</th>
            </tr>
          </thead>
          <tbody>
            {leaders.map(l => {
              const barPct = Math.round((l.elo / maxElo) * 100);
              const deltaColor = l.delta7d > 0 ? "text-emerald-400" : l.delta7d < 0 ? "text-red-400" : "text-gray-500";
              const DeltaIcon = l.delta7d > 0 ? ChevronUp : l.delta7d < 0 ? ChevronDown : Minus;
              return (
                <tr key={l.rank} className="relative border-b border-gray-800/20 hover:bg-cyan-500/5">
                  {/* ELO sparkline bar behind the row */}
                  <td colSpan={6} className="p-0 absolute inset-0 pointer-events-none">
                    <div
                      className="h-full rounded opacity-[0.06] bg-cyan-400"
                      style={{ width: `${barPct}%` }}
                    />
                  </td>
                  <td className="py-1 text-gray-500 relative z-10">{l.rank}.</td>
                  <td className="text-cyan-400 relative z-10 font-mono">{l.name}</td>
                  <td className="text-right text-white font-mono relative z-10">{l.elo}</td>
                  <td className={`text-right font-mono relative z-10 ${deltaColor}`}>
                    <span className="inline-flex items-center justify-end gap-0.5">
                      <DeltaIcon className="w-2.5 h-2.5" />
                      {Math.abs(l.delta7d)}
                    </span>
                  </td>
                  <td className="text-right text-gray-300 relative z-10">{l.winRate.toFixed(1)}%</td>
                  <td className="text-right text-gray-400 relative z-10">{l.trades}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ─── HITL APPROVAL QUEUE ──────────────────────────────────────────────────────

async function postHitlDecision(decisionId, action) {
  const base = import.meta.env.VITE_API_URL ?? "";
  const res = await fetch(`${base}/api/v1/agents/hitl/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ decision_id: decisionId, action }),
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
    <div className="aurora-card p-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider">HITL Approval Queue</h3>
        {pending.length > 0 && (
          <span className="px-2 py-0.5 bg-amber-500/20 border border-amber-500/40 rounded text-[9px] font-bold text-amber-400 animate-pulse">
            {pending.length} PENDING APPROVAL
          </span>
        )}
      </div>
      {loading && <div className="text-[10px] text-gray-500 mb-1">Loading queue...</div>}
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
              <th className="text-left pl-2 font-medium">Agent</th>
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
                  <td className="text-right text-cyan-400 font-mono">{item.confidence}%</td>
                  <td className="pl-2 text-gray-400">{item.agent}</td>
                  <td className="text-right">
                    {decided ? (
                      <span className={`text-[9px] font-bold ${decided === "approve" ? "text-emerald-400" : "text-red-400"}`}>
                        {decided.toUpperCase()}D
                      </span>
                    ) : (
                      <span className="inline-flex gap-1">
                        <button
                          onClick={() => handleDecision(item.id, "approve")}
                          className="px-1.5 py-0.5 bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 rounded text-[9px] font-bold hover:bg-emerald-500/30 transition-all"
                          title="Approve"
                        >
                          ✓
                        </button>
                        <button
                          onClick={() => handleDecision(item.id, "reject")}
                          className="px-1.5 py-0.5 bg-red-500/20 border border-red-500/40 text-red-400 rounded text-[9px] font-bold hover:bg-red-500/30 transition-all"
                          title="Reject"
                        >
                          ✗
                        </button>
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
  // These stage names define the pipeline architecture — structural config, not mock data
  const stages = ["Researcher", "RiskOfficer", "Adversary", "Arbiter"];
  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Conference Pipeline</h3>
      <div className="flex items-center gap-1 justify-center">
        {stages.map((s, i) => (
          <React.Fragment key={s}>
            <div className="px-2 py-1 bg-cyan-500/10 border border-cyan-500/30 rounded text-[9px] text-cyan-400 font-bold">{s}</div>
            {i < stages.length - 1 && <span className="text-cyan-500/40 text-xs">→</span>}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

// ─── LAST CONFERENCE ──────────────────────────────────────────────────────────

function LastConference({ conferenceData = null }) {
  if (!conferenceData) {
    return (
      <div className="aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Last Conference</h3>
        <div className="text-[10px] text-gray-500 text-center py-3">No conference data</div>
        <div className="grid grid-cols-2 gap-2 text-[10px] text-gray-600">
          <span>Symbol: —</span>
          <span>Verdict: —</span>
          <span>Confidence: 0%</span>
          <span>Duration: 0s</span>
        </div>
      </div>
    );
  }

  const votes = Array.isArray(conferenceData.votes) ? conferenceData.votes : [];
  const confidence = conferenceData.confidence ?? 0;
  const verdict = conferenceData.verdict ?? "—";
  const symbol = conferenceData.symbol ?? "—";
  const conferenceId = conferenceData.id ?? "";
  const duration = conferenceData.duration_s ?? conferenceData.duration ?? 0;

  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Last Conference</h3>
      <div className="flex items-center gap-3 mb-2">
        <span className="text-[10px] text-gray-400">{symbol}{conferenceId ? ` #${conferenceId}` : ""}</span>
        <span className={`text-[10px] font-bold ${verdict === "BUY" ? "text-emerald-400" : verdict === "SELL" ? "text-red-400" : "text-gray-400"}`}>
          VERDICT: {verdict}
        </span>
        <div className="relative w-10 h-10">
          <svg viewBox="0 0 36 36" className="w-10 h-10 -rotate-90">
            <circle cx="18" cy="18" r="16" fill="none" stroke="#1f2937" strokeWidth="3" />
            <circle cx="18" cy="18" r="16" fill="none" stroke="#06b6d4" strokeWidth="3" strokeDasharray={`${confidence} ${100 - confidence}`} strokeLinecap="round" />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-[9px] text-cyan-400 font-bold">{confidence}%</span>
        </div>
      </div>
      {votes.length === 0 ? (
        <div className="text-[10px] text-gray-500 py-2">No vote data</div>
      ) : (
        <div className="space-y-1">
          {votes.map(v => (
            <div key={v.agent} className="flex items-center gap-2 text-[10px]">
              <span className="w-16 text-gray-400">{v.agent}</span>
              <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${v.vote > 70 ? "bg-cyan-500" : v.vote > 50 ? "bg-amber-500" : "bg-red-500"}`} style={{ width: `${v.vote}%` }} />
              </div>
              <span className="text-white w-6 text-right">{v.vote}%</span>
            </div>
          ))}
        </div>
      )}
      <div className="text-[9px] text-gray-500 mt-2">Duration: {duration}s</div>
    </div>
  );
}

// ─── DRIFT MONITOR ────────────────────────────────────────────────────────────

function DriftMonitorPanel({ driftData = [] }) {
  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Drift Monitor</h3>
      {driftData.length === 0 ? (
        <div className="text-[10px] text-gray-500 text-center py-3">No drift data</div>
      ) : (
        <div className="space-y-1">
          {driftData.map((m, i) => (
            <div key={i} className="flex items-center justify-between text-[10px]">
              <span className="text-gray-400 font-mono">{m.name}</span>
              {m.val != null && <span className={m.status === "warn" ? "text-amber-400" : "text-emerald-400"}>{typeof m.val === "number" ? m.val.toFixed(2) : m.val}</span>}
              {m.val == null && <span className="text-gray-500">{m.label ?? ""}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── BLACKBOARD FEED ──────────────────────────────────────────────────────────

function BlackboardFeed({ topics = [] }) {
  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Blackboard Live Feed</h3>
      {topics.length === 0 ? (
        <div className="text-[10px] text-gray-500 text-center py-3">No activity</div>
      ) : (
        <table className="w-full text-[10px]">
          <thead><tr className="text-gray-500 border-b border-gray-800">
            <th className="text-left py-1 font-medium">Topic</th>
            <th className="text-right font-medium">Subs</th>
            <th className="text-left pl-3 font-medium">Last Message</th>
          </tr></thead>
          <tbody>{topics.map(t => (
            <tr key={t.topic} className="border-b border-gray-800/30 hover:bg-cyan-500/5">
              <td className="py-1 text-cyan-400 font-mono">{t.topic}</td>
              <td className="text-right text-white">{t.subs ?? 0}</td>
              <td className="pl-3 text-gray-400">{t.last ?? "—"}</td>
            </tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}

// ─── TEAM STATUS ──────────────────────────────────────────────────────────────

function TeamStatus({ teams = [] }) {
  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Team Status</h3>
      {teams.length === 0 ? (
        <div className="text-[10px] text-gray-500 text-center py-3">No teams</div>
      ) : (
        <div className="space-y-1.5">
          {teams.map(t => (
            <div key={t.name} className="flex items-center justify-between text-[10px]">
              <span className="text-white font-mono">{t.name}</span>
              <div className="flex items-center gap-2">
                <span className="text-gray-500">{t.agents ?? 0} agents</span>
                <span className={t.status === "ACTIVE" ? "text-cyan-400" : "text-amber-400"}>{t.status}</span>
                <span className="text-white">{t.health ?? 0}%</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── MAIN TAB ─────────────────────────────────────────────────────────────────

export default function SwarmOverviewTab({ agents = [], teams = [], alerts = [], topics = [], conferenceData = null, driftData = [] }) {
  return (
    <div className="grid grid-cols-12 gap-3">

      {/* ── ROW 1: Full-width DAG Topology ── */}
      <div className="col-span-12">
        <SwarmTopologyDAG agents={agents} />
      </div>

      {/* ── ROW 2 ── */}

      {/* Left: Health + Actions + Alerts */}
      <div className="col-span-3 space-y-3">
        <AgentHealthMatrix agents={agents} />
        <QuickActions />
        <SystemAlertsPanel alerts={alerts} />
      </div>

      {/* Center: Activity + Resources */}
      <div className="col-span-5 space-y-3">
        <LiveActivityFeed agents={agents} />
        <ResourceMonitor agents={agents} />
      </div>

      {/* Right: ELO + HITL */}
      <div className="col-span-4 space-y-3">
        <EloLeaderboard />
        <HITLQueue />
      </div>

      {/* ── ROW 3 ── */}

      {/* Conference Pipeline + Last Conference */}
      <div className="col-span-6 space-y-3">
        <ConferencePipelineViz />
        <LastConference conferenceData={conferenceData} />
      </div>

      {/* Drift + Blackboard */}
      <div className="col-span-3 space-y-3">
        <DriftMonitorPanel driftData={driftData} />
        <BlackboardFeed topics={topics} />
      </div>

      {/* Team Status */}
      <div className="col-span-3 space-y-3">
        <TeamStatus teams={teams} />
      </div>

    </div>
  );
}
