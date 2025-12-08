'use client';

import { useState, useEffect } from 'react';
import { Search } from 'lucide-react';

interface CommandBarProps {
  selectedSymbol: string;
  wsConnected: boolean;
}

interface MarketIndex {
  symbol: string;
  price: number;
  change: number;
}

export default function CommandBar({ selectedSymbol, wsConnected }: CommandBarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [indices, setIndices] = useState<MarketIndex[]>([
    { symbol: 'S&P 500', price: 6050.00, change: 0.15 },
    { symbol: 'DJI', price: 47950, change: -0.01 },
    { symbol: 'NASDAQ', price: 21180, change: 0.32 },
  ]);
  const [mainSymbolData, setMainSymbolData] = useState({ price: 685.69, volume: '25.6M', change: 2.51 });

  return (
    <div className="command-bar">
      {/* Logo */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-cyan-400 to-blue-600 rounded-lg flex items-center justify-center">
          <span className="text-white font-bold text-xl">ET</span>
        </div>
        <h1 className="text-xl font-bold cyan-glow-text">ELITE TRADER</h1>
      </div>

      {/* Search Bar */}
      <div className="relative w-80">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          type="text"
          placeholder="Search tickers..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all"
        />
      </div>

      {/* Market Indices Ribbon */}
      <div className="flex items-center gap-4">
        {indices.map((index) => (
          <div key={index.symbol} className="glass-card px-4 py-2">
            <div className="text-xs text-slate-400 uppercase">{index.symbol}</div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-mono">{index.price.toLocaleString()}</span>
              <span className={`text-xs ${index.change >= 0 ? 'text-bull' : 'text-bear'}`}>
                {index.change >= 0 ? '+' : ''}{index.change}%
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Main Symbol Display */}
      <div className="glass-card cyan-glow px-6 py-3">
        <div className="flex items-center gap-4">
          <div>
            <div className="text-xs text-slate-400 uppercase">Main Symbol</div>
            <div className="ticker cyan-glow-text">{selectedSymbol}</div>
          </div>
          <div className="border-l border-slate-700 pl-4">
            <div className="text-2xl font-bold text-mono">${mainSymbolData.price}</div>
            <div className="text-xs text-bull">+{mainSymbolData.change}%</div>
          </div>
          <div className="text-xs text-slate-400">
            Vol: {mainSymbolData.volume}
          </div>
        </div>
      </div>

      {/* System Status */}
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-bull live-indicator' : 'bg-bear'}`}></div>
        <span className="text-xs text-slate-400">
          {wsConnected ? 'Active' : 'Offline'}
        </span>
        {wsConnected && (
          <span className="text-xs text-slate-500">12ms</span>
        )}
      </div>
    </div>
  );
}
