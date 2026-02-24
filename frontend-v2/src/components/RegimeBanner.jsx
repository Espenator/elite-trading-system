/**
 * Feature 1: Macro Wave Gauge (CLAWBOT_PANEL_DESIGN.md)
 * Recharts radial chart for fear/greed oscillator; red = fear, green = greed.
 * Bias multiplier badge (+1.5x longs). Compact for header.
 */
import { useMemo } from "react";
import {
  RadialBarChart,
  RadialBar,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

const GAUGE_SIZE = 36;

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
  const chartData = useMemo(
    () => [{ name: "oscillator", value: fill * 100, fill: color }],
    [fill, color],
  );

  const mood = fill <= 0.33 ? "Fear" : fill <= 0.66 ? "Neutral" : "Greed";
  const waveLabel = wave ? String(wave).toUpperCase().slice(0, 8) : "—";
  const biasText =
    bias != null && !Number.isNaN(bias)
      ? `${Number(bias).toFixed(1)}x`
      : "1.0x";

  return (
    <div
      className="flex items-center gap-2 px-2.5 py-1 rounded-lg border border-secondary/30 bg-secondary/10 shrink-0 max-w-[200px]"
      title={`${mood} · ${wave} · Bias +${biasText} longs`}
    >
      <div
        className="shrink-0"
        style={{ width: GAUGE_SIZE, height: GAUGE_SIZE }}
        aria-hidden
      >
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            innerRadius="70%"
            outerRadius="100%"
            data={chartData}
            startAngle={90}
            endAngle={-270}
          >
            <RadialBar
              dataKey="value"
              background={{ fill: "rgba(255,255,255,0.08)" }}
              cornerRadius={4}
            />
            <Tooltip
              contentStyle={{
                background: "hsl(220 20% 12%)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
              }}
              formatter={(value) => [
                `${Number(value).toFixed(0)}% · ${mood}`,
                "Oscillator",
              ]}
            />
          </RadialBarChart>
        </ResponsiveContainer>
      </div>
      <span className="text-[11px] font-medium text-secondary ">{mood}</span>
      <span className="text-secondary/60">·</span>
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
