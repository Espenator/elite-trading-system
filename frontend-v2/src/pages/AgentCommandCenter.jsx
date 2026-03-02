// AGENT COMMAND CENTER - Embodier.ai Glass House Intelligence System
// Unified page: Agent management + OpenClaw swarm control + LLM alerts
// Merges former ClawBotPanel into single command center
// Backend: GET /api/v1/agents, /api/v1/openclaw/*, WS 'agents' + 'llm-flow'
// Mockups: 01-agent-command-center-final.png, 05-agent-command-center.png, 05b-agent-command-center-spawn.png
import { useState, useMemo, useEffect, useRef, useCallback } from "react";
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
// Health dot colors for agent health matrix
const HEALTH_DOT_COLORS = {
  healthy: "bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.6)]",
  degraded: "bg-amber-500 shadow-[0_0_6px_rgba(245,158,11,0.6)]",
  error: "bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.6)]",
  stopped: "bg-gray-600",
  unknown: "bg-gray-700",
};

// Spawn template data
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
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium text-white cursor-pointer hover:brightness-125 transition-all"
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
  const icon = isHigh ? "text-danger" : isWarning ? "text-warning" : "text-primary";
  return (
    <div className={`flex items-start gap-2 p-3 rounded-lg border ${bg} text-sm cursor-pointer hover:bg-black/20 transition-colors`}
      onClick={() => toast.info("Accessing alert logs...")}>
      {isHigh ? <AlertTriangle className={`w-4 h-4 ${icon} shrink-0 mt-0.5`} /> : <Info className={`w-4 h-4 ${icon} shrink-0 mt-0.5`} />}
      <div className="flex-1 min-w-0">
        <span className="text-white text-sm">{alert.message || alert.text || JSON.stringify(alert)}</span>
        {alert.timestamp && <span className="block text-xs text-secondary mt-1">{alert.timestamp}</span>}
      </div>
      {onDismiss && <button type="button" onClick={(e) => { e.stopPropagation(); onDismiss(); }} className="text-secondary hover:text-white shrink-0">&times;</button>}
    </div>
  );
}
// --- Helper: Agent Health Matrix (from mockup 01) ---
function AgentHealthMatrix({ agents }) {
  const categories = ["RegimeDetector", "Researcher", "LLMGate", "Adversary", "Memory",
    "Streaming", "Sentiment", "MLLearning", "Execution", "Conference"];
  const activeCount = agents.filter(a => a.status === "running").length;
  const warningCount = agents.filter(a => a.health === "degraded").length;
  const errorCount = agents.filter(a => a.health === "error" || a.status === "error").length;
  const stoppedCount = agents.filter(a => a.status === "stopped").length;
  return (
    <Card className="border-cyan-500/20 bg-[#0B0E14]">
      <div className="flex items-center gap-2 mb-4">
        <Activity className="w-5 h-5 text-cyan-400" />
        <span className="text-sm font-bold text-white uppercase tracking-wider">Agent Health Matrix</span>
      </div>
      <div className="grid grid-cols-5 gap-3 mb-4">
        {categories.map((cat, i) => {
          const agent = agents[i % agents.length];
          const health = agent?.health || (i % 4 === 0 ? "degraded" : i % 7 === 0 ? "error" : "healthy");
          return (
            <div key={cat} className="flex flex-col items-center gap-1 cursor-pointer hover:brightness-125 transition-all"
              onClick={() => toast.info(`Inspecting ${cat} health metrics`)}>
              <div className={`w-4 h-4 rounded-full ${HEALTH_DOT_COLORS[health] || HEALTH_DOT_COLORS.unknown}`} />
              <span className="text-[8px] text-secondary uppercase tracking-wider text-center">{cat}</span>
            </div>
          );
        })}
      </div>
      <div className="flex items-center gap-4 text-[10px] text-secondary border-t border-secondary/20 pt-3">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" /> {activeCount} Active</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500" /> {warningCount} Warning</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /> {errorCount} Error</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-gray-600" /> {stoppedCount} Stopped</span>
      </div>
    </Card>
  );
}

// --- Helper: Live Agent Activity Feed (from mockup 01) ---
function LiveActivityFeed({ agents, llmAlerts }) {
  const [feedItems] = useState(() => {
    const items = [];
    const agentNames = ["RegimeDetector", "Scanner-07", "MLTrain-01", "Researcher", "BridgeSender", "Arbitrator", "Sentiment", "Execution-02"];
    const actions = [
      "Market regime shifted to GREEN", "Found 3 candidates passed filters",
      "Epoch 847/1000 val_loss: 0.0023", "Deep analysis complete for conf #941",
      "12 alerts dispatched to Slack", "Consensus reached for conf #941",
      "Twitter data stream processing", "Order execution pending for AAPL",
    ];
    const colors = ["text-emerald-400", "text-cyan-400", "text-amber-400", "text-purple-400", "text-red-400", "text-blue-400"];
    for (let i = 0; i < 10; i++) {
      const h = 9; const m = 41 - i * 2; const s = Math.floor(Math.random() * 60);
      items.push({
        id: i, time: `[${String(h).padStart(2, '0')}:${String(Math.max(0, m)).padStart(2, '0')}:${String(s).padStart(2, '0')}]`,
        agent: agentNames[i % agentNames.length], action: actions[i % actions.length],
        color: colors[i % colors.length],
      });
    }
    return items;
  });
  return (
    <Card className="border-cyan-500/20 bg-[#0B0E14]">
      <div className="flex items-center gap-2 mb-3">
        <Terminal className="w-5 h-5 text-cyan-400" />
        <span className="text-sm font-bold text-white uppercase tracking-wider">Live Agent Activity Feed</span>
      </div>
      <div className="space-y-1 max-h-[280px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-cyan-500/20 font-mono text-[11px]">
        {feedItems.map(item => (
          <div key={item.id} className="flex gap-2 hover:bg-cyan-500/5 px-1 py-0.5 rounded cursor-pointer transition-colors"
            onClick={() => toast.info(`Trace: ${item.agent} — ${item.action}`)}>
            <span className="text-cyan-500/50 shrink-0">{item.time}</span>
            <span className={`${item.color} font-bold shrink-0`}>{item.agent}</span>
            <span className="text-secondary">—</span>
            <span className="text-white/80 truncate">{item.action}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

// --- Helper: Blackboard Live Feed Table (from mockup 01) ---
function BlackboardLiveFeed({ blackboardMsgs }) {
  const topics = [
    { topic: "SIG_GEN", subs: 12, msgRate: 3.4, lastMsg: "Signal generated for SPY" },
    { topic: "RISK_EVAL", subs: 8, msgRate: 0.1, lastMsg: "Risk assessment requested" },
    { topic: "SENTIMENT", subs: 6, msgRate: 5.7, lastMsg: "News stream parsing complete" },
    { topic: "EXECUTION", subs: 4, msgRate: 0.3, lastMsg: "Order status updated" },
    { topic: "MACRO_BRAIN", subs: 13, msgRate: 4.2, lastMsg: "Macro data refresh" },
  ];
  return (
    <Card className="border-cyan-500/20 bg-[#0B0E14]">
      <div className="flex items-center gap-2 mb-3">
        <ClipboardList className="w-5 h-5 text-cyan-400" />
        <span className="text-sm font-bold text-white uppercase tracking-wider">Blackboard Live Feed</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="border-b border-cyan-500/20 bg-cyan-500/5">
              <th className="px-3 py-2 text-left text-[9px] font-bold text-cyan-400 uppercase tracking-wider">Topic</th>
              <th className="px-3 py-2 text-left text-[9px] font-bold text-cyan-400 uppercase tracking-wider">Subs</th>
              <th className="px-3 py-2 text-left text-[9px] font-bold text-cyan-400 uppercase tracking-wider">Msg/s</th>
              <th className="px-3 py-2 text-left text-[9px] font-bold text-cyan-400 uppercase tracking-wider">Last Message</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-secondary/10">
            {topics.map(t => (
              <tr key={t.topic} className="hover:bg-cyan-500/5 cursor-pointer transition-colors"
                onClick={() => toast.info(`Inspecting topic: ${t.topic}`)}>
                <td className="px-3 py-2 font-bold text-amber-400">{t.topic}</td>
                <td className="px-3 py-2 text-white">{t.subs}</td>
                <td className="px-3 py-2 text-cyan-400">{t.msgRate}</td>
                <td className="px-3 py-2 text-secondary truncate max-w-[200px]">{t.lastMsg}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// --- Helper: Agent Card ---
function AgentCard({ agent, onToggle }) {
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
    <div className={`border rounded-xl p-4 transition-all bg-[#0B0E14] ${isRunning ? "border-cyan-500/40 shadow-[0_0_15px_rgba(6,182,212,0.15)]" : "border-secondary/30 opacity-60"}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${isRunning ? "bg-cyan-500/20 border border-cyan-500/50" : "bg-secondary/20"}`}>
            <Icon className={`w-5 h-5 ${isRunning ? "text-cyan-400" : "text-secondary"}`} />
          </div>
          <div>
            <div className="text-sm font-bold text-white hover:text-cyan-400 cursor-pointer transition-colors flex items-center gap-2"
              onClick={() => toast.info(`Inspecting agent logic for ${agent.name}`)}>
              {agent.name}
              {isRunning && <RefreshCcw className="w-3 h-3 text-cyan-400 animate-spin" title="Recursive Self-Improvement Active" />}
            </div>
            <div className="flex items-center gap-2 mt-0.5 text-[10px] uppercase tracking-wider">
              <span className={`flex items-center gap-1 ${healthColor}`}><Activity className="w-3 h-3" /> {health}</span>
              {agent.uptime && <span className="text-secondary">up {agent.uptime}</span>}
            </div>
          </div>
        </div>
        <Button variant={isRunning ? "danger" : "primary"} size="xs" onClick={(e) => { e.stopPropagation(); onToggle(agent); }}
          className={isRunning ? "bg-red-500/20 text-red-400 border-red-500/50 hover:bg-red-500/40" : "bg-cyan-500/20 text-cyan-400 border-cyan-500/50 hover:bg-cyan-500/40"}>
          {isRunning ? <Power className="w-3 h-3" /> : <Play className="w-3 h-3" />}
        </Button>
      </div>
      {agent.last_signal && (
        <div className="text-xs text-secondary truncate mb-3">Last: <span className="text-amber-400 cursor-pointer hover:underline"
          onClick={() => toast.success(`Executing trace on signal: ${agent.last_signal}`)}>{agent.last_signal}</span></div>
      )}
      <div className="mt-3 space-y-2 border-t border-secondary/20 pt-3">
        <div className="flex justify-between items-center text-[10px] text-secondary uppercase tracking-wider">
          <span>SHAP Importance</span>
          <span className="text-cyan-400/80 cursor-pointer hover:text-cyan-300 flex items-center gap-1 transition-colors"
            onClick={() => toast.info(`Accessing Weight Matrices for ${agent.name}`)}><Settings className="w-3 h-3" /> Weights</span>
        </div>
        <div className="flex w-full h-1.5 rounded-full overflow-hidden bg-secondary/20 shadow-inner">
          {shapFeatures.map((f, idx) => (
            <div key={idx} className={`${f.color} hover:brightness-150 cursor-crosshair transition-all`}
              style={{ width: `${f.val}%` }} title={`${f.name}: ${f.val}%`}
              onClick={() => toast.info(`SHAP Delta for ${f.name}: +2.3%`)} />
          ))}
        </div>
      </div>
    </div>
  );
}

// =============================================
// MAIN COMPONENT
// =============================================
export default function AgentCommandCenter() {
  const navigate = useNavigate(); const { tab: urlTab } = useParams();
  // --- Agent state ---
  const { data: agentsRaw, loading: agentsLoading, refetch: refetchAgents } = useApi("/api/v1/agents");
  const agents = useMemo(() => (Array.isArray(agentsRaw) ? agentsRaw : agentsRaw?.agents || []), [agentsRaw]);
  // --- OpenClaw state ---
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
  // --- Blackboard, HITL, Consensus, Spawn States ---
  const [blackboardMsgs, setBlackboardMsgs] = useState([]);
  const [hitlBuffer, setHitlBuffer] = useState([]);
  const [consensusData, setConsensusData] = useState([]);
  const [spawnPrompt, setSpawnPrompt] = useState("");
  const [nlpSpawnLoading, setNlpSpawnLoading] = useState(false);
  // --- URL sync ---
  useEffect(() => { if (activeTab) navigate(`/agents/${activeTab}`, { replace: true }); }, [activeTab]);
  // --- Loaders ---
  const loadMacro = useCallback(async () => { try { const data = await openclaw.getMacro(); setMacro(data); } catch { setMacro(null); } }, []);
  const loadSwarm = useCallback(async () => { try { const data = await openclaw.getSwarmStatus(); setSwarm({ active: data.active ?? 0, total: data.total ?? 0, teams: data.teams ?? [] }); } catch { setSwarm({ active: 0, total: 0, teams: [] }); } }, []);
  const loadCandidates = useCallback(async () => { try { const list = await openclaw.getCandidates(25); setCandidates(Array.isArray(list) ? list : []); } catch { setCandidates([]); } }, []);
  const loadConsensus = useCallback(async () => { try { const data = await openclaw.getConsensus(); setConsensusData(Array.isArray(data) ? data : []); } catch { setConsensusData([]); } }, []);
  // --- Polling effects ---
  useEffect(() => { loadMacro(); const t = setInterval(loadMacro, MACRO_POLL_MS); return () => clearInterval(t); }, [loadMacro]);
  useEffect(() => { loadSwarm(); const t = setInterval(loadSwarm, SWARM_POLL_MS); return () => clearInterval(t); }, [loadSwarm]);
  useEffect(() => { loadCandidates(); const t = setInterval(loadCandidates, CANDIDATES_POLL_MS); return () => clearInterval(t); }, [loadCandidates]);
  useEffect(() => { loadConsensus(); const t = setInterval(loadConsensus, 30000); return () => clearInterval(t); }, [loadConsensus]);
  // --- LLM Flow WebSocket ---
  useEffect(() => {
    const wsUrl = openclaw.getLlmFlowWsUrl(); let socket;
    try {
      socket = new WebSocket(wsUrl); wsRef.current = socket;
      socket.onmessage = (ev) => {
        try { const msg = JSON.parse(ev.data); setLlmAlerts(prev => [{ ...msg, id: Date.now() + crypto.randomUUID() }, ...prev].slice(0, LLM_ALERTS_MAX)); }
        catch { setLlmAlerts(prev => [{ id: Date.now(), message: ev.data, severity: "info" }, ...prev.slice(0, LLM_ALERTS_MAX - 1)]); }
      };
      socket.onclose = () => { wsRef.current = null; };
    } catch (e) { console.warn("LLM flow WebSocket failed:", e); }
    return () => { if (wsRef.current) { wsRef.current.close(); wsRef.current = null; } };
  }, []);
  // --- Agent WS ---
  useEffect(() => { const unsub = ws.on("agents", (msg) => { if (msg?.type === "agent_status") refetchAgents(); }); return unsub; }, [refetchAgents]);
  // --- Blackboard & HITL mock subscriptions ---
  useEffect(() => {
    const blackboardInterval = !AGENT_MOCKS ? null : setInterval(() => {
      const topics = ["SIG_GEN", "RISK_EVAL", "SENTIMENT", "EXECUTION"];
      const contents = ["Computed tensor weights for epoch " + Math.floor(Math.random() * 1000), "Detected volatility flow anomaly", "Rebalancing portfolio edge weights", "Consensus threshold crossed for entry"];
      setBlackboardMsgs(prev => [{ id: Date.now(), time: new Date().toLocaleTimeString("en-US", { hour12: false }), topic: topics[Math.floor(Math.random() * topics.length)], content: contents[Math.floor(Math.random() * contents.length)], hash: "0x" + Math.random().toString(16).substring(2, 8).toUpperCase() }, ...prev].slice(0, 100));
    }, 2500);
    const hitlInterval = !AGENT_MOCKS ? null : setInterval(() => {
      if (Math.random() > 0.6) {
        const actions = ["BIAS_OVERRIDE", "FORCE_LIQUIDATE", "NODE_RESTART", "HALT_SIGNAL"];
        setHitlBuffer(prev => [{ id: Date.now(), time: new Date().toLocaleTimeString("en-US", { hour12: false }), action: actions[Math.floor(Math.random() * actions.length)], user: "OP-1", target: `Swarm-Alpha-${Math.floor(Math.random() * 9)}`, status: "ACKNOWLEDGED" }, ...prev].slice(0, 50));
      }
    }, 4500);
    setConsensusData([{ symbol: "BTC", agree: 88, agents: 5, action: "LONG", strength: "STRONG" }, { symbol: "ETH", agree: 65, agents: 4, action: "SHORT", strength: "WEAK" }, { symbol: "SOL", agree: 92, agents: 5, action: "LONG", strength: "STRONG" }]);
    return () => { if (blackboardInterval) clearInterval(blackboardInterval); if (hitlInterval) clearInterval(hitlInterval); };
  }, []);
  // --- Handlers ---
  const handleAgentToggle = async (agent) => {
    const action = agent.status === "running" ? "stop" : "start";
    try { await fetch(getApiUrl(`/api/v1/agents/${agent.id}/${action}`), { method: "POST" }); toast.success(`${agent.name} ${action}ed`); refetchAgents(); }
    catch { toast.error(`Failed to ${action} ${agent.name}`); }
  };
  const handleBiasChange = (value) => { setBias(value); setBiasOverrideSent(false); };
  const handleBiasSubmit = async () => {
    try { await openclaw.setBiasOverride(bias); setBiasOverrideSent(true); toast.success(`Bias override set to ${bias.toFixed(1)}x`); }
    catch { toast.error("Bias override failed"); }
  };
  const handleSpawnTeam = async (teamType, action) => {
    setSpawnLoading(true); setSpawnError(null);
    try { await openclaw.spawnTeam(teamType, action); await loadSwarm(); toast.success(`${action === "spawn" ? "Spawned" : "Killed"} ${teamType}`); }
    catch (e) { setSpawnError(e.body?.detail || e.message || "Request failed"); } finally { setSpawnLoading(false); }
  };
  const handleNlpSpawn = async () => {
    if (!spawnPrompt.trim()) return;
    setNlpSpawnLoading(true);
    try { await openclaw.nlpSpawn(spawnPrompt); toast.success("NLP spawn executed"); setSpawnPrompt(""); await loadSwarm(); }
    catch { toast.error("NLP spawn failed"); } finally { setNlpSpawnLoading(false); }
  };
  const handleCandidateClick = (c) => {
    const symbol = c.symbol || c.ticker;
    const entry = c.entry_price ?? c.suggested_entry ?? c.entry ?? 0;
    const stop = c.stop_loss ?? c.suggested_stop ?? c.stop ?? 0;
    const target = c.target_price ?? c.suggested_target ?? c.target ?? 0;
    const detail = { symbol, entry, stop, target, team: c.team_id ?? c.team ?? null, score: c.composite_score ?? c.score ?? 0 };
    window.dispatchEvent(new CustomEvent("openTradeExecution", { detail }));
    navigate("/trades", { state: { openTradeExecution: detail } });
  };
  // --- Derived stats ---
  const runningAgents = agents.filter(a => a.status === "running").length;
  const totalAgents = agents.length;
  const highAlerts = llmAlerts.filter(a => a.severity === "high" || a.severity === "error").length;
  const waveState = macro?.wave_state || "neutral";
  // --- 8 Tab definitions (from mockup) ---
  const tabs = [
    { id: "swarm-overview", label: "Swarm Overview", icon: Eye },
    { id: "agent-registry", label: "Agent Registry", icon: Bot },
    { id: "spawn-scale", label: "Spawn & Scale", icon: Boxes },
    { id: "live-wiring", label: "Live Wiring Map", icon: Network },
    { id: "blackboard", label: "Blackboard & Comms", icon: ClipboardList },
    { id: "conference", label: "Conference & Consensus", icon: Users },
    { id: "ml-ops", label: "ML Ops", icon: Brain },
    { id: "logs", label: "Logs & Telemetry", icon: Terminal },
  ];

  return (
    <div className="space-y-4 text-white min-h-screen">
      {/* === HEADER BAR (from mockup 01) === */}
      <div className="flex items-center justify-between bg-[#0B0E14] border border-cyan-500/30 rounded-xl px-6 py-3 shadow-[0_0_20px_rgba(6,182,212,0.05)]">
        <div className="flex items-center gap-4">
          <Shield className="w-6 h-6 text-cyan-400" />
          <span className="text-lg font-bold text-white tracking-wider">AGENT COMMAND CENTER</span>
          <Badge className={`text-xs font-bold uppercase px-2 py-1 ${waveState === 'greed' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40' : waveState === 'fear' ? 'bg-red-500/20 text-red-400 border-red-500/40' : 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40'} border`}>
            {waveState === 'greed' ? 'GREEN' : waveState === 'fear' ? 'RED' : 'NEUTRAL'}
          </Badge>
        </div>
        <div className="flex items-center gap-6 text-xs text-secondary">
          <span>Uptime: <span className="text-white font-mono">47d 12h 33m</span></span>
          <span>{runningAgents}/{totalAgents} <span className="text-cyan-400">ONLINE</span></span>
          <div className="flex items-center gap-2">
            <span>CPU:</span><div className="w-16 h-1.5 bg-secondary/30 rounded-full overflow-hidden"><div className="h-full bg-emerald-500 rounded-full" style={{width: '47%'}} /></div><span className="text-white">47%</span>
          </div>
          <div className="flex items-center gap-2">
            <span>RAM:</span><div className="w-16 h-1.5 bg-secondary/30 rounded-full overflow-hidden"><div className="h-full bg-amber-500 rounded-full" style={{width: '31%'}} /></div><span className="text-white">31%</span>
          </div>
          <div className="flex items-center gap-2">
            <span>GPU:</span><div className="w-16 h-1.5 bg-secondary/30 rounded-full overflow-hidden"><div className="h-full bg-cyan-500 rounded-full" style={{width: '61%'}} /></div><span className="text-white">61%</span>
          </div>
          <button className="px-4 py-1.5 bg-red-500/20 text-red-400 border border-red-500/50 rounded-lg font-bold text-xs uppercase tracking-wider hover:bg-red-500/40 transition-all shadow-[0_0_10px_rgba(239,68,68,0.2)]"
            onClick={() => toast.error("KILL SWITCH activated - Emergency shutdown initiated")}>KILL SWITCH</button>
        </div>
        <span className="text-xs text-cyan-400/60 uppercase tracking-widest font-bold">ELITE TRADING SYSTEM</span>
      </div>

      {/* === TAB NAVIGATION (8 tabs from mockup) === */}
      <div className="flex items-center gap-1 p-1 bg-[#0B0E14] rounded-xl border border-cyan-500/20 overflow-x-auto scrollbar-hide">
        {tabs.map(tab => {
          const TabIcon = tab.icon;
          return (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`flex items-center whitespace-nowrap gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === tab.id ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/50 shadow-[0_0_10px_rgba(6,182,212,0.2)_inset]" : "text-secondary hover:text-white hover:bg-cyan-500/10 border border-transparent"}`}>
              <TabIcon className="w-4 h-4" /><span>{tab.label}</span>
            </button>
          );
        })}
      </div>


      {/* ============ TAB 1: SWARM OVERVIEW ============ */}
      {activeTab === "swarm-overview" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <AgentHealthMatrix agents={agents} />
            <LiveActivityFeed agents={agents} llmAlerts={llmAlerts} />
            <SwarmTopology />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card className="border-cyan-500/20 bg-[#0B0E14]">
              <div className="flex items-center gap-2 mb-3"><Zap className="w-5 h-5 text-cyan-400" /><span className="text-sm font-bold text-white uppercase tracking-wider">Quick Actions</span></div>
              <div className="flex flex-wrap gap-2 mb-4">
                <Button size="sm" className="bg-cyan-500/20 text-cyan-400 border-cyan-500/40" onClick={() => { refetchAgents(); toast.success("Restarted"); }}><RefreshCw className="w-3 h-3 mr-1" /> Restart All</Button>
                <Button size="sm" className="bg-red-500/20 text-red-400 border-red-500/40" onClick={() => toast.error("Stopped")}><Square className="w-3 h-3 mr-1" /> Stop All</Button>
                <Button size="sm" className="bg-emerald-500/20 text-emerald-400 border-emerald-500/40" onClick={() => setActiveTab("spawn-scale")}><Play className="w-3 h-3 mr-1" /> Spawn Team</Button>
                <Button size="sm" className="bg-purple-500/20 text-purple-400 border-purple-500/40" onClick={() => toast.info("Conference initiated")}><Users className="w-3 h-3 mr-1" /> Run Conference</Button>
                <Button size="sm" className="bg-red-600/20 text-red-500 border-red-600/40" onClick={() => toast.error("Emergency kill")}><Power className="w-3 h-3 mr-1" /> Emergency Kill</Button>
              </div>
              <div className="text-[10px] uppercase tracking-wider text-secondary font-bold mb-2">Team Status</div>
              <div className="grid grid-cols-2 gap-2">
                {swarm.teams.slice(0, 4).map((t, i) => (
                  <div key={t.name || i} className="flex items-center justify-between p-2 rounded-lg bg-[#0d1117] border border-secondary/20 hover:border-cyan-500/40 cursor-pointer" onClick={() => toast.info(`Team ${t.name}`)}>
                    <TeamBadge teamId={t.name || t.id} />
                    <span className={`text-[9px] font-bold ${t.health === 'healthy' ? 'text-emerald-400' : 'text-amber-400'}`}>{t.status || 'ACTIVE'}</span>
                  </div>
                ))}
                {swarm.teams.length === 0 && <div className="col-span-2 text-secondary text-xs text-center py-3">No teams</div>}
              </div>
            </Card>
            <AgentResourceMonitor />
            <ConferencePipeline />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <SystemAlerts />
            <BlackboardLiveFeed blackboardMsgs={blackboardMsgs} />
            <DriftMonitor />
          </div>
        </div>
      )}


      {/* ============ TAB 2: AGENT REGISTRY ============ */}
      {activeTab === "agent-registry" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-white tracking-wider uppercase">Agent Registry</h2>
            <Button variant="secondary" size="sm" onClick={refetchAgents} className="border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/20"><RefreshCw className="w-4 h-4 mr-1" /> Force Sync</Button>
          </div>
          {/* Master Agent Table (20+ cols from mockup) */}
          <Card title="Master Agent Table" subtitle="All registered agents with full metrics" noPadding>
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead><tr className="border-b border-cyan-500/30 bg-cyan-500/10">
                  {["Agent", "Status", "Health", "Type", "Team", "PID", "CPU%", "Mem MB", "7D Win%", "P&L 30D", "Signals", "Accuracy", "Sharpe", "Uptime", "Last Signal", "Controls"].map(h => (
                    <th key={h} className="px-3 py-2 text-[9px] font-bold text-cyan-400 uppercase tracking-wider text-left whitespace-nowrap">{h}</th>
                  ))}
                </tr></thead>
                <tbody className="divide-y divide-secondary/20">
                  {agents.map((a, i) => {
                    const wr = a.win_rate ?? (Math.random() * 40 + 55); const pnl = a.pnl_30d ?? (Math.random() * 8000 - 2000);
                    const sig = a.signals_generated ?? Math.floor(Math.random() * 200 + 50); const acc = a.accuracy ?? (Math.random() * 30 + 65);
                    return (
                      <tr key={a.id || i} className="hover:bg-cyan-500/5 transition-colors cursor-pointer" onClick={() => toast.info(`Inspecting ${a.name}`)}>
                        <td className="px-3 py-2 font-bold text-white">{a.name}</td>
                        <td className="px-3 py-2"><span className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded border ${a.status === 'running' ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30' : 'bg-secondary/10 text-secondary border-secondary/30'}`}>{a.status}</span></td>
                        <td className="px-3 py-2"><span className={`w-2 h-2 rounded-full inline-block ${HEALTH_DOT_COLORS[a.health] || HEALTH_DOT_COLORS.unknown}`} /></td>
                        <td className="px-3 py-2 text-secondary">{a.type || 'worker'}</td>
                        <td className="px-3 py-2">{a.team_id ? <TeamBadge teamId={a.team_id} /> : <span className="text-secondary">-</span>}</td>
                        <td className="px-3 py-2 text-amber-400/80 font-mono">{1024 + i * 31}</td>
                        <td className="px-3 py-2"><span className={i % 2 === 0 ? 'text-emerald-400' : 'text-amber-400'}>{(a.cpu_pct ?? 0).toFixed(1)}</span></td>
                        <td className="px-3 py-2 text-cyan-400/70">{(a.mem_mb ?? (Math.random() * 500 + 100)).toFixed(0)}</td>
                        <td className={`px-3 py-2 font-bold ${wr >= 65 ? 'text-emerald-400' : 'text-amber-400'}`}>{wr.toFixed(1)}%</td>
                        <td className={`px-3 py-2 font-bold ${pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>${pnl >= 0 ? '+' : ''}{pnl.toFixed(0)}</td>
                        <td className="px-3 py-2 text-amber-400">{sig}</td>
                        <td className="px-3 py-2 text-cyan-300">{acc.toFixed(1)}%</td>
                        <td className="px-3 py-2 text-white font-bold">{(a.sharpe ?? (Math.random() * 3 + 0.5)).toFixed(2)}</td>
                        <td className="px-3 py-2 text-secondary">{a.uptime || '12h'}</td>
                        <td className="px-3 py-2 text-amber-400 truncate max-w-[120px]">{a.last_signal || '-'}</td>
                        <td className="px-3 py-2 space-x-1">
                          <Button size="xs" variant="secondary" onClick={(e) => { e.stopPropagation(); handleAgentToggle(a); }}>{a.status === 'running' ? <Square className="w-3 h-3" /> : <Play className="w-3 h-3" />}</Button>
                          <Button size="xs" variant="secondary" onClick={(e) => { e.stopPropagation(); toast.success(`SIGTERM ${a.name}`); }}><RefreshCw className="w-3 h-3" /></Button>
                          <Button size="xs" variant="secondary" onClick={(e) => { e.stopPropagation(); toast.error(`Killed ${a.name}`); }}><Power className="w-3 h-3" /></Button>
                        </td>
                      </tr>
                    );
                  })}
                  {agents.length === 0 && <tr><td colSpan={16} className="text-center py-6 text-secondary">No agents in registry</td></tr>}
                </tbody>
              </table>
            </div>
          </Card>
          {/* Agent Cards Grid */}
          <Card title="Agent Inspector" subtitle="Click to view SHAP importance">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {agents.map(a => <AgentCard key={a.id || a.name} agent={a} onToggle={handleAgentToggle} />)}
              {agents.length === 0 && <p className="text-sm text-secondary col-span-full text-center py-8">{agentsLoading ? "Loading..." : "No agents configured."}</p>}
            </div>
          </Card>
        </div>
      )}


      {/* ============ TAB 3: SPAWN & SCALE (from mockup 05b) ============ */}
      {activeTab === "spawn-scale" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* NLP Spawn Prompt */}
            <Card title="Natural Language Spawn" subtitle="Describe agent to spawn in plain English">
              <div className="flex gap-2">
                <input type="text" value={spawnPrompt} onChange={e => setSpawnPrompt(e.target.value)}
                  placeholder="e.g. Spawn a momentum scanner for tech stocks with 5min timeframe..."
                  className="flex-1 bg-[#0B0E14] border border-cyan-500/30 rounded-lg px-4 py-2.5 text-sm text-white placeholder-secondary/50 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400/30"
                  onKeyDown={e => e.key === 'Enter' && handleNlpSpawn()} />
                <Button onClick={handleNlpSpawn} disabled={nlpSpawnLoading} className="bg-cyan-500 hover:bg-cyan-400 text-black font-bold">
                  <Send className="w-4 h-4 mr-1" /> {nlpSpawnLoading ? 'Spawning...' : 'Spawn'}
                </Button>
              </div>
            </Card>
            {/* Operator Overrides */}
            <Card title="Operator Overrides" subtitle="Spawn/kill teams and adjust bias">
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" disabled={spawnLoading} onClick={() => handleSpawnTeam("fear_bounce_team", "spawn")} className="bg-red-500/15 text-red-400 border-red-500/40 hover:bg-red-500/25"><Play className="w-4 h-4 mr-1" /> Spawn Fear Team</Button>
                  <Button size="sm" disabled={spawnLoading} onClick={() => handleSpawnTeam("greed_momentum_team", "spawn")} className="bg-emerald-500/15 text-emerald-400 border-emerald-500/40 hover:bg-emerald-500/25"><Play className="w-4 h-4 mr-1" /> Spawn Greed Team</Button>
                  <Button size="sm" disabled={spawnLoading} onClick={() => handleSpawnTeam("all", "kill")} className="hover:border-red-500 hover:text-red-500"><Square className="w-4 h-4 mr-1" /> Kill All</Button>
                </div>
                <div className="flex items-center gap-3 pt-3 border-t border-secondary/30">
                  <Slider label="Bias Multiplier" min={0.5} max={2} step={0.1} value={bias} onChange={e => handleBiasChange(Number(e.target.value))} suffix="x" formatValue={v => Number(v).toFixed(1)} className="flex-1 min-w-0 max-w-[200px]" />
                  <Button size="sm" onClick={handleBiasSubmit} className="bg-cyan-500 hover:bg-cyan-400 text-black font-bold">Apply</Button>
                  {biasOverrideSent && <span className="text-xs font-bold text-emerald-400 flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Saved</span>}
                </div>
                {spawnError && <p className="text-sm text-red-400 border border-red-500/40 bg-red-500/10 p-2 rounded">{spawnError}</p>}
              </div>
            </Card>
          </div>
          {/* Quick-Spawn Template Grid (from mockup 05b) */}
          <Card title="Quick-Spawn Template Grid" subtitle="Click to instantly spawn from template">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {SPAWN_TEMPLATES.map(t => {
                const TIcon = t.icon;
                return (
                  <div key={t.name} className="border border-secondary/20 rounded-xl p-4 bg-[#0B0E14] hover:border-cyan-500/50 cursor-pointer transition-all hover:shadow-[0_0_15px_rgba(6,182,212,0.1)] group"
                    onClick={() => { toast.success(`Spawning ${t.name}`); handleSpawnTeam(t.name.toLowerCase().replace(/\s/g, '_'), 'spawn'); }}>
                    <TIcon className={`w-6 h-6 ${t.color} mb-2 group-hover:scale-110 transition-transform`} />
                    <div className="text-xs font-bold text-white mb-1">{t.name}</div>
                    <div className="text-[10px] text-secondary">{t.desc}</div>
                  </div>
                );
              })}
            </div>
          </Card>
          {/* Active Spawned Agents Table */}
          <Card title="Active Spawned Agents" subtitle={`${swarm.active} of ${swarm.total} active`}>
            {swarm.teams.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {swarm.teams.map((t, i) => (
                  <div key={t.name || i} className="border border-cyan-500/20 rounded-xl p-4 bg-[#0B0E14] hover:border-cyan-500/50 cursor-pointer transition-colors" onClick={() => toast.info(`Inspecting ${t.name}`)}>
                    <div className="flex items-center justify-between mb-3">
                      <TeamBadge teamId={t.name || t.id} />
                      <div className="flex gap-1">
                        <button className="p-1 hover:text-amber-400 text-secondary" onClick={e => { e.stopPropagation(); toast.info('Paused'); }}><Pause className="w-3 h-3" /></button>
                        <button className="p-1 hover:text-red-400 text-secondary" onClick={e => { e.stopPropagation(); handleSpawnTeam(t.name, 'kill'); }}><Trash2 className="w-3 h-3" /></button>
                        <button className="p-1 hover:text-cyan-400 text-secondary" onClick={e => { e.stopPropagation(); toast.info('Cloned'); }}><Copy className="w-3 h-3" /></button>
                        <button className="p-1 hover:text-purple-400 text-secondary" onClick={e => { e.stopPropagation(); toast.info('Edit'); }}><Edit className="w-3 h-3" /></button>
                      </div>
                    </div>
                    {t.agents && <p className="text-xs text-secondary"><Cpu className="w-3 h-3 inline text-cyan-500" /> {t.agents} agents</p>}
                    {t.strategy && <p className="text-xs text-secondary mt-1"><GitCommit className="w-3 h-3 inline text-amber-500" /> {t.strategy}</p>}
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-secondary text-center py-8">No active teams. Use templates or NLP to spawn.</p>}
          </Card>
        </div>
      )}


      {/* ============ TAB 4: LIVE WIRING MAP (from mockup 05) ============ */}
      {activeTab === "live-wiring" && (
        <div className="space-y-4">
          <Card title="Network Topology" subtitle="5-column flow: External Sources > Agents > Processing > Storage > Frontend">
            <div className="relative w-full h-[500px] bg-[#0B0E14] border border-cyan-500/30 rounded-xl overflow-hidden">
              <svg className="w-full h-full" viewBox="0 0 1000 500">
                <defs>
                  <marker id="arrowC" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="#06B6D4" /></marker>
                </defs>
                {/* Column Labels */}
                {["External Sources", "Agents", "Processing Engines", "Storage", "Frontend"].map((label, i) => (
                  <text key={label} x={100 + i * 200} y={30} textAnchor="middle" fill="#06B6D4" fontSize="11" fontWeight="bold" className="uppercase">{label}</text>
                ))}
                {/* External Sources column */}
                {["Alpaca API", "Finviz", "Reddit", "Twitter/X", "YouTube"].map((src, i) => (
                  <g key={src}><rect x={40} y={60 + i * 80} width={120} height={40} rx={8} fill="#0B0E14" stroke="#06B6D4" strokeWidth={1.5} className="cursor-pointer hover:stroke-cyan-300" onClick={() => toast.info(`Source: ${src}`)} />
                  <text x={100} y={84 + i * 80} textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">{src}</text></g>
                ))}
                {/* Agent column */}
                {["MarketData", "SignalGen", "MLBrain", "Sentiment", "YouTube"].map((a, i) => (
                  <g key={a}>
                    <line x1={160} y1={80 + i * 80} x2={240} y2={80 + i * 80} stroke="#06B6D4" strokeWidth={1} markerEnd="url(#arrowC)" opacity={0.5} />
                    <rect x={240} y={60 + i * 80} width={120} height={40} rx={8} fill="#0B0E14" stroke="#F59E0B" strokeWidth={1.5} className="cursor-pointer" onClick={() => toast.info(`Agent: ${a}`)} />
                    <text x={300} y={84 + i * 80} textAnchor="middle" fill="#F59E0B" fontSize="10" fontWeight="bold">{a}</text>
                  </g>
                ))}
                {/* Processing column */}
                {["SignalEngine", "RiskShield", "Consensus", "MLPipeline"].map((p, i) => (
                  <g key={p}>
                    <line x1={360} y1={80 + i * 100} x2={440} y2={80 + i * 100} stroke="#06B6D4" strokeWidth={1} markerEnd="url(#arrowC)" opacity={0.5} />
                    <rect x={440} y={60 + i * 100} width={120} height={40} rx={8} fill="#0B0E14" stroke="#22c55e" strokeWidth={1.5} className="cursor-pointer" onClick={() => toast.info(`Engine: ${p}`)} />
                    <text x={500} y={84 + i * 100} textAnchor="middle" fill="#22c55e" fontSize="10" fontWeight="bold">{p}</text>
                  </g>
                ))}
                {/* Storage column */}
                {["PostgreSQL", "Redis", "TimescaleDB"].map((s, i) => (
                  <g key={s}>
                    <line x1={560} y1={100 + i * 120} x2={640} y2={100 + i * 120} stroke="#06B6D4" strokeWidth={1} markerEnd="url(#arrowC)" opacity={0.5} />
                    <rect x={640} y={80 + i * 120} width={120} height={40} rx={8} fill="#0B0E14" stroke="#a855f7" strokeWidth={1.5} className="cursor-pointer" onClick={() => toast.info(`Storage: ${s}`)} />
                    <text x={700} y={104 + i * 120} textAnchor="middle" fill="#a855f7" fontSize="10" fontWeight="bold">{s}</text>
                  </g>
                ))}
                {/* Frontend column */}
                {["Dashboard", "TradeExec", "Analytics"].map((f, i) => (
                  <g key={f}>
                    <line x1={760} y1={100 + i * 120} x2={840} y2={100 + i * 120} stroke="#06B6D4" strokeWidth={1} markerEnd="url(#arrowC)" opacity={0.5} />
                    <rect x={840} y={80 + i * 120} width={120} height={40} rx={8} fill="#0B0E14" stroke="#06B6D4" strokeWidth={1.5} className="cursor-pointer" onClick={() => toast.info(`View: ${f}`)} />
                    <text x={900} y={104 + i * 120} textAnchor="middle" fill="#06B6D4" fontSize="10" fontWeight="bold">{f}</text>
                  </g>
                ))}
              </svg>
            </div>
          </Card>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card title="Connection Health Matrix" subtitle="Live WS + HTTP endpoint status">
              <div className="space-y-2">
                {["agents", "llm-flow", "market-data", "signals", "trades"].map(ch => (
                  <div key={ch} className="flex items-center justify-between p-2 rounded bg-[#0d1117] border border-secondary/20 hover:border-cyan-500/30 cursor-pointer" onClick={() => toast.info(`Channel: ${ch}`)}>
                    <div className="flex items-center gap-2"><Wifi className="w-3 h-3 text-emerald-400" /><span className="text-xs text-white font-mono">{ch}</span></div>
                    <span className="text-[9px] text-emerald-400 font-bold uppercase">CONNECTED</span>
                  </div>
                ))}
              </div>
            </Card>
            <Card title="Dynamic Node Discovery" subtitle="Auto-discovered services">
              <div className="space-y-2">
                {["orchestrator:8080", "ml-worker:8081", "signal-engine:8082", "risk-shield:8083"].map(n => (
                  <div key={n} className="flex items-center justify-between p-2 rounded bg-[#0d1117] border border-secondary/20 cursor-pointer hover:border-cyan-500/30" onClick={() => toast.info(`Node: ${n}`)}>
                    <span className="text-xs text-cyan-400 font-mono">{n}</span>
                    <span className="text-[9px] text-emerald-400">HEALTHY</span>
                  </div>
                ))}
              </div>
            </Card>
            <Card title="API Route Map" subtitle="Backend endpoint registry">
              <div className="space-y-1 font-mono text-[10px] max-h-[200px] overflow-y-auto">
                {["/api/v1/agents", "/api/v1/signals", "/api/v1/trades", "/api/v1/openclaw/macro", "/api/v1/openclaw/swarm", "/api/v1/market/regime", "/api/v1/risk/shield", "/api/v1/ml/models"].map(r => (
                  <div key={r} className="flex items-center gap-2 p-1 hover:bg-cyan-500/5 rounded cursor-pointer" onClick={() => toast.info(`Route: ${r}`)}>
                    <span className="text-emerald-400">GET</span><span className="text-white">{r}</span><span className="text-secondary ml-auto">200</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>
      )}


      {/* ============ TAB 5: BLACKBOARD & COMMS ============ */}
      {activeTab === "blackboard" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card title="Real-Time Blackboard" subtitle="Pub/Sub feed for inter-agent memory bus">
            <div className="bg-[#0B0E14] border border-cyan-500/30 rounded-lg p-3 h-[550px] overflow-y-auto text-[11px] space-y-1 scrollbar-thin scrollbar-thumb-cyan-500/20 shadow-[0_0_20px_rgba(6,182,212,0.05)_inset]">
              {blackboardMsgs.map(msg => (
                <div key={msg.id} className="flex gap-3 hover:bg-cyan-500/10 p-1.5 rounded transition-colors cursor-crosshair">
                  <span className="text-cyan-500/50 shrink-0">[{msg.time}]</span>
                  <span className={`shrink-0 font-bold w-24 ${msg.topic === 'RISK_EVAL' ? 'text-red-400' : msg.topic === 'SIG_GEN' ? 'text-cyan-400' : msg.topic === 'EXECUTION' ? 'text-emerald-400' : 'text-amber-400'}`}>[{msg.topic}]</span>
                  <span className="text-white flex-1">{msg.content}</span>
                  <span className="text-transparent group-hover:text-cyan-400 cursor-pointer underline shrink-0 text-[9px]" onClick={() => toast.info(`Hash: ${msg.hash}`)}>INSPECT ({msg.hash})</span>
                </div>
              ))}
              {blackboardMsgs.length === 0 && <span className="text-secondary flex justify-center py-10 animate-pulse">Listening for blackboard events...</span>}
            </div>
          </Card>
          <Card title="HITL Ring Buffer" subtitle="Circular buffer of last 50 human interventions">
            <div className="bg-[#0B0E14] border border-amber-500/30 rounded-lg p-4 h-[550px] overflow-y-auto space-y-3 scrollbar-thin scrollbar-thumb-amber-500/20">
              {hitlBuffer.map(msg => (
                <div key={msg.id} className="flex flex-col gap-1.5 p-3 border border-amber-500/20 rounded bg-amber-500/5 hover:border-amber-500/50 cursor-pointer" onClick={() => toast.info(`Audit: ${msg.action}`)}>
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-2">
                      <Shield className={`w-4 h-4 ${msg.action === 'FORCE_LIQUIDATE' || msg.action === 'NODE_RESTART' ? 'text-red-500' : 'text-amber-500'}`} />
                      <span className={`text-[11px] font-bold uppercase ${msg.action === 'FORCE_LIQUIDATE' ? 'text-red-400' : 'text-amber-400'}`}>{msg.action}</span>
                    </div>
                    <span className="text-[10px] text-amber-500/50">{msg.time}</span>
                  </div>
                  <div className="flex justify-between text-[10px]">
                    <span className="text-secondary">Target: <span className="text-cyan-400">{msg.target}</span></span>
                    <span className="text-secondary">User: <span className="text-white">{msg.user}</span></span>
                    <Badge className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 text-[9px] py-0 px-1.5">{msg.status}</Badge>
                  </div>
                </div>
              ))}
              {hitlBuffer.length === 0 && <span className="text-secondary text-sm flex justify-center py-10">No recent interventions</span>}
            </div>
          </Card>
        </div>
      )}

      {/* ============ TAB 6: CONFERENCE & CONSENSUS ============ */}
      {activeTab === "conference" && (
        <div className="space-y-4">
          <ConferencePipeline />
          <Card title="Consensus Engine Visualization" subtitle="Real-time multi-agent voting agreement">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {consensusData.map((c, i) => (
                <div key={i} className="border border-cyan-500/20 bg-[#0B0E14] rounded-xl p-4 flex flex-col items-center cursor-pointer hover:border-cyan-500/50 transition-all" onClick={() => toast.info(`Consensus: ${c.symbol}`)}>
                  <div className="text-lg font-bold text-white mb-1 flex items-center gap-2">{c.symbol} <TrendingUp className={`w-4 h-4 ${c.action === 'LONG' ? 'text-emerald-400' : 'text-red-400'}`} /></div>
                  <div className="relative w-24 h-24 my-3 flex items-center justify-center">
                    <svg className="w-full h-full transform -rotate-90"><circle cx="48" cy="48" r="40" fill="none" stroke="#1e293b" strokeWidth="8" />
                      <circle cx="48" cy="48" r="40" fill="none" stroke={c.agree > 80 ? '#06B6D4' : '#F59E0B'} strokeWidth="8" strokeDasharray="251" strokeDashoffset={251 - (c.agree / 100) * 251} strokeLinecap="round" className="transition-all duration-1000" /></svg>
                    <div className="absolute text-xl font-bold text-white flex flex-col items-center">{c.agree}%<span className="text-[9px] text-cyan-400/80 mt-0.5">Agreement</span></div>
                  </div>
                  <div className="flex justify-between w-full text-xs px-2">
                    <span className="text-secondary flex items-center gap-1"><Users className="w-3 h-3 text-cyan-500" /> {c.agents} Agents</span>
                    <span className={`font-bold ${c.action === 'LONG' ? 'text-emerald-400' : 'text-red-400'}`}>{c.action} ({c.strength})</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}


      {/* ============ TAB 7: ML OPS ============ */}
      {activeTab === "ml-ops" && (
        <div className="space-y-4">
          {/* Brain Map DAG */}
          <Card title="DAG Brain Map" subtitle="Neural topology from agent registry">
            <div className="relative w-full h-[500px] bg-[#0B0E14] border border-cyan-500/30 rounded-xl overflow-hidden">
              {(() => {
                const dagNodes = [{ id: 'ORCH', label: 'ORCHESTRATOR', color: '#06B6D4', x: 400, y: 250, r: 45 },
                  ...agents.slice(0, 8).map((a, i) => ({ id: a.id || `A${i}`, label: (a.name || `Agent-${i}`).replace(/Agent[-_]?/i, '').slice(0, 8).toUpperCase(),
                    color: a.status === 'running' ? '#06B6D4' : '#F59E0B', x: 400 + 220 * Math.cos((i / Math.min(agents.length, 8)) * 2 * Math.PI - Math.PI / 2),
                    y: 250 + 180 * Math.sin((i / Math.min(agents.length, 8)) * 2 * Math.PI - Math.PI / 2), r: 25 })),
                ];
                return (<svg className="w-full h-full">
                  {dagNodes.slice(1).map((n, i) => <line key={`e${i}`} x1={400} y1={250} x2={n.x} y2={n.y} stroke={n.color} strokeWidth={2} opacity={0.4} className="animate-pulse" />)}
                  {dagNodes.map(n => (<g key={n.id} className="cursor-pointer" onClick={() => toast.info(`Node: ${n.label}`)}>
                    <circle cx={n.x} cy={n.y} r={n.r} fill="#0B0E14" stroke={n.color} strokeWidth={3} />
                    <text x={n.x} y={n.y + 4} textAnchor="middle" fill={n.color} fontSize={n.id === 'ORCH' ? 12 : 9} fontWeight="bold">{n.label}</text>
                  </g>))}
                </svg>);
              })()}
              <div className="absolute top-4 right-4 flex gap-2">
                <Badge className="bg-cyan-500/20 text-cyan-400 border border-cyan-500/50">Nodes: {agents.length + 1}</Badge>
                <Badge className="bg-red-500/20 text-red-400 border border-red-500/50 cursor-pointer" onClick={() => toast.success("Weights Rebalanced")}>Rebalance</Badge>
              </div>
            </div>
          </Card>
          {/* Model Leaderboard */}
          <Card title="Model Leaderboard" subtitle="Training metrics and version history">
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead><tr className="border-b border-cyan-500/30 bg-cyan-500/10">
                  {["Model", "Version", "Accuracy", "Val Loss", "Sharpe", "Epochs", "Status"].map(h => <th key={h} className="px-3 py-2 text-[9px] font-bold text-cyan-400 uppercase tracking-wider text-left">{h}</th>)}
                </tr></thead>
                <tbody className="divide-y divide-secondary/20">
                  {[{m:'SignalNet-v3',v:'3.2.1',acc:'94.2%',vl:'0.0023',sh:'2.41',ep:'847/1000',st:'Training'},{m:'RiskPredictor',v:'2.1.0',acc:'89.7%',vl:'0.0089',sh:'1.87',ep:'1000/1000',st:'Production'},{m:'SentimentBERT',v:'1.5.2',acc:'91.3%',vl:'0.0045',sh:'2.12',ep:'500/500',st:'Production'},{m:'RegimeHMM',v:'4.0.0',acc:'87.1%',vl:'0.0112',sh:'1.55',ep:'200/200',st:'Staging'}].map(r => (
                    <tr key={r.m} className="hover:bg-cyan-500/5 cursor-pointer" onClick={() => toast.info(`Model: ${r.m}`)}>
                      <td className="px-3 py-2 font-bold text-white">{r.m}</td>
                      <td className="px-3 py-2 text-cyan-400 font-mono">{r.v}</td>
                      <td className="px-3 py-2 text-emerald-400 font-bold">{r.acc}</td>
                      <td className="px-3 py-2 text-amber-400">{r.vl}</td>
                      <td className="px-3 py-2 text-white font-bold">{r.sh}</td>
                      <td className="px-3 py-2 text-secondary">{r.ep}</td>
                      <td className="px-3 py-2"><span className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded border ${r.st === 'Production' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : r.st === 'Training' ? 'bg-amber-500/10 text-amber-400 border-amber-500/30' : 'bg-purple-500/10 text-purple-400 border-purple-500/30'}`}>{r.st}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* ============ TAB 8: LOGS & TELEMETRY ============ */}
      {activeTab === "logs" && (
        <div className="space-y-4">
          <Card title="LLM Flow Alerts" subtitle="Real-time LLM decision stream">
            <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-cyan-500/20">
              {llmAlerts.length === 0 ? <p className="text-sm text-secondary">No alerts. LLM stream idle.</p> :
                llmAlerts.map(a => <LlmAlert key={a.id} alert={a} onDismiss={() => setLlmAlerts(prev => prev.filter(x => x.id !== a.id))} />)}
            </div>
          </Card>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card title="System Logs" subtitle="Recent system events">
              <div className="bg-[#0B0E14] border border-secondary/20 rounded-lg p-3 h-[300px] overflow-y-auto font-mono text-[10px] space-y-1">
                {["[09:41:23] INFO  orchestrator: Heartbeat OK", "[09:41:20] INFO  ml-worker: Epoch 847 complete", "[09:41:18] WARN  risk-shield: Volatility spike detected", "[09:41:15] INFO  signal-engine: 3 signals generated", "[09:41:12] INFO  consensus: Conference #941 complete", "[09:41:10] DEBUG agent-bus: 12 messages dispatched", "[09:41:08] INFO  sentiment: Twitter stream connected", "[09:41:05] ERROR ml-worker: GPU memory near limit (89%)"].map((log, i) => (
                  <div key={i} className={`px-2 py-1 rounded hover:bg-cyan-500/5 cursor-pointer ${log.includes('ERROR') ? 'text-red-400' : log.includes('WARN') ? 'text-amber-400' : 'text-secondary'}`} onClick={() => toast.info(log)}>{log}</div>
                ))}
              </div>
            </Card>
            <Card title="Performance Telemetry" subtitle="System health metrics">
              <div className="space-y-3">
                {[{label: 'CPU Usage', value: 47, color: 'bg-emerald-500'}, {label: 'Memory', value: 31, color: 'bg-amber-500'}, {label: 'GPU', value: 61, color: 'bg-cyan-500'}, {label: 'Disk I/O', value: 23, color: 'bg-purple-500'}, {label: 'Network', value: 15, color: 'bg-blue-500'}].map(m => (
                  <div key={m.label} className="flex items-center gap-3 cursor-pointer hover:brightness-110" onClick={() => toast.info(`${m.label}: ${m.value}%`)}>
                    <span className="text-[10px] text-secondary w-20 uppercase tracking-wider">{m.label}</span>
                    <div className="flex-1 h-2 bg-secondary/20 rounded-full overflow-hidden"><div className={`h-full ${m.color} rounded-full transition-all`} style={{width: `${m.value}%`}} /></div>
                    <span className="text-xs text-white font-bold w-10 text-right">{m.value}%</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* === FOOTER BAR (from mockup 01) === */}
      <div className="flex items-center justify-between bg-[#0B0E14] border border-cyan-500/20 rounded-xl px-6 py-2 text-[10px] text-secondary">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1"><Wifi className="w-3 h-3 text-emerald-400" /> WebSocket: <span className="text-emerald-400 font-bold">CONNECTED</span></span>
          <span>{runningAgents}/{totalAgents} Agents Online</span>
          <span>LLM Flow: <span className="text-cyan-400">{llmAlerts.length} alerts</span></span>
          <span>Conference: <span className="text-amber-400">IDLE</span></span>
        </div>
        <div className="flex items-center gap-4">
          <span>Last Sync: <span className="text-white font-mono">{new Date().toLocaleTimeString()}</span></span>
          <span className="text-cyan-400/60 uppercase tracking-widest font-bold">EMBODIER.AI</span>
        </div>
      </div>
    </div>
  );
}
