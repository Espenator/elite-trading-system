import clsx from "clsx";
import { useRef, useEffect } from "react";

const sizes = {
  sm: "w-4 h-4",
  md: "w-5 h-5",
};

/**
 * Best-in-class checkbox: custom UI, full accessibility, optional indeterminate.
 * Uses hidden native input for semantics; custom box + checkmark for visuals.
 *
 * @param {boolean} checked - Checked state
 * @param {boolean} [indeterminate] - Indeterminate state (e.g. "some selected")
 * @param {function} [onChange] - (e) => {}; omit for read-only
 * @param {string|React.ReactNode} [label] - Label text or node
 * @param {boolean} [disabled] - Disable interaction
 * @param {boolean} [readOnly] - No interaction, same as disabled
 * @param {string} [size] - 'sm' | 'md' (default: 'md')
 * @param {string} [className] - Wrapper class
 * @param {string} [id] - Optional id for input
 */
function Checkbox({
  checked = false,
  indeterminate = false,
  onChange,
  label,
  disabled = false,
  readOnly = false,
  size = "md",
  className,
  id: idProp,
  ...rest
}) {
  const inputRef = useRef(null);
  const id = idProp || `checkbox-${Math.random().toString(36).slice(2, 9)}`;
  const isInteractive =
    !disabled && !readOnly && typeof onChange === "function";
  const sizeClass = sizes[size] || sizes.md;

  // Indeterminate is a DOM property, not an HTML attribute
  useEffect(() => {
    if (inputRef.current) inputRef.current.indeterminate = !!indeterminate;
  }, [indeterminate]);

  const box = (
    <span
      className={clsx(
        "inline-flex shrink-0 items-center justify-center rounded border-2 transition-all duration-200",
        sizeClass,
        checked && !indeterminate
          ? "border-cyan-500 bg-cyan-500 text-white"
          : indeterminate
            ? "border-cyan-500 bg-cyan-500/20 text-cyan-400"
            : "border-cyan-500/40 bg-transparent text-transparent",
        !isInteractive && "opacity-70 cursor-default",
      )}
      aria-hidden
    >
      {checked && !indeterminate && (
        <svg
          className={size === "sm" ? "w-2.5 h-2.5" : "w-3 h-3"}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={3}
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M5 13l4 4L19 7" />
        </svg>
      )}
      {indeterminate && !checked && (
        <svg
          className={size === "sm" ? "w-2.5 h-2.5" : "w-3 h-3"}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={3}
          strokeLinecap="round"
        >
          <path d="M5 12h14" />
        </svg>
      )}
    </span>
  );

  const input = (
    <input
      ref={inputRef}
      type="checkbox"
      id={id}
      checked={checked}
      onChange={(e) => onChange?.(e)}
      disabled={!isInteractive}
      readOnly={readOnly && !onChange}
      aria-label={typeof label === "string" ? label : undefined}
      aria-checked={indeterminate ? "mixed" : checked}
      className="sr-only"
      {...rest}
    />
  );

  const wrapperClass = clsx(
    "inline-flex items-center gap-2.5 select-none rounded focus-within:outline-none",
    isInteractive && "cursor-pointer",
    !isInteractive && "cursor-default",
    className,
  );

  if (!label) {
    return (
      <label className={wrapperClass} htmlFor={id}>
        {input}
        {box}
      </label>
    );
  }

  return (
    <label className={wrapperClass} htmlFor={id}>
      {input}
      {box}
      {typeof label === "string" ? (
        <span className="text-sm text-secondary leading-none">{label}</span>
      ) : (
        label
      )}
    </label>
  );
}

export default Checkbox;
