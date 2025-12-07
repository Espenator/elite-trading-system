import IntelligenceRadar from './components/Zone1_IntelligenceRadar/IntelligenceRadar';
import TacticalChart from './components/Zone2_TacticalChart/TacticalChart';
import ExecutionDeck from './components/Zone3_ExecutionDeck/ExecutionDeck';
import LiveSignalFeed from './components/Zone4_LiveFeed/LiveSignalFeed';
import './App.css';

function App() {
  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-left">
          <span className="header-icon">🎯</span>
          <h1>Elite Trading Terminal</h1>
        </div>
        <div className="header-right">
          <span className="status-indicator">●</span>
          <span className="status-text">Real-time AI-powered trade signals</span>
        </div>
      </header>

      <div className="terminal-grid">
        <div className="zone zone-1">
          <IntelligenceRadar />
        </div>

        <div className="zone zone-2">
          <TacticalChart symbol="SPY" />
        </div>

        <div className="zone zone-3">
          <ExecutionDeck />
        </div>

        <div className="zone zone-4">
          <LiveSignalFeed />
        </div>
      </div>
    </div>
  );
}

export default App;
