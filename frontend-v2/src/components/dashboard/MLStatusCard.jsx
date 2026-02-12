import { Brain, Cpu, BarChart2, Clock, CheckCircle2 } from 'lucide-react';
import { mockMLStats } from '../../data/mockData';
import { format } from 'date-fns';
import clsx from 'clsx';

export default function MLStatusCard() {
  const ml = mockMLStats;

  return (
    <div className="bg-dark-card border border-dark-border rounded-xl">
      {/* Header */}
      <div className="px-4 py-3 border-b border-dark-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-purple-400" />
          <h3 className="font-semibold">ML Model</h3>
        </div>
        {ml.isProduction && (
          <div className="flex items-center gap-1 text-xs text-bullish">
            <CheckCircle2 className="w-3 h-3" />
            <span>Production</span>
          </div>
        )}
      </div>

      {/* Model info */}
      <div className="p-4 space-y-4">
        {/* Version & Last trained */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-gray-500" />
            <span className="text-sm text-gray-400">Version</span>
          </div>
          <span className="font-mono text-sm">{ml.modelVersion}</span>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-gray-500" />
            <span className="text-sm text-gray-400">Last Trained</span>
          </div>
          <span className="text-sm text-gray-300">
            {format(ml.lastTrained, 'MMM d, HH:mm')}
          </span>
        </div>

        {/* Performance metrics */}
        <div className="border-t border-dark-border pt-4">
          <h4 className="text-xs text-gray-500 mb-3">PERFORMANCE METRICS</h4>
          
          {/* Accuracy */}
          <div className="mb-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-gray-400">Accuracy</span>
              <span className={clsx(
                'font-mono font-bold',
                ml.accuracy >= 65 ? 'text-bullish' :
                ml.accuracy >= 55 ? 'text-regime-yellow' : 'text-bearish'
              )}>
                {ml.accuracy.toFixed(1)}%
              </span>
            </div>
            <div className="h-2 bg-dark-bg rounded-full overflow-hidden">
              <div
                className={clsx(
                  'h-full rounded-full transition-all',
                  ml.accuracy >= 65 ? 'bg-bullish' :
                  ml.accuracy >= 55 ? 'bg-regime-yellow' : 'bg-bearish'
                )}
                style={{ width: `${ml.accuracy}%` }}
              />
            </div>
          </div>

          {/* AUC */}
          <div className="mb-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-gray-400">AUC Score</span>
              <span className="font-mono font-bold">{ml.auc.toFixed(1)}%</span>
            </div>
            <div className="h-2 bg-dark-bg rounded-full overflow-hidden">
              <div
                className="h-full bg-purple-500 rounded-full"
                style={{ width: `${ml.auc}%` }}
              />
            </div>
          </div>

          {/* Sharpe */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Sharpe Ratio</span>
            <span className={clsx(
              'font-mono font-bold',
              ml.sharpeRatio >= 1.5 ? 'text-bullish' : 'text-gray-300'
            )}>
              {ml.sharpeRatio.toFixed(2)}
            </span>
          </div>
        </div>

        {/* Top features */}
        <div className="border-t border-dark-border pt-4">
          <div className="flex items-center gap-2 mb-3">
            <BarChart2 className="w-4 h-4 text-gray-500" />
            <h4 className="text-xs text-gray-500">TOP FEATURES</h4>
          </div>
          
          <div className="space-y-2">
            {ml.topFeatures.slice(0, 5).map((feature, i) => (
              <div key={feature.name} className="flex items-center gap-2">
                <span className="text-xs text-gray-500 w-4">{i + 1}</span>
                <span className="text-xs text-gray-400 flex-1 truncate">
                  {feature.name.replace(/_/g, ' ')}
                </span>
                <div className="w-16 h-1.5 bg-dark-bg rounded-full overflow-hidden">
                  <div
                    className="h-full bg-purple-500 rounded-full"
                    style={{ width: `${feature.importance * 100}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-gray-500 w-8">
                  {(feature.importance * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
