// frontend/src/app/signals/page.tsx
'use client';

import React, { useEffect, useState } from 'react';
import { useTradingStore } from '@/lib/store';
import { TradingSignal, SystemHealth } from '@/lib/types';
import { 
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend 
} from 'recharts';

// ─── Component: Signal Strength Gauge ─────────────────────────
function SignalStrengthGauge({ score }: { score: number }) {
  // Score 0-100. Split into 3 zones for visual context.
  const data = [
    { name: 'Weak', value: 30, color: '#ef4444' }, // Red
    { name: 'Neutral', value: 40, color: '#fbbf24' }, // Yellow
    { name: 'Strong', value: 30, color: '#10b981' }, // Green
  ];

  // Calculate needle rotation (-90 to 90 degrees)
  const rotation = -90 + (score / 100) * 180;

  return (
    <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4 relative h-[220px] flex flex-col items-center justify-center">
      <h3 className="absolute top-4 left-4 text-white text-xs font-bold uppercase tracking-wider">
        Market Conviction
      </h3>
      <div className="w-full h-[140px] relative mt-6">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="100%"
              startAngle={180}
              endAngle={0}
              innerRadius={60}
              outerRadius={85}
              paddingAngle={2}
              dataKey="value"
              stroke="none"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        {/* Needle */}
        <div 
          className="absolute bottom-0 left-[50%] w-1 h-[70px] bg-white origin-bottom transition-all duration-700 ease-out z-10"
          style={{ transform: `translateX(-50%) rotate(${rotation}deg)` }}
        >
          <div className="w-4 h-4 rounded-full bg-white absolute bottom-[-8px] left-[-6px] shadow-lg shadow-black/50" />
        </div>
      </div>
      <div className="mt-2 text-center">
        <span className="text-3xl font-bold font-mono text-white">{score.toFixed(0)}</span>
        <span className="text-slate-400 text-xs ml-1 font-mono">/ 100</span>
        <p className={`text-xs font-bold uppercase mt-1 tracking-wider
          ${score > 70 ? 'text-emerald-400' : score < 30 ? 'text-red-400' : 'text-yellow-400'}`}>
          {score > 70 ? 'Strong Buy' : score < 30 ? 'Strong Sell' : 'Neutral'}
        </p>
      </div>
    </div>
  );
}

// ─── Component: Market Regime Scanner ─────────────────────────
function MarketRegimePanel({ health }: { health: SystemHealth }) {
  const regimes = [
    { name: 'Low Vol', active: health.status === 'online' },
    { name: 'High Vol', active: health.status === 'degraded' },
    { name: 'Trend', active: true },
    { name: 'Range', active: false },
    { name: 'Crash', active: false },
  ];

  return (
    <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4 h-[220px]">
      <h3 className="text-white text-xs font-bold uppercase tracking-wider mb-4">
        Market Regime Detection
      </h3>
      <div className="grid grid-cols-2 gap-3">
        {regimes.map(r => (
          <div key={r.name} className={`
            flex items-center justify-between px-3 py-2 rounded border transition-all
            ${r.active 
              ? 'bg-blue-500/20 border-blue-500/50 shadow-[0_0_10px_rgba(59,130,246,0.3)]' 
              : 'bg-slate-900/40 border-slate-800 text-slate-500 opacity-50'}
          `}>
            <span className={`text-xs font-bold uppercase ${r.active ? 'text-white' : 'text-slate-500'}`}>
              {r.name}
            </span>
            {r.active && <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />}
          </div>
        ))}
      </div>
      <div className="mt-4 pt-3 border-t border-slate-700/50">
         <div className="flex justify-between items-center text-xs text-slate-400 mb-1">
            <span>VIX Index</span>
            <span className="text-white font-mono">14.24</span>
         </div>
         <div className="flex justify-between items-center text-xs text-slate-400">
            <span>Put/Call Ratio</span>
            <span className="text-emerald-400 font-mono">0.82</span>
         </div>
      </div>
    </div>
  );
}

// ─── Component: Agent Consensus Chart ─────────────────────────
function AgentConsensusChart({ signals }: { signals: TradingSignal[] }) {
  // Aggregate agent votes from signals
  const data = [
    { name: 'Trend', buy: 12, sell: 4 },
    { name: 'Velez', buy: 8, sell: 2 },
    { name: 'Vol', buy: 15, sell: 3 },
    { name: 'Breakout', buy: 6, sell: 8 },
    { name: 'Sentiment', buy: 10, sell: 5 },
  ];

  return (
    <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4 h-[220px]">
      <h3 className="text-white text-xs font-bold uppercase tracking-wider mb-2">
        AI Agent Consensus
      </h3>
      <ResponsiveContainer width="100%" height="85%">
        <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
          <XAxis type="number" stroke="#64748b" fontSize={10} hide />
          <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={10} width={60} />
          <Tooltip 
            contentStyle={{ backgroundColor: '#1e293b', borderColor: '#475569', fontSize: '12px' }}
            itemStyle={{ color: '#fff' }}
            cursor={{fill: 'rgba(255,255,255,0.05)'}}
          />
          <Legend wrapperStyle={{ fontSize: '10px', paddingTop: '5px' }} />
          <Bar dataKey="buy" name="Buy Votes" fill="#10b981" stackId="a" barSize={12} radius={[0, 4, 4, 0]} />
          <Bar dataKey="sell" name="Sell Votes" fill="#ef4444" stackId="a" barSize={12} radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─── Component: Massive Factor Analysis Table ─────────────────
function FactorAnalysisTable({ signals }: { signals: TradingSignal[] }) {
  const cols = [
    'Time', 'Symbol', 'Signal Type', 'Direction', 'Confidence', 'Price', 'Score', 
    'Velez', 'Compression', 'Rel Vol', 'Opt Flow', 'Sentiment', 'Catalyst', 
    'Take Profit', 'Stop Loss', 'R:R', 'Volatility', 'Liquidity', 'Status'
  ];

  return (
    <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg flex-1 flex flex-col min-h-[500px]">
      <div className="px-4 py-3 border-b border-slate-700/50 flex justify-between items-center bg-slate-900/40">
        <div className="flex items-center gap-4">
          <h3 className="text-white text-sm font-bold uppercase tracking-wider">
            Live Signal Factor Analysis
          </h3>
          <span className="px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 text-[10px] font-bold uppercase">
            {signals.length} Signals Active
          </span>
        </div>
        <div className="flex gap-2">
           <button className="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs font-bold transition-colors text-slate-200">Export CSV</button>
           <button className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 rounded text-xs font-bold transition-colors text-white">Auto-Execute All > 90%</button>
        </div>
      </div>
      
      <div className="flex-1 overflow-auto">
        <table className="w-full text-left whitespace-nowrap text-[11px] font-mono">
          <thead className="bg-slate-900/80 sticky top-0 z-10">
            <tr>
              {cols.map(c => (
                <th key={c} className="px-4 py-3 text-slate-400 font-bold uppercase tracking-wider border-b border-slate-700/50 text-[10px]">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {signals.map((sig) => (
              <tr key={sig.id} className="hover:bg-slate-700/30 transition-colors group cursor-pointer">
                <td className="px-4 py-2 text-slate-400">{new Date(sig.timestamp).toLocaleTimeString()}</td>
                <td className="px-4 py-2 text-white font-bold text-sm">{sig.symbol}</td>
                <td className="px-4 py-2">
                  <span className="px-2 py-0.5 rounded bg-slate-700/50 text-slate-300 font-semibold border border-slate-600/50">
                    {sig.type.replace(/_/g, ' ')}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase
                    ${sig.direction === 'long' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                    {sig.direction}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full ${sig.confidence > 80 ? 'bg-emerald-400' : sig.confidence > 50 ? 'bg-yellow-400' : 'bg-red-400'}`}
                        style={{ width: `${sig.confidence}%` }} 
                      />
                    </div>
                    <span className="text-white font-bold">{sig.confidence}%</span>
                  </div>
                </td>
                <td className="px-4 py-2 text-white font-mono">${sig.entryPrice.toFixed(2)}</td>
                <td className="px-4 py-2 text-cyan-400 font-bold">A+</td>
                <td className="px-4 py-2 text-emerald-400">9/10</td>
                <td className="px-4 py-2 text-yellow-400">Medium</td>
                <td className="px-4 py-2 text-white">2.4x</td>
                <td className="px-4 py-2 text-emerald-400">Bullish</td>
                <td className="px-4 py-2 text-slate-300">Neutral</td>
                <td className="px-4 py-2 text-slate-400 max-w-[150px] truncate">Earnings Beat</td>
                <td className="px-4 py-2 text-emerald-400 font-mono">${sig.takeProfit.toFixed(2)}</td>
                <td className="px-4 py-2 text-red-400 font-mono">${sig.stopLoss.toFixed(2)}</td>
                <td className="px-4 py-2 text-white">1:3.2</td>
                <td className="px-4 py-2 text-slate-400">2.1%</td>
                <td className="px-4 py-2 text-slate-400">High</td>
                <td className="px-4 py-2">
                  <span className="text-yellow-400 animate-pulse">PENDING</span>
                </td>
              </tr>
            ))}
            {signals.length === 0 && (
              <tr>
                <td colSpan={19} className="px-4 py-12 text-center text-slate-500">
                  <div className="flex flex-col items-center justify-center gap-2">
                    <span className="animate-spin text-2xl">⚡</span>
                    <span>Scanning market for high-probability setups...</span>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ═════════════════════════════════════════════════════════════════
// ─── MAIN SIGNALS PAGE ASSEMBLY ───────────────────────────────
// ═════════════════════════════════════════════════════════════════
export default function SignalsPage() {
  const { latestSignals, systemHealth, connect } = useTradingStore();
  const [marketScore, setMarketScore] = useState(68);

  // Connect to WebSocket on mount
  useEffect(() => {
    connect();
    // Simulate fluctuating market score for the gauge
    const interval = setInterval(() => {
      setMarketScore(prev => Math.min(100, Math.max(0, prev + (Math.random() - 0.5) * 5)));
    }, 2000);
    return () => clearInterval(interval);
  }, [connect]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white p-4">
      
      {/* ─── Top Stats Bar ─── */}
      <div className="flex items-center justify-between mb-4 px-2">
         <h1 className="text-2xl font-bold text-white tracking-tight">
           Signal Generation <span className="text-cyan-500">Center</span>
         </h1>
         <div className="flex gap-4 text-xs font-mono text-slate-400">
            <span className="flex items-center gap-1">
               <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
               SCANNER ACTIVE
            </span>
            <span>|</span>
            <span>CHECKING 5,402 SYMBOLS</span>
            <span>|</span>
            <span>LATENCY: 12ms</span>
         </div>
      </div>

      {/* ─── Top Row: 3 Visual Panels (Gauge, Regime, Consensus) ─── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <SignalStrengthGauge score={marketScore} />
        <MarketRegimePanel health={systemHealth} />
        <AgentConsensusChart signals={latestSignals} />
      </div>

      {/* ─── Main Content: Massive Factor Analysis Table ─── */}
      <div className="flex flex-col h-[calc(100vh-320px)] min-h-[500px]">
        <FactorAnalysisTable signals={latestSignals} />
      </div>

    </div>
  );
}
