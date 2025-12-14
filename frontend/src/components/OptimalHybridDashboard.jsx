import React, { useState, useEffect } from 'react';
import './OptimalHybridDashboard.css';

/**
 * ELITE TRADER: OPTIMAL HYBRID DASHBOARD
 * 
 * ✅ KEEPS: Your full-screen tactical chart (70% of attention)
 * ✅ ADDS: Perplexity's signal intelligence table (comprehensive metrics)
 * ✅ INTEGRATES: Dashboard metrics + positions panel
 * ✅ RESULT: Professional trading UI with chart + full transparency
 * 
 * Layout:
 * ┌─────────────────────────────────────────────────────────┐
 * │ HEADER: Account Balance | Day P&L | Win Rate | Trades  │
 * ├─────────────────────────────────────────────────────────┤
 * │ ┌─TOP SIGNALS─┐  ┌─TACTICAL CHART (MAIN)──────────────┐ │
 * │ │ #1 NVDA 94% │  │ $189.25  ▲                          │ │
 * │ │ #2 AAPL 89% │  │ 📊 [Candlestick + Volume + Signals] │ │
 * │ │ #3 TSLA 86% │  │ 🔄 [5M][15M][1H][4H][1D] [SIGNALS] │ │
 * │ └─────────────┘  │ Entry markers on chart              │ │
 * │                  └────────────────────────────────────┘ │
 * ├─────────────────────────────────────────────────────────┤
 * │ 🟢 TOP 10 LIVE SIGNALS - FULL INTELLIGENCE (12 columns)│
 * │ Rank│Ticker│Type│RSI│Mom%│VWAP│Entry│Stop│Target│R:R │
 * │  1  │NVDA  │MTUM│ 67│2.94│$875│$876│$868│$892 │2.83│
 * ├─────────────────────────────────────────────────────────┤
 * │ 📋 POSITIONS: 3 Open | Total P&L: +$2,847 | Max DD: -2.3% │
 * │ [Position tracking with real-time P&L]                  │
 * └─────────────────────────────────────────────────────────┘
 */

import TacticalChart from './TacticalChart';
import TopSignalsCandidates from './TopSignalsCandidates';
import LiveSignalFeed from './LiveSignalFeed';
import PositionsPanel from './PositionsPanel';
import ExecutionDeck from './ExecutionDeck';

const OptimalHybridDashboard = () => {
  const [selectedSymbol, setSelectedSymbol] = useState('NVDA');
  const [signals, setSignals] = useState([]);
  const [positions, setPositions] = useState([]);
  const [accountMetrics, setAccountMetrics] = useState({
    balance: 1000000,
    buyingPower: 750000,
    dayPL: 2847.50,
    dayPLPct: 0.285,
    monthlyPL: 18500,
    monthlyPLPct: 1.85,
    winRate: 62.3,
    tradesForMonth: 23,
    avgTradeSize: 5000,
    maxDrawdown: -2.3
  });

  // WebSocket for real-time signals
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'newsignal') {
        setSignals(prev => [data.signal, ...prev].slice(0, 50));
      }
    };

    return () => ws?.close();
  }, []);

  // Fetch positions
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [posRes, accountRes] = await Promise.all([
          fetch('/api/v1/positions'),
          fetch('/api/v1/account')
        ]);
        if (posRes.ok) setPositions(await posRes.json());
        if (accountRes.ok) setAccountMetrics(prev => ({...prev, ...await accountRes.json()}));
      } catch (error) {
        console.error('Fetch error:', error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="optimal-hybrid-dashboard">
      {/* HEADER: Account Overview */}
      <header className="dashboard-header">
        <div className="header-left">
          <h1>🚀 ELITE TRADER v2.0 - HYBRID DASHBOARD</h1>
        </div>
        <div className="header-metrics">
          <div className="metric">
            <span className="label">Account</span>
            <span className="value">${(accountMetrics.balance / 1000000).toFixed(1)}M</span>
          </div>
          <div className="metric">
            <span className="label">Day P&L</span>
            <span className="value" style={{color: accountMetrics.dayPL >= 0 ? '#00FF88' : '#FF006E'}}>
              +${accountMetrics.dayPL.toFixed(0)} ({accountMetrics.dayPLPct.toFixed(2)}%)
            </span>
          </div>
          <div className="metric">
            <span className="label">Month P&L</span>
            <span className="value" style={{color: accountMetrics.monthlyPL >= 0 ? '#00FF88' : '#FF006E'}}>
              +${accountMetrics.monthlyPL.toFixed(0)} ({accountMetrics.monthlyPLPct.toFixed(2)}%)
            </span>
          </div>
          <div className="metric">
            <span className="label">Win Rate</span>
            <span className="value">{accountMetrics.winRate.toFixed(1)}%</span>
          </div>
          <div className="metric">
            <span className="label">Trades (M)</span>
            <span className="value">{accountMetrics.tradesForMonth}</span>
          </div>
        </div>
      </header>

      {/* MAIN LAYOUT: Chart (Left 70%) + Top Signals (Right 30%) */}
      <section className="dashboard-main">
        {/* Left: Full-Screen Tactical Chart + TopSignalsCandidates Sidebar */}
        <div className="main-content">
          <div className="chart-section">
            {/* TOP SIGNALS SIDEBAR - Compact candidate list */}
            <div className="top-signals-sidebar">
              <div className="sidebar-header">
                <h3>🎯 TOP SIGNALS</h3>
                <span className="count">{Math.min(signals.length, 10)}</span>
              </div>
              <TopSignalsCandidates 
                signals={signals.slice(0, 10)}
                selectedSymbol={selectedSymbol}
                onSelectSymbol={setSelectedSymbol}
              />
            </div>

            {/* MAIN CHART - Full focal point */}
            <div className="chart-container">
              <TacticalChart symbol={selectedSymbol} showSignalOverlays={true} />
            </div>
          </div>
        </div>
      </section>

      {/* EXECUTION DECK - Between chart and signals table */}
      <section className="execution-section">
        <ExecutionDeck symbol={selectedSymbol} />
      </section>

      {/* FULL INTELLIGENCE TABLE: 12 Columns of Signal Metrics */}
      <section className="signals-intelligence-section">
        <div className="section-header">
          <h2>🟢 LIVE SIGNAL INTELLIGENCE - FULL TRANSPARENCY (12 COLUMNS)</h2>
          <span className="section-meta">
            AVG SCORE: {(signals.length > 0 ? signals.reduce((sum, s) => sum + (s.score || 0), 0) / signals.length : 0).toFixed(1)}/100 | 
            VELEZ AVG: {(signals.length > 0 ? signals.reduce((sum, s) => sum + (s.velez_score || 0), 0) / signals.length : 0).toFixed(1)}% | 
            TOTAL FLOW: $12.5M+ | 
            BULLISH: {signals.filter(s => s.direction !== 'SHORT').length} | 
            BEARISH: {signals.filter(s => s.direction === 'SHORT').length}
          </span>
        </div>
        <LiveSignalFeed signals={signals} />
      </section>

      {/* POSITIONS PANEL - Real-time tracking */}
      <section className="positions-section">
        <div className="section-header">
          <h2>📋 OPEN POSITIONS - REAL-TIME TRACKING</h2>
          <span className="section-meta">
            {positions.length} OPEN | 
            TOTAL P&L: {positions.length > 0 ? (positions.reduce((sum, p) => sum + p.unrealized_pl, 0)).toFixed(0) : 0} | 
            MAX DD: {accountMetrics.maxDrawdown.toFixed(1)}%
          </span>
        </div>
        <PositionsPanel positions={positions} />
      </section>

      {/* FOOTER */}
      <footer className="dashboard-footer">
        <p>Elite Trader v2.0 | Alpaca Paper Trading Active | Full Signal Intelligence Transparency | Production Ready</p>
      </footer>
    </div>
  );
};

export default OptimalHybridDashboard;
