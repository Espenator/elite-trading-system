// Mock signals - Top 20 signals
export const mockSignals = [
  {
    id: '1',
    ticker: 'NVDA',
    company: 'NVIDIA Corporation',
    direction: 'LONG',
    compositeScore: 92,
    fractalScore: 95,
    staircaseScore: 88,
    volumeScore: 91,
    mlConfidence: 87,
    entryPrice: 875.50,
    stopPrice: 858.20,
    target1: 910.00,
    target2: 945.00,
    riskReward: 2.0,
    setupType: 'FRACTAL_MOMENTUM_BREAKOUT',
    timestamp: new Date(),
    sector: 'Technology'
  },
  {
    id: '2',
    ticker: 'AMD',
    company: 'Advanced Micro Devices',
    direction: 'LONG',
    compositeScore: 88,
    fractalScore: 90,
    staircaseScore: 85,
    volumeScore: 88,
    mlConfidence: 82,
    entryPrice: 178.25,
    stopPrice: 174.50,
    target1: 185.00,
    target2: 192.00,
    riskReward: 1.8,
    setupType: 'STAIRCASE_CONTINUATION',
    timestamp: new Date(),
    sector: 'Technology'
  },
  {
    id: '3',
    ticker: 'TSLA',
    company: 'Tesla Inc',
    direction: 'LONG',
    compositeScore: 85,
    fractalScore: 88,
    staircaseScore: 82,
    volumeScore: 85,
    mlConfidence: 79,
    entryPrice: 245.80,
    stopPrice: 238.50,
    target1: 260.00,
    target2: 275.00,
    riskReward: 1.9,
    setupType: 'OVERSOLD_BOUNCE',
    timestamp: new Date(),
    sector: 'Consumer Cyclical'
  },
  {
    id: '4',
    ticker: 'META',
    company: 'Meta Platforms',
    direction: 'LONG',
    compositeScore: 83,
    fractalScore: 85,
    staircaseScore: 80,
    volumeScore: 84,
    mlConfidence: 76,
    entryPrice: 505.25,
    stopPrice: 492.00,
    target1: 525.00,
    target2: 545.00,
    riskReward: 1.5,
    setupType: 'FRACTAL_MOMENTUM_BREAKOUT',
    timestamp: new Date(),
    sector: 'Technology'
  },
  {
    id: '5',
    ticker: 'COIN',
    company: 'Coinbase Global',
    direction: 'LONG',
    compositeScore: 81,
    fractalScore: 83,
    staircaseScore: 78,
    volumeScore: 82,
    mlConfidence: 74,
    entryPrice: 185.40,
    stopPrice: 178.00,
    target1: 198.00,
    target2: 210.00,
    riskReward: 1.7,
    setupType: 'EXPLOSIVE_GROWTH',
    timestamp: new Date(),
    sector: 'Technology'
  },
  {
    id: '6',
    ticker: 'PLTR',
    company: 'Palantir Technologies',
    direction: 'LONG',
    compositeScore: 79,
    fractalScore: 81,
    staircaseScore: 76,
    volumeScore: 80,
    mlConfidence: 72,
    entryPrice: 24.85,
    stopPrice: 23.90,
    target1: 26.50,
    target2: 28.00,
    riskReward: 1.7,
    setupType: 'STAIRCASE_CONTINUATION',
    timestamp: new Date(),
    sector: 'Technology'
  },
  {
    id: '7',
    ticker: 'SMCI',
    company: 'Super Micro Computer',
    direction: 'LONG',
    compositeScore: 77,
    fractalScore: 80,
    staircaseScore: 74,
    volumeScore: 78,
    mlConfidence: 70,
    entryPrice: 785.00,
    stopPrice: 755.00,
    target1: 835.00,
    target2: 885.00,
    riskReward: 1.7,
    setupType: 'FRACTAL_MOMENTUM_BREAKOUT',
    timestamp: new Date(),
    sector: 'Technology'
  },
  {
    id: '8',
    ticker: 'MSTR',
    company: 'MicroStrategy',
    direction: 'SHORT',
    compositeScore: 75,
    fractalScore: 78,
    staircaseScore: 72,
    volumeScore: 76,
    mlConfidence: 68,
    entryPrice: 1850.00,
    stopPrice: 1920.00,
    target1: 1750.00,
    target2: 1650.00,
    riskReward: 1.4,
    setupType: 'REVERSAL_PATTERN',
    timestamp: new Date(),
    sector: 'Technology'
  },
  {
    id: '9',
    ticker: 'GOOGL',
    company: 'Alphabet Inc',
    direction: 'LONG',
    compositeScore: 73,
    fractalScore: 75,
    staircaseScore: 70,
    volumeScore: 74,
    mlConfidence: 66,
    entryPrice: 175.20,
    stopPrice: 171.00,
    target1: 182.00,
    target2: 188.00,
    riskReward: 1.6,
    setupType: 'STAIRCASE_CONTINUATION',
    timestamp: new Date(),
    sector: 'Technology'
  },
  {
    id: '10',
    ticker: 'MSFT',
    company: 'Microsoft',
    direction: 'LONG',
    compositeScore: 71,
    fractalScore: 73,
    staircaseScore: 68,
    volumeScore: 72,
    mlConfidence: 64,
    entryPrice: 415.80,
    stopPrice: 408.00,
    target1: 428.00,
    target2: 440.00,
    riskReward: 1.6,
    setupType: 'FRACTAL_MOMENTUM_BREAKOUT',
    timestamp: new Date(),
    sector: 'Technology'
  }
];

// Mock active positions
export const mockPositions = [
  {
    id: '1',
    ticker: 'NVDA',
    direction: 'LONG',
    shares: 50,
    entryPrice: 865.00,
    currentPrice: 878.50,
    stopPrice: 848.00,
    target1: 910.00,
    pnlDollars: 675.00,
    pnlPercent: 1.56,
    rMultiple: 0.79,
    entryTime: new Date(Date.now() - 3600000 * 2),
    holdingHours: 2.0
  },
  {
    id: '2',
    ticker: 'AMD',
    direction: 'LONG',
    shares: 100,
    entryPrice: 175.50,
    currentPrice: 178.90,
    stopPrice: 171.00,
    target1: 185.00,
    pnlDollars: 340.00,
    pnlPercent: 1.94,
    rMultiple: 0.76,
    entryTime: new Date(Date.now() - 3600000 * 4.5),
    holdingHours: 4.5
  },
  {
    id: '3',
    ticker: 'PLTR',
    direction: 'LONG',
    shares: 500,
    entryPrice: 24.20,
    currentPrice: 24.75,
    stopPrice: 23.50,
    target1: 26.00,
    pnlDollars: 275.00,
    pnlPercent: 2.27,
    rMultiple: 0.79,
    entryTime: new Date(Date.now() - 3600000 * 1),
    holdingHours: 1.0
  }
];

// Mock recent trades
export const mockTrades = [
  {
    id: '1',
    ticker: 'META',
    direction: 'LONG',
    entryPrice: 495.00,
    exitPrice: 512.50,
    shares: 30,
    pnlDollars: 525.00,
    pnlPercent: 3.54,
    rMultiple: 1.5,
    entryTime: new Date(Date.now() - 86400000),
    exitTime: new Date(Date.now() - 82800000),
    exitReason: 'TARGET_HIT',
    isWinner: true,
    mlWasCorrect: true
  },
  {
    id: '2',
    ticker: 'TSLA',
    direction: 'LONG',
    entryPrice: 248.00,
    exitPrice: 242.50,
    shares: 50,
    pnlDollars: -275.00,
    pnlPercent: -2.22,
    rMultiple: -0.8,
    entryTime: new Date(Date.now() - 172800000),
    exitTime: new Date(Date.now() - 169200000),
    exitReason: 'STOP_HIT',
    isWinner: false,
    mlWasCorrect: false
  },
  {
    id: '3',
    ticker: 'COIN',
    direction: 'LONG',
    entryPrice: 178.00,
    exitPrice: 192.50,
    shares: 75,
    pnlDollars: 1087.50,
    pnlPercent: 8.15,
    rMultiple: 2.1,
    entryTime: new Date(Date.now() - 259200000),
    exitTime: new Date(Date.now() - 252000000),
    exitReason: 'TARGET_HIT',
    isWinner: true,
    mlWasCorrect: true
  },
  {
    id: '4',
    ticker: 'GOOGL',
    direction: 'LONG',
    entryPrice: 172.50,
    exitPrice: 178.20,
    shares: 60,
    pnlDollars: 342.00,
    pnlPercent: 3.30,
    rMultiple: 1.2,
    entryTime: new Date(Date.now() - 345600000),
    exitTime: new Date(Date.now() - 338400000),
    exitReason: 'TARGET_HIT',
    isWinner: true,
    mlWasCorrect: true
  },
  {
    id: '5',
    ticker: 'SMCI',
    direction: 'LONG',
    entryPrice: 795.00,
    exitPrice: 775.00,
    shares: 15,
    pnlDollars: -300.00,
    pnlPercent: -2.52,
    rMultiple: -1.0,
    entryTime: new Date(Date.now() - 432000000),
    exitTime: new Date(Date.now() - 424800000),
    exitReason: 'STOP_HIT',
    isWinner: false,
    mlWasCorrect: false
  }
];

// Mock market regime
export const mockRegime = {
  regime: 'GREEN',
  vixLevel: 14.25,
  vixRsi: 35,
  breadth: 1.45,
  spyChange: 0.85,
  qqqChange: 1.12,
  riskPerTrade: 2.0,
  maxPositions: 15
};

// Mock ML model stats
export const mockMLStats = {
  modelVersion: 'xgboost-v2.3',
  accuracy: 67.5,
  auc: 72.3,
  sharpeRatio: 1.85,
  trainingSamples: 125000,
  lastTrained: new Date(Date.now() - 172800000),
  isProduction: true,
  topFeatures: [
    { name: 'rsi_14', importance: 0.15 },
    { name: 'volume_ratio', importance: 0.12 },
    { name: 'price_vs_sma20', importance: 0.11 },
    { name: 'macd_histogram', importance: 0.09 },
    { name: 'bb_position', importance: 0.08 },
    { name: 'atr_14', importance: 0.07 },
    { name: 'adx_14', importance: 0.06 },
    { name: 'correlation_spy', importance: 0.05 }
  ]
};

// Mock performance stats
export const mockPerformance = {
  todayPnl: 1290.00,
  weekPnl: 4850.00,
  monthPnl: 18750.00,
  totalTrades: 47,
  winners: 31,
  losers: 16,
  winRate: 65.96,
  avgRMultiple: 1.45,
  largestWin: 2850.00,
  largestLoss: -1200.00,
  maxDrawdown: 4.2,
  sharpeRatio: 1.85
};

// Mock system status
export const mockSystemStatus = {
  isConnected: true,
  lastUpdate: new Date(),
  nextInferenceCycle: new Date(Date.now() + 900000),
  activeSymbols: 487,
  signalsGenerated: 42,
  modelAccuracy: 67.5
};

// Mock equity curve data
export const mockEquityCurve = Array.from({ length: 30 }, (_, i) => ({
  date: new Date(Date.now() - (29 - i) * 86400000).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
  equity: 100000 + Math.random() * 5000 + i * 600,
  benchmark: 100000 + i * 300
}));

// Mock win rate history
export const mockWinRateHistory = Array.from({ length: 12 }, (_, i) => ({
  week: `W${i + 1}`,
  winRate: 55 + Math.random() * 20,
  trades: 10 + Math.floor(Math.random() * 15)
}));
