import React, { useState } from 'react';
import './ExecutionDeck.css';

interface ExecutionDeckProps {
  selectedSignal?: any;
}

const ExecutionDeck: React.FC<ExecutionDeckProps> = ({ selectedSignal }) => {
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market');
  const [quantity, setQuantity] = useState(100);
  const [limitPrice, setLimitPrice] = useState('');

  const handleExecute = () => {
    console.log('Execute trade:', { orderType, quantity, limitPrice });
  };

  return (
    <div className="execution-deck">
      <div className="deck-header">
        <h3 className="deck-title">⚡ Execution Deck</h3>
        <div className="account-summary">
          <span className="account-label">Paper Account</span>
          <span className="account-balance">$100,000.00</span>
        </div>
      </div>

      {selectedSignal ? (
        <div className="active-signal">
          <div className="signal-header">
            <h4 className="signal-ticker">{selectedSignal.ticker}</h4>
            <span className={`signal-direction ${selectedSignal.direction}`}>
              {selectedSignal.direction === 'long' ? '📈' : '📉'} {selectedSignal.direction.toUpperCase()}
            </span>
          </div>
          
          <div className="signal-metrics">
            <div className="metric">
              <span className="metric-label">Entry</span>
              <span className="metric-value">${selectedSignal.currentPrice?.toFixed(2)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Confidence</span>
              <span className="metric-value">{selectedSignal.globalConfidence}%</span>
            </div>
            <div className="metric">
              <span className="metric-label">R:R</span>
              <span className="metric-value">1:3.2</span>
            </div>
          </div>

          <div className="order-controls">
            <div className="order-type-selector">
              <button 
                className={`type-btn ${orderType === 'market' ? 'active' : ''}`}
                onClick={() => setOrderType('market')}
              >
                Market
              </button>
              <button 
                className={`type-btn ${orderType === 'limit' ? 'active' : ''}`}
                onClick={() => setOrderType('limit')}
              >
                Limit
              </button>
            </div>

            <div className="input-group">
              <label>Quantity</label>
              <input 
                type="number" 
                value={quantity}
                onChange={(e) => setQuantity(Number(e.target.value))}
                className="quantity-input"
              />
            </div>

            {orderType === 'limit' && (
              <div className="input-group">
                <label>Limit Price</label>
                <input 
                  type="text" 
                  value={limitPrice}
                  onChange={(e) => setLimitPrice(e.target.value)}
                  placeholder="Enter price"
                  className="price-input"
                />
              </div>
            )}

            <button className="execute-btn" onClick={handleExecute}>
              <span className="btn-icon">⚡</span>
              Execute Trade
            </button>
          </div>

          <div className="position-summary">
            <div className="summary-row">
              <span>Total Cost:</span>
              <span className="value">${(selectedSignal.currentPrice * quantity).toFixed(2)}</span>
            </div>
            <div className="summary-row">
              <span>Stop Loss:</span>
              <span className="value danger">${(selectedSignal.currentPrice * 0.98).toFixed(2)}</span>
            </div>
            <div className="summary-row">
              <span>Take Profit:</span>
              <span className="value success">${(selectedSignal.currentPrice * 1.06).toFixed(2)}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="no-signal-selected">
          <div className="empty-icon">🎯</div>
          <p>Select a signal to execute</p>
          <span className="hint">Click any candidate in Zone 1</span>
        </div>
      )}

      <div className="active-positions">
        <h4 className="positions-title">Active Positions</h4>
        <div className="positions-list">
          <div className="empty-positions">
            <span>No active positions</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExecutionDeck;
