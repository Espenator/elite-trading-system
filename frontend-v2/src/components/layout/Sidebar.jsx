import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Signal, 
  History, 
  Brain,
  Layers,
  Settings,
  TrendingUp
} from 'lucide-react';
import clsx from 'clsx';

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/signals', icon: Signal, label: 'Signals' },
  { to: '/trades', icon: History, label: 'Trades' },
  { to: '/ml-insights', icon: Brain, label: 'ML Insights' },
  { to: '/patterns', icon: Layers, label: 'Patterns' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export default function Sidebar() {
  return (
    <aside className="w-64 bg-dark-card border-r border-dark-border flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-dark-border">
        <TrendingUp className="w-8 h-8 text-bullish mr-3" />
        <div>
          <h1 className="text-lg font-bold">Elite AI</h1>
          <p className="text-xs text-gray-400">Trading System</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3">
        <ul className="space-y-1">
          {navItems.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
                    isActive
                      ? 'bg-bullish/10 text-bullish border-l-2 border-bullish'
                      : 'text-gray-400 hover:text-white hover:bg-dark-hover'
                  )
                }
              >
                <item.icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* System info footer */}
      <div className="p-4 border-t border-dark-border">
        <div className="bg-dark-bg rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 bg-bullish rounded-full animate-pulse" />
            <span className="text-xs text-gray-400">System Status</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-gray-500">Symbols</span>
              <p className="text-white font-mono">487</p>
            </div>
            <div>
              <span className="text-gray-500">Uptime</span>
              <p className="text-white font-mono">99.9%</p>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
