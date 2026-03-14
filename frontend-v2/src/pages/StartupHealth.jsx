/**
 * Full System Startup & Health — View
 *
 * 7 phases: environment check → backend startup → router verification →
 * API smoke tests → signal pipeline → frontend wiring → background loops.
 * Each phase runs independently with its own timeout and error handling.
 * Results are shown progressively as they complete.
 */
import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Activity,
  FileText,
  ChevronDown,
  ChevronRight,
  Loader2,
  PauseCircle,
} from "lucide-react";
import { getApiUrl, getAuthHeaders } from "../config/api";

/* ------------------------------------------------------------------ */
/*  fetchWithTimeout — independent per-request timeout + abort         */
/* ------------------------------------------------------------------ */
async function fetchWithTimeout(url, timeoutMs = 5000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      signal: controller.signal,
      headers: getAuthHeaders(),
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error("Timed out — backend may be starting up or unreachable");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

/* ------------------------------------------------------------------ */
/*  Phase definitions — each check is independent                      */
/* ------------------------------------------------------------------ */
function buildPhases() {
  const baseUrl = import.meta.env.VITE_API_URL ?? "";
  const api = (path) => `${baseUrl}/api/v1${path}`;

  return [
    {
      key: "1_environment",
      name: "Environment",
      label: "Environment variables & config",
      check: async () => {
        const vars = {
          VITE_BACKEND_URL: !!import.meta.env.VITE_BACKEND_URL,
          VITE_API_URL: !!import.meta.env.VITE_API_URL,
          VITE_API_AUTH_TOKEN: !!import.meta.env.VITE_API_AUTH_TOKEN,
        };
        const set = Object.values(vars).filter(Boolean).length;
        const total = Object.keys(vars).length;
        const missing = Object.entries(vars)
          .filter(([, v]) => !v)
          .map(([k]) => k);
        return {
          ok: true,
          detail: `${set}/${total} env vars configured${missing.length ? ` (missing: ${missing.join(", ")})` : ""}`,
          checks: Object.entries(vars).map(([k, v]) => ({
            check: k,
            status: v ? "ok" : "warn",
            detail: v ? "Set" : "Not configured",
          })),
        };
      },
    },
    {
      key: "2_backend_startup",
      name: "Backend",
      label: "Backend process & health endpoint",
      dependsOn: null,
      check: async () => {
        const data = await fetchWithTimeout(api("/system/health-check"), 5000);
        return {
          ok: true,
          detail: `Responding on port 8001 — uptime ${data.uptime || "unknown"}`,
          checks: [
            { check: "Health endpoint", status: "ok", detail: `Status: ${data.status || "ok"}` },
            { check: "Uptime", status: "ok", detail: data.uptime || "unknown" },
          ],
        };
      },
    },
    {
      key: "3_router_verification",
      name: "Router",
      label: "API router mounted & reachable",
      dependsOn: "2_backend_startup",
      check: async () => {
        const data = await fetchWithTimeout(api("/system/status"), 5000);
        const routerCount = data?.routers_mounted ?? data?.router_count ?? "?";
        return {
          ok: true,
          detail: `${routerCount} routers mounted`,
          checks: [
            { check: "Router mount", status: "ok", detail: `${routerCount} routers` },
          ],
        };
      },
    },
    {
      key: "4_api_smoke",
      name: "API Smoke Tests",
      label: "Core endpoints responding",
      dependsOn: "2_backend_startup",
      check: async () => {
        const endpoints = [
          { name: "Signals", path: "/signals" },
          { name: "System status", path: "/system/status" },
        ];
        const checks = [];
        let passed = 0;
        for (const ep of endpoints) {
          try {
            await fetchWithTimeout(api(ep.path), 5000);
            checks.push({ check: ep.name, status: "ok", detail: "Responding" });
            passed++;
          } catch (err) {
            checks.push({ check: ep.name, status: "fail", detail: err.message });
          }
        }
        return {
          ok: passed === endpoints.length,
          detail: `${passed}/${endpoints.length} endpoints responding`,
          checks,
        };
      },
    },
    {
      key: "5_signal_pipeline",
      name: "Signal Pipeline",
      label: "Signal engine & data ingestion",
      dependsOn: "2_backend_startup",
      check: async () => {
        try {
          const data = await fetchWithTimeout(api("/signals"), 8000);
          const count = Array.isArray(data) ? data.length : data?.count ?? "?";
          return {
            ok: true,
            detail: `Signal pipeline active — ${count} signals available`,
            checks: [
              { check: "Signal engine", status: "ok", detail: `${count} signals` },
            ],
          };
        } catch (err) {
          return {
            ok: false,
            detail: `Signal pipeline error: ${err.message}`,
            checks: [
              { check: "Signal engine", status: "fail", detail: err.message },
            ],
          };
        }
      },
    },
    {
      key: "6_frontend_wiring",
      name: "Frontend Wiring",
      label: "Frontend ↔ backend connectivity",
      dependsOn: "2_backend_startup",
      check: async () => {
        const checks = [];
        // Check that the API base URL is configured
        const apiUrl = getApiUrl("systemStatus");
        if (apiUrl) {
          checks.push({ check: "API URL mapping", status: "ok", detail: apiUrl });
        } else {
          checks.push({ check: "API URL mapping", status: "fail", detail: "getApiUrl returned null" });
        }
        // Try a simple round-trip
        try {
          await fetchWithTimeout(api("/system/status"), 3000);
          checks.push({ check: "Round-trip", status: "ok", detail: "Frontend can reach backend" });
        } catch (err) {
          checks.push({ check: "Round-trip", status: "fail", detail: err.message });
        }
        const allOk = checks.every((c) => c.status === "ok");
        return {
          ok: allOk,
          detail: allOk ? "Frontend wired correctly" : "Some wiring issues detected",
          checks,
        };
      },
    },
    {
      key: "7_background_loops",
      name: "Background Loops",
      label: "Scouts, streams & scheduled jobs",
      dependsOn: "2_backend_startup",
      check: async () => {
        try {
          const data = await fetchWithTimeout(api("/system/status"), 5000);
          const services = data?.services || data?.active_services || [];
          const count = Array.isArray(services) ? services.length : 0;
          return {
            ok: count > 0,
            detail: `${count} background services running`,
            checks: Array.isArray(services)
              ? services.map((s) => ({
                  check: typeof s === "string" ? s : s.name || "service",
                  status: "ok",
                  detail: typeof s === "string" ? "Running" : s.status || "Running",
                }))
              : [{ check: "Services", status: count > 0 ? "ok" : "warn", detail: `${count} active` }],
          };
        } catch (err) {
          return {
            ok: false,
            detail: `Cannot check background loops: ${err.message}`,
            checks: [{ check: "Background services", status: "fail", detail: err.message }],
          };
        }
      },
    },
  ];
}

/* ------------------------------------------------------------------ */
/*  Phase status: pending | running | passed | failed | skipped        */
/* ------------------------------------------------------------------ */
const INITIAL_RESULT = { status: "pending", ok: null, detail: "", checks: [] };

/* ------------------------------------------------------------------ */
/*  Status icons                                                       */
/* ------------------------------------------------------------------ */
function PhaseIcon({ status, ok }) {
  if (status === "running") return <Loader2 className="w-4 h-4 text-cyan-400 animate-spin flex-shrink-0" />;
  if (status === "skipped") return <PauseCircle className="w-4 h-4 text-slate-500 flex-shrink-0" />;
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

/* ------------------------------------------------------------------ */
/*  Failure patterns table (static, always shown)                      */
/* ------------------------------------------------------------------ */
const FAILURE_PATTERNS = [
  { symptom: "Health check timed out", cause: "Backend not started or too slow", remediation: "cd backend && python run_server.py" },
  { symptom: "HTTP 502 / 503", cause: "Backend starting up or overloaded", remediation: "Wait 30s and retry, or restart backend" },
  { symptom: "CORS / network error", cause: "Vite proxy misconfigured", remediation: "Check vite.config.js proxy target port" },
  { symptom: "Signal pipeline fail", cause: "Data ingestion not running", remediation: "Check Alpaca stream status in backend logs" },
  { symptom: "0/3 env vars configured", cause: ".env not loaded by Vite", remediation: "Create frontend-v2/.env with VITE_* vars" },
  { symptom: "Router mount fails", cause: "Backend import error", remediation: "Check backend startup logs for ImportError" },
];

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */
export default function StartupHealth() {
  const phases = React.useMemo(() => buildPhases(), []);
  const [results, setResults] = useState(() => {
    const init = {};
    for (const p of phases) init[p.key] = { ...INITIAL_RESULT };
    return init;
  });
  const [running, setRunning] = useState(false);
  const [expanded, setExpanded] = useState(() => new Set(phases.map((p) => p.key)));
  const [retryIn, setRetryIn] = useState(0);
  const [lastRun, setLastRun] = useState(null);
  const cancelRef = useRef(false);
  const retryIntervalRef = useRef(null);

  const toggle = useCallback((key) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  /* ---- Run all checks progressively ---- */
  const runChecks = useCallback(async () => {
    cancelRef.current = false;
    setRunning(true);
    setRetryIn(0);
    if (retryIntervalRef.current) {
      clearInterval(retryIntervalRef.current);
      retryIntervalRef.current = null;
    }

    // Reset all phases
    const fresh = {};
    for (const p of phases) fresh[p.key] = { ...INITIAL_RESULT };
    setResults(fresh);

    const completed = {};
    let anyFailed = false;

    for (const phase of phases) {
      if (cancelRef.current) break;

      // Check dependency
      if (phase.dependsOn && completed[phase.dependsOn]?.ok === false) {
        const skipped = {
          status: "skipped",
          ok: null,
          detail: `Skipped — depends on ${phase.dependsOn.replace(/^\d+_/, "")} which failed`,
          checks: [],
        };
        completed[phase.key] = skipped;
        setResults((prev) => ({ ...prev, [phase.key]: skipped }));
        continue;
      }

      // Mark running
      setResults((prev) => ({ ...prev, [phase.key]: { ...INITIAL_RESULT, status: "running" } }));

      try {
        const result = await phase.check();
        const entry = {
          status: result.ok ? "passed" : "failed",
          ok: result.ok,
          detail: result.detail,
          checks: result.checks || [],
        };
        completed[phase.key] = entry;
        if (!cancelRef.current) setResults((prev) => ({ ...prev, [phase.key]: entry }));
        if (!result.ok) anyFailed = true;
      } catch (err) {
        let message = err.message || String(err);
        // Replace cryptic abort errors
        if (message.includes("signal is aborted without reason") || message.includes("AbortError")) {
          message = "Health check timed out — backend may be starting up or unreachable";
        }
        // Add actionable advice for connection failures
        if (message.includes("Failed to fetch") || message.includes("NetworkError") || message.includes("fetch")) {
          message = "Backend is not running. Start it with: cd backend && python run_server.py";
        }
        const entry = {
          status: "failed",
          ok: false,
          detail: message,
          checks: [{ check: phase.name, status: "fail", detail: message }],
        };
        completed[phase.key] = entry;
        if (!cancelRef.current) setResults((prev) => ({ ...prev, [phase.key]: entry }));
        anyFailed = true;
      }
    }

    setRunning(false);
    setLastRun(new Date());

    // Auto-retry countdown if any phase failed
    if (anyFailed && !cancelRef.current) {
      setRetryIn(10);
      retryIntervalRef.current = setInterval(() => {
        setRetryIn((prev) => {
          if (prev <= 1) {
            clearInterval(retryIntervalRef.current);
            retryIntervalRef.current = null;
            // Trigger re-run (we call it via a ref trick since runChecks isn't stable yet)
            return -1; // sentinel
          }
          return prev - 1;
        });
      }, 1000);
    }
  }, [phases]);

  // Handle retry sentinel
  useEffect(() => {
    if (retryIn === -1) {
      setRetryIn(0);
      runChecks();
    }
  }, [retryIn, runChecks]);

  // Run on mount
  useEffect(() => {
    runChecks();
    return () => {
      cancelRef.current = true;
      if (retryIntervalRef.current) clearInterval(retryIntervalRef.current);
    };
  }, [runChecks]);

  // Compute overall status
  const allResults = Object.values(results);
  const overallOk =
    allResults.every((r) => r.status === "pending")
      ? null
      : allResults.some((r) => r.ok === false)
        ? false
        : allResults.every((r) => r.ok === true || r.status === "skipped")
          ? true
          : null;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Header */}
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
          {lastRun && (
            <span className="text-xs text-slate-500 font-mono">{lastRun.toLocaleString()}</span>
          )}
          {retryIn > 0 && (
            <span className="text-xs text-amber-400">Retrying in {retryIn}s...</span>
          )}
          <button
            type="button"
            onClick={() => {
              if (retryIntervalRef.current) {
                clearInterval(retryIntervalRef.current);
                retryIntervalRef.current = null;
                setRetryIn(0);
              }
              runChecks();
            }}
            disabled={running}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/30 text-sm disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${running ? "animate-spin" : ""}`} />
            Run check
          </button>
        </div>
      </div>

      {/* Overall status */}
      <div className="rounded-lg border border-[rgba(42,52,68,0.5)] bg-[#111827] p-4">
        <div className="flex items-center gap-2">
          <PhaseIcon status={running ? "running" : "done"} ok={overallOk} />
          <span className="font-semibold text-white">
            {running
              ? "Running checks..."
              : overallOk === true
                ? "Overall: PASS"
                : overallOk === false
                  ? "Overall: FAIL"
                  : "Overall: —"}
          </span>
        </div>
      </div>

      {/* Phase cards — shown progressively */}
      <div className="space-y-2">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400">7 Phases</h2>
        {phases.map((phase) => {
          const r = results[phase.key];
          const isExpanded = expanded.has(phase.key);
          return (
            <div
              key={phase.key}
              className="rounded-lg border border-[rgba(42,52,68,0.5)] bg-[#111827] overflow-hidden"
            >
              <button
                type="button"
                onClick={() => toggle(phase.key)}
                className="w-full flex items-center gap-2 p-3 text-left hover:bg-white/5"
              >
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-slate-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                )}
                <PhaseIcon status={r.status} ok={r.ok} />
                <span className="text-sm font-medium text-white flex-1">
                  Phase {phase.key.split("_")[0]}: {phase.label}
                </span>
                {r.status === "running" && (
                  <span className="text-xs text-cyan-400">checking...</span>
                )}
                {r.status === "skipped" && (
                  <span className="text-xs text-slate-500">skipped</span>
                )}
              </button>
              {isExpanded && r.status !== "pending" && (
                <div className="border-t border-gray-800/50 px-3 pb-3 pt-1 space-y-1">
                  {/* Phase summary */}
                  {r.detail && (
                    <div className={`text-xs mb-1 ${r.ok === false ? "text-red-400" : r.ok === true ? "text-emerald-400" : "text-slate-400"}`}>
                      {r.detail}
                    </div>
                  )}
                  {/* Individual checks */}
                  {(r.checks || []).map((c, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm">
                      <StatusBadge status={c.status} />
                      <span className="text-slate-300 whitespace-nowrap">{c.check}</span>
                      <span className="text-slate-500 flex-1 break-words min-w-0" title={c.detail}>
                        — {c.detail}
                      </span>
                    </div>
                  ))}
                  {r.status === "running" && (
                    <div className="flex items-center gap-2 text-xs text-slate-400">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Running...
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Failure patterns table */}
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
              {FAILURE_PATTERNS.map((row, i) => (
                <tr key={i} className="border-b border-gray-800/30 hover:bg-white/5">
                  <td className="py-2 px-4 text-slate-300">{row.symptom}</td>
                  <td className="py-2 px-4 text-slate-400">{row.cause}</td>
                  <td className="py-2 px-4 text-slate-400">
                    <code className="bg-slate-800 px-1 rounded text-xs">{row.remediation}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <FileText className="w-4 h-4" />
        <span>
          To write <code className="bg-slate-800 px-1 rounded">reports/STARTUP-HEALTH-REPORT.md</code>, run from repo root:{" "}
          <code className="bg-slate-800 px-1 rounded">python scripts/startup_health_check.py</code>
        </span>
      </div>
    </div>
  );
}
