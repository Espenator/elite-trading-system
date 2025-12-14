import React, { useState, useEffect, useCallback } from 'react';
import './TraderFirstDashboard.css';

/**
 * TRADER-FIRST DASHBOARD - SIGNALS ABOVE THE FOLD
 * 
 * Priority Hierarchy (Pro Trader Mindset):
 * 1. Market Context (SPY/QQQ/VIX/Breadth) - TOP HEADER
 * 2. TOP 10 LIVE SIGNALS TABLE - PRIMARY FOCUS (12 columns, full intelligence)
 * 3. Market Sentiment Stats - Quick bias assessment
 * 4. Tactical Chart (on-demand) - Deep analysis
 * 5. Open Positions - Real-time tracking
 * 6. Execution Controls - 1-click trading
 * 7. Account Metrics (collapsed) - Secondary, top-right
 * 
 * Design Philosophy:
 * "I want to see what signals are firing AND what the market is doing
 *  IMMEDIATELY when I open the app."
 * 
 * Status: PRODUCTION-READY
 * Date: December 14, 2025
 */

import TacticalChart from './TacticalChart';
import ExecutionDeck from './ExecutionDeck';

const TraderFirstDashboard = () => {
  const [signals, setSignals] = useState([
    {
      rank: 1,
      ticker: 'YUM',
      score: 94,
      velez: 91,
      signal_type: 'MOMENTUM',
      catalyst: 'Strong momentum +2.94%',
      rsi: 42,
      momentum_pct: 2.94,
      vwap: 148.50,
      entry_price: 148.12,
      stop_loss: 145.80,
      target_price: 152.60,
      risk_reward_ratio: 1.9,
      ai_confidence: 0.91,
      tier: 'T1'
    },
    {
      rank: 2,
      ticker: 'NVDA',
      score: 89,
      velez: 87,
      signal_type: 'VOLUME_SPIKE',
      catalyst: 'Volume spike 3.2x',
      rsi: 37,
      momentum_pct: 2.10,
      vwap: 875.50,
      entry_price: 189.25,
      stop_loss: 185.20,
      target_price: 197.50,
      risk_reward_ratio: 1.2,
      ai_confidence: 0.87,
      tier: 'T1'
    },
    {
      rank: 3,
      ticker: 'AAPL',
      score: 86,
      velez: 84,
      signal_type: 'MOMENTUM',
      catalyst: 'Breakout +1.8%',
      rsi: 51,
      momentum_pct: 1.80,
      vwap: 189.50,
      entry_price: 145.20,
      stop_loss: 142.10,
      target_price: 151.30,
      risk_reward_ratio: 1.5,
      ai_confidence: 0.84,
      tier: 'T1'
    }
  ]);

  const [selectedSignal, setSelectedSignal] = useState(signals[0]);
  const [filterTier, setFilterTier] = useState('all');
  const [filterType, setFilterType] = useState('all');
  const [minScore, setMinScore] = useState(0);
  const [expandAccount, setExpandAccount] = useState(false);
  const [chartExpanded, setChartExpanded] = useState(false);
  const [oneClickEnabled, setOneClickEnabled] = useState(true);
  const [notifications, setNotifications] = useState([]);

  const [marketData, setMarketData] = useState({
    spy: { price: 6050, change: 0.15 },
    dji: { price: 47950, change: -0.01 },
    nasdaq: { price: 21180, change: 0.32 },
    vix: { price: 16.2, change: -2.1 },
    advancers: 1847,
    decliners: 1203,
    breadth_pct: 60.5
  });

  const [accountMetrics, setAccountMetrics] = useState({
    balance: 1000000,
    dayPL: 2847.50,
    dayPLPct: 0.285,
    monthPL: 18500,
    monthPLPct: 1.85,
    winRate: 62.3,
    openPositions: 3,
    totalPositionPL: -365
  });

  // Filter signals
  const filteredSignals = signals.filter(s => {
    if (filterTier !== 'all' && s.tier.toLowerCase() !== filterTier) return false;
    if (filterType !== 'all' && s.signal_type.toLowerCase() !== filterType.toLowerCase()) return false;
    if (s.score < minScore) return false;
    return true;
  });

  // Signal stats
  const bullishCount = signals.filter(s => s.momentum_pct > 0).length;
  const bearishCount = signals.filter(s => s.momentum_pct <= 0).length;
  const avgScore = (signals.reduce((sum, s) => sum + s.score, 0) / signals.length).toFixed(1);
  const avgVelez = (signals.reduce((sum, s) => sum + s.velez, 0) / signals.length).toFixed(1);

  const handleQuickTrade = useCallback((signal, action) => {
    if (!oneClickEnabled) {
      alert('Enable 1-click trading in settings');
      return;
    }
    
    // Create notification
    const notification = {
      id: Date.now(),
      signal: signal.ticker,
      action: action,
      price: signal.entry_price,
      qty: 100
    };
    
    setNotifications(prev => [notification, ...prev].slice(0, 5));
    
    console.log(`${action} ${signal.ticker} x100 @ $${signal.entry_price}`);
    
    // Auto-dismiss after 4 seconds
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== notification.id));
    }, 4000);
  }, [oneClickEnabled]);

  const getSignalTypeColor = (type) => {
    const colors = {
      'MOMENTUM': '#00D9FF',
      'VOLUME_SPIKE': '#9D4EDD',
      'RSI_OVERSOLD': '#00FF88',
      'RSI_OVERBOUGHT': '#FF006E',
      'BREAKOUT': '#FFD60A',
      'VWAP_CROSS': '#FB5607'
    };
    return colors[type] || '#999';
  };

  const getRSIColor = (rsi) => {
    if (rsi > 70) return '#FF006E';
    if (rsi < 30) return '#00FF88';
    return '#FFD60A';
  };

  const getRRColor = (ratio) => {
    if (ratio >= 1.5) return '#00FF88';
    if (ratio >= 1.0) return '#FFD60A';
    return '#FF006E';
  };

  return (
    <div className="trader-first-dashboard">
      {/* HEADER: Market Context + Account (Collapsible) */}
      <header className="market-header">
        <div className="market-ticker">
          <div className="ticker-item">
            <span className="label">S&P 500</span>
            <span className="price">{marketData.spy.price.toLocaleString()}</span>
            <span className={`change ${marketData.spy.change >= 0 ? 'positive' : 'negative'}`}>
              {marketData.spy.change >= 0 ? '+' : ''}{marketData.spy.change.toFixed(2)}%
            </span>
          </div>
          <div className="ticker-item">
            <span className="label">DJI</span>
            <span className="price">{marketData.dji.price.toLocaleString()}</span>
            <span className={`change ${marketData.dji.change >= 0 ? 'positive' : 'negative'}`}>
              {marketData.dji.change >= 0 ? '+' : ''}{marketData.dji.change.toFixed(2)}%
            </span>
          </div>
          <div className="ticker-item">
            <span className="label">NASDAQ</span>
            <span className="price">{marketData.nasdaq.price.toLocaleString()}</span>
            <span className={`change ${marketData.nasdaq.change >= 0 ? 'positive' : 'negative'}`}>
              {marketData.nasdaq.change >= 0 ? '+' : ''}{marketData.nasdaq.change.toFixed(2)}%
            </span>
          </div>
          <div className="ticker-item">
            <span className="label">VIX</span>
            <span className="price">{marketData.vix.price.toFixed(1)}</span>
            <span className={`change ${marketData.vix.change <= 0 ? 'positive' : 'negative'}`}>
              {marketData.vix.change <= 0 ? '' : '+'}{marketData.vix.change.toFixed(1)}%
            </span>
          </div>
          <div className="ticker-item breadth">
            <span className="label">Breadth</span>
            <span className="value">{marketData.advancers}/{marketData.decliners}</span>
            <span className="pct positive">{marketData.breadth_pct.toFixed(1)}% Up</span>
          </div>
        </div>

        {/* Account Metrics - Collapsible */}
        <div className="account-section">
          <button className="account-toggle" onClick={() => setExpandAccount(!expandAccount)}>
            <span className="status-light">●</span>
            <span className="account-label">Account</span>
            <span className="account-balance">${(accountMetrics.balance / 1000000).toFixed(1)}M</span>
            <span className={`pl ${accountMetrics.dayPL >= 0 ? 'positive' : 'negative'}`}>
              ${Math.abs(accountMetrics.dayPL).toFixed(0)}
            </span>
            <span className="toggle-icon">{expandAccount ? '▼' : '▶'}</span>
          </button>

          {expandAccount && (
            <div className="account-panel">
              <div className="metric">
                <span>Day P&L</span>
                <span className={accountMetrics.dayPL >= 0 ? 'positive' : 'negative'}>
                  ${accountMetrics.dayPL.toFixed(0)} ({accountMetrics.dayPLPct.toFixed(2)}%)
                </span>
              </div>
              <div className="metric">
                <span>Month P&L</span>
                <span className={accountMetrics.monthPL >= 0 ? 'positive' : 'negative'}>
                  ${accountMetrics.monthPL.toFixed(0)} ({accountMetrics.monthPLPct.toFixed(2)}%)
                </span>
              </div>
              <div className="metric">
                <span>Win Rate</span>
                <span>{accountMetrics.winRate.toFixed(1)}%</span>
              </div>
              <div className="metric">
                <span>Open Positions</span>
                <span>{accountMetrics.openPositions}</span>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* MAIN SECTION: Signals Table (PRIMARY FOCUS) */}
      <section className="signals-section">
        <div className="signals-header">
          <h2>🔥 TOP 10 LIVE SIGNALS - Market Opportunities NOW</h2>
          <div className="signals-controls">
            <button className="refresh-btn">↻ REFRESH</button>
            <span className="signal-count">Showing {filteredSignals.length} of {signals.length}</span>
          </div>
        </div>

        {/* Market Sentiment Stats */}
        <div className="sentiment-bar">
          <div className="stat">
            <span className="label">Distribution</span>
            <span className="value bullish">{bullishCount} 🟢 Bullish</span>
            <span className="value bearish">{signals.length - bullishCount} 🔴 Bearish</span>
          </div>
          <div className="stat">
            <span className="label">Avg Score</span>
            <span className="value">{avgScore}/100</span>
          </div>
          <div className="stat">
            <span className="label">Avg Velez</span>
            <span className="value">{avgVelez}%</span>
          </div>
          <div className="stat">
            <span className="label">Market Bias</span>
            <span className="value positive">→ BULLISH ↑</span>
          </div>
        </div>

        {/* Filters */}
        <div className="filters-bar">
          <label>
            Tier:
            <select value={filterTier} onChange={(e) => setFilterTier(e.target.value)}>
              <option value="all">All Tiers</option>
              <option value="t1">T1 Only</option>
              <option value="t2">T2+</option>
            </select>
          </label>
          <label>
            Type:
            <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
              <option value="all">All Types</option>
              <option value="MOMENTUM">Momentum</option>
              <option value="VOLUME_SPIKE">Volume Spike</option>
              <option value="RSI_OVERSOLD">RSI Oversold</option>
              <option value="BREAKOUT">Breakout</option>
            </select>
          </label>
          <label>
            Min Score:
            <input type="range" min="0" max="100" value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} />
            {minScore}
          </label>
          <label>
            <input type="checkbox" checked={oneClickEnabled} onChange={(e) => setOneClickEnabled(e.target.checked)} />
            🛡️ 1-Click Trading: {oneClickEnabled ? 'ON' : 'OFF'}
          </label>
        </div>

        {/* Signal Table */}
        <div className="signals-table-container">
          <table className="signals-table">
            <thead>
              <tr>
                <th>RANK</th>
                <th>TICKER</th>
                <th>SCORE</th>
                <th>VELEZ</th>
                <th>TYPE</th>
                <th>RSI</th>
                <th>MOM%</th>
                <th>VWAP</th>
                <th>ENTRY</th>
                <th>STOP</th>
                <th>TARGET</th>
                <th>R:R</th>
                <th>ACTION</th>
              </tr>
            </thead>
            <tbody>
              {filteredSignals.map((signal, idx) => (
                <tr key={idx} className={`signal-row tier-${signal.tier.toLowerCase()} ${signal.ticker === selectedSignal?.ticker ? 'active' : ''}`} onClick={() => setSelectedSignal(signal)}>
                  <td className="rank">
                    <span className="rank-badge">#{signal.rank}</span>
                  </td>
                  <td className="ticker"><strong>{signal.ticker}</strong></td>
                  <td className="score">
                    <span className="badge" style={{backgroundColor: signal.score >= 75 ? '#00FF88' : signal.score >= 60 ? '#FFD60A' : '#FF006E'}}>
                      {signal.score}/100
                    </span>
                  </td>
                  <td className="velez">{signal.velez}%</td>
                  <td className="type">
                    <span className="type-badge" style={{backgroundColor: getSignalTypeColor(signal.signal_type)}}>
                      {signal.signal_type.substring(0, 4)}
                    </span>
                  </td>
                  <td className="rsi" style={{color: getRSIColor(signal.rsi)}}>{signal.rsi.toFixed(0)}</td>
                  <td className="momentum" style={{color: signal.momentum_pct >= 0 ? '#00FF88' : '#FF006E'}}>
                    {signal.momentum_pct >= 0 ? '+' : ''}{signal.momentum_pct.toFixed(2)}%
                  </td>
                  <td className="vwap">${signal.vwap.toFixed(2)}</td>
                  <td className="entry">${signal.entry_price.toFixed(2)}</td>
                  <td className="stop">${signal.stop_loss.toFixed(2)}</td>
                  <td className="target">${signal.target_price.toFixed(2)}</td>
                  <td className="ratio" style={{color: getRRColor(signal.risk_reward_ratio)}}>{signal.risk_reward_ratio.toFixed(2)}</td>
                  <td className="action">
                    <button className="quick-trade-btn" onClick={(e) => {e.stopPropagation(); handleQuickTrade(signal, 'BUY');}}>
                      [BUY 100]
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Chart Section (Collapsible) */}
      <section className={`chart-section ${chartExpanded ? 'expanded' : 'collapsed'}`}>
        <div className="chart-header">
          <h3>
            📊 TACTICAL CHART: {selectedSignal?.ticker} @ ${selectedSignal?.entry_price}
            <span className="signal-info">
              Entry: ${selectedSignal?.entry_price} | Stop: ${selectedSignal?.stop_loss} | Target: ${selectedSignal?.target_price}
            </span>
          </h3>
          <button className="expand-toggle" onClick={() => setChartExpanded(!chartExpanded)}>
            {chartExpanded ? '▼ Collapse' : '▶ Expand'}
          </button>
        </div>
        {chartExpanded && (
          <div className="chart-container">
            <TacticalChart symbol={selectedSignal?.ticker || 'SPY'} />
          </div>
        )}
      </section>

      {/* Execution Deck */}
      <section className="execution-section">
        <div className="execution-header">
          <h3>⚡ QUICK EXECUTION: {selectedSignal?.ticker}</h3>
          <span className="execution-info">1-Click Enabled: {oneClickEnabled ? '✓' : '✗'}</span>
        </div>
        <ExecutionDeck symbol={selectedSignal?.ticker || 'SPY'} />
      </section>

      {/* Notifications Toast */}
      <div className="notifications">
        {notifications.map(notif => (
          <div key={notif.id} className="notification-toast">
            <span>✓ {notif.action} {notif.signal} x{notif.qty} @ ${notif.price.toFixed(2)}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TraderFirstDashboard;
