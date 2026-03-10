// LAYOUT WRAPPER - Embodier.ai Trading Intelligence System
// CNS-aware layout: WebSocket + homeostasis + circuit breaker context for all pages.
// BUG 1 FIX: Sidebar collapsed state is owned here and passed down as props.
// BUG 2 FIX: StatusFooter now wired to real health data instead of red defaults.

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

  // BUG 2 FIX: Fetch system health for StatusFooter
  const { data: healthData } = useApi('health', { pollIntervalMs: 10000 });

  // Derive StatusFooter props from health + WS state
  const apiStatus = healthData?.status === 'healthy' ? 'green' : healthData ? 'amber' : 'red';
  const wsStatus = wsConnected ? 'green' : 'red';
  const uptimeSeconds = healthData?.event_pipeline?.uptime_seconds || healthData?.signal_engine?.uptime_seconds || 0;
  const uptimeDays = Math.floor(uptimeSeconds / 86400);
  const uptimeHours = Math.floor((uptimeSeconds % 86400) / 3600);
  const agentCount = healthData?.order_executor?.agent_weights ? Object.keys(healthData.order_executor.agent_weights).length : 0;
  const llmFlow = healthData?.event_pipeline?.total_events || 0;
  const conferenceCur = healthData?.council_gate?.councils_passed || 0;
  const conferenceMax = healthData?.council_gate?.councils_invoked || 12;
  const regime = healthData?.signal_engine?.regime || 'UNKNOWN';
  const loadCur = healthData?.order_executor?.max_portfolio_heat || 0;
  const loadMax = 4.0;

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
          llmFlow={llmFlow}
          conferenceCur={conferenceCur}
          conferenceMax={conferenceMax}
          loadCur={loadCur}
          loadMax={loadMax}
          uptimeDays={uptimeDays}
          uptimeHours={uptimeHours}
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
