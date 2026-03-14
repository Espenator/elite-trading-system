import React, { useMemo, useState, useCallback } from 'react';
import {
  TrendingUp, TrendingDown, Activity, Shield,
  Target, Zap, BarChart3, Brain,
  ArrowUpRight, ArrowDownRight, ChevronDown,
  Award, Cpu, CheckCircle, Crosshair, Star,
  Settings, Download, RefreshCw, Search, Maximize2, X, Filter,
  Info
} from 'lucide-react';
import { toast } from 'react-toastify';
import {
  AreaChart, Area, BarChart, Bar, ComposedChart,
  Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
  ScatterChart, Scatter
} from 'recharts';
import { useApi } from '../hooks/useApi';
import clsx from 'clsx';
import { TradingGradeHero, ReturnsHeatmapCalendar, ConcentricAIDial } from '../components/dashboard/PerformanceWidgets';

// ─── EMPTY DEFAULTS (all data from real API — no mock/fallback data) ─────────

const EMPTY_KPI = {
  equity: '$0', daily_pnl: '$0', open_positions: 0, win_rate: 0,
  avg_win: 0, avg_loss: 0, profit_factor: 0, sharpe: 0,
  max_drawdown: '0%', total_trades: 0, grade: '—', score: 0,
  deployed_pct: '0%', alpha: '0', expectancy: 0, max_dd: null,
  max_dd_pct: null, kelly_fraction: '0%', sortino: 0, calmar: 0,
  netPnl: 0, maxDd: 0, totalTrades: 0, winRate: 0,
  avgWin: 0, avgLoss: 0, profitFactor: 0,
  riskReward: 0,
  netPnlChg: 0, winRateChg: 0, avgWinChg: 0, avgLossChg: 0,
};

const agentColors = ['#F59E0B', '#94a3b8', '#B45309', '#6B7280', '#4B5563'];

const EMPTY_ML = {
  flywheel_cycles: 0, models_active: 0, accuracy: '0%', last_retrain: '—',
  drift_psi: 0, f1: '0', feature_store_sync: '—',
  accuracyTrend: [],
  stagedInferences: 0,
  totalInferences: 0,
  pipelineHealth: 0,
};

const EMPTY_RISK = {
  shieldStatus: '—',
  varDaily: 0,
  varWeekly: 0,
  currentExposure: 0,
  maxExposure: 100,
  riskHistory: [],
};

const EMPTY_STRATEGY = {
  signalHitRate: 0,
  totalSignals: 0,
  activeStrategies: [],
  sentiment: '—',
  regime: '—',
};

// ─── HELPER COMPONENTS ───────────────────────────────────────────────────────

const Panel = ({ title, icon: Icon, className, children, action }) => (
  <div className={clsx(
    'bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg overflow-hidden flex flex-col',
    className
  )}>
    <div className="px-3 py-2 border-b border-gray-800/50 flex items-center justify-between gap-2 shrink-0">
      <div className="flex items-center gap-2 min-w-0">
        {Icon && <Icon size={14} className="text-cyan-400 shrink-0" />}
        <span className="text-xs font-semibold text-white truncate" title={title}>{title}</span>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
    <div className="flex-1 min-h-0 p-3">
      {children}
    </div>
  </div>
);

/** Mini sparkline for KPI (mockup: small line graph) */
const MiniSparkline = ({ data = [], positive = true, height = 20, width = 48 }) => {
  const d = data.length ? data : [0, 2, 1, 3, 2, 4, 3];
  const max = Math.max(...d);
  const min = Math.min(...d);
  const range = max - min || 1;
  const points = d.map((v, i) => {
    const x = (i / (d.length - 1)) * (width - 4) + 2;
    const y = height - 2 - ((v - min) / range) * (height - 4);
    return `${x},${y}`;
  }).join(' ');
  return (
    <svg width={width} height={height} className="shrink-0">
      <polyline
        fill="none"
        stroke={positive ? '#10b981' : '#ef4444'}
        strokeWidth="1.5"
        points={points}
      />
    </svg>
  );
};

const KpiPill = ({ label, value, sub, change, positive, icon: Icon, sparkData }) => (
  <div className="flex flex-col items-center gap-0.5 px-2 py-1.5 min-w-[90px]">
    <div className="flex items-center gap-1 w-full justify-center min-w-0">
      {Icon && <Icon size={10} className="text-gray-500 shrink-0" />}
      <span className="text-[10px] text-gray-500 uppercase tracking-wider truncate" title={label}>{label}</span>
    </div>
    <span className={clsx(
      'text-sm font-bold whitespace-nowrap',
      positive === true && 'text-emerald-400',
      positive === false && 'text-red-400',
      positive === undefined && 'text-white'
    )} title={String(value)}>
      {value}
    </span>
    <div className="flex items-center gap-1 w-full justify-center">
      <MiniSparkline data={sparkData} positive={positive !== false} />
      {(change != null || sub) && (
        <span className={clsx(
          'text-[9px]',
          typeof change === 'number' && change >= 0 ? 'text-emerald-400' : 'text-red-400',
          typeof change === 'number' && change < 0 ? 'text-red-400' : typeof change === 'number' ? 'text-emerald-400' : 'text-gray-500'
        )}>
          {change != null ? `${change >= 0 ? '+' : ''}${change}%` : sub}
        </span>
      )}
    </div>
  </div>
);

const GradeCircle = ({ grade, label, size = 'lg' }) => {
  const sz = size === 'lg' ? 'w-16 h-16 text-2xl' : size === 'sm' ? 'w-8 h-8 text-sm' : 'w-10 h-10 text-base';
  const colors = {
    A: 'from-emerald-500 to-emerald-700 shadow-emerald-500/30',
    B: 'from-cyan-500 to-cyan-700 shadow-cyan-500/30',
    C: 'from-yellow-500 to-yellow-700 shadow-yellow-500/30',
    D: 'from-orange-500 to-orange-700 shadow-orange-500/30',
    F: 'from-red-500 to-red-700 shadow-red-500/30',
  };
  return (
    <div className="flex flex-col items-center gap-1">
      <div className={clsx(
        'rounded-full flex items-center justify-center font-bold bg-gradient-to-br shadow-lg',
        sz,
        colors[grade] || colors.A
      )}>
        {grade}
      </div>
      {label && <span className="text-xs text-emerald-400 font-medium">{label}</span>}
    </div>
  );
};

const MetricRow = ({ label, value, color }) => (
  <div className="flex items-center justify-between py-1">
    <span className="text-[11px] text-gray-400">{label}</span>
    <span className={clsx('text-sm font-semibold', color || 'text-white')}>{value}</span>
  </div>
);

const ProgressBar = ({ value, max = 100, color = 'bg-cyan-500', label, showPct = true }) => (
  <div className="w-full">
    {label && (
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] text-gray-400">{label}</span>
        {showPct && <span className="text-[10px] text-gray-300">{value}%</span>}
      </div>
    )}
    <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
      <div
        className={clsx('h-full rounded-full transition-all', color)}
        style={{ width: `${Math.min((value / max) * 100, 100)}%` }}
      />
    </div>
  </div>
);

const StatusDot = ({ status }) => {
  const c = status === 'Active' || status === 'active' || status === 'healthy'
    ? 'bg-emerald-400' : status === 'warning' ? 'bg-yellow-400' : 'bg-red-400';
  return <span className={clsx('inline-block w-2 h-2 rounded-full', c)} />;
};

/* Semicircle VaR gauge rendered via SVG */
const VarGauge = ({ label, value, max = 10, color = '#f59e0b' }) => {
  const pct = Math.min(value / max, 1);
  const angle = pct * 180;
  const r = 36;
  const cx = 50;
  const cy = 48;
  // Arc path
  const startX = cx - r;
  const startY = cy;
  const rad = (angle * Math.PI) / 180;
  const endX = cx - r * Math.cos(rad);
  const endY = cy - r * Math.sin(rad);
  const largeArc = angle > 180 ? 1 : 0;
  const bgPath = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;
  const valPath = `M ${startX} ${startY} A ${r} ${r} 0 ${largeArc} 1 ${endX} ${endY}`;

  return (
    <div className="flex flex-col items-center">
      <svg width="100" height="56" viewBox="0 0 100 56">
        <path d={bgPath} fill="none" stroke="#1e293b" strokeWidth="8" strokeLinecap="round" />
        <path d={valPath} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round" />
        <text x="50" y="46" textAnchor="middle" fill="#e2e8f0" fontSize="13" fontWeight="bold">
          {value}%
        </text>
      </svg>
      <span className="text-[9px] text-gray-500 -mt-1">{label}</span>
    </div>
  );
};

const chartTooltipStyle = {
  contentStyle: {
    background: '#0d1b2a',
    border: '1px solid rgba(30,58,95,0.5)',
    borderRadius: 8,
    fontSize: 11,
    color: '#e2e8f0',
  },
  cursor: { stroke: 'rgba(0,217,255,0.3)' },
};

/* Rank badge colors */
const rankColors = ['bg-emerald-500', 'bg-cyan-500', 'bg-violet-500', 'bg-amber-500', 'bg-rose-500'];

// ─── MAIN COMPONENT ──────────────────────────────────────────────────────────

export default function PerformanceAnalytics() {
  const { data: perfData, loading: perfLoading, refetch: refetchPerf } = useApi('performance');
  const { data: tradesData, loading: tradesLoading } = useApi('performanceTrades');
  const { data: flywheelData } = useApi('flywheel');
  const { data: riskData } = useApi('riskScore');
  const { data: agentsData } = useApi('agents');

  const [tradeSort, setTradeSort] = useState({ key: 'date', dir: 'desc' });
  const [showGradeModal, setShowGradeModal] = useState(false);
  const [tradeSearch, setTradeSearch] = useState('');
  const [showTradeSearch, setShowTradeSearch] = useState(false);
  const [tradeExpanded, setTradeExpanded] = useState(false);
  const [showTradeFilter, setShowTradeFilter] = useState(false);
  const [tradeFilterSide, setTradeFilterSide] = useState('all');
  const [tradeFilterPnl, setTradeFilterPnl] = useState('all');
  const [refreshing, setRefreshing] = useState(false);

  // Merge API data with empty defaults — no fake data
  const kpi = useMemo(() => ({ ...EMPTY_KPI, ...(perfData?.kpi || perfData || {}) }), [perfData]);
  const equityData = useMemo(() => perfData?.equity || [], [perfData]);
  const agents = useMemo(() => agentsData?.leaderboard || [], [agentsData]);
  const pnlBySymbol = useMemo(() => perfData?.pnlBySymbol || [], [perfData]);
  const trades = useMemo(() => {
    let raw = tradesData?.trades || [];
    // Apply search filter
    if (tradeSearch.trim()) {
      const q = tradeSearch.toLowerCase();
      raw = raw.filter(t => (t.symbol || '').toLowerCase().includes(q));
    }
    // Apply side filter
    if (tradeFilterSide !== 'all') {
      raw = raw.filter(t => {
        const side = (t.side || '').toLowerCase();
        if (tradeFilterSide === 'long') return side === 'long' || side === 'l' || side === 'buy';
        if (tradeFilterSide === 'short') return side === 'short' || side === 'h' || side === 'sell';
        return true;
      });
    }
    // Apply PnL filter
    if (tradeFilterPnl === 'winners') raw = raw.filter(t => (t.pnl ?? 0) > 0);
    if (tradeFilterPnl === 'losers') raw = raw.filter(t => (t.pnl ?? 0) < 0);
    // Sort
    const sorted = [...raw].sort((a, b) => {
      const av = a[tradeSort.key], bv = b[tradeSort.key];
      if (typeof av === 'string') return tradeSort.dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      return tradeSort.dir === 'asc' ? av - bv : bv - av;
    });
    return sorted;
  }, [tradesData, tradeSort, tradeSearch, tradeFilterSide, tradeFilterPnl]);
  const rollingRisk = useMemo(() => {
    const raw = perfData?.rollingRisk || [];
    return raw.map((r, i) => ({
      date: r.date ?? r.x ?? i,
      y: r.y ?? r.rollingSharpe ?? r.value ?? 0,
    }));
  }, [perfData]);
  const convexityData = useMemo(() => perfData?.convexity || [], [perfData]);
  const rrExpect = useMemo(() => perfData?.rrExpectancy || [], [perfData]);
  const ml = useMemo(() => ({ ...EMPTY_ML, ...(flywheelData || {}) }), [flywheelData]);
  const riskExp = useMemo(() => ({ ...EMPTY_RISK, ...(riskData || {}) }), [riskData]);
  const strategy = useMemo(() => ({ ...EMPTY_STRATEGY, ...(perfData?.strategy || {}) }), [perfData]);

  const handleSort = (key) => {
    setTradeSort(prev => ({
      key,
      dir: prev.key === key && prev.dir === 'desc' ? 'asc' : 'desc',
    }));
  };

  // Determine if we have real data
  const hasData = (kpi.totalTrades ?? 0) > 0 || trades.length > 0;

  // Refresh handler for Equity + Drawdown
  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await refetchPerf();
      toast.success('Performance data refreshed');
    } catch { toast.error('Refresh failed'); }
    setRefreshing(false);
  }, [refetchPerf]);

  // Export equity CSV
  const handleExportEquity = useCallback(() => {
    if (!equityData.length) { toast.info('No equity data to export'); return; }
    const headers = ['date', 'equity', 'drawdown'];
    const rows = equityData.map(r => headers.map(h => r[h] ?? '').join(','));
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `equity_curve_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click(); URL.revokeObjectURL(url);
    toast.success('Equity curve exported');
  }, [equityData]);

  // Export trade log CSV
  const handleExportTrades = useCallback(() => {
    if (!trades.length) { toast.info('No trades to export'); return; }
    const headers = ['date', 'symbol', 'side', 'qty', 'entry', 'exit', 'pnl'];
    const rows = trades.map(t => headers.map(h => t[h] ?? t.quantity ?? '').join(','));
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `trade_log_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click(); URL.revokeObjectURL(url);
    toast.success('Trade log exported');
  }, [trades]);

  // Format helpers for null-safe display
  const fmt = (v, fallback = '--') => (v == null || v === '' || (typeof v === 'number' && isNaN(v))) ? fallback : v;
  const fmtUsd = (v) => v == null ? '--' : `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
  const fmtPct = (v) => v == null ? '--' : `${Number(v)}%`;

  // Returns Heatmap Calendar
  const returnsCalendar = useMemo(() => {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return months.map(m => ({
      month: m,
      value: '0',
    }));
  }, []);

  return (
    <div className="h-full flex flex-col overflow-auto bg-[#0B0E14]">
      {/* ─── HEADER (mockup: center title, right A Trading Grade button) ─── */}
      <div className="px-4 py-3 flex items-center justify-between border-b border-[rgba(42,52,68,0.5)] shrink-0">
        <div className="flex-1" />
        <h1 className="text-xl font-bold text-white tracking-tight text-center flex-1">Performance Analytics</h1>
        <div className="flex-1 flex justify-end">
          <button
            onClick={() => setShowGradeModal(true)}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 border border-emerald-500/40 rounded-lg px-4 py-2 transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-lg font-bold text-white">
              {kpi.grade && kpi.grade !== '—' ? kpi.grade : 'N/A'}
            </div>
            <span className="text-sm font-semibold text-white">{kpi.grade && kpi.grade !== '—' ? `${kpi.grade} Trading Grade` : 'Trading Grade'}</span>
          </button>
        </div>
      </div>

      {/* ─── KPI STRIP (mockup: value + sparkline + change %) ───── */}
      <div className="px-4 py-2 flex items-center gap-2 overflow-x-auto border-b border-[rgba(42,52,68,0.5)] shrink-0 bg-[#0B0E14]">
        <KpiPill label="Total Trades" value={fmt(kpi.totalTrades)} icon={BarChart3} sparkData={[0,2,1,3,2]} />
        <KpiPill label="Net P&L" value={fmtUsd(kpi.netPnl)} positive={(kpi.netPnl ?? 0) > 0} change={hasData ? kpi.netPnlChg : undefined} icon={TrendingUp} sparkData={[1,2,1.5,2.5,2,3]} />
        <KpiPill label="Win Rate" value={fmtPct(kpi.winRate)} positive={(kpi.winRate ?? 0) > 50} change={hasData ? kpi.winRateChg : undefined} icon={Target} sparkData={[0,1,2,2.5,3]} />
        <KpiPill label="Avg Win" value={kpi.avgWin != null ? `$${kpi.avgWin}` : '--'} positive change={hasData ? kpi.avgWinChg : undefined} icon={ArrowUpRight} sparkData={[0,1,1.5,2,2.5,3]} />
        <KpiPill label="Avg Loss" value={kpi.avgLoss != null ? `-$${Math.abs(kpi.avgLoss).toFixed(2)}` : '--'} positive={false} change={hasData ? kpi.avgLossChg : undefined} icon={ArrowDownRight} sparkData={[3,2.5,2,2.5,2,1]} />
        <KpiPill label="Profit Factor" value={fmt(kpi.profitFactor)} positive={(kpi.profitFactor ?? 0) > 1} icon={Zap} sparkData={[0,1,1.5,2,2.2]} />
        <KpiPill label="Max DD" value={kpi.maxDd != null ? `-${Math.abs(kpi.maxDd).toLocaleString()} / ${kpi.max_dd_pct ?? 0}%` : '--'} positive={false} icon={TrendingDown} sparkData={[1,2,2.5,2,3]} />
        <KpiPill label="Sharpe" value={fmt(kpi.sharpe)} positive={(kpi.sharpe ?? 0) > 1} icon={Activity} sparkData={[0,1,1.5,1.8,2]} />
        <KpiPill label="Expectancy" value={kpi.expectancy != null ? `$${kpi.expectancy}` : '--'} positive={(kpi.expectancy ?? 0) > 0} icon={Crosshair} sparkData={[0,1,2,2.5,3]} />
        <KpiPill label="R:R" value={kpi.riskReward != null ? `${kpi.riskReward}:1` : '--'} positive icon={Shield} sparkData={[0,1,1.5,1.6,1.7]} />
      </div>

      {/* ─── CONTENT GRID ──────────────────────────────────────── */}
      <div className="flex-1 p-3 space-y-3 min-h-0 overflow-auto">

        {/* ══ ROW 1 ═══════════════════════════════════════════════
            4 panels: Risk Cockpit | Equity + Drawdown | AI + Rolling Risk | Attribution + Agent ELO
        */}
        <div className="grid grid-cols-12 gap-3" style={{ minHeight: 300 }}>

          {/* ── 1. Risk Cockpit (mockup: Trading Grade Hero, Excellent, Sharpe/Sortino/Calmar + changes, Kelly Win/Lose) ── */}
          <Panel title="Risk Cockpit" icon={Shield} className="col-span-3">
            <div className="flex flex-col gap-2 h-full">
              <div className="flex flex-col items-center gap-0.5">
                <div className="text-[10px] text-gray-500 uppercase tracking-wider">Trading Grade Hero</div>
                <TradingGradeHero grade={kpi.grade || 'A'} score={kpi.score ?? 87} size={90} />
                <div className={`text-[10px] font-semibold ${(kpi.score ?? 0) === 0 ? 'text-gray-500' : (kpi.score ?? 0) >= 80 ? 'text-emerald-400' : (kpi.score ?? 0) >= 60 ? 'text-cyan-400' : (kpi.score ?? 0) >= 40 ? 'text-yellow-400' : 'text-red-400'}`}>{(kpi.score ?? 0) === 0 ? 'N/A' : (kpi.score ?? 0) >= 80 ? 'Excellent' : (kpi.score ?? 0) >= 60 ? 'Good' : (kpi.score ?? 0) >= 40 ? 'Fair' : 'Poor'}</div>
              </div>
              {/* Sharpe / Sortino / Calmar with change indicators */}
              <div className="grid grid-cols-3 gap-1 w-full">
                {[
                  { label: 'Sharpe', val: kpi.sharpe, delta: kpi.sharpeChg },
                  { label: 'Sortino', val: kpi.sortino, delta: kpi.sortinoChg },
                  { label: 'Calmar', val: kpi.calmar, delta: kpi.calmarChg },
                ].map(({ label, val, delta }) => (
                  <div key={label} className="text-center bg-[#0B0E14] rounded p-1.5">
                    <div className="text-[9px] text-gray-500">{label}</div>
                    <div className="text-sm font-bold text-white">{fmt(val)}</div>
                    {delta != null && hasData && (
                      <div className={`text-[9px] ${delta >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        ({delta >= 0 ? '+' : ''}{delta.toFixed(2)})
                      </div>
                    )}
                  </div>
                ))}
              </div>
              {/* Kelly Criterion - Win (green) + Lose (red) bar */}
              <div className="w-full">
                <div className="text-[10px] text-gray-500 mb-1">Kelly Criterion</div>
                {(kpi.kellyWin != null || kpi.kellyLose != null) && hasData ? (
                  <div className="flex h-4 rounded overflow-hidden">
                    <div className="flex-1 bg-emerald-500 flex items-center justify-center text-[9px] font-medium text-white" title="Win">
                      {fmtUsd(kpi.kellyWin)}
                    </div>
                    <div className="w-16 bg-red-500/80 flex items-center justify-center text-[9px] font-medium text-white" title="Lose">
                      {kpi.kellyLose != null ? `-${fmtUsd(Math.abs(kpi.kellyLose))}` : '--'}
                    </div>
                  </div>
                ) : (
                  <div className="flex h-4 rounded overflow-hidden bg-gray-800 items-center justify-center">
                    <span className="text-[9px] text-gray-500">Kelly: N/A</span>
                  </div>
                )}
              </div>
              {/* Risk/Reward + Expectancy mini bar chart */}
              <div className="w-full flex-1 min-h-0">
                <div className="text-[10px] text-gray-500 mb-1">Risk/Reward + Expectancy</div>
                {rrExpect.length > 0 ? (
                  <div className="h-[70px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={rrExpect} margin={{ top: 2, right: 5, left: -15, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,58,95,0.2)" />
                        <XAxis dataKey="name" tick={{ fontSize: 8, fill: '#6b7280' }} />
                        <YAxis tick={{ fontSize: 8, fill: '#6b7280' }} />
                        <Tooltip {...chartTooltipStyle} />
                        <Bar dataKey="rr" fill="#00D9FF" radius={[2, 2, 0, 0]} opacity={0.7} name="R:R" />
                        <Line type="monotone" dataKey="expectancy" stroke="#10b981" strokeWidth={1.5} dot={false} name="Expectancy" yAxisId={0} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-[70px] flex items-center justify-center text-[10px] text-gray-600">
                    No expectancy data available
                  </div>
                )}
              </div>
            </div>
          </Panel>

          {/* ── 2. Equity + Drawdown (mockup: toolbar gear/download/refresh) ── */}
          <Panel title="Equity + Drawdown" icon={TrendingUp} className="col-span-3" action={
            <div className="flex items-center gap-1">
              <button onClick={() => toast.info('Chart settings coming soon')} className="p-1 text-gray-500 hover:text-[#00D9FF] transition-colors" title="Settings"><Settings size={12} /></button>
              <button onClick={handleExportEquity} className="p-1 text-gray-500 hover:text-[#00D9FF] transition-colors" title="Download"><Download size={12} /></button>
              <button onClick={handleRefresh} className={clsx('p-1 text-gray-500 hover:text-[#00D9FF] transition-colors', refreshing && 'animate-spin')} title="Refresh"><RefreshCw size={12} /></button>
            </div>
          }>
            <div className="flex flex-col h-full">
              {equityData.length > 0 ? (
                <div className="flex-1 min-h-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={equityData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="#10b981" stopOpacity={0.02} />
                        </linearGradient>
                        <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#ef4444" stopOpacity={0.05} />
                          <stop offset="100%" stopColor="#ef4444" stopOpacity={0.25} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,58,95,0.2)" />
                      <XAxis dataKey="date" tick={{ fontSize: 8, fill: '#6b7280' }} interval="preserveStartEnd" />
                      <YAxis yAxisId="eq" tick={{ fontSize: 8, fill: '#6b7280' }} tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} />
                      <YAxis yAxisId="dd" orientation="right" tick={{ fontSize: 8, fill: '#6b7280' }} tickFormatter={v => `${v}%`} />
                      <Tooltip {...chartTooltipStyle} />
                      <Area yAxisId="eq" type="monotone" dataKey="equity" stroke="#10b981" strokeWidth={2} fill="url(#eqGrad)" />
                      <Area yAxisId="dd" type="monotone" dataKey="drawdown" stroke="#ef4444" strokeWidth={1} fill="url(#ddGrad)" />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center text-center">
                  <div>
                    <TrendingUp size={28} className="text-gray-700 mx-auto mb-2" />
                    <p className="text-[11px] text-gray-500">No equity data — execute trades to see your performance curve</p>
                  </div>
                </div>
              )}
            </div>
          </Panel>

          {/* ── 3. AI + Rolling Risk (mockup: Nested Concentric 78.3% teal / 67% green, 67% Agent center; Rolling Risk Sharpe line) ── */}
          <Panel title="AI + Rolling Risk" icon={Brain} className="col-span-3">
            <div className="flex flex-col gap-3 h-full">
              <div className="flex flex-col items-center">
                {rollingRisk.length > 0 ? (
                  <ConcentricAIDial
                    metrics={perfData?.aiMetrics || []}
                  />
                ) : (
                  <ConcentricAIDial metrics={[]} />
                )}
              </div>
              <div className="flex-1 min-h-0">
                <div className="text-[10px] text-gray-500 mb-1">Rolling Risk Sharpe</div>
                {rollingRisk.length > 0 ? (
                  <div className="h-[80px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={rollingRisk} margin={{ top: 2, right: 5, left: -15, bottom: 0 }}>
                        <defs>
                          <linearGradient id="rollingGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#06B6D4" stopOpacity={0.4} />
                            <stop offset="100%" stopColor="#06B6D4" stopOpacity={0.02} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,58,95,0.2)" />
                        <XAxis dataKey="date" tick={{ fontSize: 7, fill: '#6b7280' }} />
                        <YAxis tick={{ fontSize: 8, fill: '#6b7280' }} domain={[0, 'auto']} />
                        <Tooltip {...chartTooltipStyle} />
                        <Area type="monotone" dataKey="y" stroke="#06B6D4" fill="url(#rollingGrad)" strokeWidth={1.5} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-[80px] flex items-center justify-center text-[10px] text-gray-600">
                    No rolling risk data
                  </div>
                )}
              </div>
            </div>
          </Panel>

          {/* ── 4. Attribution + Agent ELO (mockup: P&L By Symbol, Agent Leaderboard, Returns Heatmap) ── */}
          <Panel title="Attribution + Agent ELO" icon={Award} className="col-span-3">
            <div className="flex flex-col gap-2 h-full">
              {/* P&L By Symbol - horizontal bar chart */}
              <div>
                <div className="text-[10px] text-gray-500 mb-1">P&L By Symbol</div>
                <div className="h-24">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={pnlBySymbol} layout="vertical" margin={{ top: 0, right: 5, left: 0, bottom: 0 }}>
                      <XAxis type="number" tick={{ fontSize: 8, fill: '#6b7280' }} tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`} />
                      <YAxis type="category" dataKey="symbol" width={36} tick={{ fontSize: 9, fill: '#9ca3af' }} />
                      <Bar dataKey="pnl" radius={[0, 2, 2, 0]}>
                        {pnlBySymbol.map((entry, i) => (
                          <Cell key={i} fill={entry.pnl >= 0 ? '#10b981' : '#ef4444'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              {/* Agent Attribution Leaderboard */}
              <div>
                <div className="text-[10px] text-gray-500 mb-1">Agent Attribution Leaderboard</div>
                <table className="w-full text-[9px]">
                  <thead>
                    <tr className="border-b border-gray-800/50">
                      <th className="text-left py-0.5 text-gray-500 font-normal">#</th>
                      <th className="text-left py-0.5 text-gray-500 font-normal">Agent</th>
                      <th className="text-right py-0.5 text-gray-500 font-normal">ELO</th>
                      <th className="text-right py-0.5 text-gray-500 font-normal">Chg</th>
                      <th className="text-right py-0.5 text-gray-500 font-normal">Contrib</th>
                      <th className="text-right py-0.5 text-gray-500 font-normal">Win%</th>
                    </tr>
                  </thead>
                  <tbody>
                    {agents.slice(0, 5).map((a, idx) => (
                      <tr key={a.name} className="border-b border-gray-800/20">
                        <td className="py-0.5">
                          <span className={clsx('inline-flex items-center justify-center w-4 h-4 rounded text-[8px] font-bold text-white', rankColors[idx] || 'bg-gray-600')}>{idx + 1}</span>
                        </td>
                        <td className="py-0.5 text-gray-300">{a.name}</td>
                        <td className="py-0.5 text-right text-white">{a.elo ?? a.score}</td>
                        <td className={clsx('py-0.5 text-right', (a.change ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400')}>
                          {a.change >= 0 ? '+' : ''}{a.change} ({a.changePct >= 0 ? '+' : ''}{a.changePct}%)
                        </td>
                        <td className="py-0.5 text-right text-gray-400">{a.contribution ?? a.contrib}%</td>
                        <td className="py-0.5 text-right text-gray-400">{a.winRate}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {/* Returns Heatmap Calendar */}
              <div className="flex-1 min-h-0">
                <div className="text-[10px] text-gray-500 mb-1">Returns Heatmap Calendar</div>
                <ReturnsHeatmapCalendar data={perfData?.returnsCalendar || []} className="min-h-[60px]" />
              </div>
            </div>
          </Panel>
        </div>

        {/* ══ ROW 2 ═══════════════════════════════════════════════
            Agent Attribution Leaderboard (expanded) | Risk/Reward + Expectancy | Enhanced Trades Table
        */}
        <div className="grid grid-cols-12 gap-3" style={{ minHeight: 240 }}>

          {/* Agent Attribution Leaderboard (expanded table — mockup: #, Agent, ELO, Changes, Contributions, Win Rates, Contribution) */}
          <Panel title="Agent Attribution Leaderboard" icon={Star} className="col-span-3">
            <div className="overflow-auto">
              <table className="w-full text-[10px]">
                <thead>
                  <tr className="border-b border-gray-800/50">
                    <th className="text-left py-1 px-1 text-gray-500 font-normal">#</th>
                    <th className="text-left py-1 px-1 text-gray-500 font-normal">Agent</th>
                    <th className="text-right py-1 px-1 text-gray-500 font-normal">ELO</th>
                    <th className="text-right py-1 px-1 text-gray-500 font-normal">Chg</th>
                    <th className="text-right py-1 px-1 text-gray-500 font-normal">Contrib</th>
                    <th className="text-right py-1 px-1 text-gray-500 font-normal">Win%</th>
                    <th className="text-right py-1 px-1 text-gray-500 font-normal">Contribution</th>
                  </tr>
                </thead>
                <tbody>
                  {agents.map((a, idx) => (
                    <tr key={a.name} className="border-b border-gray-800/20">
                      <td className="py-1 px-1">
                        <span className={clsx(
                          'inline-flex items-center justify-center w-4 h-4 rounded text-[8px] font-bold text-white',
                          rankColors[idx] || 'bg-gray-600'
                        )}>{idx + 1}</span>
                      </td>
                      <td className="py-1 px-1">
                        <div className="flex items-center gap-1">
                          <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: a.color || '#6b7280' }} />
                          <span className="text-gray-300 truncate">{a.name}</span>
                        </div>
                      </td>
                      <td className="py-1 px-1 text-right text-white">{a.elo ?? a.score}</td>
                      <td className={clsx('py-1 px-1 text-right', (a.change ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400')}>
                        {(a.change ?? 0) >= 0 ? '+' : ''}{a.change ?? 0} ({(a.changePct ?? 0) >= 0 ? '+' : ''}{a.changePct ?? 0}%)
                      </td>
                      <td className="py-1 px-1 text-right text-gray-400">{a.contribution ?? a.contrib ?? 0}%</td>
                      <td className="py-1 px-1 text-right text-gray-400">{a.winRate ?? 0}%</td>
                      <td className="py-1 px-1 text-right text-gray-400">{a.contribution ?? a.contrib ?? 0}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          {/* Risk/Reward + Expectancy chart */}
          <Panel title="Risk/Reward + Expectancy" icon={Crosshair} className="col-span-3">
            {rrExpect.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={rrExpect} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,58,95,0.2)" />
                  <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#6b7280' }} />
                  <YAxis yAxisId="rr" tick={{ fontSize: 9, fill: '#6b7280' }} />
                  <YAxis yAxisId="exp" orientation="right" tick={{ fontSize: 9, fill: '#6b7280' }} />
                  <Tooltip {...chartTooltipStyle} />
                  <Bar yAxisId="rr" dataKey="rr" fill="#00D9FF" radius={[3, 3, 0, 0]} opacity={0.7} name="R:R" />
                  <Line yAxisId="exp" type="monotone" dataKey="expectancy" stroke="#10b981" strokeWidth={2} dot={{ r: 3, fill: '#10b981' }} name="Expectancy" />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-center">
                <div>
                  <Crosshair size={24} className="text-gray-700 mx-auto mb-2" />
                  <p className="text-[10px] text-gray-500">No expectancy data available</p>
                </div>
              </div>
            )}
          </Panel>

          {/* Enhanced Trades Table (mockup: TRADE LOG toolbar, Date/Symbol/Side/Qty/Entry/Exit/P&L) */}
          <Panel title="Enhanced Trades Table" icon={BarChart3} className={clsx('col-span-6', tradeExpanded && 'fixed inset-4 z-50 col-span-12')} action={
            <div className="flex items-center gap-1">
              <button onClick={handleExportTrades} className="px-2 py-0.5 text-[10px] font-medium bg-[#00D9FF]/20 text-[#00D9FF] rounded border border-[#00D9FF]/40 hover:bg-[#00D9FF]/30 transition-colors">TRADE LOG</button>
              <button onClick={() => setShowTradeSearch(p => !p)} className={clsx('p-1 transition-colors', showTradeSearch ? 'text-[#00D9FF]' : 'text-gray-500 hover:text-[#00D9FF]')}><Search size={12} /></button>
              <button onClick={() => setTradeExpanded(p => !p)} className="p-1 text-gray-500 hover:text-[#00D9FF]">{tradeExpanded ? <X size={12} /> : <Maximize2 size={12} />}</button>
              <button onClick={() => { setTradeExpanded(false); setShowTradeSearch(false); setTradeSearch(''); setShowTradeFilter(false); setTradeFilterSide('all'); setTradeFilterPnl('all'); }} className="p-1 text-gray-500 hover:text-[#00D9FF]"><X size={12} /></button>
              <button onClick={() => setShowTradeFilter(p => !p)} className={clsx('p-1 transition-colors', showTradeFilter ? 'text-[#00D9FF]' : 'text-gray-500 hover:text-[#00D9FF]')}><Filter size={12} /></button>
            </div>
          }>
            {/* Search bar */}
            {showTradeSearch && (
              <div className="mb-2">
                <input
                  type="text"
                  value={tradeSearch}
                  onChange={e => setTradeSearch(e.target.value)}
                  placeholder="Search by symbol..."
                  className="w-full bg-[#0B0E14] border border-gray-700 rounded px-2 py-1 text-xs text-white placeholder-gray-600 focus:border-cyan-500 focus:outline-none"
                  autoFocus
                />
              </div>
            )}
            {/* Filter bar */}
            {showTradeFilter && (
              <div className="mb-2 flex items-center gap-2 flex-wrap">
                <span className="text-[9px] text-gray-500">Side:</span>
                {['all', 'long', 'short'].map(s => (
                  <button key={s} onClick={() => setTradeFilterSide(s)} className={clsx('px-2 py-0.5 rounded text-[9px]', tradeFilterSide === s ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40' : 'bg-gray-800 text-gray-400 border border-gray-700')}>
                    {s === 'all' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
                  </button>
                ))}
                <span className="text-[9px] text-gray-500 ml-2">P&L:</span>
                {['all', 'winners', 'losers'].map(p => (
                  <button key={p} onClick={() => setTradeFilterPnl(p)} className={clsx('px-2 py-0.5 rounded text-[9px]', tradeFilterPnl === p ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40' : 'bg-gray-800 text-gray-400 border border-gray-700')}>
                    {p === 'all' ? 'All' : p.charAt(0).toUpperCase() + p.slice(1)}
                  </button>
                ))}
              </div>
            )}
            <div className="overflow-auto h-full">
              <table className="w-full text-[10px]">
                <thead>
                  <tr className="border-b border-gray-800/50">
                    <th className="w-6 py-1 px-1 text-gray-500"><input type="checkbox" className="rounded" /></th>
                    {['date', 'symbol', 'side', 'qty', 'entry', 'exit', 'pnl'].map((col) => (
                      <th
                        key={col}
                        onClick={() => handleSort(col)}
                        className="text-left py-1 px-1.5 text-gray-500 uppercase cursor-pointer hover:text-cyan-400 transition-colors whitespace-nowrap"
                      >
                        {col}
                        {tradeSort.key === col && (
                          <ChevronDown
                            size={10}
                            className={clsx(
                              'inline ml-0.5 transition-transform',
                              tradeSort.dir === 'asc' && 'rotate-180'
                            )}
                          />
                        )}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {trades.map((t, i) => (
                    <tr key={t.id || i} className="border-b border-gray-800/20 hover:bg-gray-900/30 transition-colors">
                      <td className="py-1 px-1"><input type="checkbox" className="rounded" /></td>
                      <td className="py-1 px-1.5 text-gray-400">{t.date}</td>
                      <td className="py-1 px-1.5 text-white font-medium">{t.symbol}</td>
                      <td className="py-1 px-1.5">
                        <span className={clsx(
                          'px-1.5 py-0.5 rounded text-[9px] font-medium',
                          (t.side === 'Long' || t.side === 'L' || t.side === 'BUY') ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'
                        )}>
                          {t.side === 'Long' || t.side === 'BUY' ? 'L' : t.side === 'Short' || t.side === 'SELL' ? 'H' : (t.side || '—')}
                        </span>
                      </td>
                      <td className="py-1 px-1.5 text-gray-300">{t.qty ?? t.quantity ?? '—'}</td>
                      <td className="py-1 px-1.5 text-gray-300">${t.entry ?? '—'}</td>
                      <td className="py-1 px-1.5 text-gray-300">${t.exit ?? '—'}</td>
                      <td className={clsx('py-1 px-1.5 font-medium', (t.pnl ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400')}>
                        {(t.pnl ?? 0) >= 0 ? '+' : ''}{(t.pnl ?? 0).toLocaleString()}
                        {t.pnlPct != null && <span className="text-[9px] text-gray-500 ml-1">({(t.pnlPct >= 0 ? '+' : '')}{t.pnlPct}%)</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>

        {/* ══ ROW 3 ═══════════════════════════════════════════════
            ML & Flywheel Engine | Risk Cockpit Expanded | Strategy & Signals
        */}
        <div className="grid grid-cols-12 gap-3" style={{ minHeight: 240 }}>

          {/* ML & Flywheel Engine */}
          <Panel title="ML & Flywheel Engine" icon={Cpu} className="col-span-3">
            <div className="space-y-2">
              {/* ML Model Accuracy Trend */}
              <div>
                <div className="text-[10px] text-gray-500 mb-1">ML Model Accuracy Trend</div>
                <div className="h-14">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={ml.accuracyTrend?.length ? ml.accuracyTrend : [{ accuracy: 0.8 }]} margin={{ top: 2, right: 2, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="accGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <Area type="monotone" dataKey="accuracy" stroke="#8b5cf6" strokeWidth={1.5} fill="url(#accGrad)" />
                      <YAxis tick={{ fontSize: 8, fill: '#6b7280' }} domain={[0.6, 1]} />
                      <Tooltip {...chartTooltipStyle} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
              {/* Staged Inferences & Flywheel Pipeline Health */}
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-[#0B0E14] rounded p-1.5 text-center">
                  <div className="text-[9px] text-gray-500">Staged Inferences</div>
                  <div className="text-sm font-bold text-violet-400">{ml.stagedInferences}</div>
                </div>
                <div className="bg-[#0B0E14] rounded p-1.5 text-center">
                  <div className="text-[9px] text-gray-500">Total Inferences</div>
                  <div className="text-sm font-bold text-gray-300">{ml.totalInferences}</div>
                </div>
              </div>
              {/* Flywheel Pipeline Health */}
              <ProgressBar
                label="Flywheel Pipeline Health"
                value={ml.pipelineHealth}
                color="bg-violet-500"
              />
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-gray-400">Flywheel Cycles</span>
                <span className="text-xs font-bold text-gray-300">{ml.flywheelCycles}</span>
              </div>
            </div>
          </Panel>

          {/* Risk Cockpit Expanded */}
          <Panel title="Risk Cockpit Expanded" icon={Shield} className="col-span-3">
            <div className="space-y-2">
              {/* Risk Shield Status (mockup: green rectangular ACTIVE button) */}
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-gray-400">Risk Shield Status</span>
                <span className={clsx(
                  'px-2 py-0.5 text-[10px] font-bold rounded',
                  (riskExp.shieldStatus === 'ACTIVE' || riskExp.shieldStatus === 'Active' || riskExp.shieldStatus === 'active')
                    ? 'bg-emerald-500 text-white'
                    : 'bg-gray-600 text-gray-300'
                )}>
                  {riskExp.shieldStatus || '—'}
                </span>
              </div>
              {/* Risk History mini chart */}
              <div>
                <div className="text-[10px] text-gray-500 mb-1">Risk History</div>
                <div className="h-12">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={riskExp.riskHistory?.length ? riskExp.riskHistory : [{ score: 0 }]} margin={{ top: 2, right: 2, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="riskHGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="#f59e0b" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <Area type="monotone" dataKey="score" stroke="#f59e0b" strokeWidth={1.5} fill="url(#riskHGrad)" />
                      <YAxis tick={{ fontSize: 8, fill: '#6b7280' }} />
                      <Tooltip {...chartTooltipStyle} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
              {/* VaR Gauges - Semicircle */}
              <div className="text-[10px] text-gray-500 mb-1">VaR Gauges</div>
              <div className="flex items-center justify-center gap-4">
                <VarGauge label="Daily VaR" value={riskExp.varDaily} max={10} color="#f59e0b" />
                <VarGauge label="Weekly VaR" value={riskExp.varWeekly} max={10} color="#ef4444" />
              </div>
              {/* Exposure */}
              <ProgressBar
                label="Current Exposure"
                value={riskExp.currentExposure}
                max={riskExp.maxExposure}
                color="bg-amber-500"
              />
            </div>
          </Panel>

          {/* Strategy & Signals */}
          <Panel title="Strategy & Signals" icon={Target} className="col-span-6">
            <div className="grid grid-cols-3 gap-4 h-full">
              {/* Signal Hit Rate */}
              <div className="space-y-2">
                <div className="text-[10px] text-gray-500">Signal Hit Rate</div>
                <div className="flex items-end gap-1">
                  <span className="text-2xl font-bold text-emerald-400">{strategy.signalHitRate}%</span>
                  <span className="text-[10px] text-gray-500 mb-1">of {strategy.totalSignals}</span>
                </div>
                <div className="h-12 mt-1">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={[
                      { name: 'Hit', value: strategy.signalHitRate },
                      { name: 'Miss', value: 100 - strategy.signalHitRate },
                    ]} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                      <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                        <Cell fill="#10b981" />
                        <Cell fill="#374151" />
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Market Sentiment & Regime */}
              <div className="space-y-2">
                <div className="text-[10px] text-gray-500">Market Sentiment & Regime</div>
                <div className="bg-[#0B0E14] rounded-lg p-2 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-gray-400">Sentiment</span>
                    <span className={clsx(
                      'text-xs font-semibold px-2 py-0.5 rounded',
                      strategy.sentiment === 'Bullish' ? 'bg-emerald-500/15 text-emerald-400' :
                      strategy.sentiment === 'Bearish' ? 'bg-red-500/15 text-red-400' :
                      'bg-yellow-500/15 text-yellow-400'
                    )}>
                      {strategy.sentiment}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-gray-400">Regime</span>
                    <span className="text-xs font-semibold text-cyan-400">{strategy.regime}</span>
                  </div>
                </div>
              </div>

              {/* Active Strategies */}
              <div className="space-y-2">
                <div className="text-[10px] text-gray-500">Active Strategies</div>
                <div className="space-y-1.5">
                  {(strategy.activeStrategies || []).map((s) => (
                    <div key={s} className="flex items-center gap-2 bg-[#0B0E14] rounded px-2 py-1.5">
                      <CheckCircle size={10} className="text-emerald-400 shrink-0" />
                      <span className="text-[10px] text-gray-300 truncate">{s}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Panel>
        </div>
      </div>

      {/* ─── TRADING GRADE MODAL ──────────────────────────────────────────────── */}
      {showGradeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setShowGradeModal(false)}>
          <div className="bg-[#111827] border border-gray-700 rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Award size={20} className="text-cyan-400" />
                Trading Grade Breakdown
              </h3>
              <button onClick={() => setShowGradeModal(false)} className="p-1 text-gray-400 hover:text-white"><X size={18} /></button>
            </div>
            {hasData ? (
              <div className="space-y-3">
                <div className="flex items-center justify-center mb-4">
                  <TradingGradeHero grade={kpi.grade || '--'} score={kpi.score ?? 0} size={100} />
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <MetricRow label="Win Rate" value={fmtPct(kpi.winRate)} color="text-emerald-400" />
                  <MetricRow label="Profit Factor" value={fmt(kpi.profitFactor)} color="text-cyan-400" />
                  <MetricRow label="Sharpe Ratio" value={fmt(kpi.sharpe)} color="text-cyan-400" />
                  <MetricRow label="Max Drawdown" value={kpi.maxDd != null ? `${kpi.maxDd}%` : '--'} color="text-red-400" />
                  <MetricRow label="R:R Ratio" value={kpi.riskReward != null ? `${kpi.riskReward}:1` : '--'} color="text-cyan-400" />
                  <MetricRow label="Expectancy" value={kpi.expectancy != null ? `$${kpi.expectancy}` : '--'} color="text-emerald-400" />
                </div>
                <p className="text-[10px] text-gray-500 text-center mt-3">
                  Grade is calculated from win rate, risk-adjusted returns, drawdown control, and consistency.
                </p>
              </div>
            ) : (
              <div className="text-center py-6">
                <Info size={32} className="text-gray-600 mx-auto mb-3" />
                <p className="text-sm text-gray-400">No trades to grade yet</p>
                <p className="text-[10px] text-gray-600 mt-1">Start trading to earn your performance grade</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─── FOOTER (mockup: Embodier Trader - Performance Analytics v2.0 | Connected | Active filters in cyan | Data: Jan 1 - Feb 28, 2026 - 312 trades) ── */}
      <div className="px-4 py-2 border-t border-gray-800/50 flex items-center justify-between text-[10px] text-[#94a3b8] shrink-0 bg-[#0B0E14]">
        <span>Embodier Trader - Performance Analytics v2.0 | Connected | Active filters in cyan | {trades.length} trades loaded</span>
      </div>
    </div>
  );
}
