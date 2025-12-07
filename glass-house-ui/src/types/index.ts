export type Tier = 'CORE' | 'LIQUID' | 'HOT';
export type TimeFrame = '1H' | '1D' | '1W';
export type FactorType = 'flow' | 'technical' | 'macro';
export type Direction = 'long' | 'short';

export interface Factor {
  name: string;
  impact: number;
  type: FactorType;
}

export interface Prediction {
  horizon: TimeFrame;
  priceTarget: number;
  confidence: number;
  lowerBound: number;
  upperBound: number;
}

export interface Signal {
  id: string;
  ticker: string;
  tier: Tier;
  currentPrice: number;
  netChange: number;
  percentChange: number;
  rvol: number;
  globalConfidence: number;
  direction: Direction;
  factors: Factor[];
  predictions: Record<TimeFrame, Prediction>;
  modelAgreement: number;
  volume: number;
  marketCap: number;
  timestamp: string;
}

export interface SystemHealth {
  status: 'operational' | 'degraded' | 'down';
  dbLatency: number;
  ingestionRate: number;
  tierCounts: Record<Tier, number>;
  marketRegime: string;
}
