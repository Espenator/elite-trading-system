import React, { useState, useCallback, useEffect, useMemo } from "react";
import {
  ShieldAlert, Target, CheckCircle2, XCircle, Activity, Send,
  RefreshCw, Zap, TrendingUp, TrendingDown, AlertTriangle,
  Clock, DollarSign, BarChart3, Layers, Settings2, X,
  ChevronDown, ChevronUp, Keyboard, Radio, Gauge,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";

// ── Constants ──────────────────────────────────────────────────────────
const ORDER_CLASSES = ["simple", "bracket", "oco", "oto"];
const ORDER_TYPES = ["market", "limit", "stop", "stop_limit", "trailing_stop"];
const TIF_OPTIONS = ["day", "gtc", "opg", "cls", "ioc", "fok"];
const SIDES = ["buy", "sell"];

const STATUS_COLORS = {
  new: "text-cyan-400", accepted: "text-cyan-400", pending_new: "text-amber-400",
  partially_filled: "text-amber-400", filled: "text-emerald-400",
  canceled: "text-slate-500", expired: "text-slate-500",
  rejected: "text-red-400", replaced: "text-purple-400",
  held: "text-slate-500",
};

const BADGE_COLORS = {
  filled: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  partially_filled: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  rejected: "bg-red-500/15 text-red-400 border-red-500/30",
  canceled: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  replaced: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
  new: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
  accepted: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
  pending_new: "bg-amber-500/15 text-amber-400 border-amber-500/30",
};

// ── Helper: Small reusable components ───────────────────────────────────────
const Badge = ({ status }) => {
  const colors = BADGE_COLORS[status] || "bg-slate-700/50 text-slate-400 border-slate-600/50";
  return (
    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase border ${colors}`}>
      {(status || "unknown").replace(/_/g, " ")}
    </span>
  );
};

const DataRow = ({ label, value, valueClass = "text-white" }) => (
  <div className="flex justify-between items-center py-0.5">
    <span className="text-[10px] text-slate-500">{label}</span>
    <span className={`text-[10px] font-mono font-semibold ${valueClass}`}>{value}</span>
  </div>
);

const MeterBar = ({ pct, color = "bg-cyan-500" }) => (
  <div className="w-16 h-1 bg-slate-700 rounded-full overflow-hidden inline-block ml-1 align-middle">
    <div className={`h-full ${color} rounded-full`} style={{ width: `${Math.min(pct, 100)}%` }} />
  </div>
);

const SelectField = ({ label, value, onChange, options, small }) => (
  <div className="flex flex-col gap-0.5">
    {label && <label className="text-[9px] text-slate-500 uppercase">{label}</label>}
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`bg-slate-800/80 border border-slate-700/50 rounded text-white font-mono outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 ${
        small ? "px-1.5 py-0.5 text-[9px]" : "px-2 py-1 text-[10px]"
      }`}
    >
      {options.map((opt) => (
        <option key={typeof opt === "string" ? opt : opt.value} value={typeof opt === "string" ? opt : opt.value}>
          {typeof opt === "string" ? opt.toUpperCase() : opt.label}
        </option>
      ))}
    </select>
  </div>
);

const InputField = ({ label, value, onChange, placeholder, disabled, className = "", type = "text" }) => (
  <div className="flex flex-col gap-0.5">
    {label && <label className="text-[9px] text-slate-500 uppercase">{label}</label>}
    <input
      type={type}
      value={value}
      onChange={(e) => onChange?.(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      className={`bg-slate-800/80 border border-slate-700/50 rounded px-2 py-1 text-[10px] text-white font-mono outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 disabled:opacity-40 disabled:cursor-not-allowed ${className}`}
    />
  </div>
);

// ── Main Component ────────────────────────────────────────────────────────
export default function TradeExecution() {
  // ── Real API hooks (no mock data) ───────────────────────────────────
  const { data: accountData, refetch: refetchAccount } = useApi("alpaca/account", { pollIntervalMs: 5000 });
  const { data: positionsData } = useApi("alpaca/positions", { pollIntervalMs: 5000 });
  const { data: ordersData, refetch: refetchOrders } = useApi("alpaca/orders?status=open&limit=50", { pollIntervalMs: 3000 });
  const { data: activitiesData, refetch: refetchActivities } = useApi("alpaca/activities?limit=30", { pollIntervalMs: 10000 });
  const { data: signalData } = useApi("signals", { pollIntervalMs: 5000 });
  const { data: riskData } = useApi("risk", { pollIntervalMs: 10000 });
  const { data: portfolioData } = useApi("portfolio", { pollIntervalMs: 10000 });
  const { data: settingsData } = useApi("settings", { pollIntervalMs: 60000 });

  // ── Derived account data ──────────────────────────────────────────
  const equity = parseFloat(accountData?.equity || 0);
  const buyingPower = parseFloat(accountData?.buying_power || 0);
  const marginUsed = parseFloat(accountData?.initial_margin || 0);
  const marginPct = equity > 0 ? ((marginUsed / equity) * 100) : 0;
  const regimeRisk = riskData?.regimeRisk || 0.02;
  const regimeState = riskData?.regime || "UNKNOWN";

  // ── Quick Exec state ──────────────────────────────────────────────
  const [quickSymbol, setQuickSymbol] = useState("NVDA");
  const [quickQty, setQuickQty] = useState("100");
  const [quickMode, setQuickMode] = useState("shares"); // shares | notional
  const [extendedHours, setExtendedHours] = useState(false);
  const [circuitBreaker, setCircuitBreaker] = useState(true);

  // ── Advanced Order Builder state ───────────────────────────────────
  const [orderClass, setOrderClass] = useState("bracket");
  const [orderType, setOrderType] = useState("limit");
  const [orderSide, setOrderSide] = useState("buy");
  const [tif, setTif] = useState("day");
  const [sizeMode, setSizeMode] = useState("shares"); // shares | notional
  const [qty, setQty] = useState("150");
  const [limitPrice, setLimitPrice] = useState("");
  const [stopPrice, setStopPrice] = useState("");
  const [clientOrderId, setClientOrderId] = useState("");
  const [extHoursOrder, setExtHoursOrder] = useState(false);

  // Bracket legs
  const [tpLimitPrice, setTpLimitPrice] = useState("");
  const [slStopPrice, setSlStopPrice] = useState("");
  const [slLimitPrice, setSlLimitPrice] = useState("");

  // Trailing stop
  const [trailType, setTrailType] = useState("percent"); // percent | price
  const [trailValue, setTrailValue] = useState("1.5");

  // Pre-flight checklist
  const [checklist, setChecklist] = useState({
    entryPx: false, stopValid: false, kellyOpt: false,
    regimeAlign: false, heatLimit: false, mentalClear: false,
  });
  const allChecked = Object.values(checklist).every(Boolean);

  // Execution state
  const [executing, setExecuting] = useState(false);
  const [orderResult, setOrderResult] = useState(null);
  const [orderError, setOrderError] = useState(null);

  // ── Position for selected symbol ───────────────────────────────────
  const positions = Array.isArray(positionsData) ? positionsData : [];
  const currentPosition = useMemo(() => {
    const sym = quickSymbol.toUpperCase();
    return positions.find((p) => (p.symbol || "").toUpperCase() === sym) || null;
  }, [positions, quickSymbol]);

  const posShares = parseFloat(currentPosition?.qty || 0);
  const posAvgCost = parseFloat(currentPosition?.avg_entry_price || 0);
  const posCurrPrice = parseFloat(currentPosition?.current_price || 0);
  const posUnrealizedPL = parseFloat(currentPosition?.unrealized_pl || 0);
  const posUnrealizedPct = parseFloat(currentPosition?.unrealized_plpc || 0) * 100;

  // ── Kelly criterion from signals ───────────────────────────────────
  const signals = Array.isArray(signalData) ? signalData : signalData?.signals || [];
  const activeSignal = signals.find(
    (s) => (s.ticker || s.symbol || "").toUpperCase() === quickSymbol.toUpperCase()
  );
  const kellyEdge = activeSignal?.kelly_edge || activeSignal?.edge || 0;
  const signalQuality = activeSignal?.signal_quality || activeSignal?.quality || 0;
  const kellyOptimalShares = useMemo(() => {
    if (!kellyEdge || !equity) return 0;
    const dollarRisk = equity * regimeRisk;
    const entryPx = parseFloat(limitPrice) || posCurrPrice || 0;
    const slPx = parseFloat(slStopPrice) || 0;
    const stopDist = entryPx && slPx ? Math.abs(entryPx - slPx) : 0;
    return stopDist > 0 ? Math.floor(dollarRisk / stopDist) : 0;
  }, [kellyEdge, equity, regimeRisk, limitPrice, slStopPrice, posCurrPrice]);

  // ── Estimated calculations ────────────────────────────────────────
  const entryPx = parseFloat(limitPrice) || 0;
  const numQty = parseInt(qty) || 0;
  const estCapital = entryPx * numQty;
  const estMarginImpact = estCapital * 0.25; // Reg T 25%
  const tpPx = parseFloat(tpLimitPrice) || 0;
  const slPx = parseFloat(slStopPrice) || 0;
  const estProfit = tpPx && entryPx ? (tpPx - entryPx) * numQty * (orderSide === "buy" ? 1 : -1) : 0;
  const estRisk = slPx && entryPx ? Math.abs(entryPx - slPx) * numQty : 0;
  const rrRatio = estRisk > 0 ? (Math.abs(estProfit) / estRisk).toFixed(1) : "--";
  const postAlloc = equity > 0 ? ((estCapital / equity) * 100).toFixed(1) : "0";

  // ── Portfolio heat ─────────────────────────────────────────────────
  const totalPositionValue = positions.reduce((acc, p) => acc + Math.abs(parseFloat(p.market_value || 0)), 0);
  const portfolioHeat = equity > 0 ? ((totalPositionValue / equity) * 100).toFixed(0) : 0;

  // ── Working orders + activities from Alpaca ─────────────────────
  const workingOrders = Array.isArray(ordersData) ? ordersData : [];
  const activities = Array.isArray(activitiesData) ? activitiesData : [];

  // ── Keyboard shortcuts ───────────────────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      if (e.shiftKey && e.key === "B") { e.preventDefault(); handleQuickOrder("buy"); }
      if (e.shiftKey && e.key === "S") { e.preventDefault(); handleQuickOrder("sell"); }
      if (e.key === "Escape") { handleCancelAll(); }
      if (e.ctrlKey && e.key === "Enter") { e.preventDefault(); handleAdvancedOrder(); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  });

  // ── Quick market order (top bar) ─────────────────────────────────
  const handleQuickOrder = useCallback(async (side) => {
    if (!quickSymbol) return;
    try {
      const body = {
        symbol: quickSymbol.toUpperCase(),
        type: "market",
        side,
        time_in_force: "day",
        extended_hours: extendedHours,
      };
      if (quickMode === "notional") {
        body.notional = quickQty;
      } else {
        body.qty = quickQty;
      }
      await fetch(getApiUrl("orders/advanced"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      refetchOrders(); refetchActivities(); refetchAccount();
    } catch (err) { console.error("Quick order failed:", err); }
  }, [quickSymbol, quickQty, quickMode, extendedHours]);

  // ── Cancel all orders ────────────────────────────────────────────
  const handleCancelAll = useCallback(async () => {
    try {
      await fetch(getApiUrl("orders"), { method: "DELETE" });
      refetchOrders(); refetchActivities();
    } catch (err) { console.error("Cancel all failed:", err); }
  }, []);

  // ── Cancel single order ──────────────────────────────────────────
  const handleCancelOrder = useCallback(async (orderId) => {
    try {
      await fetch(getApiUrl(`orders/${orderId}`), { method: "DELETE" });
      refetchOrders(); refetchActivities();
    } catch (err) { console.error("Cancel order failed:", err); }
  }, []);

  // ── Replace/modify order (PATCH) ─────────────────────────────────
  const handleReplaceOrder = useCallback(async (orderId, patches) => {
    try {
      await fetch(getApiUrl(`orders/${orderId}`), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patches),
      });
      refetchOrders();
    } catch (err) { console.error("Replace order failed:", err); }
  }, []);

  // ── Advanced order execution ─────────────────────────────────────
  const handleAdvancedOrder = useCallback(async () => {
    if (!allChecked || executing) return;
    setExecuting(true);
    setOrderError(null);
    setOrderResult(null);
    try {
      const body = {
        symbol: quickSymbol.toUpperCase(),
        side: orderSide,
        type: orderType,
        time_in_force: tif,
        extended_hours: extHoursOrder,
        order_class: orderClass === "simple" ? undefined : orderClass,
      };
      // Qty or notional
      if (sizeMode === "notional") { body.notional = qty; }
      else { body.qty = qty; }
      // Prices based on order type
      if (["limit", "stop_limit"].includes(orderType) && limitPrice) body.limit_price = limitPrice;
      if (["stop", "stop_limit"].includes(orderType) && stopPrice) body.stop_price = stopPrice;
      // Trailing stop params
      if (orderType === "trailing_stop") {
        if (trailType === "percent") body.trail_percent = trailValue;
        else body.trail_price = trailValue;
      }
      // Bracket legs
      if (orderClass === "bracket") {
        body.take_profit = { limit_price: tpLimitPrice };
        body.stop_loss = {
          stop_price: slStopPrice,
          limit_price: slLimitPrice || undefined,
        };
      }
      // OCO legs
      if (orderClass === "oco") {
        body.take_profit = { limit_price: tpLimitPrice };
        body.stop_loss = { stop_price: slStopPrice };
      }
      // OTO: secondary order sent as nested
      if (orderClass === "oto") {
        body.take_profit = { limit_price: tpLimitPrice };
      }
      // Client order ID
      if (clientOrderId) body.client_order_id = clientOrderId;

      const resp = await fetch(getApiUrl("orders/advanced"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Order failed");
      setOrderResult(data);
      refetchOrders(); refetchActivities(); refetchAccount();
      // Reset checklist
      setChecklist({ entryPx: false, stopValid: false, kellyOpt: false, regimeAlign: false, heatLimit: false, mentalClear: false });
    } catch (err) {
      setOrderError(err.message);
    } finally {
      setExecuting(false);
    }
  }, [allChecked, executing, quickSymbol, orderSide, orderType, tif, extHoursOrder, orderClass, sizeMode, qty, limitPrice, stopPrice, trailType, trailValue, tpLimitPrice, slStopPrice, slLimitPrice, clientOrderId]);

  // ── Market clock ──────────────────────────────────────────────────
  const [clock, setClock] = useState("");
  useEffect(() => {
    const tick = () => setClock(new Date().toLocaleTimeString("en-US", { hour12: false, timeZone: "America/New_York" }));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  // ── RENDER ────────────────────────────────────────────────────────────
  return (
    <div className="space-y-0 animate-in fade-in duration-500 h-full flex flex-col">
      <PageHeader
        icon={Send}
        title="Trade Execution"
        description="Advanced order execution with full Alpaca v2 API — bracket, OCO, OTO, trailing stops"
      />

      {/* ===== TOP STATUS BAR ===== */}
      <div className="flex items-center justify-between px-4 py-1.5 bg-slate-900/80 border-b border-slate-700/50 text-[9px] font-mono">
        <div className="flex items-center gap-4">
          <span className="text-cyan-400 font-bold">MARKET: {accountData?.status === "ACTIVE" ? "OPEN" : "CLOSED"}</span>
          <span className="text-slate-400">{clock} EST</span>
          <span className={`${accountData?.status === "ACTIVE" ? "text-emerald-400" : "text-red-400"}`}>
            {accountData?.status === "ACTIVE" ? "REGULAR SESSION" : "AFTER HOURS"}
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-slate-400">BUY POWER: <span className="text-white font-bold">${buyingPower.toLocaleString(undefined, {maximumFractionDigits: 0})}</span></span>
          <span className="text-slate-400">MARGIN: <MeterBar pct={marginPct} color={marginPct > 75 ? "bg-red-500" : marginPct > 50 ? "bg-amber-500" : "bg-cyan-500"} /> {marginPct.toFixed(0)}%</span>
          <span className="text-slate-400">CIRCUIT BREAKER:
            <button onClick={() => setCircuitBreaker(!circuitBreaker)} className={`ml-1 px-1.5 py-0.5 rounded text-[8px] font-bold ${circuitBreaker ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}`}>
              {circuitBreaker ? "ON" : "OFF"}
            </button>
          </span>
        </div>
      </div>

      {/* ===== QUICK EXECUTION BAR ===== */}
      <div className="flex items-center gap-3 px-4 py-2 bg-slate-800/60 border-b border-slate-700/50">
        <div className="flex items-center gap-1">
          <label className="text-[9px] text-slate-500 uppercase">SYM</label>
          <input
            type="text"
            value={quickSymbol}
            onChange={(e) => setQuickSymbol(e.target.value.toUpperCase())}
            className="w-16 bg-slate-800/80 border border-slate-700/50 rounded px-2 py-1 text-[11px] text-cyan-400 font-bold font-mono uppercase outline-none focus:border-cyan-500/50"
          />
        </div>
        <div className="flex items-center gap-1">
          <select value={quickMode} onChange={(e) => setQuickMode(e.target.value)} className="bg-slate-800/80 border border-slate-700/50 rounded px-1 py-1 text-[9px] text-white font-mono outline-none">
            <option value="shares">SHR</option>
            <option value="notional">USD</option>
          </select>
          <input
            type="text"
            value={quickQty}
            onChange={(e) => setQuickQty(e.target.value)}
            className="w-16 bg-slate-800/80 border border-slate-700/50 rounded px-2 py-1 text-[10px] text-white font-mono text-right outline-none focus:border-cyan-500/50"
          />
        </div>
        <button onClick={() => handleQuickOrder("buy")} className="px-3 py-1.5 bg-emerald-500 text-black text-[10px] font-bold rounded hover:bg-emerald-400 transition-colors">
          BUY MKT <span className="text-[8px] opacity-60">⇧B</span>
        </button>
        <button onClick={() => handleQuickOrder("sell")} className="px-3 py-1.5 bg-red-500 text-white text-[10px] font-bold rounded hover:bg-red-400 transition-colors">
          SELL MKT <span className="text-[8px] opacity-60">⇧S</span>
        </button>
        <div className="flex-1" />
        <div className="flex items-center gap-1">
          <label className="text-[9px] text-slate-500">EXT HOURS</label>
          <button onClick={() => setExtendedHours(!extendedHours)} className={`px-2 py-0.5 rounded text-[9px] font-bold ${extendedHours ? "bg-emerald-500/20 text-emerald-400" : "bg-slate-700/50 text-slate-500"}`}>
            {extendedHours ? "ON" : "OFF"}
          </button>
        </div>
        <button onClick={handleCancelAll} className="px-3 py-1.5 border border-red-500/50 text-red-400 text-[10px] font-bold rounded hover:bg-red-500/10 transition-colors">
          CANCEL ALL <span className="text-[8px] text-slate-500">ESC</span>
        </button>
      </div>

      {/* ===== MAIN GRID: 12-column layout ===== */}
      <div className="flex-1 overflow-y-auto p-2">
        <div className="grid grid-cols-12 gap-2">

          {/* ===== COL 1: Context & Risk (Span 3) ===== */}
          <div className="col-span-3 bg-slate-800/40 border border-slate-700/50 rounded-lg p-3 space-y-3">
            <div className="text-[11px] font-bold text-cyan-400 uppercase border-b border-slate-700/50 pb-1 flex justify-between">
              <span>Context & Risk</span>
              <span className="text-cyan-300">[{quickSymbol}]</span>
            </div>

            {/* Current Position */}
            <div className="border border-dashed border-slate-700/50 rounded p-2 bg-slate-800/20">
              <div className="text-[9px] text-slate-500 uppercase mb-1">Current Position</div>
              <DataRow label="Shares Held" value={posShares || "--"} valueClass={posShares ? "text-cyan-400" : "text-slate-500"} />
              <DataRow label="Avg Cost" value={posAvgCost ? `$${posAvgCost.toFixed(2)}` : "--"} />
              <DataRow label="Current Px" value={posCurrPrice ? `$${posCurrPrice.toFixed(2)}` : "--"} valueClass={posUnrealizedPL >= 0 ? "text-emerald-400" : "text-red-400"} />
              <DataRow label="Unrealized P&L" value={posUnrealizedPL ? `${posUnrealizedPL >= 0 ? "+" : ""}$${posUnrealizedPL.toFixed(2)} (${posUnrealizedPct.toFixed(1)}%)` : "--"} valueClass={posUnrealizedPL >= 0 ? "text-emerald-400" : "text-red-400"} />
            </div>

            {/* Kelly Criterion */}
            <div className="border border-dashed border-slate-700/50 rounded p-2 bg-slate-800/20">
              <div className="text-[9px] text-slate-500 uppercase mb-1">Kelly Criterion</div>
              <DataRow label="Signal Edge" value={kellyEdge ? `+${(kellyEdge * 100).toFixed(1)}%` : "--"} valueClass="text-cyan-400" />
              <DataRow label="Quality Score" value={signalQuality ? `${signalQuality.toFixed(2)} / 1.0` : "--"} valueClass={signalQuality >= 0.7 ? "text-emerald-400" : "text-amber-400"} />
              <DataRow label="Opt. Size (Shares)" value={kellyOptimalShares || "--"} valueClass="text-cyan-400" />
              <DataRow label="Rec. Allocation" value={equity > 0 && kellyOptimalShares ? `${((kellyOptimalShares * entryPx / equity) * 100).toFixed(1)}%` : "--"} />
            </div>

            {/* Risk Governor */}
            <div>
              <div className="text-[9px] text-slate-500 uppercase mb-1">Risk Governor</div>
              <DataRow label="Max Allowable Size" value={equity > 0 ? `${Math.floor(equity * 0.15 / (entryPx || 1))} sh` : "--"} />
              <DataRow label="Portfolio Heat" value={`${portfolioHeat}% util`} valueClass={portfolioHeat > 80 ? "text-red-400" : portfolioHeat > 60 ? "text-amber-400" : "text-emerald-400"} />
              <DataRow label="Regime State" value={regimeState} valueClass={regimeState.includes("BULL") ? "text-emerald-400" : regimeState.includes("BEAR") ? "text-red-400" : "text-amber-400"} />
              <DataRow label="Risk Per Trade" value={`${(regimeRisk * 100).toFixed(1)}%`} valueClass="text-amber-400" />
            </div>
          </div>

          {/* ===== COL 2: Advanced Order Builder (Span 5) ===== */}
          <div className="col-span-5 bg-slate-800/40 border border-slate-700/50 rounded-lg p-3">
            <div className="text-[11px] font-bold text-cyan-400 uppercase border-b border-slate-700/50 pb-1 flex justify-between">
              <span>Super Advanced Builder</span>
              <span className="text-slate-500">[v2/orders]</span>
            </div>

            {/* Row 1: Class, Type, TIF, Mode, Qty */}
            <div className="grid grid-cols-5 gap-2 mt-2">
              <SelectField label="Class" value={orderClass} onChange={setOrderClass} options={ORDER_CLASSES} />
              <SelectField label="Type" value={orderType} onChange={setOrderType} options={ORDER_TYPES} />
              <SelectField label="TIF" value={tif} onChange={setTif} options={TIF_OPTIONS} />
              <SelectField label="Mode" value={sizeMode} onChange={setSizeMode} options={[{value: "shares", label: "Shares"}, {value: "notional", label: "Notional ($)"}]} />
              <InputField label="Qty/Amt" value={qty} onChange={setQty} />
            </div>

            {/* Row 2: Side, Client Order ID, Ext Hours, Entry Prices */}
            <div className="grid grid-cols-5 gap-2 mt-2">
              <SelectField label="Side" value={orderSide} onChange={setOrderSide} options={SIDES} />
              <InputField label="Client Order ID" value={clientOrderId} onChange={setClientOrderId} placeholder="emb_alg_..." />
              <SelectField label="Ext. Hrs" value={extHoursOrder ? "yes" : "no"} onChange={(v) => setExtHoursOrder(v === "yes")} options={[{value: "no", label: "No"}, {value: "yes", label: "Yes"}]} />
              <InputField label="Entry LMT Px" value={limitPrice} onChange={setLimitPrice} placeholder="0.00" className="text-cyan-400 font-bold" />
              <InputField label="Entry STP Px" value={stopPrice} onChange={setStopPrice} placeholder="N/A" disabled={!["stop", "stop_limit"].includes(orderType)} />
            </div>

            {/* Bracket / OCO / OTO Legs */}
            <div className="flex gap-2 mt-2">
              {/* Take Profit Leg */}
              <div className="flex-1 border border-dashed border-slate-700/50 rounded p-2 bg-slate-800/20">
                <div className="flex justify-between text-[9px] text-slate-500 uppercase mb-1">
                  <span>Take Profit / OCO LMT</span>
                  <span className="text-emerald-400">LEG 1</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <InputField label="Limit Px" value={tpLimitPrice} onChange={setTpLimitPrice} placeholder="0.00" />
                  <div className="flex flex-col gap-0.5">
                    <label className="text-[9px] text-slate-500">Est. Profit</label>
                    <span className={`text-[10px] font-mono font-bold ${estProfit >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                      {estProfit ? `${estProfit >= 0 ? "+" : ""}$${estProfit.toLocaleString(undefined, {maximumFractionDigits: 2})}` : "--"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Stop Loss Leg */}
              <div className="flex-1 border border-dashed border-slate-700/50 rounded p-2 bg-slate-800/20">
                <div className="flex justify-between text-[9px] text-slate-500 uppercase mb-1">
                  <span>Stop Loss / OCO STP</span>
                  <span className="text-red-400">LEG 2</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <InputField label="Stop Px" value={slStopPrice} onChange={setSlStopPrice} placeholder="0.00" />
                  <InputField label="Stop Lmt" value={slLimitPrice} onChange={setSlLimitPrice} placeholder="0.00" />
                </div>
              </div>

              {/* Trailing Stop Params */}
              <div className="flex-1 border border-dashed border-slate-700/50 rounded p-2 bg-slate-800/20">
                <div className="flex justify-between text-[9px] text-slate-500 uppercase mb-1">
                  <span>Trailing Stop Params</span>
                  <span className="text-purple-400">OPT</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <SelectField label="Trail Type" value={trailType} onChange={setTrailType} options={[{value: "percent", label: "Percent (%)"}, {value: "price", label: "Price ($)"}]} small />
                  <InputField label="Value" value={trailValue} onChange={setTrailValue} placeholder="1.5" />
                </div>
              </div>
            </div>
          </div>

          {/* ===== COL 3: Matrix & Pre-Flight (Span 4) ===== */}
          <div className="col-span-4 bg-slate-800/40 border border-slate-700/50 rounded-lg p-3 flex flex-col">
            <div className="text-[11px] font-bold text-cyan-400 uppercase border-b border-slate-700/50 pb-1">
              Matrix & Pre-Flight
            </div>

            {/* Price Ladder */}
            <div className="flex border-b border-slate-700/50 mb-2" style={{ height: 130 }}>
              <div className="flex-1 relative flex items-center justify-center border-r border-slate-700/50">
                {/* Vertical line */}
                <div className="absolute w-px h-4/5 bg-slate-700/50" />
                {/* TP node */}
                <div className="absolute top-2 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded border border-emerald-500/50 bg-emerald-500/10 text-emerald-400 text-[9px] font-bold text-center">
                  TP: {tpLimitPrice || "--"}
                  <div className="text-[7px] text-emerald-300">{estProfit ? `+$${Math.abs(estProfit).toLocaleString(undefined, {maximumFractionDigits: 0})}` : ""}</div>
                </div>
                {/* Entry node */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 px-2 py-0.5 rounded bg-cyan-500 text-black text-[9px] font-bold text-center">
                  LMT: {limitPrice || "--"}
                  <div className="text-[7px]">{numQty} {sizeMode === "shares" ? "Shares" : "USD"}</div>
                </div>
                {/* SL node */}
                <div className="absolute bottom-2 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded border border-red-500/50 bg-red-500/10 text-red-400 text-[9px] font-bold text-center">
                  SL: {slStopPrice || "--"}
                  <div className="text-[7px] text-red-300">{estRisk ? `-$${estRisk.toLocaleString(undefined, {maximumFractionDigits: 0})}` : ""}</div>
                </div>
                {/* R:R ratio */}
                <div className="absolute right-1 top-1/2 -translate-y-1/2 text-[9px] text-cyan-400 text-right">
                  R:R<br /><span className="text-[11px] font-bold">1:{rrRatio}</span>
                </div>
              </div>

              {/* Pre-flight numbers */}
              <div className="flex-1 pl-2 flex flex-col justify-center">
                <DataRow label="Capital Req." value={estCapital ? `$${estCapital.toLocaleString(undefined, {maximumFractionDigits: 2})}` : "--"} />
                <DataRow label="Margin Impact" value={estMarginImpact ? `$${estMarginImpact.toLocaleString(undefined, {maximumFractionDigits: 2})}` : "--"} valueClass="text-amber-400" />
                <DataRow label="Post-Alloc." value={`${postAlloc}%`} />
              </div>
            </div>

            {/* Pre-flight checklist */}
            <div className="grid grid-cols-2 gap-1 mb-2">
              {[
                { key: "entryPx", label: "Entry Px" },
                { key: "stopValid", label: "Risk Gov" },
                { key: "kellyOpt", label: "Kelly Opt" },
                { key: "heatLimit", label: "Heat Lmt" },
                { key: "regimeAlign", label: "Regime" },
                { key: "mentalClear", label: "Mental" },
              ].map((item) => (
                <label key={item.key} className="flex items-center gap-1 cursor-pointer text-[9px]">
                  <input
                    type="checkbox"
                    checked={checklist[item.key]}
                    onChange={() => setChecklist((p) => ({ ...p, [item.key]: !p[item.key] }))}
                    className="accent-cyan-500 w-3 h-3"
                  />
                  <span className={checklist[item.key] ? "text-emerald-400" : "text-slate-500"}>
                    {checklist[item.key] ? "✓" : ""} {item.label}
                  </span>
                </label>
              ))}
            </div>

            {/* Order result/error feedback */}
            {orderError && (
              <div className="text-[9px] text-red-400 bg-red-500/10 border border-red-500/30 rounded px-2 py-1 mb-2">
                {orderError}
              </div>
            )}
            {orderResult && (
              <div className="text-[9px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 rounded px-2 py-1 mb-2">
                Order placed: {orderResult.id?.slice(0, 8)}... Status: {orderResult.status}
              </div>
            )}

            {/* Execute button */}
            <div className="mt-auto">
              <button
                onClick={handleAdvancedOrder}
                disabled={!allChecked || executing}
                className={`w-full py-3 rounded-lg text-[12px] font-bold transition-all ${
                  allChecked
                    ? "bg-cyan-500 text-black hover:bg-cyan-400 shadow-lg shadow-cyan-500/30"
                    : "bg-slate-700 text-slate-500 cursor-not-allowed"
                }`}
              >
                {executing ? "EXECUTING..." : allChecked ? `EXECUTE ${orderClass.toUpperCase()} ORDER` : "Complete checklist"}
                <span className="text-[8px] opacity-60 ml-2">^ENT</span>
              </button>
            </div>
          </div>

          {/* ===== BOTTOM LEFT: Live Working Orders (Span 6) ===== */}
          <div className="col-span-6 bg-slate-800/40 border border-slate-700/50 rounded-lg p-3" style={{ maxHeight: 380 }}>
            <div className="text-[11px] font-bold text-cyan-400 uppercase border-b border-slate-700/50 pb-1 flex justify-between">
              <span>Live Working Orders</span>
              <span className="text-slate-500">[PATCH / DELETE]</span>
            </div>
            <div className="overflow-y-auto mt-1" style={{ maxHeight: 330 }}>
              <table className="w-full text-[9px] font-mono">
                <thead>
                  <tr className="text-slate-500 uppercase border-b border-slate-700/50">
                    <th className="py-1 px-1 text-left font-normal">Time</th>
                    <th className="py-1 px-1 text-left font-normal">Sym</th>
                    <th className="py-1 px-1 text-left font-normal">Side</th>
                    <th className="py-1 px-1 text-left font-normal">Class</th>
                    <th className="py-1 px-1 text-left font-normal">Type</th>
                    <th className="py-1 px-1 text-left font-normal">Qty</th>
                    <th className="py-1 px-1 text-left font-normal">Price</th>
                    <th className="py-1 px-1 text-left font-normal">TIF</th>
                    <th className="py-1 px-1 text-left font-normal">Status</th>
                    <th className="py-1 px-1 text-left font-normal">Act</th>
                  </tr>
                </thead>
                <tbody>
                  {workingOrders.length === 0 && (
                    <tr><td colSpan={10} className="py-4 text-center text-slate-600">No working orders</td></tr>
                  )}
                  {workingOrders.map((order) => {
                    const time = order.submitted_at ? new Date(order.submitted_at).toLocaleTimeString("en-US", { hour12: false, timeZone: "America/New_York" }) : "--";
                    const status = (order.status || "").toLowerCase();
                    const isLeg = order.legs && order.legs.length > 0;
                    return (
                      <React.Fragment key={order.id}>
                        <tr className="border-b border-slate-800/50 hover:bg-slate-800/30">
                          <td className="py-1 px-1">{time}</td>
                          <td className="py-1 px-1 text-cyan-400 font-bold">{order.symbol}</td>
                          <td className="py-1 px-1">
                            <span className={`px-1 py-0.5 rounded text-[8px] font-bold uppercase border ${
                              order.side === "buy" ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" : "bg-red-500/15 text-red-400 border-red-500/30"
                            }`}>{order.side}</span>
                          </td>
                          <td className="py-1 px-1 uppercase">{order.order_class || "SIMPLE"}</td>
                          <td className="py-1 px-1 uppercase">{order.type}</td>
                          <td className="py-1 px-1">{order.qty || order.notional}</td>
                          <td className="py-1 px-1">{order.limit_price || order.stop_price || order.trail_percent ? `T-${order.trail_percent}%` : "MKT"}</td>
                          <td className="py-1 px-1 uppercase">{order.time_in_force}</td>
                          <td className={`py-1 px-1 uppercase font-bold ${STATUS_COLORS[status] || "text-slate-400"}`}>{status}</td>
                          <td className="py-1 px-1 flex gap-1">
                            <button onClick={() => handleCancelOrder(order.id)} className="px-1 py-0.5 rounded text-[8px] border border-red-500/50 text-red-400 hover:bg-red-500/10">Cxl</button>
                          </td>
                        </tr>
                        {/* Render bracket legs */}
                        {isLeg && order.legs.map((leg) => (
                          <tr key={leg.id} className="border-b border-slate-800/50 hover:bg-slate-800/30 text-slate-600">
                            <td className="py-1 px-1">{time}</td>
                            <td className="py-1 px-1 pl-3">└─ {leg.symbol}</td>
                            <td className="py-1 px-1">
                              <span className={`px-1 py-0.5 rounded text-[8px] font-bold uppercase border ${
                                leg.side === "buy" ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" : "bg-red-500/15 text-red-400 border-red-500/30"
                              }`}>{leg.side}</span>
                            </td>
                            <td className="py-1 px-1">LEG</td>
                            <td className="py-1 px-1 uppercase">{leg.type}</td>
                            <td className="py-1 px-1">{leg.qty}</td>
                            <td className="py-1 px-1">{leg.limit_price || leg.stop_price || "--"}</td>
                            <td className="py-1 px-1 uppercase">{leg.time_in_force}</td>
                            <td className={`py-1 px-1 uppercase ${STATUS_COLORS[(leg.status || "").toLowerCase()] || "text-slate-500"}`}>{leg.status}</td>
                            <td className="py-1 px-1"></td>
                          </tr>
                        ))}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* ===== BOTTOM RIGHT: Execution Feed & Fills (Span 6) ===== */}
          <div className="col-span-6 bg-slate-800/40 border border-slate-700/50 rounded-lg p-3" style={{ maxHeight: 380 }}>
            <div className="text-[11px] font-bold text-cyan-400 uppercase border-b border-slate-700/50 pb-1 flex justify-between">
              <span>Execution Feed & Fills</span>
              <span className="text-slate-500">[get_activities]</span>
            </div>
            <div className="overflow-y-auto mt-1" style={{ maxHeight: 330 }}>
              <table className="w-full text-[9px] font-mono">
                <thead>
                  <tr className="text-slate-500 uppercase border-b border-slate-700/50">
                    <th className="py-1 px-1 text-left font-normal">Time</th>
                    <th className="py-1 px-1 text-left font-normal">Event</th>
                    <th className="py-1 px-1 text-left font-normal">Sym</th>
                    <th className="py-1 px-1 text-left font-normal">Details</th>
                    <th className="py-1 px-1 text-left font-normal">Price</th>
                    <th className="py-1 px-1 text-left font-normal">Notional</th>
                  </tr>
                </thead>
                <tbody>
                  {activities.length === 0 && (
                    <tr><td colSpan={6} className="py-4 text-center text-slate-600">No recent activity</td></tr>
                  )}
                  {activities.map((act, i) => {
                    const time = act.transaction_time
                      ? new Date(act.transaction_time).toLocaleTimeString("en-US", { hour12: false, timeZone: "America/New_York" })
                      : "--";
                    const eventType = (act.type || act.activity_type || "").toLowerCase();
                    const isFill = eventType === "fill" || act.activity_type === "FILL";
                    const side = act.side || "";
                    const qty = act.qty || act.cum_qty || "";
                    const price = act.price || "";
                    const notional = price && qty ? `$${(parseFloat(price) * parseFloat(qty)).toLocaleString(undefined, {maximumFractionDigits: 2})}` : "--";
                    return (
                      <tr key={act.id || i} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                        <td className="py-1 px-1">{time}</td>
                        <td className="py-1 px-1">
                          <Badge status={isFill ? "filled" : eventType === "partial_fill" ? "partially_filled" : "canceled"} />
                        </td>
                        <td className="py-1 px-1 text-cyan-400 font-bold">{act.symbol || "--"}</td>
                        <td className="py-1 px-1">
                          {side.toUpperCase() === "BUY" ? "BOT" : "SLD"} {qty} {act.order_id ? `@ ${price}` : ""}
                        </td>
                        <td className="py-1 px-1">{price ? `$${parseFloat(price).toFixed(2)}` : "--"}</td>
                        <td className="py-1 px-1">{notional}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

        </div>{/* end grid */}
      </div>{/* end scrollable area */}
    </div>
  );
}
