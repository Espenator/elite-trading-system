// COMPLETE FRONTEND API SERVICE
// Located at: glass-house-ui/src/lib/api-service.ts

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export class ApiService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  // ===== HTTP API CALLS =====
  
  async getSignals(limit = 100) {
    const res = await fetch(`${API_BASE}/api/signals/?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch signals');
    return res.json();
  }

  async getSignalByTicker(ticker: string) {
    const res = await fetch(`${API_BASE}/api/signals/${ticker}`);
    if (!res.ok) throw new Error(`Failed to fetch signal for ${ticker}`);
    return res.json();
  }

  async getSystemHealth() {
    const res = await fetch(`${API_BASE}/api/signals/health/system`);
    if (!res.ok) throw new Error('Failed to fetch system health');
    return res.json();
  }

  async getTierCount(tier: string) {
    const res = await fetch(`${API_BASE}/api/signals/tiers/${tier}/count`);
    if (!res.ok) throw new Error(`Failed to fetch ${tier} tier count`);
    return res.json();
  }

  async getRankedSignals(limit = 25) {
    const res = await fetch(`${API_BASE}/api/signals/ranked?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch ranked signals');
    return res.json();
  }

  async getSignalFeed(limit = 1000) {
    const res = await fetch(`${API_BASE}/api/signals/feed?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch signal feed');
    return res.json();
  }

  async getMarketIndices() {
    const res = await fetch(`${API_BASE}/api/market/indices`);
    if (!res.ok) throw new Error('Failed to fetch market indices');
    return res.json();
  }

  async getChartData(symbol: string, timeframe = '15m') {
    const res = await fetch(`${API_BASE}/api/market/charts/${symbol}?timeframe=${timeframe}`);
    if (!res.ok) throw new Error(`Failed to fetch chart for ${symbol}`);
    return res.json();
  }

  async executeTrade(trade: any) {
    const res = await fetch(`${API_BASE}/api/trades`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(trade)
    });
    if (!res.ok) throw new Error('Failed to execute trade');
    return res.json();
  }

  async getPortfolio() {
    const res = await fetch(`${API_BASE}/api/portfolio`);
    if (!res.ok) throw new Error('Failed to fetch portfolio');
    return res.json();
  }

  // ===== WEBSOCKET =====
  
  connectWebSocket(onMessage: (data: any) => void, onError?: (error: any) => void) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    this.ws = new WebSocket(`${WS_BASE}/ws`);
    
    this.ws.onopen = () => {
      console.log('✅ WebSocket connected');
      this.reconnectAttempts = 0;
    };
    
    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };
    
    this.ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
      if (onError) onError(error);
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket closed. Attempting reconnect...');
      this.attemptReconnect(onMessage, onError);
    };
  }

  private attemptReconnect(onMessage: (data: any) => void, onError?: (error: any) => void) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`Reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
        this.connectWebSocket(onMessage, onError);
      }, 3000 * this.reconnectAttempts);
    } else {
      console.error('Max reconnect attempts reached');
    }
  }

  disconnectWebSocket() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export const apiService = new ApiService();
