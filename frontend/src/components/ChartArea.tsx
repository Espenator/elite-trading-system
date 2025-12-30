import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createChart, ColorType, CandlestickSeries, HistogramSeries } from 'lightweight-charts';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faArrowTrendUp, faSpinner } from '@fortawesome/free-solid-svg-icons';

interface ChartAreaProps {
  selectedSignal?: {
    symbol?: string;
  } | null;
}

interface FinvizQuoteData {
  Date: string;
  Open: string;
  High: string;
  Low: string;
  Close: string;
  Volume: string;
}

// Available timeframes: i1, i3, i5, i15, i30, h, d, w, m
// Available durations: d1, d5, m1, m3, m6, ytd, y1, y2, y5, max
const TIMEFRAME_OPTIONS = ['1m', '3m', '5m', '15m', '30m', '1H', '4H', '1D', '1W', '1M'] as const;
type Timeframe = typeof TIMEFRAME_OPTIONS[number];

const TIMEFRAME_MAP: Record<Timeframe, { p: string; r: string }> = {
  '1m': { p: 'i1', r: 'd1' },
  '3m': { p: 'i3', r: 'd1' },
  '5m': { p: 'i5', r: 'd1' },
  '15m': { p: 'i15', r: 'd1' },
  '30m': { p: 'i30', r: 'd1' },
  '1H': { p: 'h', r: 'd5' },
  '4H': { p: 'h', r: 'm1' },
  '1D': { p: 'd', r: 'ytd' },
  '1W': { p: 'w', r: 'y1' },
  '1M': { p: 'm', r: 'y2' }
};

const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';

export function ChartArea({ selectedSignal }: ChartAreaProps) {
  const [timeframe, setTimeframe] = useState<Timeframe>('1D');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPrice, setCurrentPrice] = useState<number>(0);

  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const candlestickSeriesRef = useRef<any>(null);
  const volumeSeriesRef = useRef<any>(null);
  const chartReadyRef = useRef<boolean>(false);
  const pendingDataRef = useRef<{ candles: any[]; volumes: any[] } | null>(null);

  const symbol = selectedSignal?.symbol || null;

  // Parse Finviz date format to Unix timestamp
  // Handles two formats:
  // 1. MM/DD/YYYY (e.g., "01/02/2025") - for daily/weekly/monthly
  // 2. MM/DD/YYYY HH:MM AM/PM (e.g., "12/29/2025 08:00 AM") - for intraday
  const parseFinvizDate = useCallback((dateStr: string): number => {
    if (!dateStr) {
      return Math.floor(Date.now() / 1000);
    }

    try {
      // Check if date includes time (intraday format)
      if (dateStr.includes('AM') || dateStr.includes('PM')) {
        // Format: "MM/DD/YYYY HH:MM AM/PM" or "MM/DD/YYYY HH:MM:SS AM/PM"
        // Example: "12/29/2025 08:00 AM"
        // Use regex to parse the entire string
        const match = dateStr.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM)/i);
        
        if (!match) {
          return Math.floor(Date.now() / 1000);
        }

        const [, monthStr, dayStr, yearStr, hourStr, minStr, secStr, ampm] = match;
        const month = parseInt(monthStr, 10);
        const day = parseInt(dayStr, 10);
        const year = parseInt(yearStr, 10);
        let hours = parseInt(hourStr, 10);
        const minutes = parseInt(minStr, 10);
        const seconds = secStr ? parseInt(secStr, 10) : 0;

        // Convert to 24-hour format
        if (ampm.toUpperCase() === 'PM' && hours !== 12) {
          hours += 12;
        } else if (ampm.toUpperCase() === 'AM' && hours === 12) {
          hours = 0;
        }

        const date = new Date(year, month - 1, day, hours, minutes, seconds);
        return Math.floor(date.getTime() / 1000);
      } else {
        // Format: "MM/DD/YYYY" (daily/weekly/monthly)
        const parts = dateStr.split('/');
        if (parts.length !== 3) {
          return Math.floor(Date.now() / 1000);
        }

        const [month, day, year] = parts.map(Number);
        const date = new Date(year, month - 1, day);
        return Math.floor(date.getTime() / 1000);
      }
    } catch (error) {
      return Math.floor(Date.now() / 1000);
    }
  }, []);

  // Convert Finviz API response to chart data format
  const convertToChartData = useCallback((data: FinvizQuoteData[]) => {
    const candles: any[] = [];
    const volumes: any[] = [];


    data.forEach((item, index) => {
      const open = parseFloat(item.Open || '0');
      const high = parseFloat(item.High || '0');
      const low = parseFloat(item.Low || '0');
      const close = parseFloat(item.Close || '0');
      const volume = parseInt(item.Volume?.replace(/[^0-9]/g, '') || '0', 10);

      // Validate data
      if (isNaN(open) || isNaN(high) || isNaN(low) || isNaN(close) || open <= 0) {
        return;
      }

      const time = parseFinvizDate(item.Date || '');
      
      if (!time || time <= 0) {
        return;
      }

      candles.push({
        time,
        open,
        high,
        low,
        close
      });

      volumes.push({
        time,
        value: volume,
        color: close >= open ? '#00D9FF33' : '#FF006E33'
      });
    });

    // Sort by time ascending
    candles.sort((a, b) => a.time - b.time);
    volumes.sort((a, b) => a.time - b.time);

    // Remove duplicates and ensure strictly ascending order
    // lightweight-charts requires unique, strictly ascending timestamps
    const uniqueCandles: any[] = [];
    const uniqueVolumes: any[] = [];
    let lastTime = 0;

    candles.forEach((candle) => {
      let time = candle.time;
      
      // Ensure strictly ascending timestamps (required by lightweight-charts)
      if (time <= lastTime) {
        time = lastTime + 1;
      }
      lastTime = time;
      
      uniqueCandles.push({
        ...candle,
        time
      });
    });

    // Match volumes with candles by index (they should be in same order)
    candles.forEach((originalCandle, index) => {
      if (index < volumes.length) {
        const candle = uniqueCandles[index];
        uniqueVolumes.push({
          ...volumes[index],
          time: candle.time
        });
      }
    });

    return { candles: uniqueCandles, volumes: uniqueVolumes };
  }, [parseFinvizDate]);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) {
      return;
    }

    const container = chartContainerRef.current;
    let retryCount = 0;
    let retryTimeoutId: ReturnType<typeof setTimeout> | null = null;
    let chart: ReturnType<typeof createChart> | null = null;
    let isCleanedUp = false;
    
    const initializeChart = () => {
      if (isCleanedUp) return;

      const width = container.clientWidth || container.offsetWidth;
      const height = container.clientHeight || container.offsetHeight;

      if (width === 0 || height === 0) {
        retryCount++;
        if (retryCount < 30) {
          retryTimeoutId = setTimeout(initializeChart, 100);
        }
        return;
      }


      chart = createChart(container, {
        width,
        height,
        layout: {
          background: { type: ColorType.Solid, color: '#1e293b' },
          textColor: '#d1d5db',
        },
        grid: {
          vertLines: { color: '#334155' },
          horzLines: { color: '#334155' },
        },
        crosshair: { mode: 1 },
        rightPriceScale: {
          borderColor: '#475569',
          scaleMargins: { top: 0.1, bottom: 0.1 },
        },
        timeScale: {
          borderColor: '#475569',
          timeVisible: true,
          secondsVisible: false,
        },
        handleScroll: {
          mouseWheel: true,
          pressedMouseMove: true,
          horzTouchDrag: true,
          vertTouchDrag: true,
        },
        handleScale: {
          axisPressedMouseMove: true,
          mouseWheel: true,
          pinch: true,
        },
      });

      const candlestickSeries = chart.addSeries(CandlestickSeries, {
        upColor: '#00D9FF',
        downColor: '#FF006E',
        borderUpColor: '#00D9FF',
        borderDownColor: '#FF006E',
        wickUpColor: '#00D9FF',
        wickDownColor: '#FF006E',
      });

      const volumeSeries = chart.addSeries(HistogramSeries, {
        color: '#26a69a',
        priceFormat: { type: 'volume' },
        priceScaleId: '',
      });

      chartRef.current = chart;
      candlestickSeriesRef.current = candlestickSeries;
      volumeSeriesRef.current = volumeSeries;
      chartReadyRef.current = true;
      
      // Apply pending data if any
      if (pendingDataRef.current) {
        try {
          candlestickSeries.setData(pendingDataRef.current.candles);
          volumeSeries.setData(pendingDataRef.current.volumes);
          const latestCandle = pendingDataRef.current.candles[pendingDataRef.current.candles.length - 1];
          if (latestCandle) setCurrentPrice(latestCandle.close);
          setTimeout(() => chart?.timeScale().fitContent(), 50);
          pendingDataRef.current = null;
        } catch (e) { /* ignore */ }
      }
    };

    // Handle resize
    const handleResize = () => {
      if (chart && container) {
        chart.applyOptions({
          width: container.clientWidth,
          height: container.clientHeight,
        });
      }
    };

    window.addEventListener('resize', handleResize);
    initializeChart();

    return () => {
      isCleanedUp = true;
      if (retryTimeoutId) clearTimeout(retryTimeoutId);
      window.removeEventListener('resize', handleResize);
      chartReadyRef.current = false;
      if (chart) {
        try { chart.remove(); } catch (e) { /* ignore */ }
      }
      chartRef.current = null;
      candlestickSeriesRef.current = null;
      volumeSeriesRef.current = null;
    };
  }, []);

  // Fetch chart data from API
  const fetchChartData = useCallback(async () => {
    if (!symbol) {
      if (candlestickSeriesRef.current) {
        candlestickSeriesRef.current.setData([]);
      }
      if (volumeSeriesRef.current) {
        volumeSeriesRef.current.setData([]);
      }
      setCurrentPrice(0);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const apiParams = TIMEFRAME_MAP[timeframe] || TIMEFRAME_MAP['1D'];
      const url = `${API_BASE_URL}/quotes/${symbol}?p=${apiParams.p}&r=${apiParams.r}`;

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Failed to fetch data: ${response.status} ${response.statusText}`);
      }

      const data: FinvizQuoteData[] = await response.json();

      if (!Array.isArray(data) || data.length === 0) {
        throw new Error('No data received from API');
      }

      const { candles, volumes } = convertToChartData(data);

      if (candles.length === 0) {
        throw new Error('No valid candle data found');
      }

      // Check if chart is ready
      if (!chartReadyRef.current || !chartRef.current || !candlestickSeriesRef.current || !volumeSeriesRef.current) {
        // Store data to be set when chart is ready
        pendingDataRef.current = { candles, volumes };
        const latestCandle = candles[candles.length - 1];
        setCurrentPrice(latestCandle.close);
        return;
      }

      // Update chart data
      candlestickSeriesRef.current.setData(candles);
      volumeSeriesRef.current.setData(volumes);
      
      const latestCandle = candles[candles.length - 1];
      setCurrentPrice(latestCandle.close);

      // Fit content
      setTimeout(() => {
        if (chartRef.current) {
          try {
            chartRef.current.timeScale().fitContent();
          } catch (e) { /* ignore */ }
        }
      }, 100);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load chart data';
      setError(errorMessage);
      console.error('Error fetching chart data:', err);
      
      // Clear chart on error
      if (candlestickSeriesRef.current) {
        candlestickSeriesRef.current.setData([]);
      }
      if (volumeSeriesRef.current) {
        volumeSeriesRef.current.setData([]);
      }
      setCurrentPrice(0);
    } finally {
      setIsLoading(false);
    }
  }, [symbol, timeframe, convertToChartData]);

  // Fetch data when symbol or timeframe changes
  useEffect(() => {
    fetchChartData();
  }, [fetchChartData]);

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700 flex flex-col" style={{ height: '100%', minHeight: '500px' }}>
      {/* Header */}
      <div className="p-4 border-b border-slate-700 flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <FontAwesomeIcon
              icon={faArrowTrendUp}
              className="text-cyan-400"
              style={{ width: '20px', height: '20px' }}
            />
            <h2 className="font-bold text-white">
              {symbol ? `${symbol} - ${timeframe}` : 'Select a stock to view chart'}
            </h2>
          </div>
          {currentPrice > 0 && (
            <div className="text-sm text-slate-400">
              Current: <span className="font-mono font-bold text-cyan-400">${currentPrice.toFixed(2)}</span>
            </div>
          )}
        </div>

        {/* Timeframe selector */}
        <div className="flex gap-2 flex-wrap">
          {TIMEFRAME_OPTIONS.map(tf => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              disabled={!symbol}
              className={`px-3 py-1 rounded text-xs font-bold transition ${
                timeframe === tf
                  ? 'bg-cyan-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed'
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Chart area */}
      <div className="flex-1 p-4 overflow-hidden flex flex-col" style={{ minHeight: 0 }}>
        <div className="flex-1 bg-slate-800 rounded border border-slate-700 mb-3 overflow-hidden relative" style={{ minHeight: '400px' }}>
          {/* ALWAYS render the chart container so ref is available */}
          <div
            ref={chartContainerRef}
            className="w-full h-full"
            style={{ width: '100%', height: '100%' }}
          />
          
          {/* Overlays on top of chart */}
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-800/90 z-10">
              <div className="flex items-center text-slate-400">
                <FontAwesomeIcon icon={faSpinner} className="animate-spin mr-2" />
                Loading chart data...
              </div>
            </div>
          )}
          {error && !isLoading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-800/90 z-10">
              <p className="text-sm font-semibold mb-2 text-red-400">Error loading chart</p>
              <p className="text-xs text-red-300 mb-4">{error}</p>
              {symbol && (
                <button
                  onClick={fetchChartData}
                  className="px-4 py-2 bg-cyan-600 text-white rounded hover:bg-cyan-700 transition"
                >
                  Retry
                </button>
              )}
            </div>
          )}
          {!symbol && !isLoading && !error && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-800/90 z-10">
              <p className="text-slate-400">Click on a stock row to view its chart</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
