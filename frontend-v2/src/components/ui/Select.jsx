import { forwardRef, useId } from 'react';
import clsx from 'clsx';
import { ChevronDown } from 'lucide-react';

/**
 * Reusable select dropdown.
 * options: array of { value, label } or string[] (value and label same).
 */
const Select = forwardRef(function Select(
  {
    label,
    options = [],
    error,
    placeholder,
    className,
    selectClassName,
    id: idProp,
    ...props
  },
  ref
) {
    const autoId = useId();
    const id = idProp || autoId;
  const baseSelect =
    'w-full px-4 py-2.5 bg-dark border border-secondary/50 rounded-xl text-sm text-white outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors disabled:opacity-50 appearance-none cursor-pointer';
  const errorSelect = 'border-danger focus:border-danger focus:ring-danger/30';

  const normalizedOptions = options.map((opt) =>
    typeof opt === 'string' ? { value: opt, label: opt } : opt
  );

  return (
    <div className={clsx('flex flex-col gap-1.5', className)}>
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-white">
          {label}
        </label>
      )}
      <div className="relative">
        <select
          ref={ref}
          id={id}
          className={clsx(
            baseSelect,
            error && errorSelect,
            selectClassName
          )}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {normalizedOptions.map(({ value, label: optLabel }) => (
            <option key={value} value={value}>
              {optLabel}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary" aria-hidden />
      </div>
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  );
});

export default Select;
