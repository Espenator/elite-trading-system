import { useState } from 'react';
import { 
  ArrowUpRight, 
  ArrowDownRight, 
  Filter, 
  Search,
  RefreshCw,
  Eye
} from 'lucide-react';
import { mockSignals } from '../data/mockData';
import clsx from 'clsx';

export default function Signals() {
  const [filter, setFilter] = useState('ALL');
  const [minScore, setMinScore] = useState(60);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredSignals = mockSignals
    .filter(s => filter === 'ALL' || s.direction === filter)
    .filter(s => s.compositeScore >= minScore)
    .filter(s => s.ticker.toLowerCase().includes(searchTerm.toLowerCase()));

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Signals</h1>
          <p className="text-gray-400 text-sm">All AI-generated trading signals</p>
        </div>
        <button className="flex items-center gap-2 bg-bullish/10 text-bullish px-4 py-2 rounded-lg hover:bg-bullish/20 transition-colors">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="bg-dark-card border border-dark-border rounded-xl p-4">
        <div className="flex items-center gap-4 flex-wrap">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search symbol..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-dark-bg border border-dark-border rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-bullish"
            />
          </div>

          {/* Direction filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500" />
            <div className="flex bg-dark-bg rounded-lg p-1">
              {['ALL', 'LONG', 'SHORT'].map((dir) => (
                <button
                  key={dir}
                  onClick={() => setFilter(dir)}
                  className={clsx(
                    'px-3 py-1.5 text-sm rounded-md transition-colors',
                    filter === dir
                      ? dir === 'LONG' ? 'bg-bullish text-white' :
                        dir === 'SHORT' ? 'bg-bearish text-white' :
                        'bg-gray-600 text-white'
                      : 'text-gray-400 hover:text-white'
                  )}
                >
                  {dir}
                </button>
              ))}
            </div>
          </div>

          {/* Min score */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">Min Score:</span>
            <input
              type="range"
              min="50"
              max="90"
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="w-24"
            />
            <span className="text-sm font-mono w-8">{minScore}</span>
          </div>
        </div>
      </div>

      {/* Signals table */}
      <div className="bg-dark-card border border-dark-border rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-dark-bg text-left text-xs text-gray-500 uppercase">
              <th className="px-4 py-3">Symbol</th>
              <th className="px-4 py-3">Direction</th>
              <th className="px-4 py-3">Setup Type</th>
              <th className="px-4 py-3 text-center">Composite</th>
              <th className="px-4 py-3 text-center">ML Conf</th>
              <th className="px-4 py-3 text-right">Entry</th>
              <th className="px-4 py-3 text-right">Stop</th>
              <th className="px-4 py-3 text-right">Target</th>
              <th className="px-4 py-3 text-center">R:R</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-border">
            {filteredSignals.map((signal) => (
              <tr key={signal.id} className="table-row-hover">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className={clsx(
                      'w-8 h-8 rounded-lg flex items-center justify-center',
                      signal.direction === 'LONG' ? 'bg-bullish/10' : 'bg-bearish/10'
                    )}>
                      {signal.direction === 'LONG' ? (
                        <ArrowUpRight className="w-4 h-4 text-bullish" />
                      ) : (
                        <ArrowDownRight className="w-4 h-4 text-bearish" />
                      )}
                    </div>
                    <div>
                      <span className="font-semibold">{signal.ticker}</span>
                      <p className="text-xs text-gray-500">{signal.sector}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className={clsx(
                    'text-xs px-2 py-1 rounded',
                    signal.direction === 'LONG' 
                      ? 'bg-bullish/20 text-bullish' 
                      : 'bg-bearish/20 text-bearish'
                  )}>
                    {signal.direction}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm text-gray-400">
                    {signal.setupType.replace(/_/g, ' ')}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={clsx(
                    'font-mono font-bold',
                    signal.compositeScore >= 80 ? 'text-bullish' :
                    signal.compositeScore >= 70 ? 'text-regime-yellow' : 'text-gray-400'
                  )}>
                    {signal.compositeScore}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={clsx(
                    'font-mono',
                    signal.mlConfidence >= 75 ? 'text-bullish' :
                    signal.mlConfidence >= 60 ? 'text-regime-yellow' : 'text-gray-400'
                  )}>
                    {signal.mlConfidence}%
                  </span>
                </td>
                <td className="px-4 py-3 text-right font-mono text-sm">${signal.entryPrice.toFixed(2)}</td>
                <td className="px-4 py-3 text-right font-mono text-sm text-bearish">${signal.stopPrice.toFixed(2)}</td>
                <td className="px-4 py-3 text-right font-mono text-sm text-bullish">${signal.target1.toFixed(2)}</td>
                <td className="px-4 py-3 text-center font-mono text-sm">{signal.riskReward.toFixed(1)}</td>
                <td className="px-4 py-3">
                  <button className="p-2 hover:bg-dark-hover rounded-lg transition-colors">
                    <Eye className="w-4 h-4 text-gray-500" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredSignals.length === 0 && (
          <div className="p-8 text-center text-gray-500">
            No signals match your filters
          </div>
        )}
      </div>
    </div>
  );
}
