// Council Verdict Panel — shows the latest council decision with agent vote breakdown.
// Used in Trade Execution page for pre-trade council integration.

import { useState } from 'react';
import {
  Brain, TrendingUp, TrendingDown, Minus, ShieldCheck, ShieldAlert,
  RefreshCw, Play,
} from 'lucide-react';
import { useCnsLastVerdict, fetchCouncilEvaluate } from '../../hooks/useApi';
import { useCNS } from '../../hooks/useCNS';

const DIRECTION_STYLE = {
  buy: { icon: TrendingUp, color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/40' },
  sell: { icon: TrendingDown, color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/40' },
  hold: { icon: Minus, color: 'text-secondary', bg: 'bg-secondary/10', border: 'border-secondary/30' },
};

export default function CouncilVerdictPanel({ symbol = null }) {
  const { data, loading, refetch } = useCnsLastVerdict(10000);
  const { mode, positionScale } = useCNS();
  const [evaluating, setEvaluating] = useState(false);

  const verdict = data?.verdict;
  const homeostasisMode = data?.homeostasis_mode || mode;

  const handleEvaluate = async () => {
    if (!symbol) return;
    setEvaluating(true);
    try {
      await fetchCouncilEvaluate(symbol);
      await refetch();
    } catch (err) {
      console.error('Council evaluation failed:', err);
    } finally {
      setEvaluating(false);
    }
  };

  const dir = verdict?.final_direction || 'hold';
  const style = DIRECTION_STYLE[dir] || DIRECTION_STYLE.hold;
  const DirIcon = style.icon;

  return (
    <div className="rounded-xl border border-secondary/30 bg-surface overflow-hidden">
      <div className="px-4 py-3 border-b border-secondary/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-semibold text-white">Council Verdict</h3>
          {homeostasisMode !== 'NORMAL' && (
            <span className={`text-xs px-1.5 py-0.5 rounded ${
              homeostasisMode === 'HALTED' ? 'bg-red-500/20 text-red-400' :
              homeostasisMode === 'DEFENSIVE' ? 'bg-amber-500/20 text-amber-400' :
              'bg-green-500/20 text-green-400'
            }`}>
              {homeostasisMode}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {symbol && (
            <button
              onClick={handleEvaluate}
              disabled={evaluating}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-primary/20 text-primary text-xs font-medium hover:bg-primary/30 transition-colors"
            >
              {evaluating ? (
                <RefreshCw className="w-3 h-3 animate-spin" />
              ) : (
                <Play className="w-3 h-3" />
              )}
              {evaluating ? 'Evaluating...' : `Evaluate ${symbol}`}
            </button>
          )}
        </div>
      </div>

      {verdict ? (
        <div className="p-4">
          {/* Main verdict */}
          <div className={`flex items-center justify-between p-3 rounded-lg border ${style.border} ${style.bg} mb-4`}>
            <div className="flex items-center gap-3">
              <DirIcon className={`w-6 h-6 ${style.color}`} />
              <div>
                <div className="text-lg font-bold text-white">{verdict.symbol}</div>
                <div className={`text-sm font-bold ${style.color}`}>
                  {dir.toUpperCase()}
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold font-mono text-white">
                {((verdict.final_confidence || 0) * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-secondary">confidence</div>
            </div>
          </div>

          {/* Vetoed / Execution Ready */}
          <div className="flex items-center gap-3 mb-4">
            {verdict.vetoed ? (
              <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-red-500/20 border border-red-500/30">
                <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
                <span className="text-xs text-red-400 font-bold">VETOED</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-green-500/20 border border-green-500/30">
                <ShieldCheck className="w-3.5 h-3.5 text-green-400" />
                <span className="text-xs text-green-400">Not Vetoed</span>
              </div>
            )}
            <div className={`flex items-center gap-1.5 px-2 py-1 rounded ${
              verdict.execution_ready ? 'bg-green-500/20 border border-green-500/30' : 'bg-secondary/10 border border-secondary/30'
            }`}>
              <span className={`text-xs ${verdict.execution_ready ? 'text-green-400' : 'text-secondary'}`}>
                {verdict.execution_ready ? 'Execution Ready' : 'Not Ready'}
              </span>
            </div>
            <div className="text-xs text-secondary">
              Scale: <span className="text-white font-mono">{positionScale}x</span>
            </div>
          </div>

          {/* Agent Votes */}
          {verdict.votes && verdict.votes.length > 0 && (
            <div>
              <h4 className="text-xs text-secondary uppercase tracking-wider mb-2">Agent Votes ({verdict.votes.length})</h4>
              <div className="space-y-1">
                {verdict.votes.map((vote, i) => {
                  const vDir = vote.direction || 'hold';
                  const vStyle = DIRECTION_STYLE[vDir] || DIRECTION_STYLE.hold;
                  return (
                    <div key={i} className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-white/5">
                      <span className="text-sm text-white">{vote.agent_name}</span>
                      <div className="flex items-center gap-3">
                        <span className={`text-xs font-bold ${vStyle.color}`}>{vDir.toUpperCase()}</span>
                        <div className="w-16 h-1.5 bg-secondary/20 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${vDir === 'buy' ? 'bg-green-400' : vDir === 'sell' ? 'bg-red-400' : 'bg-secondary'}`}
                            style={{ width: `${(vote.confidence || 0) * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-secondary font-mono w-10 text-right">
                          {((vote.confidence || 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Reasoning */}
          {verdict.council_reasoning && (
            <div className="mt-3 pt-3 border-t border-secondary/20">
              <p className="text-xs text-secondary leading-relaxed">{verdict.council_reasoning}</p>
            </div>
          )}
        </div>
      ) : (
        <div className="p-8 text-center text-sm text-secondary">
          No council verdict yet. {symbol ? `Click "Evaluate ${symbol}" to run the council.` : 'Run a council evaluation first.'}
        </div>
      )}
    </div>
  );
}
