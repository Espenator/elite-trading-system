import { Briefcase, Clock } from 'lucide-react';
import { mockPositions } from '../../data/mockData';
import clsx from 'clsx';

export default function ActivePositions() {
  const positions = mockPositions;
  const totalPnl = positions.reduce((sum, p) => sum + p.pnlDollars, 0);

  return (
    <div className="bg-secondary/10 border border-secondary/50 rounded-xl">
      {/* Header */}
      <div className="px-4 py-3 border-b border-secondary/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Briefcase className="w-4 h-4 text-primary" />
          <h3 className="font-semibold">Active Positions</h3>
          <span className="text-xs bg-dark-bg px-2 py-0.5 rounded-full text-secondary">
            {positions.length}
          </span>
        </div>
        <div className={clsx(
          'text-sm font-bold',
          totalPnl >= 0 ? 'text-bullish' : 'text-bearish'
        )}>
          ${totalPnl.toLocaleString()}
        </div>
      </div>

      {/* Positions list */}
      <div className="divide-y divide-secondary/50">
        {positions.map((pos) => (
          <div
            key={pos.id}
            className="px-4 py-3 table-row-hover"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="font-semibold">{pos.ticker}</span>
                <span className={clsx(
                  'text-xs px-1.5 py-0.5 rounded',
                  pos.direction === 'LONG'
                    ? 'bg-bullish/20 text-bullish'
                    : 'bg-bearish/20 text-bearish'
                )}>
                  {pos.direction}
                </span>
                <span className="text-xs text-secondary">{pos.shares} shares</span>
              </div>
              <div className={clsx(
                'font-bold',
                pos.pnlDollars >= 0 ? 'text-bullish' : 'text-bearish'
              )}>
                {pos.pnlDollars >= 0 ? '+' : ''}${pos.pnlDollars.toLocaleString()}
              </div>
            </div>

            {/* Price levels */}
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-4">
                <div>
                  <span className="text-secondary">Entry </span>
                  <span className="">${pos.entryPrice.toFixed(2)}</span>
                </div>
                <div>
                  <span className="text-secondary">Current </span>
                  <span className={clsx(
                    '',
                    pos.currentPrice >= pos.entryPrice ? 'text-bullish' : 'text-bearish'
                  )}>
                    ${pos.currentPrice.toFixed(2)}
                  </span>
                </div>
                <div>
                  <span className="text-secondary">Stop </span>
                  <span className="text-bearish">${pos.stopPrice.toFixed(2)}</span>
                </div>
              </div>
              <div className="flex items-center gap-1 text-secondary">
                <Clock className="w-3 h-3" />
                <span>{pos.holdingHours.toFixed(1)}h</span>
              </div>
            </div>

            {/* R-multiple bar */}
            <div className="mt-2">
              <div className="flex justify-between text-xs mb-1">
                <span className="text-secondary">R-Multiple</span>
                <span className={clsx(
                  '',
                  pos.rMultiple >= 0 ? 'text-bullish' : 'text-bearish'
                )}>
                  {pos.rMultiple >= 0 ? '+' : ''}{pos.rMultiple.toFixed(2)}R
                </span>
              </div>
              <div className="h-1.5 bg-dark-bg rounded-full overflow-hidden">
                <div
                  className={clsx(
                    'h-full rounded-full transition-all',
                    pos.rMultiple >= 0 ? 'bg-bullish' : 'bg-bearish'
                  )}
                  style={{ 
                    width: `${Math.min(Math.abs(pos.rMultiple) * 33, 100)}%`,
                    marginLeft: pos.rMultiple < 0 ? 'auto' : '0'
                  }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Empty state */}
      {positions.length === 0 && (
        <div className="p-8 text-center text-secondary">
          <Briefcase className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>No active positions</p>
        </div>
      )}
    </div>
  );
}
