// EMBODIER TRADER - Enhanced Header with CNS Status
// Shows: connection status, homeostasis mode badge, circuit breaker icon,
// latest verdict summary, notification bell with live count.

import { useState } from "react";
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
  Shield,
  ShieldAlert,
  Wifi,
  WifiOff,
  Gauge,
} from "lucide-react";
import { useCNS, CNS_EVENTS } from "../../hooks/useCNS";

const MODE_COLORS = {
  AGGRESSIVE: { bg: "bg-green-500/20", text: "text-green-400", border: "border-green-500/50", dot: "bg-green-400" },
  NORMAL: { bg: "bg-cyan-500/20", text: "text-cyan-400", border: "border-cyan-500/50", dot: "bg-cyan-400" },
  DEFENSIVE: { bg: "bg-amber-500/20", text: "text-amber-400", border: "border-amber-500/50", dot: "bg-amber-400" },
  HALTED: { bg: "bg-red-500/20", text: "text-red-400", border: "border-red-500/50", dot: "bg-red-400" },
};

const EVENT_ICONS = {
  [CNS_EVENTS.COUNCIL_VERDICT]: { icon: Brain, color: "text-primary" },
  [CNS_EVENTS.MODE_CHANGE]: { icon: Gauge, color: "text-amber-400" },
  [CNS_EVENTS.CIRCUIT_BREAKER_FIRE]: { icon: ShieldAlert, color: "text-red-400" },
  [CNS_EVENTS.TRADE_EXECUTED]: { icon: TrendingUp, color: "text-green-400" },
  [CNS_EVENTS.RISK_ALERT]: { icon: Activity, color: "text-amber-400" },
};

export default function Header() {
  const {
    mode, positionScale, circuitBreakerArmed, circuitBreakerFired,
    latestVerdict, wsConnected, notifications, unreadCount,
    markRead, clearNotifications,
  } = useCNS();

  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [searchFocused, setSearchFocused] = useState(false);

  const modeStyle = MODE_COLORS[mode] || MODE_COLORS.NORMAL;

  return (
    <header className="sticky top-0 z-10 border-b border-secondary/30 h-16 flex items-center justify-between gap-4 px-6 bg-surface">
      {/* Left: Search */}
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <div className="relative flex-1 min-w-0 max-w-md">
          <div
            className={`
              relative rounded-xl border transition-all duration-300
              ${searchFocused
                ? "border-primary/50 bg-secondary/20 shadow-lg shadow-primary/10"
                : "border-secondary/30 bg-secondary/10 hover:border-secondary/50"
              }
            `}
          >
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary" />
            <input
              type="text"
              placeholder="Search tickers, signals..."
              className="w-full pl-11 pr-4 py-2 bg-transparent text-sm text-white placeholder-secondary outline-none"
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setSearchFocused(false)}
            />
            <kbd className="absolute right-3 top-1/2 -translate-y-1/2 px-1.5 py-0.5 text-xs font-medium text-secondary bg-secondary/20 rounded border border-secondary/30">
              ⌘K
            </kbd>
          </div>
        </div>
      </div>

      {/* Center: CNS Status Bar */}
      <div className="flex items-center gap-3">
        {/* Connection Status */}
        <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border ${wsConnected ? 'border-green-500/30 bg-green-500/10' : 'border-red-500/30 bg-red-500/10'}`}>
          {wsConnected ? (
            <Wifi className="w-3.5 h-3.5 text-green-400" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-red-400 animate-pulse" />
          )}
          <span className={`text-xs font-medium ${wsConnected ? 'text-green-400' : 'text-red-400'}`}>
            {wsConnected ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>

        {/* Homeostasis Mode Badge */}
        <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border ${modeStyle.border} ${modeStyle.bg}`}>
          <div className={`w-2 h-2 rounded-full ${modeStyle.dot} ${mode === 'HALTED' ? 'animate-pulse' : ''}`} />
          <span className={`text-xs font-bold tracking-wider ${modeStyle.text}`}>
            {mode}
          </span>
          <span className="text-xs text-secondary/70">
            {positionScale}x
          </span>
        </div>

        {/* Circuit Breaker Icon */}
        <div
          className={`p-1.5 rounded-lg border transition-all ${
            circuitBreakerFired
              ? 'border-red-500/50 bg-red-500/20'
              : circuitBreakerArmed
                ? 'border-green-500/30 bg-green-500/10'
                : 'border-secondary/30 bg-secondary/10'
          }`}
          title={circuitBreakerFired ? `CB fired: ${circuitBreakerFired}` : circuitBreakerArmed ? 'Circuit breaker armed' : 'Circuit breaker disarmed'}
        >
          {circuitBreakerFired ? (
            <ShieldAlert className="w-4 h-4 text-red-400 animate-pulse" />
          ) : (
            <Shield className={`w-4 h-4 ${circuitBreakerArmed ? 'text-green-400' : 'text-secondary'}`} />
          )}
        </div>

        {/* Latest Verdict Mini */}
        {latestVerdict && (
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-secondary/30 bg-secondary/10">
            <Brain className="w-3.5 h-3.5 text-primary" />
            <span className="text-xs text-white font-medium">
              {latestVerdict.symbol}
            </span>
            <span className={`text-xs font-bold ${
              latestVerdict.final_direction === 'buy' ? 'text-green-400' :
              latestVerdict.final_direction === 'sell' ? 'text-red-400' :
              'text-secondary'
            }`}>
              {(latestVerdict.final_direction || 'hold').toUpperCase()}
            </span>
            <span className="text-xs text-secondary">
              {((latestVerdict.final_confidence || 0) * 100).toFixed(0)}%
            </span>
          </div>
        )}
      </div>

      {/* Right: Notifications + User */}
      <div className="flex items-center gap-3">
        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2.5 rounded-xl bg-secondary/10 border border-secondary/30 hover:bg-secondary/20 hover:border-white/20 transition-all"
          >
            <Bell className="w-5 h-5 text-secondary" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full text-xs font-bold text-white flex items-center justify-center">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* Notifications dropdown */}
          {showNotifications && (
            <div className="absolute right-0 mt-2 w-96 rounded-xl bg-dark backdrop-blur-xl border border-secondary/30 shadow-2xl shadow-black/50 overflow-hidden z-50">
              <div className="px-4 py-3 border-b border-secondary/30">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white">
                    Notifications {unreadCount > 0 && <span className="text-primary">({unreadCount})</span>}
                  </h3>
                  <button
                    onClick={clearNotifications}
                    className="text-xs text-primary hover:text-primary/80"
                  >
                    Clear all
                  </button>
                </div>
              </div>
              <div className="max-h-96 overflow-y-auto custom-scrollbar">
                {notifications.length === 0 && (
                  <div className="px-4 py-8 text-center text-sm text-secondary">
                    No notifications yet
                  </div>
                )}
                {notifications.map((notif) => {
                  const evInfo = EVENT_ICONS[notif.type] || { icon: Activity, color: "text-secondary" };
                  const Icon = evInfo.icon;
                  return (
                    <div
                      key={notif.id}
                      onClick={() => markRead(notif.id)}
                      className={`px-4 py-3 hover:bg-white/5 border-b border-white/5 cursor-pointer transition-colors ${!notif.read ? 'bg-primary/5' : ''}`}
                    >
                      <div className="flex items-start gap-3">
                        <div className={`w-8 h-8 rounded-lg ${!notif.read ? 'bg-primary/10' : 'bg-secondary/10'} flex items-center justify-center flex-shrink-0`}>
                          <Icon className={`w-4 h-4 ${evInfo.color}`} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-white leading-snug">
                            {notif.payload?.message || notif.type}
                          </p>
                          <p className="text-xs text-secondary mt-1">
                            {formatTimeAgo(notif.timestamp)}
                          </p>
                        </div>
                        {!notif.read && (
                          <div className="w-2 h-2 rounded-full bg-primary flex-shrink-0 mt-2" />
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 pl-3 pr-3 py-2 rounded-xl bg-secondary/10 border border-secondary/30 hover:bg-secondary/20 hover:border-white/20 transition-all"
          >
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br bg-primary flex items-center justify-center">
              <User className="w-3.5 h-3.5 text-white" />
            </div>
            <div className="hidden md:block text-left">
              <div className="text-sm font-medium text-white leading-tight">
                Embodier
              </div>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-secondary" />
          </button>

          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-56 rounded-xl bg-dark backdrop-blur-xl border border-secondary/30 shadow-2xl shadow-black/50 overflow-hidden z-50">
              <div className="px-4 py-3 border-b border-secondary/30">
                <div className="font-medium text-white">espen@embodier.ai</div>
                <div className="text-xs text-secondary mt-0.5">Pro Account</div>
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

function formatTimeAgo(ts) {
  const diff = Date.now() - ts;
  if (diff < 60000) return 'just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return `${Math.floor(diff / 86400000)}d ago`;
}
