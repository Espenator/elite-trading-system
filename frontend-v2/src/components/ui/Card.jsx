import clsx from 'clsx';

/**
 * Reusable card. Optional title, optional padding control.
 * loading: shows shimmer skeleton overlay
 * error: shows inline error with optional retry
 */
export default function Card({
  title,
  subtitle,
  action,
  children,
  className,
  bodyClassName,
  noPadding,
  loading,
  error,
  onRetry,
}) {
  return (
    <div
      className={clsx(
        'bg-surface border border-secondary/20 rounded-md overflow-hidden relative',
        className
      )}
    >
      {(title || subtitle || action) && (
        <div className="px-4 py-3 border-b border-secondary/20 flex items-center justify-between gap-3">
          <div className="min-w-0">
            {title && <h3 className="text-sm font-semibold text-white">{title}</h3>}
            {subtitle && <p className="text-xs text-secondary mt-0.5">{subtitle}</p>}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}
      <div className={clsx(!noPadding && 'p-4', bodyClassName)}>
        {loading ? (
          <div className="space-y-3 animate-pulse">
            <div className="h-4 bg-secondary/20 rounded w-3/4" />
            <div className="h-4 bg-secondary/20 rounded w-1/2" />
            <div className="h-4 bg-secondary/20 rounded w-5/6" />
          </div>
        ) : error ? (
          <div className="text-center py-4">
            <p className="text-sm text-red-400 mb-2">{typeof error === 'string' ? error : error.message || 'Failed to load'}</p>
            {onRetry && <button type="button" onClick={onRetry} className="text-xs text-cyan-400 hover:text-cyan-300 underline">Retry</button>}
          </div>
        ) : children}
      </div>
    </div>
  );
}
