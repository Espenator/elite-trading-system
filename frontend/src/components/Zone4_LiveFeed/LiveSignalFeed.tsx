import React from 'react';
import { FixedSizeList as List } from 'react-window';
import { useRealtimeSignals } from '../../hooks/useRealtimeSignals';
import './LiveSignalFeed.css';

const LiveSignalFeed: React.FC = () => {
  const { signals } = useRealtimeSignals();

  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const signal = signals[index];
    if (!signal) return null;

    return (
      <div className="feed-row" style={style}>
        <span className="feed-cell time">{new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</span>
        <span className="feed-cell ticker">{signal.ticker}</span>
        <span className={`feed-cell tier tier-${signal.tier?.toLowerCase()}`}>{signal.tier}</span>
        <span className="feed-cell score">{signal.globalConfidence}</span>
        <span className="feed-cell confidence">{signal.modelAgreement}%</span>
        <span className="feed-cell rvol">{signal.rvol?.toFixed(1)}x</span>
        <span className="feed-cell catalyst">Volume spike + momentum</span>
      </div>
    );
  };

  return (
    <div className="live-feed">
      <div className="feed-header">
        <span className="feed-icon">🔴</span>
        <h3 className="feed-title">Live Signal Feed</h3>
        <span className="feed-status active">● LIVE</span>
        <div className="feed-controls">
          <button className="feed-btn">Pause</button>
          <button className="feed-btn">Export</button>
        </div>
      </div>

      <div className="feed-table-header">
        <span className="header-cell time">TIME</span>
        <span className="header-cell ticker">TICKER</span>
        <span className="header-cell tier">TIER</span>
        <span className="header-cell score">SCORE</span>
        <span className="header-cell confidence">AI CONF</span>
        <span className="header-cell rvol">RVOL</span>
        <span className="header-cell catalyst">CATALYST</span>
      </div>

      <List
        height={240}
        itemCount={signals.length}
        itemSize={40}
        width="100%"
        className="feed-list"
      >
        {Row}
      </List>

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
            {signals.length > 0 
              ? (signals.reduce((sum, s) => sum + s.globalConfidence, 0) / signals.length).toFixed(0)
              : 0}%
          </span>
        </div>
      </div>
    </div>
  );
};

export default LiveSignalFeed;
