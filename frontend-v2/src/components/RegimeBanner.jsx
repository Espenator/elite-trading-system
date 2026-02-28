/**
 * Feature 1: Macro Wave Gauge (CLAWBOT_PANEL_DESIGN.md)
 * Custom SVG arc gauge for fear/greed oscillator; red = fear, green = greed.
 * Bias multiplier badge (+1.5x longs). Compact for header.
 */
import { useMemo } from "react";

const GAUGE_SIZE = 36;
const RADIUS = 14;
const STROKE_WIDTH = 4;
const CENTER = GAUGE_SIZE / 2;
const CIRCUMFERENCE = Math.PI * RADIUS; // half-circle arc

function normalizeOscillator(value) {
  if (value == null || Number.isNaN(value)) return 0.5;
  if (value <= 1 && value >= -1) return (value + 1) / 2;
  if (value <= 100 && value >= 0) return value / 100;
  return Math.max(0, Math.min(1, Number(value)));
}

function getGaugeColor(fill) {
  if (fill <= 0.33) return "#ef4444"; // red = fear
  if (fill <= 0.66) return "#eab308"; // yellow = neutral
  return "#22c55e"; // green = greed
}

export default function RegimeBanner({
  oscillator = 0,
  wave = "NEUTRAL",
  bias = 1.0,
}) {
  const fill = useMemo(() => normalizeOscillator(oscillator), [oscillator]);
  const color = useMemo(() => getGaugeColor(fill), [fill]);
  const mood = fill <= 0.33 ? "Fear" : fill <= 0.66 ? "Neutral" : "Greed";
  const waveLabel = wave ? String(wave).toUpperCase().slice(0, 8) : "--";
  const biasText =
    bias != null && !Number.isNaN(bias)
      ? `${Number(bias).toFixed(1)}x`
      : "1.0x";

  // SVG arc gauge: half-circle from left to right
  const dashOffset = CIRCUMFERENCE * (1 - fill);

  return (
    <div
      className="flex items-center gap-2 px-2.5 py-1 rounded-lg border border-secondary/30 bg-secondary/10 shrink-0 max-w-[200px]"
      title={`${mood} \u00B7 ${wave} \u00B7 Bias +${biasText} longs`}
    >
      <svg
        width={GAUGE_SIZE}
        height={GAUGE_SIZE}
        viewBox={`0 0 ${GAUGE_SIZE} ${GAUGE_SIZE}`}
        className="shrink-0"
        aria-hidden
      >
        {/* Background arc */}
        <circle
          cx={CENTER}
          cy={CENTER}
          r={RADIUS}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={STROKE_WIDTH}
          strokeDasharray={`${CIRCUMFERENCE} ${CIRCUMFERENCE}`}
          strokeDashoffset={0}
          strokeLinecap="round"
          transform={`rotate(180, ${CENTER}, ${CENTER})`}
        />
        {/* Value arc */}
        <circle
          cx={CENTER}
          cy={CENTER}
          r={RADIUS}
          fill="none"
          stroke={color}
          strokeWidth={STROKE_WIDTH}
          strokeDasharray={`${CIRCUMFERENCE} ${CIRCUMFERENCE}`}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          transform={`rotate(180, ${CENTER}, ${CENTER})`}
          style={{ transition: "stroke-dashoffset 0.3s ease" }}
        />
        {/* Center value text */}
        <text
          x={CENTER}
          y={CENTER + 2}
          textAnchor="middle"
          fill={color}
          fontSize="9"
          fontWeight="bold"
        >
          {Math.round(fill * 100)}
        </text>
      </svg>
      <span className="text-[11px] font-medium text-secondary ">{mood}</span>
      <span className="text-secondary/60">\u00B7</span>
      <span className="text-[11px] text-secondary truncate">{waveLabel}</span>
      <span
        className="text-[11px] font-semibold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 shrink-0"
        title="Bias multiplier (longs)"
      >
        +{biasText} longs
      </span>
    </div>
  );
}
