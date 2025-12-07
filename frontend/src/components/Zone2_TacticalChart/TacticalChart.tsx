import React, { useEffect, useRef, useState } from 'react';
import { createChart, IChartApi, ISeriesApi } from 'lightweight-charts';
import './TacticalChart.css';

interface TacticalChartProps {
  symbol?: string;
}

const TacticalChart: React.FC<TacticalChartProps> = ({ symbol = 'SPY' }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const [timeframe, setTimeframe] = useState('1D');

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 500,
      layout: {
        background: { color: 'transparent' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: 'rgba(148, 163, 184, 0.1)' },
        horzLines: { color: 'rgba(148, 163, 184, 0.1)' },
      },
      crosshair: {
        mode: 1,
      },
      timeScale: {
        borderColor: 'rgba(148, 163, 184, 0.2)',
        timeVisible: true,
      },
      rightPriceScale: {
        borderColor: 'rgba(148, 163, 184, 0.2)',
      },
    });

    chartRef.current = chart;

    // Candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderUpColor: '#10b981',
      borderDownColor: '#ef4444',
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    candlestickSeriesRef.current = candlestickSeries;

    // Volume series
    const volumeSeries = chart.addHistogramSeries({
      color: '#26a69a',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    volumeSeriesRef.current = volumeSeries;

    // Mock data
    const generateMockData = () => {
      const data = [];
      const volumeData = [];
      let basePrice = 100;
      const now = Math.floor(Date.now() / 1000);

      for (let i = 100; i >= 0; i--) {
        const time = now - i * 86400;
        const open = basePrice + (Math.random() - 0.5) * 5;
        const close = open + (Math.random() - 0.5) * 3;
        const high = Math.max(open, close) + Math.random() * 2;
        const low = Math.min(open, close) - Math.random() * 2;
        const volume = Math.random() * 1000000 + 500000;

        data.push({ time, open, high, low, close });
        volumeData.push({
          time,
          value: volume,
          color: close >= open ? 'rgba(16, 185, 129, 0.5)' : 'rgba(239, 68, 68, 0.5)',
        });

        basePrice = close;
      }

      return { data, volumeData };
    };

    const { data, volumeData } = generateMockData();
    candlestickSeries.setData(data);
    volumeSeries.setData(volumeData);

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [symbol, timeframe]);

  return (
    <div className="tactical-chart-container">
      <div className="chart-header">
        <div className="chart-title">
          <h3>{symbol}</h3>
          <span className="chart-subtitle">Candlestick Chart with Volume</span>
        </div>

        <div className="timeframe-selector">
          {['5M', '15M', '1H', '4H', '1D', '1W'].map((tf) => (
            <button
              key={tf}
              className={`timeframe-btn ${timeframe === tf ? 'active' : ''}`}
              onClick={() => setTimeframe(tf)}
            >
              {tf}
            </button>
          ))}
        </div>

        <div className="chart-controls">
          <button className="control-btn" title="Indicators">📊</button>
          <button className="control-btn" title="Settings">⚙️</button>
          <button className="control-btn" title="Fullscreen">⛶</button>
        </div>
      </div>

      <div ref={chartContainerRef} className="chart-canvas" />

      <div className="factor-strip">
        <div className="factor-card">
          <span className="factor-label">Volume Spike</span>
          <div className="strength-bar">
            <div className="strength-fill" style={{ width: '85%', backgroundColor: '#fbbf24' }}></div>
          </div>
          <span className="factor-value">High</span>
        </div>

        <div className="factor-card">
          <span className="factor-label">Breakout</span>
          <div className="strength-bar">
            <div className="strength-fill" style={{ width: '70%', backgroundColor: '#10b981' }}></div>
          </div>
          <span className="factor-value">Confirmed</span>
        </div>

        <div className="factor-card">
          <span className="factor-label">RSI Surge</span>
          <div className="strength-bar">
            <div className="strength-fill" style={{ width: '60%', backgroundColor: '#7c3aed' }}></div>
          </div>
          <span className="factor-value">Overbought</span>
        </div>
      </div>
    </div>
  );
};

export default TacticalChart;
