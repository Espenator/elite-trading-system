// frontend-v2/src/pages/RiskIntelligence.jsx
import React, { useState } from 'react';
import { Shield, TrendingDown, Target, Activity, Zap, AlertTriangle, ArrowUpRight } from 'lucide-react';
// IMPORTED Lightweight Chart Components (Uncommented as requested)
import RiskEquityLC from '../components/charts/RiskEquityLC';
import MonteCarloLC from '../components/charts/MonteCarloLC';

const RiskIntelligence = () => {
  const [timeframe, setTimeframe] = useState('3M');

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      
      {/* ─── HEADER ─── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Risk <span className="text-red-500">Intelligence</span>
          </h1>
          <p className="text-sm font-mono text-slate-400 mt-1 flex items-center gap-2">
            <Shield className="w-4 h-4 text-emerald-400" />
            SYSTEM SURVIVABILITY: <span className="text-emerald-400">99.8%</span> | EXPOSURE: <span className="text-yellow-400">MEDIUM</span>
          </p>
        </div>

        {/* Timeframe Selector */}
        <div className="flex bg-slate-800/50 p-1 rounded-lg border border-slate-700/50">
          {['1W', '1M', '3M', 'YTD', '1Y'].map(tf => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-3 py-1.5 text-xs font-bold font-mono rounded transition-colors ${
                timeframe === tf 
                  ? 'bg-red-500/20 text-red-400' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* ─── TOP METRICS GRID ─── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: System Drawdown */}
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4">
          <div className="flex justify-between items-start mb-2">
            <span className="text-slate-400 text-xs font-bold uppercase tracking-wider">Current Drawdown</span>
            <TrendingDown className="w-4 h-4 text-red-400" />
          </div>
          <div className="flex items-end gap-2">
            <span className="text-2xl font-bold font-mono text-white">-4.2%</span>
            <span className="text-xs font-mono text-slate-500 mb-1">vs Peak</span>
          </div>
        </div>

        {/* Metric 2: Win Rate */}
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4">
          <div className="flex justify-between items-start mb-2">
            <span className="text-slate-400 text-xs font-bold uppercase tracking-wider">Algo Win Rate</span>
            <Target className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-end gap-2">
            <span className="text-2xl font-bold font-mono text-white">68.4%</span>
            <span className="text-xs font-mono text-emerald-500 mb-1">+2.1%</span>
          </div>
        </div>

        {/* Metric 3: Value At Risk (VaR) */}
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4">
          <div className="flex justify-between items-start mb-2">
            <span className="text-slate-400 text-xs font-bold uppercase tracking-wider">Daily VaR (95%)</span>
            <AlertTriangle className="w-4 h-4 text-yellow-400" />
          </div>
          <div className="flex items-end gap-2">
            <span className="text-2xl font-bold font-mono text-white">$12,450</span>
            <span className="text-xs font-mono text-slate-500 mb-1">1.2% Cap</span>
          </div>
        </div>

        {/* Metric 4: Sharpe Ratio */}
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4">
          <div className="flex justify-between items-start mb-2">
            <span className="text-slate-400 text-xs font-bold uppercase tracking-wider">Sharpe Ratio</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="flex items-end gap-2">
            <span className="text-2xl font-bold font-mono text-white">2.41</span>
            <span className="text-xs font-mono text-slate-500 mb-1">Excellent</span>
          </div>
        </div>
      </div>

      {/* ─── CHARTS SECTION ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Left Chart: System Equity Curve */}
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg flex flex-col h-[400px]">
          <div className="px-4 py-3 border-b border-slate-700/50 bg-slate-900/40 flex justify-between items-center">
            <h3 className="text-white text-sm font-bold uppercase tracking-wider flex items-center gap-2">
              <Zap className="w-4 h-4 text-cyan-400" />
              Equity Curve vs Benchmark
            </h3>
          </div>
          <div className="flex-1 p-2">
            {/* Wires up the Lightweight Chart for Equity */}
            <RiskEquityLC data={[]} /> 
          </div>
        </div>

        {/* Right Chart: Monte Carlo Simulation */}
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg flex flex-col h-[400px]">
          <div className="px-4 py-3 border-b border-slate-700/50 bg-slate-900/40 flex justify-between items-center">
            <h3 className="text-white text-sm font-bold uppercase tracking-wider flex items-center gap-2">
              <ArrowUpRight className="w-4 h-4 text-emerald-400" />
              Monte Carlo Distribution (N=100)
            </h3>
          </div>
          <div className="flex-1 p-2">
             {/* Wires up the Lightweight Chart for Monte Carlo */}
            <MonteCarloLC data={[]} />
          </div>
        </div>

      </div>

      {/* ─── BOTTOM SECTION: ACTIVE RISK LIMITS TABLE ─── */}
      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg min-h-[250px]">
        <div className="px-4 py-3 border-b border-slate-700/50 bg-slate-900/40">
          <h3 className="text-white text-sm font-bold uppercase tracking-wider">
            Active Risk Limits & Guardrails
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm font-mono">
            <thead className="bg-slate-900/80">
              <tr>
                <th className="px-4 py-3 text-slate-400 text-xs font-bold uppercase tracking-wider border-b border-slate-700/50">Parameter</th>
                <th className="px-4 py-3 text-slate-400 text-xs font-bold uppercase tracking-wider border-b border-slate-700/50">Current Value</th>
                <th className="px-4 py-3 text-slate-400 text-xs font-bold uppercase tracking-wider border-b border-slate-700/50">Hard Limit</th>
                <th className="px-4 py-3 text-slate-400 text-xs font-bold uppercase tracking-wider border-b border-slate-700/50">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              <tr className="hover:bg-slate-700/30">
                <td className="px-4 py-3 text-slate-300">Max Portfolio Heat</td>
                <td className="px-4 py-3 text-white font-bold">14.5%</td>
                <td className="px-4 py-3 text-slate-400">20.0%</td>
                <td className="px-4 py-3"><span className="px-2 py-1 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400">NORMAL</span></td>
              </tr>
              <tr className="hover:bg-slate-700/30">
                <td className="px-4 py-3 text-slate-300">Max Sector Exposure (Tech)</td>
                <td className="px-4 py-3 text-yellow-400 font-bold">28.4%</td>
                <td className="px-4 py-3 text-slate-400">30.0%</td>
                <td className="px-4 py-3"><span className="px-2 py-1 rounded text-[10px] font-bold bg-yellow-500/20 text-yellow-400">WARNING</span></td>
              </tr>
              <tr className="hover:bg-slate-700/30">
                <td className="px-4 py-3 text-slate-300">Max Position Size</td>
                <td className="px-4 py-3 text-white font-bold">4.2%</td>
                <td className="px-4 py-3 text-slate-400">5.0%</td>
                <td className="px-4 py-3"><span className="px-2 py-1 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400">NORMAL</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};

export default RiskIntelligence;
