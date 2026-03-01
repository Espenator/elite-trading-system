// =============================================================================
// RiskIntelligence.jsx — Elite Trading System
// Synthesized from GPT-5.2 / Claude Opus 4.6 / Gemini 3.1 Pro consensus
// Route: /risk | Section: Execution | Page 10
// =============================================================================
import React, { useState, useEffect, useCallback } from 'react';
import { useApi } from "../hooks/useApi";

// ─── COLOR PALETTE (institutional terminal) ──────────────────────────────────
const C = {
  bg:        '#0A0E17',
  surface:   '#111827',
  card:      '#1A1F2E',
  border:    '#1E293B',
  cyan:      '#00D9FF',
  green:     '#10B981',
  red:       '#EF4444',
  amber:     '#F59E0B',
  purple:    '#A855F7',
  text:      '#F1F5F9',
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
    <div className="flex flex-col items-center bg-[#111827] rounded-lg p-2 border border-[#1E293B]">
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
      <span className="text-[10px] text-slate-400 mt-0.5 text-center leading-tight truncate w-full">
        {label}
      </span>
    </div>
  );
}

// ─── KPI PILL ────────────────────────────────────────────────────────────────
function KpiPill({ label, value, sub, color = C.cyan }) {
  return (
    <div className="bg-[#111827] rounded-lg px-3 py-2 border border-[#1E293B] min-w-0">
      <div className="text-[10px] text-slate-500 uppercase tracking-wider truncate">{label}</div>
      <div className="text-lg font-bold font-mono" style={{ color }}>{value}</div>
      {sub && <div className="text-[10px] text-slate-500">{sub}</div>}
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
        {passed ? '✓ PASS' : '✗ FAIL'}
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
        {tripped ? '!' : '✓'}
      </span>
    </div>
  );
}

// ─── POSITION VAR ROW ────────────────────────────────────────────────────────
function VarRow({ symbol, weight, var95, var99, contribution, color }) {
  return (
    <tr className="border-b border-[#1E293B] hover:bg-[#1A1F2E]/50 text-xs">
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
      className="rounded flex items-center justify-center text-[10px] font-mono font-bold text-white/90
                 border border-white/5 transition-all hover:brightness-125"
      style={{ backgroundColor: color || C.cyan + '40', flexBasis: `${Math.max(pct, 8)}%`, minHeight: 32 }}
      title={`${symbol}: ${pct.toFixed(1)}% VaR contribution`}
    >
      {symbol} {pct.toFixed(0)}%
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
  const { data: riskData,      loading: riskLoading }    = useApi('/api/v1/risk');
  const { data: shieldData,    loading: shieldLoading }  = useApi('/api/v1/risk/shield');
  const { data: gaugesData,    loading: gaugesLoading }  = useApi('/api/v1/risk/risk-gauges');
  const { data: kellyData,     loading: kellyLoading }   = useApi('/api/v1/risk/kelly');
  const { data: monteData,     loading: monteLoading }   = useApi('/api/v1/risk/monte-carlo');
  const { data: breakersData,  loading: breakersLoading }= useApi('/api/v1/risk/circuit-breakers');
  const { data: varData,       loading: varLoading }     = useApi('/api/v1/risk/position-var');
  const { data: historyData,   loading: histLoading }    = useApi('/api/v1/risk/history');
  const { data: portfolioData }                          = useApi('/api/v1/portfolio');

  const handleRefresh = useCallback(() => setLastRefresh(new Date()), []);

  // ─── DERIVED VALUES ──────────────────────────────────────────────────────
  const riskScore    = riskData?.risk_score ?? 0;
  const grade        = gradeFromScore(riskScore);
  const systemStatus = riskData?.system_status ?? 'UNKNOWN';
  const warnings     = riskData?.warnings ?? 0;

  // KPI array from API
  const kpis = riskData?.kpis ?? [
    { label: 'Portfolio Value',     value: '$—',       color: C.text },
    { label: 'Daily P&L',          value: '$—',       color: C.muted },
    { label: 'Max Drawdown',       value: '—%',       color: C.muted },
    { label: 'Current DD',         value: '—%',       color: C.muted },
    { label: 'Sharpe Ratio',       value: '—',        color: C.muted },
    { label: 'Win Rate',           value: '—%',       color: C.muted },
    { label: 'Profit Factor',      value: '—',        color: C.muted },
    { label: 'Open Positions',     value: '—',        color: C.muted },
    { label: 'Daily Trades',       value: '—',        color: C.muted },
    { label: 'Exposure',           value: '—%',       color: C.muted },
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

  // ─── EMERGENCY ACTIONS ───────────────────────────────────────────────────
  const handleEmergency = async (action) => {
    if (action === 'KILL' && !window.confirm(
      '🚨 KILL SWITCH: This will CLOSE ALL POSITIONS and HALT TRADING.\n\nAre you absolutely sure?'
    )) return;
    try {
      await fetch(`/api/v1/risk/emergency/${action.toLowerCase()}`, { method: 'POST' });
      handleRefresh();
    } catch (err) {
      console.error(`Emergency ${action} failed:`, err);
    }
  };

  // ─── LOADING STATE ───────────────────────────────────────────────────────
  const isLoading = riskLoading || shieldLoading || gaugesLoading;

  // =========================================================================
  // RENDER
  // =========================================================================
  return (
    <div className="min-h-screen p-3 space-y-3" style={{ backgroundColor: C.bg, color: C.text }}>

      {/* ═══ HEADER ═══════════════════════════════════════════════════════ */}
      <header className="flex items-center justify-between bg-[#111827] rounded-lg px-4 py-3 border border-[#1E293B]">
        {/* Left: shield + title */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center text-xl"
               style={{ backgroundColor: grade.color + '20', color: grade.color }}>
            🛡
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Risk Intelligence</h1>
            <span className="text-[10px] text-slate-500 uppercase tracking-widest">
              Shield Protection • Real-Time Monitoring
            </span>
          </div>
        </div>

        {/* Center: Grade + Score + Status */}
        <div className="flex items-center gap-6">
          <div className="text-center">
            <div className="text-[10px] text-slate-500 uppercase">Grade</div>
            <div className="text-3xl font-black font-mono" style={{ color: grade.color }}>
              {grade.letter}
            </div>
          </div>
          <div className="text-center">
            <div className="text-[10px] text-slate-500 uppercase">Risk Score</div>
            <div className="text-2xl font-bold font-mono" style={{ color: grade.color }}>
              {riskScore}
            </div>
          </div>
          <div className="text-center">
            <div className="text-[10px] text-slate-500 uppercase">Status</div>
            <div className="text-sm font-bold font-mono" style={{ color: statusColor(systemStatus) }}>
              ● {systemStatus}
            </div>
          </div>
          {warnings > 0 && (
            <div className="text-center">
              <div className="text-[10px] text-slate-500 uppercase">Warnings</div>
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
                    : 'bg-[#111827] text-slate-500 hover:text-slate-300'}`}
              >
                {tf}
              </button>
            ))}
          </div>
          <button
            onClick={handleRefresh}
            className="p-2 rounded-lg bg-[#1A1F2E] border border-[#1E293B]
                       hover:border-cyan-500/30 text-slate-400 hover:text-cyan-400 transition-all"
            title="Refresh"
          >
            ↻
          </button>
          <span className="text-[10px] text-slate-600 font-mono">
            {lastRefresh.toLocaleTimeString()}
          </span>
        </div>
      </header>

      {/* ═══ 10-KPI STRIP ════════════════════════════════════════════════ */}
      <div className="grid grid-cols-10 gap-2">
        {kpis.map((kpi, i) => (
          <KpiPill key={i} label={kpi.label} value={kpi.value} sub={kpi.sub} color={kpi.color || C.cyan} />
        ))}
      </div>

      {/* ═══ MAIN GRID — 12-COLUMN DENSE ═════════════════════════════════ */}
      <div className="grid grid-cols-12 gap-3 auto-rows-auto">

        {/* ─── ROW 1 LEFT: RISK SHIELD COMMAND CENTER (5 cols) ──────── */}
        <section className="col-span-5 bg-[#111827] rounded-lg border border-[#1E293B] p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
              🛡 Risk Shield — 9 Safety Checks
            </h2>
            <span className="text-xs font-mono px-2 py-0.5 rounded"
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
          <div className="border-t border-[#1E293B] pt-3">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">
              Emergency Actions
            </div>
            <div className="grid grid-cols-4 gap-2">
              <button
                onClick={() => handleEmergency('KILL')}
                className="py-2 px-2 rounded-lg text-xs font-bold uppercase
                           bg-red-600 hover:bg-red-500 text-white
                           border-2 border-red-400 shadow-lg shadow-red-500/20
                           transition-all active:scale-95"
              >
                ⛔ Kill
              </button>
              <button
                onClick={() => handleEmergency('HEDGE')}
                className="py-2 px-2 rounded-lg text-xs font-bold uppercase
                           bg-purple-600/30 hover:bg-purple-600/50 text-purple-300
                           border border-purple-500/30 transition-all active:scale-95"
              >
                🔒 Hedge
              </button>
              <button
                onClick={() => handleEmergency('REDUCE')}
                className="py-2 px-2 rounded-lg text-xs font-bold uppercase
                           bg-amber-600/30 hover:bg-amber-600/50 text-amber-300
                           border border-amber-500/30 transition-all active:scale-95"
              >
                📉 Reduce
              </button>
              <button
                onClick={() => handleEmergency('FREEZE')}
                className="py-2 px-2 rounded-lg text-xs font-bold uppercase
                           bg-cyan-600/30 hover:bg-cyan-600/50 text-cyan-300
                           border border-cyan-500/30 transition-all active:scale-95"
              >
                ❄ Freeze
              </button>
            </div>
          </div>
        </section>

        {/* ─── ROW 1 RIGHT: EQUITY / DRAWDOWN with VaR BANDS (7 cols) ─ */}
        <section className="col-span-7 bg-[#111827] rounded-lg border border-[#1E293B] p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
              Equity Curve & Drawdown — VaR Bands
            </h2>
            <span className="text-[10px] text-slate-500 font-mono">{timeframe}</span>
          </div>
          <div className="h-48 rounded-lg bg-[#0A0E17] border border-[#1E293B] flex items-center justify-center">
            {/* Placeholder for Recharts / Lightweight Charts equity curve */}
            <div className="text-center text-slate-500">
              <div className="text-4xl mb-2">📈</div>
              <div className="text-xs font-mono">Equity + DD + VaR bands</div>
              <div className="text-[10px] text-slate-600 mt-1">
                Wire to: /api/v1/risk/equity-curve?tf={timeframe}
              </div>
            </div>
          </div>
        </section>

        {/* ─── ROW 2 LEFT: 12 MINI GAUGES — 4×3 grid (5 cols) ──────── */}
        <section className="col-span-5 bg-[#111827] rounded-lg border border-[#1E293B] p-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3">
            Risk Gauges — Normalized 0–100
          </h2>
          <div className="grid grid-cols-4 gap-2">
            {gauges.slice(0, 12).map((g, i) => (
              <SemiGauge key={i} label={g.label} value={g.value} />
            ))}
          </div>
        </section>

        {/* ─── ROW 2 RIGHT-TOP: KELLY POSITION SIZING (3.5 cols) ────── */}
        <section className="col-span-4 bg-[#111827] rounded-lg border border-[#1E293B] p-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3">
            Kelly Criterion — Position Sizing
          </h2>
          <div className="space-y-2">
            {[
              { label: 'Full Kelly',      value: `${(kelly.full_kelly * 100).toFixed(1)}%`, active: kelly.current_sizing === 'full' },
              { label: 'Half Kelly',      value: `${(kelly.half_kelly * 100).toFixed(1)}%`, active: kelly.current_sizing === 'half' },
              { label: 'Quarter Kelly',   value: `${(kelly.quarter_kelly * 100).toFixed(1)}%`, active: kelly.current_sizing === 'quarter' },
            ].map((k, i) => (
              <div key={i} className={`flex items-center justify-between py-1.5 px-3 rounded text-xs
                ${k.active ? 'bg-cyan-500/10 border border-cyan-500/30' : 'border border-transparent'}`}>
                <span className="text-slate-300">{k.label}</span>
                <span className={`font-mono font-bold ${k.active ? 'text-cyan-400' : 'text-slate-400'}`}>
                  {k.value}
                  {k.active && <span className="ml-2 text-[9px] bg-cyan-500/20 px-1 rounded">ACTIVE</span>}
                </span>
              </div>
            ))}
            <div className="border-t border-[#1E293B] pt-2 mt-2 grid grid-cols-2 gap-2 text-xs">
              <div>
                <div className="text-slate-500">Win Rate</div>
                <div className="font-mono text-green-400">{(kelly.win_rate * 100).toFixed(1)}%</div>
              </div>
              <div>
                <div className="text-slate-500">Edge</div>
                <div className="font-mono text-cyan-400">{(kelly.edge * 100).toFixed(2)}%</div>
              </div>
              <div>
                <div className="text-slate-500">Avg Win</div>
                <div className="font-mono text-green-400">${kelly.avg_win?.toFixed(2) ?? '—'}</div>
              </div>
              <div>
                <div className="text-slate-500">Avg Loss</div>
                <div className="font-mono text-red-400">${kelly.avg_loss?.toFixed(2) ?? '—'}</div>
              </div>
            </div>
            <div className="bg-cyan-500/5 border border-cyan-500/20 rounded px-3 py-2 mt-2">
              <div className="text-[10px] text-slate-500">Recommended Next Trade Size</div>
              <div className="text-lg font-bold font-mono text-cyan-400">
                {(kelly.recommended_pct * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </section>

        {/* ─── ROW 2 RIGHT-BOTTOM: MONTE CARLO STRESS TEST (3 cols) ── */}
        <section className="col-span-3 bg-[#111827] rounded-lg border border-[#1E293B] p-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3">
            Monte Carlo — {monte.simulations?.toLocaleString()} Sims
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
                <span className="text-slate-400">{row.label}</span>
                <span className="font-mono font-bold" style={{ color: row.color }}>{row.value}</span>
              </div>
            ))}
            <div className="border-t border-[#1E293B] pt-2 mt-1">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Ruin Probability</span>
                <span className={`font-mono font-bold text-sm
                  ${monte.ruin_probability < 1 ? 'text-green-400' : monte.ruin_probability < 5 ? 'text-amber-400' : 'text-red-400'}`}>
                  {monte.ruin_probability?.toFixed(2)}%
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* ─── ROW 3 LEFT: CIRCUIT BREAKERS (4 cols) ────────────────── */}
        <section className="col-span-4 bg-[#111827] rounded-lg border border-[#1E293B] p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
              ⚡ Circuit Breakers
            </h2>
            <span className="text-[10px] font-mono text-slate-500">
              {breakers.filter(b => b.tripped).length} TRIPPED
            </span>
          </div>
          <div className="space-y-1">
            <div className="flex items-center text-[9px] text-slate-600 uppercase tracking-wider py-1 px-2">
              <span className="flex-1">Breaker</span>
              <span className="w-16 text-right">Limit</span>
              <span className="w-16 text-right">Current</span>
              <span className="ml-2 w-4"></span>
            </div>
            {breakers.length > 0 ? breakers.map((b, i) => (
              <BreakerRow key={i} name={b.name} threshold={b.threshold} current={b.current} tripped={b.tripped} />
            )) : (
              <div className="text-xs text-slate-600 text-center py-4 font-mono">
                Wire to: /api/v1/risk/circuit-breakers
              </div>
            )}
          </div>
        </section>

        {/* ─── ROW 3 RIGHT: POSITION VAR + TREEMAP (8 cols) ─────────── */}
        <section className="col-span-8 bg-[#111827] rounded-lg border border-[#1E293B] p-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3">
            Position VaR Decomposition
          </h2>
          <div className="grid grid-cols-12 gap-3">
            {/* Table (7 of 8) */}
            <div className="col-span-7 overflow-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-[10px] text-slate-500 uppercase tracking-wider border-b border-[#1E293B]">
                    <th className="py-1.5 px-2 text-left">Symbol</th>
                    <th className="py-1.5 px-2 text-right">Weight</th>
                    <th className="py-1.5 px-2 text-right">VaR 95%</th>
                    <th className="py-1.5 px-2 text-right">VaR 99%</th>
                    <th className="py-1.5 px-2 text-right">Contrib %</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.length > 0 ? positions.map((p, i) => (
                    <VarRow key={i} symbol={p.symbol} weight={p.weight} var95={p.var95}
                            var99={p.var99} contribution={p.contribution} color={p.color} />
                  )) : (
                    <tr>
                      <td colSpan={5} className="text-xs text-slate-600 text-center py-6 font-mono">
                        Wire to: /api/v1/risk/position-var
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {/* Treemap (5 of 8) */}
            <div className="col-span-5">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">
                VaR Contribution Treemap
              </div>
              <div className="flex flex-wrap gap-1 min-h-[120px]">
                {treemapItems.length > 0 ? treemapItems.map((t, i) => (
                  <TreemapBlock key={i} symbol={t.symbol} pct={t.pct} color={t.color} />
                )) : (
                  <div className="w-full h-full flex items-center justify-center text-xs text-slate-600 font-mono">
                    Treemap — populated by API
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* ─── ROW 4: 90-DAY RISK HISTORY TIMELINE (12 cols) ────────── */}
        <section className="col-span-12 bg-[#111827] rounded-lg border border-[#1E293B] p-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3">
            90-Day Risk History
          </h2>
          <div className="h-20 rounded bg-[#0A0E17] border border-[#1E293B] flex items-end px-1 gap-px overflow-hidden">
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
              <div className="w-full h-full flex items-center justify-center text-xs text-slate-600 font-mono">
                Wire to: /api/v1/risk/history — 90 daily risk scores
              </div>
            )}
          </div>
        </section>
      </div>

      {/* ═══ FOOTER ══════════════════════════════════════════════════════ */}
      <footer className="flex items-center justify-between bg-[#111827] rounded-lg px-4 py-2 border border-[#1E293B]
                         text-[10px] text-slate-600 font-mono">
        <span>Elite Trading System — Risk Intelligence v1.0</span>
        <span>Embodier.ai © {new Date().getFullYear()}</span>
        <span>
          Data: Alpaca • UW • FinViz | Refresh: {lastRefresh.toLocaleTimeString()}
        </span>
      </footer>
    </div>
  );
}
