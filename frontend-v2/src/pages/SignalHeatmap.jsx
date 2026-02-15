// SIGNAL HEATMAP - Embodier.ai Glass House Intelligence System
// PURPOSE: Visual heat grid of signal strength by sector/ticker - see where the EDGE is
// PROFIT FOCUS: Color-coded opportunity zones, strongest signals = highest profit potential
// BACKEND: /api/v1/signals/heatmap - aggregated signal strength across all sources

import { useState, useMemo } from 'react';
import {
  Map,
  Filter,
  TrendingUp,
  TrendingDown,
  Zap,
  Target,
  DollarSign,
  Clock
} from 'lucide-react';

// Sectors with profit-focused signal data
const SECTORS = [
  { id: 'tech', name: 'Technology', tickers: ['NVDA', 'AAPL', 'MSFT', 'GOOGL', 'META', 'AMD', 'TSLA', 'AMZN'] },
  { id: 'finance', name: 'Financials', tickers: ['JPM', 'BAC', 'GS', 'MS', 'WFC', 'C', 'BLK', 'AXP'] },
  { id: 'health', name: 'Healthcare', tickers: ['UNH', 'JNJ', 'PFE', 'ABBV', 'MRK', 'LLY', 'TMO', 'ABT'] },
  { id: 'energy', name: 'Energy', tickers: ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'OXY', 'MPC', 'PSX'] },
  { id: 'consumer', name: 'Consumer', tickers: ['WMT', 'COST', 'HD', 'NKE', 'MCD', 'SBUX', 'TGT', 'LOW'] },
];

// Generate mock signal data with profit metrics
const generateSignalData = () => {
  const data = {};
  SECTORS.forEach(sector => {
    sector.tickers.forEach(ticker => {
      const signalStrength = Math.random() * 2 - 1; // -1 to 1
      const confidence = 0.5 + Math.random() * 0.5;
      const expectedMove = (Math.random() * 8 - 2).toFixed(1);
      data[ticker] = {
        strength: signalStrength,
        confidence,
        expectedMove: parseFloat(expectedMove),
        volume: Math.floor(Math.random() * 50 + 10),
        signals: Math.floor(Math.random() * 5 + 1),
        sector: sector.id,
        edge: signalStrength > 0.5 ? 'STRONG BUY' : signalStrength > 0.2 ? 'BUY' : signalStrength < -0.5 ? 'STRONG SELL' : signalStrength < -0.2 ? 'SELL' : 'NEUTRAL'
      };
    });
  });
  return data;
};

export default function SignalHeatmap() {
  const [signalData] = useState(generateSignalData);
  const [selectedSector, setSelectedSector] = useState('all');
  const [sortBy, setSortBy] = useState('strength');

  const getHeatColor = (strength) => {
    if (strength > 0.7) return 'bg-emerald-500';
    if (strength > 0.4) return 'bg-emerald-600/70';
    if (strength > 0.2) return 'bg-emerald-700/50';
    if (strength > -0.2) return 'bg-gray-700/50';
    if (strength > -0.4) return 'bg-red-700/50';
    if (strength > -0.7) return 'bg-red-600/70';
    return 'bg-red-500';
  };

  const topOpportunities = useMemo(() => {
    return Object.entries(signalData)
      .sort((a, b) => Math.abs(b[1].strength) - Math.abs(a[1].strength))
      .slice(0, 5);
  }, [signalData]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Map className="w-7 h-7 text-cyan-400" />
            Signal Heatmap
          </h1>
          <p className="text-gray-400 text-sm mt-1">Visual signal strength grid - find the edge fast</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedSector}
            onChange={(e) => setSelectedSector(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300"
          >
            <option value="all">All Sectors</option>
            {SECTORS.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
      </div>

      {/* Top Opportunities - Where the money is */}
      <div className="bg-gradient-to-r from-cyan-500/10 to-emerald-500/10 rounded-xl p-4 border border-cyan-500/20">
        <h2 className="text-sm font-semibold text-cyan-400 mb-3 flex items-center gap-2">
          <Target className="w-4 h-4" />
          TOP OPPORTUNITIES NOW
        </h2>
        <div className="grid grid-cols-5 gap-3">
          {topOpportunities.map(([ticker, data]) => (
            <div
              key={ticker}
              className={`rounded-lg p-3 border ${
                data.strength > 0 ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-red-500/30 bg-red-500/5'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-white">{ticker}</span>
                <span className={`text-xs px-2 py-0.5 rounded ${
                  data.edge.includes('BUY') ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
                }`}>
                  {data.edge}
                </span>
              </div>
              <div className="text-lg font-bold text-white">
                {data.expectedMove > 0 ? '+' : ''}{data.expectedMove}%
              </div>
              <div className="text-xs text-gray-500">
                {data.signals} signals | {(data.confidence * 100).toFixed(0)}% conf
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Heatmap Grid */}
      <div className="bg-gray-800/30 rounded-xl border border-gray-700/50">
        <div className="p-4 border-b border-gray-700/50">
          <h2 className="text-lg font-semibold text-white">Signal Strength by Sector</h2>
        </div>
        <div className="p-4 space-y-6">
          {SECTORS.filter(s => selectedSector === 'all' || s.id === selectedSector).map(sector => (
            <div key={sector.id}>
              <div className="text-sm font-medium text-gray-400 mb-2">{sector.name}</div>
              <div className="grid grid-cols-8 gap-2">
                {sector.tickers.map(ticker => {
                  const data = signalData[ticker];
                  return (
                    <div
                      key={ticker}
                      className={`${getHeatColor(data.strength)} rounded-lg p-3 cursor-pointer hover:ring-2 hover:ring-cyan-400/50 transition-all group relative`}
                    >
                      <div className="text-xs font-bold text-white text-center">{ticker}</div>
                      <div className="text-[10px] text-white/70 text-center">
                        {data.expectedMove > 0 ? '+' : ''}{data.expectedMove}%
                      </div>
                      {/* Hover tooltip */}
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                        <div className="bg-gray-900 rounded-lg p-2 text-xs whitespace-nowrap border border-gray-700">
                          <div className="font-bold text-white">{ticker}</div>
                          <div className="text-gray-400">Signals: {data.signals}</div>
                          <div className="text-gray-400">Conf: {(data.confidence * 100).toFixed(0)}%</div>
                          <div className={data.strength > 0 ? 'text-emerald-400' : 'text-red-400'}>
                            {data.edge}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 text-xs">
        <span className="text-gray-500">STRONG SELL</span>
        <div className="flex gap-1">
          <div className="w-6 h-4 bg-red-500 rounded" />
          <div className="w-6 h-4 bg-red-600/70 rounded" />
          <div className="w-6 h-4 bg-red-700/50 rounded" />
          <div className="w-6 h-4 bg-gray-700/50 rounded" />
          <div className="w-6 h-4 bg-emerald-700/50 rounded" />
          <div className="w-6 h-4 bg-emerald-600/70 rounded" />
          <div className="w-6 h-4 bg-emerald-500 rounded" />
        </div>
        <span className="text-gray-500">STRONG BUY</span>
      </div>
    </div>
  );
}
