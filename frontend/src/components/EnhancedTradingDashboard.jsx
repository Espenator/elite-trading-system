import React, { useState, useEffect } from 'react';
import MarketHeader from './MarketHeader';
import LiveSignalFeed from './LiveSignalFeed';
import TacticalChart from './TacticalChart';
import ExecutionDeck from './ExecutionDeck';
import PositionsPanel from './PositionsPanel';
import RiskShield from './RiskShield';
import MLInsightsPanel from './MLInsightsPanel';
import NotificationCenter from './NotificationCenter';
import MarketRegimeBadge from './MarketRegimeBadge';
import KeyboardShortcuts from './KeyboardShortcuts';
import { Settings, BarChart2, Shield, Brain, Target } from 'lucide-react';

/**
 * Enhanced Trading Dashboard - Institutional-grade UI
 * 
 * Combines all improvements into a cohesive, trader-first interface:
 * - Smart notifications with audio alerts
 * - 6-layer risk validation shield
 * - ML model transparency
 * - Market regime adaptation
 * - Keyboard shortcuts for power users
 * - Preserved tactical chart as centerpiece
 */

const ViewToggle = ({ views, activeView, onViewChange }) => (
  <div className="flex gap-2 bg-slate-800/50 p-1 rounded-lg">
    {views.map(view => (
      <button
        key={view.id}
        onClick={() => onViewChange(view.id)}
        className={`px-4 py-2 rounded-md transition-colors flex items-center gap-2 ${
          activeView === view.id
            ? 'bg-teal-500/20 text-teal-400 border border-teal-500/50'
            : 'text-gray-400 hover:text-white hover:bg-slate-700/50'
        }`}
      >
        {view.icon}
        <span className="text-sm font-semibold">{view.label}</span>
      </button>
    ))}
  </div>
);

export default function EnhancedTradingDashboard() {
  const [activeView, setActiveView] = useState('signals'); // signals | positions | risk | analytics | settings
  const [selectedSignal, setSelectedSignal] = useState(null);
  const [darkMode, setDarkMode] = useState(true);

  const views = [
    { id: 'signals', label: 'Signals', icon: <Target size={16} /> },
    { id: 'positions', label: 'Positions', icon: <BarChart2 size={16} /> },
    { id: 'risk', label: 'Risk Shield', icon: <Shield size={16} /> },
    { id: 'analytics', label: 'ML Analytics', icon: <Brain size={16} /> },
    { id: 'settings', label: 'Settings', icon: <Settings size={16} /> }
  ];

  // Handle signal selection
  const handleSignalSelect = (signal) => {
    setSelectedSignal(signal);
  };

  return (
    <div className={`min-h-screen ${
      darkMode ? 'bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950' : 'bg-white'
    }`}>
      {/* Header with Market Data and Notifications */}
      <div className="sticky top-0 z-30 border-b border-slate-700/50 backdrop-blur-lg bg-slate-900/80">
        <div className="px-6 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold bg-gradient-to-r from-teal-400 to-cyan-400 bg-clip-text text-transparent">
                ELITE TRADER
              </h1>
              <MarketRegimeBadge />
            </div>
            
            <div className="flex items-center gap-4">
              <MarketHeader />
              <NotificationCenter />
            </div>
          </div>
        </div>
        
        {/* View Navigation */}
        <div className="px-6 pb-3">
          <ViewToggle 
            views={views} 
            activeView={activeView} 
            onViewChange={setActiveView} 
          />
        </div>
      </div>

      {/* Main Content Area */}
      <div className="px-6 py-6">
        {/* SIGNALS VIEW - Primary trader workflow */}
        {activeView === 'signals' && (
          <div className="grid grid-cols-12 gap-6">
            {/* Top Signals Table - Left 8 columns */}
            <div className="col-span-8">
              <LiveSignalFeed 
                onSignalSelect={handleSignalSelect}
                showSparklines={true}
              />
            </div>
            
            {/* Execution Deck + Mini Risk - Right 4 columns */}
            <div className="col-span-4 space-y-6">
              {selectedSignal && (
                <ExecutionDeck signal={selectedSignal} />
              )}
              
              {/* Compact Risk Summary */}
              <div className="p-4 bg-slate-900/50 rounded-lg border border-slate-700/50">
                <h3 className="font-bold mb-3 flex items-center gap-2">
                  <Shield className="text-teal-400" size={20} />
                  Risk Status
                </h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-400"></div>
                    <span className="text-gray-400">All Systems GO</span>
                  </div>
                  <button 
                    onClick={() => setActiveView('risk')}
                    className="text-teal-400 hover:text-teal-300 text-xs underline"
                  >
                    View Details →
                  </button>
                </div>
              </div>
            </div>
            
            {/* Tactical Chart - Full width below */}
            <div className="col-span-12">
              {selectedSignal && (
                <div className="bg-slate-900/50 rounded-lg border border-slate-700/50 p-6">
                  <h3 className="font-bold text-lg mb-4">
                    📈 Tactical Chart: {selectedSignal.symbol} - ${selectedSignal.price}
                  </h3>
                  <TacticalChart 
                    symbol={selectedSignal.symbol}
                    height={400}
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {/* POSITIONS VIEW - Active trades */}
        {activeView === 'positions' && (
          <div className="grid grid-cols-12 gap-6">
            <div className="col-span-8">
              <PositionsPanel />
            </div>
            <div className="col-span-4">
              <div className="bg-slate-900/50 rounded-lg border border-slate-700/50 p-6">
                <h3 className="font-bold text-lg mb-4">Portfolio Summary</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Total P&L Today</span>
                    <span className="text-green-400 font-bold">+$1,247 (+2.1%)</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Win Rate</span>
                    <span className="text-white font-bold">68.2%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Open Positions</span>
                    <span className="text-white font-bold">3 / 15</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Buying Power</span>
                    <span className="text-white font-bold">$48,750</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* RISK VIEW - 6-Layer validation */}
        {activeView === 'risk' && (
          <div className="max-w-4xl mx-auto">
            <RiskShield symbol={selectedSignal?.symbol || ''} />
          </div>
        )}

        {/* ANALYTICS VIEW - ML insights */}
        {activeView === 'analytics' && (
          <div className="max-w-6xl mx-auto">
            <MLInsightsPanel />
          </div>
        )}

        {/* SETTINGS VIEW - Configuration */}
        {activeView === 'settings' && (
          <div className="max-w-4xl mx-auto">
            <div className="bg-slate-900/50 rounded-lg border border-slate-700/50 p-6">
              <h2 className="text-2xl font-bold mb-6">Settings</h2>
              
              <div className="space-y-6">
                {/* Appearance */}
                <div>
                  <h3 className="font-semibold mb-3">Appearance</h3>
                  <div className="flex items-center justify-between p-3 bg-slate-800/30 rounded">
                    <span>Dark Mode</span>
                    <button 
                      onClick={() => setDarkMode(!darkMode)}
                      className={`w-12 h-6 rounded-full transition-colors ${
                        darkMode ? 'bg-teal-500' : 'bg-gray-600'
                      }`}
                    >
                      <div className={`w-5 h-5 rounded-full bg-white transition-transform ${
                        darkMode ? 'translate-x-6' : 'translate-x-1'
                      }`} />
                    </button>
                  </div>
                </div>
                
                {/* Trading Preferences */}
                <div>
                  <h3 className="font-semibold mb-3">Trading Preferences</h3>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-3 bg-slate-800/30 rounded">
                      <span>Default Position Size</span>
                      <input 
                        type="number" 
                        defaultValue="100" 
                        className="w-20 px-2 py-1 bg-slate-700 rounded text-right"
                      />
                    </div>
                    <div className="flex items-center justify-between p-3 bg-slate-800/30 rounded">
                      <span>Auto-Execute T1 Signals</span>
                      <input type="checkbox" className="w-4 h-4" />
                    </div>
                  </div>
                </div>
                
                {/* Notifications */}
                <div>
                  <h3 className="font-semibold mb-3">Notifications</h3>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-3 bg-slate-800/30 rounded">
                      <span>Audio Alerts</span>
                      <input type="checkbox" defaultChecked className="w-4 h-4" />
                    </div>
                    <div className="flex items-center justify-between p-3 bg-slate-800/30 rounded">
                      <span>T1 Signal Volume</span>
                      <input 
                        type="range" 
                        min="0" 
                        max="100" 
                        defaultValue="80" 
                        className="w-32"
                      />
                    </div>
                  </div>
                </div>
                
                {/* API Connections */}
                <div>
                  <h3 className="font-semibold mb-3">API Connections</h3>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-3 bg-slate-800/30 rounded">
                      <div>
                        <p className="font-medium">Alpaca</p>
                        <p className="text-xs text-gray-400">Paper Trading</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></div>
                        <span className="text-green-400 text-sm">Connected</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Keyboard Shortcuts Overlay */}
      <KeyboardShortcuts />
    </div>
  );
}