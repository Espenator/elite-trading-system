// AGENT COMMAND CENTER - Embodier.ai Glass House Intelligence System
// Pattern: Dashboard.jsx — stats row + grid of cards. Real-time from GET /api/v1/agents.
// Start/Stop/Pause POST to /api/v1/agents/:id/start|stop|pause. WebSocket 'agents' for live updates.
import { useState, useMemo, useEffect, useRef } from "react";
import { toast } from "react-toastify";
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
} from "lucide-react";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";
import Slider from "../components/ui/Slider";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";
import ws from "../services/websocket";

const AGENT_ICONS = {
  "Market Data Agent": Activity,
  "Signal Generation Agent": Zap,
  "ML Learning Agent": Brain,
  "Sentiment Agent": MessageCircle,
  "YouTube Knowledge Agent": Youtube,
};

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
      {sub && <div className="text-xs text-cyan-400/80 mt-0.5">{sub}</div>}
    </div>
  );
}

const TICK_INTERVAL_MS = 60 * 1000;

export default function AgentCommandCenter() {
  const [actionLoading, setActionLoading] = useState(null);
  const [nextTickSecondsLeft, setNextTickSecondsLeft] = useState(null);
  const [configOpen, setConfigOpen] = useState({});
  const nextTickAtRef = useRef(null);
  const toggleConfig = (id) => setConfigOpen((prev) => ({ ...prev, [id]: !prev[id] }));
  const { data, loading, error, refetch } = useApi("agents", {
    pollIntervalMs: 15000,
  });

  const marketDataAgent = useMemo(
    () => (data?.agents || []).find((a) => a.id === 1),
    [data?.agents],
  );
  const isMarketDataRunning = marketDataAgent?.status === "running";

  useEffect(() => {
    const unsub = ws.on("agents", (payload) => {
      if (payload?.type === "tick_completed" && payload?.last_tick_at != null) {
        if (payload.agent_id === 1) {
          nextTickAtRef.current =
            new Date(payload.last_tick_at).getTime() + TICK_INTERVAL_MS;
        }
      }
      refetch();
    });
    return unsub;
  }, [refetch]);

  // Sync next-tick time from API (agent 1 last_tick_at). Only use server last_tick_at so reload shows correct countdown.
  useEffect(() => {
    if (!isMarketDataRunning) {
      nextTickAtRef.current = null;
      setNextTickSecondsLeft(null);
      return;
    }
    const lastTickAt = marketDataAgent?.last_tick_at;
    if (!lastTickAt) {
      nextTickAtRef.current = null;
      setNextTickSecondsLeft(null);
      return;
    }
    const nextAt = new Date(lastTickAt).getTime() + TICK_INTERVAL_MS;
    if (Number.isNaN(nextAt)) return;
    nextTickAtRef.current = nextAt;
    const initial = Math.max(0, Math.ceil((nextAt - Date.now()) / 1000));
    setNextTickSecondsLeft(initial);
  }, [isMarketDataRunning, marketDataAgent?.last_tick_at]);

  // Update "next in Xs" every second when we have a known next-tick time
  useEffect(() => {
    if (!isMarketDataRunning || nextTickAtRef.current == null) return;
    const id = setInterval(() => {
      const at = nextTickAtRef.current;
      if (at == null) return;
      const sec = Math.max(0, Math.ceil((at - Date.now()) / 1000));
      setNextTickSecondsLeft(sec);
    }, 1000);
    return () => clearInterval(id);
  }, [isMarketDataRunning]);

  const sendAction = async (agentId, action) => {
    setActionLoading(agentId);
    try {
      const res = await fetch(`${getApiUrl("agents")}/${agentId}/${action}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) {
        toast.error(json.detail || `Failed to ${action} agent`);
        return;
      }
      toast.success(`Agent ${action} requested`);
      await refetch();
    } catch (err) {
      toast.error(err.message || `Failed to ${action} agent`);
    } finally {
      setActionLoading(null);
    }
  };

  const agents = useMemo(() => {
    const list = Array.isArray(data?.agents) ? data.agents : [];
    return list.map((a) => ({ ...a, icon: AGENT_ICONS[a.name] || Activity }));
  }, [data?.agents]);

  const logs = useMemo(
    () => (Array.isArray(data?.logs) ? data.logs : []),
    [data?.logs],
  );

  const getStatusVariant = (status) => {
    switch (status) {
      case "running":
      case "active":
        return "success";
      case "learning":
        return "warning";
      case "paused":
        return "warning";
      case "stopped":
        return "secondary";
      case "error":
        return "danger";
      default:
        return "secondary";
    }
  };

  const agentStats = useMemo(() => {
    const running = agents.filter(
      (a) => a.status === "running" || a.status === "active",
    ).length;
    const paused = agents.filter((a) => a.status === "paused").length;
    const stopped = agents.filter((a) => a.status === "stopped").length;
    const err = agents.filter((a) => a.status === "error").length;
    return { running, paused, stopped, error: err, total: agents.length };
  }, [agents]);

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Bot}
        title="Agent Command Center"
        description="Monitor and control your AI agents. Real-time status via WebSocket."
      >
        {error && (
          <span className="text-xs font-medium text-danger">
            Failed to load
          </span>
        )}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-1.5">
            <Radio className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
            <span className="text-xs font-medium text-cyan-400">Live</span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={refetch}
            disabled={loading}
            leftIcon={RefreshCw}
            className="border-cyan-500/40 text-cyan-400 hover:bg-cyan-500/10"
          >
            {loading ? "Refreshing…" : "Refresh"}
          </Button>
        </div>
      </PageHeader>

      {/* Stats row — Dashboard pattern */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Running"
          value={agentStats.running}
          sub="active agents"
          icon={Play}
          colorClass="from-cyan-500/15 to-cyan-500/5 border-cyan-500/30"
        />
        <StatCard
          title="Paused"
          value={agentStats.paused}
          sub="agents"
          icon={Pause}
          colorClass="from-amber-500/15 to-amber-500/5 border-amber-500/30"
        />
        <StatCard
          title="Stopped"
          value={agentStats.stopped}
          sub="agents"
          icon={Square}
          colorClass="from-secondary/20 to-secondary/5 border-secondary/30"
        />
        <StatCard
          title="Total"
          value={agentStats.total}
          sub="agents"
          icon={Bot}
          colorClass="from-cyan-500/15 to-cyan-500/5 border-cyan-500/30"
        />
      </div>

      {/* 5 agent cards — glassmorphism, cyan accents */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {agents.length === 0 && !loading && (
          <div className="col-span-full rounded-2xl border border-secondary/50 bg-secondary/10 backdrop-blur-sm p-12 text-center">
            <p className="text-secondary">
              No agents. Start the backend or check GET /api/v1/agents.
            </p>
          </div>
        )}
        {agents.map((agent) => {
          const Icon = agent.icon;
          const lastActions = Array.isArray(agent.last_actions)
            ? agent.last_actions
            : [];
          return (
            <div
              key={agent.id}
              className="rounded-2xl border border-cyan-500/20 bg-secondary/10 backdrop-blur-sm overflow-hidden hover:border-cyan-500/40 transition-colors flex flex-col"
            >
              {/* Card header */}
              <div className="p-5 border-b border-cyan-500/10">
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-12 h-12 rounded-xl bg-cyan-500/20 flex items-center justify-center shrink-0 border border-cyan-500/30">
                      <Icon className="w-6 h-6 text-cyan-400" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-base font-semibold text-white truncate">
                        {agent.name}
                      </div>
                      <div className="text-xs text-secondary line-clamp-2 mt-0.5">
                        {agent.description}
                      </div>
                    </div>
                  </div>
                  <Badge
                    variant={getStatusVariant(agent.status)}
                    className="shrink-0 capitalize"
                  >
                    {agent.status}
                  </Badge>
                </div>
                <div className="flex items-center gap-4 text-xs text-secondary flex-wrap">
                  <span className="flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-cyan-400/70" />
                    {agent.cpuPercent != null ? `${agent.cpuPercent}%` : "—"}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <HardDrive className="w-3.5 h-3.5 text-cyan-400/70" />
                    {agent.memoryMb != null ? `${agent.memoryMb} MB` : "—"}
                  </span>
                  <span>{agent.uptime || "—"}</span>
                </div>
                {agent.status === "paused" || agent.status === "stopped" ? (
                  <div className="mt-2 text-xs text-amber-400/90 px-2.5 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
                    {agent.status === "paused"
                      ? "Paused — no new data collection"
                      : "Stopped — start to resume"}
                  </div>
                ) : agent.id === 1 && agent.status === "running" ? (
                  <div className="mt-2 text-xs text-cyan-400/90 px-2.5 py-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
                    {agent.currentTask || "Scanning Finviz Elite + Alpaca bars"}
                    {nextTickSecondsLeft != null
                      ? ` (next in ${nextTickSecondsLeft}s)`
                      : " (next in ~60s)"}
                  </div>
                ) : (
                  (agent.currentTask || agent.status === "running") && (
                    <div className="mt-2 text-xs text-cyan-400/90 px-2.5 py-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
                      {agent.currentTask || "Running…"}
                    </div>
                  )
                )}
              </div>

              {/* Config — sliders/toggles (read-only from API) */}
              {agent.config && typeof agent.config === "object" && (
                <div className="border-b border-cyan-500/10">
                  <button
                    type="button"
                    onClick={() => toggleConfig(agent.id)}
                    className="w-full px-4 py-2 flex items-center justify-between text-xs font-medium text-cyan-400 hover:bg-cyan-500/5 transition-colors"
                  >
                    Config
                    {configOpen[agent.id] ? (
                      <ChevronDown className="w-4 h-4 text-secondary" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-secondary" />
                    )}
                  </button>
                  {configOpen[agent.id] && (
                    <div className="p-4 space-y-3 bg-secondary/5">
                      {agent.id === 1 && (
                        <>
                          <Slider
                            label="Run interval (s)"
                            min={30}
                            max={120}
                            value={agent.config.runIntervalSec ?? 60}
                            readOnly
                            suffix=" s"
                          />
                          <label className="flex items-center gap-2 text-xs text-secondary">
                            <input type="checkbox" checked={agent.config.marketHoursOnly !== false} readOnly className="rounded accent-cyan-500" />
                            Market hours only
                          </label>
                        </>
                      )}
                      {agent.id === 2 && (
                        <>
                          <Slider
                            label="Min composite score"
                            min={0}
                            max={100}
                            value={agent.config.minCompositeScore ?? 70}
                            readOnly
                          />
                          <label className="flex items-center gap-2 text-xs text-secondary">
                            <input type="checkbox" checked={agent.config.autoAlert !== false} readOnly className="rounded accent-cyan-500" />
                            Auto alert
                          </label>
                        </>
                      )}
                      {agent.id === 3 && (
                        <>
                          <Slider
                            label="Min accuracy"
                            min={0}
                            max={100}
                            step={5}
                            value={(agent.config.minAccuracy ?? 0.65) * 100}
                            readOnly
                            formatValue={(v) => v.toFixed(0)}
                            suffix="%"
                          />
                          <label className="flex items-center gap-2 text-xs text-secondary">
                            <input type="checkbox" checked={agent.config.gpuEnabled !== false} readOnly className="rounded accent-cyan-500" />
                            GPU enabled
                          </label>
                        </>
                      )}
                      {agent.id === 4 && (
                        <Slider
                          label="Spike threshold"
                          min={0.5}
                          max={3}
                          step={0.1}
                          value={agent.config.spikeThreshold ?? 1.5}
                          readOnly
                        />
                      )}
                      {agent.id === 5 && (
                        <>
                          <label className="flex items-center gap-2 text-xs text-secondary">
                            <input type="checkbox" checked={agent.config.autoProcess !== false} readOnly className="rounded accent-cyan-500" />
                            Auto process
                          </label>
                          <label className="flex items-center gap-2 text-xs text-secondary">
                            <input type="checkbox" checked={agent.config.extractAlgos !== false} readOnly className="rounded accent-cyan-500" />
                            Extract algos
                          </label>
                        </>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Live activity feed — scrollable */}
              <div className="flex-1 min-h-0 flex flex-col border-b border-cyan-500/10">
                <div className="px-4 py-2 border-b border-secondary/30 flex items-center justify-between">
                  <span className="text-xs font-medium text-cyan-400">
                    Live activity
                  </span>
                  <span className="text-xs text-secondary">
                    {lastActions.length} entries (last 100)
                  </span>
                </div>
                <div className="flex-1 min-h-[140px] max-h-52 overflow-y-auto overflow-x-hidden divide-y divide-secondary/20 custom-scrollbar">
                  {lastActions.length === 0 && (
                    <div className="px-4 py-6 text-center text-xs text-secondary">
                      No activity yet
                    </div>
                  )}
                  {lastActions.map((entry, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-2 px-4 py-2 hover:bg-cyan-500/5 transition-colors"
                    >
                      <span className="text-xs text-cyan-400/80 shrink-0">
                        {entry.time}
                      </span>
                      <span className="shrink-0 mt-0.5">
                        {entry.level === "success" ? (
                          <CheckCircle className="w-3.5 h-3.5 text-success" />
                        ) : entry.level === "warning" ? (
                          <AlertCircle className="w-3.5 h-3.5 text-warning" />
                        ) : (
                          <Activity className="w-3.5 h-3.5 text-cyan-400/70" />
                        )}
                      </span>
                      <span className="text-xs text-secondary flex-1 min-w-0 line-clamp-2">
                        {entry.message}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Actions */}
              <div className="p-4 flex flex-wrap gap-2 bg-secondary/5">
                <Button
                  variant="success"
                  size="sm"
                  leftIcon={Play}
                  onClick={() => sendAction(agent.id, "start")}
                  disabled={actionLoading != null}
                >
                  {actionLoading === agent.id ? "…" : "Start"}
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  leftIcon={Square}
                  onClick={() => sendAction(agent.id, "stop")}
                  disabled={actionLoading != null}
                >
                  Stop
                </Button>
                <Button
                  variant="warning"
                  size="sm"
                  leftIcon={Pause}
                  onClick={() => sendAction(agent.id, "pause")}
                  disabled={actionLoading != null}
                >
                  Pause
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  leftIcon={RefreshCw}
                  onClick={() => sendAction(agent.id, "restart")}
                  disabled={actionLoading != null}
                >
                  Restart
                </Button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Global activity log — scrollable */}
      <Card
        title="Activity log (all agents)"
        className="border-cyan-500/20 bg-secondary/10 backdrop-blur-sm"
        bodyClassName="!p-0"
      >
        <div className="divide-y divide-secondary/20 max-h-72 overflow-y-auto custom-scrollbar">
          {logs.length === 0 && !loading && (
            <div className="px-4 py-8 text-center text-secondary text-sm">
              No activity yet.
            </div>
          )}
          {logs.map((log, i) => (
            <div
              key={i}
              className="flex items-start gap-3 px-4 py-3 hover:bg-cyan-500/5 transition-colors"
            >
              <span className="text-xs text-cyan-400/80 shrink-0">
                {log.time}
              </span>
              <span className="shrink-0 mt-0.5">
                {log.level === "success" ? (
                  <CheckCircle className="w-3.5 h-3.5 text-success" />
                ) : log.level === "warning" ? (
                  <AlertCircle className="w-3.5 h-3.5 text-warning" />
                ) : (
                  <Activity className="w-3.5 h-3.5 text-cyan-400/70" />
                )}
              </span>
              <div className="flex-1 min-w-0">
                <span className="text-xs font-medium text-cyan-400">
                  [{log.agent}]
                </span>
                <span className="text-xs text-secondary ml-2">
                  {log.message}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
