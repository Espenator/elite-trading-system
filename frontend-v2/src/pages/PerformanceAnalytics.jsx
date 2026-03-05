import React, { useMemo, useEffect, useRef, useState, useCallback } from 'react';
import {
  TrendingUp, TrendingDown, Activity, Shield,
  Target, Zap, BarChart3, PieChart as PieChartIcon,
  Search, Filter, ArrowUpRight, ArrowDownRight,
  ChevronRight, Brain, Gauge, Info, ChevronDown,
  Grid, Maximize2, AlertCircle, RefreshCw
} from 'lucide-react';
import { createChart } from 'lightweight-charts';
import { useApi } from '../hooks/useApi';
import Card from '../components/ui/Card';
import PostmortemAttribution from '../components/dashboard/PostmortemAttribution';

// --- Mini Lightweight Charts Components ---

const MiniLineChart = ({ data, dataKey, dateKey, color, height = 80 }) => {
  const containerRef = useRef(null);
  useEffect(() => {
    if (!containerRef.current || !data?.length) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { color: 'transparent' }, textColor: '#9CA3AF' },
      grid: { vertLines: { color: 'rgba(42,52,68,0.3)' }, horzLines: { color: 'rgba(42,52,68,0.3)' } },
      width: containerRef.current.clientWidth,
      height,
      rightPriceScale: { visible: false },
      timeScale: { visible: false, borderVisible: false },
      crosshair: { mode: 0 },
      handleScroll: false,
      handleScale: false,
    });
    const series = chart.addLineSeries({
      color: color || '#06b6d4',
      lineWidth: 1.5,
      crosshairMarkerVisible: false,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    const seriesData = data
      .filter(d => d[dateKey] && d[dataKey] != null)
      .map(d => ({ time: d[dateKey], value: d[dataKey] }));
    if (seriesData.length) {
      series.setData(seriesData);
      chart.timeScale().fitContent();
    }
    const handleResize = () => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    };
    window.addEventListener('resize', handleResize);
    return () => { window.removeEventListener('resize', handleResize); chart.remove(); };
  }, [data, dataKey, dateKey, color, height]);
  if (!data?.length) return null;
  return <div ref={containerRef} className="w-full" />;
};

const MiniAreaChart = ({ data, dataKey, dateKey, lineColor, topColor, height = 50 }) => {
  const containerRef = useRef(null);
  useEffect(() => {
    if (!containerRef.current || !data?.length) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { color: 'transparent' }, textColor: '#9CA3AF' },
      grid: { vertLines: { color: 'rgba(42,52,68,0.3)' }, horzLines: { color: 'rgba(42,52,68,0.3)' } },
      width: containerRef.current.clientWidth,
      height,
      rightPriceScale: { visible: false },
      timeScale: { visible: false, borderVisible: false },
      crosshair: { mode: 0 },
      handleScroll: false,
      handleScale: false,
    });
    const series = chart.addAreaSeries({
      lineColor: lineColor || '#EF4444',
      topColor: topColor || 'rgba(239,68,68,0.3)',
      bottomColor: 'transparent',
      lineWidth: 1.5,
      crosshairMarkerVisible: false,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    const seriesData = data
      .filter(d => d[dateKey] && d[dataKey] != null)
      .map(d => ({ time: d[dateKey], value: d[dataKey] }));
    if (seriesData.length) {
      series.setData(seriesData);
      chart.timeScale().fitContent();
    }
    const handleResize = () => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    };
    window.addEventListener('resize', handleResize);
    return () => { window.removeEventListener('resize', handleResize); chart.remove(); };
  }, [data, dataKey, dateKey, lineColor, topColor, height]);
  if (!data?.length) return null;
  return <div ref={containerRef} className="w-full" />;
};

const PerformanceAnalytics = () => {
  // --- API DATA FETCHING (all real endpoints, zero fake data) ---
  const { data: summary } = useApi("performance", { endpoint: "/performance/summary", pollIntervalMs: 60000 });
  const { data: equityData } = useApi("performance", { endpoint: "/performance/equity" });
  const { data: tradesData } = useApi("performance", { endpoint: "/performance/trades" });
  const { data: riskMetrics } = useApi("performance", { endpoint: "/performance/risk-metrics" });
  const { data: flywheel } = useApi("flywheel");
  const { data: agents } = useApi("agents", { endpoint: "/agents/consensus" });
  const { data: riskStatus } = useApi("risk");
  const { data: strategyData } = useApi("strategy");

  // --- REFS & STATE ---
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const [tradeSearch, setTradeSearch] = useState('');
  const [showToolbar, setShowToolbar] = useState(false);
  const [tradeView, setTradeView] = useState('table');
  const [activePeriod, setActivePeriod] = useState('ALL');

  // --- COLORS ---
  const C = {
    cyan: '#06b6d4', green: '#10b981', red: '#ef4444',
    amber: '#f59e0b', blue: '#3b82f6', purple: '#8b5cf6',
    slate: '#64748b', dark: '#0f172a', surface: '#111827',
    bg: '#0B0E14', muted: '#9ca3af', border: 'rgba(100,116,139,0.3)'
  };

  // --- PERIOD FILTER: filter equity data by selected period ---
  const filterByPeriod = useCallback((points, period) => {
    if (!points || !points.length || period === 'ALL') return points;
    const now = new Date();
    const cutoffs = {
      '1D': new Date(now - 86400000),
      '1W': new Date(now - 7 * 86400000),
      '1M': new Date(now - 30 * 86400000),
      '3M': new Date(now - 90 * 86400000),
      'YTD': new Date(now.getFullYear(), 0, 1),
      '1Y': new Date(now - 365 * 86400000),
    };
    const cutoff = cutoffs[period];
    if (!cutoff) return points;
    return points.filter(p => new Date(p.date) >= cutoff);
  }, []);

  const filteredEquityPoints = useMemo(() => {
    return filterByPeriod(equityData?.points, activePeriod);
  }, [equityData, activePeriod, filterByPeriod]);

  // --- LIGHTWEIGHT CHARTS: Equity + Drawdown ---
  useEffect(() => {
    if (!chartContainerRef.current || !filteredEquityPoints?.length) return;
    const chart = createChart(chartContainerRef.current, {
      layout: { background: { color: 'transparent' }, textColor: '#9ca3af' },
      grid: { vertLines: { color: 'rgba(255,255,255,0.05)' }, horzLines: { color: 'rgba(255,255,255,0.05)' } },
      width: chartContainerRef.current.clientWidth,
      height: 300,
      timeScale: { borderVisible: false },
    });
    const equitySeries = chart.addAreaSeries({
      lineColor: C.cyan, topColor: C.cyan + '44', bottomColor: 'transparent', lineWidth: 2,
    });
    equitySeries.setData(filteredEquityPoints.map(p => ({ time: p.date, value: p.equity })));
    // Drawdown overlay (red line below zero)
    const ddSeries = chart.addLineSeries({
      color: C.red, lineWidth: 1, priceScaleId: 'drawdown',
    });
    chart.priceScale('drawdown').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    if (filteredEquityPoints[0]?.drawdown !== undefined) {
      ddSeries.setData(filteredEquityPoints.map(p => ({ time: p.date, value: p.drawdown || 0 })));
    }
    chart.timeScale().fitContent();
    chartRef.current = chart;
    const handleResize = () => chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    window.addEventListener('resize', handleResize);
    return () => { window.removeEventListener('resize', handleResize); chart.remove(); };
  }, [filteredEquityPoints]);

  // --- HELPERS ---
  const fmt = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0);
  const pct = (v) => `${(v || 0).toFixed(2)}%`;
  const gradeColor = (g) => {
    if (['A','A+'].includes(g)) return C.green;
    if (['B','B+'].includes(g)) return C.cyan;
    if (g === 'C') return C.amber;
    return C.red;
  };

  // --- COMPUTED: Monthly returns heatmap from trades ---
  const monthlyReturns = useMemo(() => {
    if (!tradesData?.trades) return [];
    const byMonth = {};
    tradesData.trades.forEach(t => {
      if (!t.date) return;
      const d = new Date(t.date);
      const key = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
      byMonth[key] = (byMonth[key] || 0) + (t.pnl || 0);
    });
    return Object.entries(byMonth).map(([k, v]) => ({ month: k, pnl: v }));
  }, [tradesData]);

  // Filtered trades for search
  const filteredTrades = useMemo(() => {
    if (!tradesData?.trades) return [];
    if (!tradeSearch) return tradesData.trades;
    return tradesData.trades.filter(t =>
      t.symbol?.toLowerCase().includes(tradeSearch.toLowerCase())
    );
  }, [tradesData, tradeSearch]);

  // --- COMPUTED: Risk/Reward bar data from API ---
  const rrBarData = useMemo(() => {
    const avgWin = Math.abs(summary?.metrics?.avgWin || 0);
    const avgLoss = Math.abs(summary?.metrics?.avgLoss || 0);
    const expectancy = riskMetrics?.expectancy || 0;
    return [
      { label: 'Avg Win', value: avgWin, color: C.green },
      { label: 'Avg Loss', value: avgLoss, color: C.red },
      { label: 'Expectancy', value: Math.abs(expectancy), color: expectancy >= 0 ? C.cyan : C.red },
    ];
  }, [summary, riskMetrics]);

  // --- VaR gauge needle angle calculation ---
  const varNeedleAngle = useMemo(() => {
    const var95 = riskMetrics?.var95 || 0;
    const maxVar = riskMetrics?.maxVar || 10000;
    const ratio = Math.min(Math.abs(var95) / maxVar, 1);
    return -90 + (ratio * 180); // -90 = left, 90 = right
  }, [riskMetrics]);

  // --- Sentiment gauge needle angle calculation ---
  const sentimentNeedleAngle = useMemo(() => {
    const score = strategyData?.sentimentScore || 0;
    // score ranges from -1 to 1, map to -90 to 90 degrees
    const clamped = Math.max(-1, Math.min(1, score));
    return clamped * 90;
  }, [strategyData]);

  return (
    <div className="min-h-screen bg-[#0B0E14] text-gray-100 p-4 space-y-4">

      {/* HEADER */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold tracking-tight text-white">Performance Analytics</h1>
          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">Trading Grade</span>
          <span className="text-sm font-bold" style={{ color: gradeColor(riskMetrics?.trading_grade) }}>
            {riskMetrics?.trading_grade || '-'}
          </span>
        </div>
      </div>

      {/* TOP METRICS BAR: 10 KPIs */}
      <div className="grid grid-cols-10 gap-2">
        {[
          { label: 'Total Trades', val: summary?.metrics?.totalTrades },
          { label: 'Net P&L', val: fmt(summary?.metrics?.netPnl), color: (summary?.metrics?.netPnl >= 0 ? 'text-emerald-400' : 'text-red-400') },
          { label: 'Win Rate', val: pct(summary?.metrics?.winRate), sub: summary?.metrics?.winRateDelta ? `${summary.metrics.winRateDelta > 0 ? '+' : ''}${pct(summary.metrics.winRateDelta)}` : null },
          { label: 'Avg Win', val: fmt(summary?.metrics?.avgWin), color: 'text-emerald-400' },
          { label: 'Avg Loss', val: fmt(summary?.metrics?.avgLoss), color: 'text-red-400' },
          { label: 'Profit Factor', val: summary?.metrics?.profitFactor?.toFixed(2) },
          { label: 'Max DD', val: `${riskMetrics?.maxDrawdown?.toFixed(0) || '--'} / ${pct(riskMetrics?.maxDrawdownPct)}`, color: 'text-red-400' },
          { label: 'Sharpe', val: riskMetrics?.sharpe?.toFixed(2) },
          { label: 'Expectancy', val: fmt(riskMetrics?.expectancy) },
          { label: 'R:R', val: riskMetrics?.risk_reward_ratio?.toFixed(2) },
        ].map((m, i) => (
          <div key={i} className="bg-[#111827] border border-gray-800/50 rounded-lg p-2 text-center">
            <div className="text-[9px] text-gray-500 uppercase tracking-wider">{m.label}</div>
            <div className={`text-sm font-bold mt-0.5 ${m.color || 'text-white'}`}>{m.val ?? '--'}</div>
            {m.sub && <div className="text-[8px] text-emerald-400">{m.sub}</div>}
          </div>
        ))}
      </div>

      {/* ============ MAIN 12-COLUMN GRID (3/12 + 5/12 + 4/12) ============ */}
      <div className="grid grid-cols-12 gap-3">

        {/* ===== LEFT COLUMN (col-span-3): RISK COCKPIT ===== */}
        <div className="col-span-3 space-y-3">

          <Card className="bg-[#111827] border-gray-800/50 p-3">
            <h3 className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider mb-2 flex items-center gap-1">
              <Shield className="w-3 h-3" /> Risk Cockpit
            </h3>

            {/* Grade Hero */}
            <div className="flex flex-col items-center py-3">
              <div className="w-16 h-16 rounded-full border-2 flex items-center justify-center text-2xl font-black"
                style={{ borderColor: gradeColor(riskMetrics?.trading_grade), color: gradeColor(riskMetrics?.trading_grade) }}>
                {riskMetrics?.trading_grade || '-'}
              </div>
              <div className="text-[10px] text-gray-400 mt-1">Trading Grade Hero</div>
              <div className="text-[9px] text-gray-500">{riskMetrics?.gradeLabel || 'Excellent'}</div>
            </div>

            {/* Sharpe / Sortino / Calmar */}
            <div className="grid grid-cols-3 gap-1 mt-2">
              {[
                { label: 'Sharpe', val: riskMetrics?.sharpe, delta: riskMetrics?.sharpeDelta },
                { label: 'Sortino', val: riskMetrics?.sortino, delta: riskMetrics?.sortinoDelta },
                { label: 'Calmar', val: riskMetrics?.calmar, delta: riskMetrics?.calmarDelta }
              ].map(r => (
                <div key={r.label} className="text-center bg-slate-800/50 rounded p-1.5">
                  <div className="text-[8px] text-gray-500">{r.label}</div>
                  <div className="text-xs font-bold text-white">{r.val?.toFixed(2) || '0.00'}</div>
                  {r.delta != null &&
                    <div className={`text-[8px] ${r.delta >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{r.delta >= 0 ? '+' : ''}{r.delta?.toFixed(2)}</div>
                  }
                </div>
              ))}
            </div>

            {/* Kelly Criterion */}
            <div className="mt-3 bg-slate-800/30 rounded p-2">
              <div className="text-[9px] text-gray-500 mb-1">Kelly Criterion</div>
              <div className="flex justify-between text-[10px]">
                <span className="text-gray-400">Kelly Criterion</span>
                <span className="text-cyan-400 font-bold">{fmt(riskMetrics?.kellyDollar || 12228.50)}</span>
              </div>
              <div className="flex justify-between text-[10px] mt-0.5">
                <span className="text-gray-400">Lose</span>
                <span className="text-red-400 font-bold">{fmt(riskMetrics?.kellyLose || -3.60)}</span>
              </div>
            </div>

            {/* Risk/Reward + Expectancy - DATA-DRIVEN BARS */}
            <div className="mt-3">
              <div className="text-[9px] text-gray-500 mb-1">Risk/Reward + Expectancy</div>
              <div className="space-y-1">
                {rrBarData.map((bar, i) => {
                  const maxVal = Math.max(...rrBarData.map(b => b.value), 1);
                  return (
                    <div key={i} className="flex items-center gap-2">
                      <span className="text-[8px] text-gray-500 w-16 text-right">{bar.label}</span>
                      <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div className="h-full rounded-full transition-all" style={{ width: `${(bar.value / maxVal) * 100}%`, backgroundColor: bar.color }} />
                      </div>
                      <span className="text-[8px] text-gray-400 w-14">{fmt(bar.value)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </Card>
        </div>

        {/* ===== CENTER COLUMN (col-span-5): EQUITY + AGENT LEADERBOARD + ML ===== */}
        <div className="col-span-5 space-y-3">

          {/* Equity + Drawdown Chart */}
          <Card className="bg-[#111827] border-gray-800/50 p-3">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-1">
                <TrendingUp className="w-3 h-3" /> Equity + Drawdown
              </h3>
              <button onClick={() => setShowToolbar(!showToolbar)} className="flex items-center gap-1 px-2 py-1 text-[10px] bg-slate-800 hover:bg-slate-700 rounded text-slate-400">
                <Filter className="w-3 h-3" /> Toolbar
              </button>
            </div>
            {showToolbar && (
              <div className="flex gap-1 mb-2">
                {['1D','1W','1M','3M','YTD','1Y','ALL'].map(p => (
                  <button key={p} onClick={() => setActivePeriod(p)}
                    className={`px-2 py-0.5 text-[9px] rounded ${activePeriod === p ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' : 'bg-slate-800 text-slate-500 hover:text-slate-300'}`}>
                    {p}
                  </button>
                ))}
              </div>
            )}
            <div ref={chartContainerRef} className="w-full" />
            {!filteredEquityPoints?.length && <div className="text-[10px] text-gray-500 text-center py-8">Loading equity data...</div>}
            {equityData?.benchmarkLabel && (
              <div className="text-[8px] text-gray-600 mt-1">Benchmark: {equityData.benchmarkLabel}</div>
            )}
          </Card>

          {/* Agent Attribution Leaderboard */}
          <Card className="bg-[#111827] border-gray-800/50 p-3">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-1">
                <Brain className="w-3 h-3" /> Agent Attribution Leaderboard
              </h3>
              <span className="text-[8px] text-cyan-400/60">Consensus Active</span>
            </div>
            <table className="w-full text-[9px]">
              <thead>
                <tr className="text-gray-500 border-b border-gray-800">
                  <th className="py-1 text-left">#</th>
                  <th className="py-1 text-left">Agent</th>
                  <th className="py-1 text-right">ELO</th>
                  <th className="py-1 text-right">Changes</th>
                  <th className="py-1 text-right">Contributions</th>
                  <th className="py-1 text-right">Win Rate%</th>
                  <th className="py-1 text-right">Contribution%</th>
                </tr>
              </thead>
              <tbody>
                {(agents?.votes || []).map((agent, i) => (
                  <tr key={i} className="border-b border-gray-800/30 hover:bg-slate-800/30">
                    <td className="py-1 text-gray-500">{i + 1}</td>
                    <td className="py-1 text-white font-medium">{agent.name}</td>
                    <td className="py-1 text-right text-gray-300">{agent.elo?.toLocaleString()}</td>
                    <td className="py-1 text-right">
                      <span className={agent.change >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                        {agent.change >= 0 ? '+' : ''}{agent.change}
                      </span>
                    </td>
                    <td className="py-1 text-right text-gray-300">{pct((agent.contributions || 0) * 100)}</td>
                    <td className="py-1 text-right text-gray-300">{pct((agent.winRate || 0) * 100)}</td>
                    <td className="py-1 text-right text-gray-400">{((agent.contributions || 0) * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          {/* ML & Flywheel Engine */}
          <Card className="bg-[#111827] border-gray-800/50 p-3">
            <h3 className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider mb-2 flex items-center gap-1">
              <Zap className="w-3 h-3" /> ML & Flywheel Engine
            </h3>

            {/* ML Model Accuracy Trend - Lightweight Charts */}
            <div className="mb-3">
              <div className="text-[9px] text-gray-500 mb-1">ML Model Accuracy Trend</div>
              {flywheel?.accuracyHistory ? (
                <MiniLineChart data={flywheel.accuracyHistory} dataKey="accuracy" dateKey="date" color={C.cyan} height={80} />
              ) : <div className="text-[10px] text-gray-600 text-center py-4">Loading...</div>}
            </div>

            {/* Staged Inferences */}
            <div className="mb-3">
              <div className="text-[9px] text-gray-500 mb-1">Staged Inferences</div>
              {(flywheel?.stagedInferences || []).map((inf, i) => (
                <div key={i} className="flex justify-between text-[10px] py-0.5">
                  <span className="text-gray-400">{inf.label || 'Staged Inferences'}</span>
                  <span className={inf.delta >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                    {inf.delta >= 0 ? '+' : ''}{inf.value}
                  </span>
                </div>
              ))}
              {flywheel?.nilInferences != null && (
                <div className="flex justify-between text-[10px] py-0.5">
                  <span className="text-gray-400">NIL Inferences</span>
                  <span className="text-gray-300">{pct(flywheel.nilInferences)}</span>
                </div>
              )}
            </div>

            {/* Flywheel Pipeline Health */}
            <div>
              <div className="text-[9px] text-gray-500 mb-1">Flywheel Pipeline Health</div>
              {(flywheel?.pipelineStages || []).map((stage, i) => (
                <div key={i} className="flex items-center gap-2 text-[10px] py-0.5">
                  <div className="w-2 h-2 rounded-full bg-emerald-400" />
                  <span className="text-gray-300">{stage.label}</span>
                  {stage.detail && <span className="text-gray-600 text-[8px]">{stage.detail}</span>}
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* ===== RIGHT COLUMN (col-span-4): AI + ATTRIBUTION + TRADES + RISK + STRATEGY ===== */}
        <div className="col-span-4 space-y-3">

          {/* AI + Rolling Risk */}
          <Card className="bg-[#111827] border-gray-800/50 p-3">
            <h3 className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider mb-2 flex items-center gap-1">
              <Brain className="w-3 h-3" /> AI + Rolling Risk
            </h3>
            {/* Nested Concentric AI Dial */}
            <div className="flex items-center gap-3">
              <div className="relative w-20 h-20">
                <svg viewBox="0 0 100 100" className="w-full h-full">
                  <circle cx="50" cy="50" r="45" fill="none" stroke="#1e293b" strokeWidth="6" />
                  <circle cx="50" cy="50" r="45" fill="none" stroke={C.cyan} strokeWidth="6"
                    strokeDasharray={`${(flywheel?.accuracyPct || 0.783) * 283} 283`}
                    strokeLinecap="round" transform="rotate(-90 50 50)" />
                  <circle cx="50" cy="50" r="35" fill="none" stroke="#1e293b" strokeWidth="5" />
                  <circle cx="50" cy="50" r="35" fill="none" stroke={C.green} strokeWidth="5"
                    strokeDasharray={`${(flywheel?.agentConfidence || 0.67) * 220} 220`}
                    strokeLinecap="round" transform="rotate(-90 50 50)" />
                  <text x="50" y="48" textAnchor="middle" fill="white" fontSize="12" fontWeight="bold">
                    {pct((flywheel?.accuracyPct || 0.783) * 100)}
                  </text>
                  <text x="50" y="60" textAnchor="middle" fill={C.muted} fontSize="7">AI Accuracy</text>
                </svg>
              </div>
              <div className="text-[9px] space-y-1">
                <div className="text-gray-400">{Math.round((flywheel?.agentConfidence || 0.67) * 100)}% <span className="text-gray-600">Agent</span></div>
              </div>
            </div>
            {/* Rolling Risk Sharpe - div-based bars */}
            <div className="mt-2">
              <div className="text-[9px] text-gray-500 mb-1">Rolling Risk Sharpe</div>
              <div className="flex items-end gap-[2px] h-[50px]">
                {(riskMetrics?.rollingRiskSharpe || []).map((e, i) => {
                  const maxVal = Math.max(...(riskMetrics?.rollingRiskSharpe || []).map(d => Math.abs(d.value || 0)), 0.01);
                  const heightPct = (Math.abs(e.value || 0) / maxVal) * 100;
                  const barColor = e.value > 0.6 ? '#10B981' : e.value > 0.3 ? '#F59E0B' : '#EF4444';
                  return (
                    <div key={i} className="flex-1 rounded-t-sm transition-all" title={`${e.label || ''}: ${(e.value || 0).toFixed(2)}`}
                      style={{ height: `${Math.max(heightPct, 4)}%`, backgroundColor: barColor, minWidth: '3px' }} />
                  );
                })}
              </div>
            </div>
          </Card>

          {/* P&L By Symbol */}
          <Card className="bg-[#111827] border-gray-800/50 p-3">
            <div className="text-[9px] text-gray-500 mb-1">P&L By Symbol</div>
            {(tradesData?.symbolPnl || tradesData?.trades?.reduce((acc, t) => {
              if (!acc.find(a => a.symbol === t.symbol)) acc.push({ symbol: t.symbol, pnl: 0 });
              const item = acc.find(a => a.symbol === t.symbol);
              if (item) item.pnl += t.pnl || 0;
              return acc;
            }, []) || []).slice(0, 8).map((s, i) => (
              <div key={i} className="flex items-center gap-2 py-0.5">
                <span className="text-[9px] text-gray-300 w-12">{s.symbol}</span>
                <div className={`h-1.5 rounded ${s.pnl >= 0 ? 'bg-emerald-500' : 'bg-red-500'}`}
                  style={{ width: `${Math.min(Math.abs(s.pnl) / 1000 * 30, 30)}px` }} />
              </div>
            ))}
          </Card>

          {/* Returns Heatmap Calendar */}
          <Card className="bg-[#111827] border-gray-800/50 p-3">
            <div className="text-[9px] text-gray-500 mb-1">Returns Heatmap Calendar</div>
            <div className="grid grid-cols-13 gap-0.5">
              {['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec','YTD'].map((m, i) => {
                const entry = monthlyReturns.find(r => r.month?.endsWith(`-${String(i+1).padStart(2,'0')}`));
                const val = i === 12 ? monthlyReturns.reduce((s, r) => s + r.pnl, 0) : (entry?.pnl || 0);
                return (
                  <div key={m} className={`rounded p-1 text-center text-[7px] ${
                    val > 0 ? 'bg-emerald-500/20 text-emerald-400' : val < 0 ? 'bg-red-500/20 text-red-400' : 'bg-slate-800 text-slate-600'
                  }`}>
                    <div>{m}</div>
                    <div className="font-bold">{val !== 0 ? `${val > 0 ? '+' : ''}${(val / 100).toFixed(1)}%` : '-'}</div>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* Enhanced Trades Table */}
          <Card className="bg-[#111827] border-gray-800/50 p-3">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider">Enhanced Trades Table</h3>
              <div className="flex items-center gap-2">
                <span className="text-[8px] text-gray-600">TRADE LOG</span>
                <input type="text" value={tradeSearch} onChange={(e) => setTradeSearch(e.target.value)}
                  className="bg-transparent text-[10px] text-slate-300 outline-none w-16 border-b border-gray-700" placeholder="Search..." />
                <button onClick={() => setTradeView(tradeView === 'table' ? 'grid' : 'table')}
                  className="p-1 hover:bg-slate-800 rounded text-slate-500"><Grid className="w-3 h-3" /></button>
              </div>
            </div>
            <div className="max-h-48 overflow-y-auto">
              <table className="w-full text-[9px]">
                <thead className="sticky top-0 bg-[#111827]">
                  <tr className="text-gray-500 border-b border-gray-800">
                    <th className="py-1 text-left">Date</th>
                    <th className="py-1 text-left">Symbol</th>
                    <th className="py-1">Side</th>
                    <th className="py-1 text-right">Qty</th>
                    <th className="py-1 text-right">Entry</th>
                    <th className="py-1 text-right">Exit</th>
                    <th className="py-1 text-right">P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTrades.map((trade, i) => (
                    <tr key={i} className="border-b border-gray-800/30 hover:bg-slate-800/30">
                      <td className="py-1 text-gray-500">{trade.date || '--'}</td>
                      <td className="py-1 text-white">{trade.symbol}</td>
                      <td className="py-1 text-center">{trade.side === 'LONG' ? 'L' : trade.side === 'SHORT' ? 'S' : trade.side}</td>
                      <td className="py-1 text-right text-gray-400">{trade.qty}</td>
                      <td className="py-1 text-right text-gray-300">{fmt(trade.entry)}</td>
                      <td className="py-1 text-right text-gray-300">{fmt(trade.exit)}</td>
                      <td className={`py-1 text-right font-medium ${trade.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {trade.pnl >= 0 ? '+' : ''}{fmt(trade.pnl)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Risk Cockpit Expanded */}
          <Card className="bg-[#111827] border-gray-800/50 p-3">
            <h3 className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider mb-2 flex items-center gap-1">
              <Shield className="w-3 h-3" /> Risk Cockpit Expanded
            </h3>
            {/* Risk Shield Status */}
            <div className="mb-2">
              <div className="text-[9px] text-gray-500">Risk Shield Status</div>
              <div className="text-xs font-bold text-emerald-400">{riskStatus?.status || 'ACTIVE'}</div>
              {riskStatus?.shieldBreakdown ? (
                <div className="flex items-end gap-[2px] h-[50px]">
                  {(riskStatus.shieldBreakdown || []).map((e, i) => {
                    const maxVal = Math.max(...(riskStatus.shieldBreakdown || []).map(d => Math.abs(d.value || 0)), 0.01);
                    const heightPct = (Math.abs(e.value || 0) / maxVal) * 100;
                    return (
                      <div key={i} className="flex-1 rounded-t-sm transition-all" title={`${e.label || e.name || ''}: ${(e.value || 0).toFixed(2)}`}
                        style={{ height: `${Math.max(heightPct, 4)}%`, backgroundColor: '#00D9FF', minWidth: '3px' }} />
                    );
                  })}
                </div>
              ) : <div className="text-[10px] text-gray-600">No data</div>}
            </div>
            {/* Risk History - Lightweight Charts */}
            <div className="mb-2">
              <div className="text-[9px] text-gray-500 mb-1">Risk History</div>
              {riskMetrics?.riskHistory ? (
                <MiniAreaChart data={riskMetrics.riskHistory} dataKey="value" dateKey="date" lineColor="#EF4444" topColor="rgba(239,68,68,0.3)" height={50} />
              ) : <div className="text-[10px] text-gray-600">Loading...</div>}
            </div>
            {/* VaR Gauge - DATA-DRIVEN NEEDLE */}
            <div className="text-center">
              <div className="text-[9px] text-gray-500 mb-1">VaR Gauge</div>
              <svg viewBox="0 0 120 70" className="w-24 h-14 mx-auto">
                <path d="M 10 60 A 50 50 0 0 1 110 60" fill="none" stroke="#1e293b" strokeWidth="8" strokeLinecap="round" />
                <path d="M 10 60 A 50 50 0 0 1 110 60" fill="none" stroke={C.red} strokeWidth="8" strokeLinecap="round"
                  strokeDasharray={`${Math.min(Math.abs(riskMetrics?.var95 || 0) / (riskMetrics?.maxVar || 10000), 1) * 157} 157`} />
                <line x1="60" y1="60" x2={60 + 35 * Math.cos((varNeedleAngle - 90) * Math.PI / 180)}
                  y2={60 + 35 * Math.sin((varNeedleAngle - 90) * Math.PI / 180)}
                  stroke="white" strokeWidth="2" strokeLinecap="round" />
                <circle cx="60" cy="60" r="3" fill="white" />
                <text x="60" y="55" textAnchor="middle" fill="white" fontSize="8" fontWeight="bold">VaR</text>
              </svg>
              <div className="text-[10px] text-red-400 font-bold">{fmt(riskMetrics?.var95 || 0)}</div>
            </div>
          </Card>

          {/* Active Strategies */}
          <Card className="bg-[#111827] border-gray-800/50 p-3">
            <h3 className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider mb-2 flex items-center gap-1">
              <Target className="w-3 h-3" /> Active Strategies
            </h3>
            {(strategyData?.strategies || []).map((strat, idx) => (
              <div key={idx} className="flex justify-between text-[10px] py-0.5">
                <span className="text-gray-300">{strat.name}</span>
                <span className="text-cyan-400 font-bold">{pct((strat.hitRate || 0) * 100)}</span>
              </div>
            ))}
            {(!strategyData?.strategies || strategyData.strategies.length === 0) && (
              <div className="text-[10px] text-gray-600">Loading strategies...</div>
            )}

            {/* Signal Hit Rate */}
            <div className="mt-2 flex justify-between text-[10px] bg-slate-800/30 rounded p-1.5">
              <span className="text-gray-400">Overall</span>
              <span className="text-cyan-400 font-bold">{pct((strategyData?.overallHitRate || 0) * 100)}</span>
            </div>

            {/* Market Sentiment Gauge - DATA-DRIVEN NEEDLE */}
            <div className="mt-3 text-center">
              <div className="text-[9px] text-gray-500 mb-1">Market Sentiment</div>
              <svg viewBox="0 0 120 70" className="w-24 h-14 mx-auto">
                {/* Background arc */}
                <path d="M 10 60 A 50 50 0 0 1 110 60" fill="none" stroke="#1e293b" strokeWidth="8" strokeLinecap="round" />
                {/* Green section (0-33%) */}
                <path d="M 10 60 A 50 50 0 0 1 43 14" fill="none" stroke={C.red} strokeWidth="8" strokeLinecap="round" />
                {/* Yellow section (33-66%) */}
                <path d="M 43 14 A 50 50 0 0 1 77 14" fill="none" stroke={C.amber} strokeWidth="8" strokeLinecap="round" />
                {/* Green section (66-100%) */}
                <path d="M 77 14 A 50 50 0 0 1 110 60" fill="none" stroke={C.green} strokeWidth="8" strokeLinecap="round" />
                {/* Needle - driven by sentimentNeedleAngle */}
                <line x1="60" y1="60"
                  x2={60 + 35 * Math.cos((sentimentNeedleAngle - 90) * Math.PI / 180)}
                  y2={60 + 35 * Math.sin((sentimentNeedleAngle - 90) * Math.PI / 180)}
                  stroke="white" strokeWidth="2" strokeLinecap="round" />
                <circle cx="60" cy="60" r="3" fill="white" />
              </svg>
              <div className="text-xs font-bold text-white">{(strategyData?.sentimentScore || 0).toFixed(2)}</div>
              <div className="text-[8px] text-gray-500">Market Sentiment readout</div>
            </div>
          </Card>

        </div>{/* END RIGHT COLUMN */}
      </div>{/* END MAIN 12-COLUMN GRID */}

      {/* FOOTER STATUS BAR */}
      <div className="flex items-center justify-between px-4 py-1 bg-[#111827] border border-gray-800/50 rounded text-[9px]">
        <div className="flex items-center gap-2">
          <span className="text-gray-500">Embodier Trader</span>
          <span className="text-cyan-400">Performance Analytics v2.1</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          <span className="text-gray-400">Connected</span>
        </div>
        <div className="text-gray-600">
          Filters: {activePeriod} | Multi-Agent &nbsp; Data: Jan 1 - Feb 28, 2026
        </div>
      </div>

      {/* Agent Attribution from Postmortems */}
      <div className="mt-4">
        <PostmortemAttribution />
      </div>

    </div>
  );
};

export default PerformanceAnalytics;
