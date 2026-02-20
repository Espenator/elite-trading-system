// EMBODIER TRADER - Embodier.ai Trading Intelligence System
// HEADER: Top navigation bar with search, notifications, agent status, user menu
// Modern gradient aesthetic with futuristic controls

import { useState } from 'react';
import {
  Search,
  Bell,
  Settings,
  User,
  ChevronDown,
  Activity,
  Zap,
  TrendingUp,
  Brain,
  Menu
} from 'lucide-react';

export default function Header({ onMenuToggle, wsConnected = false }) {
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [searchFocused, setSearchFocused] = useState(false);

  const agents = [
    { name: 'Market Scanner', status: 'active', color: 'emerald' },
    { name: 'Pattern AI', status: 'active', color: 'blue' },
    { name: 'Risk Manager', status: 'active', color: 'purple' },
    { name: 'YouTube Ingestion', status: 'learning', color: 'amber' }
  ];

  const notifications = [
    { id: 1, type: 'signal', message: 'New bullish pattern detected on AAPL', time: '2m ago' },
    { id: 2, type: 'trade', message: 'Trade executed: TSLA Long @ $245.30', time: '15m ago' },
    { id: 3, type: 'alert', message: 'Risk threshold exceeded on SPY position', time: '1h ago' },
    { id: 4, type: 'agent', message: 'YouTube Agent processed 5 new videos', time: '2h ago' }
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'bg-success';
      case 'learning': return 'bg-warning';
      case 'idle': return 'bg-secondary';
      case 'error': return 'bg-danger';
      default: return 'bg-secondary';
    }
  };

  return (
    <header className="sticky top-0 z-10 border-b border-secondary/30 h-16 flex items-center justify-between gap-6 px-6">
      {/* Left section: Menu toggle + Search */}
      <div className="flex items-center gap-4 flex-1 max-w-2xl">
        {/* Search bar */}
        <div className="relative flex-1">
          <div className={`
                relative rounded-xl border transition-all duration-300
                ${searchFocused
              ? 'border-primary/50 bg-secondary/20 shadow-lg shadow-primary/10'
              : 'border-secondary/30 bg-secondary/10 hover:border-secondary/50'
            }
              `}>
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary" />
            <input
              type="text"
              placeholder="Search tickers, patterns, signals..."
              className="w-full pl-11 pr-4 py-2.5 bg-transparent text-sm text-white placeholder-secondary outline-none"
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setSearchFocused(false)}
            />
            <kbd className="absolute right-4 top-1/2 -translate-y-1/2 px-2 py-1 text-xs font-medium text-secondary bg-secondary/20 rounded border border-secondary/30">
              ⌘K
            </kbd>
          </div>
        </div>
      </div>

      {/* Right section: Agent status + Notifications + User menu */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2.5 rounded-xl bg-secondary/10 border border-secondary/30 hover:bg-secondary/20 hover:border-white/20 transition-all"
          >
            <Bell className="w-5 h-5 text-secondary" />
            {/* Notification badge */}
            <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full text-xs font-bold text-white flex items-center justify-center">
              4
            </span>
          </button>

          {/* Notifications dropdown */}
          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 rounded-xl bg-dark backdrop-blur-xl border border-secondary/30 shadow-2xl shadow-black/50 overflow-hidden">
              <div className="px-4 py-3 border-b border-secondary/30">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white">Notifications</h3>
                  <button className="text-xs text-primary hover:text-primary/80">Mark all read</button>
                </div>
              </div>
              <div className="max-h-96 overflow-y-auto">
                {notifications.map((notif) => (
                  <div key={notif.id} className="px-4 py-3 hover:bg-white/5 border-b border-white/5 cursor-pointer transition-colors">
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                        {notif.type === 'signal' && <Zap className="w-4 h-4 text-primary" />}
                        {notif.type === 'trade' && <TrendingUp className="w-4 h-4 text-success" />}
                        {notif.type === 'alert' && <Activity className="w-4 h-4 text-warning" />}
                        {notif.type === 'agent' && <Brain className="w-4 h-4 text-primary" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-white leading-snug">{notif.message}</p>
                        <p className="text-xs text-secondary mt-1">{notif.time}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="px-4 py-3 border-t border-secondary/30">
                <button className="w-full text-sm text-primary hover:text-primary/80 font-medium">
                  View all notifications
                </button>
              </div>
            </div>
          )}
        </div>

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-3 pl-3 pr-4 py-2 rounded-xl bg-secondary/10 border border-secondary/30 hover:bg-secondary/20 hover:border-white/20 transition-all"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br bg-primary flex items-center justify-center">
              <User className="w-4 h-4 text-white" />
            </div>
            <div className="hidden md:block text-left">
              <div className="text-sm font-medium text-white">Embodier Trader</div>
              <div className="text-xs text-secondary">Pro Account</div>
            </div>
            <ChevronDown className="w-4 h-4 text-secondary" />
          </button>

          {/* User dropdown */}
          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-56 rounded-xl bg-dark backdrop-blur-xl border border-secondary/30 shadow-2xl shadow-black/50 overflow-hidden">
              <div className="px-4 py-3 border-b border-secondary/30">
                <div className="font-medium text-white">espen@embodier.ai</div>
                <div className="text-xs text-secondary mt-0.5">Account ID: EMB-2025-001</div>
              </div>
              <div className="py-2">
                <a href="#" className="flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors">
                  <User className="w-4 h-4 text-secondary" />
                  <span className="text-sm text-white">Profile</span>
                </a>
                <a href="#" className="flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors">
                  <Settings className="w-4 h-4 text-secondary" />
                  <span className="text-sm text-white">Settings</span>
                </a>
                <a href="#" className="flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors">
                  <Activity className="w-4 h-4 text-secondary" />
                  <span className="text-sm text-white">API Status</span>
                </a>
              </div>
              <div className="border-t border-secondary/30 py-2">
                <a href="#" className="flex items-center gap-3 px-4 py-2.5 text-danger hover:bg-danger/10 transition-colors">
                  <span className="text-sm font-medium">Sign out</span>
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
