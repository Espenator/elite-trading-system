// Remaining Tabs: Blackboard & Comms, Conference & Consensus, ML Ops, Logs & Telemetry
import React, { useState, useEffect, useRef } from "react";
import {
  MessageCircle, Radio, Users, Brain, Terminal, Activity, RefreshCw,
  CheckCircle, AlertTriangle, XCircle, Clock, Send, Filter, Search,
  TrendingUp, Cpu, Database, Server, Eye, Target, Shield,
} from "lucide-react";
import { useApi, useHitlBuffer } from "../../hooks/useApi";
import ws from "../../services/websocket";
import { toast } from "react-toastify";
import { getApiUrl, getAuthHeaders } from "../../config/api";

async function postHitlDecision(decisionId, action) {
  const res = await fetch(`${getApiUrl("agents")}/hitl/${decisionId}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ========== BLACKBOARD & COMMS TAB ==========
export function BlackboardCommsTab() {
  const { data: busStatus } = useApi("system/event-bus/status");
  const { data: hitlData, refetch: refetchHitl } = useHitlBuffer(15000);
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

  const topics = [
    { topic: "signal.generated", subs: 5, rate: 3.4, status: "ok" },
    { topic: "council.verdict", subs: 8, rate: 1.2, status: "ok" },
    { topic: "market_data.bar", subs: 12, rate: 15.7, status: "ok" },
    { topic: "risk.alert", subs: 6, rate: 0.3, status: "ok" },
    { topic: "agent.heartbeat", subs: 42, rate: 7.0, status: "ok" },
    { topic: "ml.training.progress", subs: 3, rate: 0.1, status: "warn" },
    { topic: "order.submitted", subs: 4, rate: 0.8, status: "ok" },
    { topic: "sentiment.update", subs: 5, rate: 2.1, status: "ok" },
  ];

  const hitlBuffer = (() => {
    if (!hitlData) return [];
    const arr = Array.isArray(hitlData) ? hitlData : hitlData.items ?? hitlData.buffer ?? [];
    return arr.map((d) => ({
      id: d.id ?? d.decision_id ?? String(Math.random()),
      type: d.type ?? "TRADE",
      symbol: d.symbol ?? "—",
      action: (d.direction ?? d.side ?? d.action ?? "—").toUpperCase(),
      confidence: Math.round((d.confidence ?? 0) * (d.confidence != null && d.confidence <= 1 ? 100 : 1)),
      status: d.status ?? "pending",
    }));
  })();

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
          <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">MessageBus Channel Monitor</h3>
          <table className="w-full text-[10px]">
            <thead><tr className="text-gray-500 border-b border-gray-800">
              <th className="text-left py-1">Topic</th><th className="text-right">Subs</th><th className="text-right">Rate/s</th><th className="text-right">Status</th>
            </tr></thead>
            <tbody>{topics.map(t => (
              <tr key={t.topic} className="border-b border-gray-800/30 hover:bg-cyan-500/5">
                <td className="py-1 text-cyan-400 font-mono">{t.topic}</td>
                <td className="text-right text-white">{t.subs}</td>
                <td className="text-right text-gray-400">{t.rate}</td>
                <td className="text-right">
                  <span className={`w-2 h-2 rounded-full inline-block ${t.status === "ok" ? "bg-emerald-500" : "bg-amber-500"}`} />
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>

      {/* HITL Buffer */}
      <div className="col-span-3 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Human-In-The-Loop Buffer</h3>
        <div className="space-y-2">
          {hitlBuffer.map(h => (
            <div key={h.id} className="bg-[#0B0E14] border border-gray-700 rounded p-2">
              <div className="flex items-center justify-between text-[10px] mb-1">
                <span className="text-amber-400 font-bold">{h.type}</span>
                <span className="text-gray-500">{h.symbol}</span>
              </div>
              <div className="text-[10px] text-white mb-1">{h.action} <span className="text-gray-500">({h.confidence}% conf)</span></div>
              {h.status === "pending" ? (
                <div className="flex gap-1">
                  <button
                    className="px-2 py-0.5 text-[9px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded"
                    onClick={async () => {
                      try {
                        await postHitlDecision(h.id, "approve");
                        toast.success(`Approved: ${h.action}`);
                        setTimeout(refetchHitl, 500);
                      } catch (e) {
                        toast.error(e?.message || "Approve failed");
                      }
                    }}
                  >
                    Approve
                  </button>
                  <button
                    className="px-2 py-0.5 text-[9px] bg-red-500/20 text-red-400 border border-red-500/30 rounded"
                    onClick={async () => {
                      try {
                        await postHitlDecision(h.id, "reject");
                        toast.warning(`Rejected: ${h.action}`);
                        setTimeout(refetchHitl, 500);
                      } catch (e) {
                        toast.error(e?.message || "Reject failed");
                      }
                    }}
                  >
                    Reject
                  </button>
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
export function ConferenceConsensusTab() {
  const { data: councilStatus } = useApi("council/status");
  const stages = [
    { name: "Stage 1: Perception", agents: ["MarketPerception", "FlowPerception", "Regime", "Intermarket"], status: "complete" },
    { name: "Stage 2: Indicators", agents: ["RSI", "BBV", "EMA_Trend", "RelativeStrength", "CycleTiming"], status: "complete" },
    { name: "Stage 3: Hypothesis", agents: ["Hypothesis"], status: "running" },
    { name: "Stage 4: Strategy", agents: ["Strategy"], status: "pending" },
    { name: "Stage 5: Risk/Exec", agents: ["Risk", "Execution"], status: "pending" },
    { name: "Stage 6: Critic", agents: ["Critic"], status: "pending" },
    { name: "Stage 7: Arbiter", agents: ["Arbiter"], status: "pending" },
  ];

  const recentConferences = [
    { id: "#841", symbol: "AAPL", verdict: "BUY", confidence: 88, duration: "4.2s", votes: { for: 9, against: 3, abstain: 1 } },
    { id: "#840", symbol: "MSFT", verdict: "HOLD", confidence: 62, duration: "3.8s", votes: { for: 5, against: 6, abstain: 2 } },
    { id: "#839", symbol: "TSLA", verdict: "SELL", confidence: 78, duration: "5.1s", votes: { for: 2, against: 10, abstain: 1 } },
    { id: "#838", symbol: "SPY", verdict: "BUY", confidence: 91, duration: "3.2s", votes: { for: 11, against: 1, abstain: 1 } },
  ];

  return (
    <div className="grid grid-cols-12 gap-3">
      {/* Pipeline Visualization */}
      <div className="col-span-8 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-3">Council DAG Pipeline (7 Stages)</h3>
        <div className="space-y-2">
          {stages.map((s, i) => (
            <div key={s.name} className={`flex items-center gap-3 p-2 rounded border ${s.status === "complete" ? "border-emerald-500/30 bg-emerald-500/5" : s.status === "running" ? "border-cyan-500/30 bg-cyan-500/10 animate-pulse" : "border-gray-700 bg-gray-800/20"}`}>
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${s.status === "complete" ? "bg-emerald-500/20 text-emerald-400" : s.status === "running" ? "bg-cyan-500/20 text-cyan-400" : "bg-gray-700 text-gray-500"}`}>
                {s.status === "complete" ? "✓" : i + 1}
              </div>
              <div className="flex-1">
                <div className="text-[10px] text-white font-bold">{s.name}</div>
                <div className="flex gap-1 mt-0.5 flex-wrap">
                  {s.agents.map(a => (
                    <span key={a} className={`px-1.5 py-0.5 rounded text-[8px] ${s.status === "complete" ? "bg-emerald-500/10 text-emerald-400" : s.status === "running" ? "bg-cyan-500/10 text-cyan-400" : "bg-gray-800 text-gray-500"}`}>{a}</span>
                  ))}
                </div>
              </div>
              <span className={`text-[9px] ${s.status === "complete" ? "text-emerald-400" : s.status === "running" ? "text-cyan-400" : "text-gray-600"}`}>{s.status.toUpperCase()}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Vote Breakdown + Recent Conferences */}
      <div className="col-span-4 space-y-3">
        <div className="aurora-card p-3">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Recent Conferences</h3>
          <div className="space-y-2">
            {recentConferences.map(c => (
              <div key={c.id} className="bg-[#0B0E14] rounded p-2 border border-gray-800">
                <div className="flex items-center justify-between text-[10px] mb-1">
                  <span className="text-gray-500">{c.id}</span>
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
                  <span className="text-gray-500">Abstain: {c.votes.abstain}</span>
                  <span className="text-gray-600 ml-auto">{c.duration}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bayesian Weights */}
        <div className="aurora-card p-3">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Bayesian Agent Weights</h3>
          {[
            ["MarketPerception", 0.12], ["FlowPerception", 0.09], ["Regime", 0.15],
            ["RSI", 0.08], ["Strategy", 0.14], ["Risk", 0.11], ["Critic", 0.10],
          ].map(([name, w]) => (
            <div key={name} className="flex items-center gap-2 text-[9px] mb-1">
              <span className="w-24 text-gray-400">{name}</span>
              <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div className="h-full bg-cyan-500 rounded-full" style={{ width: `${w * 500}%` }} />
              </div>
              <span className="text-white w-8 text-right">{(w * 100).toFixed(0)}%</span>
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
