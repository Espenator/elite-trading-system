/**
 * Trade Execution Service — connects frontend to backend order/position APIs.
 *
 * Bug #21/#22/#23 fix: rewrote to use getApiUrl() from config/api.js
 * instead of broken './api' import and non-existent '/api/trade-execution' base.
 * WebSocket now uses getWsBaseUrl() instead of hardcoded port.
 */
import { getApiUrl, getWsBaseUrl, getAuthHeaders } from '../config/api';
import log from "@/utils/logger";

// ─── Portfolio & Account ───────────────────────────────────
export const getPortfolio = async () => {
  const res = await fetch(`${getApiUrl('alpaca')}/account`);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
};

// ─── Positions ─────────────────────────────────────────────
export const getPositions = async () => {
  const res = await fetch(`${getApiUrl('alpaca')}/positions`);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
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
  return res.json();
};

// ─── Price Ladder ──────────────────────────────────────────
export const getPriceLadder = async (symbol = 'SPX') => {
  const res = await fetch(`${getApiUrl('market')}/price-ladder?symbol=${encodeURIComponent(symbol)}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
};

// ─── Order Execution ───────────────────────────────────────
export const executeOrder = async (order) => {
  const res = await fetch(getApiUrl('orders'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(order),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
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
  const res = await fetch(`${getApiUrl('sentiment')}/news?limit=${limit}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
};

// ─── System Status ─────────────────────────────────────────
export const getSystemStatus = async () => {
  const res = await fetch(getApiUrl('status'));
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
};

// ─── WebSocket ─────────────────────────────────────────────
export const createTradeWebSocket = (onMessage, onError) => {
  const wsUrl = getWsBaseUrl();
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => log.info('[TradeExecution WS] Connected');
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      log.error('[TradeExecution WS] Parse error:', e);
    }
  };
  ws.onerror = (error) => {
    log.error('[TradeExecution WS] Error:', error);
    if (onError) onError(error);
  };
  ws.onclose = () => log.info('[TradeExecution WS] Disconnected');

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
