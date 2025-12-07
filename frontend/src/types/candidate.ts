export interface Candidate {
  id: string;
  ticker: string;
  tier: string;
  currentPrice: number;
  netChange: number;
  percentChange: number;
  rvol: number;
  globalConfidence: number;
  direction: string;
  factors: any[];
  predictions: any;
  modelAgreement: number;
  volume: number;
  marketCap: number;
  timestamp: string;
}
