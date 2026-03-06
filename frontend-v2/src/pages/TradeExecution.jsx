import React, { useEffect, useCallback } from 'react';
import useTradeExecution from '../hooks/useTradeExecution';
import AlignmentEngine from "../components/settings/AlignmentEngine";
import CouncilVerdictPanel from "../components/dashboard/CouncilVerdictPanel";
import { getApiUrl } from '../config/api';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import DataTable from '../components/ui/DataTable';
import PageHeader from '../components/ui/PageHeader';
import {
  Crosshair, TrendingUp, TrendingDown, ShieldAlert, BarChart3,
  Newspaper, Activity, Terminal, Zap, ChevronRight, X, SlidersHorizontal,
} from 'lucide-react';

export default function TradeExecution() {
  const {
    portfolio, priceLadder, orderBook, positions, newsFeed, systemStatus,
    selectedRow, setSelectedRow, orderForm, updateOrderForm, loading,
    executeMarketBuy, executeMarketSell, executeLimitBuy, executeLimitSell,
    executeStopLoss, executeAdvancedOrder, closePosition, adjustPosition,
  } = useTradeExecution();

  // Alignment Preflight State
  const [preflightVerdict, setPreflightVerdict] = React.useState(null);
  const runAlignmentPreflight = async () => {
    try {
      const res = await fetch(getApiUrl('alignment/evaluate'), { method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: orderForm?.symbol || 'SPY', side: orderForm?.side || 'buy', quantity: orderForm?.quantity || 1, strategy: 'manual' })
      });
      if (!res.ok) throw new Error('Alignment preflight failed');
      const data = await res.json();
      setPreflightVerdict(data);
    } catch (err) {
      setPreflightVerdict({ allowed: false, blockedBy: 'NETWORK_ERROR', summary: err.message });
    }
  };

  // Keyboard Shortcuts
  const handleKeyDown = useCallback((e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    if (!e.ctrlKey && !e.metaKey) return;
    switch (e.key.toUpperCase()) {
      case 'B': e.preventDefault(); executeMarketBuy(); break;
      case 'S': e.preventDefault(); executeMarketSell(); break;
      case 'L': e.preventDefault(); executeLimitBuy(); break;
      case 'O': e.preventDefault(); executeLimitSell(); break;
      case 'T': e.preventDefault(); executeStopLoss(); break;
      case 'E': e.preventDefault(); executeAdvancedOrder(); break;
      default: break;
    }
  }, [executeMarketBuy, executeMarketSell, executeLimitBuy, executeLimitSell, executeStopLoss, executeAdvancedOrder]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const fmt = (v) => v?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00';
  const fmtUsd = (v) => `$${fmt(v)}`;
  const ladderArr = Array.isArray(priceLadder) ? priceLadder : (priceLadder?.levels || []);
  const bookArr = Array.isArray(orderBook) ? orderBook : (orderBook?.bids ? [...(orderBook.asks || []), ...(orderBook.bids || [])] : []);
  const posArr = Array.isArray(positions) ? positions : (positions?.positions || []);
  const newsArr = Array.isArray(newsFeed) ? newsFeed : [];
  const statusArr = Array.isArray(systemStatus) ? systemStatus : [systemStatus].filter(Boolean);
  const maxLadderSize = Math.max(...ladderArr.map(r => r.size || 0), 1);
  const maxBookSize = Math.max(...bookArr.map(r => r.size || 0), 1);

  return (
    <div className="min-h-screen bg-dark p-4 font-sans space-y-3">

      {/* ===== HEADER BAR ===== */}
      <div className="flex items-center justify-between bg-surface border border-secondary/20 rounded-xl px-5 py-3">
        <PageHeader
          icon={Crosshair}
          title="TRADE EXECUTION"
        />
        <div className="flex items-center gap-6 text-xs font-mono">
          <span className="text-gray-500">Portfolio: <span className="text-white font-bold">{fmtUsd(portfolio.value)}</span></span>
          <span className="text-gray-500">Daily P/L: <span className={portfolio.dailyPnl >= 0 ? 'text-emerald-500 font-bold' : 'text-red-500 font-bold'}>{portfolio.dailyPnl >= 0 ? '+' : ''}{fmtUsd(portfolio.dailyPnl)}</span></span>
          <span className="text-gray-500">Status: <Badge variant={portfolio.status === 'ELITE' ? 'success' : 'secondary'} size="sm">{portfolio.status}</Badge></span>
          <span className="text-gray-500">Latency: <span className="text-cyan-400 font-bold">{portfolio.latency}ms</span></span>
        </div>
      </div>

      {/* ===== QUICK EXECUTION BAR ===== */}
      <Card noPadding>
        <div className="px-4 py-3 flex items-center gap-3 flex-wrap">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider mr-1">Quick Execution</span>
          <Button variant="success" size="sm" onClick={executeMarketBuy} disabled={loading}>
            Market Buy [B]
          </Button>
          <Button variant="danger" size="sm" onClick={executeMarketSell} disabled={loading}>
            Market Sell [S]
          </Button>
          <Button variant="outline" size="sm" onClick={executeLimitBuy} disabled={loading} className="!border-blue-500/50 !text-blue-400 hover:!bg-blue-500/10">
            Limit Buy [L]
          </Button>
          <Button variant="outline" size="sm" onClick={executeLimitSell} disabled={loading} className="!border-blue-500/50 !text-blue-400 hover:!bg-blue-500/10">
            Limit Sell [O]
          </Button>
          <Button variant="outline" size="sm" onClick={executeStopLoss} disabled={loading} className="!border-red-500/50 !text-red-400 hover:!bg-red-500/10">
            Stop Loss [T]
          </Button>
        </div>
      </Card>

      {/* ===== MAIN 3-COLUMN GRID ===== */}
      <div className="grid grid-cols-12 gap-3">

        {/* --- COL 1: Multi-Price Ladder (left narrow) --- */}
        <div className="col-span-3">
          <Card title="Multi-Price Ladder" noPadding>
            <div className="overflow-y-auto max-h-[480px]">
              <table className="w-full text-xs font-mono">
                <thead className="sticky top-0 bg-surface z-10">
                  <tr className="border-b border-secondary/20">
                    <th className="px-2 py-2 text-left text-[10px] text-gray-500 font-medium">Row</th>
                    <th className="px-2 py-2 text-left text-[10px] text-gray-500 font-medium">Price</th>
                    <th className="px-2 py-2 text-right text-[10px] text-gray-500 font-medium">Size</th>
                  </tr>
                </thead>
                <tbody>
                  {ladderArr.map((row, i) => {
                    const isSelected = i + 1 === selectedRow;
                    const barColor = row.size > 15 ? 'bg-emerald-500' : row.size > 5 ? 'bg-amber-500' : 'bg-red-500';
                    const textColor = row.size > 15 ? 'text-emerald-400' : row.size > 5 ? 'text-amber-400' : 'text-red-400';
                    const pct = Math.min((row.size / maxLadderSize) * 100, 100);
                    return (
                      <tr
                        key={i}
                        onClick={() => setSelectedRow(i + 1)}
                        className={`cursor-pointer transition-colors relative ${
                          isSelected
                            ? 'bg-cyan-500/15 border-l-2 border-l-cyan-400'
                            : 'border-l-2 border-l-transparent hover:bg-cyan-500/5'
                        }`}
                      >
                        <td className="px-2 py-1 text-[10px] text-gray-600">{row.row}</td>
                        <td className={`px-2 py-1 ${isSelected ? 'text-cyan-400 font-bold' : 'text-white/80'}`}>
                          {(parseFloat(row.price) || 0).toFixed(2)}
                        </td>
                        <td className="px-2 py-1 text-right relative">
                          <div className={`absolute top-0 bottom-0 right-0 ${barColor} opacity-15`} style={{ width: `${pct}%` }} />
                          <span className={`relative z-10 ${textColor}`}>{row.size}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* --- COL 2: Advanced Order Builder + Live Order Book (middle) --- */}
        <div className="col-span-5 space-y-3">

          {/* Advanced Order Builder */}
          <Card title="Advanced Order Builder" noPadding>
            <div className="p-4 space-y-3">
              {/* Symbol + Strategy */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] text-gray-500 uppercase tracking-wider mb-1">Symbol</label>
                  <select
                    value={orderForm.symbol}
                    onChange={e => updateOrderForm({ symbol: e.target.value })}
                    className="w-full bg-dark border border-secondary/30 rounded-lg px-3 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
                  >
                    {['SPX', 'SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA', 'AMD', 'AMZN', 'MSFT', 'META'].map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-gray-500 uppercase tracking-wider mb-1">Strategy</label>
                  <select
                    value={orderForm.strategy}
                    onChange={e => updateOrderForm({ strategy: e.target.value })}
                    className="w-full bg-dark border border-secondary/30 rounded-lg px-3 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
                  >
                    {['Iron Condor', 'Bull Call Spread', 'Bear Put Spread', 'Straddle', 'Strangle', 'Butterfly', 'Calendar Spread', 'Single Option'].map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>

              {/* Call strike section */}
              <div className="bg-dark/50 border border-secondary/20 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="w-3 h-3 text-emerald-500" />
                  <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">Call</span>
                </div>
                <div className="flex gap-1.5 flex-wrap">
                  {[4460, 4470, 4460, 4450, 4460].map((v, i) => (
                    <span
                      key={i}
                      className={`px-2 py-1 rounded text-xs font-mono cursor-pointer border transition-colors ${
                        i >= 1 && i <= 2
                          ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                          : 'bg-transparent text-gray-500 border-secondary/30 hover:border-secondary/50'
                      }`}
                    >{v}</span>
                  ))}
                </div>
              </div>

              {/* Put strike section */}
              <div className="bg-dark/50 border border-secondary/20 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingDown className="w-3 h-3 text-red-500" />
                  <span className="text-[10px] font-semibold text-red-400 uppercase tracking-wider">Put</span>
                </div>
                <div className="flex gap-1.5 flex-wrap">
                  {[4440, 4430, 4430, 4430, 4380].map((v, i) => (
                    <span
                      key={i}
                      className={`px-2 py-1 rounded text-xs font-mono cursor-pointer border transition-colors ${
                        i >= 2
                          ? 'bg-blue-500/15 text-blue-400 border-blue-500/30'
                          : 'bg-transparent text-gray-500 border-secondary/30 hover:border-secondary/50'
                      }`}
                    >{v}</span>
                  ))}
                </div>
              </div>

              {/* Quantity + Limit */}
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-[10px] text-gray-500 uppercase tracking-wider mb-1">Quantity</label>
                  <input
                    type="number"
                    value={orderForm.quantity}
                    onChange={e => updateOrderForm({ quantity: parseInt(e.target.value) || 0 })}
                    className="w-full bg-dark border border-secondary/30 rounded-lg px-3 py-2 text-sm text-white font-mono focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-gray-500 uppercase tracking-wider mb-1">&nbsp;</label>
                  <select
                    value={orderForm.quantityType}
                    onChange={e => updateOrderForm({ quantityType: e.target.value })}
                    className="w-full bg-dark border border-secondary/30 rounded-lg px-3 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
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
                    className="w-full bg-dark border border-secondary/30 rounded-lg px-3 py-2 text-sm text-white font-mono focus:border-cyan-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Execute Button */}
              <button
                onClick={executeAdvancedOrder}
                disabled={loading}
                className="w-full py-2.5 rounded-lg font-bold text-sm font-mono tracking-wide text-white bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 disabled:cursor-wait transition-all hover:shadow-[0_0_20px_rgba(6,182,212,0.3)]"
              >
                {loading ? 'Executing...' : 'Execute Order [Ctrl+E]'}
              </button>
            </div>
          </Card>

          {/* Live Order Book */}
          <Card title="Live Order Book" noPadding>
            <div className="overflow-y-auto max-h-[280px]">
              <table className="w-full text-xs font-mono">
                <thead className="sticky top-0 bg-surface z-10">
                  <tr className="border-b border-secondary/20">
                    <th className="px-3 py-2 text-right text-[10px] text-gray-500 font-medium">Bid</th>
                    <th className="px-3 py-2 text-right text-[10px] text-gray-500 font-medium">Size</th>
                    <th className="px-3 py-2 text-right text-[10px] text-gray-500 font-medium">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {bookArr.map((row, i) => {
                    const isGreen = row.bid >= 4450;
                    const pct = Math.min((row.size / maxBookSize) * 100, 100);
                    return (
                      <tr key={i} className="relative hover:bg-cyan-500/5 cursor-pointer transition-colors">
                        <td className="px-3 py-1 text-right relative">
                          <div
                            className={`absolute top-0 bottom-0 left-0 ${isGreen ? 'bg-emerald-500' : 'bg-red-500'} opacity-10`}
                            style={{ width: `${pct}%` }}
                          />
                          <span className={`relative z-10 ${isGreen ? 'text-emerald-400' : 'text-red-400'}`}>{row.bid}</span>
                        </td>
                        <td className="px-3 py-1 text-right text-white/80">{row.size}</td>
                        <td className="px-3 py-1 text-right text-gray-500">{row.total}</td>
                      </tr>
                    );
                  })}
                  {bookArr.length === 0 && (
                    <tr><td colSpan={3} className="px-4 py-8 text-center text-gray-600">No order book data</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* --- COL 3: Price Charts + News Feed (right) --- */}
        <div className="col-span-4 space-y-3">

          {/* Price Charts */}
          <Card
            title="Price Charts"
            subtitle="SPX - S&P 500 Index - 1M"
            noPadding
          >
            <div className="p-4">
              <div className="text-lg font-bold text-white font-mono">
                -- <span className="text-xs text-gray-500 font-normal ml-2">Awaiting data</span>
              </div>
              <div className="mt-3 h-40 rounded-lg bg-dark/50 border border-secondary/10 flex items-center justify-center">
                <div className="text-center">
                  <BarChart3 className="w-8 h-8 text-gray-700 mx-auto mb-2" />
                  <span className="text-xs text-gray-600">Awaiting market data...</span>
                </div>
              </div>
              <div className="flex justify-end mt-2">
                <span className="text-[10px] text-gray-600 bg-dark/80 px-2 py-0.5 rounded cursor-pointer hover:text-cyan-400 transition-colors border border-secondary/20">TV</span>
              </div>
            </div>
          </Card>

          {/* News Feed */}
          <Card title="News Feed" action={<Newspaper className="w-3.5 h-3.5 text-gray-600" />} noPadding>
            <div className="max-h-[200px] overflow-y-auto divide-y divide-secondary/10">
              {newsArr.map((item, i) => {
                const typeColor = item.type === 'warning' || item.type === 'negative'
                  ? 'text-red-400'
                  : item.type === 'positive'
                    ? 'text-emerald-400'
                    : 'text-cyan-400';
                return (
                  <div key={i} className="px-4 py-2 hover:bg-cyan-500/5 transition-colors">
                    <div className="flex items-start gap-2">
                      <span className={`text-[10px] font-mono font-semibold whitespace-nowrap ${typeColor}`}>{item.time}</span>
                      <span className="text-[11px] text-gray-400 leading-snug">{item.text}</span>
                    </div>
                  </div>
                );
              })}
              {newsArr.length === 0 && (
                <div className="px-4 py-6 text-center text-xs text-gray-600">No news available</div>
              )}
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
                {posArr.map((pos, i) => {
                  const pnl = parseFloat(pos.pnl ?? pos.unrealized_pl ?? 0);
                  const isPositive = pnl >= 0;
                  return (
                    <tr key={i} className="hover:bg-cyan-500/5 transition-colors">
                      <td className="px-3 py-2.5 text-cyan-400 font-semibold">{pos.symbol}</td>
                      <td className="px-3 py-2.5">
                        <Badge variant={(pos.side || '').toLowerCase().includes('long') ? 'success' : 'danger'} size="sm">
                          {pos.side}
                        </Badge>
                      </td>
                      <td className="px-3 py-2.5 text-white/80">{parseFloat(pos.quantity ?? pos.qty ?? 0)}</td>
                      <td className="px-3 py-2.5 text-white/80">{parseFloat(pos.avgPrice ?? pos.avg_entry_price ?? 0).toFixed(2)}</td>
                      <td className="px-3 py-2.5 text-white/80">{parseFloat(pos.currentPrice ?? pos.current_price ?? 0).toFixed(2)}</td>
                      <td className={`px-3 py-2.5 font-semibold ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                        {isPositive ? '+' : ''}{fmtUsd(pnl)}
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex gap-1.5">
                          <button
                            onClick={() => closePosition(pos.symbol, pos.side)}
                            className="px-2.5 py-1 rounded text-[10px] font-semibold bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-colors"
                          >
                            <X className="w-3 h-3 inline mr-0.5" />Close
                          </button>
                          <button
                            onClick={() => adjustPosition(pos.symbol, pos.side)}
                            className="px-2.5 py-1 rounded text-[10px] font-semibold border border-secondary/30 text-gray-400 hover:bg-secondary/10 transition-colors"
                          >
                            <SlidersHorizontal className="w-3 h-3 inline mr-0.5" />Adj
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {posArr.length === 0 && (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-600 text-xs">No open positions</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* System Status Log */}
        <Card title="System Status Log" action={<Terminal className="w-3.5 h-3.5 text-gray-600" />} noPadding>
          <div className="max-h-[220px] overflow-y-auto divide-y divide-secondary/10">
            {statusArr.map((item, i) => {
              const dotColor = item.type === 'success' || item.type === 'info'
                ? 'bg-emerald-500'
                : item.type === 'warning'
                  ? 'bg-amber-500'
                  : item.type === 'error'
                    ? 'bg-red-500'
                    : 'bg-cyan-500';
              const timeColor = item.type === 'warning'
                ? 'text-amber-400'
                : item.type === 'error'
                  ? 'text-red-400'
                  : 'text-cyan-400';
              return (
                <div key={i} className="px-4 py-2 flex items-start gap-2.5 hover:bg-cyan-500/5 transition-colors">
                  <span className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${dotColor}`} />
                  <div className="text-xs leading-relaxed">
                    <span className={`font-mono font-semibold mr-2 ${timeColor}`}>{item.time}</span>
                    <span className="text-gray-400">{item.text}</span>
                  </div>
                </div>
              );
            })}
            {statusArr.length === 0 && (
              <div className="px-4 py-6 text-center text-xs text-gray-600">No status logs</div>
            )}
          </div>
        </Card>
      </div>

      {/* ===== ALIGNMENT ROW: Council Verdict + Alignment Engine ===== */}
      <div className="grid grid-cols-2 gap-3">
        <CouncilVerdictPanel symbol={orderForm?.symbol || 'SPY'} />
        <Card title="Alignment Engine">
          <div className="max-h-[400px] overflow-y-auto">
            <AlignmentEngine />
          </div>
        </Card>
      </div>

    </div>
  );
}
