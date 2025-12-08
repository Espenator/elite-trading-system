'use client';

import { Signal } from '@/lib/api-client';

interface SignalCardProps {
  signal: Signal;
  rank: number;
  onClick: () => void;
}

export default function SignalCard({ signal, rank, onClick }: SignalCardProps) {
  const tierColors = {
    Core: 'bg-green-500',
    Hot: 'bg-yellow-400',
    Liquid: 'bg-blue-500',
  };

  const tierColor = signal.tier ? tierColors[signal.tier] : 'bg-blue-500';

  return (
    <div 
      className="candidate-card slide-in cursor-pointer"
      onClick={onClick}
    >
      {/* Header Row */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">#{rank}</span>
          <span className="ticker text-lg cyan-glow-text">{signal.ticker}</span>
        </div>
        <div className={`text-sm font-bold `}>
          {signal.percentChange >= 0 ? '+' : ''}{signal.percentChange.toFixed(2)}%
        </div>
      </div>

      {/* Tier Badge */}
      <div className="mb-2">
        <span className={`tier-badge `}>
          {signal.tier || 'LIQUID'}
        </span>
      </div>

      {/* Sparkline Placeholder */}
      <div className="h-7 mb-2 bg-slate-800/50 rounded"></div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 gap-2 text-xs font-mono">
        <div>
          <span className="text-slate-500">Score:</span>
          <span className="text-white ml-1">{signal.globalConfidence.toFixed(1)}</span>
        </div>
        <div>
          <span className="text-slate-500">Conf:</span>
          <span className="text-white ml-1">{signal.globalConfidence}%</span>
        </div>
        <div>
          <span className="text-slate-500">Vol:</span>
          <span className="text-white ml-1">{(signal.volume / 1000000).toFixed(1)}M</span>
        </div>
        <div>
          <span className="text-slate-500">RVOL:</span>
          <span className="text-white ml-1">{signal.rvol || '1.5'}x</span>
        </div>
      </div>
    </div>
  );
}
