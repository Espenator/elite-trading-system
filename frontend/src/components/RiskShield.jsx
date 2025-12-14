import React, { useState, useEffect } from 'react';
import { Shield, CheckCircle, AlertTriangle, XCircle, Info } from 'lucide-react';

/**
 * Risk Shield - 6-Layer Risk Validation System
 * 
 * Displays real-time status of all risk layers:
 * 1. Trading State (ACTIVE/REDUCING/HALTED)
 * 2. Position Count (max 15)
 * 3. Position Size (≤20% cap)
 * 4. Daily Loss Limit (-5% circuit breaker)
 * 5. ML Confidence (≥70%)
 * 6. Signal Freshness (≤30 min)
 */

const StatusIcon = ({ status, size = 18 }) => {
  const icons = {
    pass: <CheckCircle className="text-green-400" size={size} />,
    warning: <AlertTriangle className="text-yellow-400" size={size} />,
    fail: <XCircle className="text-red-400" size={size} />
  };
  return icons[status] || <Info className="text-gray-400" size={size} />;
};

const RiskLayer = ({ layer, isLast }) => {
  return (
    <div className={`flex items-center gap-3 p-3 rounded bg-slate-800/30 hover:bg-slate-800/50 transition-colors ${
      !isLast ? 'mb-2' : ''
    }`}>
      <StatusIcon status={layer.status} />
      <div className="flex-1">
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm font-medium text-white">{layer.name}</span>
          <span className="text-xs text-gray-400">
            <span className={layer.status === 'pass' ? 'text-green-400' : layer.status === 'warning' ? 'text-yellow-400' : 'text-red-400'}>
              {layer.value}
            </span>
            {' / '}
            {layer.limit}
          </span>
        </div>
        <p className="text-xs text-gray-500">{layer.description}</p>
        
        {/* Progress Bar for numeric values */}
        {layer.showProgress && (
          <div className="mt-2 h-1.5 bg-slate-700 rounded overflow-hidden">
            <div 
              className={`h-full transition-all duration-300 ${
                layer.status === 'pass' ? 'bg-green-500' :
                layer.status === 'warning' ? 'bg-yellow-500' : 'bg-red-500'
              }`}
              style={{ width: `${layer.percentage}%` }}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default function RiskShield({ symbol = '' }) {
  const [layers, setLayers] = useState([]);
  const [canTrade, setCanTrade] = useState(false);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    const checkRisk = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/v1/risk/validate?symbol=${symbol}`);
        const data = await response.json();
        
        const riskLayers = [
          {
            name: 'Trading State',
            status: data.tradingState === 'ACTIVE' ? 'pass' : 'fail',
            value: data.tradingState || 'UNKNOWN',
            limit: 'ACTIVE',
            description: 'System must be in ACTIVE trading mode',
            showProgress: false
          },
          {
            name: 'Position Count',
            status: (data.positionCount || 0) <= 15 ? 'pass' : 'fail',
            value: `${data.positionCount || 0}`,
            limit: '≤ 15',
            description: 'Maximum 15 concurrent positions',
            showProgress: true,
            percentage: Math.min(100, ((data.positionCount || 0) / 15) * 100)
          },
          {
            name: 'Position Size',
            status: (data.positionSize || 0) <= 20 ? 'pass' : (data.positionSize || 0) <= 25 ? 'warning' : 'fail',
            value: `${(data.positionSize || 0).toFixed(1)}%`,
            limit: '≤ 20%',
            description: 'No single position > 20% of portfolio',
            showProgress: true,
            percentage: Math.min(100, ((data.positionSize || 0) / 20) * 100)
          },
          {
            name: 'Daily Loss Limit',
            status: (data.dailyPL || 0) >= -5 ? 'pass' : 'fail',
            value: `${(data.dailyPL || 0).toFixed(2)}%`,
            limit: '≥ -5%',
            description: 'Circuit breaker at -5% daily loss',
            showProgress: true,
            percentage: Math.min(100, ((Math.abs(data.dailyPL || 0)) / 5) * 100)
          },
          {
            name: 'ML Confidence',
            status: (data.mlConfidence || 0) >= 70 ? 'pass' : (data.mlConfidence || 0) >= 60 ? 'warning' : 'fail',
            value: `${data.mlConfidence || 0}%`,
            limit: '≥ 70%',
            description: 'AI model confidence threshold',
            showProgress: true,
            percentage: data.mlConfidence || 0
          },
          {
            name: 'Signal Freshness',
            status: (data.signalAge || 999) <= 30 ? 'pass' : (data.signalAge || 999) <= 45 ? 'warning' : 'fail',
            value: `${data.signalAge || 0} min`,
            limit: '≤ 30 min',
            description: 'Signal must be recent and actionable',
            showProgress: true,
            percentage: Math.min(100, ((data.signalAge || 0) / 30) * 100)
          }
        ];
        
        setLayers(riskLayers);
        setCanTrade(data.canTrade !== false); // Default to true if not specified
        setLastUpdate(new Date());
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch risk validation:', error);
        // Set default safe values on error
        setLayers([
          {
            name: 'Trading State',
            status: 'warning',
            value: 'UNKNOWN',
            limit: 'ACTIVE',
            description: 'Unable to verify trading state',
            showProgress: false
          }
        ]);
        setCanTrade(false);
        setLoading(false);
      }
    };
    
    checkRisk();
    const interval = setInterval(checkRisk, 5000); // Update every 5 seconds
    return () => clearInterval(interval);
  }, [symbol]);

  const failedLayers = layers.filter(l => l.status === 'fail');
  const warningLayers = layers.filter(l => l.status === 'warning');
  const passedLayers = layers.filter(l => l.status === 'pass');

  if (loading) {
    return (
      <div className="p-6 bg-slate-900/50 rounded-lg border border-slate-700/50">
        <div className="animate-pulse">
          <div className="h-6 bg-slate-700/50 rounded w-1/3 mb-4"></div>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5, 6].map(i => (
              <div key={i} className="h-16 bg-slate-700/30 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-slate-900/50 rounded-lg border border-slate-700/50">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Shield className={canTrade ? 'text-green-400' : 'text-red-400'} size={24} />
          <div>
            <h3 className="font-bold text-white text-lg">Risk Validation Shield</h3>
            {lastUpdate && (
              <p className="text-xs text-gray-500">Updated {new Date(lastUpdate).toLocaleTimeString()}</p>
            )}
          </div>
        </div>
        <div className={`px-3 py-1 rounded-full text-xs font-bold ${
          canTrade 
            ? 'bg-green-500/20 text-green-400 border border-green-500/50' 
            : 'bg-red-500/20 text-red-400 border border-red-500/50'
        }`}>
          {canTrade ? '✓ CLEARED' : '✗ BLOCKED'}
        </div>
      </div>

      {/* Status Summary */}
      <div className="grid grid-cols-3 gap-2 mb-4 p-3 bg-slate-800/30 rounded">
        <div className="text-center">
          <div className="text-2xl font-bold text-green-400">{passedLayers.length}</div>
          <div className="text-xs text-gray-400">Passed</div>
        </div>
        <div className="text-center border-l border-r border-slate-700/50">
          <div className="text-2xl font-bold text-yellow-400">{warningLayers.length}</div>
          <div className="text-xs text-gray-400">Warnings</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-red-400">{failedLayers.length}</div>
          <div className="text-xs text-gray-400">Failed</div>
        </div>
      </div>

      {/* Risk Layers */}
      <div className="space-y-2 mb-4">
        {layers.map((layer, idx) => (
          <RiskLayer key={idx} layer={layer} isLast={idx === layers.length - 1} />
        ))}
      </div>
      
      {/* Trading Status */}
      {!canTrade && failedLayers.length > 0 && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded">
          <div className="flex items-start gap-2">
            <XCircle className="text-red-400 flex-shrink-0 mt-0.5" size={20} />
            <div className="flex-1">
              <p className="text-red-400 text-sm font-bold mb-1">❌ Trading Blocked</p>
              <p className="text-xs text-gray-300">
                Fix {failedLayers.length} critical issue{failedLayers.length > 1 ? 's' : ''}: 
                <span className="font-semibold">
                  {' '}{failedLayers.map(l => l.name).join(', ')}
                </span>
              </p>
            </div>
          </div>
        </div>
      )}

      {canTrade && warningLayers.length > 0 && (
        <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded">
          <div className="flex items-start gap-2">
            <AlertTriangle className="text-yellow-400 flex-shrink-0 mt-0.5" size={20} />
            <div className="flex-1">
              <p className="text-yellow-400 text-sm font-bold mb-1">⚠️ Trade with Caution</p>
              <p className="text-xs text-gray-300">
                {warningLayers.length} warning{warningLayers.length > 1 ? 's' : ''}: 
                <span className="font-semibold">
                  {' '}{warningLayers.map(l => l.name).join(', ')}
                </span>
              </p>
            </div>
          </div>
        </div>
      )}

      {canTrade && failedLayers.length === 0 && warningLayers.length === 0 && (
        <div className="p-4 bg-green-500/10 border border-green-500/30 rounded">
          <div className="flex items-start gap-2">
            <CheckCircle className="text-green-400 flex-shrink-0 mt-0.5" size={20} />
            <div className="flex-1">
              <p className="text-green-400 text-sm font-bold mb-1">✓ All Systems GO</p>
              <p className="text-xs text-gray-300">
                All 6 risk layers passed validation. Ready to trade.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}