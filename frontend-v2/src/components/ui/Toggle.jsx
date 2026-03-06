import clsx from 'clsx';

/**
 * Reusable toggle (switch). Controlled via checked + onChange.
 * label and description are optional.
 */
export default function Toggle({
  checked = false,
  onChange,
  disabled = false,
  label,
  description,
  className,
}) {
  return (
    <div className={clsx('flex items-center justify-between gap-4', className)}>
      {(label || description) && (
        <div className="min-w-0">
          {label && <div className="text-sm font-medium text-white">{label}</div>}
          {description && <div className="text-xs text-secondary mt-0.5">{description}</div>}
        </div>
      )}
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={typeof label === 'string' ? label : undefined}
        disabled={disabled}
        onClick={() => onChange?.(!checked)}
        className={clsx(
          'relative inline-flex h-6 w-11 shrink-0 rounded-full border border-secondary/50 transition-colors focus:outline-none focus:ring-2 focus:ring-primary/40 focus:ring-offset-2 focus:ring-offset-dark',
          checked ? 'bg-primary' : 'bg-secondary/30',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <span 
          className={clsx(
            'pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow ring-0 transition translate-x-0.5 mt-[1px]',
            checked && 'translate-x-[21px]'
          )}
        />
      </button>
    </div>
  );
}
