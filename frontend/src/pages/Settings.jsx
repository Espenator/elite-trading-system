import { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faUser, faKey, faShieldAlt, faChessKnight, faBell, faPalette, 
  faPlug, faTrash, faSave, faCopy
} from '@fortawesome/free-solid-svg-icons';
import { useTheme } from '../context/ThemeContext';

export default function Settings() {
  const { theme, toggleTheme } = useTheme();
  const [darkMode, setDarkMode] = useState(theme === 'dark');
  const [autoSave, setAutoSave] = useState(true);
  const [realtimeUpdates, setRealtimeUpdates] = useState(true);
  const [tradeAlerts, setTradeAlerts] = useState(true);
  const [marketEvents, setMarketEvents] = useState(false);
  const [systemStatus, setSystemStatus] = useState(true);
  const [emailNotifications, setEmailNotifications] = useState(false);
  const [riskShield, setRiskShield] = useState(true);

  const apiKeys = [
    { id: 'key1', service: 'Alpaca Trading', expiration: '2024-12-31', status: 'Active' },
    { id: 'key2', service: 'Finviz Elite', expiration: '2025-06-15', status: 'Active' },
    { id: 'key3', service: 'UnusualWhales', expiration: '2024-10-01', status: 'Expired' },
  ];

  const handleThemeToggle = () => {
    setDarkMode(!darkMode);
    toggleTheme();
  };

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">Configure your Elite Trading System environment.</p>
      </div>

      {/* Account Settings */}
      <section className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <FontAwesomeIcon icon={faUser} className="text-blue-600 mr-3" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Account Settings</h2>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Manage your profile, display preferences, and general system settings.</p>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Leon Basil</label>
            <input
              type="text"
              value="Leon Basil"
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white"
              readOnly
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">leon.basil@trading.com</label>
            <input
              type="email"
              value="leon.basil@trading.com"
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white"
              readOnly
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Timezone</label>
            <select className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white">
              <option>UTC-05:00 (Eastern Time US & Canada)</option>
              <option>UTC-08:00 (Pacific Time)</option>
              <option>UTC+00:00 (GMT)</option>
            </select>
          </div>
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">Dark Mode</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Toggle between light and dark themes.</p>
            </div>
            <button
              onClick={handleThemeToggle}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                darkMode ? 'bg-blue-600' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  darkMode ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">Show Real-time Updates</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Enable/disable live data streaming and chart updates.</p>
            </div>
            <button
              onClick={() => setRealtimeUpdates(!realtimeUpdates)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                realtimeUpdates ? 'bg-blue-600' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  realtimeUpdates ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">Enable Auto-Save Strategies</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Automatically save changes to your trading strategies.</p>
            </div>
            <button
              onClick={() => setAutoSave(!autoSave)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                autoSave ? 'bg-blue-600' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  autoSave ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>
      </section>

      {/* API Keys */}
      <section className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <FontAwesomeIcon icon={faKey} className="text-purple-600 mr-3" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">API Keys</h2>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Manage your API keys for broker connections and data feeds.</p>
        </div>
        <div className="p-6">
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Current API Key</label>
            <div className="flex items-center space-x-2">
              <input
                type="password"
                value="ets_sk_xxxx_xxxxx"
                className="flex-1 px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white"
                readOnly
              />
              <button className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600">
                <FontAwesomeIcon icon={faCopy} />
              </button>
            </div>
          </div>

          <button className="mb-6 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Generate New API Key
          </button>

          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Existing API Keys</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Key ID</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Service</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Expiration</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {apiKeys.map((key) => (
                  <tr key={key.id}>
                    <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">{key.id}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{key.service}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{key.expiration}</td>
                    <td className="px-4 py-3 text-sm">
                      <button className="text-red-600 hover:text-red-800">Revoke</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Risk Limits */}
      <section className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <FontAwesomeIcon icon={faShieldAlt} className="text-red-600 mr-3" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Risk Limits</h2>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Define and adjust your global trading risk parameters.</p>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Daily Loss Limit</label>
            <input
              type="number"
              defaultValue="500.00"
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Maximum acceptable loss in a trading day.</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Max Position Size</label>
            <input
              type="number"
              defaultValue="100"
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Maximum number of shares/contracts per position.</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Max Drawdown Threshold</label>
            <input
              type="number"
              defaultValue="0.05"
              step="0.01"
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Percentage drawdown from peak before automatic pause.</p>
          </div>
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">Enable RiskShield</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Activate system-wide risk monitoring and automatic enforcement.</p>
            </div>
            <button
              onClick={() => setRiskShield(!riskShield)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                riskShield ? 'bg-blue-600' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  riskShield ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
          <button className="w-full mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Go to Risk Configuration →
          </button>
        </div>
      </section>

      {/* Strategy Settings */}
      <section className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <FontAwesomeIcon icon={faChessKnight} className="text-green-600 mr-3" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Strategy Settings</h2>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Configure and manage your individual trading strategies.</p>
        </div>
        <div className="p-6">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">Access a dedicated page to build, modify, and monitor your algorithmic trading strategies.</p>
          <button className="px-6 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium">
            Manage Strategies →
          </button>
        </div>
      </section>

      {/* Notifications */}
      <section className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <FontAwesomeIcon icon={faBell} className="text-yellow-600 mr-3" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Notifications</h2>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Choose how and when you receive alerts from the system.</p>
        </div>
        <div className="p-6 space-y-4">
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">Trade Execution Alerts</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Receive instant alerts for order fills, rejections, and cancellations.</p>
            </div>
            <button
              onClick={() => setTradeAlerts(!tradeAlerts)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                tradeAlerts ? 'bg-blue-600' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  tradeAlerts ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">Market Event Notifications</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Get notified about significant market movements or chaos events.</p>
            </div>
            <button
              onClick={() => setMarketEvents(!marketEvents)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                marketEvents ? 'bg-blue-600' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  marketEvents ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">System Status Updates</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Receive alerts for platform maintenance, updates, or outages.</p>
            </div>
            <button
              onClick={() => setSystemStatus(!systemStatus)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                systemStatus ? 'bg-blue-600' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  systemStatus ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">Email Notifications</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Receive important updates and summaries via email.</p>
            </div>
            <button
              onClick={() => setEmailNotifications(!emailNotifications)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                emailNotifications ? 'bg-blue-600' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  emailNotifications ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>
      </section>

      {/* Appearance */}
      <section className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <FontAwesomeIcon icon={faPalette} className="text-pink-600 mr-3" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Appearance</h2>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Customize the visual elements of your trading terminal.</p>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Chart Color Theme</label>
            <select className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white">
              <option>Dark Professional</option>
              <option>Light Classic</option>
              <option>Trading View Style</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Font Size</label>
            <select className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white">
              <option>Small</option>
              <option>Medium</option>
              <option>Large</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">UI Density</label>
            <select className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white">
              <option>Compact</option>
              <option>Normal</option>
              <option>Comfortable</option>
            </select>
          </div>
        </div>
      </section>

      {/* Integrations */}
      <section className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <FontAwesomeIcon icon={faPlug} className="text-cyan-600 mr-3" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Integrations</h2>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Connect to external brokers, data providers, and AI services.</p>
        </div>
        <div className="p-6 space-y-4">
          <div className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Alpaca Broker Connection</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Link your Alpaca brokerage account for live trading and paper trading.</p>
            </div>
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Configure →</button>
          </div>
          <div className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Finviz Elite Data Feed</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Integrate Finviz Elite for advanced market screening and fundamental data.</p>
            </div>
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Connect →</button>
          </div>
          <div className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">ML Model Integration</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Connect and fine-tune external machine learning models for signal generation.</p>
            </div>
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Manage →</button>
          </div>
        </div>
      </section>

      {/* Danger Zone */}
      <section className="bg-red-50 dark:bg-red-900/10 rounded-lg border-2 border-red-300 dark:border-red-800">
        <div className="p-6 border-b border-red-300 dark:border-red-800">
          <div className="flex items-center">
            <FontAwesomeIcon icon={faTrash} className="text-red-600 mr-3" />
            <h2 className="text-lg font-semibold text-red-900 dark:text-red-400">Danger Zone</h2>
          </div>
          <p className="text-sm text-red-700 dark:text-red-300 mt-1">Critical actions that can significantly impact your account. Proceed with caution.</p>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-red-900 dark:text-red-400">Delete Account</p>
              <p className="text-sm text-red-700 dark:text-red-300">Permanently delete your Elite Trading System account and all associated data. This action cannot be undone.</p>
            </div>
            <button className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium">
              Delete Account
            </button>
          </div>
        </div>
      </section>

      {/* Save Button */}
      <div className="flex justify-end">
        <button className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium flex items-center space-x-2">
          <FontAwesomeIcon icon={faSave} />
          <span>Save All Changes</span>
        </button>
      </div>
    </div>
  );
}

