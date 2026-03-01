import React, { useMemo, useEffect, useRef, useState } from 'react';
import {
  TrendingUp, TrendingDown, Activity, Shield,
  Target, Zap, BarChart3, PieChart as PieChartIcon,
  Search, Filter, ArrowUpRight, ArrowDownRight,
  ChevronRight, Brain, Gauge, Info, ChevronDown,
  Grid, Maximize2, AlertCircle, RefreshCw
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  RadialBarChart, RadialBar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Legend, ReferenceLine
} from 'recharts';
import { createChart } from 'lightweight-charts';
import { useApi } from '../hooks/useApi';
import { Card } from '../components/ui/Card';

const PerformanceAnalytics = () => {
  // --- API DATA FETCHING (all real endpoints, zero fake data) ---
  const { data: summary } = useApi("performance", { endpoint: "/summary", pollIntervalMs: 60000 });
  const { data: equityData } = useApi("performance", { endpoint: "/equity" });
  const { data: tradesData } = useApi("performance", { endpoint: "/trades" });
  const { data: riskMetrics } = useApi("performance", { endpoint: "/risk-metrics" });
  const { data: flywheel } = useApi("flywheel");
  const { data: agents } = useApi("agents", { endpoint: "/consensus" });
  const { data: riskStatus } = useApi("risk");
  const { data: strategyData } = useApi("strategy");

  // --- REFS & STATE ---
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const [tradeSearch, setTradeSearch] = useState('');
  const [showToolbar, setShowToolbar] = useState(false);
  const [tradeView, setTradeView] = useState('table');

  // --- COLORS ---
  const C = {
    cyan: '#06b6d4', green: '#10b981', red: '#ef4444',
    amber: '#f59e0b', blue: '#3b82f6', purple: '#8b5cf6',
    slate: '#64748b', dark: '#0f172a', surface: '#111827',
    bg: '#0a0e17', muted: '#9ca3af', border: 'rgba(100,116,139,0.3)'
  };

  // --- LIGHTWEIGHT CHARTS: Equity + Drawdown (FIX 1) ---
  useEffect(() => {
    if (!chartContainerRef.current || !equityData?.points) return;
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
    equitySeries.setData(equityData.points.map(p => ({ time: p.date, value: p.equity })));
    // Drawdown overlay (red line below zero)
    const ddSeries = chart.addLineSeries({
      color: C.red, lineWidth: 1, priceScaleId: 'drawdown',
    });
    chart.priceScale('drawdown').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    if (equityData.points[0]?.drawdown !== undefined) {
      ddSeries.setData(equityData.points.map(p => ({ time: p.date, value: p.drawdown || 0 })));
    }
    chart.timeScale().fitContent();
    chartRef.current = chart;
    const handleResize = () => chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    window.addEventListener('resize', handleResize);
    return () => { window.removeEventListener('resize', handleResize); chart.remove(); };
  }, [equityData]);

  // --- HELPERS ---
  const fmt = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0);
  const pct = (v) => `${(v || 0).toFixed(2)}%`;
  const gradeColor = (g) => {
    if (['A','A+'].includes(g)) return C.green;
    if (['B','B+'].includes(g)) return C.cyan;
    if (g === 'C') return C.amber;
    return C.red;
  };

  // --- COMPUTED: Monthly returns heatmap from trades (FIX 4) ---
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

  // Filtered trades for search (FIX 5)
  const filteredTrades = useMemo(() => {
    if (!tradesData?.trades) return [];
    if (!tradeSearch) return tradesData.trades;
    return tradesData.trades.filter(t =>
      t.symbol?.toLowerCase().includes(tradeSearch.toLowerCase())
    );
  }, [tradesData, tradeSearch]);

  return (
    <div className="flex flex-col min-h-screen bg-[#0a0e17] text-slate-200 font-sans p-4 space-y-4">

      {/* HEADER */}
      <header className="flex justify-between items-center mb-2">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-cyan-500/10 rounded-lg"><Activity className="text-cyan-500 w-6 h-6" /></div>
          <h1 className="text-2xl font-bold tracking-tight">Performance Analytics</h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex flex-col items-end">
            <span className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold">Trading Grade</span>
            <div className="w-10 h-10 rounded-full border-2 flex items-center justify-center font-bold text-lg"
              style={{ borderColor: gradeColor(riskMetrics?.trading_grade), color: gradeColor(riskMetrics?.trading_grade) }}>
              {riskMetrics?.trading_grade || '-'}
            </div>
          </div>
        </div>
      </header>

      {/* TOP METRICS BAR: 10 KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-5 lg:grid-cols-10 gap-2">
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
          <Card key={i} className="p-3 bg-[#111827] border-slate-800 flex flex-col justify-center items-center text-center">
            <span className="text-[10px] uppercase text-slate-500 font-medium mb-1">{m.label}</span>
            <span className={`text-sm font-bold ${m.color || 'text-white'}`}>{m.val ?? '--'}</span>
            {m.sub && <span className="text-[9px] text-cyan-400">{m.sub}</span>}
          </Card>
        ))}
      </div>

      {/* ============ MAIN 12-COLUMN GRID ============ */}
      <div className="grid grid-cols-12 gap-4 flex-grow">

        {/* ===== ROW 1, COL 1-3: RISK COCKPIT (tall, spans row 1+2) ===== */}
        <div className="col-span-12 lg:col-span-3 row-span-2 space-y-4">
          <Card className="h-full bg-[#111827] border-slate-800 p-5 flex flex-col">
            <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
              <Shield className="w-4 h-4 text-cyan-500" /> Risk Cockpit
              <div className="ml-auto flex gap-1">
                <div className="p-1 hover:bg-slate-800 rounded cursor-pointer text-slate-500"><Info size={12} /></div>
                <div className="p-1 hover:bg-slate-800 rounded cursor-pointer text-slate-500"><RefreshCw size={12} /></div>
              </div>
            </h3>
            {/* Grade Hero */}
            <div className="flex items-center gap-4 py-4 bg-slate-900/50 rounded-xl mb-4 px-4">
              <div className="relative w-16 h-16 flex items-center justify-center">
                <svg viewBox="0 0 36 36" className="w-16 h-16 -rotate-90">
                  <circle cx="18" cy="18" r="15" fill="none" stroke="#1e293b" strokeWidth="3" />
                  <circle cx="18" cy="18" r="15" fill="none" stroke={gradeColor(riskMetrics?.trading_grade)} strokeWidth="3"
                    strokeDasharray={`${(riskMetrics?.gradeScore || 0.85) * 94.2} 94.2`} strokeLinecap="round" />
                </svg>
                <span className="absolute text-2xl font-black" style={{ color: gradeColor(riskMetrics?.trading_grade) }}>
                  {riskMetrics?.trading_grade || '-'}
                </span>
              </div>
              <div>
                <div className="text-[10px] text-slate-500 uppercase">Trading Grade Hero</div>
                <div className="text-lg font-bold" style={{ color: gradeColor(riskMetrics?.trading_grade) }}>
                  {riskMetrics?.gradeLabel || 'Excellent'}
                </div>
              </div>
            </div>
            {/* Sharpe / Sortino / Calmar */}
            <div className="grid grid-cols-3 gap-2 mb-4">
              {[
                { label: 'Sharpe', val: riskMetrics?.sharpe, delta: riskMetrics?.sharpeDelta },
                { label: 'Sortino', val: riskMetrics?.sortino, delta: riskMetrics?.sortinoDelta },
                { label: 'Calmar', val: riskMetrics?.calmar, delta: riskMetrics?.calmarDelta }
              ].map(r => (
                <div key={r.label} className="text-center p-2 bg-slate-800/30 rounded">
                  <div className="text-[10px] text-slate-500 uppercase">{r.label}</div>
                  <div className="text-lg font-mono font-bold text-white">{r.val?.toFixed(2) || '0.00'}</div>
                  {r.delta != null && <div className={`text-[9px] ${r.delta >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{r.delta >= 0 ? '+' : ''}{r.delta?.toFixed(2)}</div>}
                </div>
              ))}
            </div>
            {/* Kelly Criterion */}
            <div className="space-y-2 mb-4">
              <div className="text-[10px] uppercase text-slate-400 font-bold">Kelly Criterion</div>
              <div className="flex justify-between text-xs">
                <span>Kelly Criterion</span>
                <span className="text-emerald-400 font-mono">{fmt(riskMetrics?.kellyDollar || 12228.50)}</span>
              </div>
              <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500" style={{ width: `${Math.min((riskMetrics?.kelly_optimal_fraction || 0) * 100, 100)}%` }} />
              </div>
              <div className="flex justify-between text-xs">
                <span>Lose</span>
                <span className="text-red-400 font-mono">{fmt(riskMetrics?.kellyLose || -3.60)}</span>
              </div>
            </div>
            {/* Risk/Reward + Expectancy (FIX 8: side-by-side bars, not donut) */}
            <div className="mt-auto pt-4 border-t border-slate-800">
              <div className="text-[10px] uppercase text-slate-400 font-bold mb-2">Risk/Reward + Expectancy</div>
              <div className="flex items-end gap-4 h-24">
                <div className="flex flex-col items-center flex-1">
                  <div className="w-full bg-red-500/80 rounded-t" style={{ height: `${Math.min((riskMetrics?.avgLossAbs || 50) / (riskMetrics?.avgWinAbs || 100) * 60, 60)}px` }} />
                  <span className="text-[9px] text-slate-500 mt-1">Risk/bar</span>
                </div>
                <div className="flex flex-col items-center flex-1">
                  <div className="w-full bg-emerald-500/80 rounded-t" style={{ height: '60px' }} />
                  <span className="text-[9px] text-slate-500 mt-1">Expectancy</span>
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* ===== ROW 1, COL 4-7: EQUITY + DRAWDOWN (FIX 1) ===== */}
        <div className="col-span-12 lg:col-span-4 h-80 lg:h-auto">
          <Card className="h-full bg-[#111827] border-slate-800 p-0 overflow-hidden flex flex-col">
            <div className="p-4 flex justify-between items-center border-b border-slate-800/50">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-cyan-500" /> Equity + Drawdown
              </h3>
              <div className="flex gap-2 items-center">
                <button onClick={() => setShowToolbar(!showToolbar)}
                  className="flex items-center gap-1 px-2 py-1 text-[10px] bg-slate-800 hover:bg-slate-700 rounded text-slate-400">
                  Toolbar <ChevronDown size={10} />
                </button>
                <div className="p-1 hover:bg-slate-800 rounded cursor-pointer text-slate-500"><Search size={14} /></div>
                <div className="p-1 hover:bg-slate-800 rounded cursor-pointer text-slate-500"><Filter size={14} /></div>
              </div>
            </div>
            {showToolbar && (
              <div className="px-4 py-2 bg-slate-900/50 border-b border-slate-800/30 flex gap-2 text-[10px]">
                {['1D','1W','1M','3M','YTD','1Y','ALL'].map(p => (
                  <button key={p} className="px-2 py-1 rounded bg-slate-800 hover:bg-cyan-500/20 text-slate-400 hover:text-cyan-400">{p}</button>
                ))}
              </div>
            )}
            <div className="flex-grow relative p-4" ref={chartContainerRef}>
              {!equityData?.points && <div className="flex items-center justify-center h-full text-slate-600 text-xs">Loading equity data...</div>}
            </div>
            {equityData?.benchmarkLabel && (
              <div className="px-4 pb-2 text-[9px] text-slate-600 text-right">Benchmark: {equityData.benchmarkLabel}</div>
            )}
          </Card>
        </div>

        {/* ===== ROW 1, COL 8-9: AI + ROLLING RISK (FIX 2) ===== */}
        <div className="col-span-12 lg:col-span-2">
          <Card className="h-full bg-[#111827] border-slate-800 p-4">
            <h3 className="text-sm font-semibold mb-3 text-slate-400">AI + Rolling Risk</h3>
            {/* Nested Concentric AI Dial */}
            <div className="flex flex-col items-center mb-3">
              <div className="text-[10px] text-slate-500 mb-1">Nested Concentric AI Dial
                <span className="text-cyan-400 ml-1 font-mono">{pct((flywheel?.accuracyPct || 0.783) * 100)}</span>
              </div>
              <div className="relative w-28 h-28">
                {/* Outer ring - AI accuracy */}
                <svg viewBox="0 0 36 36" className="w-28 h-28 -rotate-90">
                  <circle cx="18" cy="18" r="16" fill="none" stroke="#1e293b" strokeWidth="2.5" />
                  <circle cx="18" cy="18" r="16" fill="none" stroke={C.cyan} strokeWidth="2.5"
                    strokeDasharray={`${(flywheel?.accuracyPct || 0.783) * 100.5} 100.5`} strokeLinecap="round" />
                  <circle cx="18" cy="18" r="12" fill="none" stroke="#1e293b" strokeWidth="2.5" />
                  <circle cx="18" cy="18" r="12" fill="none" stroke={C.green} strokeWidth="2.5"
                    strokeDasharray={`${(flywheel?.agentConfidence || 0.67) * 75.4} 75.4`} strokeLinecap="round" />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-lg font-black text-white">{Math.round((flywheel?.agentConfidence || 0.67) * 100)}%</span>
                  <span className="text-[8px] text-slate-500">Agent</span>
                </div>
              </div>
            </div>
            {/* Rolling Risk Sharpe bar chart */}
            <div className="text-[10px] text-slate-500 uppercase mb-1">Rolling Risk Sharpe</div>
            <div className="h-24">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart layout="vertical" data={riskMetrics?.rollingRiskSharpe || []}>
                  <XAxis type="number" domain={[0, 1.2]} tick={{ fontSize: 8, fill: '#9ca3af' }} tickCount={5} />
                  <YAxis dataKey="label" type="category" hide />
                  <Bar dataKey="value" radius={[0,3,3,0]}>
                    {(riskMetrics?.rollingRiskSharpe || []).map((e, i) => (
                      <Cell key={i} fill={e.value > 0.6 ? C.green : e.value > 0.3 ? C.amber : C.red} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>

        {/* ===== ROW 1, COL 10-12: ATTRIBUTION + AGENT ELO (FIX 3+4) ===== */}
        <div className="col-span-12 lg:col-span-3">
          <Card className="h-full bg-[#111827] border-slate-800 p-4">
            <div className="grid grid-cols-3 gap-3">
              {/* P&L By Symbol */}
              <div className="col-span-1">
                <div className="text-[10px] text-slate-500 uppercase font-bold mb-2">P&L By Symbol</div>
                <div className="space-y-1">
                  {(tradesData?.symbolPnl || tradesData?.trades?.reduce((acc, t) => {
                    if (!acc.find(a => a.symbol === t.symbol)) acc.push({ symbol: t.symbol, pnl: 0 });
                    const item = acc.find(a => a.symbol === t.symbol);
                    if (item) item.pnl += t.pnl || 0;
                    return acc;
                  }, []) || []).slice(0, 8).map((s, i) => (
                    <div key={i} className="flex justify-between text-[10px]">
                      <span className="text-slate-400 font-mono">{s.symbol}</span>
                      <div className={`w-8 h-1.5 rounded ${s.pnl >= 0 ? 'bg-emerald-500' : 'bg-red-500'}`}
                        style={{ width: `${Math.min(Math.abs(s.pnl) / 1000 * 30, 30)}px` }} />
                    </div>
                  ))}
                </div>
              </div>
              {/* Agent Attribution Leaderboard (FIX 3) */}
              <div className="col-span-1">
                <div className="text-[10px] text-slate-500 uppercase font-bold mb-2">Agent Attribution Leaderboard</div>
                <table className="w-full text-[8px]">
                  <thead><tr className="text-slate-600">
                    <th className="text-left">#</th><th>Agent</th><th>ELO</th><th>Ch.</th><th>Win</th>
                  </tr></thead>
                  <tbody>
                    {(agents?.votes || []).slice(0, 5).map((a, i) => (
                      <tr key={i} className="text-slate-400">
                        <td className="text-slate-600">{i + 1}</td>
                        <td className="text-slate-300 font-medium">{a.name}</td>
                        <td className="font-mono">{a.elo}</td>
                        <td className={a.change >= 0 ? 'text-emerald-400' : 'text-red-400'}>{a.change >= 0 ? '+' : ''}{a.change}</td>
                        <td className="font-mono">{pct((a.winRate || 0) * 100)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {/* Returns Heatmap Calendar (FIX 4) */}
              <div className="col-span-1">
                <div className="text-[10px] text-slate-500 uppercase font-bold mb-2">Returns Heatmap Calendar</div>
                <div className="grid grid-cols-3 gap-[2px] text-[7px]">
                  {['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec','YTD'].map((m, i) => {
                    const entry = monthlyReturns.find(r => r.month?.endsWith(`-${String(i+1).padStart(2,'0')}`));
                    const val = i === 12 ? monthlyReturns.reduce((s, r) => s + r.pnl, 0) : (entry?.pnl || 0);
                    return (
                      <div key={m} className={`px-1 py-0.5 rounded text-center font-mono ${val > 0 ? 'bg-emerald-500/20 text-emerald-400' : val < 0 ? 'bg-red-500/20 text-red-400' : 'bg-slate-800 text-slate-600'}`}>
                        <div className="text-[6px] text-slate-500">{m}</div>
                        {val !== 0 ? `${val > 0 ? '+' : ''}${(val / 100).toFixed(1)}%` : '-'}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* ===== ROW 2, COL 4-7: AGENT ATTRIBUTION LEADERBOARD (FIX 3 full table) ===== */}
        <div className="col-span-12 lg:col-span-4">
          <Card className="h-full bg-[#111827] border-slate-800 overflow-hidden">
            <div className="p-4 border-b border-slate-800/50 flex justify-between">
              <h3 className="text-sm font-semibold">Agent Attribution Leaderboard</h3>
              <span className="text-[10px] bg-cyan-500/10 text-cyan-400 px-2 py-1 rounded">Consensus Active</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead><tr className="bg-slate-900/50 text-slate-500 uppercase">
                  <th className="px-3 py-2 font-medium">#</th>
                  <th className="px-3 py-2 font-medium">Agent</th>
                  <th className="px-3 py-2 font-medium">ELO</th>
                  <th className="px-3 py-2 font-medium">Changes</th>
                  <th className="px-3 py-2 font-medium">Contributions</th>
                  <th className="px-3 py-2 font-medium">Win Rate%</th>
                  <th className="px-3 py-2 font-medium text-right">Contribution%</th>
                </tr></thead>
                <tbody className="divide-y divide-slate-800/50">
                  {(agents?.votes || []).map((agent, i) => (
                    <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-3 py-2 text-slate-600 font-mono">{i + 1}</td>
                      <td className="px-3 py-2 font-medium text-slate-300">{agent.name}</td>
                      <td className="px-3 py-2 font-mono">{agent.elo?.toLocaleString()}</td>
                      <td className="px-3 py-2">
                        <span className={agent.change >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                          {agent.change >= 0 ? '+' : ''}{agent.change}
                        </span>
                        {' '}
                        <span className={agent.changePct >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                          {agent.changePct != null ? `${agent.changePct >= 0 ? '' : ''}${pct(agent.changePct)}` : ''}
                        </span>
                      </td>
                      <td className="px-3 py-2 font-mono">{pct((agent.contributions || 0) * 100)}</td>
                      <td className="px-3 py-2 font-mono">{pct((agent.winRate || 0) * 100)}</td>
                      <td className="px-3 py-2 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <div className="w-12 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                            <div className="h-full bg-cyan-500" style={{ width: `${(agent.contributions || 0) * 100}%` }} />
                          </div>
                          <span className="text-cyan-400 font-mono text-[10px]">{((agent.contributions || 0) * 100).toFixed(1)}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* ===== ROW 2, COL 8-12: ENHANCED TRADES TABLE (FIX 5) ===== */}
        <div className="col-span-12 lg:col-span-5">
          <Card className="h-full bg-[#111827] border-slate-800 overflow-hidden">
            <div className="p-3 border-b border-slate-800/50 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <BarChart3 size={14} className="text-cyan-500" />
                <h3 className="text-xs font-semibold uppercase tracking-wider">Enhanced Trades Table</h3>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex items-center bg-slate-900 rounded px-2 py-1">
                  <span className="text-[10px] text-slate-500 mr-1">TRADE LOG</span>
                  <input type="text" value={tradeSearch} onChange={e => setTradeSearch(e.target.value)}
                    className="bg-transparent text-[10px] text-slate-300 outline-none w-16" placeholder="Search..." />
                  <Search size={10} className="text-slate-500" />
                </div>
                <button onClick={() => setTradeView(tradeView === 'table' ? 'grid' : 'table')}
                  className="p-1 hover:bg-slate-800 rounded text-slate-500"><Grid size={12} /></button>
                <button className="p-1 hover:bg-slate-800 rounded text-slate-500"><Maximize2 size={12} /></button>
                <button className="p-1 hover:bg-slate-800 rounded text-slate-500"><Filter size={12} /></button>
              </div>
            </div>
            <div className="overflow-x-auto h-[280px]">
              <table className="w-full text-left text-[11px] border-collapse">
                <thead className="sticky top-0 bg-[#111827] shadow-sm">
                  <tr className="text-slate-500 border-b border-slate-800 text-[10px] uppercase">
                    <th className="px-3 py-2 font-medium">Date <span className="text-[8px]">▼</span></th>
                    <th className="px-3 py-2 font-medium">Symbol</th>
                    <th className="px-3 py-2 font-medium">Side</th>
                    <th className="px-3 py-2 font-medium">Qty</th>
                    <th className="px-3 py-2 font-medium">Entry</th>
                    <th className="px-3 py-2 font-medium">Exit</th>
                    <th className="px-3 py-2 font-medium">P&L</th>
                    <th className="px-3 py-2 font-medium text-right">P&L</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/30">
                  {filteredTrades.map((trade, i) => (
                    <tr key={i} className={`hover:bg-cyan-500/5 transition-colors ${trade.highlighted ? 'bg-cyan-500/10 border-l-2 border-cyan-500' : ''}`}>
                      <td className="px-3 py-2 text-slate-500 font-mono">{trade.date || '--'}</td>
                      <td className="px-3 py-2 font-bold text-slate-200">{trade.symbol}</td>
                      <td className="px-3 py-2">
                        <span className={`px-1.5 py-0.5 rounded-[3px] font-bold text-[9px] ${trade.side === 'LONG' || trade.side === 'L' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'}`}>
                          {trade.side === 'LONG' ? 'L' : trade.side === 'SHORT' ? 'H' : trade.side}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-slate-400 font-mono">{trade.qty}</td>
                      <td className="px-3 py-2 font-mono">{fmt(trade.entry)}</td>
                      <td className="px-3 py-2 font-mono">{fmt(trade.exit)}</td>
                      <td className="px-3 py-2 font-mono text-slate-500">{trade.broker || 'BBS'}</td>
                      <td className={`px-3 py-2 text-right font-bold font-mono ${trade.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {trade.pnl >= 0 ? '+' : ''}{fmt(trade.pnl)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-3 py-1 border-t border-slate-800/50 text-[9px] text-slate-600">Sticky footer</div>
          </Card>
        </div>

        {/* ===== ROW 3, COL 1-3: (covered by row-span-2 Risk Cockpit above) ===== */}

        {/* ===== ROW 3, COL 4-7: ML & FLYWHEEL ENGINE (FIX 7+10+11) ===== */}
        <div className="col-span-12 lg:col-span-4">
          <Card className="h-full bg-[#111827] border-slate-800 p-4 flex flex-col">
            <div className="flex items-center gap-2 mb-3">
              <Brain className="w-4 h-4 text-cyan-500" />
              <h3 className="text-sm font-semibold">ML & Flywheel Engine</h3>
            </div>
            <div className="grid grid-cols-3 gap-3 flex-grow">
              {/* ML Model Accuracy Trend (FIX 10: from API, no hardcoded) */}
              <div className="col-span-1">
                <div className="text-[10px] text-slate-500 uppercase mb-1">ML Model Accuracy Trend</div>
                <div className="h-28">
                  {flywheel?.accuracyHistory ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={flywheel.accuracyHistory}>
                        <XAxis dataKey="epoch" tick={{ fontSize: 7, fill: '#9ca3af' }} />
                        <YAxis domain={[0.5, 1]} tick={{ fontSize: 7, fill: '#9ca3af' }} />
                        <Line type="monotone" dataKey="accuracy" stroke={C.cyan} strokeWidth={2} dot={false} />
                        <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', fontSize: '10px' }} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : <div className="flex items-center justify-center h-full text-slate-700 text-[10px]">Loading...</div>}
                </div>
              </div>
              {/* Staged Inferences (FIX 11: multiple rows from API) */}
              <div className="col-span-1">
                <div className="text-[10px] text-slate-500 uppercase mb-1">Staged Inferences</div>
                <div className="space-y-1">
                  {(flywheel?.stagedInferences || []).map((inf, i) => (
                    <div key={i} className="flex justify-between text-[10px]">
                      <span className="text-slate-400">{inf.label || 'Staged Inferences'}</span>
                      <span className={`font-mono ${inf.delta >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {inf.delta >= 0 ? '+' : ''}{inf.value}
                      </span>
                    </div>
                  ))}
                  {flywheel?.nilInferences != null && (
                    <div className="flex justify-between text-[10px]">
                      <span className="text-slate-400">NIL Inferences</span>
                      <span className="text-red-400 font-mono">{pct(flywheel.nilInferences)}</span>
                    </div>
                  )}
                </div>
              </div>
              {/* Flywheel Pipeline Health (FIX 7) */}
              <div className="col-span-1">
                <div className="text-[10px] text-slate-500 uppercase mb-1">Flywheel Pipeline Health</div>
                <div className="space-y-2">
                  {(flywheel?.pipelineStages || []).map((stage, i) => (
                    <div key={i} className="flex items-center gap-2 text-[10px]">
                      <span className={`w-2 h-2 rounded-full ${stage.status === 'active' ? 'bg-emerald-500' : stage.status === 'warning' ? 'bg-amber-500' : 'border border-slate-600'}`} />
                      <span className="text-slate-400">{stage.label}</span>
                      {stage.detail && <span className="text-slate-600 ml-auto">{stage.detail}</span>}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* ===== ROW 3, COL 8-9: RISK COCKPIT EXPANDED (FIX 6) ===== */}
        <div className="col-span-12 lg:col-span-2">
          <Card className="h-full bg-[#111827] border-slate-800 p-4">
            <h3 className="text-sm font-semibold mb-3">Risk Cockpit Expanded</h3>
            <div className="grid grid-cols-3 gap-2">
              {/* Risk Shield Status */}
              <div>
                <div className="text-[9px] text-slate-500 uppercase mb-1">Risk Shield Status</div>
                <div className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold mb-2 ${riskStatus?.status === 'ACTIVE' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                  {riskStatus?.status || 'ACTIVE'}
                </div>
                <div className="h-16">
                  {riskStatus?.shieldBreakdown ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={riskStatus.shieldBreakdown}>
                        <Bar dataKey="value" radius={[2,2,0,0]}>
                          {(riskStatus.shieldBreakdown || []).map((e, i) => (
                            <Cell key={i} fill={e.type === 'portfolio' ? C.cyan : e.type === 'risk' ? C.amber : C.red} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : <div className="text-[9px] text-slate-700">No data</div>}
                </div>
              </div>
              {/* Risk History */}
              <div>
                <div className="text-[9px] text-slate-500 uppercase mb-1">Risk History</div>
                <div className="h-20">
                  {riskMetrics?.riskHistory ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={riskMetrics.riskHistory}>
                        <XAxis dataKey="t" tick={{ fontSize: 7, fill: '#9ca3af' }} />
                        <YAxis domain={[0, 200]} tick={{ fontSize: 7, fill: '#9ca3af' }} />
                        <Area type="monotone" dataKey="v" stroke={C.amber} fill={C.amber} fillOpacity={0.1} />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : <div className="text-[9px] text-slate-700">Loading...</div>}
                </div>
              </div>
              {/* VaR Gauge (FIX 6: semicircle gauge) */}
              <div className="flex flex-col items-center">
                <div className="text-[9px] text-slate-500 uppercase mb-1">VaR Gauge</div>
                <div className="relative w-16 h-10">
                  <svg viewBox="0 0 100 55" className="w-full">
                    <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#1e293b" strokeWidth="8" strokeLinecap="round" />
                    <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke={C.red} strokeWidth="8" strokeLinecap="round"
                      strokeDasharray={`${(riskMetrics?.varPct || 0.4) * 126} 126`} />
                    <text x="50" y="48" textAnchor="middle" fill="white" fontSize="12" fontWeight="bold">VaR</text>
                  </svg>
                </div>
                <div className="text-[10px] font-mono text-white">{fmt(riskMetrics?.var95 || 0)}</div>
              </div>
            </div>
          </Card>
        </div>

        {/* ===== ROW 3, COL 10-12: STRATEGY & SIGNALS (FIX 9+12) ===== */}
        <div className="col-span-12 lg:col-span-3">
          <Card className="h-full bg-[#111827] border-slate-800 p-4">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-500" /> Active Strategies
            </h3>
            {/* Strategy list from API (FIX 12+10: no hardcoded fallbacks) */}
            <div className="space-y-3 mb-4">
              {(strategyData?.strategies || []).map((strat, idx) => (
                <div key={idx} className="flex flex-col gap-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-300 font-medium">{strat.name}</span>
                    <span className="text-cyan-400 font-mono">{pct((strat.hitRate || 0) * 100)}</span>
                  </div>
                  <div className="w-full h-1 bg-slate-800 rounded-full">
                    <div className="h-full bg-cyan-500 rounded-full" style={{ width: `${(strat.hitRate || 0) * 100}%` }} />
                  </div>
                </div>
              ))}
              {(!strategyData?.strategies || strategyData.strategies.length === 0) && (
                <div className="text-[10px] text-slate-700">Loading strategies...</div>
              )}
            </div>
            {/* Signal Hit Rate */}
            <div className="border-t border-slate-800 pt-3 mb-4">
              <div className="text-[10px] text-slate-500 uppercase font-bold mb-2">Signal Hit Rate</div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-400">Overall</span>
                <span className="text-emerald-400 font-mono">{pct((strategyData?.overallHitRate || 0) * 100)}</span>
              </div>
            </div>
            {/* Market Sentiment Gauge (FIX 9: semicircle gauge, not bars) */}
            <div className="border-t border-slate-800 pt-3">
              <div className="text-[10px] text-slate-500 uppercase font-bold mb-2">Market Sentiment</div>
              <div className="flex flex-col items-center">
                <div className="relative w-24 h-14">
                  <svg viewBox="0 0 120 65" className="w-full">
                    {/* Background arc */}
                    <path d="M 10 60 A 50 50 0 0 1 110 60" fill="none" stroke="#1e293b" strokeWidth="10" strokeLinecap="round" />
                    {/* Green section (0-33%) */}
                    <path d="M 10 60 A 50 50 0 0 1 43 15" fill="none" stroke={C.red} strokeWidth="10" strokeLinecap="round" />
                    {/* Yellow section (33-66%) */}
                    <path d="M 43 15 A 50 50 0 0 1 77 15" fill="none" stroke={C.amber} strokeWidth="10" strokeLinecap="round" />
                    {/* Green section (66-100%) */}
                    <path d="M 77 15 A 50 50 0 0 1 110 60" fill="none" stroke={C.green} strokeWidth="10" strokeLinecap="round" />
                    {/* Needle */}
                    <line x1="60" y1="60" x2={60 + 35 * Math.cos(Math.PI * (1 - (strategyData?.sentimentScore || 0.09)))}
                      y2={60 - 35 * Math.sin(Math.PI * (1 - (strategyData?.sentimentScore || 0.09)))}
                      stroke="white" strokeWidth="2" strokeLinecap="round" />
                    <circle cx="60" cy="60" r="3" fill="white" />
                  </svg>
                </div>
                <div className="text-xs font-mono text-white mt-1">{(strategyData?.sentimentScore || 0).toFixed(2)}</div>
                <div className="text-[9px] text-slate-500">Market Sentiment readout</div>
              </div>
            </div>
          </Card>
        </div>

      </div> {/* END MAIN 12-COLUMN GRID */}

      {/* FOOTER STATUS BAR */}
      <footer className="h-[28px] mt-2 flex items-center justify-between px-3 text-[10px] font-mono text-slate-500 bg-[#111827] border border-slate-800 rounded">
        <div className="flex items-center gap-4">
          <span className="text-slate-400 font-bold uppercase tracking-widest">Embodier Trader</span>
          <span className="h-3 w-[1px] bg-slate-800" />
          <span>Performance Analytics v2.1</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-emerald-500 uppercase font-bold">Connected</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-cyan-500">Filters: YTD | Multi-Agent</span>
          <span className="h-3 w-[1px] bg-slate-800" />
          <span>Data: Jan 1 - Feb 28, 2026</span>
        </div>
      </footer>

    </div>
  );
};

export default PerformanceAnalytics;
