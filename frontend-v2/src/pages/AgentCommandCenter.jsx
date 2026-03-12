// AGENT COMMAND CENTER — Embodier.ai
// Mockups: 01-agent-command-center-final.png, 05-agent-command-center.png,
//          05b-agent-command-center-spawn.png, 05c-agent-registry.png
// Header bar + 5 tabs (SwarmOverview, AgentRegistry, LiveWiring, SpawnScale, Remaining)
import React, { useState, useMemo, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Activity, Cpu, Shield, Zap, AlertTriangle, Power,
} from "lucide-react";
import { useApi } from "../hooks/useApi";
import { toast } from "react-toastify";
import { getApiUrl, getAuthHeaders, WS_CHANNELS } from "../config/api";
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
  { key: "wiring", label: "Live Wiring Map" },
  { key: "spawn", label: "Spawn & Scale" },
  { key: "remaining", label: "More" },
];

// Remaining tab: sub-tabs for Blackboard, Conference, MLOps, Logs
const REMAINING_SUBTABS = [
  { key: "blackboard", label: "Blackboard & Comms" },
  { key: "conference", label: "Conference & Consensus" },
  { key: "mlops", label: "ML Ops" },
  { key: "logs", label: "Logs & Telemetry" },
];

function RemainingTabContent() {
  const [subTab, setSubTab] = useState("blackboard");
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 border-b border-[#1e293b] pb-2">
        {REMAINING_SUBTABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setSubTab(t.key)}
            className={`px-3 py-1.5 text-[11px] font-medium rounded-t transition-all ${
              subTab === t.key
                ? "text-[#06b6d4] bg-[#164e63]/20 border border-b-0 border-[#1e293b] -mb-[2px]"
                : "text-[#64748b] hover:text-[#94a3b8]"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {subTab === "blackboard" && <BlackboardCommsTab />}
      {subTab === "conference" && <ConferenceConsensusTab />}
      {subTab === "mlops" && <MlOpsTab />}
      {subTab === "logs" && <LogsTelemetryTab />}
    </div>
  );
}

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
  const tabParam = searchParams.get("tab") || "overview";
  const activeTab = TABS.some((t) => t.key === tabParam) ? tabParam : "overview";
  const [wsState, setWsState] = useState(ws.getState());

  // Data hooks (real API — no mock data)
  const { data: agentsRaw, loading: agentsLoading } = useApi("agents", { pollIntervalMs: 15000 });
  const { data: systemStatus } = useApi("system/health");
  const { data: teamsRaw } = useApi("teams", { pollIntervalMs: 20000 });
  const { data: alertsRaw } = useApi("systemAlerts", { pollIntervalMs: 20000 });
  const { data: conferenceRaw } = useApi("conference", { pollIntervalMs: 20000 });
  const { data: driftRaw } = useApi("drift", { pollIntervalMs: 30000 });
  const { data: blackboardRaw } = useApi("cnsBlackboard", { pollIntervalMs: 15000 });
  const { data: cnsAgentsHealthRaw } = useApi("cnsAgentsHealth", { pollIntervalMs: 15000 });

  // Backend GET /agents returns { agents: [...], logs: [...] }
  const agents = useMemo(() => {
    if (Array.isArray(agentsRaw)) return agentsRaw;
    if (agentsRaw?.agents && Array.isArray(agentsRaw.agents)) return agentsRaw.agents;
    return [];
  }, [agentsRaw]);

  const teams = useMemo(() => (Array.isArray(teamsRaw) ? teamsRaw : teamsRaw?.teams ?? []), [teamsRaw]);
  const alerts = useMemo(() => (Array.isArray(alertsRaw) ? alertsRaw : alertsRaw?.alerts ?? []), [alertsRaw]);
  const conferenceData = useMemo(() => conferenceRaw?.current ?? conferenceRaw?.conference ?? conferenceRaw ?? null, [conferenceRaw]);
  const driftData = useMemo(() => (Array.isArray(driftRaw) ? driftRaw : driftRaw?.drift ?? driftRaw?.metrics ?? []), [driftRaw]);
  const blackboardTopics = useMemo(() => {
    const b = blackboardRaw?.topics ?? blackboardRaw?.blackboard ?? blackboardRaw;
    if (Array.isArray(b)) return b;
    if (b && typeof b === "object") return Object.entries(b).map(([topic, data]) => ({ topic, ...(typeof data === "object" ? data : { last: data }) }));
    return [];
  }, [blackboardRaw]);
  const agentsForHealth = useMemo(() => {
    const healthList = cnsAgentsHealthRaw?.agents ?? cnsAgentsHealthRaw?.matrix ?? (Array.isArray(cnsAgentsHealthRaw) ? cnsAgentsHealthRaw : []);
    if (healthList.length > 0) {
      return healthList.map((a) => ({
        name: a.name ?? a.agent_name ?? a.agent,
        agent_name: a.agent_name ?? a.name,
        status: a.status ?? (a.last_heartbeat ? "running" : "stopped"),
        health: a.health ?? (a.status === "running" ? "healthy" : a.status === "error" ? "error" : "stopped"),
        last_heartbeat: a.last_heartbeat,
        type: a.type,
      }));
    }
    return agents;
  }, [cnsAgentsHealthRaw, agents]);

  // Real agent counts from /agents (no mock)
  const totalCount = agents.length;
  const activeCount = useMemo(() => agents.filter(a => (a.status || "").toLowerCase() === "running").length, [agents]);
  const erroredCount = useMemo(() => agents.filter(a => (a.status || "").toLowerCase() === "error" || (a.health || "").toLowerCase() === "error").length, [agents]);
  const cpuAvg = agents.length > 0
    ? Math.round(agents.reduce((s, a) => s + (a.cpu_usage ?? a.cpu ?? a.cpuPercent ?? 0), 0) / agents.length)
    : 0;
  const ramPct = systemStatus?.memory_percent ?? 0;
  const gpuPct = systemStatus?.gpu_percent ?? 0;
  const uptime = systemStatus?.uptime ?? "—";

  const setTab = useCallback((key) => setSearchParams((prev) => {
    const next = new URLSearchParams(prev);
    next.set("tab", key);
    return next;
  }), [setSearchParams]);

  // WebSocket: connect on mount, subscribe to agents + swarm for live events, track connection state
  useEffect(() => {
    ws.connect();
    setWsState(ws.getState());
    const onState = () => setWsState(ws.getState());
    const unsubStar = ws.on("*", onState);
    const unsubAgents = ws.on(WS_CHANNELS.agents, () => {});
    const unsubSwarm = ws.on(WS_CHANNELS.swarm, () => {});
    return () => {
      unsubStar?.();
      unsubAgents?.();
      unsubSwarm?.();
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#0B0E14] text-white flex flex-col">
      {/* ========== HEADER BAR ========== */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#1e293b] bg-[#111827] shrink-0">
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-[#06b6d4]" />
          <h1 className="text-sm font-bold tracking-widest text-[#f8fafc] font-mono">AGENT COMMAND CENTER</h1>
          <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-[#064e3b] text-[#10b981] border border-[#10b981]/40 tracking-wider">
            GREEN
          </span>
        </div>

        <div className="flex items-center gap-5 text-[10px] font-mono">
          <div className="flex items-center gap-1.5">
            <span className="text-[#64748b]">Uptime:</span>
            <span className="text-[#f8fafc] font-bold">{uptime}</span>
          </div>
          <div className="flex items-center gap-1.5">
            {agentsLoading ? (
              <span className="text-[#64748b]">Loading…</span>
            ) : (
              <>
                <span className="text-[#f8fafc] font-bold">{activeCount}/{totalCount}</span>
                <span className={erroredCount > 0 ? "text-[#f87171] font-bold" : "text-[#10b981] font-bold"}>
                  {erroredCount > 0 ? "ERRORS" : "ONLINE"}
                </span>
                {erroredCount > 0 && <span className="text-[#f87171] text-[10px]">({erroredCount})</span>}
                <div className={`w-1.5 h-1.5 rounded-full ${erroredCount > 0 ? "bg-[#f87171]" : "bg-[#10b981]"} animate-pulse`} />
              </>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[#64748b]">CPU:</span>
            <span className={cpuAvg > 80 ? "text-[#ef4444] font-bold" : cpuAvg > 60 ? "text-[#f59e0b] font-bold" : "text-[#f8fafc] font-bold"}>{cpuAvg}%</span>
            <MetricBar value={cpuAvg} color="#3b82f6" />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[#64748b]">RAM:</span>
            <span className={ramPct > 80 ? "text-[#ef4444] font-bold" : "text-[#f8fafc] font-bold"}>{ramPct}%</span>
            <MetricBar value={ramPct} color="#10b981" />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[#64748b]">GPU:</span>
            <span className={gpuPct > 80 ? "text-[#ef4444] font-bold" : gpuPct > 60 ? "text-[#f59e0b] font-bold" : "text-[#f8fafc] font-bold"}>{gpuPct}%</span>
            <MetricBar value={gpuPct} color="#8b5cf6" />
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button
            className="px-4 py-1.5 text-[11px] font-bold bg-[#7f1d1d] text-[#f87171] border border-[#ef4444]/50 rounded-full hover:bg-[#991b1b] hover:shadow-[0_0_12px_rgba(239,68,68,0.3)] transition-all flex items-center gap-1.5 tracking-wider"
            onClick={async () => {
              try {
                const res = await fetch(getApiUrl("orders/emergency-stop"), { method: "POST", headers: getAuthHeaders() });
                if (res.ok) {
                  toast.error("KILL SWITCH activated — orders cancelled, positions closed.");
                } else {
                  const err = await res.json().catch(() => ({}));
                  toast.error(err?.detail || `Emergency stop failed: ${res.status}`);
                }
              } catch (e) {
                toast.error("KILL SWITCH request failed: " + (e?.message || "network error"));
              }
            }}
          >
            <Power className="w-3 h-3" />
            KILL SWITCH
          </button>
          <span className="text-[10px] text-[#64748b] font-mono tracking-[0.2em] uppercase">ELITE TRADING SYSTEM</span>
        </div>
      </div>

      {/* ========== TAB BAR ========== */}
      <div className="flex items-center px-4 border-b border-[#1e293b] bg-[#111827]/60 shrink-0">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-[11px] font-medium border-b-2 transition-all whitespace-nowrap ${
              activeTab === t.key
                ? "text-[#06b6d4] border-[#06b6d4] bg-[#164e63]/10"
                : "text-[#64748b] border-transparent hover:text-[#94a3b8] hover:bg-[#1e293b]/50"
            }`}
          >
            {t.label}
            {activeTab === t.key && (
              <span className="ml-1.5 text-[9px] text-[#06b6d4]/70 uppercase tracking-wider">ACTIVE</span>
            )}
          </button>
        ))}
      </div>

      {/* ========== TAB CONTENT ========== */}
      <div className="flex-1 p-3 overflow-y-auto">
        {(activeTab === "overview" || activeTab === "registry") && agentsLoading && (
          <div className="flex items-center justify-center py-8 text-[#64748b] text-sm font-mono">
            Loading agents…
          </div>
        )}
        {activeTab === "overview" && !agentsLoading && (
          <SwarmOverviewTab
            agents={agentsForHealth}
            teams={teams}
            alerts={alerts}
            topics={blackboardTopics}
            conferenceData={conferenceData}
            driftData={driftData}
          />
        )}
        {activeTab === "registry" && !agentsLoading && <AgentRegistryTab agents={agents} />}
        {activeTab === "wiring" && <LiveWiringTab agents={agents} wsConnected={wsState === "connected"} />}
        {activeTab === "spawn" && <SpawnScaleTab agents={agents} />}
        {activeTab === "remaining" && <RemainingTabContent />}
      </div>

      {/* ========== FOOTER BAR: real WS state, agent count, uptime ========== */}
      <div className="flex items-center justify-between px-4 py-1.5 border-t border-[#1e293b] bg-[#111827] text-[10px] font-mono shrink-0">
        <div className="flex items-center gap-3 text-[#64748b]">
          <span className="flex items-center gap-1">
            WebSocket{" "}
            {wsState === "connected" ? (
              <>
                <span className="text-[#10b981] ml-0.5">Connected</span>
                <div className="w-1.5 h-1.5 rounded-full bg-[#10b981] animate-pulse ml-0.5" />
              </>
            ) : wsState === "connecting" || wsState === "reconnecting" ? (
              <span className="text-amber-400 ml-0.5">{wsState === "reconnecting" ? "Reconnecting…" : "Connecting…"}</span>
            ) : (
              <span className="text-[#64748b] ml-0.5">Disconnected</span>
            )}
          </span>
          <span className="text-[#374151]">|</span>
          <span><span className="text-[#f8fafc]">{totalCount}</span> agents</span>
          {erroredCount > 0 && (
            <>
              <span className="text-[#374151]">|</span>
              <span className="text-[#f87171]">{erroredCount} error{erroredCount !== 1 ? "s" : ""}</span>
            </>
          )}
          <span className="text-[#374151]">|</span>
          <span>Uptime <span className="text-[#f8fafc]">{uptime}</span></span>
        </div>
        <div className="text-[#64748b]">Embodier.ai v2.0</div>
      </div>
    </div>
  );
}
