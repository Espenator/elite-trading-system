// LiveWiringTab — matches mockup 05-agent-command-center.png
// Layout: 5-column architecture diagram showing data flow
// External Sources → Agent → Processing Engines → Storage/Databases → Frontend/Interfaces
// Right sidebar: Connection Health Matrix, Traffic Node Discovery, WebSocket Channels, API Route Status
import React from "react";
import {
  Globe, Database, Server, Monitor, Cpu, Radio, Wifi, Activity,
  ArrowRight, CheckCircle, AlertTriangle, XCircle,
} from "lucide-react";

// Node names/icons define the architecture. All statuses default to "off" (disconnected).
// Parent component or real API data should set status to "ok" when connected.
const FLOW_COLUMNS = [
  {
    title: "EXTERNAL SOURCES",
    color: "border-emerald-500/30",
    nodes: [
      { name: "Alpaca API", icon: Globe, status: "off" },
      { name: "Finviz", icon: Globe, status: "off" },
      { name: "Unusual Whales", icon: Globe, status: "off" },
      { name: "FRED Economic", icon: Database, status: "off" },
      { name: "SEC EDGAR", icon: Database, status: "off" },
      { name: "Coingecko", icon: Globe, status: "off" },
      { name: "News API", icon: Radio, status: "off" },
      { name: "Discord & Twitter", icon: Radio, status: "off" },
      { name: "YouTube Transcripts", icon: Globe, status: "off" },
      { name: "OpenClaw P2T", icon: Server, status: "off" },
    ],
  },
  {
    title: "AGENT",
    color: "border-cyan-500/30",
    nodes: [
      { name: "signal_engine.py", icon: Cpu, status: "off" },
      { name: "Signal Generation Agent", icon: Activity, status: "off" },
      { name: "ML Learning Agent", icon: Cpu, status: "off" },
      { name: "Sentiment Agent", icon: Cpu, status: "off" },
      { name: "YouTube Knowledge Agent", icon: Cpu, status: "off" },
    ],
  },
  {
    title: "PROCESSING ENGINES",
    color: "border-purple-500/30",
    nodes: [
      { name: "market_engine.py", icon: Server, status: "off" },
      { name: "execution_engine.py", icon: Server, status: "off" },
      { name: "risk_engine.py", icon: Server, status: "off" },
      { name: "ml_engine.py", icon: Server, status: "off" },
      { name: "council_runner.py", icon: Server, status: "off" },
      { name: "brain_service.py", icon: Cpu, status: "off" },
      { name: "feature_aggregator.py", icon: Server, status: "off" },
      { name: "kelly_position_sizer.py", icon: Server, status: "off" },
      { name: "openclaw_bridge", icon: Server, status: "off" },
    ],
  },
  {
    title: "STORAGE DATABASES",
    color: "border-amber-500/30",
    nodes: [
      { name: "trading_data.db", icon: Database, status: "off" },
      { name: "training_store", icon: Database, status: "off" },
      { name: "logs_db", icon: Database, status: "off" },
      { name: "feature_cache", icon: Database, status: "off" },
      { name: "websocket_manager", icon: Server, status: "off" },
    ],
  },
  {
    title: "FRONTEND INTERFACES",
    color: "border-red-500/30",
    nodes: [
      { name: "AgentCommandCenter.jsx", icon: Monitor, status: "off" },
      { name: "Dashboard.jsx", icon: Monitor, status: "off" },
      { name: "Backtesting.jsx", icon: Monitor, status: "off" },
      { name: "MLBrainFlywheel.jsx", icon: Monitor, status: "off" },
      { name: "Patterns.jsx", icon: Monitor, status: "off" },
      { name: "SignalIntelligenceV3.jsx", icon: Monitor, status: "off" },
      { name: "RiskIntelligence.jsx", icon: Monitor, status: "off" },
    ],
  },
];

function StatusDot({ status }) {
  const c = status === "ok" ? "bg-emerald-500" : status === "warn" ? "bg-amber-500" : "bg-gray-600";
  return <span className={`w-2 h-2 rounded-full ${c} inline-block`} />;
}

// --- Connection Health Matrix (heatmap) ---
// Accepts healthData prop: 2D array of cell color classes indexed [row][col].
// Defaults all cells to bg-gray-700 (no data) when healthData is not provided.
function ConnectionHealthMatrix({ healthData }) {
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
            const bg = (healthData && healthData[i] && healthData[i][j]) ? healthData[i][j] : "bg-gray-700";
            return <div key={`${i}-${j}`} className={`h-3 rounded-sm ${bg} opacity-70`} />;
          })
        )}
      </div>
    </div>
  );
}

// --- Traffic Node Discovery ---
// Accepts topology prop to override default "—" (unknown) values.
// topology: { mesh: string, design: string, autoDiscovery: string }
function TrafficDiscovery({ topology }) {
  const mesh = (topology && topology.mesh) ? topology.mesh : "—";
  const design = (topology && topology.design) ? topology.design : "—";
  const autoDiscovery = (topology && topology.autoDiscovery) ? topology.autoDiscovery : "—";
  return (
    <div className="aurora-card p-3">
      <h3 className="text-[10px] font-bold text-white uppercase tracking-wider mb-2">Traffic Node Discovery</h3>
      <div className="space-y-1 text-[9px]">
        {[
          ["Auto-Mesh vs WebSocket", mesh, "text-cyan-400"],
          ["DESIGN TOPOLOGY", design, "text-amber-400"],
          ["AUTO-DISCOVERY", autoDiscovery, "text-emerald-400"],
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
// Accepts channels prop (array of { name, status, msgs }).
// Defaults to [] (empty). Shows "No channels" when empty.
function WsChannels({ channels = [] }) {
  return (
    <div className="aurora-card p-3">
      <h3 className="text-[10px] font-bold text-white uppercase tracking-wider mb-2">WebSocket Channels</h3>
      <div className="space-y-1">
        {channels.length === 0 ? (
          <div className="text-[9px] text-gray-600 italic">No channels</div>
        ) : (
          channels.map(ch => (
            <div key={ch.name} className="flex items-center gap-2 text-[9px]">
              <StatusDot status={ch.status} />
              <span className="text-cyan-400 font-mono flex-1">{ch.name}</span>
              {ch.msgs != null && <span className="text-gray-500">{ch.msgs} msg/s</span>}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// --- API Route Status ---
// Accepts routes prop (array of { path, latency, status }).
// Defaults to [] (empty). Shows "No route data" when empty.
function ApiRouteStatus({ routes = [] }) {
  return (
    <div className="aurora-card p-3">
      <h3 className="text-[10px] font-bold text-white uppercase tracking-wider mb-2">API Route Status</h3>
      <div className="space-y-1">
        {routes.length === 0 ? (
          <div className="text-[9px] text-gray-600 italic">No route data</div>
        ) : (
          routes.map(r => (
            <div key={r.path} className="flex items-center gap-2 text-[9px]">
              <StatusDot status={r.status} />
              <span className="text-gray-400 font-mono flex-1">{r.path}</span>
              <span className="text-white">{r.latency}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// === MAIN TAB ===
// Accepts props: cpu, ram, latency, gpu, healthData, topology, channels, routes
export default function LiveWiringTab({
  cpu = "0%",
  ram = "0",
  latency = "0ms",
  gpu = "0%",
  healthData,
  topology,
  channels,
  routes,
} = {}) {
  return (
    <div className="space-y-3">
      {/* Architecture Flow Diagram — 5 columns */}
      <div className="aurora-card p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider">Live Wiring Map</h3>
          <div className="flex gap-3 text-[9px] text-gray-500">
            <span>CPU: <span className="text-white">{cpu}</span></span>
            <span>RAM: <span className="text-white">{ram}</span></span>
            <span>Latency: <span className="text-emerald-400">{latency}</span></span>
            <span>GPU: <span className="text-amber-400">{gpu}</span></span>
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
        <ConnectionHealthMatrix healthData={healthData} />
        <TrafficDiscovery topology={topology} />
        <WsChannels channels={channels} />
        <ApiRouteStatus routes={routes} />
      </div>
    </div>
  );
}
