import React, { useState, useEffect } from 'react';
import '../styles/PositionsPanel.css';

export default function PositionsPanel() {
  const [positions, setPositions] = useState([
    {
      id: 1,
      ticker: 'YUM',
      quantity: 100,
      entryPrice: 148.00,
      currentPrice: 149.50,
      stopPrice: 145.00,
      targetPrice: 152.00,
      entryTime: new Date(Date.now() - 5 * 60000), // 5 minutes ago
    },
    {
      id: 2,
      ticker: 'NVDA',
      quantity: 500,
      entryPrice: 189.00,
      currentPrice: 187.25,
      stopPrice: 185.00,
      targetPrice: 197.00,
      entryTime: new Date(Date.now() - 12 * 60000), // 12 minutes ago
    },
    {
      id: 3,
      ticker: 'AAPL',
      quantity: 250,
      entryPrice: 195.50,
      currentPrice: 195.75,
      stopPrice: 193.00,
      targetPrice: 200.00,
      entryTime: new Date(Date.now() - 3 * 60000), // 3 minutes ago
    },
  ]);

  const [flashingIds, setFlashingIds] = useState(new Set());
  const [lastUpdate, setLastUpdate] = useState(new Date());

  // Simulate real-time price updates from WebSocket
  useEffect(() => {
    const interval = setInterval(() => {
      setPositions(prevPositions =>
        prevPositions.map(pos => {
          // Random price movement (-0.5% to +0.5%)
          const movement = (Math.random() - 0.5) * 0.01;
          const newPrice = pos.currentPrice * (1 + movement);
          setFlashingIds(prev => new Set(prev).add(pos.id));
          setTimeout(() => {
            setFlashingIds(prev => {
              const next = new Set(prev);
              next.delete(pos.id);
              return next;
            });
          }, 300);
          return {
            ...pos,
            currentPrice: parseFloat(newPrice.toFixed(2)),
          };
        })
      );
      setLastUpdate(new Date());
    }, 3000); // Update every 3 seconds

    return () => clearInterval(interval);
  }, []);

  // ==================== CALCULATIONS ====================
  const calculatePnL = (pos) => {
    const pnlDollars = (pos.currentPrice - pos.entryPrice) * pos.quantity;
    const pnlPercent = ((pos.currentPrice - pos.entryPrice) / pos.entryPrice) * 100;
    return { pnlDollars, pnlPercent };
  };

  const getDuration = (entryTime) => {
    const now = new Date();
    const diffMs = now - entryTime;
    const diffMins = Math.floor(diffMs / 60000);
    const diffSecs = Math.floor((diffMs % 60000) / 1000);
    return `${diffMins}m ${diffSecs}s`;
  };

  // Calculate totals
  const totals = positions.reduce(
    (acc, pos) => {
      const { pnlDollars, pnlPercent } = calculatePnL(pos);
      acc.totalPnlDollars += pnlDollars;
      acc.totalValue += pos.entryPrice * pos.quantity;
      if (pnlDollars > 0) {
        acc.winning++;
      } else if (pnlDollars < 0) {
        acc.losing++;
      } else {
        acc.breakeven++;
      }
      return acc;
    },
    { totalPnlDollars: 0, totalValue: 0, winning: 0, losing: 0, breakeven: 0 }
  );

  const totalPnlPercent = (totals.totalPnlDollars / totals.totalValue) * 100;
  const totalWinRate = ((totals.winning / positions.length) * 100).toFixed(1);

  // ==================== HANDLERS ====================
  const handleClosePosition = (id) => {
    if (confirm('Close this position?')) {
      setPositions(positions.filter(p => p.id !== id));
    }
  };

  // ==================== RENDER ====================
  return (
    <div className="positions-panel">
      <div className="positions-header">
        <h2 className="positions-title">📋 Open Positions ({positions.length})</h2>
        <span className="last-update">Updated: {lastUpdate.toLocaleTimeString()}</span>
      </div>

      <div className="positions-table-container">
        <table className="positions-table">
          <thead>
            <tr>
              <th>TICKER</th>
              <th>QTY</th>
              <th>ENTRY</th>
              <th>CURRENT</th>
              <th>P&L ($)</th>
              <th>P&L (%)</th>
              <th>STOP</th>
              <th>TARGET</th>
              <th>DURATION</th>
              <th>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {positions.length === 0 ? (
              <tr className="empty-row">
                <td colSpan={10}>
                  <div className="empty-state">
                    <p>💰 No open positions</p>
                  </div>
                </td>
              </tr>
            ) : (
              positions.map(position => {
                const { pnlDollars, pnlPercent } = calculatePnL(position);
                const isWinning = pnlDollars > 0;
                const isFlashing = flashingIds.has(position.id);

                return (
                  <tr
                    key={position.id}
                    className={`position-row ${isWinning ? 'winning' : 'losing'} ${
                      isFlashing ? 'flash' : ''
                    }`}
                  >
                    <td className="ticker-cell">
                      <strong>{position.ticker}</strong>
                    </td>
                    <td className="qty-cell">{position.quantity}</td>
                    <td className="entry-cell">${position.entryPrice.toFixed(2)}</td>
                    <td className={`current-cell ${isFlashing ? 'flash-price' : ''}`}>
                      ${position.currentPrice.toFixed(2)}
                    </td>
                    <td className={`pnl-dollar-cell ${isWinning ? 'positive' : 'negative'}`}>
                      {isWinning ? '+' : ''}
                      ${Math.abs(pnlDollars).toFixed(2)}
                    </td>
                    <td className={`pnl-percent-cell ${isWinning ? 'positive' : 'negative'}`}>
                      <span className="pnl-badge">
                        {isWinning ? '+' : ''}
                        {pnlPercent.toFixed(2)}%
                      </span>
                    </td>
                    <td className="stop-cell">${position.stopPrice.toFixed(2)}</td>
                    <td className="target-cell">${position.targetPrice.toFixed(2)}</td>
                    <td className="duration-cell">{getDuration(position.entryTime)}</td>
                    <td className="action-cell">
                      <button
                        className="close-btn"
                        onClick={() => handleClosePosition(position.id)}
                        title="Close position"
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {positions.length > 0 && (
        <div className="positions-footer">
          <div className="footer-stats">
            <div className="stat-item">
              <span className="stat-label">Total P&L:</span>
              <span className={`stat-value ${totals.totalPnlDollars >= 0 ? 'positive' : 'negative'}`}>
                {totals.totalPnlDollars >= 0 ? '+' : ''}
                ${totals.totalPnlDollars.toFixed(2)} ({totals.totalPnlDollars >= 0 ? '+' : ''}
                {totalPnlPercent.toFixed(2)}%)
              </span>
            </div>

            <div className="stat-item">
              <span className="stat-label">Winning:</span>
              <span className="stat-value positive">
                {totals.winning} / {positions.length} ({totalWinRate}%)
              </span>
            </div>

            <div className="stat-item">
              <span className="stat-label">Losing:</span>
              <span className="stat-value negative">
                {totals.losing} / {positions.length} ({((totals.losing / positions.length) * 100).toFixed(1)}%)
              </span>
            </div>

            <div className="stat-item">
              <span className="stat-label">Breakeven:</span>
              <span className="stat-value neutral">{totals.breakeven}</span>
            </div>

            <div className="stat-item">
              <span className="stat-label">Open Value:</span>
              <span className="stat-value">${totals.totalValue.toFixed(2)}</span>
            </div>
          </div>

          <div className="footer-indicator">
            <span className="update-indicator">● Live</span>
          </div>
        </div>
      )}
    </div>
  );
}
