import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faUser, faEnvelope, faPhone, faCalendar, faCreditCard } from '@fortawesome/free-solid-svg-icons';

export default function Account() {
  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">My Account</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">View and manage your account information</p>
      </div>

      {/* Profile Card */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center space-x-4">
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
            <span className="text-white text-2xl font-bold">LB</span>
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Leon Basil</h2>
            <p className="text-gray-600 dark:text-gray-400">Professional Trader</p>
          </div>
        </div>
      </div>

      {/* Account Details */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Account Details</h2>
        </div>
        <div className="p-6 space-y-4">
          <div className="flex items-center space-x-3">
            <FontAwesomeIcon icon={faEnvelope} className="text-gray-400 w-5" />
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Email</p>
              <p className="text-gray-900 dark:text-white font-medium">leon.basil@trading.com</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <FontAwesomeIcon icon={faPhone} className="text-gray-400 w-5" />
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Phone</p>
              <p className="text-gray-900 dark:text-white font-medium">+1 (555) 123-4567</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <FontAwesomeIcon icon={faCalendar} className="text-gray-400 w-5" />
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Member Since</p>
              <p className="text-gray-900 dark:text-white font-medium">January 2024</p>
            </div>
          </div>
        </div>
      </div>

      {/* Subscription */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Subscription</h2>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">Elite Pro Plan</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">$299/month • Billed monthly</p>
            </div>
            <span className="px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 rounded-full text-sm font-medium">
              Active
            </span>
          </div>
          <div className="flex items-center space-x-3 text-gray-600 dark:text-gray-400">
            <FontAwesomeIcon icon={faCreditCard} className="w-5" />
            <span className="text-sm">Next billing date: Dec 27, 2025</span>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <button className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors">
          <p className="font-medium text-blue-900 dark:text-blue-300">Edit Profile</p>
        </button>
        <button className="p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg hover:bg-purple-100 dark:hover:bg-purple-900/30 transition-colors">
          <p className="font-medium text-purple-900 dark:text-purple-300">Change Password</p>
        </button>
        <button className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors">
          <p className="font-medium text-red-900 dark:text-red-300">Sign Out</p>
        </button>
      </div>
    </div>
  );
}

