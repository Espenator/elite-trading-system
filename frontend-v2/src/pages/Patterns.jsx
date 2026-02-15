// SCREENER & PATTERN LIBRARY - Embodier.ai Glass House Intelligence
// Full transparency: stock screener with filters, pattern recognition,
// ML insights per symbol, real-time data from multiple sources
// Backend: GET /api/v1/screener, GET /api/v1/patterns
// Data Sources: Alpaca, FRED, SEC Edgar, Stockgeist, News API

import { useState, useCallback } from 'react';
import { getApiUrl } from '../config/api';

// ========== GLASS PANEL ==========
function GlassPanel({ title, icon, collapsed, onToggle, maxHeight = '500px', children, badge, headerActions, glowColor = 'cyan' }) {
  const glowMap = {
    cyan: 'border-cyan-500/30 shadow-cyan-500/10',
    emerald: 'border-emerald-500/30 shadow-emerald-500/10',
    purple: 'border-purple-500/30 shadow-purple-500/10',
    red: 'border-red-500/30 shadow-red-500/10',
    blue: 'border-blue-500/30 shadow-blue-500/10',
    yellow: 'border-yellow-500/30 shadow-yellow-500/10',
    amber: 'border-amber-500/30 shadow-amber-500/10'
  };
  return (
    <div className={`bg-gradient-to-br from-gray-900/90 to-gray-950/95 backdrop-blur-xl border ${glowMap[glowColor]} rounded-2xl overflow-hidden shadow-2xl`}>
      <div className="flex items-center justify-between px-5 py-3 bg-gradient-to-r from-gray-800/60 to-gray-900/60 cursor-pointer hover:from-gray-700/60 hover:to-gray-800/60 transition-all" onClick={onToggle}>
        <div className="flex items-center gap-3"><span className="text-lg">{icon}</span><h3 className="text-sm font-bold text-white tracking-wide">{title}</h3>{badge && <span className="px-2 py-0.5 text-xs rounded-full bg-cyan-900/60 text-cyan-300 border border-cyan-500/20">{badge}</span>}</div>
        <div className="flex items-center gap-2">{headerActions}<svg className={`w-4 h-4 text-gray-400 transition-transform duration-300 ${collapsed ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg></div>
      </div>
      {!collapsed && <div className="overflow-y-auto custom-scrollbar" style={{ maxHeight }}>{children}</div>}
    </div>
  );
}

export default function Patterns() {
  const [panels, setPanels] = useState({ screener: true, patterns: true, detail: true, filters: true });
  const togglePanel = useCallback((key) => setPanels(prev => ({ ...prev, [key]: !prev[key] })), []);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL');
  const [assetTypes, setAssetTypes] = useState({ stocks: true, options: false, futures: false, crypto: false });
  const [marketCaps, setMarketCaps] = useState({ small: false, mid: false, large: true });
  const [exchanges, setExchanges] = useState({ nasdaq: true, nyse: true, amex: false });
  const [priceMin, setPriceMin] = useState(0);
  const [priceMax, setPriceMax] = useState(2000);
  const [patternFilter, setPatternFilter] = useState('ALL');

  // OLEH: Replace with GET /api/v1/screener - real-time from Alpaca + enriched data
  const screenerResults = [
    { symbol: 'AAPL', name: 'Apple Inc.', price: 172.03, change: 1.56, marketCap: '2.7T', pe: 28.50, volume: '52.3M', sector: 'Technology', signal: 'Bullish' },
    { symbol: 'MSFT', name: 'Microsoft Corp.', price: 420.50, change: 0.98, marketCap: '3.1T', pe: 37.15, volume: '18.7M', sector: 'Technology', signal: 'Strong Buy' },
    { symbol: 'GOOG', name: 'Alphabet Inc.', price: 155.70, change: -0.25, marketCap: '1.9T', pe: 26.33, volume: '22.1M', sector: 'Technology', signal: 'Neutral' },
    { symbol: 'AMZN', name: 'Amazon.com Inc.', price: 180.12, change: 2.10, marketCap: '1.8T', pe: 52.88, volume: '41.5M', sector: 'Consumer', signal: 'Bullish' },
    { symbol: 'TSLA', name: 'Tesla Inc.', price: 175.99, change: -1.05, marketCap: '560B', pe: 47.22, volume: '89.2M', sector: 'Automotive', signal: 'Bearish' },
    { symbol: 'NVDA', name: 'NVIDIA Corp.', price: 882.30, change: 3.45, marketCap: '2.2T', pe: 65.10, volume: '35.8M', sector: 'Technology', signal: 'Strong Buy' },
    { symbol: 'META', name: 'Meta Platforms', price: 520.00, change: 1.82, marketCap: '1.3T', pe: 33.20, volume: '14.3M', sector: 'Technology', signal: 'Bullish' },
  ];

  // OLEH: Replace with GET /api/v1/patterns - from ML pattern recognition engine
  const patterns = [
    { id: 'p1', name: 'FRACTAL_MOMENTUM_BREAKOUT', type: 'Momentum', timeframe: '4H + Daily', occurrences: 47, winners: 39, winRate: 82.98, avgR: 1.9, avgHold: 2.5, conditions: { rsi: '10-35', volCluster: 'HIGH', fractalScore: '80-100' } },
    { id: 'p2', name: 'STAIRCASE_CONTINUATION', type: 'Trend', timeframe: 'Daily', occurrences: 63, winners: 45, winRate: 71.43, avgR: 1.5, avgHold: 4.2, conditions: { adx: '25-100', priceAboveSMA20: 'true', volumeTrend: 'INCREASING' } },
    { id: 'p3', name: 'OVERSOLD_BOUNCE', type: 'Mean Reversion', timeframe: '4H', occurrences: 35, winners: 24, winRate: 68.57, avgR: 1.3, avgHold: 1.8, conditions: { rsi: '0-30', bbPosition: '0-0.2', volumeSpike: 'true' } },
    { id: 'p4', name: 'EXPLOSIVE_GROWTH', type: 'Momentum', timeframe: 'Daily + Weekly', occurrences: 22, winners: 17, winRate: 77.27, avgR: 2.1, avgHold: 6.5, conditions: { volumeRatio: '2-10', macdHistogram: 'POS_INC', adx: '30-100' } },
    { id: 'p5', name: 'REVERSAL_PATTERN', type: 'Reversal', timeframe: '4H', occurrences: 28, winners: 18, winRate: 64.29, avgR: 1.4, avgHold: 3.2, conditions: { rsi: '70-100', bbPosition: '0.8-1', divergence: 'true' } },
  ];

  const selected = screenerResults.find(s => s.symbol === selectedSymbol) || screenerResults[0];
  const filteredResults = screenerResults.filter(s => s.symbol.toLowerCase().includes(searchTerm.toLowerCase()) || s.name.toLowerCase().includes(searchTerm.toLowerCase()));
  const filteredPatterns = patternFilter === 'ALL' ? patterns : patterns.filter(p => p.type === patternFilter);

  return (
    <div className="space-y-4">
      {/* ===== PAGE HEADER ===== */}
      <div className="relative">
        <div className="absolute inset-0 bg-gradient-to-r from-purple-500/5 via-transparent to-cyan-500/5 rounded-2xl" />
        <div className="relative flex items-center justify-between p-4">
          <div>
            <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-cyan-400">Screener & Pattern Library</h1>
            <p className="text-gray-400 text-sm">AI-powered stock screening with learned pattern recognition</p>
          </div>
          <div className="flex gap-2 items-center">
            <div className="relative">
              <input type="text" placeholder="Search symbols or companies..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)} className="bg-gray-800/80 border border-gray-600/50 rounded-xl pl-8 pr-4 py-2 text-sm text-white w-64 focus:border-cyan-500 focus:outline-none" />
              <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            </div>
            <button className="px-3 py-2 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-xl transition-colors">Export Data</button>
            <button className="px-3 py-2 text-xs bg-gradient-to-r from-purple-600 to-cyan-600 hover:from-purple-500 hover:to-cyan-500 text-white rounded-xl transition-colors font-bold">Save Filter</button>
          </div>
        </div>
      </div>

      {/* ===== MAIN 3-COL LAYOUT: Filters | Results | Detail ===== */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">

        {/* LEFT: Filters Sidebar */}
        <div className="lg:col-span-3">
          <GlassPanel title="Filters" icon="\u{1F50D}" collapsed={!panels.filters} onToggle={() => togglePanel('filters')} maxHeight="600px" glowColor="purple">
            <div className="p-4 space-y-5">
              {/* Asset Type */}
              <div>
                <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider mb-2">Asset Type</h4>
                {Object.entries(assetTypes).map(([key, val]) => (
                  <label key={key} className="flex items-center gap-2 py-1 cursor-pointer">
                    <input type="checkbox" checked={val} onChange={() => setAssetTypes(p => ({...p, [key]: !p[key]}))} className="rounded bg-gray-700 border-gray-600 text-cyan-500 focus:ring-cyan-500" />
                    <span className="text-xs text-gray-300 capitalize">{key}</span>
                  </label>
                ))}
              </div>
              {/* Price Range */}
              <div>
                <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider mb-2">Price Range</h4>
                <div className="flex gap-2 items-center">
                  <input type="number" value={priceMin} onChange={e => setPriceMin(Number(e.target.value))} className="w-20 bg-gray-800/80 border border-gray-600/50 rounded-lg px-2 py-1 text-xs text-white font-mono" placeholder="$0" />
                  <span className="text-gray-500 text-xs">to</span>
                  <input type="number" value={priceMax} onChange={e => setPriceMax(Number(e.target.value))} className="w-20 bg-gray-800/80 border border-gray-600/50 rounded-lg px-2 py-1 text-xs text-white font-mono" placeholder="$2000+" />
                </div>
              </div>
              {/* Market Cap */}
              <div>
                <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider mb-2">Market Cap</h4>
                {Object.entries(marketCaps).map(([key, val]) => (
                  <label key={key} className="flex items-center gap-2 py-1 cursor-pointer">
                    <input type="checkbox" checked={val} onChange={() => setMarketCaps(p => ({...p, [key]: !p[key]}))} className="rounded bg-gray-700 border-gray-600 text-cyan-500 focus:ring-cyan-500" />
                    <span className="text-xs text-gray-300 capitalize">{key} Cap</span>
                  </label>
                ))}
              </div>
              {/* Exchange */}
              <div>
                <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider mb-2">Exchange</h4>
                {Object.entries(exchanges).map(([key, val]) => (
                  <label key={key} className="flex items-center gap-2 py-1 cursor-pointer">
                    <input type="checkbox" checked={val} onChange={() => setExchanges(p => ({...p, [key]: !p[key]}))} className="rounded bg-gray-700 border-gray-600 text-cyan-500 focus:ring-cyan-500" />
                    <span className="text-xs text-gray-300 uppercase">{key}</span>
                  </label>
                ))}
              </div>
              <button className="w-full py-2 text-xs bg-gradient-to-r from-purple-600/80 to-cyan-600/80 text-white rounded-xl font-bold">Apply Filters</button>
            </div>
          </GlassPanel>
        </div>

        {/* CENTER: Screener Results Table */}
        <div className="lg:col-span-5">
          <GlassPanel title="Screener Results" icon="\u{1F4CA}" collapsed={!panels.screener} onToggle={() => togglePanel('screener')} badge={`${filteredResults.length} results`} maxHeight="600px" glowColor="cyan">
            <div className="p-3">
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead><tr className="text-gray-400 border-b border-gray-700">
                    <th className="py-2 px-2 text-left">Symbol</th><th className="py-2 px-2 text-left">Name</th><th className="py-2 px-2">Price</th><th className="py-2 px-2">Change</th><th className="py-2 px-2">Mkt Cap</th><th className="py-2 px-2">P/E</th><th className="py-2 px-2">Signal</th>
                  </tr></thead>
                  <tbody>{filteredResults.map((s) => (
                    <tr key={s.symbol} className={`border-b border-gray-800/50 cursor-pointer transition-colors ${selectedSymbol === s.symbol ? 'bg-cyan-900/20 border-cyan-500/30' : 'hover:bg-gray-800/30'}`} onClick={() => setSelectedSymbol(s.symbol)}>
                      <td className="py-2.5 px-2 text-white font-bold">{s.symbol}</td>
                      <td className="py-2.5 px-2 text-gray-300 truncate max-w-[120px]">{s.name}</td>
                      <td className="py-2.5 px-2 text-white font-mono">${s.price.toFixed(2)}</td>
                      <td className={`py-2.5 px-2 font-mono ${s.change >= 0 ? 'text-emerald-300' : 'text-red-300'}`}>{s.change >= 0 ? '+' : ''}{s.change.toFixed(2)}%</td>
                      <td className="py-2.5 px-2 text-gray-300 font-mono">{s.marketCap}</td>
                      <td className="py-2.5 px-2 text-gray-300 font-mono">{s.pe.toFixed(1)}</td>
                      <td className="py-2.5 px-2"><span className={`px-1.5 py-0.5 rounded text-xs ${s.signal === 'Strong Buy' ? 'bg-emerald-900/60 text-emerald-300' : s.signal === 'Bullish' ? 'bg-emerald-900/40 text-emerald-400' : s.signal === 'Bearish' ? 'bg-red-900/50 text-red-300' : 'bg-gray-700/50 text-gray-400'}`}>{s.signal}</span></td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            </div>
          </GlassPanel>
        </div>

        {/* RIGHT: Stock Detail Panel */}
        <div className="lg:col-span-4">
          <GlassPanel title={`${selected.symbol} Detail`} icon="\u{1F4C4}" collapsed={!panels.detail} onToggle={() => togglePanel('detail')} maxHeight="600px" glowColor="blue">
            <div className="p-4 space-y-4">
              {/* Symbol Header */}
              <div>
                <h2 className="text-xl font-bold text-white">{selected.symbol}</h2>
                <p className="text-sm text-gray-400">{selected.name}</p>
              </div>
              {/* Mini Chart Placeholder */}
              <div className="bg-gray-800/40 rounded-xl p-4 border border-gray-700/30 h-32 flex items-center justify-center">
                <p className="text-gray-500 text-xs">Miniature Price Chart - OLEH: TradingView widget</p>
              </div>
              {/* Key Metrics */}
              <div>
                <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider mb-2">Key Metrics</h4>
                <div className="grid grid-cols-2 gap-2">
                  <div className="flex justify-between text-xs"><span className="text-gray-400">Price:</span><span className="text-white font-mono">${selected.price.toFixed(2)}</span></div>
                  <div className="flex justify-between text-xs"><span className="text-gray-400">Change:</span><span className={`font-mono ${selected.change >= 0 ? 'text-emerald-300' : 'text-red-300'}`}>{selected.change >= 0 ? '+' : ''}{selected.change.toFixed(2)}%</span></div>
                  <div className="flex justify-between text-xs"><span className="text-gray-400">Market Cap:</span><span className="text-white font-mono">{selected.marketCap}</span></div>
                  <div className="flex justify-between text-xs"><span className="text-gray-400">P/E Ratio:</span><span className="text-white font-mono">{selected.pe.toFixed(2)}</span></div>
                  <div className="flex justify-between text-xs"><span className="text-gray-400">Volume:</span><span className="text-white font-mono">{selected.volume}</span></div>
                  <div className="flex justify-between text-xs"><span className="text-gray-400">Sector:</span><span className="text-white">{selected.sector}</span></div>
                </div>
              </div>
              {/* ML Insights */}
              <div>
                <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider mb-2">ML Insights</h4>
                <div className="flex gap-2 mb-2">
                  <span className={`px-2 py-0.5 text-xs rounded-full ${selected.signal.includes('Buy') || selected.signal === 'Bullish' ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-500/20' : selected.signal === 'Bearish' ? 'bg-red-900/60 text-red-300 border border-red-500/20' : 'bg-gray-700 text-gray-300'}`}>{selected.signal === 'Bullish' ? 'Bullish Trend' : selected.signal}</span>
                </div>
                <p className="text-xs text-gray-400">AI detects institutional interest and positive sentiment, driving short-term momentum. OLEH: /api/v1/ml/insights</p>
              </div>
              {/* Recent News */}
              <div>
                <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider mb-2">Recent News</h4>
                <div className="space-y-2">
                  <p className="text-xs text-gray-400">Analysts upgrade rating on strong earnings. Source: News API</p>
                  <p className="text-xs text-gray-400">Partnership with AI firm expands market reach. Source: SEC Edgar</p>
                  <p className="text-xs text-gray-400">Social sentiment trending positive. Source: Stockgeist</p>
                </div>
              </div>
            </div>
          </GlassPanel>
        </div>
      </div>

      {/* ===== Pattern Library ===== */}
      <GlassPanel title="Learned Pattern Library" icon="\u{1F9EC}" collapsed={!panels.patterns} onToggle={() => togglePanel('patterns')} badge={`${patterns.length} patterns`} maxHeight="600px" glowColor="yellow"
        headerActions={
          <div className="flex gap-1 mr-2">
            {['ALL','Momentum','Trend','Mean Reversion','Reversal'].map(f => (
              <button key={f} onClick={(e) => { e.stopPropagation(); setPatternFilter(f); }} className={`px-2 py-0.5 text-xs rounded transition-colors ${patternFilter === f ? 'bg-yellow-600/80 text-white' : 'bg-gray-700/60 text-gray-400 hover:bg-gray-600/60'}`}>{f}</button>
            ))}
          </div>
        }>
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredPatterns.map(p => (
              <div key={p.id} className="bg-gradient-to-br from-gray-800/60 to-gray-900/80 border border-gray-700/40 rounded-xl p-4 hover:border-yellow-500/30 transition-all">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-sm font-bold text-white">{p.name.replace(/_/g, ' ')}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs bg-purple-500/20 text-purple-400 px-2 py-0.5 rounded">{p.type}</span>
                      <span className="text-xs text-gray-500">{p.timeframe}</span>
                    </div>
                  </div>
                  <div className={`text-xl font-bold font-mono ${p.winRate >= 75 ? 'text-emerald-300' : p.winRate >= 65 ? 'text-yellow-300' : 'text-gray-400'}`}>{p.winRate.toFixed(1)}%</div>
                </div>
                <div className="grid grid-cols-4 gap-2 text-center mb-3">
                  <div><div className="text-xs text-gray-500">Trades</div><div className="font-mono font-bold text-white text-sm">{p.occurrences}</div></div>
                  <div><div className="text-xs text-gray-500">Wins</div><div className="font-mono font-bold text-emerald-300 text-sm">{p.winners}</div></div>
                  <div><div className="text-xs text-gray-500">Avg R</div><div className="font-mono font-bold text-cyan-300 text-sm">{p.avgR.toFixed(1)}R</div></div>
                  <div><div className="text-xs text-gray-500">Hold</div><div className="font-mono font-bold text-white text-sm">{p.avgHold.toFixed(1)}h</div></div>
                </div>
                <div className="border-t border-gray-700/40 pt-3">
                  <div className="text-xs text-gray-500 mb-1">CONDITIONS</div>
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(p.conditions).map(([k, v]) => (
                      <span key={k} className="text-xs bg-gray-800/80 px-2 py-0.5 rounded text-gray-400">{k}: {v}</span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </GlassPanel>

    </div>
  );
}
