import { useState, useEffect } from 'react';

interface Settings {
  apiKeys: {
    unusualWhales: string;
    finviz: string;
    anthropic: string;
  };
  scanner: {
    interval: number;
    minConfidence: number;
  };
  trading: {
    startingCapital: number;
    maxRiskPerTrade: number;
    maxPositions: number;
  };
}

const DEFAULT_SETTINGS: Settings = {
  apiKeys: {
    unusualWhales: '',
    finviz: '',
    anthropic: ''
  },
  scanner: {
    interval: 15,
    minConfidence: 70
  },
  trading: {
    startingCapital: 1000000,
    maxRiskPerTrade: 2.0,
    maxPositions: 15
  }
};

export const useSettings = () => {
  const [settings, setSettings] = useState<Settings>(() => {
    const saved = localStorage.getItem('elite-trading-settings');
    return saved ? JSON.parse(saved) : DEFAULT_SETTINGS;
  });

  const saveSettings = (newSettings: Settings) => {
    setSettings(newSettings);
    localStorage.setItem('elite-trading-settings', JSON.stringify(newSettings));
  };

  const resetSettings = () => {
    setSettings(DEFAULT_SETTINGS);
    localStorage.removeItem('elite-trading-settings');
  };

  return { settings, saveSettings, resetSettings };
};
