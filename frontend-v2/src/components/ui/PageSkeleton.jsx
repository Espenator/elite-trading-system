/**
 * Consistent loading skeleton with shimmer for all pages.
 * Aurora dark theme — use when useApi().loading is true.
 */
export default function PageSkeleton({ lines = 8, className = "" }) {
  return (
    <div className={`animate-pulse space-y-3 p-4 ${className}`}>
      {/* Header bar */}
      <div className="h-6 w-48 rounded bg-white/5" />
      <div className="flex gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-20 flex-1 rounded-md bg-white/5" />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="h-32 rounded-md bg-white/5" style={{ animationDelay: `${i * 50}ms` }} />
        ))}
      </div>
      {Array.from({ length: Math.min(lines, 12) }).map((_, i) => (
        <div
          key={i}
          className="h-4 rounded bg-white/5"
          style={{
            width: i % 3 === 0 ? "100%" : i % 3 === 1 ? "85%" : "70%",
            animationDelay: `${i * 30}ms`,
          }}
        />
      ))}
    </div>
  );
}

/** Shimmer overlay — add to parent with overflow-hidden for shimmer effect */
export function ShimmerOverlay() {
  return (
    <div
      className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/5 to-transparent animate-[shimmer_1.5s_ease-in-out_infinite]"
      aria-hidden
    />
  );
}
