// Postmortem Attribution — shows per-agent contribution stats from DuckDB postmortems.
// Used in Performance Analytics page (Task 6).

import { Brain, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { useCnsAttribution, useCnsPostmortems } from '../../hooks/useApi';

const DIRECTION_COLORS = {
  buy: 'text-green-400',
  sell: 'text-red-400',
  hold: 'text-secondary',
};

export default function PostmortemAttribution() {
  const attribution = useCnsAttribution(60000);
  const postmortems = useCnsPostmortems(30000);

  const agents = attribution.data?.attribution || {};
  const totalPMs = attribution.data?.total_postmortems || 0;
  const pmList = postmortems.data?.postmortems || [];

  return (
    <div className="space-y-4">
      {/* Agent Attribution Table */}
      <div className="rounded-xl border border-secondary/30 bg-surface overflow-hidden">
        <div className="px-4 py-3 border-b border-secondary/30 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-semibold text-white">Agent Attribution</h3>
          </div>
          <span className="text-xs text-secondary">{totalPMs} postmortems analyzed</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-secondary/20">
                <th className="text-left px-4 py-2 text-xs text-secondary font-medium">Agent</th>
                <th className="text-right px-4 py-2 text-xs text-secondary font-medium">Votes</th>
                <th className="text-right px-4 py-2 text-xs text-secondary font-medium">Avg Confidence</th>
                <th className="text-center px-4 py-2 text-xs text-secondary font-medium">Direction Split</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(agents)
                .sort((a, b) => b[1].total_votes - a[1].total_votes)
                .map(([name, stats]) => (
                  <tr key={name} className="border-b border-secondary/10 hover:bg-white/5">
                    <td className="px-4 py-2.5 text-white font-medium">{name}</td>
                    <td className="px-4 py-2.5 text-right text-white font-mono">{stats.total_votes}</td>
                    <td className="px-4 py-2.5 text-right">
                      <span className="text-primary font-mono">
                        {(stats.avg_confidence * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center justify-center gap-2">
                        {Object.entries(stats.directions || {}).map(([dir, count]) => (
                          <span key={dir} className={`text-xs px-1.5 py-0.5 rounded ${DIRECTION_COLORS[dir] || 'text-secondary'}`}>
                            {dir}: {count}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>

        {Object.keys(agents).length === 0 && (
          <div className="px-4 py-8 text-center text-sm text-secondary">
            No postmortem data available yet
          </div>
        )}
      </div>

      {/* Recent Postmortems */}
      <div className="rounded-xl border border-secondary/30 bg-surface overflow-hidden">
        <div className="px-4 py-3 border-b border-secondary/30">
          <h3 className="text-sm font-semibold text-white">Recent Postmortems</h3>
        </div>
        <div className="max-h-64 overflow-y-auto custom-scrollbar">
          {pmList.map((pm, i) => (
            <div key={pm.council_decision_id || i} className="px-4 py-3 border-b border-secondary/10 hover:bg-white/5">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-white">{pm.symbol || '—'}</span>
                <span className="text-xs text-secondary font-mono">
                  {pm.council_decision_id?.slice(0, 8) || '—'}
                </span>
              </div>
              {pm.critic_analysis && (
                <p className="text-xs text-secondary leading-relaxed line-clamp-2">
                  {typeof pm.critic_analysis === 'string'
                    ? pm.critic_analysis.slice(0, 200)
                    : JSON.stringify(pm.critic_analysis).slice(0, 200)}
                </p>
              )}
            </div>
          ))}
          {pmList.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-secondary">
              No postmortems recorded yet
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
