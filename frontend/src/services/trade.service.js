// trade.service.js
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';

class TradeService {
  /**
   * Fetch stock list from Finviz screener
   */
  async getStockList(filters = null) {
    try {
      const url = new URL(`${API_BASE_URL}/stocks/list`);
      if (filters) {
        url.searchParams.append('filters', filters);
      }

      const response = await fetch(url.toString());
      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }
      return response.json();
    } catch (error) {
      console.error('Error fetching stock list:', error);
      throw error;
    }
  }

  /**
   * Fetch quote data for a specific ticker
   */
  async getQuoteData(ticker, timeframe = 'd', duration = null) {
    try {
      const url = new URL(`${API_BASE_URL}/quotes/${ticker}`);
      url.searchParams.append('p', timeframe);
      if (duration) {
        url.searchParams.append('r', duration);
      }

      const response = await fetch(url.toString());
      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }
      return response.json();
    } catch (error) {
      console.error(`Error fetching quote data for ${ticker}:`, error);
      throw error;
    }
  }

  /**
   * Transform stock data into live trading signals
   * This creates signals based on stock metrics like price change, volume, etc.
   */
  transformStocksToSignals(stocks) {
    if (!stocks || stocks.length === 0) {
      return [];
    }

    const signals = stocks
      .slice(0, 20) // Limit to top 20 stocks
      .map((stock) => {
        // Parse stock data - handle both string and number formats
        const ticker = stock.Ticker || stock.ticker || '';
        const priceStr = stock.Price || stock.price || '0';
        const price = parseFloat(priceStr.toString().replace(/[^0-9.-]/g, '') || 0);
        
        const changeStr = stock.Change || stock.change || '0%';
        const change = parseFloat(changeStr.toString().replace(/[^0-9.-]/g, '') || 0);
        
        const volumeStr = stock.Volume || stock.volume || '0';
        const volume = parseInt(volumeStr.toString().replace(/[^0-9]/g, '') || 0);
        
        const peStr = stock['P/E'] || stock['P/E'] || stock.pe || '0';
        const pe = parseFloat(peStr.toString().replace(/[^0-9.-]/g, '') || 0);

        // Calculate signal metrics
        const isPositiveChange = change > 0;
        const changePercent = Math.abs(change);
        
        // Calculate score based on multiple factors
        let score = 50; // Base score
        
        // Volume factor (higher volume = higher score)
        if (volume > 1000000) score += 10;
        if (volume > 5000000) score += 10;
        
        // Price change factor
        if (changePercent > 2) score += 15;
        if (changePercent > 5) score += 10;
        
        // P/E factor (reasonable P/E = better score)
        if (pe > 0 && pe < 30) score += 10;
        
        // Cap score at 100
        score = Math.min(100, Math.max(0, score));

        // Determine tier based on score
        let tier = 'C';
        if (score >= 90) tier = 'A-';
        else if (score >= 85) tier = 'B+';
        else if (score >= 80) tier = 'B';
        else if (score >= 75) tier = 'C+';
        else if (score >= 70) tier = 'C';
        else tier = 'D';

        // Calculate entry, target, and stop
        const entry = price;
        const volatility = changePercent / 100;
        const targetMultiplier = isPositiveChange ? 1 + (volatility * 2) : 1 - (volatility * 2);
        const stopMultiplier = isPositiveChange ? 1 - (volatility * 1.5) : 1 + (volatility * 1.5);
        
        const target = price * targetMultiplier;
        const stop = price * stopMultiplier;
        
        // Calculate risk/reward ratio
        const risk = Math.abs(price - stop);
        const reward = Math.abs(target - price);
        const rr = risk > 0 ? (reward / risk).toFixed(1) : 0;

        // Determine action (BUY for positive change, SELL for negative)
        const action = isPositiveChange ? 'BUY' : 'SELL';

        // Get current time
        const now = new Date();
        const time = now.toLocaleTimeString('en-US', { 
          hour12: false, 
          hour: '2-digit', 
          minute: '2-digit', 
          second: '2-digit' 
        });

        return {
          time,
          symbol: ticker,
          tier,
          score: Math.round(score),
          entry: parseFloat(entry.toFixed(2)),
          target: parseFloat(target.toFixed(2)),
          stop: parseFloat(stop.toFixed(2)),
          rr: parseFloat(rr),
          action
        };
      })
      .filter(signal => signal.symbol && signal.symbol.length > 0) // Filter out invalid signals
      .sort((a, b) => b.score - a.score) // Sort by score descending
      .slice(0, 10); // Return top 10 signals

    return signals;
  }

  /**
   * Fetch and transform live trading signals
   */
  async getLiveSignals(filters = null) {
    try {
      const stocks = await this.getStockList(filters);
      return this.transformStocksToSignals(stocks);
    } catch (error) {
      console.error('Error fetching live signals:', error);
      // Return empty array on error to prevent UI breakage
      return [];
    }
  }
}

export const tradeService = new TradeService();
export default tradeService;

