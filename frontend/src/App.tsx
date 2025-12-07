import { useState } from 'react';
import CommandBar from './components/Zone0_CommandBar/CommandBar';
import IntelligenceRadar from './components/Zone1_IntelligenceRadar/IntelligenceRadar';
import TacticalChart from './components/Zone2_TacticalChart/TacticalChart';
import ExecutionDeck from './components/Zone3_ExecutionDeck/ExecutionDeck';
import LiveSignalFeed from './components/Zone4_LiveFeed/LiveSignalFeed';
import SettingsModal from './components/Settings/SettingsModal';
import KeyboardShortcuts from './components/Common/KeyboardShortcuts';
import './App.css';

function App() {
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <div className="app-container">
      <CommandBar />
      
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

      <SettingsModal 
        isOpen={settingsOpen} 
        onClose={() => setSettingsOpen(false)} 
      />

      <KeyboardShortcuts />
    </div>
  );
}

export default App;
