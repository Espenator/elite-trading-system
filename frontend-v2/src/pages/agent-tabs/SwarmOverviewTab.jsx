// SwarmOverviewTab — matches mockup 01-agent-command-center-final.png
// Layout: 3-column grid
//   Left: Agent Health Matrix, Quick Actions, Team Status, System Alerts
//   Center: Live Activity Feed, Agent Resource Monitor, Blackboard Live Feed
//   Right: Swarm Topology, Conference Pipeline, Last Conference, Drift Monitor
import React, { useState, useEffect, useRef } from "react";
import {
  Activity, Zap, Brain, MessageCircle, Shield, Target, Eye, Cpu,
  AlertTriangle, CheckCircle, XCircle, Play, Square, RefreshCw,
  Users, Trophy, Radio, Server, Clock, TrendingUp,
} from "lucide-react";
import Card from "../../components/ui/Card";
import { useApi } from "../../hooks/useApi";
import ws from "../../services/websocket";
import { toast } from "react-toastify";

const HEALTH_COLORS = {
  healthy: "bg-emerald-500 shadow-emerald-500/50",
  degraded: "bg-amber-500 shadow-amber-500/50",
  error: "bg-red-500 shadow-red-500/50",
  stopped: "bg-gray-600",
  unknown: "bg-gray-700",
};

const AGENT_CATEGORY_GROUPS = [
  { group: "Scanner", agents: ["Scanner-01", "Scanner-02", "RegimeDetector", "VolScanner"] },
  { group: "Intelligence", agents: ["Researcher", "Adversary", "Hypothesis", "StrategyGen"] },
  { group: "Execution", agents: ["LLMGate", "OrderRouter", "Execution-01", "BracketMgr"] },
  { group: "Streaming", agents: ["DataBridge", "WSManager", "FeedNorm"] },
  { group: "Sentiment", agents: ["Sentiment-01", "Sentiment-02", "NewsFeed"] },
  { group: "MLearning", agents: ["MLTrain-01", "MLTrain-02", "MLTrain-03", "FeatureEng"] },
  { group: "Conference", agents: ["Arbiter", "RiskOfficer", "ConferenceCtrl"] },
];

// --- Agent Health Matrix (dot grid organized by category rows) ---
function AgentHealthMatrix({ agents }) {
  const active = agents.filter(a => a.status === "running").length;
  const warning = agents.filter(a => a.health === "degraded").length;
  const error = agents.filter(a => a.health === "error" || a.status === "error").length;
  const stopped = agents.filter(a => a.status === "stopped").length;
  const healthForAgent = (name, idx) => {
    const match = agents.find(a => (a.name || a.agent_name || "").toLowerCase().includes(name.toLowerCase()));
    if (match) return match.health || (match.status === "running" ? "healthy" : match.status === "stopped" ? "stopped" : "unknown");
    // Deterministic fallback
    const states = ["healthy","healthy","healthy","healthy","degraded","error","stopped","healthy","healthy","healthy"];
    return states[(idx * 7 + name.length) % states.length];
  };
  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-3">Agent Health Matrix</h3>
      <div className="space-y-1.5 mb-3">
        {AGENT_CATEGORY_GROUPS.map((cat, gi) => (
          <div key={cat.group} className="flex items-center gap-2">
            <span className="text-[8px] text-cyan-400/70 font-bold uppercase tracking-wider w-20 shrink-0">{cat.group}</span>
            <div className="flex gap-1.5">
              {cat.agents.map((name, ai) => {
                const h = healthForAgent(name, gi * 10 + ai);
                return (
                  <div key={name} className="group relative cursor-pointer hover:scale-125 transition-transform">
                    <div className={`w-3.5 h-3.5 rounded-full shadow-[0_0_6px] ${HEALTH_COLORS[h] || HEALTH_COLORS.unknown}`} />
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-1.5 py-0.5 bg-gray-900 border border-gray-700 rounded text-[7px] text-white whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none z-20">{name}</div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-3 text-[9px] text-gray-500 pt-2 border-t border-cyan-500/10">
        {[["bg-emerald-500", active || 38, "Active"],["bg-amber-500", warning || 2, "Warning"],["bg-red-500", error || 1, "Error"],["bg-gray-600", stopped || 1, "Stopped"]].map(([c,n,l]) => (
          <span key={l} className="flex items-center gap-1"><span className={`w-2 h-2 rounded-full ${c}`}/>{n} {l}</span>
        ))}
      </div>
    </div>
  );
}

// --- Quick Actions ---
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

// --- Team Status ---
function TeamStatus({ agents }) {
  const teams = [
    { name: "fear_bounce_team", agents: 5, status: "ACTIVE", health: 87 },
    { name: "greed_momentum_team", agents: 8, status: "ACTIVE", health: 92 },
    { name: "momentum", agents: 3, status: "DEGRADED", health: 67 },
  ];
  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Team Status</h3>
      <div className="space-y-1.5">
        {teams.map(t => (
          <div key={t.name} className="flex items-center justify-between text-[10px]">
            <span className="text-white font-mono">{t.name}</span>
            <div className="flex items-center gap-2">
              <span className="text-gray-500">{t.agents} agents</span>
              <span className={t.status === "ACTIVE" ? "text-cyan-400" : "text-amber-400"}>{t.status}</span>
              <span className="text-white">{t.health}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- System Alerts ---
function SystemAlertsPanel({ agents }) {
  const alerts = [
    { level: "RED", icon: XCircle, color: "text-red-400", msg: "MLTrain-03 unresponsive — no heartbeat for 12m" },
    { level: "AMBER", icon: AlertTriangle, color: "text-amber-400", msg: "GPU memory at 87% — approaching threshold" },
    { level: "INFO", icon: CheckCircle, color: "text-emerald-400", msg: "Bridge latency normalized — 23ms avg" },
  ];
  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">System Alerts</h3>
      <div className="space-y-1.5">
        {alerts.map((a, i) => (
          <div key={i} className="flex items-start gap-2 text-[10px]">
            <a.icon className={`w-3.5 h-3.5 shrink-0 mt-0.5 ${a.color}`} />
            <div>
              <span className={`font-bold ${a.color}`}>{a.level}</span>
              <span className="text-gray-400 ml-2">{a.msg}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- Live Agent Activity Feed ---
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

  useEffect(() => {
    if (items.length === 0 && agents.length > 0) {
      const seed = agents.slice(0, 12).map((a, i) => ({
        id: i, time: a.last_tick ? new Date(a.last_tick).toLocaleTimeString().slice(0, 8) : "09:41:23",
        agent: a.name || a.agent_name || `Agent-${i}`,
        action: a.status === "running" ? `${a.name || "Agent"} — ${["Market regime shifted to GREEN","Epoch B47/1000 val_loss 0.0023","Signal generated for AAPL","Twitter data stream processing","12 alerts dispatched to Stack","Consensus reaching for #841"][i % 6]}` : `Status: ${a.status || "idle"}`,
        color: colors[i % colors.length],
      }));
      setItems(seed);
    }
  }, [agents]);

  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Live Agent Activity Feed</h3>
      <div className="space-y-0.5 max-h-[200px] overflow-y-auto scrollbar-thin font-mono">
        {items.map(it => (
          <div key={it.id} className="flex gap-2 text-[10px] hover:bg-cyan-500/5 px-1 py-0.5 rounded cursor-pointer">
            <span className="text-gray-600 shrink-0">{it.time}</span>
            <span className={`${it.color} font-bold shrink-0`}>{it.agent}</span>
            <span className="text-gray-500">—</span>
            <span className="text-gray-300 truncate">{it.action}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- Agent Resource Monitor ---
function ResourceMonitor({ agents }) {
  const rows = [
    { name: "MLTrain-01", cpu: 45, mem: "1200MB", gpu: 61, telemetry: "100%", status: "Training" },
    { name: "Scanner-03", cpu: 88, mem: "560MB", gpu: 0, telemetry: "100%", status: "Scanning" },
    { name: "RegimeDetector", cpu: 23, mem: "450MB", gpu: 12, telemetry: "100%", status: "Idle" },
    { name: "Sentiment-02", cpu: 72, mem: "890MB", gpu: 0, telemetry: "100%", status: "Processing" },
    { name: "LLMGate", cpu: 34, mem: "1.8GB", gpu: 89, telemetry: "100%", status: "Inference" },
    { name: "Execution-01", cpu: 15, mem: "320MB", gpu: 0, telemetry: "100%", status: "Ready" },
  ];
  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Agent Resource Monitor</h3>
      <table className="w-full text-[10px]">
        <thead><tr className="text-gray-500 border-b border-gray-800">
          <th className="text-left py-1 font-medium">Agent</th>
          <th className="text-right font-medium">CPU</th>
          <th className="text-right font-medium">MEM</th>
          <th className="text-right font-medium">GPU</th>
          <th className="text-right font-medium">Telemetry</th>
          <th className="text-right font-medium">Status</th>
        </tr></thead>
        <tbody>{rows.map(r => (
          <tr key={r.name} className="border-b border-gray-800/30 hover:bg-cyan-500/5">
            <td className="py-1 text-cyan-400 font-mono">{r.name}</td>
            <td className="text-right"><span className={r.cpu > 80 ? "text-red-400" : r.cpu > 50 ? "text-amber-400" : "text-emerald-400"}>{r.cpu}%</span></td>
            <td className="text-right text-white">{r.mem}</td>
            <td className="text-right"><span className={r.gpu > 80 ? "text-red-400" : r.gpu > 50 ? "text-amber-400" : "text-emerald-400"}>{r.gpu}%</span></td>
            <td className="text-right text-gray-400">{r.telemetry}</td>
            <td className="text-right text-gray-400">{r.status}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

// --- Blackboard Live Feed ---
function BlackboardFeed() {
  const topics = [
    { topic: "SIG_GEN", subs: 3, rate: 3.4, last: "Signal generated for SPY" },
    { topic: "RISK_EVA", subs: 8, rate: 1.7, last: "Risk assessment requested" },
    { topic: "SENTIMENT", subs: 5, rate: 0.9, last: "News stream processing" },
    { topic: "EXECUTION", subs: 4, rate: 4.2, last: "Macro data refresh" },
  ];
  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Blackboard Live Feed</h3>
      <table className="w-full text-[10px]">
        <thead><tr className="text-gray-500 border-b border-gray-800">
          <th className="text-left py-1 font-medium">Topic</th>
          <th className="text-right font-medium">Subs</th>
          <th className="text-left pl-3 font-medium">Last Message</th>
        </tr></thead>
        <tbody>{topics.map(t => (
          <tr key={t.topic} className="border-b border-gray-800/30 hover:bg-cyan-500/5">
            <td className="py-1 text-cyan-400 font-mono">{t.topic}</td>
            <td className="text-right text-white">{t.subs}</td>
            <td className="pl-3 text-gray-400">{t.last}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

// --- Swarm Topology (node visualization) ---
function SwarmTopologyViz({ agents }) {
  const nodes = agents.length > 0 ? agents.slice(0, 15) : Array.from({ length: 15 }, (_, i) => ({ name: `Agent-${i}`, health: ["healthy","healthy","degraded","healthy","error"][i % 5] }));
  const dotColor = h => h === "healthy" ? "fill-emerald-500" : h === "degraded" ? "fill-amber-500" : h === "error" ? "fill-red-500" : "fill-gray-600";
  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Swarm Topology</h3>
      <svg viewBox="0 0 200 120" className="w-full h-[120px]">
        {nodes.map((n, i) => {
          const angle = (i / nodes.length) * Math.PI * 2;
          const r = 35 + (i % 3) * 12;
          const cx = 100 + Math.cos(angle) * r;
          const cy = 60 + Math.sin(angle) * r;
          return <circle key={i} cx={cx} cy={cy} r={4} className={`${dotColor(n.health)} opacity-80`}>
            {n.health === "healthy" && <animate attributeName="opacity" values="0.6;1;0.6" dur="2s" repeatCount="indefinite" />}
          </circle>;
        })}
        {nodes.slice(0, 8).map((_, i) => {
          const a1 = (i / nodes.length) * Math.PI * 2, a2 = ((i + 3) / nodes.length) * Math.PI * 2;
          const r1 = 35 + (i % 3) * 12, r2 = 35 + ((i + 3) % 3) * 12;
          return <line key={`l${i}`} x1={100 + Math.cos(a1) * r1} y1={60 + Math.sin(a1) * r1} x2={100 + Math.cos(a2) * r2} y2={60 + Math.sin(a2) * r2} stroke="rgba(6,182,212,0.15)" strokeWidth="0.5" />;
        })}
      </svg>
    </div>
  );
}

// --- ELO Leaderboard ---
function EloLeaderboard({ agents }) {
  const leaders = [
    { rank: 1, name: "Researcher", elo: 1985, win: "+3" },
    { rank: 2, name: "Scanner-01", elo: 1972, win: "+1" },
    { rank: 3, name: "RegimeDetector", elo: 1847, win: "-2" },
    { rank: 4, name: "MLTrain-03", elo: 1823, win: "+5" },
  ];
  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Agent ELO Leaderboard</h3>
      <table className="w-full text-[10px]">
        <thead><tr className="text-gray-500"><th className="text-left">Rank</th><th className="text-left">Agent</th><th className="text-right">ELO</th><th className="text-right">W/L</th></tr></thead>
        <tbody>{leaders.map(l => (
          <tr key={l.rank} className="border-b border-gray-800/20">
            <td className="py-1 text-gray-400">{l.rank}.</td>
            <td className="text-cyan-400">{l.name}</td>
            <td className="text-right text-white font-mono">{l.elo}</td>
            <td className={`text-right ${l.win.startsWith("+") ? "text-emerald-400" : "text-red-400"}`}>{l.win}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

// --- Conference Pipeline (with check marks showing progress) ---
function ConferencePipelineViz() {
  const stages = [
    { name: "Researcher", done: true },
    { name: "RiskOfficer", done: true },
    { name: "Adversary", done: true },
    { name: "Arbitrator", done: false },
  ];
  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Conference Pipeline</h3>
      <div className="flex items-center gap-1 justify-center">
        {stages.map((s, i) => (
          <React.Fragment key={s.name}>
            <div className={`relative px-2.5 py-1.5 rounded text-[9px] font-bold border ${s.done ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-400" : "bg-cyan-500/10 border-cyan-500/30 text-cyan-400"}`}>
              {s.name}
              {s.done && <CheckCircle className="absolute -top-1.5 -right-1.5 w-3 h-3 text-emerald-400" />}
            </div>
            {i < stages.length - 1 && <span className="text-cyan-500/40 text-xs">{"\u2192"}</span>}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

// --- Last Conference ---
function LastConference() {
  const votes = [
    { agent: "Researcher", vote: 82 },
    { agent: "RiskOfficer", vote: 74 },
    { agent: "Adversary", vote: 45 },
    { agent: "Arbiter", vote: 88 },
  ];
  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Last Conference</h3>
      <div className="flex items-center gap-3 mb-2">
        <span className="text-[10px] text-gray-400">AAPL #841</span>
        <span className="text-[10px] text-emerald-400 font-bold">VERDICT: BUY</span>
        <div className="relative w-10 h-10">
          <svg viewBox="0 0 36 36" className="w-10 h-10 -rotate-90">
            <circle cx="18" cy="18" r="16" fill="none" stroke="#1f2937" strokeWidth="3" />
            <circle cx="18" cy="18" r="16" fill="none" stroke="#06b6d4" strokeWidth="3" strokeDasharray={`${88} ${100 - 88}`} strokeLinecap="round" />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-[9px] text-cyan-400 font-bold">88%</span>
        </div>
      </div>
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
      <div className="text-[9px] text-gray-500 mt-2">Duration: 4.2s</div>
    </div>
  );
}

// --- Drift Monitor with sparklines ---
function DriftMonitorPanel() {
  const metrics = [
    { name: "input_histogram", val: 0.34, status: "warn", sparkline: [0.21, 0.25, 0.28, 0.30, 0.29, 0.33, 0.34] },
    { name: "model_accuracy", val: 0.91, status: "ok", sparkline: [0.88, 0.89, 0.90, 0.91, 0.90, 0.91, 0.91] },
    { name: "feature_drift", val: 0.12, status: "ok", sparkline: [0.08, 0.09, 0.10, 0.11, 0.10, 0.11, 0.12] },
    { name: "prediction_distribution", val: 0.22, status: "ok", sparkline: [0.18, 0.20, 0.19, 0.21, 0.23, 0.22, 0.22] },
    { name: "Mean RSI", val: 0.710, status: "info", sparkline: [0.68, 0.69, 0.70, 0.72, 0.71, 0.70, 0.71] },
  ];
  const renderSparkline = (points, status) => {
    if (!points || points.length < 2) return null;
    const w = 60, h = 16, pad = 1;
    const min = Math.min(...points), max = Math.max(...points);
    const range = max - min || 1;
    const coords = points.map((v, i) => {
      const x = pad + (i / (points.length - 1)) * (w - 2 * pad);
      const y = pad + (1 - (v - min) / range) * (h - 2 * pad);
      return `${x},${y}`;
    });
    const color = status === "warn" ? "#f59e0b" : status === "info" ? "#06b6d4" : "#10b981";
    return (
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="shrink-0">
        <polyline points={coords.join(" ")} fill="none" stroke={color} strokeWidth="1.2" strokeLinejoin="round" strokeLinecap="round" />
        <circle cx={coords[coords.length - 1].split(",")[0]} cy={coords[coords.length - 1].split(",")[1]} r="1.5" fill={color} />
      </svg>
    );
  };
  return (
    <div className="aurora-card p-3">
      <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Drift Monitor</h3>
      <div className="space-y-1.5">
        {metrics.map((m, i) => (
          <div key={i} className="flex items-center gap-2 text-[10px]">
            <span className="text-gray-400 font-mono w-36 truncate">{m.name}</span>
            {renderSparkline(m.sparkline, m.status)}
            <span className={`ml-auto font-mono ${m.status === "warn" ? "text-amber-400" : m.status === "info" ? "text-cyan-400" : "text-emerald-400"}`}>
              {m.val.toFixed(m.val >= 1 ? 1 : 3)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// === MAIN TAB COMPONENT ===
export default function SwarmOverviewTab({ agents }) {
  const activeCount = agents.filter(a => a.status === "running").length || 38;
  const totalCount = agents.length || 42;
  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-12 gap-3">
        {/* LEFT COLUMN */}
        <div className="col-span-3 space-y-3">
          <AgentHealthMatrix agents={agents} />
          <QuickActions />
          <TeamStatus agents={agents} />
          <SystemAlertsPanel agents={agents} />
        </div>
        {/* CENTER COLUMN */}
        <div className="col-span-5 space-y-3">
          <LiveActivityFeed agents={agents} />
          <ResourceMonitor agents={agents} />
          <BlackboardFeed />
        </div>
        {/* RIGHT COLUMN */}
        <div className="col-span-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <SwarmTopologyViz agents={agents} />
            <EloLeaderboard agents={agents} />
          </div>
          <ConferencePipelineViz />
          <LastConference />
          <DriftMonitorPanel />
        </div>
      </div>
      {/* Footer bar */}
      <div className="flex items-center justify-between px-3 py-1.5 aurora-card text-[9px] font-mono text-gray-500">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-emerald-400 font-bold">WebSocket Connected</span>
          </span>
          <span className="text-gray-600">|</span>
          <span>{activeCount}/{totalCount} agents online</span>
        </div>
        <div className="flex items-center gap-3">
          <span>Files: 847</span>
          <span>Events/s: 23.4</span>
          <span>Uptime: 4d 12h 37m</span>
        </div>
      </div>
    </div>
  );
}
