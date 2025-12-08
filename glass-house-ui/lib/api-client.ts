// Elite Trader API Client
// Handles all backend communication

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Signal {
  id: string;
  ticker: string;
  currentPrice: number;
  percentChange: number;
  globalConfidence: number;
  direction: string;
  volume: number;
  marketCap: number;
  tier?: 'Core' | 'Hot' | 'Liquid';
  rvol?: number;
  timestamp?: string;
  catalyst?: string;
}

export interface ChartData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface Prediction {
  ticker: string;
  timeframe: '1h' | '1d' | '1w';
  predictedPrice: number;
  confidence: number;
  upperBound: number;
  lowerBound: number;
}

class APIClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = ``;
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      });

      if (!response.ok) {
        throw new Error(`API Error:  `);
      }

      return await response.json();
    } catch (error) {
      console.error('API Request failed:', error);
      throw error;
    }
  }

  // Get all signals
  async getSignals(limit: number = 100): Promise<Signal[]> {
    return this.request<Signal[]>(`/api/signals/?limit=`);
  }

  // Get signals by tier
  async getSignalsByTier(tier: string): Promise<Signal[]> {
    return this.request<Signal[]>(`/api/signals/tier/`);
  }

  // Get chart data for a ticker
  async getChartData(ticker: string, interval: string = '1d'): Promise<ChartData[]> {
    return this.request<ChartData[]>(`/api/chart/?interval=`);
  }

  // Get ML predictions for a ticker
  async getPredictions(ticker: string): Promise<Prediction[]> {
    return this.request<Prediction[]>(`/api/predictions/`);
  }

  // Get system health
  async getHealth(): Promise<{ status: string; latency: number }> {
    return this.request('/api/health');
  }

  // Execute trade (paper trading)
  async executeTrade(ticker: string, side: 'buy' | 'sell', quantity: number): Promise<any> {
    return this.request('/api/execute', {
      method: 'POST',
      body: JSON.stringify({ ticker, side, quantity }),
    });
  }
}

export const apiClient = new APIClient();
