/**
 * Active Trades Page - Matches mockup: Active-Trades.png (v3)
 * Layout: KPI top bar, Positions table, Orders table, Footer
 * Real Alpaca API via useApi hooks
 */
import React, { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import log from "@/utils/logger";
import {
  Settings,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  X,
  Edit3,
  TrendingUp,
  TrendingDown,
  Minus,
  Download,
} from "lucide-react";
import { useApi } from "../hooks/useApi";
import useTradeExecution from "../hooks/useTradeExecution";
import { getApiUrl, getAuthHeaders } from "../config/api";
import tradeExecutionService from "../services/tradeExecutionService";

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

// Colorblind P/L direction icons (Aurora theme)
function PnLIcon({ value }) {
  if (value == null || isNaN(value)) return <span className="text-slate-500">─</span>;
  if (value > 0) return <TrendingUp className="inline w-3 h-3 text-emerald-400" aria-hidden />;
  if (value < 0) return <TrendingDown className="inline w-3 h-3 text-red-400" aria-hidden />;
  return <Minus className="inline w-3 h-3 text-slate-500" aria-hidden />;
}

// ── Mini Sparkline: real data only; scale [min,max]; null/empty → flat gray line ──
function MiniSparkline({ data, width = 56, height = 18, color }) {
  const pts = useMemo(() => {
    if (Array.isArray(data) && data.length >= 1) return data.map((v) => Number(v)).filter((n) => !isNaN(n));
    return null;
  }, [data]);

  if (pts == null || pts.length === 0) {
    return (
      <svg width={width} height={height} className="inline-block align-middle" aria-hidden>
        <line x1={0} y1={height / 2} x2={width} y2={height / 2} stroke="#64748b" strokeWidth={1} />
      </svg>
    );
  }

  const min = Math.min(...pts);
  const max = Math.max(...pts);
  const range = max - min || 1;
  const barW = width / pts.length;
  const baseColor = color || "#34d399";

  return (
    <svg width={width} height={height} className="inline-block align-middle" aria-hidden>
      {pts.map((v, i) => {
        const norm = (v - min) / range;
        const barH = Math.max(0, (height - 1) * norm);
        return (
          <rect
            key={i}
            x={i * barW}
            y={height - barH}
            width={Math.max(barW - 0.5, 1)}
            height={barH}
            fill={baseColor}
            opacity={0.5 + norm * 0.5}
          />
        );
      })}
    </svg>
  );
}

// ── Adjust modal inner (stop-loss / take-profit) ──
function AdjustModalContent({ initialStopLoss, initialTakeProfit, onSave, onCancel }) {
  const [stopLoss, setStopLoss] = useState(initialStopLoss ?? "");
  const [takeProfit, setTakeProfit] = useState(initialTakeProfit ?? "");
  return (
    <>
      <div className="space-y-2 mb-3">
        <label className="block text-[10px] text-slate-400 uppercase">Stop loss</label>
        <input
          type="number"
          step="0.01"
          value={stopLoss}
          onChange={(e) => setStopLoss(e.target.value)}
          className="w-full px-2 py-1 bg-[#0f1729] border border-slate-600 rounded text-xs text-white font-mono"
          placeholder="e.g. 100.50"
        />
        <label className="block text-[10px] text-slate-400 uppercase">Take profit</label>
        <input
          type="number"
          step="0.01"
          value={takeProfit}
          onChange={(e) => setTakeProfit(e.target.value)}
          className="w-full px-2 py-1 bg-[#0f1729] border border-slate-600 rounded text-xs text-white font-mono"
          placeholder="e.g. 105.00"
        />
      </div>
      <div className="flex justify-end gap-2">
        <button onClick={onCancel} className="px-3 py-1.5 rounded text-xs text-slate-300 hover:bg-slate-700/50">Cancel</button>
        <button onClick={() => onSave(stopLoss, takeProfit)} className="px-3 py-1.5 rounded text-xs font-semibold bg-cyan-500/20 text-[#00D9FF] hover:bg-cyan-500/30">Save</button>
      </div>
    </>
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
  if (s === "new" || s === "accepted" || s === "working") bg = "bg-cyan-500/20 text-[#00D9FF]";
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
  if (t === "bracket") bg = "bg-cyan-500/20 text-[#00D9FF]";
  if (t === "stop_limit") bg = "bg-amber-500/20 text-amber-400";
  return (
    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${bg}`}>
      {type || "--"}
    </span>
  );
}

const TAB_POSITIONS = "positions";
const TAB_ORDERS = "orders";
const TAB_HISTORY = "history";

export default function Trades() {
  const navigate = useNavigate();
  // ── State ──
  const [activeTab, setActiveTab] = useState(TAB_POSITIONS);
  const [posFilter, setPosFilter] = useState("");
  const [ordFilter, setOrdFilter] = useState("");
  const [posSortKey, setPosSortKey] = useState(null);
  const [posSortDir, setPosSortDir] = useState("asc");
  const [ordSortKey, setOrdSortKey] = useState("created_at");
  const [ordSortDir, setOrdSortDir] = useState("desc");
  const [rebalanceTime, setRebalanceTime] = useState("25m");
  const [expandedPositionKey, setExpandedPositionKey] = useState(null);
  const [adjustModal, setAdjustModal] = useState(null);
  const [flattenConfirmOpen, setFlattenConfirmOpen] = useState(false);
  const [flattenLoading, setFlattenLoading] = useState(false);

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

  const { closePosition: closePositionViaExecution, adjustPosition: adjustPositionViaExecution } = useTradeExecution();

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

  // Account metrics — use Number() to handle string values from Alpaca API.
  // Prefer portfolio endpoint (always returns numeric totalEquity) over raw account.
  const nav = Number(portfolioData?.totalEquity) || Number(accountData?.equity) || Number(accountData?.portfolio_value) || 0;
  const dayPnl = Number(portfolioData?.dayPnL) || Number(accountData?.profit_loss) || 0;
  const buyingPower = Number(accountData?.buying_power) || Number(accountData?.daytrading_buying_power) || 0;

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

  // History: filled/canceled orders (same API, filtered by symbol when ordFilter set)
  const historyOrders = useMemo(() => {
    const statuses = ["filled", "canceled", "cancelled", "expired", "replaced"];
    let list = orders.filter((o) => statuses.includes((o.status || "").toLowerCase()));
    if (ordFilter.trim()) {
      const up = ordFilter.toUpperCase();
      list = list.filter((o) => (o.symbol || "").toUpperCase().includes(up));
    }
    return list.sort((a, b) => {
      const tA = new Date(a.filled_at || a.updated_at || a.created_at || 0).getTime();
      const tB = new Date(b.filled_at || b.updated_at || b.created_at || 0).getTime();
      return tB - tA;
    });
  }, [orders, ordFilter]);

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

  const handleClosePosition = async (symbol, side) => {
    try {
      await closePositionViaExecution(symbol, side || "long");
      toast.success(`Closing ${symbol}`);
      refetchPositions();
    } catch (e) {
      log.error("Close position failed:", e);
      toast.error(`Close ${symbol} failed: ${e?.message || "Unknown error"}`);
    }
  };

  const handleFlattenAll = async () => {
    setFlattenLoading(true);
    try {
      await tradeExecutionService.emergencyStop();
      toast.success("Flatten all positions sent.");
      refetchPositions();
      refetchOrders();
      setFlattenConfirmOpen(false);
    } catch (e) {
      log.error("Emergency stop failed:", e);
      toast.error(`Flatten failed: ${e?.message || "Unknown error"}`);
    } finally {
      setFlattenLoading(false);
    }
  };

  const handleDownloadCsv = () => {
    const rows = [];
    if (activeTab === TAB_POSITIONS) {
      rows.push(["Symbol", "Side", "Qty", "Avg Price", "Current Price", "Unrealized P&L", "Day P&L $", "Day P&L %"]);
      filteredPositions.forEach((p) => {
        const qty = Math.abs(Number(p.qty || p.quantity || 0));
        const avg = Number(p.avg_entry_price || p.entryPrice || 0);
        const cur = Number(p.current_price || p.currentPrice || 0);
        const upl = Number(p.unrealized_pl || p.unrealizedPnL || 0);
        const dayPnl = Number(p.unrealized_intraday_pl || p.dayPnl || 0);
        const dayPct = avg ? ((cur - avg) / avg) * 100 : 0;
        rows.push([p.symbol || p.ticker, p.side || "long", qty, avg, cur, upl, dayPnl, dayPct.toFixed(2)]);
      });
    } else if (activeTab === TAB_ORDERS || activeTab === TAB_HISTORY) {
      const list = activeTab === TAB_HISTORY ? historyOrders : filteredOrders;
      rows.push(["Order ID", "Date", "Symbol", "Side", "Type", "Qty", "Status", "Limit", "Stop"]);
      list.forEach((o) => {
        const created = o.created_at || o.submitted_at || "";
        rows.push([
          o.id || o.order_id || "",
          created ? new Date(created).toLocaleString() : "",
          o.symbol || "",
          o.side || "",
          o.order_type || o.type || "",
          o.qty || o.quantity || "",
          o.status || "",
          o.limit_price ?? "",
          o.stop_price ?? "",
        ]);
      });
    }
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `trades-${activeTab}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("CSV downloaded.");
  };

  const handleAdjustSubmit = async (stopLoss, takeProfit) => {
    if (!adjustModal) return;
    try {
      await adjustPositionViaExecution(adjustModal.symbol, adjustModal.side, {
        stop_loss: stopLoss,
        take_profit: takeProfit,
      });
      toast.success(`Adjust sent for ${adjustModal.symbol}`);
      setAdjustModal(null);
      refetchPositions();
    } catch (e) {
      log.error("Adjust failed:", e);
      toast.error(`Adjust failed: ${e?.message || "Unknown error"}`);
    }
  };

  const handleCancelOrder = async (orderId) => {
    try {
      const res = await fetch(getApiUrl("orders") + `/${encodeURIComponent(orderId)}`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail?.message ?? err?.detail ?? res.statusText ?? `HTTP ${res.status}`);
      }
      toast.success("Order cancelled");
      refetchOrders();
    } catch (e) {
      log.error("Cancel order failed:", e);
      toast.error(`Cancel failed: ${e?.message || "Unknown error"}`);
    }
  };

  const handleCancelAll = async () => {
    if (!window.confirm("Cancel ALL open orders?")) return;
    try {
      const res = await fetch(getApiUrl("orders"), {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error(res.statusText || `HTTP ${res.status}`);
      toast.success("All orders cancelled");
      refetchOrders();
    } catch (e) {
      toast.error(`Cancel all failed: ${e?.message || "Unknown error"}`);
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
    { key: "gamma", label: "Gamma", align: "right" },
    { key: "vega", label: "Vega", align: "right" },
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
    <div className="flex flex-col h-full min-h-0 bg-[#0B0E14]">
      {/* ═══════════════════════════════════════════════════
          TOP KPI BAR - matches mockup header strip
          NAV | DAILY P&L | MARGIN AVAIL | BUYING POWER | REGIME | TREND | REBALANCED
          ═══════════════════════════════════════════════════ */}
      <div className="flex items-center gap-5 px-4 py-1.5 bg-[#111827] border-b border-[rgba(42,52,68,0.5)] flex-shrink-0">
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

        {/* TREND - combined with regime */}
        <div className="flex items-baseline gap-1.5">
          <span className={`text-[11px] font-bold font-mono uppercase px-2 py-0.5 rounded border ${
            regime?.toLowerCase().includes("bull") 
              ? "text-emerald-400 border-emerald-500/40 bg-emerald-500/10" 
              : regime?.toLowerCase().includes("bear") 
              ? "text-red-400 border-red-500/40 bg-red-500/10"
              : "text-amber-400 border-amber-500/40 bg-amber-500/10"
          }`}>
            {regime}_{trend}
          </span>
        </div>

        <span className="text-slate-600">|</span>

        {/* WS LATENCY — no fallback; show — when null */}
        <div className="flex items-baseline gap-1.5">
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">
            WS_LATENCY:
          </span>
          <span className="text-[13px] font-bold text-[#00D9FF] font-mono">
            {systemData?.ws_latency_ms != null || systemData?.latency != null
              ? `${systemData?.ws_latency_ms ?? systemData?.latency}ms`
              : "—"}
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
            className="px-2 py-0.5 bg-[#131A2B] border border-[rgba(42,52,68,0.5)] rounded text-[11px] text-white font-mono outline-none focus:border-[#00D9FF]/50"
          >
            <option value="5m">5m</option>
            <option value="15m">15m</option>
            <option value="25m">25m</option>
            <option value="1h">1h</option>
            <option value="4h">4h</option>
          </select>
          <button
            onClick={handleRefresh}
            className="p-1 text-slate-400 hover:text-[#00D9FF] transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════
          MAIN CONTENT: Tabs (Positions | Orders | History) + tables
          ═══════════════════════════════════════════════════ */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* Tab bar + Flatten All + Download CSV */}
        <div className="flex items-center justify-between px-3 py-1.5 bg-[#111827] border-b border-cyan-900/30 flex-shrink-0">
          <div className="flex items-center gap-4">
            <div className="flex rounded border border-slate-600/50 overflow-hidden">
              {[TAB_POSITIONS, TAB_ORDERS, TAB_HISTORY].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1 text-[10px] font-semibold uppercase tracking-wide transition-colors ${
                    activeTab === tab
                      ? "bg-cyan-500/20 text-[#00D9FF] border-b border-[#00D9FF]"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/30"
                  }`}
                >
                  {tab === TAB_POSITIONS ? "Positions" : tab === TAB_ORDERS ? "Orders" : "History"}
                </button>
              ))}
            </div>
            {activeTab === TAB_POSITIONS && (
              <>
                <input
                  type="text"
                  placeholder="Filter symbol..."
                  value={posFilter}
                  onChange={(e) => setPosFilter(e.target.value)}
                  className="px-2 py-0.5 bg-[#131A2B] border border-[rgba(42,52,68,0.5)] rounded text-[10px] text-slate-300 font-mono w-28 outline-none focus:border-[#00D9FF]/50"
                />
                <button
                  onClick={() => setFlattenConfirmOpen(true)}
                  className="px-2 py-1 bg-red-500/20 border border-red-500/40 rounded text-[10px] font-semibold text-red-400 hover:bg-red-500/30 transition-colors"
                >
                  Flatten All Positions
                </button>
              </>
            )}
            {(activeTab === TAB_ORDERS || activeTab === TAB_HISTORY) && (
              <input
                type="text"
                placeholder="Filter symbol..."
                value={ordFilter}
                onChange={(e) => setOrdFilter(e.target.value)}
                className="px-2 py-0.5 bg-[#131A2B] border border-[rgba(42,52,68,0.5)] rounded text-[10px] text-slate-300 font-mono w-28 outline-none focus:border-[#00D9FF]/50"
              />
            )}
          </div>
          <button
            onClick={handleDownloadCsv}
            className="flex items-center gap-1 px-2 py-1 bg-[#131A2B] border border-cyan-900/50 rounded text-[10px] text-[#00D9FF] hover:bg-cyan-500/10 transition-colors"
          >
            <Download className="w-3 h-3" />
            Download CSV
          </button>
        </div>

        {/* ── POSITIONS TABLE ── */}
        <div className={`flex flex-col min-h-0 overflow-hidden ${activeTab !== TAB_POSITIONS ? "hidden" : "flex-[3]"}`}>

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
                      className={`sticky top-0 bg-[#0f1729] px-1.5 py-1 text-[8px] font-semibold uppercase tracking-wider border-b border-cyan-900/30 z-10 cursor-pointer select-none hover:text-[#00D9FF] transition-colors ${
                        col.align === "left"
                          ? "text-left"
                          : col.align === "center"
                          ? "text-center"
                          : "text-right"
                      } ${
                        posSortKey === col.key
                          ? "text-[#00D9FF]"
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
                      className="px-4 py-8 text-center text-[#00D9FF] text-xs animate-pulse"
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
                  const gamma = p.gamma ?? "--";
                  const vega = p.vega ?? "--";
                  const beta = p.beta ?? "--";
                  const dailyRangeVol = p.daily_range_vol || p.dailyRangeVol || "--";

                  // Sparkline data — real API only; null → flat line in MiniSparkline
                  const sparkData = p.sparkline || p.price_history || null;
                  const rowKey = `${sym}-${side}-${i}`;
                  const isExpanded = expandedPositionKey === rowKey;

                  return (
                    <React.Fragment key={rowKey}>
                    <tr
                      onClick={() => setExpandedPositionKey((k) => (k === rowKey ? null : rowKey))}
                      className="hover:bg-[#1E293B]/50 transition-colors border-b border-[rgba(42,52,68,0.5)]/30 cursor-pointer"
                    >
                      {/* Symbol */}
                      <td className="px-1.5 py-[3px] text-left" onClick={(e) => e.stopPropagation()}>
                        <button
                          type="button"
                          onClick={() => sym !== "--" && navigate(`/symbol/${encodeURIComponent(sym)}`)}
                          className="font-bold text-white font-mono text-[10px] hover:text-cyan-400 underline cursor-pointer"
                        >
                          {sym}
                        </button>
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
                        <span className="inline-flex items-center gap-0.5">
                          <PnLIcon value={dayPnlPctVal} />
                          {dayPnlPctVal !== 0 ? fmtPct(dayPnlPctVal) : "—"}
                        </span>
                      </td>
                      {/* Day P&L ($) */}
                      <td className={`px-1.5 py-[3px] text-right font-mono font-semibold ${clr(dayPnlDollar)}`}>
                        <span className="inline-flex items-center gap-0.5">
                          <PnLIcon value={dayPnlDollar} />
                          {dayPnlDollar !== 0 ? fmtPnl(dayPnlDollar) : "—"}
                        </span>
                      </td>
                      {/* Unrealized P&L */}
                      <td className={`px-1.5 py-[3px] text-right font-mono font-bold ${clr(unrealPnl)}`}>
                        <span className="inline-flex items-center gap-0.5">
                          <PnLIcon value={unrealPnl} />
                          {fmtPnl(unrealPnl)}
                        </span>
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
                      {/* Gamma */}
                      <td className="px-1.5 py-[3px] text-right font-mono text-slate-500 text-[9px]">
                        {gamma}
                      </td>
                      {/* Vega */}
                      <td className="px-1.5 py-[3px] text-right font-mono text-slate-500 text-[9px]">
                        {vega}
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
                      <td className="px-1.5 py-[3px] text-center" onClick={(e) => e.stopPropagation()}>
                        <div className="inline-flex items-center gap-0.5">
                          <button
                            onClick={() => handleClosePosition(sym, side)}
                            className="p-0.5 text-slate-500 hover:text-red-400 transition-colors"
                            title="Close position"
                          >
                            <X className="w-3 h-3" />
                          </button>
                          <button
                            onClick={() => setAdjustModal({ symbol: sym, side, stopLoss: p.stop_loss ?? "", takeProfit: p.take_profit ?? "" })}
                            className="p-0.5 text-slate-500 hover:text-[#00D9FF] transition-colors"
                            title="Adjust stop-loss / take-profit"
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
                    {isExpanded && (
                      <tr className="bg-[#0f1729]/80 border-b border-cyan-900/20">
                        <td colSpan={posColumns.length} className="px-3 py-2 text-[10px]">
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-1 text-slate-300">
                            <span>Entry: {fmtM(avgPrice)}</span>
                            <span>Current: {fmtM(mktPrice)}</span>
                            <span>Stop: {p.stop_loss != null ? fmtM(p.stop_loss) : "—"}</span>
                            <span>Take-profit: {p.take_profit != null ? fmtM(p.take_profit) : "—"}</span>
                            <span className="col-span-2">Council decision: {p.council_decision_id || "—"}</span>
                          </div>
                          <div className="mt-1.5 flex items-center gap-2">
                            <span className="text-slate-500">P&L since entry:</span>
                            <MiniSparkline
                              data={sparkData}
                              width={120}
                              height={24}
                              color={unrealPnl >= 0 ? "#34d399" : "#f87171"}
                            />
                          </div>
                        </td>
                      </tr>
                    )}
                    </React.Fragment>
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

        {/* ── ORDERS / HISTORY TABLE ── */}
        <div className={`flex flex-col min-h-0 overflow-hidden border-t border-cyan-900/30 ${activeTab !== TAB_ORDERS && activeTab !== TAB_HISTORY ? "hidden" : "flex-[2]"}`}>
          {activeTab === TAB_ORDERS && (
            <div className="flex items-center justify-end gap-2 px-3 py-1 bg-[#111827] border-b border-cyan-900/30 flex-shrink-0">
              <button
                onClick={handleCancelAll}
                className="px-2 py-0.5 bg-[#131A2B] border border-red-500/30 rounded text-[9px] text-red-400 hover:bg-red-500/10 transition-colors"
              >
                Cancel All
              </button>
            </div>
          )}

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
                      className={`sticky top-0 bg-[#0f1729] px-1.5 py-1 text-[8px] font-semibold uppercase tracking-wider border-b border-cyan-900/30 z-10 cursor-pointer select-none hover:text-[#00D9FF] transition-colors ${
                        col.align === "left"
                          ? "text-left"
                          : col.align === "center"
                          ? "text-center"
                          : "text-right"
                      } ${
                        ordSortKey === col.key
                          ? "text-[#00D9FF]"
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
                      className="px-4 py-6 text-center text-[#00D9FF] text-xs animate-pulse"
                    >
                      Loading orders...
                    </td>
                  </tr>
                )}
                {(activeTab === TAB_HISTORY ? historyOrders : filteredOrders).map((o, i) => {
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
                        className={`hover:bg-[#1E293B]/50 transition-colors border-b border-[rgba(42,52,68,0.5)]/30 ${rowBg}`}
                      >
                        {/* Order ID */}
                        <td className="px-1.5 py-[3px] text-left font-mono text-[#00D9FF] text-[9px]">
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
                            <span className="text-[#00D9FF]">{legLabel}</span>
                          ) : (
                            "--"
                          )}
                        </td>
                        {/* Actions */}
                        <td className="px-1.5 py-[3px] text-center">
                          <div className="inline-flex items-center gap-1">
                            <button
                              onClick={() => handleCancelOrder(orderId)}
                              className="px-1.5 py-0.5 bg-[#131A2B] border border-[rgba(42,52,68,0.5)] rounded text-[8px] text-red-400 hover:bg-red-500/20 transition-colors"
                              title="Cancel order"
                            >
                              Cancel
                            </button>
                            <button
                              className="px-1.5 py-0.5 bg-[#131A2B] border border-[rgba(42,52,68,0.5)] rounded text-[8px] text-slate-400 hover:bg-slate-600/20 transition-colors"
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
                              className="bg-[#111827]/80 border-b border-[rgba(42,52,68,0.5)]/20 hover:bg-[#1E293B]/30 transition-colors"
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
                                  className="px-1.5 py-0.5 bg-[#131A2B] border border-[rgba(42,52,68,0.5)] rounded text-[8px] text-red-400 hover:bg-red-500/20 transition-colors"
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
                {((activeTab === TAB_HISTORY ? historyOrders : filteredOrders).length === 0) && !ordLoading && (
                  <tr>
                    <td
                      colSpan={ordColumns.length}
                      className="px-4 py-6 text-center text-slate-500 text-xs"
                    >
                      {activeTab === TAB_HISTORY ? "No history yet." : "No active orders."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Adjust (stop-loss / take-profit) modal */}
      {adjustModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setAdjustModal(null)}>
          <div className="bg-[#111827] border border-cyan-900/50 rounded-lg p-4 w-[320px] shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-semibold text-white mb-3">Adjust: {adjustModal.symbol}</h3>
            <AdjustModalContent
              initialStopLoss={adjustModal.stopLoss}
              initialTakeProfit={adjustModal.takeProfit}
              onSave={(stopLoss, takeProfit) => handleAdjustSubmit(stopLoss, takeProfit)}
              onCancel={() => setAdjustModal(null)}
            />
          </div>
        </div>
      )}

      {/* Flatten All confirmation */}
      {flattenConfirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => !flattenLoading && setFlattenConfirmOpen(false)}>
          <div className="bg-[#111827] border border-red-500/40 rounded-lg p-4 w-[340px] shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-semibold text-red-400 mb-2">Flatten All Positions</h3>
            <p className="text-xs text-slate-400 mb-4">This will submit an emergency stop and close all open positions. Continue?</p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => !flattenLoading && setFlattenConfirmOpen(false)}
                className="px-3 py-1.5 rounded text-xs text-slate-300 hover:bg-slate-700/50"
              >
                Cancel
              </button>
              <button
                onClick={handleFlattenAll}
                disabled={flattenLoading}
                className="px-3 py-1.5 rounded text-xs font-semibold bg-red-500/20 text-red-400 hover:bg-red-500/30 disabled:opacity-50"
              >
                {flattenLoading ? "Sending…" : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════
          FOOTER
          ═══════════════════════════════════════════════════ */}
      <div className="flex items-center px-4 py-1 bg-[#111827] border-t border-[rgba(42,52,68,0.5)] flex-shrink-0">
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
