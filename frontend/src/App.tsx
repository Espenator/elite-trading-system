import React from 'react';
import { IntelligenceRadar } from './components/Zone1_IntelligenceRadar/IntelligenceRadar';
import './App.css';

function App() {
  return (
    <div className="elite-terminal">
      <div className="terminal-header">
        <h1>🎯 Elite Trading Terminal</h1>
        <p>Real-time AI-powered trade signals</p>
      </div>
      
      <div className="terminal-grid">
        {/* Zone 1: Intelligence Radar */}
        <div className="zone zone-1">
          <IntelligenceRadar />
        </div>
        
        {/* Zone 2: Chart (placeholder) */}
        <div className="zone zone-2">
          <div className="placeholder">
            <h2>📈 Tactical Chart</h2>
            <p>Chart component coming soon</p>
          </div>
        </div>
        
        {/* Zone 3: Execution (placeholder) */}
        <div className="zone zone-3">
          <div className="placeholder">
            <h2>🎯 Execution Deck</h2>
            <p>Trade execution coming soon</p>
          </div>
        </div>
        
        {/* Zone 4: Live Feed (placeholder) */}
        <div className="zone zone-4">
          <div className="placeholder">
            <h2>🔴 Live Signal Feed</h2>
            <p>Signal feed coming soon</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
