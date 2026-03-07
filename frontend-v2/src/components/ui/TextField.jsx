import { forwardRef, useId, useState } from 'react';
import clsx from 'clsx';
import { Eye, EyeOff } from 'lucide-react';

const baseInput =
  'w-full px-4 py-2.5 bg-dark border border-secondary/50 rounded-md text-sm text-white placeholder-secondary outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed';
const errorInput = 'border-danger focus:border-danger focus:ring-danger/30';

const TextField = forwardRef(function TextField(
  { label, error, multiline = false, rows = 3, suffix, prefix, className, inputClassName, id: idProp, type: typeProp = 'text', ...props },
  ref
) {
    const autoId = useId();
    const id = idProp || autoId;
  const isPassword = typeProp === 'password';
  const [visible, setVisible] = useState(false);
  const inputType = isPassword ? (visible ? 'text' : 'password') : typeProp;
  const hasPrefix = prefix && !multiline;

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
      type={inputType}
      className={clsx(baseInput, error && errorInput, isPassword && 'pr-11', hasPrefix && 'pl-10', inputClassName)}
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
      {isPassword && !multiline ? (
        <div className="relative">
          {inputEl}
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 rounded-lg text-secondary hover:text-white hover:bg-secondary/20 transition-colors focus:outline-none focus:ring-2 focus:ring-primary/50"
            aria-label={visible ? 'Hide password' : 'Show password'}
            tabIndex={-1}
          >
            {visible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
      ) : suffix && !multiline ? (
        <div className="relative">
          {inputEl}
          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-secondary pointer-events-none">{suffix}</span>
        </div>
      ) : hasPrefix ? (
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-secondary pointer-events-none flex items-center">{prefix}</span>
          {inputEl}
        </div>
      ) : (
        inputEl
      )}
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  );
});

export default TextField;
