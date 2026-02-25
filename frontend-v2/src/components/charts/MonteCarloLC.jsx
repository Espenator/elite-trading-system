import React from "react";

/**
 * MonteCarloLC - Monte Carlo simulation chart using lightweight-charts
 * 
 * TODO: Replace placeholder bars with createChart() from lightweight-charts.
 * Props:
 *   - data: Array of simulation paths, e.g. [{ day, p5, p25, p50, p75, p95 }]
 *   - height: Chart height in pixels (default 220)
 *   - showPercentiles: Show percentile legend (default true)
 *
 * This stub renders a mini bar-chart placeholder so the page compiles.
 * Oleh: wire this up with lightweight-charts AreaSeries for each percentile band.
 */

const PERCENTILE_COLORS = [
  { label: "5th", color: "#ef4444" },
  { label: "25th", color: "#f97316" },
  { label: "50th", color: "#eab308" },
  { label: "75th", color: "#22c55e" },
  { label: "95th", color: "#10b981" },
];

export default function MonteCarloLC({ data = [], height = 220, showPercentiles = true }) {
  const hasData = Array.isArray(data) && data.length > 0;

  if (!hasData) {
    return (
      <div className="flex items-center justify-center h-full text-slate-500 text-sm">
        <div className="text-center">
          <div className="text-2xl mb-2">🎲</div>
          <div>Awaiting Monte Carlo data from API</div>
          <div className="text-xs text-slate-600 ml-1">Connect to /api/v1/performance</div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="absolute top-1 left-1 z-10">
        <span className="text-xs font-bold text-white uppercase tracking-wider">
          Monte Carlo Sim
        </span>
      </div>

      {/* Placeholder mini-bars until lightweight-charts is wired */}
      <div className="flex items-end justify-center h-full px-4 pb-4 pt-10 gap-[2px]">
        {data.slice(-60).map((point, i) => {
          const value = point.p50 ?? point.value ?? 0;
          const max = Math.max(...data.slice(-60).map(d => d.p95 ?? d.p50 ?? d.value ?? 0));
          const min = Math.min(...data.slice(-60).map(d => d.p5 ?? d.p50 ?? d.value ?? 0));
          const range = max - min || 1;
          const h = ((value - min) / range) * (height - 60);
          const isUp = i > 0 ? value >= (data.slice(-60)[i - 1]?.p50 ?? data.slice(-60)[i - 1]?.value ?? 0) : true;
          return (
            <div
              key={i}
              className={`w-1.5 rounded-t ${isUp ? 'bg-emerald-500/60' : 'bg-red-500/60'}`}
              style={{ height: `${Math.max(2, h)}px` }}
            />
          );
        })}
      </div>

      {/* Percentile legend */}
      {showPercentiles && (
        <div className="flex justify-center gap-3 text-[9px] mt-1 pb-1">
          {PERCENTILE_COLORS.map(({ label, color }) => (
            <span key={label} className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: color }} />
              <span className="text-slate-400">{label}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
