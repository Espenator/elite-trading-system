/**
 * Zustand Store - Global state management
 * All state is fed from backend via API + WebSocket
 */

import { create } from 'zustand';
import { apiClient } from '@/lib/api/client';
import { wsManager } from '@/lib/api/websocket';
import type { Market, Signal, Prediction } from '@/lib/types';

interface StoreState {
  // State
  isLoading: boolean;
  error: string | null;
  selectedSymbol: string;
  prices: Record<string, Market>;
  signals: Record<string, Signal>;
  predictions: Record<string, Prediction>;
  wsConnected: boolean;
  backendOnline: boolean;

  // Actions
  initialize: (symbols: string[]) => Promise<void>;
  checkBackendHealth: () => Promise<boolean>;
  subscribeToSymbol: (symbol: string) => void;
  unsubscribeFromSymbol: (symbol: string) => void;
  setSelectedSymbol: (symbol: string) => void;
}

export const useStore = create<StoreState>((set, get) => ({
  // Initial state
  isLoading: true,
  error: null,
  selectedSymbol: 'BTC',
  prices: {},
  signals: {},
  predictions: {},
  wsConnected: false,
  backendOnline: false,

  // Check backend health
  checkBackendHealth: async () => {
    try {
      const healthy = await apiClient.healthCheck();
      set({ backendOnline: healthy });
      return healthy;
    } catch (error) {
      set({ backendOnline: false });
      return false;
    }
  },

  // Initialize store with symbols
  initialize: async (symbols: string[]) => {
    set({ isLoading: true, error: null });

    try {
      // Connect WebSocket
      const wsConnected = await wsManager.connect();
      set({ wsConnected });

      // Fetch initial data
      const [pricesData, signalsData] = await Promise.all([
        apiClient.getPrices(symbols),
        apiClient.getSignals(symbols),
      ]);

      // Transform and set data
      const prices: Record<string, Market> = {};
      Object.entries(pricesData).forEach(([symbol, data]: any) => {
        prices[symbol] = {
          symbol,
          price: data.price,
          marketCap: data.market_cap,
          change24h: data.price * (data.change_percent_24h / 100),
          changePercent24h: data.change_percent_24h,
          volume24h: 0,
          high24h: 0,
          low24h: 0,
          timestamp: data.timestamp,
        };
      });

      const signals: Record<string, Signal> = {};
      Object.entries(signalsData).forEach(([symbol, data]: any) => {
        signals[symbol] = data;
      });

      set({
        prices,
        signals,
        isLoading: false,
      });

      // Subscribe to WebSocket updates
      symbols.forEach(symbol => {
        wsManager.subscribe(symbol, ['signal', 'price', 'prediction']);
      });

      // Handle real-time updates
      wsManager.on('price', (data: Market) => {
        set(state => ({
          prices: {
            ...state.prices,
            [data.symbol]: data,
          },
        }));
      });

      wsManager.on('signal', (data: Signal) => {
        set(state => ({
          signals: {
            ...state.signals,
            [data.symbol]: data,
          },
        }));
      });

      wsManager.on('prediction', (data: Prediction) => {
        set(state => ({
          predictions: {
            ...state.predictions,
            [data.symbol]: data,
          },
        }));
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Initialization failed';
      set({
        error: message,
        isLoading: false,
      });
    }
  },

  // Subscribe to symbol
  subscribeToSymbol: (symbol: string) => {
    wsManager.subscribe(symbol, ['signal', 'price', 'prediction']);
  },

  // Unsubscribe from symbol
  unsubscribeFromSymbol: (symbol: string) => {
    wsManager.unsubscribe(symbol);
  },

  // Set selected symbol
  setSelectedSymbol: (symbol: string) => {
    set({ selectedSymbol: symbol });
  },
}));
