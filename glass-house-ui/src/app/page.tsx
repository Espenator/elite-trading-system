'use client';

import { useEffect } from 'react';
import { useMarketStore } from '@/lib/store';

export default function GlassHouseDashboard() {
  const { wsConnected, systemHealth } = useMarketStore();

  useEffect(() => {
    // Fetch initial data from backend
    fetch('http://localhost:8000/api/signals/?limit=100')
      .then(res => res.json())
      .then(data => {
        // Transform backend data to match our Signal interface
        const signals = data.map((item: any) => ({
          id: item.id,
          ticker: item.ticker,
          tier: item.tier || 'LIQUID',
          currentPrice: item.currentPrice || 0,
          netChange: item.netChange || 0,
          percentChange: item.percentChange || 0,
          mathScore: item.globalConfidence || 50, // Temporary mapping
          aiScore: item.globalConfidence || 50,   // Will be replaced with Claude
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
    <div className=\"min-h-screen\" style={{ background: 'var(--bg-deep-space)' }}>
      {/* Status Bar */}
      <div className=\"glass border-b border-[var(--border-subtle)] px-6 py-3 flex items-center justify-between\">
        <div className=\"flex items-center gap-6\">
          <h1 className=\"font-data text-xl\" style={{ color: 'var(--math-cyan)' }}>
            GLASS HOUSE COMMAND CENTER
          </h1>
          <div className=\"text-sm\" style={{ color: 'var(--text-secondary)' }}>
            {new Date().toLocaleTimeString('en-US', { hour12: false })}
          </div>
        </div>
        
        <div className=\"flex items-center gap-4\">
          <div className=\"flex items-center gap-2\">
            <div className={\w-2 h-2 rounded-full \\} />
            <span className=\"text-xs\" style={{ color: 'var(--text-secondary)' }}>
              {wsConnected ? 'CONNECTED' : 'DISCONNECTED'}
            </span>
          </div>
        </div>
      </div>

      {/* Main Grid Layout */}
      <div className=\"flex h-[calc(100vh-64px)]\">
        {/* Left Sidebar - Tier Lists */}
        <div className=\"w-80 border-r border-[var(--border-subtle)] p-4 overflow-y-auto\">
          <TierPanel tier=\"CORE\" />
          <TierPanel tier=\"HOT\" />
          <TierPanel tier=\"LIQUID\" />
        </div>

        {/* Center Stage */}
        <div className=\"flex-1 p-6 overflow-y-auto\">
          <SignalDetailCard />
        </div>

        {/* Right Panel */}
        <div className=\"w-96 border-l border-[var(--border-subtle)] p-4 overflow-y-auto\">
          <SystemHealthPanel />
          <MLControlPanel />
        </div>
      </div>
    </div>
  );
}

// Tier Panel Component
function TierPanel({ tier }: { tier: 'CORE' | 'HOT' | 'LIQUID' }) {
  const { coreWatchlist, hotSignals, liquidSignals, signals, selectSignal, selectedSignalId } = useMarketStore();
  
  const tierColor = tier === 'CORE' ? 'var(--profit-gold)' : 
                    tier === 'HOT' ? 'var(--math-cyan)' : 
                    'var(--ai-purple)';
  
  // Get signals for this tier
  const tierSignals = tier === 'CORE' 
    ? Array.from(signals.values()).filter(s => coreWatchlist.includes(s.ticker))
    : tier === 'HOT' 
    ? hotSignals 
    : liquidSignals;

  return (
    <div className=\"mb-6\">
      <div className=\"flex items-center justify-between mb-3\">
        <h2 className=\"font-data text-sm\" style={{ color: tierColor }}>
          {tier}
        </h2>
        <span className=\"text-xs\" style={{ color: 'var(--text-dimmed)' }}>
          {tierSignals.length}
        </span>
      </div>
      
      <div className=\"space-y-2\">
        {tierSignals.slice(0, 20).map(signal => (
          <button
            key={signal.id}
            onClick={() => selectSignal(signal.id)}
            className={\w-full glass p-3 rounded-lg text-left transition-all \\}
          >
            <div className=\"flex items-center justify-between mb-1\">
              <span className=\"font-data font-bold\">{signal.ticker}</span>
              <span className=\"text-xs font-data\" style={{ 
                color: signal.percentChange >= 0 ? 'var(--hedge-green)' : 'var(--alert-red)' 
              }}>
                {signal.percentChange >= 0 ? '+' : ''}{signal.percentChange.toFixed(2)}%
              </span>
            </div>
            
            <div className=\"flex items-center gap-2\">
              <div className=\"flex-1 h-1 bg-[var(--border-subtle)] rounded-full overflow-hidden\">
                <div 
                  className=\"h-full\" 
                  style={{ 
                    width: \\%\,
                    background: 'linear-gradient(90deg, var(--math-cyan), var(--ai-purple))'
                  }} 
                />
              </div>
              <span className=\"text-xs font-data\">{signal.compositeScore}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

// Signal Detail Card
function SignalDetailCard() {
  const { selectedSignalId, signals } = useMarketStore();
  const signal = selectedSignalId ? signals.get(selectedSignalId) : null;

  if (!signal) {
    return (
      <div className=\"glass p-12 rounded-2xl text-center\">
        <p style={{ color: 'var(--text-dimmed)' }}>Select a signal to view details</p>
      </div>
    );
  }

  return (
    <div className=\"space-y-6\">
      {/* Header Card */}
      <div className=\"glass p-6 rounded-2xl\">
        <div className=\"flex items-start justify-between mb-4\">
          <div>
            <h1 className=\"font-data text-4xl font-bold mb-2\">{signal.ticker}</h1>
            <span className=\"text-xs px-3 py-1 rounded-full\" style={{
              background: signal.tier === 'CORE' ? 'var(--profit-gold)' :
                         signal.tier === 'HOT' ? 'var(--math-cyan)' :
                         'var(--ai-purple)',
              color: '#000',
            }}>
              {signal.tier}
            </span>
          </div>
          
          <div className=\"text-right\">
            <div className=\"font-data text-3xl font-bold\" style={{ color: 'var(--text-primary)' }}>
              \
            </div>
            <div className=\"text-lg font-data\" style={{
              color: signal.netChange >= 0 ? 'var(--hedge-green)' : 'var(--alert-red)'
            }}>
              {signal.netChange >= 0 ? '+' : ''}\ ({signal.percentChange.toFixed(2)}%)
            </div>
          </div>
        </div>

        {/* Dual-Brain Scores */}
        <div className=\"grid grid-cols-3 gap-4 mt-6\">
          <div className=\"text-center\">
            <div className=\"text-xs mb-2\" style={{ color: 'var(--text-secondary)' }}>MATH BRAIN</div>
            <div className=\"font-data text-2xl font-bold\" style={{ color: 'var(--math-cyan)' }}>
              {signal.mathScore}
            </div>
          </div>
          <div className=\"text-center\">
            <div className=\"text-xs mb-2\" style={{ color: 'var(--text-secondary)' }}>COMPOSITE</div>
            <div className=\"font-data text-3xl font-bold\" style={{ 
              background: 'linear-gradient(135deg, var(--math-cyan), var(--ai-purple))',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}>
              {signal.compositeScore}
            </div>
          </div>
          <div className=\"text-center\">
            <div className=\"text-xs mb-2\" style={{ color: 'var(--text-secondary)' }}>AI BRAIN</div>
            <div className=\"font-data text-2xl font-bold\" style={{ color: 'var(--ai-purple)' }}>
              {signal.aiScore}
            </div>
          </div>
        </div>
      </div>

      {/* Placeholder for Chart */}
      <div className=\"glass p-6 rounded-2xl h-96 flex items-center justify-center\">
        <p style={{ color: 'var(--text-dimmed)' }}>Price Chart (Coming Next)</p>
      </div>
    </div>
  );
}

// System Health Panel
function SystemHealthPanel() {
  const { systemHealth } = useMarketStore();
  
  return (
    <div className=\"glass p-4 rounded-xl mb-4\">
      <h3 className=\"font-data text-sm mb-3\" style={{ color: 'var(--math-cyan)' }}>
        SYSTEM HEALTH
      </h3>
      <div className=\"space-y-2 text-xs\">
        <div className=\"flex justify-between\">
          <span style={{ color: 'var(--text-secondary)' }}>DB Latency</span>
          <span className=\"font-data\">{systemHealth?.dbLatency || 0}ms</span>
        </div>
        <div className=\"flex justify-between\">
          <span style={{ color: 'var(--text-secondary)' }}>Ingestion Rate</span>
          <span className=\"font-data\">{systemHealth?.ingestionRate || 0}/min</span>
        </div>
      </div>
    </div>
  );
}

// ML Control Panel
function MLControlPanel() {
  const { criteria, updateCriteria } = useMarketStore();
  
  return (
    <div className=\"glass p-4 rounded-xl\">
      <h3 className=\"font-data text-sm mb-3\" style={{ color: 'var(--ai-purple)' }}>
        ML CONTROLS
      </h3>
      <div className=\"space-y-4\">
        <div>
          <label className=\"text-xs block mb-2\" style={{ color: 'var(--text-secondary)' }}>
            Min Composite Score: {criteria.minCompositeScore}
          </label>
          <input
            type=\"range\"
            min=\"0\"
            max=\"100\"
            value={criteria.minCompositeScore}
            onChange={(e) => updateCriteria({ minCompositeScore: Number(e.target.value) })}
            className=\"w-full\"
          />
        </div>
      </div>
    </div>
  );
}
