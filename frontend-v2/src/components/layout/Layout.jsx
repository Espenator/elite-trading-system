// LAYOUT WRAPPER - Embodier.ai Trading Intelligence System
// CNS-aware layout: WebSocket + homeostasis + circuit breaker context for all pages.
// BUG 1 FIX: Sidebar collapsed state is owned here and passed down as props.

import { useState, useEffect, useCallback, useMemo } from 'react';
import { Outlet } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';
import NotificationCenter from './NotificationCenter';
import StatusFooter from './StatusFooter';
import { CNSProvider, useCNS } from '../../hooks/useCNS';
import { useApi } from '../../hooks/useApi';
import ws from '../../services/websocket';

function LayoutInner() {
  const { wsConnected, mode } = useCNS();

  // Poll system status + market indices for the footer bar
  const { data: systemData } = useApi("system", { pollIntervalMs: 15000 });
  const { data: indicesData } = useApi("marketIndices", { pollIntervalMs: 30000 });

  // Track API health — if system endpoint responds, API is up
  const [apiHealthy, setApiHealthy] = useState(false);
  useEffect(() => {
    setApiHealthy(!!systemData);
  }, [systemData]);

  // Derive footer props from live data
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
      {/* Glass House Sidebar */}
      <Sidebar collapsed={sidebarCollapsed} onToggleCollapse={handleToggleSidebar} />

      {/* Main content area */}
      <div className={`flex-1 flex flex-col overflow-hidden bg-dark min-w-0 transition-all duration-300 ${sidebarCollapsed ? 'ml-16' : 'ml-64'}`}>
        {/* Header bar with CNS status */}
        <Header wsConnected={wsConnected} />

        {/* Page content - scrollable */}
        <main className="flex-1 overflow-y-auto custom-scrollbar p-6 pb-10">
          <Outlet />
        </main>
        <StatusFooter
          wsStatus={wsConnected ? "green" : "red"}
          apiStatus={apiHealthy ? "green" : "red"}
          mlStatus={agentCount > 0 ? "green" : "amber"}
          agentCount={agentCount}
          regime={regime}
          tickerItems={tickerItems}
        />
      </div>

      {/* Global notification overlay */}
      <NotificationCenter />
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
