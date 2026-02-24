import clsx from "clsx";

const defaultTrack =
  "w-full h-2 rounded appearance-none bg-secondary/30 accent-cyan-500 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed";

/**
 * Reusable slider (range input) with optional label and value display.
 * @param {string} [label] - Label above the slider
 * @param {number} min - Minimum value
 * @param {number} max - Maximum value
 * @param {number} [step=1] - Step value
 * @param {number} value - Current value (controlled)
 * @param {function} [onChange] - (e) => {} or (value: number) => {}; omit for read-only
 * @param {string} [suffix] - Shown after value (e.g. "%", "s")
 * @param {function} [formatValue] - (value) => string for display; default is value.toString()
 * @param {boolean} [disabled] - Disable interaction
 * @param {boolean} [readOnly] - Same as disabled for display-only sliders
 * @param {boolean} [showValue=true] - Show value + suffix next to slider; set false when using an external input
 * @param {string} [className] - Wrapper div class
 * @param {string} [inputClassName] - Range input class
 * @param {string} [valueClassName] - Value span class
 */
function Slider({
  label,
  min,
  max,
  step = 1,
  value,
  onChange,
  suffix = "",
  formatValue,
  disabled = false,
  readOnly = false,
  showValue = true,
  className,
  inputClassName,
  valueClassName,
  id: idProp,
  ...rest
}) {
    const id = idProp || `slider-${crypto.randomUUID()}`;
  const isInteractive =
    !disabled && !readOnly && typeof onChange === "function";
  const displayValue = formatValue ? formatValue(value) : value;
  const handleChange = (e) => {
    if (typeof onChange === "function") onChange(e);
  };

  return (
    <div className={clsx("flex flex-col gap-1.5", className)}>
      {label && (
        <label
          htmlFor={id}
          className="text-xs text-secondary block font-medium"
        >
          {label}
        </label>
      )}
      <div className="flex items-center gap-2 w-full">
        <input
          id={id}
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={handleChange}
          disabled={!isInteractive}
          readOnly={readOnly && !onChange}
          className={clsx(defaultTrack, inputClassName)}
          aria-label={label}
          {...rest}
        />
        {showValue && (
          <span
            className={clsx(
              "text-xs text-cyan-400/80 shrink-0 min-w-[2rem]",
              valueClassName,
            )}
          >
            {displayValue}
            {suffix}
          </span>
        )}
      </div>
    </div>
  );
}

export default Slider;
