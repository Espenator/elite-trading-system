'use client';

import { useEffect, useRef, useState } from 'react';
import * as LightweightCharts from 'lightweight-charts';

const { createChart, ColorType } = LightweightCharts;

interface TacticalChartProps {
  symbol: string;
}

interface ChartData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export default function TacticalChart({ symbol }: TacticalChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<LightweightCharts.IChartApi | null>(null);
  const candleSeriesRef = useRef<LightweightCharts.ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<LightweightCharts.ISeriesApi<'Histogram'> | null>(null);
  const [timeframe, setTimeframe] = useState('1H');
  const [chartData, setChartData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch chart data from backend
  useEffect(() => {
    const abortController = new AbortController();
    
    setChartData(null);
    setIsLoading(true);
    
    const url = `http://localhost:8000/api/chart/data/${symbol}?timeframe=${timeframe}`;
    
    fetch(url, { signal: abortController.signal })
      .then(res => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then(data => {
        if (data && data.data && data.data.length > 0) {
          setChartData(data);
          setIsLoading(false);
        } else {
          console.warn('No chart data received');
          setIsLoading(false);
        }
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Chart data error:', err);
        }
        setIsLoading(false);
      });

    return () => {
      abortController.abort();
    };
  }, [symbol, timeframe]);

  // Create chart once
  useEffect(() => {
    if (!chartContainerRef.current) return;
    
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
      layout: {
        background: { type: ColorType.Solid, color: '#0a0e1a' },
        textColor: '#7B8CA6',
      },
      grid: {
        vertLines: { color: '#1a1f2e' },
        horzLines: { color: '#1a1f2e' },
      },
      crosshair: {
        mode: 1,
      },
      timeScale: {
        borderColor: '#2B3139',
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: '#2B3139',
      },
    });

    chartRef.current = chart;

    // Add candlestick series (v3 API)
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#00D9FF',
      downColor: '#FF006E',
      borderUpColor: '#00D9FF',
      borderDownColor: '#FF006E',
      wickUpColor: '#00D9FF',
      wickDownColor: '#FF006E',
    });
    candleSeriesRef.current = candleSeries;

    // Add volume series
    const volumeSeries = chart.addHistogramSeries({
      color: '#26a69a',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
    });
    volumeSeriesRef.current = volumeSeries;

    // Handle resize
    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, []);

  // Update chart data when it changes
  useEffect(() => {
    if (!chartData || !candleSeriesRef.current || !volumeSeriesRef.current) return;

    const candleData = chartData.data.map((d: ChartData) => ({
      time: d.time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));

    const volumeData = chartData.data.map((d: ChartData) => ({
      time: d.time,
      value: d.volume,
      color: d.close >= d.open ? '#00D9FF33' : '#FF006E33',
    }));

    candleSeriesRef.current.setData(candleData);
    volumeSeriesRef.current.setData(volumeData);

    // Fit content to view
    chartRef.current?.timeScale().fitContent();
  }, [chartData]);

  return (
    <div className="tactical-chart-container">
      <div className="chart-header">
        <h2 className="chart-title">{symbol} - Tactical Chart</h2>
        <div className="timeframe-selector">
          {['5m', '15m', '1H', '4H', '1D'].map(tf => (
            <button
              key={tf}
              className={`timeframe-btn ${timeframe === tf ? 'active' : ''}`}
              onClick={() => setTimeframe(tf)}
            >
              {tf.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="chart-area">
        <div 
          ref={chartContainerRef} 
          className="chart-content"
          style={{ width: '100%', height: '100%', position: 'relative' }}
        >
          {(isLoading || !chartData) && (
            <div className="chart-placeholder" style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', zIndex: 10 }}>
              <div className="placeholder-icon">📈</div>
              <p>Loading {symbol} chart data...</p>
              <p className="placeholder-hint">Fetching market data from backend</p>
            </div>
          )}
        </div>
      </div>

      <div className="factor-strip">
        <div className="factor-label">Technical Signals</div>
        <div className="factor-timeline">
          <div className="factor-bar volume" title="Volume Spike">Vol</div>
          <div className="factor-bar breakout" title="Breakout Pattern">Break</div>
          <div className="factor-bar rsi" title="RSI Surge">RSI</div>
        </div>
      </div>
    </div>
  );
}
