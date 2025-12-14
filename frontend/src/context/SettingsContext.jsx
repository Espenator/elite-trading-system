import React, { createContext, useContext, useEffect, useState } from 'react';

const SettingsContext = createContext();

const DEFAULT_SETTINGS = {
  // Trading Preferences
  defaultOrderSize: 100,
  quickTradeEnabled: true,
  confirmationDialogs: 'always', // always | t1_only | never
  autoRefreshInterval: 10, // seconds
  minSignalScore: 60,
  preferredTiers: ['T1', 'T2', 'T3'],
  preferredSignalTypes: ['MOMENTUM', 'VOLUME_SPIKE', 'RSI_OVERSOLD'],

  // Risk Management
  maxDailyLossLimit: 5000,
  maxPositionSize: 50000,
  maxPositions: 5,
  sectorLimits: 0.3, // 30% max per sector
  correlationCheck: true,

  // Notifications
  browserNotifications: 't1_only', // t1_only | all | off
  soundAlerts: true,
  emailNotifications: true,
  telegramEnabled: false,

  // API Connections
  alpacaApiKey: '',
  alpacaSecretKey: '',
  perplexityApiKey: '',
  unusualWhalesApiKey: '',
  finvizApiKey: '',
  telegramBotToken: '',
  telegramChatId: '',

  // Appearance
  compactMode: false,
  chartTheme: 'dark', // dark | light
};

export function SettingsProvider({ children }) {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('elite-trader-settings');
    if (saved) {
      try {
        setSettings(prev => ({
          ...prev,
          ...JSON.parse(saved)
        }));
      } catch (err) {
        console.error('Error loading settings:', err);
      }
    }
    setLoading(false);
  }, []);

  // Save to localStorage whenever settings change
  useEffect(() => {
    if (!loading) {
      localStorage.setItem('elite-trader-settings', JSON.stringify(settings));
      
      // Show save indicator
      setSaved(true);
      const timer = setTimeout(() => setSaved(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [settings, loading]);

  const updateSetting = (key, value) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const updateSettings = (updates) => {
    setSettings(prev => ({
      ...prev,
      ...updates
    }));
  };

  const resetToDefaults = () => {
    if (confirm('Reset all settings to defaults? This cannot be undone.')) {
      setSettings(DEFAULT_SETTINGS);
    }
  };

  const maskApiKey = (key) => {
    if (!key) return '';
    const visible = key.substring(0, 4);
    const hidden = '*'.repeat(Math.max(0, key.length - 8));
    const end = key.substring(key.length - 4);
    return `${visible}${hidden}${end}`;
  };

  const value = {
    settings,
    updateSetting,
    updateSettings,
    resetToDefaults,
    maskApiKey,
    saved,
    loading
  };

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within SettingsProvider');
  }
  return context;
}
