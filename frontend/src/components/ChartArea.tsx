import React, { useState, useEffect, useCallback } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faArrowTrendUp } from '@fortawesome/free-solid-svg-icons';

interface CandleData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface ChartAreaProps {
  selectedSignal?: {
    symbol?: string;
  } | null;
}

export function ChartArea({ selectedSignal }: ChartAreaProps) {
  const [timeframe, setTimeframe] = useState('5m');
  const [candleData, setCandleData] = useState([] as CandleData[]);
  const [isLoading, setIsLoading] = useState(true);
  const [currentPrice, setCurrentPrice] = useState(188.50);

  const symbol = selectedSignal?.symbol || 'NVDA';

  // Fallback: Generate sample data
  const generateSampleData = useCallback(() => {
    const candles: CandleData[] = []; 
    let price = 185.0;
    for (let i = 50; i > 0; i--) {
      const open = price; 
      const close = price + (Math.random() - 0.5) * 2;
      const high = Math.max(open, close) + Math.random(); 
      const low = Math.min(open, close) - Math.random();
      price = close; 
      candles.push({ 
        time: i, 
        open, 
        high, 
        low, 
        close, 
        volume: Math.random() * 1000000 
      });
    }
    setCandleData(candles);
    if (candles.length > 0) {
      setCurrentPrice(candles[candles.length - 1].close);
    }
  }, []);

  // Fetch chart data from backend API
  useEffect(() => {
    if (!symbol) return;

    setIsLoading(true);
    const url = `http://localhost:8000/api/chart/data/${symbol}?timeframe=${timeframe}`;

    fetch(url)
      .then(res => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then(data => {
        if (data?.data?.length > 0) {
          // Convert API data format to our CandleData format
          const candles: CandleData[] = data.data.map((d: any) => ({
            time: typeof d.time === 'string' ? Date.parse(d.time) / 1000 : d.time,
            open: d.open,
            high: d.high,
            low: d.low,
            close: d.close,
            volume: d.volume || 0
          }));
          setCandleData(candles);
          
          // Update current price from latest candle
          if (candles.length > 0) {
            setCurrentPrice(candles[candles.length - 1].close);
          }
          setIsLoading(false);
        } else {
          // Fallback to sample data if API returns no data
          generateSampleData();
          setIsLoading(false);
        }
      })
      .catch(() => {
        // Fallback to sample data on error
        generateSampleData();
        setIsLoading(false);
      });
  }, [symbol, timeframe, generateSampleData]);

  const maxPrice = candleData.length > 0 ? Math.max(...candleData.map(c => c.high)) : 190;
  const minPrice = candleData.length > 0 ? Math.min(...candleData.map(c => c.low)) : 180;

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700 flex flex-col h-full">
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <FontAwesomeIcon
              icon={faArrowTrendUp}
              className="text-cyan-400"
              style={{ width: '20px', height: '20px' }}
            />
            <h2 className="font-bold">{symbol} - {timeframe}</h2>
          </div>
          <div className="text-sm text-slate-400">Current: <span className="font-mono font-bold text-cyan-400">${currentPrice.toFixed(2)}</span></div>
        </div>
        <div className="flex gap-2">
          {['1m', '5m', '15m', '1H', '4H', '1D'].map(tf => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-3 py-1 rounded text-xs font-bold transition ${
                timeframe === tf
                  ? 'bg-cyan-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 p-4 overflow-hidden flex flex-col">
        <div className="flex-1 bg-slate-800 rounded border border-slate-700 p-3 font-mono text-xs mb-3 overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center h-full min-h-[200px] text-slate-400">
              Loading chart data...
            </div>
          ) : (
            <div className="flex items-end justify-around h-full min-h-[200px]">
              {candleData.slice(-40).map((candle, i) => {
                const range = maxPrice - minPrice || 1;
                const bodyHeight = Math.abs(candle.close - candle.open) / range * 100 || 2;
                const color = candle.close >= candle.open ? 'bg-green-400' : 'bg-red-400';
                return (
                  <div key={i} className="flex flex-col items-center justify-end h-full">
                    <div
                      className={`w-2 ${color}`}
                      style={{ height: `${bodyHeight}%`, minHeight: '2px' }}
                    />
                  </div>
                );
              })}
            </div>
          )}
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
