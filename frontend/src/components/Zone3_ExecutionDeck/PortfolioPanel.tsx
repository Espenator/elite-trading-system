import React from 'react';
import Sparkline from '../Common/Sparkline';
import './PortfolioPanel.css';

const PortfolioPanel = () => {
  const openPositions = [
    {
      ticker: 'TGL',
      quantity: 500,
      entryPrice: 49.23,
      currentPrice: 52.15,
      pnl: 1460,
      pnlPercent: 5.93,
      sparklineData: Array.from({ length: 24 }, () => Math.random() * 5 + 48)
    },
    {
      ticker: 'AAPL',
      quantity: 100,
      entryPrice: 195.50,
      currentPrice: 197.23,
      pnl: 173,
      pnlPercent: 0.89,
      sparklineData: Array.from({ length: 24 }, () => Math.random() * 3 + 194)
    },
  ];

  const closedTrades = [
    { ticker: 'TSLA', pnl: 2340, pnlPercent: 12.5, outcome: 'win' },
    { ticker: 'NVDA', pnl: -850, pnlPercent: -3.2, outcome: 'loss' },
    { ticker: 'MSFT', pnl: 1120, pnlPercent: 4.8, outcome: 'win' },
  ];

  return (
    <div className="portfolio-panel">
      <div className="portfolio-header">
        <h3>Open Positions</h3>
        <span className="position-count">{openPositions.length} active</span>
      </div>

      <div className="positions-list">
        {openPositions.map((position, index) => (
          <div key={index} className="position-card">
            <div className="position-header">
              <span className="position-ticker">{position.ticker}</span>
              <span className={`position-pnl ${position.pnl >= 0 ? 'positive' : 'negative'}`}>
                {position.pnl >= 0 ? '+' : ''}${position.pnl.toFixed(2)} ({position.pnlPercent >= 0 ? '+' : ''}{position.pnlPercent}%)
              </span>
            </div>

            <div className="position-sparkline">
              <Sparkline 
                data={position.sparklineData} 
                width={280} 
                height={32}
                color={position.pnl >= 0 ? '#10b981' : '#ef4444'}
              />
            </div>

            <div className="position-details">
              <div className="detail-item">
                <span className="detail-label">Qty</span>
                <span className="detail-value">{position.quantity}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Entry</span>
                <span className="detail-value">${position.entryPrice.toFixed(2)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Current</span>
                <span className="detail-value">${position.currentPrice.toFixed(2)}</span>
              </div>
            </div>

            <button className="close-position-btn">Close Position</button>
          </div>
        ))}
      </div>

      <div className="closed-trades-section">
        <h4>Recent Closed Trades</h4>
        <div className="closed-trades-list">
          {closedTrades.map((trade, index) => (
            <div key={index} className="closed-trade-item">
              <span className="trade-ticker">{trade.ticker}</span>
              <span className={`trade-outcome ${trade.outcome}`}>
                {trade.outcome === 'win' ? '✓' : '✗'}
              </span>
              <span className={`trade-pnl ${trade.pnl >= 0 ? 'positive' : 'negative'}`}>
                {trade.pnl >= 0 ? '+' : ''}${trade.pnl}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default PortfolioPanel;
