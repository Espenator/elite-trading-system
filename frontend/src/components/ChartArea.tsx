import React, { useState, useEffect } from 'react';
import { TrendingUp } from 'lucide-react';

export function ChartArea({ selectedSignal }) {
  const [timeframe, setTimeframe] = useState('5m');
  const [candleData, setCandleData] = useState([]);

  useEffect(() => {
    const generateCandles = () => {
      const candles = []; let price = 185.0;
      for (let i = 50; i > 0; i--) {
        const open = price; const close = price + (Math.random() - 0.5) * 2;
        const high = Math.max(open, close) + Math.random(); const low = Math.min(open, close) - Math.random();
        price = close; candles.push({ time: i, open, high, low, close, volume: Math.random() * 1000000 });
      }
      setCandleData(candles);
    };
    generateCandles();
    const interval = setInterval(generateCandles, 3000);
    return () => clearInterval(interval);
  }, []);

  const maxPrice = candleData.length > 0 ? Math.max(...candleData.map(c => c.high)) : 190;
  const minPrice = candleData.length > 0 ? Math.min(...candleData.map(c => c.low)) : 180;

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700 flex flex-col h-full">
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2"><TrendingUp size={20} className="text-cyan-400" /><h2 className="font-bold">{selectedSignal ? selectedSignal.symbol : 'NVDA'} - {timeframe}</h2></div>
          <div className="text-sm text-slate-400">Current: <span className="font-mono font-bold text-cyan-400">188.50</span></div>
        </div>
        <div className="flex gap-2">
          {['1m', '5m', '15m', '1H', '4H', '1D'].map(tf => (<button key={tf} onClick={() => setTimeframe(tf)} className={'px-3 py-1 rounded text-xs font-bold transition ' + (timeframe === tf ? 'bg-cyan-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600')}>{tf}</button>))}
        </div>
      </div>
      <div className="flex-1 p-4 overflow-hidden flex flex-col">
        <div className="flex-1 bg-slate-800 rounded border border-slate-700 p-3 font-mono text-xs mb-3 overflow-x-auto">
          <div className="flex items-end justify-around h-full min-h-[200px]">
            {candleData.slice(-40).map((candle, i) => {
              const range = maxPrice - minPrice || 1;
              const bodyHeight = Math.abs(candle.close - candle.open) / range * 100 || 2;
              const color = candle.close >= candle.open ? 'bg-green-400' : 'bg-red-400';
              return (<div key={i} className="flex flex-col items-center justify-end h-full"><div className={'w-2 ' + color} style={{ height: bodyHeight + '%', minHeight: '2px' }} /></div>);
            })}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-slate-800 rounded border border-slate-700 p-3">
            <div className="text-xs text-slate-400 mb-2">RSI (14)</div>
            <div className="text-xs text-slate-300 font-mono">Value: 65</div>
          </div>
          <div className="bg-slate-800 rounded border border-slate-700 p-3">
            <div className="text-xs text-slate-400 mb-2">Volume</div>
            <div className="text-xs text-slate-300 font-mono">Avg: 500K</div>
          </div>
        </div>
      </div>
    </div>
  );
}
