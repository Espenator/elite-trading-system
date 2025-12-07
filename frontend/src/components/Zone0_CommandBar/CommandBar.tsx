import React, { useState } from 'react';
import './CommandBar.css';

interface CommandBarProps {
  activeSymbol?: string;
  onSymbolChange?: (symbol: string) => void;
}

const CommandBar: React.FC<CommandBarProps> = ({ 
  activeSymbol = 'SPY', 
  onSymbolChange 
}) => {
  const [searchValue, setSearchValue] = useState('');

  const handleSearch = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && searchValue.trim()) {
      onSymbolChange?.(searchValue.trim().toUpperCase());
      setSearchValue('');
    }
  };

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
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          onKeyDown={handleSearch}
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

      <div className="main-symbol-display">
        <div className="symbol-ticker">{activeSymbol}</div>
        <div className="symbol-price">$49.23 <span className="positive">+93.51%</span></div>
      </div>

      <div className="status-section">
        <span className="paper-mode">Paper: $1,000,000</span>
        <button className="settings-btn">⚙️</button>
      </div>
    </div>
  );
};

export default CommandBar;
