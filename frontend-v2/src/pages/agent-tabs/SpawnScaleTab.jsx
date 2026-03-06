// SpawnScaleTab — matches mockup 05b-agent-command-center-spawn.png
// Layout: Top row (4 panels), NL Prompt + Quick Spawn Grid, Custom Builder + Active Spawned Table
import React, { useState } from "react";
import {
  Zap, Brain, Shield, Target, Eye, Activity, RefreshCw, Play, Square,
  TrendingUp, Radio, Server, Cpu, AlertTriangle, Settings, Search,
} from "lucide-react";
import { toast } from "react-toastify";

// --- Top 4 panels ---
function OrchestratorPanel() {
  const rows = [
    { name: "Scanner Fleet", count: 8, mem: "2.4GB", cpu: 34, status: "Active" },
    { name: "ML Pipeline", count: 4, mem: "6.1GB", cpu: 67, status: "Training" },
    { name: "Conference", count: 3, mem: "1.2GB", cpu: 12, status: "Idle" },
    { name: "Execution", count: 5, mem: "890MB", cpu: 45, status: "Active" },
  ];
  return (
    <div className="aurora-card p-3">
      <h3 className="text-[10px] font-bold text-white uppercase tracking-wider mb-2">Agent Spawn & Swarm Orchestrator</h3>
      <table className="w-full text-[9px]">
        <thead><tr className="text-gray-500 border-b border-gray-800">
          <th className="text-left py-1">Fleet</th><th className="text-right">Count</th><th className="text-right">MEM</th><th className="text-right">CPU</th><th className="text-right">Status</th>
        </tr></thead>
        <tbody>{rows.map(r => (
          <tr key={r.name} className="border-b border-gray-800/30">
            <td className="py-1 text-cyan-400">{r.name}</td>
            <td className="text-right text-white">{r.count}</td>
            <td className="text-right text-gray-400">{r.mem}</td>
            <td className={`text-right ${r.cpu > 60 ? "text-amber-400" : "text-emerald-400"}`}>{r.cpu}%</td>
            <td className={`text-right ${r.status === "Active" ? "text-emerald-400" : r.status === "Training" ? "text-purple-400" : "text-gray-500"}`}>{r.status}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function OpenClawControl() {
  return (
    <div className="aurora-card p-3">
      <h3 className="text-[10px] font-bold text-white uppercase tracking-wider mb-2">OpenClaw Swarm Control</h3>
      <div className="flex items-center gap-3 mb-2">
        <span className="text-[10px] text-gray-400">Regime:</span>
        <span className="text-[10px] text-emerald-400 font-bold">MOMENTUM</span>
      </div>
      <div className="relative w-20 h-20 mx-auto mb-2">
        <svg viewBox="0 0 36 36" className="w-20 h-20 -rotate-90">
          <circle cx="18" cy="18" r="14" fill="none" stroke="#1f2937" strokeWidth="4" />
          <circle cx="18" cy="18" r="14" fill="none" stroke="#06b6d4" strokeWidth="4" strokeDasharray="77 23" strokeLinecap="round" />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-sm text-cyan-400 font-bold">0.77</span>
      </div>
      <div className="text-center text-[9px] text-gray-500">Confidence</div>
      <div className="grid grid-cols-2 gap-1 mt-2 text-[9px]">
        <div className="text-gray-500">Walk Forward:</div><div className="text-emerald-400">Passed</div>
        <div className="text-gray-500">Regime Accuracy:</div><div className="text-white">84%</div>
      </div>
    </div>
  );
}

function MLEnginePanel() {
  return (
    <div className="aurora-card p-3">
      <h3 className="text-[10px] font-bold text-white uppercase tracking-wider mb-2">ML Engine & Flywheel</h3>
      <div className="space-y-1 text-[9px]">
        {[
          ["Active Models", "7", "text-white"],
          ["Walk Forward Accuracy", "82.3%", "text-emerald-400"],
          ["Training Queue", "3 jobs", "text-amber-400"],
          ["Last Epoch", "B47/1000", "text-cyan-400"],
          ["Val Loss", "0.0023", "text-emerald-400"],
          ["Feature Drift", "0.12 PSI", "text-white"],
        ].map(([k, v, c]) => (
          <div key={k} className="flex justify-between">
            <span className="text-gray-500">{k}</span>
            <span className={c}>{v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TradingConferencePanel() {
  return (
    <div className="aurora-card p-3">
      <h3 className="text-[10px] font-bold text-white uppercase tracking-wider mb-2">Trading Conference & Auto-Scale</h3>
      <div className="space-y-1 text-[9px]">
        {[
          ["Active Conferences", "2", "text-cyan-400"],
          ["Avg Duration", "4.2s", "text-white"],
          ["Auto-Scale Policy", "CPU > 80%", "text-amber-400"],
          ["Scale Cooldown", "60s", "text-gray-400"],
          ["Max Agents", "64", "text-white"],
          ["Current Load", "42/64", "text-emerald-400"],
        ].map(([k, v, c]) => (
          <div key={k} className="flex justify-between">
            <span className="text-gray-500">{k}</span>
            <span className={c}>{v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- NL Spawn Prompt ---
function NLSpawnPrompt() {
  const [prompt, setPrompt] = useState("Spawn a momentum scanner agent focused on NASDAQ small-caps with 30s interval, high sensitivity, connected to Alpaca and Finviz");
  return (
    <div className="aurora-card p-3">
      <h3 className="text-[10px] font-bold text-white uppercase tracking-wider mb-2">Natural Language Spawn Prompt</h3>
      <textarea
        className="w-full h-16 bg-[#0B0E14] border border-cyan-500/30 rounded p-2 text-[11px] text-cyan-400 font-mono outline-none resize-none focus:border-cyan-500/60"
        value={prompt}
        onChange={e => setPrompt(e.target.value)}
      />
      <button
        className="mt-2 px-4 py-2 bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 rounded font-bold text-xs hover:bg-cyan-500/30 transition-all w-full"
        onClick={() => toast.success("Executing spawn prompt...")}
      >
        [ EXECUTE PROMPT ]
      </button>
    </div>
  );
}

// --- Quick Spawn Template Grid ---
function QuickSpawnGrid() {
  const templates = [
    { name: "Momentum Scanner", icon: TrendingUp, color: "text-emerald-400 border-emerald-500/30" },
    { name: "Mean Reversion Hunter", icon: RefreshCw, color: "text-purple-400 border-purple-500/30" },
    { name: "Breakout Detector", icon: Zap, color: "text-amber-400 border-amber-500/30" },
    { name: "Arbitrage Sniffer", icon: Target, color: "text-cyan-400 border-cyan-500/30" },
    { name: "Sentiment Analyzer", icon: Brain, color: "text-blue-400 border-blue-500/30" },
    { name: "News Event Tracker", icon: Radio, color: "text-pink-400 border-pink-500/30" },
    { name: "Options Flow Reader", icon: Eye, color: "text-indigo-400 border-indigo-500/30" },
    { name: "Volume Profile Agent", icon: Activity, color: "text-orange-400 border-orange-500/30" },
    { name: "Correlation Mapper", icon: Server, color: "text-teal-400 border-teal-500/30" },
    { name: "Risk Sentinel", icon: Shield, color: "text-red-400 border-red-500/30" },
    { name: "Custom Agent", icon: Settings, color: "text-gray-400 border-gray-500/30" },
  ];
  return (
    <div className="aurora-card p-3">
      <h3 className="text-[10px] font-bold text-white uppercase tracking-wider mb-2">Quick Spawn Template Grid</h3>
      <div className="grid grid-cols-4 gap-2">
        {templates.map(t => (
          <button key={t.name}
            className={`flex flex-col items-center gap-1 p-2 rounded border bg-[#0B0E14]/50 hover:bg-cyan-500/10 transition-all ${t.color}`}
            onClick={() => toast.info(`Spawning ${t.name}...`)}>
            <t.icon className="w-4 h-4" />
            <span className="text-[8px] text-center leading-tight">{t.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// --- Custom Agent Builder ---
function CustomBuilder() {
  return (
    <div className="aurora-card p-3">
      <h3 className="text-[10px] font-bold text-white uppercase tracking-wider mb-2">Custom Agent Builder</h3>
      <div className="grid grid-cols-2 gap-2 text-[10px]">
        {[
          ["Agent Name", "input", "my_scanner_01"],
          ["Agent Type", "select", "Scanner"],
          ["Data Sources", "tags", "alpaca, finviz"],
          ["Target Symbols", "input", "NASDAQ"],
        ].map(([label, type, placeholder]) => (
          <div key={label}>
            <label className="text-gray-500 text-[9px]">{label}</label>
            <input className="w-full bg-[#0B0E14] border border-gray-700 rounded px-2 py-1 text-[10px] text-white outline-none mt-0.5" placeholder={placeholder} />
          </div>
        ))}
      </div>
      <div className="mt-2 space-y-1.5">
        <div className="text-[9px] text-gray-500">Risk Interval</div>
        <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <div className="h-full bg-cyan-500 rounded-full" style={{ width: "65%" }} />
        </div>
        <div className="text-[9px] text-gray-500">Kill Condition: <span className="text-white font-mono">loss_streak &gt; 5 || drawdown &gt; 0.15</span></div>
      </div>
    </div>
  );
}

// --- Active Spawned Agents Table ---
function ActiveSpawnedTable() {
  const spawned = [
    { name: "MomoScanner-01", type: "Scanner", status: "Running", cpu: 23, elo: 1834, spawn: "2024-03-01 12:34" },
    { name: "SentAnalyzer-02", type: "Sentiment", status: "Running", cpu: 45, elo: 1756, spawn: "2024-03-01 11:20" },
    { name: "BreakoutDet-01", type: "Detector", status: "Degraded", cpu: 78, elo: 1698, spawn: "2024-03-01 10:45" },
    { name: "RiskSentinel-03", type: "Risk", status: "Running", cpu: 12, elo: 1923, spawn: "2024-03-01 09:15" },
    { name: "FlowReader-01", type: "Options", status: "Running", cpu: 34, elo: 1812, spawn: "2024-03-01 08:30" },
  ];
  return (
    <div className="aurora-card p-3">
      <h3 className="text-[10px] font-bold text-white uppercase tracking-wider mb-2">Active Spawned Agents Table</h3>
      <table className="w-full text-[9px]">
        <thead><tr className="text-gray-500 border-b border-gray-800">
          <th className="text-left py-1">Name</th><th className="text-left">Type</th><th className="text-right">Status</th>
          <th className="text-right">CPU</th><th className="text-right">ELO</th><th className="text-right">Spawned</th>
          <th className="text-right">Actions</th>
        </tr></thead>
        <tbody>{spawned.map(s => (
          <tr key={s.name} className="border-b border-gray-800/30 hover:bg-cyan-500/5">
            <td className="py-1 text-cyan-400 font-mono">{s.name}</td>
            <td className="text-gray-400">{s.type}</td>
            <td className={`text-right ${s.status === "Running" ? "text-emerald-400" : "text-amber-400"}`}>{s.status}</td>
            <td className={`text-right ${s.cpu > 60 ? "text-amber-400" : "text-emerald-400"}`}>{s.cpu}%</td>
            <td className="text-right text-white">{s.elo}</td>
            <td className="text-right text-gray-500">{s.spawn}</td>
            <td className="text-right">
              <button className="text-red-400 hover:text-red-300 text-[9px]" onClick={() => toast.warning(`Killing ${s.name}`)}>Kill</button>
            </td>
          </tr>
        ))}</tbody>
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
