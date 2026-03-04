import { Shield, TrendingUp, TrendingDown, Activity, AlertTriangle } from 'lucide-react';
import clsx from 'clsx';

// Default regime data (replaces mockData.js import per Issue #8 cleanup)
const DEFAULT_REGIME = {
  regime: 'unknown', current: 'unknown',
  vixLevel: 0, vixRsi: 0, breadth: 0,
  spyChange: 0, qqqChange: 0,
  riskPerTrade: 0, maxPositions: 0
};

export default function MarketRegimeCard({ regime: regimeData = null }) {
  const regime = regimeData || DEFAULT_REGIME;

  const regimeConfig = {
    GREEN: {
      color: 'bg-success',
      textColor: 'text-success',
      borderColor: 'border-success',
      icon: TrendingUp,
      description: 'Bullish conditions, momentum favored',
      strategy: '70% momentum / 30% reversion',
      kellyScale: 1.0, maxPosition: '10%', minEdge: '3%',
    },
    YELLOW: {
      color: 'bg-warning',
      textColor: 'text-warning',
      borderColor: 'border-warning',
      icon: AlertTriangle,
      description: 'Mixed conditions, selective trading',
      strategy: '50% momentum / 50% reversion',
      kellyScale: 0.7, maxPosition: '7%', minEdge: '5%',
    },
    RED: {
      color: 'bg-danger',
      textColor: 'text-danger',
      borderColor: 'border-danger',
      icon: TrendingDown,
      description: 'Bearish/volatile, defensive mode',
      strategy: '30% momentum / 70% reversion',
      kellyScale: 0.3, maxPosition: '4%', minEdge: '8%',
    },
    RED_RECOVERY: {
      color: 'bg-warning',
      textColor: 'text-warning',
      borderColor: 'border-warning',
      icon: Activity,
      description: 'Recovery phase, volatility unwinding',
      strategy: '40% momentum / 60% reversion',
      kellyScale: 0.5, maxPosition: '5%', minEdge: '6%',
    },
    unknown: {
      color: 'bg-secondary',
      textColor: 'text-secondary',
      borderColor: 'border-secondary',
      icon: Shield,
      description: 'Awaiting regime data...',
      strategy: 'No active strategy',
      kellyScale: 0.5, maxPosition: '5%', minEdge: '5%',
    }
  };

  const config = regimeConfig[regime.regime] || regimeConfig.unknown;
  const Icon = config.icon;

  return (
    <div className={clsx(
      'bg-secondary/10 border rounded-xl overflow-hidden',
      config.borderColor
    )}>
      {/* Header with regime indicator */}
      <div className={clsx('px-4 py-3 flex items-center justify-between', config.color + '/10')}>
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-secondary" />
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
      <div className="px-4 py-3 border-b border-secondary/50">
        <p className="text-sm text-secondary">{config.description}</p>
        <p className="text-xs text-secondary mt-1">Strategy: {config.strategy}</p>
      </div>

      {/* Metrics */}
      <div className="p-4 space-y-3">
        {/* VIX */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-secondary">VIX Level</span>
          <div className="flex items-center gap-2">
            <span className={clsx(
              'font-bold',
              regime.vixLevel < 20 ? 'text-bullish' :
              regime.vixLevel < 30 ? 'text-warning' : 'text-danger'
            )}>
              {regime.vixLevel.toFixed(2)}
            </span>
            <span className="text-xs text-secondary">RSI: {regime.vixRsi}</span>
          </div>
        </div>

        {/* Breadth */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-secondary">Market Breadth</span>
          <span className={clsx(
            'font-bold',
            regime.breadth > 1 ? 'text-bullish' : 'text-danger'
          )}>
            {regime.breadth.toFixed(2)}
          </span>
        </div>

        {/* SPY/QQQ */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-secondary">SPY / QQQ</span>
          <div className="flex items-center gap-2">
            <span className={clsx(
              'text-sm',
              regime.spyChange >= 0 ? 'text-bullish' : 'text-danger'
            )}>
              {regime.spyChange >= 0 ? '+' : ''}{regime.spyChange.toFixed(2)}%
            </span>
            <span className="text-secondary">/</span>
            <span className={clsx(
              'text-sm',
              regime.qqqChange >= 0 ? 'text-bullish' : 'text-danger'
            )}>
              {regime.qqqChange >= 0 ? '+' : ''}{regime.qqqChange.toFixed(2)}%
            </span>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-secondary/50 pt-3">
          <h4 className="text-xs text-secondary mb-2">RISK PARAMETERS</h4>

          <div className="flex items-center justify-between">
            <span className="text-sm text-secondary">Risk Per Trade</span>
            <span className="font-bold text-white">{regime.riskPerTrade}%</span>
          </div>

          <div className="flex items-center justify-between mt-2">
            <span className="text-sm text-secondary">Max Positions</span>
            <span className="font-bold text-white">{regime.maxPositions}</span>
          </div>
        </div>

          {/* Kelly Criterion Parameters */}
          <div className="border-t border-secondary/50 pt-2 mt-2">
            <h4 className="text-xs text-emerald-400 mb-2 font-bold">KELLY SIZING</h4>
            <div className="flex items-center justify-between">
              <span className="text-sm text-secondary">Kelly Scale</span>
              <span className="font-bold text-emerald-400">{config.kellyScale}x</span>
            </div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-sm text-secondary">Max Position</span>
              <span className="font-bold text-white">{config.maxPosition}</span>
            </div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-sm text-secondary">Min Edge</span>
              <span className="font-bold text-white">{config.minEdge}</span>
            </div>
          </div>
      </div>

            {/* Risk Score & Drawdown Monitor */}
      <div className="border-t border-secondary/50 pt-2 mt-2">
        <h4 className="text-xs text-red-400 mb-2 font-bold">RISK MONITOR</h4>
        <div className="flex items-center justify-between">
          <span className="text-sm text-secondary">Risk Score</span>
          <span className={`font-bold ${(regime?.riskScore || 100) >= 60 ? 'text-emerald-400' : (regime?.riskScore || 100) >= 40 ? 'text-amber-400' : 'text-red-400'}`}>
            {regime?.riskScore || 'N/A'} {regime?.riskGrade ? `(${regime.riskGrade})` : ''}
          </span>
        </div>
        <div className="flex items-center justify-between mt-1">
          <span className="text-sm text-secondary">Daily P&L</span>
          <span className={`font-bold ${(regime?.dailyPnlPct || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {regime?.dailyPnlPct ? `${regime.dailyPnlPct.toFixed(2)}%` : 'N/A'}
          </span>
        </div>
        <div className="flex items-center justify-between mt-1">
          <span className="text-sm text-secondary">Trading Allowed</span>
          <span className={`font-bold ${regime?.tradingAllowed !== false ? 'text-emerald-400' : 'text-red-400'}`}>
            {regime?.tradingAllowed !== false ? 'YES' : 'PAUSED'}
          </span>
        </div>
      </div>
    </div>
  );
}
