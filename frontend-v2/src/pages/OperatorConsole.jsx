// OPERATOR CONSOLE - Embodier.ai Glass House Intelligence System
// PURPOSE: Master command view - see everything the AI sees, all agent activity, profit impact
// BACKEND: GET /api/v1/logs (activity feed), GET /api/v1/agents (agent grid)

import { useState, useMemo } from "react";
import {
  Monitor,
  Activity,
  CheckCircle,
  Clock,
  DollarSign,
  TrendingUp,
  Eye,
  Pause,
  Play,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";

/** Normalize backend log { ts, level, message, source, agent, type, ticker?, confidence?, pnlImpact? } to UI shape */
function normalizeLogs(backend) {
  if (!backend?.logs?.length) return [];
  return backend.logs.map((log, i) => {
    const ts = log.ts || "";
    const time = ts.slice(11, 19); // HH:mm:ss from ISO
    return {
      id: i + 1,
      timestamp: time || "—",
      agent: log.agent || log.source || "system",
      action: log.message || "—",
      ticker: log.ticker ?? "—",
      confidence: log.confidence ?? 0,
      pnlImpact: log.pnlImpact ?? "—",
      type: log.type || "signal",
    };
  });
}

/** Map agents API to Operator Console grid (signals/profitToday/winRate are placeholders if not provided) */
function normalizeAgents(backend) {
  if (!backend?.agents?.length) return [];
  return backend.agents.map((a) => ({
    name: a.name?.replace(/\s+Agent$/, "Agent") || "Agent",
    status: a.status === "running" ? "running" : "paused",
    signals: a.signals ?? 0,
    profitToday: a.profitToday ?? 0,
    winRate: a.winRate ?? 0.7,
    lastAction: a.lastAction ? "Recent" : "—",
  }));
}

export default function OperatorConsole() {
  const [isPaused, setIsPaused] = useState(false);
  const [filter, setFilter] = useState("all");
  const {
    data: logsData,
    loading: logsLoading,
    error: logsError,
    refetch: refetchLogs,
  } = useApi("logs", { pollIntervalMs: 15000 });
  const { data: agentsData, loading: agentsLoading } = useApi("agents", {
    pollIntervalMs: 20000,
  });

  const logs = useMemo(() => normalizeLogs(logsData), [logsData]);
  const agents = useMemo(() => normalizeAgents(agentsData), [agentsData]);

  const totalProfitToday = agents.reduce(
    (sum, a) => sum + (a.profitToday || 0),
    0,
  );
  const activeAgents = agents.filter((a) => a.status === "running").length;
  const isLoading = logsLoading && agentsLoading;

  const getLogTypeColor = (type) => {
    switch (type) {
      case "signal":
        return "text-cyan-400 bg-cyan-500/10";
      case "risk":
        return "text-amber-400 bg-amber-500/10";
      case "ml":
        return "text-purple-400 bg-purple-500/10";
      case "data":
        return "text-blue-400 bg-blue-500/10";
      case "sentiment":
        return "text-emerald-400 bg-emerald-500/10";
      default:
        return "text-gray-400 bg-gray-500/10";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with P&L Summary */}
      <PageHeader
        icon={Monitor}
        title="Operator Console"
        description={
          logsError
            ? "Failed to load activity"
            : "Glass House view - see everything, control everything"
        }
      >
        <div className="flex items-center gap-4">
          {logsError && (
            <button
              onClick={() => refetchLogs()}
              className="text-xs text-amber-400 hover:text-amber-300"
            >
              Retry logs
            </button>
          )}
          <div className="bg-gray-800/50 rounded-lg px-4 py-2 border border-gray-700/50">
            <div className="text-xs text-gray-500">TODAY'S P&L</div>
            <div
              className={`text-xl font-bold ${totalProfitToday >= 0 ? "text-emerald-400" : "text-red-400"}`}
            >
              {totalProfitToday >= 0 ? "+" : ""}$
              {totalProfitToday.toLocaleString()}
            </div>
          </div>
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`p-3 rounded-lg transition-all ${
              isPaused
                ? "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30"
                : "bg-amber-500/20 text-amber-400 hover:bg-amber-500/30"
            }`}
          >
            {isPaused ? (
              <Play className="w-5 h-5" />
            ) : (
              <Pause className="w-5 h-5" />
            )}
          </button>
        </div>
      </PageHeader>

      {/* Agent Status Grid */}
      {agentsLoading && agents.length === 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50 animate-pulse"
            >
              <div className="h-4 bg-gray-600/50 rounded w-2/3 mb-3" />
              <div className="space-y-2">
                <div className="h-3 bg-gray-600/30 rounded w-full" />
                <div className="h-3 bg-gray-600/30 rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      )}
      {!agentsLoading && agents.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {agents.map((agent) => (
            <div
              key={agent.name}
              className={`bg-gray-800/30 rounded-xl p-4 border ${
                agent.status === "running"
                  ? "border-emerald-500/30"
                  : "border-amber-500/30"
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-white">
                  {agent.name}
                </span>
                <div
                  className={`w-2 h-2 rounded-full ${
                    agent.status === "running"
                      ? "bg-emerald-400 animate-pulse"
                      : "bg-amber-400"
                  }`}
                />
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-500">Signals</span>
                  <span className="text-gray-300">{agent.signals}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Profit</span>
                  <span
                    className={
                      agent.profitToday >= 0
                        ? "text-emerald-400"
                        : "text-red-400"
                    }
                  >
                    +${agent.profitToday.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Win Rate</span>
                  <span className="text-cyan-400">
                    {(agent.winRate * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Live Activity Feed */}
      <div className="bg-gray-800/30 rounded-xl border border-gray-700/50">
        <div className="p-4 border-b border-gray-700/50 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-cyan-400" />
            Live Activity Feed
            <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full ml-2">
              {isPaused ? "PAUSED" : "LIVE"}
            </span>
          </h2>
          <div className="flex items-center gap-2">
            {["all", "signal", "risk", "ml", "sentiment"].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 text-xs rounded-lg transition-all ${
                  filter === f
                    ? "bg-cyan-500/20 text-cyan-400"
                    : "text-gray-500 hover:text-gray-300"
                }`}
              >
                {f.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
        <div className="divide-y divide-gray-700/30 max-h-96 overflow-y-auto">
          {logsLoading && logs.length === 0 && (
            <div className="p-6 text-center text-gray-500 text-sm">
              Loading activity...
            </div>
          )}
          {!logsLoading && logs.length === 0 && (
            <div className="p-6 text-center text-gray-500 text-sm">
              No activity logs yet.
            </div>
          )}
          {logs
            .filter((log) => filter === "all" || log.type === filter)
            .map((log) => (
              <div
                key={log.id}
                className="p-3 hover:bg-gray-800/30 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-500 w-16">
                      {log.timestamp}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${getLogTypeColor(log.type)}`}
                    >
                      {log.agent}
                    </span>
                    <span className="text-sm text-gray-300">{log.action}</span>
                    <span className="text-sm font-medium text-white">
                      {log.ticker}
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-xs text-gray-500">
                      Confidence:{" "}
                      <span className="text-cyan-400">
                        {(log.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div
                      className={`text-xs font-medium ${
                        String(log.pnlImpact || "").includes("+")
                          ? "text-emerald-400"
                          : "text-gray-400"
                      }`}
                    >
                      {log.pnlImpact}
                    </div>
                  </div>
                </div>
              </div>
            ))}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
            <Eye className="w-4 h-4" />
            Active Agents
          </div>
          <div className="text-2xl font-bold text-white">
            {activeAgents}/{agents.length}
          </div>
        </div>
        <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
            <TrendingUp className="w-4 h-4" />
            Signals Today
          </div>
          <div className="text-2xl font-bold text-cyan-400">
            {agents.reduce((s, a) => s + a.signals, 0)}
          </div>
        </div>
        <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
            <CheckCircle className="w-4 h-4" />
            Avg Win Rate
          </div>
          <div className="text-2xl font-bold text-emerald-400">
            {(
              (agents.reduce((s, a) => s + a.winRate, 0) / agents.length) *
              100
            ).toFixed(0)}
            %
          </div>
        </div>
        <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
            <Clock className="w-4 h-4" />
            System Uptime
          </div>
          <div className="text-2xl font-bold text-white">99.9%</div>
        </div>
      </div>
    </div>
  );
}
