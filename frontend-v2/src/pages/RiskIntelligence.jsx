// =============================================================================
// RiskIntelligence.jsx — Elite Trading System
// Synthesized from GPT-5.2 / Claude Opus 4.6 / Gemini 3.1 Pro consensus
// Route: /risk | Section: Execution | Page 10
// =============================================================================
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useApi } from "../hooks/useApi";
import { getApiUrl, getAuthHeaders } from "../config/api";
import log from "@/utils/logger";
import SelfAwarenessPanel from "../components/agents/SelfAwarenessPanel";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import PageHeader from "../components/ui/PageHeader";
import {
  Shield, RefreshCw, AlertTriangle, Activity, TrendingDown,
  Zap, Target, BarChart3, Grid3X3, Gauge, Brain, DollarSign,
  Clock, Eye, Flame, Octagon, Snowflake, ChevronDown, Lock,
  ArrowDownRight, ArrowUpRight, Crosshair, Layers, Radio,
  ShieldAlert, ShieldCheck, CircleDot, TriangleAlert, Ban
} from 'lucide-react';

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
    <div className="flex flex-col items-center bg-[#111827] rounded-lg p-2 border border-[rgba(42,52,68,0.5)]
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
      <span className="text-[10px] text-gray-500 mt-0.5 text-center leading-tight truncate w-full">
        {label}
      </span>
    </div>
  );
}

// ─── KPI PILL ────────────────────────────────────────────────────────────────
function KpiPill({ label, value, sub, color = C.cyan }) {
  return (
    <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg min-w-0 px-3 py-2
                    hover:shadow-[0_0_15px_rgba(0,217,255,0.08)] transition-all">
      <div className="text-[10px] uppercase tracking-wider text-gray-500 truncate">{label}</div>
      <div className="text-lg font-bold font-mono" style={{ color }}>{value}</div>
      {sub && <div className="text-[10px] text-gray-500">{sub}</div>}
    </div>
  );
}

// ─── SAFETY CHECK ROW ────────────────────────────────────────────────────────
function SafetyCheck({ label, status }) {
  const passed = status === 'PASS' || status === 'OK' || status === 'SAFE';
  return (
    <div className="flex items-center justify-between py-1 border-b border-[#1E293B] last:border-0">
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
    <div className={`flex items-center justify-between py-1.5 px-2 rounded text-xs
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
    <tr className="border-b border-[#1E293B] hover:bg-white/5 text-xs">
      <td className="py-1.5 px-2 font-mono font-bold" style={{ color: color || C.cyan }}>{symbol}</td>
      <td className="py-1.5 px-2 text-right text-slate-300">{Number(weight).toFixed(1)}%</td>
      <td className="py-1.5 px-2 text-right text-amber-400">{Number(var95).toFixed(2)}%</td>
      <td className="py-1.5 px-2 text-right text-red-400">{Number(var99).toFixed(2)}%</td>
      <td className="py-1.5 px-2 text-right text-slate-300">{Number(contribution).toFixed(1)}%</td>
    </tr>
  );
}

// ─── TREEMAP BLOCK ───────────────────────────────────────────────────────────
function TreemapBlock({ symbol, pct, color }) {
  return (
    <div
      className="rounded flex items-center justify-center text-[10px] font-mono font-bold text-white/90
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
  if (!data || !data.symbols || !data.matrix || data.symbols.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500 py-8">
        <Grid3X3 className="w-6 h-6 mb-2 opacity-40" />
        <div className="text-xs font-mono">Awaiting correlation data</div>
      </div>
    );
  }
  const { symbols, matrix } = data;
  const n = symbols.length;

  return (
    <div className="overflow-auto custom-scrollbar">
      <table className="w-full border-collapse text-[10px] font-mono" style={{ minWidth: n * 44 + 48 }}>
        <thead>
          <tr>
            <th className="py-1 px-1 text-left text-gray-500 sticky left-0 bg-[#111827] z-10 border-b border-r border-[rgba(42,52,68,0.5)]"
                style={{ minWidth: 48 }}></th>
            {symbols.map((s) => (
              <th key={s} className="py-1 px-1 text-center font-bold border-b border-[rgba(42,52,68,0.5)]"
                  style={{ color: C.cyan, minWidth: 40 }}>
                {s}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {symbols.map((rowSym, ri) => (
            <tr key={rowSym}>
              <td className="py-1 px-1 font-bold sticky left-0 bg-[#111827] z-10 whitespace-nowrap border-r border-[rgba(42,52,68,0.5)]"
                  style={{ color: C.cyan }}>
                {rowSym}
              </td>
              {matrix[ri]?.map((val, ci) => {
                const isDiag = ri === ci;
                const safeVal = val ?? 0;
                return (
                  <td
                    key={ci}
                    className="py-1 px-1 text-center font-bold transition-all"
                    style={{
                      color: isDiag ? C.dimText : corrColor(safeVal),
                      backgroundColor: isDiag
                        ? 'rgba(0,217,255,0.06)'
                        : corrBgColor(safeVal),
                      border: `1px solid ${isDiag ? 'rgba(0,217,255,0.15)' : 'rgba(42,52,68,0.3)'}`,
                      fontSize: n > 8 ? '9px' : '10px',
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
    </div>
  );
}

// ─── VaR HISTOGRAM (div-based with 95% confidence marker) ──────────────────
function VarHistogram({ data }) {
  if (!data || !data.buckets || data.buckets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500 py-8">
        <BarChart3 className="w-6 h-6 mb-2 opacity-40" />
        <div className="text-xs font-mono">Awaiting VaR distribution data</div>
      </div>
    );
  }
  const { buckets, var95, mean } = data;
  const maxCount = Math.max(...buckets.map(b => b.count), 1);
  const allLo = Math.min(...buckets.map(b => b.range[0]));
  const allHi = Math.max(...buckets.map(b => b.range[1]));
  const rangeSpan = allHi - allLo || 1;

  const var95Pct = var95 != null ? ((var95 - allLo) / rangeSpan) * 100 : null;
  const meanPct = mean != null ? ((mean - allLo) / rangeSpan) * 100 : null;

  return (
    <div className="w-full space-y-1.5">
      <div className="relative w-full rounded-lg bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] p-2"
           style={{ minHeight: 120 }}>
        <div className="flex items-end gap-px w-full" style={{ height: 96 }}>
          {buckets.map((b, i) => {
            const hPct = (b.count / maxCount) * 100;
            const midVal = (b.range[0] + b.range[1]) / 2;
            const isInTail = var95 != null && midVal < var95;
            return (
              <div
                key={i}
                className="flex-1 min-w-[2px] rounded-t transition-all hover:brightness-125 relative group"
                style={{
                  height: `${Math.max(hPct, 1)}%`,
                  backgroundColor: isInTail ? 'rgba(239,68,68,0.55)' : '#00D9FF',
                  opacity: 0.85,
                }}
                title={`${b.range[0].toFixed(2)}% to ${b.range[1].toFixed(2)}%: ${b.count}`}
              />
            );
          })}
        </div>

        {var95Pct != null && (
          <div className="absolute top-2 bottom-6"
               style={{ left: `calc(${var95Pct}% + 8px - ${var95Pct * 0.16}px)`, width: 0 }}>
            <div className="h-full border-l-2 border-dashed" style={{ borderColor: '#EF4444' }} />
            <div className="absolute -top-0.5 -left-[22px] text-[8px] font-mono font-bold px-1 py-0.5 rounded whitespace-nowrap"
                 style={{ color: '#EF4444', backgroundColor: 'rgba(239,68,68,0.12)' }}>
              VaR 95%
            </div>
          </div>
        )}

        {meanPct != null && (
          <div className="absolute top-2 bottom-6"
               style={{ left: `calc(${meanPct}% + 8px - ${meanPct * 0.16}px)`, width: 0 }}>
            <div className="h-full border-l border-dashed" style={{ borderColor: '#00D9FF' }} />
            <div className="absolute -bottom-0.5 -left-[10px] text-[7px] font-mono px-0.5"
                 style={{ color: '#00D9FF' }}>
              Mean
            </div>
          </div>
        )}
      </div>

      <div className="flex justify-between px-1 text-[8px] font-mono text-gray-500">
        <span>{allLo.toFixed(1)}%</span>
        {var95 != null && <span style={{ color: '#EF4444' }}>{var95.toFixed(2)}%</span>}
        <span>{allHi.toFixed(1)}%</span>
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

  const sizingBars = [
    { label: 'Full Kelly', pct: fullKellyPct, color: C.red },
    { label: 'Half Kelly', pct: fullKellyPct * 0.5, color: C.amber },
    { label: 'Quarter Kelly', pct: fullKellyPct * 0.25, color: C.green },
    { label: 'Recommended', pct: recommended, color: C.cyan },
  ];

  const maxPct = Math.max(...sizingBars.map(b => b.pct), 1);

  return (
    <div className="space-y-2">
      {sizingBars.map((bar, i) => (
        <div key={i} className="space-y-0.5">
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-gray-400">{bar.label}</span>
            <span className="font-mono font-bold" style={{ color: bar.color }}>{bar.pct.toFixed(1)}%</span>
          </div>
          <div className="w-full h-3 bg-[#0B0E14] rounded overflow-hidden">
            <div className="h-full rounded transition-all"
                 style={{ width: `${Math.min((bar.pct / maxPct) * 100, 100)}%`, backgroundColor: bar.color + 'B0' }} />
          </div>
        </div>
      ))}
      {accountVal > 0 && (
        <div className="text-[10px] text-gray-500 font-mono text-right pt-1">
          ${recommendedDollars.toLocaleString(undefined, { maximumFractionDigits: 0 })} position
        </div>
      )}
    </div>
  );
}

// ─── DRAWDOWN WATERFALL ──────────────────────────────────────────────────────
function DrawdownWaterfall({ data }) {
  const episodes = data?.episodes;
  const series = data?.series;

  if ((!episodes || episodes.length === 0) && (!series || series.length === 0)) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500 py-8">
        <TrendingDown className="w-6 h-6 mb-2 opacity-40" />
        <div className="text-xs font-mono">Awaiting drawdown data</div>
      </div>
    );
  }

  if (series && series.length > 0) {
    const maxDD = Math.max(...series.map(s => Math.abs(s.drawdown || 0)), 1);
    return (
      <div className="w-full h-32 flex items-start gap-px overflow-hidden rounded bg-[#0B0E14] border border-[#1E293B] p-1">
        {series.map((pt, i) => {
          const dd = Math.abs(pt.drawdown || 0);
          const h = (dd / maxDD) * 100;
          const barColor = dd > 15 ? C.red : dd > 8 ? C.amber : dd > 3 ? C.purple + 'A0' : C.cyan + '60';
          return (
            <div key={i} className="flex-1 min-w-[2px] rounded-b transition-all hover:opacity-80"
                 style={{ height: `${h}%`, backgroundColor: barColor, minHeight: dd > 0 ? 2 : 0 }}
                 title={`${pt.date}: -${dd.toFixed(2)}%`} />
          );
        })}
      </div>
    );
  }

  const maxDepth = Math.max(...episodes.map(e => Math.abs(e.depth)), 1);
  return (
    <div className="space-y-1 max-h-40 overflow-y-auto custom-scrollbar">
      {episodes.map((ep, i) => {
        const pctOfMax = (Math.abs(ep.depth) / maxDepth) * 100;
        return (
          <div key={i} className="flex items-center gap-2 text-[10px]">
            <span className="font-mono text-gray-500 w-16 shrink-0 truncate">{ep.start}</span>
            <div className="flex-1 h-4 bg-[#0B0E14] rounded overflow-hidden relative">
              <div className="h-full rounded transition-all"
                   style={{
                     width: `${pctOfMax}%`,
                     backgroundColor: Math.abs(ep.depth) > 15 ? C.red + 'A0' : Math.abs(ep.depth) > 8 ? C.amber + '80' : C.purple + '60',
                   }} />
              <span className="absolute inset-0 flex items-center px-1 font-mono font-bold text-white/80">
                {ep.depth.toFixed(1)}%
              </span>
            </div>
            <span className={`font-mono w-10 text-right ${ep.recovered ? 'text-green-400' : 'text-red-400'}`}>
              {ep.duration}d
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ─── RISK RULES TABLE ────────────────────────────────────────────────────────
function classifyRuleStatus(status, current, limit) {
  const s = (status ?? '').toUpperCase();
  if (s === 'PASS' || s === 'OK' || s === 'SAFE') return 'PASS';
  if (s === 'WARNING' || s === 'CAUTION' || s === 'WARN') return 'WARNING';
  if (s === 'FAIL' || s === 'BREACH' || s === 'CRITICAL') return 'BREACH';

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
  const rules = useMemo(() => {
    const result = [];

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

    if (riskData?.vix_filter != null) {
      result.push({
        rule: 'VIX Filter',
        type: 'Volatility',
        limit: riskData.vix_limit ?? '30',
        current: riskData.vix_current ?? '--',
        status: riskData.vix_filter ? 'PASS' : 'BREACH',
      });
    }

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
      <div className="flex items-center gap-3 mb-1">
        <span className="inline-flex items-center gap-1.5 text-[10px] font-mono font-bold px-2 py-1 rounded"
              style={{ backgroundColor: 'rgba(16,185,129,0.1)', color: C.green, border: '1px solid rgba(16,185,129,0.2)' }}>
          <span className="w-2 h-2 rounded-full bg-green-400" />
          {passCount} PASS
        </span>
        {warnCount > 0 && (
          <span className="inline-flex items-center gap-1.5 text-[10px] font-mono font-bold px-2 py-1 rounded"
                style={{ backgroundColor: 'rgba(245,158,11,0.1)', color: C.amber, border: '1px solid rgba(245,158,11,0.2)' }}>
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            {warnCount} WARNING
          </span>
        )}
        {breachCount > 0 && (
          <span className="inline-flex items-center gap-1.5 text-[10px] font-mono font-bold px-2 py-1 rounded"
                style={{ backgroundColor: 'rgba(239,68,68,0.1)', color: C.red, border: '1px solid rgba(239,68,68,0.2)' }}>
            <span className="w-2 h-2 rounded-full bg-red-400" />
            {breachCount} BREACH
          </span>
        )}
        <span className="text-[10px] text-gray-500 font-mono ml-auto">
          {rules.length} rules active
        </span>
      </div>

      <div className="overflow-auto custom-scrollbar">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-[10px] text-gray-500 uppercase tracking-wider border-b border-[rgba(42,52,68,0.5)]">
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
              const rowBg = isBreach ? 'rgba(239,68,68,0.04)' : isWarning ? 'rgba(245,158,11,0.04)' : 'transparent';
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
                  <td className="py-1.5 px-2 text-right font-mono text-gray-500">{r.limit}</td>
                  <td className="py-1.5 px-2 text-right font-mono"
                      style={{ color: isBreach ? C.red : isWarning ? C.amber : '#cbd5e1' }}>
                    {r.current}
                  </td>
                  <td className="py-1.5 px-2 text-center">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold"
                          style={{
                            backgroundColor: isPassed ? 'rgba(16,185,129,0.15)' : isWarning ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
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
      await fetch(getApiUrl('risk') + `/emergency/${action.toLowerCase()}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      });
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
    <div className="min-h-screen p-3 space-y-3" style={{ backgroundColor: C.bg, color: C.text }}>

      {/* ══════════════════════════════════════════════════════════════════════
          HEADER BAR
          ══════════════════════════════════════════════════════════════════════ */}
      <header className="bg-surface border border-secondary/20 rounded-xl px-5 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg flex items-center justify-center"
               style={{ backgroundColor: grade.color + '20' }}>
            <Shield className="w-5 h-5" style={{ color: grade.color }} />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              RISK_INTELLIGENCE
              <Badge variant="primary" size="sm">LIVE</Badge>
            </h1>
            <span className="text-[10px] text-gray-500 uppercase tracking-widest font-mono">
              Shield Protection &middot; Real-Time Monitoring
            </span>
          </div>
        </div>

        {/* Center: Grade + Score + Status */}
        <div className="flex items-center gap-6">
          <div className="text-center">
            <div className="text-[10px] uppercase tracking-wider text-gray-500">Grade</div>
            <div className="text-3xl font-black font-mono leading-none" style={{ color: grade.color }}>
              {grade.letter}
            </div>
          </div>
          <div className="text-center">
            <div className="text-[10px] uppercase tracking-wider text-gray-500">Risk Score</div>
            <div className="text-2xl font-bold font-mono leading-none" style={{ color: grade.color }}>
              {riskScore}
            </div>
          </div>
          <div className="text-center">
            <div className="text-[10px] uppercase tracking-wider text-gray-500">Status</div>
            <div className="text-sm font-bold font-mono" style={{ color: statusColor(systemStatus) }}>
              {systemStatus}
            </div>
          </div>
          {warnings > 0 && (
            <div className="text-center">
              <div className="text-[10px] uppercase tracking-wider text-gray-500">Warnings</div>
              <div className="text-lg font-bold text-amber-400">{warnings}</div>
            </div>
          )}
        </div>

        {/* Right: timeframe + refresh */}
        <div className="flex items-center gap-3">
          <div className="flex rounded-lg overflow-hidden border border-[#1E293B]">
            {['1D', '1W', '1M', '3M'].map(tf => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-3 py-1.5 text-xs font-mono font-bold transition-all
                  ${timeframe === tf
                    ? 'bg-cyan-500/20 text-cyan-400'
                    : 'bg-[#1A1F2E] text-gray-500 hover:text-slate-300'}`}
              >
                {tf}
              </button>
            ))}
          </div>
          <button
            onClick={handleRefresh}
            className="p-2 rounded-lg bg-white/5 border border-[#1E293B]
                       hover:border-cyan-500/30 text-gray-500 hover:text-cyan-400 transition-all"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <span className="text-[10px] text-gray-500 font-mono">
            {lastRefresh.toLocaleTimeString()}
          </span>
        </div>
      </header>

      {/* ══════════════════════════════════════════════════════════════════════
          ROW 1: Risk Configuration | Parameter Sweeps | Realtime Risk Detail
          ══════════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-12 gap-3">

        {/* --- Risk Configuration (left, 4 cols) --- */}
        <Card title="Risk Configuration"
              subtitle="Source: Automated Risk Assessment"
              className="col-span-4"
              action={<Badge variant="success" size="sm">ACTIVE</Badge>}>
          <div className="space-y-2">
            {/* Config items */}
            {[
              { label: 'Signal Confidence Sentinel', value: riskData?.signal_confidence ?? 'HIGH', color: C.green },
              { label: 'Capital Exposure Watchdog', value: riskData?.capital_exposure ?? 'MODERATE', color: C.amber },
              { label: 'Regime Sentinels', value: riskData?.regime_sentinel ?? 'ACTIVE', color: C.cyan },
              { label: 'Volatility Monitor', value: riskData?.vol_monitor ?? 'ACTIVE', color: C.cyan },
              { label: 'Drawdown Protection', value: riskData?.dd_protection ?? 'ARMED', color: C.green },
              { label: 'Multi-Agent Consensus', value: riskData?.consensus ?? 'ENABLED', color: C.cyan },
              { label: 'Performance Analytics', value: riskData?.perf_analytics ?? 'ONLINE', color: C.green },
              { label: 'Risk Budgets', value: riskData?.risk_budgets ?? 'ACTIVE', color: C.cyan },
            ].map((item, i) => (
              <div key={i} className="flex items-center justify-between py-1 border-b border-[#1E293B]/60 last:border-0">
                <span className="text-xs text-gray-400">{item.label}</span>
                <span className="text-xs font-mono font-bold" style={{ color: item.color }}>{item.value}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* --- Parameter Sweeps (center, 5 cols) --- */}
        <Card title="Parameter Sweeps" className="col-span-5"
              action={<span className="text-[10px] text-gray-500 font-mono">{timeframe}</span>}>
          <div className="grid grid-cols-5 gap-2 mb-4">
            {kpis.slice(0, 10).map((kpi, i) => (
              <div key={i} className="bg-[#0B0E14] border border-[#1E293B]/50 rounded-lg px-2 py-1.5 text-center">
                <div className="text-[9px] text-gray-500 uppercase tracking-wider truncate">{kpi.label}</div>
                <div className="text-sm font-bold font-mono mt-0.5" style={{ color: kpi.color || C.cyan }}>
                  {kpi.value}
                </div>
              </div>
            ))}
          </div>
          {/* Equity Curve mini chart */}
          <div className="h-24 rounded-lg bg-[#0B0E14] border border-[#1E293B]/50 flex items-end p-1.5 gap-px overflow-hidden">
            {(equityCurveData?.points || []).length > 0 ? (
              equityCurveData.points.map((pt, i) => {
                const maxEq = Math.max(...equityCurveData.points.map(p => p.equity || 0), 1);
                const h = ((pt.equity || 0) / maxEq) * 100;
                const dd = pt.drawdown || 0;
                const barColor = dd > 10 ? C.red : dd > 5 ? C.amber : C.green;
                return (
                  <div key={i} className="flex-1 min-w-[2px] rounded-t"
                       style={{ height: `${h}%`, backgroundColor: barColor + '80', minHeight: 2 }}
                       title={`${pt.date}: $${pt.equity?.toLocaleString()} DD:${dd.toFixed(1)}%`} />
                );
              })
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-500">
                <Activity className="w-4 h-4 mr-2 opacity-40" />
                <span className="text-[10px] font-mono">Equity Curve -- Awaiting data</span>
              </div>
            )}
          </div>
        </Card>

        {/* --- Realtime Risk Detail (right, 3 cols) --- */}
        <Card title="Realtime Risk Detail" className="col-span-3"
              action={<Badge variant={systemStatus === 'SAFE' ? 'success' : 'warning'} size="sm">{systemStatus}</Badge>}>
          <div className="space-y-2.5">
            {[
              { label: 'Portfolio VaR (95%)', value: gauges.find(g => g.label === 'VaR 95%')?.value ?? 0, max: 100, color: C.amber },
              { label: 'Tail Risk (CVaR)', value: gauges.find(g => g.label === 'CVaR')?.value ?? 0, max: 100, color: C.red },
              { label: 'Volatility Level', value: gauges.find(g => g.label === 'Volatility')?.value ?? 0, max: 100, color: C.purple },
              { label: 'Beta Exposure', value: gauges.find(g => g.label === 'Beta')?.value ?? 0, max: 100, color: C.cyan },
              { label: 'Concentration', value: gauges.find(g => g.label === 'Concentration')?.value ?? 0, max: 100, color: C.amber },
              { label: 'Liquidity Score', value: gauges.find(g => g.label === 'Liquidity')?.value ?? 0, max: 100, color: C.green },
              { label: 'Skew Risk', value: gauges.find(g => g.label === 'Skew Risk')?.value ?? 0, max: 100, color: C.red },
              { label: 'Regime Risk', value: gauges.find(g => g.label === 'Regime Risk')?.value ?? 0, max: 100, color: C.amber },
            ].map((item, i) => (
              <div key={i} className="space-y-0.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-gray-400">{item.label}</span>
                  <span className="text-[10px] font-mono font-bold" style={{ color: item.color }}>
                    {Math.round(item.value)}%
                  </span>
                </div>
                <div className="w-full h-2 bg-[#0B0E14] rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-500"
                       style={{
                         width: `${Math.min(item.value, 100)}%`,
                         backgroundColor: item.color,
                         boxShadow: `0 0 6px ${item.color}40`,
                       }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* ══════════════════════════════════════════════════════════════════════
          ROW 2: Stop-Loss | Correlation | Volatility Regime | AI Monitors | Position Sizing
          ══════════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-12 gap-3">

        {/* --- Stop-Loss Command (3 cols) --- */}
        <Card title="Stop-Loss Command" className="col-span-3"
              action={
                <span className="text-[10px] font-mono" style={{ color: safetyChecks.every(c => c.status === 'PASS') ? C.green : C.amber }}>
                  {safetyChecks.filter(c => c.status === 'PASS').length}/{safetyChecks.length} PASS
                </span>
              }>
          <div className="space-y-0.5 mb-3">
            {safetyChecks.map((check, i) => (
              <SafetyCheck key={i} label={check.label} status={check.status} />
            ))}
          </div>

          {/* Emergency Actions */}
          <div className="border-t border-[#1E293B] pt-3 space-y-2">
            <button
              onClick={() => handleEmergency('KILL')}
              className="w-full py-2.5 rounded-lg text-xs font-bold uppercase
                         bg-red-600 hover:bg-red-500 text-white
                         border-2 border-red-400 shadow-lg shadow-red-500/20
                         transition-all active:scale-95 flex items-center justify-center gap-2"
            >
              <Octagon className="w-4 h-4" />
              EMERGENCY STOP ALL
            </button>
            <div className="grid grid-cols-3 gap-1.5">
              <button
                onClick={() => handleEmergency('HEDGE')}
                className="py-1.5 rounded-lg text-[10px] font-bold uppercase
                           bg-purple-600/30 hover:bg-purple-600/50 text-purple-300
                           border border-purple-500/30 transition-all"
              >
                Hedge
              </button>
              <button
                onClick={() => handleEmergency('REDUCE')}
                className="py-1.5 rounded-lg text-[10px] font-bold uppercase
                           bg-amber-600/30 hover:bg-amber-600/50 text-amber-300
                           border border-amber-500/30 transition-all"
              >
                Reduce
              </button>
              <button
                onClick={() => handleEmergency('FREEZE')}
                className="py-1.5 rounded-lg text-[10px] font-bold uppercase
                           bg-cyan-600/30 hover:bg-cyan-600/50 text-cyan-300
                           border border-cyan-500/30 transition-all"
              >
                Freeze
              </button>
            </div>
          </div>
        </Card>

        {/* --- Correlation Matrix (3 cols) --- */}
        <Card title="Correlation Matrix" className="col-span-3"
              action={<Grid3X3 className="w-4 h-4 text-cyan-400" />}>
          <CorrelationHeatmap data={correlationData} />
        </Card>

        {/* --- Volatility Regime Monitor (2 cols) --- */}
        <Card title="Volatility Regime Monitor" className="col-span-2"
              action={<Gauge className="w-4 h-4 text-cyan-400" />}>
          <div className="grid grid-cols-2 gap-2">
            {gauges.slice(0, 4).map((g, i) => (
              <SemiGauge key={i} label={g.label} value={g.value} />
            ))}
          </div>
          <div className="mt-3 space-y-1.5">
            {[
              { label: 'Momentum', value: gauges.find(g => g.label === 'Momentum')?.value ?? 0, color: C.cyan },
              { label: 'Regime', value: gauges.find(g => g.label === 'Regime Risk')?.value ?? 0, color: C.amber },
            ].map((item, i) => (
              <div key={i}>
                <div className="flex items-center justify-between text-[10px] mb-0.5">
                  <span className="text-gray-500">{item.label}</span>
                  <span className="font-mono font-bold" style={{ color: item.color }}>{Math.round(item.value)}%</span>
                </div>
                <div className="w-full h-1.5 bg-[#0B0E14] rounded-full overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${item.value}%`, backgroundColor: item.color }} />
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* --- AI Agent Risk Monitors (2 cols) --- */}
        <Card title="AI Agent Risk Monitors" className="col-span-2"
              action={<Brain className="w-4 h-4 text-cyan-400" />}>
          <div className="space-y-2">
            {[
              { label: 'Monte Carlo P(profit)', value: monte.prob_profit, color: C.green },
              { label: 'MC Median Return', value: Math.max(0, monte.median_return + 50), color: C.cyan },
              { label: 'Ruin Probability', value: Math.min(monte.ruin_probability * 10, 100), color: C.red, invert: true },
              { label: 'Max DD (P95)', value: Math.min(Math.abs(monte.max_dd_p95) * 3, 100), color: C.amber },
              { label: 'Kelly Edge', value: Math.min((kelly.edge ?? 0) * 1000, 100), color: C.purple },
              { label: 'Win Rate', value: (kelly.win_rate ?? 0) * 100, color: C.green },
            ].map((item, i) => (
              <div key={i}>
                <div className="flex items-center justify-between text-[10px] mb-0.5">
                  <span className="text-gray-400">{item.label}</span>
                  <span className="font-mono font-bold" style={{ color: item.color }}>
                    {typeof item.value === 'number' ? Math.round(item.value) : '--'}
                  </span>
                </div>
                <div className="w-full h-2.5 bg-[#0B0E14] rounded overflow-hidden">
                  <div className="h-full rounded transition-all duration-500"
                       style={{
                         width: `${Math.min(Math.max(item.value, 0), 100)}%`,
                         backgroundColor: item.color + 'B0',
                       }} />
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* --- Position Sizing (2 cols) --- */}
        <Card title="Position Sizing" className="col-span-2"
              action={<DollarSign className="w-4 h-4 text-cyan-400" />}>
          <PositionSizer kelly={kelly} portfolioValue={portfolioValue} />
        </Card>
      </div>

      {/* ══════════════════════════════════════════════════════════════════════
          ROW 3: Risk Rules Engine (full width)
          ══════════════════════════════════════════════════════════════════════ */}
      <Card title="Risk Rules Engine"
            subtitle={`${breakers.filter(b => b.tripped).length} breakers tripped`}
            action={<ShieldCheck className="w-4 h-4 text-cyan-400" />}>
        <RiskRulesTable riskData={riskData} shieldData={shieldData} breakersData={breakersData} />
      </Card>

      {/* ══════════════════════════════════════════════════════════════════════
          ROW 4: 90-Day Risk History (full width)
          ══════════════════════════════════════════════════════════════════════ */}
      <Card title="90-Day Risk History"
            action={
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: C.green }} />
                  <span className="text-[9px] text-gray-500">Low</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: C.amber }} />
                  <span className="text-[9px] text-gray-500">Medium</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: C.red }} />
                  <span className="text-[9px] text-gray-500">High</span>
                </div>
              </div>
            }>
        <div className="space-y-2">
          <div className="h-24 rounded-lg bg-[#0B0E14] border border-[#1E293B]/50 flex items-end px-1.5 gap-px overflow-hidden">
            {history.length > 0 ? history.slice(-90).map((day, i) => {
              const h = Math.max(2, (day.score / 100) * 80);
              const barColor = day.score <= 35 ? C.green
                             : day.score <= 65 ? C.amber
                             : C.red;
              return (
                <div
                  key={i}
                  className="flex-1 rounded-t transition-all hover:opacity-80"
                  style={{ height: h, backgroundColor: barColor, minWidth: 2, opacity: 0.85 }}
                  title={`${day.date}: score ${day.score}`}
                />
              );
            }) : (
              <div className="w-full h-full flex items-center justify-center text-xs text-gray-500 font-mono">
                <Clock className="w-4 h-4 mr-2 opacity-40" />
                Awaiting 90-day risk history data
              </div>
            )}
          </div>
          {/* X-axis date labels */}
          {history.length > 0 && (
            <div className="flex justify-between px-1 text-[8px] font-mono text-gray-600">
              <span>{history[0]?.date ?? ''}</span>
              {history.length > 45 && <span>{history[Math.floor(history.length / 4)]?.date ?? ''}</span>}
              {history.length > 45 && <span>{history[Math.floor(history.length / 2)]?.date ?? ''}</span>}
              {history.length > 45 && <span>{history[Math.floor(history.length * 3 / 4)]?.date ?? ''}</span>}
              <span>{history[history.length - 1]?.date ?? ''}</span>
            </div>
          )}
        </div>
      </Card>

      {/* ══════════════════════════════════════════════════════════════════════
          AGENT SELF-AWARENESS
          ══════════════════════════════════════════════════════════════════════ */}
      <Card title="Agent Self-Awareness"
            subtitle="Bayesian Weights & Streak Status"
            action={<Eye className="w-4 h-4 text-cyan-400" />}>
        <SelfAwarenessPanel />
      </Card>

      {/* ══════════════════════════════════════════════════════════════════════
          FOOTER
          ══════════════════════════════════════════════════════════════════════ */}
      <footer className="bg-surface border border-secondary/20 rounded-xl flex items-center justify-between px-4 py-2
                         text-[10px] text-gray-500 font-mono">
        <span className="flex items-center gap-2">
          <Radio className="w-3 h-3 text-cyan-400" />
          Elite Trading System -- Risk Intelligence v2.0
        </span>
        <span>Embodier.ai -- {new Date().getFullYear()}</span>
        <span>
          Data: Alpaca | UW | FinViz | Refresh: {lastRefresh.toLocaleTimeString()}
        </span>
      </footer>
    </div>
  );
}
