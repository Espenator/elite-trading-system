import React from 'react';
import React, { useState, useEffect } from 'react';
import './PositionSizer.css';

interface PositionSizerProps {
  accountBalance: number;
  maxRiskPercent: number;
  currentPrice: number;
  stopPrice: number;
}

const PositionSizer: React.FC<PositionSizerProps> = ({
  accountBalance,
  maxRiskPercent,
  currentPrice,
  stopPrice
}) => {
  const [riskPercent, setRiskPercent] = useState(2.0);
  const [calculatedSize, setCalculatedSize] = useState(0);
  const [totalCost, setTotalCost] = useState(0);
  const [maxLoss, setMaxLoss] = useState(0);
  const [percentOfAccount, setPercentOfAccount] = useState(0);

  useEffect(() => {
    // Calculate position size based on risk %
    const riskDollars = accountBalance * (riskPercent / 100);
    const stopDistance = Math.abs(currentPrice - stopPrice);
    const shares = stopDistance > 0 ? Math.floor(riskDollars / stopDistance) : 0;
    const cost = shares * currentPrice;
    const loss = shares * stopDistance;
    const percentAccount = (cost / accountBalance) * 100;

    setCalculatedSize(shares);
    setTotalCost(cost);
    setMaxLoss(loss);
    setPercentOfAccount(percentAccount);
  }, [riskPercent, accountBalance, currentPrice, stopPrice]);

  const isRisky = riskPercent > maxRiskPercent;
  const isOverExposed = percentOfAccount > 20;

  return (
    <div className="position-sizer">
      <div className="sizer-header">
        <h4>💰 Position Sizing Calculator</h4>
        <span className="sizer-subtitle">Velez 2% Risk Rule</span>
      </div>

      <div className="sizer-input">
        <label>Risk Per Trade (%)</label>
        <div className="risk-slider-container">
          <input 
            type="range"
            min="0.5"
            max="5"
            step="0.1"
            value={riskPercent}
            onChange={(e) => setRiskPercent(parseFloat(e.target.value))}
            className={`risk-slider ${isRisky ? 'risky' : ''}`}
          />
          <span className={`risk-value ${isRisky ? 'danger' : 'safe'}`}>
            {riskPercent.toFixed(1)}%
          </span>
        </div>
        {isRisky && (
          <div className="risk-warning">
            ⚠️ Exceeds maximum risk ({maxRiskPercent}%)
          </div>
        )}
      </div>

      <div className="sizer-results">
        <div className="result-card primary">
          <span className="result-label">Recommended Size</span>
          <span className="result-value">{calculatedSize.toLocaleString()} shares</span>
        </div>

        <div className="result-grid">
          <div className="result-item">
            <span className="result-label">Total Cost</span>
            <span className="result-value">${totalCost.toLocaleString()}</span>
          </div>
          <div className="result-item">
            <span className="result-label">Max Loss</span>
            <span className="result-value danger">${maxLoss.toFixed(2)}</span>
          </div>
          <div className="result-item">
            <span className="result-label">% of Account</span>
            <span className={`result-value ${isOverExposed ? 'danger' : ''}`}>
              {percentOfAccount.toFixed(1)}%
            </span>
          </div>
          <div className="result-item">
            <span className="result-label">Stop Distance</span>
            <span className="result-value">
              ${Math.abs(currentPrice - stopPrice).toFixed(2)}
            </span>
          </div>
        </div>

        {isOverExposed && (
          <div className="exposure-warning">
            ⚠️ Position exceeds 20% of account - Consider reducing size
          </div>
        )}
      </div>

      <div className="sizer-info">
        <div className="info-item">
          <span className="info-icon">ℹ️</span>
          <span className="info-text">
            Velez rule: Never risk more than {maxRiskPercent}% per trade
          </span>
        </div>
        <div className="info-item">
          <span className="info-icon">💡</span>
          <span className="info-text">
            Size calculated from: Entry ${currentPrice.toFixed(2)} | Stop ${stopPrice.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  );
};

export default PositionSizer;

