// Circuit Breaker Panel — real-time view of all 5 brainstem reflexes.
// Shows thresholds, current values, armed status, and last trigger event.

import { useState } from 'react';
import {
  Shield, ShieldAlert, ShieldCheck, Zap, TrendingDown,
  Clock, AlertTriangle, Activity, RefreshCw,
} from 'lucide-react';
import { useCircuitBreakerStatus, useHomeostasis } from '../../hooks/useApi';
import { useCNS } from '../../hooks/useCNS';

const CHECK_ICONS = {
  flash_crash_detector: TrendingDown,
  vix_spike_detector: Zap,
  daily_drawdown_limit: AlertTriangle,
  position_limit_check: Activity,
  market_hours_check: Clock,
};

const THRESHOLD_LABELS = {
  cb_vix_spike_threshold: 'VIX Spike Threshold',
  cb_daily_drawdown_limit: 'Daily Drawdown Limit',
  cb_flash_crash_threshold: 'Flash Crash Threshold',
  cb_max_positions: 'Max Positions',
  cb_max_single_position_pct: 'Max Single Position %',
};

export default function CircuitBreakerPanel() {
  const cbStatus = useCircuitBreakerStatus(10000);
  const homeostasis = useHomeostasis(10000);
  const { circuitBreakerFired } = useCNS();

  const data = cbStatus.data || {};
  const checks = data.checks || [];
  const thresholds = data.thresholds || {};
  const vitals = homeostasis.data?.vitals || {};

  return (
    <div className="space-y-4">
      {/* Status Banner */}
      <div className={`rounded-xl border p-4 ${
        circuitBreakerFired
          ? 'border-red-500/50 bg-red-500/10'
          : 'border-green-500/30 bg-green-500/10'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {circuitBreakerFired ? (
              <ShieldAlert className="w-8 h-8 text-red-400 animate-pulse" />
            ) : (
              <ShieldCheck className="w-8 h-8 text-green-400" />
            )}
            <div>
              <h3 className="text-lg font-bold text-white">
                {circuitBreakerFired ? 'CIRCUIT BREAKER TRIGGERED' : 'ALL SYSTEMS NOMINAL'}
              </h3>
              <p className="text-sm text-secondary">
                {circuitBreakerFired
                  ? `Reason: ${circuitBreakerFired}`
                  : `${checks.length} checks armed and passing`
                }
              </p>
            </div>
          </div>
          <button
            onClick={() => cbStatus.refetch()}
            className="p-2 rounded-lg bg-secondary/10 hover:bg-secondary/20 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 text-secondary ${cbStatus.loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Checks Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {checks.map((check) => {
          const Icon = CHECK_ICONS[check.name] || Shield;
          return (
            <div
              key={check.name}
              className="rounded-xl border border-secondary/30 bg-surface p-4 hover:border-primary/30 transition-colors"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                  <Icon className="w-5 h-5 text-green-400" />
                </div>
                <div>
                  <h4 className="text-sm font-medium text-white">
                    {check.name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                  </h4>
                  <p className="text-xs text-secondary">{check.description}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-400" />
                <span className="text-xs text-green-400 font-medium">Passing</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Thresholds Table */}
      <div className="rounded-xl border border-secondary/30 bg-surface overflow-hidden">
        <div className="px-4 py-3 border-b border-secondary/30">
          <h3 className="text-sm font-semibold text-white">Thresholds</h3>
        </div>
        <div className="divide-y divide-secondary/10">
          {Object.entries(thresholds).map(([key, value]) => (
            <div key={key} className="flex items-center justify-between px-4 py-2.5 hover:bg-white/5">
              <span className="text-sm text-white">{THRESHOLD_LABELS[key] || key}</span>
              <span className="text-sm font-mono text-primary">
                {typeof value === 'number' && value < 1 ? `${(value * 100).toFixed(1)}%` : value}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Current Vitals */}
      <div className="rounded-xl border border-secondary/30 bg-surface overflow-hidden">
        <div className="px-4 py-3 border-b border-secondary/30">
          <h3 className="text-sm font-semibold text-white">Live Vitals</h3>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-secondary/10">
          <VitalCard label="Risk Score" value={vitals.risk_score ?? '--'} color={
            (vitals.risk_score || 0) > 80 ? 'text-green-400' :
            (vitals.risk_score || 0) > 50 ? 'text-cyan-400' :
            (vitals.risk_score || 0) > 30 ? 'text-amber-400' : 'text-red-400'
          } />
          <VitalCard label="Portfolio Heat" value={vitals.portfolio_heat != null ? `${(vitals.portfolio_heat * 100).toFixed(1)}%` : '--'} />
          <VitalCard label="Drawdown" value={vitals.drawdown_pct != null ? `${(vitals.drawdown_pct * 100).toFixed(2)}%` : '--'} color={vitals.drawdown_breached ? 'text-red-400' : 'text-white'} />
          <VitalCard label="Positions" value={vitals.positions_count ?? '--'} />
        </div>
      </div>
    </div>
  );
}

function VitalCard({ label, value, color = 'text-white' }) {
  return (
    <div className="bg-surface p-3">
      <div className="text-xs text-secondary mb-1">{label}</div>
      <div className={`text-lg font-bold font-mono ${color}`}>{value}</div>
    </div>
  );
}
