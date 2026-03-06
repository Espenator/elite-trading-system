import { useState, useEffect, useCallback, useRef } from 'react';
import tradeExecutionService from '../services/tradeExecutionService';
import log from "@/utils/logger";

const POLL_INTERVAL = 10000; // 10s — was 2s, caused browser connection exhaustion

// ─── Default State (empty — real data loaded from API) ─────
const defaultPortfolio = { value: 0, dailyPnl: 0, dailyPnlPct: 0, status: 'OFFLINE', latency: 0 };
const defaultPriceLadder = [];
const defaultOrderBook = [];
const defaultPositions = [];
const defaultNewsFeed = [];
const defaultSystemStatus = [{ time: new Date().toLocaleTimeString(), text: 'Awaiting backend connection...', type: 'info' }];

export default function useTradeExecution() {
  // ─── State ─────────────────────────────────────────────
  const [portfolio, setPortfolio] = useState(defaultPortfolio);
  const [priceLadder, setPriceLadder] = useState(defaultPriceLadder);
  const [orderBook, setOrderBook] = useState(defaultOrderBook);
  const [positions, setPositions] = useState(defaultPositions);
  const [newsFeed, setNewsFeed] = useState(defaultNewsFeed);
  const [systemStatus, setSystemStatus] = useState(defaultSystemStatus);
  const [selectedRow, setSelectedRow] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  // ─── Order Form State ──────────────────────────────────
  const [orderForm, setOrderForm] = useState({
    symbol: 'SPY',
    strategy: 'Iron Condor',
    callStrikes: { call: [0, 0], put: [0, 0] },
    putStrikes: { call: [0, 0], put: [0, 0] },
    quantity: 1,
    quantityType: 'Contracts',
    limitPrice: 0,
    stopPrice: 0,
  });

  const wsRef = useRef(null);
  const pollRef = useRef(null);

  // ─── Fetch All Data ────────────────────────────────────
  const fetchAll = useCallback(async () => {
    try {
      const [portfolioRes, positionsRes, orderBookRes, ladderRes, newsRes, statusRes] = await Promise.allSettled([
        tradeExecutionService.getPortfolio(),
        tradeExecutionService.getPositions(),
        tradeExecutionService.getOrderBook(orderForm.symbol),
        tradeExecutionService.getPriceLadder(orderForm.symbol),
        tradeExecutionService.getNewsFeed(),
        tradeExecutionService.getSystemStatus(),
      ]);

      if (portfolioRes.status === 'fulfilled') setPortfolio(portfolioRes.value);
      if (positionsRes.status === 'fulfilled') setPositions(positionsRes.value);
      if (orderBookRes.status === 'fulfilled') setOrderBook(orderBookRes.value);
      if (ladderRes.status === 'fulfilled') setPriceLadder(ladderRes.value);
      if (newsRes.status === 'fulfilled') setNewsFeed(newsRes.value);
      if (statusRes.status === 'fulfilled') setSystemStatus(statusRes.value);
      setLastUpdate(new Date());
    } catch (err) {
      log.warn('[useTradeExecution] Fetch error, using defaults:', err.message);
    }
  }, [orderForm.symbol]);

  // ─── WebSocket Handler ─────────────────────────────────
  const handleWsMessage = useCallback((data) => {
    if (!data || typeof data !== 'object') return;
    const payload = data.payload;
    switch (data.type) {
      case 'portfolio':
        if (payload) setPortfolio(payload);
        break;
      case 'order_book':
        if (payload) setOrderBook(Array.isArray(payload) ? payload : []);
        break;
      case 'price_ladder':
        if (payload) setPriceLadder(Array.isArray(payload) ? payload : (payload.levels || []));
        break;
      case 'positions':
        if (payload) setPositions(Array.isArray(payload) ? payload : (payload.positions || []));
        break;
      case 'news':
        if (payload) setNewsFeed(prev => [payload, ...prev].slice(0, 20));
        break;
      case 'system_status':
        if (payload) setSystemStatus(prev => [payload, ...prev].slice(0, 20));
        break;
      case 'order_executed':
        setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: payload?.message || 'Order executed', type: 'success' }, ...prev].slice(0, 20));
        break;
      default:
        break;
    }
    setLastUpdate(new Date());
  }, []);

  // ─── Init: Fetch + WS + Polling ────────────────────────
  useEffect(() => {
    fetchAll();

    try {
      wsRef.current = tradeExecutionService.createTradeWebSocket(handleWsMessage);
    } catch (e) {
      log.warn('[useTradeExecution] WS unavailable, polling only');
    }

    pollRef.current = setInterval(fetchAll, POLL_INTERVAL);

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchAll, handleWsMessage]);

  // ─── Order Execution Actions ───────────────────────────
  const executeMarketBuy = useCallback(async () => {
    setLoading(true);
    try {
      const result = await tradeExecutionService.marketBuy(orderForm.symbol, orderForm.quantity);
      setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: `Market Buy executed: ${orderForm.symbol} x${orderForm.quantity}`, type: 'success' }, ...prev]);
      await fetchAll();
      return result;
    } catch (err) {
      setError(err.message);
      setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: `Order failed: ${err.message}`, type: 'error' }, ...prev]);
    } finally {
      setLoading(false);
    }
  }, [orderForm, fetchAll]);

  const executeMarketSell = useCallback(async () => {
    setLoading(true);
    try {
      const result = await tradeExecutionService.marketSell(orderForm.symbol, orderForm.quantity);
      setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: `Market Sell executed: ${orderForm.symbol} x${orderForm.quantity}`, type: 'success' }, ...prev]);
      await fetchAll();
      return result;
    } catch (err) {
      setError(err.message);
      setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: `Order failed: ${err.message}`, type: 'error' }, ...prev]);
    } finally {
      setLoading(false);
    }
  }, [orderForm, fetchAll]);

  const executeLimitBuy = useCallback(async () => {
    setLoading(true);
    try {
      const result = await tradeExecutionService.limitBuy(orderForm.symbol, orderForm.quantity, orderForm.limitPrice);
      setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: `Limit Buy placed: ${orderForm.symbol} x${orderForm.quantity} @ $${orderForm.limitPrice}`, type: 'success' }, ...prev]);
      await fetchAll();
      return result;
    } catch (err) {
      setError(err.message);
      setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: `Order failed: ${err.message}`, type: 'error' }, ...prev]);
    } finally {
      setLoading(false);
    }
  }, [orderForm, fetchAll]);

  const executeLimitSell = useCallback(async () => {
    setLoading(true);
    try {
      const result = await tradeExecutionService.limitSell(orderForm.symbol, orderForm.quantity, orderForm.limitPrice);
      setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: `Limit Sell placed: ${orderForm.symbol} x${orderForm.quantity} @ $${orderForm.limitPrice}`, type: 'success' }, ...prev]);
      await fetchAll();
      return result;
    } catch (err) {
      setError(err.message);
      setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: `Order failed: ${err.message}`, type: 'error' }, ...prev]);
    } finally {
      setLoading(false);
    }
  }, [orderForm, fetchAll]);

  const executeStopLoss = useCallback(async () => {
    setLoading(true);
    try {
      const result = await tradeExecutionService.stopLoss(orderForm.symbol, orderForm.quantity, orderForm.stopPrice);
      setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: `Stop Loss placed: ${orderForm.symbol} x${orderForm.quantity} @ $${orderForm.stopPrice}`, type: 'success' }, ...prev]);
      await fetchAll();
      return result;
    } catch (err) {
      setError(err.message);
      setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: `Order failed: ${err.message}`, type: 'error' }, ...prev]);
    } finally {
      setLoading(false);
    }
  }, [orderForm, fetchAll]);

  const executeAdvancedOrder = useCallback(async () => {
    setLoading(true);
    try {
      const result = await tradeExecutionService.executeAdvancedOrder({
        symbol: orderForm.symbol,
        strategy: orderForm.strategy,
        callStrikes: orderForm.callStrikes,
        putStrikes: orderForm.putStrikes,
        quantity: orderForm.quantity,
        limitPrice: orderForm.limitPrice,
        stopPrice: orderForm.stopPrice,
      });
      setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: `${orderForm.strategy} executed: ${orderForm.symbol} x${orderForm.quantity}`, type: 'success' }, ...prev]);
      await fetchAll();
      return result;
    } catch (err) {
      setError(err.message);
      setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: `Advanced order failed: ${err.message}`, type: 'error' }, ...prev]);
    } finally {
      setLoading(false);
    }
  }, [orderForm, fetchAll]);

  const closePositionAction = useCallback(async (symbol, side) => {
    setLoading(true);
    try {
      await tradeExecutionService.closePosition(symbol, side);
      setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: `Position closed: ${symbol} ${side}`, type: 'success' }, ...prev]);
      await fetchAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [fetchAll]);

  const adjustPositionAction = useCallback(async (symbol, side) => {
    setLoading(true);
    setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: `Adjusting position: ${symbol} ${side}`, type: 'info' }, ...prev]);
    try {
      await tradeExecutionService.adjustPosition(symbol, side, { action: 'scale' });
      setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: `Position adjusted: ${symbol} ${side}`, type: 'success' }, ...prev]);
      await fetchAll();
    } catch (err) {
      setError(err.message);
      setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: `Adjust failed: ${err.message}`, type: 'error' }, ...prev]);
    } finally {
      setLoading(false);
    }
  }, [fetchAll]);

  const updateOrderForm = useCallback((updates) => {
    setOrderForm(prev => ({ ...prev, ...updates }));
  }, []);

  return {
    portfolio,
    priceLadder,
    orderBook,
    positions,
    newsFeed,
    systemStatus,
    selectedRow,
    setSelectedRow,
    orderForm,
    updateOrderForm,
    loading,
    error,
    lastUpdate,
    executeMarketBuy,
    executeMarketSell,
    executeLimitBuy,
    executeLimitSell,
    executeStopLoss,
    executeAdvancedOrder,
    closePosition: closePositionAction,
    adjustPosition: adjustPositionAction,
    refresh: fetchAll,
  };
}
