// lib/types/index.ts
// Embodier.ai Trading System - Core Type Definitions
// All data structures for real API payloads (zero mock data)

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

export interface KPICard {
  label: string;
  value: string | number;
  change?: number;
  changePercent?: number;
  icon?: string;
  color?: 'success' | 'danger' | 'warning' | 'info';
}

export interface EquityCurvePoint {
  time: number;
  value: number;
  drawdown?: number;
}

export interface PerformanceMetrics {
  totalReturn: number;
  sharpeRatio: number;
  sortinoRatio: number;
  maxDrawdown: number;
  winRate: number;
  profitFactor: number;
  calmarRatio: number;
  beta: number;
  alpha: number;
  informationRatio: number;
  treynorRatio: number;
  omega: number;
}

export interface BacktestResult {
  id: string;
  strategyName: string;
  startDate: string;
  endDate: string;
  metrics: PerformanceMetrics;
  equityCurve: EquityCurvePoint[];
  trades: TradeRecord[];
}

export interface TradeRecord {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  entryPrice: number;
  exitPrice: number;
  entryTime: string;
  exitTime: string;
  pnl: number;
  pnlPercent: number;
  duration: string;
  signalSource: string;
}

export interface RiskMetrics {
  portfolioVaR: number;
  beta: number;
  sortino: number;
  maxDrawdown: number;
  sharpe: number;
  concentration: number;
  liquidityScore: number;
  riskScore: 'Low' | 'Medium' | 'High' | 'Critical';
  calmar: number;
  treynor: number;
  omega: number;
  tailRisk: number;
  var99: number;
  informationRatio: number;
}

export interface MLModel {
  id: string;
  name: string;
  accuracy: number;
  f1Score: number;
  precision: number;
  recall: number;
  aucRoc: number;
  trainingTime: string;
  lastRetrained: string;
  status: 'active' | 'training' | 'inactive';
  confidence: number;
}

export interface FeatureImportance {
  feature: string;
  importance: number;
  shapValue: number;
}

export interface StressTestScenario {
  name: string;
  impact: number;
  probability: number;
  description: string;
}

export interface CorrelationMatrix {
  assets: string[];
  values: number[][];
}

export interface MonteCarloPath {
  percentile: number;
  values: number[];
}

export interface AgentNode {
  id: string;
  name: string;
  type: 'detector' | 'predictor' | 'executor' | 'risk_manager';
  status: 'active' | 'paused' | 'error';
  accuracy: number;
  lastSignal: string;
  connections: string[];
}

export interface AppSettings {
  alpacaApiKey: string;
  alpacaSecretKey: string;
  alpacaEndpoint: 'paper' | 'live';
  defaultOrderType: 'market' | 'limit' | 'stop' | 'stop_limit';
  maxPositionSize: number;
  maxDailyLoss: number;
  maxDrawdown: number;
  enableAutoTrading: boolean;
  enableNotifications: boolean;
  notificationEmail: string;
  theme: 'dark' | 'light';
  timezone: string;
  refreshInterval: number;
}

export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
  channel?: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: string;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}
