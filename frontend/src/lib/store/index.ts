// frontend/src/lib/store/index.ts
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { wsManager } from '../api/websocket';
import {
  PriceTick,
  TradingSignal,
  ActivePosition,
  OrderBook,
  SystemHealth,
  AgentActivityLog,
  MarketRegime
} from '../types';

interface TradingState {
  // --- High-Frequency Data (Throttled) ---
  prices: Record<string, PriceTick>; // Map symbol -> PriceTick
  orderBooks: Record<string, OrderBook>; // Map symbol -> OrderBook

  // --- Low-Frequency Data (Real-time) ---
  activePositions: ActivePosition[];
  latestSignals: TradingSignal[];
  agentLogs: AgentActivityLog[];
  systemHealth: SystemHealth;
  marketRegime: MarketRegime;

  // --- UI State ---
  isConnected: boolean;
  selectedSymbol: string | null;
  activeSubscriptions: Set<string>;

  // --- Actions ---
  connect: () => void;
  disconnect: () => void;
  subscribeToSymbol: (symbol: string) => void;
  unsubscribeFromSymbol: (symbol: string) => void;
  setSelectedSymbol: (symbol: string) => void;

  // Internal batch processing (called automatically)
  processTickBuffer: () => void;
}

// Buffer for high-frequency updates to prevent React render thrashing
let priceBuffer: Map<string, PriceTick> = new Map();
let orderBookBuffer: Map<string, OrderBook> = new Map();

export const useTradingStore = create<TradingState>()(
  devtools((set, get) => ({
    // Initial State
    prices: {},
    orderBooks: {},
    activePositions: [],
    latestSignals: [],
    agentLogs: [],
    systemHealth: {
      status: 'offline',
      latencyMs: 0,
      activeAgents: 0,
      lastTick: new Date().toISOString(),
    },
    marketRegime: 'consolidation',
    isConnected: false,
    selectedSymbol: 'BTC',
    activeSubscriptions: new Set(['BTC']),

    // Actions
    connect: () => {
      if (get().isConnected) return;
      wsManager.connect();

      // Wire up WebSocket listeners
      wsManager.on('price_tick', (tick: PriceTick) => {
        // PUSH TO BUFFER - DO NOT SET STATE YET
        priceBuffer.set(tick.symbol, tick);
      });
      wsManager.on('order_book', (book: OrderBook) => {
        orderBookBuffer.set(book.symbol, book);
      });

      // Low-frequency events can update state immediately
      wsManager.on('trading_signal', (signal: TradingSignal) => {
        set((state) => ({
          latestSignals: [signal, ...state.latestSignals].slice(0, 100) // Keep last 100
        }));
      });
      wsManager.on('active_positions', (positions: ActivePosition[]) => {
        set({ activePositions: positions });
      });
      wsManager.on('system_health', (health: SystemHealth) => {
        set({ systemHealth: health });
      });
      wsManager.on('agent_activity', (log: AgentActivityLog) => {
        set((state) => ({
          agentLogs: [log, ...state.agentLogs].slice(0, 50) // Keep last 50
        }));
      });

      set({ isConnected: true });

      // Start the batch flush loop (100ms = 10fps updates)
      // This gives "cinematic" smoothness without CPU overload
      setInterval(() => {
        get().processTickBuffer();
      }, 100);
    },

    disconnect: () => {
      // wsManager.disconnect(); // If you add disconnect to WS manager
      set({ isConnected: false });
    },

    subscribeToSymbol: (symbol: string) => {
      const currentSubs = get().activeSubscriptions;
      if (!currentSubs.has(symbol)) {
        wsManager.subscribe('ticker', symbol);
        wsManager.subscribe('orderbook', symbol);

        const newSubs = new Set(currentSubs);
        newSubs.add(symbol);
        set({ activeSubscriptions: newSubs });
      }
    },

    unsubscribeFromSymbol: (symbol: string) => {
      const currentSubs = get().activeSubscriptions;
      if (currentSubs.has(symbol)) {
        wsManager.unsubscribe('ticker', symbol);
        wsManager.unsubscribe('orderbook', symbol);

        const newSubs = new Set(currentSubs);
        newSubs.delete(symbol);
        set({ activeSubscriptions: newSubs });
      }
    },

    setSelectedSymbol: (symbol: string) => {
      set({ selectedSymbol: symbol });
      // Auto-subscribe when selecting detailed view
      get().subscribeToSymbol(symbol);
    },

    processTickBuffer: () => {
      if (priceBuffer.size === 0 && orderBookBuffer.size === 0) return;

      set((state) => {
        // 1. Merge buffered prices into existing state map
        const newPrices = { ...state.prices };
        priceBuffer.forEach((value, key) => {
          newPrices[key] = value;
        });

        // 2. Merge buffered orderbooks
        const newOrderBooks = { ...state.orderBooks };
        orderBookBuffer.forEach((value, key) => {
          newOrderBooks[key] = value;
        });

        // 3. Clear buffers
        priceBuffer.clear();
        orderBookBuffer.clear();

        return { prices: newPrices, orderBooks: newOrderBooks };
      });
    },
  }))
);
