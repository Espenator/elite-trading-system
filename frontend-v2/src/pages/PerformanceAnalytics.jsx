import React, { useMemo, useState } from 'react';
import {
  TrendingUp, TrendingDown, Activity, Shield,
  Target, Zap, BarChart3, Brain,
  ArrowUpRight, ArrowDownRight, ChevronDown,
  Award, Cpu, CheckCircle, Crosshair, Star,
  Settings, Download, RefreshCw, Search, Maximize2, X, Filter
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, ComposedChart,
  Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
  ScatterChart, Scatter
} from 'recharts';
import { useApi } from '../hooks/useApi';
import clsx from 'clsx';
import { TradingGradeHero, ReturnsHeatmapCalendar, ConcentricAIDial } from '../components/dashboard/PerformanceWidgets';

// ─── FALLBACK DATA (zeros / empty until API provides real values) ────────────

// Mockup fallback values
const FALLBACK_KPI = {
  equity: '$0', daily_pnl: '$0', open_positions: 0, win_rate: 68.4,
  avg_win: 312.5, avg_loss: -187.2, profit_factor: 2.14, sharpe: 1.87,
  max_drawdown: '0%', total_trades: 247, grade: 'A', score: 87,
  deployed_pct: '0%', alpha: '0', expectancy: 89.4, max_dd: 4230,
  max_dd_pct: -8.2, kelly_fraction: '0%', sortino: 2.85, calmar: 1.87,
  netPnl: 12847.32, maxDd: 4230, totalTrades: 247, winRate: 68.4,
  avgWin: 312.5, avgLoss: -187.2, profitFactor: 2.14,
  riskReward: 1.67,
  // Change indicators for KPI strip
  netPnlChg: 0.37, winRateChg: 0.07, avgWinChg: 0.07, avgLossChg: -0.27,
};

const FALLBACK_EQUITY = Array.from({ length: 21 }, (_, i) => ({
  date: String(i),
  equity: 100000 + i * 600 + Math.sin(i / 2) * 2000,
  drawdown: -Math.min(i * 0.4, 10),
}));

const agentColors = ['#F59E0B', '#94a3b8', '#B45309', '#6B7280', '#4B5563'];
const FALLBACK_AGENTS = [
  { name: 'Alpha Scout', elo: 1850, change: 45, changePct: 2.5, contribution: 28, winRate: 72, color: agentColors[0], pnl: 3600, trades: 84 },
  { name: 'Risk Guardian', elo: 1780, change: -12, changePct: -0.7, contribution: 22, winRate: 68, color: agentColors[1], pnl: 2827, trades: 66 },
  { name: 'Momentum Tracker', elo: 1720, change: 38, changePct: 2.2, contribution: 18, winRate: 65, color: agentColors[2], pnl: 2312, trades: 54 },
  { name: 'Sector Rotator', elo: 1690, change: 22, changePct: 1.3, contribution: 15, winRate: 61, color: agentColors[3], pnl: 1927, trades: 43 },
];
const FALLBACK_PNL_BY_SYMBOL = [
  { symbol: 'AAPL', pnl: 4200 },
  { symbol: 'TSLA', pnl: -1200 },
  { symbol: 'NVDA', pnl: 5800 },
  { symbol: 'MSFT', pnl: 2100 },
  { symbol: 'GOOGL', pnl: 1800 },
  { symbol: 'META', pnl: -800 },
];

const FALLBACK_TRADES = [
  { id: '1', date: '02/28', symbol: 'NVDA', side: 'L', qty: 50, entry: 875.2, exit: 891.4, pnl: 810, pnlPct: 1.9 },
  { id: '2', date: '02/28', symbol: 'AAPL', side: 'H', qty: 100, entry: 178.5, exit: 177.2, pnl: -130, pnlPct: -0.7 },
  { id: '3', date: '02/27', symbol: 'TSLA', side: 'L', qty: 25, entry: 205.0, exit: 212.8, pnl: 195, pnlPct: 3.8 },
  { id: '4', date: '02/27', symbol: 'MSFT', side: 'L', qty: 40, entry: 408.1, exit: 412.0, pnl: 156, pnlPct: 1.0 },
  { id: '5', date: '02/26', symbol: 'GOOGL', side: 'L', qty: 30, entry: 142.0, exit: 143.5, pnl: 45, pnlPct: 1.1 },
  { id: '6', date: '02/26', symbol: 'META', side: 'H', qty: 20, entry: 495.0, exit: 502.1, pnl: -142, pnlPct: -1.4 },
];

const FALLBACK_ROLLING_RISK = [{ date: 0, y: 0.5 }, { date: 2, y: 0.7 }, { date: 4, y: 0.6 }, { date: 6, y: 0.9 }, { date: 8, y: 1.0 }, { date: 10, y: 1.2 }];

const FALLBACK_CONVEXITY = [];

const FALLBACK_RR_EXPECT = [{ name: 'R:R', rr: 1.67, expectancy: 89.4 }];

const FALLBACK_ML = {
  flywheel_cycles: 12, models_active: 4, accuracy: '0%', last_retrain: '—',
  drift_psi: 0, f1: '0', feature_store_sync: '—',
  accuracyTrend: Array.from({ length: 20 }, (_, i) => ({ accuracy: 0.7 + (i / 20) * 0.25 + Math.sin(i / 3) * 0.05 })),
  stagedInferences: 1847,
  totalInferences: 2103,
  pipelineHealth: 85,
};

const FALLBACK_RISK_EXPANDED = {
  shieldStatus: 'ACTIVE',
  varDaily: 4.2,
  varWeekly: 6.8,
  currentExposure: 65,
  maxExposure: 100,
  riskHistory: Array.from({ length: 61 }, (_, i) => ({ score: 50 + Math.sin(i / 8) * 40 + i * 0.5 })),
};

const FALLBACK_STRATEGY = {
  signalHitRate: 72,
  totalSignals: 312,
  activeStrategies: ['Strateg A'],
  sentiment: 'Bullish',
  regime: 'GREEN',
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
        <span className="text-xs font-semibold text-white truncate">{title}</span>
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
  <div className="flex flex-col items-center gap-0.5 px-2 py-1.5 min-w-[72px]">
    <div className="flex items-center gap-1 w-full justify-center">
      {Icon && <Icon size={10} className="text-gray-500 shrink-0" />}
      <span className="text-[10px] text-gray-500 uppercase tracking-wider truncate">{label}</span>
    </div>
    <span className={clsx(
      'text-sm font-bold whitespace-nowrap',
      positive === true && 'text-emerald-400',
      positive === false && 'text-red-400',
      positive === undefined && 'text-white'
    )}>
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
  const { data: perfData, loading: perfLoading } = useApi('performance');
  const { data: tradesData, loading: tradesLoading } = useApi('performanceTrades');
  const { data: flywheelData } = useApi('flywheel');
  const { data: riskData } = useApi('riskScore');
  const { data: agentsData } = useApi('agents');

  const [tradeSort, setTradeSort] = useState({ key: 'date', dir: 'desc' });

  // Merge API data with fallbacks
  const kpi = useMemo(() => ({ ...FALLBACK_KPI, ...(perfData?.kpi || perfData || {}) }), [perfData]);
  const equityData = useMemo(() => perfData?.equity || FALLBACK_EQUITY, [perfData]);
  const agents = useMemo(() => agentsData?.leaderboard || FALLBACK_AGENTS, [agentsData]);
  const pnlBySymbol = useMemo(() => perfData?.pnlBySymbol || FALLBACK_PNL_BY_SYMBOL, [perfData]);
  const trades = useMemo(() => {
    const raw = tradesData?.trades || FALLBACK_TRADES;
    const sorted = [...raw].sort((a, b) => {
      const av = a[tradeSort.key], bv = b[tradeSort.key];
      if (typeof av === 'string') return tradeSort.dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      return tradeSort.dir === 'asc' ? av - bv : bv - av;
    });
    return sorted;
  }, [tradesData, tradeSort]);
  const rollingRisk = useMemo(() => {
    const raw = perfData?.rollingRisk || FALLBACK_ROLLING_RISK;
    return raw.map((r, i) => ({
      date: r.date ?? r.x ?? i,
      y: r.y ?? r.rollingSharpe ?? r.value ?? FALLBACK_ROLLING_RISK[i]?.y ?? 0.5,
    }));
  }, [perfData]);
  const convexityData = useMemo(() => perfData?.convexity || FALLBACK_CONVEXITY, [perfData]);
  const rrExpect = useMemo(() => perfData?.rrExpectancy || FALLBACK_RR_EXPECT, [perfData]);
  const ml = useMemo(() => ({ ...FALLBACK_ML, ...(flywheelData || {}) }), [flywheelData]);
  const riskExp = useMemo(() => ({ ...FALLBACK_RISK_EXPANDED, ...(riskData || {}) }), [riskData]);
  const strategy = useMemo(() => ({ ...FALLBACK_STRATEGY, ...(perfData?.strategy || {}) }), [perfData]);

  const handleSort = (key) => {
    setTradeSort(prev => ({
      key,
      dir: prev.key === key && prev.dir === 'desc' ? 'asc' : 'desc',
    }));
  };

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
          <button className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 border border-emerald-500/40 rounded-lg px-4 py-2 transition-colors">
            <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-lg font-bold text-white">
              {kpi.grade || 'A'}
            </div>
            <span className="text-sm font-semibold text-white">A Trading Grade</span>
          </button>
        </div>
      </div>

      {/* ─── KPI STRIP (mockup: value + sparkline + change %) ───── */}
      <div className="px-4 py-2 flex items-center gap-2 overflow-x-auto border-b border-[rgba(42,52,68,0.5)] shrink-0 bg-[#0B0E14]">
        <KpiPill label="Total Trades" value={kpi.totalTrades} icon={BarChart3} sparkData={[0,2,1,3,2]} />
        <KpiPill label="Net P&L" value={`+$${(kpi.netPnl ?? 0).toLocaleString(undefined,{minimumFractionDigits:2})}`} positive={(kpi.netPnl ?? 0) > 0} change={kpi.netPnlChg} icon={TrendingUp} sparkData={[1,2,1.5,2.5,2,3]} />
        <KpiPill label="Win Rate" value={`${(kpi.winRate ?? 0)}%`} positive={(kpi.winRate ?? 0) > 50} change={kpi.winRateChg} icon={Target} sparkData={[0,1,2,2.5,3]} />
        <KpiPill label="Avg Win" value={`$${kpi.avgWin ?? 0}`} positive change={kpi.avgWinChg} icon={ArrowUpRight} sparkData={[0,1,1.5,2,2.5,3]} />
        <KpiPill label="Avg Loss" value={`-$${Math.abs(kpi.avgLoss ?? 0).toFixed(2)}`} positive={false} change={kpi.avgLossChg} icon={ArrowDownRight} sparkData={[3,2.5,2,2.5,2,1]} />
        <KpiPill label="Profit Factor" value={kpi.profitFactor} positive={(kpi.profitFactor ?? 0) > 1} icon={Zap} sparkData={[0,1,1.5,2,2.2]} />
        <KpiPill label="Max DD" value={`-${Math.abs(kpi.maxDd ?? 0).toLocaleString()} / ${(kpi.max_dd_pct ?? -8.2)}%`} positive={false} icon={TrendingDown} sparkData={[1,2,2.5,2,3]} />
        <KpiPill label="Sharpe" value={kpi.sharpe} positive={(kpi.sharpe ?? 0) > 1} icon={Activity} sparkData={[0,1,1.5,1.8,2]} />
        <KpiPill label="Expectancy" value={`$${kpi.expectancy ?? 0}`} positive={(kpi.expectancy ?? 0) > 0} icon={Crosshair} sparkData={[0,1,2,2.5,3]} />
        <KpiPill label="R:R" value={`${kpi.riskReward ?? 0}:1`} positive icon={Shield} sparkData={[0,1,1.5,1.6,1.7]} />
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
                <div className="text-[10px] font-semibold text-emerald-400">Excellent</div>
              </div>
              {/* Sharpe / Sortino / Calmar with change indicators */}
              <div className="grid grid-cols-3 gap-1 w-full">
                <div className="text-center bg-[#0B0E14] rounded p-1.5">
                  <div className="text-[9px] text-gray-500">Sharpe</div>
                  <div className="text-sm font-bold text-white">{kpi.sharpe}</div>
                  <div className="text-[9px] text-emerald-400">(+0.50)</div>
                </div>
                <div className="text-center bg-[#0B0E14] rounded p-1.5">
                  <div className="text-[9px] text-gray-500">Sortino</div>
                  <div className="text-sm font-bold text-white">{kpi.sortino}</div>
                  <div className="text-[9px] text-emerald-400">(+0.92)</div>
                </div>
                <div className="text-center bg-[#0B0E14] rounded p-1.5">
                  <div className="text-[9px] text-gray-500">Calmar</div>
                  <div className="text-sm font-bold text-white">{kpi.calmar}</div>
                  <div className="text-[9px] text-red-400">(-0.29)</div>
                </div>
              </div>
              {/* Kelly Criterion - Win (green) + Lose (red) bar */}
              <div className="w-full">
                <div className="text-[10px] text-gray-500 mb-1">Kelly Criterion</div>
                <div className="flex h-4 rounded overflow-hidden">
                  <div className="flex-1 bg-emerald-500 flex items-center justify-center text-[9px] font-medium text-white" title="Win">$12,828.50</div>
                  <div className="w-16 bg-red-500/80 flex items-center justify-center text-[9px] font-medium text-white" title="Lose">-$3.50</div>
                </div>
              </div>
              {/* Risk/Reward + Expectancy mini bar chart */}
              <div className="w-full flex-1 min-h-0">
                <div className="text-[10px] text-gray-500 mb-1">Risk/Reward + Expectancy</div>
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
              </div>
            </div>
          </Panel>

          {/* ── 2. Equity + Drawdown (mockup: toolbar gear/download/refresh) ── */}
          <Panel title="Equity + Drawdown" icon={TrendingUp} className="col-span-3" action={
            <div className="flex items-center gap-1">
              <button className="p-1 text-gray-500 hover:text-[#00D9FF] transition-colors" title="Settings"><Settings size={12} /></button>
              <button className="p-1 text-gray-500 hover:text-[#00D9FF] transition-colors" title="Download"><Download size={12} /></button>
              <button className="p-1 text-gray-500 hover:text-[#00D9FF] transition-colors" title="Refresh"><RefreshCw size={12} /></button>
            </div>
          }>
            <div className="flex flex-col h-full">
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
            </div>
          </Panel>

          {/* ── 3. AI + Rolling Risk (mockup: Nested Concentric 78.3% teal / 67% green, 67% Agent center; Rolling Risk Sharpe line) ── */}
          <Panel title="AI + Rolling Risk" icon={Brain} className="col-span-3">
            <div className="flex flex-col gap-3 h-full">
              <div className="flex flex-col items-center">
                <ConcentricAIDial
                  metrics={[{ name: 'Outer', value: 78.3, color: '#06B6D4' }, { name: 'Agent', value: 67, color: '#10B981' }]}
                  centerLabel="67% Agent"
                />
              </div>
              <div className="flex-1 min-h-0">
                <div className="text-[10px] text-gray-500 mb-1">Rolling Risk Sharpe</div>
                <div className="h-[80px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={rollingRisk.length ? rollingRisk : FALLBACK_ROLLING_RISK} margin={{ top: 2, right: 5, left: -15, bottom: 0 }}>
                      <defs>
                        <linearGradient id="rollingGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#06B6D4" stopOpacity={0.4} />
                          <stop offset="100%" stopColor="#06B6D4" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,58,95,0.2)" />
                      <XAxis dataKey="date" tick={{ fontSize: 7, fill: '#6b7280' }} />
                      <YAxis tick={{ fontSize: 8, fill: '#6b7280' }} domain={[0, 1.5]} />
                      <Tooltip {...chartTooltipStyle} />
                      <Area type="monotone" dataKey="y" stroke="#06B6D4" fill="url(#rollingGrad)" strokeWidth={1.5} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
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
          </Panel>

          {/* Enhanced Trades Table (mockup: TRADE LOG toolbar, Date/Symbol/Side/Qty/Entry/Exit/P&L) */}
          <Panel title="Enhanced Trades Table" icon={BarChart3} className="col-span-6" action={
            <div className="flex items-center gap-1">
              <button className="px-2 py-0.5 text-[10px] font-medium bg-[#00D9FF]/20 text-[#00D9FF] rounded border border-[#00D9FF]/40">TRADE LOG</button>
              <button className="p-1 text-gray-500 hover:text-[#00D9FF]"><Search size={12} /></button>
              <button className="p-1 text-gray-500 hover:text-[#00D9FF]"><Maximize2 size={12} /></button>
              <button className="p-1 text-gray-500 hover:text-[#00D9FF]"><X size={12} /></button>
              <button className="p-1 text-gray-500 hover:text-[#00D9FF]"><Filter size={12} /></button>
            </div>
          }>
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

      {/* ─── FOOTER (mockup: Embodier Trader - Performance Analytics v2.0 | Connected | Active filters in cyan | Data: Jan 1 - Feb 28, 2026 - 312 trades) ── */}
      <div className="px-4 py-2 border-t border-gray-800/50 flex items-center justify-between text-[10px] text-[#94a3b8] shrink-0 bg-[#0B0E14]">
        <span>Embodier Trader - Performance Analytics v2.0 | Connected | Active filters in cyan | Data: Jan 1 - Feb 28, 2026 - 312 trades</span>
      </div>
    </div>
  );
}
