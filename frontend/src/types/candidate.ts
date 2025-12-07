export interface Candidate {
  id: string;
  ticker: string;
  companyName: string;
  price: number;
  change: number;
  volume: number;
  rvol: number;
  score: number;
  aiConfidence: number;
  modelAgreement: number;
  tier: 'Core' | 'Hot' | 'Liquid';
  structure: 'HHHL' | 'LLLH' | 'NEUTRAL';
  timestamp: number;
  priceHistory: number[];
  velezScores: {
    weekly: number;
    daily: number;
    fourHour: number;
    oneHour: number;
  };
  darkPoolBlocks: number;
  catalyst: string;
  status?: 'NEW' | 'WATCHING' | 'TRADED' | 'IGNORED';
}
