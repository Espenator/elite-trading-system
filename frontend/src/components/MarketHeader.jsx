import React, { useState, useEffect } from 'react';
import '../styles/MarketHeader.css';

const MarketHeader = () => {
  // ==================== STATE ====================
  const [marketData, setMarketData] = useState({
    indices: {
      SPY: { price: 595.45, change: 0.15, changePercent: 0.15 },
      DJI: { price: 47950, change: -4.79, changePercent: -0.01 },
      IXIC: { price: 21180, change: 67.58, changePercent: 0.32 }
    },
    vix: { price: 16.2, change: -2.1, changePercent: -11.5, status: 'low' },
    breadth: { advancers: 1847, decliners: 1203, ratio: 1.53, status: 'bullish' },
    sectors: [
      { name: 'Technology', symbol: 'XLK', change: 1.2, changePercent: 1.2 },
      { name: 'Consumer', symbol: 'XLY', change: 0.8, changePercent: 0.8 },
      { name: 'Energy', symbol: 'XLE', change: -0.5, changePercent: -0.5 }
    ],
    tradingStatus: { isOpen: true, statusText: '🟢 LIVE' },
    lastUpdate: new Date()
  });

  const [wsConnected, setWsConnected] = useState(false);
  const [sectorScroll, setSectorScroll] = useState(0);

  // ==================== EFFECTS ====================
  
  // Initial data fetch
  useEffect(() => {
    fetchMarketData();
    const interval = setInterval(fetchMarketData, 5000); // Update every 5s
    return () => clearInterval(interval);
  }, []);

  // WebSocket connection for real-time updates
  useEffect(() => {
    connectWebSocket();
    return () => {
      // Cleanup WebSocket on unmount
    };
  }, []);

  // Sector scroll animation
  useEffect(() => {
    const scrollTimer = setInterval(() => {
      setSectorScroll(prev => (prev + 1) % 100);
    }, 20);
    return () => clearInterval(scrollTimer);
  }, []);

  // ==================== FUNCTIONS ====================

  /**
   * Fetch market data from backend API
   * Sources: Alpaca, YFinance, UnusualWhales
   */
  const fetchMarketData = async () => {
    try {
      // In production, these would call your backend endpoints
      // For now, we simulate with mock data that updates
      const response = await fetch('http://localhost:8000/api/v1/market/overview');
      
      if (response.ok) {
        const data = await response.json();
        setMarketData(prev => ({
          ...prev,
          ...data,
          lastUpdate: new Date()
        }));
      } else {
        // Use mock data if API fails
        updateMockData();
      }
    } catch (error) {
      console.log('Using mock market data (API unavailable)');
      updateMockData();
    }
  };

  /**
   * Update mock data with realistic market fluctuations
   */
  const updateMockData = () => {
    setMarketData(prev => {
      const fluctuation = (Math.random() - 0.5) * 0.05; // Small random change
      return {
        ...prev,
        indices: {
          SPY: { price: 595.45 + fluctuation, change: 0.15, changePercent: 0.15 },
          DJI: { price: 47950 + Math.random() * 100, change: -4.79, changePercent: -0.01 },
          IXIC: { price: 21180 + fluctuation, change: 67.58, changePercent: 0.32 }
        },
        vix: { price: 16.2 + Math.random() * 2, change: -2.1, changePercent: -11.5, status: 'low' },
        lastUpdate: new Date()
      };
    });
  };

  /**
   * Connect to WebSocket for real-time market data
   * Alpaca paper trading API WebSocket endpoint
   */
  const connectWebSocket = () => {
    try {
      const ws = new WebSocket('ws://localhost:8000/ws/market');
      
      ws.onopen = () => {
        console.log('✅ Market WebSocket Connected');
        setWsConnected(true);
        
        // Subscribe to market streams
        ws.send(JSON.stringify({
          action: 'subscribe',
          quotes: ['SPY', 'DJI', '^VIX']
        }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Handle different message types
          if (data.T === 'q') { // Quote message
            updateQuoteData(data);
          } else if (data.T === 'breadth') {
            updateBreadthData(data);
          }
        } catch (err) {
          console.error('WebSocket message error:', err);
        }
      };

      ws.onclose = () => {
        console.log('❌ Market WebSocket Disconnected');
        setWsConnected(false);
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setWsConnected(false);
      };

      return ws;
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      return null;
    }
  };

  /**
   * Update quote data from WebSocket message
   */
  const updateQuoteData = (quoteData) => {
    setMarketData(prev => {
      const updated = { ...prev };
      
      // Map symbols to indices
      if (quoteData.S === 'SPY') {
        updated.indices.SPY = {
          price: quoteData.p || quoteData.lp,
          change: quoteData.c || 0,
          changePercent: quoteData.cp || 0
        };
      } else if (quoteData.S === 'DJI') {
        updated.indices.DJI = {
          price: quoteData.p || quoteData.lp,
          change: quoteData.c || 0,
          changePercent: quoteData.cp || 0
        };
      } else if (quoteData.S === '^VIX') {
        const vixPrice = quoteData.p || quoteData.lp;
        updated.vix = {
          price: vixPrice,
          change: quoteData.c || 0,
          changePercent: quoteData.cp || 0,
          status: getVixStatus(vixPrice)
        };
      }
      
      return { ...updated, lastUpdate: new Date() };
    });
  };

  /**
   * Update market breadth data from WebSocket
   */
  const updateBreadthData = (breadthData) => {
    setMarketData(prev => ({
      ...prev,
      breadth: {
        advancers: breadthData.adv || prev.breadth.advancers,
        decliners: breadthData.dec || prev.breadth.decliners,
        ratio: (breadthData.adv || prev.breadth.advancers) / (breadthData.dec || prev.breadth.decliners),
        status: getBreadthStatus(breadthData.adv, breadthData.dec)
      },
      lastUpdate: new Date()
    }));
  };

  /**
   * Get VIX volatility status (low/normal/high/extreme)
   */
  const getVixStatus = (vixPrice) => {
    if (vixPrice < 12) return 'low';
    if (vixPrice < 20) return 'normal';
    if (vixPrice < 30) return 'high';
    return 'extreme';
  };

  /**
   * Get market breadth status (bearish/neutral/bullish)
   */
  const getBreadthStatus = (advancers, decliners) => {
    const ratio = advancers / decliners;
    if (ratio > 1.2) return 'bullish';
    if (ratio < 0.8) return 'bearish';
    return 'neutral';
  };

  /**
   * Format number with proper decimals and commas
   */
  const formatPrice = (price, decimals = 2) => {
    return parseFloat(price).toFixed(decimals);
  };

  /**
   * Format percentage with color
   */
  const formatPercent = (percent) => {
    return `${percent > 0 ? '+' : ''}${percent.toFixed(2)}%`;
  };

  /**
   * Get arrow icon for direction
   */
  const getArrow = (change) => {
    if (change > 0) return '📈';
    if (change < 0) return '📉';
    return '➡️';
  };

  /**
   * Get color class for change
   */
  const getChangeColor = (change) => {
    if (change > 0) return 'positive';
    if (change < 0) return 'negative';
    return 'neutral';
  };

  // ==================== RENDER ====================
  return (
    <div className="market-header">
      {/* CONNECTION STATUS */}
      <div className="ws-indicator">
        <span className={`indicator ${wsConnected ? 'connected' : 'disconnected'}`}>
          {wsConnected ? '🟢' : '🔴'} {marketData.tradingStatus.statusText}
        </span>
      </div>

      {/* MAJOR INDICES */}
      <div className="indices-section">
        {/* S&P 500 */}
        <div className="index-item">
          <div className="index-label">S&P 500</div>
          <div className="index-value">{formatPrice(marketData.indices.SPY.price)}</div>
          <div className={`index-change ${getChangeColor(marketData.indices.SPY.change)}`}>
            {getArrow(marketData.indices.SPY.change)} {formatPercent(marketData.indices.SPY.changePercent)}
          </div>
        </div>

        {/* Dow Jones */}
        <div className="index-item">
          <div className="index-label">DJI</div>
          <div className="index-value">{formatPrice(marketData.indices.DJI.price, 0)}</div>
          <div className={`index-change ${getChangeColor(marketData.indices.DJI.change)}`}>
            {getArrow(marketData.indices.DJI.change)} {formatPercent(marketData.indices.DJI.changePercent)}
          </div>
        </div>

        {/* NASDAQ */}
        <div className="index-item">
          <div className="index-label">NASDAQ</div>
          <div className="index-value">{formatPrice(marketData.indices.IXIC.price, 0)}</div>
          <div className={`index-change ${getChangeColor(marketData.indices.IXIC.change)}`}>
            {getArrow(marketData.indices.IXIC.change)} {formatPercent(marketData.indices.IXIC.changePercent)}
          </div>
        </div>
      </div>

      {/* VIX VOLATILITY INDEX */}
      <div className={`vix-section vix-${marketData.vix.status}`}>
        <div className="vix-label">VIX</div>
        <div className="vix-value">{formatPrice(marketData.vix.price, 1)}</div>
        <div className={`vix-change ${getChangeColor(marketData.vix.change)}`}>
          {formatPercent(marketData.vix.changePercent)}
        </div>
        <div className="vix-tooltip">
          {marketData.vix.price < 12 && '🟢 Low vol - Favorable for trading'}
          {marketData.vix.price >= 12 && marketData.vix.price < 20 && '🟡 Normal vol'}
          {marketData.vix.price >= 20 && marketData.vix.price < 30 && '🔴 High vol - Caution'}
          {marketData.vix.price >= 30 && '🔴 Extreme vol - Extreme caution'}
        </div>
      </div>

      {/* MARKET BREADTH */}
      <div className={`breadth-section breadth-${marketData.breadth.status}`}>
        <div className="breadth-label">Breadth</div>
        <div className="breadth-bar">
          <div className="breadth-fill" style={{ width: `${(marketData.breadth.ratio / 2) * 100}%` }}></div>
        </div>
        <div className="breadth-text">
          {marketData.breadth.advancers} ▲ / {marketData.breadth.decliners} ▼
          <br />
          Ratio: {formatPrice(marketData.breadth.ratio, 2)}
        </div>
        <div className={`breadth-status breadth-${marketData.breadth.status}`}>
          {marketData.breadth.status.toUpperCase()}
        </div>
      </div>

      {/* HOT SECTORS (Scrolling) */}
      <div className="sectors-section">
        <div className="sectors-label">🔥 HOT SECTORS</div>
        <div className="sectors-scroll">
          {marketData.sectors.map((sector, idx) => (
            <div key={idx} className={`sector-ticker ${getChangeColor(sector.change)}`}>
              <span className="sector-name">{sector.name}</span>
              <span className="sector-change">{formatPercent(sector.changePercent)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* MARKET TIME */}
      <div className="market-time">
        <div className="time-label">Last Update</div>
        <div className="time-value">
          {marketData.lastUpdate.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
          })}
        </div>
      </div>
    </div>
  );
};

export default MarketHeader;
