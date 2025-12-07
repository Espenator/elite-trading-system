import React, { useState } from 'react';
import TacticalChart from './TacticalChart';
import './SignalComparison.css';

interface Signal {
  ticker: string;
  score: number;
  confidence: number;
  rvol: number;
  recommendation: 'BUY' | 'HOLD' | 'SELL';
}

interface SignalComparisonProps {
  signals: Signal[];
}

const SignalComparison: React.FC<SignalComparisonProps> = ({ signals }) => {
  const [viewMode, setViewMode] = useState<'single' | 'comparison'>('single');
  const [activeSignal, setActiveSignal] = useState(0);

  const topSignals = signals.slice(0, 3);

  return (
    <div className="signal-comparison">
      <div className="comparison-controls">
        <div className="view-mode-toggle">
          <button 
            className={`mode-btn ${viewMode === 'single' ? 'active' : ''}`}
            onClick={() => setViewMode('single')}
          >
            📈 Single View
          </button>
          <button 
            className={`mode-btn ${viewMode === 'comparison' ? 'active' : ''}`}
            onClick={() => setViewMode('comparison')}
          >
            📊 Compare Top 3
          </button>
        </div>
      </div>

      {viewMode === 'single' ? (
        <div className="single-chart-view">
          <TacticalChart symbol={topSignals[activeSignal]?.ticker || 'SPY'} />
        </div>
      ) : (
        <div className="comparison-grid">
          {topSignals.map((signal, index) => (
            <div key={signal.ticker} className="comparison-cell">
              <div className="cell-header">
                <div className="cell-title">
                  <span className="cell-rank">#{index + 1}</span>
                  <span className="cell-ticker">{signal.ticker}</span>
                  <span className={`cell-rec ${signal.recommendation.toLowerCase()}`}>
                    {signal.recommendation}
                  </span>
                </div>
                <div className="cell-score">Score: {signal.score}</div>
              </div>

              <div className="cell-chart">
                <TacticalChart symbol={signal.ticker} compact={true} />
              </div>

              <div className="cell-metrics">
                <div className="metric">
                  <span className="metric-label">AI Confidence</span>
                  <span className="metric-value">{signal.confidence}%</span>
                </div>
                <div className="metric">
                  <span className="metric-label">RVOL</span>
                  <span className="metric-value">{signal.rvol.toFixed(1)}x</span>
                </div>
              </div>

              <button 
                className="load-chart-btn"
                onClick={() => {
                  setActiveSignal(index);
                  setViewMode('single');
                }}
              >
                Load Full Chart
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SignalComparison;
