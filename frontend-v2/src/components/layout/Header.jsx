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

export default function Header({ onMenuToggle }) {
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
    switch(status) {
      case 'active': return 'bg-emerald-500';
      case 'learning': return 'bg-amber-500';
      case 'idle': return 'bg-gray-500';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <header className="sticky top-0 z-50 border-b border-white/10">
              {/* Gradient background */}
      <div className="absolute inset-0 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 opacity-95" />
      <div className="absolute inset-0 bg-gradient-to-b from-blue-500/5 via-purple-500/5 to-transparent" />
      
      <div className="relative px-6 py-4">
        <div className="flex items-center justify-between gap-6">
          
          {/* Left section: Menu toggle + Search */}
          <div className="flex items-center gap-4 flex-1 max-w-2xl">
            {/* Mobile menu toggle */}
            <button
              onClick={onMenuToggle}
              className="lg:hidden p-2 rounded-lg hover:bg-white/5 transition-colors"
            >
              <Menu className="w-5 h-5 text-gray-400" />
            </button>

            {/* Search bar */}
            <div className="relative flex-1">
              <div className={`
                relative rounded-xl border transition-all duration-300
                ${searchFocused 
                  ? 'border-blue-500/50 bg-slate-800/60 shadow-lg shadow-blue-500/10' 
                  : 'border-white/10 bg-slate-800/40 hover:border-white/20'
                }
              `}>
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search tickers, patterns, signals..."
                  className="w-full pl-11 pr-4 py-2.5 bg-transparent text-sm text-white placeholder-gray-500 outline-none"
                  onFocus={() => setSearchFocused(true)}
                  onBlur={() => setSearchFocused(false)}
                />
                <kbd className="absolute right-4 top-1/2 -translate-y-1/2 px-2 py-1 text-xs font-medium text-gray-500 bg-slate-700/50 rounded border border-white/10">
                  ⌘K
                </kbd>
              </div>
            </div>
          </div>

          {/* Right section: Agent status + Notifications + User menu */}
          <div className="flex items-center gap-4">
            
            {/* Agent status indicators */}
            <div className="hidden xl:flex items-center gap-3 px-4 py-2 rounded-xl bg-slate-800/40 border border-white/10">
              <Activity className="w-4 h-4 text-emerald-400" />
              <div className="flex items-center gap-2">
                {agents.map((agent, idx) => (
                  <div key={idx} className="group relative">
                    <div className={`w-2 h-2 rounded-full ${getStatusColor(agent.status)} animate-pulse`} />
                    {/* Tooltip */}
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-slate-800 border border-white/10 rounded-lg text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                      <div className="font-medium text-white">{agent.name}</div>
                      <div className="text-gray-400 capitalize">{agent.status}</div>
                    </div>
                  </div>
                ))}
              </div>
              <span className="text-xs font-medium text-gray-400">
                4/4 Active
              </span>
            </div>

            {/* Market status indicator */}
            <div className="hidden lg:flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              <span className="text-sm font-medium text-emerald-400">Market Open</span>
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            </div>

            {/* Notifications */}
            <div className="relative">
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="relative p-2.5 rounded-xl bg-slate-800/40 border border-white/10 hover:bg-slate-700/40 hover:border-white/20 transition-all"
              >
                <Bell className="w-5 h-5 text-gray-400" />
                {/* Notification badge */}
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full text-xs font-bold text-white flex items-center justify-center border-2 border-slate-900">
                  4
                </span>
              </button>

              {/* Notifications dropdown */}
              {showNotifications && (
                <div className="absolute right-0 mt-2 w-80 rounded-xl bg-slate-800/95 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/50 overflow-hidden">
                  <div className="px-4 py-3 border-b border-white/10">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-semibold text-white">Notifications</h3>
                      <button className="text-xs text-blue-400 hover:text-blue-300">Mark all read</button>
                    </div>
                  </div>
                  <div className="max-h-96 overflow-y-auto">
                    {notifications.map((notif) => (
                      <div key={notif.id} className="px-4 py-3 hover:bg-white/5 border-b border-white/5 cursor-pointer transition-colors">
                        <div className="flex items-start gap-3">
                          <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center flex-shrink-0">
                            {notif.type === 'signal' && <Zap className="w-4 h-4 text-blue-400" />}
                            {notif.type === 'trade' && <TrendingUp className="w-4 h-4 text-emerald-400" />}
                            {notif.type === 'alert' && <Activity className="w-4 h-4 text-amber-400" />}
                            {notif.type === 'agent' && <Brain className="w-4 h-4 text-purple-400" />}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-white leading-snug">{notif.message}</p>
                            <p className="text-xs text-gray-500 mt-1">{notif.time}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="px-4 py-3 border-t border-white/10">
                    <button className="w-full text-sm text-blue-400 hover:text-blue-300 font-medium">
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
                className="flex items-center gap-3 pl-3 pr-4 py-2 rounded-xl bg-slate-800/40 border border-white/10 hover:bg-slate-700/40 hover:border-white/20 transition-all"
              >
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                  <User className="w-4 h-4 text-white" />
                </div>
                <div className="hidden md:block text-left">
                            <div className="text-sm font-medium text-white">Embodier Trader</div>
                  <div className="text-xs text-gray-500">Pro Account</div>
                </div>
                <ChevronDown className="w-4 h-4 text-gray-400" />
              </button>

              {/* User dropdown */}
              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-56 rounded-xl bg-slate-800/95 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/50 overflow-hidden">
                  <div className="px-4 py-3 border-b border-white/10">
                                  <div className="font-medium text-white">espen@embodier.ai</div>
                                  <div className="text-xs text-gray-500 mt-0.5">Account ID: EMB-2025-001</div>
                  </div>
                  <div className="py-2">
                    <a href="#" className="flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors">
                      <User className="w-4 h-4 text-gray-400" />
                      <span className="text-sm text-white">Profile</span>
                    </a>
                    <a href="#" className="flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors">
                      <Settings className="w-4 h-4 text-gray-400" />
                      <span className="text-sm text-white">Settings</span>
                    </a>
                    <a href="#" className="flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors">
                      <Activity className="w-4 h-4 text-gray-400" />
                      <span className="text-sm text-white">API Status</span>
                    </a>
                  </div>
                  <div className="border-t border-white/10 py-2">
                    <a href="#" className="flex items-center gap-3 px-4 py-2.5 text-red-400 hover:bg-red-500/5 transition-colors">
                      <span className="text-sm font-medium">Sign out</span>
                    </a>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
