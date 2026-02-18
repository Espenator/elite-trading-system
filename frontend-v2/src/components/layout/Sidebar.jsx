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
      className={`${collapsed ? 'w-16' : 'w-64'
        } bg-dark border-r border-secondary/50 flex flex-col transition-all duration-300 shrink-0 relative z-50`}
    >
      {/* Logo + Collapse — when collapsed: single centered strip */}
      <div
        className={`flex items-center border-b border-secondary/50 relative transition-all duration-300 ${collapsed ? 'justify-center gap-1 px-2 py-3' : 'justify-between px-4 py-4'
          }`}
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary to-success flex items-center justify-center shrink-0">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <h1 className="text-sm font-bold text-white leading-tight truncate">Embodier.ai</h1>
              <p className="text-[10px] text-primary/70 truncate">Trading Intelligence</p>
            </div>
          )}
        </div>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={`rounded-md text-secondary hover:text-white transition-colors
              ${collapsed ? 'p-0.5 absolute top-1/2 -translate-y-1/2 right-0 translate-x-1/2 border border-secondary/50 bg-dark' : 'p-1.5'}`}
          title="Expand sidebar"
        >
          <ChevronLeft className={`w-4 h-4 ${collapsed ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Navigation — when collapsed: centered icons, left-accent active */}
      <nav className="flex-1 overflow-y-auto custom-scrollbar py-2 min-h-0">
        {navSections.map((section, sectionIndex) => (
          <div key={section.label} className={collapsed ? '' : 'mb-1'}>
            {!collapsed && (
              <div className="px-4 py-2">
                <span className="text-[10px] font-bold text-secondary tracking-widest uppercase">
                  {section.label}
                </span>
              </div>
            )}
            {collapsed && sectionIndex > 0 && (
              <div className="mx-3 my-1.5 border-t border-secondary/40" aria-hidden />
            )}
            <ul className={collapsed ? 'space-y-0.5 px-1.5' : 'space-y-0.5 px-2'}>
              {section.items.map((item) => {
                const isActive = location.pathname === item.to;
                const Icon = item.icon;
                return (
                  <li key={item.to} className={`${collapsed ? 'mx-0.5' : ''}`}>
                    <NavLink
                      to={item.to}
                      title={item.label}
                      className={() =>
                        `flex items-center transition-all duration-200 group outline-none ${collapsed
                          ? `justify-center py-3 rounded-lg ${isActive
                            ? 'bg-primary/15 text-primary'
                            : 'text-secondary hover:text-white hover:bg-secondary/20'
                          }`
                          : `gap-3 px-3 py-2.5 rounded-lg ${isActive
                            ? 'bg-primary/10 text-primary border border-primary/20 shadow-sm shadow-primary/5'
                            : 'text-secondary hover:text-white border border-transparent hover:bg-secondary/20'
                          }`
                        }`
                      }
                    >
                      <span className={`flex-shrink-0 flex items-center justify-center ${isActive && !collapsed ? 'drop-shadow-[0_0_6px_rgba(6,182,212,0.4)]' : ''}`}>
                        <Icon className={collapsed ? 'w-5 h-5' : 'w-4 h-4'} strokeWidth={2} />
                      </span>
                      {!collapsed && (
                        <span className={`text-sm font-medium truncate ${isActive ? 'text-primary' : ''}`}>
                          {item.label}
                        </span>
                      )}
                    </NavLink>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Bottom: System Status — when collapsed: compact pulse + tooltip */}
      <div className={`border-t border-secondary/50 ${collapsed ? 'p-2' : 'p-3'}`}>
        {collapsed ? (
          <div
            className="flex justify-center"
            title="System status: 3 agents running, all healthy"
          >
            <div className="w-2.5 h-2.5 rounded-full bg-success animate-pulse ring-2 ring-success/30" />
          </div>
        ) : (
          <div className="bg-secondary/10 rounded-lg p-2.5">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] text-secondary font-medium uppercase tracking-wider">System</span>
              <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
            </div>
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-secondary">3 Agents</span>
              <span className="text-success font-medium">OK</span>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
