import { Brain, Cpu, BarChart2, Clock, CheckCircle2 } from 'lucide-react';
import { mockMLStats } from '../../data/mockData';
import { format } from 'date-fns';
import clsx from 'clsx';

export default function MLStatusCard() {
  const ml = mockMLStats;

  return (
    <div className="bg-secondary/10 border border-secondary/50 rounded-xl">
      {/* Header */}
      <div className="px-4 py-3 border-b border-secondary/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-primary" />
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
            <Cpu className="w-4 h-4 text-secondary" />
            <span className="text-sm text-secondary">Version</span>
          </div>
          <span className="font-mono text-sm">{ml.modelVersion}</span>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-secondary" />
            <span className="text-sm text-secondary">Last Trained</span>
          </div>
          <span className="text-sm text-secondary">
            {format(ml.lastTrained, 'MMM d, HH:mm')}
          </span>
        </div>

        {/* Performance metrics */}
        <div className="border-t border-secondary/50 pt-4">
          <h4 className="text-xs text-secondary mb-3">PERFORMANCE METRICS</h4>
          
          {/* Accuracy */}
          <div className="mb-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-secondary">Accuracy</span>
              <span className={clsx(
                'font-mono font-bold',
                ml.accuracy >= 65 ? 'text-bullish' :
                ml.accuracy >= 55 ? 'text-warning' : 'text-danger'
              )}>
                {ml.accuracy.toFixed(1)}%
              </span>
            </div>
            <div className="h-2 bg-dark-bg rounded-full overflow-hidden">
              <div
                className={clsx(
                  'h-full rounded-full transition-all',
                  ml.accuracy >= 65 ? 'bg-bullish' :
                  ml.accuracy >= 55 ? 'bg-warning' : 'bg-danger'
                )}
                style={{ width: `${ml.accuracy}%` }}
              />
            </div>
          </div>

          {/* AUC */}
          <div className="mb-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-secondary">AUC Score</span>
              <span className="font-mono font-bold">{ml.auc.toFixed(1)}%</span>
            </div>
            <div className="h-2 bg-dark-bg rounded-full overflow-hidden">
              <div
                className="h-full bg-primary rounded-full"
                style={{ width: `${ml.auc}%` }}
              />
            </div>
          </div>

          {/* Sharpe */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-secondary">Sharpe Ratio</span>
            <span className={clsx(
              'font-mono font-bold',
              ml.sharpeRatio >= 1.5 ? 'text-bullish' : 'text-secondary'
            )}>
              {ml.sharpeRatio.toFixed(2)}
            </span>
          </div>
        </div>

        {/* Top features */}
        <div className="border-t border-secondary/50 pt-4">
          <div className="flex items-center gap-2 mb-3">
            <BarChart2 className="w-4 h-4 text-secondary" />
            <h4 className="text-xs text-secondary">TOP FEATURES</h4>
          </div>
          
          <div className="space-y-2">
            {ml.topFeatures.slice(0, 5).map((feature, i) => (
              <div key={feature.name} className="flex items-center gap-2">
                <span className="text-xs text-secondary w-4">{i + 1}</span>
                <span className="text-xs text-secondary flex-1 truncate">
                  {feature.name.replace(/_/g, ' ')}
                </span>
                <div className="w-16 h-1.5 bg-dark-bg rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full"
                    style={{ width: `${feature.importance * 100}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-secondary w-8">
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
