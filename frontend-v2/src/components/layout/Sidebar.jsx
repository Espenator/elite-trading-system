// OLEH: This is the main navigation for all 16 pages
// Organized by section: Command, Intelligence, ML & Analysis, Execution, System
// Every page maps 1:1 to a backend module per the architecture doc

import { NavLink, useLocation } from 'react-router-dom';
import { useState } from 'react';
import {
  LayoutDashboard,
  Bot,
  Monitor,
  Zap,
  Map,
  MessageCircle,
  Link2,
  Youtube,
  Brain,
  Search,
  RotateCcw,
  TrendingUp,
  LineChart,
  Shield,
  Target,
  Settings,
  ChevronLeft,
  Sparkles,
} from 'lucide-react';

// ----------- NAV SECTIONS -----------
// Grouped logically so Espen can find anything in 2 clicks
const navSections = [
  {
    label: 'COMMAND',
    items: [
      { to: '/dashboard', icon: LayoutDashboard, label: 'Intelligence Dashboard' },
      { to: '/agents', icon: Bot, label: 'Agent Command Center' },
      { to: '/operator', icon: Monitor, label: 'Operator Console' },
    ]
  },
  {
    label: 'INTELLIGENCE',
    items: [
      { to: '/signals', icon: Zap, label: 'Signal Intelligence' },
      { to: '/signal-heatmap', icon: Map, label: 'Signal Heatmap' },
      { to: '/sentiment', icon: MessageCircle, label: 'Sentiment Intelligence' },
      { to: '/data-sources', icon: Link2, label: 'Data Sources Monitor' },
      { to: '/youtube', icon: Youtube, label: 'YouTube Knowledge' },
    ]
  },
  {
    label: 'ML & ANALYSIS',
    items: [
      { to: '/ml-insights', icon: Brain, label: 'ML Brain & Flywheel' },
      { to: '/patterns', icon: Search, label: 'Screener & Patterns' },
      { to: '/backtest', icon: RotateCcw, label: 'Backtesting Lab' },
      { to: '/performance', icon: TrendingUp, label: 'Performance Analytics' },
    ]
  },
  {
    label: 'EXECUTION',
    items: [
      { to: '/trades', icon: LineChart, label: 'Trade Execution' },
      { to: '/risk', icon: Shield, label: 'Risk Intelligence' },
      { to: '/strategy', icon: Target, label: 'Strategy Intelligence' },
    ]
  },
  {
    label: 'SYSTEM',
    items: [
      { to: '/settings', icon: Settings, label: 'Settings' },
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
      } bg-dark border-r border-secondary/50 flex flex-col transition-all duration-300 overflow-hidden`}
    >
      {/* Logo + Collapse */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-secondary/50">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-success flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-white leading-tight">Embodier.ai</h1>
                            <p className="text-[10px] text-primary/70">Trading Intelligence</p>
            </div>
          </div>
        )}
        {collapsed && (
          <div className="w-8 h-8 mx-auto rounded-lg bg-gradient-to-br from-primary to-success flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="text-secondary hover:text-white transition-colors p-1"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <ChevronLeft className={`w-4 h-4 transition-transform duration-300 ${collapsed ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Navigation Sections */}
      <nav className="flex-1 overflow-y-auto custom-scrollbar py-2">
        {navSections.map((section) => (
          <div key={section.label} className="mb-1">
            {/* Section Label */}
            {!collapsed && (
              <div className="px-4 py-2">
                <span className="text-[10px] font-bold text-secondary tracking-widest">
                  {section.label}
                </span>
              </div>
            )}
            {collapsed && <div className="border-b border-secondary/30 mx-2 my-1" />}

            {/* Nav Items */}
            <ul className="space-y-0.5 px-2">
              {section.items.map((item) => {
                const isActive = location.pathname === item.to;
                const Icon = item.icon;
                return (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      className={() =>
                        `flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 group ${
                          isActive
                            ? 'bg-primary/10 text-primary border border-primary/20 shadow-sm shadow-primary/5'
                            : 'text-secondary hover:text-white hover:bg-secondary/20'
                        }`
                      }
                      title={collapsed ? item.label : undefined}
                    >
                      <span className={`flex-shrink-0 ${isActive ? 'drop-shadow-[0_0_4px_rgba(6,182,212,0.5)]' : ''}`}>
                        <Icon className="w-4 h-4" />
                      </span>
                      {!collapsed && (
                        <span className={`text-xs font-medium truncate ${isActive ? 'text-primary' : ''}`}>
                          {item.label}
                        </span>
                      )}
                      {isActive && !collapsed && (
                        <div className="ml-auto w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
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
        <div className="border-t border-secondary/50 p-3">
          <div className="bg-secondary/10 rounded-lg p-2">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] text-secondary font-medium">SYSTEM STATUS</span>
              <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
            </div>
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-secondary">3 Agents Running</span>
              <span className="text-success">All Healthy</span>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
