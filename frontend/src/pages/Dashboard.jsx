import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import '../styles/Dashboard.css';

export default function Dashboard() {
  // ========== STATE ==========
  const [activeSignal, setActiveSignal] = useState(null);
  const [showChart, setShowChart] = useState(false);
  const [showAccount, setShowAccount] = useState(false);
  const [signals, setSignals] = useState([]);
  const [selectedStrategy, setSelectedStrategy] = useState('TWAP');
  const [riskChecks, setRiskChecks] = useState({});
  const [marketData] = useState({
    spy: 595.45, spyChange: 0.15,
    dji: 47950, djiChange: -0.01,
    nasdaq: 21180, nasdaqChange: 0.32,
    vix: 16.2, vixChange: -2.1,
    breadth: { advancers: 1847, decliners: 1203 }
  });
  const [portfolio] = useState({
    balance: 1000000, dayPL: 2340, dayPLPct: 0.23,
    winRate: 0.725, modelAccuracy: 0.752
  });

  const mockSignals = [
    { id: 1, rank: 1, ticker: 'YUM', score: 94, velez: 91, type: 'MOMENTUM', catalyst: 'Strong momentum +2.94%, Volume 2.6x avg', rsi: 42, momentum: 2.94, vwap: 148.00, entry: 148.12, stop: 145.00, target: 152.60, rr: 1.9 },
    { id: 2, rank: 2, ticker: 'NVDA', score: 89, velez: 87, type: 'VOLUME', catalyst: 'Blackwell chip production ramp-up confirmed', rsi: 37, momentum: 2.14, vwap: 189.50, entry: 189.25, stop: 185.00, target: 197.50, rr: 2.1 },
    { id: 3, rank: 3, ticker: 'AAPL', score: 86, velez: 84, type: 'MOMENTUM', catalyst: 'Analyst upgrade + earnings beat expectations', rsi: 51, momentum: 1.82, vwap: 225.00, entry: 225.45, stop: 220.00, target: 235.60, rr: 1.6 },
    { id: 4, rank: 4, ticker: 'TSLA', score: 82, velez: 79, type: 'RSI', catalyst: 'Oversold on sector pullback, support holding', rsi: 28, momentum: 1.23, vwap: 243.00, entry: 243.80, stop: 235.00, target: 258.40, rr: 1.7 },
    { id: 5, rank: 5, ticker: 'MSFT', score: 78, velez: 75, type: 'VOLUME', catalyst: 'Cloud growth accelerating, guidance raised', rsi: 58, momentum: 1.56, vwap: 372.00, entry: 372.10, stop: 365.00, target: 388.50, rr: 1.5 },
    { id: 6, rank: 6, ticker: 'GOOGL', score: 75, velez: 72, type: 'MOMENTUM', catalyst: 'AI products showing strong adoption metrics', rsi: 45, momentum: 1.89, vwap: 139.00, entry: 139.30, stop: 134.00, target: 148.20, rr: 1.8 },
    { id: 7, rank: 7, ticker: 'AMD', score: 72, velez: 68, type: 'RSI', catalyst: 'Data center demand strength, technical bounce', rsi: 31, momentum: 0.92, vwap: 168.00, entry: 168.50, stop: 162.00, target: 180.30, rr: 1.4 },
    { id: 8, rank: 8, ticker: 'META', score: 68, velez: 65, type: 'VOLUME', catalyst: 'Ad recovery thesis + AI infrastructure spending', rsi: 62, momentum: 1.34, vwap: 492.00, entry: 492.20, stop: 485.00, target: 512.80, rr: 1.6 },
    { id: 9, rank: 9, ticker: 'NFLX', score: 65, velez: 61, type: 'MOMENTUM', catalyst: 'Subscriber growth beat + margin expansion', rsi: 55, momentum: 0.78, vwap: 282.00, entry: 282.90, stop: 275.00, target: 298.40, rr: 1.5 },
    { id: 10, rank: 10, ticker: 'CRWD', score: 62, velez: 58, type: 'RSI', catalyst: 'Security demand resilient despite macro concerns', rsi: 26, momentum: 0.54, vwap: 345.00, entry: 345.10, stop: 335.00, target: 365.80, rr: 1.3 }
  ];

  useEffect(() => {
    setSignals(mockSignals);
    setRiskChecks({
      heat: { value: '14.2%', limit: '15%', status: 'pass' },
      sector: { value: '9.1%', limit: '10%', status: 'pass' },
      correlation: { value: '1 pos', limit: '<2', status: 'pass' },
      vix: { value: '1.0x', detail: 'VIX: 16.2', status: 'pass' },
      drawdown: { value: '-0.23%', limit: '-10%', status: 'pass' },
      timeFilter: { value: '10:30 AM', detail: 'Valid hours', status: 'pass' }
    });
  }, []);

  const handleSignalClick = (signal) => { setActiveSignal(signal); setShowChart(true); };
  const getRSIColor = (rsi) => rsi > 70 ? 'overbought' : rsi < 30 ? 'oversold' : 'neutral';
  const getMomentumColor = (momentum) => momentum > 0 ? 'positive' : 'negative';
  const getRRColor = (rr) => rr > 1.5 ? 'excellent' : rr > 1.0 ? 'good' : 'poor';
  const getScoreColor = (score) => score >= 85 ? 'high' : score >= 75 ? 'medium' : 'low';

  const bullishCount = signals.filter(s => s.momentum > 0).length;
  const bearishCount = signals.filter(s => s.momentum <= 0).length;
  const avgScore = (signals.reduce((sum, s) => sum + s.score, 0) / signals.length).toFixed(1);
  const avgVelez = (signals.reduce((sum, s) => sum + s.velez, 0) / signals.length).toFixed(1);

  function generateChartData(ticker) {
    const basePrice = { 'YUM': 148, 'NVDA': 189, 'AAPL': 225, 'TSLA': 243, 'MSFT': 372, 'GOOGL': 139, 'AMD': 168, 'META': 492, 'NFLX': 282, 'CRWD': 345 }[ticker] || 200;
    return Array.from({ length: 48 }, (_, i) => ({ time: `${String(Math.floor(i / 2)).padStart(2, '0')}:${String((i % 2) * 30).padStart(2, '0')}`, price: basePrice + (Math.random() - 0.5) * 10 + Math.sin(i / 10) * 5, ma20: basePrice + Math.sin(i / 15) * 3 }));
  }

  function buySignal(ticker, price) {
    const toast = document.createElement('div');
    toast.className = 'toast toast-success';
    toast.textContent = `✓ BUY INITIATED: ${ticker} @ $${price.toFixed(2)}`;
    document.getElementById('toast-container').appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
  }

  return (
    <div className="dashboard-signal-first">
      {/* ========== MARKET CONTEXT HEADER ========== */}
      <div className="market-header">
        <div className="market-tickers">
          <div className="ticker-item">
            <span className="ticker-label">S&P 500</span>
            <span className="ticker-value">{marketData.spy.toFixed(2)}</span>
            <span className={`ticker-change ${marketData.spyChange > 0 ? 'positive' : 'negative'}`}>
              {marketData.spyChange > 0 ? '+' : ''}{marketData.spyChange.toFixed(2)}%
            </span>
          </div>

          <div className="ticker-item">
            <span className="ticker-label">DJI</span>
            <span className="ticker-value">{marketData.dji.toLocaleString()}</span>
            <span className={`ticker-change ${marketData.djiChange > 0 ? 'positive' : 'negative'}`}>
              {marketData.djiChange > 0 ? '+' : ''}{marketData.djiChange.toFixed(2)}%
            </span>
          </div>

          <div className="ticker-item">
            <span className="ticker-label">NASDAQ</span>
            <span className="ticker-value">{marketData.nasdaq.toLocaleString()}</span>
            <span className={`ticker-change ${marketData.nasdaqChange > 0 ? 'positive' : 'negative'}`}>
              {marketData.nasdaqChange > 0 ? '+' : ''}{marketData.nasdaqChange.toFixed(2)}%
            </span>
          </div>

          <div className="ticker-item vix">
            <span className="ticker-label">VIX</span>
            <span className="ticker-value">{marketData.vix.toFixed(1)}</span>
            <span className={`ticker-change ${marketData.vixChange > 0 ? 'negative' : 'positive'}`}>
              {marketData.vixChange > 0 ? '+' : ''}{marketData.vixChange.toFixed(1)}%
            </span>
          </div>

          <div className="ticker-item breadth">
            <span className="ticker-label">Breadth</span>
            <span className="breadth-value">
              {(marketData.breadth.advancers / (marketData.breadth.advancers + marketData.breadth.decliners) * 100).toFixed(1)}% Up
            </span>
          </div>

          <div className="ticker-item account" onClick={() => setShowAccount(!showAccount)}>
            <span className="ticker-label">Account</span>
            <span className="ticker-value" style={{ cursor: 'pointer' }}>${(portfolio.balance / 1000000).toFixed(1)}M</span>
            <span className={`ticker-change ${portfolio.dayPL > 0 ? 'positive' : 'negative'}`}>
              {portfolio.dayPL > 0 ? '+' : ''}${portfolio.dayPL.toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      {/* ========== ACCOUNT PANEL (COLLAPSED) ========== */}
      {showAccount && (
        <div className="account-panel">
          <button className="account-close" onClick={() => setShowAccount(false)}>×</button>
          <h3>Account Metrics</h3>
          <div className="account-metrics">
            <div className="metric"><span>Balance</span> <span>${portfolio.balance.toLocaleString()}</span></div>
            <div className="metric"><span>Day P&L</span> <span className={portfolio.dayPL > 0 ? 'positive' : 'negative'}>{portfolio.dayPL > 0 ? '+' : ''}${portfolio.dayPL.toLocaleString()} ({portfolio.dayPLPct > 0 ? '+' : ''}{portfolio.dayPLPct.toFixed(2)}%)</span></div>
            <div className="metric"><span>Win Rate</span> <span className="positive">{(portfolio.winRate * 100).toFixed(1)}%</span></div>
            <div className="metric"><span>Model Accuracy</span> <span className="positive">{(portfolio.modelAccuracy * 100).toFixed(1)}%</span></div>
          </div>
        </div>
      )}

      {/* ========== SIGNAL INTELLIGENCE STATS ========== */}
      <div className="signal-stats">
        <div className="stat-box">
          <span className="stat-label">🔥 Active Signals</span>
          <span className="stat-value">{signals.length}</span>
        </div>
        <div className="stat-box">
          <span className="stat-label">📈 Bullish / Bearish</span>
          <span className="stat-value"><span style={{ color: '#00FF88' }}>{bullishCount}</span> / <span style={{ color: '#FF0055' }}>{bearishCount}</span></span>
        </div>
        <div className="stat-box">
          <span className="stat-label">📊 Avg Score</span>
          <span className="stat-value">{avgScore}/100</span>
        </div>
        <div className="stat-box">
          <span className="stat-label">🤖 Avg Velez</span>
          <span className="stat-value">{avgVelez}%</span>
        </div>
        <div className="stat-box">
          <span className="stat-label">📍 Market Bias</span>
          <span className="stat-value" style={{ color: '#00FF88' }}>BULLISH ↑</span>
        </div>
      </div>

      <div className="dashboard-main">
        {/* ========== LEFT: SIGNALS TABLE (PRIMARY FOCUS) ========== */}
        <div className="signals-section">
          <div className="signals-header">
            <h2>🔥 Top 10 Live Signals - Click to Load Chart</h2>
            <div className="filters">
              <select defaultValue="all"><option value="all">All Tiers</option><option value="t1">T1 Only</option></select>
              <select defaultValue="all"><option value="all">All Types</option><option value="momentum">Momentum</option></select>
            </div>
          </div>

          <div className="table-wrapper">
            <table className="signals-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Ticker</th>
                  <th>Score</th>
                  <th>Velez</th>
                  <th>Type</th>
                  <th>Catalyst</th>
                  <th>RSI</th>
                  <th>Mom%</th>
                  <th>Entry</th>
                  <th>R:R</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {signals.map((signal) => (
                  <tr key={signal.id} className={activeSignal?.id === signal.id ? 'active' : ''} onClick={() => handleSignalClick(signal)} style={{ cursor: 'pointer' }}>
                    <td>{signal.rank === 1 ? '🥇' : signal.rank === 2 ? '🥈' : signal.rank === 3 ? '🥉' : signal.rank}</td>
                    <td className="ticker-link"><strong>{signal.ticker}</strong></td>
                    <td><span className={`score-badge score-${getScoreColor(signal.score)}`}>{signal.score}</span></td>
                    <td>{signal.velez}%</td>
                    <td><span className={`type-badge type-${signal.type.toLowerCase()}`}>{signal.type}</span></td>
                    <td className="catalyst-text">{signal.catalyst}</td>
                    <td><span className={`rsi-badge rsi-${getRSIColor(signal.rsi)}`}>{signal.rsi}</span></td>
                    <td><span className={`momentum-badge ${getMomentumColor(signal.momentum)}`}>{signal.momentum > 0 ? '+' : ''}{signal.momentum.toFixed(2)}%</span></td>
                    <td>${signal.entry.toFixed(2)}</td>
                    <td><span className={`rr-badge rr-${getRRColor(signal.rr)}`}>{signal.rr.toFixed(1)}</span></td>
                    <td><button className="btn-buy" onClick={() => buySignal(signal.ticker, signal.entry)}>BUY</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ========== RIGHT: EXECUTION & RISK ========== */}
        <div className="right-sidebar">
          {/* EXECUTION DECK */}
          <div className="execution-deck">
            <h3>⚡ Quick Execution</h3>
            {activeSignal ? (
              <div className="execution-form">
                <div className="exec-symbol">{activeSignal.ticker}</div>
                <div className="exec-group">
                  <label>Strategy</label>
                  <select value={selectedStrategy} onChange={(e) => setSelectedStrategy(e.target.value)}>
                    <option value="TWAP">TWAP (15 min)</option>
                    <option value="VWAP">VWAP</option>
                    <option value="MARKET">Market</option>
                  </select>
                </div>
                <div className="exec-group">
                  <label>Qty</label>
                  <input type="number" defaultValue="100" min="1" />
                </div>
                <button className="btn-execute" onClick={() => buySignal(activeSignal.ticker, activeSignal.entry)}>Execute {selectedStrategy}</button>
                <p className="exec-note">Entry: ${activeSignal.entry.toFixed(2)} | Stop: ${activeSignal.stop.toFixed(2)} | Tgt: ${activeSignal.target.toFixed(2)}</p>
              </div>
            ) : (
              <p className="no-selection">← Click signal to execute</p>
            )}
          </div>

          {/* RISK MONITOR */}
          <div className="risk-monitor">
            <h3>🎯 6-Layer Risk</h3>
            <div className="risk-items">
              {Object.entries(riskChecks).map(([key, check]) => (
                <div key={key} className={`risk-item risk-${check.status}`}>
                  <span className="risk-label">{key === 'heat' ? 'Portfolio Heat' : key === 'sector' ? 'Sector Limit' : key === 'correlation' ? 'Correlation' : key === 'vix' ? 'VIX Adjust' : key === 'drawdown' ? 'Daily DD' : 'Trading Hours'}</span>
                  <span className="risk-value">{check.value}</span>
                  <span className="risk-icon">✅</span>
                </div>
              ))}</div>
          </div>
        </div>
      </div>

      {/* ========== COLLAPSIBLE CHART ========== */}
      {activeSignal && (
        <div className="chart-section">
          <div className="chart-header">
            <h3>📊 {activeSignal.ticker} Technical Analysis</h3>
            <button className="chart-toggle" onClick={() => setShowChart(!showChart)}>
              {showChart ? '▼ Collapse' : '▶ Expand'}
            </button>
          </div>

          {showChart && (
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={generateChartData(activeSignal.ticker)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="time" stroke="#999" style={{ fontSize: '12px' }} />
                  <YAxis stroke="#999" style={{ fontSize: '12px' }} />
                  <Tooltip contentStyle={{ background: '#f9f9f9', border: '1px solid #ddd', borderRadius: '6px' }} />
                  <Line type="monotone" dataKey="price" stroke="#2180 8d" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="ma20" stroke="#ff9800" strokeWidth={1} strokeDasharray="5 5" dot={false} />
                </LineChart>
              </ResponsiveContainer>

              <div className="chart-info">
                <div className="info-item">Entry: ${activeSignal.entry.toFixed(2)}</div>
                <div className="info-item">Stop: ${activeSignal.stop.toFixed(2)}</div>
                <div className="info-item">Target: ${activeSignal.target.toFixed(2)}</div>
                <div className="info-item">R:R: {activeSignal.rr.toFixed(1)}</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TOAST CONTAINER */}
      <div id="toast-container"></div>
    </div>
  );
}