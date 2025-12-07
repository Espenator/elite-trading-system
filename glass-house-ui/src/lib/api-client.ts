import axios from 'axios';
import { Signal, SystemHealth } from '../types';

const API_BASE_URL = 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const signalsApi = {
  getAll: async (tier?: string, limit: number = 600): Promise<Signal[]> => {
    const params = new URLSearchParams();
    if (tier) params.append('tier', tier);
    params.append('limit', limit.toString());
    
    const response = await apiClient.get<Signal[]>(`/api/signals?${params}`);
    return response.data;
  },

  getByTicker: async (ticker: string): Promise<Signal> => {
    const response = await apiClient.get<Signal>(`/api/signals/${ticker}`);
    return response.data;
  },

  getSystemHealth: async (): Promise<SystemHealth> => {
    const response = await apiClient.get<SystemHealth>('/api/signals/health/system');
    return response.data;
  },

  getTierCount: async (tier: string): Promise<{ tier: string; count: number }> => {
    const response = await apiClient.get<{ tier: string; count: number }>(`/api/signals/tiers/${tier}/count`);
    return response.data;
  },
};

export default apiClient;
