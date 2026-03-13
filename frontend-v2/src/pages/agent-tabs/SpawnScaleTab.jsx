// SpawnScaleTab — matches mockup 05b-agent-command-center-spawn.png
import React, { useState, useMemo } from "react";
import {
  Zap, Brain, Shield, Target, Eye, Activity, RefreshCw, Play, Square,
  TrendingUp, Radio, Server, Cpu, AlertTriangle, Settings, Search,
} from "lucide-react";
import { toast } from "react-toastify";
import { useApi } from "../../hooks/useApi";

const CARD_CLASS = "bg-[#111827] border border-[#1e293b] rounded-md p-3";
const HEADER_CLASS = "text-[10px] font-bold text-[#94a3b8] uppercase tracking-wider mb-2 font-mono";

function OrchestratorPanel() {
  const { data: resources } = useApi("agentResources", { pollIntervalMs: 20000 });
  const { data: teams } = useApi("teams", { pollIntervalMs: 20000 });
  const rows = useMemo(() => {
    if (Array.isArray(resources)) return resources;
    if (resources?.fleets) return resources.fleets;
    if (Array.isArray(teams)) return teams.map(t => ({ name: t.name, count: t.agents ?? 0, mem: "—", cpu: t.health ?? 0, status: t.status ?? "—" }));
    return [];
  }, [resources, teams]);
  return (
    <div className={CARD_CLASS}>
      <h3 className={HEADER_CLASS}>Agent Spawn & Swarm Orchestrator</h3>
      <table className="w-full text-[9px] font-mono">
        <thead><tr className="text-[#94a3b8] border-b border-[#1e293b]">
          <th className="text-left py-1">Fleet</th><th className="text-right">Count</th><th className="text-right">MEM</th><th className="text-right">CPU</th><th className="text-right">Status</th>
        </tr></thead>
        <tbody>
          {rows.length === 0 ? (
            <tr><td colSpan={5} className="py-3 text-center text-[#64748b]">No fleet data</td></tr>
          ) : rows.map(r => (
            <tr key={r.name} className="border-b border-[#1e293b]/50 hover:bg-[#1e293b]">
              <td className="py-1 text-[#06b6d4]">{r.name}</td>
              <td className="text-right text-[#f8fafc]">{r.count}</td>
              <td className="text-right text-[#94a3b8]">{r.mem ?? "—"}</td>
              <td className={`text-right ${(r.cpu ?? 0) > 60 ? "text-[#f59e0b]" : "text-[#10b981]"}`}>{r.cpu ?? 0}%</td>
              <td className={`text-right ${r.status === "Active" ? "text-[#10b981]" : r.status === "Training" ? "text-[#8b5cf6]" : "text-[#64748b]"}`}>{r.status ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OpenClawControl() {
  const { data: regime } = useApi("openclaw/regime", { pollIntervalMs: 20000 });
  const conf = regime?.confidence ?? regime?.confidence_score ?? 0.77;
  const regimeName = regime?.regime ?? regime?.current ?? "MOMENTUM";
  return (
    <div className={CARD_CLASS}>
      <h3 className={HEADER_CLASS}>OpenClaw Swarm Control</h3>
      <div className="flex items-center gap-3 mb-2">
        <span className="text-[10px] text-[#64748b]">Regime:</span>
        <span className="text-[10px] text-[#10b981] font-bold font-mono">{String(regimeName).toUpperCase()}</span>
      </div>
      <div className="relative w-20 h-20 mx-auto mb-2">
        <svg viewBox="0 0 36 36" className="w-20 h-20 -rotate-90">
          <circle cx="18" cy="18" r="14" fill="none" stroke="#1e293b" strokeWidth="4" />
          <circle cx="18" cy="18" r="14" fill="none" stroke="#06b6d4" strokeWidth="4" strokeDasharray={`${conf * 100} ${100 - conf * 100}`} strokeLinecap="round" />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-sm font-bold font-mono text-[#06b6d4]">{typeof conf === "number" ? conf.toFixed(2) : conf}</span>
      </div>
      <div className="text-center text-[9px] text-[#64748b]">Confidence</div>
      <div className="grid grid-cols-2 gap-1 mt-2 text-[9px] font-mono">
        <div className="text-[#64748b]">Walk Forward:</div><div className="text-[#10b981]">{regime?.walk_forward ?? "—"}</div>
        <div className="text-[#64748b]">Regime Accuracy:</div><div className="text-[#f8fafc]">{regime?.accuracy != null ? `${regime.accuracy}%` : "—"}</div>
      </div>
    </div>
  );
}

function MLEnginePanel() {
  const { data: models } = useApi("ml-brain/models", { pollIntervalMs: 30000 });
  const { data: training } = useApi("training", { pollIntervalMs: 30000 });
  const modelCount = Array.isArray(models) ? models.length : (models?.length ?? models?.count ?? "—");
  const trainingQueue = training?.queue_length ?? training?.jobs ?? "—";
  const lastEpoch = training?.last_epoch ?? training?.epoch ?? "—";
  const valLoss = training?.val_loss ?? training?.loss ?? "—";
  return (
    <div className={CARD_CLASS}>
      <h3 className={HEADER_CLASS}>ML Engine & Flywheel</h3>
      <div className="space-y-1 text-[9px] font-mono">
        <div className="flex justify-between"><span className="text-[#64748b]">Active Models</span><span className="text-[#f8fafc]">{modelCount}</span></div>
        <div className="flex justify-between"><span className="text-[#64748b]">Training Queue</span><span className="text-[#f59e0b]">{trainingQueue} jobs</span></div>
        <div className="flex justify-between"><span className="text-[#64748b]">Last Epoch</span><span className="text-[#06b6d4]">{lastEpoch}</span></div>
        <div className="flex justify-between"><span className="text-[#64748b]">Val Loss</span><span className="text-[#10b981]">{typeof valLoss === "number" ? valLoss.toFixed(4) : valLoss}</span></div>
      </div>
    </div>
  );
}

function TradingConferencePanel() {
  const { data: conference } = useApi("conference", { pollIntervalMs: 20000 });
  const activeCount = conference?.active_count ?? conference?.count ?? "—";
  const avgDuration = conference?.avg_duration ?? conference?.duration_s ?? "—";
  return (
    <div className={CARD_CLASS}>
      <h3 className={HEADER_CLASS}>Trading Conference & Auto-Scale</h3>
      <div className="space-y-1 text-[9px] font-mono">
        <div className="flex justify-between"><span className="text-[#64748b]">Active Conferences</span><span className="text-[#06b6d4]">{activeCount}</span></div>
        <div className="flex justify-between"><span className="text-[#64748b]">Avg Duration</span><span className="text-[#f8fafc]">{avgDuration}</span></div>
        <div className="flex justify-between"><span className="text-[#64748b]">Max Agents</span><span className="text-[#f8fafc]">{conference?.max_agents ?? "—"}</span></div>
      </div>
    </div>
  );
}

function NLSpawnPrompt() {
  const [prompt, setPrompt] = useState("");
  return (
    <div className={CARD_CLASS}>
      <h3 className={HEADER_CLASS}>Natural Language Spawn Prompt</h3>
      <textarea
        className="w-full h-16 bg-[#0f1219] border border-[#06b6d4]/30 rounded p-2 text-[11px] text-[#06b6d4] font-mono outline-none resize-none focus:border-[#06b6d4]"
        placeholder="Describe the agent you want..."
        value={prompt}
        onChange={e => setPrompt(e.target.value)}
      />
      <button
        type="button"
        className="mt-2 px-4 py-2 rounded font-bold text-xs w-full cursor-pointer bg-[#164e63] text-[#06b6d4] border border-[#06b6d4]/50 hover:bg-[#164e63]/80"
        onClick={() => toast.info("Spawn & scale APIs coming soon.")}
      >
        [ EXECUTE PROMPT ]
      </button>
    </div>
  );
}

function QuickSpawnGrid() {
  const templates = [
    { name: "Scanner", icon: TrendingUp, color: "#06b6d4", bg: "#164e63" },
    { name: "Intelligence", icon: Brain, color: "#3b82f6", bg: "#1e3a8a" },
    { name: "Execution", icon: Zap, color: "#8b5cf6", bg: "#4c1d95" },
    { name: "Streaming", icon: Radio, color: "#f97316", bg: "#9a3412" },
    { name: "Sentiment", icon: Activity, color: "#ec4899", bg: "#9d174d" },
    { name: "MLearning", icon: Cpu, color: "#eab308", bg: "#713f12" },
    { name: "Conference", icon: Server, color: "#10b981", bg: "#064e3b" },
    { name: "Custom", icon: Settings, color: "#94a3b8", bg: "#1e293b" },
  ];
  return (
    <div className={CARD_CLASS}>
      <h3 className={HEADER_CLASS}>Template Grid</h3>
      <div className="grid grid-cols-4 gap-2">
        {templates.map(t => (
          <button
            key={t.name}
            type="button"
            className="flex flex-col items-center gap-1 p-2.5 rounded-md border bg-[#0f1219] hover:bg-[#1e293b] transition-all cursor-pointer font-mono"
            style={{ borderColor: `${t.color}50` }}
            onClick={() => toast.info("Select template then use Custom Builder or Spawn prompt.")}
          >
            <t.icon className="w-4 h-4 shrink-0" style={{ color: t.color }} />
            <span className="text-[9px] text-center leading-tight font-semibold uppercase tracking-wider" style={{ color: t.color }}>{t.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

const AGENT_TYPES = ["Scanner", "Intelligence", "Execution", "Streaming", "Sentiment", "MLearning", "Conference"];

function CustomBuilder() {
  const [name, setName] = useState("");
  const [type, setType] = useState("Scanner");
  const [configJson, setConfigJson] = useState("{\n  \"enabled\": true,\n  \"threshold\": 0.65\n}");

  return (
    <div className={CARD_CLASS}>
      <h3 className={HEADER_CLASS}>Custom Agent Builder</h3>
      <div className="grid grid-cols-2 gap-2 text-[10px]">
        <div>
          <label className="text-[#64748b] text-[9px] uppercase tracking-wider font-mono">Agent Name</label>
          <input className="w-full bg-[#0f1219] border border-[#1e293b] rounded px-2 py-1 text-[10px] text-[#f8fafc] font-mono outline-none mt-0.5 placeholder-[#64748b] focus:border-[#06b6d4]/50" placeholder="e.g. my-scanner" value={name} onChange={e => setName(e.target.value)} />
        </div>
        <div>
          <label className="text-[#64748b] text-[9px] uppercase tracking-wider font-mono">Agent Type</label>
          <select className="w-full bg-[#0f1219] border border-[#1e293b] rounded px-2 py-1 text-[10px] text-[#f8fafc] font-mono outline-none mt-0.5 cursor-pointer focus:border-[#06b6d4]/50" value={type} onChange={e => setType(e.target.value)}>
            {AGENT_TYPES.map(t => (<option key={t} value={t}>{t}</option>))}
          </select>
        </div>
      </div>
      <div className="mt-2">
        <label className="text-[#64748b] text-[9px] uppercase tracking-wider font-mono block mb-1">Config JSON</label>
        <textarea className="w-full min-h-[80px] bg-[#0f1219] border border-[#1e293b] rounded px-2 py-1.5 text-[9px] text-[#94a3b8] font-mono outline-none resize-y focus:border-[#06b6d4]/50 placeholder-[#64748b]" placeholder="{}" value={configJson} onChange={e => setConfigJson(e.target.value)} spellCheck={false} />
      </div>
      <button type="button" className="mt-2 px-3 py-1.5 text-[10px] font-bold rounded border cursor-pointer bg-[#164e63] text-[#06b6d4] border-[#06b6d4]/50 hover:bg-[#164e63]/80 font-mono" onClick={() => toast.info("Spawn API will use Agent Registry.")}>Apply & Spawn</button>
    </div>
  );
}

function ActiveSpawnedTable() {
  const { data: agents } = useApi("agents", { pollIntervalMs: 15000 });
  const spawned = useMemo(() => {
    if (!Array.isArray(agents)) return [];
    return agents.filter(a => (a.status ?? a.statusDisplay) === "Running" || (a.status ?? a.statusDisplay) === "running").map(a => ({
      name: a.name ?? a.agent_name,
      type: a.type ?? "—",
      status: a.status ?? a.statusDisplay ?? "—",
      cpu: a.cpu ?? a.cpu_usage ?? 0,
      elo: a.elo ?? "—",
      spawn: a.last_heartbeat ?? a.started_at ?? "—",
      id: a.id,
    }));
  }, [agents]);
  return (
    <div className={CARD_CLASS}>
      <h3 className={HEADER_CLASS}>Active Spawned Agents</h3>
      <table className="w-full text-[9px] font-mono">
        <thead><tr className="text-[#94a3b8] border-b border-[#1e293b]">
          <th className="text-left py-1">Name</th><th className="text-left">Type</th><th className="text-right">Status</th>
          <th className="text-right">CPU</th><th className="text-right">ELO</th><th className="text-right">Spawned</th>
          <th className="text-right">Actions</th>
        </tr></thead>
        <tbody>
          {spawned.length === 0 ? (
            <tr><td colSpan={7} className="py-3 text-center text-[#64748b]">No active agents</td></tr>
          ) : spawned.map(s => (
            <tr key={s.id ?? s.name} className="border-b border-[#1e293b]/50 hover:bg-[#1e293b]">
              <td className="py-1 text-[#06b6d4]">{s.name}</td>
              <td className="text-[#94a3b8]">{s.type}</td>
              <td className={`text-right ${s.status === "Running" ? "text-[#10b981]" : "text-[#f59e0b]"}`}>{s.status}</td>
              <td className={`text-right ${(s.cpu ?? 0) > 60 ? "text-[#f59e0b]" : "text-[#10b981]"}`}>{s.cpu}%</td>
              <td className="text-right text-[#f8fafc]">{s.elo}</td>
              <td className="text-right text-[#64748b]">{s.spawn}</td>
              <td className="text-right">
                <button type="button" className="text-[#ef4444] hover:text-[#f87171] text-[9px] cursor-pointer" onClick={() => toast.warning(`Kill ${s.name} — use Agent Registry.`)}>Kill</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// === MAIN TAB ===
export default function SpawnScaleTab() {
  return (
    <div className="space-y-3">
      {/* Top 4 panels */}
      <div className="grid grid-cols-4 gap-3">
        <OrchestratorPanel />
        <OpenClawControl />
        <MLEnginePanel />
        <TradingConferencePanel />
      </div>
      {/* NL Prompt + Template Grid */}
      <div className="grid grid-cols-2 gap-3">
        <NLSpawnPrompt />
        <QuickSpawnGrid />
      </div>
      {/* Custom Builder + Active Table */}
      <div className="grid grid-cols-2 gap-3">
        <CustomBuilder />
        <ActiveSpawnedTable />
      </div>
    </div>
  );
}
