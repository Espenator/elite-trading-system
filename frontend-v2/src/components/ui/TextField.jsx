import { forwardRef } from 'react';
import clsx from 'clsx';

const baseInput =
  'w-full px-4 py-2.5 bg-dark border border-secondary/50 rounded-xl text-sm text-white placeholder-secondary outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed';
const errorInput = 'border-danger focus:border-danger focus:ring-danger/30';

const TextField = forwardRef(function TextField(
  { label, error, multiline = false, rows = 3, suffix, className, inputClassName, id: idProp, ...props },
  ref
) {
  const id = idProp || `textfield-${Math.random().toString(36).slice(2, 9)}`;
  const inputEl = multiline ? (
    <textarea
      ref={ref}
      id={id}
      rows={rows}
      className={clsx(baseInput, 'resize-y min-h-[80px]', error && errorInput, inputClassName)}
      {...props}
    />
  ) : (
    <input
      ref={ref}
      id={id}
      type="text"
      className={clsx(baseInput, error && errorInput, inputClassName)}
      {...props}
    />
  );

  return (
    <div className={clsx('flex flex-col gap-1.5', className)}>
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-white">
          {label}
        </label>
      )}
      {suffix && !multiline ? (
        <div className="relative">
          {inputEl}
          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-secondary pointer-events-none">{suffix}</span>
        </div>
      ) : (
        inputEl
      )}
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  );
});

export default TextField;
