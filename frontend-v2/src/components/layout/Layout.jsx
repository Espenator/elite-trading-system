// LAYOUT WRAPPER - Embodier.ai Trading Intelligence System
// CNS-aware layout: WebSocket + homeostasis + circuit breaker context for all pages.
// BUG 1 FIX: Sidebar collapsed state is owned here and passed down as props.

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Outlet } from 'react-router-dom';
import { toast } from 'react-toastify';
import Header from './Header';
import Sidebar from './Sidebar';
import NotificationCenter from './NotificationCenter';
import StatusFooter from './StatusFooter';
import CommandPalette from '../ui/CommandPalette';
import { CNSProvider, useCNS } from '../../hooks/useCNS';
import { useApi } from '../../hooks/useApi';
import { SIDEBAR_ROUTES } from '../ui/CommandPalette';
import ws from '../../services/websocket';

function LayoutInner() {
  const { wsConnected, wsState = 'disconnected', mode } = useCNS();
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const prevApiHealthy = useRef(null);

  // Poll system status + market indices for the footer bar
  const { data: systemData } = useApi("system", { pollIntervalMs: 15000 });
  const { data: indicesData } = useApi("marketIndices", { pollIntervalMs: 30000 });

  // Track API health — if system endpoint responds, API is up
  const [apiHealthy, setApiHealthy] = useState(false);
  useEffect(() => {
    const next = !!systemData;
    if (prevApiHealthy.current === false && next) {
      toast.success("API connection restored", { autoClose: 4000 });
    }
    if (prevApiHealthy.current === true && !next && systemData !== undefined) {
      toast.warning("API connection lost", { autoClose: 6000 });
    }
    prevApiHealthy.current = next;
    setApiHealthy(next);
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

  // Keyboard: Ctrl+K command palette, Escape close modals, Ctrl+1–9 sidebar nav
  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === "Escape") {
        setCommandPaletteOpen(false);
        return;
      }
      const isMac = /Mac|iPod|iPhone|iPad/.test(navigator.platform);
      const mod = isMac ? e.metaKey : e.ctrlKey;
      if (!mod) return;
      if (e.key === "k") {
        e.preventDefault();
        setCommandPaletteOpen((open) => !open);
        return;
      }
      const num = e.key >= "1" && e.key <= "9" ? parseInt(e.key, 10) : null;
      if (num !== null && SIDEBAR_ROUTES[num - 1]) {
        e.preventDefault();
        window.location.href = SIDEBAR_ROUTES[num - 1].path;
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const wsFooterStatus =
    wsState === "connected" ? "green" : wsState === "reconnecting" || wsState === "connecting" ? "amber" : "red";

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
        <CommandPalette open={commandPaletteOpen} onClose={() => setCommandPaletteOpen(false)} />
        <StatusFooter
          wsStatus={wsFooterStatus}
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
