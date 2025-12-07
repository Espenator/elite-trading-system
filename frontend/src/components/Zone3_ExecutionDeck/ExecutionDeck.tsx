import React, { useState, useEffect } from 'react';
import PortfolioPanel from './PortfolioPanel';
import './ExecutionDeck.css';

interface ExecutionDeckProps {
  selectedSignal?: any;
}

const ExecutionDeck: React.FC<ExecutionDeckProps> = ({ selectedSignal }) => {
  const [activeTab, setActiveTab] = useState<'trade' | 'portfolio'>('trade');
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market');
  const [quantity, setQuantity] = useState(500);
  const [price, setPrice] = useState(selectedSignal?.price || 49.23);
  const [stopLoss, setStopLoss] = useState(selectedSignal?.stopLoss || 47.00);
  
  const accountBalance = 1000000;
  
  // Calculate risk
  const calculateRisk = () => {
    const totalCost = quantity * price;
    const stopDistance = price - stopLoss;
    const maxLoss = quantity * stopDistance;
    const riskPercent = (maxLoss / accountBalance) * 100;
    const rewardPercent = ((55.00 - price) / price) * 100; // Assuming target $55
    const rrRatio = rewardPercent / (stopDistance / price * 100);
    
    return {
      totalCost,
      maxLoss,
      riskPercent,
      rrRatio
    };
  };
  
  const risk = calculateRisk();

  return (
    <div className="execution-deck">
      <div className="deck-tabs">
        <button 
          className={`tab-btn ${activeTab === 'trade' ? 'active' : ''}`}
          onClick={() => setActiveTab('trade')}
        >
          🎯 Trade
        </button>
        <button 
          className={`tab-btn ${activeTab === 'portfolio' ? 'active' : ''}`}
          onClick={() => setActiveTab('portfolio')}
        >
          💼 Portfolio
        </button>
      </div>

      {activeTab === 'trade' ? (
        <>
          <div className="deck-header">
            <h3 className="deck-title">Paper Trade</h3>
            <div className="account-summary">
              <span className="account-label">Paper Account</span>
              <span className="account-balance">${accountBalance.toLocaleString()}</span>
            </div>
          </div>

          <div className="trade-form">
            <div className="form-group">
              <label>Symbol</label>
              <input 
                type="text" 
                value={selectedSignal?.ticker || 'TGL'} 
                readOnly 
                className="symbol-input"
              />
            </div>

            <div className="form-group">
              <label>Order Type</label>
              <select 
                value={orderType} 
                onChange={(e) => setOrderType(e.target.value as 'market' | 'limit')}
                className="order-type-select"
              >
                <option value="market">Market</option>
                <option value="limit">Limit</option>
              </select>
            </div>

            <div className="form-group">
              <label>Quantity</label>
              <input 
                type="number" 
                value={quantity} 
                onChange={(e) => setQuantity(Number(e.target.value))}
                className="quantity-input"
              />
              
              <div className="quick-size">
                <button 
                  className={`size-btn ${quantity === 100 ? 'active' : ''}`}
                  onClick={() => setQuantity(100)}
                >
                  100
                </button>
                <button 
                  className={`size-btn ${quantity === 500 ? 'active' : ''}`}
                  onClick={() => setQuantity(500)}
                >
                  500
                </button>
                <button 
                  className={`size-btn ${quantity === 1000 ? 'active' : ''}`}
                  onClick={() => setQuantity(1000)}
                >
                  1000
                </button>
              </div>
            </div>

            <div className="form-group">
              <label>Price</label>
              <input 
                type="number" 
                value={price} 
                onChange={(e) => setPrice(Number(e.target.value))}
                step="0.01"
                className="price-input"
              />
            </div>

            <div className="form-group">
              <label>Stop Loss</label>
              <input 
                type="number" 
                value={stopLoss} 
                onChange={(e) => setStopLoss(Number(e.target.value))}
                step="0.01"
                className="stop-input"
              />
            </div>

            <div className="risk-display">
              <h4>Risk Analysis</h4>
              <div className="risk-metrics">
                <div className="risk-metric">
                  <span className="risk-label">Total Cost</span>
                  <span className="risk-value">${risk.totalCost.toLocaleString()}</span>
                </div>
                <div className="risk-metric">
                  <span className="risk-label">Max Loss</span>
                  <span className={`risk-value ${risk.riskPercent > 2 ? 'danger' : 'success'}`}>
                    ${risk.maxLoss.toFixed(2)} ({risk.riskPercent.toFixed(2)}%)
                  </span>
                </div>
                <div className="risk-metric">
                  <span className="risk-label">R/R Ratio</span>
                  <span className="risk-value">{risk.rrRatio.toFixed(2)}:1</span>
                </div>
              </div>
              
              {risk.riskPercent > 2 && (
                <div className="risk-warning">
                  ⚠️ Risk exceeds 2% rule!
                </div>
              )}
            </div>

            <button className="execute-btn">
              PLACE PAPER TRADE
            </button>
          </div>
        </>
      ) : (
        <PortfolioPanel />
      )}
    </div>
  );
};

export default ExecutionDeck;
