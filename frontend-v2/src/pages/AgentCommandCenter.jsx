// AGENT COMMAND CENTER - Embodier.ai Glass House Intelligence System
// GET /api/v1/agents - agent status and activity log; POST .../start, stop, pause, restart
import { useState, useMemo, useEffect } from "react";
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
} from "lucide-react";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Toggle from "../components/ui/Toggle";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";
import ws from "../services/websocket";

// The 5 AI agents (README): Market Data, Signal Generation, ML Learning, Sentiment, YouTube Knowledge
const AGENT_ICONS = {
  "Market Data Agent": Activity,
  "Signal Generation Agent": Zap,
  "ML Learning Agent": Brain,
  "Sentiment Agent": MessageCircle,
  "YouTube Knowledge Agent": Youtube,
};

export default function AgentCommandCenter() {
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [actionLoading, setActionLoading] = useState(null); // agent id being acted on
  const { data, loading, error, refetch } = useApi("agents", {
    pollIntervalMs: 30000,
  });

  useEffect(() => {
    const unsub = ws.on("agents", () => refetch());
    return unsub;
  }, [refetch]);

  const sendAction = async (agentId, action) => {
    setActionLoading(agentId);
    try {
      const res = await fetch(`${getApiUrl("agents")}/${agentId}/${action}`, {
        method: "POST",
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
        return "secondary";
      case "stopped":
        return "secondary";
      case "error":
        return "danger";
      default:
        return "secondary";
    }
  };

  const getLevelColor = (level) => {
    switch (level) {
      case "success":
        return "text-success";
      case "warning":
        return "text-warning";
      case "error":
        return "text-danger";
      default:
        return "text-primary";
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
        description="Monitor and control your AI agents"
      >
        {agents.length > 0 && (
          <div className="flex items-center gap-2 text-xs">
            {agentStats.running > 0 && (
              <span className="flex items-center gap-1.5 text-success">
                <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
                {agentStats.running} running
              </span>
            )}
            {agentStats.paused > 0 && (
              <span className="flex items-center gap-1.5 text-warning">
                <span className="w-2 h-2 rounded-full bg-warning" />
                {agentStats.paused} paused
              </span>
            )}
            {agentStats.stopped > 0 && (
              <span className="flex items-center gap-1.5 text-secondary">
                <span className="w-2 h-2 rounded-full bg-secondary" />
                {agentStats.stopped} stopped
              </span>
            )}
            {agentStats.error > 0 && (
              <span className="flex items-center gap-1.5 text-danger">
                <span className="w-2 h-2 rounded-full bg-danger" />
                {agentStats.error} error
              </span>
            )}
          </div>
        )}
        {error && (
          <span className="text-xs text-danger font-medium">
            Failed to load
          </span>
        )}
        <Button
          variant="outline"
          size="sm"
          onClick={refetch}
          disabled={loading}
          leftIcon={RefreshCw}
        >
          {loading ? "Refreshing…" : "Refresh"}
        </Button>
      </PageHeader>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {agents.length === 0 && !loading && (
          <Card className="col-span-full py-12 text-center">
            <p className="text-secondary">
              No agents. Start the backend or check GET /api/v1/agents.
            </p>
          </Card>
        )}
        {agents.map((agent) => {
          const Icon = agent.icon;
          return (
            <Card
              key={agent.id}
              noPadding
              className={`p-5 transition-all cursor-pointer ${selectedAgent === agent.id ? "border-primary/50 ring-1 ring-primary/20" : "hover:border-primary/30"}`}
              onClick={() =>
                setSelectedAgent(selectedAgent === agent.id ? null : agent.id)
              }
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                    <Icon className="w-5 h-5 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-lg font-semibold text-white truncate">
                      {agent.name}
                    </div>
                    <div className="text-xs text-secondary line-clamp-2">
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
              {/* CPU / Memory */}
              <div className="flex items-center gap-4 mb-3 text-xs">
                <span className="flex items-center gap-1.5 text-secondary">
                  <Cpu className="w-3.5 h-3.5" />
                  CPU {agent.cpuPercent != null ? `${agent.cpuPercent}%` : "—"}
                </span>
                <span className="flex items-center gap-1.5 text-secondary">
                  <HardDrive className="w-3.5 h-3.5" />
                  {agent.memoryMb != null ? `${agent.memoryMb} MB` : "—"}
                </span>
                <span className="text-secondary">
                  Uptime {agent.uptime || "—"}
                </span>
              </div>
              {/* Current task */}
              {agent.currentTask && (
                <div className="text-xs text-primary/90 mb-2 px-2 py-1.5 rounded-lg bg-primary/10">
                  Task: {agent.currentTask}
                </div>
              )}
              {/* Last action timestamp + action */}
              <div className="text-xs text-secondary mb-3">
                <span className="text-white">Last: </span>
                {agent.lastAction}
              </div>
              {/* Config toggles/sliders (key vars only) */}
              {agent.config && Object.keys(agent.config).length > 0 && (
                <div className="mb-3 pt-2 border-t border-secondary/30 space-y-2">
                  {typeof agent.config.marketHoursOnly === "boolean" && (
                    <Toggle
                      label="Market hours only"
                      checked={agent.config.marketHoursOnly}
                      onChange={() => {}}
                      className="py-1"
                    />
                  )}
                  {typeof agent.config.autoAlert === "boolean" && (
                    <Toggle
                      label="Auto alert"
                      checked={agent.config.autoAlert}
                      onChange={() => {}}
                      className="py-1"
                    />
                  )}
                  {typeof agent.config.autoProcess === "boolean" && (
                    <Toggle
                      label="Auto process"
                      checked={agent.config.autoProcess}
                      onChange={() => {}}
                      className="py-1"
                    />
                  )}
                  {typeof agent.config.gpuEnabled === "boolean" && (
                    <Toggle
                      label="GPU enabled"
                      checked={agent.config.gpuEnabled}
                      onChange={() => {}}
                      className="py-1"
                    />
                  )}
                </div>
              )}
              <div className="flex items-center gap-2 pt-3 border-t border-secondary/30">
                <Button
                  variant="success"
                  size="sm"
                  leftIcon={Play}
                  onClick={(e) => {
                    e.stopPropagation();
                    sendAction(agent.id, "start");
                  }}
                  disabled={actionLoading != null}
                >
                  {actionLoading === agent.id ? "…" : "Start"}
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  leftIcon={Square}
                  onClick={(e) => {
                    e.stopPropagation();
                    sendAction(agent.id, "stop");
                  }}
                  disabled={actionLoading != null}
                >
                  Stop
                </Button>
                <Button
                  variant="warning"
                  size="sm"
                  leftIcon={Pause}
                  onClick={(e) => {
                    e.stopPropagation();
                    sendAction(agent.id, "pause");
                  }}
                  disabled={actionLoading != null}
                >
                  Pause
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  leftIcon={RefreshCw}
                  onClick={(e) => {
                    e.stopPropagation();
                    sendAction(agent.id, "restart");
                  }}
                  disabled={actionLoading != null}
                >
                  Restart
                </Button>
              </div>
            </Card>
          );
        })}
      </div>

      <Card title="Activity Log (last 100)" bodyClassName="p-0">
        <div className="flex justify-end px-4 -mt-2 mb-2">
          <span className="text-xs text-secondary">Real-time</span>
        </div>
        <div className="divide-y divide-secondary/30 max-h-80 overflow-y-auto overflow-x-hidden">
          {logs.length === 0 && !loading && (
            <div className="px-4 py-8 text-center text-secondary text-sm">
              No activity log yet.
            </div>
          )}
          {logs.map((log, i) => (
            <div
              key={i}
              className="flex items-start gap-3 px-4 py-3 hover:bg-secondary/5 transition-colors"
            >
              <span className="text-xs text-secondary shrink-0 mt-0.5">
                {log.time}
              </span>
              <span className={`shrink-0 mt-0.5 ${getLevelColor(log.level)}`}>
                {log.level === "success" ? (
                  <CheckCircle className="w-3.5 h-3.5 inline" />
                ) : log.level === "warning" ? (
                  <AlertCircle className="w-3.5 h-3.5 inline" />
                ) : (
                  <Activity className="w-3.5 h-3.5 inline" />
                )}
              </span>
              <div className="flex-1 min-w-0">
                <span className="text-xs font-medium text-primary">
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
