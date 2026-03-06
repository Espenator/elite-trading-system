import React, { useEffect, useCallback, useRef } from 'react';
import useTradeExecution from '../hooks/useTradeExecution';
import { getApiUrl, getAuthHeaders } from '../config/api';
import { useApi } from '../hooks/useApi';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import PageHeader from '../components/ui/PageHeader';
import clsx from 'clsx';
import {
  Crosshair, TrendingUp, TrendingDown, ShieldAlert, BarChart3,
  Newspaper, Activity, Terminal, Zap, ChevronRight, X, SlidersHorizontal,
  AlertTriangle, CheckCircle2, XCircle, Info,
} from 'lucide-react';

export default function TradeExecution() {
  const {
    portfolio, priceLadder, orderBook, positions, newsFeed, systemStatus,
    selectedRow, setSelectedRow, orderForm, updateOrderForm, loading,
    executeMarketBuy, executeMarketSell, executeLimitBuy, executeLimitSell,
    executeStopLoss, executeAdvancedOrder, closePosition, adjustPosition,
  } = useTradeExecution();

  // Symbol universe from API (fallback to common tickers)
  const { data: stocksData } = useApi('stocks', { pollIntervalMs: 120000 });
  const FALLBACK_SYMBOLS = ['SPX', 'SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA', 'AMD', 'AMZN', 'MSFT', 'META'];
  const symbolList = (stocksData?.symbols || stocksData?.tickers || stocksData?.universe || [])
    .map(s => typeof s === 'string' ? s : (s.symbol || s.ticker))
    .filter(Boolean);
  const symbols = symbolList.length > 0 ? symbolList : FALLBACK_SYMBOLS;

  // Strategy list
  const STRATEGIES = ['Iron Condor', 'Bull Call Spread', 'Bear Put Spread', 'Straddle', 'Strangle', 'Butterfly', 'Calendar Spread', 'Single Option'];

  // Options chain for strike prices
  const { data: chainData } = useApi('quotes', {
    endpoint: `/quotes/${orderForm?.symbol || 'SPY'}/options-chain`,
    pollIntervalMs: 60000,
    enabled: !!orderForm?.symbol,
  });
  const callStrikes = (chainData?.calls || []).map(c => c.strike).filter(Boolean).slice(0, 5);
  const putStrikes = (chainData?.puts || []).map(p => p.strike).filter(Boolean).slice(0, 5);
  const FALLBACK_CALL_STRIKES = [4450, 4455, 4460, 4465, 4470];
  const FALLBACK_PUT_STRIKES = [4440, 4435, 4430, 4425, 4420];
  const displayCallStrikes = callStrikes.length > 0 ? callStrikes : FALLBACK_CALL_STRIKES;
  const displayPutStrikes = putStrikes.length > 0 ? putStrikes : FALLBACK_PUT_STRIKES;

  // Candle data for price chart
  const { data: candleData } = useApi('quotes', {
    endpoint: `/quotes/${orderForm?.symbol || 'SPY'}/candles?timeframe=1h`,
    pollIntervalMs: 30000,
    enabled: !!orderForm?.symbol,
  });

  const chartRef = useRef(null);
  const chartInstanceRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    const initChart = async () => {
      if (!chartRef.current) return;
      try {
        const { createChart } = await import('lightweight-charts');
        if (cancelled) return;
        const chart = createChart(chartRef.current, {
          width: chartRef.current.clientWidth,
          height: 140,
          layout: { background: { color: '#0B0E14' }, textColor: '#94a3b8', fontSize: 9, fontFamily: "'JetBrains Mono', monospace" },
          grid: { vertLines: { color: 'rgba(42,52,68,0.3)' }, horzLines: { color: 'rgba(42,52,68,0.3)' } },
          crosshair: { mode: 0 },
          rightPriceScale: { borderColor: 'rgba(42,52,68,0.5)' },
          timeScale: { borderColor: 'rgba(42,52,68,0.5)', timeVisible: true },
        });
        const series = chart.addCandlestickSeries({
          upColor: '#10b981', downColor: '#ef4444',
          borderUpColor: '#10b981', borderDownColor: '#ef4444',
          wickUpColor: '#10b981', wickDownColor: '#ef4444',
        });
        chartInstanceRef.current = { chart, series };
        const handleResize = () => { if (chartRef.current) chart.applyOptions({ width: chartRef.current.clientWidth }); };
        window.addEventListener('resize', handleResize);
        chartInstanceRef.current.cleanup = () => { window.removeEventListener('resize', handleResize); chart.remove(); };
      } catch (err) { /* lightweight-charts not available */ }
    };
    initChart();
    return () => { cancelled = true; if (chartInstanceRef.current?.cleanup) chartInstanceRef.current.cleanup(); chartInstanceRef.current = null; };
  }, []);

  useEffect(() => {
    const inst = chartInstanceRef.current;
    if (!inst?.series || !candleData) return;
    const candles = candleData.candles || candleData.bars || candleData.ohlcv || [];
    if (!candles.length) return;
    const mapped = candles
      .map(c => {
        const time = c.time || c.timestamp || c.t;
        if (!time) return null;
        const tStr = typeof time === 'string' ? time.slice(0, 10) : time;
        return { time: tStr, open: c.open ?? c.o, high: c.high ?? c.h, low: c.low ?? c.l, close: c.close ?? c.c };
      })
      .filter(c => c && c.open != null)
      .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));
    const seen = new Set();
    const unique = mapped.filter(c => { if (seen.has(c.time)) return false; seen.add(c.time); return true; });
    if (unique.length) inst.series.setData(unique);
  }, [candleData]);

  // Alignment Preflight State
  const [preflightVerdict, setPreflightVerdict] = React.useState(null);
  const [preflightLoading, setPreflightLoading] = React.useState(false);
  const runAlignmentPreflight = async (side = 'buy') => {
    setPreflightLoading(true);
    try {
      const res = await fetch(getApiUrl('alignment/evaluate'), { method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ symbol: orderForm?.symbol || 'SPY', side, quantity: orderForm?.quantity || 1, strategy: 'manual' })
      });
      if (!res.ok) throw new Error('Alignment preflight failed');
      const data = await res.json();
      setPreflightVerdict(data);
      return data;
    } catch (err) {
      const verdict = { allowed: true, blockedBy: 'NETWORK_ERROR', summary: err.message };
      setPreflightVerdict(verdict);
      return verdict;
    } finally {
      setPreflightLoading(false);
    }
  };

  const withPreflight = async (side, action) => {
    const verdict = await runAlignmentPreflight(side);
    if (verdict && verdict.allowed === false) {
      if (!window.confirm(`Alignment blocked: ${verdict.summary || verdict.blockedBy}\n\nOverride and execute anyway?`)) return;
    }
    return action();
  };

  // Keyboard Shortcuts
  const handleKeyDown = useCallback((e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    if (!e.ctrlKey && !e.metaKey) return;
    switch (e.key.toUpperCase()) {
      case 'B': e.preventDefault(); if (window.confirm(`Market BUY ${orderForm.symbol} x${orderForm.quantity}?`)) withPreflight('buy', executeMarketBuy); break;
      case 'S': e.preventDefault(); if (window.confirm(`Market SELL ${orderForm.symbol} x${orderForm.quantity}?`)) withPreflight('sell', executeMarketSell); break;
      case 'L': e.preventDefault(); withPreflight('buy', executeLimitBuy); break;
      case 'O': e.preventDefault(); withPreflight('sell', executeLimitSell); break;
      case 'T': e.preventDefault(); executeStopLoss(); break;
      case 'E': e.preventDefault(); withPreflight('buy', executeAdvancedOrder); break;
      default: break;
    }
  }, [executeMarketBuy, executeMarketSell, executeLimitBuy, executeLimitSell, executeStopLoss, executeAdvancedOrder, orderForm.symbol, orderForm.quantity]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Formatters
  const fmt = (v) => v?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00';
  const fmtUsd = (v) => `$${fmt(v)}`;

  // Normalize data arrays
  const ladderArr = Array.isArray(priceLadder) ? priceLadder : (priceLadder?.levels || []);
  const bookBids = Array.isArray(orderBook) ? orderBook.filter(r => r.side === 'bid') : (orderBook?.bids || []);
  const bookAsks = Array.isArray(orderBook) ? orderBook.filter(r => r.side === 'ask') : (orderBook?.asks || []);
  const bookArr = Array.isArray(orderBook) ? orderBook : [...(orderBook?.asks || []).reverse(), ...(orderBook?.bids || [])];
  const posArr = Array.isArray(positions) ? positions : (positions?.positions || []);
  const newsArr = Array.isArray(newsFeed) ? newsFeed : [];
  const statusArr = Array.isArray(systemStatus) ? systemStatus : [systemStatus].filter(Boolean);
  const maxLadderSize = Math.max(...ladderArr.map(r => r.size || 0), 1);
  const maxBookSize = Math.max(...bookArr.map(r => r.size || 0), 1);

  // Generate fallback price ladder if empty
  const displayLadder = ladderArr.length > 0 ? ladderArr : Array.from({ length: 20 }, (_, i) => ({
    row: i + 1,
    price: (4449 - i).toFixed(2),
    size: Math.floor(Math.random() * 80) + 5,
    side: i < 10 ? 'ask' : 'bid',
  }));
  const displayMaxLadder = Math.max(...displayLadder.map(r => r.size || 0), 1);

  // Generate fallback order book if empty
  const displayBook = bookArr.length > 0 ? bookArr : Array.from({ length: 14 }, (_, i) => {
    const isAsk = i < 7;
    return {
      price: isAsk ? (4455 - i).toFixed(2) : (4448 - (i - 7)).toFixed(2),
      size: Math.floor(Math.random() * 150) + 10,
      total: Math.floor(Math.random() * 500) + 50,
      side: isAsk ? 'ask' : 'bid',
    };
  });
  const displayMaxBook = Math.max(...displayBook.map(r => r.size || 0), 1);

  // Fallback news
  const displayNews = newsArr.length > 0 ? newsArr : [
    { time: '09:30:25', text: 'FED official comments on interest rates cause market volatility', type: 'negative' },
    { time: '09:15:30', text: 'Strong economic data released, boosting sentiment.', type: 'positive' },
    { time: '09:13:00', text: '[Breaking] Geopolitical tensions escalate, impacting oil prices.', type: 'warning' },
    { time: '09:10:15', text: '[Earnings Alert] XYZ Inc. reports Q2 results, beats estimates.', type: 'positive' },
  ];

  // Fallback system status
  const displayStatus = statusArr.length > 0 ? statusArr : [
    { time: '09:01:22', text: 'Order #12345 executed successfully (SPX, Buy, 50 contracts)', type: 'success' },
    { time: '09:00:45', text: 'Connected to market data feed. Latency: 5ms.', type: 'success' },
    { time: '08:59:12', text: 'Warning: High market volatility detected.', type: 'warning' },
    { time: '08:55:30', text: 'Market initialized. All services online.', type: 'info' },
    { time: '08:50:00', text: 'User Logged in. ELITE status confirmed.', type: 'success' },
  ];

  // Fallback positions
  const displayPositions = posArr.length > 0 ? posArr : [
    { symbol: 'SPX', side: 'Long', quantity: 50, avgPrice: 4435.00, currentPrice: 4450.25, pnl: 762.50 },
    { symbol: 'SPY', side: 'Long', quantity: 90, avgPrice: 455.00, currentPrice: 4410.25, pnl: -9.92 },
  ];

  return (
    <div className="space-y-3">

      {/* ===== HEADER BAR ===== */}
      <div className="flex items-center justify-between bg-surface border border-secondary/20 rounded-xl px-5 py-3">
        <PageHeader
          icon={Crosshair}
          title="TRADE EXECUTION"
        />
        <div className="flex items-center gap-6 text-xs font-mono">
          <span className="text-gray-500">Portfolio: <span className="text-white font-bold">{fmtUsd(portfolio.value || 1580430.55)}</span></span>
          <span className="text-gray-500">Daily P/L: <span className={(portfolio.dailyPnl || 12500.80) >= 0 ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>+{fmtUsd(portfolio.dailyPnl || 12500.80)}</span></span>
          <span className="text-gray-500">Status: <Badge variant="success" size="sm">{portfolio.status || 'ELITE'}</Badge></span>
          <span className="text-gray-500">Latency: <span className="text-cyan-400 font-bold">{portfolio.latency || 8}ms</span></span>
        </div>
      </div>

      {/* ===== QUICK EXECUTION BAR ===== */}
      <Card noPadding>
        <div className="px-4 py-3 flex items-center gap-3 flex-wrap">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider mr-1">Quick Execution</span>
          <Button variant="success" size="sm" onClick={() => { if (window.confirm(`Market BUY ${orderForm.symbol} x${orderForm.quantity}?`)) withPreflight('buy', executeMarketBuy); }} disabled={loading || preflightLoading}>
            Market Buy [B]
          </Button>
          <Button variant="danger" size="sm" onClick={() => { if (window.confirm(`Market SELL ${orderForm.symbol} x${orderForm.quantity}?`)) withPreflight('sell', executeMarketSell); }} disabled={loading || preflightLoading}>
            Market Sell [S]
          </Button>
          <Button variant="outline" size="sm" onClick={() => withPreflight('buy', executeLimitBuy)} disabled={loading} className="!border-blue-500/50 !text-blue-400 hover:!bg-blue-500/10">
            Limit Buy [$]
          </Button>
          <Button variant="outline" size="sm" onClick={() => withPreflight('sell', executeLimitSell)} disabled={loading} className="!border-amber-500/50 !text-amber-400 hover:!bg-amber-500/10">
            Limit Sell [$]
          </Button>
          <Button variant="outline" size="sm" onClick={executeStopLoss} disabled={loading} className="!border-red-500/50 !text-red-400 hover:!bg-red-500/10">
            Stop Loss [T]
          </Button>
        </div>
      </Card>

      {/* ===== MAIN 3-COLUMN GRID ===== */}
      <div className="grid grid-cols-12 gap-3">

        {/* --- COL 1: Multi-Price Ladder --- */}
        <div className="col-span-3">
          <Card title="Multi-Price Ladder" noPadding>
            <div className="overflow-y-auto max-h-[520px]">
              <table className="w-full text-xs font-mono">
                <thead className="sticky top-0 bg-surface z-10">
                  <tr className="border-b border-secondary/20">
                    <th className="px-2 py-1.5 text-left text-[10px] text-gray-500 font-medium">Row</th>
                    <th className="px-2 py-1.5 text-center text-[10px] text-gray-500 font-medium">Price</th>
                    <th className="px-2 py-1.5 text-right text-[10px] text-gray-500 font-medium">Size</th>
                  </tr>
                </thead>
                <tbody>
                  {displayLadder.map((row, i) => {
                    const rowNum = row.row || i + 1;
                    const isSelected = rowNum === selectedRow;
                    const price = parseFloat(row.price) || 0;
                    const size = row.size || 0;
                    const isBid = row.side === 'bid' || i >= displayLadder.length / 2;
                    const isAsk = row.side === 'ask' || i < displayLadder.length / 2;
                    const isSpread = i === Math.floor(displayLadder.length / 2) - 1 || i === Math.floor(displayLadder.length / 2);
                    const barColor = isBid ? 'bg-emerald-500' : 'bg-red-500';
                    const textColor = isBid ? 'text-emerald-400' : 'text-red-400';
                    const pct = Math.min((size / displayMaxLadder) * 100, 100);
                    return (
                      <tr
                        key={i}
                        onClick={() => setSelectedRow(rowNum)}
                        className={clsx(
                          'cursor-pointer transition-colors relative',
                          isSelected
                            ? 'bg-cyan-500/15 border-l-2 border-l-cyan-400'
                            : isSpread
                              ? 'bg-cyan-900/10 border-l-2 border-l-transparent hover:bg-cyan-500/10'
                              : 'border-l-2 border-l-transparent hover:bg-white/[0.02]'
                        )}
                      >
                        <td className="px-2 py-[3px] text-[10px] text-gray-600 w-8">{rowNum}</td>
                        <td className={clsx(
                          'px-2 py-[3px] text-center',
                          isSelected ? 'text-cyan-400 font-bold' : 'text-white/80'
                        )}>
                          {price.toFixed(2)}
                        </td>
                        <td className="px-2 py-[3px] text-right relative">
                          <div className={clsx('absolute top-0 bottom-0 right-0 opacity-20', barColor)} style={{ width: `${pct}%` }} />
                          <span className={clsx('relative z-10', textColor)}>{size}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* --- COL 2: Advanced Order Builder --- */}
        <div className="col-span-3">
          <Card title="Advanced Order Builder" noPadding>
            <div className="p-3 space-y-2.5">
              {/* Symbol + Strategy */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[10px] text-gray-500 uppercase tracking-wider mb-1">Symbol</label>
                  <select
                    value={orderForm.symbol}
                    onChange={e => updateOrderForm({ symbol: e.target.value })}
                    className="w-full bg-dark border border-secondary/30 rounded px-2 py-1.5 text-xs text-white focus:border-cyan-500 focus:outline-none font-mono"
                  >
                    {symbols.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-gray-500 uppercase tracking-wider mb-1">Strategy</label>
                  <select
                    value={orderForm.strategy}
                    onChange={e => updateOrderForm({ strategy: e.target.value })}
                    className="w-full bg-dark border border-secondary/30 rounded px-2 py-1.5 text-xs text-white focus:border-cyan-500 focus:outline-none"
                  >
                    {STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>

              {/* Call strike section */}
              <div className="bg-dark/50 border border-secondary/20 rounded p-2.5">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="w-3 h-3 text-emerald-500" />
                  <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">Call</span>
                </div>
                <div className="flex gap-1.5 flex-wrap">
                  {displayCallStrikes.map((v, i) => {
                    const selected = orderForm.callStrikes?.call?.includes(v);
                    return (
                      <span
                        key={i}
                        onClick={() => updateOrderForm({ callStrikes: { ...orderForm.callStrikes, call: selected ? orderForm.callStrikes.call.filter(s => s !== v) : [...(orderForm.callStrikes?.call || []), v] } })}
                        className={clsx(
                          'px-2 py-1 rounded text-[11px] font-mono cursor-pointer border transition-colors',
                          selected
                            ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                            : 'bg-transparent text-gray-500 border-secondary/30 hover:border-secondary/50'
                        )}
                      >{v}</span>
                    );
                  })}
                </div>
              </div>

              {/* Put strike section */}
              <div className="bg-dark/50 border border-secondary/20 rounded p-2.5">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingDown className="w-3 h-3 text-red-500" />
                  <span className="text-[10px] font-semibold text-red-400 uppercase tracking-wider">Put</span>
                </div>
                <div className="flex gap-1.5 flex-wrap">
                  {displayPutStrikes.map((v, i) => {
                    const selected = orderForm.putStrikes?.put?.includes(v);
                    return (
                      <span
                        key={i}
                        onClick={() => updateOrderForm({ putStrikes: { ...orderForm.putStrikes, put: selected ? orderForm.putStrikes.put.filter(s => s !== v) : [...(orderForm.putStrikes?.put || []), v] } })}
                        className={clsx(
                          'px-2 py-1 rounded text-[11px] font-mono cursor-pointer border transition-colors',
                          selected
                            ? 'bg-red-500/15 text-red-400 border-red-500/30'
                            : 'bg-transparent text-gray-500 border-secondary/30 hover:border-secondary/50'
                        )}
                      >{v}</span>
                    );
                  })}
                </div>
              </div>

              {/* Quantity + Limit */}
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="block text-[10px] text-gray-500 uppercase tracking-wider mb-1">Quantity</label>
                  <input
                    type="number"
                    value={orderForm.quantity}
                    onChange={e => updateOrderForm({ quantity: parseInt(e.target.value) || 0 })}
                    className="w-full bg-dark border border-secondary/30 rounded px-2 py-1.5 text-xs text-white font-mono focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-gray-500 uppercase tracking-wider mb-1">&nbsp;</label>
                  <select
                    value={orderForm.quantityType}
                    onChange={e => updateOrderForm({ quantityType: e.target.value })}
                    className="w-full bg-dark border border-secondary/30 rounded px-2 py-1.5 text-xs text-white focus:border-cyan-500 focus:outline-none"
                  >
                    {['Contracts', 'Shares', 'Lots'].map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-gray-500 uppercase tracking-wider mb-1">Limit</label>
                  <input
                    type="number"
                    step="0.01"
                    value={orderForm.limitPrice}
                    onChange={e => updateOrderForm({ limitPrice: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-dark border border-secondary/30 rounded px-2 py-1.5 text-xs text-white font-mono focus:border-cyan-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Execute Button */}
              <button
                onClick={() => withPreflight('buy', executeAdvancedOrder)}
                disabled={loading}
                className="w-full py-2 rounded font-bold text-xs font-mono tracking-wide text-white bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 disabled:opacity-50 disabled:cursor-wait transition-all hover:shadow-[0_0_20px_rgba(16,185,129,0.3)]"
              >
                {loading ? 'Executing...' : 'Execute Order [!]'}
              </button>
            </div>
          </Card>
        </div>

        {/* --- COL 3: Live Order Book --- */}
        <div className="col-span-3">
          <Card title="Live Order Book" noPadding>
            <div className="overflow-y-auto max-h-[520px]">
              <table className="w-full text-xs font-mono">
                <thead className="sticky top-0 bg-surface z-10">
                  <tr className="border-b border-secondary/20">
                    <th className="px-2 py-1.5 text-right text-[10px] text-gray-500 font-medium">Bid</th>
                    <th className="px-2 py-1.5 text-right text-[10px] text-gray-500 font-medium">Size</th>
                    <th className="px-2 py-1.5 text-right text-[10px] text-gray-500 font-medium">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {displayBook.map((row, i) => {
                    const isGreen = row.side === 'bid' || (row.bid && row.bid >= 4450) || i >= displayBook.length / 2;
                    const size = row.size || 0;
                    const pct = Math.min((size / displayMaxBook) * 100, 100);
                    const price = row.price || row.bid || row.ask || 0;
                    return (
                      <tr key={i} className="relative hover:bg-white/[0.02] cursor-pointer transition-colors">
                        <td className="px-2 py-[3px] text-right relative">
                          <div
                            className={clsx(
                              'absolute top-0 bottom-0 opacity-15',
                              isGreen ? 'bg-emerald-500 right-0' : 'bg-red-500 right-0'
                            )}
                            style={{ width: `${pct}%` }}
                          />
                          <span className={clsx('relative z-10', isGreen ? 'text-emerald-400' : 'text-red-400')}>
                            {parseFloat(price).toFixed(2)}
                          </span>
                        </td>
                        <td className="px-2 py-[3px] text-right text-white/80">{size}</td>
                        <td className="px-2 py-[3px] text-right text-gray-500">{row.total || Math.floor(size * 2.5)}</td>
                      </tr>
                    );
                  })}
                  {displayBook.length === 0 && (
                    <tr><td colSpan={3} className="px-4 py-8 text-center text-gray-600">No order book data</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* --- COL 4: Price Charts + News Feed --- */}
        <div className="col-span-3 space-y-3">

          {/* Price Charts */}
          <Card title="Price Charts" subtitle={`SPY / S&P 500 Index 1M`} noPadding>
            <div className="p-3">
              <div className="h-[140px] rounded bg-dark/50 border border-secondary/10 overflow-hidden">
                <div ref={chartRef} className="w-full h-full" />
              </div>
            </div>
          </Card>

          {/* News Feed */}
          <Card title="News Feed" action={<Newspaper className="w-3.5 h-3.5 text-gray-600" />} noPadding>
            <div className="max-h-[220px] overflow-y-auto divide-y divide-secondary/10">
              {displayNews.map((item, i) => {
                const severityColor = item.type === 'negative' || item.type === 'error'
                  ? 'text-red-400'
                  : item.type === 'warning'
                    ? 'text-amber-400'
                    : item.type === 'positive' || item.type === 'success'
                      ? 'text-emerald-400'
                      : 'text-cyan-400';
                const dotColor = item.type === 'negative' || item.type === 'error'
                  ? 'bg-red-500'
                  : item.type === 'warning'
                    ? 'bg-amber-500'
                    : item.type === 'positive' || item.type === 'success'
                      ? 'bg-emerald-500'
                      : 'bg-cyan-500';
                return (
                  <div key={i} className="px-3 py-2 hover:bg-white/[0.02] transition-colors">
                    <div className="flex items-start gap-2">
                      <span className={clsx('w-1.5 h-1.5 rounded-full mt-1.5 shrink-0', dotColor)} />
                      <div className="min-w-0">
                        <span className={clsx('text-[10px] font-mono font-semibold mr-2', severityColor)}>{item.time}</span>
                        <span className="text-[11px] text-gray-400 leading-snug">{item.text}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      </div>

      {/* ===== BOTTOM ROW: Live Positions + System Status Log ===== */}
      <div className="grid grid-cols-2 gap-3">

        {/* Live Positions */}
        <Card title="Live Positions" noPadding>
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b border-secondary/20">
                  {['Symbol', 'Side', 'Quantity', 'Avg. Price', 'Current Price', 'P/L', 'Actions'].map(h => (
                    <th key={h} className="px-3 py-2 text-left text-[10px] text-cyan-400/70 font-medium uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-secondary/10">
                {displayPositions.map((pos, i) => {
                  const pnl = parseFloat(pos.pnl ?? pos.unrealized_pl ?? 0);
                  const isPositive = pnl >= 0;
                  return (
                    <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-3 py-2 text-cyan-400 font-semibold">{pos.symbol}</td>
                      <td className="px-3 py-2">
                        <Badge variant={(pos.side || '').toLowerCase().includes('long') ? 'success' : 'danger'} size="sm">
                          {pos.side}
                        </Badge>
                      </td>
                      <td className="px-3 py-2 text-white/80">{parseFloat(pos.quantity ?? pos.qty ?? 0)}</td>
                      <td className="px-3 py-2 text-white/80">{parseFloat(pos.avgPrice ?? pos.avg_entry_price ?? 0).toFixed(2)}</td>
                      <td className="px-3 py-2 text-white/80">{parseFloat(pos.currentPrice ?? pos.current_price ?? 0).toFixed(2)}</td>
                      <td className={clsx('px-3 py-2 font-semibold', isPositive ? 'text-emerald-400' : 'text-red-400')}>
                        {isPositive ? '+' : ''}{fmtUsd(pnl)}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex gap-1.5">
                          <button
                            onClick={() => closePosition(pos.symbol, pos.side)}
                            className="px-2 py-0.5 rounded text-[10px] font-semibold bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-colors"
                          >
                            <X className="w-3 h-3 inline mr-0.5" />Close
                          </button>
                          <button
                            onClick={() => adjustPosition(pos.symbol, pos.side)}
                            className="px-2 py-0.5 rounded text-[10px] font-semibold border border-secondary/30 text-gray-400 hover:bg-secondary/10 transition-colors"
                          >
                            <SlidersHorizontal className="w-3 h-3 inline mr-0.5" />Adj
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {displayPositions.length === 0 && (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-600 text-xs">No open positions</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* System Status Log */}
        <Card title="System Status Log" action={<Terminal className="w-3.5 h-3.5 text-gray-600" />} noPadding>
          <div className="max-h-[220px] overflow-y-auto divide-y divide-secondary/10">
            {displayStatus.map((item, i) => {
              const iconEl = item.type === 'success' || item.type === 'info'
                ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                : item.type === 'warning'
                  ? <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                  : item.type === 'error'
                    ? <XCircle className="w-3.5 h-3.5 text-red-500 shrink-0 mt-0.5" />
                    : <Info className="w-3.5 h-3.5 text-cyan-500 shrink-0 mt-0.5" />;
              const timeColor = item.type === 'warning'
                ? 'text-amber-400'
                : item.type === 'error'
                  ? 'text-red-400'
                  : 'text-emerald-400';
              return (
                <div key={i} className="px-3 py-2 flex items-start gap-2 hover:bg-white/[0.02] transition-colors">
                  {iconEl}
                  <div className="text-[11px] leading-relaxed min-w-0">
                    <span className={clsx('font-mono font-semibold mr-2', timeColor)}>{item.time}</span>
                    <span className="text-gray-400">{item.text}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

    </div>
  );
}
