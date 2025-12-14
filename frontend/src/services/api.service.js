// api.service.js
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

class ApiService {
  async get(endpoint, params = {}) {
    const url = new URL(`${API_BASE_URL}${endpoint}`);
    Object.keys(params).forEach(key => {
      if (params[key] !== undefined && params[key] !== null) {
        url.searchParams.append(key, params[key]);
      }
    });

    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    return response.json();
  }

  async post(endpoint, data = {}) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    return response.json();
  }

  // Stock endpoints
  async getStocks(params = {}) {
    return this.get('/stocks/', params);
  }

  async getStockByTicker(ticker) {
    return this.get(`/stocks/ticker/${ticker}`);
  }

  async getSectors() {
    return this.get('/stocks/sectors');
  }

  async getCountries() {
    return this.get('/stocks/countries');
  }

  async scrapeStocks(filters = null) {
    return this.post('/stocks/scrape', { filters });
  }
}

export const apiService = new ApiService();
export default apiService;
