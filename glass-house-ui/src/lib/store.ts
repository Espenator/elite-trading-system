import { create } from 'zustand';

export interface MarketSignal {
  id: string;
  symbol: string;
  current_price: number;
  change: number;
  confidence: number;
  direction: 'LONG' | 'SHORT';
  tier: 'CORE' | 'HOT' | 'LIQUID';
  rvol: number;
  volume: string;
  timestamp: string;
  key_factors: string[];
}

interface SystemHealth {
  apiConnected: boolean;
  wsConnected: boolean;
  lastUpdate: string;
  signalCount: number;
}

interface MLConfig {
  confidenceThreshold: number;
  volumeWeight: number;
  rvolWeight: number;
  darkPoolWeight: number;
  optionsFlowWeight: number;
}

interface MarketStore {
  allSignals: MarketSignal[];
  coreSignals: MarketSignal[];
  hotSignals: MarketSignal[];
  liquidSignals: MarketSignal[];
  selectedSignal: MarketSignal | null;
  systemHealth: SystemHealth;
  mlConfig: MLConfig;
  setSelectedSignal: (signal: MarketSignal | null) => void;
  updateSignals: (signals: MarketSignal[]) => void;
  fetchSignals: () => Promise<void>;
  updateSystemHealth: (health: Partial<SystemHealth>) => void;
  updateMLConfig: (config: Partial<MLConfig>) => void;
  setConnectionStatus: (status: 'connected' | 'disconnected' | 'error') => void;
}

export const useMarketStore = create<MarketStore>((set, get) => ({
  allSignals: [],
  coreSignals: [],
  hotSignals: [],
  liquidSignals: [],
  selectedSignal: null,
  systemHealth: { apiConnected: false, wsConnected: false, lastUpdate: new Date().toISOString(), signalCount: 0 },
  mlConfig: { confidenceThreshold: 80, volumeWeight: 30, rvolWeight: 25, darkPoolWeight: 25, optionsFlowWeight: 20 },
  setSelectedSignal: (signal) => set({ selectedSignal: signal }),
  updateSignals: (signals) => {
    const coreSignals = signals.filter(s => s.tier === 'CORE');
    const hotSignals = signals.filter(s => s.tier === 'HOT').slice(0, 20);
    const liquidSignals = signals.filter(s => s.tier === 'LIQUID').slice(0, 40);
    set({ allSignals: signals, coreSignals, hotSignals, liquidSignals });
  },
  fetchSignals: async () => {
    try {
      const response = await fetch('http://localhost:8000/api/signals?limit=100');
      if (!response.ok) throw new Error('Failed to fetch signals');
      const data = await response.json();
      const signals: MarketSignal[] = data.signals || [];
      get().updateSignals(signals);
      set((state) => ({ systemHealth: { ...state.systemHealth, apiConnected: true, lastUpdate: new Date().toISOString(), signalCount: signals.length } }));
    } catch (error) {
      console.error('Error fetching signals:', error);
      set((state) => ({ systemHealth: { ...state.systemHealth, apiConnected: false } }));
    }
  },
  updateSystemHealth: (health) => set((state) => ({ systemHealth: { ...state.systemHealth, ...health } })),
  updateMLConfig: (config) => set((state) => ({ mlConfig: { ...state.mlConfig, ...config } })),
  setConnectionStatus: (status) => set((state) => ({ systemHealth: { ...state.systemHealth, wsConnected: status === 'connected' } })),
}));
