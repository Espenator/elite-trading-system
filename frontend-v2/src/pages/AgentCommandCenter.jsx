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
} from "lucide-react";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";
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
  fear: { bg: "from-red-900/40 to-red-800/20", border: "border-red-500/50", text: "text-red-400", glow: "shadow-red-500/20" },
  greed: { bg: "from-green-900/40 to-green-800/20", border: "border-green-500/50", text: "text-green-400", glow: "shadow-green-500/20" },
  neutral: { bg: "from-cyan-900/40 to-cyan-800/20", border: "border-cyan-500/50", text: "text-cyan-400", glow: "shadow-cyan-500/20" },
};

// --- Helper: Stat Card ---
function StatCard({ title, value, sub, icon: Icon, colorClass }) {
  return (
    <div className={`bg-gradient-to-br border rounded-2xl p-5 backdrop-blur-sm ${colorClass}`}>
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
  const hue = (label.split("").reduce((a, c) => a + c.charCodeAt(0), 0) % 12) * 30;
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium text-white"
      style={{ backgroundColor: `hsl(${hue}, 55%, 40%)` }}
      title={teamId}
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
  const icon = isHigh ? "text-danger" : isWarning ? "text-warning" : "text-primary";
  return (
    <div className={`flex items-start gap-2 p-3 rounded-lg border ${bg} text-sm`}>
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
          <span className="block text-xs text-secondary mt-1">{alert.timestamp}</span>
        )}
      </div>
      {onDismiss && (
        <button type="button" onClick={onDismiss} className="text-secondary hover:text-white shrink-0">
          \u00d7
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
  const needleAngle = ((oscillator / 100) * 180) - 90;

  return (
    <div className={`bg-gradient-to-br ${regime.bg} border ${regime.border} rounded-2xl p-6 shadow-lg ${regime.glow}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Gauge className={`w-5 h-5 ${regime.text}`} />
          <span className="text-sm font-medium text-white">Macro Regime</span>
        </div>
        <span className={`text-xs font-bold uppercase px-2 py-1 rounded ${regime.text} bg-black/30`}>
          {waveState}
        </span>
      </div>
      {/* SVG Gauge */}
      <div className="flex justify-center my-4">
        <svg viewBox="0 0 200 120" className="w-48 h-28">
          <defs>
            <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#ef4444" />
              <stop offset="50%" stopColor="#22d3ee" />
              <stop offset="100%" stopColor="#22c55e" />
            </linearGradient>
          </defs>
          <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="#1e293b" strokeWidth="12" strokeLinecap="round" />
          <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="url(#gaugeGrad)" strokeWidth="12" strokeLinecap="round" strokeDasharray="251" strokeDashoffset={251 - (oscillator / 100) * 251} />
          <line
            x1="100" y1="100"
            x2={100 + 60 * Math.cos((needleAngle * Math.PI) / 180)}
            y2={100 + 60 * Math.sin((needleAngle * Math.PI) / 180)}
            stroke="white" strokeWidth="2" strokeLinecap="round"
          />
          <circle cx="100" cy="100" r="4" fill="white" />
          <text x="100" y="88" textAnchor="middle" fill="white" fontSize="22" fontWeight="bold">
            {oscillator}
          </text>
        </svg>
      </div>
      <div className="grid grid-cols-3 gap-3 text-center text-xs">
        <div>
          <span className="text-secondary">Oscillator</span>
          <div className="text-white font-bold text-lg">{oscillator}</div>
        </div>
        <div>
          <span className="text-secondary">Bias</span>
          <div className="text-white font-bold text-lg">{biasMultiplier.toFixed(2)}x</div>
        </div>
        <div>
          <span className="text-secondary">Wave</span>
          <div className={`font-bold text-lg capitalize ${regime.text}`}>{waveState}</div>
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
  const healthColor = health === "healthy" ? "text-success" : health === "degraded" ? "text-warning" : "text-secondary";

  return (
    <div className={`border rounded-xl p-4 transition-all ${
      isRunning ? "border-primary/40 bg-primary/5" : "border-secondary/30 bg-secondary/5 opacity-60"
    }`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${isRunning ? "bg-primary/20" : "bg-secondary/20"}`}>
            <Icon className={`w-5 h-5 ${isRunning ? "text-primary" : "text-secondary"}`} />
          </div>
          <div>
            <div className="text-sm font-medium text-white">{agent.name}</div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`text-xs ${healthColor}`}>{health}</span>
              {agent.uptime && <span className="text-xs text-secondary">up {agent.uptime}</span>}
            </div>
          </div>
        </div>
        <Button
          variant={isRunning ? "danger" : "primary"}
          size="xs"
          onClick={() => onToggle(agent)}
        >
          {isRunning ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
        </Button>
      </div>
      {agent.last_signal && (
        <div className="text-xs text-secondary truncate">Last: {agent.last_signal}</div>
      )}
    </div>
  );
}

// =============================================
// MAIN COMPONENT
// =============================================
export default function AgentCommandCenter() {
  const navigate = useNavigate();

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
  const [spawnModalOpen, setSpawnModalOpen] = useState(false);
  const [spawnLoading, setSpawnLoading] = useState(false);
  const [spawnError, setSpawnError] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const wsRef = useRef(null);

  // --- Loaders ---
  const loadMacro = useCallback(async () => {
    try {
      const data = await openclaw.getMacro();
      setMacro(data);
    } catch { setMacro(null); }
  }, []);

  const loadSwarm = useCallback(async () => {
    try {
      const data = await openclaw.getSwarmStatus();
      setSwarm({ active: data.active ?? 0, total: data.total ?? 0, teams: data.teams ?? [] });
    } catch { setSwarm({ active: 0, total: 0, teams: [] }); }
  }, []);

  const loadCandidates = useCallback(async () => {
    try {
      const list = await openclaw.getCandidates(25);
      setCandidates(Array.isArray(list) ? list : []);
    } catch { setCandidates([]); }
  }, []);

  // --- Polling effects ---
  useEffect(() => { loadMacro(); const t = setInterval(loadMacro, MACRO_POLL_MS); return () => clearInterval(t); }, [loadMacro]);
  useEffect(() => { loadSwarm(); const t = setInterval(loadSwarm, SWARM_POLL_MS); return () => clearInterval(t); }, [loadSwarm]);
  useEffect(() => { loadCandidates(); const t = setInterval(loadCandidates, CANDIDATES_POLL_MS); return () => clearInterval(t); }, [loadCandidates]);

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
            [{ ...msg, id: Date.now() + crypto.randomUUID() }, ...prev].slice(0, LLM_ALERTS_MAX)
          );
        } catch {
          setLlmAlerts((prev) => [
            { id: Date.now(), message: ev.data, severity: "info" },
            ...prev.slice(0, LLM_ALERTS_MAX - 1),
          ]);
        }
      };
      socket.onclose = () => { wsRef.current = null; };
    } catch (e) {
      console.warn("LLM flow WebSocket failed:", e);
    }
    return () => { if (wsRef.current) { wsRef.current.close(); wsRef.current = null; } };
  }, []);

  // --- Agent WS for live status ---
  useEffect(() => {
    const unsub = ws.subscribe("agents", (msg) => {
      if (msg.type === "agent_status") refetchAgents();
    });
    return unsub;
  }, [refetchAgents]);

  // --- Handlers ---
  const handleAgentToggle = async (agent) => {
    const action = agent.status === "running" ? "stop" : "start";
    try {
      await fetch(getApiUrl(`/api/v1/agents/${agent.id}/${action}`), { method: "POST" });
      toast.success(`${agent.name} ${action}ed`);
      refetchAgents();
    } catch (e) {
      toast.error(`Failed to ${action} ${agent.name}`);
    }
  };

  const handleBiasChange = (value) => { setBias(value); setBiasOverrideSent(false); };

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
  const highAlerts = llmAlerts.filter((a) => a.severity === "high" || a.severity === "error").length;
  const waveState = macro?.wave_state || "neutral";

  // --- Tab buttons ---
  const tabs = [
    { id: "overview", label: "Overview", icon: Eye },
    { id: "agents", label: "Agents", icon: Bot },
    { id: "swarm", label: "Swarm Control", icon: Boxes },
    { id: "candidates", label: "Candidates", icon: Target },
    { id: "alerts", label: "LLM Flow", icon: Radio },
  ];

  return (
    <div className="space-y-6">
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
          sub={runningAgents === totalAgents ? "All systems go" : `${totalAgents - runningAgents} offline`}
          icon={Bot}
          colorClass="from-primary/10 to-primary/5 border-primary/30"
        />
        <StatCard
          title="Swarm Teams"
          value={`${swarm.active}/${swarm.total}`}
          sub={swarm.active > 0 ? "Hunting" : "Idle"}
          icon={Boxes}
          colorClass="from-cyan-500/10 to-cyan-500/5 border-cyan-500/30"
        />
        <StatCard
          title="Candidates"
          value={candidates.length}
          sub="Ranked positions"
          icon={Target}
          colorClass="from-green-500/10 to-green-500/5 border-green-500/30"
        />
        <StatCard
          title="LLM Alerts"
          value={llmAlerts.length}
          sub={highAlerts > 0 ? `${highAlerts} critical` : "All clear"}
          icon={Radio}
          colorClass={highAlerts > 0 ? "from-red-500/10 to-red-500/5 border-red-500/30" : "from-secondary/10 to-secondary/5 border-secondary/30"}
        />
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-1 p-1 bg-secondary/10 rounded-xl border border-secondary/20">
        {tabs.map((tab) => {
          const TabIcon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? "bg-primary/20 text-primary border border-primary/30"
                  : "text-secondary hover:text-white hover:bg-secondary/20"
              }`}
            >
              <TabIcon className="w-4 h-4" />
              <span className="hidden sm:inline">{tab.label}</span>
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
            <Card className="border-cyan-500/20">
              <div className="flex items-center gap-2 mb-4">
                <Boxes className="w-5 h-5 text-cyan-400" />
                <span className="text-sm font-medium text-white">Swarm Status</span>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-secondary text-sm">Active Teams</span>
                  <span className="text-white font-bold text-lg">{swarm.active}/{swarm.total}</span>
                </div>
                {swarm.teams.length > 0 ? (
                  <div className="space-y-2">
                    {swarm.teams.slice(0, 5).map((team, i) => (
                      <div key={team.name || i} className="flex items-center justify-between p-2 rounded-lg bg-secondary/10">
                        <div className="flex items-center gap-2">
                          <TeamBadge teamId={team.name || team.id} />
                        </div>
                        <span className={`text-xs font-medium ${
                          team.health === "healthy" ? "text-success" : team.health === "degraded" ? "text-warning" : "text-secondary"
                        }`}>
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
            <Card className="border-secondary/20">
              <div className="flex items-center gap-2 mb-4">
                <Radio className="w-5 h-5 text-cyan-400" />
                <span className="text-sm font-medium text-white">Recent Alerts</span>
              </div>
              <div className="space-y-2 max-h-56 overflow-y-auto">
                {llmAlerts.length === 0 ? (
                  <p className="text-sm text-secondary">No alerts. LLM stream idle.</p>
                ) : (
                  llmAlerts.slice(0, 4).map((a) => (
                    <LlmAlert
                      key={a.id}
                      alert={a}
                      onDismiss={() => setLlmAlerts((prev) => prev.filter((x) => x.id !== a.id))}
                    />
                  ))
                )}
              </div>
            </Card>
          </div>

          {/* Agents Quick Grid */}
          <Card title="Intelligence Agents" subtitle="Core system agents status">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {agents.map((agent) => (
                <AgentCard key={agent.id || agent.name} agent={agent} onToggle={handleAgentToggle} />
              ))}
              {agents.length === 0 && (
                <p className="text-sm text-secondary col-span-full text-center py-8">
                  {agentsLoading ? "Loading agents..." : "No agents configured."}
                </p>
              )}
            </div>
          </Card>

          {/* Candidates Mini + Heatmap */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Candidates Preview */}
            <Card title="Top Candidates" subtitle="Click to open Trade Execution">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-secondary/50">
                      <th className="px-3 py-2 text-left text-xs font-medium text-secondary uppercase">Symbol</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-secondary uppercase">Score</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-secondary uppercase">Team</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-secondary uppercase">Entry</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-secondary/30">
                    {candidates.slice(0, 8).map((c) => {
                      const symbol = c.symbol || c.ticker || "\u2014";
                      const score = c.composite_score ?? c.score ?? 0;
                      const entry = c.entry_price ?? c.suggested_entry ?? c.entry ?? "\u2014";
                      const teamId = c.team_id ?? c.team ?? null;
                      return (
                        <tr key={symbol + score} onClick={() => handleCandidateClick(c)} className="hover:bg-secondary/20 cursor-pointer transition-colors">
                          <td className="px-3 py-2 font-medium text-white">{symbol}</td>
                          <td className="px-3 py-2 text-secondary">{Number(score).toFixed(1)}</td>
                          <td className="px-3 py-2"><TeamBadge teamId={teamId} /></td>
                          <td className="px-3 py-2 text-secondary">{typeof entry === "number" ? entry.toFixed(2) : entry}</td>
                        </tr>
                      );
                    })}
                    {candidates.length === 0 && (
                      <tr><td colSpan="4" className="px-3 py-6 text-center text-secondary">No candidates</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </Card>

            {/* Score Heatmap */}
            <Card title="Symbol Heatmap" subtitle="Top candidates by composite score">
              <div className="flex flex-wrap gap-2">
                {candidates.slice(0, 20).map((c) => {
                  const symbol = c.symbol || c.ticker;
                  const score = c.composite_score ?? c.score ?? 0;
                  const pct = Math.min(100, Math.max(0, score));
                  return (
                    <span
                      key={symbol}
                      onClick={() => handleCandidateClick(c)}
                      className="px-3 py-2 rounded-lg text-xs font-medium text-white cursor-pointer hover:opacity-80 transition-opacity"
                      style={{ backgroundColor: `hsl(${120 - (pct / 100) * 120}, 60%, 35%)` }}
                      title={`${symbol}: ${score.toFixed(1)}`}
                    >
                      {symbol}
                    </span>
                  );
                })}
                {candidates.length === 0 && (
                  <span className="text-sm text-secondary">No symbols available</span>
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
            <h2 className="text-lg font-semibold text-white">Intelligence Agents</h2>
            <Button variant="secondary" size="sm" onClick={refetchAgents}>
              <RefreshCw className="w-4 h-4 mr-1" /> Refresh
            </Button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map((agent) => (
              <AgentCard key={agent.id || agent.name} agent={agent} onToggle={handleAgentToggle} />
            ))}
            {agents.length === 0 && (
              <p className="text-sm text-secondary col-span-full text-center py-12">
                {agentsLoading ? "Loading agents..." : "No agents configured. Check backend /api/v1/agents endpoint."}
              </p>
            )}
          </div>
        </div>
      )}

      {/* ============ SWARM CONTROL TAB ============ */}
      {activeTab === "swarm" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Regime Gauge full */}
            <RegimeGauge macro={macro} />

            {/* Operator Overrides */}
            <Card title="Operator Overrides" subtitle="Spawn/kill teams and adjust bias">
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={spawnLoading}
                    onClick={() => handleSpawnTeam("fear_bounce_team", "spawn")}
                    className="bg-danger/15 text-danger border-danger/40 hover:bg-danger/25"
                  >
                    <Play className="w-4 h-4 mr-1" /> Spawn Fear Team
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={spawnLoading}
                    onClick={() => handleSpawnTeam("greed_momentum_team", "spawn")}
                    className="bg-success/15 text-success border-success/40 hover:bg-success/25"
                  >
                    <Play className="w-4 h-4 mr-1" /> Spawn Greed Team
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={spawnLoading}
                    onClick={() => handleSpawnTeam("all", "kill")}
                  >
                    <Square className="w-4 h-4 mr-1" /> Kill All
                  </Button>
                </div>
                <div className="flex items-center gap-3 pt-3 border-t border-secondary/30">
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
                  <Button variant="primary" size="sm" onClick={handleBiasSubmit}>Apply</Button>
                  {biasOverrideSent && <span className="text-xs text-success">Saved</span>}
                </div>
                {spawnError && <p className="text-sm text-danger mt-2">{spawnError}</p>}
              </div>
            </Card>
          </div>

          {/* Swarm Teams Detail */}
          <Card title="Active Swarm Teams" subtitle={`${swarm.active} of ${swarm.total} teams active`}>
            {swarm.teams.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {swarm.teams.map((team, i) => (
                  <div key={team.name || i} className="border border-secondary/30 rounded-xl p-4 bg-secondary/5">
                    <div className="flex items-center justify-between mb-2">
                      <TeamBadge teamId={team.name || team.id} />
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        team.health === "healthy" ? "bg-success/20 text-success" : "bg-warning/20 text-warning"
                      }`}>
                        {team.health || "active"}
                      </span>
                    </div>
                    {team.agents && <p className="text-xs text-secondary">{team.agents} agents</p>}
                    {team.strategy && <p className="text-xs text-secondary mt-1">Strategy: {team.strategy}</p>}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-secondary text-center py-8">No swarm teams active. Use operator overrides to spawn teams.</p>
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
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-secondary/50">
                    <th className="px-4 py-3 text-left text-xs font-medium text-secondary uppercase">Symbol</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-secondary uppercase">Score</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-secondary uppercase">Team</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-secondary uppercase">Entry</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-secondary uppercase">Stop</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-secondary uppercase">Target</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-secondary/30">
                  {candidates.length === 0 ? (
                    <tr>
                      <td colSpan="6" className="px-4 py-8 text-center text-secondary">
                        No candidates. OpenClaw bridge may be idle or not configured.
                      </td>
                    </tr>
                  ) : (
                    candidates.map((c) => {
                      const symbol = c.symbol || c.ticker || "\u2014";
                      const score = c.composite_score ?? c.score ?? 0;
                      const entry = c.entry_price ?? c.suggested_entry ?? c.entry ?? "\u2014";
                      const stop = c.stop_loss ?? c.suggested_stop ?? c.stop ?? "\u2014";
                      const target = c.target_price ?? c.suggested_target ?? c.target ?? "\u2014";
                      const teamId = c.team_id ?? c.team ?? null;
                      return (
                        <tr
                          key={symbol + (c.composite_score ?? "")}
                          onClick={() => handleCandidateClick(c)}
                          className="hover:bg-secondary/20 cursor-pointer transition-colors"
                        >
                          <td className="px-4 py-3 font-medium text-white">{symbol}</td>
                          <td className="px-4 py-3 text-secondary">{Number(score).toFixed(1)}</td>
                          <td className="px-4 py-3">
                            <TeamBadge teamId={teamId} />
                            {!teamId && <span className="text-secondary text-xs">\u2014</span>}
                          </td>
                          <td className="px-4 py-3 text-secondary">{typeof entry === "number" ? entry.toFixed(2) : entry}</td>
                          <td className="px-4 py-3 text-secondary">{typeof stop === "number" ? stop.toFixed(2) : stop}</td>
                          <td className="px-4 py-3 text-secondary">{typeof target === "number" ? target.toFixed(2) : target}</td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Heatmap full */}
          <Card title="Symbols by Score" subtitle="Top candidates by composite score">
            <div className="flex flex-wrap gap-2">
              {candidates.slice(0, 25).map((c) => {
                const symbol = c.symbol || c.ticker;
                const score = c.composite_score ?? c.score ?? 0;
                const pct = Math.min(100, Math.max(0, score));
                return (
                  <span
                    key={symbol}
                    onClick={() => handleCandidateClick(c)}
                    className="px-3 py-2 rounded-lg text-xs font-medium text-white cursor-pointer hover:opacity-80 transition-opacity"
                    style={{ backgroundColor: `hsl(${120 - (pct / 100) * 120}, 60%, 35%)` }}
                    title={`${symbol}: ${score.toFixed(1)}`}
                  >
                    {symbol}
                  </span>
                );
              })}
              {candidates.length === 0 && <span className="text-sm text-secondary">No symbols</span>}
            </div>
          </Card>
        </div>
      )}

      {/* ============ LLM FLOW TAB ============ */}
      {activeTab === "alerts" && (
        <div className="space-y-6">
          <Card title="LLM Flow Alerts" subtitle={`Last ${LLM_ALERTS_MAX} alerts from WebSocket stream`}>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {llmAlerts.length === 0 ? (
                <p className="text-sm text-secondary text-center py-8">
                  No alerts yet. Connect to LLM flow stream for real-time alerts.
                </p>
              ) : (
                llmAlerts.map((a) => (
                  <LlmAlert
                    key={a.id}
                    alert={a}
                    onDismiss={() => setLlmAlerts((prev) => prev.filter((x) => x.id !== a.id))}
                  />
                ))
              )}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
