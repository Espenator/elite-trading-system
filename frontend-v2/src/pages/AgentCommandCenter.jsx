// AGENT COMMAND CENTER — Embodier.ai
// Mockups: 01-agent-command-center-final.png, 05-agent-command-center.png,
//          05b-agent-command-center-spawn.png, 05c-agent-registry.png
// Header bar + 8 tabs, each in its own component file
import React, { useState, useMemo, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Activity, Cpu, Shield, Zap, AlertTriangle, Power,
} from "lucide-react";
import { useApi } from "../hooks/useApi";
import { toast } from "react-toastify";
import { getApiUrl, getAuthHeaders } from "../config/api";
import ws from "../services/websocket";

// Tab components (split for manageable file sizes)
import SwarmOverviewTab from "./agent-tabs/SwarmOverviewTab";
import AgentRegistryTab from "./agent-tabs/AgentRegistryTab";
import SpawnScaleTab from "./agent-tabs/SpawnScaleTab";
import LiveWiringTab from "./agent-tabs/LiveWiringTab";
import { BlackboardCommsTab, ConferenceConsensusTab, MlOpsTab, LogsTelemetryTab } from "./agent-tabs/RemainingTabs";

const TABS = [
  { key: "overview", label: "Swarm Overview" },
  { key: "registry", label: "Agent Registry" },
  { key: "spawn", label: "Spawn & Scale" },
  { key: "wiring", label: "Live Wiring Map" },
  { key: "blackboard", label: "Blackboard & Comms" },
  { key: "conference", label: "Conference & Consensus" },
  { key: "mlops", label: "ML Ops" },
  { key: "logs", label: "Logs & Telemetry" },
];

// Progress bar component for system metrics
function MetricBar({ value, max = 100, color = "#00D9FF" }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const barColor = value > 80 ? "#ef4444" : value > 60 ? "#f59e0b" : color;
  return (
    <div className="inline-flex items-center gap-1">
      <div className="w-12 h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: barColor }}
        />
      </div>
    </div>
  );
}

export default function AgentCommandCenter() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get("tab") || "overview";

  // Data hooks
  const { data: agentsRaw, lastUpdated } = useApi("agents", { pollIntervalMs: 15000 });
  const { data: systemStatus } = useApi("system/health", { pollIntervalMs: 30000 });
  const { data: apiStatus } = useApi("status", { pollIntervalMs: 15000 });
  const { data: gpuStatus } = useApi("system/health", { endpoint: "/system/gpu", pollIntervalMs: 30000 });
  const { data: eventBusStatus } = useApi("system/event-bus/status", { pollIntervalMs: 15000 });
  const { data: alertsStatus } = useApi("systemAlerts", { pollIntervalMs: 30000 });
  const [wsConnected, setWsConnected] = useState(ws.isConnected());
  const agents = useMemo(() => (
    Array.isArray(agentsRaw)
      ? agentsRaw
      : Array.isArray(agentsRaw?.agents)
        ? agentsRaw.agents
        : []
  ), [agentsRaw]);

  useEffect(() => {
    ws.connect();
    const unsubscribe = ws.on("*", (event) => {
      if (event?.type === "connected") setWsConnected(true);
      if (event?.type === "disconnected" || event?.type === "error") setWsConnected(false);
    });
    setWsConnected(ws.isConnected());
    return unsubscribe;
  }, []);

  // Derived metrics
  const onlineCount = agents.filter(a => String(a.status).toLowerCase() === "running").length;
  const totalCount = agents.length;
  const cpuValues = agents
    .map((a) => a.cpuPercent ?? a.cpu_usage)
    .filter((value) => typeof value === "number");
  const cpuAvg = cpuValues.length > 0
    ? Math.round(cpuValues.reduce((sum, value) => sum + value, 0) / cpuValues.length)
    : null;
  const memoryMb = agents.find((agent) => typeof agent.memoryMb === "number")?.memoryMb ?? null;
  const gpuPct = gpuStatus?.gpus?.[0]?.gpu_utilization_pct ?? null;
  const uptime = agents.find((agent) => agent.uptime)?.uptime ?? null;
  const apiHealthy = apiStatus?.connected === true;
  const topicCount = Array.isArray(eventBusStatus?.topics) ? eventBusStatus.topics.length : 0;
  const alertCount = Array.isArray(alertsStatus?.alerts) ? alertsStatus.alerts.length : 0;
  const lastRefresh = lastUpdated
    ? new Date(lastUpdated).toLocaleTimeString("en-US", { hour12: false })
    : "—";
  const healthBadge = !apiHealthy ? "RED" : alertCount > 0 ? "AMBER" : "GREEN";
  const healthBadgeClasses = {
    GREEN: "bg-emerald-500/20 text-emerald-400 border-emerald-500/40",
    AMBER: "bg-amber-500/20 text-amber-400 border-amber-500/40",
    RED: "bg-red-500/20 text-red-400 border-red-500/40",
  };

  const setTab = (key) => setSearchParams({ tab: key });

  const handleEmergencyStop = useCallback(async () => {
    if (!window.confirm("Emergency stop will cancel all orders and flatten all positions. Continue?")) {
      return;
    }

    try {
      const response = await fetch(getApiUrl("orders/emergency-stop"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.detail || `HTTP ${response.status}`);
      }
      toast.success(payload?.status || "Emergency stop executed");
    } catch (error) {
      toast.error(`Emergency stop failed: ${error.message}`);
    }
  }, []);

  return (
    <div className="min-h-screen bg-[#0B0E14] text-white flex flex-col">
      {/* ========== HEADER BAR ========== */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-[#111827]/90 shrink-0">
        {/* Left: Title + Status */}
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-[#00D9FF]" />
          <h1 className="text-sm font-bold tracking-widest text-white font-mono">AGENT COMMAND CENTER</h1>
          <span className={`px-2 py-0.5 text-[10px] font-bold rounded border tracking-wider ${healthBadgeClasses[healthBadge]}`}>
            {healthBadge}
          </span>
        </div>

        {/* Center: System Metrics */}
        <div className="flex items-center gap-5 text-[10px] font-mono">
          <div className="flex items-center gap-1.5">
            <span className="text-gray-500">Uptime:</span>
            <span className="text-white font-bold">{uptime ?? "—"}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-white font-bold">{onlineCount}/{totalCount}</span>
            <span className={onlineCount === totalCount && totalCount > 0 ? "text-emerald-400 font-bold" : "text-amber-400 font-bold"}>
              RUNNING
            </span>
            <div className={`w-1.5 h-1.5 rounded-full ${onlineCount === totalCount && totalCount > 0 ? "bg-emerald-400" : "bg-amber-400"} ${onlineCount > 0 ? "animate-pulse" : ""}`} />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-gray-500">CPU:</span>
            <span className={cpuAvg > 80 ? "text-red-400 font-bold" : cpuAvg > 60 ? "text-amber-400 font-bold" : "text-white font-bold"}>{cpuAvg != null ? `${cpuAvg}%` : "—"}</span>
            {cpuAvg != null && <MetricBar value={cpuAvg} />}
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-gray-500">MEM:</span>
            <span className="text-white font-bold">{memoryMb != null ? `${memoryMb}MB` : "—"}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-gray-500">GPU:</span>
            <span className={gpuPct > 80 ? "text-red-400 font-bold" : gpuPct > 60 ? "text-amber-400 font-bold" : "text-white font-bold"}>{gpuPct != null ? `${Math.round(gpuPct)}%` : "—"}</span>
            {gpuPct != null && <MetricBar value={gpuPct} color="#a855f7" />}
          </div>
        </div>

        {/* Right: Kill Switch + Branding */}
        <div className="flex items-center gap-4">
          <button
            className="px-3 py-1.5 text-[11px] font-bold bg-red-600/20 text-red-400 border border-red-500/50 rounded hover:bg-red-600/40 hover:shadow-[0_0_12px_rgba(239,68,68,0.3)] transition-all flex items-center gap-1.5 tracking-wider"
            onClick={handleEmergencyStop}
          >
            <Power className="w-3 h-3" />
            KILL SWITCH
          </button>
          <span className="text-[10px] text-gray-500 font-mono tracking-[0.2em] uppercase">ELITE TRADING SYSTEM</span>
        </div>
      </div>

      {/* ========== TAB BAR ========== */}
      <div className="flex items-center px-4 border-b border-gray-800 bg-[#111827]/40 shrink-0">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-[11px] font-medium border-b-2 transition-all whitespace-nowrap ${
              activeTab === t.key
                ? "text-[#00D9FF] border-[#00D9FF] bg-[#00D9FF]/5"
                : "text-gray-500 border-transparent hover:text-gray-300 hover:bg-gray-800/30"
            }`}
          >
            {t.label}
            {activeTab === t.key && (
              <span className="ml-1.5 text-[9px] text-[#00D9FF]/60 uppercase tracking-wider">ACTIVE</span>
            )}
          </button>
        ))}
      </div>

      {/* ========== TAB CONTENT ========== */}
      <div className="flex-1 p-3 overflow-y-auto">
        {activeTab === "overview" && <SwarmOverviewTab agents={agents} />}
        {activeTab === "registry" && <AgentRegistryTab agents={agents} />}
        {activeTab === "spawn" && <SpawnScaleTab />}
        {activeTab === "wiring" && <LiveWiringTab />}
        {activeTab === "blackboard" && <BlackboardCommsTab />}
        {activeTab === "conference" && <ConferenceConsensusTab />}
        {activeTab === "mlops" && <MlOpsTab />}
        {activeTab === "logs" && <LogsTelemetryTab />}
      </div>

      {/* ========== FOOTER BAR ========== */}
      <div className="flex items-center justify-between px-4 py-1 border-t border-gray-800 bg-[#111827]/80 text-[9px] font-mono shrink-0">
        <div className="flex items-center gap-3 text-gray-600">
          <span className="flex items-center gap-1">
            WebSocket <span className={`${wsConnected ? "text-emerald-400" : "text-red-400"} ml-0.5`}>{wsConnected ? "Connected" : "Disconnected"}</span>
            <div className={`w-1.5 h-1.5 rounded-full ml-0.5 ${wsConnected ? "bg-emerald-400 animate-pulse" : "bg-red-400"}`} />
          </span>
          <span className="text-gray-700">|</span>
          <span>API <span className={apiHealthy ? "text-emerald-400" : "text-red-400"}>{apiHealthy ? "Healthy" : "Unavailable"}</span>
            <div className={`w-1.5 h-1.5 inline-block ml-0.5 rounded-full ${apiHealthy ? "bg-emerald-400 animate-pulse" : "bg-red-400"}`} />
          </span>
          <span className="text-gray-700">|</span>
          <span><span className="text-white">{onlineCount}/{totalCount}</span> agents</span>
          <span className="text-gray-700">|</span>
          <span>Topics <span className="text-white">{topicCount}</span></span>
          <span className="text-gray-700">|</span>
          <span>Alerts <span className={alertCount > 0 ? "text-amber-400" : "text-white"}>{alertCount}</span></span>
          <span className="text-gray-700">|</span>
          <span>Mode <span className="text-white">{systemStatus?.trading_mode ?? "—"}</span></span>
          <span className="text-gray-700">|</span>
          <span>Last Refresh <span className="text-[#00D9FF]">{lastRefresh}</span></span>
          <span className="text-gray-700">|</span>
          <span>Uptime <span className="text-white">{uptime ?? "—"}</span></span>
        </div>
        <div className="text-gray-700">
          Embodier.ai v2.0
        </div>
      </div>
    </div>
  );
}
