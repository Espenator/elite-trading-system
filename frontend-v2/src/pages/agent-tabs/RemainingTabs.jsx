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
import { getApiUrl, getAuthHeaders } from "../../config/api";

function normalizePercentage(value) {
  const numericValue = Number(value ?? 0);
  if (!Number.isFinite(numericValue)) return 0;
  return Math.min(Math.max(Math.round(numericValue * (numericValue <= 1 ? 100 : 1)), 0), 100);
}

function formatTimestamp(ts) {
  if (!ts) return "—";
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) return String(ts);
  return date.toLocaleTimeString("en-US", { hour12: false });
}

function normalizeHitlItems(data) {
  const raw = Array.isArray(data) ? data : data?.items ?? data?.buffer ?? [];
  return raw.map((item, index) => {
    const confidenceValue = item.confidence ?? 0;
    return {
      id: item.id ?? item.decision_id ?? `hitl-${index}`,
      type: item.type ?? item.category ?? "REVIEW",
      symbol: item.symbol ?? item.ticker ?? "—",
      action: item.action ?? item.direction ?? item.side ?? "—",
      confidence: normalizePercentage(confidenceValue),
      status: String(item.status ?? "pending").toLowerCase(),
    };
  });
}

async function postHitlDecision(itemId, action) {
  const response = await fetch(getApiUrl(`/agents/hitl/${encodeURIComponent(itemId)}/${action}`), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload?.detail || `HTTP ${response.status}`);
  }
  return payload;
}

function buildModelRows(models) {
  if (Array.isArray(models)) return models;
  if (Array.isArray(models?.latest_runs)) return models.latest_runs;
  return [];
}

// ========== BLACKBOARD & COMMS TAB ==========
export function BlackboardCommsTab() {
  const { data: busStatus } = useApi("system/event-bus/status");
  const { data: hitlData, refetch: refetchHitl } = useApi("agentHitlBuffer", { pollIntervalMs: 15000 });
  const [messages, setMessages] = useState([]);
  const [pendingActions, setPendingActions] = useState({});
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

  const topics = Array.isArray(busStatus?.topics) ? busStatus.topics : [];
  const hitlBuffer = normalizeHitlItems(hitlData);

  const handleHitlAction = async (itemId, action) => {
    setPendingActions((current) => ({ ...current, [itemId]: action }));
    try {
      await postHitlDecision(itemId, action);
      toast.success(`HITL ${action} submitted`);
      refetchHitl();
    } catch (error) {
      toast.error(`HITL ${action} failed: ${error.message}`);
    } finally {
      setPendingActions((current) => {
        const next = { ...current };
        delete next[itemId];
        return next;
      });
    }
  };

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
          {topics.length === 0 ? (
            <div className="text-gray-500 text-xs py-8 text-center">
              No MessageBus topics reported by the backend.
            </div>
          ) : (
            <table className="w-full text-[10px]">
              <thead><tr className="text-gray-500 border-b border-gray-800">
                <th className="text-left py-1">Topic</th><th className="text-right">Subs</th><th className="text-right">Rate</th><th className="text-right">Status</th>
              </tr></thead>
              <tbody>{topics.map((topic) => {
                const msgRate = topic.msgRate ?? topic.rate ?? 0;
                const subs = topic.subs ?? topic.subscribers ?? 0;
                const active = subs > 0 || msgRate > 0;
                return (
                  <tr key={topic.topic} className="border-b border-gray-800/30 hover:bg-cyan-500/5">
                    <td className="py-1 text-cyan-400 font-mono">{topic.topic}</td>
                    <td className="text-right text-white">{subs}</td>
                    <td className="text-right text-gray-400">{msgRate}</td>
                    <td className="text-right">
                      <span className={`w-2 h-2 rounded-full inline-block ${active ? "bg-emerald-500" : "bg-gray-600"}`} />
                    </td>
                  </tr>
                );
              })}</tbody>
            </table>
          )}
        </div>
      </div>

      {/* HITL Buffer */}
      <div className="col-span-3 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Human-In-The-Loop Buffer</h3>
        {hitlBuffer.length === 0 ? (
          <div className="text-gray-500 text-xs py-8 text-center">
            No pending HITL items in the backend buffer.
          </div>
        ) : (
          <div className="space-y-2">
            {hitlBuffer.map((item) => (
              <div key={item.id} className="bg-[#0B0E14] border border-gray-700 rounded p-2">
                <div className="flex items-center justify-between text-[10px] mb-1">
                  <span className="text-amber-400 font-bold">{item.type}</span>
                  <span className="text-gray-500">{item.symbol}</span>
                </div>
                <div className="text-[10px] text-white mb-1">
                  {item.action} <span className="text-gray-500">({item.confidence}% conf)</span>
                </div>
                {item.status === "pending" ? (
                  <div className="flex gap-1">
                    <button
                      className="px-2 py-0.5 text-[9px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded disabled:opacity-50"
                      disabled={Boolean(pendingActions[item.id])}
                      onClick={() => handleHitlAction(item.id, "approve")}
                    >
                      Approve
                    </button>
                    <button
                      className="px-2 py-0.5 text-[9px] bg-red-500/20 text-red-400 border border-red-500/30 rounded disabled:opacity-50"
                      disabled={Boolean(pendingActions[item.id])}
                      onClick={() => handleHitlAction(item.id, "reject")}
                    >
                      Reject
                    </button>
                  </div>
                ) : (
                  <span className={`text-[9px] ${item.status === "approved" ? "text-emerald-400" : item.status === "rejected" ? "text-red-400" : "text-gray-400"}`}>
                    {item.status.toUpperCase()}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ========== CONFERENCE & CONSENSUS TAB ==========
export function ConferenceConsensusTab() {
  const { data: councilStatus } = useApi("council/status");
  const { data: conferenceStatus } = useApi("conference", { pollIntervalMs: 15000 });

  const stages = Array.isArray(councilStatus?.dag_stages)
    ? councilStatus.dag_stages.map((agents, index) => ({
        name: `Stage ${index + 1}`,
        agents,
      }))
    : [];
  const latestConference = conferenceStatus?.last_conference;
  const weightEntries = Object.entries(councilStatus?.agent_weights ?? {});

  return (
    <div className="grid grid-cols-12 gap-3">
      {/* Pipeline Visualization */}
      <div className="col-span-8 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-3">Council DAG Pipeline (7 Stages)</h3>
        {stages.length === 0 ? (
          <div className="text-gray-500 text-xs py-10 text-center">
            No council DAG configuration reported by the backend.
          </div>
        ) : (
          <div className="space-y-2">
            {stages.map((stage, index) => (
              <div key={stage.name} className="flex items-center gap-3 p-2 rounded border border-gray-700 bg-gray-800/20">
                <div className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold bg-cyan-500/20 text-cyan-400">
                  {index + 1}
                </div>
                <div className="flex-1">
                  <div className="text-[10px] text-white font-bold">{stage.name}</div>
                  <div className="flex gap-1 mt-0.5 flex-wrap">
                    {stage.agents.map((agent) => (
                      <span key={agent} className="px-1.5 py-0.5 rounded text-[8px] bg-cyan-500/10 text-cyan-400">
                        {agent}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Vote Breakdown + Recent Conferences */}
      <div className="col-span-4 space-y-3">
        <div className="aurora-card p-3">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Latest Conference</h3>
          {!latestConference || latestConference.ticker === "N/A" ? (
            <div className="text-gray-500 text-xs py-6 text-center">
              No conference has been recorded yet.
            </div>
          ) : (
            <div className="bg-[#0B0E14] rounded p-2 border border-gray-800">
              <div className="flex items-center justify-between text-[10px] mb-1">
                <span className="text-gray-500">#{conferenceStatus?.total_conferences ?? 0}</span>
                <span className="text-cyan-400 font-bold">{latestConference.ticker}</span>
                <span className={`font-bold ${latestConference.verdict === "BUY" ? "text-emerald-400" : latestConference.verdict === "SELL" ? "text-red-400" : "text-amber-400"}`}>
                  {latestConference.verdict}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-cyan-500 rounded-full" style={{ width: `${latestConference.confidence ?? 0}%` }} />
                </div>
                <span className="text-[9px] text-white">{latestConference.confidence ?? 0}%</span>
              </div>
              <div className="flex gap-2 mt-1 text-[8px] flex-wrap">
                {Object.entries(latestConference.votes ?? {}).map(([side, count]) => (
                  <span key={side} className="text-gray-400">{side}: {count}</span>
                ))}
                <span className="text-gray-600 ml-auto">{latestConference.duration ?? 0}s</span>
              </div>
            </div>
          )}
        </div>

        {/* Bayesian Weights */}
        <div className="aurora-card p-3">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Bayesian Agent Weights</h3>
          {weightEntries.length === 0 ? (
            <div className="text-gray-500 text-xs py-4 text-center">
              No Bayesian weight data available.
            </div>
          ) : weightEntries.map(([name, weight]) => (
            <div key={name} className="flex items-center gap-2 text-[9px] mb-1">
              <span className="w-24 text-gray-400">{name}</span>
              <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div className="h-full bg-cyan-500 rounded-full" style={{ width: `${Math.min(Number(weight || 0) * 100, 100)}%` }} />
              </div>
              <span className="text-white w-10 text-right">{(Number(weight || 0) * 100).toFixed(1)}%</span>
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
  const { data: drift } = useApi("drift", { pollIntervalMs: 30000 });
  const modelList = buildModelRows(models);
  const trainingJobs = modelList.filter((model) => String(model.stage ?? model.status).toLowerCase() === "training");
  const driftMetrics = Array.isArray(drift?.metrics) ? drift.metrics : [];

  return (
    <div className="grid grid-cols-12 gap-3">
      {/* Model Registry */}
      <div className="col-span-6 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Model Registry</h3>
        {modelList.length === 0 ? (
          <div className="text-gray-500 text-xs py-8 text-center">
            The model registry has not reported any runs yet.
          </div>
        ) : (
          <table className="w-full text-[10px]">
            <thead><tr className="text-gray-500 border-b border-gray-800">
              <th className="text-left py-1">Model</th><th className="text-left">Run ID</th><th className="text-right">Accuracy</th><th className="text-right">Stage</th><th className="text-right">Created</th>
            </tr></thead>
            <tbody>{modelList.map((model, index) => {
              const accuracy = model.metrics?.val_accuracy ?? model.metrics?.cv_accuracy ?? model.metrics?.accuracy ?? null;
              const stage = model.stage ?? model.status ?? "unknown";
              return (
                <tr key={model.run_id || model.name || index} className="border-b border-gray-800/30 hover:bg-cyan-500/5">
                  <td className="py-1.5 text-cyan-400 font-mono">{model.model_name ?? model.name ?? "—"}</td>
                  <td className="text-gray-400 font-mono">{model.run_id ?? model.version ?? "—"}</td>
                  <td className="text-right text-emerald-400">{typeof accuracy === "number" ? `${normalizePercentage(accuracy)}%` : "—"}</td>
                  <td className="text-right">
                    <span className={`px-1.5 py-0.5 rounded text-[9px] ${stage === "champion" ? "bg-emerald-500/20 text-emerald-400" : stage === "training" ? "bg-purple-500/20 text-purple-400" : "bg-amber-500/20 text-amber-400"}`}>{stage}</span>
                  </td>
                  <td className="text-right text-gray-500">{formatTimestamp(model.created_at)}</td>
                </tr>
              );
            })}</tbody>
          </table>
        )}
      </div>

      {/* Training Pipeline */}
      <div className="col-span-3 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Training Pipeline</h3>
        {trainingJobs.length === 0 ? (
          <div className="text-gray-500 text-xs py-8 text-center">
            No training jobs are currently reported by the registry.
          </div>
        ) : (
          <div className="space-y-2">
            {trainingJobs.map((job) => (
              <div key={job.run_id} className="bg-[#0B0E14] rounded p-2 border border-gray-800">
                <div className="flex items-center justify-between text-[10px] mb-1">
                  <span className="text-gray-500 font-mono">{job.run_id}</span>
                  <span className="text-cyan-400 font-bold">{job.model_name ?? "model"}</span>
                </div>
                <div className="text-[9px] text-gray-400">
                  Created <span className="text-white">{formatTimestamp(job.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Drift Detection */}
      <div className="col-span-3 aurora-card p-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Drift Detection</h3>
        {driftMetrics.length === 0 ? (
          <div className="text-gray-500 text-xs py-8 text-center">
            No drift metrics are currently available.
          </div>
        ) : (
          <div className="space-y-2">
            {driftMetrics.map((metric) => (
              <div key={metric.name}>
                <div className="flex justify-between text-[9px] mb-0.5">
                  <span className="text-gray-400">{metric.name}</span>
                  <span className={metric.status === "warn" ? "text-amber-400" : "text-emerald-400"}>{metric.value}</span>
                </div>
                <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${metric.status === "warn" ? "bg-amber-500" : "bg-emerald-500"}`} style={{ width: `${normalizePercentage(metric.value)}%` }} />
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="mt-3 text-[9px] text-gray-500">
          Mean PSI: {drift?.mean_psi ?? "—"} · Drift detected: {drift?.drift_detected ? "yes" : "no"}
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

  const logEntries = Array.isArray(logs)
    ? logs.slice(0, 100)
    : Array.isArray(logs?.logs)
      ? logs.logs.slice(0, 100)
      : [];

  const levelColors = {
    INFO: "text-cyan-400", WARN: "text-amber-400", ERROR: "text-red-400", DEBUG: "text-gray-500",
  };

  const filtered = logEntries.filter(l => {
    if (filter !== "all" && (l.level || "INFO") !== filter.toUpperCase()) return false;
    if (search && !(l.msg || "").toLowerCase().includes(search.toLowerCase()) && !(l.source || "").toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });
  const logCounts = logEntries.reduce((counts, entry) => {
    const level = String(entry.level || "").toLowerCase();
    if (level === "error") counts.errors += 1;
    if (level === "warning" || level === "warn") counts.warnings += 1;
    if (entry.type === "signal") counts.signals += 1;
    counts.sources.add(entry.source || "system");
    return counts;
  }, { errors: 0, warnings: 0, signals: 0, sources: new Set() });

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
        {filtered.length === 0 ? (
          <div className="text-gray-500 text-xs py-10 text-center">
            No log entries match the current backend response.
          </div>
        ) : (
          <div className="max-h-[450px] overflow-y-auto scrollbar-thin font-mono space-y-0">
            {filtered.map((logEntry, i) => {
              const logLevel = (logEntry.level || "INFO").toUpperCase();
              return (
              <div key={i} className="flex gap-3 text-[10px] hover:bg-cyan-500/5 px-2 py-0.5 rounded cursor-pointer border-b border-gray-800/20">
                <span className="text-gray-600 shrink-0 w-20">{formatTimestamp(logEntry.ts)}</span>
                <span className={`shrink-0 w-10 font-bold ${levelColors[logLevel]}`}>{logLevel}</span>
                <span className="text-purple-400 shrink-0 w-24 truncate">{logEntry.source || "system"}</span>
                <span className="text-gray-300 flex-1">{logEntry.msg || logEntry.message || JSON.stringify(logEntry).slice(0, 150)}</span>
              </div>
            )})}
          </div>
        )}
      </div>

      {/* Telemetry Summary */}
      <div className="grid grid-cols-6 gap-3">
        {[
          ["Entries", String(logEntries.length), "text-cyan-400"],
          ["Errors", String(logCounts.errors), "text-red-400"],
          ["Warnings", String(logCounts.warnings), "text-amber-400"],
          ["Sources", String(logCounts.sources.size), "text-white"],
          ["Latest", logEntries[0]?.ts ? formatTimestamp(logEntries[0].ts) : "—", "text-white"],
          ["Signals", String(logCounts.signals), "text-emerald-400"],
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
