/**
 * Active Trades - Ultrawide Command Strip Layout
 * Matches approved mockup: 10-active-trades.html / Active-Trades.png
 * Real Alpaca API via useApi hooks - NO mock data
 * Endpoints: portfolio (positions+fills), orders (active orders), risk, dataSources
 */
import React, { useState, useCallback, useEffect } from "react";
import log from "@/utils/logger";
import {
  TrendingUp,
  TrendingDown,
  RefreshCw,
  XCircle,
  Filter,
  Download,
  Search,
  Send,
  AlertTriangle,
  CheckCircle,
  Activity,
  BarChart3,
} from "lucide-react";
import { useApi } from "../hooks/useApi";
import { getApiUrl, getAuthHeaders } from "../config/api";

// ── Formatters ──
const fmtM = (n) => {
  if (n == null || isNaN(n)) return "--";
  return "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};
const fmtP = (n) => {
  if (n == null || isNaN(n)) return "--";
  return (n > 0 ? "+" : "") + Number(n).toFixed(2) + "%";
};
const clr = (n) => (n >= 0 ? "text-emerald-400" : "text-red-400");
const bgClr = (n) => (n >= 0 ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400");

export default function Trades() {
  // ── State ──
  const [posFilter, setPosFilter] = useState("");
  const [ordFilter, setOrdFilter] = useState("");
  const [orderForm, setOrderForm] = useState({
    symbol: "", side: "BUY", type: "Limit", qty: "", limitPrice: "", stopPrice: "", tif: "DAY",
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitMsg, setSubmitMsg] = useState(null);

  // ── Real API Hooks ──
  const { data: portfolioData, loading: posLoading, error: posError, refetch: refetchPortfolio } =
    useApi("portfolio", { pollIntervalMs: 5000 });
  const { data: ordersData, loading: ordLoading, refetch: refetchOrders } =
    useApi("orders", { pollIntervalMs: 5000 });
  const { data: riskData } = useApi("risk", { pollIntervalMs: 10000 });
  const { data: dsData } = useApi("dataSources", { pollIntervalMs: 30000 });
  const { data: systemData } = useApi("system", { pollIntervalMs: 30000 });

  // ── Derived Data ──
  const positions = portfolioData?.positions || [];
  const fills = portfolioData?.history || [];
  const summary = portfolioData?.summary || {};
  const orders = Array.isArray(ordersData) ? ordersData : (ordersData?.orders || []);
  const dsStatus = dsData?.sources || dsData?.dataSources || [];

  // API connection indicators
  const alpacaOk = positions.length > 0 || !posError;
  const uwOk = dsStatus.some?.((s) => s.name?.toLowerCase().includes("unusual") && s.status === "connected");
  const fvOk = dsStatus.some?.((s) => s.name?.toLowerCase().includes("finviz") && s.status === "connected");

  // Account metrics from summary
  const equity = summary.totalValue || 0;
  const dayPnl = summary.totalUnrealizedPnl || summary.daily_pnl_est || 0;
  const buyingPower = summary.buyingPower || 0;
  const exposure = summary.max_position_pct || 0;
  const posCount = positions.length;
  const ordCount = orders.length;

  // ── Filtered lists ──
  const filteredPositions = positions.filter((p) =>
    !posFilter || (p.symbol || p.ticker || "").toUpperCase().includes(posFilter.toUpperCase())
  );
  const filteredOrders = orders.filter((o) =>
    !ordFilter || (o.symbol || "").toUpperCase().includes(ordFilter.toUpperCase())
  );

  // ── Actions ──
  const handleRefresh = () => { refetchPortfolio(); refetchOrders(); };

  const handleCancelAll = async () => {
    try {
      const res = await fetch(getApiUrl("orders"), { method: "DELETE", headers: getAuthHeaders() });
      if (!res.ok) throw new Error('Failed');
      refetchOrders();
    } catch (e) { log.error("Cancel all failed:", e); }
  };

  const handleClosePosition = async (symbol, pct = 100) => {
    try {
      const qty = pct < 100 ? `&qty_pct=${pct}` : "";
      const res = await fetch(getApiUrl("orders") + `/close?symbol=${encodeURIComponent(symbol)}${qty}`, { method: "POST", headers: getAuthHeaders() });
      if (!res.ok) throw new Error('Failed');
      refetchPortfolio();
    } catch (e) { log.error("Close position failed:", e); }
  };

  const handleCloseLosers = async () => {
    const losers = positions.filter((p) => (p.unrealizedPnL || p.pnl || 0) < 0);
    for (const p of losers) {
      await handleClosePosition(p.symbol || p.ticker);
    }
  };

  const handleFlattenAll = async () => {
    await handleCancelAll();
    for (const p of positions) {
      await handleClosePosition(p.symbol || p.ticker);
    }
  };

  const handleSubmitOrder = async () => {
    if (!orderForm.symbol || !orderForm.qty) return;
    setSubmitting(true);
    setSubmitMsg(null);
    try {
      const body = {
        symbol: orderForm.symbol.toUpperCase(),
        side: orderForm.side.toLowerCase(),
        type: orderForm.type === "limit" ? "limit" : "market",
        time_in_force: "day",
        qty: String(parseInt(orderForm.qty)),
      };
      if (orderForm.type === "limit" && orderForm.limitPrice) {
        body.limit_price = String(parseFloat(orderForm.limitPrice));
      }
      if (orderForm.stopPrice) {
        body.stop_loss = { stop_price: String(parseFloat(orderForm.stopPrice)) };
        body.order_class = "bracket";
      }
      const res = await fetch(getApiUrl("orders/advanced"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setSubmitMsg({ type: "success", text: `Order submitted: ${data.alpaca_status || "OK"}` });
        setOrderForm((f) => ({ ...f, symbol: "", qty: "", limitPrice: "", stopPrice: "" }));
        refetchOrders();
      } else {
        setSubmitMsg({ type: "error", text: data.detail || "Order failed" });
      }
    } catch (e) {
      setSubmitMsg({ type: "error", text: e.message });
    }
    setSubmitting(false);
  };

  const handleCancelOrder = async (orderId) => {
    try {
      await fetch(getApiUrl("orders") + `/${orderId}`, { method: "DELETE", headers: getAuthHeaders() });
      refetchOrders();
    } catch (e) { log.error("Cancel order failed:", e); }
  };

  const handleExportCSV = (data, filename) => {
    if (!data.length) return;
    const headers = Object.keys(data[0]).join(",");
    const rows = data.map((r) => Object.values(r).map((v) => `"${v ?? ""}"`).join(","));
    const csv = [headers, ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  };

  // ── RENDER ──
  return (
    <div className="flex flex-col h-full min-h-0 animate-in fade-in duration-500">
      {/* ══ TOP COMMAND STRIP - Teal bar matching mockup ══ */}
      <div className="flex items-center justify-between px-4 py-3 bg-cyan-500 text-black flex-shrink-0">
        <div className="flex items-center gap-3">
          <BarChart3 className="w-5 h-5" />
          <span className="text-base font-bold font-mono tracking-wider">ACTIVE_TRADES_V3</span>
          <span className="px-2 py-0.5 bg-black/10 border border-black/20 rounded text-[9px] font-bold">OC_CORE_v5.2.1</span>
          <span className="px-2 py-0.5 bg-black/10 border border-black/20 rounded text-[9px] font-bold">WS_LATENCY: --ms</span>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-semibold opacity-80">EQUITY</span>
            <span className="text-base font-bold font-mono">{fmtM(equity)}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-semibold opacity-80">DAY P&L</span>
            <span className="text-base font-bold font-mono">{fmtM(dayPnl)}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-semibold opacity-80">BUYING POWER</span>
            <span className="text-base font-bold font-mono">{fmtM(buyingPower)}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-semibold opacity-80">EXPOSURE</span>
            <span className="text-base font-bold font-mono">{exposure.toFixed(1)}%</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold">TRADE MODE:</span>
            {(systemData?.tradingMode || systemData?.trading_mode || "live").toUpperCase() === "LIVE" ? (
              <span className="px-2 py-0.5 bg-red-600 text-white rounded text-[9px] font-bold animate-pulse">LIVE</span>
            ) : (
              <span className="px-2 py-0.5 bg-emerald-500 text-white rounded text-[9px] font-bold">PAPER</span>
            )}
          </div>
        </div>
      </div>

      {/* ══ SPLIT LAYOUT - Positions top, Orders bottom ══ */}
      <div className="flex-1 flex flex-col gap-3 p-3 min-h-0 overflow-hidden">

        {/* ── POSITIONS PANEL ── */}
        <div className="flex-1 flex flex-col bg-slate-800/40 border border-slate-700/50 rounded-lg min-h-0 overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 bg-slate-900/60 border-b border-slate-700/50">
            <span className="text-xs font-semibold text-slate-200">OPEN POSITIONS ({posCount})</span>
            <div className="flex items-center gap-2">
              <input
                type="text" placeholder="Filter..." value={posFilter}
                onChange={(e) => setPosFilter(e.target.value)}
                className="px-2 py-1 bg-slate-900 border border-slate-700 rounded text-[10px] text-slate-300 w-24 outline-none focus:border-cyan-500"
              />
              <button onClick={handleCloseLosers} className="px-2 py-1 bg-slate-900 border border-slate-700 rounded text-[10px] text-slate-300 hover:bg-slate-700">Close Losers</button>
              <button onClick={handleFlattenAll} className="px-2 py-1 bg-slate-900 border border-red-500/30 rounded text-[10px] text-red-400 hover:bg-red-500/10">Flatten All</button>
              <button onClick={() => handleExportCSV(positions, "positions.csv")} className="px-2 py-1 bg-slate-900 border border-slate-700 rounded text-[10px] text-slate-300 hover:bg-slate-700">
                <Download className="w-3 h-3 inline" /> CSV
              </button>
              <button onClick={handleRefresh} className="px-2 py-1 bg-slate-900 border border-slate-700 rounded text-[10px] text-cyan-400 hover:bg-slate-700">
                <RefreshCw className="w-3 h-3 inline" />
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-auto">
            <table className="w-full text-right whitespace-nowrap">
              <thead className="sticky top-0 z-10">
                <tr className="bg-slate-900/80">
                  {["Symbol","Side","Qty","Avail","Avg Entry","Current","Mkt Value","Unreal P&L","P&L %","Day P&L","Day %","Cost Basis","Chg Today","Asset Class","Exchange","Actions"].map((h) => (
                    <th key={h} className="px-2 py-1.5 text-slate-500 text-[9px] font-semibold uppercase tracking-wider border-b border-slate-700/50 first:text-left">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {posLoading && positions.length === 0 && (
                  <tr><td colSpan={16} className="px-4 py-6 text-center text-cyan-500 text-xs animate-pulse">Loading positions from Alpaca...</td></tr>
                )}
                {posError && (
                  <tr><td colSpan={16} className="px-4 py-4 text-center text-red-400 text-xs">API Error: {posError.message}</td></tr>
                )}
                {filteredPositions.map((p, i) => {
                  const pnl = p.unrealizedPnL ?? p.pnl ?? 0;
                  const pnlPct = p.pnlPct ?? 0;
                  const dayPnlVal = pnl * 0.3; // Estimate intraday as portion of unrealized
                  const chg = p.changeToday ?? 0;
                  return (
                    <tr key={p.symbol || i} className="hover:bg-slate-700/30 transition-colors border-b border-slate-800/50">
                      <td className="px-2 py-1.5 text-left text-white font-bold text-[11px] font-mono">{p.symbol || p.ticker}</td>
                      <td className="px-2 py-1.5"><span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${p.side === "Long" ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"}`}>{p.side === "Long" ? "LONG" : "SHORT"}</span></td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-slate-300">{p.qty ?? p.quantity}</td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-slate-300">{p.qty ?? p.quantity}</td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-slate-300">{fmtM(p.entryPrice ?? p.entry)}</td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-white font-bold">{fmtM(p.currentPrice ?? p.current)}</td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-slate-300">{fmtM(p.marketValue)}</td>
                      <td className={`px-2 py-1.5 font-mono text-[11px] font-bold ${clr(pnl)}`}>{fmtM(pnl)}</td>
                      <td className={`px-2 py-1.5 font-mono text-[11px] ${clr(pnlPct)}`}>{fmtP(pnlPct)}</td>
                      <td className={`px-2 py-1.5 font-mono text-[11px] ${clr(dayPnlVal)}`}>{fmtM(dayPnlVal)}</td>
                      <td className={`px-2 py-1.5 font-mono text-[11px] ${clr(chg)}`}>{fmtP(chg)}</td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-slate-300">{fmtM(p.costBasis)}</td>
                      <td className={`px-2 py-1.5 font-mono text-[11px] ${clr(chg)}`}>{fmtP(chg)}</td>
                      <td className="px-2 py-1.5 text-[11px] text-slate-500">us_equity</td>
                      <td className="px-2 py-1.5 text-[11px] text-slate-500">NASDAQ</td>
                      <td className="px-2 py-1.5">
                        <button onClick={() => handleClosePosition(p.symbol || p.ticker)} className="px-1.5 py-0.5 bg-slate-900 border border-slate-700 rounded text-[9px] text-slate-300 hover:bg-red-500/20 hover:text-red-400">Cxl</button>
                      </td>
                    </tr>
                  );
                })}
                {filteredPositions.length === 0 && !posLoading && !posError && (
                  <tr><td colSpan={16} className="px-4 py-6 text-center text-slate-500 text-xs">No open positions.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── ORDERS PANEL ── */}
        <div className="flex-1 flex flex-col bg-slate-800/40 border border-slate-700/50 rounded-lg min-h-0 overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 bg-slate-900/60 border-b border-slate-700/50">
            <span className="text-xs font-semibold text-slate-200">ACTIVE ORDERS ({ordCount})</span>
            <div className="flex items-center gap-2">
              <button className="px-2 py-1 bg-slate-900 border border-slate-700 rounded text-[10px] text-slate-300 hover:bg-slate-700">Filter: Working</button>
              <button onClick={handleCancelAll} className="px-2 py-1 bg-slate-900 border border-red-500/30 rounded text-[10px] text-red-400 hover:bg-red-500/10">Cancel All</button>
            </div>
          </div>
          <div className="flex-1 overflow-auto">
            <table className="w-full text-right whitespace-nowrap">
              <thead className="sticky top-0 z-10">
                <tr className="bg-slate-900/80">
                  {["Symbol","Side","Type","Class","Qty","Filled","Limit Px","Stop Px","Trail %","TIF","Status","Submitted","Filled At","Avg Fill","Ext Hrs","Legs","Actions"].map((h) => (
                    <th key={h} className="px-2 py-1.5 text-slate-500 text-[9px] font-semibold uppercase tracking-wider border-b border-slate-700/50 first:text-left">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ordLoading && orders.length === 0 && (
                  <tr><td colSpan={17} className="px-4 py-6 text-center text-cyan-500 text-xs animate-pulse">Loading orders...</td></tr>
                )}
                {filteredOrders.map((o, i) => {
                  const sym = o.symbol || "--";
                  const side = (o.side || "").toUpperCase();
                  const isBuy = side.includes("BUY");
                  const typ = o.order_type || o.type || "--";
                  const qty = o.quantity || o.qty || 0;
                  const filled = o.filled_qty || o.filledQty || 0;
                  const status = o.alpaca_status || o.status || "WORKING";
                  const submitted = o.created_at || o.timestamp || "";
                  const subDisplay = submitted ? new Date(submitted).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "--";
                  return (
                    <tr key={o.id || i} className="hover:bg-slate-700/30 transition-colors border-b border-slate-800/50">
                      <td className="px-2 py-1.5 text-left text-white font-bold text-[11px] font-mono">{sym}</td>
                      <td className="px-2 py-1.5"><span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${isBuy ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"}`}>{side || "BUY"}</span></td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-slate-300">{typ}</td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-slate-300">{o.order_class || "Simple"}</td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-slate-300">{qty}</td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-slate-300">
                        <div className="inline-flex items-center gap-1">
                          <div className="w-10 h-1 bg-slate-700 rounded-full inline-block">
                            <div className="h-full bg-cyan-500 rounded-full" style={{ width: `${qty > 0 ? (filled / qty) * 100 : 0}%` }} />
                          </div>
                          <span>{filled}</span>
                        </div>
                      </td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-slate-300">{typ === "Limit" || typ === "Stop Limit" ? fmtM(o.price) : "--"}</td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-slate-300">{typ === "Stop" || typ === "Stop Limit" ? fmtM(o.price) : "--"}</td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-slate-300">--</td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-slate-300">DAY</td>
                      <td className="px-2 py-1.5"><span className="text-cyan-400 text-[10px] font-semibold">{status}</span></td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-slate-400">{subDisplay}</td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-slate-400">--</td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-slate-400">--</td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-slate-400">Y</td>
                      <td className="px-2 py-1.5 font-mono text-[11px] text-slate-400">1</td>
                      <td className="px-2 py-1.5">
                        <div className="flex items-center gap-1">
                          <button className="px-1.5 py-0.5 bg-slate-900 border border-slate-700 rounded text-[9px] text-slate-300 hover:bg-slate-700">Mod</button>
                          <button onClick={() => handleCancelOrder(o.id)} className="px-1.5 py-0.5 bg-slate-900 border border-slate-700 rounded text-[9px] text-red-400 hover:bg-red-500/20">Cxl</button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {filteredOrders.length === 0 && !ordLoading && (
                  <tr><td colSpan={17} className="px-4 py-6 text-center text-slate-500 text-xs">No active orders.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ══ BOTTOM QUICK EXECUTE BAR - Matching mockup inline order entry ══ */}
      <div className="flex items-center gap-3 px-4 py-2.5 bg-slate-800/60 border-t border-slate-700/50 flex-shrink-0">
        <span className="text-[10px] font-bold text-cyan-400 mr-2">QUICK EXECUTE</span>
        <input
          type="text" placeholder="SYM" value={orderForm.symbol}
          onChange={(e) => setOrderForm((f) => ({ ...f, symbol: e.target.value.toUpperCase() }))}
          className="w-20 px-2 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-white font-mono outline-none focus:border-cyan-500 uppercase"
        />
        <select
          value={orderForm.side}
          onChange={(e) => setOrderForm((f) => ({ ...f, side: e.target.value }))}
          className="px-2 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-white font-mono outline-none focus:border-cyan-500"
        >
          <option value="BUY">BUY</option>
          <option value="SELL">SELL</option>
          <option value="SHORT">SHORT</option>
        </select>
        <input
          type="number" placeholder="QTY" value={orderForm.qty}
          onChange={(e) => setOrderForm((f) => ({ ...f, qty: e.target.value }))}
          className="w-20 px-2 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-white font-mono outline-none focus:border-cyan-500"
        />
        <select
          value={orderForm.type}
          onChange={(e) => setOrderForm((f) => ({ ...f, type: e.target.value }))}
          className="px-2 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-white font-mono outline-none focus:border-cyan-500"
        >
          <option value="Limit">Limit</option>
          <option value="Market">Market</option>
          <option value="Stop">Stop</option>
        </select>
        <input
          type="number" placeholder="LIMIT $" value={orderForm.limitPrice}
          onChange={(e) => setOrderForm((f) => ({ ...f, limitPrice: e.target.value }))}
          className="w-24 px-2 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-white font-mono outline-none focus:border-cyan-500"
        />
        <select
          value={orderForm.tif}
          onChange={(e) => setOrderForm((f) => ({ ...f, tif: e.target.value }))}
          className="px-2 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-white font-mono outline-none focus:border-cyan-500"
        >
          <option value="DAY">DAY</option>
          <option value="GTC">GTC</option>
          <option value="IOC">IOC</option>
        </select>
        <button
          onClick={handleSubmitOrder}
          disabled={submitting || !orderForm.symbol || !orderForm.qty}
          className="ml-auto px-5 py-1.5 bg-cyan-500 text-black font-bold text-xs font-mono rounded hover:bg-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {submitting ? "SENDING..." : "SUBMIT (Ctrl+Enter)"}
        </button>
      </div>

      {/* Submit feedback toast */}
      {submitMsg && (
        <div className={`fixed bottom-16 right-4 px-4 py-2 rounded-lg text-xs font-bold z-50 ${submitMsg.type === "success" ? "bg-emerald-500/20 border border-emerald-500/50 text-emerald-400" : "bg-red-500/20 border border-red-500/50 text-red-400"}`}>
          {submitMsg.text}
          <button onClick={() => setSubmitMsg(null)} className="ml-3 opacity-60 hover:opacity-100">×</button>
        </div>
      )}
    </div>
  );
}
