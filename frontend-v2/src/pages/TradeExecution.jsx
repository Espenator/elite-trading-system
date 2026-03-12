import React, { useEffect, useCallback, useRef, useState } from 'react';
import { toast } from 'react-toastify';
import useTradeExecution from '../hooks/useTradeExecution';
import { getApiUrl, getAuthHeaders, WS_CHANNELS } from '../config/api';
import { useApi } from '../hooks/useApi';
import ws from '../services/websocket';
import clsx from 'clsx';
import { Minus, Plus, Power } from 'lucide-react';
import { VisualPriceLadder, CouncilDecisionPanel } from '../components/dashboard/TradeExecutionWidgets';

/* ────────────────────────────────────────────────────────────
   Shared tiny components used only in this page
   ──────────────────────────────────────────────────────────── */
const PanelHead = ({ children }) => (
  <div className="px-3 py-[7px] border-b border-[rgba(42,52,68,0.5)] flex items-center justify-between bg-[#111827] shrink-0">
    <span className="font-mono text-[9px] font-semibold text-gray-500 uppercase tracking-[0.5px]">{children}</span>
    <div className="flex gap-[3px]">
      <span className="w-[3px] h-[3px] rounded-full bg-[#5a6f8a]" />
      <span className="w-[3px] h-[3px] rounded-full bg-[#5a6f8a]" />
      <span className="w-[3px] h-[3px] rounded-full bg-[#5a6f8a]" />
    </div>
  </div>
);

const FormField = ({ label, children }) => (
  <div className="flex items-center mb-2.5">
    <label className="w-[90px] text-[10px] text-gray-500 shrink-0">{label}</label>
    {children}
  </div>
);

const FormSelect = ({ value, onChange, children, className }) => (
  <select
    value={value}
    onChange={onChange}
    className={clsx(
      'flex-1 bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] text-white px-2.5 py-1.5 font-mono text-[10px] rounded-[3px] outline-none',
      'focus:border-[#00D9FF] focus:shadow-[0_0_8px_rgba(0,212,232,0.15)]',
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
      'bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] text-white px-2.5 py-1.5 font-mono text-[10px] rounded-[3px] outline-none',
      'focus:border-[#00D9FF] focus:shadow-[0_0_8px_rgba(0,212,232,0.15)]',
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
    refresh: refreshTradeData,
  } = useTradeExecution();

  // --- WebSocket live updates for trade execution ---
  useEffect(() => {
    const unsubs = [
      ws.on(WS_CHANNELS.trades, () => refreshTradeData()),
      ws.on(WS_CHANNELS.market, () => refreshTradeData()),
      ws.on(WS_CHANNELS.council_verdict, () => refreshTradeData()),
    ];
    return () => unsubs.forEach((fn) => fn());
  }, [refreshTradeData]);

  // Symbol universe from API (fallback to common tickers)
  const { data: stocksData } = useApi('stocks', { pollIntervalMs: 120000 });
  const symbolList = (stocksData?.symbols || stocksData?.tickers || stocksData?.universe || [])
    .map(s => typeof s === 'string' ? s : (s.symbol || s.ticker))
    .filter(Boolean);
  const symbols = symbolList;

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
  const FALLBACK_CALL = [];
  const FALLBACK_PUT  = [];
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
  const [killSwitchModalOpen, setKillSwitchModalOpen] = useState(false);
  const [killSwitchLoading, setKillSwitchLoading] = useState(false);

  useEffect(() => {
    if (!killSwitchModalOpen) return;
    const onKey = (e) => { if (e.key === 'Escape') setKillSwitchModalOpen(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [killSwitchModalOpen]);

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
        const raw = typeof time === 'string' ? time.slice(0, 10) : time; const tStr = typeof raw === 'string' && raw.includes('/') ? (() => { const p = raw.split('/'); return p.length === 3 && p[2].length === 4 ? `${p[2]}-${p[0].padStart(2,'0')}-${p[1].padStart(2,'0')}` : raw; })() : raw;
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

  const handleKillSwitch = useCallback(async () => {
    setKillSwitchLoading(true);
    try {
      const res = await fetch(getApiUrl('orders/emergency-stop'), { method: 'POST', headers: getAuthHeaders() });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || data?.message || `HTTP ${res.status}`);
      toast.error('Kill Switch activated — orders cancelled, positions closed.');
      setKillSwitchModalOpen(false);
      refreshTradeData();
    } catch (err) {
      toast.error(err?.message || 'Kill Switch request failed');
    } finally {
      setKillSwitchLoading(false);
    }
  }, [refreshTradeData]);

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

  /* ── Data from API only (no mock fallbacks) ── */
  const displayLadder = ladderArr;
  const maxBidSz = Math.max(...displayLadder.map(r => r.side === 'bid' ? (r.bidSize || r.size || 0) : 0), 1);
  const maxAskSz = Math.max(...displayLadder.map(r => r.side === 'ask' ? (r.askSize || r.size || 0) : 0), 1);

  const bookBids = orderBook?.bids || [];
  const bookAsks = orderBook?.asks || [];
  const displayBookBids = bookBids.slice(0, 10);
  const displayBookAsks = bookAsks.slice(0, 10);

  const displayNews = newsArr;
  const displayStatus = statusArr;
  const displayPositions = posArr;

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
      <div className="h-[42px] bg-[#111827] border-b border-[rgba(42,52,68,0.5)] flex items-center px-5 gap-5 shrink-0 relative">
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-400 to-transparent" />
        <span className="font-mono text-sm font-bold text-white uppercase tracking-widest">TRADE EXECUTION</span>
        <div className="flex items-center gap-5 ml-auto font-mono text-[10px]">
          <span><span className="text-gray-500 mr-1">Portfolio:</span><span className="text-white">{fmtUsd(portfolio?.value)}</span></span>
          <span className="text-gray-700">|</span>
          <span><span className="text-gray-500 mr-1">Daily P/L:</span><span className="text-[#00e676]">{portfolio?.dailyPnl != null ? (portfolio.dailyPnl >= 0 ? '+' : '') + fmtUsd(portfolio.dailyPnl) : '—'}</span></span>
          <span className="text-gray-700">|</span>
          <span><span className="text-gray-500 mr-1">Status:</span><span className="px-2 py-0.5 rounded text-[9px] font-bold bg-[#00D9FF]/25 text-[#00D9FF]">{portfolio?.status ?? '—'}</span></span>
          <span className="text-gray-700">|</span>
          <span><span className="text-gray-500 mr-1">Latency:</span><span className="text-white">{portfolio?.latency != null ? `${portfolio.latency}ms` : '—'}</span></span>
          <span className="text-gray-700">|</span>
          <button
            type="button"
            onClick={() => setKillSwitchModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded font-mono text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30 transition-colors"
            title="Emergency: close all positions and halt trading"
          >
            <Power className="w-3.5 h-3.5" />
            KILL SWITCH
          </button>
        </div>
      </div>

      {/* Kill Switch confirmation modal */}
      {killSwitchModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="kill-switch-title" onClick={() => setKillSwitchModalOpen(false)}>
          <div className="w-full max-w-md rounded-lg border border-red-500/40 bg-[#111827] p-6 shadow-xl" onClick={e => e.stopPropagation()}>
            <h2 id="kill-switch-title" className="text-lg font-bold text-red-400 mb-2">Kill Switch</h2>
            <p className="text-sm text-gray-300 mb-4">
              This will close all positions and halt trading. Are you absolutely sure?
            </p>
            <div className="flex gap-3 justify-end">
              <button
                type="button"
                onClick={() => setKillSwitchModalOpen(false)}
                disabled={killSwitchLoading}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-[rgba(42,52,68,0.6)] text-gray-300 border border-[rgba(42,52,68,0.8)] hover:bg-[rgba(42,52,68,0.8)] disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleKillSwitch}
                disabled={killSwitchLoading}
                className="px-4 py-2 rounded-lg text-sm font-bold bg-red-600 text-white border border-red-500 hover:bg-red-700 disabled:opacity-50"
              >
                {killSwitchLoading ? 'Activating…' : 'Yes, activate Kill Switch'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════ QUICK EXECUTION BAR ═══════ */}
      <div className="h-10 bg-[#111827]/80 border-b border-[rgba(42,52,68,0.5)] flex items-center px-4 gap-2 shrink-0">
        <span className="font-mono text-[9px] text-gray-500 uppercase tracking-[1px] mr-2">Quick Execution</span>
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
        >Limit Sell <span className="text-[7px] bg-black/30 px-[3px] py-px rounded-sm">O</span></button>
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
          background: 'rgba(42,52,68,0.5)',
        }}
      >

        {/* ═══ COL 1 ROW 1: MULTI-PRICE LADDER ═══ */}
        <div className="bg-[#111827]/80 flex flex-col overflow-hidden">
          <PanelHead>Multi-Price Ladder</PanelHead>
          <div className="flex-1 overflow-y-auto">
            {displayLadder.length === 0 ? (
              <div className="p-4 text-center font-mono text-[10px] text-gray-500">No price ladder data</div>
            ) : displayLadder.map((row, i) => {
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
                    isCurrent && 'bg-[#00D9FF] text-black rounded-sm py-px',
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
        <div className="bg-[rgba(42,52,68,0.5)] flex flex-row overflow-hidden" style={{ gap: '1px' }}>
        <div className="bg-[#111827]/80 flex flex-col overflow-hidden" style={{ flex: '3 1 0%' }}>
          <PanelHead>Advanced Order Builder</PanelHead>
          <div className="flex-1 overflow-y-auto p-3.5">
            {/* Tabs */}
            <div className="flex gap-0 mb-3.5 border-b border-[rgba(42,52,68,0.5)]">
              {['Advanced', 'Strategy', 'News'].map(tab => (
                <button
                  key={tab}
                  onClick={() => setBuilderTab(tab)}
                  className={clsx(
                    'px-3.5 py-[5px] text-[10px] border-b-2 transition-colors cursor-pointer',
                    builderTab === tab ? 'text-[#00D9FF] border-[#00D9FF]' : 'text-gray-500 border-transparent hover:text-[#c8d6e5]',
                  )}
                >{tab}</button>
              ))}
            </div>

            <FormField label="Symbol:">
              <FormSelect value={orderForm.symbol} onChange={e => updateOrderForm({ symbol: e.target.value })}>
                {symbols.length === 0 ? (
                  <option value="">No symbols (check data source)</option>
                ) : (
                  symbols.map(s => <option key={s} value={s}>{s}</option>)
                )}
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
                <button onClick={() => updateOrderForm({ callStrikeIdx: Math.max(callIdx - 1, 0) })} className="w-6 h-6 flex items-center justify-center bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] rounded-[3px] text-gray-500 hover:border-[#00D9FF] hover:text-[#00D9FF] transition-colors shrink-0"><Minus className="w-3 h-3" /></button>
                <FormInput readOnly value={curCall} className="flex-1 text-center" />
                <button onClick={() => updateOrderForm({ callStrikeIdx: Math.min(callIdx + 1, displayCallStrikes.length - 1) })} className="w-6 h-6 flex items-center justify-center bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] rounded-[3px] text-gray-500 hover:border-[#00D9FF] hover:text-[#00D9FF] transition-colors shrink-0"><Plus className="w-3 h-3" /></button>
              </div>
            </FormField>

            {/* Put with +/- stepper */}
            <FormField label="Put:">
              <div className="flex-1 flex items-center gap-1">
                <button onClick={() => updateOrderForm({ putStrikeIdx: Math.max(putIdx - 1, 0) })} className="w-6 h-6 flex items-center justify-center bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] rounded-[3px] text-gray-500 hover:border-[#00D9FF] hover:text-[#00D9FF] transition-colors shrink-0"><Minus className="w-3 h-3" /></button>
                <FormInput readOnly value={curPut} className="flex-1 text-center" />
                <button onClick={() => updateOrderForm({ putStrikeIdx: Math.min(putIdx + 1, displayPutStrikes.length - 1) })} className="w-6 h-6 flex items-center justify-center bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] rounded-[3px] text-gray-500 hover:border-[#00D9FF] hover:text-[#00D9FF] transition-colors shrink-0"><Plus className="w-3 h-3" /></button>
              </div>
            </FormField>

            <FormField label="Quantity:">
              <div className="flex-1 flex items-center gap-1.5">
                <FormInput type="number" value={orderForm.quantity} onChange={e => updateOrderForm({ quantity: parseInt(e.target.value) || 0 })} className="flex-1" />
                <span className="text-[9px] text-gray-500 shrink-0">Contracts</span>
              </div>
            </FormField>

            <FormField label="Limit:">
              <div className="flex-1 flex gap-2">
                <FormInput type="number" step="0.01" value={orderForm.limitPrice} onChange={e => updateOrderForm({ limitPrice: parseFloat(e.target.value) || 0 })} className="flex-1" placeholder="1.55" />
                <FormInput type="number" step="0.01" value={orderForm.stopPrice} onChange={e => updateOrderForm({ stopPrice: parseFloat(e.target.value) || 0 })} className="flex-1" placeholder="1.00" />
              </div>
            </FormField>

            {/* Execute button -- cyan/teal gradient matching mockup */}
            <button
              onClick={() => withPreflight('buy', executeAdvancedOrder)}
              disabled={loading}
              className="w-full py-3 mt-3.5 rounded font-mono text-[13px] font-bold text-black uppercase tracking-[1px] bg-gradient-to-br from-[#007a8a] to-[#00d4e8] hover:brightness-[1.15] hover:-translate-y-px transition-all disabled:opacity-50 disabled:cursor-wait shadow-[0_4px_20px_rgba(0,212,232,0.15)] hover:shadow-[0_6px_30px_rgba(0,212,232,0.3)] flex items-center justify-center gap-2"
            >{loading ? 'Executing...' : <>Execute Order <span className="text-[9px] bg-black/25 px-[4px] py-px rounded-sm">E</span></>}</button>
          </div>
        </div>
        {/* VisualPriceLadder — narrow adjacent column (~1/4 width) */}
        <div className="bg-[#111827]/80 flex flex-col overflow-hidden" style={{ flex: '1 1 0%', minWidth: 180 }}>
          <VisualPriceLadder
            entry={0}
            stop={0}
            target={0}
            currentPrice={0}
            symbol=""
          />
        </div>
        </div>{/* /col2-flex-row */}

        {/* ═══ COL 3 ROW 1: LIVE ORDER BOOK ═══ */}
        <div className="bg-[#111827]/80 flex flex-col overflow-hidden">
          <PanelHead>Live Order Book</PanelHead>
          <div className="flex-1 overflow-y-auto">
            {displayBookBids.length === 0 && displayBookAsks.length === 0 ? (
              <div className="p-4 text-center font-mono text-[10px] text-gray-500">No order book data</div>
            ) : (
            <>
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className="px-1.5 py-1 font-mono text-[8px] text-gray-500 uppercase text-left border-b border-[rgba(42,52,68,0.5)] sticky top-0 bg-[#111827] z-[2]">Bid</th>
                  <th className="px-1.5 py-1 font-mono text-[8px] text-gray-500 uppercase text-right border-b border-[rgba(42,52,68,0.5)] sticky top-0 bg-[#111827] z-[2]">Size</th>
                  <th className="px-1.5 py-1 font-mono text-[8px] text-gray-500 uppercase text-right border-b border-[rgba(42,52,68,0.5)] sticky top-0 bg-[#111827] z-[2]">Total</th>
                </tr>
              </thead>
              <tbody>
                {displayBookBids.map((r, i) => (
                  <tr key={`b-${i}`} className="hover:bg-[rgba(0,212,232,0.03)]">
                    <td className="px-1.5 py-[3px] font-mono text-[9px] text-[#00e676] border-b border-[rgba(26,39,68,0.3)]">{parseFloat(r.price ?? r.bid ?? 0).toFixed(2)}</td>
                    <td className="px-1.5 py-[3px] font-mono text-[9px] text-[#c8d6e5] text-right border-b border-[rgba(26,39,68,0.3)]">{r.size ?? r.qty ?? 0}</td>
                    <td className="px-1.5 py-[3px] font-mono text-[9px] text-[#c8d6e5] text-right border-b border-[rgba(26,39,68,0.3)]">{r.total ?? r.size ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="border-t-2 border-[rgba(42,52,68,0.5)]" />
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className="px-1.5 py-1 font-mono text-[8px] text-gray-500 uppercase text-left border-b border-[rgba(42,52,68,0.5)] bg-[#111827]">Ask</th>
                  <th className="px-1.5 py-1 font-mono text-[8px] text-gray-500 uppercase text-right border-b border-[rgba(42,52,68,0.5)] bg-[#111827]">Size</th>
                  <th className="px-1.5 py-1 font-mono text-[8px] text-gray-500 uppercase text-right border-b border-[rgba(42,52,68,0.5)] bg-[#111827]">Total</th>
                </tr>
              </thead>
              <tbody>
                {displayBookAsks.map((r, i) => (
                  <tr key={`a-${i}`} className="hover:bg-[rgba(0,212,232,0.03)]">
                    <td className="px-1.5 py-[3px] font-mono text-[9px] text-[#ff3860] border-b border-[rgba(26,39,68,0.3)]">{parseFloat(r.price ?? r.ask ?? 0).toFixed(2)}</td>
                    <td className="px-1.5 py-[3px] font-mono text-[9px] text-[#c8d6e5] text-right border-b border-[rgba(26,39,68,0.3)]">{r.size ?? r.qty ?? 0}</td>
                    <td className="px-1.5 py-[3px] font-mono text-[9px] text-[#c8d6e5] text-right border-b border-[rgba(26,39,68,0.3)]">{r.total ?? r.size ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </>
            )}
          </div>
        </div>

        {/* ═══ COL 4 ROW 1: PRICE CHARTS + NEWS FEED ═══ */}
        <div className="flex flex-col overflow-hidden" style={{ background: 'rgba(42,52,68,0.5)' }}>
          {/* Price Charts */}
          <div className="flex-1 bg-[#111827]/80 flex flex-col overflow-hidden min-h-0">
            <PanelHead>Price Charts</PanelHead>
            <div className="px-2.5 py-1 font-mono text-[8px] text-gray-500 flex items-center gap-2 border-b border-[rgba(42,52,68,0.5)] shrink-0">
              <span className="text-white font-semibold">{orderForm.symbol || 'SPY'}</span>
              <span>-</span>
              <span>S&P 500 Index</span>
              <div className="ml-auto flex gap-1">
                {['1M', '5M', '15M', '1H'].map(tf => (
                  <button
                    key={tf}
                    onClick={() => setChartTimeframe(tf)}
                    className={clsx(
                      'px-1.5 py-0.5 rounded-sm text-[7px] font-mono font-semibold transition-colors',
                      chartTimeframe === tf ? 'bg-[#00D9FF]/20 text-[#00D9FF]' : 'text-gray-500 hover:text-[#c8d6e5]',
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
          <div className="h-px bg-[rgba(42,52,68,0.5)] shrink-0" />
          {/* News Feed */}
          <div className="flex-1 bg-[#111827]/80 flex flex-col overflow-hidden min-h-0">
            <PanelHead>News Feed</PanelHead>
            <div className="flex-1 overflow-y-auto">
              {displayNews.length === 0 ? (
                <div className="p-4 text-center font-mono text-[10px] text-gray-500">No news feed</div>
              ) : displayNews.map((item, i) => {
                const dotColor =
                  item.type === 'negative' || item.type === 'error' ? 'bg-[#ff3860]' :
                  item.type === 'warning' ? 'bg-[#ffab00]' :
                  item.type === 'positive' || item.type === 'success' ? 'bg-[#00e676]' :
                  'bg-[#00D9FF]';
                return (
                  <div key={i} className="px-2.5 py-1.5 border-b border-[rgba(26,39,68,0.3)] flex gap-2 items-start">
                    <span className="text-[8px] font-mono text-gray-500 shrink-0">{item.time}</span>
                    <span className={clsx('w-1.5 h-1.5 rounded-full mt-1 shrink-0', dotColor)} />
                    <div className="text-[9px] text-slate-300 leading-snug min-w-0">{item.text}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* ═══ BOTTOM LEFT (cols 1-3): LIVE POSITIONS ═══ */}
        <div className="bg-[#111827]/80 flex flex-col overflow-hidden" style={{ gridColumn: '1 / 4' }}>
          <div className="flex gap-0 bg-[#111827] border-b border-[rgba(42,52,68,0.5)] shrink-0">
            <button className="px-3.5 py-1.5 font-mono text-[9px] text-[#00D9FF] border-b-2 border-[#00D9FF] cursor-pointer">Live Positions</button>
            <button className="px-3.5 py-1.5 font-mono text-[9px] text-gray-500 border-b-2 border-transparent cursor-pointer hover:text-[#c8d6e5]">Order History</button>
          </div>
          <div className="flex-1 overflow-y-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  {['Symbol', 'Side', 'Quantity', 'Avg. Price', 'Current Price', 'P/L', 'Actions'].map(h => (
                    <th key={h} className="px-2 py-1.5 font-mono text-[8px] text-gray-500 uppercase text-left border-b border-[rgba(42,52,68,0.5)] sticky top-0 bg-[#111827]/80 z-[2]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {displayPositions.length === 0 ? (
                  <tr><td colSpan={7} className="px-2 py-4 text-center font-mono text-[10px] text-gray-500">No positions</td></tr>
                ) : displayPositions.map((pos, i) => {
                  const side = pos.side || (pos.quantity > 0 ? 'Long' : 'Short');
                  const pnl = pos.pnl ?? pos.unrealizedPl ?? pos.pnl_impact ?? 0;
                  const pnlClr = pnl >= 0 ? 'text-[#00e676]' : 'text-[#ff3860]';
                  return (
                    <tr key={i} className="hover:bg-[rgba(0,212,232,0.03)]">
                      <td className="px-2 py-1 font-mono text-[9px] text-[#00D9FF] border-b border-[rgba(26,39,68,0.3)]">{pos.symbol}</td>
                      <td className={clsx('px-2 py-1 font-mono text-[9px] font-semibold border-b border-[rgba(26,39,68,0.3)]', side === 'Long' ? 'text-[#00e676]' : 'text-[#ff3860]')}>{side}</td>
                      <td className="px-2 py-1 font-mono text-[9px] text-[#c8d6e5] border-b border-[rgba(26,39,68,0.3)]">{pos.quantity ?? pos.qty ?? 0}</td>
                      <td className="px-2 py-1 font-mono text-[9px] text-[#c8d6e5] border-b border-[rgba(26,39,68,0.3)]">{(pos.avgPrice ?? pos.avg_entry_price) != null ? fmtUsd(pos.avgPrice ?? pos.avg_entry_price) : '-'}</td>
                      <td className="px-2 py-1 font-mono text-[9px] text-[#c8d6e5] border-b border-[rgba(26,39,68,0.3)]">{(pos.currentPrice ?? pos.current_price ?? pos.market_value) != null ? fmtUsd(pos.currentPrice ?? pos.current_price) : '-'}</td>
                      <td className={clsx('px-2 py-1 font-mono text-[9px] font-semibold border-b border-[rgba(26,39,68,0.3)]', pnlClr)}>{(pnl >= 0 ? '+' : '') + fmtUsd(pnl)}</td>
                      <td className="px-2 py-1 border-b border-[rgba(26,39,68,0.3)]">
                        <div className="flex gap-1">
                          <button onClick={() => closePosition?.(pos.symbol, pos.side)} className="px-1.5 py-0.5 rounded text-[8px] font-medium bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] text-slate-300 hover:text-red-400 hover:border-red-500/30 transition-colors">Close</button>
                          <button onClick={() => adjustPosition?.(pos.symbol, pos.side)} className="px-1.5 py-0.5 rounded text-[8px] font-medium bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] text-slate-300 hover:text-[#00D9FF] transition-colors">Adjust</button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* ═══ BOTTOM RIGHT (col 4): SYSTEM STATUS LOG ═══ */}
        <div className="bg-[#111827]/80 flex flex-col overflow-hidden">
          <PanelHead>System Status Log</PanelHead>
          <div className="flex-1 overflow-y-auto px-2.5 py-1.5 font-mono text-[8px]">
            {displayStatus.length === 0 ? (
              <div className="py-4 text-center text-gray-500">No status log</div>
            ) : displayStatus.map((item, i) => {
              const dotColor =
                item.type === 'success' ? 'bg-[#00e676]' :
                item.type === 'warning' ? 'bg-[#ffab00]' :
                item.type === 'info' ? 'bg-[#00D9FF]' :
                item.type === 'error' ? 'bg-[#ff3860]' : 'bg-[#00e676]';
              const tc =
                item.type === 'success' ? 'text-[#00e676]' :
                item.type === 'warning' ? 'text-[#ffab00]' :
                item.type === 'info' ? 'text-[#00D9FF]' :
                item.type === 'error' ? 'text-[#ff3860]' : 'text-slate-300';
              return (
                <div key={i} className="flex gap-2 items-start py-1 border-b border-[rgba(26,39,68,0.2)] last:border-0">
                  <span className="text-gray-500 shrink-0">{item.time}</span>
                  <span className={clsx('w-1.5 h-1.5 rounded-full mt-1 shrink-0', dotColor)} />
                  <span className={tc}>{item.text}</span>
                </div>
              );
            })}
          </div>
        </div>

      </div>{/* /main-grid */}

      {/* ═══ COUNCIL DECISION PANEL ═══ */}
      <div className="shrink-0 border-t border-[rgba(42,52,68,0.5)] bg-[#111827]/80 p-3">
        <CouncilDecisionPanel
          onExecute={(data) => { console.log('Execute:', data); }}
          onOverride={() => { console.log('Override'); }}
          onDismiss={() => { console.log('Dismiss'); }}
        />
      </div>
    </div>
  );
}
