import React, { useState, useEffect } from 'react';
import { TrendingUp, AlertTriangle } from 'lucide-react';

export function MLInsightsPanel() {
  const [modelStats, setModelStats] = useState({ accuracy: 73.2, confidence: 85, samples: 1250, drift: false });
  const [features] = useState([{ name: 'RSI14', importance: 15.2 }, { name: 'Volume', importance: 12.8 }, { name: 'SMA20', importance: 10.4 }, { name: 'ATR14', importance: 8.9 }, { name: 'MACD', importance: 7.6 }]);

  useEffect(() => {
    const interval = setInterval(() => { setModelStats(prev => ({ ...prev, accuracy: Math.min(75, prev.accuracy + (Math.random() - 0.5) * 0.5), samples: prev.samples + Math.floor(Math.random() * 5) })); }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700 flex flex-col h-full">
      <div className="p-3 border-b border-slate-700"><h3 className="font-bold text-cyan-400 flex items-center gap-2"><TrendingUp size={18} />ML INSIGHTS</h3></div>
      <div className="p-3 space-y-2 text-xs">
        <div className="bg-slate-800 rounded p-2"><div className="text-slate-400">Accuracy</div><div className="text-lg font-bold text-green-400">{modelStats.accuracy.toFixed(1)}%</div></div>
        <div className="bg-slate-800 rounded p-2"><div className="text-slate-400">Confidence</div><div className="text-lg font-bold text-cyan-400">{modelStats.confidence}%</div></div>
        <div className="bg-slate-800 rounded p-2"><div className="text-slate-400">Samples</div><div className="text-lg font-bold text-slate-200">{modelStats.samples}</div></div>
      </div>
      <div className="p-3 border-t border-slate-700 flex-1 overflow-hidden">
        <div className="text-xs text-slate-400 mb-2 font-bold">Top Features</div>
        <div className="space-y-1 text-xs">
          {features.map((f, i) => (<div key={i} className="flex items-center justify-between"><span className="text-slate-300">{f.name}</span><div className="flex-1 mx-2 bg-slate-700 rounded h-1.5 overflow-hidden"><div className="bg-cyan-500 h-full" style={{ width: (f.importance * 5) + '%' }} /></div><span className="text-slate-400 w-8 text-right">{f.importance}%</span></div>))}
        </div>
      </div>
    </div>
  );
}
