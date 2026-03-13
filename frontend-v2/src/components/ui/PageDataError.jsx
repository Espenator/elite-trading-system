/**
 * Data fetch error state with retry — use when useApi().error is set.
 * Aurora dark theme; consistent with PageErrorFallback (crash boundary).
 */
export default function PageDataError({ error, onRetry, className = "" }) {
  return (
    <div className={`flex items-center justify-center min-h-[280px] p-6 ${className}`}>
      <div className="max-w-md text-center">
        <h2 className="text-lg font-bold text-red-400 mb-2">Failed to load data</h2>
        <p className="text-sm text-gray-400 mb-4">
          {error?.message || "Request failed. Check connection and try again."}
        </p>
        <div className="flex gap-3 justify-center">
          <button
            type="button"
            onClick={onRetry}
            className="px-4 py-2 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/30 text-sm font-medium"
          >
            Retry
          </button>
          <a
            href="/dashboard"
            className="px-4 py-2 rounded-lg bg-white/5 text-gray-300 border border-white/10 hover:bg-white/10 text-sm"
          >
            Dashboard
          </a>
        </div>
      </div>
    </div>
  );
}
