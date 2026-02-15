// SIGNALS PAGE - Embodier.ai Glass House Intelligence System
// Signal scanner with filters, composite scoring, and signal cards
import { useState } from 'react';
import {
  Zap, Filter, ArrowUpRight, ArrowDownRight, TrendingUp,
  Clock, Target, Brain, ChevronDown, Search
} from 'lucide-react';

const MOCK_SIGNALS = [
  { id: 1, ticker: 'AAPL', type: 'Bullish Breakout', direction: 'long', score: 92, mlConfidence: 88, price: 192.30, target: 198.50, stop: 188.00, timeframe: '1D', time: '2m ago', source: 'Pattern AI' },
  { id: 2, ticker: 'MSFT', type: 'Momentum Surge', direction: 'long', score: 87, mlConfidence: 82, price: 415.20, target: 428.00, stop: 408.00, timeframe: '4H', time: '8m ago', source: 'Market Scanner' },
  { id: 3, ticker: 'TSLA', type: 'Mean Reversion', direction: 'long', score: 74, mlConfidence: 71, price: 248.10, target: 260.00, stop: 240.00, timeframe: '1D', time: '15m ago', source: 'ML Engine' },
  { id: 4, ticker: 'AMD', type: 'Support Bounce', direction: 'long', score: 81, mlConfidence: 78, price: 168.50, target: 178.00, stop: 163.00, timeframe: '1H', time: '22m ago', source: 'Pattern AI' },
  { id: 5, ticker: 'NVDA', type: 'Bearish Divergence', direction: 'short', score: 68, mlConfidence: 64, price: 868.20, target: 840.00, stop: 885.00, timeframe: '1D', time: '35m ago', source: 'ML Engine' },
  { id: 6, ticker: 'META', type: 'Channel Breakout', direction: 'long', score: 85, mlConfidence: 80, price: 582.40, target: 600.00, stop: 570.00, timeframe: '4H', time: '42m ago', source: 'Market Scanner' },
  { id: 7, ticker: 'SPY', type: 'Bearish Engulfing', direction: 'short', score: 72, mlConfidence: 69, price: 502.10, target: 495.00, stop: 506.00, timeframe: '1D', time: '1h ago', source: 'Pattern AI' },
  { id: 8, ticker: 'GOOGL', type: 'Golden Cross', direction: 'long', score: 79, mlConfidence: 75, price: 175.80, target: 185.00, stop: 170.00, timeframe: '1D', time: '1h ago', source: 'ML Engine' },
];

function ScoreRing({ score, size = 48 }) {
  const r = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const color = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';
  return (
    <svg width={size} height={size} className="-rotate-90">
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#1e293b" strokeWidth={3} />
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={3}
        strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round" className="transition-all duration-700" />
      <text x={size/2} y={size/2} textAnchor="middle" dominantBaseline="central" className="rotate-90 origin-center"
        fill="white" fontSize="13" fontWeight="bold">{score}</text>
    </svg>
  );
}

export default function Signals() {
  const [filter, setFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('score');

  const filtered = MOCK_SIGNALS
    .filter(s => filter === 'all' || s.direction === filter)
    .filter(s => !searchQuery || s.ticker.toLowerCase().includes(searchQuery.toLowerCase()))
    .sort((a, b) => sortBy === 'score' ? b.score - a.score : 0);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Signals</h1>
          <p className="text-sm text-gray-400 mt-1">{filtered.length} active signals detected</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-sm text-emerald-400">Live Scanning</span>
        </div>
      </div>

      {/* Filters bar */}
      <div className="flex flex-wrap items-center gap-4 p-4 bg-slate-800/30 border border-white/10 rounded-2xl">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text" placeholder="Search ticker..."
            value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-800/60 border border-white/10 rounded-xl text-sm text-white placeholder-gray-500 outline-none focus:border-blue-500/50"
          />
        </div>
        <div className="flex gap-2">
          {['all', 'long', 'short'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                filter === f ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30' : 'text-gray-400 hover:text-white bg-slate-800/40 border border-white/10'
              }`}>
              {f === 'all' ? 'All' : f === 'long' ? 'Long' : 'Short'}
            </button>
          ))}
        </div>
        <select value={sortBy} onChange={e => setSortBy(e.target.value)}
          className="px-4 py-2 bg-slate-800/60 border border-white/10 rounded-xl text-sm text-white outline-none">
          <option value="score">Sort by Score</option>
          <option value="time">Sort by Time</option>
        </select>
      </div>

      {/* Signal cards grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {filtered.map(signal => (
          <div key={signal.id} className="bg-slate-800/30 border border-white/10 rounded-2xl p-5 hover:border-white/20 transition-all">
            <div className="flex items-start gap-4">
              {/* Score ring */}
              <ScoreRing score={signal.score} />

              {/* Signal details */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg font-bold text-white">{signal.ticker}</span>
                  <span className={`px-2 py-0.5 rounded-lg text-xs font-medium ${
                    signal.direction === 'long' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
                  }`}>
                    {signal.direction === 'long' ? 'LONG' : 'SHORT'}
                  </span>
                  <span className="text-xs text-gray-500">{signal.timeframe}</span>
                </div>
                <div className="text-sm text-gray-400 mb-2">{signal.type}</div>
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span className="flex items-center gap-1"><Target className="w-3 h-3" /> T: ${signal.target}</span>
                  <span className="flex items-center gap-1 text-red-400">S: ${signal.stop}</span>
                  <span className="flex items-center gap-1"><Brain className="w-3 h-3" /> ML: {signal.mlConfidence}%</span>
                  <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {signal.time}</span>
                </div>
              </div>

              {/* Action button */}
              <button className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-xl text-sm font-medium text-white transition-colors">
                Trade
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
