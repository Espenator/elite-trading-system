import { ArrowUpRight, ArrowDownRight, Zap } from 'lucide-react';
import { mockSignals } from '../../data/mockData';
import clsx from 'clsx';

export default function LiveSignalFeed() {
  const signals = mockSignals.slice(0, 8);

  return (
    <div className="bg-secondary/10 border border-secondary/50 rounded-xl">
      {/* Header */}
      <div className="px-4 py-3 border-b border-secondary/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-regime-yellow" />
          <h3 className="font-semibold">Live Signals</h3>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 bg-bullish rounded-full animate-pulse" />
          <span className="text-xs text-secondary">Live</span>
        </div>
      </div>

      {/* Signal list */}
      <div className="divide-y divide-secondary/50">
        {signals.map((signal) => (
          <div
            key={signal.id}
            className="px-4 py-3 table-row-hover flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              {/* Direction indicator */}
              <div className={clsx(
                'w-8 h-8 rounded-lg flex items-center justify-center',
                signal.direction === 'LONG' 
                  ? 'bg-bullish/10' 
                  : 'bg-bearish/10'
              )}>
                {signal.direction === 'LONG' ? (
                  <ArrowUpRight className="w-4 h-4 text-bullish" />
                ) : (
                  <ArrowDownRight className="w-4 h-4 text-bearish" />
                )}
              </div>

              {/* Symbol & setup */}
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{signal.ticker}</span>
                  <span className={clsx(
                    'text-xs px-1.5 py-0.5 rounded',
                    signal.direction === 'LONG'
                      ? 'bg-bullish/20 text-bullish'
                      : 'bg-bearish/20 text-bearish'
                  )}>
                    {signal.direction}
                  </span>
                </div>
                <span className="text-xs text-secondary">{signal.setupType.replace(/_/g, ' ')}</span>
              </div>
            </div>

            {/* Scores */}
            <div className="text-right">
              <div className="flex items-center gap-2">
                <span className="text-xs text-secondary">Score</span>
                <span className={clsx(
                  'font-bold',
                  signal.compositeScore >= 80 ? 'text-bullish' :
                  signal.compositeScore >= 70 ? 'text-regime-yellow' : 'text-secondary'
                )}>
                  {signal.compositeScore}
                </span>
              </div>
              <div className="text-xs text-secondary">
                ML: {signal.mlConfidence}%
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-secondary/50">
        <button className="text-xs text-bullish hover:text-bullish/80 transition-colors">
          View all signals →
        </button>
      </div>
    </div>
  );
}
