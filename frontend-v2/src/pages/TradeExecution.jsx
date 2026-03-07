import React, { useEffect, useCallback, useRef, useState } from 'react';
import useTradeExecution from '../hooks/useTradeExecution';
import { getApiUrl, getAuthHeaders } from '../config/api';
import { useApi } from '../hooks/useApi';
import clsx from 'clsx';
import { Minus, Plus } from 'lucide-react';
import { VisualPriceLadder, CouncilDecisionPanel } from '../components/dashboard/TradeExecutionWidgets';

/* ────────────────────────────────────────────────────────────
   Shared tiny components used only in this page
   ──────────────────────────────────────────────────────────── */
const PanelHead = ({ children }) => (
  <div className="px-3 py-[7px] border-b border-[#1a2744] flex items-center justify-between bg-[#070d18] shrink-0">
    <span className="font-mono text-[9px] font-semibold text-[#5a6f8a] uppercase tracking-[0.5px]">{children}</span>
    <div className="flex gap-[3px]">
      <span className="w-[3px] h-[3px] rounded-full bg-[#5a6f8a]" />
      <span className="w-[3px] h-[3px] rounded-full bg-[#5a6f8a]" />
      <span className="w-[3px] h-[3px] rounded-full bg-[#5a6f8a]" />
    </div>
  </div>
);

const FormField = ({ label, children }) => (
  <div className="flex items-center mb-2.5">
    <label className="w-[90px] text-[10px] text-[#5a6f8a] shrink-0">{label}</label>
    {children}
  </div>
);

const FormSelect = ({ value, onChange, children, className }) => (
  <select
    value={value}
    onChange={onChange}
    className={clsx(
      'flex-1 bg-[#111b2e] border border-[#1a2744] text-[#e8f0fe] px-2.5 py-1.5 font-mono text-[10px] rounded-[3px] outline-none',
      'focus:border-cyan-400 focus:shadow-[0_0_8px_rgba(0,212,232,0.15)]',
      'appearance-none cursor-pointer',
      className
    )}
  >
    {children}
  </select>
);

const FormInput = ({ value, onChange, type = 'text', step, readOnly, className, ...rest }) => (
  <input
    type={type}
    step={step}
    value={value}
    onChange={onChange}
    readOnly={readOnly}
    className={clsx(
      'bg-[#111b2e] border border-[#1a2744] text-[#e8f0fe] px-2.5 py-1.5 font-mono text-[10px] rounded-[3px] outline-none',
      'focus:border-cyan-400 focus:shadow-[0_0_8px_rgba(0,212,232,0.15)]',
      className
    )}
    {...rest}
  />
);

/* ────────────────────────────────────────────────────────────
   Main component
   ──────────────────────────────────────────────────────────── */
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
  const putStrikes  = (chainData?.puts  || []).map(p => p.strike).filter(Boolean).slice(0, 5);
  const FALLBACK_CALL = [4450, 4455, 4460, 4465, 4470];
  const FALLBACK_PUT  = [4440, 4435, 4430, 4425, 4420];
  const displayCallStrikes = callStrikes.length > 0 ? callStrikes : FALLBACK_CALL;
  const displayPutStrikes  = putStrikes.length  > 0 ? putStrikes  : FALLBACK_PUT;

  // Candle data for price chart
  const { data: candleData } = useApi('quotes', {
    endpoint: `/quotes/${orderForm?.symbol || 'SPY'}/candles?timeframe=1h`,
    pollIntervalMs: 30000,
    enabled: !!orderForm?.symbol,
  });

  const chartRef = useRef(null);
  const chartInstanceRef = useRef(null);
  const [chartTimeframe, setChartTimeframe] = useState('1M');
  const [builderTab, setBuilderTab] = useState('Advanced');

  /* -- Chart init -- */
  useEffect(() => {
    let cancelled = false;
    const initChart = async () => {
      if (!chartRef.current) return;
      try {
        const { createChart } = await import('lightweight-charts');
        if (cancelled) return;
        const chart = createChart(chartRef.current, {
          width: chartRef.current.clientWidth,
          height: chartRef.current.clientHeight || 160,
          layout: { background: { color: '#0a1020' }, textColor: '#5a6f8a', fontSize: 9, fontFamily: "'JetBrains Mono', monospace" },
          grid: { vertLines: { color: 'rgba(26,39,68,0.3)' }, horzLines: { color: 'rgba(26,39,68,0.3)' } },
          crosshair: { mode: 0 },
          rightPriceScale: { borderColor: 'rgba(26,39,68,0.5)' },
          timeScale: { borderColor: 'rgba(26,39,68,0.5)', timeVisible: true },
        });
        const series = chart.addCandlestickSeries({
          upColor: '#00e676', downColor: '#ff3860',
          borderUpColor: '#00e676', borderDownColor: '#ff3860',
          wickUpColor: '#00e676', wickDownColor: '#ff3860',
        });
        chartInstanceRef.current = { chart, series };
        const ro = new ResizeObserver(() => {
          if (chartRef.current) chart.applyOptions({ width: chartRef.current.clientWidth, height: chartRef.current.clientHeight });
        });
        ro.observe(chartRef.current);
        chartInstanceRef.current.cleanup = () => { ro.disconnect(); chart.remove(); };
      } catch { /* lightweight-charts not available */ }
    };
    initChart();
    return () => { cancelled = true; chartInstanceRef.current?.cleanup?.(); chartInstanceRef.current = null; };
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

  /* -- Alignment Preflight -- */
  const [preflightLoading, setPreflightLoading] = useState(false);
  const runAlignmentPreflight = async (side = 'buy') => {
    setPreflightLoading(true);
    try {
      const res = await fetch(getApiUrl('alignment/evaluate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ symbol: orderForm?.symbol || 'SPY', side, quantity: orderForm?.quantity || 1, strategy: 'manual' }),
      });
      if (!res.ok) throw new Error('Alignment preflight failed');
      return await res.json();
    } catch (err) {
      return { allowed: true, blockedBy: 'NETWORK_ERROR', summary: err.message };
    } finally {
      setPreflightLoading(false);
    }
  };

  const withPreflight = async (side, action) => {
    const verdict = await runAlignmentPreflight(side);
    if (verdict?.allowed === false) {
      if (!window.confirm(`Alignment blocked: ${verdict.summary || verdict.blockedBy}\n\nOverride and execute anyway?`)) return;
    }
    return action();
  };

  /* -- Keyboard Shortcuts -- */
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

  /* -- Formatters -- */
  const fmt  = (v) => v?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00';
  const fmtUsd = (v) => `$${fmt(v)}`;

  /* -- Normalize data arrays -- */
  const ladderArr = Array.isArray(priceLadder) ? priceLadder : (priceLadder?.levels || []);
  const bookArr   = Array.isArray(orderBook) ? orderBook : [...(orderBook?.asks || []).reverse(), ...(orderBook?.bids || [])];
  const posArr    = Array.isArray(positions) ? positions : (positions?.positions || []);
  const newsArr   = Array.isArray(newsFeed) ? newsFeed : [];
  const statusArr = Array.isArray(systemStatus) ? systemStatus : [systemStatus].filter(Boolean);

  /* ── Fallback: Price Ladder (5-column with bid/ask depth bars) ── */
  const displayLadder = ladderArr.length > 0 ? ladderArr : (() => {
    const base = 4449.50;
    const mid = 9;
    return Array.from({ length: 20 }, (_, i) => {
      const price = (base - i * 0.50).toFixed(2);
      const isCurrent = i === mid;
      const isAsk = i < mid;
      const isBid = i > mid;
      return {
        row: i + 1, price,
        bidSize: isBid ? Math.floor(Math.random() * 55) + 5 : (isCurrent ? 3100000 : 0),
        askSize: isAsk ? Math.floor(Math.random() * 55) + 5 : (isCurrent ? 3200000 : 0),
        side: isCurrent ? 'current' : (isBid ? 'bid' : 'ask'),
        isCurrent,
      };
    });
  })();
  const maxBidSz = Math.max(...displayLadder.map(r => r.side === 'bid' ? (r.bidSize || r.size || 0) : 0), 1);
  const maxAskSz = Math.max(...displayLadder.map(r => r.side === 'ask' ? (r.askSize || r.size || 0) : 0), 1);

  /* ── Fallback: Order Book (two halves) ── */
  const displayBookTop = bookArr.length > 0 ? bookArr.slice(0, Math.ceil(bookArr.length / 2)) : Array.from({ length: 10 }, () => ({
    asset: '-', bid: (276 + Math.random() * 4).toFixed(3), ask: (273 + Math.random() * 13).toFixed(3), value: Math.floor(Math.random() * 1300) + 300,
  }));
  const displayBookBot = bookArr.length > 0 ? bookArr.slice(Math.ceil(bookArr.length / 2)) : Array.from({ length: 12 }, () => ({
    asset: Math.floor(Math.random() * 9000) + 100, bid: (271 + Math.random() * 8).toFixed(3), ask: (271 + Math.random() * 6).toFixed(3), volume: '-',
  }));

  /* ── Fallback: News Feed ── */
  const displayNews = newsArr.length > 0 ? newsArr : [
    { time: '2 min ago',  text: 'Evercore ISI: market volatility expected to rise amid trade policy uncertainty heading into Q3...', type: 'warning' },
    { time: '7 min ago',  text: 'Nvidia reports record data center revenue, beating estimates by 12% on strong AI chip demand...', type: 'positive' },
    { time: '15 min ago', text: 'US Treasury yields spike as Fed signals fewer rate cuts, SPX futures down 0.8% in after-hours...', type: 'negative' },
    { time: '32 min ago', text: 'Apple announces strategic AI partnership with OpenAI; shares up 2.1% on the news...', type: 'info' },
    { time: '1 hour ago', text: 'CrowdStrike downgraded by Morgan Stanley on valuation concerns after 60% YTD run-up...', type: 'negative' },
  ];

  /* ── Fallback: System Status Log ── */
  const displayStatus = statusArr.length > 0 ? statusArr : [
    { time: '16:55:28', text: 'Processed Brackets succeeded.', type: 'success' },
    { time: '16:55:27', text: 'Processed Quotes succeeded.', type: 'success' },
    { time: '16:55:25', text: 'Rescanned System Status log.', type: 'warning' },
    { time: '16:55:24', text: 'Order:Vertation moved compose queue.', type: 'info' },
    { time: '16:55:22', text: 'Processed Destinations exceeded.', type: 'success' },
    { time: '16:55:21', text: 'Processed Quotes succeeded.', type: 'success' },
    { time: '16:55:20', text: 'Rescanned System Status log.', type: 'warning' },
    { time: '16:55:18', text: 'Kelly optimizer recalc: edge 4.2%, quality 0.88', type: 'info' },
    { time: '16:55:15', text: 'Alpaca WS heartbeat OK. Latency: 8ms', type: 'success' },
    { time: '16:55:12', text: 'Risk gov: heat 68%, regime BULL_VOLATILE', type: 'info' },
    { time: '16:55:10', text: 'Bracket NVDA queued: 785.50/820/770', type: 'success' },
    { time: '16:55:08', text: 'Circuit breaker armed: max $15,000/day', type: 'warning' },
    { time: '16:55:05', text: 'Market data: 342 symbols active', type: 'success' },
    { time: '16:55:01', text: 'Session opened. Equity: $1,580,420.55', type: 'info' },
  ];

  /* ── Fallback: Positions ── */
  const displayPositions = posArr.length > 0 ? posArr : [
    { symbol: 'SPX',  orderName: 'Iron Condor 06/21',      orderType: 'Multi-Leg', quantity: 10,   limit: '$2.45',   status: 'FILLED',   legs: 4 },
    { symbol: 'NVDA', orderName: 'Bracket Buy 785.50',     orderType: 'Bracket',   quantity: 150,  limit: '$785.50', status: 'PENDING',  legs: 3 },
    { symbol: 'AAPL', orderName: 'Trail Stop -1.5%',       orderType: 'Trailing',  quantity: 500,  limit: 'T-1.5%',  status: 'ACCEPTED', legs: 1 },
    { symbol: 'TSLA', orderName: 'OCO Exit 195/180',       orderType: 'OCO',       quantity: 200,  limit: '$195.00', status: 'ACCEPTED', legs: 2 },
    { symbol: 'MSFT', orderName: 'OTO Entry + TP',         orderType: 'OTO',       quantity: 100,  limit: '$405.00', status: 'PARTIAL',  legs: 2 },
    { symbol: 'META', orderName: 'Limit Buy 480',          orderType: 'Limit',     quantity: 300,  limit: '$480.00', status: 'FILLED',   legs: 1 },
    { symbol: 'PLTR', orderName: 'Bracket Short 25.50',    orderType: 'Bracket',   quantity: 1000, limit: '$25.50',  status: 'ACCEPTED', legs: 3 },
    { symbol: 'AMD',  orderName: 'Trail Stop -$2.00',      orderType: 'Trailing',  quantity: 250,  limit: 'T-$2.00', status: 'ACCEPTED', legs: 1 },
  ];

  /* Strike helpers */
  const callIdx = orderForm.callStrikeIdx ?? 0;
  const putIdx  = orderForm.putStrikeIdx  ?? 0;
  const curCall = displayCallStrikes[callIdx] || displayCallStrikes[0];
  const curPut  = displayPutStrikes[putIdx]  || displayPutStrikes[0];

  const fmtSz = (s) => {
    if (!s) return '';
    if (s >= 1000000) return (s / 1000000).toFixed(1) + 'M';
    if (s >= 1000) return (s / 1000).toFixed(0) + 'K';
    return '+' + s;
  };

  /* ────────────────────────────────────────
     RENDER
     ──────────────────────────────────────── */
  return (
    <div className="flex flex-col overflow-hidden -m-6" style={{ height: 'calc(100vh - 64px)' }}>

      {/* ═══════ HEADER BAR ═══════ */}
      <div className="h-[42px] bg-[#070d18] border-b border-[#1a2744] flex items-center px-5 gap-5 shrink-0 relative">
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-400 to-transparent" />
        <span className="font-mono text-xs font-semibold text-cyan-400 uppercase tracking-wider">Trade Execution</span>
        <div className="flex items-center gap-5 ml-auto font-mono text-[10px]">
          <span><span className="text-[#5a6f8a] mr-1">Portfolio:</span><span className="text-[#e8f0fe]">{fmtUsd(portfolio.value || 1580430.55)}</span></span>
          <span className="text-[#243352]">|</span>
          <span><span className="text-[#5a6f8a] mr-1">Daily P/L:</span><span className="text-[#00e676]">+{fmtUsd(portfolio.dailyPnl || 12500.80)}</span></span>
          <span className="text-[#243352]">|</span>
          <span><span className="text-[#5a6f8a] mr-1">Status:</span><span className="text-cyan-400 font-semibold">{portfolio.status || 'ELITE'}</span></span>
          <span className="text-[#243352]">|</span>
          <span><span className="text-[#5a6f8a] mr-1">Latency:</span><span className="text-[#e8f0fe]">{portfolio.latency || 8}ms</span></span>
        </div>
      </div>

      {/* ═══════ QUICK EXECUTION BAR ═══════ */}
      <div className="h-10 bg-[#0a1020] border-b border-[#1a2744] flex items-center px-4 gap-2 shrink-0">
        <span className="font-mono text-[9px] text-[#5a6f8a] uppercase tracking-[1px] mr-2">Quick Execution</span>
        {/* Market Buy */}
        <button
          onClick={() => { if (window.confirm(`Market BUY ${orderForm.symbol} x${orderForm.quantity}?`)) withPreflight('buy', executeMarketBuy); }}
          disabled={loading || preflightLoading}
          className="px-3.5 py-[5px] rounded-[3px] font-mono text-[9px] font-semibold bg-[#00e676] text-black hover:brightness-[1.2] hover:-translate-y-px transition-all disabled:opacity-50 flex items-center gap-1.5"
        >Market Buy <span className="text-[7px] bg-black/30 px-[3px] py-px rounded-sm">B</span></button>
        {/* Market Sell */}
        <button
          onClick={() => { if (window.confirm(`Market SELL ${orderForm.symbol} x${orderForm.quantity}?`)) withPreflight('sell', executeMarketSell); }}
          disabled={loading || preflightLoading}
          className="px-3.5 py-[5px] rounded-[3px] font-mono text-[9px] font-semibold bg-[#ff3860] text-white hover:brightness-[1.2] hover:-translate-y-px transition-all disabled:opacity-50 flex items-center gap-1.5"
        >Market Sell <span className="text-[7px] bg-black/30 px-[3px] py-px rounded-sm">S</span></button>
        {/* Limit Buy */}
        <button
          onClick={() => withPreflight('buy', executeLimitBuy)}
          disabled={loading || preflightLoading}
          className="px-3.5 py-[5px] rounded-[3px] font-mono text-[9px] font-semibold bg-transparent border border-[#00e676] text-[#00e676] hover:brightness-[1.2] hover:-translate-y-px transition-all disabled:opacity-50 flex items-center gap-1.5"
        >Limit Buy <span className="text-[7px] bg-black/30 px-[3px] py-px rounded-sm">L</span></button>
        {/* Limit Sell */}
        <button
          onClick={() => withPreflight('sell', executeLimitSell)}
          disabled={loading || preflightLoading}
          className="px-3.5 py-[5px] rounded-[3px] font-mono text-[9px] font-semibold bg-transparent border border-[#ff3860] text-[#ff3860] hover:brightness-[1.2] hover:-translate-y-px transition-all disabled:opacity-50 flex items-center gap-1.5"
        >Limit Sell <span className="text-[7px] bg-black/30 px-[3px] py-px rounded-sm">K</span></button>
        {/* Stop Loss */}
        <button
          onClick={executeStopLoss}
          disabled={loading || preflightLoading}
          className="px-3.5 py-[5px] rounded-[3px] font-mono text-[9px] font-semibold bg-transparent border border-[#ffab00] text-[#ffab00] hover:brightness-[1.2] hover:-translate-y-px transition-all disabled:opacity-50 flex items-center gap-1.5"
        >Stop Loss <span className="text-[7px] bg-black/30 px-[3px] py-px rounded-sm">T</span></button>
      </div>

      {/* ═══════ MAIN 4-COLUMN GRID ═══════
           Cols: 240px  1fr  240px  300px
           Rows: 1fr   200px
           Col 4 row 1 = Charts + News (split vertically inside)
           Bottom-left = cols 1-3
           Bottom-right (col 4) = System Status Log
      */}
      <div
        className="flex-1 grid overflow-hidden min-h-0"
        style={{
          gridTemplateColumns: '240px 1fr 240px 300px',
          gridTemplateRows: '1fr 200px',
          gap: '1px',
          background: '#1a2744',
        }}
      >

        {/* ═══ COL 1 ROW 1: MULTI-PRICE LADDER ═══ */}
        <div className="bg-[#0a1020] flex flex-col overflow-hidden">
          <PanelHead>Multi-Price Ladder</PanelHead>
          <div className="flex-1 overflow-y-auto">
            {displayLadder.map((row, i) => {
              const price = parseFloat(row.price) || 0;
              const isCurrent = row.isCurrent || row.side === 'current';
              const isAbove = row.side === 'ask' && !isCurrent;
              const isBelow = row.side === 'bid' && !isCurrent;
              const bidSz = row.bidSize || (row.side === 'bid' ? (row.size || 0) : 0);
              const askSz = row.askSize || (row.side === 'ask' ? (row.size || 0) : 0);
              const bidPct = isBelow ? Math.min((bidSz / maxBidSz) * 100, 100) : 0;
              const askPct = isAbove ? Math.min((askSz / maxAskSz) * 100, 100) : 0;

              return (
                <div
                  key={i}
                  onClick={() => setSelectedRow(row.row || i + 1)}
                  className={clsx(
                    'grid h-5 items-center border-b border-[rgba(26,39,68,0.3)] font-mono text-[9px] cursor-pointer transition-colors',
                    isCurrent && 'bg-[rgba(0,212,232,0.06)]',
                    !isCurrent && 'hover:bg-[rgba(0,212,232,0.04)]',
                  )}
                  style={{ gridTemplateColumns: '42px 1fr 56px 1fr 42px' }}
                >
                  {/* Bid volume */}
                  <div className="text-center text-[8px] text-[#00e676]">{bidSz > 0 ? fmtSz(bidSz) : ''}</div>
                  {/* Bid bar */}
                  <div className="flex justify-end pr-0.5 h-3">
                    {bidPct > 0 && <div className="h-3 rounded-[1px]" style={{ width: `${bidPct}%`, background: 'linear-gradient(270deg, rgba(0,230,118,0.35), rgba(0,230,118,0.05))' }} />}
                  </div>
                  {/* Price */}
                  <div className={clsx(
                    'text-center font-semibold text-[9px]',
                    isCurrent && 'bg-cyan-400 text-black rounded-sm py-px',
                    isAbove && !isCurrent && 'text-[#00e676]',
                    isBelow && !isCurrent && 'text-[#ff3860]',
                  )}>{price.toFixed(2)}</div>
                  {/* Ask bar */}
                  <div className="flex justify-start pl-0.5 h-3">
                    {askPct > 0 && <div className="h-3 rounded-[1px]" style={{ width: `${askPct}%`, background: 'linear-gradient(90deg, rgba(255,56,96,0.35), rgba(255,56,96,0.05))' }} />}
                  </div>
                  {/* Ask volume */}
                  <div className="text-center text-[8px] text-[#ff3860]">{askSz > 0 ? fmtSz(askSz) : ''}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ═══ COL 2 ROW 1: ADVANCED ORDER BUILDER + VISUAL PRICE LADDER ═══ */}
        <div className="bg-[#1a2744] flex flex-row overflow-hidden" style={{ gap: '1px' }}>
        <div className="bg-[#0a1020] flex flex-col overflow-hidden" style={{ flex: '3 1 0%' }}>
          <PanelHead>Advanced Order Builder</PanelHead>
          <div className="flex-1 overflow-y-auto p-3.5">
            {/* Tabs */}
            <div className="flex gap-0 mb-3.5 border-b border-[#1a2744]">
              {['Advanced', 'Strategy', 'News'].map(tab => (
                <button
                  key={tab}
                  onClick={() => setBuilderTab(tab)}
                  className={clsx(
                    'px-3.5 py-[5px] text-[10px] border-b-2 transition-colors cursor-pointer',
                    builderTab === tab ? 'text-cyan-400 border-cyan-400' : 'text-[#5a6f8a] border-transparent hover:text-[#c8d6e5]',
                  )}
                >{tab}</button>
              ))}
            </div>

            <FormField label="Symbol:">
              <FormSelect value={orderForm.symbol} onChange={e => updateOrderForm({ symbol: e.target.value })}>
                {symbols.map(s => <option key={s} value={s}>{s}</option>)}
              </FormSelect>
            </FormField>

            <FormField label="Strategy:">
              <FormSelect value={orderForm.strategy} onChange={e => updateOrderForm({ strategy: e.target.value })}>
                {STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
              </FormSelect>
            </FormField>

            {/* Call with +/- stepper */}
            <FormField label="Call:">
              <div className="flex-1 flex items-center gap-1">
                <button onClick={() => updateOrderForm({ callStrikeIdx: Math.max(callIdx - 1, 0) })} className="w-6 h-6 flex items-center justify-center bg-[#111b2e] border border-[#1a2744] rounded-[3px] text-[#5a6f8a] hover:border-cyan-400 hover:text-cyan-400 transition-colors shrink-0"><Minus className="w-3 h-3" /></button>
                <FormInput readOnly value={curCall} className="flex-1 text-center" />
                <button onClick={() => updateOrderForm({ callStrikeIdx: Math.min(callIdx + 1, displayCallStrikes.length - 1) })} className="w-6 h-6 flex items-center justify-center bg-[#111b2e] border border-[#1a2744] rounded-[3px] text-[#5a6f8a] hover:border-cyan-400 hover:text-cyan-400 transition-colors shrink-0"><Plus className="w-3 h-3" /></button>
              </div>
            </FormField>

            {/* Put with +/- stepper */}
            <FormField label="Put:">
              <div className="flex-1 flex items-center gap-1">
                <button onClick={() => updateOrderForm({ putStrikeIdx: Math.max(putIdx - 1, 0) })} className="w-6 h-6 flex items-center justify-center bg-[#111b2e] border border-[#1a2744] rounded-[3px] text-[#5a6f8a] hover:border-cyan-400 hover:text-cyan-400 transition-colors shrink-0"><Minus className="w-3 h-3" /></button>
                <FormInput readOnly value={curPut} className="flex-1 text-center" />
                <button onClick={() => updateOrderForm({ putStrikeIdx: Math.min(putIdx + 1, displayPutStrikes.length - 1) })} className="w-6 h-6 flex items-center justify-center bg-[#111b2e] border border-[#1a2744] rounded-[3px] text-[#5a6f8a] hover:border-cyan-400 hover:text-cyan-400 transition-colors shrink-0"><Plus className="w-3 h-3" /></button>
              </div>
            </FormField>

            <FormField label="Quantity:">
              <div className="flex-1 flex items-center gap-1.5">
                <FormInput type="number" value={orderForm.quantity} onChange={e => updateOrderForm({ quantity: parseInt(e.target.value) || 0 })} className="flex-1" />
                <span className="text-[9px] text-[#5a6f8a] shrink-0">Contracts</span>
              </div>
            </FormField>

            <FormField label="Limit:">
              <FormInput type="number" step="0.01" value={orderForm.limitPrice} onChange={e => updateOrderForm({ limitPrice: parseFloat(e.target.value) || 0 })} className="flex-1" />
            </FormField>

            {/* Execute button -- cyan/teal gradient matching mockup */}
            <button
              onClick={() => withPreflight('buy', executeAdvancedOrder)}
              disabled={loading}
              className="w-full py-3 mt-3.5 rounded font-mono text-[13px] font-bold text-black uppercase tracking-[1px] bg-gradient-to-br from-[#007a8a] to-[#00d4e8] hover:brightness-[1.15] hover:-translate-y-px transition-all disabled:opacity-50 disabled:cursor-wait shadow-[0_4px_20px_rgba(0,212,232,0.15)] hover:shadow-[0_6px_30px_rgba(0,212,232,0.3)]"
            >{loading ? 'Executing...' : 'Execute Order'}</button>
          </div>
        </div>
        {/* VisualPriceLadder — narrow adjacent column (~1/4 width) */}
        <div className="bg-[#0a1020] flex flex-col overflow-hidden" style={{ flex: '1 1 0%', minWidth: 180 }}>
          <VisualPriceLadder
            entry={185.50}
            stop={182.00}
            target={194.25}
            currentPrice={186.20}
            symbol="AAPL"
          />
        </div>
        </div>{/* /col2-flex-row */}

        {/* ═══ COL 3 ROW 1: LIVE ORDER BOOK ═══ */}
        <div className="bg-[#0a1020] flex flex-col overflow-hidden">
          <PanelHead>Live Order Book</PanelHead>
          <div className="flex-1 overflow-y-auto">
            {/* Top asks */}
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className="px-1.5 py-1 font-mono text-[8px] text-[#5a6f8a] uppercase text-left border-b border-[#1a2744] sticky top-0 bg-[#070d18] z-[2]">Asset</th>
                  <th className="px-1.5 py-1 font-mono text-[8px] text-[#5a6f8a] uppercase text-right border-b border-[#1a2744] sticky top-0 bg-[#070d18] z-[2]">Bid</th>
                  <th className="px-1.5 py-1 font-mono text-[8px] text-[#5a6f8a] uppercase text-right border-b border-[#1a2744] sticky top-0 bg-[#070d18] z-[2]">Ask</th>
                  <th className="px-1.5 py-1 font-mono text-[8px] text-[#5a6f8a] uppercase text-right border-b border-[#1a2744] sticky top-0 bg-[#070d18] z-[2]">Value</th>
                </tr>
              </thead>
              <tbody>
                {displayBookTop.map((r, i) => (
                  <tr key={i} className="hover:bg-[rgba(0,212,232,0.03)]">
                    <td className="px-1.5 py-[3px] font-mono text-[9px] text-[#5a6f8a] border-b border-[rgba(26,39,68,0.3)]">{r.asset || '-'}</td>
                    <td className="px-1.5 py-[3px] font-mono text-[9px] text-[#00e676] text-right border-b border-[rgba(26,39,68,0.3)]">{parseFloat(r.bid || r.price || 0).toFixed(3)}</td>
                    <td className="px-1.5 py-[3px] font-mono text-[9px] text-[#ff3860] text-right border-b border-[rgba(26,39,68,0.3)]">{parseFloat(r.ask || 0).toFixed(3)}</td>
                    <td className="px-1.5 py-[3px] font-mono text-[9px] text-[#c8d6e5] text-right border-b border-[rgba(26,39,68,0.3)]">{r.value || r.total || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="border-t border-[#1a2744]" />
            {/* Bottom bids */}
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className="px-1.5 py-1 font-mono text-[8px] text-[#5a6f8a] uppercase text-left border-b border-[#1a2744] bg-[#070d18]">Asset $</th>
                  <th className="px-1.5 py-1 font-mono text-[8px] text-[#5a6f8a] uppercase text-right border-b border-[#1a2744] bg-[#070d18]">Bid</th>
                  <th className="px-1.5 py-1 font-mono text-[8px] text-[#5a6f8a] uppercase text-right border-b border-[#1a2744] bg-[#070d18]">Ask</th>
                  <th className="px-1.5 py-1 font-mono text-[8px] text-[#5a6f8a] uppercase text-right border-b border-[#1a2744] bg-[#070d18]">Volume</th>
                </tr>
              </thead>
              <tbody>
                {displayBookBot.map((r, i) => (
                  <tr key={i} className="hover:bg-[rgba(0,212,232,0.03)]">
                    <td className="px-1.5 py-[3px] font-mono text-[9px] text-[#c8d6e5] border-b border-[rgba(26,39,68,0.3)]">{r.asset || '-'}</td>
                    <td className="px-1.5 py-[3px] font-mono text-[9px] text-[#00e676] text-right border-b border-[rgba(26,39,68,0.3)]">{parseFloat(r.bid || r.price || 0).toFixed(3)}</td>
                    <td className="px-1.5 py-[3px] font-mono text-[9px] text-[#ff3860] text-right border-b border-[rgba(26,39,68,0.3)]">{parseFloat(r.ask || 0).toFixed(3)}</td>
                    <td className="px-1.5 py-[3px] font-mono text-[9px] text-[#c8d6e5] text-right border-b border-[rgba(26,39,68,0.3)]">{r.volume || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ═══ COL 4 ROW 1: PRICE CHARTS + NEWS FEED ═══ */}
        <div className="flex flex-col overflow-hidden" style={{ background: '#1a2744' }}>
          {/* Price Charts */}
          <div className="flex-1 bg-[#0a1020] flex flex-col overflow-hidden min-h-0">
            <PanelHead>Price Charts</PanelHead>
            <div className="px-2.5 py-1 font-mono text-[8px] text-[#5a6f8a] flex items-center gap-2 border-b border-[#1a2744] shrink-0">
              <span className="text-[#e8f0fe] font-semibold">{orderForm.symbol || 'SPY'}</span>
              <span>-</span>
              <span>S&P 500 Index</span>
              <div className="ml-auto flex gap-1">
                {['1M', '5M', '15M', '1H'].map(tf => (
                  <button
                    key={tf}
                    onClick={() => setChartTimeframe(tf)}
                    className={clsx(
                      'px-1.5 py-0.5 rounded-sm text-[7px] font-mono font-semibold transition-colors',
                      chartTimeframe === tf ? 'bg-cyan-400/20 text-cyan-400' : 'text-[#5a6f8a] hover:text-[#c8d6e5]',
                    )}
                  >{tf}</button>
                ))}
              </div>
            </div>
            <div className="flex-1 relative p-1.5 min-h-0">
              <div ref={chartRef} className="w-full h-full" />
            </div>
          </div>
          {/* 1px gap */}
          <div className="h-px bg-[#1a2744] shrink-0" />
          {/* News Feed */}
          <div className="flex-1 bg-[#0a1020] flex flex-col overflow-hidden min-h-0">
            <PanelHead>News Feed</PanelHead>
            <div className="flex-1 overflow-y-auto">
              {displayNews.map((item, i) => {
                const dotColor =
                  item.type === 'negative' || item.type === 'error' ? 'bg-[#ff3860]' :
                  item.type === 'warning' ? 'bg-[#ffab00]' :
                  item.type === 'positive' || item.type === 'success' ? 'bg-[#00e676]' :
                  'bg-cyan-400';
                return (
                  <div key={i} className="px-2.5 py-1.5 border-b border-[rgba(26,39,68,0.3)] flex gap-1.5 items-start">
                    <span className={clsx('w-1 h-1 rounded-full mt-1.5 shrink-0', dotColor)} />
                    <div className="min-w-0">
                      <div className="text-[9px] text-[#5a6f8a] leading-snug">{item.text}</div>
                      <div className="text-[7px] text-[#5a6f8a] opacity-60 mt-0.5">{item.time}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* ═══ BOTTOM LEFT (cols 1-3): LIVE POSITIONS ═══ */}
        <div className="bg-[#0a1020] flex flex-col overflow-hidden" style={{ gridColumn: '1 / 4' }}>
          <div className="flex gap-0 bg-[#070d18] border-b border-[#1a2744] shrink-0">
            <button className="px-3.5 py-1.5 font-mono text-[9px] text-cyan-400 border-b-2 border-cyan-400 cursor-pointer">Live Positions</button>
            <button className="px-3.5 py-1.5 font-mono text-[9px] text-[#5a6f8a] border-b-2 border-transparent cursor-pointer hover:text-[#c8d6e5]">Order History</button>
          </div>
          <div className="flex-1 overflow-y-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  {['Asset', 'Order Name', 'Order Type', 'Quantity', 'Limit', 'Order Log', 'Legs'].map(h => (
                    <th key={h} className="px-2 py-1.5 font-mono text-[8px] text-[#5a6f8a] uppercase text-left border-b border-[#1a2744] sticky top-0 bg-[#0a1020] z-[2]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {displayPositions.map((pos, i) => {
                  const sc = pos.status === 'FILLED' || pos.status === 'ACCEPTED' ? 'text-[#00e676]' : pos.status === 'PENDING' || pos.status === 'PARTIAL' ? 'text-[#ffab00]' : 'text-[#c8d6e5]';
                  return (
                    <tr key={i} className="hover:bg-[rgba(0,212,232,0.03)]">
                      <td className="px-2 py-1 font-mono text-[9px] text-cyan-400 border-b border-[rgba(26,39,68,0.3)]">{pos.symbol}</td>
                      <td className="px-2 py-1 font-mono text-[9px] text-[#c8d6e5] border-b border-[rgba(26,39,68,0.3)]">{pos.orderName || `${pos.side || ''} ${pos.symbol}`}</td>
                      <td className="px-2 py-1 font-mono text-[9px] text-[#c8d6e5] border-b border-[rgba(26,39,68,0.3)]">{pos.orderType || 'Market'}</td>
                      <td className="px-2 py-1 font-mono text-[9px] text-[#c8d6e5] border-b border-[rgba(26,39,68,0.3)]">{pos.quantity || pos.qty || 0}</td>
                      <td className="px-2 py-1 font-mono text-[9px] text-[#c8d6e5] border-b border-[rgba(26,39,68,0.3)]">{pos.limit || (pos.avgPrice ? fmtUsd(pos.avgPrice) : '-')}</td>
                      <td className={clsx('px-2 py-1 font-mono text-[9px] border-b border-[rgba(26,39,68,0.3)]', sc)}>{pos.status || 'ACTIVE'}</td>
                      <td className="px-2 py-1 font-mono text-[9px] text-[#c8d6e5] border-b border-[rgba(26,39,68,0.3)]">{pos.legs || '-'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* ═══ BOTTOM RIGHT (col 4): SYSTEM STATUS LOG ═══ */}
        <div className="bg-[#0a1020] flex flex-col overflow-hidden">
          <PanelHead>System Status Log</PanelHead>
          <div className="flex-1 overflow-y-auto px-2.5 py-1.5 font-mono text-[8px]">
            {displayStatus.map((item, i) => {
              const tc =
                item.type === 'success' ? 'text-[#00e676]' :
                item.type === 'warning' ? 'text-[#ffab00]' :
                item.type === 'info'    ? 'text-cyan-400' :
                item.type === 'error'   ? 'text-[#ff3860]' :
                'text-[#00e676]';
              return (
                <div key={i} className="mb-px leading-relaxed">
                  <span className="text-[#5a6f8a]">[{item.time}]</span>{' '}
                  <span className={tc}>{item.text}</span>
                </div>
              );
            })}
          </div>
        </div>

      </div>{/* /main-grid */}

      {/* ═══ COUNCIL DECISION PANEL ═══ */}
      <div className="shrink-0 border-t border-[#1a2744] bg-[#0a1020] p-3">
        <CouncilDecisionPanel
          onExecute={(data) => { console.log('Execute:', data); }}
          onOverride={() => { console.log('Override'); }}
          onDismiss={() => { console.log('Dismiss'); }}
        />
      </div>
    </div>
  );
}
