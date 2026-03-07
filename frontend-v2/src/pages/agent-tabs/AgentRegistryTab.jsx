// AgentRegistryTab — matches mockup 05c-agent-registry.png
// Layout: Left 60% Master Agent Table, Right 40% Agent Inspector
// Bottom: Lifecycle Controls Bar
import React, { useState, useMemo } from "react";
import {
  Search, Filter, Play, Square, RefreshCw, Trash2, Eye,
  CheckCircle, XCircle, AlertTriangle, ChevronDown, Settings,
} from "lucide-react";
import { toast } from "react-toastify";
import { getApiUrl, getAuthHeaders } from "../../config/api";

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
  Running: "text-emerald-400",
  Stopped: "text-gray-500",
  Error: "text-red-400",
  Degraded: "text-amber-400",
};

const DEFAULT_AGENTS = [];

function AgentInspector({ agent }) {
  if (!agent) return (
    <div className="aurora-card p-4 flex items-center justify-center h-full">
      <span className="text-gray-500 text-xs">Select an agent to inspect</span>
    </div>
  );

  const shapFeatures = [
    { name: "Price Action", val: 77, color: "bg-cyan-500" },
    { name: "Vol Flow", val: 62, color: "bg-amber-500" },
    { name: "Regime Context", val: 45, color: "bg-purple-500" },
    { name: "Sentiment", val: 33, color: "bg-emerald-500" },
  ];

  return (
    <div className="aurora-card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-white">Agent Inspector: <span className="text-cyan-400">{agent.name}</span></h3>
          <span className={`text-[10px] px-2 py-0.5 rounded ${agent.status === "Running" ? "bg-emerald-500/20 text-emerald-400" : agent.status === "Error" ? "bg-red-500/20 text-red-400" : "bg-gray-700 text-gray-400"}`}>{agent.status}</span>
        </div>
        <div className="flex gap-2 text-[10px] text-gray-500">
          <span>PID: {1942 + agent.id}</span>
          <span>CPU: {agent.cpu}%</span>
          <span>MEM: {agent.mem}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Configuration */}
        <div>
          <h4 className="text-[10px] font-bold text-gray-400 uppercase mb-2">Configuration</h4>
          <div className="bg-[#0B0E14] rounded p-2 font-mono text-[9px] text-gray-400 space-y-0.5">
            <div>model: <span className="text-cyan-400">xgboost_v3</span></div>
            <div>features: <span className="text-white">price, volume</span></div>
            <div>risk_level: <span className="text-amber-400">medium</span></div>
            <div>entry_cond: <span className="text-white">score &gt; 0.72</span></div>
            <div>pnl_allocation: <span className="text-emerald-400">8%</span></div>
            <div>gpu_allocation: <span className="text-white">0.5</span></div>
          </div>
          <div className="flex gap-2 mt-2">
            <button className="px-2 py-1 text-[10px] bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded hover:brightness-125" onClick={async () => { if (!agent) return; try { await agentApi.updateConfig(agent.id, agent.config || {}); toast.success(`Config updated for ${agent.name}`); } catch (e) { toast.error(`Config update failed: ${e.message}`); } }}>Apply Changes</button>
            <button className="px-2 py-1 text-[10px] bg-gray-700 text-gray-300 border border-gray-600 rounded hover:brightness-125">Reset</button>
          </div>
        </div>
        {/* Performance Metrics */}
        <div>
          <h4 className="text-[10px] font-bold text-gray-400 uppercase mb-2">Performance Metrics</h4>
          <div className="space-y-1 text-[10px]">
            {[
              ["Requests/min", "847"],
              ["Avg Latency", agent.latency],
              ["Error Rate", `${agent.errorRate}%`],
              ["Success Rate", `${agent.successRate}%`],
              ["Tokens 24h", "189,400"],
              ["Queue Depth", `${agent.queueDepth}`],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <span className="text-gray-500">{k}:</span>
                <span className={k.includes("Error") ? "text-amber-400" : k.includes("Success") ? "text-emerald-400" : "text-white"}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Agent Logs mini */}
      <div>
        <h4 className="text-[10px] font-bold text-gray-400 uppercase mb-1">Agent Logs</h4>
        <div className="bg-[#0B0E14] rounded p-2 font-mono text-[9px] text-gray-500 max-h-[60px] overflow-y-auto">
          <div><span className="text-gray-600">09:41:23</span> <span className="text-cyan-400">{agent.name}</span> High-quality signal detected on AAPL — forwarding to council</div>
          <div><span className="text-gray-600">09:41:18</span> <span className="text-emerald-400">{agent.name}</span> Completed analysis cycle in {agent.latency}</div>
        </div>
      </div>

      {/* SHAP Feature Importance */}
      <div>
        <h4 className="text-[10px] font-bold text-gray-400 uppercase mb-1">SHAP Feature Importance</h4>
        <div className="space-y-1">
          {shapFeatures.map(f => (
            <div key={f.name} className="flex items-center gap-2 text-[10px]">
              <span className="w-20 text-gray-400">{f.name}</span>
              <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div className={`h-full ${f.color} rounded-full`} style={{ width: `${f.val}%` }} />
              </div>
              <span className="text-white w-6 text-right">{f.val}%</span>
            </div>
          ))}
        </div>
        <button className="text-[9px] text-cyan-400 hover:underline mt-1" onClick={() => toast.info("Opening Bayesian Weight matrices...")}>Bayesian Weights →</button>
      </div>

      {/* Donut gauge */}
      <div className="flex justify-center">
        <div className="relative w-16 h-16">
          <svg viewBox="0 0 36 36" className="w-16 h-16 -rotate-90">
            <circle cx="18" cy="18" r="14" fill="none" stroke="#1f2937" strokeWidth="3" />
            <circle cx="18" cy="18" r="14" fill="none" stroke="#10b981" strokeWidth="3" strokeDasharray={`${agent.successRate} ${100 - agent.successRate}`} strokeLinecap="round" />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-sm text-emerald-400 font-bold">{Math.round(agent.successRate)}%</span>
        </div>
      </div>
    </div>
  );
}

export default function AgentRegistryTab({ agents }) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [typeFilter, setTypeFilter] = useState("All Types");
  const [selected, setSelected] = useState(null);
  const [page, setPage] = useState(0);
  const perPage = 20;

  // Use real agents from props if provided, otherwise empty
  const agentList = Array.isArray(agents) ? agents : DEFAULT_AGENTS;

  const filtered = useMemo(() => {
    return agentList.filter(a => {
      if (search && !a.name.toLowerCase().includes(search.toLowerCase())) return false;
      if (statusFilter !== "All" && a.status !== statusFilter) return false;
      if (typeFilter !== "All Types" && a.type !== typeFilter) return false;
      return true;
    });
  }, [agentList, search, statusFilter, typeFilter]);

  const paged = filtered.slice(page * perPage, (page + 1) * perPage);
  const totalPages = Math.ceil(filtered.length / perPage);

  return (
    <div className="grid grid-cols-12 gap-3">
      {/* MASTER TABLE — left 7 cols */}
      <div className="col-span-7 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Master Agent Table</h3>
        {/* Toolbar */}
        <div className="flex items-center gap-2 mb-2">
          <div className="flex items-center gap-1 bg-[#0B0E14] border border-gray-700 rounded px-2 py-1 flex-1">
            <Search className="w-3 h-3 text-gray-500" />
            <input className="bg-transparent text-[10px] text-white outline-none flex-1 placeholder-gray-600" placeholder="Search agents..." value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          <div className="flex gap-1 text-[10px]">
            {["All", "Running", "Stopped", "Error"].map(s => (
              <button key={s} onClick={() => setStatusFilter(s)}
                className={`px-2 py-1 rounded border ${statusFilter === s ? "bg-cyan-500/20 text-cyan-400 border-cyan-500/30" : "bg-transparent text-gray-500 border-gray-700"}`}>
                {s}
              </button>
            ))}
          </div>
          <div className="flex gap-1">
            <button className="p-1 text-emerald-400 hover:bg-emerald-500/20 rounded" title="Bulk Start" onClick={async () => { try { await agentApi.batchStart(); toast.success("All agents starting"); } catch (e) { toast.error(`Bulk start failed: ${e.message}`); } }}><Play className="w-3.5 h-3.5" /></button>
            <button className="p-1 text-red-400 hover:bg-red-500/20 rounded" title="Bulk Restart" onClick={async () => { try { await agentApi.batchRestart(); toast.info("All agents restarting"); } catch (e) { toast.error(`Bulk restart failed: ${e.message}`); } }}><RefreshCw className="w-3.5 h-3.5" /></button>
            <button className="p-1 text-amber-400 hover:bg-amber-500/20 rounded" title="Bulk Stop" onClick={async () => { try { await agentApi.batchStop(); toast.warning("All agents stopping"); } catch (e) { toast.error(`Bulk stop failed: ${e.message}`); } }}><Square className="w-3.5 h-3.5" /></button>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto max-h-[420px] overflow-y-auto scrollbar-thin">
          <table className="w-full text-[10px]">
            <thead className="sticky top-0 bg-[#111827] z-10">
              <tr className="text-gray-500 border-b border-gray-700">
                {["Agent","Type","Status","CPU","MEM","Win%","PnL","ELO","Subs","Last Tick","Actions"].map(h => (
                  <th key={h} className={`py-1.5 font-medium ${h === "Agent" ? "text-left" : "text-right"} px-1`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paged.length === 0 && (
                <tr>
                  <td colSpan={11} className="px-4 py-8 text-center text-gray-500 text-xs">
                    No agents registered
                  </td>
                </tr>
              )}
              {paged.map(a => (
                <tr key={a.id}
                  className={`border-b border-gray-800/30 cursor-pointer transition-colors ${selected?.id === a.id ? "bg-cyan-500/10 border-l-2 border-l-cyan-500" : "hover:bg-cyan-500/5"}`}
                  onClick={() => setSelected(a)}>
                  <td className="py-1.5 px-1 text-left">
                    <div className="flex items-center gap-1.5">
                      <span className={`w-1.5 h-1.5 rounded-full ${a.status === "Running" ? "bg-emerald-500" : a.status === "Error" ? "bg-red-500" : "bg-gray-600"}`} />
                      <span className="text-white font-mono">{a.name}</span>
                    </div>
                  </td>
                  <td className="text-right px-1 text-gray-400">{a.type}</td>
                  <td className={`text-right px-1 ${STATUS_COLORS[a.status]}`}>{a.status}</td>
                  <td className={`text-right px-1 ${a.cpu > 80 ? "text-red-400" : a.cpu > 50 ? "text-amber-400" : "text-emerald-400"}`}>{a.cpu}%</td>
                  <td className="text-right px-1 text-white">{a.mem}</td>
                  <td className="text-right px-1 text-white">{a.winRate}%</td>
                  <td className={`text-right px-1 ${Number(a.pnl) >= 0 ? "text-emerald-400" : "text-red-400"}`}>${a.pnl}</td>
                  <td className="text-right px-1 text-white">{a.elo}</td>
                  <td className="text-right px-1 text-gray-400">{a.subscribers}</td>
                  <td className="text-right px-1 text-gray-500">{a.lastTick}</td>
                  <td className="text-right px-1">
                    <div className="flex gap-0.5 justify-end">
                      <button className="p-0.5 hover:text-cyan-400 text-gray-600" onClick={e => { e.stopPropagation(); setSelected(a); }}><Eye className="w-3 h-3" /></button>
                      <button className="p-0.5 hover:text-emerald-400 text-gray-600" onClick={async e => { e.stopPropagation(); try { if (a.status === "Running") { await agentApi.stop(a.id); toast.info(`Stopping ${a.name}`); } else { await agentApi.start(a.id); toast.success(`Starting ${a.name}`); } } catch (err) { toast.error(`Toggle failed: ${err.message}`); } }}><Play className="w-3 h-3" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between mt-2 text-[10px] text-gray-500">
          <span>{filtered.length} agents total</span>
          <div className="flex gap-1">
            {Array.from({ length: totalPages }, (_, i) => (
              <button key={i} onClick={() => setPage(i)}
                className={`px-1.5 py-0.5 rounded ${page === i ? "bg-cyan-500/20 text-cyan-400" : "hover:bg-gray-700 text-gray-500"}`}>
                {i + 1}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* AGENT INSPECTOR — right 5 cols */}
      <div className="col-span-5">
        <AgentInspector agent={selected} />

        {/* Lifecycle Controls Bar */}
        <div className="aurora-card p-3 mt-3">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Lifecycle Controls Bar</h3>
          <div className="flex items-center gap-3">
            <div className="relative w-12 h-12">
              <svg viewBox="0 0 36 36" className="w-12 h-12 -rotate-90">
                <circle cx="18" cy="18" r="14" fill="none" stroke="#1f2937" strokeWidth="3" />
                <circle cx="18" cy="18" r="14" fill="none" stroke="#10b981" strokeWidth="3" strokeDasharray="95 5" strokeLinecap="round" />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-[10px] text-emerald-400 font-bold">95%</span>
            </div>
            <div className="flex-1 space-y-1 text-[10px]">
              <div className="flex flex-wrap gap-1.5">
                {["Dependencies","AllocateRam","Memory","LitMake"].map(t => (
                  <span key={t} className="px-1.5 py-0.5 bg-gray-800 text-gray-400 rounded">{t}</span>
                ))}
              </div>
              <div className="flex items-center gap-3 text-gray-500">
                <span>Auto-Restart: <span className="text-emerald-400">ON</span></span>
                <span>Max Restarts: <span className="text-white">5</span></span>
                <span>Cooldown: <span className="text-white">30s</span></span>
              </div>
            </div>
            <button className="px-3 py-1.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded text-[10px] font-bold hover:brightness-125"
              onClick={async () => { try { await agentApi.batchStart(); toast.success("All agents spawning"); } catch (e) { toast.error(`Spawn failed: ${e.message}`); } }}>Spawn</button>
            <button className="px-3 py-1.5 bg-red-500/20 text-red-400 border border-red-500/30 rounded text-[10px] font-bold hover:brightness-125"
              onClick={async () => { try { await agentApi.batchStop(); toast.warning("All agents retiring"); } catch (e) { toast.error(`Retire failed: ${e.message}`); } }}>Retire</button>
          </div>
        </div>
      </div>
    </div>
  );
}
