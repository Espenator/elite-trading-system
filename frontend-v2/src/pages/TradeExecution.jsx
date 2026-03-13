import React, { useEffect, useCallback, useRef, useState } from 'react';
import { toast } from 'react-toastify';
import useTradeExecution from '../hooks/useTradeExecution';
import { getApiUrl, getAuthHeaders, WS_CHANNELS } from '../config/api';
import { useApi } from '../hooks/useApi';
import ws from '../services/websocket';
import { emergencyStop as emergencyStopApi } from '../services/tradeExecutionService';
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
    portfolio, priceLadder, orderBook, positions, newsFeed, systemStatus, recentOrders,
    selectedRow, setSelectedRow, orderForm, updateOrderForm, loading,
    submitOrder, executeMarketBuy, executeMarketSell, executeLimitBuy, executeLimitSell,
    executeStopLoss, executeAdvancedOrder, closePosition, adjustPosition,
    refresh: refreshTradeData,
  } = useTradeExecution();

  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  const [confirmPayload, setConfirmPayload] = useState(null);
  const [killSwitchModalOpen, setKillSwitchModalOpen] = useState(false);
  const [killSwitchStep, setKillSwitchStep] = useState(1);
  const [killSwitchLoading, setKillSwitchLoading] = useState(false);

  const openConfirmModal = useCallback(() => {
    setConfirmPayload({ symbol: orderForm.symbol, side: orderForm.side, orderType: orderForm.orderType || 'market', quantity: orderForm.quantity, limitPrice: orderForm.limitPrice, stopPrice: orderForm.stopPrice, timeInForce: orderForm.timeInForce || 'day' });
    setConfirmModalOpen(true);
  }, [orderForm]);

  const doSubmitOrder = useCallback(async () => {
    if (!confirmPayload) return;
    const { symbol, side, orderType, quantity, limitPrice, stopPrice, timeInForce } = confirmPayload;
    try {
      if (orderType === 'market' && side === 'buy') {
        await executeMarketBuy();
      } else if (orderType === 'market' && side === 'sell') {
        await executeMarketSell();
      } else if (orderType === 'limit' && side === 'buy') {
        await executeLimitBuy();
      } else if (orderType === 'limit' && side === 'sell') {
        await executeLimitSell();
      } else if (orderType === 'stop' || (stopPrice != null && stopPrice !== '')) {
        await executeStopLoss();
      } else {
        await submitOrder({ symbol, side, orderType, quantity, limit_price: limitPrice, stop_price: stopPrice, timeInForce });
      }
      setConfirmModalOpen(false);
      setConfirmPayload(null);
      refreshTradeData();
    } catch (e) {
      toast.error(e?.message || 'Order failed', { theme: 'dark' });
    }
  }, [confirmPayload, submitOrder, executeMarketBuy, executeMarketSell, executeLimitBuy, executeLimitSell, executeStopLoss, refreshTradeData]);

  const handleKillSwitch = useCallback(async () => {
    if (killSwitchStep === 1) { setKillSwitchStep(2); return; }
    setKillSwitchLoading(true);
    try {
      await emergencyStopApi();
      setKillSwitchModalOpen(false);
      setKillSwitchStep(1);
      refreshTradeData();
      toast.success('Kill switch executed — all orders cancelled, positions closed.', { theme: 'dark' });
    } catch (err) {
      toast.error(`Kill switch failed: ${err?.message || 'network error'}`, { theme: 'dark' });
    } finally {
      setKillSwitchLoading(false);
    }
  }, [killSwitchStep, refreshTradeData]);

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

  const chartRef = useRef(null);
  const chartInstanceRef = useRef(null);
  const [chartTimeframe, setChartTimeframe] = useState('1H');
  const [builderTab, setBuilderTab] = useState('Advanced');

  const timeframeParam = chartTimeframe === '1M' ? '1Min' : chartTimeframe === '5M' ? '5Min' : chartTimeframe === '15M' ? '15Min' : chartTimeframe === '1H' ? '1Hour' : '1Day';
  const { data: candleData, loading: candlesLoading } = useApi('quotes', {
    endpoint: `/quotes/${orderForm?.symbol || 'SPY'}/candles?timeframe=${timeframeParam}`,
    pollIntervalMs: 30000,
    enabled: !!orderForm?.symbol,
  });

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

  /* -- Keyboard Shortcuts -- */
  const handleKeyDown = useCallback((e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    if (!e.ctrlKey && !e.metaKey) return;
    if (e.key.toUpperCase() === 'B' || e.key.toUpperCase() === 'S') { e.preventDefault(); openConfirmModal(); }
  }, [openConfirmModal]);

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

  /* ── Price Ladder: real data only; empty state in UI ── */
  const displayLadder = ladderArr.length > 0 ? ladderArr : [];
  const maxBidSz = displayLadder.length ? Math.max(...displayLadder.map(r => r.side === 'bid' ? (r.bidSize || r.size || 0) : 0), 1) : 1;
  const maxAskSz = displayLadder.length ? Math.max(...displayLadder.map(r => r.side === 'ask' ? (r.askSize || r.size || 0) : 0), 1) : 1;

  /* ── Order Book: real data only (service may return array or { bids, asks }) ── */
  const bookBids = Array.isArray(orderBook)
    ? (orderBook.filter(r => r.side === 'bid').slice(0, 10))
    : (orderBook?.bids || []).slice(0, 10);
  const bookAsks = Array.isArray(orderBook)
    ? (orderBook.filter(r => r.side === 'ask').slice(0, 10))
    : (orderBook?.asks || []).slice(0, 10);
  const displayBookBids = bookBids;
  const displayBookAsks = bookAsks;
  const orderBookMid = (displayBookBids.length && displayBookAsks.length)
    ? (parseFloat(displayBookBids[0]?.price ?? displayBookBids[0]?.bid ?? 0) + parseFloat(displayBookAsks[0]?.price ?? displayBookAsks[0]?.ask ?? 0)) / 2
    : 0;

  /* ── News, Status, Positions: real data only (no mock) ── */
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

      {/* ═══════ HEADER BAR (Account info) ═══════ */}
      <div className="h-[42px] bg-[#111827] border-b border-[rgba(42,52,68,0.5)] flex items-center px-5 gap-5 shrink-0 relative">
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-400 to-transparent" />
        <span className="font-mono text-sm font-bold text-white uppercase tracking-widest">TRADE EXECUTION</span>
        <div className="flex items-center gap-5 ml-auto font-mono text-[10px]">
          <span><span className="text-gray-500 mr-1">Buying power:</span><span className="text-white">{fmtUsd(portfolio?.buyingPower ?? portfolio?.value)}</span></span>
          <span className="text-gray-700">|</span>
          <span><span className="text-gray-500 mr-1">Equity:</span><span className="text-white">{fmtUsd(portfolio?.value)}</span></span>
          <span className="text-gray-700">|</span>
          <span><span className="text-gray-500 mr-1">Daily P/L:</span><span className={(portfolio?.dailyPnl ?? 0) < 0 ? 'text-red-400' : 'text-emerald-400'}>{(portfolio?.dailyPnl ?? 0) < 0 ? '' : '+'}{fmtUsd(portfolio?.dailyPnl || 0)}</span></span>
          <span className="text-gray-700">|</span>
          <span><span className="text-gray-500 mr-1">Status:</span><span className="px-2 py-0.5 rounded text-[9px] font-bold bg-[#00D9FF]/25 text-[#00D9FF]">{portfolio?.status ?? '—'}</span></span>
          <span className="text-gray-700">|</span>
          <button type="button" onClick={() => setKillSwitchModalOpen(true)} className="flex items-center gap-1.5 px-3 py-1.5 rounded font-mono text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30 transition-colors" title="Emergency: close all positions and cancel all orders"><Power className="w-3.5 h-3.5" />KILL SWITCH</button>
        </div>
      </div>

      {killSwitchModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" role="dialog" aria-modal="true" onClick={() => setKillSwitchModalOpen(false)}>
          <div className="w-full max-w-md rounded-lg border border-red-500/40 bg-[#111827] p-6 shadow-xl" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-red-400 mb-2">Emergency Stop</h2>
            {killSwitchStep === 1 ? (
              <>
                <p className="text-sm text-gray-300 mb-4">This will cancel all open orders and close all positions. Are you sure?</p>
                <div className="flex gap-3 justify-end">
                  <button type="button" onClick={() => setKillSwitchModalOpen(false)} className="px-4 py-2 rounded-lg text-sm font-medium bg-[rgba(42,52,68,0.6)] text-gray-300 border border-[rgba(42,52,68,0.8)]">Cancel</button>
                  <button type="button" onClick={handleKillSwitch} className="px-4 py-2 rounded-lg text-sm font-bold bg-red-600 text-white border border-red-500 hover:bg-red-700">Continue</button>
                </div>
              </>
            ) : (
              <>
                <p className="text-sm text-red-300 mb-2 font-semibold">Second confirmation</p>
                <p className="text-sm text-gray-300 mb-4">All positions will be closed and all orders cancelled. Click &quot;Execute emergency stop&quot; to proceed.</p>
                <div className="flex gap-3 justify-end">
                  <button type="button" onClick={() => setKillSwitchStep(1)} disabled={killSwitchLoading} className="px-4 py-2 rounded-lg text-sm font-medium bg-[rgba(42,52,68,0.6)] text-gray-300 border">Back</button>
                  <button type="button" onClick={handleKillSwitch} disabled={killSwitchLoading} className="px-4 py-2 rounded-lg text-sm font-bold bg-red-600 text-white border border-red-500 disabled:opacity-50">{killSwitchLoading ? 'Executing…' : 'Execute emergency stop'}</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {confirmModalOpen && confirmPayload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" role="dialog" aria-modal="true" onClick={() => setConfirmModalOpen(false)}>
          <div className="w-full max-w-md rounded-lg border border-[rgba(42,52,68,0.8)] bg-[#111827] p-6 shadow-xl" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-white mb-2">Confirm order</h2>
            <div className="font-mono text-sm text-gray-300 space-y-1 mb-4">
              <p><span className="text-gray-500">Symbol:</span> {confirmPayload.symbol}</p>
              <p><span className="text-gray-500">Side:</span> {confirmPayload.side?.toUpperCase()}</p>
              <p><span className="text-gray-500">Type:</span> {confirmPayload.orderType}</p>
              <p><span className="text-gray-500">Quantity:</span> {confirmPayload.quantity}</p>
              {confirmPayload.limitPrice != null && confirmPayload.limitPrice !== '' && <p><span className="text-gray-500">Limit price:</span> {fmtUsd(Number(confirmPayload.limitPrice))}</p>}
              {confirmPayload.stopPrice != null && confirmPayload.stopPrice !== '' && <p><span className="text-gray-500">Stop price:</span> {fmtUsd(Number(confirmPayload.stopPrice))}</p>}
              <p><span className="text-gray-500">Time in force:</span> {confirmPayload.timeInForce?.toUpperCase() || 'DAY'}</p>
            </div>
            <div className="flex gap-3 justify-end">
              <button type="button" onClick={() => { setConfirmModalOpen(false); setConfirmPayload(null); }} disabled={loading} className="px-4 py-2 rounded-lg text-sm font-medium bg-[rgba(42,52,68,0.6)] text-gray-300 border">Cancel</button>
              <button type="button" onClick={doSubmitOrder} disabled={loading} className="px-4 py-2 rounded-lg text-sm font-bold bg-[#00D9FF] text-black disabled:opacity-50">{loading ? 'Placing…' : 'Place order'}</button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════ QUICK EXECUTION BAR ═══════ */}
      <div className="h-10 bg-[#111827]/80 border-b border-[rgba(42,52,68,0.5)] flex items-center px-4 gap-2 shrink-0">
        <span className="font-mono text-[9px] text-gray-500 uppercase tracking-[1px] mr-2">Quick</span>
        <button onClick={() => { updateOrderForm({ side: 'buy', orderType: 'market' }); openConfirmModal(); }} disabled={loading || !orderForm.symbol || orderForm.quantity < 1} className="px-3.5 py-[5px] rounded-[3px] font-mono text-[9px] font-semibold bg-[#00e676] text-black hover:brightness-[1.2] disabled:opacity-50">Market Buy</button>
        <button onClick={() => { updateOrderForm({ side: 'sell', orderType: 'market' }); openConfirmModal(); }} disabled={loading || !orderForm.symbol || orderForm.quantity < 1} className="px-3.5 py-[5px] rounded-[3px] font-mono text-[9px] font-semibold bg-[#ff3860] text-white hover:brightness-[1.2] disabled:opacity-50">Market Sell</button>
        <button onClick={() => { updateOrderForm({ side: 'buy', orderType: 'limit' }); openConfirmModal(); }} disabled={loading || !orderForm.symbol || orderForm.quantity < 1} className="px-3.5 py-[5px] rounded-[3px] font-mono text-[9px] font-semibold bg-[#00e676]/80 text-[#00e676] border border-[#00e676]/50 hover:bg-[#00e676]/30 disabled:opacity-50">Limit Buy</button>
        <button onClick={() => { updateOrderForm({ side: 'sell', orderType: 'limit' }); openConfirmModal(); }} disabled={loading || !orderForm.symbol || orderForm.quantity < 1} className="px-3.5 py-[5px] rounded-[3px] font-mono text-[9px] font-semibold bg-[#ff3860]/80 text-[#ff3860] border border-[#ff3860]/50 hover:bg-[#ff3860]/30 disabled:opacity-50">Limit Sell</button>
        <button onClick={() => { updateOrderForm({ orderType: 'bracket' }); openConfirmModal(); }} disabled={loading || !orderForm.symbol || orderForm.quantity < 1} className="px-3.5 py-[5px] rounded-[3px] font-mono text-[9px] font-semibold bg-[#00D9FF]/20 text-[#00D9FF] border border-[#00D9FF]/50 hover:bg-[#00D9FF]/30 disabled:opacity-50">Bracket</button>
        <button onClick={openConfirmModal} disabled={loading} className="px-3.5 py-[5px] rounded-[3px] font-mono text-[9px] font-semibold bg-[#00D9FF]/20 text-[#00D9FF] border border-[#00D9FF]/50 hover:bg-[#00D9FF]/30 disabled:opacity-50">Submit order</button>
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
              <div className="flex items-center justify-center h-full text-[10px] text-gray-500 font-mono">No ladder data</div>
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
                  onClick={() => {
                    setSelectedRow(row.row || i + 1);
                    const p = parseFloat(row.price);
                    if (!Number.isNaN(p)) updateOrderForm({ limitPrice: p });
                  }}
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

            {/* Execute button — opens confirmation modal */}
            <button
              onClick={openConfirmModal}
              disabled={loading || !orderForm.symbol || orderForm.quantity < 1}
              className="w-full py-3 mt-3.5 rounded font-mono text-[13px] font-bold text-black uppercase tracking-[1px] bg-gradient-to-br from-[#007a8a] to-[#00d4e8] hover:brightness-[1.15] hover:-translate-y-px transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_4px_20px_rgba(0,212,232,0.15)] hover:shadow-[0_6px_30px_rgba(0,212,232,0.3)] flex items-center justify-center gap-2"
            >{loading ? 'Placing…' : <>Place order (confirm) <span className="text-[9px] bg-black/25 px-[4px] py-px rounded-sm">E</span></>}</button>

            {recentOrders?.length > 0 && (
              <div className="mt-3 pt-2 border-t border-[rgba(42,52,68,0.5)]">
                <div className="font-mono text-[9px] text-gray-500 uppercase tracking-wider mb-1.5">Recent orders</div>
                <div className="space-y-1 max-h-24 overflow-y-auto">
                  {recentOrders.slice(0, 10).map((o, i) => (
                    <div key={o.id || i} className="flex justify-between gap-2 font-mono text-[9px]">
                      <span className="text-[#00D9FF] truncate">{o.symbol ?? o.symbol_id ?? '—'}</span>
                      <span className={clsx('shrink-0', (o.filled_qty ?? o.filled_quantity) > 0 ? 'text-[#00e676]' : 'text-gray-400')}>{o.status ?? '—'}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
        {/* VisualPriceLadder — narrow adjacent column (~1/4 width) */}
        <div className="bg-[#111827]/80 flex flex-col overflow-hidden" style={{ flex: '1 1 0%', minWidth: 180 }}>
          <VisualPriceLadder
            entry={Number(orderForm.limitPrice) || 0}
            stop={Number(orderForm.stopPrice) || 0}
            target={Number(orderForm.limitPrice) || 0}
            currentPrice={orderBookMid || 0}
            symbol={orderForm.symbol || ''}
          />
        </div>
        </div>{/* /col2-flex-row */}

        {/* ═══ COL 3 ROW 1: LIVE ORDER BOOK ═══ */}
        <div className="bg-[#111827]/80 flex flex-col overflow-hidden">
          <PanelHead>Live Order Book</PanelHead>
          <div className="flex-1 overflow-y-auto">
            {displayBookBids.length === 0 && displayBookAsks.length === 0 ? (
              <div className="flex items-center justify-center h-full min-h-[80px] text-[10px] text-gray-500 font-mono">No order book data</div>
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
              <div className="ml-auto flex gap-1 items-center">
                {['1M', '5M', '15M', '1H', '1D'].map(tf => (
                  <button
                    key={tf}
                    type="button"
                    onClick={() => setChartTimeframe(tf)}
                    disabled={candlesLoading && chartTimeframe === tf}
                    className={clsx(
                      'px-1.5 py-0.5 rounded-sm text-[7px] font-mono font-semibold transition-colors disabled:opacity-70',
                      chartTimeframe === tf ? 'bg-[#00D9FF]/20 text-[#00D9FF]' : 'text-gray-500 hover:text-[#c8d6e5]',
                    )}
                  >{candlesLoading && chartTimeframe === tf ? '…' : tf}</button>
                ))}
              </div>
            </div>
            <div className="flex-1 relative p-1.5 min-h-0">
              {candlesLoading && (
                <div className="absolute inset-0 flex items-center justify-center bg-[#0a0e1a]/80 z-10">
                  <div className="w-6 h-6 border-2 border-[#00D9FF] border-t-transparent rounded-full animate-spin" />
                </div>
              )}
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
                <div className="flex items-center justify-center h-full min-h-[60px] text-[10px] text-gray-500 font-mono">No news</div>
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
                {displayPositions.map((pos, i) => {
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
                          <button type="button" onClick={() => { const s = (pos.side || (pos.quantity > 0 ? 'long' : 'short')).toString().toLowerCase(); closePosition(pos.symbol, s); }} className="px-1.5 py-0.5 rounded text-[8px] font-medium bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] text-slate-300 hover:text-red-400 hover:border-red-500/30 transition-colors">Close</button>
                          <button type="button" onClick={() => { const s = (pos.side || (pos.quantity > 0 ? 'long' : 'short')).toString().toLowerCase(); adjustPosition(pos.symbol, s); }} className="px-1.5 py-0.5 rounded text-[8px] font-medium bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] text-slate-300 hover:text-[#00D9FF] transition-colors">Adjust</button>
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
              <div className="flex items-center justify-center h-full min-h-[60px] text-[10px] text-gray-500 font-mono">No status messages</div>
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
          onExecute={(verdict) => {
            if (!verdict?.symbol) return;
            const side = (verdict.direction === 'BUY' ? 'buy' : 'sell');
            const qty = Number(verdict.suggested_qty ?? verdict.quantity ?? orderForm.quantity) || 100;
            submitOrder({
              symbol: verdict.symbol,
              side,
              orderType: 'market',
              quantity: qty,
              timeInForce: 'day',
            });
          }}
          onOverride={() => { /* Override: keep current form, user can edit */ }}
          onDismiss={() => { /* Dismiss: no-op or clear council highlight */ }}
        />
      </div>
    </div>
  );
}
