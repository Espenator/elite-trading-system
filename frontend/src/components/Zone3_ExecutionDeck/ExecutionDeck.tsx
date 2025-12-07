import React, { useState } from 'react';
import PortfolioPanel from './PortfolioPanel';
import './ExecutionDeck.css';

interface ExecutionDeckProps {
  selectedSignal?: any;
}

const ExecutionDeck: React.FC<ExecutionDeckProps> = ({ selectedSignal }) => {
  const [activeTab, setActiveTab] = useState<'trade' | 'portfolio'>('trade');
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market');
  const [quantity, setQuantity] = useState(100);

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
              <span className="account-balance">$1,000,000.00</span>
            </div>
          </div>

          {/* Trade execution form - keep existing */}
          <div className="no-signal-selected">
            <div className="empty-icon">🎯</div>
            <p>Select a signal to execute</p>
          </div>
        </>
      ) : (
        <PortfolioPanel />
      )}
    </div>
  );
};

export default ExecutionDeck;
