import React, { useEffect, useRef, useCallback, useState } from 'react';
import { createChart, ColorType, LineSeries } from 'lightweight-charts';

const API_BASE_URL = (import.meta as unknown as { env?: { VITE_API_BASE_URL?: string } }).env?.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';

interface FinvizQuoteItem {
  Date: string;
  Open: string;
  High: string;
  Low: string;
  Close: string;
  Volume?: string;
}

interface MiniChartProps {
  symbol: string | null;
  className?: string;
}

function parseFinvizDate(dateStr: string): number {
  if (!dateStr) return Math.floor(Date.now() / 1000);
  try {
    if (dateStr.includes('AM') || dateStr.includes('PM')) {
      const match = dateStr.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM)/i);
      if (!match) return Math.floor(Date.now() / 1000);
      const [, monthStr, dayStr, yearStr, hourStr, minStr, secStr, ampm] = match;
      const month = parseInt(monthStr, 10);
      const day = parseInt(dayStr, 10);
      const year = parseInt(yearStr, 10);
      let hours = parseInt(hourStr, 10);
      const minutes = parseInt(minStr, 10);
      const seconds = secStr ? parseInt(secStr, 10) : 0;
      if (ampm.toUpperCase() === 'PM' && hours !== 12) hours += 12;
      else if (ampm.toUpperCase() === 'AM' && hours === 12) hours = 0;
      const date = new Date(year, month - 1, day, hours, minutes, seconds);
      return Math.floor(date.getTime() / 1000);
    }
    const parts = dateStr.split('/');
    if (parts.length !== 3) return Math.floor(Date.now() / 1000);
    const [month, day, year] = parts.map(Number);
    const date = new Date(year, month - 1, day);
    return Math.floor(date.getTime() / 1000);
  } catch {
    return Math.floor(Date.now() / 1000);
  }
}

export function MiniChart({ symbol, className = '' }: MiniChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof createChart> | null>(null);
  const seriesRef = useRef<InstanceType<typeof LineSeries> | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAndSetData = useCallback(async () => {
    if (!symbol || !containerRef.current) return;
    setError(null);
    setIsLoading(true);
    try {
      const url = `${API_BASE_URL}/quotes/${encodeURIComponent(symbol)}?p=d&r=m1`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Failed to load: ${res.status}`);
      const data: FinvizQuoteItem[] = await res.json();
      if (!Array.isArray(data) || data.length === 0) {
        if (seriesRef.current) seriesRef.current.setData([]);
        setIsLoading(false);
        return;
      }
      let lastTime = 0;
      const lineData = data
        .map((item) => {
          const open = parseFloat(item.Open || '0');
          const close = parseFloat(item.Close || '0');
          if (isNaN(open) || isNaN(close) || open <= 0) return null;
          let time = parseFinvizDate(item.Date || '');
          if (time <= lastTime) time = lastTime + 1;
          lastTime = time;
          return { time, value: close };
        })
        .filter((d): d is { time: number; value: number } => d !== null)
        .sort((a, b) => a.time - b.time);
      if (seriesRef.current && lineData.length > 0) {
        seriesRef.current.setData(lineData);
        chartRef.current?.timeScale().fitContent();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load chart');
      if (seriesRef.current) seriesRef.current.setData([]);
    } finally {
      setIsLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    if (!containerRef.current || !symbol) return;
    const container = containerRef.current;
    const width = container.clientWidth || 200;
    const height = container.clientHeight || 128;
    const chart = createChart(container, {
      width,
      height,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9ca3af',
      },
      grid: { vertLines: { visible: false }, horzLines: { color: 'rgba(156,163,175,0.2)' } },
      rightPriceScale: {
        borderVisible: false,
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderVisible: false,
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: { mouseWheel: false, pressedMouseMove: false, horzTouchDrag: false, vertTouchDrag: false },
      handleScale: { axisPressedMouseMove: false, mouseWheel: false, pinch: false },
    });
    const lineSeries = chart.addSeries(LineSeries, {
      color: '#3b82f6',
      lineWidth: 2,
      lastValueVisible: true,
      priceLineVisible: false,
    });
    chartRef.current = chart;
    seriesRef.current = lineSeries;
    const resize = () => {
      if (chart && containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth, height: containerRef.current.clientHeight });
      }
    };
    window.addEventListener('resize', resize);
    fetchAndSetData();
    return () => {
      window.removeEventListener('resize', resize);
      try { chart.remove(); } catch { /* ignore */ }
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [symbol, fetchAndSetData]);

  if (!symbol) {
    return (
      <div className={`flex items-center justify-center text-gray-500 dark:text-gray-400 text-sm ${className}`} style={{ minHeight: 128 }}>
        Select a stock
      </div>
    );
  }

  return (
    <div className={`relative ${className}`} style={{ minHeight: 128 }}>
      <div ref={containerRef} className="w-full h-full" style={{ width: '100%', height: 128 }} />
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-50/80 dark:bg-gray-900/80 rounded text-gray-500 dark:text-gray-400 text-xs">
          Loading…
        </div>
      )}
      {error && !isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-50/80 dark:bg-gray-900/80 rounded text-red-500 dark:text-red-400 text-xs">
          {error}
        </div>
      )}
    </div>
  );
}

export default MiniChart;
