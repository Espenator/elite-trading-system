import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, AlertTriangle, Activity } from 'lucide-react';

/**
 * Market Regime Badge - Shows current market regime and strategy allocation
 * Based on VIX and RSI levels
 */

export default function MarketRegimeBadge() {
  const [regime, setRegime] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRegime = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/market/regime');
        const data = await response.json();
        setRegime(data);
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch market regime:', error);
        // Set default regime
        setRegime({
          regime: 'GREEN',
          vix: 15,
          rsi: 55,
          allocation: { momentum: 70, reversion: 30 },
          riskMultiplier: 2.0,
          maxPositions: 6
        });
        setLoading(false);
      }
    };
    
    fetchRegime();
    const interval = setInterval(fetchRegime, 60000); // Update every minute
    return () => clearInterval(interval);
  }, []);

  if (loading || !regime) {
    return (
      <div className="px-3 py-1 bg-slate-700/30 rounded animate-pulse">
        <div className="h-5 w-24 bg-slate-600/30 rounded"></div>
      </div>
    );
  }

  const regimeConfig = {
    GREEN: {
      icon: <TrendingUp size={16} />,
      color: 'bg-green-500/20 text-green-400 border-green-500/50',
      label: '🟢 GREEN',
      description: `VIX <20: ${regime.allocation.momentum}% Momentum, ${regime.allocation.reversion}% Reversion, ${regime.riskMultiplier}% risk`
    },
    YELLOW: {
      icon: <Activity size={16} />,
      color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50',
      label: '🟡 YELLOW',
      description: `VIX 20-30: ${regime.allocation.momentum}% Momentum, ${regime.allocation.reversion}% Reversion, ${regime.riskMultiplier}% risk`
    },
    RED: {
      icon: <AlertTriangle size={16} />,
      color: 'bg-red-500/20 text-red-400 border-red-500/50',
      label: '🔴 RED',
      description: 'HALT - No Trading (VIX >30, RSI <40)'
    },
    RED_RECOVERY: {
      icon: <TrendingDown size={16} />,
      color: 'bg-orange-500/20 text-orange-400 border-orange-500/50',
      label: '🟠 RECOVERY',
      description: `VIX >30, RSI ≥40: 100% Reversion, ${regime.riskMultiplier}% risk`
    }
  };

  const config = regimeConfig[regime.regime] || regimeConfig.GREEN;

  return (
    <div className="group relative">
      <div className={`px-3 py-1 rounded border flex items-center gap-2 cursor-pointer ${config.color}`}>
        {config.icon}
        <span className="font-bold text-sm">{config.label}</span>
      </div>
      
      {/* Tooltip */}
      <div className="absolute top-full left-0 mt-2 w-64 p-3 bg-slate-800 border border-slate-700 rounded shadow-xl opacity-0 group-hover:opacity-100 transition-opacity z-50">
        <p className="text-xs text-white mb-2">{config.description}</p>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <span className="text-gray-400">VIX:</span>
            <span className="text-white ml-1">{regime.vix.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-gray-400">RSI:</span>
            <span className="text-white ml-1">{regime.rsi.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-gray-400">Max Positions:</span>
            <span className="text-white ml-1">{regime.maxPositions}</span>
          </div>
          <div>
            <span className="text-gray-400">Risk:</span>
            <span className="text-white ml-1">{regime.riskMultiplier}%</span>
          </div>
        </div>
      </div>
    </div>
  );
}