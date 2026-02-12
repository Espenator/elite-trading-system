import { Shield, TrendingUp, TrendingDown, Activity, AlertTriangle } from 'lucide-react';
import { mockRegime } from '../../data/mockData';
import clsx from 'clsx';

export default function MarketRegimeCard() {
  const regime = mockRegime;

  const regimeConfig = {
    GREEN: {
      color: 'bg-regime-green',
      textColor: 'text-regime-green',
      borderColor: 'border-regime-green',
      icon: TrendingUp,
      description: 'Bullish conditions, momentum favored',
      strategy: '70% momentum / 30% reversion'
    },
    YELLOW: {
      color: 'bg-regime-yellow',
      textColor: 'text-regime-yellow',
      borderColor: 'border-regime-yellow',
      icon: AlertTriangle,
      description: 'Mixed conditions, selective trading',
      strategy: '50% momentum / 50% reversion'
    },
    RED: {
      color: 'bg-regime-red',
      textColor: 'text-regime-red',
      borderColor: 'border-regime-red',
      icon: TrendingDown,
      description: 'Bearish/volatile, defensive mode',
      strategy: '30% momentum / 70% reversion'
    },
    RED_RECOVERY: {
      color: 'bg-orange-500',
      textColor: 'text-orange-500',
      borderColor: 'border-orange-500',
      icon: Activity,
      description: 'Recovery phase, volatility unwinding',
      strategy: '40% momentum / 60% reversion'
    }
  };

  const config = regimeConfig[regime.regime];
  const Icon = config.icon;

  return (
    <div className={clsx(
      'bg-dark-card border rounded-xl overflow-hidden',
      config.borderColor
    )}>
      {/* Header with regime indicator */}
      <div className={clsx('px-4 py-3 flex items-center justify-between', config.color + '/10')}>
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-gray-400" />
          <h3 className="font-semibold">Market Regime</h3>
        </div>
        <div className={clsx(
          'flex items-center gap-2 px-3 py-1 rounded-full',
          config.color + '/20'
        )}>
          <Icon className={clsx('w-4 h-4', config.textColor)} />
          <span className={clsx('font-bold', config.textColor)}>{regime.regime}</span>
        </div>
      </div>

      {/* Description */}
      <div className="px-4 py-3 border-b border-dark-border">
        <p className="text-sm text-gray-400">{config.description}</p>
        <p className="text-xs text-gray-500 mt-1">Strategy: {config.strategy}</p>
      </div>

      {/* Metrics */}
      <div className="p-4 space-y-3">
        {/* VIX */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">VIX Level</span>
          <div className="flex items-center gap-2">
            <span className={clsx(
              'font-mono font-bold',
              regime.vixLevel < 20 ? 'text-bullish' :
              regime.vixLevel < 30 ? 'text-regime-yellow' : 'text-bearish'
            )}>
              {regime.vixLevel.toFixed(2)}
            </span>
            <span className="text-xs text-gray-500">RSI: {regime.vixRsi}</span>
          </div>
        </div>

        {/* Breadth */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">Market Breadth</span>
          <span className={clsx(
            'font-mono font-bold',
            regime.breadth > 1 ? 'text-bullish' : 'text-bearish'
          )}>
            {regime.breadth.toFixed(2)}
          </span>
        </div>

        {/* SPY/QQQ */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">SPY / QQQ</span>
          <div className="flex items-center gap-2">
            <span className={clsx(
              'font-mono text-sm',
              regime.spyChange >= 0 ? 'text-bullish' : 'text-bearish'
            )}>
              {regime.spyChange >= 0 ? '+' : ''}{regime.spyChange.toFixed(2)}%
            </span>
            <span className="text-gray-500">/</span>
            <span className={clsx(
              'font-mono text-sm',
              regime.qqqChange >= 0 ? 'text-bullish' : 'text-bearish'
            )}>
              {regime.qqqChange >= 0 ? '+' : ''}{regime.qqqChange.toFixed(2)}%
            </span>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-dark-border pt-3">
          <h4 className="text-xs text-gray-500 mb-2">RISK PARAMETERS</h4>
          
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Risk Per Trade</span>
            <span className="font-mono font-bold text-white">{regime.riskPerTrade}%</span>
          </div>
          
          <div className="flex items-center justify-between mt-2">
            <span className="text-sm text-gray-400">Max Positions</span>
            <span className="font-mono font-bold text-white">{regime.maxPositions}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
