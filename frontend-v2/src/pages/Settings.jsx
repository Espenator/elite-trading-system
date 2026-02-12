import { useState } from 'react';
import { 
  Bell,
  Shield,
  Cpu,
  Key,
  Save
} from 'lucide-react';
import clsx from 'clsx';

export default function Settings() {
  const [settings, setSettings] = useState({
    // Notifications
    telegramEnabled: true,
    emailEnabled: true,
    signalAlerts: true,
    tradeAlerts: true,
    dailySummary: true,
    weeklySummary: true,
    
    // Risk
    maxPositions: 15,
    riskPerTrade: 2.0,
    maxDailyLoss: 5.0,
    circuitBreaker: true,
    
    // ML
    minCompositeScore: 60,
    minMLConfidence: 50,
    autoRetrain: true,
    retrainDay: 'Sunday',
    
    // API Keys
    finnhubKey: '••••••••••••••••',
    unusualWhalesKey: '••••••••••••••••',
    telegramToken: '••••••••••••••••',
    telegramChatId: '••••••••••••••••'
  });

  const handleChange = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const Toggle = ({ enabled, onChange }) => (
    <button
      onClick={onChange}
      className={clsx(
        'w-12 h-6 rounded-full transition-colors relative',
        enabled ? 'bg-bullish' : 'bg-gray-600'
      )}
    >
      <div className={clsx(
        'w-5 h-5 bg-white rounded-full absolute top-0.5 transition-transform',
        enabled ? 'translate-x-6' : 'translate-x-0.5'
      )} />
    </button>
  );

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-gray-400 text-sm">Configure system parameters</p>
        </div>
        <button className="flex items-center gap-2 bg-bullish text-white px-4 py-2 rounded-lg hover:bg-bullish/80 transition-colors">
          <Save className="w-4 h-4" />
          Save Changes
        </button>
      </div>

      {/* Notifications */}
      <div className="bg-dark-card border border-dark-border rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Bell className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-semibold">Notifications</h2>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span>Telegram Notifications</span>
              <Toggle 
                enabled={settings.telegramEnabled}
                onChange={() => handleChange('telegramEnabled', !settings.telegramEnabled)}
              />
            </div>

            <div className="flex items-center justify-between">
              <span>Email Notifications</span>
              <Toggle 
                enabled={settings.emailEnabled}
                onChange={() => handleChange('emailEnabled', !settings.emailEnabled)}
              />
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span>Signal Alerts</span>
              <Toggle 
                enabled={settings.signalAlerts}
                onChange={() => handleChange('signalAlerts', !settings.signalAlerts)}
              />
            </div>

            <div className="flex items-center justify-between">
              <span>Daily Summary</span>
              <Toggle 
                enabled={settings.dailySummary}
                onChange={() => handleChange('dailySummary', !settings.dailySummary)}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Risk Management */}
      <div className="bg-dark-card border border-dark-border rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-5 h-5 text-red-400" />
          <h2 className="text-lg font-semibold">Risk Management</h2>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Max Positions</label>
            <input
              type="number"
              value={settings.maxPositions}
              onChange={(e) => handleChange('maxPositions', Number(e.target.value))}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 focus:outline-none focus:border-bullish"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Risk Per Trade (%)</label>
            <input
              type="number"
              step="0.5"
              value={settings.riskPerTrade}
              onChange={(e) => handleChange('riskPerTrade', Number(e.target.value))}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 focus:outline-none focus:border-bullish"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Max Daily Loss (%)</label>
            <input
              type="number"
              step="0.5"
              value={settings.maxDailyLoss}
              onChange={(e) => handleChange('maxDailyLoss', Number(e.target.value))}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 focus:outline-none focus:border-bullish"
            />
          </div>

          <div className="flex items-center justify-between pt-6">
            <span>Circuit Breaker</span>
            <Toggle 
              enabled={settings.circuitBreaker}
              onChange={() => handleChange('circuitBreaker', !settings.circuitBreaker)}
            />
          </div>
        </div>
      </div>

      {/* ML Settings */}
      <div className="bg-dark-card border border-dark-border rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Cpu className="w-5 h-5 text-purple-400" />
          <h2 className="text-lg font-semibold">ML Configuration</h2>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Min Composite Score</label>
            <input
              type="number"
              value={settings.minCompositeScore}
              onChange={(e) => handleChange('minCompositeScore', Number(e.target.value))}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 focus:outline-none focus:border-bullish"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Min ML Confidence (%)</label>
            <input
              type="number"
              value={settings.minMLConfidence}
              onChange={(e) => handleChange('minMLConfidence', Number(e.target.value))}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 focus:outline-none focus:border-bullish"
            />
          </div>

          <div className="flex items-center justify-between">
            <span>Auto Retrain Weekly</span>
            <Toggle 
              enabled={settings.autoRetrain}
              onChange={() => handleChange('autoRetrain', !settings.autoRetrain)}
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Retrain Day</label>
            <select
              value={settings.retrainDay}
              onChange={(e) => handleChange('retrainDay', e.target.value)}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 focus:outline-none focus:border-bullish"
            >
              <option>Sunday</option>
              <option>Saturday</option>
              <option>Friday</option>
            </select>
          </div>
        </div>
      </div>

      {/* API Keys */}
      <div className="bg-dark-card border border-dark-border rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Key className="w-5 h-5 text-yellow-400" />
          <h2 className="text-lg font-semibold">API Keys</h2>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Finnhub API Key</label>
            <input
              type="password"
              value={settings.finnhubKey}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 focus:outline-none focus:border-bullish"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Unusual Whales API Key</label>
            <input
              type="password"
              value={settings.unusualWhalesKey}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 focus:outline-none focus:border-bullish"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Telegram Bot Token</label>
            <input
              type="password"
              value={settings.telegramToken}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 focus:outline-none focus:border-bullish"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Telegram Chat ID</label>
            <input
              type="password"
              value={settings.telegramChatId}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 focus:outline-none focus:border-bullish"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
