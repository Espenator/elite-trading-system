'use client';

import { useEliteStore } from '@/lib/store';

export default function LiveFeed() {
  const { signals, setSelectedTicker, isPaused, togglePause } = useEliteStore();

  return (
    <div className="live-feed">
      <div className="live-feed-header">
        <div className="flex items-center justify-between">
          <h3>LIVE SIGNAL FEED</h3>
          <div className="flex gap-4 text-xs">
            <button 
              className="text-cyan-400 hover:text-cyan-300 transition-colors"
              onClick={togglePause}
            >
              {isPaused ? 'Resume' : 'Pause'}
            </button>
            <button className="text-cyan-400 hover:text-cyan-300 transition-colors">
              Export
            </button>
          </div>
        </div>
      </div>

      {/* Table Header */}
      <div className="live-feed-row font-mono text-xs text-slate-400 bg-slate-900 sticky top-0">
        <div className="w-20">TIME</div>
        <div className="w-24">TICKER</div>
        <div className="w-20">TIER</div>
        <div className="w-20">SCORE</div>
        <div className="w-24">AI CONF</div>
        <div className="w-20">RVOL</div>
        <div className="flex-1">CATALYST</div>
      </div>

      {/* Table Rows */}
      <div className="overflow-y-auto" style={{ maxHeight: '280px' }}>
        {signals.slice(0, 100).map(signal => (
          <div 
            key={signal.id} 
            className="live-feed-row font-mono text-sm"
            onClick={() => setSelectedTicker(signal.ticker)}
          >
            <div className="w-20 text-slate-400">
              {new Date(signal.timestamp || Date.now()).toLocaleTimeString('en-US', { 
                hour: '2-digit', 
                minute: '2-digit' 
              })}
            </div>
            <div className="w-24 font-bold cyan-glow-text">{signal.ticker}</div>
            <div className="w-20">
              <span className={`tier-badge `}>
                {signal.tier?.substring(0, 3).toUpperCase() || 'LIQ'}
              </span>
            </div>
            <div className="w-20 text-cyan-400">{signal.globalConfidence.toFixed(1)}</div>
            <div className="w-24 text-green-400">{signal.globalConfidence}%</div>
            <div className="w-20 text-yellow-400">{signal.rvol || '1.5'}x</div>
            <div className="flex-1 text-slate-400 truncate">
              {signal.catalyst || 'Volume spike breakout pattern'}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
