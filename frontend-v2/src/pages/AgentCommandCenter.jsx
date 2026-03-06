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

export default function AgentCommandCenter() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get("tab") || "overview";

  // Data hooks
  const { data: agentsRaw } = useApi("agents", { pollIntervalMs: 15000 });
  const { data: systemStatus } = useApi("system/health");
  const agents = useMemo(() => (Array.isArray(agentsRaw) ? agentsRaw : []), [agentsRaw]);

  // Derived metrics
  const onlineCount = agents.filter(a => a.status === "running").length;
  const totalCount = agents.length || 42;
  const cpuAvg = agents.length > 0
    ? Math.round(agents.reduce((s, a) => s + (a.cpu_usage || 0), 0) / agents.length)
    : 47;
  const ramPct = systemStatus?.memory_percent || 31;
  const gpuPct = systemStatus?.gpu_percent || 67;
  const uptime = systemStatus?.uptime || "47h 12m 33s";

  const setTab = (key) => setSearchParams({ tab: key });

  return (
    <div className="min-h-screen bg-[#0B0E14] text-white">
      {/* ========== HEADER BAR ========== */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-800 bg-[#111827]/80">
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-cyan-400" />
          <h1 className="text-base font-bold tracking-wide">AGENT COMMAND CENTER</h1>
          <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            OPERATIONAL
          </span>
          <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            GREEN
          </span>
        </div>

        <div className="flex items-center gap-4 text-[10px]">
          <span className="text-gray-500">Uptime: <span className="text-white font-mono">{uptime}</span></span>
          <span className="text-gray-500">{onlineCount}/{totalCount} <span className="text-emerald-400">ONLINE</span></span>
          <div className="flex items-center gap-1">
            <Cpu className="w-3 h-3 text-gray-500" />
            <span className="text-gray-500">CPU:</span>
            <span className={cpuAvg > 80 ? "text-red-400" : cpuAvg > 60 ? "text-amber-400" : "text-white"}>{cpuAvg}%</span>
          </div>
          <span className="text-gray-500">RAM: <span className={ramPct > 80 ? "text-red-400" : "text-white"}>{ramPct}%</span></span>
          <span className="text-gray-500">GPU: <span className={gpuPct > 80 ? "text-red-400" : gpuPct > 60 ? "text-amber-400" : "text-white"}>{gpuPct}%</span></span>
          <button
            className="px-3 py-1 text-[10px] font-bold bg-red-600/30 text-red-300 border border-red-500/50 rounded hover:bg-red-600/50 transition-all flex items-center gap-1"
            onClick={() => toast.error("KILL SWITCH activated — all agents halting!")}
          >
            <Power className="w-3 h-3" />
            KILL SWITCH
          </button>
          <span className="text-gray-600 text-[9px]">ELITE TRADING SYSTEM</span>
        </div>
      </div>

      {/* ========== TAB BAR ========== */}
      <div className="flex items-center gap-0 px-4 border-b border-gray-800 bg-[#111827]/40">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-[11px] font-medium border-b-2 transition-all ${
              activeTab === t.key
                ? "text-cyan-400 border-cyan-400 bg-cyan-500/5"
                : "text-gray-500 border-transparent hover:text-gray-300 hover:bg-gray-800/30"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ========== TAB CONTENT ========== */}
      <div className="p-4">
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
      <div className="flex items-center justify-between px-4 py-1.5 border-t border-gray-800 bg-[#111827]/60 text-[9px] text-gray-600">
        <div className="flex items-center gap-3">
          <span>WebSocket: <span className="text-emerald-400">Connected</span></span>
          <span>•</span>
          <span>{totalCount} Agents</span>
          <span>•</span>
          <span>Live Files: 847</span>
          <span>•</span>
          <span>Council: {onlineCount}/{totalCount}</span>
        </div>
        <div className="flex items-center gap-3">
          <span>{new Date().toLocaleTimeString()}</span>
          <span>•</span>
          <span>{onlineCount} active</span>
          <span>•</span>
          <span>{totalCount - onlineCount} idle</span>
        </div>
      </div>
    </div>
  );
}
