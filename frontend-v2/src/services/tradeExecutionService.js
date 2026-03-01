import api from './api';

const API_BASE = '/api/trade-execution';

// ─── Portfolio & Account ───────────────────────────────────
export const getPortfolio = async () => {
  const { data } = await api.get(`${API_BASE}/portfolio`);
  return data;
};

// ─── Positions ─────────────────────────────────────────────
export const getPositions = async () => {
  const { data } = await api.get(`${API_BASE}/positions`);
  return data;
};

export const closePosition = async (symbol, side) => {
  const { data } = await api.post(`${API_BASE}/positions/close`, { symbol, side });
  return data;
};

export const adjustPosition = async (symbol, side, adjustment) => {
  const { data } = await api.post(`${API_BASE}/positions/adjust`, { symbol, side, ...adjustment });
  return data;
};

// ─── Order Book ────────────────────────────────────────────
export const getOrderBook = async (symbol = 'SPX') => {
  const { data } = await api.get(`${API_BASE}/order-book`, { params: { symbol } });
  return data;
};

// ─── Price Ladder ──────────────────────────────────────────
export const getPriceLadder = async (symbol = 'SPX') => {
  const { data } = await api.get(`${API_BASE}/price-ladder`, { params: { symbol } });
  return data;
};

// ─── Order Execution ───────────────────────────────────────
export const executeOrder = async (order) => {
  const { data } = await api.post(`${API_BASE}/orders`, order);
  return data;
};

export const marketBuy = async (symbol, quantity) => {
  return executeOrder({ symbol, side: 'buy', type: 'market', quantity });
};

export const marketSell = async (symbol, quantity) => {
  return executeOrder({ symbol, side: 'sell', type: 'market', quantity });
};

export const limitBuy = async (symbol, quantity, limitPrice) => {
  return executeOrder({ symbol, side: 'buy', type: 'limit', quantity, limit_price: limitPrice });
};

export const limitSell = async (symbol, quantity, limitPrice) => {
  return executeOrder({ symbol, side: 'sell', type: 'limit', quantity, limit_price: limitPrice });
};

export const stopLoss = async (symbol, quantity, stopPrice) => {
  return executeOrder({ symbol, side: 'sell', type: 'stop', quantity, stop_price: stopPrice });
};

// ─── Advanced Order (Iron Condor, Spreads, etc.) ───────────
export const executeAdvancedOrder = async (order) => {
  const { data } = await api.post(`${API_BASE}/orders/advanced`, order);
  return data;
};

// ─── News Feed ─────────────────────────────────────────────
export const getNewsFeed = async (limit = 20) => {
  const { data } = await api.get(`${API_BASE}/news-feed`, { params: { limit } });
  return data;
};

// ─── System Status ─────────────────────────────────────────
export const getSystemStatus = async () => {
  const { data } = await api.get(`${API_BASE}/system-status`);
  return data;
};

// ─── WebSocket ─────────────────────────────────────────────
export const createTradeWebSocket = (onMessage, onError) => {
  const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:8000/ws/trade-execution`;
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => console.log('[TradeExecution WS] Connected');
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error('[TradeExecution WS] Parse error:', e);
    }
  };
  ws.onerror = (error) => {
    console.error('[TradeExecution WS] Error:', error);
    if (onError) onError(error);
  };
  ws.onclose = () => console.log('[TradeExecution WS] Disconnected');

  return ws;
};

export default {
  getPortfolio,
  getPositions,
  closePosition,
  adjustPosition,
  getOrderBook,
  getPriceLadder,
  executeOrder,
  marketBuy,
  marketSell,
  limitBuy,
  limitSell,
  stopLoss,
  executeAdvancedOrder,
  getNewsFeed,
  getSystemStatus,
  createTradeWebSocket,
};
