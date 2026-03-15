/**
 * Trade Execution Service — connects frontend to backend order/position APIs.
 *
 * Bug #21/#22/#23 fix: rewrote to use getApiUrl() from config/api.js
 * instead of broken './api' import and non-existent '/api/trade-execution' base.
 * WebSocket now uses getWsBaseUrl() instead of hardcoded port.
 */
import { getApiUrl, getWsBaseUrl, getAuthHeaders } from '../config/api';
import log from "@/utils/logger";
import appWs from './websocket';

// ─── Portfolio & Account ───────────────────────────────────
export const getPortfolio = async () => {
  const start = performance.now();
  const res = await fetch(`${getApiUrl('alpaca')}/account`);
  const latency = Math.round(performance.now() - start);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  const acct = await res.json();
  // Normalize Alpaca account shape to what the UI expects
  return {
    value: parseFloat(acct.equity || acct.portfolio_value || 0),
    dailyPnl: parseFloat(acct.equity || 0) - parseFloat(acct.last_equity || acct.equity || 0),
    dailyPnlPct: acct.last_equity ? ((parseFloat(acct.equity) - parseFloat(acct.last_equity)) / parseFloat(acct.last_equity)) * 100 : 0,
    status: acct.status || 'ACTIVE',
    latency,
    buyingPower: parseFloat(acct.buying_power || 0),
    cash: parseFloat(acct.cash || 0),
  };
};

// ─── Positions ─────────────────────────────────────────────
export const getPositions = async () => {
  const res = await fetch(`${getApiUrl('alpaca')}/positions`);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  const data = await res.json();
  // Ensure array (backend returns {positions:[...]} or [...])
  return Array.isArray(data) ? data : (data.positions || []);
};

export const closePosition = async (symbol, side) => {
  const res = await fetch(`${getApiUrl('orders')}/close`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ symbol, side }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
};

export const adjustPosition = async (symbol, side, adjustment) => {
  const res = await fetch(`${getApiUrl('orders')}/adjust`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ symbol, side, ...adjustment }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
};

// ─── Order Book ────────────────────────────────────────────
export const getOrderBook = async (symbol = 'SPX') => {
  const res = await fetch(`${getApiUrl('market')}/order-book?symbol=${encodeURIComponent(symbol)}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  const data = await res.json();
  // Backend returns {symbol, bids, asks, status} — UI expects flat array of rows
  const bids = (data.bids || []).map(b => ({ ...b, side: 'bid' }));
  const asks = (data.asks || []).map(a => ({ ...a, side: 'ask' }));
  return [...asks.reverse(), ...bids];
};

// ─── Price Ladder ──────────────────────────────────────────
export const getPriceLadder = async (symbol = 'SPX') => {
  const res = await fetch(`${getApiUrl('market')}/price-ladder?symbol=${encodeURIComponent(symbol)}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  const data = await res.json();
  // Backend returns {symbol, levels, status} — UI expects flat array of levels
  return data.levels || [];
};

export const getRecentOrders = async (limit = 10) => {
  const res = await fetch(`${getApiUrl('orders/recent')}?limit=${limit}`, { headers: getAuthHeaders() });
  if (!res.ok) return [];
  const data = await res.json();
  return Array.isArray(data) ? data : [];
};

export const emergencyStop = async () => {
  const res = await fetch(getApiUrl('orders/emergency-stop'), { method: 'POST', headers: getAuthHeaders() });
  if (!res.ok) throw new Error(`Emergency stop failed: ${res.status}`);
  return res.json();
};

// ─── Order Execution ───────────────────────────────────────
export const executeOrder = async (order) => {
  const body = {
    symbol: order.symbol,
    side: order.side || 'buy',
    type: (order.type || order.orderType || 'market').toLowerCase(),
    time_in_force: (order.time_in_force || order.timeInForce || 'day').toLowerCase(),
    qty: String(order.quantity ?? order.qty ?? 1),
  };
  if (order.limit_price != null && order.limit_price !== '') body.limit_price = String(order.limit_price);
  if (order.stop_price != null && order.stop_price !== '') body.stop_price = String(order.stop_price);
  const res = await fetch(getApiUrl('orders/advanced'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(body),
  });
  if (!res.ok) { const errBody = await res.json().catch(() => ({})); throw new Error(errBody.detail?.message || errBody.detail || `HTTP ${res.status}`); }
  return res.json();
};

export const marketBuy = async (symbol, quantity) => {
  return executeOrder({ symbol, side: 'buy', type: 'market', quantity });
};

export const marketSell = async (symbol, quantity) => {
  return executeOrder({ symbol, side: 'sell', type: 'market', quantity });
};

export const limitBuy = async (symbol, quantity, limitPrice) => {
  return executeOrder({ symbol, side: 'buy', type: 'limit', quantity, limit_price: String(limitPrice) });
};

export const limitSell = async (symbol, quantity, limitPrice) => {
  return executeOrder({ symbol, side: 'sell', type: 'limit', quantity, limit_price: String(limitPrice) });
};

export const stopLoss = async (symbol, quantity, stopPrice) => {
  return executeOrder({ symbol, side: 'sell', type: 'stop', quantity, stop_price: String(stopPrice) });
};

// ─── Advanced Order (Iron Condor, Spreads, etc.) ───────────
export const executeAdvancedOrder = async (order) => {
  const res = await fetch(`${getApiUrl('orders')}/advanced`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(order),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
};

// ─── News Feed ─────────────────────────────────────────────
export const getNewsFeed = async (limit = 20) => {
  try {
    const res = await fetch(getApiUrl('swarmNewsStatus'));
    if (!res.ok) return [];
    const data = await res.json();
    return (data.recent_items || []).slice(0, limit);
  } catch {
    return [];
  }
};

// ─── System Status ─────────────────────────────────────────
export const getSystemStatus = async () => {
  try {
    const res = await fetch(getApiUrl('status'));
    if (!res.ok) return [{ time: new Date().toLocaleTimeString(), text: `System status: HTTP ${res.status}`, type: 'warning' }];
    const data = await res.json();
    // Backend returns {status, connected, latency, ...} — UI expects array of log entries
    return [{ time: new Date().toLocaleTimeString(), text: `System ${data.status || 'ok'} — latency ${data.latency || 0}ms`, type: data.status === 'ok' ? 'info' : 'warning' }];
  } catch {
    return [{ time: new Date().toLocaleTimeString(), text: 'System status check failed', type: 'warning' }];
  }
};

// ─── WebSocket ─────────────────────────────────────────────
// Use the singleton AppWebSocket from websocket.js instead of creating a standalone connection.
// This avoids duplicate WS connections and leverages the shared reconnect/heartbeat logic.

export const subscribeTradeUpdates = (onMessage, onError) => {
  // Subscribe to the 'trades' channel on the shared WebSocket
  const unsub = appWs.on('trades', (data) => {
    try {
      onMessage(data);
    } catch (e) {
      log.error('[TradeExecution WS] Handler error:', e);
      if (onError) onError(e);
    }
  });
  // Ensure the shared WS is connected
  if (!appWs.isConnected()) appWs.connect();
  return unsub;
};

// Backwards-compatible alias — returns an object with a .close() method
export const createTradeWebSocket = (onMessage, onError) => {
  const unsub = subscribeTradeUpdates(onMessage, onError);
  return { close: unsub };
};

export default {
  getPortfolio,
  getPositions,
  getRecentOrders,
  closePosition,
  adjustPosition,
  getOrderBook,
  getPriceLadder,
  executeOrder,
  emergencyStop,
  marketBuy,
  marketSell,
  limitBuy,
  limitSell,
  stopLoss,
  executeAdvancedOrder,
  getNewsFeed,
  getSystemStatus,
  createTradeWebSocket,
  subscribeTradeUpdates,
};
