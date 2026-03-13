// LiveWiringTab — matches mockup 05-agent-command-center.png
// 5-column DAG: External Sources → Scanners → Intelligence → Execution → Output
import React from "react";
import {
  Globe, Database, Server, Monitor, Cpu, Radio, Wifi, Activity,
  ArrowRight, CheckCircle, AlertTriangle, XCircle,
} from "lucide-react";
import { useApi } from "../../hooks/useApi";

const CARD_CLASS = "bg-[#111827] border border-[#1e293b] rounded-md p-3";
const HEADER_CLASS = "text-[10px] font-bold text-[#94a3b8] uppercase tracking-wider mb-2 font-mono";

// 5-column DAG per spec: External Sources → Scanners → Intelligence → Execution → Output
const FLOW_COLUMNS = [
  { title: "EXTERNAL SOURCES", color: "#10b981", nodes: ["Alpaca", "Finviz", "Unusual Whales", "FRED", "EDGAR", "News API", "YouTube"] },
  { title: "SCANNERS", color: "#06b6d4", nodes: ["Signal Engine", "ML Scanner", "Regime Scanner", "Flow Scanner"] },
  { title: "INTELLIGENCE", color: "#3b82f6", nodes: ["Hypothesis", "Sentiment", "Research", "Memory"] },
  { title: "EXECUTION", color: "#8b5cf6", nodes: ["Council", "Risk", "Order Exec", "Kelly Sizer"] },
  { title: "OUTPUT", color: "#f59e0b", nodes: ["Orders", "Dashboard", "Alerts", "Logs"] },
];

function StatusDot({ status }) {
  const c = status === "ok" || status === "healthy" || status === "connected" ? "#10b981" : status === "warn" || status === "degraded" ? "#f59e0b" : "#64748b";
  return <span className="w-2 h-2 rounded-full shrink-0 inline-block" style={{ backgroundColor: c }} title={status} />;
}

function ConnectionHealthMatrix({ healthData }) {
  const services = ["Alpaca", "Finviz", "FRED", "EDGAR", "WS", "DB", "ML", "Council", "Risk"];
  return (
    <div className={CARD_CLASS}>
      <h3 className={HEADER_CLASS}>Connection Health Matrix</h3>
      <div className="grid gap-0.5" style={{ gridTemplateColumns: `repeat(${services.length}, 1fr)` }}>
        {services.map(s => (
          <div key={s} className="text-[7px] text-[#64748b] text-center truncate font-mono">{s}</div>
        ))}
        {services.map((s, i) =>
          services.map((_, j) => {
            const bg = (healthData && healthData[i] && healthData[i][j]) ? healthData[i][j] : "#1e293b";
            return <div key={`${i}-${j}`} className="h-3 rounded-sm opacity-70" style={{ backgroundColor: typeof bg === "string" && bg.startsWith("#") ? bg : "#1e293b" }} />;
          })
        )}
      </div>
    </div>
  );
}

function TrafficDiscovery({ topology }) {
  const mesh = topology?.mesh ?? "—";
  const design = topology?.design ?? "—";
  const autoDiscovery = topology?.autoDiscovery ?? "—";
  return (
    <div className={CARD_CLASS}>
      <h3 className={HEADER_CLASS}>Node Discovery</h3>
      <div className="space-y-1 text-[9px] font-mono">
        <div className="flex justify-between"><span className="text-[#64748b]">Auto-Mesh</span><span className="text-[#06b6d4] font-bold">{mesh}</span></div>
        <div className="flex justify-between"><span className="text-[#64748b]">Design</span><span className="text-[#f59e0b] font-bold">{design}</span></div>
        <div className="flex justify-between"><span className="text-[#64748b]">Auto-Discovery</span><span className="text-[#10b981] font-bold">{autoDiscovery}</span></div>
      </div>
    </div>
  );
}

function WsChannels({ channels = [] }) {
  return (
    <div className={CARD_CLASS}>
      <h3 className={HEADER_CLASS}>WebSocket Channels</h3>
      <div className="space-y-1">
        {channels.length === 0 ? (
          <div className="text-[9px] text-[#64748b] font-mono">No channels</div>
        ) : (
          channels.map(ch => (
            <div key={ch.name} className="flex items-center gap-2 text-[9px]">
              <StatusDot status={ch.status} />
              <span className="text-[#06b6d4] font-mono flex-1">{ch.name}</span>
              {ch.msgs != null && <span className="text-[#64748b] font-mono">{ch.msgs} msg/s</span>}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function ApiRouteStatus({ routes = [] }) {
  return (
    <div className={CARD_CLASS}>
      <h3 className={HEADER_CLASS}>API Route Map</h3>
      <div className="space-y-1">
        {routes.length === 0 ? (
          <div className="text-[9px] text-[#64748b] font-mono">No route data</div>
        ) : (
          routes.map(r => (
            <div key={r.path} className="flex items-center gap-2 text-[9px]">
              <StatusDot status={r.status} />
              <span className="text-[#94a3b8] font-mono flex-1 truncate">{r.path}</span>
              <span className="text-[#f8fafc] font-mono">{r.latency ?? "—"}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// === MAIN TAB ===
export default function LiveWiringTab() {
  const { data: topology } = useApi("swarmTopology", { pollIntervalMs: 20000 });
  const { data: channelsRaw } = useApi("agentWsChannels", { pollIntervalMs: 15000 });
  const { data: systemStatus } = useApi("system/health");
  const { data: healthRaw } = useApi("cnsAgentsHealth", { pollIntervalMs: 15000 });

  const channels = Array.isArray(channelsRaw) ? channelsRaw : (channelsRaw?.channels ?? []);
  const routes = topology?.routes ?? [];
  const healthData = topology?.health_matrix;
  const cpu = systemStatus?.cpu_percent ?? systemStatus?.cpu ?? "0";
  const ram = systemStatus?.memory_percent ?? systemStatus?.memory ?? "0";
  const gpu = systemStatus?.gpu_percent ?? systemStatus?.gpu ?? "0";

  const nodeStatusMap = React.useMemo(() => {
    const list = healthRaw?.agents ?? healthRaw?.matrix ?? (Array.isArray(healthRaw) ? healthRaw : []);
    const m = {};
    list.forEach(a => {
      const name = (a.name ?? a.agent_name ?? "").toLowerCase();
      m[name] = a.health ?? (a.status === "running" ? "ok" : "warn");
    });
    return m;
  }, [healthRaw]);

  const getNodeStatus = (nodeName) => {
    const key = nodeName.toLowerCase().replace(/\s+/g, "");
    if (nodeStatusMap[key]) return nodeStatusMap[key];
    for (const k of Object.keys(nodeStatusMap)) { if (k.includes(key) || key.includes(k)) return nodeStatusMap[k]; }
    return "off";
  };

  return (
    <div className="space-y-3">
      <div className={CARD_CLASS + " p-4"}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-bold text-[#94a3b8] uppercase tracking-wider font-mono">Network Topology</h3>
          <div className="flex gap-3 text-[9px] font-mono text-[#64748b]">
            <span>CPU: <span className="text-[#f8fafc]">{cpu}%</span></span>
            <span>RAM: <span className="text-[#f8fafc]">{ram}%</span></span>
            <span>GPU: <span className="text-[#f59e0b]">{gpu}%</span></span>
          </div>
        </div>

        <div className="grid grid-cols-5 gap-2">
          {FLOW_COLUMNS.map((col) => (
            <div key={col.title} className="border rounded-md p-2 bg-[#0f1219]" style={{ borderColor: `${col.color}40` }}>
              <div className="text-[8px] font-bold uppercase tracking-wider mb-2 text-center border-b border-[#1e293b] pb-1 font-mono" style={{ color: col.color }}>{col.title}</div>
              <div className="space-y-1">
                {col.nodes.map((nodeName) => (
                  <div key={nodeName} className="flex items-center gap-1.5 px-1.5 py-1 rounded hover:bg-[#1e293b] transition-colors cursor-pointer">
                    <StatusDot status={getNodeStatus(nodeName)} />
                    <span className="text-[8px] text-[#94a3b8] font-mono truncate">{nodeName}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-center gap-2 mt-3 text-[9px] text-[#06b6d4]/60 font-mono">
          <span>Sources</span><ArrowRight className="w-3 h-3" /><span>Scanners</span><ArrowRight className="w-3 h-3" /><span>Intelligence</span><ArrowRight className="w-3 h-3" /><span>Execution</span><ArrowRight className="w-3 h-3" /><span>Output</span>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3">
        <ConnectionHealthMatrix healthData={healthData} />
        <TrafficDiscovery topology={topology} />
        <WsChannels channels={channels} />
        <ApiRouteStatus routes={routes} />
      </div>
    </div>
  );
}
