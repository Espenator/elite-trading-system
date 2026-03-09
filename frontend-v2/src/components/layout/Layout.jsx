// LAYOUT WRAPPER - Embodier.ai Trading Intelligence System
// CNS-aware layout: WebSocket + homeostasis + circuit breaker context for all pages.
// BUG 1 FIX: Sidebar collapsed state is owned here and passed down as props.

import { useState, useEffect, useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';
import NotificationCenter from './NotificationCenter';
import StatusFooter from './StatusFooter';
import { CNSProvider, useCNS } from '../../hooks/useCNS';
import ws from '../../services/websocket';
import { getApiUrl } from '../../config/api';

const API_HEALTH_POLL_MS = 20000;

function LayoutInner() {
  const { wsConnected } = useCNS();

  // BUG 1 FIX: Layout owns the sidebar collapsed state
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  // Footer status: derive from CNS + lightweight API health poll
  const [apiStatus, setApiStatus] = useState('red');

  const handleToggleSidebar = useCallback(() => {
    setSidebarCollapsed(prev => !prev);
  }, []);

  // Lightweight API health check for footer "API Healthy / Down"
  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const res = await fetch(getApiUrl('status'), { method: 'GET' });
        if (!cancelled) setApiStatus(res.ok ? 'green' : 'red');
      } catch {
        if (!cancelled) setApiStatus('red');
      }
    };
    check();
    const id = setInterval(check, API_HEALTH_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
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
          wsStatus={wsConnected ? 'green' : 'red'}
          apiStatus={apiStatus}
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
