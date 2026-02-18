// LAYOUT WRAPPER - Embodier.ai Glass House Intelligence System
// OLEH: This wraps every page. Sidebar left, Header top, content below.
// The dark gradient background is the Glass House foundation.
// All scrolling happens inside <main>, not on the body.

import { Outlet } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';

export default function Layout() {
  return (
    <div className="flex min-h-screen bg-dark text-white overflow-hidden">
      {/* Glass House Sidebar */}
      <Sidebar />

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header bar */}
        <Header />

        {/* Page content - scrollable */}
        <main className="flex-1 overflow-y-auto custom-scrollbar p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
