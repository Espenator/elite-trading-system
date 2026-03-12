/**
 * Shared loading skeleton with shimmer animation.
 * Use as fallback for Suspense or while useApi loading.
 * Aurora theme: dark bg, cyan shimmer.
 */
export default function PageSkeleton({ lines = 8, className = "" }) {
  return (
    <div
      className={`animate-pulse space-y-3 p-4 ${className}`}
      aria-busy="true"
      aria-label="Loading"
    >
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          className="h-4 rounded bg-[rgba(42,52,68,0.6)]"
          style={{
            width: i === 0 ? "60%" : i === lines - 1 ? "35%" : `${85 - i * 5}%`,
            animation: "shimmer 1.5s ease-in-out infinite",
          }}
        />
      ))}
      <style>{`
        @keyframes shimmer {
          0%, 100% { opacity: 0.4; }
          50% { opacity: 0.8; }
        }
      `}</style>
    </div>
  );
}

/** Card-style skeleton for dashboard/widget content */
export function CardSkeleton({ className = "" }) {
  return (
    <div
      className={`rounded-md border border-[rgba(42,52,68,0.5)] bg-[#111827]/80 p-4 ${className}`}
      aria-busy="true"
    >
      <div className="h-3 w-24 rounded bg-[rgba(42,52,68,0.6)] mb-3 animate-pulse" />
      <div className="h-6 w-32 rounded bg-[rgba(42,52,68,0.5)] animate-pulse" />
    </div>
  );
}
