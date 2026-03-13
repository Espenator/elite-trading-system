import React, { useMemo, useState, useRef, useCallback } from 'react';
import {
  TrendingUp, TrendingDown, Activity, Shield,
  Target, Zap, BarChart3, Brain,
  ArrowUpRight, ArrowDownRight, ChevronDown, ChevronRight,
  Award, Cpu, CheckCircle, Crosshair, Star,
  Settings, Download, RefreshCw, Search, Maximize2, X, Filter
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, ComposedChart,
  Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import { useApi } from '../hooks/useApi';
import clsx from 'clsx';
import { TradingGradeHero, ReturnsHeatmapCalendar, ConcentricAIDial } from '../components/dashboard/PerformanceWidgets';

// Period options for API refetch (backend may accept ?range=)
const PERIODS = [
  { id: '1D', label: '1D' },
  { id: '5D', label: '5D' },
  { id: '1M', label: '1M' },
  { id: '3M', label: '3M' },
  { id: '1Y', label: '1Y' },
];

// Stable palette for agent attribution (no mock data — index-based)
const AGENT_PALETTE = ['#F59E0B', '#06B6D4', '#10b981', '#8B5CF6', '#EF4444', '#94a3b8'];

const rankColors = ['bg-emerald-500', 'bg-cyan-500', 'bg-violet-500', 'bg-amber-500', 'bg-rose-500'];

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

function formatNull(v) {
  if (v === null || v === undefined) return '—';
  return v;
}

/** Mini sparkline — uses real data or nothing */
const MiniSparkline = ({ data = [], positive = true, height = 20, width = 48 }) => {
  const d = Array.isArray(data) && data.length ? data : [];
  if (d.length === 0) {
    return (
      <svg width={width} height={height} className="shrink-0 opacity-40">
        <line x1={2} y1={height / 2} x2={width - 2} y2={height / 2} stroke="#6b7280" strokeWidth="1" />
      </svg>
    );
  }
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
          typeof change === 'number' && change < 0 ? 'text-red-400' : 'text-gray-500'
        )}>
          {change != null ? `${change >= 0 ? '+' : ''}${change}%` : sub}
        </span>
      )}
    </div>
  </div>
);

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
        {showPct && <span className="text-[10px] text-gray-300">{formatNull(value)}%</span>}
      </div>
    )}
    <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
      <div
        className={clsx('h-full rounded-full transition-all', color)}
        style={{ width: `${Math.min((Number(value) || 0) / max * 100, 100)}%` }}
      />
    </div>
  </div>
);

const VarGauge = ({ label, value, max = 10, color = '#f59e0b' }) => {
  const pct = Math.min((Number(value) || 0) / max, 1);
  const angle = pct * 180;
  const r = 36;
  const cx = 50;
  const cy = 48;
  const rad = (angle * Math.PI) / 180;
  const startX = cx - r;
  const startY = cy;
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
          {formatNull(value)}%
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

/** Skeleton placeholder for charts while loading */
const ChartSkeleton = ({ height = 120 }) => (
  <div className="w-full animate-pulse rounded bg-gray-800/50 flex items-end gap-0.5" style={{ height }}>
    {Array.from({ length: 12 }).map((_, i) => (
      <div key={i} className="flex-1 bg-gray-700/50 rounded-t" style={{ height: `${30 + (i % 5) * 12}%` }} />
    ))}
  </div>
);

// ─── MAIN COMPONENT ──────────────────────────────────────────────────────────

export default function PerformanceAnalytics() {
  const [range, setRange] = useState('1M');
  const [agentFilter, setAgentFilter] = useState(new Set()); // empty = show all
  const [tradeSort, setTradeSort] = useState({ key: 'date', dir: 'desc' });
  const [expandedAgent, setExpandedAgent] = useState(null);
  const [heatmapSelectedDay, setHeatmapSelectedDay] = useState(null); // { year, month }
  const riskCockpitRef = useRef(null);
  const equityRef = useRef(null);
  const attributionRef = useRef(null);
  const tradesTableRef = useRef(null);

  const query = useMemo(() => (range ? `?range=${range}` : ''), [range]);

  const { data: perfData, loading: perfLoading, refetch: refetchPerf } = useApi('performance', {
    endpointOverride: `/performance${query}`,
  });
  const { data: equityResponse, loading: equityLoading } = useApi('performanceEquity', {
    endpointOverride: `/performance/equity${query}`,
  });
  const { data: tradesData } = useApi('performanceTrades');
  const { data: flywheelData } = useApi('flywheel');
  const { data: riskData } = useApi('riskScore');
  const { data: agentsData } = useApi('agents');

  const loading = perfLoading || equityLoading;

  // KPI from API only — "—" when null
  const kpi = useMemo(() => {
    const raw = perfData?.kpi ?? perfData ?? {};
    return {
      totalTrades: raw.totalTrades ?? raw.total_trades,
      netPnl: raw.netPnl ?? raw.net_pnl,
      winRate: raw.winRate ?? raw.win_rate,
      avgWin: raw.avgWin ?? raw.avg_win,
      avgLoss: raw.avgLoss ?? raw.avg_loss,
      profitFactor: raw.profitFactor ?? raw.profit_factor,
      sharpe: raw.sharpe ?? raw.sharpeRatio,
      sortino: raw.sortino,
      calmar: raw.calmar,
      maxDd: raw.maxDrawdown ?? raw.max_drawdown,
      max_dd_pct: raw.max_drawdown_pct,
      expectancy: raw.expectancy,
      riskReward: raw.riskReward ?? raw.risk_reward_ratio,
      grade: raw.trading_grade ?? raw.grade,
      score: raw.score,
      netPnlChg: raw.netPnlChg,
      winRateChg: raw.winRateChg,
      avgWinChg: raw.avgWinChg,
      avgLossChg: raw.avgLossChg,
    };
  }, [perfData]);

  // Equity curve from performance or dedicated equity endpoint — no fallback data
  const equityData = useMemo(() => {
    const points = equityResponse?.points ?? equityResponse?.equity;
    const curve = perfData?.equityCurve ?? perfData?.equity ?? equityResponse?.equity_curve ?? equityResponse?.equity;
    if (Array.isArray(points) && points.length) {
      return points.map((p, i) => ({
        date: p.date ?? p.time ?? String(i),
        equity: p.equity ?? p.value ?? 0,
        drawdown: p.drawdown ?? null,
      }));
    }
    if (Array.isArray(curve) && curve.length) {
      return curve.map((c, i) => ({
        date: c.time ?? c.date ?? String(i),
        equity: c.value ?? c.equity ?? 0,
        drawdown: null,
      }));
    }
    return [];
  }, [perfData, equityResponse]);

  // Agents from API only; filter by agentFilter when non-empty
  const agentsRaw = useMemo(() => agentsData?.leaderboard ?? [], [agentsData]);
  const agents = useMemo(() => {
    let list = Array.isArray(agentsRaw) ? agentsRaw : [];
    if (agentFilter.size > 0) {
      list = list.filter((a) => agentFilter.has(a.name ?? a.agent_name));
    }
    return list.map((a, idx) => ({
      ...a,
      name: a.name ?? a.agent_name ?? '—',
      elo: a.elo ?? a.score,
      change: a.change ?? 0,
      changePct: a.changePct ?? a.change_pct ?? 0,
      contribution: a.contribution ?? a.contrib ?? 0,
      winRate: a.winRate ?? a.win_rate ?? 0,
      color: AGENT_PALETTE[idx % AGENT_PALETTE.length],
    }));
  }, [agentsRaw, agentFilter]);

  const pnlBySymbol = useMemo(() => perfData?.pnlBySymbol ?? [], [perfData]);
  const trades = useMemo(() => {
    const raw = tradesData?.trades ?? [];
    const sorted = [...raw].sort((a, b) => {
      const key = tradeSort.key === 'date' ? 'closed_at' : tradeSort.key;
      const av = a[tradeSort.key] ?? a[key];
      const bv = b[tradeSort.key] ?? b[key];
      if (av == null && bv == null) return 0;
      if (typeof av === 'string' && typeof bv === 'string') return tradeSort.dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      const aNum = Number(av);
      const bNum = Number(bv);
      return tradeSort.dir === 'asc' ? (aNum - bNum) : (bNum - aNum);
    });
    return sorted;
  }, [tradesData, tradeSort]);

  const rollingRisk = useMemo(() => {
    const raw = perfData?.rollingRisk ?? [];
    return raw.map((r, i) => ({
      date: r.date ?? r.x ?? i,
      y: r.y ?? r.rollingSharpe ?? r.value ?? 0,
    }));
  }, [perfData]);

  const rrExpect = useMemo(() => {
    const raw = perfData?.rrExpectancy ?? perfData?.rrExpect ?? [];
    if (Array.isArray(raw) && raw.length) return raw;
    const pf = kpi.profitFactor != null ? Number(kpi.profitFactor) : null;
    const exp = kpi.expectancy != null ? Number(kpi.expectancy) : null;
    if (pf != null || exp != null) return [{ name: 'R:R', rr: pf ?? 0, expectancy: exp ?? 0 }];
    return [];
  }, [perfData, kpi.profitFactor, kpi.expectancy]);

  const ml = useMemo(() => ({
    accuracyTrend: flywheelData?.accuracyTrend ?? [],
    stagedInferences: flywheelData?.stagedInferences ?? null,
    totalInferences: flywheelData?.totalInferences ?? null,
    pipelineHealth: flywheelData?.pipelineHealth ?? null,
    flywheelCycles: flywheelData?.flywheel_cycles ?? flywheelData?.flywheelCycles ?? null,
  }), [flywheelData]);

  const riskExp = useMemo(() => ({
    shieldStatus: riskData?.shieldStatus ?? riskData?.status ?? null,
    varDaily: riskData?.varDaily ?? riskData?.var_1d_95 ?? null,
    varWeekly: riskData?.varWeekly ?? null,
    currentExposure: riskData?.currentExposure ?? riskData?.exposure_pct ?? null,
    maxExposure: riskData?.maxExposure ?? 100,
    riskHistory: riskData?.riskHistory ?? riskData?.risk_history ?? [],
  }), [riskData]);

  const strategy = useMemo(() => ({
    signalHitRate: perfData?.strategy?.signalHitRate ?? null,
    totalSignals: perfData?.strategy?.totalSignals ?? null,
    activeStrategies: perfData?.strategy?.activeStrategies ?? [],
    sentiment: perfData?.strategy?.sentiment ?? null,
    regime: perfData?.strategy?.regime ?? null,
  }), [perfData]);

  const returnsCalendar = useMemo(() => perfData?.returnsCalendar ?? [], [perfData]);

  const handleSort = useCallback((key) => {
    setTradeSort((prev) => ({
      key,
      dir: prev.key === key && prev.dir === 'desc' ? 'asc' : 'desc',
    }));
  }, []);

  const scrollToSection = useCallback((ref) => {
    ref?.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  const exportReport = useCallback(() => {
    const rows = [
      ['Metric', 'Value'],
      ['Total Trades', formatNull(kpi.totalTrades)],
      ['Net P&L', kpi.netPnl != null ? Number(kpi.netPnl).toFixed(2) : '—'],
      ['Win Rate %', kpi.winRate != null ? Number(kpi.winRate).toFixed(1) : '—'],
      ['Profit Factor', formatNull(kpi.profitFactor)],
      ['Sharpe', formatNull(kpi.sharpe)],
      ['Max Drawdown', formatNull(kpi.maxDd)],
      [''],
      ['Date', 'Symbol', 'Side', 'Qty', 'Entry', 'Exit', 'P&L'],
      ...trades.slice(0, 500).map((t) => [
        t.date ?? t.closed_at ?? '—',
        t.symbol ?? '—',
        t.side ?? '—',
        formatNull(t.qty ?? t.quantity),
        t.entry != null ? Number(t.entry).toFixed(2) : '—',
        t.exit != null ? Number(t.exit).toFixed(2) : '—',
        t.pnl != null ? Number(t.pnl).toFixed(2) : '—',
      ]),
    ];
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `performance-report-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [kpi, trades]);

  const toggleAgentFilter = useCallback((name) => {
    setAgentFilter((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }, []);

  const tradesForHeatmapDay = useMemo(() => {
    if (!heatmapSelectedDay || !trades.length) return [];
    const { year, month } = heatmapSelectedDay;
    const prefix = `${year}-${String(month).padStart(2, '0')}`;
    return trades.filter((t) => {
      const d = t.closed_at ?? t.date ?? '';
      const s = String(d);
      return s.startsWith(prefix) || s.includes(`/${month}/${year}`);
    });
  }, [heatmapSelectedDay, trades]);

  const tradeCols = ['date', 'symbol', 'side', 'qty', 'entry', 'exit', 'pnl'];

  return (
    <div className="h-full flex flex-col overflow-auto bg-[#0a0e1a]">
      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between border-b border-[rgba(42,52,68,0.5)] shrink-0 bg-[#0a0e1a]">
        <div className="flex-1 flex items-center gap-2">
          {PERIODS.map((p) => (
            <button
              key={p.id}
              onClick={() => setRange(p.id)}
              className={clsx(
                'px-2 py-1 rounded text-xs font-medium transition-colors',
                range === p.id
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                  : 'text-gray-400 hover:text-white border border-transparent'
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
        <h1 className="text-xl font-bold text-white tracking-tight text-center flex-1">Performance Analytics</h1>
        <div className="flex-1 flex justify-end items-center gap-2">
          <button
            onClick={exportReport}
            className="flex items-center gap-2 bg-[#111827] hover:bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 transition-colors"
          >
            <Download size={14} />
            Export Report
          </button>
          <button
            onClick={() => { refetchPerf?.(); }}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 border border-emerald-500/40 rounded-lg px-4 py-2 transition-colors"
            title="Refetch performance"
          >
            <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-lg font-bold text-white">
              {formatNull(kpi.grade) || '—'}
            </div>
            <span className="text-sm font-semibold text-white">Trading Grade</span>
          </button>
        </div>
      </div>

      {/* KPI strip — all from API, "—" when null */}
      <div className="px-4 py-2 flex items-center gap-2 overflow-x-auto border-b border-[rgba(42,52,68,0.5)] shrink-0 bg-[#0a0e1a]">
        <KpiPill label="Total Trades" value={formatNull(kpi.totalTrades)} icon={BarChart3} sparkData={[]} />
        <KpiPill
          label="Net P&L"
          value={kpi.netPnl != null ? `${(kpi.netPnl >= 0 ? '+' : '')}$${Number(kpi.netPnl).toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '—'}
          positive={kpi.netPnl != null ? kpi.netPnl > 0 : undefined}
          change={kpi.netPnlChg}
          icon={TrendingUp}
          sparkData={[]}
        />
        <KpiPill
          label="Win Rate"
          value={kpi.winRate != null ? `${Number(kpi.winRate).toFixed(1)}%` : '—'}
          positive={kpi.winRate != null ? kpi.winRate > 50 : undefined}
          change={kpi.winRateChg}
          icon={Target}
          sparkData={[]}
        />
        <KpiPill label="Avg Win" value={kpi.avgWin != null ? `$${Number(kpi.avgWin).toFixed(2)}` : '—'} positive icon={ArrowUpRight} sparkData={[]} />
        <KpiPill label="Avg Loss" value={kpi.avgLoss != null ? `-$${Math.abs(Number(kpi.avgLoss)).toFixed(2)}` : '—'} positive={false} icon={ArrowDownRight} sparkData={[]} />
        <KpiPill label="Profit Factor" value={formatNull(kpi.profitFactor)} positive={kpi.profitFactor != null ? kpi.profitFactor > 1 : undefined} icon={Zap} sparkData={[]} />
        <KpiPill
          label="Max DD"
          value={kpi.maxDd != null || kpi.max_dd_pct != null ? `-${Math.abs(Number(kpi.maxDd ?? 0)).toLocaleString()} / ${kpi.max_dd_pct != null ? `${Number(kpi.max_dd_pct)}%` : '—'}` : '—'}
          positive={false}
          icon={TrendingDown}
          sparkData={[]}
        />
        <KpiPill label="Sharpe" value={formatNull(kpi.sharpe)} positive={kpi.sharpe != null ? kpi.sharpe > 1 : undefined} icon={Activity} sparkData={[]} />
        <KpiPill label="Expectancy" value={kpi.expectancy != null ? `$${Number(kpi.expectancy).toFixed(2)}` : '—'} positive={kpi.expectancy != null ? kpi.expectancy > 0 : undefined} icon={Crosshair} sparkData={[]} />
        <KpiPill label="R:R" value={kpi.riskReward != null ? `${kpi.riskReward}:1` : '—'} positive icon={Shield} sparkData={[]} />
      </div>

      {/* Content: dense 3-col 20 / 50 / 30 (Aurora) */}
      <div className="flex-1 p-3 min-h-0 overflow-auto">
        <div className="grid gap-3" style={{ gridTemplateColumns: '2fr 5fr 3fr' }}>

          {/* ─── LEFT 20% ───────────────────────────────────────────────────── */}
          <div className="flex flex-col gap-3">
            <div ref={riskCockpitRef}>
            <Panel title="Risk Cockpit" icon={Shield} className="min-h-[200px]">
              <div className="flex flex-col gap-2 h-full">
                <div className="flex flex-col items-center gap-0.5">
                  <div className="text-[10px] text-gray-500 uppercase tracking-wider">Trading Grade</div>
                  <TradingGradeHero grade={kpi.grade || '—'} score={kpi.score != null ? Number(kpi.score) : 0} size={90} />
                  <div className="text-[10px] font-semibold text-emerald-400">Grade</div>
                </div>
                <div className="grid grid-cols-3 gap-1 w-full">
                  {['Sharpe', 'Sortino', 'Calmar'].map((label, i) => (
                    <button
                      key={label}
                      type="button"
                      onClick={() => scrollToSection(riskCockpitRef)}
                      className="text-center bg-[#0a0e1a] rounded p-1.5 hover:ring-1 hover:ring-cyan-500/40 transition-colors"
                    >
                      <div className="text-[9px] text-gray-500">{label}</div>
                      <div className="text-sm font-bold text-white">{formatNull([kpi.sharpe, kpi.sortino, kpi.calmar][i])}</div>
                    </button>
                  ))}
                </div>
                <div className="w-full">
                  <div className="text-[10px] text-gray-500 mb-1">Kelly / Risk</div>
                  <div className="flex h-4 rounded overflow-hidden bg-gray-800">
                    <div className="flex-1 bg-emerald-500/80 flex items-center justify-center text-[9px] font-medium text-white">
                      {kpi.avgWin != null ? `$${Number(kpi.avgWin).toFixed(2)}` : '—'}
                    </div>
                    <div className="w-16 bg-red-500/80 flex items-center justify-center text-[9px] font-medium text-white">
                      {kpi.avgLoss != null ? `-$${Math.abs(Number(kpi.avgLoss)).toFixed(2)}` : '—'}
                    </div>
                  </div>
                </div>
                {rrExpect.length > 0 && (
                  <div className="flex-1 min-h-0">
                    <div className="text-[10px] text-gray-500 mb-1">Risk/Reward + Expectancy</div>
                    <div className="h-[70px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={rrExpect} margin={{ top: 2, right: 5, left: -15, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,58,95,0.2)" />
                          <XAxis dataKey="name" tick={{ fontSize: 8, fill: '#6b7280' }} />
                          <YAxis tick={{ fontSize: 8, fill: '#6b7280' }} />
                          <Tooltip {...chartTooltipStyle} />
                          <Bar dataKey="rr" fill="#00D9FF" radius={[2, 2, 0, 0]} opacity={0.7} name="R:R" />
                          <Line type="monotone" dataKey="expectancy" stroke="#10b981" strokeWidth={1.5} dot={false} name="Expectancy" />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}
              </div>
            </Panel>
            </div>

            <Panel title="Agent filter" icon={Filter} className="shrink-0">
              <p className="text-[10px] text-gray-500 mb-2">Toggle agents to include in attribution</p>
              <div className="flex flex-wrap gap-1 max-h-24 overflow-auto">
                {(agentsData?.leaderboard ?? []).slice(0, 12).map((a) => {
                  const name = a.name ?? a.agent_name ?? '—';
                  const on = agentFilter.size === 0 || agentFilter.has(name);
                  return (
                    <button
                      key={name}
                      type="button"
                      onClick={() => toggleAgentFilter(name)}
                      className={clsx(
                        'px-2 py-0.5 rounded text-[10px] border transition-colors',
                        on ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40' : 'bg-gray-800 text-gray-500 border-gray-700'
                      )}
                    >
                      {name}
                    </button>
                  );
                })}
              </div>
            </Panel>
          </div>

          {/* ─── CENTER 50% ────────────────────────────────────────────────── */}
          <div className="flex flex-col gap-3">
            <div ref={equityRef}>
            <Panel
              title="Equity + Drawdown"
              icon={TrendingUp}
              action={
                <div className="flex items-center gap-1">
                  <button className="p-1 text-gray-500 hover:text-cyan-400 transition-colors" title="Settings"><Settings size={12} /></button>
                  <button onClick={exportReport} className="p-1 text-gray-500 hover:text-cyan-400 transition-colors" title="Download"><Download size={12} /></button>
                  <button onClick={() => refetchPerf?.()} className="p-1 text-gray-500 hover:text-cyan-400 transition-colors" title="Refresh"><RefreshCw size={12} /></button>
                </div>
              }
            >
              <div className="h-[200px]">
                {loading ? (
                  <ChartSkeleton height={200} />
                ) : equityData.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-gray-500 text-sm">No equity data — connect data source</div>
                ) : (
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
                      <YAxis yAxisId="eq" tick={{ fontSize: 8, fill: '#6b7280' }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                      <YAxis yAxisId="dd" orientation="right" tick={{ fontSize: 8, fill: '#6b7280' }} tickFormatter={(v) => `${v}%`} />
                      <Tooltip {...chartTooltipStyle} />
                      <Area yAxisId="eq" type="monotone" dataKey="equity" stroke="#10b981" strokeWidth={2} fill="url(#eqGrad)" />
                      <Area yAxisId="dd" type="monotone" dataKey="drawdown" stroke="#ef4444" strokeWidth={1} fill="url(#ddGrad)" />
                    </ComposedChart>
                  </ResponsiveContainer>
                )}
              </div>
            </Panel>
            </div>

            <Panel title="AI + Rolling Risk" icon={Brain}>
              <div className="flex flex-col gap-3 h-full">
                <div className="flex flex-col items-center">
                  <ConcentricAIDial
                    metrics={[
                      { name: 'Outer', value: ml.pipelineHealth != null ? Number(ml.pipelineHealth) : 0, color: '#06B6D4' },
                      { name: 'Agent', value: kpi.score != null ? Number(kpi.score) : 0, color: '#10B981' },
                    ]}
                    centerLabel={kpi.score != null ? `${kpi.score}%` : '—'}
                  />
                </div>
                {rollingRisk.length > 0 && (
                  <div className="flex-1 min-h-0">
                    <div className="text-[10px] text-gray-500 mb-1">Rolling Risk Sharpe</div>
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
                          <YAxis tick={{ fontSize: 8, fill: '#6b7280' }} domain={[0, 1.5]} />
                          <Tooltip {...chartTooltipStyle} />
                          <Area type="monotone" dataKey="y" stroke="#06B6D4" fill="url(#rollingGrad)" strokeWidth={1.5} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}
              </div>
            </Panel>

            <div ref={attributionRef}>
            <Panel title="Attribution + Agent ELO" icon={Award}>
              <div className="flex flex-col gap-2 h-full">
                {pnlBySymbol.length > 0 && (
                  <div>
                    <div className="text-[10px] text-gray-500 mb-1">P&L By Symbol</div>
                    <div className="h-24">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={pnlBySymbol} layout="vertical" margin={{ top: 0, right: 5, left: 0, bottom: 0 }}>
                          <XAxis type="number" tick={{ fontSize: 8, fill: '#6b7280' }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                          <YAxis type="category" dataKey="symbol" width={36} tick={{ fontSize: 9, fill: '#9ca3af' }} />
                          <Bar dataKey="pnl" radius={[0, 2, 2, 0]}>
                            {pnlBySymbol.map((entry, i) => (
                              <Cell key={i} fill={(entry.pnl ?? 0) >= 0 ? '#10b981' : '#ef4444'} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}
                <div>
                  <div className="text-[10px] text-gray-500 mb-1">Agent Attribution</div>
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
                        <React.Fragment key={a.name}>
                          <tr
                            className="border-b border-gray-800/20 hover:bg-gray-900/30 cursor-pointer transition-colors"
                            onClick={() => setExpandedAgent(expandedAgent === a.name ? null : a.name)}
                          >
                            <td className="py-0.5">
                              <span className={clsx('inline-flex items-center justify-center w-4 h-4 rounded text-[8px] font-bold text-white', rankColors[idx] || 'bg-gray-600')}>{idx + 1}</span>
                            </td>
                            <td className="py-0.5 text-gray-300 flex items-center gap-1">
                              {expandedAgent === a.name ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
                              {a.name}
                            </td>
                            <td className="py-0.5 text-right text-white">{formatNull(a.elo)}</td>
                            <td className={clsx('py-0.5 text-right', (a.change ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400')}>
                              {(a.change ?? 0) >= 0 ? '+' : ''}{a.change} ({(a.changePct ?? 0) >= 0 ? '+' : ''}{formatNull(a.changePct)}%)
                            </td>
                            <td className="py-0.5 text-right text-gray-400">{formatNull(a.contribution)}%</td>
                            <td className="py-0.5 text-right text-gray-400">{formatNull(a.winRate)}%</td>
                          </tr>
                          {expandedAgent === a.name && (
                            <tr className="bg-gray-900/50 border-b border-gray-800/20">
                              <td colSpan={6} className="py-2 px-2 text-[10px] text-gray-400">
                                <div className="grid grid-cols-3 gap-2">
                                  <span>Accuracy by regime: {formatNull(a.accuracyByRegime ?? a.accuracy_by_regime)}</span>
                                  <span>Avg confidence: {formatNull(a.avgConfidence ?? a.avg_confidence)}</span>
                                  <span>Signal count: {formatNull(a.signalCount ?? a.signal_count)}</span>
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      ))}
                      {agents.length === 0 && (
                        <tr><td colSpan={6} className="py-2 text-center text-gray-500 text-[10px]">No agent data — use API</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
                <div className="flex-1 min-h-0">
                  <div className="text-[10px] text-gray-500 mb-1">Returns Heatmap</div>
                  <ReturnsHeatmapCalendar
                    data={returnsCalendar}
                    className="min-h-[60px]"
                    onCellClick={(year, month) => setHeatmapSelectedDay({ year, month })}
                  />
                </div>
              </div>
            </Panel>
            </div>
          </div>

          {/* ─── RIGHT 30% ───────────────────────────────────────────────────── */}
          <div className="flex flex-col gap-3">
            <Panel title="Grade & Stats" icon={Star}>
              <div className="space-y-2">
                <div className="flex items-center justify-center gap-2">
                  <TradingGradeHero grade={kpi.grade || '—'} score={kpi.score != null ? Number(kpi.score) : 0} size={70} />
                </div>
                <MetricRow label="Win %" value={kpi.winRate != null ? `${Number(kpi.winRate).toFixed(1)}%` : '—'} />
                <MetricRow label="Profit Factor" value={formatNull(kpi.profitFactor)} />
                <button type="button" onClick={() => scrollToSection(riskCockpitRef)} className="text-[10px] text-cyan-400 hover:underline">Scroll to Risk Cockpit →</button>
                <button type="button" onClick={() => scrollToSection(equityRef)} className="text-[10px] text-cyan-400 hover:underline block">Scroll to Equity →</button>
                <button type="button" onClick={() => scrollToSection(attributionRef)} className="text-[10px] text-cyan-400 hover:underline block">Scroll to Attribution →</button>
                <button type="button" onClick={() => scrollToSection(tradesTableRef)} className="text-[10px] text-cyan-400 hover:underline block">Scroll to Trades →</button>
              </div>
            </Panel>

            <Panel title="Risk Expanded" icon={Shield}>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-gray-400">Risk Shield</span>
                  <span className={clsx(
                    'px-2 py-0.5 text-[10px] font-bold rounded',
                    (riskExp.shieldStatus === 'ACTIVE' || riskExp.shieldStatus === 'Active') ? 'bg-emerald-500 text-white' : 'bg-gray-600 text-gray-300'
                  )}>
                    {formatNull(riskExp.shieldStatus)}
                  </span>
                </div>
                {riskExp.riskHistory?.length > 0 && (
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
                )}
                <div className="text-[10px] text-gray-500 mb-1">VaR Gauges</div>
                <div className="flex items-center justify-center gap-4">
                  <VarGauge label="Daily VaR" value={riskExp.varDaily} max={10} color="#f59e0b" />
                  <VarGauge label="Weekly VaR" value={riskExp.varWeekly} max={10} color="#ef4444" />
                </div>
                <ProgressBar label="Current Exposure" value={riskExp.currentExposure} max={riskExp.maxExposure || 100} color="bg-amber-500" />
              </div>
            </Panel>

            <div ref={tradesTableRef}>
            <Panel title="Enhanced Trades Table" icon={BarChart3} action={
              <div className="flex items-center gap-1">
                <button className="px-2 py-0.5 text-[10px] font-medium bg-cyan-500/20 text-cyan-400 rounded border border-cyan-500/40">TRADE LOG</button>
                <button className="p-1 text-gray-500 hover:text-cyan-400"><Search size={12} /></button>
                <button className="p-1 text-gray-500 hover:text-cyan-400"><Filter size={12} /></button>
              </div>
            }>
              <div className="overflow-auto max-h-[280px]">
                <table className="w-full text-[10px]">
                  <thead className="sticky top-0 bg-[#111827] z-10">
                    <tr className="border-b border-gray-800/50">
                      <th className="w-6 py-1 px-1 text-gray-500" />
                      {tradeCols.map((col) => (
                        <th
                          key={col}
                          onClick={() => handleSort(col === 'date' ? 'closed_at' : col)}
                          className="text-left py-1 px-1.5 text-gray-500 uppercase cursor-pointer hover:text-cyan-400 transition-colors whitespace-nowrap"
                        >
                          {col}
                          {tradeSort.key === col || (col === 'date' && tradeSort.key === 'closed_at') && (
                            <ChevronDown size={10} className={clsx('inline ml-0.5', tradeSort.dir === 'asc' && 'rotate-180')} />
                          )}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((t, i) => (
                      <tr key={t.id ?? i} className="border-b border-gray-800/20 hover:bg-gray-900/30">
                        <td className="py-1 px-1" />
                        <td className="py-1 px-1.5 text-gray-400">{t.date ?? t.closed_at ?? '—'}</td>
                        <td className="py-1 px-1.5 text-white font-medium">{t.symbol ?? '—'}</td>
                        <td className="py-1 px-1.5">
                          <span className={clsx(
                            'px-1.5 py-0.5 rounded text-[9px] font-medium',
                            (t.side === 'Long' || t.side === 'L' || t.side === 'BUY' || t.side === 'buy') ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'
                          )}>
                            {t.side === 'Long' || t.side === 'BUY' || t.side === 'buy' ? 'L' : t.side === 'Short' || t.side === 'SELL' || t.side === 'sell' ? 'H' : formatNull(t.side)}
                          </span>
                        </td>
                        <td className="py-1 px-1.5 text-gray-300">{formatNull(t.qty ?? t.quantity)}</td>
                        <td className="py-1 px-1.5 text-gray-300">{t.entry != null ? `$${Number(t.entry).toFixed(2)}` : '—'}</td>
                        <td className="py-1 px-1.5 text-gray-300">{t.exit != null ? `$${Number(t.exit).toFixed(2)}` : '—'}</td>
                        <td className={clsx('py-1 px-1.5 font-medium', (t.pnl ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400')}>
                          {t.pnl != null ? `${(t.pnl >= 0 ? '+' : '')}${Number(t.pnl).toLocaleString()}` : '—'}
                          {t.pnlPct != null && <span className="text-[9px] text-gray-500 ml-1">({(t.pnlPct >= 0 ? '+' : '')}{t.pnlPct}%)</span>}
                        </td>
                      </tr>
                    ))}
                    {trades.length === 0 && (
                      <tr><td colSpan={8} className="py-4 text-center text-gray-500 text-[10px]">No trades — connect data source</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </Panel>
            </div>

            {heatmapSelectedDay && (
              <Panel title={`Trades ${heatmapSelectedDay.year}-${String(heatmapSelectedDay.month).padStart(2, '0')}`} icon={BarChart3} action={<button onClick={() => setHeatmapSelectedDay(null)} className="p-1 text-gray-500 hover:text-white"><X size={14} /></button>}>
                <div className="max-h-40 overflow-auto text-[10px]">
                  {tradesForHeatmapDay.length === 0 ? (
                    <p className="text-gray-500">No trades for this period</p>
                  ) : (
                    <ul className="space-y-1">
                      {tradesForHeatmapDay.map((t, i) => (
                        <li key={i} className="flex justify-between gap-2">
                          <span>{t.symbol ?? '—'}</span>
                          <span>{t.side ?? '—'}</span>
                          <span className={clsx((t.pnl ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400')}>{t.pnl != null ? Number(t.pnl).toFixed(2) : '—'}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </Panel>
            )}
          </div>
        </div>
      </div>

      <footer className="px-4 py-2 border-t border-gray-800/50 flex items-center justify-between text-[10px] text-gray-500 shrink-0 bg-[#0a0e1a]">
        <span>Embodier Trader — Performance Analytics | Range: {range} | Trades: {trades.length} | No mock data</span>
      </footer>
    </div>
  );
}
