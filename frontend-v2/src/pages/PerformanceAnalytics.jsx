import React, { useMemo, useState } from 'react';
import {
  TrendingUp, TrendingDown, Activity, Shield,
  Target, Zap, BarChart3, Brain, Gauge,
  ArrowUpRight, ArrowDownRight, ChevronDown,
  RefreshCw, Award, Cpu, AlertTriangle,
  CheckCircle, Clock, Crosshair, Star
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, ComposedChart,
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, RadialBarChart,
  RadialBar, Cell, ReferenceLine, ScatterChart, Scatter
} from 'recharts';
import { useApi } from '../hooks/useApi';
import clsx from 'clsx';

// ─── MOCK / FALLBACK DATA ────────────────────────────────────────────────────

const FALLBACK_KPI = {
  totalTrades: 247,
  netPnl: 52147.32,
  winRate: 68.4,
  avgWin: 312.58,
  avgLoss: -187.28,
  profitFactor: 2.14,
  maxDd: -4238,
  maxDdPct: -4.1,
  sharpe: 1.87,
  expectancy: 89.40,
  riskReward: 1.67,
  sortino: 1.85,
  calmar: 1.87,
  kellyPct: 34.2,
  grade: 'A',
  gradeLabel: 'Excellent',
};

const FALLBACK_EQUITY = Array.from({ length: 60 }, (_, i) => ({
  date: `2024-${String(Math.floor(i / 5) + 1).padStart(2, '0')}-${String((i % 28) + 1).padStart(2, '0')}`,
  equity: 10000 + i * 850 + Math.sin(i * 0.4) * 2000 + Math.random() * 1500,
  drawdown: -(Math.random() * 4 + (i % 10 === 0 ? 3 : 0.5)),
}));

const FALLBACK_AGENTS = [
  { name: 'Alpha Scout', score: 87, elo: 1842, pnl: 27300, trades: 84, winRate: 72.1, color: '#10b981' },
  { name: 'Risk Guardian', score: 79, elo: 1798, pnl: 14200, trades: 63, winRate: 68.3, color: '#06b6d4' },
  { name: 'Meta Architect', score: 71, elo: 1756, pnl: 8400, trades: 55, winRate: 65.5, color: '#8b5cf6' },
  { name: 'Meta Guardian', score: 63, elo: 1710, pnl: 2247, trades: 45, winRate: 60.0, color: '#f59e0b' },
];

const FALLBACK_TRADES = [
  { id: 1, date: '2024-08-08', symbol: 'AAPL', side: 'Long', entry: 185.42, exit: 192.18, pnl: 676.00, rr: '2.3:1', status: 'Won' },
  { id: 2, date: '2024-08-07', symbol: 'MSFT', side: 'Long', entry: 338.90, exit: 345.60, pnl: 670.00, rr: '1.8:1', status: 'Won' },
  { id: 3, date: '2024-08-07', symbol: 'TSLA', side: 'Short', entry: 245.00, exit: 252.30, pnl: -730.00, rr: '-1.2:1', status: 'Lost' },
  { id: 4, date: '2024-08-06', symbol: 'NVDA', side: 'Long', entry: 460.20, exit: 471.50, pnl: 1130.00, rr: '3.1:1', status: 'Won' },
  { id: 5, date: '2024-08-06', symbol: 'AMZN', side: 'Long', entry: 178.50, exit: 176.20, pnl: -230.00, rr: '-0.8:1', status: 'Lost' },
  { id: 6, date: '2024-08-05', symbol: 'SPY', side: 'Long', entry: 448.30, exit: 453.80, pnl: 550.00, rr: '1.9:1', status: 'Won' },
  { id: 7, date: '2024-08-05', symbol: 'META', side: 'Long', entry: 475.10, exit: 482.40, pnl: 730.00, rr: '2.1:1', status: 'Won' },
  { id: 8, date: '2024-08-04', symbol: 'GOOG', side: 'Short', entry: 172.80, exit: 168.50, pnl: 430.00, rr: '1.5:1', status: 'Won' },
];

const FALLBACK_ROLLING_RISK = Array.from({ length: 30 }, (_, i) => ({
  date: `Aug ${i + 1}`,
  rollingVol: 12 + Math.sin(i * 0.3) * 4 + Math.random() * 2,
  rollingSharpe: 1.5 + Math.sin(i * 0.2) * 0.5 + Math.random() * 0.3,
}));

const FALLBACK_RR_EXPECT = [
  { name: 'Watchlist', rr: 1.8, expectancy: 92 },
  { name: 'Momentum', rr: 2.1, expectancy: 105 },
  { name: 'Mean Rev', rr: 1.4, expectancy: 68 },
  { name: 'Breakout', rr: 2.4, expectancy: 118 },
  { name: 'Scalp', rr: 1.2, expectancy: 45 },
];

const FALLBACK_ML = {
  accuracyTrend: Array.from({ length: 20 }, (_, i) => ({
    epoch: i + 1,
    accuracy: 0.72 + Math.sin(i * 0.3) * 0.05 + i * 0.005,
  })),
  stagedInferences: 12,
  totalInferences: 847,
  pipelineHealth: 94,
  flywheelCycles: 156,
};

const FALLBACK_RISK_EXPANDED = {
  shieldStatus: 'Active',
  varDaily: 2.1,
  varWeekly: 4.8,
  currentExposure: 67,
  maxExposure: 85,
  riskHistory: Array.from({ length: 20 }, (_, i) => ({
    day: i + 1,
    score: 65 + Math.sin(i * 0.4) * 15 + Math.random() * 5,
  })),
};

const FALLBACK_STRATEGY = {
  signalHitRate: 73.2,
  totalSignals: 412,
  activeStrategies: ['Momentum Alpha', 'Mean Reversion V2', 'Breakout Scanner'],
  sentiment: 'Bullish',
  regime: 'Trending',
};

// ─── HELPER COMPONENTS ───────────────────────────────────────────────────────

const Panel = ({ title, icon: Icon, className, children, action }) => (
  <div className={clsx(
    'bg-[#0a1628] border border-[#1e3a5f]/40 rounded-lg overflow-hidden flex flex-col',
    className
  )}>
    <div className="px-3 py-2 border-b border-[#1e3a5f]/30 flex items-center justify-between gap-2 shrink-0">
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

const KpiPill = ({ label, value, sub, positive, icon: Icon }) => (
  <div className="flex flex-col items-center gap-0.5 px-2 py-1.5 min-w-0">
    <div className="flex items-center gap-1">
      {Icon && <Icon size={11} className="text-gray-500" />}
      <span className="text-[10px] text-gray-500 uppercase tracking-wider whitespace-nowrap">{label}</span>
    </div>
    <span className={clsx(
      'text-sm font-bold whitespace-nowrap',
      positive === true && 'text-emerald-400',
      positive === false && 'text-red-400',
      positive === undefined && 'text-white'
    )}>
      {value}
    </span>
    {sub && <span className="text-[10px] text-gray-500">{sub}</span>}
  </div>
);

const GradeCircle = ({ grade, label, size = 'lg' }) => {
  const sz = size === 'lg' ? 'w-16 h-16 text-2xl' : 'w-10 h-10 text-base';
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

const chartTooltipStyle = {
  contentStyle: {
    background: '#0d1b2a',
    border: '1px solid rgba(30,58,95,0.5)',
    borderRadius: 8,
    fontSize: 11,
    color: '#e2e8f0',
  },
  cursor: { stroke: 'rgba(6,182,212,0.3)' },
};

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
  const trades = useMemo(() => {
    const raw = tradesData?.trades || FALLBACK_TRADES;
    const sorted = [...raw].sort((a, b) => {
      const av = a[tradeSort.key], bv = b[tradeSort.key];
      if (typeof av === 'string') return tradeSort.dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      return tradeSort.dir === 'asc' ? av - bv : bv - av;
    });
    return sorted;
  }, [tradesData, tradeSort]);
  const rollingRisk = useMemo(() => perfData?.rollingRisk || FALLBACK_ROLLING_RISK, [perfData]);
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

  // Returns Heatmap Calendar placeholder
  const returnsCalendar = useMemo(() => {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return months.map(m => ({
      month: m,
      value: (Math.random() * 8 - 2).toFixed(1),
    }));
  }, []);

  return (
    <div className="h-full flex flex-col overflow-auto bg-[#060e1a]">
      {/* ─── HEADER ────────────────────────────────────────────── */}
      <div className="px-4 py-3 flex items-center justify-between border-b border-[#1e3a5f]/30 shrink-0">
        <h1 className="text-lg font-bold text-white tracking-tight">Performance Analytics</h1>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-[#0a1628] border border-emerald-500/30 rounded-full px-3 py-1">
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center text-[10px] font-bold text-white">
              {kpi.grade}
            </div>
            <span className="text-xs text-emerald-400 font-medium">Trading Grade</span>
          </div>
        </div>
      </div>

      {/* ─── KPI STRIP ─────────────────────────────────────────── */}
      <div className="px-4 py-2 flex items-center gap-1 overflow-x-auto border-b border-[#1e3a5f]/20 shrink-0 bg-[#070f1c]">
        <KpiPill label="Total Trades" value={kpi.totalTrades} icon={BarChart3} />
        <div className="w-px h-8 bg-[#1e3a5f]/30" />
        <KpiPill label="Net P&L" value={`+$${kpi.netPnl.toLocaleString()}`} positive={kpi.netPnl > 0} icon={TrendingUp} />
        <div className="w-px h-8 bg-[#1e3a5f]/30" />
        <KpiPill label="Win Rate" value={`${kpi.winRate}%`} positive={kpi.winRate > 50} icon={Target} />
        <div className="w-px h-8 bg-[#1e3a5f]/30" />
        <KpiPill label="Avg Win" value={`$${kpi.avgWin}`} positive icon={ArrowUpRight} />
        <div className="w-px h-8 bg-[#1e3a5f]/30" />
        <KpiPill label="Avg Loss" value={`-$${Math.abs(kpi.avgLoss)}`} positive={false} icon={ArrowDownRight} />
        <div className="w-px h-8 bg-[#1e3a5f]/30" />
        <KpiPill label="Profit Factor" value={kpi.profitFactor} positive={kpi.profitFactor > 1} icon={Zap} />
        <div className="w-px h-8 bg-[#1e3a5f]/30" />
        <KpiPill label="Max DD" value={`$${kpi.maxDd.toLocaleString()} / ${kpi.maxDdPct}%`} positive={false} icon={TrendingDown} />
        <div className="w-px h-8 bg-[#1e3a5f]/30" />
        <KpiPill label="Sharpe" value={kpi.sharpe} positive={kpi.sharpe > 1} icon={Activity} />
        <div className="w-px h-8 bg-[#1e3a5f]/30" />
        <KpiPill label="Expectancy" value={`$${kpi.expectancy}`} positive={kpi.expectancy > 0} icon={Crosshair} />
        <div className="w-px h-8 bg-[#1e3a5f]/30" />
        <KpiPill label="R:R" value={`${kpi.riskReward}:1`} icon={Shield} />
      </div>

      {/* ─── CONTENT GRID ──────────────────────────────────────── */}
      <div className="flex-1 p-3 space-y-3 min-h-0 overflow-auto">

        {/* ══ ROW 1 ════════════════════════════════════════════ */}
        <div className="grid grid-cols-12 gap-3" style={{ minHeight: 280 }}>

          {/* Risk Cockpit */}
          <Panel title="Risk Cockpit" icon={Shield} className="col-span-3">
            <div className="flex flex-col items-center gap-3 h-full">
              <GradeCircle grade={kpi.grade} label={kpi.gradeLabel} />
              <div className="grid grid-cols-3 gap-3 w-full">
                <div className="text-center">
                  <div className="text-[10px] text-gray-500 mb-0.5">Sharpe</div>
                  <div className="text-sm font-bold text-cyan-400">{kpi.sharpe}</div>
                </div>
                <div className="text-center">
                  <div className="text-[10px] text-gray-500 mb-0.5">Sortino</div>
                  <div className="text-sm font-bold text-cyan-400">{kpi.sortino}</div>
                </div>
                <div className="text-center">
                  <div className="text-[10px] text-gray-500 mb-0.5">Calmar</div>
                  <div className="text-sm font-bold text-cyan-400">{kpi.calmar}</div>
                </div>
              </div>
              <div className="w-full mt-1">
                <ProgressBar
                  label="Kelly Criterion"
                  value={kpi.kellyPct}
                  color="bg-emerald-500"
                />
              </div>
              {/* Returns Heatmap Calendar */}
              <div className="w-full mt-1">
                <div className="text-[10px] text-gray-500 mb-1">Returns Heatmap Calendar</div>
                <div className="grid grid-cols-6 gap-1">
                  {returnsCalendar.map((m) => (
                    <div
                      key={m.month}
                      className={clsx(
                        'text-center rounded px-1 py-0.5 text-[9px] font-medium',
                        parseFloat(m.value) >= 3 ? 'bg-emerald-600/50 text-emerald-300' :
                        parseFloat(m.value) >= 0 ? 'bg-emerald-900/30 text-emerald-400' :
                        'bg-red-900/30 text-red-400'
                      )}
                    >
                      <div>{m.month}</div>
                      <div>{m.value}%</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Panel>

          {/* Equity + Drawdown */}
          <Panel title="Equity + Drawdown" icon={TrendingUp} className="col-span-5">
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
                <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#6b7280' }} interval="preserveStartEnd" />
                <YAxis yAxisId="eq" tick={{ fontSize: 9, fill: '#6b7280' }} tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} />
                <YAxis yAxisId="dd" orientation="right" tick={{ fontSize: 9, fill: '#6b7280' }} tickFormatter={v => `${v}%`} />
                <Tooltip {...chartTooltipStyle} />
                <Area yAxisId="eq" type="monotone" dataKey="equity" stroke="#10b981" strokeWidth={2} fill="url(#eqGrad)" />
                <Area yAxisId="dd" type="monotone" dataKey="drawdown" stroke="#ef4444" strokeWidth={1} fill="url(#ddGrad)" />
              </ComposedChart>
            </ResponsiveContainer>
          </Panel>

          {/* AI + Rolling Risk & Attribution + Agent ELO */}
          <div className="col-span-4 flex flex-col gap-3">
            {/* AI + Rolling Risk */}
            <Panel title="AI + Rolling Risk" icon={Brain} className="flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={rollingRisk} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,58,95,0.2)" />
                  <XAxis dataKey="date" tick={{ fontSize: 8, fill: '#6b7280' }} interval={4} />
                  <YAxis tick={{ fontSize: 8, fill: '#6b7280' }} />
                  <Tooltip {...chartTooltipStyle} />
                  <Bar dataKey="rollingVol" fill="#06b6d4" opacity={0.4} radius={[2, 2, 0, 0]} />
                  <Line type="monotone" dataKey="rollingSharpe" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </Panel>

            {/* Attribution + Agent ELO */}
            <Panel title="Attribution + Agent ELO" icon={Award} className="flex-1">
              <div className="space-y-1.5">
                {agents.slice(0, 4).map((a) => (
                  <div key={a.name} className="flex items-center gap-2">
                    <span className="text-[10px] text-gray-400 w-20 truncate">{a.name}</span>
                    <div className="flex-1 h-3 bg-gray-800/60 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${a.score}%`, backgroundColor: a.color }}
                      />
                    </div>
                    <span className="text-[10px] text-gray-300 w-6 text-right">{a.score}</span>
                  </div>
                ))}
              </div>
            </Panel>
          </div>
        </div>

        {/* ══ ROW 2 ════════════════════════════════════════════ */}
        <div className="grid grid-cols-12 gap-3" style={{ minHeight: 240 }}>

          {/* Agent Attribution Leaderboard */}
          <Panel title="Agent Attribution Leaderboard" icon={Star} className="col-span-3">
            <div className="space-y-2">
              {agents.map((a) => (
                <div key={a.name}>
                  <div className="flex items-center justify-between mb-0.5">
                    <div className="flex items-center gap-1.5">
                      <div className="w-2 h-2 rounded-full" style={{ backgroundColor: a.color }} />
                      <span className="text-[11px] text-gray-300">{a.name}</span>
                    </div>
                    <span className="text-[10px] text-gray-400">{a.elo} ELO</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-gray-800/60 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{ width: `${(a.pnl / 30000) * 100}%`, backgroundColor: a.color }}
                      />
                    </div>
                    <span className="text-[10px] text-emerald-400 w-14 text-right">${(a.pnl / 1000).toFixed(1)}k</span>
                  </div>
                  <div className="flex gap-3 mt-0.5">
                    <span className="text-[9px] text-gray-500">{a.trades} trades</span>
                    <span className="text-[9px] text-gray-500">{a.winRate}% win</span>
                  </div>
                </div>
              ))}
            </div>
          </Panel>

          {/* Risk/Reward + Expectancy */}
          <Panel title="Risk/Reward + Expectancy" icon={Crosshair} className="col-span-4">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={rrExpect} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,58,95,0.2)" />
                <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#6b7280' }} />
                <YAxis yAxisId="rr" tick={{ fontSize: 9, fill: '#6b7280' }} />
                <YAxis yAxisId="exp" orientation="right" tick={{ fontSize: 9, fill: '#6b7280' }} />
                <Tooltip {...chartTooltipStyle} />
                <Bar yAxisId="rr" dataKey="rr" fill="#06b6d4" radius={[3, 3, 0, 0]} opacity={0.7} name="R:R" />
                <Line yAxisId="exp" type="monotone" dataKey="expectancy" stroke="#10b981" strokeWidth={2} dot={{ r: 3, fill: '#10b981' }} name="Expectancy" />
              </ComposedChart>
            </ResponsiveContainer>
          </Panel>

          {/* Enhanced Trades Table */}
          <Panel title="Enhanced Trades Table" icon={BarChart3} className="col-span-5">
            <div className="overflow-auto h-full">
              <table className="w-full text-[10px]">
                <thead>
                  <tr className="border-b border-[#1e3a5f]/30">
                    {['date', 'symbol', 'side', 'entry', 'exit', 'pnl', 'rr', 'status'].map((col) => (
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
                  {trades.map((t) => (
                    <tr key={t.id} className="border-b border-[#1e3a5f]/15 hover:bg-[#0d1f35]/50 transition-colors">
                      <td className="py-1 px-1.5 text-gray-400">{t.date}</td>
                      <td className="py-1 px-1.5 text-white font-medium">{t.symbol}</td>
                      <td className="py-1 px-1.5">
                        <span className={clsx(
                          'px-1.5 py-0.5 rounded text-[9px] font-medium',
                          t.side === 'Long' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'
                        )}>
                          {t.side}
                        </span>
                      </td>
                      <td className="py-1 px-1.5 text-gray-300">${t.entry}</td>
                      <td className="py-1 px-1.5 text-gray-300">${t.exit}</td>
                      <td className={clsx('py-1 px-1.5 font-medium', t.pnl >= 0 ? 'text-emerald-400' : 'text-red-400')}>
                        {t.pnl >= 0 ? '+' : ''}{t.pnl.toLocaleString()}
                      </td>
                      <td className="py-1 px-1.5 text-gray-300">{t.rr}</td>
                      <td className="py-1 px-1.5">
                        <span className={clsx(
                          'px-1.5 py-0.5 rounded text-[9px] font-medium',
                          t.status === 'Won' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'
                        )}>
                          {t.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>

        {/* ══ ROW 3 ════════════════════════════════════════════ */}
        <div className="grid grid-cols-12 gap-3" style={{ minHeight: 220 }}>

          {/* ML & Flywheel Engine */}
          <Panel title="ML & Flywheel Engine" icon={Cpu} className="col-span-3">
            <div className="space-y-3">
              {/* ML Model Accuracy Trend */}
              <div>
                <div className="text-[10px] text-gray-500 mb-1">ML Model Accuracy Trend</div>
                <div className="h-14">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={ml.accuracyTrend} margin={{ top: 2, right: 2, left: -20, bottom: 0 }}>
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
              {/* Staged Inferences */}
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-gray-400">Staged Inferences</span>
                <span className="text-xs font-bold text-violet-400">{ml.stagedInferences}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-gray-400">Total Inferences</span>
                <span className="text-xs font-bold text-gray-300">{ml.totalInferences}</span>
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
              {/* Risk Shield Status */}
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-gray-400">Risk Shield Status</span>
                <div className="flex items-center gap-1.5">
                  <StatusDot status={riskExp.shieldStatus} />
                  <span className="text-[10px] text-emerald-400 font-medium">{riskExp.shieldStatus}</span>
                </div>
              </div>
              {/* Risk History mini chart */}
              <div>
                <div className="text-[10px] text-gray-500 mb-1">Risk History</div>
                <div className="h-12">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={riskExp.riskHistory} margin={{ top: 2, right: 2, left: -20, bottom: 0 }}>
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
              {/* VaR Gauges */}
              <div className="text-[10px] text-gray-500 mb-1">VaR Gauges</div>
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-[#0d1b2a] rounded p-2 text-center">
                  <div className="text-[9px] text-gray-500">Daily VaR</div>
                  <div className="text-sm font-bold text-amber-400">{riskExp.varDaily}%</div>
                </div>
                <div className="bg-[#0d1b2a] rounded p-2 text-center">
                  <div className="text-[9px] text-gray-500">Weekly VaR</div>
                  <div className="text-sm font-bold text-amber-400">{riskExp.varWeekly}%</div>
                </div>
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
                <div className="bg-[#0d1b2a] rounded-lg p-2 space-y-2">
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
                  {strategy.activeStrategies.map((s, i) => (
                    <div key={s} className="flex items-center gap-2 bg-[#0d1b2a] rounded px-2 py-1.5">
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

      {/* ─── FOOTER ────────────────────────────────────────────── */}
      <div className="px-4 py-2 border-t border-[#1e3a5f]/30 flex items-center justify-between text-[10px] text-gray-600 shrink-0 bg-[#060e1a]">
        <span>Embodier Trader &gt; Performance Analytics v2.5</span>
        <span>{new Date().toLocaleString()}</span>
      </div>
    </div>
  );
}
