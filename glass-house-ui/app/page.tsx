'use client';

import { useEffect, useState } from 'react';
import { useEliteStore } from '@/lib/store';
import { useNotifications } from '@/hooks/useNotifications';
import IntelligenceRadar from '@/components/IntelligenceRadar';
import TradingViewChart from '@/components/TradingViewChart';
import ExecutionDeck from '@/components/ExecutionDeck';
import LiveFeed from '@/components/LiveFeed';
import SettingsPanel from '@/components/SettingsPanel';
import Notification from '@/components/Notification';

export default function EliteTraderTerminal() {
  const { selectedTicker, timeframe, setTimeframe, systemStatus, latency, soundEnabled, toggleSound } = useEliteStore();
  const { notifications, addNotification, removeNotification } = useNotifications();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());

  // Update time every second
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <div className="elite-terminal-grid">
        {/* ZONE 0: COMMAND BAR */}
        <div className="command-bar">
          <div className="flex items-center gap-6 w-full">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-cyan-400 to-purple-500 rounded-lg flex items-center justify-center">
                <span className="text-xl font-bold">ET</span>
              </div>
              <h1 className="text-xl font-bold cyan-glow-text">ELITE TRADER</h1>
            </div>

            {/* Search Bar */}
            <div className="flex-1 max-w-md">
              <input
                type="text"
                placeholder="Search tickers..."
                className="w-full px-4 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none transition-colors"
              />
            </div>

            {/* Market Indices */}
            <div className="flex gap-4">
              <div className="main-symbol-card">
                <div className="text-xs text-slate-400">S&P 500</div>
                <div className="text-lg font-mono font-bold">6,850.69</div>
                <div className="text-xs text-green-400">+0.51%</div>
              </div>
              <div className="main-symbol-card">
                <div className="text-xs text-slate-400">DJI</div>
                <div className="text-lg font-mono font-bold">47,950</div>
                <div className="text-xs text-red-400">-0.01%</div>
              </div>
              <div className="main-symbol-card">
                <div className="text-xs text-slate-400">NASDAQ</div>
                <div className="text-lg font-mono font-bold">21,180</div>
                <div className="text-xs text-green-400">+0.12%</div>
              </div>
            </div>

            {/* Controls */}
            <div className="flex items-center gap-4">
              {/* Sound Toggle */}
              <button
                onClick={toggleSound}
                className={`p-2 rounded-lg transition-all `}
                title={soundEnabled ? 'Mute sounds' : 'Enable sounds'}
              >
                {soundEnabled ? '??' : '??'}
              </button>

              {/* Settings */}
              <button
                onClick={() => setSettingsOpen(true)}
                className="p-2 bg-slate-800 text-slate-400 rounded-lg hover:text-cyan-400 hover:bg-slate-700 transition-all"
                title="Settings"
              >
                ??
              </button>
            </div>

            {/* System Status */}
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full `}></div>
              <span className="text-xs text-slate-400">System {systemStatus}</span>
              <span className="text-xs text-slate-500">|</span>
              <span className="text-xs text-green-400 font-mono">{latency}ms</span>
            </div>

            {/* Time */}
            <div className="text-sm text-slate-400 font-mono">
              {currentTime.toLocaleTimeString()}
            </div>
          </div>
        </div>

        {/* ZONE 1: INTELLIGENCE RADAR */}
        <IntelligenceRadar />

        {/* ZONE 2: TACTICAL CHART */}
        <div className="tactical-chart">
          <div className="glass-card h-full flex flex-col">
            {/* Chart Header */}
            <div className="flex items-center justify-between p-4 border-b border-slate-700">
              <div>
                <h2 className="text-2xl font-bold cyan-glow-text">{selectedTicker}</h2>
                <div className="text-sm text-slate-400">Tactical Chart Center</div>
              </div>
              
              {/* Timeframe Selector */}
              <div className="flex gap-2">
                {(['1D', '1H', '15M', '5M'] as const).map(tf => (
                  <button
                    key={tf}
                    className={`px-4 py-2 rounded-lg border transition-all `}
                    onClick={() => setTimeframe(tf)}
                  >
                    {tf}
                  </button>
                ))}
              </div>
            </div>

            {/* TradingView Chart */}
            <div className="flex-1 p-4">
              <TradingViewChart />
            </div>

            {/* Factor Strip */}
            <div className="h-16 bg-slate-900/80 border-t border-slate-700 p-3">
              <div className="flex gap-2">
                <div className="flex-1 h-8 bg-yellow-500/20 border border-yellow-500/40 rounded flex items-center justify-center text-xs">
                  High Vol
                </div>
                <div className="flex-1 h-8 bg-green-500/20 border border-green-500/40 rounded flex items-center justify-center text-xs">
                  Breakout
                </div>
                <div className="flex-1 h-8 bg-purple-500/20 border border-purple-500/40 rounded flex items-center justify-center text-xs">
                  RSI Surge
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ZONE 3: EXECUTION DECK */}
        <ExecutionDeck />

        {/* ZONE 4: LIVE FEED */}
        <LiveFeed />
      </div>

      {/* Settings Panel */}
      <SettingsPanel isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />

      {/* Notification Stack */}
      <div className="fixed top-4 right-4 z-50 w-96">
        {notifications.map(notification => (
          <Notification
            key={notification.id}
            {...notification}
            onClose={() => removeNotification(notification.id)}
          />
        ))}
      </div>
    </>
  );
}
