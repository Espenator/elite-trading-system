import { BarChart3, TrendingUp, TrendingDown, Award } from 'lucide-react';
import { mockPerformance, mockTrades } from '../../data/mockData';
import clsx from 'clsx';

export default function PerformanceCard() {
  const perf = mockPerformance;
  const recentTrades = mockTrades.slice(0, 5);

  return (
    <div className="bg-secondary/10 border border-secondary/50 rounded-xl">
      {/* Header */}
      <div className="px-4 py-3 border-b border-secondary/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-primary" />
          <h3 className="font-semibold">Performance Summary</h3>
        </div>
        <select className="bg-dark text-sm px-2 py-1 rounded border border-secondary/50">
          <option>This Month</option>
          <option>This Week</option>
          <option>All Time</option>
        </select>
      </div>

      {/* Stats grid */}
      <div className="p-4 grid grid-cols-4 gap-4 border-b border-secondary/50">
        <div className="text-center">
          <div className="text-2xl font-bold text-bullish">
            ${perf.monthPnl.toLocaleString()}
          </div>
          <div className="text-xs text-secondary">Month P&L</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold">
            {perf.winRate.toFixed(1)}%
          </div>
          <div className="text-xs text-secondary">Win Rate</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold">
            {perf.avgRMultiple.toFixed(2)}R
          </div>
          <div className="text-xs text-secondary">Avg R</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold">
            {perf.sharpeRatio.toFixed(2)}
          </div>
          <div className="text-xs text-secondary">Sharpe</div>
        </div>
      </div>

      {/* Recent trades */}
      <div className="p-4">
        <h4 className="text-sm font-medium text-secondary mb-3">Recent Trades</h4>
        <div className="space-y-2">
          {recentTrades.map((trade) => (
            <div
              key={trade.id}
              className="flex items-center justify-between py-2 px-3 bg-dark rounded-lg"
            >
              <div className="flex items-center gap-3">
                <div className={clsx(
                  'w-6 h-6 rounded flex items-center justify-center',
                  trade.isWinner ? 'bg-bullish/10' : 'bg-bearish/10'
                )}>
                  {trade.isWinner ? (
                    <TrendingUp className="w-3 h-3 text-bullish" />
                  ) : (
                    <TrendingDown className="w-3 h-3 text-bearish" />
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{trade.ticker}</span>
                    <span className="text-xs text-secondary">{trade.direction}</span>
                  </div>
                  <span className="text-xs text-secondary">{trade.exitReason.replace(/_/g, ' ')}</span>
                </div>
              </div>
              <div className="text-right">
                <div className={clsx(
                  'font-medium',
                  trade.pnlDollars >= 0 ? 'text-bullish' : 'text-bearish'
                )}>
                  {trade.pnlDollars >= 0 ? '+' : ''}${trade.pnlDollars.toLocaleString()}
                </div>
                <div className={clsx(
                  'text-xs',
                  trade.rMultiple >= 0 ? 'text-bullish' : 'text-bearish'
                )}>
                  {trade.rMultiple >= 0 ? '+' : ''}{trade.rMultiple.toFixed(1)}R
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Best/Worst */}
      <div className="px-4 pb-4 grid grid-cols-2 gap-4">
        <div className="bg-bullish/5 border border-bullish/20 rounded-lg p-3">
          <div className="flex items-center gap-2 text-xs text-secondary mb-1">
            <Award className="w-3 h-3 text-bullish" />
            Best Trade
          </div>
          <div className="text-lg font-bold text-bullish">
            +${perf.largestWin.toLocaleString()}
          </div>
        </div>
        <div className="bg-bearish/5 border border-bearish/20 rounded-lg p-3">
          <div className="flex items-center gap-2 text-xs text-secondary mb-1">
            <TrendingDown className="w-3 h-3 text-bearish" />
            Worst Trade
          </div>
          <div className="text-lg font-bold text-bearish">
            ${perf.largestLoss.toLocaleString()}
          </div>
        </div>
      </div>
    </div>
  );
}
