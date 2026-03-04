// Self-Awareness Panel — Bayesian weights, streak status, health monitoring.
// Used in Agent Command Center and Risk Intelligence pages.

import { useState } from 'react';
import {
  Brain, RefreshCw, AlertTriangle, Pause, Play, RotateCcw,
} from 'lucide-react';
import { useCnsAgentsHealth, postAgentOverrideStatus, postAgentOverrideWeight } from '../../hooks/useApi';

const STATUS_STYLES = {
  ACTIVE: { bg: 'bg-green-500/10', text: 'text-green-400', border: 'border-green-500/30' },
  PROBATION: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/30' },
  HIBERNATION: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30' },
};

export default function SelfAwarenessPanel() {
  const { data, loading, refetch } = useCnsAgentsHealth(15000);
  const [actionLoading, setActionLoading] = useState(null);

  const agents = data?.agents || {};
  const summary = data?.summary || {};

  const handleOverride = async (name, action) => {
    setActionLoading(`${name}-${action}`);
    try {
      await postAgentOverrideStatus(name, action);
      await refetch();
    } catch (err) {
      console.error('Override failed:', err);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="grid grid-cols-3 gap-3">
        <SummaryCard label="Total Agents" value={summary.total_agents || 0} color="text-cyan-400" />
        <SummaryCard label="Hibernated" value={summary.hibernated || 0} color={summary.hibernated > 0 ? 'text-red-400' : 'text-green-400'} />
        <SummaryCard label="On Probation" value={summary.on_probation || 0} color={summary.on_probation > 0 ? 'text-amber-400' : 'text-green-400'} />
      </div>

      {/* Agent Cards */}
      <div className="space-y-2">
        {Object.entries(agents).map(([name, info]) => {
          const streakStatus = info.streak?.status || 'ACTIVE';
          const style = STATUS_STYLES[streakStatus] || STATUS_STYLES.ACTIVE;
          const dist = info.distribution || {};

          return (
            <div key={name} className={`rounded-xl border ${style.border} ${style.bg} p-4`}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <Brain className={`w-5 h-5 ${style.text}`} />
                  <div>
                    <h4 className="text-sm font-medium text-white">{name}</h4>
                    <span className={`text-xs font-bold ${style.text}`}>{streakStatus}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {streakStatus === 'HIBERNATION' && (
                    <button
                      onClick={() => handleOverride(name, 'reset')}
                      disabled={actionLoading === `${name}-reset`}
                      className="flex items-center gap-1 px-2 py-1 rounded bg-green-500/20 text-green-400 text-xs hover:bg-green-500/30 transition-colors"
                    >
                      <RotateCcw className="w-3 h-3" />
                      Reset
                    </button>
                  )}
                  {streakStatus === 'ACTIVE' && (
                    <button
                      onClick={() => handleOverride(name, 'probation')}
                      disabled={actionLoading === `${name}-probation`}
                      className="flex items-center gap-1 px-2 py-1 rounded bg-amber-500/20 text-amber-400 text-xs hover:bg-amber-500/30 transition-colors"
                    >
                      <Pause className="w-3 h-3" />
                      Probation
                    </button>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-4 gap-3">
                {/* Bayesian Weight */}
                <div>
                  <div className="text-xs text-secondary mb-1">Bayesian Weight</div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-secondary/20 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-cyan-400 rounded-full transition-all"
                        style={{ width: `${(info.bayesian_weight || 0) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs font-mono text-white">{((info.bayesian_weight || 0) * 100).toFixed(0)}%</span>
                  </div>
                </div>

                {/* Effective Weight */}
                <div>
                  <div className="text-xs text-secondary mb-1">Effective Weight</div>
                  <div className="text-sm font-bold font-mono text-primary">
                    {((info.effective_weight || 0) * 100).toFixed(1)}%
                  </div>
                </div>

                {/* Distribution */}
                <div>
                  <div className="text-xs text-secondary mb-1">Beta Distribution</div>
                  <div className="text-xs text-white font-mono">
                    α={dist.alpha?.toFixed(1) || '2.0'} β={dist.beta?.toFixed(1) || '2.0'}
                  </div>
                  <div className="text-xs text-secondary">
                    {dist.samples?.toFixed(0) || 0} samples
                  </div>
                </div>

                {/* Streak */}
                <div>
                  <div className="text-xs text-secondary mb-1">Loss Streak</div>
                  <div className={`text-sm font-bold font-mono ${
                    (info.streak?.loss_streak || 0) >= 10 ? 'text-red-400' :
                    (info.streak?.loss_streak || 0) >= 5 ? 'text-amber-400' : 'text-green-400'
                  }`}>
                    {info.streak?.loss_streak || 0}
                  </div>
                  <div className="text-xs text-secondary">
                    max: {info.streak?.max_loss_streak || 0}
                  </div>
                </div>
              </div>

              {/* Health metrics */}
              {info.health && info.health.total_runs > 0 && (
                <div className="mt-2 pt-2 border-t border-white/10 flex gap-4">
                  <span className="text-xs text-secondary">
                    Runs: <span className="text-white">{info.health.total_runs}</span>
                  </span>
                  <span className="text-xs text-secondary">
                    Errors: <span className={info.health.errors > 0 ? 'text-red-400' : 'text-white'}>{info.health.errors}</span>
                  </span>
                  <span className="text-xs text-secondary">
                    Avg Latency: <span className="text-white">{info.health.avg_latency_ms?.toFixed(0) || 0}ms</span>
                  </span>
                </div>
              )}
            </div>
          );
        })}

        {Object.keys(agents).length === 0 && !loading && (
          <div className="text-center py-8 text-secondary">
            No agent data available yet. Run a council evaluation first.
          </div>
        )}
      </div>
    </div>
  );
}

function SummaryCard({ label, value, color = 'text-white' }) {
  return (
    <div className="rounded-xl border border-secondary/30 bg-surface p-3">
      <div className="text-xs text-secondary mb-1">{label}</div>
      <div className={`text-2xl font-bold font-mono ${color}`}>{value}</div>
    </div>
  );
}
