import { useId } from "react";
import clsx from "clsx";

/**
 * Slider with gradient track and white thumb (dark theme).
 * Layout: label (left) | slider (center) | value (right)
 *
 * @param {string} [label] - Label on the left of the slider
 * @param {number} min - Minimum value
 * @param {number} max - Maximum value
 * @param {number} [step=1] - Step value
 * @param {number} value - Current value (controlled)
 * @param {function} [onChange] - (value: number) => {}
 * @param {string} [suffix] - Shown after value (e.g. "%")
 * @param {function} [formatValue] - (value) => string for display
 * @param {boolean} [disabled] - Disable interaction
 * @param {boolean} [readOnly] - Same as disabled
 * @param {boolean} [showValue=true] - Show value + suffix on the right
 * @param {string} [className] - Wrapper div class
 * @param {string} [inputClassName] - Range input class
 * @param {string} [valueClassName] - Value span class
 * @param {boolean} [labelAbove] - If true, label renders above (legacy layout)
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
  labelAbove = false,
  id: idProp,
  ...rest
}) {
  const autoId = useId();
  const id = idProp || autoId;
  const isInteractive =
    !disabled && !readOnly && typeof onChange === "function";
  const displayValue = formatValue ? formatValue(value) : value;
  const pct = max > min ? Math.round(((value - min) / (max - min)) * 100) : 0;

  const handleChange = (e) => {
    if (typeof onChange === "function") {
      const raw = e.target.value;
      const num = step >= 1 ? parseInt(raw, 10) : parseFloat(raw);
      onChange(Number.isNaN(num) ? value : num);
    }
  };

  // Gradient: blue (#6A82FB) → cyan (#00C6FF) on filled portion; dark grey (#374151) on unfilled
  const trackStyle = {
    background: `linear-gradient(to right, #6A82FB 0%, #00C6FF ${pct}%, #374151 ${pct}%, #374151 100%)`,
  };

  return (
    <div className={clsx("w-full", className)}>
      {labelAbove && label && (
        <label
          htmlFor={id}
          className="text-xs text-secondary block font-medium mb-1.5"
        >
          {label}
        </label>
      )}
      <div
        className={clsx(
          "flex items-center gap-2 w-full",
          !labelAbove && "gap-3",
        )}
      >
        {label && !labelAbove && (
          <label
            htmlFor={id}
            title={label}
            className="text-xs text-gray-400 font-medium shrink-0 max-w-[7rem] truncate"
          >
            {label}
          </label>
        )}
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
          style={trackStyle}
          className={clsx(
            "slider-gradient-track flex-1 min-w-[4rem] h-1.5 rounded-full appearance-none cursor-pointer",
            "focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed",
            "transition-none",
            inputClassName,
          )}
          aria-label={label}
          {...rest}
        />
        {showValue && (
          <span
            className={clsx(
              "text-xs text-gray-400 font-medium shrink-0 min-w-[10px] w-[30px] text-right tabular-nums",
              valueClassName,
            )}
          >
            {displayValue}
            {suffix}
          </span>
        )}
      </div>
      <style>{`
        .slider-gradient-track::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: #FFFFFF;
          cursor: pointer;
          box-shadow: 0 0 0 1px rgba(0,0,0,0.1);
        }
        .slider-gradient-track::-webkit-slider-thumb:hover {
          background: #F3F4F6;
        }
        .slider-gradient-track::-moz-range-thumb {
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: #FFFFFF;
          cursor: pointer;
          border: none;
          box-shadow: 0 0 0 1px rgba(0,0,0,0.1);
        }
        .slider-gradient-track::-moz-range-thumb:hover {
          background: #F3F4F6;
        }
      `}</style>
    </div>
  );
}

export default Slider;
