import { useState } from 'react';
import { 
  Layers, 
  Clock, 
  Search,
  Eye
} from 'lucide-react';
import clsx from 'clsx';

// Mock pattern data
const mockPatterns = [
  {
    id: 'p1',
    name: 'FRACTAL_MOMENTUM_BREAKOUT',
    type: 'Momentum',
    timeframe: '4H + Daily',
    occurrences: 47,
    winners: 39,
    winRate: 82.98,
    avgRMultiple: 1.9,
    avgHoldingHours: 2.5,
    lastSeen: new Date(Date.now() - 3600000),
    conditions: {
      rsi: [10, 35],
      volCluster: 'HIGH',
      fractalScore: [80, 100],
      priceStructure: 'HHHL'
    }
  },
  {
    id: 'p2',
    name: 'STAIRCASE_CONTINUATION',
    type: 'Trend',
    timeframe: 'Daily',
    occurrences: 63,
    winners: 45,
    winRate: 71.43,
    avgRMultiple: 1.5,
    avgHoldingHours: 4.2,
    lastSeen: new Date(Date.now() - 7200000),
    conditions: {
      adx: [25, 100],
      priceAboveSMA20: true,
      volumeTrend: 'INCREASING',
      priceStructure: 'HHHL'
    }
  },
  {
    id: 'p3',
    name: 'OVERSOLD_BOUNCE',
    type: 'Mean Reversion',
    timeframe: '4H',
    occurrences: 35,
    winners: 24,
    winRate: 68.57,
    avgRMultiple: 1.3,
    avgHoldingHours: 1.8,
    lastSeen: new Date(Date.now() - 86400000),
    conditions: {
      rsi: [0, 30],
      bbPosition: [0, 0.2],
      volumeSpike: true,
      priceStructure: 'ANY'
    }
  },
  {
    id: 'p4',
    name: 'EXPLOSIVE_GROWTH',
    type: 'Momentum',
    timeframe: 'Daily + Weekly',
    occurrences: 22,
    winners: 17,
    winRate: 77.27,
    avgRMultiple: 2.1,
    avgHoldingHours: 6.5,
    lastSeen: new Date(Date.now() - 172800000),
    conditions: {
      volumeRatio: [2, 10],
      macdHistogram: 'POSITIVE_INCREASING',
      adx: [30, 100],
      priceStructure: 'BREAKOUT'
    }
  },
  {
    id: 'p5',
    name: 'REVERSAL_PATTERN',
    type: 'Reversal',
    timeframe: '4H',
    occurrences: 28,
    winners: 18,
    winRate: 64.29,
    avgRMultiple: 1.4,
    avgHoldingHours: 3.2,
    lastSeen: new Date(Date.now() - 259200000),
    conditions: {
      rsi: [70, 100],
      bbPosition: [0.8, 1],
      divergence: true,
      priceStructure: 'LHLH'
    }
  }
];

export default function Patterns() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPattern, setSelectedPattern] = useState(null);

  const filteredPatterns = mockPatterns.filter(p =>
    p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.type.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Pattern Library</h1>
          <p className="text-gray-400 text-sm">Learned winning patterns from historical trades</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <Layers className="w-4 h-4" />
          <span>{mockPatterns.length} patterns</span>
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        <input
          type="text"
          placeholder="Search patterns..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full bg-dark-card border border-dark-border rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-bullish"
        />
      </div>

      {/* Patterns grid */}
      <div className="grid grid-cols-2 gap-4">
        {filteredPatterns.map((pattern) => (
          <div
            key={pattern.id}
            className={clsx(
              'bg-dark-card border rounded-xl p-4 cursor-pointer transition-all',
              selectedPattern === pattern.id
                ? 'border-bullish ring-1 ring-bullish/20'
                : 'border-dark-border hover:border-gray-600'
            )}
            onClick={() => setSelectedPattern(pattern.id)}
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="font-semibold">{pattern.name.replace(/_/g, ' ')}</h3>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs bg-purple-500/20 text-purple-400 px-2 py-0.5 rounded">
                    {pattern.type}
                  </span>
                  <span className="text-xs text-gray-500">{pattern.timeframe}</span>
                </div>
              </div>
              <div className={clsx(
                'text-2xl font-bold font-mono',
                pattern.winRate >= 75 ? 'text-bullish' :
                pattern.winRate >= 65 ? 'text-regime-yellow' : 'text-gray-400'
              )}>
                {pattern.winRate.toFixed(1)}%
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-4 gap-3 text-center">
              <div>
                <div className="text-xs text-gray-500">Occurrences</div>
                <div className="font-mono font-bold">{pattern.occurrences}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Winners</div>
                <div className="font-mono font-bold text-bullish">{pattern.winners}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Avg R</div>
                <div className="font-mono font-bold">{pattern.avgRMultiple.toFixed(1)}R</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Avg Hold</div>
                <div className="font-mono font-bold">{pattern.avgHoldingHours.toFixed(1)}h</div>
              </div>
            </div>

            {/* Conditions preview */}
            <div className="mt-4 pt-4 border-t border-dark-border">
              <div className="text-xs text-gray-500 mb-2">KEY CONDITIONS</div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(pattern.conditions).slice(0, 3).map(([key, value]) => (
                  <span 
                    key={key}
                    className="text-xs bg-dark-bg px-2 py-1 rounded text-gray-400"
                  >
                    {key}: {Array.isArray(value) ? value.join('-') : String(value)}
                  </span>
                ))}
              </div>
            </div>

            {/* Footer */}
            <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>Last seen: {pattern.lastSeen.toLocaleDateString()}</span>
              </div>
              <button className="flex items-center gap-1 text-bullish hover:text-bullish/80">
                <Eye className="w-3 h-3" />
                Details
              </button>
            </div>
          </div>
        ))}
      </div>

      {filteredPatterns.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <Layers className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>No patterns match your search</p>
        </div>
      )}
    </div>
  );
}
