// LAYOUT WRAPPER - Embodier.ai Trading Intelligence System
// CNS-aware layout: WebSocket + homeostasis + circuit breaker context for all pages.
// BUG 1 FIX: Sidebar collapsed state is owned here and passed down as props.

import { useState, useEffect, useCallback, useMemo, Component } from 'react';
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

/**
 * Full-page fallback when CNSProvider crashes — keeps app usable.
 * Shows a friendly message with retry button instead of blank screen.
 */
function LayoutFallback() {
  return (
    <div className="flex min-h-screen bg-dark text-white items-center justify-center">
      <div className="text-center max-w-lg p-8">
        <h1 className="text-2xl font-bold text-red-400 mb-4">System Initializing...</h1>
        <p className="text-gray-400 mb-4">
          The trading system is starting up or the backend is offline.
        </p>
        <p className="text-gray-500 text-sm mb-6">
          Start the backend: <code className="bg-gray-800 px-2 py-1 rounded">cd backend && python run_server.py</code>
        </p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-white transition-colors"
        >
          Retry
        </button>
      </div>
    </div>
  );
}

/**
 * Error boundary specifically for the CNS system — renders LayoutFallback
 * instead of killing the entire app when CNSProvider throws.
 */
class CNSErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[CNSErrorBoundary] CNS system crashed — showing fallback:', error, errorInfo);
    try {
      fetch('/api/v1/system/frontend-errors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          component: 'CNSProvider',
          error: error.message,
          stack: error.stack?.slice(0, 500),
          timestamp: new Date().toISOString(),
        }),
      }).catch(() => {});
    } catch {}
  }

  render() {
    if (this.state.hasError) {
      return <LayoutFallback />;
    }
    return this.props.children;
  }
}

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
    <CNSErrorBoundary>
      <CNSProvider>
        <LayoutInner />
      </CNSProvider>
    </CNSErrorBoundary>
  );
}
