// LAYOUT WRAPPER - Embodier.ai Trading Intelligence System
// CNS-aware layout: WebSocket + homeostasis + circuit breaker context for all pages.
// BUG 1 FIX: Sidebar collapsed state is owned here and passed down as props.

import { useState, useEffect, useCallback, useMemo } from 'react';
import { Outlet } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';
import NotificationCenter from './NotificationCenter';
import StatusFooter from './StatusFooter';
import KeyboardShortcuts from '../ui/KeyboardShortcuts';
import { CNSProvider, useCNS } from '../../hooks/useCNS';
import { useApi } from '../../hooks/useApi';
import useKeyboardShortcuts from '../../hooks/useKeyboardShortcuts';
import ws from '../../services/websocket';

function LayoutInner() {
  useKeyboardShortcuts();
  const { wsConnected, wsReconnecting, mode } = useCNS();

  // Lightweight health probe for footer — /healthz (25s timeout; backend can be slow when event loop busy)
  const { data: healthzData } = useApi("healthz", { pollIntervalMs: 20000 });
  const { data: systemData } = useApi("system", { pollIntervalMs: 30000 });
  const { data: indicesData } = useApi("marketIndices", { pollIntervalMs: 30000 });

  // API health from lightweight liveness probe — reliable even when event loop is busy
  const apiHealthy = healthzData?.status === "alive";

  // Derive footer props from live data (system for agentCount/regime; regime may fallback to CNS mode)
  const agentCount = systemData?.activeAgents ?? systemData?.active_agents ?? 0;
  const regime = systemData?.regime ?? mode ?? "GREEN";

  // Build ticker items from market indices data
  const tickerItems = useMemo(() => {
    const raw = indicesData?.indices || indicesData?.marketIndices || indicesData;
    if (!Array.isArray(raw)) return undefined; // let StatusFooter use defaults
    const items = raw
      .filter((e) => e.price != null || e.value != null)
      .map((e) => ({
        symbol: e.id || e.symbol,
        price: e.price ?? e.value ?? "--",
        change: e.changePct != null || e.change != null
          ? `${(e.changePct ?? e.change) >= 0 ? "+" : ""}${Number(e.changePct ?? e.change).toFixed(2)}%`
          : null,
        changeColor: (e.changePct ?? e.change ?? 0) >= 0 ? "green" : "red",
      }));
    return items.length > 0 ? items : undefined;
  }, [indicesData]);

  // BUG 1 FIX: Layout owns the sidebar collapsed state
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const handleToggleSidebar = useCallback(() => {
    setSidebarCollapsed(prev => !prev);
  }, []);

  return (
    <div className="flex min-h-screen bg-dark text-white overflow-hidden">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-cyan-600 focus:text-white focus:rounded">
        Skip to main content
      </a>
      {/* Glass House Sidebar */}
      <Sidebar collapsed={sidebarCollapsed} onToggleCollapse={handleToggleSidebar} />

      {/* Main content area */}
      <div className={`flex-1 flex flex-col overflow-hidden bg-dark min-w-0 transition-all duration-300 ${sidebarCollapsed ? 'ml-0 md:ml-16' : 'ml-0 md:ml-64'}`}>
        {/* Header bar with CNS status */}
        <Header wsConnected={wsConnected} />

        {/* Page content - scrollable */}
        <main id="main-content" role="main" className="flex-1 overflow-y-auto custom-scrollbar p-6 pb-10">
          <Outlet />
        </main>
        <StatusFooter
          wsStatus={wsConnected ? "green" : wsReconnecting ? "amber" : "red"}
          apiStatus={apiHealthy ? "green" : "red"}
          mlStatus={agentCount > 0 ? "green" : "amber"}
          agentCount={agentCount}
          regime={regime}
          tickerItems={tickerItems}
        />
      </div>

      {/* Global notification overlay */}
      <NotificationCenter />
      {/* Keyboard shortcuts help (press ?) */}
      <KeyboardShortcuts />
    </div>
  );
}

export default function Layout() {
  useEffect(() => {
    ws.connect();
    return () => ws.disconnect();
  }, []);

  return (
    <CNSProvider>
      <LayoutInner />
    </CNSProvider>
  );
}
