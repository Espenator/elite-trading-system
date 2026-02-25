// lib/types/index.ts

export type MarketRegime = 'bullish_trend' | 'bearish_trend' | 'high_volatility' | 'consolidation';

export interface SystemHealth {
  status: 'online' | 'degraded' | 'offline';
  latencyMs: number;
  activeAgents: number;
  lastTick: string;
}

export interface PriceTick {
  symbol: string;
  price: number;
  change24h: number;
  volume24h: number;
  timestamp: string;
}

export interface OHLCV {
  time: number; // Unix timestamp for Lightweight Charts
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ShapFactor {
  feature: string;
  contribution: number;
  direction: 'bullish' | 'bearish' | 'neutral';
}

export interface PredictionAgent {
  id: string;
  name: string;
  horizon: '1H' | '1D' | '1W';
  prediction: number;
  confidence: number;
  shapFactors: ShapFactor[];
}

export interface TradingSignal {
  id: string;
  symbol: string;
  type: 'compression' | 'ignition' | 'momentum_breakout';
  direction: 'long' | 'short';
  entryPrice: number;
  stopLoss: number;
  takeProfit: number;
  confidence: number;
  timestamp: string;
  agents: PredictionAgent[];
}

export interface ActivePosition {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  size: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnL: number;
  unrealizedPnLPercent: number;
  marginUsed: number;
  duration: string;
}

export interface OrderBookLevel {
  price: number;
  size: number;
  total: number;
}

export interface OrderBook {
  symbol: string;
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  timestamp: string;
}

export interface AgentActivityLog {
  id: string;
  agentId: string;
  action: string;
  details: string;
  timestamp: string;
  status: 'success' | 'processing' | 'error';
}
