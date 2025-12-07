/**
 * API Client - HTTP communication with backend
 * All backend calls go through this centralized client
 */

import axios, { AxiosInstance } from 'axios';

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface Price {
  symbol: string;
  price: number;
  market_cap: number;
  change_percent_24h: number;
  timestamp: number;
}

export interface Signal {
  symbol: string;
  type: 'compression' | 'ignition' | 'neutral' | 'bearish';
  strength: number;
  timestamp: number;
  details: string;
}

export interface Prediction {
  symbol: string;
  timeframe: '1h' | '1d' | '1w';
  direction: 'up' | 'down' | 'neutral';
  confidence: number;
  target: number;
  timestamp: number;
}

export interface Indicator {
  symbol: string;
  rsi: number;
  macd: number;
  macd_signal: number;
  bb_upper: number;
  bb_lower: number;
  bb_middle: number;
  volume_ma: number;
}

class ApiClient {
  private client: AxiosInstance;
  private baseURL: string;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    this.client = axios.create({
      baseURL: this.baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 10000,
    });

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      response => response,
      error => {
        console.error('[API Error]', error.response?.data || error.message);
        throw error;
      }
    );
  }

  // ==================== HEALTH CHECK ====================
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.client.get('/health');
      return response.status === 200;
    } catch (error) {
      return false;
    }
  }

  // ==================== PRICES ====================
  async getPrices(symbols: string[]): Promise<Record<string, Price>> {
    try {
      const response = await this.client.post<ApiResponse<Record<string, Price>>>('/api/v1/prices', {
        symbols,
      });
      return response.data.data || {};
    } catch (error) {
      console.error('[API] Error fetching prices:', error);
      return {};
    }
  }

  async getPrice(symbol: string): Promise<Price | null> {
    try {
      const response = await this.client.get<ApiResponse<Price>>(`/api/v1/prices/${symbol}`);
      return response.data.data || null;
    } catch (error) {
      console.error('[API] Error fetching price:', error);
      return null;
    }
  }

  // ==================== SIGNALS ====================
  async getSignal(symbol: string): Promise<Signal | null> {
    try {
      const response = await this.client.get<ApiResponse<Signal>>(`/api/v1/signals/${symbol}`);
      return response.data.data || null;
    } catch (error) {
      console.error('[API] Error fetching signal:', error);
      return null;
    }
  }

  async getSignals(symbols: string[]): Promise<Record<string, Signal>> {
    try {
      const response = await this.client.post<ApiResponse<Record<string, Signal>>>('/api/v1/signals', {
        symbols,
      });
      return response.data.data || {};
    } catch (error) {
      console.error('[API] Error fetching signals:', error);
      return {};
    }
  }

  // ==================== PREDICTIONS ====================
  async getPredictions(symbol: string, timeframe: '1h' | '1d' | '1w' = '1d'): Promise<Prediction | null> {
    try {
      const response = await this.client.get<ApiResponse<Prediction>>(
        `/api/v1/predictions/${symbol}?timeframe=${timeframe}`
      );
      return response.data.data || null;
    } catch (error) {
      console.error('[API] Error fetching predictions:', error);
      return null;
    }
  }

  // ==================== INDICATORS ====================
  async getIndicators(symbol: string, timeframe: string = '1D'): Promise<Indicator | null> {
    try {
      const response = await this.client.get<ApiResponse<Indicator>>(
        `/api/v1/indicators/${symbol}?timeframe=${timeframe}`
      );
      return response.data.data || null;
    } catch (error) {
      console.error('[API] Error fetching indicators:', error);
      return null;
    }
  }

  // ==================== MARKET DATA ====================
  async getMarketOverview(): Promise<any> {
    try {
      const response = await this.client.get('/api/v1/market/overview');
      return response.data.data || null;
    } catch (error) {
      console.error('[API] Error fetching market overview:', error);
      return null;
    }
  }

  // ==================== SETTINGS ====================
  getBaseURL(): string {
    return this.baseURL;
  }
}

export const apiClient = new ApiClient();
