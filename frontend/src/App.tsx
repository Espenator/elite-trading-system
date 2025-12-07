import { useState } from 'react';
import CommandBar from './components/Zone0_CommandBar/CommandBar';
import IntelligenceRadar from './components/Zone1_IntelligenceRadar/IntelligenceRadar';
import TacticalChart from './components/Zone2_TacticalChart/TacticalChart';
import ExecutionDeck from './components/Zone3_ExecutionDeck/ExecutionDeck';
import LiveSignalFeed from './components/Zone4_LiveFeed/LiveSignalFeed';
import KeyboardShortcuts from './components/Common/KeyboardShortcuts';
import PerformanceOverlay from './components/Common/PerformanceOverlay';
import ThemeSwitcher from './components/Common/ThemeSwitcher';
import { ToastProvider } from './components/Notifications/ToastProvider';
import ContextMenu from './components/Common/ContextMenu';
import './App.css';
import './styles/legendary.css';

function App() {
  const [activeSymbol, setActiveSymbol] = useState('SPY');
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; ticker: string } | null>(null);

  const handleTickerClick = (ticker: string) => {
    setActiveSymbol(ticker);
  };

  const handleContextMenu = (e: React.MouseEvent, ticker: string) => {
    e.preventDefault();
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      ticker
    });
  };

  // Request notification permission
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  return (
    <ToastProvider>
      <div className="app-container">
        <CommandBar 
          activeSymbol={activeSymbol}
          onSymbolChange={setActiveSymbol}
        />
        
        <div className="terminal-grid">
          <div className="zone zone-1 card-legendary interactive-lift">
            <IntelligenceRadar onContextMenu={handleContextMenu} />
          </div>

          <div className="zone zone-2 card-legendary interactive-lift">
            <TacticalChart symbol={activeSymbol} />
          </div>

          <div className="zone zone-3 card-legendary interactive-lift">
            <ExecutionDeck />
          </div>

          <div className="zone zone-4 card-legendary interactive-lift">
            <LiveSignalFeed onTickerClick={handleTickerClick} onContextMenu={handleContextMenu} />
          </div>
        </div>

        {contextMenu && (
          <ContextMenu
            x={contextMenu.x}
            y={contextMenu.y}
            ticker={contextMenu.ticker}
            onClose={() => setContextMenu(null)}
          />
        )}

        <div className="floating-controls">
          <ThemeSwitcher />
        </div>

        <KeyboardShortcuts />
        <PerformanceOverlay />
      </div>
    </ToastProvider>
  );
}

export default App;
