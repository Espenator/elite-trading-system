import clsx from 'clsx';

/**
 * Aurora Card — core surface component.
 *
 * Visual spec (matches mockups exactly):
 *   - Background: linear-gradient(145deg, #111827, #1F2937)
 *   - Border:     1px solid rgba(42,52,68,0.5)
 *   - Radius:     8px
 *   - Blur:       backdrop-filter blur(16px)
 *   - Shadow:     0 8px 32px rgba(0,0,0,0.3)
 *   - Hover glow: 0 0 20px rgba(0,217,255,0.3)  + border-color shifts to rgba(0,217,255,0.2)
 *
 * Props:
 *   title        string             — card header title
 *   subtitle     string             — optional sub-title below title
 *   action       ReactNode          — optional right-side element in header
 *   children     ReactNode          — card body
 *   className    string             — additional wrapper classes
 *   bodyClassName string            — additional body classes
 *   noPadding    bool               — skip default body padding
 *   loading      bool               — shows shimmer skeleton
 *   error        string | Error     — shows inline error message
 *   onRetry      function           — shows "Retry" link when error is set
 *   noHover      bool               — disable hover glow (for static info cards)
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
  noHover = false,
}) {
  return (
    <div
      className={clsx(
        // Aurora gradient base
        'relative overflow-hidden rounded-[8px]',
        // Gradient background via inline style (Tailwind can't express arbitrary gradients cleanly)
        'border',
        noHover ? '' : 'transition-all duration-300 group',
        className
      )}
      style={{
        background: 'linear-gradient(145deg, #111827, #1F2937)',
        borderColor: 'rgba(42,52,68,0.5)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
      }}
      onMouseEnter={
        noHover
          ? undefined
          : (e) => {
              e.currentTarget.style.boxShadow = '0 0 20px rgba(0,217,255,0.3)';
              e.currentTarget.style.borderColor = 'rgba(0,217,255,0.2)';
            }
      }
      onMouseLeave={
        noHover
          ? undefined
          : (e) => {
              e.currentTarget.style.boxShadow = '0 8px 32px rgba(0,0,0,0.3)';
              e.currentTarget.style.borderColor = 'rgba(42,52,68,0.5)';
            }
      }
    >
      {/* Card Header */}
      {(title || subtitle || action) && (
        <div
          className="px-4 py-3 flex items-center justify-between gap-2 flex-wrap"
          style={{ borderBottom: '1px solid rgba(42,52,68,0.5)' }}
        >
          <div className="min-w-0 flex-1">
            {title && (
              <h3 className="text-sm font-semibold text-white leading-tight truncate" title={typeof title === 'string' ? title : undefined}>
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-xs text-[#9CA3AF] mt-0.5">{subtitle}</p>
            )}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}

      {/* Card Body */}
      <div className={clsx(!noPadding && 'p-4', bodyClassName)}>
        {loading ? (
          <div className="space-y-3 animate-pulse">
            <div className="h-4 bg-white/5 rounded w-3/4" />
            <div className="h-4 bg-white/5 rounded w-1/2" />
            <div className="h-4 bg-white/5 rounded w-5/6" />
          </div>
        ) : error ? (
          <div className="text-center py-4">
            <p className="text-sm text-red-400 mb-2">
              {typeof error === 'string' ? error : error.message || 'Failed to load'}
            </p>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="text-xs text-[#00D9FF] hover:text-[#00D9FF]/80 underline transition-colors"
              >
                Retry
              </button>
            )}
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
