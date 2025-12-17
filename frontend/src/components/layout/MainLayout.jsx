import { useState } from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faChartLine, faExchangeAlt, faThLarge, faBrain, faChartBar,
  faSearch, faHistory, faCog, faShieldAlt, faChessKnight,
  faChevronLeft, faChevronRight
} from '@fortawesome/free-solid-svg-icons';
import Header from './Header';
import Footer from './Footer';

const menuItems = [
  { path: '/dashboard', icon: faChartLine, label: 'Dashboard' },
  { path: '/trade', icon: faExchangeAlt, label: 'Trade Execution' },
  { path: '/portfolio', icon: faThLarge, label: 'Portfolio Heatmap' },
  { path: '/model-training', icon: faBrain, label: 'Model Training & Metrics' },
  { path: '/performance', icon: faChartBar, label: 'Performance Analytics' },
  { path: '/screener', icon: faSearch, label: 'Screener Results' },
  { path: '/order-history', icon: faHistory, label: 'Order History & Backtest' },
  { path: '/risk-config', icon: faShieldAlt, label: 'Risk Configuration' },
  { path: '/strategy', icon: faChessKnight, label: 'Strategy Settings' },
  { path: '/settings', icon: faCog, label: 'Settings' },
];

export default function MainLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      {/* Sidebar */}
      <aside className={`${sidebarCollapsed ? 'w-20' : 'w-64'} bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-all duration-300 flex flex-col`}>
        {/* Logo */}
        <div className="h-16 flex items-center justify-center border-b border-gray-200 dark:border-gray-700">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <FontAwesomeIcon icon={faChartLine} className="text-white text-xl" />
          </div>
          {!sidebarCollapsed && (
            <span className="ml-3 text-lg font-bold text-gray-900 dark:text-white">Elite Trader</span>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-4">
          <ul className="space-y-1 px-3">
            {menuItems.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center px-3 py-2.5 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`
                  }
                >
                  <FontAwesomeIcon icon={item.icon} className="w-5 h-5" />
                  {!sidebarCollapsed && <span className="ml-3 text-sm font-medium">{item.label}</span>}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* Collapse Button */}
        <div className="border-t border-gray-200 dark:border-gray-700 p-4">
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="w-full flex items-center justify-center px-3 py-2 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <FontAwesomeIcon icon={sidebarCollapsed ? faChevronRight : faChevronLeft} />
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <Header />

        {/* Page Content with Footer */}
        <main className="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900">
          <Outlet />
          {/* Footer - scrolls with content */}
          <Footer />
        </main>
      </div>
    </div>
  );
}

