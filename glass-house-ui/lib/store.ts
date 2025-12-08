// Elite Trader State Management
// Zustand store for global application state

import { create } from 'zustand';
import { Signal } from './api-client';

interface EliteTraderStore {
  // Signals
  signals: Signal[];
  setSignals: (signals: Signal[]) => void;
  addSignal: (signal: Signal) => void;
  updateSignal: (id: string, updates: Partial<Signal>) => void;

  // Selected ticker
  selectedTicker: string;
  setSelectedTicker: (ticker: string) => void;

  // Chart timeframe
  timeframe: '1D' | '1H' | '15M' | '5M';
  setTimeframe: (timeframe: '1D' | '1H' | '15M' | '5M') => void;

  // System status
  systemStatus: 'active' | 'degraded' | 'offline';
  latency: number;
  setSystemStatus: (status: 'active' | 'degraded' | 'offline', latency?: number) => void;

  // Filters
  tierFilter: 'all' | 'Core' | 'Hot' | 'Liquid';
  setTierFilter: (tier: 'all' | 'Core' | 'Hot' | 'Liquid') => void;

  minConfidence: number;
  setMinConfidence: (confidence: number) => void;

  // UI State
  isPaused: boolean;
  togglePause: () => void;

  soundEnabled: boolean;
  toggleSound: () => void;
}

export const useEliteStore = create<EliteTraderStore>((set) => ({
  // Initial state
  signals: [],
  selectedTicker: 'SPY',
  timeframe: '1D',
  systemStatus: 'active',
  latency: 12,
  tierFilter: 'all',
  minConfidence: 0,
  isPaused: false,
  soundEnabled: true,

  // Actions
  setSignals: (signals) => set({ signals }),
  
  addSignal: (signal) => set((state) => ({
    signals: [signal, ...state.signals].slice(0, 1000), // Keep max 1000 signals
  })),

  updateSignal: (id, updates) => set((state) => ({
    signals: state.signals.map(s => s.id === id ? { ...s, ...updates } : s),
  })),

  setSelectedTicker: (ticker) => set({ selectedTicker: ticker }),
  
  setTimeframe: (timeframe) => set({ timeframe }),
  
  setSystemStatus: (status, latency) => set({ 
    systemStatus: status,
    ...(latency !== undefined && { latency })
  }),

  setTierFilter: (tier) => set({ tierFilter: tier }),
  
  setMinConfidence: (confidence) => set({ minConfidence: confidence }),
  
  togglePause: () => set((state) => ({ isPaused: !state.isPaused })),
  
  toggleSound: () => set((state) => ({ soundEnabled: !state.soundEnabled })),
}));
