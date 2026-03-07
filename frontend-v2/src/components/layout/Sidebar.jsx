// EMBODIER TRADER — Sidebar (Aurora Design System)
// V3 CONSOLIDATION: 16 sidebar pages (see V3-ARCHITECTURE.md)
//
// Visual spec (matches mockups exactly):
//   - bg: #111827, border-right: rgba(42,52,68,0.5)
//   - Header: "Embodier.ai" / "Embodier Trader" + "Trading Intelligence" tagline, icon gradient
//   - Section labels: #00D9FF (primary), uppercase tracked, JetBrains Mono
//   - Active item: 3px left cyan bar (#00D9FF) + rgba(0,217,255,0.08) bg
//   - Inactive item hover: rgba(0,217,255,0.05) bg
//   - Icons: 14px (expanded), 18px (collapsed), monochrome → cyan when active
//   - Bottom: "EXTENDED SWARM (N)" + agent count + health dot

import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Bot,
  Zap,
  MessageCircle,
  Link2,
  Brain,
  Search,
  RotateCcw,
  TrendingUp,
  LineChart,
  Shield,
  Crosshair,
  Settings,
  ChevronLeft,
  Sparkles,
  BarChart3,
  Radar,
} from "lucide-react";
import { useApi } from "../../hooks/useApi";

// ── Nav sections ─────────────────────────────────────────────────────────────
const navSections = [
  {
    label: "COMMAND",
    items: [
      { to: "/dashboard",           icon: LayoutDashboard, label: "Intelligence Dashboard" },
      { to: "/agents",              icon: Bot,             label: "Agent Command Center"  },
    ],
  },
  {
    label: "INTELLIGENCE",
    items: [
      { to: "/sentiment",           icon: MessageCircle, label: "Sentiment Intelligence" },
      { to: "/data-sources",        icon: Link2,         label: "Data Sources Manager"   },
      { to: "/signal-intelligence-v3", icon: Radar,      label: "Signal Intelligence"    },
    ],
  },
  {
    label: "ML & ANALYSIS",
    items: [
      { to: "/ml-brain",    icon: Brain,     label: "ML Brain & Flywheel"    },
      { to: "/patterns",    icon: Search,    label: "Screener & Patterns"    },
      { to: "/backtest",    icon: RotateCcw, label: "Backtesting Lab"        },
      { to: "/performance", icon: TrendingUp, label: "Performance Analytics" },
      { to: "/market-regime", icon: BarChart3, label: "Market Regime"        },
    ],
  },
  {
    label: "EXECUTION",
    items: [
      { to: "/trades",         icon: LineChart, label: "Active Trades"    },
      { to: "/risk",           icon: Shield,    label: "Risk Intelligence" },
      { to: "/trade-execution", icon: Crosshair, label: "Trade Execution" },
    ],
  },
  {
    label: "SYSTEM",
    items: [
      { to: "/settings", icon: Settings, label: "Settings" },
    ],
  },
];

// ── Sidebar ──────────────────────────────────────────────────────────────────
export default function Sidebar({ collapsed, onToggleCollapse }) {
  const { data: systemData } = useApi("system", { pollIntervalMs: 30_000 });
  const agentCount = systemData?.activeAgents  ?? "...";
  const swarmTotal = systemData?.totalAgents   ?? agentCount;
  const systemOk   = systemData?.healthy       ?? null;
  const healthOk   = systemData?.healthyAgents ?? null;

  // health indicator colour
  const dotColor =
    systemOk === true  ? "#10B981" :
    systemOk === false ? "#EF4444" :
    "#6B7280";
  const dotGlow =
    systemOk === true  ? "0 0 6px rgba(16,185,129,0.5)" :
    systemOk === false ? "0 0 6px rgba(239,68,68,0.5)"  :
    "none";

  return (
    <aside
      style={{
        background:   "#111827",
        borderRight:  "1px solid rgba(42,52,68,0.5)",
        width:        collapsed ? 64 : 256,
        transition:   "width 0.3s cubic-bezier(0.4,0,0.2,1)",
      }}
      className="fixed left-0 top-0 h-screen flex flex-col z-50 overflow-hidden"
    >
      {/* ── Logo Header ─────────────────────────────────────────────── */}
      <div
        className={`flex items-center h-16 relative transition-all duration-300 ${
          collapsed ? "justify-center px-2" : "justify-between px-4"
        }`}
        style={{ borderBottom: "1px solid rgba(42,52,68,0.5)" }}
      >
        <div className="flex items-center gap-3 min-w-0">
          {/* Icon mark */}
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
            style={{
              background: "linear-gradient(135deg, #00D9FF 0%, #10B981 100%)",
              boxShadow:  "0 0 12px rgba(0,217,255,0.25)",
            }}
          >
            <Sparkles className="w-5 h-5 text-white" />
          </div>

          {!collapsed && (
            <div className="min-w-0">
              <h1 className="text-sm font-bold text-white leading-tight truncate">
                Embodier.ai
              </h1>
              <p
                className="text-[10px] truncate font-mono tracking-wide"
                style={{ color: "rgba(0,217,255,0.6)" }}
              >
                Trading Intelligence
              </p>
            </div>
          )}
        </div>

        {/* Collapse toggle */}
        <button
          onClick={onToggleCollapse}
          aria-expanded={!collapsed}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="rounded-md transition-colors"
          style={{
            position:    collapsed ? "absolute" : "static",
            ...(collapsed ? {
              top:       "50%",
              right:     0,
              transform: "translateY(-50%) translateX(50%)",
              background: "#111827",
              border:    "1px solid rgba(42,52,68,0.5)",
              padding:   "2px",
              zIndex:    10,
            } : {
              padding: "6px",
            }),
          }}
          onMouseEnter={(e) => { e.currentTarget.style.color = "#fff"; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = ""; }}
        >
          <ChevronLeft
            className="w-4 h-4 text-[#6B7280] transition-transform duration-300"
            style={{ transform: collapsed ? "rotate(180deg)" : "none" }}
          />
        </button>
      </div>

      {/* ── Navigation ──────────────────────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto custom-scrollbar py-2 min-h-0">
        {navSections.map((section, sectionIdx) => (
          <div
            key={section.label}
            className={collapsed ? "" : "mb-0.5"}
          >
            {/* Section label (expanded) */}
            {!collapsed && (
              <div className="px-4 pt-3 pb-1">
                <span
                  className="font-mono text-[10px] font-bold tracking-[0.15em] uppercase"
                  style={{ color: "#00D9FF" }}
                >
                  {section.label}
                </span>
              </div>
            )}

            {/* Divider between sections (collapsed) */}
            {collapsed && sectionIdx > 0 && (
              <div
                className="mx-3 my-1.5"
                style={{ borderTop: "1px solid rgba(42,52,68,0.5)" }}
                aria-hidden="true"
              />
            )}

            <ul className={collapsed ? "space-y-0.5 px-1.5" : "space-y-0.5 px-2"}>
              {section.items.map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      title={item.label}
                      className="outline-none"
                    >
                      {({ isActive }) => (
                        <span
                          className={`flex items-center transition-all duration-200 relative ${
                            collapsed
                              ? "justify-center py-3 rounded-lg"
                              : "gap-3 px-3 py-2 rounded-[6px]"
                          }`}
                          style={{
                            background: isActive
                              ? "rgba(0,217,255,0.08)"
                              : "transparent",
                            // Hover is handled by CSS (no onMouseEnter needed — NavLink handles styling)
                          }}
                          onMouseEnter={(e) => {
                            if (!isActive) {
                              e.currentTarget.style.background = "rgba(0,217,255,0.05)";
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (!isActive) {
                              e.currentTarget.style.background = "transparent";
                            }
                          }}
                        >
                          {/* Active left-bar indicator (expanded only) */}
                          {isActive && !collapsed && (
                            <span
                              className="absolute left-0 top-1/2 rounded-r-sm"
                              style={{
                                width:     "3px",
                                height:    "60%",
                                transform: "translateY(-50%)",
                                background: "#00D9FF",
                                boxShadow:  "0 0 8px rgba(0,217,255,0.6)",
                              }}
                            />
                          )}

                          {/* Icon */}
                          <span
                            className="flex-shrink-0 flex items-center justify-center"
                            style={{
                              color: isActive ? "#00D9FF" : "#9CA3AF",
                              filter: isActive
                                ? "drop-shadow(0 0 4px rgba(0,217,255,0.5))"
                                : "none",
                              transition: "color 0.15s, filter 0.15s",
                            }}
                          >
                            <Icon
                              size={collapsed ? 18 : 14}
                              strokeWidth={isActive ? 2.5 : 1.75}
                            />
                          </span>

                          {/* Label */}
                          {!collapsed && (
                            <span
                              className="text-[13px] font-medium truncate transition-colors duration-150"
                              style={{ color: isActive ? "#F9FAFB" : "#9CA3AF" }}
                            >
                              {item.label}
                            </span>
                          )}
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

      {/* ── Bottom: System Status ────────────────────────────────────── */}
      <div
        style={{ borderTop: "1px solid rgba(42,52,68,0.5)" }}
        className={collapsed ? "p-2" : "p-3"}
      >
        {collapsed ? (
          /* Collapsed: just the health dot */
          <div
            className="flex justify-center"
            title={`System: ${agentCount} agents${systemOk === true ? " · All healthy" : systemOk === false ? " · Issues detected" : ""}`}
          >
            <div
              className="w-2.5 h-2.5 rounded-full animate-pulse"
              style={{ background: dotColor, boxShadow: dotGlow }}
            />
          </div>
        ) : (
          /* Expanded: full system info block */
          <div
            className="rounded-[6px] p-2.5"
            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(42,52,68,0.4)" }}
          >
            {/* Top row */}
            <div className="flex items-center justify-between mb-1.5">
              <span
                className="font-mono text-[10px] font-bold uppercase tracking-[0.12em]"
                style={{ color: "#9CA3AF" }}
              >
                EXTENDED SWARM
                {swarmTotal !== "..." && (
                  <span style={{ color: "#00D9FF" }}> ({swarmTotal})</span>
                )}
              </span>
              <div
                className="w-2 h-2 rounded-full animate-pulse"
                style={{ background: dotColor, boxShadow: dotGlow }}
              />
            </div>

            {/* Bottom row */}
            <div className="flex items-center justify-between">
              <span
                className="font-mono text-[10px]"
                style={{ color: "#6B7280" }}
              >
                {agentCount !== "..." ? (
                  <>
                    <span style={{ color: "#F9FAFB" }}>{agentCount}</span> Agents
                  </>
                ) : (
                  "Loading…"
                )}
              </span>
              <span
                className="font-mono text-[10px] font-semibold"
                style={{
                  color:
                    systemOk === true
                      ? "#10B981"
                      : systemOk === false
                      ? "#EF4444"
                      : "#9CA3AF",
                }}
              >
                {systemOk === true
                  ? `${healthOk ?? agentCount} OK`
                  : systemOk === false
                  ? "ERR"
                  : "…"}
              </span>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
