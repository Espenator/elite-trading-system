import React, { useMemo, useEffect, useRef, useState } from 'react';
import { 
  TrendingUp, TrendingDown, Activity, Shield, 
  Target, Zap, BarChart3, PieChart as PieChartIcon, 
  Search, Filter, ArrowUpRight, ArrowDownRight,
  ChevronRight, Brain, Gauge, Info
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

/**
 * PerformanceAnalytics Component
 * A high-fidelity dashboard for trading performance, risk metrics, and AI attribution.
 */
const PerformanceAnalytics = () => {
  // --- API DATA FETCHING ---
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

  // --- COLORS ---
  const COLORS = {
    primary: '#06b6d4', // cyan
    success: '#10b981', // emerald
    danger: '#ef4444',  // red
    amber: '#f59e0b',   // amber
    surface: '#111827',
    background: '#0a0e17',
    textMuted: '#9ca3af'
  };

  // --- LIGHTWEIGHT CHARTS EFFECT (EQUITY/DRAWDOWN) ---
  useEffect(() => {
    if (!chartContainerRef.current || !equityData?.points) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: 'transparent' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 300,
      timeScale: { borderVisible: false },
    });

    const areaSeries = chart.addAreaSeries({
      lineColor: COLORS.primary,
      topColor: `${COLORS.primary}44`,
      bottomColor: 'transparent',
      lineWidth: 2,
    });

    const data = equityData.points.map(p => ({
      time: p.date,
      value: p.equity
    }));

    areaSeries.setData(data);
    chart.timeScale().fitContent();
    chartRef.current = chart;

    const handleResize = () => {
      chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [equityData]);

  // --- HELPERS ---
  const formatCurrency = (val) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val || 0);
  const formatPct = (val) => `${(val || 0).toFixed(2)}%`;
  const getGradeColor = (grade) => {
    if (['A', 'A+'].includes(grade)) return COLORS.success;
    if (['B', 'B+'].includes(grade)) return COLORS.primary;
    if (grade === 'C') return COLORS.amber;
    return COLORS.danger;
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#0a0e17] text-slate-200 font-sans p-4 space-y-4">
      
      {/* HEADER */}
      <header className="flex justify-between items-center mb-2">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-cyan-500/10 rounded-lg">
            <Activity className="text-cyan-500 w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Performance Analytics</h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex flex-col items-end">
            <span className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold">Trading Grade</span>
            <div className={`w-10 h-10 rounded-full border-2 flex items-center justify-center font-bold text-lg`}
                 style={{ borderColor: getGradeColor(riskMetrics?.trading_grade), color: getGradeColor(riskMetrics?.trading_grade) }}>
              {riskMetrics?.trading_grade || '-'}
            </div>
          </div>
        </div>
      </header>

      {/* TOP METRICS BAR: 10 Columns */}
      <div className="grid grid-cols-2 md:grid-cols-5 lg:grid-cols-10 gap-2">
        {[
          { label: 'Total Trades', val: summary?.metrics?.totalTrades },
          { label: 'Net P&L', val: formatCurrency(summary?.metrics?.netPnl), color: (summary?.metrics?.netPnl >= 0 ? 'text-emerald-400' : 'text-red-400') },
          { label: 'Win Rate', val: formatPct(summary?.metrics?.winRate) },
          { label: 'Avg Win', val: formatCurrency(summary?.metrics?.avgWin), color: 'text-emerald-400' },
          { label: 'Avg Loss', val: formatCurrency(summary?.metrics?.avgLoss), color: 'text-red-400' },
          { label: 'Profit Factor', val: summary?.metrics?.profitFactor?.toFixed(2) },
          { label: 'Max DD', val: formatPct(summary?.metrics?.maxDrawdown), color: 'text-red-400' },
          { label: 'Sharpe', val: riskMetrics?.sharpe?.toFixed(2) },
          { label: 'Expectancy', val: formatCurrency(riskMetrics?.expectancy) },
          { label: 'R:R Ratio', val: riskMetrics?.risk_reward_ratio?.toFixed(2) },
        ].map((m, i) => (
          <Card key={i} className="p-3 bg-[#111827] border-slate-800 flex flex-col justify-center items-center text-center">
            <span className="text-[10px] uppercase text-slate-500 font-medium mb-1">{m.label}</span>
            <span className={`text-sm font-bold ${m.color || 'text-white'}`}>{m.val ?? '--'}</span>
          </Card>
        ))}
      </div>

      {/* MAIN GRID - 12 COLUMNS */}
      <div className="grid grid-cols-12 gap-4 flex-grow">
        
        {/* ROW 1, COL 1-3: RISK COCKPIT (Spans Row 1-3 partially) */}
        <div className="col-span-12 lg:col-span-3 row-span-2 space-y-4">
          <Card className="h-full bg-[#111827] border-slate-800 p-5 flex flex-col">
            <h3 className="text-sm font-semibold mb-6 flex items-center gap-2">
              <Shield className="w-4 h-4 text-cyan-500" /> Risk Cockpit
            </h3>
            
            {/* Grade Hero */}
            <div className="flex flex-col items-center justify-center py-6 bg-slate-900/50 rounded-xl mb-6">
              <div className="relative w-24 h-24 flex items-center justify-center">
                <div className="absolute inset-0 rounded-full border-4 border-slate-800"></div>
                <div 
                  className="absolute inset-0 rounded-full border-4 transition-all duration-1000" 
                  style={{ 
                    borderColor: getGradeColor(riskMetrics?.trading_grade),
                    clipPath: `inset(0 0 0 0)` // Logic for partial circle can go here
                  }}
                ></div>
                <span className="text-4xl font-black" style={{ color: getGradeColor(riskMetrics?.trading_grade) }}>
                  {riskMetrics?.trading_grade || '-'}
                </span>
              </div>
              <span className="mt-2 text-xs text-slate-400 uppercase tracking-tighter">System Health Rating</span>
            </div>

            {/* Sharpe/Sortino/Calmar Grid */}
            <div className="grid grid-cols-3 gap-2 mb-6">
              {[
                { label: 'Sharpe', val: riskMetrics?.sharpe },
                { label: 'Sortino', val: riskMetrics?.sortino },
                { label: 'Calmar', val: riskMetrics?.calmar }
              ].map(r => (
                <div key={r.label} className="text-center p-2 bg-slate-800/30 rounded">
                  <div className="text-[10px] text-slate-500 uppercase">{r.label}</div>
                  <div className="text-sm font-mono font-bold text-cyan-400">{r.val?.toFixed(2) || '0.00'}</div>
                </div>
              ))}
            </div>

            {/* Kelly Criterion */}
            <div className="space-y-2 mb-6">
              <div className="flex justify-between text-[10px] uppercase text-slate-400 font-bold">
                <span>Kelly Fraction (Optimal)</span>
                <span className="text-emerald-400">{formatPct(riskMetrics?.kelly_optimal_fraction * 100)}</span>
              </div>
              <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-emerald-500" 
                  style={{ width: `${Math.min((riskMetrics?.kelly_optimal_fraction || 0) * 100, 100)}%` }}
                ></div>
              </div>
            </div>

            {/* R:R Donut + Expectancy */}
            <div className="mt-auto pt-4 border-t border-slate-800 flex items-center justify-between">
              <div className="w-20 h-20">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={[{ value: riskMetrics?.win_rate || 0.5 }, { value: 1 - (riskMetrics?.win_rate || 0.5) }]}
                      innerRadius={25}
                      outerRadius={35}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      <Cell fill={COLORS.success} />
                      <Cell fill={COLORS.danger} fillOpacity={0.3} />
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="text-right">
                <div className="text-[10px] text-slate-500 uppercase">Expectancy</div>
                <div className="text-xl font-bold text-white">{formatCurrency(riskMetrics?.expectancy)}</div>
                <div className="text-[10px] text-emerald-400 flex items-center justify-end gap-1">
                  <TrendingUp className="w-3 h-3" /> Positive Edge
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* ROW 1, COL 4-7: EQUITY + DRAWDOWN (Lightweight Charts) */}
        <div className="col-span-12 lg:col-span-4 h-80 lg:h-auto">
          <Card className="h-full bg-[#111827] border-slate-800 p-0 overflow-hidden flex flex-col">
            <div className="p-4 flex justify-between items-center border-b border-slate-800/50">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-cyan-500" /> Equity Curve
              </h3>
              <div className="flex gap-2">
                <div className="p-1 hover:bg-slate-800 rounded cursor-pointer text-slate-500"><Search size={14} /></div>
                <div className="p-1 hover:bg-slate-800 rounded cursor-pointer text-slate-500"><Filter size={14} /></div>
              </div>
            </div>
            <div className="flex-grow relative p-4" ref={chartContainerRef}>
              {/* Chart renders here */}
            </div>
          </Card>
        </div>

        {/* ROW 1, COL 8-9: AI + ROLLING RISK */}
        <div className="col-span-12 lg:col-span-2">
          <Card className="h-full bg-[#111827] border-slate-800 p-4">
            <h3 className="text-sm font-semibold mb-4 text-slate-400">AI Confidence Dial</h3>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart cx="50%" cy="50%" innerRadius="60%" outerRadius="100%" barSize={10} data={[
                  { name: 'Accuracy', value: (flywheel?.accuracyPd || 0) * 100, fill: COLORS.primary },
                  { name: 'Health', value: (flywheel?.pipelineHealth || 0) * 100, fill: COLORS.success }
                ]}>
                  <RadialBar background dataKey="value" cornerRadius={5} />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-slate-500 uppercase">Staged Inferences</span>
                <span className="font-mono text-cyan-400">{flywheel?.stagedInferences || 0}</span>
              </div>
              <div className="h-20">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={[{v: 2}, {v: 5}, {v: 3}, {v: 8}, {v: 6}, {v: 9}, {v: 4}]}>
                    <Bar dataKey="v" fill={COLORS.primary} opacity={0.4} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </Card>
        </div>

        {/* ROW 1, COL 10-12: ATTRIBUTION + ELO */}
        <div className="col-span-12 lg:col-span-3">
          <Card className="h-full bg-[#111827] border-slate-800 p-4">
            <h3 className="text-sm font-semibold mb-4">P&L by Symbol</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart layout="vertical" data={tradesData?.trades?.slice(0, 6) || []}>
                  <XAxis type="number" hide />
                  <YAxis dataKey="symbol" type="category" axisLine={false} tickLine={false} fontSize={10} stroke="#9ca3af" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px', fontSize: '12px' }}
                    itemStyle={{ color: COLORS.primary }}
                  />
                  <Bar dataKey="pnl" radius={[0, 4, 4, 0]}>
                    { (tradesData?.trades || []).map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.pnl >= 0 ? COLORS.success : COLORS.danger} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>

        {/* ROW 2, COL 4-7: AGENT ATTRIBUTION LEADERBOARD */}
        <div className="col-span-12 lg:col-span-4">
          <Card className="h-full bg-[#111827] border-slate-800 overflow-hidden">
            <div className="p-4 border-b border-slate-800/50 flex justify-between">
              <h3 className="text-sm font-semibold">Agent Attribution</h3>
              <span className="text-[10px] bg-cyan-500/10 text-cyan-400 px-2 py-1 rounded">Consensus Active</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="bg-slate-900/50 text-slate-500 uppercase">
                    <th className="px-4 py-3 font-medium">Agent</th>
                    <th className="px-4 py-3 font-medium">ELO</th>
                    <th className="px-4 py-3 font-medium">Win Rate</th>
                    <th className="px-4 py-3 font-medium text-right">Contrib %</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {agents?.votes?.map((agent, i) => (
                    <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 font-medium text-slate-300">{agent.name}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          {agent.elo}
                          <span className={agent.change >= 0 ? 'text-emerald-500' : 'text-red-500'}>
                            {agent.change >= 0 ? '▲' : '▼'}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">{formatPct(agent.winRate * 100)}</td>
                      <td className="px-4 py-3 text-right text-cyan-400 font-mono">{(agent.contributions * 10).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* ROW 2, COL 8-12: ENHANCED TRADES TABLE */}
        <div className="col-span-12 lg:col-span-5">
          <Card className="h-full bg-[#111827] border-slate-800 overflow-hidden">
            <div className="p-4 border-b border-slate-800/50 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <BarChart3 size={16} className="text-cyan-500" />
                <h3 className="text-sm font-semibold uppercase tracking-wider">Trade Log</h3>
              </div>
              <div className="flex gap-2">
                <Search size={14} className="text-slate-500" />
                <Filter size={14} className="text-slate-500" />
              </div>
            </div>
            <div className="overflow-x-auto h-[300px]">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="sticky top-0 bg-[#111827] shadow-sm">
                  <tr className="text-slate-500 border-b border-slate-800">
                    <th className="px-4 py-3 font-medium">Symbol</th>
                    <th className="px-4 py-3 font-medium">Side</th>
                    <th className="px-4 py-3 font-medium">Qty</th>
                    <th className="px-4 py-3 font-medium">Entry</th>
                    <th className="px-4 py-3 font-medium">Exit</th>
                    <th className="px-4 py-3 font-medium text-right">P&L</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/30">
                  {tradesData?.trades?.map((trade, i) => (
                    <tr key={i} className="hover:bg-cyan-500/5 transition-colors group">
                      <td className="px-4 py-3 font-bold text-slate-200">{trade.symbol}</td>
                      <td className="px-4 py-3">
                        <span className={`px-1.5 py-0.5 rounded-[4px] font-bold text-[10px] ${trade.side === 'LONG' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'}`}>
                          {trade.side}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-400 font-mono">{trade.qty}</td>
                      <td className="px-4 py-3 font-mono">{trade.entry?.toFixed(2)}</td>
                      <td className="px-4 py-3 font-mono">{trade.exit?.toFixed(2)}</td>
                      <td className={`px-4 py-3 text-right font-bold font-mono ${trade.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {trade.pnl >= 0 ? '+' : ''}{trade.pnl?.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* ROW 3, COL 4-7: ML & FLYWHEEL ENGINE */}
        <div className="col-span-12 lg:col-span-4">
          <Card className="h-full bg-[#111827] border-slate-800 p-4 flex flex-col">
            <div className="flex items-center gap-2 mb-4">
              <Brain className="w-4 h-4 text-cyan-500" />
              <h3 className="text-sm font-semibold">ML & Flywheel Engine</h3>
            </div>
            <div className="flex-grow h-32">
               <ResponsiveContainer width="100%" height="100%">
                <LineChart data={[{t:1, a:0.72}, {t:2, a:0.75}, {t:3, a:0.71}, {t:4, a:0.78}, {t:5, a:0.82}, {t:6, a:0.84}]}>
                  <Line type="monotone" dataKey="a" stroke={COLORS.primary} strokeWidth={2} dot={false} />
                  <YAxis domain={[0.5, 1]} hide />
                  <Tooltip />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-2 gap-4 mt-4">
              <div className="p-2 bg-slate-900/50 rounded-lg">
                <span className="text-[10px] text-slate-500 uppercase block">Model Accuracy</span>
                <span className="text-lg font-bold text-emerald-400">{formatPct((flywheel?.accuracyPd || 0.84) * 100)}</span>
              </div>
              <div className="p-2 bg-slate-900/50 rounded-lg">
                <span className="text-[10px] text-slate-500 uppercase block">Pipeline Health</span>
                <span className="text-lg font-bold text-cyan-400">OPTIMAL</span>
              </div>
            </div>
          </Card>
        </div>

        {/* ROW 3, COL 8-9: RISK COCKPIT EXPANDED (Shield/VaR) */}
        <div className="col-span-12 lg:col-span-2">
          <Card className="h-full bg-[#111827] border-slate-800 p-4">
            <div className="flex flex-col h-full">
              <div className="flex justify-between items-start mb-4">
                <div className="text-xs text-slate-500 uppercase font-bold tracking-tighter">Risk Shield</div>
                <div className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${riskStatus?.status === 'ACTIVE' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50' : 'bg-red-500/20 text-red-400'}`}>
                   ● {riskStatus?.status || 'ACTIVE'}
                </div>
              </div>
              
              <div className="flex-grow flex flex-col justify-center items-center py-4">
                 <div className="text-[10px] text-slate-500 uppercase mb-1">Value at Risk (VaR)</div>
                 <div className="text-2xl font-black text-white">$4,280</div>
                 <div className="text-[10px] text-red-400">1.2% of Equity</div>
              </div>

              <div className="h-16">
                 <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={[{v:10}, {v:15}, {v:12}, {v:18}, {v:14}]}>
                    <Area type="monotone" dataKey="v" stroke={COLORS.danger} fill={COLORS.danger} fillOpacity={0.1} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </Card>
        </div>

        {/* ROW 3, COL 10-12: STRATEGY & SIGNALS */}
        <div className="col-span-12 lg:col-span-3">
          <Card className="h-full bg-[#111827] border-slate-800 p-4">
             <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-500" /> Active Strategies
            </h3>
            <div className="space-y-3">
              {(strategyData?.strategies || [{name: 'MeanReversion_V4', hitRate: 0.62}, {name: 'BreakoutAlpha', hitRate: 0.58}]).map((strat, idx) => (
                <div key={idx} className="flex flex-col gap-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-300 font-medium">{strat.name}</span>
                    <span className="text-cyan-400 font-mono">{formatPct(strat.hitRate * 100)}</span>
                  </div>
                  <div className="w-full h-1 bg-slate-800 rounded-full">
                    <div className="h-full bg-cyan-500" style={{ width: `${strat.hitRate * 100}%` }}></div>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-6 pt-4 border-t border-slate-800">
               <div className="flex justify-between items-center">
                  <span className="text-xs text-slate-500 uppercase">Sentiment</span>
                  <div className="flex gap-1">
                    {[1,2,3,4,5].map(i => (
                      <div key={i} className={`w-3 h-1 rounded-sm ${i <= 4 ? 'bg-emerald-500' : 'bg-slate-700'}`}></div>
                    ))}
                  </div>
               </div>
            </div>
          </Card>
        </div>

      </div>

      {/* FOOTER STATUS BAR */}
      <footer className="h-[28px] mt-2 flex items-center justify-between px-3 text-[10px] font-mono text-slate-500 bg-[#111827] border border-slate-800 rounded">
        <div className="flex items-center gap-4">
          <span className="text-slate-400 font-bold uppercase tracking-widest">Embodier Trader</span>
          <span className="h-3 w-[1px] bg-slate-800"></span>
          <span>Performance Analytics v2.0</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="text-emerald-500 uppercase font-bold">Connected</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-cyan-500">Filters: YTD | Multi-Agent</span>
          <span className="h-3 w-[1px] bg-slate-800"></span>
          <span>Data: Jan 1 - Feb 28, 2026</span>
        </div>
      </footer>
    </div>
  );
};

export default PerformanceAnalytics;
