import React, { useEffect, useState } from 'react';
import { useRealtimeSignals } from '../../hooks/useRealtimeSignals';
import './LiveSignalFeed.css';

const LiveSignalFeed: React.FC = () => {
  const { signals } = useRealtimeSignals();
  const [tickerIndex, setTickerIndex] = useState(0);

  useEffect(() => {
    if (signals.length === 0) return;
    
    const interval = setInterval(() => {
      setTickerIndex(prev => (prev + 1) % signals.length);
    }, 3000);

    return () => clearInterval(interval);
  }, [signals.length]);

  if (signals.length === 0) {
    return (
      <div className="live-feed">
        <div className="feed-header">
          <span className="feed-icon">🔴</span>
          <h3 className="feed-title">Live Signal Feed</h3>
          <span className="feed-status">● WAITING</span>
        </div>
        <div className="feed-empty">
          <p>No signals available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="live-feed">
      <div className="feed-header">
        <span className="feed-icon">🔴</span>
        <h3 className="feed-title">Live Signal Feed</h3>
        <span className="feed-status active">● LIVE</span>
      </div>

      <div className="ticker-container">
        <div className="ticker-scroll">
          {signals.map((signal, idx) => (
            <div key={signal.id} className={`ticker-item ${idx === tickerIndex ? 'active' : ''}`}>
              <span className="ticker-symbol">{signal.ticker}</span>
              <span className={`ticker-change ${signal.percentChange >= 0 ? 'positive' : 'negative'}`}>
                {signal.percentChange >= 0 ? '▲' : '▼'} {Math.abs(signal.percentChange).toFixed(2)}%
              </span>
              <span className="ticker-price">${signal.currentPrice?.toFixed(2)}</span>
              <span className="ticker-confidence">{signal.globalConfidence}%</span>
            </div>
          ))}
        </div>
      </div>

      <div className="feed-stats">
        <div className="stat">
          <span className="stat-label">Total Signals</span>
          <span className="stat-value">{signals.length}</span>
        </div>
        <div className="stat">
          <span className="stat-label">High Confidence</span>
          <span className="stat-value success">
            {signals.filter(s => s.globalConfidence >= 70).length}
          </span>
        </div>
        <div className="stat">
          <span className="stat-label">Avg Confidence</span>
          <span className="stat-value">
            {(signals.reduce((sum, s) => sum + s.globalConfidence, 0) / signals.length).toFixed(0)}%
          </span>
        </div>
      </div>
    </div>
  );
};

export default LiveSignalFeed;
