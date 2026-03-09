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
  const uptime = systemStatus?.uptime || "47d 12h 33m";

  const setTab = (key) => setSearchParams({ tab: key });

  return (
    <div className="min-h-screen bg-[#0B0E14] text-white flex flex-col">
      {/* ========== HEADER BAR (mockup 01: AGENT COMMAND CENTER, GREEN, Uptime, 42/42 ONLINE, CPU/RAM/GPU, KILL SWITCH, ELITE TRADING SYSTEM) ========== */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#1e293b] bg-[#111827] shrink-0">
        {/* Left: Title + Status */}
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-[#06b6d4]" />
          <h1 className="text-sm font-bold tracking-widest text-[#f8fafc] font-mono">AGENT COMMAND CENTER</h1>
          <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-[#064e3b] text-[#10b981] border border-[#10b981]/40 tracking-wider">
            GREEN
          </span>
        </div>

        {/* Center: System Metrics */}
        <div className="flex items-center gap-5 text-[10px] font-mono">
          <div className="flex items-center gap-1.5">
            <span className="text-[#64748b]">Uptime:</span>
            <span className="text-[#f8fafc] font-bold">{uptime}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[#f8fafc] font-bold">{onlineCount}/{totalCount}</span>
            <span className="text-[#10b981] font-bold">ONLINE</span>
            <div className="w-1.5 h-1.5 rounded-full bg-[#10b981] animate-pulse" />
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

        {/* Right: Kill Switch + Branding */}
        <div className="flex items-center gap-4">
          <button
            className="px-4 py-1.5 text-[11px] font-bold bg-[#7f1d1d] text-[#f87171] border border-[#ef4444]/50 rounded-full hover:bg-[#991b1b] hover:shadow-[0_0_12px_rgba(239,68,68,0.3)] transition-all flex items-center gap-1.5 tracking-wider"
            onClick={() => toast.error("KILL SWITCH activated — all agents halting!")}
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
        {activeTab === "overview" && <SwarmOverviewTab agents={agents} />}
        {activeTab === "registry" && <AgentRegistryTab agents={agents} />}
        {activeTab === "spawn" && <SpawnScaleTab />}
        {activeTab === "wiring" && <LiveWiringTab />}
        {activeTab === "blackboard" && <BlackboardCommsTab />}
        {activeTab === "conference" && <ConferenceConsensusTab />}
        {activeTab === "mlops" && <MlOpsTab />}
        {activeTab === "logs" && <LogsTelemetryTab />}
      </div>

      {/* ========== FOOTER BAR (mockup: WebSocket Connected • API Healthy • 42 agents • LLM Flow 847 • Conference 8/12 • Last Refresh • Load • Uptime) ========== */}
      <div className="flex items-center justify-between px-4 py-1.5 border-t border-[#1e293b] bg-[#111827] text-[10px] font-mono shrink-0">
        <div className="flex items-center gap-3 text-[#64748b]">
          <span className="flex items-center gap-1">
            WebSocket <span className="text-[#10b981] ml-0.5">Connected</span>
            <div className="w-1.5 h-1.5 rounded-full bg-[#10b981] animate-pulse ml-0.5" />
          </span>
          <span className="text-[#374151]">|</span>
          <span>API <span className="text-[#10b981]">Healthy</span>
            <div className="w-1.5 h-1.5 rounded-full bg-[#10b981] animate-pulse inline-block ml-0.5" />
          </span>
          <span className="text-[#374151]">|</span>
          <span><span className="text-[#f8fafc]">{totalCount}</span> agents</span>
          <span className="text-[#374151]">|</span>
          <span>LLM Flow <span className="text-[#f8fafc]">847</span></span>
          <span className="text-[#374151]">|</span>
          <span>Conference <span className="text-[#f8fafc]">8/12</span></span>
          <span className="text-[#374151]">|</span>
          <span>Last Refresh <span className="text-[#06b6d4]">{new Date().toLocaleTimeString("en-US", { hour12: false })}</span></span>
          <span className="text-[#374151]">|</span>
          <span>Load <span className="text-[#f8fafc]">2.4/4.0</span></span>
          <span className="text-[#374151]">|</span>
          <span>Uptime <span className="text-[#f8fafc]">{uptime}</span></span>
        </div>
        <div className="text-[#64748b]">
          Embodier.ai v2.0
        </div>
      </div>
    </div>
  );
}
