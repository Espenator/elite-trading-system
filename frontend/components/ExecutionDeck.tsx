'use client';

import { useState, useEffect } from 'react';

interface ExecutionDeckProps {
  symbol: string;
}

interface SignalData {
  type: string;
  confidence: number;
  entry?: number;
  target?: number;
  stop?: number;
  riskReward?: number;
}

export default function ExecutionDeck({ symbol }: ExecutionDeckProps) {
  const [activeSignal, setActiveSignal] = useState<SignalData | null>(null);
  const [quantity, setQuantity] = useState(100);
  const [accountBalance, setAccountBalance] = useState(1000000);

  useEffect(() => {
    // Fetch active signal for symbol
    fetch(`http://localhost:8000/api/signals/active/${symbol}`)
      .then(res => {
        if (!res.ok) {
          // No active signal is not an error
          return null;
        }
        return res.json();
      })
      .then(data => {
        if (data && data.entry) {
          setActiveSignal(data);
        } else {
          setActiveSignal(null);
        }
      })
      .catch(err => {
        console.error('Signal fetch error:', err);
        setActiveSignal(null);
      });
  }, [symbol]);

  const handleTrade = (side: 'buy' | 'sell') => {
    console.log(`Executing ${side.toUpperCase()} order for ${quantity} shares of ${symbol}`);
    // TODO: Connect to paper trading API
  };

  const entryPrice = activeSignal?.entry || 0;
  const targetPrice = activeSignal?.target || 0;
  const stopPrice = activeSignal?.stop || 0;
  const riskReward = activeSignal?.riskReward || 0;

  return (
    <div className="execution-deck">
      <h2 className="deck-title">🎯 Execution Deck</h2>

      {/* Paper Account Summary */}
      <div className="account-summary">
        <div className="account-stat">
          <span className="stat-label">Balance</span>
          <span className="stat-value">${accountBalance.toLocaleString()}</span>
        </div>
        <div className="account-stat">
          <span className="stat-label">Buying Power</span>
          <span className="stat-value">${accountBalance.toLocaleString()}</span>
        </div>
        <div className="account-stat">
          <span className="stat-label">Day P&L</span>
          <span className="stat-value positive">+$12,430</span>
        </div>
      </div>

      {/* Active Signal Card */}
      {activeSignal && entryPrice > 0 ? (
        <div className="signal-card active">
          <div className="signal-header">
            <span className="signal-type">🟢 {activeSignal.type}</span>
            <span className="signal-confidence">{activeSignal.confidence}% Conf</span>
          </div>
          <div className="signal-details">
            <div className="detail-row">
              <span>Entry:</span>
              <span className="value">${entryPrice.toFixed(2)}</span>
            </div>
            <div className="detail-row">
              <span>Target:</span>
              <span className="value positive">${targetPrice.toFixed(2)}</span>
            </div>
            <div className="detail-row">
              <span>Stop:</span>
              <span className="value negative">${stopPrice.toFixed(2)}</span>
            </div>
            <div className="detail-row">
              <span>R/R:</span>
              <span className="value">{riskReward.toFixed(1)}:1</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="signal-card empty">
          <div className="empty-state">
            <div className="empty-icon">📡</div>
            <p>No active signal for {symbol}</p>
            <p className="empty-hint">Waiting for setup...</p>
          </div>
        </div>
      )}

      {/* Order Entry */}
      <div className="order-entry">
        <h3 className="section-title">Order Entry</h3>
        
        <div className="input-group">
          <label>Quantity</label>
          <div className="quantity-input">
            <input 
              type="number" 
              value={quantity}
              onChange={(e) => setQuantity(parseInt(e.target.value) || 0)}
              className="qty-field"
            />
            <div className="quick-size">
              <button onClick={() => setQuantity(100)}>100</button>
              <button onClick={() => setQuantity(500)}>500</button>
              <button onClick={() => setQuantity(1000)}>1K</button>
            </div>
          </div>
        </div>

        <div className="execution-buttons">
          <button 
            className="exec-btn buy"
            onClick={() => handleTrade('buy')}
          >
            BUY MARKET
          </button>
          <button 
            className="exec-btn sell"
            onClick={() => handleTrade('sell')}
          >
            SELL MARKET
          </button>
        </div>
      </div>

      {/* Risk Display */}
      <div className="risk-display">
        <div className="risk-row">
          <span>Total Cost:</span>
          <span className="risk-value">${(quantity * entryPrice).toLocaleString()}</span>
        </div>
        <div className="risk-row">
          <span>Portfolio %:</span>
          <span className="risk-value">0.98%</span>
        </div>
        <div className="risk-row">
          <span>Max Risk:</span>
          <span className="risk-value negative">-$446</span>
        </div>
      </div>
    </div>
  );
}
