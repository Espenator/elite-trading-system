// LAYOUT WRAPPER - Embodier.ai Glass House Intelligence System
// OLEH: This wraps every page. Sidebar left, Header top, content below.
// WebSocket: connect on mount, disconnect on unmount; Header shows connection status.

import { useState, useEffect, useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';
import ws from '../../services/websocket';

export default function Layout() {
  const [wsConnected, setWsConnected] = useState(false);
  // BUG 1 FIX: Track sidebar collapsed state for dynamic margin
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const handleSidebarCollapse = useCallback((collapsed) => {
    setSidebarCollapsed(collapsed);
  }, []);

  useEffect(() => {
    ws.connect();
    return () => ws.disconnect();
  }, []);

  useEffect(() => {
    const unsub = ws.on('*', (ev) => {
      if (ev.type === 'connected') setWsConnected(true);
      if (ev.type === 'disconnected') setWsConnected(false);
    });
    return unsub;
  }, []);

  return (
    <div className="flex min-h-screen bg-dark text-white overflow-hidden">
      {/* Glass House Sidebar */}
      <Sidebar onCollapse={handleSidebarCollapse} />

      {/* Main content area */}
      {/* BUG 1 FIX: Dynamic margin that responds to sidebar collapsed state */}
      <div className={`flex-1 flex flex-col overflow-hidden bg-dark min-w-0 transition-all duration-300 ${sidebarCollapsed ? 'ml-16' : 'ml-64'}`}>
        {/* Header bar */}
        <Header wsConnected={wsConnected} />

        {/* Page content - scrollable */}
        <main className="flex-1 overflow-y-auto custom-scrollbar p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
