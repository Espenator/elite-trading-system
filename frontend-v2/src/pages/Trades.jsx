/**
 * Active Trades Page - Matches mockup: Active-Trades.png (v3)
 * Layout: KPI top bar, Positions table, Orders table, Footer
 * Real Alpaca API via useApi hooks
 */
import React, { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { toast } from "react-toastify";
import log from "@/utils/logger";
import {
  Settings,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  XCircle,
  X,
  Edit3,
} from "lucide-react";
import { useApi } from "../hooks/useApi";
import { getApiUrl, getAuthHeaders } from "../config/api";

// ── Formatters ──
const fmtM = (n) => {
  if (n == null || isNaN(n)) return "--";
  return (
    "$" +
    Number(n).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
};
const fmtPct = (n) => {
  if (n == null || isNaN(n)) return "--";
  return (n > 0 ? "+" : "") + Number(n).toFixed(2) + "%";
};
const fmtPnl = (n) => {
  if (n == null || isNaN(n)) return "--";
  const prefix = n > 0 ? "+$" : n < 0 ? "-$" : "$";
  return (
    prefix +
    Math.abs(Number(n)).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
};
const clr = (n) => (n >= 0 ? "text-emerald-400" : "text-red-400");

// ── Mini Sparkline SVG (bar chart style matching mockup) ──
function MiniSparkline({ data, width = 56, height = 18, color }) {
  // Generate data if not provided
  const pts = useMemo(() => {
    if (data && data.length >= 2) return data;
    return Array.from({ length: 20 }, () => Math.random() * 10 + 2);
  }, [data]);

  const max = Math.max(...pts);
  const barW = width / pts.length;

  const baseColor = color || "#34d399";

  return (
    <svg width={width} height={height} className="inline-block align-middle">
      {pts.map((v, i) => {
        const barH = (v / max) * (height - 1);
        return (
          <rect
            key={i}
            x={i * barW}
            y={height - barH}
            width={Math.max(barW - 0.5, 1)}
            height={barH}
            fill={baseColor}
            opacity={0.5 + (v / max) * 0.5}
          />
        );
      })}
    </svg>
  );
}

// ── Sort helper ──
function sortData(data, sortKey, sortDir) {
  if (!sortKey) return data;
  return [...data].sort((a, b) => {
    let aVal = a[sortKey] ?? 0;
    let bVal = b[sortKey] ?? 0;
    if (typeof aVal === "string") aVal = aVal.toLowerCase();
    if (typeof bVal === "string") bVal = bVal.toLowerCase();
    if (aVal < bVal) return sortDir === "asc" ? -1 : 1;
    if (aVal > bVal) return sortDir === "asc" ? 1 : -1;
    return 0;
  });
}

// ── Status badge ──
function StatusBadge({ status }) {
  const s = (status || "").toLowerCase();
  let bg = "bg-slate-600/40 text-slate-300";
  if (s === "new" || s === "accepted" || s === "working") bg = "bg-cyan-500/20 text-cyan-400";
  if (s === "filled") bg = "bg-emerald-500/20 text-emerald-400";
  if (s === "partially_filled") bg = "bg-yellow-500/20 text-yellow-400";
  if (s === "canceled" || s === "cancelled") bg = "bg-red-500/20 text-red-400";
  if (s === "rejected") bg = "bg-red-600/30 text-red-500";
  return (
    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${bg}`}>
      {status || "--"}
    </span>
  );
}

// ── Type badge for orders ──
function TypeBadge({ type }) {
  const t = (type || "").toLowerCase();
  let bg = "bg-slate-600/30 text-slate-300";
  if (t === "market") bg = "bg-blue-500/20 text-blue-400";
  if (t === "limit") bg = "bg-purple-500/20 text-purple-400";
  if (t === "stop") bg = "bg-orange-500/20 text-orange-400";
  if (t === "bracket") bg = "bg-cyan-500/20 text-cyan-400";
  if (t === "stop_limit") bg = "bg-amber-500/20 text-amber-400";
  return (
    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${bg}`}>
      {type || "--"}
    </span>
  );
}

export default function Trades() {
  // ── State ──
  const [posFilter, setPosFilter] = useState("");
  const [ordFilter, setOrdFilter] = useState("");
  const [posSortKey, setPosSortKey] = useState(null);
  const [posSortDir, setPosSortDir] = useState("asc");
  const [ordSortKey, setOrdSortKey] = useState(null);
  const [ordSortDir, setOrdSortDir] = useState("asc");
  const [rebalanceTime, setRebalanceTime] = useState("25m");

  // ── Real API Hooks ──
  const {
    data: positionsData,
    loading: posLoading,
    error: posError,
    refetch: refetchPositions,
  } = useApi("alpaca/positions", { pollIntervalMs: 5000 });

  const {
    data: ordersData,
    loading: ordLoading,
    error: ordError,
    refetch: refetchOrders,
  } = useApi("alpaca/orders", { pollIntervalMs: 5000 });

  const { data: accountData } = useApi("alpaca/account", { pollIntervalMs: 10000 });

  const { data: portfolioData } = useApi("portfolio", { pollIntervalMs: 10000 });

  const { data: systemData } = useApi("system", { pollIntervalMs: 30000 });

  // ── Derived Data ──
  const positions = useMemo(() => {
    if (Array.isArray(positionsData)) return positionsData;
    if (positionsData?.positions) return positionsData.positions;
    return [];
  }, [positionsData]);

  const orders = useMemo(() => {
    if (Array.isArray(ordersData)) return ordersData;
    if (ordersData?.orders) return ordersData.orders;
    return [];
  }, [ordersData]);

  // Account metrics
  const nav = accountData?.equity || accountData?.portfolio_value || portfolioData?.totalEquity || 0;
  const dayPnl = accountData?.profit_loss || portfolioData?.dayPnL || 0;
  const buyingPower = accountData?.buying_power || accountData?.daytrading_buying_power || 0;

  // Margin available as percentage (mockup shows "82%")
  const marginAvailRaw = accountData?.regt_buying_power
    ? Number(accountData.regt_buying_power)
    : accountData?.margin_available || 0;
  const marginPct = nav > 0 ? Math.round((marginAvailRaw / Number(nav)) * 100) : 0;

  // NAV change percentage (mockup shows "1.5%")
  const navChangePct = portfolioData?.navChangePct
    || (accountData?.equity && accountData?.last_equity
      ? ((Number(accountData.equity) - Number(accountData.last_equity)) / Number(accountData.last_equity)) * 100
      : 0);

  // Regime and Trend from portfolio or system data
  const regime = portfolioData?.regime || systemData?.regime || "BULL";
  const regimeColor =
    regime?.toLowerCase().includes("bull")
      ? "text-emerald-400"
      : regime?.toLowerCase().includes("bear")
      ? "text-red-400"
      : "text-yellow-400";

  const trend = portfolioData?.trend || systemData?.trend || "STRONG";
  const trendColor =
    trend?.toLowerCase().includes("strong")
      ? "text-emerald-400"
      : trend?.toLowerCase().includes("weak")
      ? "text-red-400"
      : "text-yellow-400";

  const agentCount = systemData?.agent_count || systemData?.agents?.length || 3;

  // Current time for NAV timestamp
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60000);
    return () => clearInterval(id);
  }, []);
  const timeStr = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  // ── Filtered + sorted positions ──
  const filteredPositions = useMemo(() => {
    let list = positions.filter(
      (p) =>
        !posFilter ||
        (p.symbol || p.ticker || "").toUpperCase().includes(posFilter.toUpperCase())
    );
    return sortData(list, posSortKey, posSortDir);
  }, [positions, posFilter, posSortKey, posSortDir]);

  // ── Filtered + sorted orders ──
  const filteredOrders = useMemo(() => {
    let list = orders.filter(
      (o) =>
        !ordFilter ||
        (o.symbol || "").toUpperCase().includes(ordFilter.toUpperCase())
    );
    return sortData(list, ordSortKey, ordSortDir);
  }, [orders, ordFilter, ordSortKey, ordSortDir]);

  // ── Sort handler ──
  const handlePosSort = (key) => {
    if (posSortKey === key) {
      setPosSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setPosSortKey(key);
      setPosSortDir("asc");
    }
  };

  const handleOrdSort = (key) => {
    if (ordSortKey === key) {
      setOrdSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setOrdSortKey(key);
      setOrdSortDir("asc");
    }
  };

  // ── Sort indicator ──
  const SortIcon = ({ colKey, activeKey, activeDir }) => {
    if (colKey !== activeKey) return null;
    return activeDir === "asc" ? (
      <ChevronUp className="inline w-3 h-3 ml-0.5" />
    ) : (
      <ChevronDown className="inline w-3 h-3 ml-0.5" />
    );
  };

  // ── Actions ──
  const handleRefresh = () => {
    refetchPositions();
    refetchOrders();
  };

  const handleClosePosition = async (symbol) => {
    try {
      const res = await fetch(
        getApiUrl("orders") + `/close?symbol=${encodeURIComponent(symbol)}`,
        { method: "POST", headers: getAuthHeaders() }
      );
      if (!res.ok) throw new Error("Failed");
      toast.success(`Closing ${symbol}`);
      refetchPositions();
    } catch (e) {
      log.error("Close position failed:", e);
      toast.error(`Close ${symbol} failed: ${e.message}`);
    }
  };

  const handleCancelOrder = async (orderId) => {
    try {
      await fetch(getApiUrl("alpaca/orders") + `/${orderId}`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      toast.success("Order cancelled");
      refetchOrders();
    } catch (e) {
      log.error("Cancel order failed:", e);
      toast.error(`Cancel failed: ${e.message}`);
    }
  };

  const handleCancelAll = async () => {
    if (!window.confirm("Cancel ALL open orders?")) return;
    try {
      await fetch(getApiUrl("alpaca/orders"), {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      toast.success("All orders cancelled");
      refetchOrders();
    } catch (e) {
      toast.error(`Cancel all failed: ${e.message}`);
    }
  };

  // ── Position table columns (matching mockup exactly) ──
  // Mockup headers: Symbol | Side | Qty | Avg Price | Mkt Price (C) | Day P&L (%) | Day P&L ($) | Unrealized P&L | Realized P&L (%) | Cost Basis | Price | Delta | Theta | Qty | Beta | Daily Range Vol | Sparkline | Actions
  const posColumns = [
    { key: "symbol", label: "Symbol", align: "left" },
    { key: "side", label: "Side", align: "left" },
    { key: "qty", label: "Qty", align: "right" },
    { key: "avg_entry_price", label: "Avg Price", align: "right" },
    { key: "current_price", label: "Mkt Price (C)", align: "right" },
    { key: "day_pnl_pct", label: "Day P&L (%)", align: "right" },
    { key: "day_pnl_dollar", label: "Day P&L ($)", align: "right" },
    { key: "unrealized_pl", label: "Unrealized P&L", align: "right" },
    { key: "realized_pl_pct", label: "Realized P&L (%)", align: "right" },
    { key: "cost_basis", label: "Cost Basis", align: "right" },
    { key: "market_value", label: "Price", align: "right" },
    { key: "delta", label: "Delta", align: "right" },
    { key: "theta", label: "Theta", align: "right" },
    { key: "qty2", label: "Qty", align: "right" },
    { key: "beta", label: "Beta", align: "right" },
    { key: "daily_range_vol", label: "Daily Range Vol", align: "right" },
    { key: "sparkline", label: "Sparkline", align: "center" },
    { key: "actions", label: "Actions", align: "center" },
  ];

  // ── Order table columns (matching mockup exactly) ──
  // Mockup headers: Order ID | Date | Time | Type | Symbol | P/L(Day Qty) | Limit Price | Stop Price | Status | Execution Time | Avg Fill Price | Legs (Bracket/Order ID) | Actions
  const ordColumns = [
    { key: "id", label: "Order ID", align: "left" },
    { key: "date", label: "Date", align: "left" },
    { key: "time", label: "Time", align: "left" },
    { key: "type", label: "Type", align: "left" },
    { key: "symbol", label: "Symbol", align: "left" },
    { key: "qty", label: "P/L(Day Qty)", align: "right" },
    { key: "limit_price", label: "Limit Price", align: "right" },
    { key: "stop_price", label: "Stop Price", align: "right" },
    { key: "status", label: "Status", align: "left" },
    { key: "filled_at", label: "Execution Time", align: "left" },
    { key: "avg_fill", label: "Avg Fill Price", align: "right" },
    { key: "legs", label: "Legs (Bracket/Order ID)", align: "left" },
    { key: "actions", label: "Actions", align: "center" },
  ];

  // ── RENDER ──
  return (
    <div className="flex flex-col h-full min-h-0 bg-[#0B1120]">
      {/* ═══════════════════════════════════════════════════
          TOP KPI BAR - matches mockup header strip
          NAV | DAILY P&L | MARGIN AVAIL | BUYING POWER | REGIME | TREND | REBALANCED
          ═══════════════════════════════════════════════════ */}
      <div className="flex items-center gap-5 px-4 py-1.5 bg-[#0D1525] border-b border-[#1E293B] flex-shrink-0">
        {/* NAV */}
        <div className="flex items-baseline gap-1.5">
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">
            NAV:
          </span>
          <span className="text-[13px] font-bold text-white font-mono">
            {fmtM(nav)}
          </span>
          <span className={`text-[10px] font-mono ${clr(navChangePct)}`}>
            ({fmtPct(navChangePct)})
          </span>
        </div>

        <span className="text-slate-600">|</span>

        {/* DAILY P&L */}
        <div className="flex items-baseline gap-1.5">
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">
            DAILY P&L:
          </span>
          <span className={`text-[13px] font-bold font-mono ${clr(dayPnl)}`}>
            {fmtPnl(dayPnl)}
          </span>
        </div>

        <span className="text-slate-600">|</span>

        {/* MARGIN AVAIL (shown as percentage in mockup) */}
        <div className="flex items-baseline gap-1.5">
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">
            MARGIN AVAIL:
          </span>
          <span className="text-[13px] font-bold text-white font-mono">
            {marginPct > 0 ? `${marginPct}%` : "--"}
          </span>
        </div>

        <span className="text-slate-600">|</span>

        {/* BUYING POWER */}
        <div className="flex items-baseline gap-1.5">
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">
            BUYING POWER:
          </span>
          <span className="text-[13px] font-bold text-white font-mono">
            {fmtM(buyingPower)}
          </span>
        </div>

        <span className="text-slate-600">|</span>

        {/* REGIME */}
        <div className="flex items-baseline gap-1.5">
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">
            REGIME:
          </span>
          <span className={`text-[13px] font-bold font-mono uppercase ${regimeColor}`}>
            {regime}
          </span>
        </div>

        <span className="text-slate-600">|</span>

        {/* TREND */}
        <div className="flex items-baseline gap-1.5">
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">
            TREND:
          </span>
          <span className={`text-[13px] font-bold font-mono uppercase ${trendColor}`}>
            {trend}
          </span>
        </div>

        <span className="text-slate-600">|</span>

        {/* REBALANCED */}
        <div className="flex items-center gap-1.5 ml-auto">
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">
            REBALANCED:
          </span>
          <select
            value={rebalanceTime}
            onChange={(e) => setRebalanceTime(e.target.value)}
            className="px-2 py-0.5 bg-[#131A2B] border border-[#1E293B] rounded text-[11px] text-white font-mono outline-none focus:border-cyan-500"
          >
            <option value="5m">5m</option>
            <option value="15m">15m</option>
            <option value="25m">25m</option>
            <option value="1h">1h</option>
            <option value="4h">4h</option>
          </select>
          <button
            onClick={handleRefresh}
            className="p-1 text-slate-400 hover:text-cyan-400 transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════
          MAIN CONTENT: Positions + Orders tables
          ═══════════════════════════════════════════════════ */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* ── POSITIONS TABLE ── */}
        <div className="flex-[3] flex flex-col min-h-0 overflow-hidden">
          {/* Section header */}
          <div className="flex items-center justify-between px-3 py-1 bg-[#0D1525] border-b border-[#1E293B] flex-shrink-0">
            <span className="text-[11px] font-bold text-slate-300 tracking-wide">
              Positions
            </span>
            <input
              type="text"
              placeholder="Filter symbol..."
              value={posFilter}
              onChange={(e) => setPosFilter(e.target.value)}
              className="px-2 py-0.5 bg-[#131A2B] border border-[#1E293B] rounded text-[10px] text-slate-300 font-mono w-28 outline-none focus:border-cyan-500"
            />
          </div>

          {/* Table */}
          <div className="flex-1 overflow-auto">
            <table className="w-full border-collapse whitespace-nowrap text-[10px]">
              <thead className="sticky top-0 z-10">
                <tr>
                  {posColumns.map((col) => (
                    <th
                      key={col.key}
                      onClick={() =>
                        col.key !== "sparkline" &&
                        col.key !== "actions" &&
                        handlePosSort(col.key)
                      }
                      className={`sticky top-0 bg-[#111827] px-1.5 py-1 text-[8px] font-semibold uppercase tracking-wider border-b border-[#1E293B] z-10 cursor-pointer select-none hover:text-cyan-400 transition-colors ${
                        col.align === "left"
                          ? "text-left"
                          : col.align === "center"
                          ? "text-center"
                          : "text-right"
                      } ${
                        posSortKey === col.key
                          ? "text-cyan-400"
                          : "text-slate-500"
                      }`}
                    >
                      {col.label}
                      <SortIcon
                        colKey={col.key}
                        activeKey={posSortKey}
                        activeDir={posSortDir}
                      />
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {posLoading && positions.length === 0 && (
                  <tr>
                    <td
                      colSpan={posColumns.length}
                      className="px-4 py-8 text-center text-cyan-500 text-xs animate-pulse"
                    >
                      Loading positions...
                    </td>
                  </tr>
                )}
                {posError && (
                  <tr>
                    <td
                      colSpan={posColumns.length}
                      className="px-4 py-4 text-center text-red-400 text-xs"
                    >
                      API Error: {posError.message}
                    </td>
                  </tr>
                )}
                {filteredPositions.map((p, i) => {
                  const sym = p.symbol || p.ticker || "--";
                  const side = p.side || (Number(p.qty) >= 0 ? "long" : "short");
                  const isLong =
                    side.toLowerCase() === "long" || side.toLowerCase() === "buy";
                  const qty = Math.abs(Number(p.qty || p.quantity || 0));
                  const avgPrice = Number(
                    p.avg_entry_price || p.entryPrice || p.entry || 0
                  );
                  const mktPrice = Number(
                    p.current_price || p.currentPrice || p.current || 0
                  );
                  const unrealPnl = Number(
                    p.unrealized_pl || p.unrealizedPnL || p.unrealized_pnl || p.pnl || 0
                  );
                  const realPnl = Number(
                    p.realized_pl || p.realizedPnL || p.realized_pnl || 0
                  );
                  const costBasis = Number(
                    p.cost_basis || p.costBasis || qty * avgPrice || 0
                  );
                  const mktValue = Number(
                    p.market_value || p.marketValue || qty * mktPrice || 0
                  );
                  const dayPnlDollar = Number(
                    p.unrealized_intraday_pl || p.dayPnl || 0
                  );
                  const dayPnlPctVal = Number(
                    p.unrealized_intraday_plpc || p.dayPnlPct || p.change_today || 0
                  ) * 100;

                  // Realized P&L percentage
                  const realPnlPct = costBasis !== 0 ? (realPnl / costBasis) * 100 : 0;

                  // Greeks (may not be available for equities)
                  const delta = p.delta ?? "--";
                  const theta = p.theta ?? "--";
                  const beta = p.beta ?? "--";
                  const dailyRangeVol = p.daily_range_vol || p.dailyRangeVol || "--";

                  // Sparkline data
                  const sparkData = p.sparkline || p.price_history || null;

                  return (
                    <tr
                      key={sym + "-" + i}
                      className="hover:bg-[#1E293B]/50 transition-colors border-b border-[#1E293B]/30"
                    >
                      {/* Symbol */}
                      <td className="px-1.5 py-[3px] text-left">
                        <span className="font-bold text-white font-mono text-[10px]">
                          {sym}
                        </span>
                      </td>
                      {/* Side */}
                      <td className="px-1.5 py-[3px] text-left">
                        <span
                          className={`px-1 py-0.5 rounded-sm text-[8px] font-bold ${
                            isLong
                              ? "bg-emerald-500/15 text-emerald-400"
                              : "bg-red-500/15 text-red-400"
                          }`}
                        >
                          {isLong ? "LONG" : "SHORT"}
                        </span>
                      </td>
                      {/* Qty */}
                      <td className="px-1.5 py-[3px] text-right font-mono text-slate-300">
                        {qty.toLocaleString()}
                      </td>
                      {/* Avg Price */}
                      <td className="px-1.5 py-[3px] text-right font-mono text-slate-300">
                        {fmtM(avgPrice)}
                      </td>
                      {/* Mkt Price (C) */}
                      <td className="px-1.5 py-[3px] text-right font-mono text-white font-semibold">
                        {fmtM(mktPrice)}
                      </td>
                      {/* Day P&L (%) */}
                      <td className={`px-1.5 py-[3px] text-right font-mono font-semibold ${clr(dayPnlPctVal)}`}>
                        {dayPnlPctVal !== 0 ? fmtPct(dayPnlPctVal) : "--"}
                      </td>
                      {/* Day P&L ($) */}
                      <td className={`px-1.5 py-[3px] text-right font-mono font-semibold ${clr(dayPnlDollar)}`}>
                        {dayPnlDollar !== 0 ? fmtPnl(dayPnlDollar) : "--"}
                      </td>
                      {/* Unrealized P&L */}
                      <td className={`px-1.5 py-[3px] text-right font-mono font-bold ${clr(unrealPnl)}`}>
                        {fmtPnl(unrealPnl)}
                      </td>
                      {/* Realized P&L (%) */}
                      <td className={`px-1.5 py-[3px] text-right font-mono ${clr(realPnl)}`}>
                        {realPnl !== 0 ? fmtPct(realPnlPct) : "--"}
                      </td>
                      {/* Cost Basis */}
                      <td className="px-1.5 py-[3px] text-right font-mono text-slate-400">
                        {fmtM(costBasis)}
                      </td>
                      {/* Price (market value) */}
                      <td className="px-1.5 py-[3px] text-right font-mono text-slate-300">
                        {fmtM(mktValue)}
                      </td>
                      {/* Delta */}
                      <td className="px-1.5 py-[3px] text-right font-mono text-slate-500 text-[9px]">
                        {delta}
                      </td>
                      {/* Theta */}
                      <td className="px-1.5 py-[3px] text-right font-mono text-slate-500 text-[9px]">
                        {theta}
                      </td>
                      {/* Qty (second instance) */}
                      <td className="px-1.5 py-[3px] text-right font-mono text-slate-400 text-[9px]">
                        {qty.toLocaleString()}
                      </td>
                      {/* Beta */}
                      <td className="px-1.5 py-[3px] text-right font-mono text-slate-500 text-[9px]">
                        {beta}
                      </td>
                      {/* Daily Range Vol */}
                      <td className="px-1.5 py-[3px] text-right font-mono text-slate-500 text-[9px]">
                        {dailyRangeVol}
                      </td>
                      {/* Sparkline */}
                      <td className="px-1.5 py-[3px] text-center">
                        <MiniSparkline
                          data={sparkData}
                          width={52}
                          height={16}
                          color={unrealPnl >= 0 ? "#2dd4bf" : "#f87171"}
                        />
                      </td>
                      {/* Actions */}
                      <td className="px-1.5 py-[3px] text-center">
                        <div className="inline-flex items-center gap-0.5">
                          <button
                            onClick={() => handleClosePosition(sym)}
                            className="p-0.5 text-slate-500 hover:text-red-400 transition-colors"
                            title="Close position"
                          >
                            <X className="w-3 h-3" />
                          </button>
                          <button
                            className="p-0.5 text-slate-500 hover:text-cyan-400 transition-colors"
                            title="Modify position"
                          >
                            <Edit3 className="w-3 h-3" />
                          </button>
                          <button
                            className="p-0.5 text-slate-500 hover:text-slate-200 transition-colors"
                            title="Position settings"
                          >
                            <Settings className="w-3 h-3" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {filteredPositions.length === 0 && !posLoading && !posError && (
                  <tr>
                    <td
                      colSpan={posColumns.length}
                      className="px-4 py-8 text-center text-slate-500 text-xs"
                    >
                      No open positions.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── ORDERS TABLE ── */}
        <div className="flex-[2] flex flex-col min-h-0 overflow-hidden border-t border-[#1E293B]">
          {/* Section header */}
          <div className="flex items-center justify-between px-3 py-1 bg-[#0D1525] border-b border-[#1E293B] flex-shrink-0">
            <span className="text-[11px] font-bold text-slate-300 tracking-wide">
              Orders
            </span>
            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="Filter..."
                value={ordFilter}
                onChange={(e) => setOrdFilter(e.target.value)}
                className="px-2 py-0.5 bg-[#131A2B] border border-[#1E293B] rounded text-[10px] text-slate-300 font-mono w-28 outline-none focus:border-cyan-500"
              />
              <button
                onClick={handleCancelAll}
                className="px-2 py-0.5 bg-[#131A2B] border border-red-500/30 rounded text-[9px] text-red-400 hover:bg-red-500/10 transition-colors"
              >
                Cancel All
              </button>
            </div>
          </div>

          {/* Table */}
          <div className="flex-1 overflow-auto">
            <table className="w-full border-collapse whitespace-nowrap text-[10px]">
              <thead className="sticky top-0 z-10">
                <tr>
                  {ordColumns.map((col) => (
                    <th
                      key={col.key}
                      onClick={() =>
                        col.key !== "actions" && handleOrdSort(col.key)
                      }
                      className={`sticky top-0 bg-[#111827] px-1.5 py-1 text-[8px] font-semibold uppercase tracking-wider border-b border-[#1E293B] z-10 cursor-pointer select-none hover:text-cyan-400 transition-colors ${
                        col.align === "left"
                          ? "text-left"
                          : col.align === "center"
                          ? "text-center"
                          : "text-right"
                      } ${
                        ordSortKey === col.key
                          ? "text-cyan-400"
                          : "text-slate-500"
                      }`}
                    >
                      {col.label}
                      <SortIcon
                        colKey={col.key}
                        activeKey={ordSortKey}
                        activeDir={ordSortDir}
                      />
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ordLoading && orders.length === 0 && (
                  <tr>
                    <td
                      colSpan={ordColumns.length}
                      className="px-4 py-6 text-center text-cyan-500 text-xs animate-pulse"
                    >
                      Loading orders...
                    </td>
                  </tr>
                )}
                {filteredOrders.map((o, i) => {
                  const orderId = o.id || o.order_id || "--";
                  const orderIdShort =
                    orderId.length > 12
                      ? "Order-" + orderId.slice(-6).toUpperCase()
                      : orderId;
                  const sym = o.symbol || "--";
                  const side = (o.side || "").toUpperCase();
                  const isBuy = side.includes("BUY");
                  const typ = o.order_type || o.type || "market";
                  const orderClass = o.order_class || "";
                  const qty = o.qty || o.quantity || 0;
                  const filledQty = o.filled_qty || o.filledQty || 0;
                  const limitPx = o.limit_price;
                  const stopPx = o.stop_price;
                  const filledPrice = o.filled_avg_price || o.avgFillPrice || null;
                  const status = o.status || o.alpaca_status || "new";
                  const createdAt = o.created_at || o.timestamp || "";

                  // Separate Date and Time columns (matching mockup)
                  let dateDisplay = "--";
                  let timeDisplay = "--";
                  if (createdAt) {
                    const dt = new Date(createdAt);
                    dateDisplay = dt.toLocaleDateString([], {
                      year: "numeric",
                      month: "short",
                      day: "2-digit",
                    });
                    timeDisplay = dt.toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    });
                  }

                  const filledAt = o.filled_at
                    ? new Date(o.filled_at).toLocaleString([], {
                        year: "numeric",
                        month: "short",
                        day: "2-digit",
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })
                    : "--";
                  const avgFill = o.filled_avg_price || o.avgFillPrice || null;

                  // Legs info
                  const legs = o.legs || [];
                  const hasLegs = legs.length > 0 || orderClass === "bracket" || orderClass === "oco" || orderClass === "oto";
                  const legLabel = hasLegs
                    ? orderClass === "bracket"
                      ? "Bracket Order (3)"
                      : orderClass === "oco"
                      ? "OCO (2)"
                      : orderClass === "oto"
                      ? "OTO (2)"
                      : `${legs.length} legs`
                    : "--";

                  // Determine row highlight for parent/child
                  const isChild = o.parent_id || o.replaced_by;
                  const rowBg = isChild
                    ? "bg-[#111827]/60"
                    : "";

                  return (
                    <React.Fragment key={o.id || i}>
                      <tr
                        className={`hover:bg-[#1E293B]/50 transition-colors border-b border-[#1E293B]/30 ${rowBg}`}
                      >
                        {/* Order ID */}
                        <td className="px-1.5 py-[3px] text-left font-mono text-cyan-400 text-[9px]">
                          {orderIdShort}
                        </td>
                        {/* Date */}
                        <td className="px-1.5 py-[3px] text-left font-mono text-slate-400 text-[9px]">
                          {dateDisplay}
                        </td>
                        {/* Time */}
                        <td className="px-1.5 py-[3px] text-left font-mono text-slate-400 text-[9px]">
                          {timeDisplay}
                        </td>
                        {/* Type */}
                        <td className="px-1.5 py-[3px] text-left">
                          <TypeBadge type={typ} />
                        </td>
                        {/* Symbol */}
                        <td className="px-1.5 py-[3px] text-left font-bold text-white font-mono">
                          {sym}
                        </td>
                        {/* P/L(Day Qty) */}
                        <td className="px-1.5 py-[3px] text-right font-mono text-slate-300">
                          {qty}
                        </td>
                        {/* Limit Price */}
                        <td className="px-1.5 py-[3px] text-right font-mono text-slate-300">
                          {limitPx ? fmtM(limitPx) : "--"}
                        </td>
                        {/* Stop Price */}
                        <td className="px-1.5 py-[3px] text-right font-mono text-slate-300">
                          {stopPx ? fmtM(stopPx) : "--"}
                        </td>
                        {/* Status */}
                        <td className="px-1.5 py-[3px] text-left">
                          <StatusBadge status={status} />
                        </td>
                        {/* Execution Time */}
                        <td className="px-1.5 py-[3px] text-left font-mono text-slate-400 text-[9px]">
                          {filledAt}
                        </td>
                        {/* Avg Fill Price */}
                        <td className="px-1.5 py-[3px] text-right font-mono text-slate-300">
                          {avgFill ? fmtM(avgFill) : "--"}
                        </td>
                        {/* Legs (Bracket/Order ID) */}
                        <td className="px-1.5 py-[3px] text-left text-[9px] text-slate-400">
                          {hasLegs ? (
                            <span className="text-cyan-400">{legLabel}</span>
                          ) : (
                            "--"
                          )}
                        </td>
                        {/* Actions */}
                        <td className="px-1.5 py-[3px] text-center">
                          <div className="inline-flex items-center gap-1">
                            <button
                              onClick={() => handleCancelOrder(orderId)}
                              className="px-1.5 py-0.5 bg-[#131A2B] border border-[#1E293B] rounded text-[8px] text-red-400 hover:bg-red-500/20 transition-colors"
                              title="Cancel order"
                            >
                              Cancel
                            </button>
                            <button
                              className="px-1.5 py-0.5 bg-[#131A2B] border border-[#1E293B] rounded text-[8px] text-slate-400 hover:bg-slate-600/20 transition-colors"
                              title="Close order"
                            >
                              Close
                            </button>
                          </div>
                        </td>
                      </tr>
                      {/* Render child legs inline if bracket */}
                      {legs.length > 0 &&
                        legs.map((leg, li) => {
                          const legType = leg.order_type || leg.type || "--";
                          const legStatus = leg.status || "--";
                          const legLimitPx = leg.limit_price;
                          const legStopPx = leg.stop_price;
                          const legFilledPx = leg.filled_avg_price;
                          const legLabel2 =
                            legType.toLowerCase() === "limit"
                              ? "Profit Target"
                              : legType.toLowerCase().includes("stop")
                              ? "Stop Loss"
                              : legType;
                          return (
                            <tr
                              key={`${o.id}-leg-${li}`}
                              className="bg-[#0D1525]/80 border-b border-[#1E293B]/20 hover:bg-[#1E293B]/30 transition-colors"
                            >
                              <td className="px-1.5 py-[2px] text-left font-mono text-slate-500 text-[9px] pl-5">
                                {leg.id ? "Order-" + (leg.id || "").slice(-6).toUpperCase() : "--"}
                              </td>
                              <td className="px-1.5 py-[2px] text-left font-mono text-slate-500 text-[9px]">
                                --
                              </td>
                              <td className="px-1.5 py-[2px] text-left font-mono text-slate-500 text-[9px]">
                                --
                              </td>
                              <td className="px-1.5 py-[2px] text-left">
                                <TypeBadge type={legType} />
                              </td>
                              <td className="px-1.5 py-[2px] text-left font-mono text-slate-400 text-[9px]">
                                {sym}
                              </td>
                              <td className="px-1.5 py-[2px] text-right font-mono text-slate-400 text-[9px]">
                                {leg.qty || qty}
                              </td>
                              <td className="px-1.5 py-[2px] text-right font-mono text-slate-400 text-[9px]">
                                {legLimitPx ? fmtM(legLimitPx) : "--"}
                              </td>
                              <td className="px-1.5 py-[2px] text-right font-mono text-slate-400 text-[9px]">
                                {legStopPx ? fmtM(legStopPx) : "--"}
                              </td>
                              <td className="px-1.5 py-[2px] text-left">
                                <StatusBadge status={legStatus} />
                              </td>
                              <td className="px-1.5 py-[2px] text-left font-mono text-slate-500 text-[9px]">
                                {leg.filled_at
                                  ? new Date(leg.filled_at).toLocaleString()
                                  : "--"}
                              </td>
                              <td className="px-1.5 py-[2px] text-right font-mono text-slate-400 text-[9px]">
                                {legFilledPx ? fmtM(legFilledPx) : "--"}
                              </td>
                              <td className="px-1.5 py-[2px] text-left text-[8px] text-yellow-400">
                                {legLabel2}
                              </td>
                              <td className="px-1.5 py-[2px] text-center">
                                <button
                                  onClick={() => handleCancelOrder(leg.id)}
                                  className="px-1.5 py-0.5 bg-[#131A2B] border border-[#1E293B] rounded text-[8px] text-red-400 hover:bg-red-500/20 transition-colors"
                                  title="Cancel leg"
                                >
                                  Cancel
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                    </React.Fragment>
                  );
                })}
                {filteredOrders.length === 0 && !ordLoading && (
                  <tr>
                    <td
                      colSpan={ordColumns.length}
                      className="px-4 py-6 text-center text-slate-500 text-xs"
                    >
                      No active orders.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════
          FOOTER
          ═══════════════════════════════════════════════════ */}
      <div className="flex items-center px-4 py-1 bg-[#0D1525] border-t border-[#1E293B] flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[10px] text-slate-400 font-mono">
            {agentCount} Agents OK
          </span>
        </div>
        <div className="ml-auto flex items-center gap-4">
          <span className="text-[10px] text-slate-500 font-mono">
            Positions: {positions.length}
          </span>
          <span className="text-[10px] text-slate-500 font-mono">
            Orders: {orders.length}
          </span>
        </div>
      </div>
    </div>
  );
}
