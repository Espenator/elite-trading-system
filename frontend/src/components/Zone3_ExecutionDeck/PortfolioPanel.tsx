import React from 'react';
import './PortfolioPanel.css';

const PortfolioPanel = () => {
  const positions = [
    { ticker: 'TGL', shares: 200, entry: 49.23, current: 49.75, pnl: 104, pnlPercent: 1.1 }
  ];

  return (
    <div className="portfolio-panel">
      <div className="portfolio-summary">
        <div className="summary-stat">
          <span className="stat-label">Total Value</span>
          <span className="stat-value">$1,012,430</span>
        </div>
        <div className="summary-stat">
          <span className="stat-label">Day P&L</span>
          <span className="stat-value success">+$12,430</span>
        </div>
        <div className="summary-stat">
          <span className="stat-label">Positions</span>
          <span className="stat-value">{positions.length}</span>
        </div>
      </div>

      <h4 className="section-title">Open Positions ({positions.length})</h4>

      {positions.map((pos) => (
        <div key={pos.ticker} className="position-card">
          <div className="position-header">
            <span className="position-ticker">{pos.ticker}</span>
            <span className="position-shares">{pos.shares} shares</span>
          </div>
          
          <div className="position-metrics">
            <div className="metric">
              <span className="metric-label">Entry</span>
              <span className="metric-value">${pos.entry.toFixed(2)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Current</span>
              <span className="metric-value">${pos.current.toFixed(2)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">P&L</span>
              <span className={`metric-value ${pos.pnl >= 0 ? 'success' : 'danger'}`}>
                ${pos.pnl.toFixed(2)} ({pos.pnlPercent >= 0 ? '+' : ''}{pos.pnlPercent}%)
              </span>
            </div>
          </div>

          <button className="close-position-btn">Close Position</button>
        </div>
      ))}

      {positions.length === 0 && (
        <div className="empty-positions">
          <p>No active positions</p>
        </div>
      )}
    </div>
  );
};

export default PortfolioPanel;
