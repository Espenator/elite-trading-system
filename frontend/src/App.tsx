import { useState, useEffect } from 'react';
import CommandBar from './components/Zone0_CommandBar/CommandBar';
import IntelligenceRadar from './components/Zone1_IntelligenceRadar/IntelligenceRadar';
import SignalComparison from './components/Zone2_TacticalChart/SignalComparison';
import ExecutionDeck from './components/Zone3_ExecutionDeck/ExecutionDeck';
import PortfolioRace from './components/Zone3_ExecutionDeck/PortfolioRace';
import PositionSizer from './components/Zone3_ExecutionDeck/PositionSizer';
import LiveSignalFeed from './components/Zone4_LiveFeed/LiveSignalFeed';
import KeyboardShortcuts from './components/Common/KeyboardShortcuts';
import PerformanceOverlay from './components/Common/PerformanceOverlay';
import ThemeSwitcher from './components/Common/ThemeSwitcher';
import { ToastProvider } from './components/Notifications/ToastProvider';
import ContextMenu from './components/Common/ContextMenu';
import './App.css';
import './styles/legendary.css';
import './styles/ultra-wide.css';

function App() {
  const [activeSymbol, setActiveSymbol] = useState('SPY');
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; ticker: string } | null>(null);

  const mockSignals = [
    { ticker: 'TGL', score: 92.3, confidence: 88, rvol: 2.3, recommendation: 'BUY' as const },
    { ticker: 'SMX', score: 87.6, confidence: 91, rvol: 1.8, recommendation: 'BUY' as const },
    { ticker: 'AAPL', score: 83.1, confidence: 85, rvol: 1.2, recommendation: 'HOLD' as const },
  ];

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
            <SignalComparison signals={mockSignals} />
          </div>

          <div className="zone zone-3 card-legendary interactive-lift">
            <div className="zone3-stack">
              <PortfolioRace />
              <PositionSizer 
                accountBalance={1000000}
                maxRiskPercent={2.0}
                currentPrice={49.23}
                stopPrice={47.00}
              />
              <ExecutionDeck />
            </div>
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
