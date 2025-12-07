import { create } from 'zustand';
import { Signal, SystemHealth } from '../types';
import { signalsApi } from '../lib/api-client';

interface TradingStore {
  signals: Signal[];
  selectedSignal: Signal | null;
  systemHealth: SystemHealth | null;
  isLoading: boolean;
  error: string | null;
  
  fetchSignals: (tier?: string) => Promise<void>;
  fetchSystemHealth: () => Promise<void>;
  selectSignal: (signal: Signal | null) => void;
  refreshData: () => Promise<void>;
}

export const useTradingStore = create<TradingStore>((set, get) => ({
  signals: [],
  selectedSignal: null,
  systemHealth: null,
  isLoading: false,
  error: null,

  fetchSignals: async (tier?: string) => {
    set({ isLoading: true, error: null });
    try {
      const signals = await signalsApi.getAll(tier);
      set({ signals, isLoading: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to fetch signals',
        isLoading: false 
      });
    }
  },

  fetchSystemHealth: async () => {
    try {
      const systemHealth = await signalsApi.getSystemHealth();
      set({ systemHealth });
    } catch (error) {
      console.error('Failed to fetch system health:', error);
    }
  },

  selectSignal: (signal: Signal | null) => {
    set({ selectedSignal: signal });
  },

  refreshData: async () => {
    const { fetchSignals, fetchSystemHealth } = get();
    await Promise.all([
      fetchSignals(),
      fetchSystemHealth()
    ]);
  },
}));
