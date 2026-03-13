/**
 * Full System Startup & Health — View
 *
 * 7 phases: environment check → backend startup → router verification →
 * API smoke tests → signal pipeline → frontend wiring → background loops.
 * Displays common failure patterns table. Report can be written to
 * reports/STARTUP-HEALTH-REPORT.md via scripts/startup_health_check.py.
 */
import React, { useCallback } from "react";
import { useApi } from "../hooks/useApi";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Activity,
  FileText,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

const PHASE_ORDER = [
  "1_environment",
  "2_backend_startup",
  "3_router_verification",
  "4_api_smoke",
  "5_signal_pipeline",
  "6_frontend_wiring",
  "7_background_loops",
];

function PhaseIcon({ ok }) {
  if (ok === true) return <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />;
  if (ok === false) return <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />;
  return <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />;
}

function StatusBadge({ status }) {
  const s = (status || "").toLowerCase();
  if (s === "ok") return <span className="text-xs px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">ok</span>;
  if (s === "fail") return <span className="text-xs px-1.5 py-0.5 rounded bg-red-500/20 text-red-400">fail</span>;
  if (s === "warn") return <span className="text-xs px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400">warn</span>;
  if (s === "skip") return <span className="text-xs px-1.5 py-0.5 rounded bg-slate-500/20 text-slate-400">skip</span>;
  return <span className="text-xs text-slate-400">{status}</span>;
}

export default function StartupHealth() {
  const { data, loading, error, refetch } = useApi("startupCheck", { pollIntervalMs: 0 });
  const [expanded, setExpanded] = React.useState(new Set(PHASE_ORDER));
  const toggle = useCallback((key) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const phases = data?.phases || {};
  const overallOk = data?.overall_ok ?? null;
  const failurePatterns = data?.failure_patterns || [];
  const timestamp = data?.timestamp;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Activity className="w-6 h-6 text-cyan-400" />
            Full System Startup & Health
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            7 phases: environment → backend → router → API smoke → signal pipeline → frontend → background loops
          </p>
        </div>
        <div className="flex items-center gap-3">
          {timestamp && (
            <span className="text-xs text-slate-500 font-mono">{new Date(timestamp).toLocaleString()}</span>
          )}
          <button
            type="button"
            onClick={() => refetch()}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/30 text-sm disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Run check
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
          Failed to load startup health: {error.message || String(error)}
        </div>
      )}

      {loading && !data && (
        <div className="flex items-center justify-center py-12 text-slate-400">
          <RefreshCw className="w-6 h-6 animate-spin mr-2" />
          Running 7-phase check…
        </div>
      )}

      {data && (
        <>
          <div className="rounded-lg border border-[rgba(42,52,68,0.5)] bg-[#111827] p-4">
            <div className="flex items-center gap-2">
              <PhaseIcon ok={overallOk} />
              <span className="font-semibold text-white">
                Overall: {overallOk === true ? "PASS" : overallOk === false ? "FAIL" : "—"}
              </span>
            </div>
          </div>

          <div className="space-y-2">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400">7 Phases</h2>
            {PHASE_ORDER.map((key) => {
              const phase = phases[key];
              if (!phase) return null;
              const isExpanded = expanded.has(key);
              return (
                <div
                  key={key}
                  className="rounded-lg border border-[rgba(42,52,68,0.5)] bg-[#111827] overflow-hidden"
                >
                  <button
                    type="button"
                    onClick={() => toggle(key)}
                    className="w-full flex items-center gap-2 p-3 text-left hover:bg-white/5"
                  >
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-slate-400" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-slate-400" />
                    )}
                    <PhaseIcon ok={phase.ok} />
                    <span className="text-sm font-medium text-white flex-1">
                      Phase {key.split("_")[0]}: {phase.label}
                    </span>
                  </button>
                  {isExpanded && (
                    <div className="border-t border-gray-800/50 px-3 pb-3 pt-1 space-y-1">
                      {(phase.checks || []).map((c, i) => (
                        <div key={i} className="flex items-center gap-2 text-sm">
                          <StatusBadge status={c.status} />
                          <span className="text-slate-300">{c.check}</span>
                          <span className="text-slate-500 truncate flex-1" title={c.detail}>
                            — {c.detail}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="rounded-lg border border-[rgba(42,52,68,0.5)] bg-[#111827] overflow-hidden">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 px-4 pt-4 pb-2">
              Common failure patterns
            </h2>
            <p className="text-xs text-slate-500 px-4 pb-3">
              Use this table when a phase fails to find likely cause and remediation.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-y border-gray-800/50">
                    <th className="text-left text-slate-400 font-medium py-2 px-4">Symptom</th>
                    <th className="text-left text-slate-400 font-medium py-2 px-4">Cause</th>
                    <th className="text-left text-slate-400 font-medium py-2 px-4">Remediation</th>
                  </tr>
                </thead>
                <tbody>
                  {failurePatterns.map((row, i) => (
                    <tr key={i} className="border-b border-gray-800/30 hover:bg-white/5">
                      <td className="py-2 px-4 text-slate-300">{row.symptom}</td>
                      <td className="py-2 px-4 text-slate-400">{row.cause}</td>
                      <td className="py-2 px-4 text-slate-400">{row.remediation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-500">
            <FileText className="w-4 h-4" />
            <span>
              To write <code className="bg-slate-800 px-1 rounded">reports/STARTUP-HEALTH-REPORT.md</code>, run from repo root:{" "}
              <code className="bg-slate-800 px-1 rounded">python scripts/startup_health_check.py</code>
            </span>
          </div>
        </>
      )}
    </div>
  );
}
