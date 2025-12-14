import React, { useState } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

export function ExecutionPanel({ selectedSignal }) {
  const [quantity, setQuantity] = useState(100);
  const [orderType, setOrderType] = useState('MARKET');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const symbol = selectedSignal?.symbol || 'NVDA';
  const currentPrice = 188.5;
  const stopLoss = currentPrice * 0.98;
  const positionValue = quantity * currentPrice;

  const handleTrade = async (side) => {
    setIsSubmitting(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    alert(side + ' order: ' + quantity + ' ' + symbol + ' @ ' + currentPrice);
    setIsSubmitting(false);
  };

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700 flex flex-col h-full">
      <div className="p-3 border-b border-slate-700">
        <h3 className="font-bold text-cyan-400 mb-1">ORDER ENTRY</h3>
        <div className="text-xs text-slate-400">{symbol}</div>
      </div>
      <div className="p-3 space-y-3 flex-1 overflow-y-auto">
        <div>
          <label className="text-xs text-slate-400 block mb-1">Quantity</label>
          <input type="number" value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} className="w-full px-2 py-1 bg-slate-800 border border-slate-600 rounded text-sm font-mono text-slate-100" />
        </div>
        <div className="grid grid-cols-3 gap-1">
          <button onClick={() => setQuantity(50)} className="px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs font-bold">50</button>
          <button onClick={() => setQuantity(100)} className="px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs font-bold">100</button>
          <button onClick={() => setQuantity(200)} className="px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs font-bold">200</button>
        </div>
        <div>
          <label className="text-xs text-slate-400 block mb-1">Order Type</label>
          <select value={orderType} onChange={(e) => setOrderType(e.target.value)} className="w-full px-2 py-1 bg-slate-800 border border-slate-600 rounded text-sm text-slate-100">
            <option>MARKET</option>
            <option>LIMIT</option>
            <option>STOP</option>
          </select>
        </div>
        <div className="bg-slate-800 rounded p-2 space-y-1 text-xs">
          <div className="flex justify-between"><span className="text-slate-400">Entry</span><span className="font-mono font-bold">{currentPrice}</span></div>
          <div className="flex justify-between"><span className="text-slate-400">Stop Loss</span><span className="font-mono font-bold text-red-400">{stopLoss.toFixed(2)}</span></div>
          <div className="flex justify-between"><span className="text-slate-400">Value</span><span className="font-mono font-bold">{positionValue}</span></div>
        </div>
      </div>
      <div className="p-3 space-y-2 border-t border-slate-700">
        <button onClick={() => handleTrade('BUY')} disabled={isSubmitting} className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-bold rounded flex items-center justify-center gap-2"><TrendingUp size={16} />BUY</button>
        <button onClick={() => handleTrade('SELL')} disabled={isSubmitting} className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-bold rounded flex items-center justify-center gap-2"><TrendingDown size={16} />SELL</button>
      </div>
    </div>
  );
}
