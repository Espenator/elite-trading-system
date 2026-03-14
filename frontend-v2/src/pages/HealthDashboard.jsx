import { useApi } from "../hooks/useApi";

const STATUS_COLORS = {
  healthy: "bg-emerald-400",
  ok: "bg-emerald-400",
  active: "bg-emerald-400",
  degraded: "bg-amber-400",
  unreachable: "bg-amber-400",
  not_configured: "bg-gray-500",
  error: "bg-red-500",
  idle: "bg-blue-400",
  unknown: "bg-gray-500",
};

function Dot({ status }) {
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full mr-2 ${STATUS_COLORS[status] ?? "bg-gray-500"}`}
    />
  );
}

function StatRow({ label, value, status }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-white/5 text-sm">
      <span className="text-gray-400">{label}</span>
      <span className="font-mono">
        {status && <Dot status={status} />}
        {value ?? "—"}
      </span>
    </div>
  );
}

function Panel({ title, children, unreachable }) {
  return (
    <div
      className={`rounded-lg p-5 space-y-2 border ${
        unreachable
          ? "border-amber-500/40 bg-amber-900/10"
          : "border-[rgba(42,52,68,0.5)] bg-[#111827]"
      }`}
    >
      <h2 className="font-semibold text-lg mb-3">{title}</h2>
      {unreachable ? (
        <div className="text-amber-400 font-mono text-sm">UNREACHABLE</div>
      ) : (
        children
      )}
    </div>
  );
}

export default function HealthDashboard() {
  const { data: health, loading, error, lastUpdated } = useApi("systemHealth", {
    pollIntervalMs: 10_000,
  });

  if (loading && !health) {
    return <div className="p-6 text-gray-400">Loading system health...</div>;
  }

  if (error && !health) {
    return (
      <div className="p-6 text-red-400">
        Health fetch failed: {error.message ?? String(error)}
      </div>
    );
  }

  if (!health) return null;

  const { pc1, pc2, council_mode, redis_mesh } = health;
  const pc2Data = pc2?.data ?? {};
  const pc2Reachable = pc2?.status === "healthy";
  const lastDecision = pc1?.last_decision;

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">System Health</h1>
        <span className="text-xs text-gray-500">
          Updated {lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : "—"}
        </span>
      </div>

      {/* Council Mode Banner */}
      <div
        className={`p-3 rounded-lg font-semibold text-sm ${
          council_mode === "FULL"
            ? "bg-emerald-900/40 text-emerald-300 border border-emerald-700/40"
            : "bg-amber-900/40 text-amber-300 border border-amber-700/40"
        }`}
      >
        <Dot status={council_mode === "FULL" ? "healthy" : "degraded"} />
        Council Mode: {council_mode}
        {council_mode === "DEGRADED" &&
          " — PC2 unreachable, hypothesis using CPU fallback (conf=0.1)"}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* PC1 Panel */}
        <Panel title="PC1 — ESPENMAIN">
          <StatRow label="API Server" value="healthy" status="healthy" />
          <StatRow
            label="Council Runner"
            value={pc1?.council_runner ?? "unknown"}
            status={pc1?.council_runner === "active" ? "active" : "idle"}
          />
          <StatRow
            label="Redis"
            value={pc1?.redis ?? "unknown"}
            status={pc1?.redis === "healthy" ? "healthy" : pc1?.redis === "not_configured" ? "not_configured" : "error"}
          />
          <StatRow
            label="DuckDB"
            value={pc1?.duckdb ?? "unknown"}
            status={pc1?.duckdb === "ok" || pc1?.duckdb === "healthy" ? "healthy" : "error"}
          />
          {lastDecision && (
            <>
              <div className="pt-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                Last Decision
              </div>
              <StatRow label="Symbol" value={lastDecision.symbol} />
              <StatRow label="Direction" value={lastDecision.direction} />
              <StatRow
                label="Confidence"
                value={
                  lastDecision.confidence != null
                    ? `${(lastDecision.confidence * 100).toFixed(1)}%`
                    : "—"
                }
              />
              <StatRow
                label="At"
                value={
                  lastDecision.created_at
                    ? new Date(lastDecision.created_at).toLocaleTimeString()
                    : "—"
                }
              />
            </>
          )}
        </Panel>

        {/* PC2 Panel */}
        <Panel title="PC2 — ProfitTrader" unreachable={!pc2Reachable}>
          {pc2Reachable && (
            <>
              <StatRow
                label="brain_service gRPC"
                value={pc2Data.grpc_status ?? "healthy"}
                status="healthy"
              />
              <StatRow
                label="GPU Worker"
                value={pc2Data.gpu_worker ?? "active"}
                status="active"
              />
              <StatRow
                label="PyTorch CUDA"
                value={pc2Data.cuda_available ? "yes" : "no"}
                status={pc2Data.cuda_available ? "healthy" : "error"}
              />
              <StatRow
                label="VRAM Used"
                value={
                  pc2Data.vram_used_gb
                    ? `${pc2Data.vram_used_gb.toFixed(1)} / 17.2 GB`
                    : "—"
                }
              />
              {(pc2Data.loaded_models ?? []).length > 0 && (
                <>
                  <div className="pt-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                    Loaded Models
                  </div>
                  {pc2Data.loaded_models.map((m) => (
                    <StatRow
                      key={m.name}
                      label={m.name}
                      value={`${m.vram_gb?.toFixed(1) ?? "?"}GB`}
                      status="healthy"
                    />
                  ))}
                </>
              )}
              {pc2Data.last_inference && (
                <>
                  <div className="pt-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                    Last Inference
                  </div>
                  <StatRow label="Model" value={pc2Data.last_inference.model} />
                  <StatRow
                    label="Latency"
                    value={`${pc2Data.last_inference.latency_ms?.toFixed(0)}ms`}
                  />
                  <StatRow
                    label="Confidence"
                    value={`${(pc2Data.last_inference.confidence * 100).toFixed(1)}%`}
                  />
                </>
              )}
            </>
          )}
        </Panel>
      </div>

      {/* System-wide row */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-lg p-4 bg-[#111827] border border-[rgba(42,52,68,0.5)] text-sm">
          <div className="text-gray-400 mb-1">Redis Mesh</div>
          <div className="font-mono">
            <Dot status={redis_mesh === "healthy" ? "healthy" : "error"} />
            {redis_mesh ?? "unknown"}
          </div>
        </div>
        <div className="rounded-lg p-4 bg-[#111827] border border-[rgba(42,52,68,0.5)] text-sm">
          <div className="text-gray-400 mb-1">PC1 → PC2 gRPC</div>
          <div className="font-mono">
            <Dot status={pc2Reachable ? "healthy" : "unreachable"} />
            {pc2Reachable ? "connected" : "unreachable"}
          </div>
        </div>
        <div className="rounded-lg p-4 bg-[#111827] border border-[rgba(42,52,68,0.5)] text-sm">
          <div className="text-gray-400 mb-1">Council Mode</div>
          <div
            className={`font-mono font-semibold ${
              council_mode === "FULL" ? "text-emerald-400" : "text-amber-400"
            }`}
          >
            {council_mode}
          </div>
        </div>
      </div>
    </div>
  );
}
