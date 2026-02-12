import { useState } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  Calendar,
  Download,
  Filter
} from 'lucide-react';
import { mockTrades, mockPerformance } from '../data/mockData';
import { format } from 'date-fns';
import clsx from 'clsx';

export default function Trades() {
  const [filter, setFilter] = useState('ALL');
  const trades = mockTrades.filter(t => {
    if (filter === 'WINNERS') return t.isWinner;
    if (filter === 'LOSERS') return !t.isWinner;
    return true;
  });
  const perf = mockPerformance;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Trade History</h1>
          <p className="text-gray-400 text-sm">All executed trades and outcomes</p>
        </div>
        <button className="flex items-center gap-2 bg-dark-card border border-dark-border px-4 py-2 rounded-lg hover:bg-dark-hover transition-colors">
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-5 gap-4">
        <div className="bg-dark-card border border-dark-border rounded-xl p-4">
          <div className="text-xs text-gray-500 mb-1">Total Trades</div>
          <div className="text-2xl font-bold font-mono">{perf.totalTrades}</div>
        </div>
        <div className="bg-dark-card border border-dark-border rounded-xl p-4">
          <div className="text-xs text-gray-500 mb-1">Winners</div>
          <div className="text-2xl font-bold font-mono text-bullish">{perf.winners}</div>
        </div>
        <div className="bg-dark-card border border-dark-border rounded-xl p-4">
          <div className="text-xs text-gray-500 mb-1">Losers</div>
          <div className="text-2xl font-bold font-mono text-bearish">{perf.losers}</div>
        </div>
        <div className="bg-dark-card border border-dark-border rounded-xl p-4">
          <div className="text-xs text-gray-500 mb-1">Win Rate</div>
          <div className="text-2xl font-bold font-mono">{perf.winRate.toFixed(1)}%</div>
        </div>
        <div className="bg-dark-card border border-dark-border rounded-xl p-4">
          <div className="text-xs text-gray-500 mb-1">Avg R-Multiple</div>
          <div className={clsx(
            'text-2xl font-bold font-mono',
            perf.avgRMultiple >= 1 ? 'text-bullish' : 'text-bearish'
          )}>
            {perf.avgRMultiple.toFixed(2)}R
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-500" />
          <div className="flex bg-dark-card border border-dark-border rounded-lg p-1">
            {['ALL', 'WINNERS', 'LOSERS'].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={clsx(
                  'px-3 py-1.5 text-sm rounded-md transition-colors',
                  filter === f
                    ? f === 'WINNERS' ? 'bg-bullish text-white' :
                      f === 'LOSERS' ? 'bg-bearish text-white' :
                      'bg-gray-600 text-white'
                    : 'text-gray-400 hover:text-white'
                )}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-gray-500" />
          <select className="bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-sm">
            <option>Last 7 days</option>
            <option>Last 30 days</option>
            <option>This month</option>
            <option>All time</option>
          </select>
        </div>
      </div>

      {/* Trades table */}
      <div className="bg-dark-card border border-dark-border rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-dark-bg text-left text-xs text-gray-500 uppercase">
              <th className="px-4 py-3">Symbol</th>
              <th className="px-4 py-3">Direction</th>
              <th className="px-4 py-3">Entry</th>
              <th className="px-4 py-3">Exit</th>
              <th className="px-4 py-3">Shares</th>
              <th className="px-4 py-3 text-right">P&L</th>
              <th className="px-4 py-3 text-right">R-Multiple</th>
              <th className="px-4 py-3">Exit Reason</th>
              <th className="px-4 py-3">ML Correct</th>
              <th className="px-4 py-3">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-border">
            {trades.map((trade) => (
              <tr key={trade.id} className="table-row-hover">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className={clsx(
                      'w-8 h-8 rounded-lg flex items-center justify-center',
                      trade.isWinner ? 'bg-bullish/10' : 'bg-bearish/10'
                    )}>
                      {trade.isWinner ? (
                        <TrendingUp className="w-4 h-4 text-bullish" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-bearish" />
                      )}
                    </div>
                    <span className="font-semibold">{trade.ticker}</span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className={clsx(
                    'text-xs px-2 py-1 rounded',
                    trade.direction === 'LONG' 
                      ? 'bg-bullish/20 text-bullish' 
                      : 'bg-bearish/20 text-bearish'
                  )}>
                    {trade.direction}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono text-sm">${trade.entryPrice.toFixed(2)}</td>
                <td className="px-4 py-3 font-mono text-sm">${trade.exitPrice.toFixed(2)}</td>
                <td className="px-4 py-3 font-mono text-sm">{trade.shares}</td>
                <td className={clsx(
                  'px-4 py-3 text-right font-mono font-bold',
                  trade.pnlDollars >= 0 ? 'text-bullish' : 'text-bearish'
                )}>
                  {trade.pnlDollars >= 0 ? '+' : ''}${trade.pnlDollars.toLocaleString()}
                </td>
                <td className={clsx(
                  'px-4 py-3 text-right font-mono',
                  trade.rMultiple >= 0 ? 'text-bullish' : 'text-bearish'
                )}>
                  {trade.rMultiple >= 0 ? '+' : ''}{trade.rMultiple.toFixed(1)}R
                </td>
                <td className="px-4 py-3">
                  <span className={clsx(
                    'text-xs px-2 py-1 rounded',
                    trade.exitReason === 'TARGET_HIT' ? 'bg-bullish/20 text-bullish' :
                    trade.exitReason === 'STOP_HIT' ? 'bg-bearish/20 text-bearish' :
                    'bg-gray-600/20 text-gray-400'
                  )}>
                    {trade.exitReason.replace(/_/g, ' ')}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {trade.mlWasCorrect ? (
                    <span className="text-bullish text-sm">✓ Yes</span>
                  ) : (
                    <span className="text-bearish text-sm">✗ No</span>
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-gray-400">
                  {format(trade.exitTime, 'MMM d, HH:mm')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
