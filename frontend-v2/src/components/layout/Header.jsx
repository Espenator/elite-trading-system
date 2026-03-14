// EMBODIER TRADER — Header (Aurora Design System)
//
// Visual spec (matches mockups):
//   - bg-surface (#111827), 64px height, border-bottom rgba(42,52,68,0.5)
//   - Left:   search bar with ⌘K shortcut
//   - Center: CNS status (WS/API health dots + LIVE/OFFLINE) · Mode badge · Circuit-breaker icon · Latest verdict
//   - Right:  Regime badge (GREEN/YELLOW/RED + %) · Notification bell · User profile
//
// All accent colour references use #00D9FF (primary) — NOT #06b6d4.

import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Bell,
  Settings,
  User,
  ChevronDown,
  Activity,
  Brain,
  Shield,
  ShieldAlert,
  Wifi,
  WifiOff,
  TrendingUp,
  Gauge,
} from "lucide-react";
import { useCNS, CNS_EVENTS } from "../../hooks/useCNS";

// ── Mode badge colours ────────────────────────────────────────────────────────
const MODE_COLORS = {
  AGGRESSIVE: {
    bg:     "rgba(16,185,129,0.12)",
    border: "rgba(16,185,129,0.35)",
    text:   "#10B981",
    dot:    "#10B981",
  },
  NORMAL: {
    bg:     "rgba(0,217,255,0.10)",
    border: "rgba(0,217,255,0.30)",
    text:   "#00D9FF",
    dot:    "#00D9FF",
  },
  DEFENSIVE: {
    bg:     "rgba(245,158,11,0.12)",
    border: "rgba(245,158,11,0.35)",
    text:   "#F59E0B",
    dot:    "#F59E0B",
  },
  HALTED: {
    bg:     "rgba(239,68,68,0.12)",
    border: "rgba(239,68,68,0.35)",
    text:   "#EF4444",
    dot:    "#EF4444",
  },
};

// ── Regime badge colours ──────────────────────────────────────────────────────
const REGIME_COLORS = {
  GREEN:  { bg: "rgba(16,185,129,0.15)",  border: "rgba(16,185,129,0.4)",  text: "#10B981" },
  YELLOW: { bg: "rgba(245,158,11,0.15)",  border: "rgba(245,158,11,0.4)",  text: "#F59E0B" },
  RED:    { bg: "rgba(239,68,68,0.15)",   border: "rgba(239,68,68,0.4)",   text: "#EF4444" },
};

// ── Notification event icon map ───────────────────────────────────────────────
const EVENT_ICONS = {
  [CNS_EVENTS?.COUNCIL_VERDICT]:      { icon: Brain,     color: "#00D9FF" },
  [CNS_EVENTS?.MODE_CHANGE]:          { icon: Gauge,     color: "#F59E0B" },
  [CNS_EVENTS?.CIRCUIT_BREAKER_FIRE]: { icon: ShieldAlert, color: "#EF4444" },
  [CNS_EVENTS?.TRADE_EXECUTED]:       { icon: TrendingUp, color: "#10B981" },
  [CNS_EVENTS?.RISK_ALERT]:           { icon: Activity,  color: "#F59E0B" },
};

// ── Pill component — reused for WS/API indicators ────────────────────────────
function StatusPill({ children, bg, border }) {
  return (
    <div
      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium"
      style={{ background: bg, border: `1px solid ${border}` }}
    >
      {children}
    </div>
  );
}

// ── Regime badge ─────────────────────────────────────────────────────────────
function RegimeBadge({ regime = "GREEN", pct }) {
  const c = REGIME_COLORS[regime] ?? REGIME_COLORS.GREEN;
  return (
    <div
      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg"
      style={{ background: c.bg, border: `1px solid ${c.border}` }}
    >
      <div
        className="w-2 h-2 rounded-full"
        style={{ background: c.text, boxShadow: `0 0 6px ${c.text}` }}
      />
      <span className="text-xs font-bold tracking-wider" style={{ color: c.text }}>
        {regime}
      </span>
      {pct != null && (
        <span className="text-xs font-mono text-[#9CA3AF]">{pct}%</span>
      )}
    </div>
  );
}

// ── Main ─────────────────────────────────────────────────────────────────────
export default function Header() {
  const navigate = useNavigate();
  const {
    mode,
    positionScale,
    circuitBreakerArmed,
    circuitBreakerFired,
    latestVerdict,
    wsConnected,
    wsReconnecting,
    notifications = [],
    unreadCount = 0,
    markRead,
    clearNotifications,
    marketRegime,
    regimePct,
  } = useCNS();

  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu]           = useState(false);
  const [searchFocused, setSearchFocused]         = useState(false);
  const [searchValue, setSearchValue]             = useState("");

  const modeStyle = MODE_COLORS[mode] ?? MODE_COLORS.NORMAL;

  const searchInputRef = useRef(null);
  useEffect(() => {
    const onKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        searchInputRef.current?.focus();
        searchInputRef.current?.select?.();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const handleSearchSubmit = useCallback(() => {
    const sym = searchValue.trim().toUpperCase();
    if (!sym) return;
    setSearchValue("");
    setSearchFocused(false);
    navigate(`/symbol/${encodeURIComponent(sym)}`);
  }, [searchValue, navigate]);

  return (
    <header
      role="banner"
      className="sticky top-0 z-10 h-16 flex items-center justify-between gap-4 px-3 md:px-6 overflow-x-auto no-scrollbar"
      style={{
        background:   "#111827",
        borderBottom: "1px solid rgba(42,52,68,0.5)",
      }}
    >
      {/* ── Left: Search ────────────────────────────────────────────────── */}
      <div className="hidden sm:flex items-center flex-1 min-w-0 max-w-xs">
        <div
          className="relative w-full rounded-[8px] transition-all duration-200"
          style={{
            background:   searchFocused ? "rgba(0,217,255,0.05)" : "rgba(255,255,255,0.04)",
            border:       `1px solid ${searchFocused ? "rgba(0,217,255,0.4)" : "rgba(42,52,68,0.6)"}`,
            boxShadow:    searchFocused ? "0 0 0 1px rgba(0,217,255,0.15)" : "none",
          }}
        >
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5"
            style={{ color: searchFocused ? "#00D9FF" : "#6B7280" }}
          />
          <input
            ref={searchInputRef}
            type="text"
            placeholder="Search tickers, signals…"
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleSearchSubmit();
              }
            }}
            aria-label="Search tickers and signals"
            className="w-full pl-9 pr-12 py-2 bg-transparent text-sm text-white placeholder-[#6B7280] outline-none"
          />
          <kbd
            className="absolute right-3 top-1/2 -translate-y-1/2 px-1.5 py-0.5 text-[10px] font-medium rounded"
            style={{
              color:       "#6B7280",
              background:  "rgba(255,255,255,0.05)",
              border:      "1px solid rgba(42,52,68,0.6)",
            }}
          >
            ⌘K
          </kbd>
        </div>
      </div>

      {/* ── Center: CNS Status ──────────────────────────────────────────── */}
      <div className="flex items-center gap-2 shrink-0">
        {/* WS Connection — LIVE | RECONNECTING | DOWN (24/7 auto-reconnect) */}
        <StatusPill
          bg={wsConnected ? "rgba(16,185,129,0.10)" : wsReconnecting ? "rgba(245,158,11,0.10)" : "rgba(239,68,68,0.10)"}
          border={wsConnected ? "rgba(16,185,129,0.35)" : wsReconnecting ? "rgba(245,158,11,0.35)" : "rgba(239,68,68,0.35)"}
        >
          {wsConnected ? (
            <Wifi className="w-3.5 h-3.5" style={{ color: "#10B981" }} />
          ) : wsReconnecting ? (
            <Wifi className="w-3.5 h-3.5 animate-pulse" style={{ color: "#F59E0B" }} />
          ) : (
            <WifiOff className="w-3.5 h-3.5 animate-pulse" style={{ color: "#EF4444" }} />
          )}
          <span
            className="text-xs font-bold tracking-wider"
            style={{ color: wsConnected ? "#10B981" : wsReconnecting ? "#F59E0B" : "#EF4444" }}
          >
            WS
          </span>
          <span
            className="text-[10px]"
            style={{ color: wsConnected ? "#10B981" : wsReconnecting ? "#F59E0B" : "#EF4444", opacity: 0.8 }}
          >
            {wsConnected ? "LIVE" : wsReconnecting ? "RECONNECTING" : "DOWN"}
          </span>
        </StatusPill>

        {/* Homeostasis Mode Badge */}
        <div
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg"
          style={{
            background: modeStyle.bg,
            border:     `1px solid ${modeStyle.border}`,
          }}
        >
          <div
            className={`w-2 h-2 rounded-full ${mode === "HALTED" ? "animate-pulse" : ""}`}
            style={{
              background: modeStyle.dot,
              boxShadow:  `0 0 6px ${modeStyle.dot}80`,
            }}
          />
          <span
            className="text-xs font-bold tracking-wider"
            style={{ color: modeStyle.text }}
          >
            {mode ?? "NORMAL"}
          </span>
          {positionScale != null && (
            <span className="text-xs text-[#9CA3AF]">{positionScale}x</span>
          )}
        </div>

        {/* Circuit Breaker Icon */}
        <div
          className="p-1.5 rounded-lg transition-all duration-200"
          style={{
            background: circuitBreakerFired
              ? "rgba(239,68,68,0.15)"
              : circuitBreakerArmed
              ? "rgba(16,185,129,0.10)"
              : "rgba(255,255,255,0.04)",
            border: circuitBreakerFired
              ? "1px solid rgba(239,68,68,0.4)"
              : circuitBreakerArmed
              ? "1px solid rgba(16,185,129,0.3)"
              : "1px solid rgba(42,52,68,0.5)",
          }}
          title={
            circuitBreakerFired
              ? `CB fired: ${circuitBreakerFired}`
              : circuitBreakerArmed
              ? "Circuit breaker armed"
              : "Circuit breaker disarmed"
          }
        >
          {circuitBreakerFired ? (
            <ShieldAlert
              className="w-4 h-4 animate-pulse"
              style={{ color: "#EF4444" }}
            />
          ) : (
            <Shield
              className="w-4 h-4"
              style={{ color: circuitBreakerArmed ? "#10B981" : "#6B7280" }}
            />
          )}
        </div>

        {/* Latest Verdict — desktop only */}
        {latestVerdict && (
          <div
            className="hidden lg:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg"
            style={{
              background: "rgba(255,255,255,0.03)",
              border:     "1px solid rgba(42,52,68,0.5)",
            }}
          >
            <Brain className="w-3.5 h-3.5" style={{ color: "#00D9FF" }} />
            <span className="text-xs text-white font-medium font-mono">
              {latestVerdict.symbol}
            </span>
            <span
              className="text-xs font-bold font-mono"
              style={{
                color:
                  latestVerdict.final_direction === "buy"
                    ? "#10B981"
                    : latestVerdict.final_direction === "sell"
                    ? "#EF4444"
                    : "#9CA3AF",
              }}
            >
              {(latestVerdict.final_direction ?? "hold").toUpperCase()}
            </span>
            <span className="text-xs text-[#9CA3AF] font-mono">
              {((latestVerdict.final_confidence ?? 0) * 100).toFixed(0)}%
            </span>
          </div>
        )}
      </div>

      {/* ── Right: Regime + Bell + User ─────────────────────────────────── */}
      <div className="flex items-center gap-2">
        {/* Regime Badge */}
        <RegimeBadge
          regime={marketRegime ?? "GREEN"}
          pct={regimePct}
        />

        {/* Notification Bell */}
        <div className="relative">
          <button
            type="button"
            aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
            onClick={() => {
              setShowNotifications(!showNotifications);
              setShowUserMenu(false);
            }}
            className="relative p-2 rounded-lg transition-all duration-200"
            style={{
              background:   "rgba(255,255,255,0.04)",
              border:       "1px solid rgba(42,52,68,0.5)",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = "rgba(0,217,255,0.3)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(42,52,68,0.5)"; }}
          >
            <Bell className="w-4 h-4 text-[#9CA3AF]" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-[#EF4444] rounded-full text-[9px] font-bold text-white flex items-center justify-center leading-none">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </button>

          {/* Notification dropdown */}
          {showNotifications && (
            <div
              className="absolute right-0 mt-2 w-96 rounded-[8px] overflow-hidden z-50"
              style={{
                background:   "#111827",
                border:       "1px solid rgba(42,52,68,0.8)",
                backdropFilter: "blur(16px)",
                boxShadow:    "0 20px 40px rgba(0,0,0,0.5)",
              }}
            >
              <div
                className="px-4 py-3 flex items-center justify-between"
                style={{ borderBottom: "1px solid rgba(42,52,68,0.5)" }}
              >
                <h3 className="text-sm font-semibold text-white">
                  Notifications{" "}
                  {unreadCount > 0 && (
                    <span style={{ color: "#00D9FF" }}>({unreadCount})</span>
                  )}
                </h3>
                <button
                  type="button"
                  onClick={clearNotifications}
                  className="text-xs transition-colors"
                  style={{ color: "#00D9FF" }}
                  onMouseEnter={(e) => { e.currentTarget.style.opacity = "0.7"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.opacity = "1"; }}
                >
                  Clear all
                </button>
              </div>

              <div className="max-h-80 overflow-y-auto custom-scrollbar">
                {notifications.length === 0 ? (
                  <div className="px-4 py-8 text-center text-sm text-[#6B7280]">
                    No notifications yet
                  </div>
                ) : (
                  notifications.map((notif) => {
                    const evInfo = EVENT_ICONS[notif.type] ?? {
                      icon: Activity,
                      color: "#6B7280",
                    };
                    const Icon = evInfo.icon;
                    return (
                      <div
                        key={notif.id}
                        onClick={() => markRead?.(notif.id)}
                        className="px-4 py-3 cursor-pointer transition-colors hover:bg-white/5"
                        style={{
                          borderBottom: "1px solid rgba(42,52,68,0.3)",
                          background:   !notif.read ? "rgba(0,217,255,0.03)" : "transparent",
                        }}
                      >
                        <div className="flex items-start gap-3">
                          <div
                            className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                            style={{ background: !notif.read ? "rgba(0,217,255,0.08)" : "rgba(255,255,255,0.05)" }}
                          >
                            <Icon className="w-4 h-4" style={{ color: evInfo.color }} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-white leading-snug">
                              {notif.payload?.message ?? notif.type}
                            </p>
                            <p className="text-xs text-[#6B7280] mt-1 font-mono">
                              {formatTimeAgo(notif.timestamp)}
                            </p>
                          </div>
                          {!notif.read && (
                            <div
                              className="w-2 h-2 rounded-full flex-shrink-0 mt-2"
                              style={{ background: "#00D9FF", boxShadow: "0 0 6px rgba(0,217,255,0.5)" }}
                            />
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Menu */}
        <div className="relative">
          <button
            type="button"
            aria-label="User menu"
            onClick={() => {
              setShowUserMenu(!showUserMenu);
              setShowNotifications(false);
            }}
            className="flex items-center gap-2 pl-2 pr-3 py-1.5 rounded-lg transition-all duration-200"
            style={{
              background: "rgba(255,255,255,0.04)",
              border:     "1px solid rgba(42,52,68,0.5)",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = "rgba(0,217,255,0.3)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(42,52,68,0.5)"; }}
          >
            {/* Avatar */}
            <div
              className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-white"
              style={{ background: "linear-gradient(135deg, #00D9FF 0%, #10B981 100%)" }}
            >
              <User className="w-3.5 h-3.5" />
            </div>
            <div className="hidden md:block text-left">
              <div className="text-xs font-semibold text-white leading-tight">
                Embodier
              </div>
              <div className="text-[9px] text-[#6B7280] leading-tight font-mono">
                espen@embodier.ai
              </div>
            </div>
            <ChevronDown className="w-3 h-3 text-[#6B7280]" />
          </button>

          {showUserMenu && (
            <div
              className="absolute right-0 mt-2 w-56 rounded-[8px] overflow-hidden z-50"
              style={{
                background:     "#111827",
                border:         "1px solid rgba(42,52,68,0.8)",
                backdropFilter: "blur(16px)",
                boxShadow:      "0 20px 40px rgba(0,0,0,0.5)",
              }}
            >
              <div
                className="px-4 py-3"
                style={{ borderBottom: "1px solid rgba(42,52,68,0.5)" }}
              >
                <div className="font-semibold text-white text-sm">espen@embodier.ai</div>
                <div className="text-xs text-[#9CA3AF] mt-0.5">Pro Account</div>
              </div>
              <div className="py-1">
                {[
                  { icon: User,     label: "Profile" },
                  { icon: Settings, label: "Settings" },
                  { icon: Activity, label: "API Status" },
                ].map(({ icon: ItemIcon, label }) => (
                  <a
                    key={label}
                    href="#"
                    className="flex items-center gap-3 px-4 py-2.5 text-sm text-white transition-colors hover:bg-white/5"
                  >
                    <ItemIcon className="w-4 h-4 text-[#6B7280]" />
                    {label}
                  </a>
                ))}
              </div>
              <div
                className="py-1"
                style={{ borderTop: "1px solid rgba(42,52,68,0.5)" }}
              >
                <a
                  href="#"
                  className="flex items-center gap-3 px-4 py-2.5 text-sm font-medium transition-colors"
                  style={{ color: "#EF4444" }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(239,68,68,0.08)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                >
                  Sign out
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function formatTimeAgo(ts) {
  const diff = Date.now() - ts;
  if (diff < 60_000)    return "just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return `${Math.floor(diff / 86_400_000)}d ago`;
}
