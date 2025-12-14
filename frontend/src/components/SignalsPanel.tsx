import React, { useState, useEffect } from 'react';

export function SignalsPanel({ signals, setSignals, onSelectSignal }) {
  const [sortBy, setSortBy] = useState('score');
  const [selectedId, setSelectedId] = useState(null);

  useEffect(() => {
    const mockSignals = [
      { id: '1', symbol: 'NVDA', score: 94, tier: 'T1', direction: 'LONG', volume: 85, momentum: 92, rsi: 78, timestamp: new Date(), confidence: 0.87 },
      { id: '2', symbol: 'AAPL', score: 89, tier: 'T1', direction: 'LONG', volume: 78, momentum: 88, rsi: 72, timestamp: new Date(Date.now() - 60000), confidence: 0.82 },
      { id: '3', symbol: 'TSLA', score: 78, tier: 'T2', direction: 'LONG', volume: 72, momentum: 75, rsi: 65, timestamp: new Date(Date.now() - 120000), confidence: 0.71 },
      { id: '4', symbol: 'META', score: 75, tier: 'T2', direction: 'SHORT', volume: 68, momentum: 62, rsi: 55, timestamp: new Date(Date.now() - 300000), confidence: 0.68 },
      { id: '5', symbol: 'AMD', score: 68, tier: 'T3', direction: 'LONG', volume: 55, momentum: 58, rsi: 48, timestamp: new Date(Date.now() - 600000), confidence: 0.62 }
    ];
    setSignals(mockSignals);
  }, [setSignals]);

  const sorted = [...signals].sort((a, b) => b.score - a.score);

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700 flex flex-col h-full">
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between mb-3"><h2 className="font-bold text-cyan-400">TOP SIGNALS</h2><div className="text-xs text-slate-400">{signals.length} Active</div></div>
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="w-full px-2 py-1 bg-slate-800 border border-slate-600 rounded text-xs text-slate-300">
          <option value="score">Sort by Score</option><option value="confidence">Sort by Confidence</option><option value="time">Sort by Time</option>
        </select>
      </div>
      <div className="overflow-y-auto flex-1">
        {sorted.map((signal) => (
          <div key={signal.id} onClick={() => { setSelectedId(signal.id); onSelectSignal(signal); }} className={'p-3 border-b border-slate-700 cursor-pointer transition ' + (selectedId === signal.id ? 'bg-cyan-900/30' : 'hover:bg-slate-800')}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-white">{signal.symbol}</span>
                <span className={'px-2 py-0.5 rounded text-xs font-bold ' + (signal.tier === 'T1' ? 'bg-green-900/50 text-green-300' : signal.tier === 'T2' ? 'bg-yellow-900/50 text-yellow-300' : 'bg-orange-900/50 text-orange-300')}>{signal.tier}</span>
              </div>
              <span className="text-xl font-bold text-cyan-400">{signal.score}</span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div><span className="text-slate-400">Vol</span><div className="font-mono font-bold text-slate-200">{signal.volume}</div></div>
              <div><span className="text-slate-400">Mom</span><div className="font-mono font-bold text-slate-200">{signal.momentum}</div></div>
              <div><span className="text-slate-400">RSI</span><div className="font-mono font-bold text-slate-200">{signal.rsi}</div></div>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <span className={'text-xs font-bold ' + (signal.direction === 'LONG' ? 'text-green-400' : 'text-red-400')}>{signal.direction}</span>
              <span className="text-xs text-slate-500">{Math.round((Date.now() - signal.timestamp.getTime()) / 60000)}m ago</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
