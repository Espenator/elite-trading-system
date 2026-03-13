// Remaining Tabs: Blackboard & Comms, Conference & Consensus, ML Ops, Logs & Telemetry
// Design system: bg-[#111827], border-[#1e293b], text-[#94a3b8] headers, text-[#f8fafc] primary
import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  MessageCircle, Radio, Users, Brain, Terminal, Activity, RefreshCw,
  CheckCircle, AlertTriangle, XCircle, Clock, Send, Filter, Search,
  TrendingUp, Cpu, Database, Server, Eye, Target, Shield,
} from "lucide-react";
import { useApi, useHitlBuffer } from "../../hooks/useApi";
import ws from "../../services/websocket";
import { toast } from "react-toastify";
import { getApiUrl, getAuthHeaders } from "../../config/api";

const CARD_CLASS = "bg-[#111827] border border-[#1e293b] rounded-md p-3";
const HEADER_CLASS = "text-xs font-bold text-[#94a3b8] uppercase tracking-wider mb-2 font-mono";

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
  const { data: blackboardData } = useApi("cnsBlackboard", { pollIntervalMs: 15000 });
  const { data: hitlData, refetch: refetchHitl } = useHitlBuffer(15000);
  const [messages, setMessages] = useState([]);
  const feedRef = useRef([]);

  const topics = useMemo(() => {
    const raw = blackboardData?.topics ?? blackboardData?.channels ?? blackboardData;
    if (Array.isArray(raw)) return raw;
    if (raw && typeof raw === "object") return Object.entries(raw).map(([topic, data]) => ({ topic, subs: data?.subs ?? 0, rate: data?.rate ?? data?.msgs ?? 0, status: data?.status ?? "ok" }));
    return [];
  }, [blackboardData]);

  const hitlBuffer = useMemo(() => {
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
  }, [hitlData]);

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

  return (
    <div className="grid grid-cols-12 gap-3">
      <div className="col-span-5 border border-[#1e293b] rounded-md p-3 bg-[#111827]">
        <h3 className={HEADER_CLASS}>Real-Time Message Feed</h3>
        <div className="space-y-0.5 max-h-[400px] overflow-y-auto scrollbar-thin font-mono">
          {messages.length === 0 ? (
            <div className="text-[#64748b] text-xs text-center py-8">No messages yet. Connect WebSocket for live data.</div>
          ) : messages.map(m => (
            <div key={m.id} className="flex gap-2 text-[9px] hover:bg-[#1e293b] px-1 py-0.5 rounded cursor-pointer">
              <span className="text-[#64748b] shrink-0 font-mono">{m.time}</span>
              <span className="text-[#06b6d4] shrink-0 font-bold">{m.topic}</span>
              <span className="text-[#94a3b8] truncate">{m.payload}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="col-span-4 space-y-3">
        <div className="bg-[#111827] border border-[#1e293b] rounded-md p-3">
          <h3 className={HEADER_CLASS}>Blackboard Topics</h3>
          <table className="w-full text-[10px] font-mono">
            <thead><tr className="text-[#94a3b8] border-b border-[#1e293b]">
              <th className="text-left py-1">Topic</th><th className="text-right">Subs</th><th className="text-right">Rate/s</th><th className="text-right">Status</th>
            </tr></thead>
            <tbody>
              {topics.length === 0 ? (
                <tr><td colSpan={4} className="py-3 text-center text-[#64748b]">No channel data</td></tr>
              ) : topics.map(t => (
              <tr key={t.topic} className="border-b border-[#1e293b]/50 hover:bg-[#1e293b]">
                <td className="py-1 text-[#06b6d4]">{t.topic}</td>
                <td className="text-right text-[#f8fafc]">{t.subs}</td>
                <td className="text-right text-[#94a3b8]">{t.rate}</td>
                <td className="text-right">
                  <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: t.status === "ok" ? "#10b981" : "#f59e0b" }} />
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>

      <div className="col-span-3 bg-[#111827] border border-[#1e293b] rounded-md p-3">
        <h3 className={HEADER_CLASS}>HITL Ring Buffer</h3>
        <div className="space-y-2">
          {hitlBuffer.length === 0 ? (
            <div className="text-[10px] text-[#64748b] font-mono py-3 text-center">No pending HITL items</div>
          ) : hitlBuffer.map(h => (
            <div key={h.id} className="bg-[#0f1219] border border-[#1e293b] rounded p-2">
              <div className="flex items-center justify-between text-[10px] mb-1 font-mono">
                <span className="text-[#f59e0b] font-bold">{h.type}</span>
                <span className="text-[#64748b]">{h.symbol}</span>
              </div>
              <div className="text-[10px] text-[#f8fafc] mb-1 font-mono">{h.action} <span className="text-[#64748b]">({h.confidence}% conf)</span></div>
              {h.status === "pending" ? (
                <div className="flex gap-1">
                  <button
                    type="button"
                    className="px-2 py-0.5 text-[9px] rounded cursor-pointer bg-[#10b981]/20 text-[#10b981] border border-[#10b981]/30 hover:bg-[#10b981]/30"
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
                    type="button"
                    className="px-2 py-0.5 text-[9px] rounded cursor-pointer bg-[#ef4444]/20 text-[#ef4444] border border-[#ef4444]/30 hover:bg-[#ef4444]/30"
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
                <span className="text-[9px] text-[#10b981]">Approved</span>
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
  const { data: councilStatus } = useApi("council/status", { pollIntervalMs: 15000 });
  const { data: conferenceData } = useApi("conference", { pollIntervalMs: 20000 });
  const { data: weightsRaw } = useApi("councilWeights", { pollIntervalMs: 20000 });

  const stages = useMemo(() => {
    const s = councilStatus?.stages;
    if (Array.isArray(s) && s.length > 0) return s;
    return [];
  }, [councilStatus?.stages]);

  const recentConferences = useMemo(() => {
    if (Array.isArray(conferenceData)) return conferenceData.slice(0, 10);
    const recent = conferenceData?.recent ?? conferenceData?.history ?? conferenceData?.conferences;
    return Array.isArray(recent) ? recent.slice(0, 10) : (conferenceData?.id ? [conferenceData] : []);
  }, [conferenceData]);

  const weightsList = useMemo(() => {
    const w = weightsRaw?.weights ?? weightsRaw;
    if (Array.isArray(w) && w.length > 0) return w;
    if (w && typeof w === "object") return Object.entries(w).map(([name, weight]) => ({ name, weight: typeof weight === "number" ? weight : 0 }));
    return [];
  }, [weightsRaw]);
  return (
    <div className="grid grid-cols-12 gap-3">
      <div className={"col-span-8 " + CARD_CLASS}>
        <h3 className={HEADER_CLASS}>Council DAG Pipeline</h3>
        <div className="space-y-2">
          {stages.length === 0 ? (
            <div className="text-[#64748b] text-[10px] font-mono py-6 text-center">No council stage data. Connect to council/status for pipeline.</div>
          ) : stages.map((s, i) => (
            <div key={s.name ?? i} className={`flex items-center gap-3 p-2 rounded border ${s.status === "complete" ? "border-[#10b981]/30 bg-[#10b981]/5" : s.status === "running" ? "border-[#06b6d4]/30 bg-[#06b6d4]/10" : "border-[#1e293b] bg-[#0f1219]"}`}>
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold font-mono ${s.status === "complete" ? "bg-[#10b981]/20 text-[#10b981]" : s.status === "running" ? "bg-[#06b6d4]/20 text-[#06b6d4]" : "bg-[#1e293b] text-[#64748b]"}`}>
                {s.status === "complete" ? "✓" : i + 1}
              </div>
              <div className="flex-1">
                <div className="text-[10px] text-[#f8fafc] font-bold font-mono">{s.name}</div>
                <div className="flex gap-1 mt-0.5 flex-wrap">
                  {(Array.isArray(s.agents) ? s.agents : []).map(a => (
                    <span key={a} className={`px-1.5 py-0.5 rounded text-[8px] font-mono ${s.status === "complete" ? "bg-[#10b981]/10 text-[#10b981]" : s.status === "running" ? "bg-[#06b6d4]/10 text-[#06b6d4]" : "bg-[#1e293b] text-[#64748b]"}`}>{a}</span>
                  ))}
                </div>
              </div>
              <span className={`text-[9px] font-mono ${s.status === "complete" ? "text-[#10b981]" : s.status === "running" ? "text-[#06b6d4]" : "text-[#64748b]"}`}>{String(s.status).toUpperCase()}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="col-span-4 space-y-3">
        <div className={CARD_CLASS}>
          <h3 className={HEADER_CLASS}>Recent Conferences</h3>
          <div className="space-y-2">
            {recentConferences.length === 0 ? (
              <div className="text-[10px] text-[#64748b] font-mono py-4 text-center">No conference data</div>
            ) : recentConferences.map(c => (
              <div key={c.id ?? c.symbol} className="bg-[#0f1219] rounded p-2 border border-[#1e293b]">
                <div className="flex items-center justify-between text-[10px] mb-1 font-mono">
                  <span className="text-[#64748b]">{c.id ?? "—"}</span>
                  <span className="text-[#06b6d4] font-bold">{c.symbol ?? "—"}</span>
                  <span className={`font-bold ${c.verdict === "BUY" ? "text-[#10b981]" : c.verdict === "SELL" ? "text-[#ef4444]" : "text-[#f59e0b]"}`}>{c.verdict ?? "—"}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: "#1e293b" }}>
                    <div className="h-full rounded-full bg-[#06b6d4]" style={{ width: `${c.confidence ?? 0}%` }} />
                  </div>
                  <span className="text-[9px] text-[#f8fafc] font-mono">{c.confidence ?? 0}%</span>
                </div>
                <div className="flex gap-2 mt-1 text-[8px] font-mono">
                  <span className="text-[#10b981]">For: {c.votes?.for ?? "—"}</span>
                  <span className="text-[#ef4444]">Against: {c.votes?.against ?? "—"}</span>
                  <span className="text-[#64748b]">Abstain: {c.votes?.abstain ?? "—"}</span>
                  <span className="text-[#64748b] ml-auto">{c.duration ?? "—"}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className={CARD_CLASS}>
          <h3 className={HEADER_CLASS}>Bayesian Agent Weights</h3>
          {weightsList.length === 0 ? (
            <div className="text-[#64748b] text-[10px] font-mono py-4 text-center">No weight data. councilWeights API will populate when available.</div>
          ) : weightsList.map((item, i) => {
            const name = item.name ?? item.agent_name ?? `Agent ${i + 1}`;
            const w = typeof item.weight === "number" ? item.weight : (Array.isArray(item) ? item[1] : 0);
            const pct = w <= 1 ? w * 100 : Math.min(100, w);
            return (
              <div key={name + i} className="flex items-center gap-2 text-[9px] mb-1 font-mono">
                <span className="w-24 text-[#94a3b8] truncate">{name}</span>
                <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: "#1e293b" }}>
                  <div className="h-full rounded-full bg-[#06b6d4]" style={{ width: `${pct}%` }} />
                </div>
                <span className="text-[#f8fafc] w-8 text-right">{pct.toFixed(0)}%</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ========== ML OPS TAB ==========
export function MlOpsTab() {
  const { data: models } = useApi("ml-brain/models");
  const { data: training } = useApi("training");
  const { data: driftData } = useApi("drift", { pollIntervalMs: 30000 });
  const modelList = Array.isArray(models) ? models : (models?.models ?? []);
  const trainingJobs = Array.isArray(training) ? training : (training?.jobs ?? []);
  const driftMetrics = Array.isArray(driftData) ? driftData : (driftData?.metrics ?? driftData?.drift ?? []);

  return (
    <div className="grid grid-cols-12 gap-3">
      <div className={"col-span-6 " + CARD_CLASS}>
        <h3 className={HEADER_CLASS}>Model Registry</h3>
        <table className="w-full text-[10px] font-mono">
          <thead><tr className="text-[#94a3b8] border-b border-[#1e293b]">
            <th className="text-left py-1">Model</th><th className="text-left">Version</th><th className="text-right">Accuracy</th><th className="text-right">Status</th><th className="text-right">Last Train</th>
          </tr></thead>
          <tbody>
            {modelList.length === 0 ? (
              <tr><td colSpan={5} className="py-4 text-center text-[#64748b]">No models</td></tr>
            ) : modelList.map((m, i) => (
            <tr key={m.name || i} className="border-b border-[#1e293b]/50 hover:bg-[#1e293b]">
              <td className="py-1.5 text-[#06b6d4]">{m.name}</td>
              <td className="text-[#94a3b8]">{m.version ?? "—"}</td>
              <td className="text-right text-[#10b981]">{typeof m.accuracy === "number" ? `${m.accuracy}%` : m.accuracy ?? "—"}</td>
              <td className="text-right">
                <span className="px-1.5 py-0.5 rounded-full text-[9px] font-semibold" style={{ backgroundColor: m.status === "deployed" ? "#10b98120" : m.status === "training" ? "#8b5cf620" : "#f59e0b20", color: m.status === "deployed" ? "#10b981" : m.status === "training" ? "#8b5cf6" : "#f59e0b" }}>{m.status ?? "—"}</span>
              </td>
              <td className="text-right text-[#64748b]">{m.lastTrain ?? m.last_train ?? "—"}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>

      <div className={"col-span-3 " + CARD_CLASS}>
        <h3 className={HEADER_CLASS}>Training Pipeline</h3>
        <div className="space-y-2">
          {trainingJobs.length === 0 ? (
            <div className="text-[10px] text-[#64748b] font-mono py-4 text-center">No training jobs</div>
          ) : trainingJobs.map(j => (
            <div key={j.id} className="bg-[#0f1219] rounded p-2 border border-[#1e293b]">
              <div className="flex items-center justify-between text-[10px] mb-1 font-mono">
                <span className="text-[#64748b]">{j.id}</span>
                <span className="text-[#06b6d4] font-bold">{j.model}</span>
              </div>
              <div className="text-[9px] text-[#94a3b8] mb-1 font-mono">Epoch: <span className="text-[#f8fafc]">{j.epoch ?? "—"}</span> | Loss: <span className="text-[#10b981]">{j.loss ?? "—"}</span></div>
              <div className="h-1.5 rounded-full overflow-hidden mb-1" style={{ backgroundColor: "#1e293b" }}>
                <div className="h-full rounded-full bg-[#8b5cf6]" style={{ width: `${typeof j.progress === "number" ? j.progress : 50}%` }} />
              </div>
              <div className="flex justify-between text-[8px] font-mono text-[#64748b]">
                <span>ETA: {j.eta ?? "—"}</span>
                <span className="text-[#f59e0b]">GPU: {j.gpu ?? "—"}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className={"col-span-3 " + CARD_CLASS}>
        <h3 className={HEADER_CLASS}>Drift Detection</h3>
        <div className="space-y-2">
          {driftMetrics.length === 0 ? (
            <div className="text-[10px] text-[#64748b] font-mono py-4 text-center">No drift data</div>
          ) : driftMetrics.map((d, i) => (
            <div key={d.name ?? i}>
              <div className="flex justify-between text-[9px] mb-0.5 font-mono">
                <span className="text-[#94a3b8]">{d.name}</span>
                <span className={d.status === "warn" ? "text-[#f59e0b]" : "text-[#10b981]"}>{d.val ?? 0} / {d.threshold ?? "—"}</span>
              </div>
              <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: "#1e293b" }}>
                <div className="h-full rounded-full" style={{ width: `${d.threshold ? Math.min(100, (d.val / d.threshold) * 100) : 0}%`, backgroundColor: d.status === "warn" ? "#f59e0b" : "#10b981" }} />
              </div>
            </div>
          ))}
        </div>
        <div className="mt-3 text-[9px] text-[#64748b] font-mono">Auto-retrain: PSI &gt; 0.25</div>
      </div>
    </div>
  );
}

// ========== LOGS & TELEMETRY TAB ==========
export function LogsTelemetryTab() {
  const { data: logs } = useApi("logs/system", { pollIntervalMs: 10000 });
  const { data: systemHealth } = useApi("system/health");
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  const logEntries = useMemo(() => {
    if (!logs) return [];
    if (Array.isArray(logs)) return logs.slice(0, 200);
    const entries = logs.logs ?? logs.entries ?? logs;
    return Array.isArray(entries) ? entries.slice(0, 200) : [];
  }, [logs]);

  const levelColors = { INFO: "text-[#06b6d4]", WARN: "text-[#f59e0b]", ERROR: "text-[#ef4444]", DEBUG: "text-[#64748b]" };

  const filtered = useMemo(() => {
    return logEntries.filter(l => {
      if (filter !== "all" && (l.level || "INFO").toUpperCase() !== filter.toUpperCase()) return false;
      const msg = (l.msg ?? l.message ?? "").toString();
      const src = (l.source ?? l.component ?? "").toString();
      if (search && !msg.toLowerCase().includes(search.toLowerCase()) && !src.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [logEntries, filter, search]);

  const telemetry = useMemo(() => {
    const uptime = systemHealth?.uptime ?? "—";
    return [
      ["Log Rate", logs?.rate ?? "—", "text-[#06b6d4]"],
      ["Error Rate", systemHealth?.error_rate != null ? `${systemHealth.error_rate}%` : "—", "text-[#10b981]"],
      ["Latency", systemHealth?.latency_ms != null ? `${systemHealth.latency_ms}ms` : "—", "text-[#f8fafc]"],
      ["Shown", String(filtered.length), "text-[#94a3b8]"],
      ["Filter", filter, "text-[#94a3b8]"],
      ["Uptime", uptime, "text-[#10b981]"],
    ];
  }, [logs, systemHealth, filtered.length, filter]);

  return (
    <div className="space-y-3">
      <div className={CARD_CLASS}>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-[#0f1219] border border-[#1e293b] rounded px-2 py-1 flex-1 max-w-xs">
            <Search className="w-3 h-3 text-[#64748b]" />
            <input className="bg-transparent text-[10px] text-[#f8fafc] font-mono outline-none flex-1 placeholder-[#64748b]" placeholder="Search logs..." value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          <div className="flex gap-1 text-[10px]">
            {["all", "info", "warn", "error", "debug"].map(f => (
              <button key={f} type="button" onClick={() => setFilter(f)} className={`px-2 py-1 rounded border uppercase font-mono cursor-pointer ${filter === f ? "bg-[#164e63] text-[#06b6d4] border-[#06b6d4]/50" : "text-[#64748b] border-[#1e293b] hover:text-[#94a3b8] hover:bg-[#1e293b]"}`}>{f}</button>
            ))}
          </div>
          <button type="button" className="p-1.5 text-[#64748b] hover:text-[#06b6d4] border border-[#1e293b] rounded cursor-pointer" onClick={() => toast.info("Exporting logs...")}><Terminal className="w-3.5 h-3.5" /></button>
        </div>
      </div>

      <div className={CARD_CLASS}>
        <h3 className={HEADER_CLASS}>System Logs</h3>
        <div className="max-h-[450px] overflow-y-auto scrollbar-thin font-mono space-y-0">
          {filtered.length === 0 ? (
            <div className="text-[#64748b] text-[10px] py-8 text-center font-mono">No log entries. logs/system API will populate when available.</div>
          ) : filtered.map((l, i) => (
            <div key={i} className="flex gap-3 text-[10px] hover:bg-[#1e293b] px-2 py-0.5 rounded cursor-pointer border-b border-[#1e293b]/30">
              <span className="text-[#64748b] shrink-0 w-20 font-mono">{l.ts ?? l.timestamp ?? "—"}</span>
              <span className={`shrink-0 w-10 font-bold font-mono ${levelColors[(l.level || "INFO").toUpperCase()] ?? "text-[#06b6d4]"}`}>{l.level ?? "INFO"}</span>
              <span className="text-[#8b5cf6] shrink-0 w-24 truncate font-mono">{l.source ?? l.component ?? "system"}</span>
              <span className="text-[#94a3b8] flex-1">{l.msg ?? l.message ?? JSON.stringify(l).slice(0, 150)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-6 gap-3">
        {telemetry.map(([label, val, c]) => (
          <div key={label} className={CARD_CLASS + " p-2 text-center"}>
            <div className={`text-sm font-bold font-mono ${c}`}>{val}</div>
            <div className="text-[8px] text-[#64748b] uppercase tracking-wider font-mono">{label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
