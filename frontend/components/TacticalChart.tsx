'use client';

import { useEffect, useRef, useState } from 'react';

interface TacticalChartProps {
  symbol: string;
}

export default function TacticalChart({ symbol }: TacticalChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const [timeframe, setTimeframe] = useState('1H');
  const [chartData, setChartData] = useState<any>(null);

  useEffect(() => {
    // Fetch chart data from backend
    setChartData(null); // Reset on symbol/timeframe change
    fetch(`http://localhost:8000/api/chart/data/${symbol}?timeframe=${timeframe}`)
      .then(res => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then(data => {
        if (data && data.data && data.data.length > 0) {
          setChartData(data);
        } else {
          console.warn('No chart data received');
        }
      })
      .catch(err => {
        console.error('Chart data error:', err);
        // Keep chartData as null to show placeholder
      });
  }, [symbol, timeframe]);

  return (
    <div className="tactical-chart-container">
      <div className="chart-header">
        <h2 className="chart-title">{symbol} - Tactical Chart</h2>
        <div className="timeframe-selector">
          {['5M', '15M', '1H', '4H', '1D'].map(tf => (
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

      <div ref={chartContainerRef} className="chart-area">
        {!chartData ? (
          <div className="chart-placeholder">
            <div className="placeholder-icon">📈</div>
            <p>Loading {symbol} chart data...</p>
            <p className="placeholder-hint">Click "Force Scan" to load market data</p>
          </div>
        ) : (
          <div className="chart-content">
            <p>Chart for {symbol} ({timeframe})</p>
            <div className="chart-mock">
              {/* TradingView Lightweight Charts will be integrated here */}
              <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <p style={{ color: '#00D9FF' }}>📈 Chart Ready - TradingView Integration Pending</p>
              </div>
            </div>
          </div>
        )}
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
