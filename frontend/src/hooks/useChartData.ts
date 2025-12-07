import { useState, useEffect } from 'react';
import { OHLCVData } from '../types/chart';

export const useChartData = (symbol: string, timeframe: string) => {
  const [data, setData] = useState<OHLCVData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const generateMockData = (): OHLCVData[] => {
      const now = Date.now();
      const bars: OHLCVData[] = [];
      let basePrice = 150;

      for (let i = 100; i >= 0; i--) {
        const timestamp = now - (i * 3600000);
        const open = basePrice + (Math.random() - 0.5) * 5;
        const close = open + (Math.random() - 0.5) * 4;
        const high = Math.max(open, close) + Math.random() * 2;
        const low = Math.min(open, close) - Math.random() * 2;
        const volume = Math.random() * 1000000;

        bars.push({
          time: Math.floor(timestamp / 1000),
          open,
          high,
          low,
          close,
          volume
        });

        basePrice = close;
      }
      return bars;
    };

    setTimeout(() => {
      setData(generateMockData());
      setLoading(false);
    }, 500);

    const interval = setInterval(() => {
      setData(prev => {
        const last = prev[prev.length - 1];
        if (!last) return prev;

        const newBar: OHLCVData = {
          time: Math.floor(Date.now() / 1000),
          open: last.close,
          high: last.close + Math.random() * 2,
          low: last.close - Math.random() * 2,
          close: last.close + (Math.random() - 0.5) * 3,
          volume: Math.random() * 1000000
        };

        return [...prev.slice(1), newBar];
      });
    }, 3000);

    return () => clearInterval(interval);
  }, [symbol, timeframe]);

  return { data, loading };
};
