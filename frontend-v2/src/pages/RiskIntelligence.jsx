// =============================================================================
// RiskIntelligence.jsx — Embodier Trader
// Route: /risk | Section: Execution | Page 10
// Rebuilt to match mockup 13-risk-intelligence.png
// =============================================================================
import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { useApi } from "../hooks/useApi";
import { getApiUrl, getAuthHeaders, WS_CHANNELS } from "../config/api";
import ws from "../services/websocket";
import log from "@/utils/logger";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import {
  Shield, RefreshCw, Target, Grid3X3, Gauge, Brain, DollarSign,
  Clock, Octagon, ChevronDown, Radio
} from 'lucide-react';
import { format } from 'date-fns';
import { CorrelationMatrixHeatmap, ParameterSweepsPanel } from '../components/dashboard/RiskWidgets';

// ─── COLOR PALETTE (dark theme) ─────────────────────────────────────────────
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
  teal:      '#14B8A6',
  text:      '#f8fafc',
  muted:     '#64748B',
  dimText:   '#94A3B8',
};

// ─── RISK GRADE HELPER ──────────────────────────────────────────────────────
function gradeFromScore(score) {
  if (score <= 20) return { letter: 'A+', color: C.green };
  if (score <= 35) return { letter: 'A', color: C.green };
  if (score <= 50) return { letter: 'B', color: C.cyan };
  if (score <= 65) return { letter: 'C', color: C.amber };
  if (score <= 80) return { letter: 'D', color: C.red };
  return { letter: 'F', color: C.red };
}

function statusColor(status) {
  if (status === 'SAFE' || status === 'OK' || status === 'PASS') return C.green;
  if (status === 'WARNING' || status === 'CAUTION') return C.amber;
  return C.red;
}

// ─── CORRELATION COLOR ──────────────────────────────────────────────────────
function corrCellBg(val) {
  const v = Math.abs(val ?? 0);
  if (v >= 0.8) return 'rgba(239,68,68,0.35)';
  if (v >= 0.6) return 'rgba(245,158,11,0.30)';
  if (v >= 0.4) return 'rgba(251,191,36,0.25)';
  if (v >= 0.2) return 'rgba(16,185,129,0.25)';
  return 'rgba(20,184,166,0.20)';
}

// ─── SAFETY CHECK ROW ───────────────────────────────────────────────────────
function SafetyCheck({ label, status }) {
  const passed = status === 'PASS' || status === 'OK' || status === 'SAFE';
  return (
    <div className="flex items-center justify-between py-1 border-b border-[rgba(42,52,68,0.5)] last:border-0">
      <span className="text-xs text-slate-300">{label}</span>
      <span className="text-xs font-mono font-bold" style={{ color: passed ? C.green : C.red }}>
        {passed ? '+ PASS' : 'x FAIL'}
      </span>
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
  const cellSize = n > 8 ? 28 : 34;

  return (
    <div className="overflow-auto custom-scrollbar">
      <table className="border-collapse text-[10px] font-mono" style={{ minWidth: n * cellSize + 40 }}>
        <thead>
          <tr>
            <th className="py-1 px-1 text-left text-gray-500 sticky left-0 bg-[#111827] z-10"
                style={{ minWidth: 40 }}></th>
            {symbols.map((s) => (
              <th key={s} className="py-1 px-0.5 text-center font-bold text-[#00D9FF]"
                  style={{ minWidth: cellSize, fontSize: n > 8 ? '8px' : '9px' }}>
                {s}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {symbols.map((rowSym, ri) => (
            <tr key={rowSym}>
              <td className="py-0.5 px-1 font-bold sticky left-0 bg-[#111827] z-10 whitespace-nowrap text-[#00D9FF]"
                  style={{ fontSize: n > 8 ? '8px' : '9px' }}>
                {rowSym}
              </td>
              {matrix[ri]?.map((val, ci) => {
                const isDiag = ri === ci;
                const safeVal = val ?? 0;
                return (
                  <td
                    key={ci}
                    className="text-center font-bold transition-all"
                    style={{
                      color: isDiag ? C.dimText : '#fff',
                      backgroundColor: isDiag ? 'rgba(0,217,255,0.08)' : corrCellBg(safeVal),
                      border: '1px solid rgba(42,52,68,0.3)',
                      fontSize: n > 8 ? '8px' : '9px',
                      padding: '3px 2px',
                      minWidth: cellSize,
                      height: cellSize,
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

// ─── POSITION SIZER VERTICAL BARS ───────────────────────────────────────────
function PositionSizer({ kelly, portfolioValue }) {
  const fullKellyPct = ((kelly?.full_kelly ?? 0) * 100);
  const sizingBars = [
    { label: 'Full', pct: fullKellyPct || 8.2, color: C.red },
    { label: 'Half', pct: (fullKellyPct * 0.5) || 4.1, color: C.amber },
    { label: '1/4', pct: (fullKellyPct * 0.25) || 2.0, color: C.green },
    { label: 'Rec', pct: kelly?.recommended_pct ?? ((fullKellyPct * 0.25) || 2.5), color: C.cyan },
    { label: 'Max', pct: fullKellyPct * 0.75 || 6.1, color: C.purple },
    { label: 'Min', pct: fullKellyPct * 0.1 || 0.8, color: C.teal },
  ];
  const maxPct = Math.max(...sizingBars.map(b => b.pct), 1);

  return (
    <div>
      <div className="flex items-end justify-between gap-1.5" style={{ height: 100 }}>
        {sizingBars.map((bar, i) => {
          const h = Math.max((bar.pct / maxPct) * 100, 5);
          return (
            <div key={i} className="flex-1 flex flex-col items-center gap-1">
              <span className="text-[8px] font-mono font-bold" style={{ color: bar.color }}>
                {bar.pct.toFixed(1)}%
              </span>
              <div className="w-full bg-[#0B0E14] rounded-t relative" style={{ height: 80 }}>
                <div
                  className="absolute bottom-0 left-0 right-0 rounded-t transition-all duration-500"
                  style={{ height: `${h}%`, backgroundColor: bar.color, opacity: 0.85 }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex justify-between gap-1.5 mt-1">
        {sizingBars.map((bar, i) => (
          <div key={i} className="flex-1 text-center">
            <span className="text-[8px] text-gray-500 font-mono">{bar.label}</span>
          </div>
        ))}
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
  const [riskModel, setRiskModel] = useState('Adaptive Multi-Factor');
  const [strategy, setStrategy] = useState('Enhanced MetaResolved TrenchRunner');

  // ─── API HOOKS ────────────────────────────────────────────────────────────
  const { data: riskData, refetch: refetchRisk } = useApi('risk');
  const { data: riskScoreData } = useApi('riskScore');
  const { data: shieldData, refetch: refetchShield } = useApi('riskShield');
  const { data: gaugesData, refetch: refetchGauges } = useApi('risk', { endpoint: '/risk/risk-gauges' });
  const { data: kellyData } = useApi('kellySizer');
  const { data: monteData } = useApi('risk', { endpoint: '/risk/monte-carlo' });
  const { data: historyData } = useApi('risk', { endpoint: '/risk/history' });
  const { data: portfolioData } = useApi('portfolio');
  const { data: correlationData } = useApi('risk', { endpoint: '/risk/correlation-matrix' });
  const handleRefresh = useCallback(() => {
    setLastRefresh(new Date());
    refetchRisk(); refetchShield(); refetchGauges();
  }, [refetchRisk, refetchShield, refetchGauges]);

  // ─── WebSocket live updates ──────────────────────────────────────────────
  useEffect(() => {
    const unsub = ws.on(WS_CHANNELS.risk, () => handleRefresh());
    return unsub;
  }, [handleRefresh]);

  // ─── DERIVED VALUES ───────────────────────────────────────────────────────
  const rawScore = riskScoreData?.score ?? riskData?.risk_score ?? 0;
  const riskScore = (typeof rawScore === 'number' && !Number.isNaN(rawScore)) ? rawScore : Number(rawScore) || 0;
  const grade = gradeFromScore(riskScore);
  const systemStatus = riskData?.system_status ?? 'UNKNOWN';

  // Safety checks from shield
  const safetyChecks = shieldData?.checks ?? [
    { label: 'Max Position Size', status: 'PASS' },
    { label: 'Portfolio Concentration', status: 'PASS' },
    { label: 'Daily Loss Limit', status: 'PASS' },
    { label: 'Drawdown Threshold', status: 'PASS' },
    { label: 'Correlation Check', status: 'PASS' },
    { label: 'Volatility Regime', status: 'PASS' },
    { label: 'Liquidity Check', status: 'PASS' },
    { label: 'Sector Exposure', status: 'PASS' },
    { label: 'Risk Budget', status: 'PASS' },
  ];

  // Risk gauges (raw 0-1 scale for horizontal bars)
  const rawGauges = gaugesData?.gauges ?? [
    { label: 'VaR 95%', value: 15 },
    { label: 'Beta', value: 43 },
    { label: 'CVaR', value: 15 },
    { label: 'Skew Risk', value: 15 },
    { label: 'Correlation', value: 45 },
    { label: 'Volatility', value: 32 },
    { label: 'Tail Risk', value: 18 },
    { label: 'Concentration', value: 22 },
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

  // Risk configuration items
  const configItems = [
    { label: 'Signal Confidence Sentinel', value: riskData?.signal_confidence ?? 'HIGH', color: C.green },
    { label: 'Capital Exposure Watchdog', value: riskData?.capital_exposure ?? 'MODERATE', color: C.amber },
    { label: 'Regime Sentinels', value: riskData?.regime_sentinel ?? 'ACTIVE', color: C.cyan },
    { label: 'Volatility Monitor', value: riskData?.vol_monitor ?? 'ACTIVE', color: C.cyan },
    { label: 'Drawdown Protection', value: riskData?.dd_protection ?? 'ARMED', color: C.green },
    { label: 'Multi-Agent Consensus', value: riskData?.consensus ?? 'ENABLED', color: C.cyan },
    { label: 'Performance Analytics', value: riskData?.perf_analytics ?? 'ONLINE', color: C.green },
    { label: 'Risk Budgets', value: riskData?.risk_budgets ?? 'ACTIVE', color: C.cyan },
  ];

  // Volatility regime data
  const volRegimeItems = [
    { label: 'VIX Level', value: riskData?.vix_current ?? 18.5, max: 80, color: C.amber },
    { label: 'Hist Vol (20d)', value: riskData?.hist_vol_20d ?? 14.2, max: 60, color: C.cyan },
    { label: 'Impl Vol Skew', value: riskData?.iv_skew ?? 3.8, max: 20, color: C.purple },
    { label: 'Vol Regime', value: riskData?.vol_regime_score ?? 35, max: 100, color: C.green },
  ];

  // AI Agent risk monitors (guard against NaN from API)
  const safeNum = (v, fallback = 0) => (typeof v === 'number' && !Number.isNaN(v) ? v : fallback);
  const agentMonitors = [
    { label: 'Monte Carlo P(profit)', value: safeNum(monte.prob_profit, 0), color: C.green },
    { label: 'MC Median Return', value: Math.max(0, safeNum(monte.median_return, 0) + 50), color: C.cyan },
    { label: 'Ruin Probability', value: Math.min(safeNum(monte.ruin_probability, 0) * 10, 100), color: C.red },
    { label: 'Max DD (P95)', value: Math.min(Math.abs(safeNum(monte.max_dd_p95, 0)) * 3, 100), color: C.amber },
    { label: 'Kelly Edge', value: Math.min(safeNum(kelly.edge, 0) * 1000, 100), color: C.purple },
    { label: 'Win Rate', value: safeNum(kelly.win_rate, 0) * 100, color: C.green },
  ];

  // 90-day risk history — show only real API data, no fabricated fallback
  const history = historyData?.history ?? [];
  const historyTableRows = useMemo(() => {
    if (history.length > 0) return history.slice(-20);
    // No real data — return empty array (table shows zero-state)
    return [];
  }, [history]);

  // Portfolio value for sizer
  const portfolioValue = portfolioData?.total_value ?? portfolioData?.portfolio_value ?? riskData?.portfolio_value ?? 0;

  // ─── EMERGENCY ACTIONS ────────────────────────────────────────────────────
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

  // =========================================================================
  // RENDER
  // =========================================================================
  return (
    <div className="flex flex-col min-h-0" style={{ backgroundColor: C.bg, color: C.text }}>

      {/* ════════════════════════════════════════════════════════════════════════
          HEADER BAR (mockup 13-risk-intelligence: aligns with system header style)
          ════════════════════════════════════════════════════════════════════════ */}
      <header className="px-5 py-3 flex items-center justify-between border-b border-[rgba(42,52,68,0.5)] shrink-0 bg-[#111827]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg flex items-center justify-center"
               style={{ backgroundColor: grade.color + '20' }}>
            <Shield className="w-5 h-5" style={{ color: grade.color }} />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              Risk Intelligence
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
        </div>

        {/* Right: timeframe + refresh */}
        <div className="flex items-center gap-3">
          <div className="flex rounded-lg overflow-hidden border border-[rgba(42,52,68,0.5)]">
            {['1D', '1W', '1M', '3M'].map(tf => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-3 py-1.5 text-xs font-mono font-bold transition-all
                  ${timeframe === tf
                    ? 'bg-cyan-500/20 text-[#00D9FF]'
                    : 'bg-[#1A1F2E] text-gray-500 hover:text-slate-300'}`}
              >
                {tf}
              </button>
            ))}
          </div>
          <button
            onClick={handleRefresh}
            className="p-2 rounded-lg bg-white/5 border border-[rgba(42,52,68,0.5)]
                       hover:border-[#00D9FF]/50 text-gray-500 hover:text-[#00D9FF] transition-all"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <span className="text-[10px] text-gray-500 font-mono">
            {lastRefresh.toLocaleTimeString()}
          </span>
        </div>
      </header>

      {/* ════════════════════════════════════════════════════════════════════════
          MAIN CONTENT
          ════════════════════════════════════════════════════════════════════════ */}
      <div className="p-3 space-y-3">
      {/* TOP SECTION ROW: Risk Configuration | Parameter Sweeps | Realtime Risk Detail */}
      <div className="grid grid-cols-12 gap-3">

        {/* --- Risk Configuration (left, 4 cols) --- */}
        <Card title="Risk Configuration"
              subtitle={`Strategy: ${strategy}`}
              className="col-span-4"
              action={<Badge variant="success" size="sm">ACTIVE</Badge>}>
          <div className="space-y-3">
            {/* Risk Model Selector */}
            <div>
              <label className="text-[10px] text-gray-500 uppercase tracking-wider block mb-1">Risk Model</label>
              <div className="relative">
                <select
                  value={riskModel}
                  onChange={(e) => setRiskModel(e.target.value)}
                  className="w-full bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] rounded-lg px-3 py-1.5 text-xs text-white
                             font-mono appearance-none cursor-pointer hover:border-[#00D9FF]/50 transition-all"
                >
                  <option>Adaptive Multi-Factor</option>
                  <option>Momentum Risk</option>
                  <option>Mean Reversion</option>
                  <option>Volatility Regime</option>
                </select>
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500 pointer-events-none" />
              </div>
            </div>
            {/* Strategy Selector */}
            <div>
              <label className="text-[10px] text-gray-500 uppercase tracking-wider block mb-1">Strategy</label>
              <div className="relative">
                <select
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value)}
                  className="w-full bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] rounded-lg px-3 py-1.5 text-xs text-white
                             font-mono appearance-none cursor-pointer hover:border-[#00D9FF]/50 transition-all"
                >
                  <option>Enhanced MetaResolved TrenchRunner</option>
                  <option>Momentum Alpha</option>
                  <option>Multi-Agent Consensus</option>
                  <option>Hybrid Adaptive</option>
                </select>
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500 pointer-events-none" />
              </div>
            </div>
            {/* Config toggles */}
            <div className="space-y-1 pt-1">
              {configItems.map((item, i) => (
                <div key={i} className="flex items-center justify-between py-1 border-b border-[rgba(42,52,68,0.5)]/60 last:border-0">
                  <span className="text-xs text-gray-400">{item.label}</span>
                  <span className="text-xs font-mono font-bold" style={{ color: item.color }}>{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>

        {/* --- Parameter Sweeps (center, 5 cols) --- */}
        <Card title="Parameter Sweeps" className="col-span-5"
              action={<span className="text-[10px] text-gray-500 font-mono">{timeframe}</span>}>
          <ParameterSweepsPanel
            onRun={(values) => console.log('Sweep started:', values)}
            onStop={() => console.log('Sweep stopped')}
          />
          {/* Sweep parameter grid - numerical columns */}
          <div className="overflow-auto custom-scrollbar">
            <table className="w-full text-[10px] font-mono border-collapse">
              <thead>
                <tr className="text-[9px] text-gray-500 uppercase tracking-wider">
                  <th className="py-1 px-1.5 text-left text-gray-500">Param</th>
                  {[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8].map((v) => (
                    <th key={v} className="py-1 px-1 text-center text-[#00D9FF]/70">{v.toFixed(1)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  { param: 'SL Mult', vals: [0.82, 0.79, 0.85, 0.91, 0.88, 0.76, 0.72, 0.68] },
                  { param: 'TP Ratio', vals: [1.21, 1.35, 1.48, 1.52, 1.61, 1.44, 1.38, 1.29] },
                  { param: 'Trail %', vals: [0.45, 0.52, 0.61, 0.58, 0.55, 0.49, 0.43, 0.38] },
                  { param: 'Conf Thr', vals: [0.65, 0.71, 0.78, 0.82, 0.85, 0.79, 0.74, 0.69] },
                  { param: 'Vol Adj', vals: [0.33, 0.41, 0.48, 0.55, 0.52, 0.46, 0.39, 0.35] },
                  { param: 'Size Fac', vals: [0.18, 0.24, 0.31, 0.28, 0.35, 0.29, 0.22, 0.19] },
                ].map((row, ri) => (
                  <tr key={ri} className="border-t border-[rgba(42,52,68,0.5)]/40 hover:bg-[rgba(0,217,255,0.03)]">
                    <td className="py-1 px-1.5 text-gray-400 whitespace-nowrap">{row.param}</td>
                    {row.vals.map((v, ci) => {
                      const intensity = v;
                      const cellColor = intensity > 0.7 ? C.green : intensity > 0.4 ? C.cyan : C.muted;
                      return (
                        <td key={ci} className="py-1 px-1 text-center font-bold"
                            style={{ color: cellColor }}>
                          {v.toFixed(2)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* --- RealTime Risk Vitals (right, 3 cols) --- */}
        <Card title="RealTime Risk Vitals" className="col-span-3"
              action={<Badge variant={systemStatus === 'SAFE' ? 'success' : 'warning'} size="sm">{systemStatus}</Badge>}>
          <div className="space-y-2.5">
            {[
              { label: 'Portfolio VaR (95%)', value: rawGauges.find(g => g.label === 'VaR 95%')?.value ?? 0, color: C.amber },
              { label: 'Tail Risk (CVaR)', value: rawGauges.find(g => g.label === 'CVaR')?.value ?? 0, color: C.red },
              { label: 'Volatility Level', value: rawGauges.find(g => g.label === 'Volatility')?.value ?? 0, color: C.purple },
              { label: 'Beta Exposure', value: rawGauges.find(g => g.label === 'Beta')?.value ?? 0, color: C.cyan },
              { label: 'Concentration', value: rawGauges.find(g => g.label === 'Concentration')?.value ?? 0, color: C.amber },
              { label: 'Liquidity Score', value: rawGauges.find(g => g.label === 'Liquidity')?.value ?? 0, color: C.green },
              { label: 'Skew Risk', value: rawGauges.find(g => g.label === 'Skew Risk')?.value ?? 0, color: C.red },
              { label: 'Regime Risk', value: rawGauges.find(g => g.label === 'Regime Risk')?.value ?? 0, color: C.amber },
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

      {/* ════════════════════════════════════════════════════════════════════════
          MAIN GRID ROW: Stop-Loss | Correlation | Vol Regime | AI Monitors | Position Sizing
          ════════════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-12 gap-3">

        {/* --- Stop-Loss Command (2 cols) --- */}
        <Card title="Stop-Loss Command" className="col-span-2"
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
          <div className="border-t border-[rgba(42,52,68,0.5)] pt-3 space-y-2">
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
                           border border-[#00D9FF]/50 transition-all"
              >
                Freeze
              </button>
            </div>
          </div>
        </Card>

        {/* --- Correlation Matrix (3 cols) --- */}
        <Card title="Correlation Matrix" className="col-span-3"
              action={<Grid3X3 className="w-4 h-4 text-[#00D9FF]" />}>
          <CorrelationHeatmap data={correlationData} />
          <CorrelationMatrixHeatmap />
        </Card>

        {/* --- Volatility Regime Monitor (2 cols) --- */}
        <Card title="Volatility Regime Monitor" className="col-span-2"
              action={<Gauge className="w-4 h-4 text-[#00D9FF]" />}>
          <div className="space-y-2.5">
            {volRegimeItems.map((item, i) => (
              <div key={i}>
                <div className="flex items-center justify-between text-[10px] mb-0.5">
                  <span className="text-gray-400">{item.label}</span>
                  <span className="font-mono font-bold" style={{ color: item.color }}>
                    {typeof item.value === 'number' ? item.value.toFixed(1) : item.value}
                  </span>
                </div>
                <div className="w-full h-2.5 bg-[#0B0E14] rounded overflow-hidden">
                  <div className="h-full rounded transition-all duration-500"
                       style={{
                         width: `${Math.min((typeof item.value === 'number' ? item.value / item.max : 0) * 100, 100)}%`,
                         backgroundColor: item.color + 'B0',
                       }} />
                </div>
              </div>
            ))}
            {/* Regime indicator */}
            <div className="mt-2 p-2 bg-[#0B0E14] border border-[rgba(42,52,68,0.5)]/50 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-gray-500">Current Regime</span>
                <span className="text-[10px] font-mono font-bold" style={{ color: C.green }}>
                  {riskData?.volatility_regime ?? 'LOW VOL'}
                </span>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-[10px] text-gray-500">Regime Confidence</span>
                <span className="text-[10px] font-mono font-bold" style={{ color: C.cyan }}>
                  {riskData?.regime_confidence ?? '82%'}
                </span>
              </div>
            </div>
          </div>
        </Card>

        {/* --- AI Agent Risk Monitors (3 cols) --- */}
        <Card title="AI Agent Risk Monitors" className="col-span-3"
              action={<Brain className="w-4 h-4 text-[#00D9FF]" />}>
          <div className="space-y-2">
            {agentMonitors.map((item, i) => (
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
              action={<DollarSign className="w-4 h-4 text-[#00D9FF]" />}>
          <PositionSizer kelly={kelly} portfolioValue={portfolioValue} />
        </Card>
      </div>

      {/* ════════════════════════════════════════════════════════════════════════
          ROW 3: Risk Interdependencies
          ════════════════════════════════════════════════════════════════════════ */}
      <Card title="Risk Interdependencies"
            subtitle="Cross-factor dependency analysis"
            action={<Target className="w-4 h-4 text-[#00D9FF]" />}>
        <div className="overflow-auto custom-scrollbar">
          <table className="w-full text-[10px] font-mono border-collapse">
            <thead>
              <tr className="text-[9px] text-gray-500 uppercase tracking-wider border-b border-[rgba(42,52,68,0.5)]">
                <th className="py-1.5 px-2 text-left">Risk Factor</th>
                <th className="py-1.5 px-2 text-center">Volatility</th>
                <th className="py-1.5 px-2 text-center">Correlation</th>
                <th className="py-1.5 px-2 text-center">Liquidity</th>
                <th className="py-1.5 px-2 text-center">Drawdown</th>
                <th className="py-1.5 px-2 text-center">Concentration</th>
                <th className="py-1.5 px-2 text-center">Tail Risk</th>
                <th className="py-1.5 px-2 text-center">Regime</th>
                <th className="py-1.5 px-2 text-right">Impact</th>
                <th className="py-1.5 px-2 text-left" style={{ width: '18%' }}>Dependency</th>
              </tr>
            </thead>
            <tbody>
              {[
                { factor: 'Market Beta', scores: [0.72, 0.85, 0.41, 0.68, 0.55, 0.33, 0.78], impact: 'HIGH' },
                { factor: 'Sector Tilt', scores: [0.45, 0.62, 0.38, 0.51, 0.71, 0.28, 0.42], impact: 'MED' },
                { factor: 'FX Exposure', scores: [0.58, 0.31, 0.67, 0.44, 0.29, 0.52, 0.61], impact: 'MED' },
                { factor: 'Rate Sens.', scores: [0.81, 0.55, 0.49, 0.73, 0.38, 0.65, 0.82], impact: 'HIGH' },
                { factor: 'Momentum', scores: [0.39, 0.48, 0.55, 0.35, 0.62, 0.41, 0.37], impact: 'LOW' },
                { factor: 'Leverage', scores: [0.65, 0.72, 0.58, 0.82, 0.69, 0.75, 0.71], impact: 'HIGH' },
                { factor: 'Liquidity', scores: [0.42, 0.35, 0.88, 0.55, 0.31, 0.48, 0.52], impact: 'MED' },
              ].map((row, ri) => {
                const impColor = row.impact === 'HIGH' ? C.red : row.impact === 'MED' ? C.amber : C.green;
                const avgScore = row.scores.reduce((a, b) => a + b, 0) / row.scores.length;
                return (
                  <tr key={ri} className="border-b border-[rgba(42,52,68,0.3)] hover:bg-[rgba(42,52,68,0.15)] transition-colors">
                    <td className="py-1.5 px-2 font-bold text-[#00D9FF] whitespace-nowrap">{row.factor}</td>
                    {row.scores.map((s, ci) => (
                      <td key={ci} className="py-1.5 px-2 text-center font-bold"
                          style={{ color: s > 0.7 ? C.red : s > 0.4 ? C.amber : C.green }}>
                        {s.toFixed(2)}
                      </td>
                    ))}
                    <td className="py-1.5 px-2 text-right">
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[8px] font-bold"
                            style={{ backgroundColor: impColor + '20', color: impColor }}>
                        {row.impact}
                      </span>
                    </td>
                    <td className="py-1.5 px-2">
                      <div className="w-full h-2.5 bg-[#0B0E14] rounded overflow-hidden">
                        <div className="h-full rounded transition-all"
                             style={{ width: `${avgScore * 100}%`, backgroundColor: impColor + 'A0' }} />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {/* ════════════════════════════════════════════════════════════════════════
          ROW 4: Risk Event Timeline
          ════════════════════════════════════════════════════════════════════════ */}
      <Card title="Risk Event Timeline"
            subtitle="Horizontal risk exposure over time"
            action={<Clock className="w-4 h-4 text-[#00D9FF]" />}>
        <div className="overflow-auto custom-scrollbar">
          {(() => {
            const timelineDays = Array.from({ length: 20 }, (_, i) => {
              const d = new Date();
              d.setDate(d.getDate() - (19 - i));
              return format(d, 'MM/dd');
            });
            const timelineRows = [
              { label: 'Market Risk', color: C.red, segments: [1,1,2,2,1,0,0,1,2,2,3,3,2,1,1,0,1,2,2,1] },
              { label: 'Credit Risk', color: C.amber, segments: [0,1,1,1,2,2,1,1,0,0,1,1,2,2,1,1,0,0,1,1] },
              { label: 'Liquidity', color: C.cyan, segments: [1,0,0,1,1,1,2,2,1,0,0,0,1,1,2,2,1,1,0,0] },
              { label: 'Volatility', color: C.purple, segments: [2,2,1,1,0,1,1,2,3,3,2,2,1,0,0,1,1,2,2,1] },
              { label: 'Concentration', color: C.teal, segments: [0,0,1,1,1,1,0,0,1,1,2,1,1,0,0,0,1,1,1,0] },
              { label: 'Tail Risk', color: C.red, segments: [0,0,0,1,1,2,2,1,0,0,0,1,1,2,3,2,1,1,0,0] },
            ];
            return (
              <div>
                {/* Date header */}
                <div className="flex items-center mb-1">
                  <div className="w-24 shrink-0" />
                  <div className="flex-1 flex">
                    {timelineDays.map((d, i) => (
                      <div key={i} className="flex-1 text-center text-[7px] text-gray-500 font-mono">{i % 3 === 0 ? d : ''}</div>
                    ))}
                  </div>
                </div>
                {/* Timeline rows */}
                {timelineRows.map((row, ri) => (
                  <div key={ri} className="flex items-center mb-0.5">
                    <div className="w-24 shrink-0 text-[9px] text-gray-400 font-mono truncate pr-2 text-right">{row.label}</div>
                    <div className="flex-1 flex gap-px h-4">
                      {row.segments.map((level, si) => {
                        const opacity = level === 0 ? 0.08 : level === 1 ? 0.3 : level === 2 ? 0.6 : 0.9;
                        return (
                          <div key={si} className="flex-1 rounded-sm transition-all"
                               style={{ backgroundColor: row.color, opacity }}
                               title={`${row.label} ${timelineDays[si]}: Level ${level}`} />
                        );
                      })}
                    </div>
                  </div>
                ))}
                {/* Legend */}
                <div className="flex items-center gap-4 mt-2 justify-end">
                  {['None', 'Low', 'Medium', 'High'].map((lbl, i) => (
                    <div key={i} className="flex items-center gap-1">
                      <div className="w-3 h-2.5 rounded-sm" style={{ backgroundColor: C.cyan, opacity: i === 0 ? 0.08 : i === 1 ? 0.3 : i === 2 ? 0.6 : 0.9 }} />
                      <span className="text-[8px] text-gray-500">{lbl}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}
        </div>
      </Card>

      {/* ════════════════════════════════════════════════════════════════════════
          BOTTOM: 90-Day Risk History (data table)
          ════════════════════════════════════════════════════════════════════════ */}
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
        <div className="overflow-auto custom-scrollbar">
          <table className="w-full text-[10px] font-mono border-collapse">
            <thead>
              <tr className="text-[9px] text-gray-500 uppercase tracking-wider border-b border-[rgba(42,52,68,0.5)]">
                <th className="py-1.5 px-2 text-left">Date</th>
                <th className="py-1.5 px-2 text-right">Score</th>
                <th className="py-1.5 px-2 text-right">VaR</th>
                <th className="py-1.5 px-2 text-right">DD%</th>
                <th className="py-1.5 px-2 text-right">Vol</th>
                <th className="py-1.5 px-2 text-right">Beta</th>
                <th className="py-1.5 px-2 text-right">Sharpe</th>
                <th className="py-1.5 px-2 text-center">Regime</th>
                <th className="py-1.5 px-2 text-center">Status</th>
                <th className="py-1.5 px-2 text-left" style={{ width: '15%' }}>Risk Bar</th>
              </tr>
            </thead>
            <tbody>
              {historyTableRows.map((row, ri) => {
                const score = row.score ?? 0;
                const scoreColor = score <= 35 ? C.green : score <= 65 ? C.amber : C.red;
                const st = row.status ?? (score <= 35 ? 'SAFE' : score <= 65 ? 'CAUTION' : 'DANGER');
                const stColor = st === 'SAFE' ? C.green : st === 'CAUTION' ? C.amber : C.red;
                return (
                  <tr key={ri} className="border-b border-[rgba(42,52,68,0.25)] hover:bg-[rgba(42,52,68,0.12)] transition-colors">
                    <td className="py-1 px-2 text-gray-400">{row.date}</td>
                    <td className="py-1 px-2 text-right font-bold" style={{ color: scoreColor }}>{score}</td>
                    <td className="py-1 px-2 text-right text-slate-300">{row.var95 ?? '--'}</td>
                    <td className="py-1 px-2 text-right text-slate-300">{row.drawdown ?? row.dd ?? '--'}%</td>
                    <td className="py-1 px-2 text-right text-slate-300">{row.vol ?? '--'}</td>
                    <td className="py-1 px-2 text-right text-slate-300">{row.beta ?? '--'}</td>
                    <td className="py-1 px-2 text-right text-slate-300">{row.sharpe ?? '--'}</td>
                    <td className="py-1 px-2 text-center">
                      <span className="text-[8px]" style={{ color: C.cyan }}>{row.regime ?? '--'}</span>
                    </td>
                    <td className="py-1 px-2 text-center">
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[8px] font-bold"
                            style={{ backgroundColor: stColor + '18', color: stColor }}>
                        <span className="w-1 h-1 rounded-full" style={{ backgroundColor: stColor }} />
                        {st}
                      </span>
                    </td>
                    <td className="py-1 px-2">
                      <div className="w-full h-2 bg-[#0B0E14] rounded overflow-hidden">
                        <div className="h-full rounded transition-all"
                             style={{ width: `${Math.min(score, 100)}%`, backgroundColor: scoreColor + 'B0' }} />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      </div>

      {/* ════════════════════════════════════════════════════════════════════════
          FOOTER (mockup: aligns with system footer style)
          ════════════════════════════════════════════════════════════════════════ */}
      <footer className="mt-3 px-4 py-2 border border-[rgba(42,52,68,0.5)] rounded-lg flex items-center justify-between
                         text-[10px] text-[#94a3b8] font-mono bg-[#111827]">
        <span className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <Radio className="w-3 h-3 text-[#00D9FF]" />
          Embodier Trader -- Risk Intelligence v2.0
        </span>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: C.green }} />
            Shields: ACTIVE
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: C.cyan }} />
            Risk Engine: ONLINE
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: C.green }} />
            Monte Carlo: READY
          </span>
        </div>
        <span className="text-[#94a3b8]">
          Embodier Trader - Risk Intelligence v2.0 | Refresh: {lastRefresh.toLocaleTimeString()}
        </span>
      </footer>
    </div>
  );
}
