import React, { useState, useEffect } from 'react';
import './PortfolioRace.css';

interface Position {
  ticker: string;
  entryPrice: number;
  currentPrice: number;
  quantity: number;
  pnl: number;
  pnlPercent: number;
}

const PortfolioRace: React.FC = () => {
  const [positions, setPositions] = useState<Position[]>([
    { ticker: 'TGL', entryPrice: 49.23, currentPrice: 55.38, quantity: 500, pnl: 3075, pnlPercent: 12.5 },
    { ticker: 'AAPL', entryPrice: 195.50, currentPrice: 203.90, quantity: 100, pnl: 840, pnlPercent: 4.3 },
    { ticker: 'NVDA', entryPrice: 485.20, currentPrice: 495.40, quantity: 50, pnl: 510, pnlPercent: 2.1 },
    { ticker: 'TSLA', entryPrice: 242.80, currentPrice: 239.90, quantity: 75, pnl: -217.50, pnlPercent: -1.2 },
  ]);

  // Simulate live updates
  useEffect(() => {
    const interval = setInterval(() => {
      setPositions(prev => prev.map(pos => ({
        ...pos,
        currentPrice: pos.currentPrice * (1 + (Math.random() - 0.5) * 0.002),
        pnl: (pos.currentPrice - pos.entryPrice) * pos.quantity,
        pnlPercent: ((pos.currentPrice - pos.entryPrice) / pos.entryPrice) * 100
      })));
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const sortedPositions = [...positions].sort((a, b) => b.pnlPercent - a.pnlPercent);
  const maxPnl = Math.max(...positions.map(p => Math.abs(p.pnlPercent)));

  return (
    <div className="portfolio-race">
      <div className="race-header">
        <h4>🏁 Live Portfolio Race</h4>
        <span className="race-total">
          Total P&L: <span className={positions.reduce((sum, p) => sum + p.pnl, 0) >= 0 ? 'positive' : 'negative'}>
            ${positions.reduce((sum, p) => sum + p.pnl, 0).toFixed(2)}
          </span>
        </span>
      </div>

      <div className="race-tracks">
        {sortedPositions.map((position, index) => (
          <div key={position.ticker} className="race-track">
            <div className="race-info">
              <span className="race-rank">#{index + 1}</span>
              <span className="race-ticker">{position.ticker}</span>
              <span className="race-qty">{position.quantity} shares</span>
            </div>

            <div className="race-bar-container">
              <div 
                className={`race-bar ${position.pnlPercent >= 0 ? 'winning' : 'losing'}`}
                style={{ 
                  width: `${(Math.abs(position.pnlPercent) / maxPnl) * 100}%`,
                  transition: 'width 0.5s ease-out'
                }}
              >
                <span className="race-pnl">
                  {position.pnlPercent >= 0 ? '+' : ''}{position.pnlPercent.toFixed(2)}%
                </span>
              </div>
            </div>

            <div className="race-values">
              <span className="race-entry">${position.entryPrice.toFixed(2)}</span>
              <span className="race-arrow">→</span>
              <span className="race-current">${position.currentPrice.toFixed(2)}</span>
              <span className={`race-dollar ${position.pnl >= 0 ? 'positive' : 'negative'}`}>
                {position.pnl >= 0 ? '+' : ''}${position.pnl.toFixed(2)}
              </span>
            </div>
          </div>
        ))}
      </div>

      {positions.length === 0 && (
        <div className="race-empty">
          <p>No open positions</p>
          <p className="race-hint">Execute a trade to see live performance</p>
        </div>
      )}
    </div>
  );
};

export default PortfolioRace;
