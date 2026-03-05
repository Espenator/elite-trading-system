// LAYOUT WRAPPER - Embodier.ai Trading Intelligence System
// CNS-aware layout: WebSocket + homeostasis + circuit breaker context for all pages.
// BUG 1 FIX: Sidebar collapsed state is owned here and passed down as props.

import { useState, useEffect, useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';
import NotificationCenter from './NotificationCenter';
import { CNSProvider, useCNS } from '../../hooks/useCNS';
import ws from '../../services/websocket';

function LayoutInner() {
  const { wsConnected } = useCNS();

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
        <main className="flex-1 overflow-y-auto custom-scrollbar p-6">
          <Outlet />
        </main>
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
