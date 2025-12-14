import React, { useState, useEffect } from 'react';
import { Bell, Settings, Moon, Sun } from 'lucide-react';

export function Header() {
  const [theme, setTheme] = useState('dark');
  const [indices, setIndices] = useState({ spy: { price: 487.23, change: 1.25 }, qqq: { price: 410.56, change: 2.15 }, vix: { price: 14.32, change: -0.8 } });

  useEffect(() => {
    const interval = setInterval(() => {
      setIndices(prev => ({ spy: { ...prev.spy, price: prev.spy.price + (Math.random() - 0.5) * 0.5 }, qqq: { ...prev.qqq, price: prev.qqq.price + (Math.random() - 0.5) * 0.5 }, vix: { ...prev.vix, price: prev.vix.price + (Math.random() - 0.5) * 0.5 } }));
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 bg-slate-900 border-b border-slate-700 flex items-center justify-between px-6">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-cyan-500 rounded-lg flex items-center justify-center font-bold text-slate-900">E</div>
        <span className="text-lg font-bold text-cyan-400">ELITE TRADER</span>
      </div>
      <div className="flex gap-6">
        <div className="text-sm"><span className="text-slate-400">SPY</span><span className="ml-2 font-mono font-bold">\</span><span className={\ml-2 \\}>{indices.spy.change >= 0 ? '+' : ''}{indices.spy.change.toFixed(2)}%</span></div>
        <div className="text-sm"><span className="text-slate-400">QQQ</span><span className="ml-2 font-mono font-bold">\</span><span
@"
import React, { useState } from 'react';
import { TrendingUp, AlertTriangle, BarChart3 } from 'lucide-react';

export function LeftSidebar() {
  const [tradingState] = useState('ACTIVE');

  return (
    <div className="p-4 space-y-6 h-full overflow-y-auto">
      <div className="bg-gradient-to-r from-green-900 to-green-800 rounded-lg p-4 border border-green-700">
        <div className="flex items-center gap-2 mb-2"><TrendingUp size={20} className="text-green-400" /><span className="text-sm font-bold text-green-300">MARKET REGIME</span></div>
        <div className="text-lg font-bold text-green-300">BULLISH TREND</div>
        <div className="text-xs text-green-200 mt-1">VIX: 14.2 | RSI: 65</div>
      </div>
      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
        <div className="text-xs text-slate-400 mb-2">TRADING STATE</div>
        <div className="flex items-center gap-2"><div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" /><span className="font-bold text-green-400">{tradingState}</span></div>
      </div>
      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
        <div className="text-xs text-slate-400 mb-3 flex items-center gap-2"><AlertTriangle size={16} />RISK SHIELD</div>
        <div className="space-y-1 text-xs">
          <div className="flex items-center gap-2"><span className="text-green-400">✓</span><span>Position Count: 5/15</span></div>
          <div className="flex items-center gap-2"><span className="text-green-400">✓</span><span>Position Size: 8.5%</span></div>
          <div className="flex items-center gap-2"><span className="text-green-400">✓</span><span>Daily Loss: -0.8%</span></div>
          <div className="flex items-center gap-2"><span className="text-green-400">✓</span><span>ML Confidence: 85%</span></div>
        </div>
      </div>
      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 space-y-3">
        <div className="text-xs text-slate-400 flex items-center gap-2"><BarChart3 size={16} />PERFORMANCE</div>
        <div><div className="text-xs text-slate-400">Win Rate</div><div className="text-lg font-bold text-green-400">68.4%</div></div>
        <div><div className="text-xs text-slate-400">Sharpe Ratio</div><div className="text-lg font-bold text-cyan-400">1.82</div></div>
        <div><div className="text-xs text-slate-400">Max Drawdown</div><div className="text-lg font-bold text-red-400">-8.2%</div></div>
        <div><div className="text-xs text-slate-400">Account Balance</div><div className="text-lg font-bold text-green-400">\,450</div></div>
      </div>
      <nav className="space-y-2">
        <button className="w-full px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded text-sm font-medium transition">Signals</button>
        <button className="w-full px-4 py-2 hover:bg-slate-700 rounded text-sm font-medium transition">Portfolio</button>
        <button className="w-full px-4 py-2 hover:bg-slate-700 rounded text-sm font-medium transition">ML Models</button>
        <button className="w-full px-4 py-2 hover:bg-slate-700 rounded text-sm font-medium transition">Backtest</button>
        <button className="w-full px-4 py-2 hover:bg-slate-700 rounded text-sm font-medium transition">Settings</button>
      </nav>
    </div>
  );
}
