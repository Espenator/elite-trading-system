// This is the main navigation for all 15 sidebar pages
// Organized by section: Command, Intelligence, ML & Analysis, Execution, System
// Every page maps 1:1 to a backend module per the architecture doc
// V3 CONSOLIDATION: 15 sidebar pages (see V3-ARCHITECTURE.md)

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

// ----------- NAV SECTIONS -----------
// Grouped logically so Espen can find anything in 2 clicks
const navSections = [
  {
    label: "COMMAND",
    items: [
      {
        to: "/dashboard",
        icon: LayoutDashboard,
        label: "Intelligence Dashboard",
      },
      { to: "/agents", icon: Bot, label: "Agent Command Center" },
    ],
  },
  {
    label: "INTELLIGENCE",
    items: [
      { to: "/signals", icon: Zap, label: "Signal Intelligence" },
      {
        to: "/sentiment",
        icon: MessageCircle,
        label: "Sentiment Intelligence",
      },
      { to: "/data-sources", icon: Link2, label: "Data Sources Manager" },
      { to: "/signal-intelligence-v3", icon: Radar, label: "Signal Intelligence V3" },
    ],
  },
  {
    label: "ML & ANALYSIS",
    items: [
      { to: "/ml-brain", icon: Brain, label: "ML Brain & Flywheel" },
      { to: "/patterns", icon: Search, label: "Screener & Patterns" },
      { to: "/backtest", icon: RotateCcw, label: "Backtesting Lab" },
      { to: "/performance", icon: TrendingUp, label: "Performance Analytics" },
      { to: "/market-regime", icon: BarChart3, label: "Market Regime" },
    ],
  },
  {
    label: "EXECUTION",
    items: [
      { to: "/trades", icon: LineChart, label: "Active Trades" },
      { to: "/risk", icon: Shield, label: "Risk Intelligence" },
      { to: "/trade-execution", icon: Crosshair, label: "Trade Execution" },
            { to: "/alignment-engine", icon: Sparkles, label: "Alignment Engine" },
    ],
  },
  {
    label: "SYSTEM",
    items: [{ to: "/settings", icon: Settings, label: "Settings" }],
  },
];

// BUG 1 FIX: Accept collapsed/onToggleCollapse props from Layout
// BUG 3 FIX: Removed useLocation - now using React Router's NavLink isActive
// BUG 6 FIX: Added useApi('system') for live system status
export default function Sidebar({ collapsed, onToggleCollapse }) {
  // BUG 6 FIX: Wire system status to real API instead of hardcoded values
  const { data: systemData } = useApi('system', { pollIntervalMs: 30000 });
  const agentCount = systemData?.activeAgents ?? '...';
  const systemOk = systemData?.healthy ?? null;

  return (
    <aside
      className={`fixed left-0 top-0 h-screen ${
        collapsed ? "w-16" : "w-64"
      } bg-surface border-r border-secondary/50 flex flex-col transition-all duration-300 z-50`}
    >
      {/* Logo + Collapse */}
      <div
        className={`flex items-center h-16 border-b border-secondary/50 relative transition-all duration-300 ${
          collapsed ? "justify-center gap-1 px-2 py-3" : "justify-between px-4"
        }`}
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary to-success flex items-center justify-center shrink-0">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <h1 className="text-sm font-bold text-white leading-tight truncate">
                Embodier.ai
              </h1>
              <p className="text-[10px] text-primary/70 truncate">
                Trading Intelligence
              </p>
            </div>
          )}
        </div>
        {/* BUG 2 FIX: Dynamic title based on collapsed state */}
        {/* BUG 5 FIX: Added aria-expanded and aria-label for accessibility */}
        <button
          onClick={onToggleCollapse}
          className={`rounded-md text-secondary hover:text-white transition-colors
            ${collapsed ? "p-0.5 absolute top-1/2 -translate-y-1/2 right-0 translate-x-1/2 border border-secondary/50 bg-surface" : "p-1.5"}`}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!collapsed}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <ChevronLeft className={`w-4 h-4 ${collapsed ? "rotate-180" : ""}`} />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto custom-scrollbar py-2 min-h-0">
        {navSections.map((section, sectionIndex) => (
          <div key={section.label} className={collapsed ? "" : "mb-1"}>
            {!collapsed && (
              <div className="px-4 py-2">
                <span className="text-xs font-bold text-primary tracking-widest uppercase">
                  {section.label}
                </span>
              </div>
            )}
            {/* BUG 4 FIX: aria-hidden now has explicit "true" value */}
            {collapsed && sectionIndex > 0 && (
              <div
                className="mx-3 my-1.5 border-t border-secondary/40"
                aria-hidden="true"
              />
            )}
            <ul
              className={collapsed ? "space-y-0.5 px-1.5" : "space-y-0.5 px-2"}
            >
              {/* BUG 3 FIX: Using React Router's isActive from NavLink callback */}
              {section.items.map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.to} className={`${collapsed ? "mx-0.5" : ""}`}>
                    <NavLink
                      to={item.to}
                      title={item.label}
                      className={({ isActive }) =>
                        `flex items-center transition-all duration-200 group outline-none ${
                          collapsed
                            ? `justify-center py-3 rounded-lg ${
                                isActive
                                  ? "bg-primary/15 text-primary"
                                  : "text-white hover:text-white hover:bg-secondary/20"
                              }`
                            : `gap-3 px-3 py-2.5 rounded-lg ${
                                isActive
                                  ? "bg-primary/30 text-primary"
                                  : "text-white hover:text-white hover:bg-primary/10"
                              }`
                        }`
                      }
                    >
                      {({ isActive }) => (
                        <>
                          <span
                            className={`flex-shrink-0 flex items-center justify-center ${isActive && !collapsed ? "drop-shadow-[0_0_6px_rgba(6,182,212,0.4)]" : ""}`}
                          >
                            <Icon
                              className={collapsed ? "w-5 h-5" : "w-4 h-4"}
                              strokeWidth={2}
                            />
                          </span>
                          {!collapsed && (
                            <span
                              className={`text-sm font-medium truncate ${isActive ? "text-white" : ""}`}
                            >
                              {item.label}
                            </span>
                          )}
                        </>
                      )}
                    </NavLink>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Bottom: System Status - BUG 6 FIX: wired to /api/v1/system */}
      <div
        className={`border-t border-secondary/50 ${collapsed ? "p-2" : "p-3"}`}
      >
        {collapsed ? (
          <div
            className="flex justify-center"
            title={`System status: ${agentCount} agents running${systemOk === true ? ', all healthy' : systemOk === false ? ', issues detected' : ''}`}
          >
            <div className={`w-2.5 h-2.5 rounded-full ${
              systemOk === true ? 'bg-success' : systemOk === false ? 'bg-danger' : 'bg-secondary'
            } animate-pulse ring-2 ${
              systemOk === true ? 'ring-success/30' : systemOk === false ? 'ring-danger/30' : 'ring-secondary/30'
            }`} />
          </div>
        ) : (
          <div className="bg-secondary/10 rounded-lg p-2.5">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] text-secondary font-medium uppercase tracking-wider">
                System
              </span>
              <div className={`w-2 h-2 rounded-full ${
                systemOk === true ? 'bg-success' : systemOk === false ? 'bg-danger' : 'bg-secondary'
              } animate-pulse`} />
            </div>
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-secondary">{agentCount} Agents</span>
              <span className={`font-medium ${
                systemOk === true ? 'text-success' : systemOk === false ? 'text-danger' : 'text-secondary'
              }`}>
                {systemOk === true ? 'OK' : systemOk === false ? 'ERR' : '...'}
              </span>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
