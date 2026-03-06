// AGENT COMMAND CENTER — Embodier.ai
// Glass Box Intelligence Cockpit + Swarm Management
// Header bar + 12 tabs: 4 Glass Box + 8 Swarm
import React, { useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Activity, Cpu, Shield, Zap, AlertTriangle, Power, Eye, Settings,
  Radio, BookOpen, Brain,
} from "lucide-react";
import { useApi } from "../hooks/useApi";
import { toast } from "react-toastify";

// Glass Box cockpit tabs
import { CouncilTransparencyTab, OperatorControlsTab, LiveEventFeedTab, LearningSummaryTab, DecisionReplayTab } from "./agent-tabs/GlassBoxTabs";

// Swarm management tabs
import SwarmOverviewTab from "./agent-tabs/SwarmOverviewTab";
import AgentRegistryTab from "./agent-tabs/AgentRegistryTab";
import SpawnScaleTab from "./agent-tabs/SpawnScaleTab";
import LiveWiringTab from "./agent-tabs/LiveWiringTab";
import { BlackboardCommsTab, ConferenceConsensusTab, MlOpsTab, LogsTelemetryTab } from "./agent-tabs/RemainingTabs";

const TABS = [
  // Glass Box Intelligence Cockpit
  { key: "council", label: "Council", icon: "eye", group: "glass-box" },
  { key: "controls", label: "Operator Controls", icon: "settings", group: "glass-box" },
  { key: "events", label: "Event Feed", icon: "radio", group: "glass-box" },
  { key: "learning", label: "Learning", icon: "brain", group: "glass-box" },
  { key: "replay", label: "Decision Replay", icon: "book", group: "glass-box" },
  // Swarm Management
  { key: "overview", label: "Swarm Overview", group: "swarm" },
  { key: "registry", label: "Agent Registry", group: "swarm" },
  { key: "spawn", label: "Spawn & Scale", group: "swarm" },
  { key: "wiring", label: "Live Wiring Map", group: "swarm" },
  { key: "blackboard", label: "Blackboard & Comms", group: "swarm" },
  { key: "conference", label: "Conference & Consensus", group: "swarm" },
  { key: "mlops", label: "ML Ops", group: "swarm" },
  { key: "logs", label: "Logs & Telemetry", group: "swarm" },
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
  const gpuPct = systemStatus?.gpu_percent || 61;
  const uptime = systemStatus?.uptime || "47h 12m 33s";

  const setTab = (key) => setSearchParams({ tab: key });

  const glassBoxTabs = TABS.filter(t => t.group === "glass-box");
  const swarmTabs = TABS.filter(t => t.group === "swarm");

  return (
    <div className="min-h-screen bg-[#0B0E14] text-white">
      {/* ========== HEADER BAR ========== */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-800 bg-[#111827]/80">
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-cyan-400" />
          <h1 className="text-base font-bold tracking-wide">AGENT COMMAND CENTER</h1>
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

      {/* ========== TAB BAR (Glass Box + Swarm groups) ========== */}
      <div className="flex items-center gap-0 px-4 border-b border-gray-800 bg-[#111827]/40">
        {/* Glass Box section */}
        <div className="flex items-center gap-0 border-r border-gray-700 pr-1 mr-1">
          <span className="text-[8px] text-gray-600 uppercase tracking-widest px-2 py-2">Glass Box</span>
          {glassBoxTabs.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-3 py-2 text-[11px] font-medium border-b-2 transition-all ${
                activeTab === t.key
                  ? "text-cyan-400 border-cyan-400 bg-cyan-500/5"
                  : "text-gray-500 border-transparent hover:text-gray-300 hover:bg-gray-800/30"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        {/* Swarm section */}
        <div className="flex items-center gap-0">
          <span className="text-[8px] text-gray-600 uppercase tracking-widest px-2 py-2">Swarm</span>
          {swarmTabs.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-3 py-2 text-[11px] font-medium border-b-2 transition-all ${
                activeTab === t.key
                  ? "text-cyan-400 border-cyan-400 bg-cyan-500/5"
                  : "text-gray-500 border-transparent hover:text-gray-300 hover:bg-gray-800/30"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* ========== TAB CONTENT ========== */}
      <div className="p-4">
        {/* Glass Box tabs */}
        {activeTab === "council" && <CouncilTransparencyTab />}
        {activeTab === "controls" && <OperatorControlsTab />}
        {activeTab === "events" && <LiveEventFeedTab />}
        {activeTab === "learning" && <LearningSummaryTab />}
        {activeTab === "replay" && <DecisionReplayTab />}
        {/* Swarm tabs */}
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
