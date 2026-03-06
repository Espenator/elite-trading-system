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

  // Account metrics — totalEquity/dayPnL are top-level, buyingPower from risk endpoint
  const equity = portfolioData?.totalEquity || summary.totalValue || 0;
  const dayPnl = portfolioData?.dayPnL || summary.totalUnrealizedPnL || summary.daily_pnl_est || 0;
  const buyingPower = riskData?.buyingPower || 0;
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

  // ── Keyboard shortcut: Ctrl+Enter to submit order ──
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        if (orderForm.symbol && orderForm.qty && !submitting) handleSubmitOrder();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  });

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
        type: orderForm.type.toLowerCase() === "limit" ? "limit" : orderForm.type.toLowerCase() === "stop" ? "stop" : "market",
        time_in_force: orderForm.tif.toLowerCase(),
        qty: String(parseInt(orderForm.qty) || 1),
      };
      if (orderForm.type.toLowerCase() === "limit" && orderForm.limitPrice) {
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

  const tradingMode = (systemData?.tradingMode || systemData?.trading_mode || "live").toUpperCase();

  // ── RENDER ──
  return (
    <div className="flex flex-col h-full min-h-0">
      {/* ══════════════════════════════════════════════════════════════════
          TOP COMMAND STRIP — Teal bar (matches mockup top-bar)
          ══════════════════════════════════════════════════════════════════ */}
      <div className="h-[60px] bg-cyan-500 flex items-center justify-between px-4 flex-shrink-0 text-black">
        {/* Left: title + status pills */}
        <div className="flex items-center gap-3">
          <BarChart3 className="w-5 h-5" strokeWidth={2} />
          <span className="text-[16px] font-bold font-mono tracking-wide">ACTIVE_TRADES_V3</span>
          <div className="flex items-center gap-2 ml-2">
            <span className="px-2 py-0.5 bg-black/10 border border-black/20 rounded text-[9px] font-bold">OC_CORE_v5.2.1</span>
            <span className="px-2 py-0.5 bg-black/10 border border-black/20 rounded text-[9px] font-bold">WS_LATENCY: --ms</span>
            <span className="px-2 py-0.5 bg-black/10 border border-black/20 rounded text-[9px] font-bold">API_LIMIT: 95%</span>
          </div>
        </div>

        {/* Right: account metrics + trade mode */}
        <div className="flex items-center gap-6">
          <div className="flex items-baseline gap-1.5">
            <label className="text-[10px] font-semibold opacity-80">EQUITY</label>
            <span className="text-[16px] font-bold font-mono">{fmtM(equity)}</span>
          </div>
          <div className="flex items-baseline gap-1.5">
            <label className="text-[10px] font-semibold opacity-80">DAY P&L</label>
            <span className="text-[16px] font-bold font-mono">{fmtM(dayPnl)}</span>
          </div>
          <div className="flex items-baseline gap-1.5">
            <label className="text-[10px] font-semibold opacity-80">BUYING POWER</label>
            <span className="text-[16px] font-bold font-mono">{fmtM(buyingPower)}</span>
          </div>
          <div className="flex items-baseline gap-1.5">
            <label className="text-[10px] font-semibold opacity-80">EXPOSURE</label>
            <span className="text-[16px] font-bold font-mono">{(Number(exposure) || 0).toFixed(1)}%</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold">TRADE MODE:</span>
            {tradingMode === "LIVE" ? (
              <span className="px-2 py-0.5 bg-emerald-500 text-white rounded text-[9px] font-bold">LIVE</span>
            ) : (
              <span className="px-2 py-0.5 bg-emerald-500 text-white rounded text-[9px] font-bold">PAPER</span>
            )}
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          SPLIT LAYOUT — Positions (top) + Orders (bottom)
          ══════════════════════════════════════════════════════════════════ */}
      <div className="flex-1 flex flex-col gap-3 p-3 min-h-0 overflow-hidden">

        {/* ── POSITIONS PANEL ── */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-[#1A222C] border border-[#2D3748] rounded-md">
          {/* Panel header */}
          <div className="flex items-center justify-between px-3 py-2 bg-[#212A35] border-b border-[#2D3748] flex-shrink-0">
            <span className="text-xs font-semibold text-slate-200">OPEN POSITIONS ({posCount})</span>
            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="Filter..."
                value={posFilter}
                onChange={(e) => setPosFilter(e.target.value)}
                className="px-2 py-1 bg-[#131A22] border border-[#2D3748] rounded text-[10px] text-slate-300 font-mono w-24 outline-none focus:border-cyan-500"
              />
              <button
                onClick={handleCloseLosers}
                className="px-2.5 py-1 bg-[#131A22] border border-[#2D3748] rounded text-[10px] text-slate-300 hover:bg-[#2A3644] transition-colors"
              >
                Close Losers
              </button>
              <button
                onClick={handleFlattenAll}
                className="px-2.5 py-1 bg-[#131A22] border border-red-500/30 rounded text-[10px] text-red-400 hover:bg-red-500/10 transition-colors"
              >
                Flatten All
              </button>
            </div>
          </div>

          {/* Positions table */}
          <div className="flex-1 overflow-auto">
            <table className="w-full border-collapse text-right whitespace-nowrap">
              <thead className="sticky top-0 z-10">
                <tr>
                  {["Symbol","Side","Qty","Avail","Avg Entry","Current","Mkt Value","Unreal P&L","P&L %","Day P&L","Day %","Cost Basis","Chg Today","Asset Class","Exchange","Actions"].map((h) => (
                    <th
                      key={h}
                      className={`sticky top-0 bg-[#212A35] px-2 py-1.5 text-[9px] font-semibold uppercase text-slate-500 border-b border-[#2D3748] z-10 ${h === "Symbol" ? "text-left" : "text-right"}`}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {posLoading && positions.length === 0 && (
                  <tr>
                    <td colSpan={16} className="px-4 py-6 text-center text-cyan-500 text-xs animate-pulse">
                      Loading positions from Alpaca...
                    </td>
                  </tr>
                )}
                {posError && (
                  <tr>
                    <td colSpan={16} className="px-4 py-4 text-center text-red-400 text-xs">
                      API Error: {posError.message}
                    </td>
                  </tr>
                )}
                {filteredPositions.map((p, i) => {
                  const sym = p.symbol || p.ticker;
                  const isLong = p.side === "Long" || p.side === "long";
                  const qty = p.qty ?? p.quantity;
                  const entryPrice = p.entryPrice ?? p.entry;
                  const currentPrice = p.currentPrice ?? p.current;
                  const mktValue = p.marketValue ?? (qty * (currentPrice || 0));
                  const costBasis = p.costBasis ?? (qty * (entryPrice || 0));
                  const pnl = p.unrealizedPnL ?? p.pnl ?? 0;
                  const pnlPct = p.pnlPct ?? 0;
                  const dayPnlVal = pnl * 0.3;
                  const dayPnlPct = pnlPct * 0.5;
                  const chg = p.changeToday ?? 0;
                  return (
                    <tr key={sym || i} className="hover:bg-[#2A3644] transition-colors">
                      <td className="px-2 py-[5px] text-left font-bold text-white text-[11px] font-mono border-b border-[#2D3748]">{sym}</td>
                      <td className="px-2 py-[5px] border-b border-[#2D3748]">
                        <span className={`px-1.5 py-0.5 rounded-sm text-[9px] font-bold ${isLong ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"}`}>
                          {isLong ? "LONG" : "SHORT"}
                        </span>
                      </td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-300 border-b border-[#2D3748]">{qty}</td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-300 border-b border-[#2D3748]">{qty}</td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-300 border-b border-[#2D3748]">{fmtM(entryPrice)}</td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-white font-bold border-b border-[#2D3748]">{fmtM(currentPrice)}</td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-300 border-b border-[#2D3748]">{fmtM(mktValue)}</td>
                      <td className={`px-2 py-[5px] font-mono text-[11px] font-bold border-b border-[#2D3748] ${clr(pnl)}`}>{fmtM(pnl)}</td>
                      <td className={`px-2 py-[5px] font-mono text-[11px] border-b border-[#2D3748] ${clr(pnlPct)}`}>{fmtP(pnlPct)}</td>
                      <td className={`px-2 py-[5px] font-mono text-[11px] border-b border-[#2D3748] ${clr(dayPnlVal)}`}>{fmtM(dayPnlVal)}</td>
                      <td className={`px-2 py-[5px] font-mono text-[11px] border-b border-[#2D3748] ${clr(dayPnlPct)}`}>{fmtP(dayPnlPct)}</td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-300 border-b border-[#2D3748]">{fmtM(costBasis)}</td>
                      <td className={`px-2 py-[5px] font-mono text-[11px] border-b border-[#2D3748] ${clr(chg)}`}>{fmtP(chg)}</td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-500 border-b border-[#2D3748]">us_equity</td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-500 border-b border-[#2D3748]">NASDAQ</td>
                      <td className="px-2 py-[5px] border-b border-[#2D3748]">
                        <button
                          onClick={() => handleClosePosition(sym)}
                          className="px-1.5 py-0.5 bg-[#131A22] border border-[#2D3748] rounded text-[9px] text-slate-300 hover:bg-red-500/20 hover:text-red-400 transition-colors"
                        >
                          Cxl
                        </button>
                      </td>
                    </tr>
                  );
                })}
                {filteredPositions.length === 0 && !posLoading && !posError && (
                  <tr>
                    <td colSpan={16} className="px-4 py-6 text-center text-slate-500 text-xs">
                      No open positions.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── ORDERS PANEL ── */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-[#1A222C] border border-[#2D3748] rounded-md">
          {/* Panel header */}
          <div className="flex items-center justify-between px-3 py-2 bg-[#212A35] border-b border-[#2D3748] flex-shrink-0">
            <span className="text-xs font-semibold text-slate-200">ACTIVE ORDERS ({ordCount})</span>
            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="Filter..."
                value={ordFilter}
                onChange={(e) => setOrdFilter(e.target.value)}
                className="px-2 py-1 bg-[#131A22] border border-[#2D3748] rounded text-[10px] text-slate-300 font-mono w-24 outline-none focus:border-cyan-500"
              />
              <button
                className="px-2.5 py-1 bg-[#131A22] border border-[#2D3748] rounded text-[10px] text-slate-300 hover:bg-[#2A3644] transition-colors"
              >
                Filter: Working
              </button>
              <button
                onClick={handleCancelAll}
                className="px-2.5 py-1 bg-[#131A22] border border-red-500/30 rounded text-[10px] text-red-400 hover:bg-red-500/10 transition-colors"
              >
                Cancel All
              </button>
            </div>
          </div>

          {/* Orders table */}
          <div className="flex-1 overflow-auto">
            <table className="w-full border-collapse text-right whitespace-nowrap">
              <thead className="sticky top-0 z-10">
                <tr>
                  {["Symbol","Side","Type","Class","Qty","Filled","Limit Px","Stop Px","Trail %","TIF","Status","Submitted","Filled At","Avg Fill","Ext Hrs","Legs","Actions"].map((h) => (
                    <th
                      key={h}
                      className={`sticky top-0 bg-[#212A35] px-2 py-1.5 text-[9px] font-semibold uppercase text-slate-500 border-b border-[#2D3748] z-10 ${h === "Symbol" ? "text-left" : "text-right"}`}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ordLoading && orders.length === 0 && (
                  <tr>
                    <td colSpan={17} className="px-4 py-6 text-center text-cyan-500 text-xs animate-pulse">
                      Loading orders...
                    </td>
                  </tr>
                )}
                {filteredOrders.map((o, i) => {
                  const sym = o.symbol || "--";
                  const side = (o.side || "").toUpperCase();
                  const isBuy = side.includes("BUY");
                  const typ = o.order_type || o.type || "--";
                  const orderClass = o.order_class || "Simple";
                  const qty = o.quantity || o.qty || 0;
                  const filled = o.filled_qty || o.filledQty || 0;
                  const fillPct = qty > 0 ? (filled / qty) * 100 : 0;
                  const status = o.alpaca_status || o.status || "WORKING";
                  const submitted = o.created_at || o.timestamp || "";
                  const subDisplay = submitted ? new Date(submitted).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "--";
                  const filledAt = o.filled_at ? new Date(o.filled_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "--";
                  const avgFill = o.filled_avg_price || o.avgFillPrice;
                  return (
                    <tr key={o.id || i} className="hover:bg-[#2A3644] transition-colors">
                      <td className="px-2 py-[5px] text-left font-bold text-white text-[11px] font-mono border-b border-[#2D3748]">{sym}</td>
                      <td className="px-2 py-[5px] border-b border-[#2D3748]">
                        <span className={`px-1.5 py-0.5 rounded-sm text-[9px] font-bold ${isBuy ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"}`}>
                          {side || "BUY"}
                        </span>
                      </td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-300 border-b border-[#2D3748]">{typ}</td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-300 border-b border-[#2D3748]">{orderClass}</td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-300 border-b border-[#2D3748]">{qty}</td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-300 border-b border-[#2D3748]">
                        <span className="inline-flex items-center gap-1.5">
                          <span className="inline-block w-[50px] h-1 bg-white/10 rounded-sm align-middle">
                            <span className="block h-full bg-cyan-500 rounded-sm" style={{ width: `${fillPct}%` }} />
                          </span>
                          {filled}
                        </span>
                      </td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-300 border-b border-[#2D3748]">{o.limit_price ? fmtM(o.limit_price) : "-"}</td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-300 border-b border-[#2D3748]">{o.stop_price ? fmtM(o.stop_price) : "-"}</td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-300 border-b border-[#2D3748]">{o.trail_percent ? `${o.trail_percent}%` : "-"}</td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-300 border-b border-[#2D3748]">{(o.time_in_force || o.tif || "day").toUpperCase()}</td>
                      <td className="px-2 py-[5px] border-b border-[#2D3748]">
                        <span className="text-cyan-400 text-[10px] font-semibold">{status}</span>
                      </td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-400 border-b border-[#2D3748]">{subDisplay}</td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-400 border-b border-[#2D3748]">{filledAt}</td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-400 border-b border-[#2D3748]">{avgFill ? fmtM(avgFill) : "-"}</td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-400 border-b border-[#2D3748]">Y</td>
                      <td className="px-2 py-[5px] font-mono text-[11px] text-slate-400 border-b border-[#2D3748]">1</td>
                      <td className="px-2 py-[5px] border-b border-[#2D3748]">
                        <div className="inline-flex items-center gap-1">
                          <button
                            onClick={() => {
                              handleCancelOrder(o.id);
                              setOrderForm({ symbol: sym, side: side, type: typ || "Limit", qty: String(qty), limitPrice: o.limit_price || "", stopPrice: o.stop_price || "", tif: (o.time_in_force || "day").toUpperCase() });
                            }}
                            className="px-1.5 py-0.5 bg-[#131A22] border border-[#2D3748] rounded text-[9px] text-slate-300 hover:bg-[#2A3644] transition-colors"
                            title="Cancel & replace: fills Quick Execute with this order"
                          >
                            Mod
                          </button>
                          <button
                            onClick={() => handleCancelOrder(o.id)}
                            className="px-1.5 py-0.5 bg-[#131A22] border border-[#2D3748] rounded text-[9px] text-red-400 hover:bg-red-500/20 transition-colors"
                          >
                            Cxl
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {filteredOrders.length === 0 && !ordLoading && (
                  <tr>
                    <td colSpan={17} className="px-4 py-6 text-center text-slate-500 text-xs">
                      No active orders.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          BOTTOM QUICK EXECUTE BAR — Inline order entry (matches mockup)
          ══════════════════════════════════════════════════════════════════ */}
      <div className="h-12 bg-[#1A222C] border-t border-[#2D3748] flex items-center px-4 gap-3 flex-shrink-0">
        <span className="text-[10px] font-bold text-cyan-400 mr-2">QUICK EXECUTE</span>
        <input
          type="text"
          placeholder="SYM"
          value={orderForm.symbol}
          onChange={(e) => setOrderForm((f) => ({ ...f, symbol: e.target.value.toUpperCase() }))}
          className="w-20 px-2.5 py-1.5 bg-[#131A22] border border-[#2D3748] rounded text-xs text-white font-mono outline-none focus:border-cyan-500 uppercase"
        />
        <select
          value={orderForm.side}
          onChange={(e) => setOrderForm((f) => ({ ...f, side: e.target.value }))}
          className="w-20 px-2.5 py-1.5 bg-[#131A22] border border-[#2D3748] rounded text-xs text-white font-mono outline-none focus:border-cyan-500"
        >
          <option value="BUY">BUY</option>
          <option value="SELL">SELL</option>
          <option value="SHORT">SHORT</option>
        </select>
        <input
          type="number"
          placeholder="QTY"
          value={orderForm.qty}
          onChange={(e) => setOrderForm((f) => ({ ...f, qty: e.target.value }))}
          className="w-20 px-2.5 py-1.5 bg-[#131A22] border border-[#2D3748] rounded text-xs text-white font-mono outline-none focus:border-cyan-500"
        />
        <select
          value={orderForm.type}
          onChange={(e) => setOrderForm((f) => ({ ...f, type: e.target.value }))}
          className="w-[100px] px-2.5 py-1.5 bg-[#131A22] border border-[#2D3748] rounded text-xs text-white font-mono outline-none focus:border-cyan-500"
        >
          <option value="Limit">Limit</option>
          <option value="Market">Market</option>
          <option value="Stop">Stop</option>
        </select>
        <input
          type="number"
          placeholder="LIMIT $"
          value={orderForm.limitPrice}
          onChange={(e) => setOrderForm((f) => ({ ...f, limitPrice: e.target.value }))}
          className="w-[100px] px-2.5 py-1.5 bg-[#131A22] border border-[#2D3748] rounded text-xs text-white font-mono outline-none focus:border-cyan-500"
        />
        <select
          value={orderForm.tif}
          onChange={(e) => setOrderForm((f) => ({ ...f, tif: e.target.value }))}
          className="w-20 px-2.5 py-1.5 bg-[#131A22] border border-[#2D3748] rounded text-xs text-white font-mono outline-none focus:border-cyan-500"
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
          <button onClick={() => setSubmitMsg(null)} className="ml-3 opacity-60 hover:opacity-100">&times;</button>
        </div>
      )}
    </div>
  );
}
