import { create } from 'zustand';

// Types matching your backend API
export interface Signal {
  id: string;
  ticker: string;
  tier: 'CORE' | 'HOT' | 'LIQUID';
  currentPrice: number;
  netChange: number;
  percentChange: number;
  rvol: number;
  globalConfidence: number;
  direction: 'long' | 'short';
  factors: Array<{
    name: string;
    impact: number;
    type: string;
  }>;
  predictions?: {
    '1H': {
      priceTarget: number;
      confidence: number;
    };
    '1D': {
      priceTarget: number;
      confidence: number;
    };
  };
  modelAgreement?: number;
  volume: number;
  marketCap: number;
  timestamp: string;
  mathScore?: number;
  aiScore?: number;
  compositeScore?: number;
  predictedPath?: any[];
}

export interface MarketState {
  signals: Map<string, Signal>;
  selectedSignalId: string | null;
  wsConnected: boolean;
  loading: boolean;
  error: string | null;
  coreWatchlist: string[];
  hotSignals: Signal[];
  liquidSignals: Signal[];
  systemHealth: {
    dbLatency: number;
    ingestionRate: number;
  } | null;
  criteria: {
    minCompositeScore: number;
  };
  
  // Actions
  setSignals: (signals: Signal[]) => void;
  addSignal: (signal: Signal) => void;
  selectSignal: (signalId: string | null) => void;
  setWsConnected: (connected: boolean) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  updateCriteria: (criteria: Partial<MarketState['criteria']>) => void;
}

export const useMarketStore = create<MarketState>((set) => ({
  signals: new Map(),
  selectedSignalId: null,
  wsConnected: false,
  loading: false,
  error: null,
  coreWatchlist: ['NVDA', 'AAPL', 'TSLA', 'MSFT', 'GOOGL'],
  hotSignals: [],
  liquidSignals: [],
  systemHealth: {
    dbLatency: 12,
    ingestionRate: 45,
  },
  criteria: {
    minCompositeScore: 70,
  },

  setSignals: (signalsArray) => {
    const signalsMap = new Map<string, Signal>();
    const hot: Signal[] = [];
    const liquid: Signal[] = [];
    
    signalsArray.forEach(signal => {
      signalsMap.set(signal.id, signal);
      
      if (signal.tier === 'HOT') {
        hot.push(signal);
      } else if (signal.tier === 'LIQUID') {
        liquid.push(signal);
      }
    });
    
    set({ signals: signalsMap, hotSignals: hot, liquidSignals: liquid });
  },
  
  addSignal: (signal) => set((state) => {
    const newSignals = new Map(state.signals);
    newSignals.set(signal.id, signal);
    return { signals: newSignals };
  }),
  
  selectSignal: (signalId) => set({ selectedSignalId: signalId }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  updateCriteria: (newCriteria) => set((state) => ({
    criteria: { ...state.criteria, ...newCriteria }
  })),
}));

