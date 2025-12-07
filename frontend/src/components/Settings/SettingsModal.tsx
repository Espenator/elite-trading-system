import React, { useState } from 'react';
import './SettingsModal.css';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState('api');

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
                <input type="password" placeholder="Enter API key..." />
                <button className="test-btn">Test Connection</button>
              </div>

              <div className="api-key-group">
                <label>📈 Finviz Elite API Key</label>
                <input type="password" placeholder="Enter API key..." />
                <button className="test-btn">Test Connection</button>
              </div>

              <div className="api-key-group">
                <label>🤖 Anthropic API Key</label>
                <input type="password" placeholder="Enter API key..." />
                <button className="test-btn">Test Connection</button>
              </div>
            </div>
          )}

          {activeTab === 'scanner' && (
            <div className="settings-section">
              <h3>Scanner Configuration</h3>
              
              <div className="setting-group">
                <label>Scan Interval (minutes)</label>
                <input type="number" defaultValue={15} min={5} max={60} />
              </div>

              <div className="setting-group">
                <label>Minimum Confidence (%)</label>
                <input type="number" defaultValue={70} min={0} max={100} />
              </div>
            </div>
          )}

          {activeTab === 'trading' && (
            <div className="settings-section">
              <h3>Paper Trading Settings</h3>
              
              <div className="setting-group">
                <label>Starting Capital ($)</label>
                <input type="number" defaultValue={1000000} />
              </div>

              <div className="setting-group">
                <label>Max Risk Per Trade (%)</label>
                <input type="number" defaultValue={2} min={0.5} max={10} step={0.5} />
              </div>

              <div className="setting-group">
                <label>Max Open Positions</label>
                <input type="number" defaultValue={15} min={1} max={50} />
              </div>
            </div>
          )}
        </div>

        <div className="settings-footer">
          <button className="cancel-btn" onClick={onClose}>Cancel</button>
          <button className="save-btn">Save Changes</button>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
