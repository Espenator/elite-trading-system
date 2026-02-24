import clsx from 'clsx';

/**
 * Reusable card. Optional title, optional padding control.
 */
export default function Card({
  title,
  subtitle,
  action,
  children,
  className,
  bodyClassName,
  noPadding,
}) {
  return (
    <div
      className={clsx(
        'bg-secondary/10 border border-secondary/50 rounded-xl overflow-hidden',
        className
      )}
    >
      {(title || subtitle || action) && (
        <div className="px-4 py-3 border-b border-secondary/50 flex items-center justify-between gap-3">
          <div className="min-w-0">
            {title && <h3 className="text-sm font-semibold text-white">{title}</h3>}
            {subtitle && <p className="text-xs text-secondary mt-0.5">{subtitle}</p>}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}
      <div className={clsx(!noPadding && 'p-4', bodyClassName)}>{children}</div>
    </div>
  );
}
