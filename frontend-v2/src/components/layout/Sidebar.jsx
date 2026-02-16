// OLEH: This is the main navigation for all 15 pages
// Organized by section: Command, Intelligence, ML & Analysis, Execution, System
// Every page maps 1:1 to a backend module per the architecture doc

import { NavLink, useLocation } from 'react-router-dom';
import { useState } from 'react';

// ----------- NAV SECTIONS -----------
// Grouped logically so Espen can find anything in 2 clicks
const navSections = [
  {
    label: 'COMMAND',
    items: [
      { to: '/dashboard', icon: '⬢', label: 'Intelligence Dashboard' },
      { to: '/agents', icon: '⚙️', label: 'Agent Command Center' },
      { to: '/operator', icon: '🖥️', label: 'Operator Console' },
    ]
  },
  {
    label: 'INTELLIGENCE',
    items: [
      { to: '/signals', icon: '⚡', label: 'Signal Intelligence' },
      { to: '/signal-heatmap', icon: '🗺️', label: 'Signal Heatmap' },
      { to: '/sentiment', icon: '🔴', label: 'Sentiment Intelligence' },
      { to: '/data-sources', icon: '🔗', label: 'Data Sources Monitor' },
      { to: '/youtube', icon: '🎬', label: 'YouTube Knowledge' },
    ]
  },
  {
    label: 'ML & ANALYSIS',
    items: [
      { to: '/ml-insights', icon: '🧬', label: 'ML Brain & Flywheel' },
      { to: '/patterns', icon: '🔍', label: 'Screener & Patterns' },
      { to: '/backtest', icon: '⏪', label: 'Backtesting Lab' },
      { to: '/performance', icon: '📈', label: 'Performance Analytics' },
    ]
  },
  {
    label: 'EXECUTION',
    items: [
      { to: '/trades', icon: '💹', label: 'Trade Execution' },
      { to: '/risk', icon: '🛡️', label: 'Risk Intelligence' },
      { to: '/strategy', icon: '🎯', label: 'Strategy Intelligence' },
    ]
  },
  {
    label: 'SYSTEM',
    items: [
      { to: '/settings', icon: '⚙️', label: 'Settings' },
    ]
  },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  return (
    <aside
      className={`${
        collapsed ? 'w-16' : 'w-64'
      } bg-gradient-to-b from-gray-950 via-gray-900 to-gray-950 border-r border-gray-800/50 flex flex-col transition-all duration-300 overflow-hidden`}
    >
      {/* Logo + Collapse */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-gray-800/50">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-emerald-500 flex items-center justify-center">
              <span className="text-white font-bold text-sm">◈</span>
            </div>
            <div>
              <h1 className="text-sm font-bold text-white leading-tight">Embodier.ai</h1>
                            <p className="text-[10px] text-cyan-400/70">Trading Intelligence</p>
            </div>
          </div>
        )}
        {collapsed && (
          <div className="w-8 h-8 mx-auto rounded-lg bg-gradient-to-br from-cyan-500 to-emerald-500 flex items-center justify-center">
            <span className="text-white font-bold text-sm">◈</span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="text-gray-500 hover:text-white transition-colors p-1"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <svg className={`w-4 h-4 transition-transform duration-300 ${collapsed ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7" />
          </svg>
        </button>
      </div>

      {/* Navigation Sections */}
      <nav className="flex-1 overflow-y-auto custom-scrollbar py-2">
        {navSections.map((section) => (
          <div key={section.label} className="mb-1">
            {/* Section Label */}
            {!collapsed && (
              <div className="px-4 py-2">
                <span className="text-[10px] font-bold text-gray-600 tracking-widest">
                  {section.label}
                </span>
              </div>
            )}
            {collapsed && <div className="border-b border-gray-800/30 mx-2 my-1" />}

            {/* Nav Items */}
            <ul className="space-y-0.5 px-2">
              {section.items.map((item) => {
                const isActive = location.pathname === item.to;
                return (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      className={() =>
                        `flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 group ${
                          isActive
                            ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shadow-sm shadow-cyan-500/5'
                            : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                        }`
                      }
                      title={collapsed ? item.label : undefined}
                    >
                      <span className={`text-base flex-shrink-0 ${isActive ? 'drop-shadow-[0_0_4px_rgba(6,182,212,0.5)]' : ''}`}>
                        {item.icon}
                      </span>
                      {!collapsed && (
                        <span className={`text-xs font-medium truncate ${isActive ? 'text-cyan-300' : ''}`}>
                          {item.label}
                        </span>
                      )}
                      {isActive && !collapsed && (
                        <div className="ml-auto w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                      )}
                    </NavLink>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Bottom: System Status */}
      {!collapsed && (
        <div className="border-t border-gray-800/50 p-3">
          <div className="bg-gray-800/30 rounded-lg p-2">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] text-gray-500 font-medium">SYSTEM STATUS</span>
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            </div>
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-gray-400">3 Agents Running</span>
              <span className="text-emerald-400">All Healthy</span>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
