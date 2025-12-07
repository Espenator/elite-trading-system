import React, { useEffect, useRef, useState } from 'react';
import { createChart, IChartApi, ISeriesApi, IPriceLine } from 'lightweight-charts';
import { addVelezLevels, calculateVelezLevels, removeVelezLevels } from '../../utils/velezLevels';
import './TacticalChart.css';

interface TacticalChartProps {
  symbol?: string;
  compact?: boolean;
}

const TacticalChart: React.FC<TacticalChartProps> = ({ symbol = 'SPY', compact = false }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const priceLinesRef = useRef<IPriceLine[]>([]);
  const [timeframe, setTimeframe] = useState('1D');
  const [showLevels, setShowLevels] = useState(true);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: compact ? 200 : 500,
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

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderUpColor: '#10b981',
      borderDownColor: '#ef4444',
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    candlestickSeriesRef.current = candlestickSeries;

    if (!compact) {
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
    }

    // Generate mock data
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

      return { data, volumeData, currentPrice: basePrice };
    };

    const { data, volumeData, currentPrice } = generateMockData();
    candlestickSeries.setData(data);
    
    if (volumeSeriesRef.current) {
      volumeSeriesRef.current.setData(volumeData);
    }

    // Add Velez levels if not compact
    if (!compact && showLevels) {
      const levels = calculateVelezLevels(
        currentPrice,
        currentPrice * 1.08, // ML prediction +8%
        currentPrice * 0.015 // ATR ~1.5%
      );

      priceLinesRef.current = addVelezLevels(chart, levels);
    }

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
      if (priceLinesRef.current.length > 0 && chartRef.current) {
        removeVelezLevels(chartRef.current, priceLinesRef.current);
      }
      chart.remove();
    };
  }, [symbol, timeframe, compact, showLevels]);

  return (
    <div className="tactical-chart-container">
      {!compact && (
        <div className="chart-header">
          <div className="chart-title">
            <h3>{symbol}</h3>
            <span className="chart-subtitle">Velez System Analysis</span>
          </div>

          <div className="chart-options">
            <label className="levels-toggle">
              <input 
                type="checkbox" 
                checked={showLevels}
                onChange={(e) => setShowLevels(e.target.checked)}
              />
              <span>Show Velez Levels</span>
            </label>
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
      )}

      <div ref={chartContainerRef} className="chart-canvas" />

      {!compact && (
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
      )}
    </div>
  );
};

export default TacticalChart;
