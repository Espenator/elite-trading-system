import React, { useState, useEffect, useCallback } from 'react';
import { Shield, ShieldCheck, ShieldX, RefreshCw, AlertTriangle, CheckCircle, XCircle, Loader2 } from 'lucide-react';

interface RiskCheck {
  name: string;
  value: string;
  passed: boolean;
  threshold: string;
  category: 'position' | 'portfolio' | 'market' | 'model';
}

interface RiskValidationResponse {
  symbol: string;
  all_passed: boolean;
  checks: RiskCheck[];
  risk_score: number;
  timestamp: string;
  trading_allowed: boolean;
}

interface RiskShieldProps {
  symbol?: string;
  quantity?: number;
  onValidationComplete?: (result: RiskValidationResponse) => void;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

const API_URL = 'http://localhost:8000/api/v1/risk';

export function RiskShield({ symbol = 'NVDA', quantity = 100, onValidationComplete, autoRefresh = true, refreshInterval = 10000 }: RiskShieldProps) {
  const [validation, setValidation] = useState<RiskValidationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchValidation = useCallback(async (showRefreshIndicator = false) => {
    if (showRefreshIndicator) setIsRefreshing(true);
    else setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        API_URL + '/validate?symbol=' + encodeURIComponent(symbol) + '&quantity=' + quantity,
        {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
          signal: AbortSignal.timeout(5000)
        }
      );

      if (!response.ok) {
        throw new Error('HTTP ' + response.status + ': ' + response.statusText);
      }

      const data: RiskValidationResponse = await response.json();
      setValidation(data);
      setLastUpdated(new Date());
      
      if (onValidationComplete) {
        onValidationComplete(data);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to validate risk';
      setError(message);
      console.error('[RiskShield] Validation error:', err);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [symbol, quantity, onValidationComplete]);

  useEffect(() => {
    fetchValidation();
  }, [symbol, quantity]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => fetchValidation(true), refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchValidation]);

  const getCategoryIcon = (category: RiskCheck['category']) => {
    switch (category) {
      case 'position': return '📊';
      case 'portfolio': return '💼';
      case 'market': return '📈';
      case 'model': return '🤖';
      default: return '⚡';
    }
  };

  const formatLastUpdated = () => {
    if (!lastUpdated) return '';
    const seconds = Math.floor((Date.now() - lastUpdated.getTime()) / 1000);
    if (seconds < 5) return 'Just now';
    if (seconds < 60) return seconds + 's ago';
    return Math.floor(seconds / 60) + 'm ago';
  };

  if (isLoading && !validation) {
    return (
      <div className="bg-slate-900 rounded-lg border border-slate-700 p-4">
        <div className="flex items-center justify-center gap-3 py-8">
          <Loader2 size={24} className="text-cyan-400 animate-spin" />
          <span className="text-slate-400">Validating risk parameters...</span>
        </div>
      </div>
    );
  }

  if (error && !validation) {
    return (
      <div className="bg-slate-900 rounded-lg border border-red-700 p-4">
        <div className="flex items-center gap-3 mb-4">
          <ShieldX size={24} className="text-red-400" />
          <h3 className="font-bold text-red-400">Risk Validation Error</h3>
        </div>
        <p className="text-sm text-red-300 mb-4">{error}</p>
        <button onClick={() => fetchValidation()} className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-medium flex items-center gap-2">
          <RefreshCw size={16} />Retry
        </button>
      </div>
    );
  }

  const allPassed = validation?.all_passed ?? false;
  const riskScore = validation?.risk_score ?? 0;

  return (
    <div className={'bg-slate-900 rounded-lg border p-4 ' + (allPassed ? 'border-green-700' : 'border-red-700')}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {allPassed ? <ShieldCheck size={24} className="text-green-400" /> : <ShieldX size={24} className="text-red-400" />}
          <div>
            <h3 className={'font-bold text-lg ' + (allPassed ? 'text-green-400' : 'text-red-400')}>
              {allPassed ? 'RISK SHIELD: PASS' : 'RISK SHIELD: BLOCKED'}
            </h3>
            <p className="text-xs text-slate-400">
              {validation?.symbol} • Score: {riskScore.toFixed(0)}% • {formatLastUpdated()}
            </p>
          </div>
        </div>
        <button onClick={() => fetchValidation(true)} disabled={isRefreshing} className="p-2 hover:bg-slate-700 rounded transition disabled:opacity-50">
          <RefreshCw size={18} className={'text-slate-400 ' + (isRefreshing ? 'animate-spin' : '')} />
        </button>
      </div>

      {error && (
        <div className="mb-4 p-2 bg-yellow-900/30 border border-yellow-700 rounded text-yellow-400 text-xs flex items-center gap-2">
          <AlertTriangle size={14} />
          <span>Using cached data. {error}</span>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        {validation?.checks.map((check, index) => (
          <div key={index} className={'p-3 rounded border transition ' + (check.passed ? 'bg-slate-800 border-slate-700' : 'bg-red-900/20 border-red-700')}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-slate-400 flex items-center gap-1">
                {getCategoryIcon(check.category)}{check.name}
              </span>
              {check.passed ? <CheckCircle size={14} className="text-green-400" /> : <XCircle size={14} className="text-red-400" />}
            </div>
            <div className={'font-mono font-bold ' + (check.passed ? 'text-green-400' : 'text-red-400')}>{check.value}</div>
            <div className="text-xs text-slate-500 mt-1">Limit: {check.threshold}</div>
          </div>
        ))}
      </div>

      {!allPassed && (
        <div className="mt-4 p-3 bg-red-900/20 border border-red-700 rounded">
          <div className="flex items-center gap-2 text-red-400 font-bold text-sm mb-1">
            <AlertTriangle size={16} />TRADING BLOCKED
          </div>
          <p className="text-xs text-red-300">One or more risk checks failed. Resolve issues before executing trades.</p>
        </div>
      )}

      {allPassed && validation?.trading_allowed && (
        <div className="mt-4 p-3 bg-green-900/20 border border-green-700 rounded">
          <div className="flex items-center gap-2 text-green-400 font-bold text-sm">
            <CheckCircle size={16} />READY TO TRADE
          </div>
          <p className="text-xs text-green-300 mt-1">All risk parameters validated. Execution authorized.</p>
        </div>
      )}
    </div>
  );
}
