// =============================================================================
// RiskIntelligence.jsx — Elite Trading System
// Synthesized from GPT-5.2 / Claude Opus 4.6 / Gemini 3.1 Pro consensus
// Route: /risk | Section: Execution | Page 10
// =============================================================================
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";
import log from "@/utils/logger";

// ─── COLOR PALETTE (aurora design system) ──────────────────────────────────
const C = {
  bg:        '#0B0E14',
  surface:   '#111827',
  card:      '#1A1F2E',
  border:    '#1E293B',
  cyan:      '#00D9FF',
  green:     '#10B981',
  red:       '#EF4444',
  amber:     '#F59E0B',
  purple:    '#A855F7',
  text:      '#f8fafc',
  muted:     '#64748B',
  dimText:   '#94A3B8',
};

// ─── RISK GRADE HELPER ───────────────────────────────────────────────────────
function gradeFromScore(score) {
  if (score <= 20)  return { letter: 'A+', color: C.green };
  if (score <= 35)  return { letter: 'A',  color: C.green };
  if (score <= 50)  return { letter: 'B',  color: C.cyan };
  if (score <= 65)  return { letter: 'C',  color: C.amber };
  if (score <= 80)  return { letter: 'D',  color: C.red };
  return                    { letter: 'F',  color: C.red };
}

function statusColor(status) {
  if (status === 'SAFE' || status === 'OK' || status === 'PASS') return C.green;
  if (status === 'WARNING' || status === 'CAUTION')              return C.amber;
  return C.red;
}

// ─── CORRELATION COLOR (smooth gradient: green -> yellow -> red) ─────────────
function corrColor(val) {
  const abs = Math.min(Math.abs(val ?? 0), 1);
  // Smooth HSL interpolation: 140 (green) -> 60 (yellow) -> 0 (red)
  const hue = 140 - abs * 140;
  const sat = 70 + abs * 20; // increase saturation as correlation grows
  const light = 50 + (1 - abs) * 10; // slightly lighter at low correlation
  return `hsl(${hue}, ${sat}%, ${light}%)`;
}

function corrBgColor(val) {
  const abs = Math.min(Math.abs(val ?? 0), 1);
  const hue = 140 - abs * 140;
  const alpha = 0.08 + abs * 0.17; // 0.08 at 0 -> 0.25 at 1.0
  return `hsla(${hue}, 80%, 50%, ${alpha})`;
}

// ─── MINI SEMICIRCLE GAUGE (SVG, normalized 0-100) ───────────────────────────
function SemiGauge({ label, value = 0, unit = '%', thresholds = [30, 70] }) {
  const clamped = Math.max(0, Math.min(100, value));
  const angle   = (clamped / 100) * 180;
  const rad     = (angle - 180) * (Math.PI / 180);
  const r       = 36;
  const cx      = 44;
  const cy      = 44;
  const x       = cx + r * Math.cos(rad);
  const y       = cy + r * Math.sin(rad);
  const large   = angle > 180 ? 1 : 0;
  const color   = clamped <= thresholds[0] ? C.green
                : clamped <= thresholds[1] ? C.amber
                : C.red;

  return (
    <div className="flex flex-col items-center bg-[#111827] rounded-[8px] p-2 border border-[rgba(42,52,68,0.5)]
                    hover:shadow-[0_0_12px_rgba(0,217,255,0.06)] transition-all">
      <svg width="88" height="52" viewBox="0 0 88 52">
        {/* track */}
        <path d={`M 8 44 A 36 36 0 0 1 80 44`}
              fill="none" stroke="#1E293B" strokeWidth="6" strokeLinecap="round" />
        {/* filled arc */}
        {clamped > 0 && (
          <path d={`M 8 44 A 36 36 0 ${large} 1 ${x.toFixed(1)} ${y.toFixed(1)}`}
                fill="none" stroke={color} strokeWidth="6" strokeLinecap="round" />
        )}
        <text x="44" y="42" textAnchor="middle" fill={C.text}
              fontSize="14" fontWeight="700" fontFamily="monospace">
          {Math.round(clamped)}{unit}
        </text>
      </svg>
      <span className="text-[10px] text-aurora-subtext mt-0.5 text-center leading-tight truncate w-full">
        {label}
      </span>
    </div>
  );
}

// ─── KPI PILL ────────────────────────────────────────────────────────────────
function KpiPill({ label, value, sub, color = C.cyan }) {
  return (
    <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] min-w-0 px-3 py-2
                    hover:shadow-[0_0_15px_rgba(0,217,255,0.08)] transition-all">
      <div className="aurora-label truncate">{label}</div>
      <div className="text-lg font-bold font-mono" style={{ color }}>{value}</div>
      {sub && <div className="text-[10px] text-aurora-subtext">{sub}</div>}
    </div>
  );
}

// ─── SAFETY CHECK ROW ────────────────────────────────────────────────────────
function SafetyCheck({ label, status }) {
  const passed = status === 'PASS' || status === 'OK' || status === 'SAFE';
  return (
    <div className="flex items-center justify-between py-1 border-b border-aurora-border last:border-0">
      <span className="text-xs text-slate-300">{label}</span>
      <span className="text-xs font-mono font-bold" style={{ color: passed ? C.green : C.red }}>
        {passed ? '+ PASS' : 'x FAIL'}
      </span>
    </div>
  );
}

// ─── CIRCUIT BREAKER ROW ─────────────────────────────────────────────────────
function BreakerRow({ name, threshold, current, tripped }) {
  return (
    <div className={`flex items-center justify-between py-1.5 px-2 rounded-aurora text-xs
      ${tripped ? 'bg-red-500/10 border border-red-500/30' : 'border border-transparent'}`}>
      <span className="text-slate-300 flex-1">{name}</span>
      <span className="font-mono text-slate-400 w-16 text-right">{threshold}</span>
      <span className={`font-mono w-16 text-right font-bold ${tripped ? 'text-red-400' : 'text-green-400'}`}>
        {current}
      </span>
      <span className={`ml-2 w-4 h-4 rounded-full flex items-center justify-center text-[8px]
        ${tripped ? 'bg-red-500 text-white' : 'bg-green-500/20 text-green-400'}`}>
        {tripped ? '!' : '+'}
      </span>
    </div>
  );
}

// ─── POSITION VAR ROW ────────────────────────────────────────────────────────
function VarRow({ symbol, weight, var95, var99, contribution, color }) {
  return (
    <tr className="border-b border-aurora-border hover:bg-aurora-muted/20 text-xs">
      <td className="py-1.5 px-2 font-mono font-bold" style={{ color: color || C.cyan }}>{symbol}</td>
      <td className="py-1.5 px-2 text-right text-slate-300">{weight}</td>
      <td className="py-1.5 px-2 text-right text-amber-400">{var95}</td>
      <td className="py-1.5 px-2 text-right text-red-400">{var99}</td>
      <td className="py-1.5 px-2 text-right text-slate-300">{contribution}</td>
    </tr>
  );
}

// ─── TREEMAP BLOCK ───────────────────────────────────────────────────────────
function TreemapBlock({ symbol, pct, color }) {
  return (
    <div
      className="rounded-aurora flex items-center justify-center text-[10px] font-mono font-bold text-white/90
                 border border-white/5 transition-all hover:brightness-125"
      style={{ backgroundColor: color || C.cyan + '40', flexBasis: `${Math.max(pct, 8)}%`, minHeight: 32 }}
      title={`${symbol}: ${pct.toFixed(1)}% VaR contribution`}
    >
      {symbol} {pct.toFixed(0)}%
    </div>
  );
}

// ─── CORRELATION HEATMAP ────────────────────────────────────────────────────
function CorrelationHeatmap({ data }) {
  // data expected: { symbols: string[], matrix: number[][] }
  if (!data || !data.symbols || !data.matrix || data.symbols.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-aurora-subtext py-8">
        <div className="text-xs font-mono">Correlation Heatmap</div>
        <div className="text-[10px] mt-1">Awaiting correlation data from API</div>
      </div>
    );
  }
  const { symbols, matrix } = data;
  const n = symbols.length;

  return (
    <div className="overflow-auto custom-scrollbar">
      <table className="w-full border-collapse text-[10px] font-mono" style={{ minWidth: n * 48 + 56 }}>
        <thead>
          <tr>
            <th className="py-1.5 px-1 text-left text-aurora-subtext sticky left-0 bg-[#111827] z-10 border-b border-r border-[rgba(42,52,68,0.5)]"
                style={{ minWidth: 56 }}></th>
            {symbols.map((s) => (
              <th key={s} className="py-1.5 px-1 text-center font-bold border-b border-[rgba(42,52,68,0.5)]"
                  style={{ color: C.cyan, minWidth: 44 }}>
                {s}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {symbols.map((rowSym, ri) => (
            <tr key={rowSym}>
              <td className="py-1.5 px-1.5 font-bold sticky left-0 bg-[#111827] z-10 whitespace-nowrap border-r border-[rgba(42,52,68,0.5)]"
                  style={{ color: C.cyan }}>
                {rowSym}
              </td>
              {matrix[ri]?.map((val, ci) => {
                const isDiag = ri === ci;
                const safeVal = val ?? 0;
                const abs = Math.abs(safeVal);
                return (
                  <td
                    key={ci}
                    className="py-1.5 px-1 text-center font-bold transition-all"
                    style={{
                      color: isDiag ? C.dimText : corrColor(safeVal),
                      backgroundColor: isDiag
                        ? 'rgba(0,217,255,0.06)'
                        : corrBgColor(safeVal),
                      border: `1px solid ${isDiag ? 'rgba(0,217,255,0.15)' : 'rgba(42,52,68,0.3)'}`,
                      fontSize: n > 8 ? '9px' : '10px',
                      // subtle glow on high-correlation off-diagonal cells
                      boxShadow: !isDiag && abs >= 0.7 ? `inset 0 0 8px ${corrBgColor(safeVal)}` : 'none',
                    }}
                    title={`${rowSym} vs ${symbols[ci]}: ${safeVal.toFixed(4)}`}
                  >
                    {isDiag ? '1.00' : safeVal.toFixed(2)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {/* Gradient legend */}
      <div className="flex items-center gap-2 mt-2 px-1">
        <span className="text-[9px] text-aurora-subtext">Low</span>
        <div className="flex-1 h-2 rounded-full" style={{
          background: 'linear-gradient(to right, hsl(140,70%,55%), hsl(60,80%,50%), hsl(0,90%,50%))'
        }} />
        <span className="text-[9px] text-aurora-subtext">High</span>
      </div>
    </div>
  );
}

// ─── VaR HISTOGRAM (div-based with 95% confidence marker) ──────────────────
function VarHistogram({ data }) {
  // data expected: { buckets: { range: [lo, hi], count: number }[], var95: number, mean: number }
  if (!data || !data.buckets || data.buckets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-aurora-subtext py-8">
        <div className="text-xs font-mono">VaR Distribution Histogram</div>
        <div className="text-[10px] mt-1">Awaiting return distribution data from API</div>
      </div>
    );
  }
  const { buckets, var95, mean } = data;
  const maxCount = Math.max(...buckets.map(b => b.count), 1);
  const allLo = Math.min(...buckets.map(b => b.range[0]));
  const allHi = Math.max(...buckets.map(b => b.range[1]));
  const rangeSpan = allHi - allLo || 1;

  // Position of the VaR 95% line as a percentage across the histogram
  const var95Pct = var95 != null ? ((var95 - allLo) / rangeSpan) * 100 : null;
  const meanPct = mean != null ? ((mean - allLo) / rangeSpan) * 100 : null;

  return (
    <div className="w-full space-y-1.5">
      {/* Histogram container */}
      <div className="relative w-full rounded-[8px] bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] p-2"
           style={{ minHeight: 120 }}>
        {/* Bars row */}
        <div className="flex items-end gap-px w-full" style={{ height: 96 }}>
          {buckets.map((b, i) => {
            const hPct = (b.count / maxCount) * 100;
            const midVal = (b.range[0] + b.range[1]) / 2;
            const isNeg = midVal < 0;
            // Bars left of VaR line get a warning tint; others use #00D9FF
            const isInTail = var95 != null && midVal < var95;
            return (
              <div
                key={i}
                className="flex-1 min-w-[2px] rounded-t transition-all hover:brightness-125 relative group"
                style={{
                  height: `${Math.max(hPct, 1)}%`,
                  backgroundColor: isInTail ? 'rgba(239,68,68,0.55)' : '#00D9FF',
                  opacity: isNeg && !isInTail ? 0.6 : 0.85,
                }}
                title={`${b.range[0].toFixed(2)}% to ${b.range[1].toFixed(2)}%: ${b.count} occurrences`}
              >
                {/* Hover tooltip bar */}
                <div className="absolute -top-5 left-1/2 -translate-x-1/2 hidden group-hover:block
                                bg-[#1A1F2E] border border-[rgba(42,52,68,0.5)] rounded px-1 py-0.5
                                text-[8px] font-mono text-slate-300 whitespace-nowrap z-20 shadow-lg">
                  {b.count}
                </div>
              </div>
            );
          })}
        </div>

        {/* VaR 95% vertical marker line */}
        {var95Pct != null && (
          <div
            className="absolute top-2 bottom-6"
            style={{ left: `calc(${var95Pct}% + 8px - ${var95Pct * 0.16}px)`, width: 0 }}
          >
            <div className="h-full border-l-2 border-dashed" style={{ borderColor: '#EF4444' }} />
            <div className="absolute -top-0.5 -left-[22px] text-[8px] font-mono font-bold px-1 py-0.5 rounded whitespace-nowrap"
                 style={{ color: '#EF4444', backgroundColor: 'rgba(239,68,68,0.12)' }}>
              VaR 95%
            </div>
          </div>
        )}

        {/* Mean marker line */}
        {meanPct != null && (
          <div
            className="absolute top-2 bottom-6"
            style={{ left: `calc(${meanPct}% + 8px - ${meanPct * 0.16}px)`, width: 0 }}
          >
            <div className="h-full border-l border-dashed" style={{ borderColor: '#00D9FF' }} />
            <div className="absolute -bottom-0.5 -left-[10px] text-[7px] font-mono px-0.5"
                 style={{ color: '#00D9FF' }}>
              Mean
            </div>
          </div>
        )}
      </div>

      {/* X-axis labels */}
      <div className="flex justify-between px-1 text-[8px] font-mono text-aurora-subtext">
        <span>{allLo.toFixed(1)}%</span>
        {var95 != null && (
          <span style={{ color: '#EF4444' }}>{var95.toFixed(2)}%</span>
        )}
        <span>{allHi.toFixed(1)}%</span>
      </div>

      {/* Summary stats */}
      <div className="flex items-center justify-between text-[9px] font-mono pt-0.5 px-0.5">
        <span className="text-aurora-subtext">
          Samples: <span className="text-slate-300">{buckets.reduce((s, b) => s + b.count, 0)}</span>
        </span>
        {var95 != null && (
          <span style={{ color: '#EF4444' }}>
            VaR(95): {var95.toFixed(2)}%
          </span>
        )}
        {mean != null && (
          <span style={{ color: '#00D9FF' }}>
            Mean: {mean.toFixed(2)}%
          </span>
        )}
      </div>
    </div>
  );
}

// ─── POSITION SIZER ──────────────────────────────────────────────────────────
function PositionSizer({ kelly, portfolioValue }) {
  const [kellyFraction, setKellyFraction] = useState(0.25); // quarter kelly default
  const [fixedPct, setFixedPct] = useState(2.0);
  const [mode, setMode] = useState('kelly'); // 'kelly' | 'fixed'

  const accountVal = portfolioValue || 0;
  const fullKellyPct = (kelly?.full_kelly ?? 0) * 100;
  const adjKellyPct = fullKellyPct * kellyFraction;
  const kellyDollars = accountVal * (adjKellyPct / 100);
  const fixedDollars = accountVal * (fixedPct / 100);

  const recommended = mode === 'kelly' ? adjKellyPct : fixedPct;
  const recommendedDollars = mode === 'kelly' ? kellyDollars : fixedDollars;

  return (
    <div className="space-y-3">
      {/* Mode toggle */}
      <div className="flex rounded-[8px] overflow-hidden border border-[rgba(42,52,68,0.5)]">
        <button
          onClick={() => setMode('kelly')}
          className="flex-1 px-3 py-1.5 text-xs font-mono font-bold transition-all"
          style={{
            backgroundColor: mode === 'kelly' ? 'rgba(0,217,255,0.15)' : '#1A1F2E',
            color: mode === 'kelly' ? '#00D9FF' : '#64748B',
          }}
        >
          Kelly Criterion
        </button>
        <button
          onClick={() => setMode('fixed')}
          className="flex-1 px-3 py-1.5 text-xs font-mono font-bold transition-all"
          style={{
            backgroundColor: mode === 'fixed' ? 'rgba(0,217,255,0.15)' : '#1A1F2E',
            color: mode === 'fixed' ? '#00D9FF' : '#64748B',
          }}
        >
          Fixed %
        </button>
      </div>

      {mode === 'kelly' ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-aurora-subtext">Kelly Fraction</span>
            <span className="font-mono font-bold" style={{ color: '#00D9FF' }}>{(kellyFraction * 100).toFixed(0)}%</span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={kellyFraction * 100}
            onChange={(e) => setKellyFraction(Number(e.target.value) / 100)}
            className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
            style={{ background: `linear-gradient(to right, #00D9FF80 ${kellyFraction * 100}%, #1E293B ${kellyFraction * 100}%)` }}
          />
          <div className="flex justify-between text-[9px] text-aurora-subtext">
            <span>0% (Skip)</span>
            <span>25%</span>
            <span>50%</span>
            <span>100% (Full Kelly)</span>
          </div>
          {/* Calculation breakdown */}
          <div className="bg-[#0B0E14] rounded-[8px] border border-[rgba(42,52,68,0.5)] p-2 space-y-1 text-[10px] font-mono">
            <div className="text-aurora-subtext text-[9px] uppercase tracking-wider mb-1">Calculation Breakdown</div>
            <div className="flex justify-between">
              <span className="text-aurora-subtext">Win Rate (W)</span>
              <span className="text-slate-300">{((kelly?.win_rate ?? 0) * 100).toFixed(1)}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-aurora-subtext">Win/Loss Ratio (R)</span>
              <span className="text-slate-300">
                {(kelly?.avg_loss ?? 0) !== 0
                  ? ((kelly?.avg_win ?? 0) / Math.abs(kelly?.avg_loss ?? 1)).toFixed(2)
                  : '--'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-aurora-subtext">K = W - (1-W)/R</span>
              <span className="text-slate-300">{fullKellyPct.toFixed(2)}%</span>
            </div>
            <div className="flex justify-between border-t border-[rgba(42,52,68,0.5)] pt-1 mt-1">
              <span className="text-aurora-subtext">Fraction Applied</span>
              <span style={{ color: '#00D9FF' }}>{(kellyFraction * 100).toFixed(0)}%</span>
            </div>
            <div className="flex justify-between font-bold">
              <span className="text-slate-300">Adjusted Size</span>
              <span style={{ color: '#00D9FF' }}>{adjKellyPct.toFixed(2)}%</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-aurora-subtext">Position Size</span>
            <span className="font-mono font-bold" style={{ color: '#00D9FF' }}>{fixedPct.toFixed(1)}%</span>
          </div>
          <input
            type="range"
            min={0.5}
            max={10}
            step={0.5}
            value={fixedPct}
            onChange={(e) => setFixedPct(Number(e.target.value))}
            className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
            style={{ background: `linear-gradient(to right, #00D9FF80 ${(fixedPct / 10) * 100}%, #1E293B ${(fixedPct / 10) * 100}%)` }}
          />
          <div className="flex justify-between text-[9px] text-aurora-subtext">
            <span>0.5%</span>
            <span>2%</span>
            <span>5%</span>
            <span>10%</span>
          </div>
          {/* Calculation breakdown for fixed mode */}
          <div className="bg-[#0B0E14] rounded-[8px] border border-[rgba(42,52,68,0.5)] p-2 space-y-1 text-[10px] font-mono">
            <div className="text-aurora-subtext text-[9px] uppercase tracking-wider mb-1">Calculation Breakdown</div>
            <div className="flex justify-between">
              <span className="text-aurora-subtext">Account Value</span>
              <span className="text-slate-300">${accountVal.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-aurora-subtext">Risk Percent</span>
              <span className="text-slate-300">{fixedPct.toFixed(1)}%</span>
            </div>
            <div className="flex justify-between border-t border-[rgba(42,52,68,0.5)] pt-1 mt-1 font-bold">
              <span className="text-slate-300">Position Size</span>
              <span style={{ color: '#00D9FF' }}>
                ${fixedDollars.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Result -- aurora-kpi styled */}
      <div className="bg-[#111827] border border-[rgba(0,217,255,0.25)] rounded-[8px] px-3 py-3
                      shadow-[0_0_15px_rgba(0,217,255,0.08)] hover:shadow-[0_0_20px_rgba(0,217,255,0.15)]
                      transition-all">
        <div className="text-[10px] text-aurora-subtext uppercase tracking-wider">Recommended Position Size</div>
        <div className="flex items-baseline gap-3 mt-1">
          <span className="text-2xl font-black font-mono" style={{ color: '#00D9FF' }}>
            {recommended.toFixed(1)}%
          </span>
          {accountVal > 0 && (
            <span className="text-sm font-mono font-bold text-slate-300">
              ${recommendedDollars.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </span>
          )}
        </div>
        <div className="text-[9px] text-aurora-subtext mt-1 font-mono">
          Mode: {mode === 'kelly' ? `Kelly (${(kellyFraction * 100).toFixed(0)}% fraction)` : `Fixed ${fixedPct.toFixed(1)}%`}
        </div>
      </div>
    </div>
  );
}

// ─── DRAWDOWN WATERFALL ──────────────────────────────────────────────────────
function DrawdownWaterfall({ data }) {
  // data expected: { episodes: { start: string, end: string, depth: number, duration: number, recovered: boolean }[] }
  // OR drawdown series: { date: string, drawdown: number }[]
  const episodes = data?.episodes;
  const series = data?.series;

  if ((!episodes || episodes.length === 0) && (!series || series.length === 0)) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-aurora-subtext py-8">
        <div className="text-xs font-mono">Drawdown Waterfall</div>
        <div className="text-[10px] mt-1">Awaiting drawdown episode data from API</div>
      </div>
    );
  }

  // If we have a drawdown series, render as waterfall bars
  if (series && series.length > 0) {
    const maxDD = Math.max(...series.map(s => Math.abs(s.drawdown || 0)), 1);
    return (
      <div className="w-full h-32 flex items-start gap-px overflow-hidden rounded-aurora bg-[#0B0E14] border border-aurora-border p-1">
        {series.map((pt, i) => {
          const dd = Math.abs(pt.drawdown || 0);
          const h = (dd / maxDD) * 100;
          const barColor = dd > 15 ? C.red : dd > 8 ? C.amber : dd > 3 ? C.purple + 'A0' : C.cyan + '60';
          return (
            <div
              key={i}
              className="flex-1 min-w-[2px] rounded-b transition-all hover:opacity-80"
              style={{ height: `${h}%`, backgroundColor: barColor, minHeight: dd > 0 ? 2 : 0 }}
              title={`${pt.date}: -${dd.toFixed(2)}%`}
            />
          );
        })}
      </div>
    );
  }

  // Episode-based waterfall
  const maxDepth = Math.max(...episodes.map(e => Math.abs(e.depth)), 1);
  return (
    <div className="space-y-1 max-h-40 overflow-y-auto custom-scrollbar">
      {episodes.map((ep, i) => {
        const pctOfMax = (Math.abs(ep.depth) / maxDepth) * 100;
        return (
          <div key={i} className="flex items-center gap-2 text-[10px]">
            <span className="font-mono text-aurora-subtext w-16 shrink-0 truncate">{ep.start}</span>
            <div className="flex-1 h-4 bg-[#0B0E14] rounded-aurora overflow-hidden relative">
              <div
                className="h-full rounded-aurora transition-all"
                style={{
                  width: `${pctOfMax}%`,
                  backgroundColor: Math.abs(ep.depth) > 15 ? C.red + 'A0' : Math.abs(ep.depth) > 8 ? C.amber + '80' : C.purple + '60',
                }}
              />
              <span className="absolute inset-0 flex items-center px-1 font-mono font-bold text-white/80">
                {ep.depth.toFixed(1)}%
              </span>
            </div>
            <span className={`font-mono w-10 text-right ${ep.recovered ? 'text-green-400' : 'text-red-400'}`}>
              {ep.duration}d
            </span>
            <span className={`w-3 h-3 rounded-full text-[7px] flex items-center justify-center
              ${ep.recovered ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
              {ep.recovered ? '+' : '!'}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ─── RISK RULES TABLE ────────────────────────────────────────────────────────
function classifyRuleStatus(status, current, limit) {
  // Normalize status string
  const s = (status ?? '').toUpperCase();
  if (s === 'PASS' || s === 'OK' || s === 'SAFE') return 'PASS';
  if (s === 'WARNING' || s === 'CAUTION' || s === 'WARN') return 'WARNING';
  if (s === 'FAIL' || s === 'BREACH' || s === 'CRITICAL') return 'BREACH';

  // If status not set, try to infer from current vs limit
  if (current != null && limit != null) {
    const curNum = parseFloat(String(current).replace(/[%$,]/g, ''));
    const limNum = parseFloat(String(limit).replace(/[%$,]/g, ''));
    if (!isNaN(curNum) && !isNaN(limNum) && limNum > 0) {
      const ratio = curNum / limNum;
      if (ratio >= 1.0) return 'BREACH';
      if (ratio >= 0.8) return 'WARNING';
      return 'PASS';
    }
  }
  return s === '' ? 'PASS' : 'BREACH';
}

function RiskRulesTable({ riskData, shieldData, breakersData }) {
  // Build rules from available API data
  const rules = useMemo(() => {
    const result = [];

    // From shield checks
    const checks = shieldData?.checks ?? [];
    const ruleTypeMap = {
      'Max Position Size':       { type: 'Size',        limit: '10%' },
      'Portfolio Concentration': { type: 'Exposure',    limit: '25%' },
      'Daily Loss Limit':       { type: 'Loss',        limit: '2%' },
      'Drawdown Threshold':     { type: 'Drawdown',    limit: '15%' },
      'Correlation Check':      { type: 'Correlation', limit: '0.70' },
      'Volatility Regime':      { type: 'Volatility',  limit: 'Low/Med' },
      'Liquidity Check':        { type: 'Liquidity',   limit: 'Min $1M' },
      'Sector Exposure':        { type: 'Exposure',    limit: '30%' },
      'Risk Budget':            { type: 'Budget',      limit: '100%' },
    };

    checks.forEach((c) => {
      const info = ruleTypeMap[c.label] || { type: 'Check', limit: '--' };
      const limit = c.limit ?? info.limit;
      const current = c.current ?? '--';
      result.push({
        rule: c.label,
        type: info.type,
        limit,
        current,
        status: classifyRuleStatus(c.status, current, limit),
      });
    });

    // From circuit breakers
    const breakers = breakersData?.breakers ?? [];
    breakers.forEach((b) => {
      result.push({
        rule: b.name,
        type: 'Breaker',
        limit: b.threshold,
        current: b.current,
        status: b.tripped ? 'BREACH' : 'PASS',
      });
    });

    // Add VIX filter if in riskData
    if (riskData?.vix_filter != null) {
      result.push({
        rule: 'VIX Filter',
        type: 'Volatility',
        limit: riskData.vix_limit ?? '30',
        current: riskData.vix_current ?? '--',
        status: riskData.vix_filter ? 'PASS' : 'BREACH',
      });
    }

    // If nothing from API, show default placeholders
    if (result.length === 0) {
      return [
        { rule: 'Max Position Size',   type: 'Size',        limit: '10%',    current: '--', status: 'PASS' },
        { rule: 'Max Drawdown',        type: 'Drawdown',    limit: '15%',    current: '--', status: 'PASS' },
        { rule: 'Correlation Cap',     type: 'Correlation', limit: '0.70',   current: '--', status: 'PASS' },
        { rule: 'Daily Loss Limit',    type: 'Loss',        limit: '2%',     current: '--', status: 'PASS' },
        { rule: 'VIX Filter',          type: 'Volatility',  limit: '30',     current: '--', status: 'PASS' },
        { rule: 'Sector Concentration',type: 'Exposure',    limit: '30%',    current: '--', status: 'PASS' },
        { rule: 'Liquidity Min',       type: 'Liquidity',   limit: '$1M',    current: '--', status: 'PASS' },
        { rule: 'Risk Budget',         type: 'Budget',      limit: '100%',   current: '--', status: 'PASS' },
      ];
    }

    return result;
  }, [riskData, shieldData, breakersData]);

  const passCount = rules.filter(r => r.status === 'PASS').length;
  const warnCount = rules.filter(r => r.status === 'WARNING').length;
  const breachCount = rules.filter(r => r.status === 'BREACH').length;

  return (
    <div className="space-y-2">
      {/* Summary badges */}
      <div className="flex items-center gap-3 mb-1">
        <span className="inline-flex items-center gap-1.5 text-[10px] font-mono font-bold px-2 py-1 rounded-[8px]"
              style={{ backgroundColor: 'rgba(16,185,129,0.1)', color: C.green, border: '1px solid rgba(16,185,129,0.2)' }}>
          <span className="w-2 h-2 rounded-full bg-green-400" />
          {passCount} PASS
        </span>
        {warnCount > 0 && (
          <span className="inline-flex items-center gap-1.5 text-[10px] font-mono font-bold px-2 py-1 rounded-[8px]"
                style={{ backgroundColor: 'rgba(245,158,11,0.1)', color: C.amber, border: '1px solid rgba(245,158,11,0.2)' }}>
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            {warnCount} WARNING
          </span>
        )}
        {breachCount > 0 && (
          <span className="inline-flex items-center gap-1.5 text-[10px] font-mono font-bold px-2 py-1 rounded-[8px]"
                style={{ backgroundColor: 'rgba(239,68,68,0.1)', color: C.red, border: '1px solid rgba(239,68,68,0.2)' }}>
            <span className="w-2 h-2 rounded-full bg-red-400" />
            {breachCount} BREACH
          </span>
        )}
        <span className="text-[10px] text-aurora-subtext font-mono ml-auto">
          {rules.length} rules active
        </span>
      </div>

      <div className="overflow-auto custom-scrollbar">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-[10px] text-aurora-subtext uppercase tracking-wider border-b border-[rgba(42,52,68,0.5)]">
              <th className="py-2 px-2 text-left">Rule</th>
              <th className="py-2 px-2 text-left">Type</th>
              <th className="py-2 px-2 text-right">Threshold</th>
              <th className="py-2 px-2 text-right">Current</th>
              <th className="py-2 px-2 text-center">Status</th>
              <th className="py-2 px-2 text-center">Action</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((r, i) => {
              const isPassed = r.status === 'PASS';
              const isWarning = r.status === 'WARNING';
              const isBreach = r.status === 'BREACH';
              // Row background tint for breach/warning
              const rowBg = isBreach
                ? 'rgba(239,68,68,0.04)'
                : isWarning
                  ? 'rgba(245,158,11,0.04)'
                  : 'transparent';
              return (
                <tr key={i}
                    className="border-b border-[rgba(42,52,68,0.3)] hover:bg-[rgba(42,52,68,0.15)] transition-colors"
                    style={{ backgroundColor: rowBg }}>
                  <td className="py-1.5 px-2 text-slate-300 font-medium">{r.rule}</td>
                  <td className="py-1.5 px-2">
                    <span className="inline-block text-[9px] font-mono font-bold px-1.5 py-0.5 rounded"
                          style={{ backgroundColor: '#00D9FF15', color: '#00D9FF' }}>
                      {r.type}
                    </span>
                  </td>
                  <td className="py-1.5 px-2 text-right font-mono text-aurora-subtext">{r.limit}</td>
                  <td className="py-1.5 px-2 text-right font-mono"
                      style={{ color: isBreach ? C.red : isWarning ? C.amber : '#cbd5e1' }}>
                    {r.current}
                  </td>
                  <td className="py-1.5 px-2 text-center">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold"
                          style={{
                            backgroundColor: isPassed
                              ? 'rgba(16,185,129,0.15)'
                              : isWarning
                                ? 'rgba(245,158,11,0.15)'
                                : 'rgba(239,68,68,0.15)',
                            color: isPassed ? C.green : isWarning ? C.amber : C.red,
                          }}>
                      <span className="w-1.5 h-1.5 rounded-full"
                            style={{ backgroundColor: isPassed ? C.green : isWarning ? C.amber : C.red }} />
                      {isPassed ? 'PASS' : isWarning ? 'WARNING' : 'BREACH'}
                    </span>
                  </td>
                  <td className="py-1.5 px-2 text-center">
                    {isBreach && (
                      <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded"
                            style={{ color: C.red, backgroundColor: 'rgba(239,68,68,0.1)' }}>
                        Intervene
                      </span>
                    )}
                    {isWarning && (
                      <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded"
                            style={{ color: C.amber, backgroundColor: 'rgba(245,158,11,0.1)' }}>
                        Review
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================
export default function RiskIntelligence() {
  const [timeframe, setTimeframe] = useState('1D');
  const [lastRefresh, setLastRefresh] = useState(new Date());

  // ─── API HOOKS (wired to real backend endpoints) ─────────────────────────
  const { data: riskData, loading: riskLoading, refetch: refetchRisk } = useApi('risk');
  const { data: shieldData, loading: shieldLoading, refetch: refetchShield } = useApi('risk', { endpoint: '/risk/shield' });
  const { data: gaugesData, loading: gaugesLoading, refetch: refetchGauges } = useApi('risk', { endpoint: '/risk/risk-gauges' });
  const { data: kellyData, loading: kellyLoading } = useApi('kellySizer');
  const { data: monteData, loading: monteLoading } = useApi('risk', { endpoint: '/risk/monte-carlo' });
  const { data: breakersData, loading: breakersLoading } = useApi('risk', { endpoint: '/risk/circuit-breakers' });
  const { data: varData, loading: varLoading } = useApi('risk', { endpoint: '/risk/position-var' });
  const { data: historyData, loading: histLoading } = useApi('risk', { endpoint: '/risk/history' });
  const { data: portfolioData } = useApi('portfolio');
  const { data: brightLines } = useApi('alignment/bright-lines');
  const { data: recentVerdicts } = useApi('alignment/verdicts');
  const { data: equityCurveData } = useApi('risk', { endpoint: `/risk/equity-curve?tf=${timeframe}`, pollIntervalMs: 30000 });
  // New API hooks for added sections
  const { data: correlationData } = useApi('risk', { endpoint: '/risk/correlation-matrix' });
  const { data: varHistData } = useApi('risk', { endpoint: '/risk/var-histogram' });
  const { data: drawdownData } = useApi('risk', { endpoint: '/risk/drawdown-episodes' });

  const handleRefresh = useCallback(() => {
    setLastRefresh(new Date());
    refetchRisk(); refetchShield(); refetchGauges();
  }, [refetchRisk, refetchShield, refetchGauges]);
  // ─── DERIVED VALUES ──────────────────────────────────────────────────────
  const riskScore    = riskData?.risk_score ?? 0;
  const grade        = gradeFromScore(riskScore);
  const systemStatus = riskData?.system_status ?? 'UNKNOWN';
  const warnings     = riskData?.warnings ?? 0;

  // KPI array from API
  const kpis = riskData?.kpis ?? [
    { label: 'Portfolio Value',     value: '$--',       color: C.text },
    { label: 'Daily P&L',          value: '$--',       color: C.muted },
    { label: 'Max Drawdown',       value: '--%',       color: C.muted },
    { label: 'Current DD',         value: '--%',       color: C.muted },
    { label: 'Sharpe Ratio',       value: '--',        color: C.muted },
    { label: 'Win Rate',           value: '--%',       color: C.muted },
    { label: 'Profit Factor',      value: '--',        color: C.muted },
    { label: 'Open Positions',     value: '--',        color: C.muted },
    { label: 'Daily Trades',       value: '--',        color: C.muted },
    { label: 'Exposure',           value: '--%',       color: C.muted },
  ];

  // Shield checks
  const safetyChecks = shieldData?.checks ?? [
    { label: 'Max Position Size',       status: 'PASS' },
    { label: 'Portfolio Concentration',  status: 'PASS' },
    { label: 'Daily Loss Limit',        status: 'PASS' },
    { label: 'Drawdown Threshold',      status: 'PASS' },
    { label: 'Correlation Check',       status: 'PASS' },
    { label: 'Volatility Regime',       status: 'PASS' },
    { label: 'Liquidity Check',         status: 'PASS' },
    { label: 'Sector Exposure',         status: 'PASS' },
    { label: 'Risk Budget',             status: 'PASS' },
  ];

  // Gauges (normalized 0-100)
  const gauges = gaugesData?.gauges ?? [
    { label: 'VaR 95%',          value: 0 },
    { label: 'VaR 99%',          value: 0 },
    { label: 'CVaR',             value: 0 },
    { label: 'Beta',             value: 0 },
    { label: 'Correlation',      value: 0 },
    { label: 'Volatility',       value: 0 },
    { label: 'Skew Risk',        value: 0 },
    { label: 'Tail Risk',        value: 0 },
    { label: 'Liquidity',        value: 0 },
    { label: 'Concentration',    value: 0 },
    { label: 'Momentum',         value: 0 },
    { label: 'Regime Risk',      value: 0 },
  ];

  // Kelly sizing
  const kelly = kellyData ?? {
    full_kelly: 0, half_kelly: 0, quarter_kelly: 0,
    current_sizing: 'quarter', win_rate: 0, avg_win: 0, avg_loss: 0,
    edge: 0, recommended_pct: 0,
  };

  // Monte Carlo
  const monte = monteData ?? {
    simulations: 10000, median_return: 0, p5_return: 0, p95_return: 0,
    prob_profit: 0, max_dd_median: 0, max_dd_p95: 0, ruin_probability: 0,
  };

  // Circuit breakers
  const breakers = breakersData?.breakers ?? [];

  // Position VaR
  const positions = varData?.positions ?? [];
  const treemapItems = varData?.treemap ?? [];

  // 90-day risk history
  const history = historyData?.history ?? [];

  // Portfolio value for position sizer
  const portfolioValue = portfolioData?.total_value ?? portfolioData?.portfolio_value ?? riskData?.portfolio_value ?? 0;

  // ─── EMERGENCY ACTIONS ───────────────────────────────────────────────────
  const handleEmergency = async (action) => {
    if (action === 'KILL' && !window.confirm(
      'KILL SWITCH: This will CLOSE ALL POSITIONS and HALT TRADING.\n\nAre you absolutely sure?'
    )) return;
    try {
            await fetch(getApiUrl('risk') + `/emergency/${action.toLowerCase()}`, { method: 'POST' });
handleRefresh();
    } catch (err) {
      log.error(`Emergency ${action} failed:`, err);
    }
  };

  // ─── LOADING STATE ───────────────────────────────────────────────────────
  const isLoading = riskLoading || shieldLoading || gaugesLoading;

  // =========================================================================
  // RENDER
  // =========================================================================
  return (
    <div className="min-h-screen p-3 space-y-3 bg-[#0B0E14] text-aurora-text">

      {/* === HEADER ========================================================= */}
      <header className="aurora-card flex items-center justify-between px-4 py-3">
        {/* Left: shield + title */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-aurora flex items-center justify-center text-xl"
               style={{ backgroundColor: grade.color + '20', color: grade.color }}>
            S
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Risk Intelligence</h1>
            <span className="text-[10px] text-aurora-subtext uppercase tracking-widest">
              Shield Protection -- Real-Time Monitoring
            </span>
          </div>
        </div>

        {/* Center: Grade + Score + Status */}
        <div className="flex items-center gap-6">
          <div className="text-center">
            <div className="aurora-label">Grade</div>
            <div className="text-3xl font-black font-mono" style={{ color: grade.color }}>
              {grade.letter}
            </div>
          </div>
          <div className="text-center">
            <div className="aurora-label">Risk Score</div>
            <div className="text-2xl font-bold font-mono" style={{ color: grade.color }}>
              {riskScore}
            </div>
          </div>
          <div className="text-center">
            <div className="aurora-label">Status</div>
            <div className="text-sm font-bold font-mono" style={{ color: statusColor(systemStatus) }}>
              {systemStatus}
            </div>
          </div>
          {warnings > 0 && (
            <div className="text-center">
              <div className="aurora-label">Warnings</div>
              <div className="text-lg font-bold text-amber-400">{warnings}</div>
            </div>
          )}
        </div>

        {/* Right: timeframe + refresh */}
        <div className="flex items-center gap-3">
          <div className="flex rounded-aurora overflow-hidden border border-aurora-border">
            {['1D', '1W', '1M', '3M'].map(tf => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-3 py-1.5 text-xs font-mono font-bold transition-all
                  ${timeframe === tf
                    ? 'bg-aurora-primary/20 text-aurora-primary'
                    : 'bg-aurora-card text-aurora-subtext hover:text-slate-300'}`}
              >
                {tf}
              </button>
            ))}
          </div>
          <button
            onClick={handleRefresh}
            className="p-2 rounded-aurora bg-aurora-muted/20 border border-aurora-border
                       hover:border-aurora-primary/30 hover:shadow-glow text-aurora-subtext hover:text-aurora-primary transition-all"
            title="Refresh"
          >
            R
          </button>
          <span className="text-[10px] text-aurora-subtext font-mono">
            {lastRefresh.toLocaleTimeString()}
          </span>
        </div>
      </header>

      {/* === 10-KPI STRIP ==================================================== */}
      <div className="grid grid-cols-10 gap-2">
        {kpis.map((kpi, i) => (
          <KpiPill key={i} label={kpi.label} value={kpi.value} sub={kpi.sub} color={kpi.color || C.cyan} />
        ))}
      </div>

      {/* === MAIN GRID -- 12-COLUMN DENSE =================================== */}
      <div className="grid grid-cols-12 gap-3 auto-rows-auto">

        {/* --- ROW 1 LEFT: RISK SHIELD COMMAND CENTER (5 cols) ------------- */}
        <section className="col-span-5 bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4
                            hover:shadow-[0_0_20px_rgba(0,217,255,0.12)] transition-all">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
              Risk Shield -- 9 Safety Checks
            </h2>
            <span className="text-xs font-mono px-2 py-0.5 rounded-aurora"
                  style={{
                    backgroundColor: safetyChecks.every(c => c.status === 'PASS') ? C.green + '20' : C.amber + '20',
                    color: safetyChecks.every(c => c.status === 'PASS') ? C.green : C.amber,
                  }}>
              {safetyChecks.filter(c => c.status === 'PASS').length}/9 PASS
            </span>
          </div>

          <div className="space-y-0.5 mb-4">
            {safetyChecks.map((check, i) => (
              <SafetyCheck key={i} label={check.label} status={check.status} />
            ))}
          </div>

          {/* Emergency Actions */}
          <div className="border-t border-aurora-border pt-3">
            <div className="aurora-label mb-2">
              Emergency Actions
            </div>
            <div className="grid grid-cols-4 gap-2">
              <button
                onClick={() => handleEmergency('KILL')}
                className="py-2 px-2 rounded-aurora text-xs font-bold uppercase
                           bg-red-600 hover:bg-red-500 text-white
                           border-2 border-red-400 shadow-lg shadow-red-500/20
                           transition-all active:scale-95"
              >
                KILL
              </button>
              <button
                onClick={() => handleEmergency('HEDGE')}
                className="py-2 px-2 rounded-aurora text-xs font-bold uppercase
                           bg-purple-600/30 hover:bg-purple-600/50 text-purple-300
                           border border-purple-500/30 transition-all active:scale-95"
              >
                Hedge
              </button>
              <button
                onClick={() => handleEmergency('REDUCE')}
                className="py-2 px-2 rounded-aurora text-xs font-bold uppercase
                           bg-amber-600/30 hover:bg-amber-600/50 text-amber-300
                           border border-amber-500/30 transition-all active:scale-95"
              >
                Reduce
              </button>
              <button
                onClick={() => handleEmergency('FREEZE')}
                className="py-2 px-2 rounded-aurora text-xs font-bold uppercase
                           bg-cyan-600/30 hover:bg-cyan-600/50 text-cyan-300
                           border border-cyan-500/30 transition-all active:scale-95"
              >
                Freeze
              </button>
            </div>
          </div>
        </section>

        {/* --- ROW 1 RIGHT: EQUITY / DRAWDOWN with VaR BANDS (7 cols) ------ */}
        <section className="col-span-7 aurora-card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
              Equity Curve & Drawdown -- VaR Bands
            </h2>
            <span className="text-[10px] text-aurora-subtext font-mono">{timeframe}</span>
          </div>
            <div className="h-48 rounded-aurora bg-[#0B0E14] border border-aurora-border flex items-end p-2 gap-px overflow-hidden">
              {(equityCurveData?.points || []).length > 0 ? (
                equityCurveData.points.map((pt, i) => {
                  const maxEq = Math.max(...equityCurveData.points.map(p => p.equity || 0), 1);
                  const h = ((pt.equity || 0) / maxEq) * 100;
                  const dd = pt.drawdown || 0;
                  const barColor = dd > 10 ? C.red : dd > 5 ? C.amber : C.green;
                  return (
                    <div key={i} className="flex-1 min-w-[2px] rounded-t" style={{ height: `${h}%`, backgroundColor: barColor + '80', minHeight: 2 }} title={`${pt.date}: $${pt.equity?.toLocaleString()} DD:${dd.toFixed(1)}%`} />
                  );
                })
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-aurora-subtext">
                  <div className="text-xs font-mono">Equity Curve -- Awaiting data from API</div>
                  <div className="text-[10px] text-aurora-subtext mt-1">Endpoint: /api/v1/risk/equity-curve?tf={timeframe}</div>
                </div>
              )}
            </div>
        </section>

        {/* --- ROW 2 LEFT: 12 MINI GAUGES -- 4x3 grid (5 cols) ------------ */}
        <section className="col-span-5 aurora-card">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3">
            Risk Gauges -- Normalized 0-100
          </h2>
          <div className="grid grid-cols-4 gap-2">
            {gauges.slice(0, 12).map((g, i) => (
              <SemiGauge key={i} label={g.label} value={g.value} />
            ))}
          </div>
        </section>

        {/* --- ROW 2 CENTER: CORRELATION HEATMAP (4 cols) -------- */}
        <section className="col-span-4 bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4
                            hover:shadow-[0_0_20px_rgba(0,217,255,0.12)] transition-all">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3">
            Correlation Heatmap
          </h2>
          <CorrelationHeatmap data={correlationData} />
        </section>

        {/* --- ROW 2 RIGHT: VaR HISTOGRAM (3 cols) --------------- */}
        <section className="col-span-3 bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4
                            hover:shadow-[0_0_20px_rgba(0,217,255,0.12)] transition-all">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3">
            VaR Distribution
          </h2>
          <VarHistogram data={varHistData} />
        </section>

        {/* --- ROW 3 LEFT: POSITION SIZER (4 cols) --------------- */}
        <section className="col-span-4 bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4
                            hover:shadow-[0_0_20px_rgba(0,217,255,0.12)] transition-all">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3">
            Position Sizer
          </h2>
          <PositionSizer kelly={kelly} portfolioValue={portfolioValue} />
        </section>

        {/* --- ROW 3 CENTER: DRAWDOWN WATERFALL (4 cols) --------- */}
        <section className="col-span-4 aurora-card">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3">
            Drawdown Waterfall
          </h2>
          <DrawdownWaterfall data={drawdownData} />
        </section>

        {/* --- ROW 3 RIGHT: KELLY CRITERION (4 cols) ------------- */}
        <section className="col-span-4 aurora-card">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3">
            Kelly Criterion -- Position Sizing
          </h2>
          <div className="space-y-2">
            {[
              { label: 'Full Kelly',      value: `${(kelly.full_kelly * 100).toFixed(1)}%`, active: kelly.current_sizing === 'full' },
              { label: 'Half Kelly',      value: `${(kelly.half_kelly * 100).toFixed(1)}%`, active: kelly.current_sizing === 'half' },
              { label: 'Quarter Kelly',   value: `${(kelly.quarter_kelly * 100).toFixed(1)}%`, active: kelly.current_sizing === 'quarter' },
            ].map((k, i) => (
              <div key={i} className={`flex items-center justify-between py-1.5 px-3 rounded-aurora text-xs
                ${k.active ? 'bg-aurora-primary/10 border border-aurora-primary/30' : 'border border-transparent'}`}>
                <span className="text-slate-300">{k.label}</span>
                <span className={`font-mono font-bold ${k.active ? 'text-aurora-primary' : 'text-aurora-subtext'}`}>
                  {k.value}
                  {k.active && <span className="ml-2 text-[9px] bg-aurora-primary/20 px-1 rounded">ACTIVE</span>}
                </span>
              </div>
            ))}
            <div className="border-t border-aurora-border pt-2 mt-2 grid grid-cols-2 gap-2 text-xs">
              <div>
                <div className="text-aurora-subtext">Win Rate</div>
                <div className="font-mono text-green-400">{(kelly.win_rate * 100).toFixed(1)}%</div>
              </div>
              <div>
                <div className="text-aurora-subtext">Edge</div>
                <div className="font-mono text-aurora-primary">{(kelly.edge * 100).toFixed(2)}%</div>
              </div>
              <div>
                <div className="text-aurora-subtext">Avg Win</div>
                <div className="font-mono text-green-400">${kelly.avg_win?.toFixed(2) ?? '--'}</div>
              </div>
              <div>
                <div className="text-aurora-subtext">Avg Loss</div>
                <div className="font-mono text-red-400">${kelly.avg_loss?.toFixed(2) ?? '--'}</div>
              </div>
            </div>
            <div className="bg-aurora-primary/5 border border-aurora-primary/20 rounded-aurora px-3 py-2 mt-2">
              <div className="text-[10px] text-aurora-subtext">Recommended Next Trade Size</div>
              <div className="text-lg font-bold font-mono text-aurora-primary">
                {(kelly.recommended_pct * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </section>

        {/* --- ROW 4 LEFT: MONTE CARLO STRESS TEST (4 cols) -------------- */}
        <section className="col-span-4 aurora-card">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3">
            Monte Carlo -- {monte.simulations?.toLocaleString()} Sims
          </h2>
          <div className="space-y-2 text-xs">
            {[
              { label: 'Median Return',   value: `${monte.median_return >= 0 ? '+' : ''}${monte.median_return?.toFixed(1)}%`,
                color: monte.median_return >= 0 ? C.green : C.red },
              { label: 'P5 (Worst)',      value: `${monte.p5_return?.toFixed(1)}%`,    color: C.red },
              { label: 'P95 (Best)',      value: `+${monte.p95_return?.toFixed(1)}%`,  color: C.green },
              { label: 'Prob of Profit',  value: `${monte.prob_profit?.toFixed(1)}%`,  color: C.cyan },
              { label: 'Max DD (Median)', value: `${monte.max_dd_median?.toFixed(1)}%`, color: C.amber },
              { label: 'Max DD (P95)',    value: `${monte.max_dd_p95?.toFixed(1)}%`,   color: C.red },
            ].map((row, i) => (
              <div key={i} className="flex items-center justify-between py-1">
                <span className="text-aurora-subtext">{row.label}</span>
                <span className="font-mono font-bold" style={{ color: row.color }}>{row.value}</span>
              </div>
            ))}
            <div className="border-t border-aurora-border pt-2 mt-1">
              <div className="flex items-center justify-between">
                <span className="text-aurora-subtext">Ruin Probability</span>
                <span className={`font-mono font-bold text-sm
                  ${monte.ruin_probability < 1 ? 'text-green-400' : monte.ruin_probability < 5 ? 'text-amber-400' : 'text-red-400'}`}>
                  {monte.ruin_probability?.toFixed(2)}%
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* --- ROW 4 RIGHT: CIRCUIT BREAKERS (4 cols) -------------------- */}
        <section className="col-span-4 aurora-card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
              Circuit Breakers
            </h2>
            <span className="text-[10px] font-mono text-aurora-subtext">
              {breakers.filter(b => b.tripped).length} TRIPPED
            </span>
          </div>
          <div className="space-y-1">
            <div className="flex items-center text-[9px] text-aurora-subtext uppercase tracking-wider py-1 px-2">
              <span className="flex-1">Breaker</span>
              <span className="w-16 text-right">Limit</span>
              <span className="w-16 text-right">Current</span>
              <span className="ml-2 w-4"></span>
            </div>
            {breakers.length > 0 ? breakers.map((b, i) => (
              <BreakerRow key={i} name={b.name} threshold={b.threshold} current={b.current} tripped={b.tripped} />
            )) : (
              <div className="text-xs text-aurora-subtext text-center py-4 font-mono">
                Awaiting data from /api/v1/risk/circuit-breakers
              </div>
            )}
          </div>
        </section>

        {/* --- ROW 4 REMAINING: POSITION VAR + TREEMAP (4 cols) ---------- */}
        <section className="col-span-4 aurora-card">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3">
            Position VaR
          </h2>
          <div className="overflow-auto custom-scrollbar">
            <table className="w-full">
              <thead>
                <tr className="text-[10px] text-aurora-subtext uppercase tracking-wider border-b border-aurora-border">
                  <th className="py-1.5 px-2 text-left">Symbol</th>
                  <th className="py-1.5 px-2 text-right">Wt</th>
                  <th className="py-1.5 px-2 text-right">VaR95</th>
                  <th className="py-1.5 px-2 text-right">VaR99</th>
                  <th className="py-1.5 px-2 text-right">Contrib</th>
                </tr>
              </thead>
              <tbody>
                {positions.length > 0 ? positions.map((p, i) => (
                  <VarRow key={i} symbol={p.symbol} weight={p.weight} var95={p.var95}
                          var99={p.var99} contribution={p.contribution} color={p.color} />
                )) : (
                  <tr>
                    <td colSpan={5} className="text-xs text-aurora-subtext text-center py-6 font-mono">
                      Awaiting data from /api/v1/risk/position-var
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {/* Treemap */}
          <div className="mt-3">
            <div className="aurora-label mb-2">VaR Contribution Treemap</div>
            <div className="flex flex-wrap gap-1 min-h-[60px]">
              {treemapItems.length > 0 ? treemapItems.map((t, i) => (
                <TreemapBlock key={i} symbol={t.symbol} pct={t.pct} color={t.color} />
              )) : (
                <div className="w-full h-full flex items-center justify-center text-xs text-aurora-subtext font-mono py-2">
                  Treemap -- populated by API
                </div>
              )}
            </div>
          </div>
        </section>

        {/* --- ROW 5: RISK RULES TABLE (12 cols, full width) ------------- */}
        <section className="col-span-12 bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4
                            hover:shadow-[0_0_20px_rgba(0,217,255,0.12)] transition-all">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3">
            Risk Rules Engine
          </h2>
          <RiskRulesTable riskData={riskData} shieldData={shieldData} breakersData={breakersData} />
        </section>

        {/* --- ROW 6: 90-DAY RISK HISTORY TIMELINE (12 cols) ------------- */}
        <section className="col-span-12 aurora-card">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3">
            90-Day Risk History
          </h2>
          <div className="h-20 rounded-aurora bg-[#0B0E14] border border-aurora-border flex items-end px-1 gap-px overflow-hidden">
            {history.length > 0 ? history.slice(-90).map((day, i) => {
              const h = Math.max(2, (day.score / 100) * 64);
              const barColor = day.score <= 35 ? C.green
                             : day.score <= 65 ? C.amber
                             : C.red;
              return (
                <div
                  key={i}
                  className="flex-1 rounded-t transition-all hover:opacity-80"
                  style={{ height: h, backgroundColor: barColor, minWidth: 2 }}
                  title={`${day.date}: score ${day.score}`}
                />
              );
            }) : (
              <div className="w-full h-full flex items-center justify-center text-xs text-aurora-subtext font-mono">
                Awaiting data from /api/v1/risk/history -- 90 daily risk scores
              </div>
            )}
          </div>
        </section>

        {/* --- ROW 7: ALIGNMENT ENGINE -- BRIGHT LINES + RECENT BLOCKS --- */}
        <section className="col-span-12 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="aurora-card">
          <h3 className="text-sm font-bold uppercase tracking-wider mb-3" style={{color: C.amber}}>Bright Lines -- Constitutional Limits</h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-[#0B0E14] rounded-aurora p-3">
              <div className="aurora-label">Portfolio Heat</div>
              <div className="text-lg font-bold text-aurora-text">{brightLines?.currentHeat ?? '--'}%</div>
              <div className="w-full bg-gray-800 rounded-full h-1.5 mt-1"><div className="h-1.5 rounded-full" style={{backgroundColor: C.cyan, width: `${Math.min(100, ((brightLines?.currentHeat ?? 0) / 25) * 100)}%`}} /></div>
              <div className="text-[9px] mt-0.5 text-aurora-subtext">Cap: 25%</div>
            </div>
            <div className="bg-[#0B0E14] rounded-aurora p-3">
              <div className="aurora-label">Drawdown</div>
              <div className="text-lg font-bold text-aurora-text">{brightLines?.currentDrawdown ?? '--'}%</div>
              <div className="w-full bg-gray-800 rounded-full h-1.5 mt-1"><div className="h-1.5 rounded-full" style={{backgroundColor: (brightLines?.currentDrawdown ?? 0) > 12 ? C.red : C.green, width: `${Math.min(100, ((brightLines?.currentDrawdown ?? 0) / 15) * 100)}%`}} /></div>
              <div className="text-[9px] mt-0.5 text-aurora-subtext">Cap: 15%</div>
            </div>
            <div className="bg-[#0B0E14] rounded-aurora p-3">
              <div className="aurora-label">Daily Trades</div>
              <div className="text-lg font-bold text-aurora-text">{brightLines?.todayTradeCount ?? '--'} / {brightLines?.dailyCap ?? 20}</div>
            </div>
            <div className="bg-[#0B0E14] rounded-aurora p-3">
              <div className="aurora-label">Circuit Breaker</div>
              <div className="text-lg font-bold" style={{color: brightLines?.haltActive ? C.red : C.green}}>{brightLines?.haltActive ? 'HALTED' : 'CLEAR'}</div>
            </div>
          </div>
        </div>
        <div className="aurora-card">
          <h3 className="text-sm font-bold uppercase tracking-wider mb-3" style={{color: C.red}}>Recent Alignment Blocks</h3>
          <div className="space-y-1 max-h-48 overflow-y-auto custom-scrollbar">
            {(recentVerdicts?.verdicts ?? []).filter(v => !v.allowed).slice(0, 8).map((v, i) => (
              <div key={i} className="flex items-center gap-2 py-1.5 px-2 text-xs border-b border-aurora-border/50 hover:bg-aurora-muted/10 transition-colors">
                <span className="font-mono w-20 shrink-0 text-aurora-subtext">{new Date(v.timestamp).toLocaleTimeString()}</span>
                <span className="font-bold w-14 text-aurora-text">{v.symbol}</span>
                <span className="px-1.5 py-0.5 rounded text-[9px] font-bold" style={{backgroundColor: C.red + '20', color: C.red}}>{v.blockedBy}</span>
                <span className="truncate text-aurora-subtext">{v.summary}</span>
              </div>
            ))}
            {(recentVerdicts?.verdicts ?? []).filter(v => !v.allowed).length === 0 && (
              <div className="text-xs text-aurora-subtext">No recent blocks</div>
            )}
          </div>
        </div>
        </section>
      </div>

      {/* === FOOTER ========================================================= */}
      <footer className="aurora-card flex items-center justify-between px-4 py-2
                         text-[10px] text-aurora-subtext font-mono">
        <span>Elite Trading System -- Risk Intelligence v2.0</span>
        <span>Embodier.ai -- {new Date().getFullYear()}</span>
        <span>
          Data: Alpaca | UW | FinViz | Refresh: {lastRefresh.toLocaleTimeString()}
        </span>
      </footer>
    </div>
  );
}
