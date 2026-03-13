// AgentRegistryTab — matches mockup 05c-agent-registry.png
// Layout: Left 60% Master Agent Table, Right 40% Agent Inspector
// Bottom: Lifecycle Controls Bar. Override status/weight via useApi helpers.
import React, { useState, useMemo, useEffect } from "react";
import {
  Search, Filter, Play, Square, RefreshCw, Trash2, Eye,
  CheckCircle, XCircle, AlertTriangle, ChevronDown, Settings,
} from "lucide-react";
import { toast } from "react-toastify";
import { getApiUrl, getAuthHeaders } from "../../config/api";
import { postAgentOverrideStatus, postAgentOverrideWeight } from "../../hooks/useApi";

// ── Agent lifecycle API helpers ──────────────────────────────
const agentApi = {
  async start(agentId) {
    const res = await fetch(getApiUrl("agents") + `/${agentId}/start`, {
      method: "POST", headers: { ...getAuthHeaders() },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async stop(agentId) {
    const res = await fetch(getApiUrl("agents") + `/${agentId}/stop`, {
      method: "POST", headers: { ...getAuthHeaders() },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async restart(agentId) {
    const res = await fetch(getApiUrl("agents") + `/${agentId}/restart`, {
      method: "POST", headers: { ...getAuthHeaders() },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async updateConfig(agentId, config) {
    const res = await fetch(getApiUrl("agents") + `/${agentId}/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async batchStart() {
    const res = await fetch(getApiUrl("agents") + "/batch/start", {
      method: "POST", headers: { ...getAuthHeaders() },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async batchStop() {
    const res = await fetch(getApiUrl("agents") + "/batch/stop", {
      method: "POST", headers: { ...getAuthHeaders() },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async batchRestart() {
    const res = await fetch(getApiUrl("agents") + "/batch/restart", {
      method: "POST", headers: { ...getAuthHeaders() },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
};

const STATUS_COLORS = {
  Running: "text-[#10b981]",
  Stopped: "text-[#64748b]",
  Error: "text-[#ef4444]",
  Degraded: "text-[#f59e0b]",
};

// Agent type → design system badge color (spec)
const TYPE_COLORS = {
  Scanner: { bg: "#164e63", text: "#06b6d4" },
  Intelligence: { bg: "#1e3a8a", text: "#3b82f6" },
  Execution: { bg: "#4c1d95", text: "#8b5cf6" },
  Streaming: { bg: "#9a3412", text: "#f97316" },
  Sentiment: { bg: "#9d174d", text: "#ec4899" },
  MLearning: { bg: "#713f12", text: "#eab308" },
  Conference: { bg: "#064e3b", text: "#10b981" },
};
function getTypeStyle(type) {
  const t = (type || "").toLowerCase();
  for (const [key, style] of Object.entries(TYPE_COLORS)) {
    if (t.includes(key.toLowerCase())) return style;
  }
  return { bg: "#1e293b", text: "#94a3b8" };
}

function AgentInspector({ agent }) {
  if (!agent) return (
    <div className="bg-[#111827] border border-[#1e293b] rounded-md p-4 flex items-center justify-center h-full min-h-[200px]">
      <span className="text-[#64748b] text-xs font-mono">Select an agent to inspect</span>
    </div>
  );

  const shapFeatures = agent.shap_features ?? agent.attribution ?? [];
  const hasShap = Array.isArray(shapFeatures) && shapFeatures.length > 0;

  return (
    <div className="bg-[#111827] border border-[#1e293b] rounded-md p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-[#f8fafc]">Agent Inspector: <span className="text-[#06b6d4] font-mono">{agent.name}</span></h3>
          <span className="text-[10px] px-2 py-0.5 rounded-full uppercase font-semibold" style={{ backgroundColor: (agent.statusDisplay ?? agent.status) === "Running" ? "#10b98120" : (agent.statusDisplay ?? agent.status) === "Error" ? "#ef444420" : "#64748b40", color: (agent.statusDisplay ?? agent.status) === "Running" ? "#10b981" : (agent.statusDisplay ?? agent.status) === "Error" ? "#ef4444" : "#94a3b8" }}>{agent.statusDisplay ?? agent.status}</span>
        </div>
        <div className="flex gap-2 text-[10px] text-[#64748b] font-mono">
          <span>PID: {agent.pid ?? "—"}</span>
          <span>CPU: {agent.cpu != null ? `${agent.cpu}%` : agent.cpu_usage != null ? `${agent.cpu_usage}%` : agent.cpuPercent != null ? `${agent.cpuPercent}%` : "—"}</span>
          <span>MEM: {agent.mem ?? agent.memory_mb ?? agent.memoryMb ?? "—"}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Configuration */}
        <div>
          <h4 className="text-[10px] font-bold text-[#94a3b8] uppercase tracking-wider mb-2">Configuration</h4>
          <div className="bg-[#0f1219] border border-[#1e293b] rounded p-2 font-mono text-[9px] text-[#94a3b8] space-y-0.5 overflow-x-auto">
            {agent.config && typeof agent.config === "object" ? (
              Object.entries(agent.config).slice(0, 8).map(([k, v]) => (
                <div key={k}>{k}: <span className="text-[#06b6d4]">{typeof v === "object" ? JSON.stringify(v) : String(v)}</span></div>
              ))
            ) : (
              <pre className="text-[#64748b]">{JSON.stringify(agent.config ?? {}, null, 2).slice(0, 300)}</pre>
            )}
          </div>
          <div className="flex gap-2 mt-2">
            <button type="button" className="px-2 py-1 text-[10px] rounded cursor-pointer hover:opacity-90" style={{ backgroundColor: "#164e63", color: "#06b6d4", border: "1px solid #06b6d4" }} onClick={async () => { if (!agent) return; try { await agentApi.updateConfig(agent.id, agent.config || {}); toast.success(`Config updated for ${agent.name}`); } catch (e) { toast.error(`Config update failed: ${e.message}`); } }}>Apply Changes</button>
            <button type="button" className="px-2 py-1 text-[10px] bg-[#1e293b] text-[#94a3b8] border border-[#374151] rounded cursor-pointer hover:bg-[#374151]">Reset</button>
          </div>
        </div>
        {/* Performance Metrics */}
        <div>
          <h4 className="text-[10px] font-bold text-[#94a3b8] uppercase tracking-wider mb-2">Performance Metrics</h4>
          <div className="space-y-1 text-[10px] font-mono">
            {[
              ["Requests/min", agent.requests_per_min ?? "—"],
              ["Avg Latency", agent.latency ?? agent.latency_ms ?? "—"],
              ["Error Rate", agent.errorRate != null ? `${agent.errorRate}%` : "—"],
              ["Success Rate", agent.successRate != null ? `${agent.successRate}%` : "—"],
              ["Tokens 24h", agent.tokens_24h ?? agent.tokens ?? "—"],
              ["Queue Depth", agent.queueDepth ?? agent.queue_depth ?? "—"],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <span className="text-[#64748b]">{k}:</span>
                <span className={k.includes("Error") ? "text-[#f59e0b]" : k.includes("Success") ? "text-[#10b981]" : "text-[#f8fafc]"}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Agent Logs mini */}
      <div>
        <h4 className="text-[10px] font-bold text-[#94a3b8] uppercase mb-1">Agent Logs</h4>
        <div className="bg-[#0f1219] border border-[#1e293b] rounded p-2 font-mono text-[9px] text-[#64748b] max-h-[60px] overflow-y-auto">
          {agent.logs && agent.logs.length > 0 ? agent.logs.slice(0, 3).map((log, i) => (
            <div key={i}><span className="text-[#64748b]">{log.ts ?? "—"}</span> <span className="text-[#06b6d4]">{agent.name}</span> {log.msg ?? log.message ?? ""}</div>
          )) : (
            <div className="text-[#64748b]">No recent logs</div>
          )}
        </div>
      </div>

      {/* SHAP / Attribution — only when API provides agent.shap_features or agent.attribution */}
      {hasShap && (
        <div>
          <h4 className="text-[10px] font-bold text-[#94a3b8] uppercase mb-1">SHAP / Attribution</h4>
          <div className="space-y-1">
            {shapFeatures.slice(0, 8).map((f, i) => {
              const name = f.name ?? f.feature ?? `F${i + 1}`;
              const val = typeof f.val === "number" ? f.val : (f.value ?? 0);
              const pct = val <= 1 ? Math.round(val * 100) : Math.min(100, val);
              const color = f.color?.startsWith("#") ? f.color : "#06b6d4";
              return (
                <div key={name + i} className="flex items-center gap-2 text-[10px]">
                  <span className="w-20 text-[#94a3b8] truncate">{name}</span>
                  <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: "#1e293b" }}>
                    <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
                  </div>
                  <span className="text-[#f8fafc] w-6 text-right font-mono">{pct}%</span>
                </div>
              );
            })}
          </div>
          <button type="button" className="text-[9px] text-[#06b6d4] hover:text-[#22d3ee] cursor-pointer mt-1" onClick={() => toast.info("Opening Bayesian Weight matrices...")}>Bayesian Weights →</button>
        </div>
      )}

      {/* Donut gauge */}
      <div className="flex justify-center">
        <div className="relative w-16 h-16">
          <svg viewBox="0 0 36 36" className="w-16 h-16 -rotate-90">
            <circle cx="18" cy="18" r="14" fill="none" stroke="#1e293b" strokeWidth="3" />
            <circle cx="18" cy="18" r="14" fill="none" stroke="#10b981" strokeWidth="3" strokeDasharray={`${agent.successRate ?? 0} ${100 - (agent.successRate ?? 0)}`} strokeLinecap="round" />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-sm font-bold font-mono" style={{ color: "#10b981" }}>{Math.round(agent.successRate ?? 0)}%</span>
        </div>
      </div>

      {/* Lifecycle controls */}
      <div className="flex flex-wrap gap-2 pt-2 border-t border-[#1e293b]">
        <button type="button" className="px-2 py-1 text-[10px] rounded cursor-pointer bg-[#10b981]/20 text-[#10b981] border border-[#10b981]/40 hover:bg-[#10b981]/30" onClick={async () => { try { await agentApi.start(agent.id); toast.success(`Started ${agent.name}`); } catch (e) { toast.error(e?.message); } }}>Start</button>
        <button type="button" className="px-2 py-1 text-[10px] rounded cursor-pointer bg-[#f59e0b]/20 text-[#f59e0b] border border-[#f59e0b]/40 hover:bg-[#f59e0b]/30" onClick={async () => { try { await agentApi.stop(agent.id); toast.info(`Stopped ${agent.name}`); } catch (e) { toast.error(e?.message); } }}>Stop</button>
        <button type="button" className="px-2 py-1 text-[10px] rounded cursor-pointer bg-[#06b6d4]/20 text-[#06b6d4] border border-[#06b6d4]/40 hover:bg-[#06b6d4]/30" onClick={async () => { try { await agentApi.restart(agent.id); toast.success(`Restarted ${agent.name}`); } catch (e) { toast.error(e?.message); } }}>Restart</button>
        <button type="button" className="px-2 py-1 text-[10px] rounded cursor-pointer bg-[#ef4444]/20 text-[#ef4444] border border-[#ef4444]/40 hover:bg-[#ef4444]/30" onClick={() => toast.warning("Delete requires confirmation.")}>Delete</button>
      </div>

      {/* Council override: enable/disable + weight (alpha, beta) — wired to postAgentOverrideStatus / postAgentOverrideWeight */}
      <AgentCouncilOverride agent={agent} />
    </div>
  );
}

function AgentCouncilOverride({ agent }) {
  const [alpha, setAlpha] = useState(agent?.alpha ?? agent?.weight ?? 1);
  const [beta, setBeta] = useState(agent?.beta ?? 1);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    setAlpha(agent?.alpha ?? agent?.weight ?? 1);
    setBeta(agent?.beta ?? 1);
  }, [agent?.name, agent?.alpha, agent?.beta, agent?.weight]);

  if (!agent) return null;
  const agentName = agent.name ?? agent.agent_name ?? agent.id;

  const handleStatus = async (action) => {
    setLoading(true);
    try {
      await postAgentOverrideStatus(agentName, action);
      toast.success(`Agent override: ${action}`);
    } catch (e) {
      toast.error(`Override failed: ${e?.message ?? "network error"}`);
    } finally {
      setLoading(false);
    }
  };

  const handleWeight = async () => {
    const a = Number(alpha);
    const b = Number(beta);
    if (Number.isNaN(a) || Number.isNaN(b) || a < 0 || b < 0) {
      toast.error("Alpha and beta must be non-negative numbers");
      return;
    }
    setLoading(true);
    try {
      await postAgentOverrideWeight(agentName, a, b);
      toast.success("Weight override saved");
    } catch (e) {
      toast.error(`Weight override failed: ${e?.message ?? "network error"}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-3 pt-3 border-t border-[#1e293b]">
      <h4 className="text-[10px] font-bold text-[#94a3b8] uppercase mb-2">Council Override</h4>
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" disabled={loading} className="px-2 py-1 text-[10px] rounded cursor-pointer bg-[#10b981]/20 text-[#10b981] border border-[#10b981]/40 hover:bg-[#10b981]/30 disabled:opacity-50" onClick={() => handleStatus("enable")}>Enable</button>
        <button type="button" disabled={loading} className="px-2 py-1 text-[10px] rounded cursor-pointer bg-[#64748b]/20 text-[#94a3b8] border border-[#64748b]/40 hover:bg-[#64748b]/30 disabled:opacity-50" onClick={() => handleStatus("disable")}>Disable</button>
        <span className="text-[9px] text-[#64748b] font-mono">α</span>
        <input type="number" min={0} step={0.1} value={alpha} onChange={e => setAlpha(e.target.value)} className="w-14 bg-[#0f1219] border border-[#1e293b] rounded px-1 py-0.5 text-[10px] font-mono text-[#f8fafc]" />
        <span className="text-[9px] text-[#64748b] font-mono">β</span>
        <input type="number" min={0} step={0.1} value={beta} onChange={e => setBeta(e.target.value)} className="w-14 bg-[#0f1219] border border-[#1e293b] rounded px-1 py-0.5 text-[10px] font-mono text-[#f8fafc]" />
        <button type="button" disabled={loading} className="px-2 py-1 text-[10px] rounded cursor-pointer bg-[#06b6d4]/20 text-[#06b6d4] border border-[#06b6d4]/40 hover:bg-[#06b6d4]/30 disabled:opacity-50" onClick={handleWeight}>Set weight</button>
      </div>
    </div>
  );
}

export default function AgentRegistryTab({ agents, preselectedAgentName, onClearPreselection }) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [typeFilter, setTypeFilter] = useState("All Types");
  const [selected, setSelected] = useState(null);
  const [page, setPage] = useState(0);
  const perPage = 20;

  // Use real agents from props only — no mock data
  const agentList = Array.isArray(agents) ? agents : [];

  // When navigating from Overview (click on health matrix dot), select the agent
  useEffect(() => {
    if (!preselectedAgentName || agentList.length === 0) return;
    const match = agentList.find(a => {
      const n = (a.name ?? a.agent_name ?? "").toString().toLowerCase();
      const p = preselectedAgentName.toString().toLowerCase();
      return n === p || n.includes(p) || p.includes(n);
    });
    if (match) {
      setSelected(match);
      setPage(0);
    }
    onClearPreselection?.();
  }, [preselectedAgentName, agentList.length]);

  const typeOptions = useMemo(() => {
    const set = new Set(agentList.map(a => a.type).filter(Boolean));
    return ["All Types", ...Array.from(set).sort()];
  }, [agentList]);

  const filtered = useMemo(() => {
    return agentList.filter(a => {
      const name = (a.name ?? a.agent_name ?? "").toString();
      if (search && !name.toLowerCase().includes(search.toLowerCase())) return false;
      const displayStatus = (a.statusDisplay ?? a.status ?? "").toString().toLowerCase();
      if (statusFilter !== "All" && displayStatus !== statusFilter.toLowerCase()) return false;
      if (typeFilter !== "All Types" && (a.type ?? "") !== typeFilter) return false;
      return true;
    });
  }, [agentList, search, statusFilter, typeFilter]);

  const paged = filtered.slice(page * perPage, (page + 1) * perPage);
  const totalPages = Math.ceil(filtered.length / perPage);

  const tableColumns = ["Agent", "Type", "Status", "Health", "CPU%", "RAM%", "GPU%", "ELO", "Win%", "Sharpe", "Last Heartbeat", "Uptime", "Version", "Subs", "PnL", "Latency", "Tokens", "Actions"];

  return (
    <div className="grid grid-cols-12 gap-3">
      {/* MASTER TABLE — left 7 cols */}
      <div className="col-span-7 bg-[#111827] border border-[#1e293b] rounded-md p-3">
        <h3 className="text-xs font-bold text-[#94a3b8] uppercase tracking-wider mb-2 font-mono">Master Agent Table</h3>
        <div className="flex items-center gap-2 mb-2">
          <div className="flex items-center gap-1 bg-[#0f1219] border border-[#1e293b] rounded px-2 py-1 flex-1">
            <Search className="w-3 h-3 text-[#64748b]" />
            <input className="bg-transparent text-[10px] text-[#f8fafc] outline-none flex-1 placeholder-[#64748b] font-mono" placeholder="Search agents..." value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          <div className="flex gap-1 text-[10px]">
            {["All", "Running", "Stopped", "Error"].map(s => (
              <button key={s} type="button" onClick={() => setStatusFilter(s)}
                className={`px-2 py-1 rounded border cursor-pointer font-mono ${statusFilter === s ? "bg-[#164e63] text-[#06b6d4] border-[#06b6d4]/50" : "bg-transparent text-[#64748b] border-[#1e293b] hover:text-[#94a3b8]"}`}>
                {s}
              </button>
            ))}
            <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="bg-[#0f1219] border border-[#1e293b] rounded px-2 py-1 text-[10px] text-[#f8fafc] font-mono cursor-pointer max-w-[120px]">
              {typeOptions.map(t => (<option key={t} value={t}>{t}</option>))}
            </select>
          </div>
          <div className="flex gap-1">
            <button type="button" className="p-1 text-[#10b981] hover:bg-[#10b981]/20 rounded cursor-pointer" title="Bulk Start" onClick={async () => { try { await agentApi.batchStart(); toast.success("All agents starting"); } catch (e) { toast.error(`Bulk start failed: ${e.message}`); } }}><Play className="w-3.5 h-3.5" /></button>
            <button type="button" className="p-1 text-[#06b6d4] hover:bg-[#06b6d4]/20 rounded cursor-pointer" title="Bulk Restart" onClick={async () => { try { await agentApi.batchRestart(); toast.info("All agents restarting"); } catch (e) { toast.error(`Bulk restart failed: ${e.message}`); } }}><RefreshCw className="w-3.5 h-3.5" /></button>
            <button type="button" className="p-1 text-[#f59e0b] hover:bg-[#f59e0b]/20 rounded cursor-pointer" title="Bulk Stop" onClick={async () => { try { await agentApi.batchStop(); toast.warning("All agents stopping"); } catch (e) { toast.error(`Bulk stop failed: ${e.message}`); } }}><Square className="w-3.5 h-3.5" /></button>
          </div>
        </div>

        <div className="overflow-x-auto max-h-[420px] overflow-y-auto scrollbar-thin">
          <table className="w-full text-[10px] font-mono">
            <thead className="sticky top-0 bg-[#111827] z-10 border-b border-[#1e293b]">
              <tr className="text-[#94a3b8]">
                {tableColumns.map(h => (
                  <th key={h} className={`py-1.5 font-medium text-[10px] uppercase whitespace-nowrap px-1 ${h === "Agent" ? "text-left" : "text-right"}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paged.length === 0 ? (
                <tr>
                  <td colSpan={tableColumns.length} className="px-4 py-8 text-center text-[#64748b] text-xs font-mono">
                    No agents registered
                  </td>
                </tr>
              ) : paged.map(a => {
                const typeStyle = getTypeStyle(a.type);
                const status = a.statusDisplay ?? a.status;
                const dotColor = status === "Running" ? "#10b981" : status === "Error" ? "#ef4444" : status === "Degraded" ? "#f59e0b" : "#64748b";
                return (
                  <tr key={a.id}
                    className={`border-b border-[#1e293b]/50 cursor-pointer transition-colors ${selected?.id === a.id ? "bg-[#164e63]/20 border-l-2 border-l-[#06b6d4]" : "hover:bg-[#1e293b]"}`}
                    onClick={() => setSelected(a)}>
                    <td className="py-1.5 px-1 text-left">
                      <div className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: dotColor }} />
                        <span className="text-[#f8fafc] font-mono truncate max-w-[100px]">{a.name}</span>
                      </div>
                    </td>
                    <td className="text-right px-1">
                      <span className="px-1.5 py-0.5 rounded-full text-[9px] font-semibold uppercase" style={{ backgroundColor: typeStyle.bg, color: typeStyle.text }}>{a.type || "—"}</span>
                    </td>
                    <td className={`text-right px-1 ${STATUS_COLORS[status] || "text-[#94a3b8]"}`}>{status}</td>
                    <td className="text-right px-1 text-[#94a3b8]">{a.health ?? "—"}</td>
                    <td className="text-right px-1 text-[#f8fafc]">{a.cpu ?? a.cpu_usage ?? a.cpuPercent ?? "—"}%</td>
                    <td className="text-right px-1 text-[#f8fafc]">{a.mem ?? a.memory_mb ?? a.memoryMb ?? "—"}</td>
                    <td className="text-right px-1 text-[#f8fafc]">{a.gpu ?? a.gpu_percent ?? "—"}%</td>
                    <td className="text-right px-1 text-[#f8fafc]">{a.elo ?? "—"}</td>
                    <td className="text-right px-1 text-[#f8fafc]">{a.winRate ?? "—"}%</td>
                    <td className="text-right px-1 text-[#f8fafc]">{a.sharpe ?? "—"}</td>
                    <td className="text-right px-1 text-[#64748b]">{a.last_heartbeat ?? a.lastHeartbeat ?? "—"}</td>
                    <td className="text-right px-1 text-[#64748b]">{a.uptime ?? "—"}</td>
                    <td className="text-right px-1 text-[#94a3b8]">{a.version ?? "—"}</td>
                    <td className="text-right px-1 text-[#94a3b8]">{a.subscribers ?? "—"}</td>
                    <td className={`text-right px-1 ${Number(a.pnl) >= 0 ? "text-[#10b981]" : "text-[#ef4444]"}`}>{a.pnl != null ? `$${a.pnl}` : "—"}</td>
                    <td className="text-right px-1 text-[#94a3b8]">{a.latency ?? a.latency_ms ?? "—"}</td>
                    <td className="text-right px-1 text-[#94a3b8]">{a.tokens ?? a.tokens_24h ?? "—"}</td>
                    <td className="text-right px-1">
                      <div className="flex gap-0.5 justify-end">
                        <button type="button" className="p-0.5 hover:text-[#06b6d4] text-[#64748b] cursor-pointer" onClick={e => { e.stopPropagation(); setSelected(a); }}><Eye className="w-3 h-3" /></button>
                        <button type="button" className="p-0.5 hover:text-[#10b981] text-[#64748b] cursor-pointer" onClick={async e => { e.stopPropagation(); try { if (status === "Running") { await agentApi.stop(a.id); toast.info(`Stopping ${a.name}`); } else { await agentApi.start(a.id); toast.success(`Starting ${a.name}`); } } catch (err) { toast.error(`Toggle failed: ${err.message}`); } }}><Play className="w-3 h-3" /></button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between mt-2 text-[10px] text-[#64748b] font-mono">
          <span>{filtered.length} agents total</span>
          <div className="flex gap-1">
            {Array.from({ length: totalPages }, (_, i) => (
              <button key={i} type="button" onClick={() => setPage(i)}
                className={`px-1.5 py-0.5 rounded cursor-pointer ${page === i ? "bg-[#164e63] text-[#06b6d4]" : "hover:bg-[#1e293b] text-[#64748b]"}`}>
                {i + 1}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* AGENT INSPECTOR — right 5 cols */}
      <div className="col-span-5">
        <AgentInspector agent={selected} />
        <div className="bg-[#111827] border border-[#1e293b] rounded-md p-3 mt-3">
          <h3 className="text-xs font-bold text-[#94a3b8] uppercase tracking-wider mb-2 font-mono">Lifecycle Controls</h3>
          <div className="flex items-center gap-3 flex-wrap">
            <button type="button" className="px-3 py-1.5 rounded text-[10px] font-bold cursor-pointer bg-[#10b981]/20 text-[#10b981] border border-[#10b981]/40 hover:bg-[#10b981]/30"
              onClick={async () => { try { await agentApi.batchStart(); toast.success("All agents spawning"); } catch (e) { toast.error(`Spawn failed: ${e.message}`); } }}>Spawn</button>
            <button type="button" className="px-3 py-1.5 rounded text-[10px] font-bold cursor-pointer bg-[#ef4444]/20 text-[#ef4444] border border-[#ef4444]/40 hover:bg-[#ef4444]/30"
              onClick={async () => { try { await agentApi.batchStop(); toast.warning("All agents retiring"); } catch (e) { toast.error(`Retire failed: ${e.message}`); } }}>Retire</button>
          </div>
        </div>
      </div>
    </div>
  );
}

