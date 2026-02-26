// LAYOUT WRAPPER - Embodier.ai Glass House Intelligence System
// OLEH: This wraps every page. Sidebar left, Header top, content below.
// WebSocket: connect on mount, disconnect on unmount; Header shows connection status.

import { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';
import ws from '../../services/websocket';

export default function Layout() {
  const [wsConnected, setWsConnected] = useState(false);

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
      <Sidebar />

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden bg-dark ml-64 min-w-0">
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
