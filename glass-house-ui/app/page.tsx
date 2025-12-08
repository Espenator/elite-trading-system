'use client';

import { useEffect, useState } from 'react';

interface Signal {
  id: string;
  ticker: string;
  currentPrice: number;
  percentChange: number;
  globalConfidence: number;
  direction: string;
  volume: number;
  marketCap: number;
  tier?: string;
  rvol?: number;
}

export default function EliteTraderTerminal() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string>('SPY');
  const [currentTime, setCurrentTime] = useState(new Date());

  // Fetch signals from backend
  useEffect(() => {
    fetch('http://localhost:8000/api/signals/?limit=100')
      .then(res => res.json())
      .then(data => setSignals(data))
      .catch(err => console.error('Backend connection error:', err));
  }, []);

  // Update time every second
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Get top candidates (for Intelligence Radar)
  const topCandidates = signals.slice(0, 25);
  
  // Get active signals (for Execution Deck)
  const activeSignals = signals.filter(s => s.globalConfidence >= 70).slice(0, 5);

  return (
    <div className="elite-terminal-grid">
      {/* ZONE 0: COMMAND BAR */}
      <div className="command-bar">
        <div className="flex items-center gap-6 w-full">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-cyan-400 to-purple-500 rounded-lg flex items-center justify-center">
              <span className="text-xl font-bold">ET</span>
            </div>
            <h1 className="text-xl font-bold cyan-glow-text">ELITE TRADER</h1>
          </div>

          {/* Search Bar */}
          <div className="flex-1 max-w-md">
            <input
              type="text"
              placeholder="Search tickers..."
              className="w-full px-4 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none"
            />
          </div>

          {/* Market Indices */}
          <div className="flex gap-4">
            <div className="main-symbol-card">
              <div className="text-xs text-slate-400">S&P 500</div>
              <div className="text-lg font-mono font-bold">6,850.69</div>
              <div className="text-xs text-green-400">+0.51%</div>
            </div>
            <div className="main-symbol-card">
              <div className="text-xs text-slate-400">DJI</div>
              <div className="text-lg font-mono font-bold">47,950</div>
              <div className="text-xs text-red-400">-0.01%</div>
            </div>
            <div className="main-symbol-card">
              <div className="text-xs text-slate-400">NASDAQ</div>
              <div className="text-lg font-mono font-bold">21,180</div>
              <div className="text-xs text-green-400">+0.12%</div>
            </div>
          </div>

          {/* System Status */}
          <div className="flex items-center gap-2 ml-auto">
            <div className="live-indicator w-2 h-2 bg-green-400 rounded-full"></div>
            <span className="text-xs text-slate-400">System Active</span>
            <span className="text-xs text-slate-500">|</span>
            <span className="text-xs text-green-400 font-mono">12ms</span>
          </div>

          {/* Time */}
          <div className="text-sm text-slate-400 font-mono">
            {currentTime.toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* ZONE 1: INTELLIGENCE RADAR - Left Panel */}
      <div className="intelligence-radar">
        <div className="mb-4">
          <h3 className="text-cyan-400 mb-2">TOP TRADE CANDIDATES</h3>
          <div className="text-xs text-slate-500">Updated 2 mins ago</div>
        </div>

        <div className="space-y-2">
          {topCandidates.map((signal, index) => (
            <div 
              key={signal.id}
              className="candidate-card slide-in"
              onClick={() => setSelectedTicker(signal.ticker)}
            >
              {/* Header Row */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">#{index + 1}</span>
                  <span className="ticker text-lg cyan-glow-text">{signal.ticker}</span>
                </div>
                <div className={`text-sm font-bold ${signal.percentChange >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {signal.percentChange >= 0 ? '+' : ''}{signal.percentChange.toFixed(2)}%
                </div>
              </div>

              {/* Tier Badge */}
              <div className="mb-2">
                <span className={`tier-badge ${signal.tier === 'Core' ? 'tier-core' : signal.tier === 'Hot' ? 'tier-hot' : 'tier-liquid'}`}>
                  {signal.tier || 'LIQUID'}
                </span>
              </div>

              {/* Metrics Row */}
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div>
                  <span className="text-slate-500">Score:</span>
                  <span className="text-white ml-1">{signal.globalConfidence}</span>
                </div>
                <div>
                  <span className="text-slate-500">Conf:</span>
                  <span className="text-white ml-1">{signal.globalConfidence}%</span>
                </div>
                <div>
                  <span className="text-slate-500">Vol:</span>
                  <span className="text-white ml-1">{(signal.volume / 1000000).toFixed(1)}M</span>
                </div>
                <div>
                  <span className="text-slate-500">RVOL:</span>
                  <span className="text-white ml-1">{signal.rvol || '1.5'}x</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ZONE 2: TACTICAL CHART - Center Panel */}
      <div className="tactical-chart">
        <div className="glass-card h-full flex flex-col">
          {/* Chart Header */}
          <div className="flex items-center justify-between p-4 border-b border-slate-700">
            <div>
              <h2 className="text-2xl font-bold cyan-glow-text">{selectedTicker}</h2>
              <div className="text-sm text-slate-400">Tactical Chart Center</div>
            </div>
            
            {/* Timeframe Selector */}
            <div className="flex gap-2">
              {['1D', '1H', '15M', '5M'].map(tf => (
                <button
                  key={tf}
                  className="px-4 py-2 rounded-lg border border-cyan-500/30 bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/25 transition-all"
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>

          {/* Chart Placeholder */}
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="text-6xl mb-4 cyan-glow-text">📈</div>
              <h3 className="text-xl text-slate-400 mb-2">TradingView Chart</h3>
              <p className="text-sm text-slate-500">Chart integration coming next</p>
              <p className="text-xs text-slate-600 mt-2">Selected: {selectedTicker}</p>
            </div>
          </div>

          {/* Factor Strip */}
          <div className="h-16 bg-slate-900/80 border-t border-slate-700 p-3">
            <div className="flex gap-2">
              <div className="flex-1 h-8 bg-yellow-500/20 border border-yellow-500/40 rounded flex items-center justify-center text-xs">
                High Vol
              </div>
              <div className="flex-1 h-8 bg-green-500/20 border border-green-500/40 rounded flex items-center justify-center text-xs">
                Breakout
              </div>
              <div className="flex-1 h-8 bg-purple-500/20 border border-purple-500/40 rounded flex items-center justify-center text-xs">
                RSI Surge
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ZONE 3: EXECUTION DECK - Right Panel */}
      <div className="execution-deck">
        <div className="mb-4">
          <h3 className="text-cyan-400 mb-2">ACTIVE SIGNALS</h3>
        </div>

        <div className="space-y-4">
          {/* Ignition Signal */}
          {activeSignals.slice(0, 2).map(signal => (
            <div key={signal.id} className="signal-card ignition">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-3 h-3 bg-green-400 rounded-full live-indicator"></div>
                <h4 className="text-xs font-bold text-slate-400">IGNITION SIGNAL</h4>
              </div>
              
              <div className="mb-3">
                <div className="text-2xl font-bold ticker cyan-glow-text">{signal.ticker}</div>
                <div className="text-sm text-slate-400">Entry: ${signal.currentPrice.toFixed(2)}</div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                <div>
                  <div className="text-slate-500">Target</div>
                  <div className="text-green-400 font-bold">${(signal.currentPrice * 1.12).toFixed(2)} (+11.7%)</div>
                </div>
                <div>
                  <div className="text-slate-500">Stop</div>
                  <div className="text-red-400 font-bold">${(signal.currentPrice * 0.955).toFixed(2)} (-4.5%)</div>
                </div>
              </div>

              <div className="mb-3">
                <div className="text-xs text-slate-500 mb-1">Confidence: {signal.globalConfidence}%</div>
                <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-cyan-400 to-purple-500"
                    style={{ width: `${signal.globalConfidence}%` }}
                  ></div>
                </div>
              </div>

              <div className="text-xs text-slate-500">RR Ratio: 2.6:1 | 2 mins ago</div>
            </div>
          ))}

          {/* Execution Controls */}
          <div className="glass-card p-4">
            <h4 className="text-xs font-bold text-slate-400 mb-3">EXECUTION CONTROLS</h4>
            
            <div className="grid grid-cols-2 gap-3 mb-4">
              <button className="execution-button buy">BUY MKT</button>
              <button className="execution-button sell">SELL MKT</button>
            </div>

            <div className="mb-3">
              <div className="text-xs text-slate-500 mb-2">Quick Size</div>
              <div className="grid grid-cols-3 gap-2">
                {['100', '500', '1000'].map(size => (
                  <button
                    key={size}
                    className="px-3 py-2 bg-slate-800 border border-slate-700 rounded text-xs hover:border-cyan-400 transition-all"
                  >
                    {size}
                  </button>
                ))}
              </div>
            </div>

            <div className="text-xs">
              <div className="flex justify-between mb-1">
                <span className="text-slate-500">Portfolio Risk:</span>
                <span className="text-cyan-400 font-bold">2.5%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Max Loss:</span>
                <span className="text-red-400 font-bold">$1,230</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ZONE 4: LIVE SIGNAL FEED - Bottom Panel */}
      <div className="live-feed">
        <div className="live-feed-header">
          <div className="flex items-center justify-between">
            <h3>LIVE SIGNAL FEED</h3>
            <div className="flex gap-4 text-xs">
              <button className="text-cyan-400 hover:text-cyan-300">Pause</button>
              <button className="text-cyan-400 hover:text-cyan-300">Export</button>
            </div>
          </div>
        </div>

        {/* Table Header */}
        <div className="live-feed-row font-mono text-xs text-slate-400 bg-slate-900">
          <div className="w-20">TIME</div>
          <div className="w-24">TICKER</div>
          <div className="w-20">TIER</div>
          <div className="w-20">SCORE</div>
          <div className="w-24">AI CONF</div>
          <div className="w-20">RVOL</div>
          <div className="flex-1">CATALYST</div>
        </div>

        {/* Table Rows */}
        {signals.map(signal => (
          <div 
            key={signal.id} 
            className="live-feed-row font-mono text-sm"
            onClick={() => setSelectedTicker(signal.ticker)}
          >
            <div className="w-20 text-slate-400">{new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</div>
            <div className="w-24 font-bold cyan-glow-text">{signal.ticker}</div>
            <div className="w-20">
              <span className={`tier-badge ${signal.tier === 'Core' ? 'tier-core' : signal.tier === 'Hot' ? 'tier-hot' : 'tier-liquid'}`}>
                {signal.tier || 'LIQ'}
              </span>
            </div>
            <div className="w-20 text-cyan-400">{signal.globalConfidence.toFixed(1)}</div>
            <div className="w-24 text-green-400">{signal.globalConfidence}%</div>
            <div className="w-20 text-yellow-400">{signal.rvol || '1.5'}x</div>
            <div className="flex-1 text-slate-400 truncate">Volume spike breakout pattern</div>
          </div>
        ))}
      </div>
    </div>
  );
}
