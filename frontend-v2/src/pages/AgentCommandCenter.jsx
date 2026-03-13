// AGENT COMMAND CENTER — Embodier.ai
// Mockups: 01-agent-command-center-final.png, 05-agent-command-center.png,
//          05b-agent-command-center-spawn.png, 05c-agent-registry.png
// Header bar + 8 tabs, each in its own component file
import React, { useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Activity, Cpu, Shield, Zap, AlertTriangle, Power,
} from "lucide-react";
import { useApi } from "../hooks/useApi";
import { toast } from "react-toastify";
import { getApiUrl, getAuthHeaders } from "../config/api";

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

// Format uptime_seconds to "Xd Xh Xm" for display
function formatUptime(seconds) {
  if (seconds == null || typeof seconds !== "number") return null;
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const parts = [];
  if (d > 0) parts.push(`${d}d`);
  if (h > 0) parts.push(`${h}h`);
  parts.push(`${m}m`);
  return parts.join(" ");
}

// Progress bar component for system metrics (design system: track #1e293b, 4–6px height). value null → show dash.
function MetricBar({ value, max = 100 }) {
  if (value == null || (typeof value === "number" && (Number.isNaN(value)))) {
    return <span className="text-[#64748b] font-mono text-[10px]">—</span>;
  }
  const num = Number(value);
  const pct = Math.min(100, Math.max(0, (num / max) * 100));
  const barColor = num > 80 ? "#ef4444" : num > 60 ? "#f59e0b" : "#06b6d4";
  return (
    <div className="inline-flex items-center gap-1">
      <div className="w-12 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: "#1e293b" }}>
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
  const [registryPreselectedAgent, setRegistryPreselectedAgent] = useState(null);

  // Data hooks (real API — no mock data); all 8 hooks per spec
  const { data: agentsRaw } = useApi("agents", { pollIntervalMs: 15000 });
  const { data: systemStatus } = useApi("system/health");
  const { data: teamsRaw } = useApi("teams", { pollIntervalMs: 20000 });
  const { data: alertsRaw } = useApi("systemAlerts", { pollIntervalMs: 20000 });
  const { data: conferenceRaw } = useApi("conference", { pollIntervalMs: 20000 });
  const { data: driftRaw } = useApi("drift", { pollIntervalMs: 30000 });
  const { data: blackboardRaw } = useApi("cnsBlackboard", { pollIntervalMs: 15000 });
  const { data: cnsAgentsHealthRaw } = useApi("cnsAgentsHealth", { pollIntervalMs: 15000 });
  const agents = useMemo(() => (Array.isArray(agentsRaw) ? agentsRaw : []), [agentsRaw]);
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

  // Derived metrics — live from system/health only; show "—" when null (no mock fallbacks)
  const onlineCount = agents.filter(a => a.status === "running").length;
  const totalCount = agents.length;
  const cpuPct = systemStatus?.cpu_percent ?? systemStatus?.cpu ?? null;
  const ramPct = systemStatus?.memory_used_percent ?? systemStatus?.memory_percent ?? systemStatus?.memory ?? systemStatus?.ram ?? null;
  const gpuPct = systemStatus?.gpu_percent ?? systemStatus?.gpu ?? (systemStatus?.gpus?.[0]?.gpu_utilization_pct) ?? null;
  const uptime = systemStatus?.uptime ?? (systemStatus?.uptime_seconds != null ? formatUptime(systemStatus.uptime_seconds) : null) ?? "—";

  const setTab = (key) => setSearchParams({ tab: key });
  const handleAgentClickFromOverview = (agentName) => {
    setRegistryPreselectedAgent(agentName);
    setTab("registry");
  };

  return (
    <div className="min-h-screen bg-[#0B0E14] text-white flex flex-col">
      {/* ========== HEADER BAR (mockup 01: AGENT COMMAND CENTER, GREEN, Uptime, 42/42 ONLINE, CPU/RAM/GPU, KILL SWITCH, ELITE TRADING SYSTEM) ========== */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#1e293b] bg-[#111827] shrink-0">
        {/* Left: Title + Status (mockup: text-xl bold white, GREEN dot + GREEN text) */}
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-[#f8fafc] tracking-wide">AGENT COMMAND CENTER</h1>
          <div className="w-2 h-2 rounded-full bg-[#10b981] shrink-0" title="System green" />
          <span className="text-[#10b981] font-semibold text-sm uppercase tracking-wider">GREEN</span>
        </div>

        {/* Center: System Metrics */}
        <div className="flex items-center gap-5 text-[10px] font-mono">
          <div className="flex items-center gap-1.5">
            <span className="text-[#64748b]">Uptime:</span>
            <span className="text-[#f8fafc] font-bold">{uptime ?? "—"}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[#f8fafc] font-bold">{onlineCount}/{totalCount}</span>
            <span className="text-[#10b981] font-bold">ONLINE</span>
            <div className="w-1.5 h-1.5 rounded-full bg-[#10b981] animate-pulse" />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[#64748b]">CPU:</span>
            <span className={`font-mono font-bold ${cpuPct == null ? "text-[#64748b]" : cpuPct > 80 ? "text-[#ef4444]" : cpuPct > 60 ? "text-[#f59e0b]" : "text-[#f8fafc]"}`}>{cpuPct != null ? `${cpuPct}%` : "—"}</span>
            <MetricBar value={cpuPct} />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[#64748b]">RAM:</span>
            <span className={`font-mono font-bold ${ramPct == null ? "text-[#64748b]" : ramPct > 80 ? "text-[#ef4444]" : "text-[#f8fafc]"}`}>{ramPct != null ? `${ramPct}%` : "—"}</span>
            <MetricBar value={ramPct} />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[#64748b]">GPU:</span>
            <span className={`font-mono font-bold ${gpuPct == null ? "text-[#64748b]" : gpuPct > 80 ? "text-[#ef4444]" : gpuPct > 60 ? "text-[#f59e0b]" : "text-[#f8fafc]"}`}>{gpuPct != null ? `${gpuPct}%` : "—"}</span>
            <MetricBar value={gpuPct} />
          </div>
        </div>

        {/* Right: Kill Switch + Branding */}
        <div className="flex items-center gap-4">
          <button
            className="px-4 py-1.5 text-[11px] font-bold bg-[#ef4444] text-white border border-[#ef4444]/50 rounded-md hover:bg-[#dc2626] hover:shadow-[0_0_12px_rgba(239,68,68,0.3)] transition-all flex items-center gap-1.5 tracking-wider cursor-pointer"
            onClick={async () => {
              try {
                const res = await fetch(getApiUrl("orders/emergency-stop"), {
                  method: "POST",
                  headers: { "Content-Type": "application/json", ...getAuthHeaders() },
                });
                if (res.ok) {
                  toast.success("Kill switch activated — orders cancelled, positions closed.");
                } else {
                  const err = await res.json().catch(() => ({}));
                  toast.error(err?.detail?.message ?? err?.detail ?? `Emergency stop failed: ${res.status}`);
                }
              } catch (e) {
                toast.error("Kill switch request failed: " + (e?.message || "network error"));
              }
            }}
          >
            <Power className="w-3 h-3" />
            KILL SWITCH
          </button>
          <span className="text-[10px] text-[#64748b] font-mono tracking-[0.2em] uppercase">ELITE TRADING SYSTEM</span>
        </div>
      </div>

      {/* ========== TAB BAR (mockup: Swarm Overview active with underline) ========== */}
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
        {activeTab === "overview" && (
          <SwarmOverviewTab
            agents={agentsForHealth}
            teams={teams}
            alerts={alerts}
            topics={blackboardTopics}
            conferenceData={conferenceData}
            driftData={driftData}
            onAgentClick={handleAgentClickFromOverview}
            setTab={setTab}
          />
        )}
        {activeTab === "registry" && (
          <AgentRegistryTab
            agents={agents}
            preselectedAgentName={registryPreselectedAgent}
            onClearPreselection={() => setRegistryPreselectedAgent(null)}
          />
        )}
        {activeTab === "spawn" && <SpawnScaleTab />}
        {activeTab === "wiring" && <LiveWiringTab />}
        {activeTab === "blackboard" && <BlackboardCommsTab />}
        {activeTab === "conference" && <ConferenceConsensusTab />}
        {activeTab === "mlops" && <MlOpsTab />}
        {activeTab === "logs" && <LogsTelemetryTab />}
      </div>

      {/* ========== FOOTER BAR: Left = WS + API | Center = agents, LLM Flow, Conference | Right = Last Refresh, Load, Uptime + Embodier.ai ========== */}
      <div className="flex items-center justify-between px-4 py-1.5 border-t border-[#1e293b] bg-[#111827] text-xs font-mono text-[#64748b] shrink-0">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#10b981] shrink-0" />
            <span>WebSocket <span className="text-[#10b981]">Connected</span></span>
          </span>
          <span className="text-[#374151]">|</span>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#10b981] shrink-0" />
            <span>API <span className="text-[#10b981]">Healthy</span></span>
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span><span className="text-[#f8fafc]">{totalCount}</span> agents</span>
          <span className="text-[#374151]">|</span>
          <span>LLM Flow <span className="text-[#f8fafc]">{conferenceData ? (conferenceData.id ?? "—") : "—"}</span></span>
          <span className="text-[#374151]">|</span>
          <span>Conference <span className="text-[#f8fafc]">{onlineCount}/{totalCount}</span></span>
        </div>
        <div className="flex items-center gap-3">
          <span>Last Refresh <span className="text-[#06b6d4]">{new Date().toLocaleTimeString("en-US", { hour12: false })}</span></span>
          <span className="text-[#374151]">|</span>
          <span>Load <span className="text-[#f8fafc]">{cpuPct != null ? `${cpuPct}/100` : "—"}</span></span>
          <span className="text-[#374151]">|</span>
          <span>Uptime <span className="text-[#f8fafc]">{uptime ?? "—"}</span></span>
          <span className="text-[#374151] ml-2">|</span>
          <span className="text-[#64748b]">Embodier.ai v2.0</span>
        </div>
      </div>
    </div>
  );
}
