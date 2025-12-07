import React, { useState, useEffect } from 'react';
import Sparkline from '../Common/Sparkline';
import SettingsModal from '../Settings/SettingsModal';
import './CommandBar.css';

interface CommandBarProps {
  activeSymbol?: string;
  onSymbolChange?: (symbol: string) => void;
  onSettingsClick?: () => void;
}

const CommandBar: React.FC<CommandBarProps> = ({ 
  activeSymbol = 'SPY', 
  onSymbolChange,
  onSettingsClick 
}) => {
  const [searchValue, setSearchValue] = useState('');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [latency, setLatency] = useState(12);

  // Simulate latency updates
  useEffect(() => {
    const interval = setInterval(() => {
      setLatency(Math.floor(Math.random() * 30) + 10);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Generate mock sparkline data
  const generateSparklineData = () => {
    return Array.from({ length: 30 }, () => Math.random() * 10 + 95);
  };

  const handleSearch = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && searchValue.trim()) {
      onSymbolChange?.(searchValue.trim().toUpperCase());
      setSearchValue('');
    }
  };

  const latencyColor = latency < 50 ? '#10b981' : latency < 100 ? '#fbbf24' : '#ef4444';

  return (
    <>
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
            <div className="index-header">
              <span className="index-name">S&P 500</span>
              <span className="index-change positive">+0.12%</span>
            </div>
            <span className="index-price">5,785.69</span>
            <div className="index-sparkline">
              <Sparkline 
                data={generateSparklineData()} 
                width={60} 
                height={20}
                color="#10b981"
                showGradient={false}
              />
            </div>
          </div>

          <div className="index-card">
            <div className="index-header">
              <span className="index-name">DJI</span>
              <span className="index-change negative">-0.08%</span>
            </div>
            <span className="index-price">43,950</span>
            <div className="index-sparkline">
              <Sparkline 
                data={generateSparklineData()} 
                width={60} 
                height={20}
                color="#ef4444"
                showGradient={false}
              />
            </div>
          </div>

          <div className="index-card">
            <div className="index-header">
              <span className="index-name">NASDAQ</span>
              <span className="index-change positive">+0.24%</span>
            </div>
            <span className="index-price">18,230</span>
            <div className="index-sparkline">
              <Sparkline 
                data={generateSparklineData()} 
                width={60} 
                height={20}
                color="#10b981"
                showGradient={false}
              />
            </div>
          </div>
        </div>

        <div className="main-symbol-display">
          <div className="symbol-ticker">{activeSymbol}</div>
          <div className="symbol-price">$49.23 <span className="positive">+93.51%</span></div>
        </div>

        <div className="status-section">
          <div className="system-status">
            <span className="status-indicator active">●</span>
            <span className="status-text">LIVE</span>
            <span className="latency" style={{ color: latencyColor }}>
              {latency}ms
            </span>
          </div>
          <span className="paper-mode">Paper: $1,000,000</span>
          <button className="settings-btn" onClick={() => setSettingsOpen(true)}>⚙️</button>
        </div>
      </div>

      <SettingsModal 
        isOpen={settingsOpen} 
        onClose={() => setSettingsOpen(false)} 
      />
    </>
  );
};

export default CommandBar;
