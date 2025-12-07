/**
 * Type Definitions - Shared types across application
 */

export interface Market {
  symbol: string;
  price: number;
  marketCap: number;
  change24h: number;
  changePercent24h: number;
  volume24h: number;
  high24h: number;
  low24h: number;
  timestamp: number;
}

export interface Signal {
  symbol: string;
  type: 'compression' | 'ignition' | 'neutral' | 'bearish';
  strength: number;
  timestamp: number;
  details?: string;
  volumeIncrease?: number;
  volatilityChange?: number;
}

export interface Prediction {
  symbol: string;
  timeframe: '1h' | '1d' | '1w';
  direction: 'up' | 'down' | 'neutral';
  confidence: number;
  target?: number;
  timestamp: number;
}

export interface Indicator {
  symbol: string;
  rsi: number;
  macd: number;
  macdSignal: number;
  bollingerUpper: number;
  bollingerLower: number;
  bollingerMiddle: number;
  volumeMa: number;
  timestamp: number;
}

export interface PortfolioPosition {
  symbol: string;
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  profitLoss: number;
  profitLossPercent: number;
  allocation: number;
}

export interface Portfolio {
  totalValue: number;
  totalProfit: number;
  totalProfitPercent: number;
  positions: PortfolioPosition[];
  timestamp: number;
}

export interface AlertRule {
  id: string;
  symbol: string;
  type: 'price' | 'signal' | 'prediction';
  condition: string;
  enabled: boolean;
  notified: boolean;
  createdAt: number;
}

export interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
}

export type TimeFrame = '1m' | '5m' | '15m' | '30m' | '1h' | '4h' | '1d' | '1w' | '1M';

export interface ChartData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}
