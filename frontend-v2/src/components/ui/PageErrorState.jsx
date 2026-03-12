/**
 * Inline error state for useApi (or similar) with retry.
 * Use when data fetch fails; does not replace page-level ErrorBoundary.
 */
import { AlertCircle } from "lucide-react";

export default function PageErrorState({ error, onRetry, message }) {
  const msg = message || error?.message || "Failed to load data.";
  return (
    <div
      className="flex flex-col items-center justify-center rounded-lg border border-red-500/30 bg-red-500/5 p-6 text-center"
      role="alert"
    >
      <AlertCircle className="w-10 h-10 text-red-400 mb-3 shrink-0" />
      <p className="text-sm text-gray-300 mb-4 max-w-md">{msg}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="px-4 py-2 rounded-lg text-sm font-medium bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/30 transition-colors"
        >
          Try again
        </button>
      )}
    </div>
  );
}
