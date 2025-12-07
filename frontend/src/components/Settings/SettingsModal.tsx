import React, { useState } from 'react';
import { useSettings } from '../../hooks/useSettings';
import './SettingsModal.css';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const { settings, saveSettings, resetSettings } = useSettings();
  const [activeTab, setActiveTab] = useState('api');
  const [localSettings, setLocalSettings] = useState(settings);

  const handleSave = () => {
    saveSettings(localSettings);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="settings-overlay">
      <div className="settings-modal">
        <div className="settings-header">
          <h2>⚙️ Settings</h2>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="settings-tabs">
          <button 
            className={`tab-btn ${activeTab === 'api' ? 'active' : ''}`}
            onClick={() => setActiveTab('api')}
          >
            🔑 API Keys
          </button>
          <button 
            className={`tab-btn ${activeTab === 'scanner' ? 'active' : ''}`}
            onClick={() => setActiveTab('scanner')}
          >
            📊 Scanner
          </button>
          <button 
            className={`tab-btn ${activeTab === 'trading' ? 'active' : ''}`}
            onClick={() => setActiveTab('trading')}
          >
            💼 Trading
          </button>
        </div>

        <div className="settings-content">
          {activeTab === 'api' && (
            <div className="settings-section">
              <h3>API Keys & Integrations</h3>
              
              <div className="api-key-group">
                <label>🐋 Unusual Whales API Key</label>
                <input 
                  type="password" 
                  placeholder="Enter API key..."
                  value={localSettings.apiKeys.unusualWhales}
                  onChange={(e) => setLocalSettings({
                    ...localSettings,
                    apiKeys: { ...localSettings.apiKeys, unusualWhales: e.target.value }
                  })}
                />
                <button className="test-btn">Test Connection</button>
              </div>

              <div className="api-key-group">
                <label>📈 Finviz Elite API Key</label>
                <input 
                  type="password" 
                  placeholder="Enter API key..."
                  value={localSettings.apiKeys.finviz}
                  onChange={(e) => setLocalSettings({
                    ...localSettings,
                    apiKeys: { ...localSettings.apiKeys, finviz: e.target.value }
                  })}
                />
                <button className="test-btn">Test Connection</button>
              </div>

              <div className="api-key-group">
                <label>🤖 Anthropic API Key</label>
                <input 
                  type="password" 
                  placeholder="Enter API key..."
                  value={localSettings.apiKeys.anthropic}
                  onChange={(e) => setLocalSettings({
                    ...localSettings,
                    apiKeys: { ...localSettings.apiKeys, anthropic: e.target.value }
                  })}
                />
                <button className="test-btn">Test Connection</button>
              </div>
            </div>
          )}

          {activeTab === 'scanner' && (
            <div className="settings-section">
              <h3>Scanner Configuration</h3>
              
              <div className="setting-group">
                <label>Scan Interval (minutes)</label>
                <input 
                  type="number" 
                  value={localSettings.scanner.interval}
                  onChange={(e) => setLocalSettings({
                    ...localSettings,
                    scanner: { ...localSettings.scanner, interval: Number(e.target.value) }
                  })}
                  min={5} 
                  max={60} 
                />
              </div>

              <div className="setting-group">
                <label>Minimum Confidence (%)</label>
                <input 
                  type="number" 
                  value={localSettings.scanner.minConfidence}
                  onChange={(e) => setLocalSettings({
                    ...localSettings,
                    scanner: { ...localSettings.scanner, minConfidence: Number(e.target.value) }
                  })}
                  min={0} 
                  max={100} 
                />
              </div>
            </div>
          )}

          {activeTab === 'trading' && (
            <div className="settings-section">
              <h3>Paper Trading Settings</h3>
              
              <div className="setting-group">
                <label>Starting Capital ($)</label>
                <input 
                  type="number" 
                  value={localSettings.trading.startingCapital}
                  onChange={(e) => setLocalSettings({
                    ...localSettings,
                    trading: { ...localSettings.trading, startingCapital: Number(e.target.value) }
                  })}
                />
              </div>

              <div className="setting-group">
                <label>Max Risk Per Trade (%)</label>
                <input 
                  type="number" 
                  value={localSettings.trading.maxRiskPerTrade}
                  onChange={(e) => setLocalSettings({
                    ...localSettings,
                    trading: { ...localSettings.trading, maxRiskPerTrade: Number(e.target.value) }
                  })}
                  min={0.5} 
                  max={10} 
                  step={0.5} 
                />
              </div>

              <div className="setting-group">
                <label>Max Open Positions</label>
                <input 
                  type="number" 
                  value={localSettings.trading.maxPositions}
                  onChange={(e) => setLocalSettings({
                    ...localSettings,
                    trading: { ...localSettings.trading, maxPositions: Number(e.target.value) }
                  })}
                  min={1} 
                  max={50} 
                />
              </div>
            </div>
          )}
        </div>

        <div className="settings-footer">
          <button className="cancel-btn" onClick={onClose}>Cancel</button>
          <button className="reset-btn" onClick={resetSettings}>Reset Defaults</button>
          <button className="save-btn" onClick={handleSave}>Save Changes</button>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
