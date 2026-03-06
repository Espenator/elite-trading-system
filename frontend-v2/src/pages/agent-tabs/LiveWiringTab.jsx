// LiveWiringTab — matches mockup 05-agent-command-center.png
// Layout: 5-column architecture diagram showing data flow
// External Sources → Agent → Processing Engines → Storage/Databases → Frontend/Interfaces
// Right sidebar: Connection Health Matrix, Traffic Node Discovery, WebSocket Channels, API Route Status
import React from "react";
import {
  Globe, Database, Server, Monitor, Cpu, Radio, Wifi, Activity,
  ArrowRight, CheckCircle, AlertTriangle, XCircle,
} from "lucide-react";

const FLOW_COLUMNS = [
  {
    title: "EXTERNAL SOURCES",
    color: "border-emerald-500/30",
    nodes: [
      { name: "Alpaca API", icon: Globe, status: "ok" },
      { name: "Finviz", icon: Globe, status: "ok" },
      { name: "Unusual Whales", icon: Globe, status: "ok" },
      { name: "FRED Economic", icon: Database, status: "ok" },
      { name: "SEC EDGAR", icon: Database, status: "warn" },
      { name: "Coingecko", icon: Globe, status: "off" },
      { name: "News API", icon: Radio, status: "ok" },
      { name: "Discord & Twitter", icon: Radio, status: "ok" },
      { name: "YouTube Transcripts", icon: Globe, status: "ok" },
      { name: "OpenClaw P2T", icon: Server, status: "ok" },
    ],
  },
  {
    title: "AGENT",
    color: "border-cyan-500/30",
    nodes: [
      { name: "signal_engine.py", icon: Cpu, status: "ok" },
      { name: "Signal Generation Agent", icon: Activity, status: "ok" },
      { name: "ML Learning Agent", icon: Cpu, status: "ok" },
      { name: "Sentiment Agent", icon: Cpu, status: "ok" },
      { name: "YouTube Knowledge Agent", icon: Cpu, status: "ok" },
    ],
  },
  {
    title: "PROCESSING ENGINES",
    color: "border-purple-500/30",
    nodes: [
      { name: "market_engine.py", icon: Server, status: "ok" },
      { name: "execution_engine.py", icon: Server, status: "ok" },
      { name: "risk_engine.py", icon: Server, status: "ok" },
      { name: "ml_engine.py", icon: Server, status: "ok" },
      { name: "council_runner.py", icon: Server, status: "ok" },
      { name: "brain_service.py", icon: Cpu, status: "warn" },
      { name: "feature_aggregator.py", icon: Server, status: "ok" },
      { name: "kelly_position_sizer.py", icon: Server, status: "ok" },
      { name: "openclaw_bridge", icon: Server, status: "ok" },
    ],
  },
  {
    title: "STORAGE DATABASES",
    color: "border-amber-500/30",
    nodes: [
      { name: "trading_data.db", icon: Database, status: "ok" },
      { name: "training_store", icon: Database, status: "ok" },
      { name: "logs_db", icon: Database, status: "ok" },
      { name: "feature_cache", icon: Database, status: "ok" },
      { name: "websocket_manager", icon: Server, status: "ok" },
    ],
  },
  {
    title: "FRONTEND INTERFACES",
    color: "border-red-500/30",
    nodes: [
      { name: "AgentCommandCenter.jsx", icon: Monitor, status: "ok" },
      { name: "Dashboard.jsx", icon: Monitor, status: "ok" },
      { name: "Backtesting.jsx", icon: Monitor, status: "ok" },
      { name: "MLBrainFlywheel.jsx", icon: Monitor, status: "ok" },
      { name: "Patterns.jsx", icon: Monitor, status: "ok" },
      { name: "SignalIntelligenceV3.jsx", icon: Monitor, status: "ok" },
      { name: "RiskIntelligence.jsx", icon: Monitor, status: "ok" },
    ],
  },
];

function StatusDot({ status }) {
  const c = status === "ok" ? "bg-emerald-500" : status === "warn" ? "bg-amber-500" : "bg-gray-600";
  return <span className={`w-2 h-2 rounded-full ${c} inline-block`} />;
}

// --- Connection Health Matrix (heatmap) ---
function ConnectionHealthMatrix() {
  const services = ["Alpaca","Finviz","FRED","EDGAR","WS","DB","ML","Council","Risk"];
  return (
    <div className="aurora-card p-3">
      <h3 className="text-[10px] font-bold text-white uppercase tracking-wider mb-2">Connection Health Matrix</h3>
      <div className="grid gap-0.5" style={{ gridTemplateColumns: `repeat(${services.length}, 1fr)` }}>
        {services.map(s => (
          <div key={s} className="text-[7px] text-gray-500 text-center truncate">{s}</div>
        ))}
        {services.map((s, i) =>
          services.map((_, j) => {
            const val = Math.random();
            const bg = val > 0.8 ? "bg-emerald-500" : val > 0.5 ? "bg-emerald-700" : val > 0.2 ? "bg-amber-700" : "bg-red-700";
            return <div key={`${i}-${j}`} className={`h-3 rounded-sm ${bg} opacity-70`} />;
          })
        )}
      </div>
    </div>
  );
}

// --- Traffic Node Discovery ---
function TrafficDiscovery() {
  return (
    <div className="aurora-card p-3">
      <h3 className="text-[10px] font-bold text-white uppercase tracking-wider mb-2">Traffic Node Discovery</h3>
      <div className="space-y-1 text-[9px]">
        {[
          ["Auto-Mesh vs WebSocket", "MESH", "text-cyan-400"],
          ["DESIGN TOPOLOGY", "STAR", "text-amber-400"],
          ["AUTO-DISCOVERY", "ON", "text-emerald-400"],
        ].map(([k, v, c]) => (
          <div key={k} className="flex justify-between">
            <span className="text-gray-500">{k}</span>
            <span className={`font-mono font-bold ${c}`}>{v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- WebSocket Channels ---
function WsChannels() {
  const channels = [
    { name: "agents", status: "ok", msgs: 847 },
    { name: "council", status: "ok", msgs: 234 },
    { name: "signals", status: "ok", msgs: 1203 },
    { name: "llm-flow", status: "warn", msgs: 56 },
    { name: "market-data", status: "ok", msgs: 4521 },
  ];
  return (
    <div className="aurora-card p-3">
      <h3 className="text-[10px] font-bold text-white uppercase tracking-wider mb-2">WebSocket Channels</h3>
      <div className="space-y-1">
        {channels.map(ch => (
          <div key={ch.name} className="flex items-center gap-2 text-[9px]">
            <StatusDot status={ch.status} />
            <span className="text-cyan-400 font-mono flex-1">{ch.name}</span>
            <span className="text-gray-500">{ch.msgs} msg/s</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- API Route Status ---
function ApiRouteStatus() {
  const routes = [
    { path: "/api/v1/agents", latency: "12ms", status: "ok" },
    { path: "/api/v1/signals", latency: "8ms", status: "ok" },
    { path: "/api/v1/council", latency: "45ms", status: "ok" },
    { path: "/api/v1/risk", latency: "23ms", status: "warn" },
    { path: "/api/v1/ml-brain", latency: "67ms", status: "ok" },
  ];
  return (
    <div className="aurora-card p-3">
      <h3 className="text-[10px] font-bold text-white uppercase tracking-wider mb-2">API Route Status</h3>
      <div className="space-y-1">
        {routes.map(r => (
          <div key={r.path} className="flex items-center gap-2 text-[9px]">
            <StatusDot status={r.status} />
            <span className="text-gray-400 font-mono flex-1">{r.path}</span>
            <span className="text-white">{r.latency}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// === MAIN TAB ===
export default function LiveWiringTab() {
  return (
    <div className="space-y-3">
      {/* Architecture Flow Diagram — 5 columns */}
      <div className="aurora-card p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider">Live Wiring Map</h3>
          <div className="flex gap-3 text-[9px] text-gray-500">
            <span>CPU: <span className="text-white">47%</span></span>
            <span>RAM: <span className="text-white">3.1GB</span></span>
            <span>Latency: <span className="text-emerald-400">12ms</span></span>
            <span>GPU: <span className="text-amber-400">67%</span></span>
          </div>
        </div>

        <div className="grid grid-cols-5 gap-2">
          {FLOW_COLUMNS.map((col, ci) => (
            <div key={col.title} className={`border ${col.color} rounded-lg p-2 bg-[#0B0E14]/50`}>
              <div className="text-[8px] font-bold text-gray-400 uppercase tracking-wider mb-2 text-center border-b border-gray-800 pb-1">{col.title}</div>
              <div className="space-y-1">
                {col.nodes.map(n => (
                  <div key={n.name} className="flex items-center gap-1.5 px-1.5 py-1 rounded hover:bg-cyan-500/10 transition-colors cursor-pointer group">
                    <StatusDot status={n.status} />
                    <n.icon className="w-3 h-3 text-gray-500 group-hover:text-cyan-400" />
                    <span className="text-[8px] text-gray-400 group-hover:text-white truncate">{n.name}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Flow arrows overlay (simplified with CSS) */}
        <div className="flex items-center justify-center gap-2 mt-3 text-[9px] text-cyan-500/40">
          <span>Sources</span><ArrowRight className="w-3 h-3" />
          <span>Agents</span><ArrowRight className="w-3 h-3" />
          <span>Engines</span><ArrowRight className="w-3 h-3" />
          <span>Storage</span><ArrowRight className="w-3 h-3" />
          <span>Frontend</span>
        </div>
      </div>

      {/* Bottom panels */}
      <div className="grid grid-cols-4 gap-3">
        <ConnectionHealthMatrix />
        <TrafficDiscovery />
        <WsChannels />
        <ApiRouteStatus />
      </div>
    </div>
  );
}
