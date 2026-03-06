import clsx from 'clsx';

/**
 * Inline banner shown when API data is stale (served from cache after fetch failure).
 * Pair with useApi's `isStale` + `lastUpdated` return values.
 */
export default function StaleBanner({ isStale, lastUpdated, onRetry, className }) {
  if (!isStale) return null;
  const age = lastUpdated ? Math.round((Date.now() - lastUpdated) / 1000) : null;
  return (
    <div className={clsx(
      "flex items-center gap-2 px-3 py-1.5 rounded-lg bg-warning/10 border border-warning/30 text-warning text-xs",
      className
    )}>
      <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 16 16"><path d="M8 1l7 14H1L8 1z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" /><path d="M8 6v4M8 12v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
      <span>Data may be outdated{age ? ` (${age}s ago)` : ''}</span>
      {onRetry && (
        <button type="button" onClick={onRetry} className="ml-auto underline hover:text-warning/80">
          Retry
        </button>
      )}
    </div>
  );
}
