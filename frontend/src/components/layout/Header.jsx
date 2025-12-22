import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faBars, faSun, faMoon, faBell, faCog, faSignOutAlt, 
  faKey, faChevronDown, faCheckCircle, faExclamationCircle, 
  faInfoCircle, faTimesCircle
} from '@fortawesome/free-solid-svg-icons';
import { useTheme } from '../../context/ThemeContext';

export default function Header() {
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const [showNotificationsDropdown, setShowNotificationsDropdown] = useState(false);
  const userDropdownRef = useRef(null);
  const notificationsDropdownRef = useRef(null);

  // Sample notifications data
  const notifications = [
    { id: 1, type: 'success', title: 'Order Filled', message: 'TSLA buy order for 100 shares executed at $150.25', time: '2 minutes ago' },
    { id: 2, type: 'info', title: 'Signal Generated', message: 'New T1 signal detected for MSFT with 92% confidence', time: '15 minutes ago' },
    { id: 3, type: 'warning', title: 'Risk Alert', message: 'Portfolio exposure approaching limit threshold', time: '1 hour ago' },
    { id: 4, type: 'success', title: 'Position Closed', message: 'GOOG position closed with +$250.00 profit', time: '2 hours ago' },
    { id: 5, type: 'error', title: 'Connection Issue', message: 'Temporary connection loss to data feed. Reconnected.', time: '3 hours ago' },
  ];

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (userDropdownRef.current && !userDropdownRef.current.contains(event.target)) {
        setShowUserDropdown(false);
      }
      if (notificationsDropdownRef.current && !notificationsDropdownRef.current.contains(event.target)) {
        setShowNotificationsDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleUserMenuClick = (action) => {
    setShowUserDropdown(false);
    switch (action) {
      case 'settings':
        navigate('/settings');
        break;
      case 'change-password':
        // Navigate to change password page or show modal
        // TODO: Implement change password functionality
        break;
      case 'sign-out':
        // Handle sign out logic
        // TODO: Implement sign out functionality
        break;
      default:
        break;
    }
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'success':
        return faCheckCircle;
      case 'warning':
        return faExclamationCircle;
      case 'error':
        return faTimesCircle;
      default:
        return faInfoCircle;
    }
  };

  const getNotificationColor = (type) => {
    switch (type) {
      case 'success':
        return 'text-green-600 dark:text-green-400';
      case 'warning':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'error':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-blue-600 dark:text-blue-400';
    }
  };

  return (
    <header className="h-16 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-6 relative z-50">
      <div className="flex items-center space-x-4">
        <button className="lg:hidden text-gray-600 dark:text-gray-300">
          <FontAwesomeIcon icon={faBars} />
        </button>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
          Elite Trading System
        </h1>
      </div>

      <div className="flex items-center space-x-4">
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          aria-label="Toggle theme"
        >
          <FontAwesomeIcon icon={theme === 'dark' ? faSun : faMoon} />
        </button>

        {/* Notifications */}
        <div className="relative" ref={notificationsDropdownRef}>
          <button 
            onClick={() => setShowNotificationsDropdown(!showNotificationsDropdown)}
            className="p-2 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors relative"
            aria-label="Notifications"
          >
            <FontAwesomeIcon icon={faBell} />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>

          {/* Notifications Dropdown */}
          {showNotificationsDropdown && (
            <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Notifications</h3>
              </div>
              <div className="max-h-96 overflow-y-auto">
                {notifications.map((notification) => (
                  <div
                    key={notification.id}
                    className="p-4 border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
                  >
                    <div className="flex items-start space-x-3">
                      <FontAwesomeIcon 
                        icon={getNotificationIcon(notification.type)} 
                        className={`mt-0.5 ${getNotificationColor(notification.type)}`}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {notification.title}
                        </p>
                        <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                          {notification.message}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                          {notification.time}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="p-3 border-t border-gray-200 dark:border-gray-700 text-center">
                <button className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium">
                  View All Notifications
                </button>
              </div>
            </div>
          )}
        </div>

        {/* User Avatar */}
        <div className="relative" ref={userDropdownRef}>
          <button
            onClick={() => setShowUserDropdown(!showUserDropdown)}
            className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center cursor-pointer hover:opacity-80 transition-opacity"
          >
            <span className="text-white text-sm font-medium">LB</span>
          </button>

          {/* User Dropdown */}
          {showUserDropdown && (
            <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="py-1">
                <button
                  onClick={() => handleUserMenuClick('settings')}
                  className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2 transition-colors"
                >
                  <FontAwesomeIcon icon={faCog} className="w-4 h-4" />
                  <span>Settings</span>
                </button>
                <button
                  onClick={() => handleUserMenuClick('change-password')}
                  className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2 transition-colors"
                >
                  <FontAwesomeIcon icon={faKey} className="w-4 h-4" />
                  <span>Change Password</span>
                </button>
                <div className="border-t border-gray-200 dark:border-gray-700 my-1"></div>
                <button
                  onClick={() => handleUserMenuClick('sign-out')}
                  className="w-full px-4 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center space-x-2 transition-colors"
                >
                  <FontAwesomeIcon icon={faSignOutAlt} className="w-4 h-4" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
