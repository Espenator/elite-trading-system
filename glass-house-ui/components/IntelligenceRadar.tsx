'use client';

import { useEffect } from 'react';
import { useEliteStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';
import { wsManager } from '@/lib/websocket';
import SignalCard from './SignalCard';

export default function IntelligenceRadar() {
  const { signals, setSignals, addSignal, setSelectedTicker, tierFilter, minConfidence } = useEliteStore();

  // Fetch initial signals
  useEffect(() => {
    const fetchSignals = async () => {
      try {
        const data = await apiClient.getSignals(100);
        setSignals(data);
      } catch (error) {
        console.error('Failed to fetch signals:', error);
      }
    };

    fetchSignals();

    // Connect WebSocket for live updates
    wsManager.connect();

    // Listen for new signals
    const handleNewSignal = (signal: any) => {
      addSignal(signal);
    };

    wsManager.on('new_signal', handleNewSignal);

    return () => {
      wsManager.off('new_signal', handleNewSignal);
    };
  }, []);

  // Filter signals
  const filteredSignals = signals
    .filter(s => tierFilter === 'all' || s.tier === tierFilter)
    .filter(s => s.globalConfidence >= minConfidence)
    .slice(0, 25);

  return (
    <div className="intelligence-radar">
      <div className="mb-4">
        <h3 className="text-cyan-400 mb-2">TOP TRADE CANDIDATES</h3>
        <div className="text-xs text-slate-500">
          Updated {new Date().toLocaleTimeString()}
        </div>
      </div>

      {/* Filters */}
      <div className="mb-4 flex gap-2">
        <select 
          className="px-3 py-1 bg-slate-800 border border-slate-700 rounded text-xs text-white"
          value={tierFilter}
          onChange={(e) => useEliteStore.setState({ tierFilter: e.target.value as any })}
        >
          <option value="all">All Tiers</option>
          <option value="Core">Core</option>
          <option value="Hot">Hot</option>
          <option value="Liquid">Liquid</option>
        </select>
      </div>

      <div className="space-y-2 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 250px)' }}>
        {filteredSignals.map((signal, index) => (
          <SignalCard
            key={signal.id}
            signal={signal}
            rank={index + 1}
            onClick={() => setSelectedTicker(signal.ticker)}
          />
        ))}
      </div>
    </div>
  );
}
