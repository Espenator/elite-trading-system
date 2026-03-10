// LAYOUT WRAPPER - Embodier.ai Trading Intelligence System
// CNS-aware layout: WebSocket + homeostasis + circuit breaker context for all pages.
// BUG 1 FIX: Sidebar collapsed state is owned here and passed down as props.
// BUG 2 FIX: StatusFooter now wired to real API data instead of red defaults.

import { useState, useEffect, useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';
import NotificationCenter from './NotificationCenter';
import StatusFooter from './StatusFooter';
import { CNSProvider, useCNS } from '../../hooks/useCNS';
import { useApi } from '../../hooks/useApi';
import ws from '../../services/websocket';

function LayoutInner() {
  const { wsConnected } = useCNS();

  // BUG 1 FIX: Layout owns the sidebar collapsed state
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const handleToggleSidebar = useCallback(() => {
    setSidebarCollapsed(prev => !prev);
  }, []);

  // BUG 2 FIX: Fetch API status + system data for StatusFooter
  const { data: statusData } = useApi('status', { pollIntervalMs: 10000 });
  const { data: systemData } = useApi('system', { pollIntervalMs: 15000 });
  const { data: regimeData } = useApi('openclawRegime', { pollIntervalMs: 15000 });

  // Derive StatusFooter props
  const apiStatus = statusData?.status === 'ok' ? 'green' : statusData ? 'amber' : 'red';
  const wsStatus = wsConnected ? 'green' : 'red';
  const regime = regimeData?.regime || systemData?.regime || 'UNKNOWN';
  // Agent count from system/agents data
  const agentCount = systemData?.modules ? Object.keys(systemData.modules).length : 0;

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
          apiStatus={apiStatus}
          wsStatus={wsStatus}
          agentCount={agentCount}
          regime={regime}
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
