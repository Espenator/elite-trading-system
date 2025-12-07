import React from 'react';
import './CommandBar.css';

const CommandBar: React.FC = () => {
  return (
    <div className="command-bar">
      <div className="brand-section">
        <span className="brand-icon">◈</span>
        <span className="brand-name">ELITE</span>
      </div>

      <div className="search-section">
        <input 
          type="text" 
          className="universal-search"
          placeholder="🔍 Search symbol... (Ctrl+K)"
        />
      </div>

      <div className="indices-ribbon">
        <div className="index-card">
          <span className="index-name">S&P 500</span>
          <span className="index-price">5,785.69</span>
          <span className="index-change positive">+0.12%</span>
        </div>
        <div className="index-card">
          <span className="index-name">DJI</span>
          <span className="index-price">43,950</span>
          <span className="index-change negative">-0.08%</span>
        </div>
        <div className="index-card">
          <span className="index-name">NASDAQ</span>
          <span className="index-price">18,230</span>
          <span className="index-change positive">+0.24%</span>
        </div>
      </div>

      <div className="status-section">
        <span className="paper-mode">Paper: $1,000,000</span>
        <button className="settings-btn">⚙️</button>
      </div>
    </div>
  );
};

export default CommandBar;
