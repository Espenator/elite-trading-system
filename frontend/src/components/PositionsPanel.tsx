import React, { useState, useEffect } from 'react';
import { X, TrendingUp, TrendingDown } from 'lucide-react';

export function PositionsPanel({ positions, setPositions }) {
  const [localPositions, setLocalPositions] = useState([]);

  useEffect(() => {
    const mockPositions = [
      { id: '1', symbol: 'NVDA', qty: 100, entryPrice: 185.2, currentPrice: 188.5, pl: 330, plPct: 1.78 },
      { id: '2', symbol: 'AAPL', qty: 150, entryPrice: 178.4, currentPrice: 180.2, pl: 270, plPct: 1.01 },
      { id: '3', symbol: 'TSLA', qty: 50, entryPrice: 248.0, currentPrice: 245.5, pl: -125, plPct: -1.01 }
    ];
    setLocalPositions(mockPositions); setPositions(mockPositions);
  }, [setPositions]);

  useEffect(() => {
    const interval = setInterval(() => {
      setLocalPositions(prev => prev.map(p => { const newPrice = p.currentPrice + (Math.random() - 0.5) * 0.5; const newPL = (newPrice - p.entryPrice) * p.qty; const newPLPct = ((newPrice - p.entryPrice) / p.entryPrice) * 100; return { ...p, currentPrice: newPrice, pl: newPL, plPct: newPLPct }; }));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const totalPL = localPositions.reduce((sum, p) => sum + p.pl, 0);
  const closePosition = (id) => { const filtered = localPositions.filter(p => p.id !== id); setLocalPositions(filtered); setPositions(filtered); };

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700 flex flex-col h-full">
      <div className="p-3 border-b border-slate-700">
        <h3 className="font-bold text-cyan-400 mb-2">OPEN POSITIONS ({localPositions.length})</h3>
        <div className="text-xs"><span className="text-slate-400">Total P/L: </span><span className={totalPL >= 0 ? 'text-green-400 font-bold' : 'text-red-400 font-bold'}>{totalPL.toFixed(0)}</span></div>
      </div>
      <div className="flex-1 overflow-y-auto">
        {localPositions.map(pos => (
          <div key={pos.id} className="p-3 border-b border-slate-700 hover:bg-slate-800 transition">
            <div className="flex items-center justify-between mb-2"><span className="font-bold text-lg">{pos.symbol}</span><button onClick={() => closePosition(pos.id)} className="p-1 hover:bg-red-900 rounded text-red-400"><X size={16} /></button></div>
            <div className="grid grid-cols-2 gap-2 text-xs mb-2">
              <div><span className="text-slate-400">Qty</span><div className="font-mono font-bold">{pos.qty} @ {pos.currentPrice.toFixed(2)}</div></div>
              <div><span className="text-slate-400">Entry</span><div className="font-mono font-bold">{pos.entryPrice.toFixed(2)}</div></div>
            </div>
            <div className="flex items-center justify-between">
              <span className={pos.pl >= 0 ? 'text-green-400 font-bold' : 'text-red-400 font-bold'}>{pos.pl.toFixed(0)}</span>
              <span className={pos.plPct >= 0 ? 'text-green-400 font-bold' : 'text-red-400 font-bold'}>{pos.plPct >= 0 ? '+' : ''}{pos.plPct.toFixed(2)}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
