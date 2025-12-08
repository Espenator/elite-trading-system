'use client';

import { useEffect, useState } from 'react';

interface LiveSignalFeedProps {
  onSelectSymbol: (symbol: string) => void;
}

interface Signal {
  id: string;
  time: string;
  ticker: string;
  tier: string;
  score: number;
  aiConf: number;
  rvol: number;
  catalyst: string;
}

export default function LiveSignalFeed({ onSelectSymbol }: LiveSignalFeedProps) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [isPaused, setIsPaused] = useState(false);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws');
    
    ws.onmessage = (event) => {
      if (!isPaused) {
        const newSignal = JSON.parse(event.data);
        setSignals(prev => [newSignal, ...prev].slice(0, 100));
      }
    };

    return () => ws.close();
  }, [isPaused]);

  return (
    <div className="live-signal-feed">
      <div className="feed-header">
        <h2 className="feed-title">🔴 LIVE SIGNAL FEED</h2>
        <div className="feed-controls">
          <span className="signal-count">{signals.length} signals</span>
          <button 
            className="feed-control-btn"
            onClick={() => setIsPaused(!isPaused)}
          >
            {isPaused ? '▶ Resume' : '⏸ Pause'}
          </button>
          <button className="feed-control-btn">📥 Export</button>
        </div>
      </div>

      <div className="feed-table-container">
        <table className="feed-table">
          <thead>
            <tr>
              <th>TIME</th>
              <th>TICKER</th>
              <th>TIER</th>
              <th>SCORE</th>
              <th>AI CONF</th>
              <th>RVOL</th>
              <th>CATALYST</th>
            </tr>
          </thead>
          <tbody>
            {signals.length === 0 ? (
              <tr className="empty-row">
                <td colSpan={7}>
                  <div className="feed-empty-state">
                    <p>No signals - Click "Force Scan" to load market data</p>
                  </div>
                </td>
              </tr>
            ) : (
              signals.map(signal => (
                <tr 
                  key={signal.id}
                  className="feed-row"
                  onClick={() => onSelectSymbol(signal.ticker)}
                >
                  <td className="time-cell">{signal.time}</td>
                  <td className="ticker-cell">{signal.ticker}</td>
                  <td>
                    <span className={`tier-badge ${signal.tier.toLowerCase()}`}>
                      {signal.tier}
                    </span>
                  </td>
                  <td className="score-cell">{signal.score.toFixed(1)}</td>
                  <td className="conf-cell">{signal.aiConf}%</td>
                  <td className="rvol-cell">{signal.rvol.toFixed(1)}x</td>
                  <td className="catalyst-cell">{signal.catalyst}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
