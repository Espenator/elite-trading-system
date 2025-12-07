import React, { useEffect, useRef, useState } from 'react';
import { createChart, IChartApi, ISeriesApi } from 'lightweight-charts';
import './TacticalChart.css';

interface TacticalChartProps {
  symbol?: string;
}

const TacticalChart: React.FC<TacticalChartProps> = ({ symbol = 'SPY' }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const [timeframe, setTimeframe] = useState('1D');

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: '#0a0e1a' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: 'rgba(148, 163, 184, 0.1)' },
        horzLines: { color: 'rgba(148, 163, 184, 0.1)' },
      },
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
      timeScale: {
        borderColor: 'rgba(148, 163, 184, 0.2)',
      },
      rightPriceScale: {
        borderColor: 'rgba(148, 163, 184, 0.2)',
      },
    });

    chartRef.current = chart;

    // Create candlestick series
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderUpColor: '#10b981',
      borderDownColor: '#ef4444',
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    candleSeriesRef.current = candleSeries;

    // Generate sample data (replace with real API data)
    const generateSampleData = () => {
      const data = [];
      const startDate = new Date('2024-01-01').getTime() / 1000;
      let price = 100;

      for (let i = 0; i < 365; i++) {
        const time = startDate + i * 86400;
        const open = price;
        const change = (Math.random() - 0.5) * 5;
        const close = open + change;
        const high = Math.max(open, close) + Math.random() * 2;
        const low = Math.min(open, close) - Math.random() * 2;

        data.push({
          time,
          open,
          high,
          low,
          close,
        });

        price = close;
      }

      return data;
    };

    candleSeries.setData(generateSampleData());

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [symbol]);

  return (
    <div className="tactical-chart-container">
      <div className="chart-controls">
        <div className="controls-left">
          <h3 className="chart-symbol">{symbol}</h3>
          <span className="chart-label">Tactical Analysis</span>
        </div>

        <div className="controls-center">
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
        </div>

        <div className="controls-right">
          <button className="control-btn" title="Indicators">📊</button>
          <button className="control-btn" title="Settings">⚙️</button>
          <button className="control-btn" title="Fullscreen">⛶</button>
        </div>
      </div>

      <div className="chart-wrapper" ref={chartContainerRef}></div>

      <div className="factor-strip">
        <div className="factor-strip-header">
          <span className="strip-label">Technical Signals</span>
        </div>
        <div className="factor-cards">
          <div className="factor-card bullish">
            <span className="factor-icon">🚀</span>
            <div className="factor-info">
              <span className="factor-name">Volume Spike</span>
              <div className="factor-strength">
                <div className="strength-bar" style={{ width: '85%' }}></div>
                <span className="strength-value">85%</span>
              </div>
            </div>
          </div>
          <div className="factor-card bullish">
            <span className="factor-icon">📈</span>
            <div className="factor-info">
              <span className="factor-name">Breakout</span>
              <div className="factor-strength">
                <div className="strength-bar" style={{ width: '72%' }}></div>
                <span className="strength-value">72%</span>
              </div>
            </div>
          </div>
          <div className="factor-card bearish">
            <span className="factor-icon">⚠️</span>
            <div className="factor-info">
              <span className="factor-name">Overbought RSI</span>
              <div className="factor-strength">
                <div className="strength-bar" style={{ width: '45%' }}></div>
                <span className="strength-value">45%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TacticalChart;
