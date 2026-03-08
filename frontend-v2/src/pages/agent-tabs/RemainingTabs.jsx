// Remaining Tabs: Blackboard & Comms, Conference & Consensus, ML Ops, Logs & Telemetry
import React, { useState, useEffect, useRef } from "react";
import {
  MessageCircle, Radio, Users, Brain, Terminal, Activity, RefreshCw,
  CheckCircle, AlertTriangle, XCircle, Clock, Send, Filter, Search,
  TrendingUp, Cpu, Database, Server, Eye, Target, Shield,
} from "lucide-react";
import { useApi } from "../../hooks/useApi";
import ws from "../../services/websocket";
import { toast } from "react-toastify";

// ========== BLACKBOARD & COMMS TAB ==========
export function BlackboardCommsTab() {
  const { data: busStatus } = useApi("system/event-bus/status");
  const { data: wsChannelsRaw } = useApi("agentWsChannels", { pollIntervalMs: 15000 });
  const { data: hitlRaw } = useApi("agentHitlBuffer", { pollIntervalMs: 15000 });
  const [messages, setMessages] = useState([]);
  const feedRef = useRef([]);

  useEffect(() => {
    const handler = (msg) => {
      if (!msg) return;
      const now = new Date();
      const time = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}.${String(now.getMilliseconds()).padStart(3, "0")}`;
      feedRef.current = [{ id: Date.now() + Math.random(), time, topic: msg.topic || msg.type || "system", payload: JSON.stringify(msg).slice(0, 200) }, ...feedRef.current].slice(0, 100);
      setMessages([...feedRef.current]);
    };
    ws.subscribe("agents", handler);
    ws.subscribe("council", handler);
    return () => { ws.unsubscribe("agents", handler); ws.unsubscribe("council", handler); };
  }, []);

  // Use real WS channel data from /agents/ws-channels; empty array if unavailable
  const channels = Array.isArray(wsChannelsRaw?.channels) ? wsChannelsRaw.channels : [];

  // Use real HITL buffer data; empty array if no pending items
  const hitlBuffer = Array.isArray(hitlRaw?.buffer) ? hitlRaw.buffer : [];

  return (
    <div className="grid grid-cols-12 gap-3">
      {/* Real-time Message Feed */}
      <div className="col-span-5 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Real-Time Message Feed</h3>
        <div className="space-y-0.5 max-h-[400px] overflow-y-auto scrollbar-thin font-mono">
          {messages.length === 0 ? (
            <div className="text-gray-500 text-xs text-center py-8">Awaiting messages... Connect WebSocket to see live data</div>
          ) : messages.map(m => (
            <div key={m.id} className="flex gap-2 text-[9px] hover:bg-cyan-500/5 px-1 py-0.5 rounded">
              <span className="text-gray-600 shrink-0">{m.time}</span>
              <span className="text-cyan-400 shrink-0 font-bold">{m.topic}</span>
              <span className="text-gray-400 truncate">{m.payload}</span>
            </div>
          ))}
        </div>
      </div>

      {/* WS Channel Monitor */}
      <div className="col-span-4 space-y-3">
        <div className="aurora-card p-3">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">
            MessageBus Channel Monitor
            {wsChannelsRaw?.total_connections != null && (
              <span className="ml-2 text-gray-500 font-normal normal-case text-[9px]">
                {wsChannelsRaw.total_connections} connection{wsChannelsRaw.total_connections !== 1 ? "s" : ""}
              </span>
            )}
          </h3>
          {channels.length === 0 ? (
            <div className="text-gray-500 text-[10px] text-center py-4">No channel data — backend may be offline</div>
          ) : (
            <table className="w-full text-[10px]">
              <thead><tr className="text-gray-500 border-b border-gray-800">
                <th className="text-left py-1">Channel</th><th className="text-right">Subs</th><th className="text-right">Msg/s</th><th className="text-right">Status</th>
              </tr></thead>
              <tbody>{channels.map(t => (
                <tr key={t.channel} className="border-b border-gray-800/30 hover:bg-cyan-500/5">
                  <td className="py-1 text-cyan-400 font-mono">{t.channel}</td>
                  <td className="text-right text-white">{t.subscribers ?? 0}</td>
                  <td className="text-right text-gray-400">{t.msg_per_sec ?? 0}</td>
                  <td className="text-right">
                    <span className={`w-2 h-2 rounded-full inline-block ${t.status === "active" ? "bg-emerald-500" : "bg-gray-600"}`} />
                  </td>
                </tr>
              ))}</tbody>
            </table>
          )}
        </div>
      </div>

      {/* HITL Buffer */}
      <div className="col-span-3 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Human-In-The-Loop Buffer</h3>
        <div className="space-y-2">
          {hitlBuffer.length === 0 ? (
            <div className="text-gray-500 text-[10px] text-center py-4">No pending items</div>
          ) : hitlBuffer.map(h => (
            <div key={h.id} className="bg-[#0B0E14] border border-gray-700 rounded p-2">
              <div className="flex items-center justify-between text-[10px] mb-1">
                <span className="text-amber-400 font-bold">{h.type}</span>
                <span className="text-gray-500">{h.symbol}</span>
              </div>
              <div className="text-[10px] text-white mb-1">{h.action} <span className="text-gray-500">({h.confidence}% conf)</span></div>
              {h.status === "pending" ? (
                <div className="flex gap-1">
                  <button className="px-2 py-0.5 text-[9px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded" onClick={() => toast.success(`Approved: ${h.action}`)}>Approve</button>
                  <button className="px-2 py-0.5 text-[9px] bg-red-500/20 text-red-400 border border-red-500/30 rounded" onClick={() => toast.warning(`Rejected: ${h.action}`)}>Reject</button>
                </div>
              ) : (
                <span className="text-[9px] text-emerald-400">Approved</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ========== CONFERENCE & CONSENSUS TAB ==========
export function ConferenceConsensusTab({ councilStatus: councilStatusProp }) {
  // Accept councilStatus as a prop (pre-fetched in ACC) or fetch locally as fallback
  const { data: councilStatusFetched } = useApi("council/status", { pollIntervalMs: 30000, enabled: !councilStatusProp });
  const councilStatus = councilStatusProp ?? councilStatusFetched;

  const { data: councilLatest } = useApi("councilLatest", { pollIntervalMs: 15000 });
  const { data: councilWeightsData } = useApi("councilWeights", { pollIntervalMs: 30000 });

  // Build real DAG stages from /council/status — fall back to known schema if not yet loaded
  const STAGE_LABELS = [
    "Stage 1: Perception",
    "Stage 2: Indicators",
    "Stage 3: Hypothesis",
    "Stage 4: Strategy",
    "Stage 5: Risk/Exec",
    "Stage 6: Critic",
    "Stage 7: Arbiter",
  ];
  const dagStages = Array.isArray(councilStatus?.dag_stages) ? councilStatus.dag_stages : [
    ["market_perception", "flow_perception", "regime", "intermarket"],
    ["rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing"],
    ["hypothesis"],
    ["strategy"],
    ["risk", "execution"],
    ["critic"],
    ["arbiter"],
  ];
  const stages = dagStages.map((agentList, i) => ({
    name: STAGE_LABELS[i] ?? `Stage ${i + 1}`,
    agents: agentList.map(a => a.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())),
    status: "ready",
  }));

  // Latest council decision from /council/latest
  const hasDecision = councilLatest && councilLatest.status !== "no_evaluation_yet" && councilLatest.symbol;
  const latestConference = hasDecision ? [{
    id: councilLatest.council_decision_id || "#—",
    symbol: councilLatest.symbol,
    verdict: (councilLatest.final_direction || "hold").toUpperCase(),
    confidence: Math.round((councilLatest.final_confidence ?? 0) * 100),
    duration: councilLatest.cognitive?.total_latency_ms != null
      ? `${(councilLatest.cognitive.total_latency_ms / 1000).toFixed(1)}s`
      : "—",
    votes: {
      for: (councilLatest.votes ?? []).filter(v => v.direction === councilLatest.final_direction).length,
      against: (councilLatest.votes ?? []).filter(v => v.direction !== councilLatest.final_direction && !v.veto).length,
      vetoed: (councilLatest.votes ?? []).filter(v => v.veto).length,
    },
  }] : [];

  // Real Bayesian weights from /council/weights
  const rawWeights = councilWeightsData?.weights ?? councilStatus?.agent_weights ?? {};
  const weightEntries = Object.entries(rawWeights)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([name, w]) => [
      name.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
      typeof w === "number" ? w : 1.0,
    ]);
  const weightSum = weightEntries.reduce((s, [, w]) => s + w, 0) || 1;

  return (
    <div className="grid grid-cols-12 gap-3">
      {/* Pipeline Visualization */}
      <div className="col-span-8 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-3">
          Council DAG Pipeline ({stages.length} Stages · {councilStatus?.agent_count ?? dagStages.flat().length} agents)
        </h3>
        <div className="space-y-2">
          {stages.map((s, i) => (
            <div key={s.name} className="flex items-center gap-3 p-2 rounded border border-gray-700 bg-gray-800/20">
              <div className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold bg-gray-700 text-gray-300">
                {i + 1}
              </div>
              <div className="flex-1">
                <div className="text-[10px] text-white font-bold">{s.name}</div>
                <div className="flex gap-1 mt-0.5 flex-wrap">
                  {s.agents.map(a => (
                    <span key={a} className="px-1.5 py-0.5 rounded text-[8px] bg-cyan-500/10 text-cyan-400">{a}</span>
                  ))}
                </div>
              </div>
              <span className="text-[9px] text-gray-500">READY</span>
            </div>
          ))}
        </div>
        {!councilStatus && (
          <div className="text-[9px] text-gray-600 mt-2">Connecting to /council/status…</div>
        )}
      </div>

      {/* Latest Conference + Bayesian Weights */}
      <div className="col-span-4 space-y-3">
        <div className="aurora-card p-3">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Latest Council Decision</h3>
          {latestConference.length === 0 ? (
            <div className="text-gray-500 text-[10px] text-center py-4">
              No evaluation yet — run a council evaluation to see results
            </div>
          ) : latestConference.map(c => (
            <div key={c.id} className="bg-[#0B0E14] rounded p-2 border border-gray-800">
              <div className="flex items-center justify-between text-[10px] mb-1">
                <span className="text-gray-500 font-mono">{c.id}</span>
                <span className="text-cyan-400 font-bold">{c.symbol}</span>
                <span className={`font-bold ${c.verdict === "BUY" ? "text-emerald-400" : c.verdict === "SELL" ? "text-red-400" : "text-amber-400"}`}>{c.verdict}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-cyan-500 rounded-full" style={{ width: `${c.confidence}%` }} />
                </div>
                <span className="text-[9px] text-white">{c.confidence}%</span>
              </div>
              <div className="flex gap-2 mt-1 text-[8px]">
                <span className="text-emerald-400">For: {c.votes.for}</span>
                <span className="text-red-400">Against: {c.votes.against}</span>
                <span className="text-gray-500">Vetoed: {c.votes.vetoed}</span>
                <span className="text-gray-600 ml-auto">{c.duration}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Bayesian Weights — real data from /council/weights */}
        <div className="aurora-card p-3">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Bayesian Agent Weights</h3>
          {weightEntries.length === 0 ? (
            <div className="text-gray-500 text-[10px] text-center py-4">Connecting to /council/weights…</div>
          ) : weightEntries.map(([name, w]) => (
            <div key={name} className="flex items-center gap-2 text-[9px] mb-1">
              <span className="w-28 text-gray-400 truncate">{name}</span>
              <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div className="h-full bg-cyan-500 rounded-full" style={{ width: `${Math.min(100, (w / weightSum) * 100)}%` }} />
              </div>
              <span className="text-white w-10 text-right font-mono">{w.toFixed(3)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ========== ML OPS TAB ==========
export function MlOpsTab() {
  const { data: models } = useApi("ml-brain/models");
  const modelList = Array.isArray(models) ? models : [
    { name: "xgboost_v3", version: "3.2.1", accuracy: 84.2, status: "deployed", lastTrain: "2h ago" },
    { name: "lstm_regime", version: "2.1.0", accuracy: 78.9, status: "deployed", lastTrain: "6h ago" },
    { name: "hmm_regime", version: "1.4.2", accuracy: 81.3, status: "deployed", lastTrain: "12h ago" },
    { name: "xgboost_v4", version: "4.0.0-beta", accuracy: 86.1, status: "training", lastTrain: "running" },
    { name: "sentiment_bert", version: "1.0.0", accuracy: 72.4, status: "staging", lastTrain: "1d ago" },
  ];

  const trainingJobs = [
    { id: "JOB-001", model: "xgboost_v4", epoch: "47/1000", loss: 0.0023, eta: "2h 14m", gpu: 89 },
    { id: "JOB-002", model: "lstm_v3", epoch: "120/500", loss: 0.0156, eta: "45m", gpu: 45 },
  ];

  const driftMetrics = [
    { name: "Feature PSI", val: 0.12, threshold: 0.25, status: "ok" },
    { name: "Prediction Calibration", val: 0.08, threshold: 0.15, status: "ok" },
    { name: "Input Distribution", val: 0.34, threshold: 0.30, status: "warn" },
    { name: "Label Drift", val: 0.05, threshold: 0.20, status: "ok" },
  ];

  return (
    <div className="grid grid-cols-12 gap-3">
      {/* Model Registry */}
      <div className="col-span-6 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Model Registry</h3>
        <table className="w-full text-[10px]">
          <thead><tr className="text-gray-500 border-b border-gray-800">
            <th className="text-left py-1">Model</th><th className="text-left">Version</th><th className="text-right">Accuracy</th><th className="text-right">Status</th><th className="text-right">Last Train</th>
          </tr></thead>
          <tbody>{modelList.map((m, i) => (
            <tr key={m.name || i} className="border-b border-gray-800/30 hover:bg-cyan-500/5">
              <td className="py-1.5 text-cyan-400 font-mono">{m.name}</td>
              <td className="text-gray-400">{m.version}</td>
              <td className="text-right text-emerald-400">{typeof m.accuracy === "number" ? `${m.accuracy}%` : m.accuracy || "—"}</td>
              <td className="text-right">
                <span className={`px-1.5 py-0.5 rounded text-[9px] ${m.status === "deployed" ? "bg-emerald-500/20 text-emerald-400" : m.status === "training" ? "bg-purple-500/20 text-purple-400" : "bg-amber-500/20 text-amber-400"}`}>{m.status}</span>
              </td>
              <td className="text-right text-gray-500">{m.lastTrain}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>

      {/* Training Pipeline */}
      <div className="col-span-3 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Training Pipeline</h3>
        <div className="space-y-2">
          {trainingJobs.map(j => (
            <div key={j.id} className="bg-[#0B0E14] rounded p-2 border border-gray-800">
              <div className="flex items-center justify-between text-[10px] mb-1">
                <span className="text-gray-500">{j.id}</span>
                <span className="text-cyan-400 font-bold">{j.model}</span>
              </div>
              <div className="text-[9px] text-gray-400 mb-1">Epoch: <span className="text-white">{j.epoch}</span> | Loss: <span className="text-emerald-400">{j.loss}</span></div>
              <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden mb-1">
                <div className="h-full bg-purple-500 rounded-full animate-pulse" style={{ width: `${(parseInt(j.epoch) / parseInt(j.epoch.split("/")[1])) * 100}%` }} />
              </div>
              <div className="flex justify-between text-[8px]">
                <span className="text-gray-500">ETA: {j.eta}</span>
                <span className="text-amber-400">GPU: {j.gpu}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Drift Detection */}
      <div className="col-span-3 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Drift Detection</h3>
        <div className="space-y-2">
          {driftMetrics.map(d => (
            <div key={d.name}>
              <div className="flex justify-between text-[9px] mb-0.5">
                <span className="text-gray-400">{d.name}</span>
                <span className={d.status === "warn" ? "text-amber-400" : "text-emerald-400"}>{d.val} / {d.threshold}</span>
              </div>
              <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${d.status === "warn" ? "bg-amber-500" : "bg-emerald-500"}`} style={{ width: `${(d.val / d.threshold) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
        <div className="mt-3 text-[9px] text-gray-500">
          Auto-retrain trigger: PSI &gt; 0.25 on any feature
        </div>
      </div>
    </div>
  );
}

// ========== LOGS & TELEMETRY TAB ==========
export function LogsTelemetryTab() {
  const { data: logs } = useApi("logs/system");
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  const logEntries = Array.isArray(logs) ? logs.slice(0, 100) : [
    { ts: "09:41:23.847", level: "INFO", source: "CouncilGate", msg: "Signal #841 forwarded to council — AAPL score 78" },
    { ts: "09:41:22.112", level: "INFO", source: "Arbiter", msg: "Conference #841 verdict: BUY (88% confidence, 9/3/1)" },
    { ts: "09:41:21.003", level: "WARN", source: "MLTrain-03", msg: "GPU memory at 87% — approaching threshold" },
    { ts: "09:41:19.556", level: "INFO", source: "OrderExecutor", msg: "Order submitted: BUY AAPL x25 @ market" },
    { ts: "09:41:18.201", level: "ERROR", source: "MLTrain-03", msg: "No heartbeat for 12m — marking unresponsive" },
    { ts: "09:41:15.889", level: "INFO", source: "Scanner-01", msg: "Scanning NASDAQ — 847 symbols processed" },
    { ts: "09:41:14.002", level: "DEBUG", source: "WeightLearner", msg: "Bayesian update: Researcher weight 0.12 → 0.13" },
    { ts: "09:41:12.441", level: "INFO", source: "Sentiment-02", msg: "Twitter stream: 234 mentions processed for AAPL" },
    { ts: "09:41:10.998", level: "WARN", source: "BridgeCreator", msg: "Latency spike on Alpaca WS: 89ms" },
    { ts: "09:41:09.112", level: "INFO", source: "RiskEngine", msg: "Portfolio VaR: $2,341 (within limits)" },
    { ts: "09:41:07.556", level: "INFO", source: "FeatureAggr", msg: "Feature refresh complete: 847 features x 42 symbols" },
    { ts: "09:41:05.002", level: "INFO", source: "Conference-01", msg: "Conference #840 complete in 3.8s — HOLD MSFT" },
  ];

  const levelColors = {
    INFO: "text-cyan-400", WARN: "text-amber-400", ERROR: "text-red-400", DEBUG: "text-gray-500",
  };

  const filtered = logEntries.filter(l => {
    if (filter !== "all" && (l.level || "INFO") !== filter.toUpperCase()) return false;
    if (search && !(l.msg || "").toLowerCase().includes(search.toLowerCase()) && !(l.source || "").toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="aurora-card p-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-[#0B0E14] border border-gray-700 rounded px-2 py-1 flex-1 max-w-xs">
            <Search className="w-3 h-3 text-gray-500" />
            <input className="bg-transparent text-[10px] text-white outline-none flex-1 placeholder-gray-600" placeholder="Search logs..." value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          <div className="flex gap-1 text-[10px]">
            {["all", "info", "warn", "error", "debug"].map(f => (
              <button key={f} onClick={() => setFilter(f)}
                className={`px-2 py-1 rounded border uppercase ${filter === f ? "bg-cyan-500/20 text-cyan-400 border-cyan-500/30" : "text-gray-500 border-gray-700"}`}>
                {f}
              </button>
            ))}
          </div>
          <button className="p-1.5 text-gray-400 hover:text-cyan-400 border border-gray-700 rounded" onClick={() => toast.info("Exporting logs...")}>
            <Terminal className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Log Stream */}
      <div className="aurora-card p-3">
        <div className="max-h-[450px] overflow-y-auto scrollbar-thin font-mono space-y-0">
          {filtered.map((l, i) => (
            <div key={i} className="flex gap-3 text-[10px] hover:bg-cyan-500/5 px-2 py-0.5 rounded cursor-pointer border-b border-gray-800/20">
              <span className="text-gray-600 shrink-0 w-20">{l.ts || "—"}</span>
              <span className={`shrink-0 w-10 font-bold ${levelColors[l.level || "INFO"]}`}>{l.level || "INFO"}</span>
              <span className="text-purple-400 shrink-0 w-24 truncate">{l.source || "system"}</span>
              <span className="text-gray-300 flex-1">{l.msg || l.message || JSON.stringify(l).slice(0, 150)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Telemetry Summary */}
      <div className="grid grid-cols-6 gap-3">
        {[
          ["Log Rate", "847/min", "text-cyan-400"],
          ["Error Rate", "0.3%", "text-emerald-400"],
          ["Avg Latency", "12ms", "text-white"],
          ["Active Streams", "8", "text-cyan-400"],
          ["Buffer Size", "2.4MB", "text-white"],
          ["Uptime", "47h 12m", "text-emerald-400"],
        ].map(([label, val, c]) => (
          <div key={label} className="aurora-card p-2 text-center">
            <div className={`text-sm font-bold ${c}`}>{val}</div>
            <div className="text-[8px] text-gray-500 uppercase">{label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
