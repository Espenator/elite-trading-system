/**
 * Default data structures for dashboard components.
 * These provide empty/zero defaults so the UI renders gracefully
 * before real API data arrives. NO fabricated numbers.
 *
 * TODO: Each component should fetch from the backend API via
 * hooks (usePositions, usePerformance, etc.) and pass data as props.
 * Once API integration is complete, this file can be removed.
 */

// Signals - populated by backend /api/v1/signals endpoint
export const mockSignals = [];

// Performance summary - populated by backend /api/v1/portfolio/performance
export const mockPerformance = {
  todayPnl: 0,
  weekPnl: 0,
  monthPnl: 0,
  totalPnl: 0,
  winRate: 0,
  avgRMultiple: 0,
  maxDrawdown: 0,
  totalTrades: 0,
  winners: 0,
  losers: 0,
};

// Active positions - populated by Alpaca /api/v1/portfolio/positions
export const mockPositions = [];

// ML model stats - populated by backend /api/v1/ml/status
export const mockMLStats = {
  modelName: 'Awaiting training',
  accuracy: 0,
  precision: 0,
  recall: 0,
  f1Score: 0,
  lastTrained: null,
  trainingStatus: 'not_started',
  totalPredictions: 0,
  correctPredictions: 0,
};

// Equity curve data - populated by backend /api/v1/portfolio/equity-curve
export const mockEquityCurve = [];

// Recent trades - populated by backend /api/v1/portfolio/trades
export const mockTrades = [];

// Market regime - populated by backend /api/v1/risk/regime
export const mockRegime = {
  current: 'unknown',
  confidence: 0,
  description: 'Connect API keys in Settings to enable market regime detection',
  indicators: {},
};

// Weekly performance - populated by backend
export const mockWeeklyPerformance = [];
