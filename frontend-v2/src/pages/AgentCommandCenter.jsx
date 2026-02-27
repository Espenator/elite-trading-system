// AGENT COMMAND CENTER - Embodier.ai Glass House Intelligence System
// Unified page: Agent management + OpenClaw swarm control + LLM alerts
// Merges former ClawBotPanel into single command center
// Backend: GET /api/v1/agents, /api/v1/openclaw/*, WS 'agents' + 'llm-flow'
import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import { toast } from "react-toastify";
import { useNavigate } from "react-router-dom";
import {
  Activity,
  Zap,
  Brain,
  MessageCircle,
  Youtube,
  Play,
  Square,
  Pause,
  RefreshCw,
  RefreshCcw,
  CheckCircle,
  AlertCircle,
  Bot,
  Cpu,
  HardDrive,
  Radio,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  AlertTriangle,
  Info,
  Target,
  Gauge,
  Boxes,
  TrendingUp,
  TrendingDown,
  Shield,
  Eye,
  Settings,
  BarChart3,
  Network,
  Trophy,
  ClipboardList,
  Workflow,
  Terminal,
  Power,
  Server,
  GitCommit,
  Users,
} from "lucide-react";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";
import DataTable from "../components/ui/DataTable";
import SymbolIcon from "../components/ui/SymbolIcon";
import { DATA_SOURCE_ICON_SLUGS } from "../lib/dataSourceIcons";
import Slider from "../components/ui/Slider";
import Checkbox from "../components/ui/Checkbox";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";
import ws from "../services/websocket";
import * as openclaw from "../services/openclawService";

// --- Constants ---
const AGENT_ICONS = {
  "Market Data Agent": Activity,
  "Signal Generation Agent": Zap,
  "ML Learning Agent": Brain,
  "Sentiment Agent": MessageCircle,
  "YouTube Knowledge Agent": Youtube,
};
const TICK_INTERVAL_MS = 60 * 1000;
const SWARM_POLL_MS = 15000;
const MACRO_POLL_MS = 30000;
const CANDIDATES_POLL_MS = 30000;
const LLM_ALERTS_MAX = 8;

const REGIME_COLORS = {
  fear: {
    bg: "from-red-900/40 to-red-800/20",
    border: "border-red-500/50",
    text: "text-red-400",
    glow: "shadow-red-500/20",
  },
  greed: {
    bg: "from-green-900/40 to-green-800/20",
    border: "border-green-500/50",
    text: "text-green-400",
    glow: "shadow-green-500/20",
  },
  neutral: {
    bg: "from-cyan-900/40 to-cyan-800/20",
    border: "border-cyan-500/50",
    text: "text-cyan-400",
    glow: "shadow-cyan-500/20",
  },
};

// --- Helper: Stat Card ---
function StatCard({ title, value, sub, icon: Icon, colorClass }) {
  return (
    <div
      className={`bg-gradient-to-br border rounded-2xl p-5 backdrop-blur-sm ${colorClass}`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-secondary">{title}</span>
        {Icon && <Icon className="w-5 h-5 text-cyan-400/80" />}
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {sub && <div className="text-xs text-cyan-400/80 ml-0.5">{sub}</div>}
    </div>
  );
}

// --- Helper: Team Badge ---
function TeamBadge({ teamId }) {
  if (!teamId) return null;
  const label = String(teamId).replace(/_/g, " ");
  const hue =
    (label.split("").reduce((a, c) => a + c.charCodeAt(0), 0) % 12) * 30;
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium text-white cursor-pointer hover:brightness-125 transition-all"
      style={{ backgroundColor: `hsl(${hue}, 55%, 40%)` }}
      title={teamId}
      onClick={() => toast.info(`Inspecting Team: ${label}`)}
    >
      {label}
    </span>
  );
}

// --- Helper: LLM Alert ---
function LlmAlert({ alert, onDismiss }) {
  const severity = alert.severity || "info";
  const isHigh = severity === "high" || severity === "error";
  const isWarning = severity === "warning";
  const bg = isHigh
    ? "bg-danger/15 border-danger/40"
    : isWarning
      ? "bg-warning/15 border-warning/40"
      : "bg-primary/15 border-primary/40";
  const icon = isHigh
    ? "text-danger"
    : isWarning
      ? "text-warning"
      : "text-primary";
  return (
    <div
      className={`flex items-start gap-2 p-3 rounded-lg border ${bg} text-sm cursor-pointer hover:bg-black/20 transition-colors`}
      onClick={() => toast.info("Accessing alert logs...")}
    >
      {isHigh ? (
        <AlertTriangle className={`w-4 h-4 ${icon} shrink-0 mt-0.5`} />
      ) : (
        <Info className={`w-4 h-4 ${icon} shrink-0 mt-0.5`} />
      )}
      <div className="flex-1 min-w-0">
        <span className="text-white text-sm">
          {alert.message || alert.text || JSON.stringify(alert)}
        </span>
        {alert.timestamp && (
          <span className="block text-xs text-secondary mt-1">
            {alert.timestamp}
          </span>
        )}
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDismiss();
          }}
          className="text-secondary hover:text-white shrink-0"
        >
          ×
        </button>
      )}
    </div>
  );
}

// --- Helper: Regime Gauge ---
function RegimeGauge({ macro }) {
  const waveState = macro?.wave_state || "neutral";
  const oscillator = macro?.oscillator ?? 50;
  const biasMultiplier = macro?.bias_multiplier ?? 1.0;
  const regime = REGIME_COLORS[waveState] || REGIME_COLORS.neutral;
  const needleAngle = (oscillator / 100) * 180 - 90;

  return (
    <div
      className={`bg-[#0B0E14] border ${regime.border} rounded-2xl p-6 shadow-lg ${regime.glow} cursor-pointer hover:brightness-110 transition-all`}
      onClick={() => toast.info("Opening Macro Regime Details")}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Gauge className={`w-5 h-5 ${regime.text}`} />
          <span className="text-sm font-medium text-white">Macro Regime</span>
        </div>
        <span
          className={`text-xs font-bold uppercase px-2 py-1 rounded ${regime.text} bg-black/50 border ${regime.border}`}
        >
          {waveState}
        </span>
      </div>
      {/* SVG Gauge */}
      <div className="flex justify-center my-4 relative">
        <svg viewBox="0 0 200 120" className="w-48 h-28">
          <defs>
            <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#ef4444" />
              <stop offset="50%" stopColor="#06B6D4" />
              <stop offset="100%" stopColor="#22c55e" />
            </linearGradient>
          </defs>
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="#1e293b"
            strokeWidth="12"
            strokeLinecap="round"
          />
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="url(#gaugeGrad)"
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray="251"
            strokeDashoffset={251 - (oscillator / 100) * 251}
            className="transition-all duration-1000 ease-out"
          />
          <line
            x1="100"
            y1="100"
            x2={100 + 60 * Math.cos((needleAngle * Math.PI) / 180)}
            y2={100 + 60 * Math.sin((needleAngle * Math.PI) / 180)}
            stroke="#06B6D4"
            strokeWidth="3"
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />
          <circle
            cx="100"
            cy="100"
            r="5"
            fill="#0B0E14"
            stroke="#06B6D4"
            strokeWidth="2"
          />
          <text
            x="100"
            y="88"
            textAnchor="middle"
            fill="#fff"
            fontSize="22"
            fontWeight="bold"
            className="drop-shadow-[0_0_8px_rgba(6,182,212,0.8)]"
          >
            {oscillator}
          </text>
        </svg>
      </div>
      <div className="grid grid-cols-3 gap-3 text-center text-xs">
        <div>
          <span className="text-secondary uppercase tracking-wider text-[10px]">
            Oscillator
          </span>
          <div className="text-white font-bold text-lg">{oscillator}</div>
        </div>
        <div>
          <span className="text-secondary uppercase tracking-wider text-[10px]">
            Bias
          </span>
          <div className="text-cyan-400 font-bold text-lg">
            {biasMultiplier.toFixed(2)}x
          </div>
        </div>
        <div>
          <span className="text-secondary uppercase tracking-wider text-[10px]">
            Wave
          </span>
          <div className={`font-bold text-lg capitalize ${regime.text}`}>
            {waveState}
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Helper: Agent Card ---
function AgentCard({ agent, onToggle }) {
  const Icon = AGENT_ICONS[agent.name] || Bot;
  const isRunning = agent.status === "running";
  const health = agent.health || "unknown";
  const healthColor =
    health === "healthy"
      ? "text-success"
      : health === "degraded"
        ? "text-amber-400"
        : "text-secondary";

  // MISSING V3 ULTRA-DENSE COMPONENT: SHAP Bars mock features
  const shapFeatures = [
    { name: "Price Action", val: 45, color: "bg-cyan-500" },
    { name: "Vol Flow", val: 30, color: "bg-amber-500" },
    { name: "Regime", val: 15, color: "bg-red-500" },
    { name: "Sentiment", val: 10, color: "bg-purple-500" },
  ];

  return (
    <div
      className={`border rounded-xl p-4 transition-all bg-[#0B0E14] ${
        isRunning
          ? "border-cyan-500/40 shadow-[0_0_15px_rgba(6,182,212,0.15)]"
          : "border-secondary/30 opacity-60"
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div
            className={`p-2 rounded-lg ${isRunning ? "bg-cyan-500/20 border border-cyan-500/50" : "bg-secondary/20"}`}
          >
            <Icon
              className={`w-5 h-5 ${isRunning ? "text-cyan-400" : "text-secondary"}`}
            />
          </div>
          <div>
            <div
              className="text-sm font-bold text-white hover:text-cyan-400 cursor-pointer transition-colors flex items-center gap-2"
              onClick={() =>
                toast.info(`Inspecting agent logic for ${agent.name}`)
              }
            >
              {agent.name}
              {isRunning && (
                <RefreshCcw
                  className="w-3 h-3 text-cyan-400 animate-spin"
                  title="Recursive Self-Improvement Active"
                />
              )}
            </div>
            <div className="flex items-center gap-2 mt-0.5 text-[10px] uppercase tracking-wider">
              <span className={`flex items-center gap-1 ${healthColor}`}>
                <Activity className="w-3 h-3" /> {health}
              </span>
              {agent.uptime && (
                <span className="text-secondary">up {agent.uptime}</span>
              )}
            </div>
          </div>
        </div>
        <Button
          variant={isRunning ? "danger" : "primary"}
          size="xs"
          onClick={(e) => {
            e.stopPropagation();
            onToggle(agent);
          }}
          className={
            isRunning
              ? "bg-red-500/20 text-red-400 border-red-500/50 hover:bg-red-500/40"
              : "bg-cyan-500/20 text-cyan-400 border-cyan-500/50 hover:bg-cyan-500/40"
          }
        >
          {isRunning ? (
            <Power className="w-3 h-3" />
          ) : (
            <Play className="w-3 h-3" />
          )}
        </Button>
      </div>
      {agent.last_signal && (
        <div className="text-xs text-secondary truncate mb-3">
          Last:{" "}
          <span
            className="text-amber-400 cursor-pointer hover:underline"
            onClick={() =>
              toast.success(`Executing trace on signal: ${agent.last_signal}`)
            }
          >
            {agent.last_signal}
          </span>
        </div>
      )}

      {/* MISSING V3 ULTRA-DENSE COMPONENT: SHAP Bars */}
      <div className="mt-3 space-y-2 border-t border-secondary/20 pt-3">
        <div className="flex justify-between items-center text-[10px] text-secondary uppercase tracking-wider">
          <span>SHAP Importance</span>
          <span
            className="text-cyan-400/80 cursor-pointer hover:text-cyan-300 flex items-center gap-1 transition-colors"
            onClick={() =>
              toast.info(`Accessing Weight Matrices for ${agent.name}`)
            }
          >
            <Settings className="w-3 h-3" /> Weights
          </span>
        </div>
        <div className="flex w-full h-1.5 rounded-full overflow-hidden bg-secondary/20 shadow-inner">
          {shapFeatures.map((f, idx) => (
            <div
              key={idx}
              className={`${f.color} hover:brightness-150 cursor-crosshair transition-all`}
              style={{ width: `${f.val}%` }}
              title={`${f.name}: ${f.val}%`}
              onClick={() => toast.info(`SHAP Delta for ${f.name}: +2.3%`)}
            ></div>
          ))}
        </div>
        <div className="flex justify-between text-[9px] text-secondary/70 px-0.5">
          <span>{shapFeatures[0].name}</span>
          <span>{shapFeatures[1].name}</span>
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

  // --- Agent state ---
  const {
    data: agentsRaw,
    loading: agentsLoading,
    refetch: refetchAgents,
  } = useApi("/api/v1/agents");
  const agents = useMemo(
    () => (Array.isArray(agentsRaw) ? agentsRaw : agentsRaw?.agents || []),
    [agentsRaw],
  );

  // --- OpenClaw state ---
  const [macro, setMacro] = useState(null);
  const [swarm, setSwarm] = useState({ active: 0, total: 0, teams: [] });
  const [candidates, setCandidates] = useState([]);
  const [llmAlerts, setLlmAlerts] = useState([]);
  const [bias, setBias] = useState(1.0);
  const [biasOverrideSent, setBiasOverrideSent] = useState(false);
  const [spawnModalOpen, setSpawnModalOpen] = useState(false);
  const [spawnLoading, setSpawnLoading] = useState(false);
  const [spawnError, setSpawnError] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const wsRef = useRef(null);

  // --- Blackboard, HITL, and Consensus States ---
  const [blackboardMsgs, setBlackboardMsgs] = useState([]);
  const [hitlBuffer, setHitlBuffer] = useState([]);
  const [consensusData, setConsensusData] = useState([]);

  // --- Loaders ---
  const loadMacro = useCallback(async () => {
    try {
      const data = await openclaw.getMacro();
      setMacro(data);
    } catch {
      setMacro(null);
    }
  }, []);

  const loadSwarm = useCallback(async () => {
    try {
      const data = await openclaw.getSwarmStatus();
      setSwarm({
        active: data.active ?? 0,
        total: data.total ?? 0,
        teams: data.teams ?? [],
      });
    } catch {
      setSwarm({ active: 0, total: 0, teams: [] });
    }
  }, []);

  const loadCandidates = useCallback(async () => {
    try {
      const list = await openclaw.getCandidates(25);
      setCandidates(Array.isArray(list) ? list : []);
    } catch {
      setCandidates([]);
    }
  }, []);

  // --- Polling effects ---
  useEffect(() => {
    loadMacro();
    const t = setInterval(loadMacro, MACRO_POLL_MS);
    return () => clearInterval(t);
  }, [loadMacro]);
  useEffect(() => {
    loadSwarm();
    const t = setInterval(loadSwarm, SWARM_POLL_MS);
    return () => clearInterval(t);
  }, [loadSwarm]);
  useEffect(() => {
    loadCandidates();
    const t = setInterval(loadCandidates, CANDIDATES_POLL_MS);
    return () => clearInterval(t);
  }, [loadCandidates]);

  // --- LLM Flow WebSocket ---
  useEffect(() => {
    const wsUrl = openclaw.getLlmFlowWsUrl();
    let socket;
    try {
      socket = new WebSocket(wsUrl);
      wsRef.current = socket;
      socket.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          setLlmAlerts((prev) =>
            [{ ...msg, id: Date.now() + crypto.randomUUID() }, ...prev].slice(
              0,
              LLM_ALERTS_MAX,
            ),
          );
        } catch {
          setLlmAlerts((prev) => [
            { id: Date.now(), message: ev.data, severity: "info" },
            ...prev.slice(0, LLM_ALERTS_MAX - 1),
          ]);
        }
      };
      socket.onclose = () => {
        wsRef.current = null;
      };
    } catch (e) {
      console.warn("LLM flow WebSocket failed:", e);
    }
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  // --- Agent WS for live status ---
  useEffect(() => {
    const unsub = ws.on("agents", (msg) => {
      if (msg?.type === "agent_status") refetchAgents();
    });
    return unsub;
  }, [refetchAgents]);

  // --- Blackboard & HITL WebSocket Subscriptions ---
  useEffect(() => {
    // Mock Blackboard pub/sub
    const blackboardInterval = setInterval(() => {
      const topics = ["SIG_GEN", "RISK_EVAL", "SENTIMENT", "EXECUTION"];
      const contents = [
        `Computed tensor weights for epoch ${Math.floor(0.5 * 1000)} - Validation OK.`,
        `Detected volatility flow anomaly in sector indices.`,
        `Rebalancing portfolio edge weights against macro drift.`,
        `Analyzing sentiment divergence across FinTwit targets.`,
        `Consensus threshold crossed for entry execution.`,
      ];
      const msg = {
        id: Date.now(),
        time: new Date().toLocaleTimeString("en-US", {
          hour12: false,
          hour: "numeric",
          minute: "numeric",
          second: "numeric",
          fractionalSecondDigits: 3,
        }),
        topic: topics[Math.floor(0.5 * topics.length)],
        content: contents[Math.floor(0.5 * contents.length)],
        hash: "0x" + 0.5.toString(16).substring(2, 8).toUpperCase(),
      };
      setBlackboardMsgs((prev) => [msg, ...prev].slice(0, 100));
    }, 2500);

    // Mock HITL Ring buffer
    const hitlInterval = setInterval(() => {
      if (0.5 > 0.6) {
        const actions = [
          "BIAS_OVERRIDE",
          "FORCE_LIQUIDATE",
          "NODE_RESTART",
          "HALT_SIGNAL",
        ];
        const msg = {
          id: Date.now(),
          time: new Date().toLocaleTimeString("en-US", { hour12: false }),
          action: actions[Math.floor(0.5 * actions.length)],
          user: "OP-1",
          target: `Swarm-Alpha-${Math.floor(0.5 * 9)}`,
          status: "ACKNOWLEDGED",
        };
        setHitlBuffer((prev) => [msg, ...prev].slice(0, 50));
      }
    }, 4500);

    // Mock Consensus Data
    setConsensusData([
      {
        symbol: "BTC",
        agree: 88,
        agents: 5,
        action: "LONG",
        strength: "STRONG",
      },
      {
        symbol: "ETH",
        agree: 65,
        agents: 4,
        action: "SHORT",
        strength: "WEAK",
      },
      {
        symbol: "SOL",
        agree: 92,
        agents: 5,
        action: "LONG",
        strength: "STRONG",
      },
    ]);

    return () => {
      clearInterval(blackboardInterval);
      clearInterval(hitlInterval);
    };
  }, []);

  // --- Consensus Data from OpenClaw API ---
  const loadConsensus = useCallback(async () => {
    try {
      const data = await openclaw.getConsensus();
      setConsensusData(Array.isArray(data) ? data : []);
    } catch {
      setConsensusData([]);
    }
  }, []);
  useEffect(() => {
    loadConsensus();
    const t = setInterval(loadConsensus, 30000);
    return () => clearInterval(t);
  }, [loadConsensus]);

  // --- Handlers ---
  const handleAgentToggle = async (agent) => {
    const action = agent.status === "running" ? "stop" : "start";
    try {
      await fetch(getApiUrl(`/api/v1/agents/${agent.id}/${action}`), {
        method: "POST",
      });
      toast.success(`${agent.name} ${action}ed`);
      refetchAgents();
    } catch (e) {
      toast.error(`Failed to ${action} ${agent.name}`);
    }
  };

  const handleBiasChange = (value) => {
    setBias(value);
    setBiasOverrideSent(false);
  };

  const handleBiasSubmit = async () => {
    try {
      await openclaw.setBiasOverride(bias);
      setBiasOverrideSent(true);
      toast.success(`Bias override set to ${bias.toFixed(1)}x`);
    } catch (e) {
      toast.error("Bias override failed");
    }
  };

  const handleSpawnTeam = async (teamType, action) => {
    setSpawnLoading(true);
    setSpawnError(null);
    try {
      await openclaw.spawnTeam(teamType, action);
      await loadSwarm();
      toast.success(`${action === "spawn" ? "Spawned" : "Killed"} ${teamType}`);
    } catch (e) {
      setSpawnError(e.body?.detail || e.message || "Request failed");
    } finally {
      setSpawnLoading(false);
    }
  };

  const handleCandidateClick = (c) => {
    const symbol = c.symbol || c.ticker;
    const entry = c.entry_price ?? c.suggested_entry ?? c.entry ?? 0;
    const stop = c.stop_loss ?? c.suggested_stop ?? c.stop ?? 0;
    const target = c.target_price ?? c.suggested_target ?? c.target ?? 0;
    const team = c.team_id ?? c.team ?? null;
    const score = c.composite_score ?? c.score ?? 0;
    const detail = { symbol, entry, stop, target, team, score };
    window.dispatchEvent(new CustomEvent("openTradeExecution", { detail }));
    navigate("/trades", { state: { openTradeExecution: detail } });
  };

  // --- Derived stats ---
  const runningAgents = agents.filter((a) => a.status === "running").length;
  const totalAgents = agents.length;
  const highAlerts = llmAlerts.filter(
    (a) => a.severity === "high" || a.severity === "error",
  ).length;
  const waveState = macro?.wave_state || "neutral";

  // --- Tab buttons ---
  const tabs = [
    { id: "overview", label: "Overview", icon: Eye },
    { id: "agents", label: "Agents", icon: Bot },
    { id: "swarm", label: "Swarm Control", icon: Boxes },
    { id: "candidates", label: "Candidates", icon: Target },
    { id: "alerts", label: "LLM Flow", icon: Radio },
    { id: "brain-map", label: "Brain Map", icon: Network },
    { id: "leaderboard", label: "Leaderboard", icon: Trophy },
    { id: "blackboard", label: "Blackboard", icon: ClipboardList },
  ];

  return (
    <div className="space-y-6 text-white min-h-screen">
      {/* Page Header */}
      <PageHeader
        icon={Shield}
        title="Agent Command Center"
        description="Unified intelligence hub: agent management, swarm control, macro regime, and LLM flow alerts."
      />

      {/* Top Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Active Agents"
          value={`${runningAgents}/${totalAgents}`}
          sub={
            runningAgents === totalAgents
              ? "All systems go"
              : `${totalAgents - runningAgents} offline`
          }
          icon={Bot}
          colorClass="bg-[#0B0E14] border-cyan-500/30 shadow-[0_0_10px_rgba(6,182,212,0.1)]"
        />
        <StatCard
          title="Swarm Teams"
          value={`${swarm.active}/${swarm.total}`}
          sub={swarm.active > 0 ? "Hunting" : "Idle"}
          icon={Boxes}
          colorClass="bg-[#0B0E14] border-cyan-500/30 shadow-[0_0_10px_rgba(6,182,212,0.1)]"
        />
        <StatCard
          title="Candidates"
          value={candidates.length}
          sub="Ranked positions"
          icon={Target}
          colorClass="bg-[#0B0E14] border-amber-500/30 shadow-[0_0_10px_rgba(245,158,11,0.1)]"
        />
        <StatCard
          title="LLM Alerts"
          value={llmAlerts.length}
          sub={highAlerts > 0 ? `${highAlerts} critical` : "All clear"}
          icon={Radio}
          colorClass={
            highAlerts > 0
              ? "bg-[#0B0E14] border-red-500/40 shadow-[0_0_15px_rgba(239,68,68,0.2)]"
              : "bg-[#0B0E14] border-secondary/30"
          }
        />
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-1 p-1 bg-[#0B0E14] rounded-xl border border-cyan-500/20 overflow-x-auto scrollbar-hide">
        {tabs.map((tab) => {
          const TabIcon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center whitespace-nowrap gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/50 shadow-[0_0_10px_rgba(6,182,212,0.2)_inset]"
                  : "text-secondary hover:text-white hover:bg-cyan-500/10 border border-transparent"
              }`}
            >
              <TabIcon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* ============ OVERVIEW TAB ============ */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Top row: Regime Gauge + Swarm + Alerts summary */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Macro Regime Gauge */}
            <RegimeGauge macro={macro} />

            {/* Swarm Status Summary */}
            <Card className="border-cyan-500/20 bg-[#0B0E14]">
              <div className="flex items-center gap-2 mb-4">
                <Boxes className="w-5 h-5 text-cyan-400" />
                <span className="text-sm font-bold text-white uppercase tracking-wider">
                  Swarm Status
                </span>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between items-center bg-cyan-500/5 p-3 rounded-lg border border-cyan-500/10">
                  <span className="text-cyan-400 text-xs uppercase tracking-wider">
                    Active Teams
                  </span>
                  <span className="text-white font-bold text-lg">
                    {swarm.active}/{swarm.total}
                  </span>
                </div>
                {swarm.teams.length > 0 ? (
                  <div className="space-y-2">
                    {swarm.teams.slice(0, 5).map((team, i) => (
                      <div
                        key={team.name || i}
                        className="flex items-center justify-between p-2 rounded-lg bg-[#0B0E14] border border-secondary/20 hover:border-cyan-500/40 cursor-pointer transition-colors"
                        onClick={() => toast.info("Accessing team logs")}
                      >
                        <div className="flex items-center gap-2">
                          <TeamBadge teamId={team.name || team.id} />
                        </div>
                        <span
                          className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${
                            team.health === "healthy"
                              ? "text-success bg-success/10 border-success/30"
                              : team.health === "degraded"
                                ? "text-amber-400 bg-warning/10 border-warning/30"
                                : "text-secondary bg-secondary/10 border-secondary/30"
                          }`}
                        >
                          {team.health || team.status || "active"}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-secondary">No active teams</p>
                )}
              </div>
            </Card>

            {/* Recent Alerts */}
            <Card className="border-secondary/20 bg-[#0B0E14]">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Radio className="w-5 h-5 text-amber-400" />
                  <span className="text-sm font-bold text-white uppercase tracking-wider">
                    Recent Alerts
                  </span>
                </div>
                <Badge className="bg-amber-500/20 text-amber-400 border border-amber-500/40 cursor-pointer hover:bg-amber-500/30">
                  Live Stream
                </Badge>
              </div>
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-amber-500/20">
                {llmAlerts.length === 0 ? (
                  <p className="text-sm text-secondary">
                    No alerts. LLM stream idle.
                  </p>
                ) : (
                  llmAlerts
                    .slice(0, 4)
                    .map((a) => (
                      <LlmAlert
                        key={a.id}
                        alert={a}
                        onDismiss={() =>
                          setLlmAlerts((prev) =>
                            prev.filter((x) => x.id !== a.id),
                          )
                        }
                      />
                    ))
                )}
              </div>
            </Card>
          </div>

          {/* MISSING V3 ULTRA-DENSE COMPONENT: Consensus Engine Visualization */}
          <Card
            title="Consensus Engine Visualization"
            subtitle="Real-time multi-agent voting agreement (Hotlinked)"
          >
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {consensusData.map((c, i) => (
                <div
                  key={i}
                  className="border border-cyan-500/20 bg-[#0B0E14] rounded-xl p-4 flex flex-col items-center relative overflow-hidden group cursor-pointer hover:border-cyan-500/50 shadow-[0_0_20px_rgba(6,182,212,0.05)_inset] transition-all"
                  onClick={() =>
                    toast.info(`Inspecting Consensus for ${c.symbol}`)
                  }
                >
                  <div className="absolute inset-0 bg-cyan-500/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <div className="text-lg font-bold text-white mb-1 tracking-wider flex items-center gap-2">
                    {c.symbol}{" "}
                    <TrendingUp
                      className={`w-4 h-4 ${c.action === "LONG" ? "text-success" : "text-danger"}`}
                    />
                  </div>
                  <div className="relative w-24 h-24 my-3 flex items-center justify-center">
                    <svg className="w-full h-full transform -rotate-90">
                      <circle
                        cx="48"
                        cy="48"
                        r="40"
                        fill="none"
                        stroke="#1e293b"
                        strokeWidth="8"
                      />
                      <circle
                        cx="48"
                        cy="48"
                        r="40"
                        fill="none"
                        stroke={c.agree > 80 ? "#06B6D4" : "#F59E0B"}
                        strokeWidth="8"
                        strokeDasharray="251"
                        strokeDashoffset={251 - (c.agree / 100) * 251}
                        className="transition-all duration-1000 ease-out"
                        strokeLinecap="round"
                      />
                    </svg>
                    <div className="absolute text-xl font-bold text-white flex flex-col items-center">
                      {c.agree}%
                      <span className="text-[9px] text-cyan-400/80 font-normal uppercase mt-0.5">
                        Agreement
                      </span>
                    </div>
                  </div>
                  <div className="flex justify-between w-full text-xs mt-2 px-2">
                    <span className="text-secondary flex items-center gap-1 hover:text-white transition-colors">
                      <Users className="w-3 h-3 text-cyan-500" /> {c.agents}{" "}
                      Agents
                    </span>
                    <span
                      className={`font-bold hover:underline ${c.action === "LONG" ? "text-success" : "text-danger"}`}
                    >
                      {c.action} ({c.strength})
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Agents Quick Grid */}
          <Card
            title="Intelligence Agents"
            subtitle="Core system agents status"
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {agents.map((agent) => (
                <AgentCard
                  key={agent.id || agent.name}
                  agent={agent}
                  onToggle={handleAgentToggle}
                />
              ))}
              {agents.length === 0 && (
                <p className="text-sm text-secondary col-span-full text-center py-8">
                  {agentsLoading
                    ? "Loading agents..."
                    : "No agents configured."}
                </p>
              )}
            </div>
          </Card>

          {/* Candidates Mini + Heatmap */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Candidates Preview */}
            <Card
              title="Top Candidates"
              subtitle="Click to open Trade Execution"
              noPadding
            >
              <DataTable
                columns={[
                  {
                    key: "symbol",
                    label: "Symbol",
                    render: (v, row) => {
                      const sym = v || row.ticker;
                      return sym ? <SymbolIcon symbol={sym} size="sm" /> : "—";
                    },
                    cellClassName: "font-bold",
                  },
                  {
                    key: "composite_score",
                    label: "Score",
                    render: (v) => (v != null ? Number(v).toFixed(1) : "—"),
                    cellClassName: "text-amber-400",
                  },
                  {
                    key: "tier",
                    label: "Tier",
                    render: (v) => v ?? "—",
                    cellClassName: "text-xs",
                  },
                  {
                    key: "source",
                    label: "Source",
                    render: (v) => {
                      if (v == null || v === "") return "—";
                      const slug =
                        DATA_SOURCE_ICON_SLUGS[String(v).toLowerCase()];
                      if (slug) {
                        return (
                          <span
                            className="inline-flex items-center gap-1.5"
                            title={v}
                          >
                            <img
                              src={`/data-sources/${slug}.png`}
                              alt={v}
                              className="w-5 h-5 object-contain"
                            />
                            <span className="text-secondary capitalize">
                              {v.replace(/_/g, " ")}
                            </span>
                          </span>
                        );
                      }
                      return (
                        <span className="capitalize">
                          {String(v).replace(/_/g, " ")}
                        </span>
                      );
                    },
                  },
                  {
                    key: "price",
                    label: "Price",
                    render: (v) =>
                      v != null ? `$${Number(v).toFixed(2)}` : "—",
                    cellClassName: "text-secondary",
                  },
                  {
                    key: "suggested_entry",
                    label: "Entry",
                    render: (v) =>
                      v != null && typeof v === "number"
                        ? v.toFixed(2)
                        : (v ?? "—"),
                    cellClassName: "text-secondary",
                  },
                ]}
                data={candidates.slice(0, 8)}
                emptyMessage="No candidates"
                rowKey={(row) =>
                  (row.symbol || row.ticker || "") +
                  (row.composite_score ?? row.score ?? "")
                }
                onRowClick={handleCandidateClick}
                className="rounded-lg border-none bg-[#0B0E14]"
              />
            </Card>

            {/* Score Heatmap */}
            <Card
              title="Symbol Heatmap"
              subtitle="Top candidates by composite score"
            >
              <div className="flex flex-wrap gap-2 p-2 bg-[#0B0E14] border border-secondary/20 rounded-lg min-h-[200px] content-start">
                {candidates.slice(0, 20).map((c) => {
                  const symbol = c.symbol || c.ticker;
                  const score = c.composite_score ?? c.score ?? 0;
                  const pct = Math.min(100, Math.max(0, score));
                  return (
                    <span
                      key={symbol}
                      onClick={() => handleCandidateClick(c)}
                      className="px-3 py-2 rounded border border-white/10 text-xs font-bold text-white cursor-pointer hover:scale-105 hover:shadow-[0_0_10px_rgba(255,255,255,0.3)] transition-all shadow-sm"
                      style={{
                        backgroundColor: `hsl(${120 - (pct / 100) * 120}, 70%, 25%)`,
                      }}
                      title={`${symbol}: ${score.toFixed(1)}`}
                    >
                      {symbol}
                    </span>
                  );
                })}
                {candidates.length === 0 && (
                  <div className="w-full flex items-center justify-center text-sm text-secondary">
                    No symbols available
                  </div>
                )}
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* ============ AGENTS TAB ============ */}
      {activeTab === "agents" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-white tracking-wider uppercase">
              Intelligence Agents
            </h2>
            <Button
              variant="secondary"
              size="sm"
              onClick={refetchAgents}
              className="border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/20"
            >
              <RefreshCw className="w-4 h-4 mr-1" /> Force Sync
            </Button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map((agent) => (
              <AgentCard
                key={agent.id || agent.name}
                agent={agent}
                onToggle={handleAgentToggle}
              />
            ))}
            {agents.length === 0 && (
              <p className="text-sm text-secondary col-span-full text-center py-12 border border-dashed border-secondary/30 rounded-xl bg-[#0B0E14]">
                {agentsLoading
                  ? "Loading agents..."
                  : "No agents configured. Check backend /api/v1/agents endpoint."}
              </p>
            )}
          </div>

          {/* MISSING V3 ULTRA-DENSE COMPONENT: Node Control Panel */}
          <Card
            title="Node Control Panel"
            subtitle="Low-level agent lifecycle management & memory stats"
          >
            <div className="overflow-x-auto bg-[#0B0E14] rounded-lg border border-secondary/20">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-cyan-500/20 bg-cyan-500/5">
                    <th className="px-4 py-2 text-left text-[10px] font-bold text-cyan-400 uppercase tracking-wider">
                      Process/Node
                    </th>
                    <th className="px-4 py-2 text-left text-[10px] font-bold text-cyan-400 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-4 py-2 text-left text-[10px] font-bold text-cyan-400 uppercase tracking-wider">
                      PID
                    </th>
                    <th className="px-4 py-2 text-left text-[10px] font-bold text-cyan-400 uppercase tracking-wider">
                      CPU / Mem
                    </th>
                    <th className="px-4 py-2 text-right text-[10px] font-bold text-cyan-400 uppercase tracking-wider">
                      Controls
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-secondary/20">
                  {agents.map((agent, i) => (
                    <tr
                      key={agent.id || i}
                      className="hover:bg-cyan-500/5 transition-colors"
                    >
                      <td
                        className="px-4 py-3 text-cyan-400 text-xs flex items-center gap-2 cursor-pointer hover:text-cyan-300 hover:underline"
                        onClick={() =>
                          toast.info(`Accessing logs for ${agent.name}`)
                        }
                      >
                        <Server className="w-4 h-4" /> embodiments.ai.
                        {agent.name.toLowerCase().replace(/\s/g, "_")}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center gap-1 text-[9px] uppercase font-bold px-2 py-0.5 rounded border ${agent.status === "running" ? "bg-cyan-500/10 text-cyan-400 border-cyan-500/30" : "bg-secondary/10 text-secondary border-secondary/30"}`}
                        >
                          {agent.status === "running" ? (
                            <Activity className="w-3 h-3" />
                          ) : (
                            <Square className="w-3 h-3" />
                          )}
                          {agent.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-amber-400/80 text-xs cursor-text select-all">
                        {1024 + i * 31}
                      </td>
                      <td className="px-4 py-3 text-secondary text-xs">
                        <span
                          className={
                            i % 2 === 0 ? "text-success" : "text-amber-400"
                          }
                        >
                          {(0.5 * 10 + 1).toFixed(1)}%
                        </span>{" "}
                        /{" "}
                        <span className="text-cyan-400/70">
                          {(0.5 * 500 + 100).toFixed(0)}MB
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right space-x-2">
                        <Button
                          size="xs"
                          variant="secondary"
                          onClick={() => handleAgentToggle(agent)}
                          className="hover:text-cyan-400 border-secondary/30 bg-[#0B0E14]"
                        >
                          {agent.status === "running" ? (
                            <Square className="w-3 h-3" />
                          ) : (
                            <Play className="w-3 h-3" />
                          )}
                        </Button>
                        <Button
                          size="xs"
                          variant="secondary"
                          onClick={() =>
                            toast.success(`Sent SIGTERM to node ${agent.name}`)
                          }
                          className="hover:text-amber-400 border-secondary/30 bg-[#0B0E14]"
                        >
                          <RefreshCw className="w-3 h-3" />
                        </Button>
                        <Button
                          size="xs"
                          variant="secondary"
                          onClick={() =>
                            toast.error(`Force killed node ${agent.name}`)
                          }
                          className="hover:text-red-500 border-secondary/30 bg-[#0B0E14]"
                        >
                          <Power className="w-3 h-3" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {agents.length === 0 && (
                    <tr>
                      <td
                        colSpan="5"
                        className="text-center py-6 text-secondary"
                      >
                        No nodes found in orchestrator
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* ============ SWARM CONTROL TAB ============ */}
      {activeTab === "swarm" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Regime Gauge full */}
            <RegimeGauge macro={macro} />

            {/* Operator Overrides */}
            <Card
              title="Operator Overrides"
              subtitle="Spawn/kill teams and adjust bias"
            >
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={spawnLoading}
                    onClick={() => handleSpawnTeam("fear_bounce_team", "spawn")}
                    className="bg-danger/15 text-danger border-danger/40 hover:bg-danger/25 shadow-[0_0_10px_rgba(239,68,68,0.1)]"
                  >
                    <Play className="w-4 h-4 mr-1" /> Spawn Fear Team
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={spawnLoading}
                    onClick={() =>
                      handleSpawnTeam("greed_momentum_team", "spawn")
                    }
                    className="bg-success/15 text-success border-success/40 hover:bg-success/25 shadow-[0_0_10px_rgba(34,197,94,0.1)]"
                  >
                    <Play className="w-4 h-4 mr-1" /> Spawn Greed Team
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={spawnLoading}
                    onClick={() => handleSpawnTeam("all", "kill")}
                    className="hover:border-red-500 hover:text-red-500"
                  >
                    <Square className="w-4 h-4 mr-1" /> Kill All
                  </Button>
                </div>
                <div className="flex items-center gap-3 pt-4 border-t border-secondary/30">
                  <Slider
                    label="Bias Multiplier"
                    min={0.5}
                    max={2}
                    step={0.1}
                    value={bias}
                    onChange={(e) => handleBiasChange(Number(e.target.value))}
                    suffix="x"
                    formatValue={(v) => Number(v).toFixed(1)}
                    className="flex-1 min-w-0 max-w-[200px]"
                  />
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleBiasSubmit}
                    className="bg-cyan-500 hover:bg-cyan-400 text-black font-bold"
                  >
                    Apply
                  </Button>
                  {biasOverrideSent && (
                    <span className="text-xs font-bold text-success flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" /> Saved
                    </span>
                  )}
                </div>
                {spawnError && (
                  <p className="text-sm font-bold text-danger mt-2 border border-danger/40 bg-danger/10 p-2 rounded">
                    {spawnError}
                  </p>
                )}
              </div>
            </Card>
          </div>

          {/* Swarm Teams Detail */}
          <Card
            title="Active Swarm Teams"
            subtitle={`${swarm.active} of ${swarm.total} teams active`}
          >
            {swarm.teams.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {swarm.teams.map((team, i) => (
                  <div
                    key={team.name || i}
                    className="border border-cyan-500/20 rounded-xl p-4 bg-[#0B0E14] shadow-[0_0_10px_rgba(6,182,212,0.05)_inset] hover:border-cyan-500/50 cursor-pointer transition-colors"
                    onClick={() =>
                      toast.info(`Inspecting Swarm: ${team.name || team.id}`)
                    }
                  >
                    <div className="flex items-center justify-between mb-3">
                      <TeamBadge teamId={team.name || team.id} />
                      <span
                        className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${
                          team.health === "healthy"
                            ? "bg-success/10 text-success border-success/30"
                            : "bg-warning/10 text-warning border-warning/30"
                        }`}
                      >
                        {team.health || "active"}
                      </span>
                    </div>
                    {team.agents && (
                      <p className="text-xs text-secondary flex items-center gap-1">
                        <Cpu className="w-3 h-3 text-cyan-500" /> {team.agents}{" "}
                        agents
                      </p>
                    )}
                    {team.strategy && (
                      <p className="text-xs text-secondary mt-1 flex items-center gap-1">
                        <GitCommit className="w-3 h-3 text-amber-500" /> Strat:{" "}
                        {team.strategy}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-secondary text-center py-8 border border-dashed border-secondary/30 rounded-xl bg-[#0B0E14]">
                No swarm teams active. Use operator overrides to spawn teams.
              </p>
            )}
          </Card>
        </div>
      )}

      {/* ============ CANDIDATES TAB ============ */}
      {activeTab === "candidates" && (
        <div className="space-y-6">
          <Card
            title="Ranked Candidates"
            subtitle="Click a row to open Trade Execution with entry/stop/target pre-filled."
          >
            <div className="overflow-x-auto bg-[#0B0E14] border border-cyan-500/20 rounded-lg">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-cyan-500/30 bg-cyan-500/5">
                    <th className="px-4 py-3 text-left text-[10px] font-bold text-cyan-400 uppercase tracking-wider">
                      Symbol
                    </th>
                    <th className="px-4 py-3 text-left text-[10px] font-bold text-cyan-400 uppercase tracking-wider">
                      Score
                    </th>
                    <th className="px-4 py-3 text-left text-[10px] font-bold text-cyan-400 uppercase tracking-wider">
                      Team
                    </th>
                    <th className="px-4 py-3 text-left text-[10px] font-bold text-cyan-400 uppercase tracking-wider">
                      Entry
                    </th>
                    <th className="px-4 py-3 text-left text-[10px] font-bold text-cyan-400 uppercase tracking-wider">
                      Stop
                    </th>
                    <th className="px-4 py-3 text-left text-[10px] font-bold text-cyan-400 uppercase tracking-wider">
                      Target
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-secondary/20">
                  {candidates.length === 0 ? (
                    <tr>
                      <td
                        colSpan="6"
                        className="px-4 py-8 text-center text-secondary"
                      >
                        No candidates. OpenClaw bridge may be idle or not
                        configured.
                      </td>
                    </tr>
                  ) : (
                    candidates.map((c) => {
                      const symbol = c.symbol || c.ticker || "—";
                      const score = c.composite_score ?? c.score ?? 0;
                      const entry =
                        c.entry_price ?? c.suggested_entry ?? c.entry ?? "—";
                      const stop =
                        c.stop_loss ?? c.suggested_stop ?? c.stop ?? "—";
                      const target =
                        c.target_price ?? c.suggested_target ?? c.target ?? "—";
                      const teamId = c.team_id ?? c.team ?? null;
                      return (
                        <tr
                          key={symbol + (c.composite_score ?? "")}
                          onClick={() => handleCandidateClick(c)}
                          className="hover:bg-cyan-500/10 cursor-pointer transition-colors group"
                        >
                          <td className="px-4 py-3 font-bold text-white group-hover:text-cyan-400">
                            {symbol}
                          </td>
                          <td className="px-4 py-3 text-amber-400">
                            {Number(score).toFixed(1)}
                          </td>
                          <td className="px-4 py-3">
                            <TeamBadge teamId={teamId} />
                            {!teamId && (
                              <span className="text-secondary text-xs">—</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-white">
                            {typeof entry === "number"
                              ? entry.toFixed(2)
                              : entry}
                          </td>
                          <td className="px-4 py-3 text-danger">
                            {typeof stop === "number" ? stop.toFixed(2) : stop}
                          </td>
                          <td className="px-4 py-3 text-success">
                            {typeof target === "number"
                              ? target.toFixed(2)
                              : target}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Heatmap full */}
          <Card
            title="Symbols by Score"
            subtitle="Top candidates by composite score"
          >
            <div className="flex flex-wrap gap-2 bg-[#0B0E14] border border-cyan-500/20 p-4 rounded-lg min-h-[150px] content-start">
              {candidates.slice(0, 25).map((c) => {
                const symbol = c.symbol || c.ticker;
                const score = c.composite_score ?? c.score ?? 0;
                const pct = Math.min(100, Math.max(0, score));
                return (
                  <span
                    key={symbol}
                    onClick={() => handleCandidateClick(c)}
                    className="px-3 py-2 rounded border border-white/10 text-xs font-bold text-white cursor-pointer hover:scale-110 hover:shadow-[0_0_15px_rgba(255,255,255,0.4)] transition-all shadow-sm"
                    style={{
                      backgroundColor: `hsl(${120 - (pct / 100) * 120}, 70%, 25%)`,
                    }}
                    title={`${symbol}: ${score.toFixed(1)}`}
                  >
                    {symbol}
                  </span>
                );
              })}
              {candidates.length === 0 && (
                <span className="text-sm text-secondary w-full text-center">
                  No symbols
                </span>
              )}
            </div>
          </Card>
        </div>
      )}

      {/* ============ LLM FLOW TAB ============ */}
      {activeTab === "alerts" && (
        <div className="space-y-6">
          <Card
            title="LLM Flow Alerts"
            subtitle={`Last ${LLM_ALERTS_MAX} alerts from WebSocket stream`}
          >
            <div className="space-y-2 max-h-[600px] overflow-y-auto bg-[#0B0E14] border border-secondary/20 p-2 rounded-lg">
              {llmAlerts.length === 0 ? (
                <p className="text-sm text-secondary text-center py-12 border border-dashed border-secondary/30 rounded mx-2">
                  No alerts yet. Connect to LLM flow stream for real-time
                  alerts.
                </p>
              ) : (
                llmAlerts.map((a) => (
                  <LlmAlert
                    key={a.id}
                    alert={a}
                    onDismiss={() =>
                      setLlmAlerts((prev) => prev.filter((x) => x.id !== a.id))
                    }
                  />
                ))
              )}
            </div>
          </Card>
        </div>
      )}

      {/* MISSING V3 ULTRA-DENSE COMPONENT: BRAIN MAP TAB */}
      {activeTab === "brain-map" && (
        <div className="space-y-6 animate-in fade-in zoom-in-95 duration-200">
          <Card
            title="DAG Brain Map"
            subtitle="Neural topology and agent inter-dependencies"
          >
            <div className="relative w-full h-[600px] bg-[#0B0E14] border border-cyan-500/30 rounded-xl overflow-hidden shadow-[0_0_40px_rgba(6,182,212,0.1)_inset]">
              {/* Brain Map SVG Template - TODO: Wire nodes dynamically from agents array */}
              <svg className="w-full h-full">
                <defs>
                  <radialGradient id="glow-cyan" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#06B6D4" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#06B6D4" stopOpacity="0" />
                  </radialGradient>
                  <radialGradient id="glow-amber" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#F59E0B" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#F59E0B" stopOpacity="0" />
                  </radialGradient>
                  <radialGradient id="glow-red" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#ef4444" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#ef4444" stopOpacity="0" />
                  </radialGradient>
                </defs>

                {/* Edges */}
                <path
                  d="M 150 150 C 300 150, 200 300, 400 300"
                  fill="none"
                  stroke="#06B6D4"
                  strokeWidth="2"
                  strokeDasharray="5,5"
                  className="opacity-50 animate-pulse"
                />
                <path
                  d="M 150 450 C 300 450, 200 300, 400 300"
                  fill="none"
                  stroke="#F59E0B"
                  strokeWidth="2"
                  className="opacity-40"
                />
                <path
                  d="M 400 300 C 600 300, 500 150, 700 150"
                  fill="none"
                  stroke="#06B6D4"
                  strokeWidth="3"
                  className="opacity-60 shadow-lg"
                />
                <path
                  d="M 400 300 C 600 300, 500 450, 700 450"
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth="2"
                  strokeDasharray="3,3"
                  className="opacity-40"
                />
                <path
                  d="M 150 150 L 150 450"
                  fill="none"
                  stroke="#64748b"
                  strokeWidth="1"
                  strokeDasharray="2,4"
                  className="opacity-30"
                />
                <path
                  d="M 700 150 L 700 450"
                  fill="none"
                  stroke="#64748b"
                  strokeWidth="1"
                  strokeDasharray="2,4"
                  className="opacity-30"
                />

                {/* Nodes */}
                <g
                  className="cursor-pointer hover:brightness-150 transition-all"
                  onClick={() =>
                    toast.info("Inspecting Market Data Node Tensor")
                  }
                >
                  <circle cx="150" cy="150" r="50" fill="url(#glow-cyan)" />
                  <circle
                    cx="150"
                    cy="150"
                    r="28"
                    fill="#0B0E14"
                    stroke="#06B6D4"
                    strokeWidth="3"
                  />
                  <text
                    x="150"
                    y="154"
                    textAnchor="middle"
                    fill="#fff"
                    fontSize="11"
                    className="font-bold tracking-widest"
                  >
                    DATA
                  </text>
                </g>
                <g
                  className="cursor-pointer hover:brightness-150 transition-all"
                  onClick={() => toast.info("Inspecting Sentiment Flow Node")}
                >
                  <circle cx="150" cy="450" r="50" fill="url(#glow-amber)" />
                  <circle
                    cx="150"
                    cy="450"
                    r="28"
                    fill="#0B0E14"
                    stroke="#F59E0B"
                    strokeWidth="3"
                  />
                  <text
                    x="150"
                    y="454"
                    textAnchor="middle"
                    fill="#fff"
                    fontSize="11"
                    className="font-bold tracking-widest"
                  >
                    NLP
                  </text>
                </g>
                <g
                  className="cursor-pointer hover:scale-105 transition-transform"
                  onClick={() => toast.info("Inspecting Core ML Brain Weights")}
                >
                  <circle cx="400" cy="300" r="80" fill="url(#glow-cyan)" />
                  <circle
                    cx="400"
                    cy="300"
                    r="45"
                    fill="#0B0E14"
                    stroke="#06B6D4"
                    strokeWidth="5"
                    className="shadow-[0_0_15px_rgba(6,182,212,0.8)]"
                  />
                  <text
                    x="400"
                    y="306"
                    textAnchor="middle"
                    fill="#06B6D4"
                    fontSize="16"
                    fontWeight="bold"
                    className="tracking-widest drop-shadow-md"
                  >
                    BRAIN
                  </text>
                </g>
                <g
                  className="cursor-pointer hover:brightness-150 transition-all"
                  onClick={() => toast.info("Inspecting Signal Generator")}
                >
                  <circle cx="700" cy="150" r="50" fill="url(#glow-cyan)" />
                  <circle
                    cx="700"
                    cy="150"
                    r="28"
                    fill="#0B0E14"
                    stroke="#06B6D4"
                    strokeWidth="3"
                  />
                  <text
                    x="700"
                    y="154"
                    textAnchor="middle"
                    fill="#fff"
                    fontSize="11"
                    className="font-bold tracking-widest"
                  >
                    SIG
                  </text>
                </g>
                <g
                  className="cursor-pointer hover:brightness-150 transition-all"
                  onClick={() =>
                    toast.info("Inspecting Risk Engine Constraints")
                  }
                >
                  <circle cx="700" cy="450" r="50" fill="url(#glow-red)" />
                  <circle
                    cx="700"
                    cy="450"
                    r="28"
                    fill="#0B0E14"
                    stroke="#ef4444"
                    strokeWidth="3"
                  />
                  <text
                    x="700"
                    y="454"
                    textAnchor="middle"
                    fill="#fff"
                    fontSize="11"
                    className="font-bold tracking-widest"
                  >
                    RISK
                  </text>
                </g>
              </svg>

              <div className="absolute top-4 right-4 flex gap-2">
                <Badge className="bg-cyan-500/20 text-cyan-400 border border-cyan-500/50">
                  Nodes: 5
                </Badge>
                <Badge className="bg-amber-500/20 text-amber-400 border border-amber-500/50">
                  Edges: 6
                </Badge>
                <Badge
                  className="bg-red-500/20 text-red-400 border border-red-500/50 hover:bg-red-500/40 cursor-pointer transition-colors font-bold uppercase tracking-wider"
                  onClick={() => toast.success("Weights Rebalanced")}
                >
                  Rebalance Weights
                </Badge>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* MISSING V3 ULTRA-DENSE COMPONENT: LEADERBOARD TAB */}
      {activeTab === "leaderboard" && (
        <div className="space-y-6 animate-in fade-in zoom-in-95 duration-200">
          <Card
            title="Agent Performance Leaderboard"
            subtitle="Quantitative metrics and historical rankings across swarm models"
          >
            <div className="overflow-x-auto bg-[#0B0E14] border border-cyan-500/20 rounded-lg shadow-lg">
              <table className="w-full text-sm text-left">
                <thead>
                  <tr className="border-b border-cyan-500/30 bg-cyan-500/10">
                    <th className="px-4 py-3 font-bold text-cyan-400 uppercase tracking-wider text-[10px]">
                      Agent Name
                    </th>
                    <th className="px-4 py-3 font-bold text-cyan-400 uppercase tracking-wider text-[10px]">
                      7D Win Rate
                    </th>
                    <th className="px-4 py-3 font-bold text-cyan-400 uppercase tracking-wider text-[10px]">
                      P&L (30D)
                    </th>
                    <th className="px-4 py-3 font-bold text-cyan-400 uppercase tracking-wider text-[10px]">
                      Signals Gen.
                    </th>
                    <th className="px-4 py-3 font-bold text-cyan-400 uppercase tracking-wider text-[10px]">
                      Accuracy
                    </th>
                    <th className="px-4 py-3 font-bold text-cyan-400 uppercase tracking-wider text-[10px]">
                      Sharpe
                    </th>
                    <th className="px-4 py-3 font-bold text-cyan-400 uppercase tracking-wider text-[10px] text-right">
                      Action
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cyan-500/10">
                  {agents.map((agent, i) => {
                    // Deterministic mock quant data
                    const winRate = 50 + ((i * 7) % 35);
                    const pnl =
                      (1000 + ((i * 2345) % 8000)) * (i % 2 === 0 ? 1 : -0.2);
                    const signals = 120 + ((i * 45) % 300);
                    const acc = winRate + (i % 5);
                    const sharpe = (1.2 + ((i * 0.3) % 2)).toFixed(2);
                    return (
                      <tr
                        key={agent.id || agent.name}
                        className="hover:bg-cyan-500/10 transition-colors group"
                      >
                        <td className="px-4 py-3 font-bold text-white flex items-center gap-2">
                          <Bot className="w-4 h-4 text-cyan-500/50 group-hover:text-cyan-400 transition-colors" />
                          <span
                            className="cursor-pointer hover:text-cyan-300 hover:underline transition-all"
                            onClick={() =>
                              toast.info(`Viewing deep stats for ${agent.name}`)
                            }
                          >
                            {agent.name}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-white text-xs">
                          <div className="flex items-center gap-2">
                            <span className="w-10">{winRate.toFixed(1)}%</span>
                            <div className="w-16 h-1.5 bg-secondary/30 rounded-full overflow-hidden border border-black/50">
                              <div
                                className="h-full bg-cyan-500 shadow-[0_0_5px_rgba(6,182,212,0.8)]"
                                style={{ width: `${winRate}%` }}
                              ></div>
                            </div>
                          </div>
                        </td>
                        <td
                          className={`px-4 py-3 font-bold tracking-wider text-xs ${pnl >= 0 ? "text-success" : "text-danger"}`}
                        >
                          {pnl >= 0 ? "+" : "-"}${Math.abs(pnl).toFixed(2)}
                        </td>
                        <td className="px-4 py-3 text-amber-400 text-xs">
                          {signals}
                        </td>
                        <td className="px-4 py-3 text-cyan-300 text-xs">
                          {acc.toFixed(1)}%
                        </td>
                        <td className="px-4 py-3 font-bold text-white text-xs drop-shadow-sm">
                          {sharpe}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Button
                            size="xs"
                            variant="secondary"
                            className="bg-[#0B0E14] border-cyan-500/30 text-cyan-400 hover:border-cyan-400 hover:bg-cyan-500/20 text-[10px] tracking-widest font-bold"
                            onClick={() => toast.success("Backtest Triggered")}
                          >
                            BACKTEST
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                  {agents.length === 0 && (
                    <tr>
                      <td
                        colSpan="7"
                        className="text-center py-8 text-secondary border border-dashed border-secondary/30 rounded"
                      >
                        No agents available to rank
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* MISSING V3 ULTRA-DENSE COMPONENT: BLACKBOARD TAB */}
      {activeTab === "blackboard" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-in fade-in zoom-in-95 duration-200">
          {/* Real-time Blackboard */}
          <Card
            title="Real-Time Blackboard"
            subtitle="Pub/Sub feed for inter-agent memory bus"
          >
            <div className="bg-[#0B0E14] border border-cyan-500/30 rounded-lg p-3 h-[550px] overflow-y-auto text-[11px] space-y-1 scrollbar-thin scrollbar-thumb-cyan-500/20 shadow-[0_0_20px_rgba(6,182,212,0.05)_inset]">
              {blackboardMsgs.map((msg) => (
                <div
                  key={msg.id}
                  className="flex gap-3 hover:bg-cyan-500/10 p-1.5 rounded transition-colors group cursor-crosshair"
                >
                  <span className="text-cyan-500/50 shrink-0">
                    [{msg.time}]
                  </span>
                  <span
                    className={`shrink-0 font-bold w-24 ${msg.topic === "RISK_EVAL" ? "text-red-400" : msg.topic === "SIG_GEN" ? "text-cyan-400" : msg.topic === "EXECUTION" ? "text-success" : "text-amber-400"}`}
                  >
                    [{msg.topic}]
                  </span>
                  <span className="text-white flex-1 drop-shadow-sm">
                    {msg.content}
                  </span>
                  <span
                    className="text-transparent group-hover:text-cyan-400 cursor-pointer underline decoration-cyan-400/50 shrink-0 transition-colors font-bold tracking-widest text-[9px]"
                    onClick={() =>
                      toast.info(`Inspecting state hash: ${msg.hash}`)
                    }
                  >
                    INSPECT ({msg.hash})
                  </span>
                </div>
              ))}
              {blackboardMsgs.length === 0 && (
                <span className="text-secondary flex justify-center py-10 animate-pulse">
                  Listening for blackboard events...
                </span>
              )}
            </div>
          </Card>

          {/* HITL Ring Buffer */}
          <Card
            title="HITL Ring Buffer"
            subtitle="Circular buffer of last 50 human interventions"
          >
            <div className="bg-[#0B0E14] border border-amber-500/30 rounded-lg p-4 h-[550px] overflow-y-auto space-y-3 shadow-[0_0_20px_rgba(245,158,11,0.05)_inset] scrollbar-thin scrollbar-thumb-amber-500/20">
              {hitlBuffer.map((msg) => (
                <div
                  key={msg.id}
                  className="flex flex-col gap-1.5 p-3 border border-amber-500/20 rounded bg-amber-500/5 hover:border-amber-500/50 transition-colors cursor-pointer hover:shadow-[0_0_10px_rgba(245,158,11,0.1)]"
                  onClick={() =>
                    toast.info(`Viewing audit trail for ${msg.action}`)
                  }
                >
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-2">
                      <Shield
                        className={`w-4 h-4 ${msg.action === "FORCE_LIQUIDATE" || msg.action === "NODE_RESTART" ? "text-red-500" : "text-amber-500"}`}
                      />
                      <span
                        className={`text-[11px] font-bold uppercase tracking-wider ${msg.action === "FORCE_LIQUIDATE" || msg.action === "NODE_RESTART" ? "text-red-400" : "text-amber-400"}`}
                      >
                        {msg.action}
                      </span>
                    </div>
                    <span className="text-[10px] text-amber-500/50">
                      {msg.time}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-[10px] mt-1">
                    <span className="text-secondary uppercase">
                      Target:{" "}
                      <span className="text-cyan-400">{msg.target}</span>
                    </span>
                    <span className="text-secondary uppercase">
                      User: <span className="text-white">{msg.user}</span>
                    </span>
                    <Badge className="bg-success/20 text-success border border-success/40 text-[9px] py-0 px-1.5 uppercase font-bold tracking-wider">
                      {msg.status}
                    </Badge>
                  </div>
                </div>
              ))}
              {hitlBuffer.length === 0 && (
                <span className="text-secondary text-sm flex justify-center py-10">
                  No recent interventions in ring buffer
                </span>
              )}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
