'use client';

import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface Candidate {
  rank: number;
  ticker: string;
  price: number;
  change: number;
  tier: 'Core' | 'Hot' | 'Liquid';
  score: number;
  confidence: number;
  volume: string;
  rvol: number;
}

interface IntelligenceRadarProps {
  onSelectSymbol: (symbol: string) => void;
}

export default function IntelligenceRadar({ onSelectSymbol }: IntelligenceRadarProps) {
  const [candidates, setCandidates] = useState<Candidate[]>([
    { rank: 1, ticker: 'TGL', price: 276.44, change: 5.2, tier: 'Core', score: 92.3, confidence: 88, volume: '25.6M', rvol: 2.3 },
    { rank: 2, ticker: 'SMX', price: 135.45, change: 3.8, tier: 'Hot', score: 87.6, confidence: 91, volume: '21.2M', rvol: 1.8 },
    { rank: 3, ticker: 'AAPL', price: 195.43, change: 1.2, tier: 'Core', score: 83.1, confidence: 85, volume: '89.5M', rvol: 1.2 },
    { rank: 4, ticker: 'NVDA', price: 685.23, change: 2.5, tier: 'Hot', score: 81.4, confidence: 89, volume: '156.2M', rvol: 1.9 },
    { rank: 5, ticker: 'TSLA', price: 388.91, change: -0.8, tier: 'Liquid', score: 79.4, confidence: 82, volume: '122.3M', rvol: 2.1 },
  ]);

  return (
    <div className="intelligence-radar">
      <div className="p-4 border-b border-slate-700">
        <h3 className="text-sm font-bold uppercase text-slate-400">Top Trade Candidates</h3>
        <p className="text-xs text-slate-500 mt-1">Updated 2 mins ago</p>
      </div>

      <div className="overflow-y-auto h-full p-3 space-y-2">
        {candidates.map((candidate) => (
          <div
            key={candidate.ticker}
            onClick={() => onSelectSymbol(candidate.ticker)}
            className="candidate-card glass-card-hover cursor-pointer p-3 slide-in"
          >
            {/* Header Row */}
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500 font-semibold">#{candidate.rank}</span>
                <span className="ticker cyan-glow-text">{candidate.ticker}</span>
              </div>
              <div className="flex items-center gap-1">
                <span className={`text-sm font-bold ${candidate.change >= 0 ? 'text-bull' : 'text-bear'}`}>
                  {candidate.change >= 0 ? '+' : ''}{candidate.change}%
                </span>
                {candidate.change >= 0 ? (
                  <TrendingUp className="w-3 h-3 text-bull" />
                ) : (
                  <TrendingDown className="w-3 h-3 text-bear" />
                )}
              </div>
            </div>

            {/* Price & Tier Badge */}
            <div className="flex items-center justify-between mb-2">
              <span className="text-lg font-bold text-mono">${candidate.price}</span>
              <span className={`tier-badge ${candidate.tier.toLowerCase()}`}>
                {candidate.tier}
              </span>
            </div>

            {/* Sparkline Placeholder */}
            <div className="h-7 bg-slate-900/50 rounded mb-2 flex items-center justify-center">
              <span className="text-xs text-slate-600">📈 Sparkline</span>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-slate-500">Score:</span>
                <span className="ml-1 font-bold text-mono">{candidate.score}</span>
              </div>
              <div>
                <span className="text-slate-500">Conf:</span>
                <span className="ml-1 font-bold text-mono">{candidate.confidence}%</span>
              </div>
              <div>
                <span className="text-slate-500">Vol:</span>
                <span className="ml-1 text-mono">{candidate.volume}</span>
              </div>
              <div>
                <span className="text-slate-500">RVOL:</span>
                <span className="ml-1 font-bold text-mono">{candidate.rvol}x</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
