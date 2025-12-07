'use client';

import { useEffect, useState } from 'react';

interface Signal {
  id: string;
  ticker: string;
  currentPrice: number;
  percentChange: number;
  globalConfidence: number;
  direction: string;
  volume: number;
  marketCap: number;
}

export default function Dashboard() {
  const [signals, setSignals] = useState<Signal[]>([]);

  useEffect(() => {
    fetch('http://localhost:8000/api/signals/?limit=100')
      .then(res => res.json())
      .then(data => setSignals(data))
      .catch(err => console.error(err));
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-blue-950 to-slate-950 text-white">
      {/* Header */}
      <div className="border-b border-slate-700 px-6 py-4 flex items-center justify-between bg-slate-900/50">
        <h1 className="text-2xl font-bold text-cyan-400">ELITE TRADING - GLASS HOUSE</h1>
        <div className="text-sm text-slate-400">{new Date().toLocaleTimeString()}</div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-12 gap-6 p-6">
        {/* Signal Cards */}
        {signals.map(signal => (
          <div key={signal.id} className="col-span-3 bg-slate-800/60 backdrop-blur border border-slate-700 rounded-lg p-4 hover:border-cyan-500 transition-all">
            <div className="flex justify-between items-start mb-3">
              <h3 className="text-xl font-bold">{signal.ticker}</h3>
              <span className={`text-sm font-semibold ${signal.percentChange >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {signal.percentChange >= 0 ? '+' : ''}{signal.percentChange.toFixed(2)}%
              </span>
            </div>
            <div className="text-2xl font-bold mb-2">${signal.currentPrice.toFixed(2)}</div>
            <div className="flex items-center gap-2 text-xs text-slate-400 mb-3">
              <span>Confidence: {signal.globalConfidence}%</span>
            </div>
            <div className="text-xs text-slate-500">
              Vol: {(signal.volume / 1000000).toFixed(2)}M | MCap: ${(signal.marketCap / 1000000000).toFixed(2)}B
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
