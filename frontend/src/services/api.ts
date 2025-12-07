const API_BASE_URL = 'http://localhost:8000';

export interface Signal {
  id: string;
  ticker: string;
  tier: string;
  currentPrice: number;
  netChange: number;
  percentChange: number;
  rvol: number;
  globalConfidence: number;
  direction: string;
  factors: Factor[];
  predictions: any;
  modelAgreement: number;
  volume: number;
  marketCap: number;
  timestamp: string;
}

export interface Factor {
  name: string;
  impact: number;
  type: string;
}

export interface SystemHealth {
  status: string;
  dbLatency: number;
  ingestionRate: number;
  tierCounts: {
    CORE: number;
    HOT: number;
    LIQUID: number;
  };
  marketRegime: string;
}

class APIClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  async fetchSignals(tier?: string, limit: number = 600): Promise<Signal[]> {
    const params = new URLSearchParams();
    if (tier) params.append('tier', tier);
    params.append('limit', limit.toString());

    const response = await fetch(`${this.baseURL}/api/signals?${params}`);
    if (!response.ok) throw new Error('Failed to fetch signals');
    return response.json();
  }

  async fetchSignalByTicker(ticker: string): Promise<Signal> {
    const response = await fetch(`${this.baseURL}/api/signals/${ticker}`);
    if (!response.ok) throw new Error(`Signal not found for ${ticker}`);
    return response.json();
  }

  async fetchSystemHealth(): Promise<SystemHealth> {
    const response = await fetch(`${this.baseURL}/api/signals/health/system`);
    if (!response.ok) throw new Error('Failed to fetch system health');
    return response.json();
  }

  async fetchTierCount(tier: string): Promise<{ tier: string; count: number }> {
    const response = await fetch(`${this.baseURL}/api/signals/tiers/${tier}/count`);
    if (!response.ok) throw new Error(`Failed to fetch tier count for ${tier}`);
    return response.json();
  }
}

export const apiClient = new APIClient();
