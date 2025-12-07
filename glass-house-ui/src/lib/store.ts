import { create } from "zustand";
import { apiService } from "./api-service";

export interface MarketSignal {
  id: string;
  ticker: string;
  tier: "CORE" | "HOT" | "LIQUID";
  currentPrice: number;
  netChange: number;
  percentChange: number;
  rvol: number;
  globalConfidence: number;
  direction: "long" | "short";
  volume: number;
  marketCap: number;
  factors: any[];
  predictions: any;
  modelAgreement: number;
  timestamp: string;
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
  setConnectionStatus: (status: "connected" | "disconnected") => void;
  connectWebSocket: () => void;
  disconnectWebSocket: () => void;
}

export const useMarketStore = create<MarketStore>((set, get) => ({
  allSignals: [],
  coreSignals: [],
  hotSignals: [],
  liquidSignals: [],
  selectedSignal: null,
  systemHealth: {
    apiConnected: false,
    wsConnected: false,
    lastUpdate: new Date().toISOString(),
    signalCount: 0,
  },
  mlConfig: {
    confidenceThreshold: 80,
    volumeWeight: 30,
    rvolWeight: 25,
    darkPoolWeight: 25,
    optionsFlowWeight: 20,
  },

  setSelectedSignal: (signal) => set({ selectedSignal: signal }),

  updateSignals: (signals) => {
    const coreSignals = signals.filter((s) => s.tier === "CORE");
    const hotSignals = signals.filter((s) => s.tier === "HOT").slice(0, 20);
    const liquidSignals = signals.filter((s) => s.tier === "LIQUID").slice(0, 40);
    set({
      allSignals: signals,
      coreSignals,
      hotSignals,
      liquidSignals,
    });
  },

  fetchSignals: async () => {
    try {
      const signals = await apiService.getSignals(100);
      get().updateSignals(signals);
      set((state) => ({
        systemHealth: {
          ...state.systemHealth,
          apiConnected: true,
          lastUpdate: new Date().toISOString(),
          signalCount: signals.length,
        },
      }));
    } catch (error) {
      console.error("Error fetching signals:", error);
      set((state) => ({
        systemHealth: { ...state.systemHealth, apiConnected: false },
      }));
    }
  },

  updateSystemHealth: (health) =>
    set((state) => ({
      systemHealth: { ...state.systemHealth, ...health },
    })),

  updateMLConfig: (config) =>
    set((state) => ({
      mlConfig: { ...state.mlConfig, ...config },
    })),

  setConnectionStatus: (status) =>
    set((state) => ({
      systemHealth: {
        ...state.systemHealth,
        wsConnected: status === "connected",
      },
    })),

  connectWebSocket: () => {
    apiService.connectWebSocket(
      (data) => {
        // Handle WebSocket messages
        if (data.type === "system_update") {
          set((state) => ({
            systemHealth: {
              ...state.systemHealth,
              wsConnected: true,
              lastUpdate: data.data.timestamp,
              signalCount: data.data.recentSignals?.length || 0,
            },
          }));
        }
      },
      (error) => {
        console.error("WebSocket error:", error);
        set((state) => ({
          systemHealth: { ...state.systemHealth, wsConnected: false },
        }));
      }
    );
  },

  disconnectWebSocket: () => {
    apiService.disconnectWebSocket();
    set((state) => ({
      systemHealth: { ...state.systemHealth, wsConnected: false },
    }));
  },
}));
