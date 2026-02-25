// RiskEquityLC - Lightweight Charts equity curve for Risk Intelligence page
// TODO(@oleh-savenko): Replace placeholder with real TradingView Lightweight Charts implementation
// This component should render an equity curve using createChart() from 'lightweight-charts'
// wired to the /api/v1/risk/equity endpoint via useApi hook.
//
// Props: { data, height, timeframe, showBenchmark }
// Data shape: Array<{ time: number, value: number }>

import React from "react";

export default function RiskEquityLC({ data = [], height = 300, timeframe = "1M", showBenchmark = true }) {
  // Placeholder - will be replaced with lightweight-charts canvas
  const hasData = data && data.length > 0;

  return (
    <div
      className="relative rounded-lg border border-slate-700/50 bg-slate-900/40 overflow-hidden"
      style={{ height: `${height}px` }}
    >
      {/* Header */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
        <span className="text-xs font-bold text-white uppercase tracking-wider">
          Equity Curve
        </span>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-400 font-mono">
          {timeframe}
        </span>
        {showBenchmark && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-400 font-mono">
            vs SPY
          </span>
        )}
      </div>

      {hasData ? (
        // TODO: Replace with createChart() from lightweight-charts
        <div className="flex items-end justify-center h-full px-4 pb-4 pt-10 gap-[2px]">
          {data.slice(-60).map((point, i) => {
            const max = Math.max(...data.slice(-60).map(d => d.value));
            const min = Math.min(...data.slice(-60).map(d => d.value));
            const range = max - min || 1;
            const h = ((point.value - min) / range) * (height - 60);
            const isUp = i > 0 ? point.value >= data.slice(-60)[i - 1]?.value : true;
            return (
              <div
                key={i}
                className={`w-1.5 rounded-t ${isUp ? 'bg-emerald-500/60' : 'bg-red-500/60'}`}
                style={{ height: `${Math.max(2, h)}px` }}
              />
            );
          })}
        </div>
      ) : (
        <div className="flex items-center justify-center h-full text-slate-500 text-sm">
          <div className="text-center">
            <div className="text-2xl mb-2">📈</div>
            <div>Awaiting equity data from API</div>
            <div className="text-xs text-slate-600 mt-1">Connect to /api/v1/risk/equity</div>
          </div>
        </div>
      )}
    </div>
  );
}
