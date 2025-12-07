'use client';

import { useEffect } from 'react';
import { useMarketStore } from '@/lib/store';

export default function GlassHouseDashboard() {
  const { wsConnected } = useMarketStore();

  useEffect(() => {
    fetch('http://localhost:8000/api/signals/?limit=100')
      .then(res => res.json())
      .then(data => {
        const signals = data.map((item: any) => ({
          id: item.id,
          ticker: item.ticker,
          tier: item.tier || 'LIQUID',
          currentPrice: item.currentPrice || 0,
          netChange: item.netChange || 0,
          percentChange: item.percentChange || 0,
          mathScore: item.globalConfidence || 50,
          aiScore: item.globalConfidence || 50,
          compositeScore: item.globalConfidence || 50,
          rvol: item.rvol || 1.0,
          globalConfidence: item.globalConfidence || 50,
          direction: item.direction || 'long',
          volume: item.volume || 0,
          marketCap: item.marketCap || 0,
          factors: item.factors || [],
          predictedPath: [],
          timestamp: item.timestamp || new Date().toISOString(),
        }));
        
        useMarketStore.getState().setSignals(signals);
      })
      .catch(err => console.error('Failed to fetch signals:', err));
  }, []);

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(135deg, #0a0e17 0%, #131720 50%, #0f1419 100%)' }}>
      <div style={{ 
        background: 'rgba(19, 23, 32, 0.7)',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.05)'
      }} className="px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <h1 className="font-data text-xl" style={{ color: '#06b6d4' }}>
            GLASS HOUSE COMMAND CENTER
          </h1>
          <div className="text-sm" style={{ color: '#94a3b8' }}>
            {new Date().toLocaleTimeString('en-US', { hour12: false })}
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full`} style={{ background: wsConnected ? '#10b981' : '#ef4444' }} />
            <span className="text-xs" style={{ color: '#94a3b8' }}>
              {wsConnected ? 'CONNECTED' : 'DISCONNECTED'}
            </span>
          </div>
        </div>
      </div>

      <div className="flex h-[calc(100vh-64px)]">
        <div className="w-80 p-4 overflow-y-auto" style={{ borderRight: '1px solid rgba(255, 255, 255, 0.05)' }}>
          <TierPanel tier="CORE" />
          <TierPanel tier="HOT" />
          <TierPanel tier="LIQUID" />
        </div>

        <div className="flex-1 p-6 overflow-y-auto">
          <SignalDetailCard />
        </div>

        <div className="w-96 p-4 overflow-y-auto" style={{ borderLeft: '1px solid rgba(255, 255, 255, 0.05)' }}>
          <SystemHealthPanel />
          <MLControlPanel />
        </div>
      </div>
    </div>
  );
}

function TierPanel({ tier }: { tier: 'CORE' | 'HOT' | 'LIQUID' }) {
  const { coreWatchlist, hotSignals, liquidSignals, signals, selectSignal, selectedSignalId } = useMarketStore();
  
  const tierColor = tier === 'CORE' ? '#fbbf24' : tier === 'HOT' ? '#06b6d4' : '#a855f7';
  
  const tierSignals = tier === 'CORE' 
    ? Array.from(signals.values()).filter(s => coreWatchlist.includes(s.ticker))
    : tier === 'HOT' 
    ? hotSignals 
    : liquidSignals;

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-data text-sm" style={{ color: tierColor }}>
          {tier}
        </h2>
        <span className="text-xs" style={{ color: '#64748b' }}>
          {tierSignals.length}
        </span>
      </div>
      
      <div className="space-y-2">
        {tierSignals.slice(0, 20).map(signal => (
          <button
            key={signal.id}
            onClick={() => selectSignal(signal.id)}
            className="w-full p-3 rounded-lg text-left transition-all"
            style={{
              background: 'rgba(19, 23, 32, 0.7)',
              backdropFilter: 'blur(20px)',
              border: selectedSignalId === signal.id ? '1px solid #06b6d4' : '1px solid rgba(255, 255, 255, 0.05)',
              boxShadow: selectedSignalId === signal.id ? '0 0 20px rgba(6, 182, 212, 0.4)' : 'none'
            }}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-data font-bold">{signal.ticker}</span>
              <span className="text-xs font-data" style={{ 
                color: signal.percentChange >= 0 ? '#10b981' : '#ef4444'
              }}>
                {signal.percentChange >= 0 ? '+' : ''}{signal.percentChange.toFixed(2)}%
              </span>
            </div>
            
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255, 255, 255, 0.05)' }}>
                <div 
                  className="h-full" 
                  style={{ 
                    width: `${signal.compositeScore}%`,
                    background: 'linear-gradient(90deg, #06b6d4, #a855f7)'
                  }} 
                />
              </div>
              <span className="text-xs font-data">{signal.compositeScore}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function SignalDetailCard() {
  const { selectedSignalId, signals } = useMarketStore();
  const signal = selectedSignalId ? signals.get(selectedSignalId) : null;

  if (!signal) {
    return (
      <div className="p-12 rounded-2xl text-center" style={{
        background: 'rgba(19, 23, 32, 0.7)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(255, 255, 255, 0.05)'
      }}>
        <p style={{ color: '#64748b' }}>Select a signal to view details</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="p-6 rounded-2xl" style={{
        background: 'rgba(19, 23, 32, 0.7)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(255, 255, 255, 0.05)'
      }}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="font-data text-4xl font-bold mb-2">{signal.ticker}</h1>
            <span className="text-xs px-3 py-1 rounded-full" style={{
              background: signal.tier === 'CORE' ? '#fbbf24' : signal.tier === 'HOT' ? '#06b6d4' : '#a855f7',
              color: '#000',
            }}>
              {signal.tier}
            </span>
          </div>
          
          <div className="text-right">
            <div className="font-data text-3xl font-bold" style={{ color: '#e4e4e7' }}>
              ${signal.currentPrice.toFixed(2)}
            </div>
            <div className="text-lg font-data" style={{
              color: signal.netChange >= 0 ? '#10b981' : '#ef4444'
            }}>
              {signal.netChange >= 0 ? '+' : ''}${signal.netChange.toFixed(2)} ({signal.percentChange.toFixed(2)}%)
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mt-6">
          <div className="text-center">
            <div className="text-xs mb-2" style={{ color: '#94a3b8' }}>MATH BRAIN</div>
            <div className="font-data text-2xl font-bold" style={{ color: '#06b6d4' }}>
              {signal.mathScore}
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs mb-2" style={{ color: '#94a3b8' }}>COMPOSITE</div>
            <div className="font-data text-3xl font-bold" style={{ 
              background: 'linear-gradient(135deg, #06b6d4, #a855f7)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}>
              {signal.compositeScore}
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs mb-2" style={{ color: '#94a3b8' }}>AI BRAIN</div>
            <div className="font-data text-2xl font-bold" style={{ color: '#a855f7' }}>
              {signal.aiScore}
            </div>
          </div>
        </div>
      </div>

      <div className="p-6 rounded-2xl h-96 flex items-center justify-center" style={{
        background: 'rgba(19, 23, 32, 0.7)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(255, 255, 255, 0.05)'
      }}>
        <p style={{ color: '#64748b' }}>Price Chart (Coming Next)</p>
      </div>
    </div>
  );
}

function SystemHealthPanel() {
  const { systemHealth } = useMarketStore();
  
  return (
    <div className="p-4 rounded-xl mb-4" style={{
      background: 'rgba(19, 23, 32, 0.7)',
      backdropFilter: 'blur(20px)',
      border: '1px solid rgba(255, 255, 255, 0.05)'
    }}>
      <h3 className="font-data text-sm mb-3" style={{ color: '#06b6d4' }}>
        SYSTEM HEALTH
      </h3>
      <div className="space-y-2 text-xs">
        <div className="flex justify-between">
          <span style={{ color: '#94a3b8' }}>DB Latency</span>
          <span className="font-data">{systemHealth?.dbLatency || 0}ms</span>
        </div>
        <div className="flex justify-between">
          <span style={{ color: '#94a3b8' }}>Ingestion Rate</span>
          <span className="font-data">{systemHealth?.ingestionRate || 0}/min</span>
        </div>
      </div>
    </div>
  );
}

function MLControlPanel() {
  const { criteria, updateCriteria } = useMarketStore();
  
  return (
    <div className="p-4 rounded-xl" style={{
      background: 'rgba(19, 23, 32, 0.7)',
      backdropFilter: 'blur(20px)',
      border: '1px solid rgba(255, 255, 255, 0.05)'
    }}>
      <h3 className="font-data text-sm mb-3" style={{ color: '#a855f7' }}>
        ML CONTROLS
      </h3>
      <div className="space-y-4">
        <div>
          <label className="text-xs block mb-2" style={{ color: '#94a3b8' }}>
            Min Composite Score: {criteria.minCompositeScore}
          </label>
          <input
            type="range"
            min="0"
            max="100"
            value={criteria.minCompositeScore}
            onChange={(e) => updateCriteria({ minCompositeScore: Number(e.target.value) })}
            className="w-full"
          />
        </div>
      </div>
    </div>
  );
}
