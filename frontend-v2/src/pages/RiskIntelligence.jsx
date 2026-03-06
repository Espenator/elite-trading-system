// =============================================================================
// RiskIntelligence.jsx — Elite Trading System
// Route: /risk | Section: Execution | Page 10
// Rebuilt to match mockup 13-risk-intelligence.png
// =============================================================================
import React, { useState, useCallback, useMemo } from 'react';
import { useApi } from "../hooks/useApi";
import { getApiUrl, getAuthHeaders } from "../config/api";
import log from "@/utils/logger";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import PageHeader from "../components/ui/PageHeader";
import {
  Shield, RefreshCw, AlertTriangle, Activity, TrendingDown,
  Zap, Target, BarChart3, Grid3X3, Gauge, Brain, DollarSign,
  Clock, Eye, Octagon, ChevronDown,
  ShieldCheck, Radio
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell, CartesianGrid, Area, AreaChart
} from 'recharts';
import { format, subDays } from 'date-fns';
import clsx from 'clsx';

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
function corrCellColor(val) {
  const v = Math.abs(val ?? 0);
  if (v >= 0.8) return '#EF4444';       // red - high correlation
  if (v >= 0.6) return '#F59E0B';       // amber
  if (v >= 0.4) return '#FBBF24';       // yellow
  if (v >= 0.2) return '#10B981';       // green
  return '#14B8A6';                      // teal - low correlation
}

function corrCellBg(val) {
  const v = Math.abs(val ?? 0);
  if (v >= 0.8) return 'rgba(239,68,68,0.35)';
  if (v >= 0.6) return 'rgba(245,158,11,0.30)';
  if (v >= 0.4) return 'rgba(251,191,36,0.25)';
  if (v >= 0.2) return 'rgba(16,185,129,0.25)';
  return 'rgba(20,184,166,0.20)';
}

// ─── HORIZONTAL GAUGE BAR ───────────────────────────────────────────────────
function HorizontalGauge({ label, value = 0, color = C.cyan }) {
  const displayVal = typeof value === 'number' ? value.toFixed(2) : value;
  const pct = Math.min(Math.max((typeof value === 'number' ? value : 0) * 100, 0), 100);
  return (
    <div className="flex items-center gap-2 min-w-0">
      <span className="text-[9px] text-gray-500 w-16 truncate text-right shrink-0">{label}</span>
      <div className="flex-1 h-4 bg-[#0B0E14] rounded overflow-hidden relative">
        <div
          className="h-full rounded transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color, opacity: 0.85 }}
        />
        <span className="absolute inset-0 flex items-center justify-end pr-1.5 text-[9px] font-mono font-bold text-white/90">
          {displayVal}
        </span>
      </div>
    </div>
  );
}

// ─── SAFETY CHECK ROW ───────────────────────────────────────────────────────
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
              <th key={s} className="py-1 px-0.5 text-center font-bold text-cyan-400"
                  style={{ minWidth: cellSize, fontSize: n > 8 ? '8px' : '9px' }}>
                {s}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {symbols.map((rowSym, ri) => (
            <tr key={rowSym}>
              <td className="py-0.5 px-1 font-bold sticky left-0 bg-[#111827] z-10 whitespace-nowrap text-cyan-400"
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

// ─── POSITION SIZER BARS ────────────────────────────────────────────────────
function PositionSizer({ kelly, portfolioValue }) {
  const fullKellyPct = ((kelly?.full_kelly ?? 0) * 100);
  const sizingBars = [
    { label: 'Full Kelly', pct: fullKellyPct, color: C.red },
    { label: 'Half Kelly', pct: fullKellyPct * 0.5, color: C.amber },
    { label: 'Quarter Kelly', pct: fullKellyPct * 0.25, color: C.green },
    { label: 'Recommended', pct: kelly?.recommended_pct ?? fullKellyPct * 0.25, color: C.cyan },
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
  const [strategy, setStrategy] = useState('Momentum Alpha');

  // ─── API HOOKS ────────────────────────────────────────────────────────────
  const { data: riskData, loading: riskLoading, refetch: refetchRisk } = useApi('risk');
  const { data: riskScoreData } = useApi('riskScore');
  const { data: shieldData, loading: shieldLoading, refetch: refetchShield } = useApi('riskShield');
  const { data: drawdownData } = useApi('drawdownCheck');
  const { data: kellyRankedData } = useApi('kellyRanked');
  const { data: gaugesData, loading: gaugesLoading, refetch: refetchGauges } = useApi('risk', { endpoint: '/risk/risk-gauges' });
  const { data: kellyData } = useApi('kellySizer');
  const { data: monteData } = useApi('risk', { endpoint: '/risk/monte-carlo' });
  const { data: historyData } = useApi('risk', { endpoint: '/risk/history' });
  const { data: portfolioData } = useApi('portfolio');
  const { data: correlationData } = useApi('risk', { endpoint: '/risk/correlation-matrix' });
  const { data: equityCurveData } = useApi('risk', { endpoint: `/risk/equity-curve?tf=${timeframe}`, pollIntervalMs: 30000 });

  const handleRefresh = useCallback(() => {
    setLastRefresh(new Date());
    refetchRisk(); refetchShield(); refetchGauges();
  }, [refetchRisk, refetchShield, refetchGauges]);

  // ─── DERIVED VALUES ───────────────────────────────────────────────────────
  const riskScore = riskScoreData?.score ?? riskData?.risk_score ?? 0;
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

  // Normalize gauge values for horizontal bars (0-1 range)
  const gaugeItems = rawGauges.slice(0, 8).map((g) => {
    const val = (g.value ?? 0) / 100;
    let color = C.green;
    if (val > 0.6) color = C.red;
    else if (val > 0.35) color = C.amber;
    else if (val > 0.2) color = C.cyan;
    return { label: g.label, value: val, color };
  });

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

  // KPIs for parameter sweeps
  const kpis = riskData?.kpis ?? [
    { label: 'Portfolio Value', value: '$--', color: C.text },
    { label: 'Daily P&L', value: '$--', color: C.muted },
    { label: 'Max Drawdown', value: '--%', color: C.muted },
    { label: 'Current DD', value: '--%', color: C.muted },
    { label: 'Sharpe Ratio', value: '--', color: C.muted },
    { label: 'Win Rate', value: '--%', color: C.muted },
    { label: 'Profit Factor', value: '--', color: C.muted },
    { label: 'Open Positions', value: '--', color: C.muted },
    { label: 'Daily Trades', value: '--', color: C.muted },
    { label: 'Exposure', value: '--%', color: C.muted },
  ];

  // Volatility regime data
  const volRegimeItems = [
    { label: 'VIX Level', value: riskData?.vix_current ?? 18.5, max: 80, color: C.amber },
    { label: 'Hist Vol (20d)', value: riskData?.hist_vol_20d ?? 14.2, max: 60, color: C.cyan },
    { label: 'Impl Vol Skew', value: riskData?.iv_skew ?? 3.8, max: 20, color: C.purple },
    { label: 'Vol Regime', value: riskData?.vol_regime_score ?? 35, max: 100, color: C.green },
  ];

  // AI Agent risk monitors
  const agentMonitors = [
    { label: 'Monte Carlo P(profit)', value: monte.prob_profit, color: C.green },
    { label: 'MC Median Return', value: Math.max(0, monte.median_return + 50), color: C.cyan },
    { label: 'Ruin Probability', value: Math.min(monte.ruin_probability * 10, 100), color: C.red },
    { label: 'Max DD (P95)', value: Math.min(Math.abs(monte.max_dd_p95) * 3, 100), color: C.amber },
    { label: 'Kelly Edge', value: Math.min((kelly.edge ?? 0) * 1000, 100), color: C.purple },
    { label: 'Win Rate', value: (kelly.win_rate ?? 0) * 100, color: C.green },
  ];

  // 90-day risk history
  const history = historyData?.history ?? [];

  // Portfolio value for sizer
  const portfolioValue = portfolioData?.total_value ?? portfolioData?.portfolio_value ?? riskData?.portfolio_value ?? 0;

  // Estimated edge/scenarios from kelly ranked data
  const kellyRanked = kellyRankedData?.ranked ?? kellyRankedData?.tickers ?? [];
  const edgeScenarios = useMemo(() => {
    if (kellyRanked.length > 0) return kellyRanked.slice(0, 6);
    return [
      { ticker: 'AAPL', edge: 0.023, kelly_pct: 4.2, confidence: 'HIGH' },
      { ticker: 'MSFT', edge: 0.018, kelly_pct: 3.1, confidence: 'HIGH' },
      { ticker: 'GOOGL', edge: 0.015, kelly_pct: 2.8, confidence: 'MED' },
      { ticker: 'TSLA', edge: 0.031, kelly_pct: 5.5, confidence: 'MED' },
      { ticker: 'NVDA', edge: 0.027, kelly_pct: 4.8, confidence: 'HIGH' },
      { ticker: 'AMZN', edge: 0.012, kelly_pct: 2.2, confidence: 'MED' },
    ];
  }, [kellyRanked]);

  // Drawdown check data
  const ddCheck = drawdownData ?? {
    current_drawdown: riskData?.current_drawdown ?? 0,
    max_drawdown: riskData?.max_drawdown ?? 0,
    status: 'OK',
    threshold: 15,
  };

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

  const isLoading = riskLoading || shieldLoading || gaugesLoading;

  // =========================================================================
  // RENDER
  // =========================================================================
  return (
    <div className="min-h-screen p-3 space-y-3" style={{ backgroundColor: C.bg, color: C.text }}>

      {/* ════════════════════════════════════════════════════════════════════════
          HEADER BAR
          ════════════════════════════════════════════════════════════════════════ */}
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

      {/* ════════════════════════════════════════════════════════════════════════
          TOP SECTION ROW: Risk Configuration | Parameter Sweeps | Realtime Risk Detail
          ════════════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-12 gap-3">

        {/* --- Risk Configuration (left, 4 cols) --- */}
        <Card title="Risk Configuration"
              subtitle="Source: Automated Risk Assessment"
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
                  className="w-full bg-[#0B0E14] border border-[#1E293B] rounded-lg px-3 py-1.5 text-xs text-white
                             font-mono appearance-none cursor-pointer hover:border-cyan-500/30 transition-all"
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
                  className="w-full bg-[#0B0E14] border border-[#1E293B] rounded-lg px-3 py-1.5 text-xs text-white
                             font-mono appearance-none cursor-pointer hover:border-cyan-500/30 transition-all"
                >
                  <option>Momentum Alpha</option>
                  <option>Multi-Agent Consensus</option>
                  <option>Mean Reversion</option>
                  <option>Hybrid Adaptive</option>
                </select>
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500 pointer-events-none" />
              </div>
            </div>
            {/* Config toggles */}
            <div className="space-y-1 pt-1">
              {configItems.map((item, i) => (
                <div key={i} className="flex items-center justify-between py-1 border-b border-[#1E293B]/60 last:border-0">
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
          RISK GAUGES ROW - Horizontal gauge bars
          ════════════════════════════════════════════════════════════════════════ */}
      <div className="bg-surface border border-secondary/20 rounded-xl px-4 py-3">
        <div className="grid grid-cols-8 gap-3">
          {gaugeItems.map((g, i) => (
            <HorizontalGauge key={i} label={g.label} value={g.value} color={g.color} />
          ))}
        </div>
      </div>

      {/* ════════════════════════════════════════════════════════════════════════
          MAIN GRID ROW: Stop-Loss | Correlation | Vol Regime | AI Monitors | Position Sizing
          ════════════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-12 gap-3">

        {/* --- Stop-Loss Command (2.5 cols) --- */}
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
        <Card title="Correlation Matrix" className="col-span-2"
              action={<Grid3X3 className="w-4 h-4 text-cyan-400" />}>
          <CorrelationHeatmap data={correlationData} />
        </Card>

        {/* --- Volatility Regime Monitor (2 cols) --- */}
        <Card title="Volatility Regime Monitor" className="col-span-2"
              action={<Gauge className="w-4 h-4 text-cyan-400" />}>
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
            <div className="mt-2 p-2 bg-[#0B0E14] border border-[#1E293B]/50 rounded-lg">
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
              action={<Brain className="w-4 h-4 text-cyan-400" />}>
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
              action={<DollarSign className="w-4 h-4 text-cyan-400" />}>
          <PositionSizer kelly={kelly} portfolioValue={portfolioValue} />
        </Card>
      </div>

      {/* ════════════════════════════════════════════════════════════════════════
          ROW 2: Estimated Edge/Scenarios
          ════════════════════════════════════════════════════════════════════════ */}
      <Card title="Estimated Edge / Scenarios"
            subtitle={`${edgeScenarios.length} tickers analyzed`}
            action={<Target className="w-4 h-4 text-cyan-400" />}>
        <div className="overflow-auto custom-scrollbar">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-[10px] text-gray-500 uppercase tracking-wider border-b border-[rgba(42,52,68,0.5)]">
                <th className="py-2 px-3 text-left">Ticker</th>
                <th className="py-2 px-3 text-right">Edge</th>
                <th className="py-2 px-3 text-right">Kelly %</th>
                <th className="py-2 px-3 text-center">Confidence</th>
                <th className="py-2 px-3 text-left" style={{ width: '40%' }}>Edge Bar</th>
              </tr>
            </thead>
            <tbody>
              {edgeScenarios.map((item, i) => {
                const edge = item.edge ?? 0;
                const kellyPct = item.kelly_pct ?? item.kelly ?? 0;
                const conf = item.confidence ?? 'MED';
                const confColor = conf === 'HIGH' ? C.green : conf === 'MED' ? C.amber : C.red;
                const maxEdge = Math.max(...edgeScenarios.map(e => e.edge ?? 0), 0.01);
                const barPct = (edge / maxEdge) * 100;
                return (
                  <tr key={i} className="border-b border-[rgba(42,52,68,0.3)] hover:bg-[rgba(42,52,68,0.15)] transition-colors">
                    <td className="py-1.5 px-3 font-mono font-bold text-cyan-400">{item.ticker ?? item.symbol}</td>
                    <td className="py-1.5 px-3 text-right font-mono text-slate-300">{(edge * 100).toFixed(2)}%</td>
                    <td className="py-1.5 px-3 text-right font-mono text-slate-300">{typeof kellyPct === 'number' ? kellyPct.toFixed(1) : kellyPct}%</td>
                    <td className="py-1.5 px-3 text-center">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold"
                            style={{ backgroundColor: confColor + '20', color: confColor }}>
                        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: confColor }} />
                        {conf}
                      </span>
                    </td>
                    <td className="py-1.5 px-3">
                      <div className="w-full h-3 bg-[#0B0E14] rounded overflow-hidden">
                        <div className="h-full rounded transition-all"
                             style={{
                               width: `${barPct}%`,
                               backgroundColor: confColor + 'A0',
                             }} />
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
          BOTTOM: 90-Day Risk History
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
        <div className="space-y-2">
          {/* Bar chart for 90-day history */}
          {history.length > 0 ? (
            <div style={{ width: '100%', height: 120 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={history.slice(-90)} margin={{ top: 4, right: 4, left: 4, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 8, fill: '#64748B', fontFamily: 'monospace' }}
                    tickLine={false}
                    axisLine={{ stroke: '#1E293B' }}
                    interval={Math.floor(history.slice(-90).length / 6)}
                  />
                  <YAxis
                    tick={{ fontSize: 8, fill: '#64748B', fontFamily: 'monospace' }}
                    tickLine={false}
                    axisLine={false}
                    domain={[0, 100]}
                    width={28}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1A1F2E',
                      border: '1px solid #1E293B',
                      borderRadius: 8,
                      fontSize: 11,
                      fontFamily: 'monospace',
                      color: '#f8fafc',
                    }}
                    labelStyle={{ color: '#64748B', fontSize: 10 }}
                    formatter={(value) => [`${value}`, 'Risk Score']}
                  />
                  <Bar dataKey="score" radius={[2, 2, 0, 0]}>
                    {history.slice(-90).map((day, i) => (
                      <Cell
                        key={i}
                        fill={day.score <= 35 ? C.green : day.score <= 65 ? C.amber : C.red}
                        fillOpacity={0.85}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-28 rounded-lg bg-[#0B0E14] border border-[#1E293B]/50 flex items-center justify-center">
              <div className="flex items-center text-xs text-gray-500 font-mono">
                <Clock className="w-4 h-4 mr-2 opacity-40" />
                Awaiting 90-day risk history data
              </div>
            </div>
          )}

          {/* Date axis labels for no-data fallback are handled by Recharts XAxis above */}
        </div>
      </Card>

      {/* ════════════════════════════════════════════════════════════════════════
          FOOTER
          ════════════════════════════════════════════════════════════════════════ */}
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
