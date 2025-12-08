'use client';

import { useState } from 'react';
import { useEliteStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';

export default function ExecutionDeck() {
  const { signals, selectedTicker } = useEliteStore();
  const [selectedSize, setSelectedSize] = useState(100);

  const activeSignals = signals
    .filter(s => s.globalConfidence >= 70)
    .slice(0, 3);

  const handleTrade = async (side: 'buy' | 'sell') => {
    try {
      await apiClient.executeTrade(selectedTicker, side, selectedSize);
      alert(` order placed:  shares of `);
    } catch (error) {
      console.error('Trade execution failed:', error);
      alert('Trade execution failed');
    }
  };

  return (
    <div className="execution-deck">
      <div className="mb-4">
        <h3 className="text-cyan-400 mb-2">ACTIVE SIGNALS</h3>
      </div>

      <div className="space-y-4">
        {/* Active Signal Cards */}
        {activeSignals.map(signal => (
          <div key={signal.id} className="signal-card ignition">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-3 h-3 bg-green-400 rounded-full live-indicator"></div>
              <h4 className="text-xs font-bold text-slate-400">IGNITION SIGNAL</h4>
            </div>
            
            <div className="mb-3">
              <div className="text-2xl font-bold ticker cyan-glow-text">{signal.ticker}</div>
              <div className="text-sm text-slate-400">Entry: \</div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs mb-3">
              <div>
                <div className="text-slate-500">Target</div>
                <div className="text-green-400 font-bold">
                  \ (+11.7%)
                </div>
              </div>
              <div>
                <div className="text-slate-500">Stop</div>
                <div className="text-red-400 font-bold">
                  \ (-4.5%)
                </div>
              </div>
            </div>

            <div className="mb-3">
              <div className="text-xs text-slate-500 mb-1">
                Confidence: {signal.globalConfidence}%
              </div>
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-cyan-400 to-purple-500"
                  style={{ width: `%` }}
                ></div>
              </div>
            </div>

            <div className="text-xs text-slate-500">
              RR Ratio: 2.6:1 | {new Date().toLocaleTimeString()}
            </div>
          </div>
        ))}

        {/* Execution Controls */}
        <div className="glass-card p-4">
          <h4 className="text-xs font-bold text-slate-400 mb-3">EXECUTION CONTROLS</h4>
          
          <div className="grid grid-cols-2 gap-3 mb-4">
            <button 
              className="execution-button buy"
              onClick={() => handleTrade('buy')}
            >
              BUY MKT
            </button>
            <button 
              className="execution-button sell"
              onClick={() => handleTrade('sell')}
            >
              SELL MKT
            </button>
          </div>

          <div className="mb-3">
            <div className="text-xs text-slate-500 mb-2">Quick Size</div>
            <div className="grid grid-cols-3 gap-2">
              {[100, 500, 1000].map(size => (
                <button
                  key={size}
                  className={`px-3 py-2 rounded text-xs transition-all  border`}
                  onClick={() => setSelectedSize(size)}
                >
                  {size}
                </button>
              ))}
            </div>
          </div>

          <div className="text-xs">
            <div className="flex justify-between mb-1">
              <span className="text-slate-500">Portfolio Risk:</span>
              <span className="text-cyan-400 font-bold">2.5%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Max Loss:</span>
              <span className="text-red-400 font-bold">\</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
