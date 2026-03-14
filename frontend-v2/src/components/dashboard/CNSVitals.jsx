// CNS Vitals Panel — shows homeostasis mode, circuit breaker status,
// agent health summary, latest verdict, and position scale.
// Designed to sit at the top of the Dashboard page.

import React, { useState } from 'react';
import {
  Brain, Shield, ShieldAlert, Activity, TrendingUp, TrendingDown,
  Gauge, Heart, AlertTriangle, ChevronDown, ChevronUp, Zap,
} from 'lucide-react';
import { useCNS } from '../../hooks/useCNS';
import { useCircuitBreakerStatus, useCnsAgentsHealth } from '../../hooks/useApi';

const MODE_CONFIG = {
  AGGRESSIVE: { color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/40', label: 'AGGRESSIVE', scale: '1.5x', icon: TrendingUp },
  NORMAL: { color: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500/40', label: 'NORMAL', scale: '1.0x', icon: Activity },
  DEFENSIVE: { color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/40', label: 'DEFENSIVE', scale: '0.5x', icon: AlertTriangle },
  HALTED: { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/40', label: 'HALTED', scale: '0.0x', icon: ShieldAlert },
};

function CNSVitals() {
  const { mode, positionScale, latestVerdict, circuitBreakerFired } = useCNS();
  const cbStatus = useCircuitBreakerStatus(15000);
  const agentsHealth = useCnsAgentsHealth(15000);
  const [expanded, setExpanded] = useState(false);

  const modeConfig = MODE_CONFIG[mode] || MODE_CONFIG.NORMAL;
  const ModeIcon = modeConfig.icon;
  const agents = agentsHealth.data?.agents || {};
  const summary = agentsHealth.data?.summary || {};
  const checks = cbStatus.data?.checks || [];
  const thresholds = cbStatus.data?.thresholds || {};

  return (
    <div className={`rounded-md border ${modeConfig.border} ${modeConfig.bg} backdrop-blur-sm mb-4`}>
      {/* Compact bar */}
      <div
        className="flex items-center justify-between px-4 py-2.5 cursor-pointer hover:bg-white/5 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-4">
          {/* Mode */}
          <div className="flex items-center gap-2">
            <Brain className={`w-4 h-4 ${modeConfig.color}`} />
            <span className="text-[10px] text-secondary uppercase tracking-wider">CNS</span>
            <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded ${modeConfig.bg} border ${modeConfig.border}`}>
              <ModeIcon className={`w-3 h-3 ${modeConfig.color}`} />
              <span className={`text-[10px] font-bold tracking-wider ${modeConfig.color}`}>{modeConfig.label}</span>
            </div>
            <span className="text-[10px] text-secondary">{positionScale}x sizing</span>
          </div>

          {/* Circuit Breaker */}
          <div className="flex items-center gap-1.5">
            {circuitBreakerFired ? (
              <>
                <ShieldAlert className="w-3.5 h-3.5 text-red-400 animate-pulse" />
                <span className="text-[10px] text-red-400 font-bold">CB FIRED</span>
              </>
            ) : (
              <>
                <Shield className="w-3.5 h-3.5 text-green-400" />
                <span className="text-[10px] text-green-400">CB OK</span>
              </>
            )}
          </div>

          {/* Agent Health */}
          <div className="flex items-center gap-1.5">
            <Heart className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-[10px] text-white">
              {summary.total_agents || 0} agents
            </span>
            {summary.hibernated > 0 && (
              <span className="text-[10px] text-red-400">({summary.hibernated} hibernated)</span>
            )}
            {summary.on_probation > 0 && (
              <span className="text-[10px] text-amber-400">({summary.on_probation} probation)</span>
            )}
          </div>

          {/* Latest Verdict */}
          {latestVerdict && (
            <div className="flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-primary" />
              <span className="text-[10px] text-white font-medium">{latestVerdict.symbol}</span>
              <span className={`text-[10px] font-bold ${
                latestVerdict.final_direction === 'buy' ? 'text-green-400' :
                latestVerdict.final_direction === 'sell' ? 'text-red-400' : 'text-secondary'
              }`}>
                {(latestVerdict.final_direction || 'hold').toUpperCase()}
              </span>
              <span className="text-[10px] text-secondary">
                {((latestVerdict.final_confidence || 0) * 100).toFixed(0)}%
              </span>
              {latestVerdict.vetoed && (
                <span className="text-[10px] text-red-400 font-bold">VETOED</span>
              )}
            </div>
          )}
        </div>

        <button className="text-secondary hover:text-white">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="px-4 pb-3 grid grid-cols-3 gap-4 border-t border-white/10 pt-3">
          {/* Circuit Breaker Checks */}
          <div>
            <h4 className="text-[10px] text-secondary uppercase tracking-wider mb-2">Circuit Breaker Checks</h4>
            <div className="space-y-1.5">
              {checks.map((check) => (
                <div key={check.name} className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
                  <span className="text-[10px] text-white">{check.description}</span>
                </div>
              ))}
              {Object.entries(thresholds).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between">
                  <span className="text-[10px] text-secondary">{key.replace('cb_', '').replace(/_/g, ' ')}</span>
                  <span className="text-[10px] text-white font-mono">{typeof value === 'number' && value < 1 ? `${(value * 100).toFixed(0)}%` : value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Agent Weights */}
          <div>
            <h4 className="text-[10px] text-secondary uppercase tracking-wider mb-2">Agent Bayesian Weights</h4>
            <div className="space-y-1">
              {Object.entries(agents).slice(0, 8).map(([name, info]) => (
                <div key={name} className="flex items-center gap-2">
                  <div className={`w-1.5 h-1.5 rounded-full ${info.skip ? 'bg-red-400' : info.streak?.status === 'PROBATION' ? 'bg-amber-400' : 'bg-green-400'}`} />
                  <span className="text-[10px] text-white flex-1">{name}</span>
                  <div className="w-16 h-1.5 bg-secondary/20 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${info.skip ? 'bg-red-400' : 'bg-cyan-400'}`}
                      style={{ width: `${(info.effective_weight || 0) * 100}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-secondary font-mono w-8 text-right">
                    {((info.effective_weight || 0) * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Latest Verdict Details */}
          <div>
            <h4 className="text-[10px] text-secondary uppercase tracking-wider mb-2">Latest Council Verdict</h4>
            {latestVerdict ? (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-secondary">Symbol</span>
                  <span className="text-[10px] text-white font-bold">{latestVerdict.symbol}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-secondary">Direction</span>
                  <span className={`text-[10px] font-bold ${latestVerdict.final_direction === 'buy' ? 'text-green-400' : latestVerdict.final_direction === 'sell' ? 'text-red-400' : 'text-secondary'}`}>
                    {(latestVerdict.final_direction || 'hold').toUpperCase()}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-secondary">Confidence</span>
                  <span className="text-[10px] text-white font-mono">{((latestVerdict.final_confidence || 0) * 100).toFixed(1)}%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-secondary">Agents Voted</span>
                  <span className="text-[10px] text-white">{latestVerdict.votes?.length || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-secondary">Execution Ready</span>
                  <span className={`text-[10px] ${latestVerdict.execution_ready ? 'text-green-400' : 'text-red-400'}`}>
                    {latestVerdict.execution_ready ? 'YES' : 'NO'}
                  </span>
                </div>
                {latestVerdict.council_reasoning && (
                  <p className="text-[10px] text-secondary/80 mt-1 leading-relaxed">
                    {latestVerdict.council_reasoning}
                  </p>
                )}
              </div>
            ) : (
              <p className="text-[10px] text-secondary">No verdict yet</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default React.memo(CNSVitals);
