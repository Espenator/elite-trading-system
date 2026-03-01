import { useState, useEffect, useCallback, useRef } from 'react';
import tradeExecutionService from '../services/tradeExecutionService';

const POLL_INTERVAL = 2000;

// ─── Default State ─────────────────────────────────────────
const defaultPortfolio = {
  value: 1580420.55,
  dailyPnl: 12500.80,
  dailyPnlPct: 0.35,
  status: 'ELITE',
  latency: 8,
};

const defaultPriceLadder = Array.from({ length: 20 }, (_, i) => ({
  row: i + 1,
  price: (4450.00 + (Math.random() - 0.5) * 10).toFixed(2),
  size: Math.floor(Math.random() * 30),
  bidSize: Math.floor(Math.random() * 15),
  askSize: Math.floor(Math.random() * 15),
}));

const defaultOrderBook = Array.from({ length: 20 }, (_, i) => ({
  price: (4450.75 - i * 0.25).toFixed(2),
  bid: (4450.50 - i * 0.25).toFixed(2),
  size: Math.floor(Math.random() * 150) + 10,
  total: Math.floor(Math.random() * 800) + 100,
}));

const defaultPositions = [
  { symbol: 'SPX', side: 'Long', quantity: 50, avgPrice: 4435.00, currentPrice: 4450.25, pnl: 7625.00 },
  { symbol: 'SPX', side: 'Short', quantity: 50, avgPrice: 4435.00, currentPrice: 4450.25, pnl: 7625.00 },
];

const defaultNewsFeed = [
  { time: '09:30:05', text: 'FED official comments on interest rates cause market volatility.', type: 'warning' },
  { time: '09:25:45', text: 'Strong economic data released, boosting sentiment.', type: 'positive' },
  { time: '09:15:30', text: 'Breaking: Geopolitical tensions escalate, impacting oil prices.', type: 'negative' },
  { time: '09:10:15', text: 'Earnings Alert: XYZ Inc. reports Q2 results, beats estimates.', type: 'positive' },
];

const defaultSystemStatus = [
  { time: '09:30:12', text: 'Order #123456 executed successfully (SPX, Buy, 50 contracts).', type: 'success' },
  { time: '09:30:08', text: 'Connected to market data feed: Latency 8ms.', type: 'info' },
  { time: '09:30:02', text: 'Warning: High market volatility detected.', type: 'warning' },
  { time: '09:30:00', text: 'System initialized. All services online.', type: 'success' },
  { time: '09:29:55', text: 'User Logged In: ELITE status confirmed.', type: 'info' },
];

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
    symbol: 'SPX',
    strategy: 'Iron Condor',
    callStrikes: { call: [4460, 4470], put: [4440, 4430] },
    putStrikes: { call: [4440, 4450], put: [4440, 4430] },
    quantity: 10,
    quantityType: 'Contracts',
    limitPrice: 1.55,
    stopPrice: 1.00,
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
      console.warn('[useTradeExecution] Fetch error, using defaults:', err.message);
    }
  }, [orderForm.symbol]);

  // ─── WebSocket Handler ─────────────────────────────────
  const handleWsMessage = useCallback((data) => {
    switch (data.type) {
      case 'portfolio':
        setPortfolio(data.payload);
        break;
      case 'order_book':
        setOrderBook(data.payload);
        break;
      case 'price_ladder':
        setPriceLadder(data.payload);
        break;
      case 'positions':
        setPositions(data.payload);
        break;
      case 'news':
        setNewsFeed(prev => [data.payload, ...prev].slice(0, 20));
        break;
      case 'system_status':
        setSystemStatus(prev => [data.payload, ...prev].slice(0, 20));
        break;
      case 'order_executed':
        setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: data.payload.message, type: 'success' }, ...prev].slice(0, 20));
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
      console.warn('[useTradeExecution] WS unavailable, polling only');
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
    setSystemStatus(prev => [{ time: new Date().toLocaleTimeString(), text: `Adjusting position: ${symbol} ${side}`, type: 'info' }, ...prev]);
  }, []);

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
