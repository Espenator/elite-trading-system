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
        <div className="text-sm"><span className="text-slate-400">SPY </span><span className="font-mono font-bold text-white">{indices.spy.price.toFixed(2)}</span><span className={indices.spy.change >= 0 ? 'text-green-400 ml-2' : 'text-red-400 ml-2'}>{indices.spy.change >= 0 ? '+' : ''}{indices.spy.change.toFixed(2)}%</span></div>
        <div className="text-sm"><span className="text-slate-400">QQQ </span><span className="font-mono font-bold text-white">{indices.qqq.price.toFixed(2)}</span><span className={indices.qqq.change >= 0 ? 'text-green-400 ml-2' : 'text-red-400 ml-2'}>{indices.qqq.change >= 0 ? '+' : ''}{indices.qqq.change.toFixed(2)}%</span></div>
        <div className="text-sm"><span className="text-slate-400">VIX </span><span className="font-mono font-bold text-white">{indices.vix.price.toFixed(2)}</span><span className={indices.vix.change >= 0 ? 'text-red-400 ml-2' : 'text-green-400 ml-2'}>{indices.vix.change >= 0 ? '+' : ''}{indices.vix.change.toFixed(2)}%</span></div>
      </div>
      <div className="flex items-center gap-4">
        <span className="text-sm text-slate-400">Account: <span className="text-green-400 font-bold">+2,450</span></span>
        <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} className="p-2 hover:bg-slate-700 rounded">{theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}</button>
        <Bell size={20} className="cursor-pointer text-slate-400 hover:text-cyan-400" />
        <Settings size={20} className="cursor-pointer text-slate-400 hover:text-cyan-400" />
      </div>
    </header>
  );
}
