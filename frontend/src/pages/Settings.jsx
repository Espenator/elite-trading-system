import React, { useState } from 'react';
import { useTheme } from '../context/ThemeContext';
import { useSettings } from '../context/SettingsContext';
import SettingsSection from '../components/SettingsSection';
import '../styles/Settings.css';

export default function Settings() {
  const { theme, toggleTheme } = useTheme();
  const { settings, updateSetting, updateSettings, resetToDefaults, maskApiKey, saved } = useSettings();
  const [activeTab, setActiveTab] = useState('appearance');
  const [showApiKeys, setShowApiKeys] = useState({});
  const [backendStatus, setBackendStatus] = useState('connected');
  const [latency, setLatency] = useState('12ms');

  // ==================== TAB NAVIGATION ====================
  const tabs = [
    { id: 'appearance', label: '🎨 Appearance', icon: '🎨' },
    { id: 'trading', label: '💰 Trading', icon: '💰' },
    { id: 'risk', label: '⚠️ Risk', icon: '⚠️' },
    { id: 'notifications', label: '🔔 Notifications', icon: '🔔' },
    { id: 'apis', label: '🔑 API Keys', icon: '🔑' },
    { id: 'data', label: '💾 Data', icon: '💾' },
    { id: 'system', label: '⚙️ System', icon: '⚙️' },
  ];

  // ==================== HELPERS ====================
  const handleToggleApiKey = (key) => {
    setShowApiKeys(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const handleExportTrades = (format) => {
    console.log(`Export trades as ${format}`);
    // TODO: Implement trade export
  };

  const handleClearHistory = () => {
    if (confirm('Clear all trade history? This cannot be undone.')) {
      console.log('Clear trade history');
      // TODO: Implement
    }
  };

  // ==================== RENDER: APPEARANCE TAB ====================
  const renderAppearance = () => (
    <div className="settings-tabs-content">
      {/* Theme Toggle */}
      <SettingsSection 
        title="Theme"
        description="Choose between dark and light modes"
        icon="🌙"
      >
        <div className="settings-row">
          <label className="settings-label">Display Mode</label>
          <div className="theme-toggle">
            <button 
              className={`toggle-btn ${theme === 'dark' ? 'active' : ''}`}
              onClick={toggleTheme}
            >
              🌙 Dark
            </button>
            <button 
              className={`toggle-btn ${theme === 'light' ? 'active' : ''}`}
              onClick={toggleTheme}
            >
              ☀️ Light
            </button>
          </div>
        </div>
      </SettingsSection>

      {/* Color Scheme */}
      <SettingsSection 
        title="Color Scheme"
        description="Choose your preferred color palette"
        icon="🎭"
      >
        <div className="settings-row">
          <label className="settings-label">Scheme</label>
          <select className="settings-select">
            <option value="default">Default (Cyan/Purple)</option>
            <option value="bloomberg">Bloomberg (Orange/Blue)</option>
            <option value="modern">Modern (Green/Red)</option>
            <option value="custom">Custom</option>
          </select>
        </div>
      </SettingsSection>

      {/* Font Size */}
      <SettingsSection 
        title="Font Size"
        description="Adjust text size across the application"
        icon="📝"
      >
        <div className="settings-row">
          <label className="settings-label">Size</label>
          <div className="radio-group">
            {['small', 'medium', 'large'].map(size => (
              <label key={size} className="radio-label">
                <input type="radio" value={size} name="font-size" />
                <span className="radio-text">{size.charAt(0).toUpperCase() + size.slice(1)}</span>
              </label>
            ))}
          </div>
        </div>
      </SettingsSection>

      {/* Chart Theme */}
      <SettingsSection 
        title="Chart Theme"
        description="Configure how charts are displayed"
        icon="📊"
      >
        <div className="settings-row">
          <label className="settings-label">Chart Colors</label>
          <select className="settings-select">
            <option value="dark">Dark Theme</option>
            <option value="light">Light Theme</option>
            <option value="custom">Custom Colors</option>
          </select>
        </div>
      </SettingsSection>

      {/* Compact Mode */}
      <SettingsSection 
        title="Compact Mode"
        description="Dense tables and reduced spacing"
        icon="📦"
      >
        <div className="settings-row">
          <label className="settings-label">Layout</label>
          <label className="checkbox-label">
            <input 
              type="checkbox" 
              checked={settings.compactMode}
              onChange={(e) => updateSetting('compactMode', e.target.checked)}
            />
            <span>Enable compact mode</span>
          </label>
        </div>
      </SettingsSection>
    </div>
  );

  // ==================== RENDER: TRADING TAB ====================
  const renderTrading = () => (
    <div className="settings-tabs-content">
      {/* Default Order Size */}
      <SettingsSection 
        title="Default Order Size"
        description="Pre-selected quantity for quick trades"
        icon="🛒"
      >
        <div className="settings-row">
          <label className="settings-label">Shares per Trade</label>
          <select 
            className="settings-select"
            value={settings.defaultOrderSize}
            onChange={(e) => updateSetting('defaultOrderSize', parseInt(e.target.value))}
          >
            <option value={100}>100 shares</option>
            <option value={500}>500 shares</option>
            <option value={1000}>1,000 shares</option>
            <option value={2500}>2,500 shares</option>
            <option value={5000}>5,000 shares</option>
          </select>
        </div>
      </SettingsSection>

      {/* Quick Trade */}
      <SettingsSection 
        title="Quick Trade Buttons"
        description="Enable/disable one-click trading"
        icon="⚡"
      >
        <div className="settings-row">
          <label className="settings-label">Status</label>
          <label className="checkbox-label">
            <input 
              type="checkbox" 
              checked={settings.quickTradeEnabled}
              onChange={(e) => updateSetting('quickTradeEnabled', e.target.checked)}
            />
            <span>Enable quick trade buttons</span>
          </label>
        </div>
      </SettingsSection>

      {/* Confirmation Dialogs */}
      <SettingsSection 
        title="Confirmation Dialogs"
        description="Require confirmation before executing trades"
        icon="✓"
      >
        <div className="settings-row">
          <label className="settings-label">Confirmations</label>
          <select 
            className="settings-select"
            value={settings.confirmationDialogs}
            onChange={(e) => updateSetting('confirmationDialogs', e.target.value)}
          >
            <option value="always">Always confirm</option>
            <option value="t1_only">T1 signals only</option>
            <option value="never">Never confirm</option>
          </select>
        </div>
      </SettingsSection>

      {/* Auto-Refresh */}
      <SettingsSection 
        title="Auto-Refresh Interval"
        description="How often signals update"
        icon="🔄"
      >
        <div className="settings-row">
          <label className="settings-label">Interval</label>
          <select 
            className="settings-select"
            value={settings.autoRefreshInterval}
            onChange={(e) => updateSetting('autoRefreshInterval', parseInt(e.target.value))}
          >
            <option value={5}>5 seconds</option>
            <option value={10}>10 seconds</option>
            <option value={30}>30 seconds</option>
            <option value={60}>60 seconds</option>
          </select>
        </div>
      </SettingsSection>

      {/* Signal Filters */}
      <SettingsSection 
        title="Default Signal Filters"
        description="Pre-filter signals by score and type"
        icon="🎯"
      >
        <div className="settings-row">
          <label className="settings-label">Minimum Score</label>
          <input 
            type="number" 
            min="0" 
            max="100" 
            value={settings.minSignalScore}
            onChange={(e) => updateSetting('minSignalScore', parseInt(e.target.value))}
            className="settings-input"
          />
          <span className="input-suffix">/ 100</span>
        </div>
        <div className="settings-row">
          <label className="settings-label">Preferred Tiers</label>
          <div className="checkbox-group">
            {['T1', 'T2', 'T3'].map(tier => (
              <label key={tier} className="checkbox-label">
                <input 
                  type="checkbox" 
                  checked={settings.preferredTiers.includes(tier)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      updateSetting('preferredTiers', [...settings.preferredTiers, tier]);
                    } else {
                      updateSetting('preferredTiers', settings.preferredTiers.filter(t => t !== tier));
                    }
                  }}
                />
                <span>{tier}</span>
              </label>
            ))}
          </div>
        </div>
      </SettingsSection>
    </div>
  );

  // ==================== RENDER: RISK TAB ====================
  const renderRisk = () => (
    <div className="settings-tabs-content">
      {/* Daily Loss Limit */}
      <SettingsSection 
        title="Daily Loss Limit"
        description="Stop trading when daily loss reached"
        icon="💰"
      >
        <div className="settings-row">
          <label className="settings-label">Max Daily Loss</label>
          <input 
            type="number" 
            value={settings.maxDailyLossLimit}
            onChange={(e) => updateSetting('maxDailyLossLimit', parseInt(e.target.value))}
            className="settings-input"
          />
          <span className="input-suffix">USD</span>
        </div>
      </SettingsSection>

      {/* Position Size */}
      <SettingsSection 
        title="Position Sizing"
        description="Maximum size per individual trade"
        icon="📊"
      >
        <div className="settings-row">
          <label className="settings-label">Max Position Size</label>
          <input 
            type="number" 
            value={settings.maxPositionSize}
            onChange={(e) => updateSetting('maxPositionSize', parseInt(e.target.value))}
            className="settings-input"
          />
          <span className="input-suffix">USD</span>
        </div>
      </SettingsSection>

      {/* Max Positions */}
      <SettingsSection 
        title="Portfolio Limits"
        description="Maximum simultaneous open positions"
        icon="🎯"
      >
        <div className="settings-row">
          <label className="settings-label">Max Positions</label>
          <input 
            type="number" 
            min="1" 
            max="50" 
            value={settings.maxPositions}
            onChange={(e) => updateSetting('maxPositions', parseInt(e.target.value))}
            className="settings-input"
          />
          <span className="input-suffix">trades</span>
        </div>
      </SettingsSection>

      {/* Sector Limits */}
      <SettingsSection 
        title="Sector Concentration"
        description="Maximum portfolio % in any single sector"
        icon="🏭"
      >
        <div className="settings-row">
          <label className="settings-label">Sector Limit</label>
          <input 
            type="number" 
            min="0" 
            max="100" 
            step="5"
            value={Math.round(settings.sectorLimits * 100)}
            onChange={(e) => updateSetting('sectorLimits', parseInt(e.target.value) / 100)}
            className="settings-input"
          />
          <span className="input-suffix">%</span>
        </div>
      </SettingsSection>

      {/* Correlation Check */}
      <SettingsSection 
        title="Correlation Check"
        description="Prevent correlated positions"
        icon="🔗"
      >
        <div className="settings-row">
          <label className="settings-label">Risk Management</label>
          <label className="checkbox-label">
            <input 
              type="checkbox" 
              checked={settings.correlationCheck}
              onChange={(e) => updateSetting('correlationCheck', e.target.checked)}
            />
            <span>Enable correlation check</span>
          </label>
        </div>
      </SettingsSection>
    </div>
  );

  // ==================== RENDER: NOTIFICATIONS TAB ====================
  const renderNotifications = () => (
    <div className="settings-tabs-content">
      {/* Browser Notifications */}
      <SettingsSection 
        title="Browser Notifications"
        description="Desktop alerts for trading signals"
        icon="🔔"
      >
        <div className="settings-row">
          <label className="settings-label">Alerts</label>
          <select 
            className="settings-select"
            value={settings.browserNotifications}
            onChange={(e) => updateSetting('browserNotifications', e.target.value)}
          >
            <option value="off">Off</option>
            <option value="t1_only">T1 signals only</option>
            <option value="all">All signals</option>
          </select>
        </div>
      </SettingsSection>

      {/* Sound Alerts */}
      <SettingsSection 
        title="Sound Alerts"
        description="Audio notification for new signals"
        icon="🔊"
      >
        <div className="settings-row">
          <label className="settings-label">Status</label>
          <label className="checkbox-label">
            <input 
              type="checkbox" 
              checked={settings.soundAlerts}
              onChange={(e) => updateSetting('soundAlerts', e.target.checked)}
            />
            <span>Enable sound alerts</span>
          </label>
        </div>
      </SettingsSection>

      {/* Email Notifications */}
      <SettingsSection 
        title="Email Alerts"
        description="Receive trading updates via email"
        icon="📧"
      >
        <div className="settings-row">
          <label className="settings-label">Status</label>
          <label className="checkbox-label">
            <input 
              type="checkbox" 
              checked={settings.emailNotifications}
              onChange={(e) => updateSetting('emailNotifications', e.target.checked)}
            />
            <span>Enable email notifications</span>
          </label>
        </div>
      </SettingsSection>

      {/* Telegram Integration */}
      <SettingsSection 
        title="Telegram Alerts"
        description="Receive signals on Telegram"
        icon="📱"
      >
        <div className="settings-row">
          <label className="settings-label">Enable Telegram</label>
          <label className="checkbox-label">
            <input 
              type="checkbox" 
              checked={settings.telegramEnabled}
              onChange={(e) => updateSetting('telegramEnabled', e.target.checked)}
            />
            <span>Connect Telegram bot</span>
          </label>
        </div>
        {settings.telegramEnabled && (
          <>
            <div className="settings-row">
              <label className="settings-label">Bot Token</label>
              <input 
                type="password" 
                value={settings.telegramBotToken}
                onChange={(e) => updateSetting('telegramBotToken', e.target.value)}
                placeholder="Paste your Telegram bot token"
                className="settings-input"
              />
            </div>
            <div className="settings-row">
              <label className="settings-label">Chat ID</label>
              <input 
                type="text" 
                value={settings.telegramChatId}
                onChange={(e) => updateSetting('telegramChatId', e.target.value)}
                placeholder="Your Telegram chat ID"
                className="settings-input"
              />
            </div>
          </>
        )}
      </SettingsSection>
    </div>
  );

  // ==================== RENDER: API KEYS TAB ====================
  const renderApiKeys = () => (
    <div className="settings-tabs-content">
      {/* Alpaca */}
      <SettingsSection 
        title="Alpaca Trading API"
        description="Connect to Alpaca broker for trade execution"
        icon="🚀"
      >
        <div className="settings-row">
          <label className="settings-label">API Key</label>
          <div className="api-key-input">
            <input 
              type={showApiKeys['alpaca-key'] ? 'text' : 'password'}
              value={settings.alpacaApiKey}
              onChange={(e) => updateSetting('alpacaApiKey', e.target.value)}
              placeholder="sk_live_..."
              className="settings-input"
            />
            <button 
              className="reveal-btn"
              onClick={() => handleToggleApiKey('alpaca-key')}
            >
              {showApiKeys['alpaca-key'] ? '😨' : '👁️'}
            </button>
          </div>
          <span className="api-masked">{maskApiKey(settings.alpacaApiKey)}</span>
        </div>
        <div className="settings-row">
          <label className="settings-label">Secret Key</label>
          <div className="api-key-input">
            <input 
              type={showApiKeys['alpaca-secret'] ? 'text' : 'password'}
              value={settings.alpacaSecretKey}
              onChange={(e) => updateSetting('alpacaSecretKey', e.target.value)}
              placeholder="sk_live_..."
              className="settings-input"
            />
            <button 
              className="reveal-btn"
              onClick={() => handleToggleApiKey('alpaca-secret')}
            >
              {showApiKeys['alpaca-secret'] ? '😨' : '👁️'}
            </button>
          </div>
          <span className="api-masked">{maskApiKey(settings.alpacaSecretKey)}</span>
        </div>
      </SettingsSection>

      {/* Perplexity */}
      <SettingsSection 
        title="Perplexity AI API"
        description="Market analysis and insights"
        icon="🤖"
      >
        <div className="settings-row">
          <label className="settings-label">API Key</label>
          <div className="api-key-input">
            <input 
              type={showApiKeys['perplexity'] ? 'text' : 'password'}
              value={settings.perplexityApiKey}
              onChange={(e) => updateSetting('perplexityApiKey', e.target.value)}
              placeholder="pplx-..."
              className="settings-input"
            />
            <button 
              className="reveal-btn"
              onClick={() => handleToggleApiKey('perplexity')}
            >
              {showApiKeys['perplexity'] ? '😨' : '👁️'}
            </button>
          </div>
          <span className="api-masked">{maskApiKey(settings.perplexityApiKey)}</span>
        </div>
      </SettingsSection>

      {/* Unusual Whales */}
      <SettingsSection 
        title="Unusual Whales API"
        description="Unusual activity and flow detection"
        icon="🐋"
      >
        <div className="settings-row">
          <label className="settings-label">API Key</label>
          <div className="api-key-input">
            <input 
              type={showApiKeys['unusual-whales'] ? 'text' : 'password'}
              value={settings.unusualWhalesApiKey}
              onChange={(e) => updateSetting('unusualWhalesApiKey', e.target.value)}
              placeholder="Your API key"
              className="settings-input"
            />
            <button 
              className="reveal-btn"
              onClick={() => handleToggleApiKey('unusual-whales')}
            >
              {showApiKeys['unusual-whales'] ? '😨' : '👁️'}
            </button>
          </div>
          <span className="api-masked">{maskApiKey(settings.unusualWhalesApiKey)}</span>
        </div>
      </SettingsSection>

      {/* Finviz */}
      <SettingsSection 
        title="Finviz Elite API"
        description="Stock screener and data"
        icon="📈"
      >
        <div className="settings-row">
          <label className="settings-label">API Key</label>
          <div className="api-key-input">
            <input 
              type={showApiKeys['finviz'] ? 'text' : 'password'}
              value={settings.finvizApiKey}
              onChange={(e) => updateSetting('finvizApiKey', e.target.value)}
              placeholder="Your API key"
              className="settings-input"
            />
            <button 
              className="reveal-btn"
              onClick={() => handleToggleApiKey('finviz')}
            >
              {showApiKeys['finviz'] ? '😨' : '👁️'}
            </button>
          </div>
          <span className="api-masked">{maskApiKey(settings.finvizApiKey)}</span>
        </div>
      </SettingsSection>
    </div>
  );

  // ==================== RENDER: DATA TAB ====================
  const renderData = () => (
    <div className="settings-tabs-content">
      {/* Export Trades */}
      <SettingsSection 
        title="Export Trades"
        description="Download your trading history"
        icon="📥"
      >
        <div className="settings-row">
          <label className="settings-label">Format</label>
          <div className="button-group">
            <button 
              className="action-btn primary"
              onClick={() => handleExportTrades('csv')}
            >
              📄 Export CSV
            </button>
            <button 
              className="action-btn"
              onClick={() => handleExportTrades('json')}
            >
              📋 Export JSON
            </button>
          </div>
        </div>
      </SettingsSection>

      {/* Clear History */}
      <SettingsSection 
        title="Clear Trade History"
        description="Permanently delete all trades (cannot be undone)"
        icon="🗑️"
      >
        <div className="settings-row">
          <button 
            className="action-btn danger"
            onClick={handleClearHistory}
          >
            🗑️ Clear History
          </button>
        </div>
      </SettingsSection>

      {/* Download Logs */}
      <SettingsSection 
        title="Download Logs"
        description="Debug logs for troubleshooting"
        icon="📝"
      >
        <div className="settings-row">
          <button className="action-btn">
            📝 Download Logs
          </button>
        </div>
      </SettingsSection>

      {/* Database Backup */}
      <SettingsSection 
        title="Database Backup"
        description="Backup and restore your settings"
        icon="💾"
      >
        <div className="settings-row">
          <div className="button-group">
            <button className="action-btn">
              ☁️ Backup Now
            </button>
            <button className="action-btn">
              ↩️ Restore
            </button>
          </div>
        </div>
      </SettingsSection>
    </div>
  );

  // ==================== RENDER: SYSTEM TAB ====================
  const renderSystem = () => (
    <div className="settings-tabs-content">
      {/* Version Info */}
      <SettingsSection 
        title="Version Information"
        description="System version and build details"
        icon="ℹ️"
      >
        <div className="settings-row">
          <div className="info-item">
            <span className="info-label">App Version</span>
            <span className="info-value">2.1.0</span>
          </div>
          <div className="info-item">
            <span className="info-label">Build Date</span>
            <span className="info-value">Dec 14, 2025</span>
          </div>
          <div className="info-item">
            <span className="info-label">Backend Version</span>
            <span className="info-value">1.5.2</span>
          </div>
        </div>
      </SettingsSection>

      {/* Backend Status */}
      <SettingsSection 
        title="Backend Connection"
        description="Real-time system status"
        icon="🔌"
      >
        <div className="settings-row">
          <div className="status-item">
            <span className="status-indicator" style={{
              background: backendStatus === 'connected' ? '#10b981' : '#ef4444'
            }}></span>
            <span className="status-text">
              {backendStatus === 'connected' ? '🟢 Connected' : '🔴 Disconnected'}
            </span>
          </div>
        </div>
        <div className="settings-row">
          <div className="info-item">
            <span className="info-label">Latency</span>
            <span className="info-value">{latency}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Last Update</span>
            <span className="info-value">2 seconds ago</span>
          </div>
        </div>
      </SettingsSection>

      {/* Advanced */}
      <SettingsSection 
        title="Advanced Settings"
        description="Reset and debug options"
        icon="⚙️"
      >
        <div className="settings-row">
          <button 
            className="action-btn danger"
            onClick={resetToDefaults}
          >
            🔄 Reset All Settings
          </button>
        </div>
      </SettingsSection>
    </div>
  );

  // ==================== MAIN RENDER ====================
  return (
    <div className="settings-page">
      <div className="settings-header">
        <h1 className="settings-title">⚙️ Settings</h1>
        {saved && <span className="save-indicator">✓ Saved</span>}
      </div>

      <div className="settings-container">
        {/* Tab Navigation */}
        <div className="settings-tabs">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`settings-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
              title={tab.label}
            >
              <span className="tab-icon">{tab.icon}</span>
              <span className="tab-label">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="settings-content">
          {activeTab === 'appearance' && renderAppearance()}
          {activeTab === 'trading' && renderTrading()}
          {activeTab === 'risk' && renderRisk()}
          {activeTab === 'notifications' && renderNotifications()}
          {activeTab === 'apis' && renderApiKeys()}
          {activeTab === 'data' && renderData()}
          {activeTab === 'system' && renderSystem()}
        </div>
      </div>
    </div>
  );
}
