import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "react-toastify";
import log from "@/utils/logger";
import { useApi, fetchCouncilEvaluate, useCouncilLatest } from "../hooks/useApi";
import { getApiUrl, getAuthHeaders } from "../config/api";
import CNSVitals from "../components/dashboard/CNSVitals";
import ProfitBrainBar from "../components/dashboard/ProfitBrainBar";
import ws from "../services/websocket";

// --- TOP TICKER STRIP (scrolling market tickers); click symbol to select ---
const TickerStrip = ({ indices, signals, onSelectSymbol }) => {
  // indices is normalized in Dashboard to a symbol-keyed map: { SPX: { value, change }, ... }
  const tickers = useMemo(() => {
    const items = [];
    const indexMap = {
      SPY: indices?.SPY,
      QQQ: indices?.QQQ,
      AAPL: indices?.AAPL,
      MSFT: indices?.MSFT,
      TSLA: indices?.TSLA,
      AMZN: indices?.AMZN,
      NVDA: indices?.NVDA,
      META: indices?.META,
      GOOGL: indices?.GOOGL,
      SPX: indices?.SPX,
      NDAQ: indices?.NDAQ,
      DIA: indices?.DIA,
      DOW: indices?.DOW,
      BTC: indices?.BTC,
      ETH: indices?.ETH,
      VIX: indices?.VIX,
    };
    Object.entries(indexMap).forEach(([sym, data]) => {
      if (data) {
        items.push({
          symbol: sym,
          price: data.price ?? data.value ?? data.last ?? null,
          change: data.change ?? data.changePct ?? 0,
        });
      }
    });
    // Add top signals as tickers if not already present (use null so UI shows — when no data)
    if (signals?.length) {
      signals.slice(0, 12).forEach((sig) => {
        if (!items.find((t) => t.symbol === sig.symbol)) {
          const entry = sig.entry ?? sig.price ?? null;
          const ch = sig.momentum ?? sig.changePct ?? null;
          items.push({
            symbol: sig.symbol,
            price: entry != null && entry !== "" ? Number(entry) : null,
            change: ch != null && ch !== "" ? Number(ch) : null,
          });
        }
      });
    }
    // No fallback tickers — only show real API data
    return items;
  }, [indices, signals]);

  return (
    <div className="bg-[#111827] border-b border-[rgba(42,52,68,0.5)] shrink-0 overflow-hidden">
      <div className="ticker-strip flex items-center gap-6 px-3 py-1 whitespace-nowrap">
        {/* First copy */}
        {[...tickers, ...tickers].map((t, i) => {
          const isPositive = (t.change ?? 0) >= 0;
          const changeColor =
            t.change == null
              ? "text-[#64748b]"
              : isPositive
                ? "text-[#10b981]"
                : "text-[#ef4444]";
          return (
            <button
              key={`${t.symbol}-${i}`}
              type="button"
              onClick={() => onSelectSymbol?.(t.symbol)}
              className="inline-flex items-center gap-1.5 text-[10px] font-mono hover:bg-white/5 rounded px-1 py-0.5 transition-colors cursor-pointer"
            >
              <span className="text-[#94a3b8] font-bold">{t.symbol}</span>
              <span className="text-white">
                {t.price != null
                  ? typeof t.price === "number"
                    ? t.price.toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })
                    : t.price
                  : "\u2014"}
              </span>
              <span className={changeColor}>
                {t.change != null
                  ? `${isPositive ? "+" : ""}${typeof t.change === "number" ? t.change.toFixed(2) : t.change}%`
                  : "\u2014"}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

// --- ICONS ---
const HexagonLogo = () => (
  <svg
    className="w-5 h-5 text-[#00D9FF]"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
  >
    <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
  </svg>
);

// --- REGIME DONUT RING (SVG) ---
const RegimeDonut = ({ regime, score }) => {
  const radius = 36;
  const stroke = 6;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.min(100, Math.max(0, score || 0));
  const offset = circumference - (pct / 100) * circumference;
  const color =
    regime === "BEAR" ? "#ef4444" : regime === "BULL" ? "#10b981" : "#f59e0b";
  return (
    <svg width="90" height="90" viewBox="0 0 90 90">
      <circle
        cx="45"
        cy="45"
        r={radius}
        fill="none"
        stroke="#1e293b"
        strokeWidth={stroke}
      />
      <circle
        cx="45"
        cy="45"
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={stroke}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 45 45)"
        style={{ transition: "stroke-dashoffset 0.6s ease" }}
      />
      <text
        x="45"
        y="40"
        textAnchor="middle"
        fill="#f8fafc"
        fontSize="14"
        fontFamily="'JetBrains Mono', monospace"
        fontWeight="bold"
      >
        {pct}
      </text>
      <text
        x="45"
        y="55"
        textAnchor="middle"
        fill={color}
        fontSize="9"
        fontFamily="'Inter', sans-serif"
        fontWeight="600"
      >
        {regime || "\u2014"}
      </text>
    </svg>
  );
};

// --- TOP TRADES DONUT (from mockup 02) ---
const TopTradesDonut = ({ buyCount, sellCount, holdCount }) => {
  const total = (buyCount || 0) + (sellCount || 0) + (holdCount || 0) || 1;
  const buyPct = ((buyCount || 0) / total) * 100;
  const sellPct = ((sellCount || 0) / total) * 100;
  const holdPct = ((holdCount || 0) / total) * 100;
  const r = 36,
    cx = 45,
    cy = 45,
    sw = 8;
  const circ = 2 * Math.PI * r;
  const buyOff = 0;
  const sellOff = (buyPct / 100) * circ;
  const holdOff = sellOff + (sellPct / 100) * circ;
  return (
    <div className="flex items-center gap-4">
      <svg width="90" height="90" viewBox="0 0 90 90">
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#1e293b"
          strokeWidth={sw}
        />
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#10b981"
          strokeWidth={sw}
          strokeDasharray={`${(buyPct / 100) * circ} ${circ}`}
          strokeDashoffset={0}
          transform="rotate(-90 45 45)"
          strokeLinecap="round"
        />
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#ef4444"
          strokeWidth={sw}
          strokeDasharray={`${(sellPct / 100) * circ} ${circ}`}
          strokeDashoffset={-sellOff}
          transform="rotate(-90 45 45)"
          strokeLinecap="round"
        />
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#f59e0b"
          strokeWidth={sw}
          strokeDasharray={`${(holdPct / 100) * circ} ${circ}`}
          strokeDashoffset={-holdOff}
          transform="rotate(-90 45 45)"
          strokeLinecap="round"
        />
        <text
          x={cx}
          y="42"
          textAnchor="middle"
          fill="#f8fafc"
          fontSize="14"
          fontFamily="'JetBrains Mono', monospace"
          fontWeight="bold"
        >
          {total}
        </text>
        <text
          x={cx}
          y="55"
          textAnchor="middle"
          fill="#94a3b8"
          fontSize="8"
          fontFamily="'Inter', sans-serif"
        >
          TRADES
        </text>
      </svg>
      <div className="text-[10px] space-y-1">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-slate-400">Buy</span>
          <span className="text-white font-bold">{buyPct.toFixed(0)}%</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-red-500" />
          <span className="text-slate-400">Sell</span>
          <span className="text-white font-bold">{sellPct.toFixed(0)}%</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-amber-500" />
          <span className="text-slate-400">Hold</span>
          <span className="text-white font-bold">{holdPct.toFixed(0)}%</span>
        </div>
      </div>
    </div>
  );
};

// --- SIGNAL BAR CHART (Colored vertical bars per symbol with Aurora design) ---
const SignalBarChart = ({ signals, selectedSymbol, onSelect }) => {
  if (!signals || !signals.length) return null;
  const maxScore = Math.max(...signals.map((s) => s.score || 0), 1);
  return (
    <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)]">
      {/* Hidden SVG defs for aurora gradient */}
      <svg width="0" height="0" style={{ position: "absolute" }}>
        <defs>
          <linearGradient id="auroraBar" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#06B6D4" stopOpacity={0.9} />
            <stop offset="100%" stopColor="#10B981" stopOpacity={0.6} />
          </linearGradient>
        </defs>
      </svg>
      <div className="flex items-center justify-between px-3 py-1 border-b border-[rgba(42,52,68,0.5)]">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
          SIGNAL STRENGTH
        </span>
        <div className="flex items-center gap-2 text-[7px] font-mono text-[#64748b]">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-[#10b981]" /> 85+
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-[#00D9FF]" /> 70+
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-[#f59e0b]" /> 50+
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-[#ef4444]" /> &lt;50
          </span>
        </div>
      </div>
      <div className="flex items-end gap-[3px] h-[130px] px-3 py-2 overflow-x-auto no-scrollbar">
        {signals.map((sig, i) => {
          const h = ((sig.score || 0) / maxScore) * 100;
          const isLong = sig.direction === "LONG";
          const isSelected = sig.symbol === selectedSymbol;
          // Aurora gradient for high scores, fallback colors for lower scores
          const useAurora = sig.score >= 70;
          const barColor =
            sig.score >= 85
              ? "#10b981"
              : sig.score >= 70
                ? "#00D9FF"
                : sig.score >= 50
                  ? "#f59e0b"
                  : "#ef4444";
          return (
            <div
              key={sig.symbol + i}
              className="flex flex-col items-center cursor-pointer group"
              onClick={() => onSelect(sig.symbol)}
              style={{ minWidth: "30px" }}
            >
              {/* Score label on hover */}
              <span className="text-[7px] font-mono font-bold text-white opacity-0 group-hover:opacity-100 transition-opacity mb-0.5">
                {sig.score}
              </span>
              {/* Aurora bar rendered as inline SVG rect for gradient support */}
              <svg
                width="20"
                height={`${Math.max(h * 1.1, 4)}px`}
                style={{ minHeight: "4px", display: "block" }}
                className={`rounded-t-sm transition-all duration-200 ${isSelected ? "ring-2 ring-[#00D9FF] shadow-[0_0_8px_rgba(0,217,255,0.4)]" : ""}`}
              >
                <defs>
                  <linearGradient id={`auroraBar-${i}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#06B6D4" stopOpacity={useAurora ? 0.9 : 0.7} />
                    <stop offset="100%" stopColor={useAurora ? "#10B981" : barColor} stopOpacity={useAurora ? 0.6 : 0.7} />
                  </linearGradient>
                </defs>
                <rect
                  x="0" y="0" width="20" height="100%"
                  fill={`url(#auroraBar-${i})`}
                  opacity={isSelected ? 1 : 0.8}
                />
              </svg>
              <span
                className={`text-[7px] font-mono mt-0.5 ${isSelected ? "text-[#00D9FF] font-bold" : "text-[#94a3b8] group-hover:text-white"}`}
              >
                {sig.symbol}
              </span>
              <span
                className={`text-[6px] font-mono font-bold ${isLong ? "text-[#10b981]" : "text-[#ef4444]"}`}
              >
                {isLong ? "LONG" : "SHORT"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};



// --- SKELETON LOADER (no mock data) ---
const Skeleton = ({ className = "" }) => (
  <div className={`animate-pulse bg-[#1e293b] rounded ${className}`} />
);

// --- MINI EQUITY CURVE (SVG Sparkline, memoized by values) ---
const MiniEquityCurve = ({ points }) => {
  const pad = 4;
  const w = 280;
  const h = 40;
  const values = useMemo(() => (points || []).map((p) => Number(p?.value ?? p?.equity ?? p?.y ?? 0)).filter((v) => !Number.isNaN(v)), [points]);
  const { coords, minV, maxV, range, first, last, change, color } = useMemo(() => {
    if (!values.length || values.length < 2)
      return { coords: null, minV: 0, maxV: 0, range: 1, first: null, last: null, change: null, color: "#10b981" };
    const minV = Math.min(...values);
    const maxV = Math.max(...values);
    const range = maxV - minV || 1;
    const coords = values.map((v, i) => {
      const x = pad + (i / (values.length - 1)) * (w - 2 * pad);
      const y = pad + (1 - (v - minV) / range) * (h - 2 * pad);
      return `${x},${y}`;
    });
    const last = values[values.length - 1];
    const first = values[0];
    const change = last - first;
    return { coords, minV, maxV, range, first, last, change, color: change >= 0 ? "#10b981" : "#ef4444" };
  }, [values]);

  if (!values.length || values.length < 2) {
    const initEquity = points?.[0]?.value ?? points?.[0]?.equity ?? null;
    if (initEquity == null && (!points || points.length === 0))
      return (
        <div className="space-y-1">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      );
    return (
      <div>
        <div className="text-[8px] text-[#64748b] text-center font-mono mb-1">
          {initEquity != null ? `Initial: $${Number(initEquity).toLocaleString()}` : "\u2014"}
        </div>
        <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="w-full">
          <line x1={pad} y1={h / 2} x2={w - pad} y2={h / 2} stroke="#10b981" strokeWidth="1.5" strokeDasharray="4 2" />
        </svg>
      </div>
    );
  }
  return (
    <div>
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="w-full">
        <defs>
          <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.3" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon
          points={`${pad},${h - pad} ${coords.join(" ")} ${w - pad},${h - pad}`}
          fill="url(#eqGrad)"
        />
        <polyline
          points={coords.join(" ")}
          fill="none"
          stroke={color}
          strokeWidth="1.5"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      </svg>
      <div className="flex justify-between text-[8px] font-mono px-1 mt-0.5">
        <span className="text-[#94a3b8] kpi-num">
          ${first.toLocaleString(undefined, { maximumFractionDigits: 0 })}
        </span>
        <span className={change >= 0 ? "text-green-400 font-bold kpi-num" : "text-red-400 font-bold kpi-num"}>
          {change >= 0 ? "+" : ""}
          {change.toLocaleString(undefined, { maximumFractionDigits: 0 })}
        </span>
        <span className="text-white kpi-num">
          ${last.toLocaleString(undefined, { maximumFractionDigits: 0 })}
        </span>
      </div>
    </div>
  );
};

// --- AGENT CONSENSUS RING (Large Donut) ---
const AgentConsensusRing = ({ buyPct, sellPct, holdPct, consensus }) => {
  const r = 50,
    cx = 60,
    cy = 60,
    sw = 10;
  const circ = 2 * Math.PI * r;
  const total = (buyPct || 0) + (sellPct || 0) + (holdPct || 0) || 1;
  const bFrac = (buyPct || 0) / total;
  const sFrac = (sellPct || 0) / total;
  const hFrac = (holdPct || 0) / total;
  const buyLen = bFrac * circ;
  const sellLen = sFrac * circ;
  const holdLen = hFrac * circ;
  return (
    <div className="flex items-center gap-3">
      <svg width="120" height="120" viewBox="0 0 120 120">
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#1e293b"
          strokeWidth={sw}
        />
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#10b981"
          strokeWidth={sw}
          strokeDasharray={`${buyLen} ${circ - buyLen}`}
          strokeDashoffset={0}
          transform="rotate(-90 60 60)"
          strokeLinecap="round"
        />
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#ef4444"
          strokeWidth={sw}
          strokeDasharray={`${sellLen} ${circ - sellLen}`}
          strokeDashoffset={-buyLen}
          transform="rotate(-90 60 60)"
          strokeLinecap="round"
        />
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#f59e0b"
          strokeWidth={sw}
          strokeDasharray={`${holdLen} ${circ - holdLen}`}
          strokeDashoffset={-(buyLen + sellLen)}
          transform="rotate(-90 60 60)"
          strokeLinecap="round"
        />
        <text
          x={cx}
          y="56"
          textAnchor="middle"
          fill="#f8fafc"
          fontSize="18"
          fontWeight="bold"
          fontFamily="'JetBrains Mono', monospace"
        >
          {consensus ?? "\u2014"}
        </text>
        <text
          x={cx}
          y="70"
          textAnchor="middle"
          fill="#94a3b8"
          fontSize="8"
          fontFamily="'Inter', sans-serif"
        >
          CONSENSUS
        </text>
      </svg>
      <div className="space-y-1 text-[9px] font-mono">
        <div className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-green-500" />
          <span className="text-slate-400">Buy</span>
          <span className="text-white font-bold">
            {Math.round(bFrac * 100)}%
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-red-500" />
          <span className="text-slate-400">Sell</span>
          <span className="text-white font-bold">
            {Math.round(sFrac * 100)}%
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-amber-500" />
          <span className="text-slate-400">Hold</span>
          <span className="text-white font-bold">
            {Math.round(hFrac * 100)}%
          </span>
        </div>
      </div>
    </div>
  );
};

// --- FLYWHEEL STATUS PIPELINE ---
const FlywheelPipeline = ({ flywheel }) => {
  const stages = [
    {
      label: "Collect",
      key: "resolvedSignals",
      icon: "\u2b07",
      color: "#00D9FF",
    },
    { label: "Train", key: "accuracy30d", icon: "\u2699", color: "#8b5cf6" },
    { label: "Predict", key: "accuracy30d", icon: "\u26a1", color: "#f59e0b" },
    { label: "Evaluate", key: "accuracy90d", icon: "\u2714", color: "#10b981" },
  ];
  // accuracy30d/90d are 0–1; accuracy from API is already 0–100
  const acc30Pct = flywheel?.accuracy30d != null ? Number(flywheel.accuracy30d) * 100 : (flywheel?.accuracy != null ? Number(flywheel.accuracy) : null);
  const acc90Pct = flywheel?.accuracy90d != null ? Number(flywheel.accuracy90d) * 100 : null;
  const resolved = flywheel?.resolvedSignals ?? 0;
  const isActive = (acc30Pct != null && acc30Pct > 0) || resolved > 0;
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        {stages.map((s, i) => (
          <div key={s.label} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full border-2 flex items-center justify-center text-sm ${isActive ? `border-[${s.color}] text-[${s.color}]` : "border-[#374151] text-[#64748b]"}`}
                style={{
                  borderColor: isActive ? s.color : "#374151",
                  color: isActive ? s.color : "#64748b",
                }}
              >
                {s.icon}
              </div>
              <span className="text-[7px] mt-0.5 text-[#94a3b8]">
                {s.label}
              </span>
            </div>
            {i < stages.length - 1 && (
              <div
                className={`w-6 h-px mx-1 ${isActive ? "bg-[#00D9FF]" : "bg-[#374151]"}`}
              />
            )}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-1 text-center font-mono text-[8px]">
        <div>
          <span className="text-[#94a3b8]">30d Acc</span>
          <br />
          <span className="text-[#00D9FF] font-bold">
            {acc30Pct != null ? `${Number(acc30Pct).toFixed(1)}%` : "\u2014"}
          </span>
        </div>
        <div>
          <span className="text-[#94a3b8]">90d Acc</span>
          <br />
          <span className="text-[#00D9FF] font-bold">
            {acc90Pct != null ? `${Number(acc90Pct).toFixed(1)}%` : "\u2014"}
          </span>
        </div>
        <div>
          <span className="text-[#94a3b8]">Resolved</span>
          <br />
          <span className="text-white font-bold">{resolved}</span>
        </div>
      </div>
    </div>
  );
};

// --- CONSENSUS HORIZONTAL BARS ---
const ConsensusBar = ({ label, buyPct, sellPct }) => (
  <div className="flex items-center gap-2 text-[8px] font-mono">
    <span className="w-16 text-[#94a3b8] truncate">{label}</span>
    <div className="flex-1 flex h-2 rounded-sm overflow-hidden bg-[#1e293b]">
      <div
        className="h-full bg-[#10b981]"
        style={{ width: `${buyPct || 0}%` }}
      />
      <div
        className="h-full bg-[#ef4444]"
        style={{ width: `${sellPct || 0}%` }}
      />
    </div>
    <span className="text-[#10b981] w-6 text-right">{buyPct || 0}%</span>
  </div>
);

// --- BOTTOM HEATMAP GRID (sector/symbol performance heatmap) ---
const HeatmapGrid = ({ signals }) => {
  // Group signals by sector
  const sectorMap = useMemo(() => {
    if (!signals || !signals.length) return {};
    const map = {};
    signals.forEach((sig) => {
      const sector = sig.sector || "Other";
      if (!map[sector]) map[sector] = [];
      map[sector].push(sig);
    });
    return map;
  }, [signals]);

  if (!signals || !signals.length) return null;

  // Color interpolation: score 0-100; red minimum brightness #ef4444 (239,68,68)
  const getHeatColor = (score) => {
    const s = Math.min(100, Math.max(0, score || 0));
    if (s >= 70) {
      const t = (s - 70) / 30;
      const r = Math.round(245 * (1 - t));
      const g = Math.round(158 + 97 * t);
      const b = Math.round(11 + 120 * t);
      return `rgb(${r},${g},${b})`;
    }
    if (s >= 40) {
      const t = (s - 40) / 30;
      const r = Math.round(239 + 6 * t);
      const g = Math.round(68 + 90 * t);
      const b = Math.round(68 - 57 * t);
      return `rgb(${r},${g},${b})`;
    }
    // red range: min brightness #ef4444
    const t = s / 40;
    const r = Math.round(239);
    const g = Math.round(29 + 39 * t);
    const b = Math.round(68);
    return `rgb(${r},${g},${b})`;
  };

  const getHeatBg = (score) => {
    const s = Math.min(100, Math.max(0, score || 0));
    if (s >= 70) return "rgba(16,185,129,0.15)";
    if (s >= 40) return "rgba(245,158,11,0.12)";
    return "rgba(239,68,68,0.12)";
  };

  return (
    <div className="bg-[#111827] border-t border-[rgba(42,52,68,0.5)]">
      <div className="flex items-center justify-between px-3 py-1 border-b border-[rgba(42,52,68,0.5)]">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
          SECTOR HEATMAP
        </span>
        <div className="flex items-center gap-2 text-[7px] font-mono text-[#64748b]">
          <span>Score:</span>
          <div className="flex items-center h-2 w-20 rounded-sm overflow-hidden">
            <div
              className="h-full flex-1"
              style={{
                background:
                  "linear-gradient(to right, #7f1d1d, #ef4444, #f59e0b, #10b981)",
              }}
            />
          </div>
          <span>0 - 100</span>
        </div>
      </div>
      <div
        className="flex flex-wrap gap-[2px] p-2 overflow-x-auto no-scrollbar"
        style={{ maxHeight: "120px" }}
      >
        {Object.entries(sectorMap).map(([sector, sigs]) => (
          <div key={sector} className="flex flex-col gap-[1px]">
            <span
              className="text-[6px] font-mono text-[#64748b] uppercase px-0.5 truncate"
              style={{ maxWidth: "80px" }}
            >
              {sector}
            </span>
            <div className="flex gap-[1px]">
              {sigs.slice(0, 8).map((sig, i) => (
                <div
                  key={sig.symbol + i}
                  className="flex flex-col items-center justify-center rounded-sm cursor-pointer transition-all hover:scale-110 hover:z-10"
                  style={{
                    width: "42px",
                    height: "32px",
                    backgroundColor: getHeatBg(sig.score),
                    border: `1px solid ${getHeatColor(sig.score)}33`,
                  }}
                  title={`${sig.symbol}: Score ${sig.score}, ${sig.direction}`}
                >
                  <span className="text-[7px] font-mono font-bold text-white leading-none heatmap-text">
                    {sig.symbol}
                  </span>
                  <span
                    className="text-[7px] font-mono font-bold leading-none heatmap-text"
                    style={{ color: getHeatColor(sig.score) }}
                  >
                    {sig.score}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// --- CONSTANTS ---
const SORT_PILLS = [
  "Composite Score",
  "Swarm Leader",
  "Technical Rank",
  "Momentum",
  "Breakout",
  "Rebound",
  "Mean Reversion",
  "Kelly Optimal",
  "SHAP Impact",
  "Risk-Reward",
  "ML Probability",
  "Sentiment",
  "Volume Surge",
  "Sector Rotation",
  "Options Flow",
];
const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1D", "1W"];

const SCORE_FILTERS = [
  { id: "all", label: "All", min: 0, max: 100 },
  { id: "85+", label: "85+", min: 85, max: 100 },
  { id: "70+", label: "70+", min: 70, max: 100 },
  { id: "50+", label: "50+", min: 50, max: 100 },
  { id: "<50", label: "<50", min: 0, max: 49 },
];

// Column header key -> sort pill key for table sort
const TABLE_SORT_COLUMNS = [
  { label: "Sym", sortKey: null },
  { label: "Dir", sortKey: null },
  { label: "Score", sortKey: "Composite Score" },
  { label: "Regime", sortKey: null },
  { label: "ML", sortKey: "ML Probability" },
  { label: "Sent", sortKey: "Sentiment" },
  { label: "Tech", sortKey: "Technical Rank" },
  { label: "Agent", sortKey: null },
  { label: "Swarm", sortKey: "Swarm Leader" },
  { label: "SHAP", sortKey: "SHAP Impact" },
  { label: "Kelly", sortKey: "Kelly Optimal" },
  { label: "Entry", sortKey: null },
  { label: "Tgt", sortKey: null },
  { label: "Stop", sortKey: null },
  { label: "R-Mult", sortKey: "Risk-Reward" },
  { label: "P&L", sortKey: null },
  { label: "Sec", sortKey: "Sector Rotation" },
  { label: "Mom", sortKey: "Momentum" },
  { label: "Vol", sortKey: "Volume Surge" },
  { label: "News", sortKey: null },
  { label: "Pat", sortKey: null },
];

export default function Dashboard() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  // --- STATE ---
  const [activeSortKey, setActiveSortKey] = useState("Composite Score");
  const [selectedSymbol, setSelectedSymbol] = useState(() => {
    const q = searchParams.get("symbol");
    return (q && q.trim().toUpperCase()) || null;
  });
  const [symbolSearch, setSymbolSearch] = useState(""); // user-typed symbol for search box
  const [activeTimeframe, setActiveTimeframe] = useState("1h");
  const [autoExec, setAutoExec] = useState(false);
  const [scoreFilter, setScoreFilter] = useState("all"); // all | 85+ | 70+ | 50+ | <50
  const [councilVerdictSymbol, setCouncilVerdictSymbol] = useState(null); // cyan glow row
  const councilGlowRef = useRef(null);

  // Sync selected symbol from URL (?symbol=XXX) when navigating from Header search
  useEffect(() => {
    const q = searchParams.get("symbol");
    const sym = q?.trim().toUpperCase();
    if (sym && sym !== selectedSymbol) setSelectedSymbol(sym);
  }, [searchParams]);

  // Metrics (must be declared before any effect that uses metricsData)
  const { data: metricsData, refetch: refetchMetrics } = useApi("metrics", { pollIntervalMs: 15000 });

  // Sync auto-execute (Manual vs Automated) from backend metrics
  useEffect(() => {
    const oe = metricsData?.order_executor;
    if (oe && typeof oe.auto_execute === "boolean") setAutoExec(oe.auto_execute);
  }, [metricsData?.order_executor?.auto_execute]);

  const setSelectedSymbolAndUrl = useCallback((sym) => {
    const s = (sym && sym.trim().toUpperCase()) || "";
    if (!s) return;
    navigate(`/symbol/${encodeURIComponent(s)}`);
  }, [navigate]);

  // --- WebSocket connection (Layout handles this now, but keep as safety net) ---
  useEffect(() => {
    ws.connect();
    return () => ws.disconnect();
  }, []);

  // --- API HOOKS (Real-time polling) ---
  const { data: apiStatusData, error: apiStatusError, refetch: refetchStatus } = useApi("status", { pollIntervalMs: 10000 });

  const {
    data: signalsData,
    loading: sigLoading,
    error: sigErr,
    isStale: sigStale,
    refetch: refetchSignals,
  } = useApi("signals", {
    pollIntervalMs: 15000,
    endpoint: `/signals/?timeframe=${encodeURIComponent(activeTimeframe)}`,
  });
  const { data: kellyData, error: kellyErr, refetch: refetchKelly } = useApi("kellyRanked", { pollIntervalMs: 30000 });
  const { data: portfolioData, error: portfolioErr, refetch: refetchPortfolio } = useApi("portfolio", { pollIntervalMs: 15000 });
  const { data: indicesData, error: indicesErr, refetch: refetchIndices } = useApi("marketIndices", {
    pollIntervalMs: 15000,
  });
  const { data: openclawData, error: openclawErr, refetch: refetchOpenclaw } = useApi("openclaw", { pollIntervalMs: 30000 });
  const { data: performanceData, refetch: refetchPerformance } = useApi("performance", {
    pollIntervalMs: 60000,
  });
  const { data: agentsData } = useApi("agents", { pollIntervalMs: 30000 });
  const { data: consensusData, refetch: refetchConsensus } = useApi("agentConsensus", { pollIntervalMs: 20000 });
  const { data: performanceEquityData, refetch: refetchPerformanceEquity } = useApi("performanceEquity", { pollIntervalMs: 30000 });
  const { data: riskScoreData, refetch: refetchRiskScore } = useApi("riskScore", {
    pollIntervalMs: 30000,
  });
  const { data: alertsData, refetch: refetchAlerts } = useApi("systemAlerts", {
    pollIntervalMs: 30000,
  });
  const { data: flywheelData, refetch: refetchFlywheel } = useApi("flywheel", { pollIntervalMs: 60000 });
  const { data: sentimentData, refetch: refetchSentiment } = useApi("sentiment", {
    pollIntervalMs: 30000,
  });
  const { data: cognitiveData, refetch: refetchCognitive } = useApi("cognitiveDashboard", { pollIntervalMs: 30000 });
  const { data: councilLatestData } = useCouncilLatest(15000);

  // Right Panel specific APIs based on selectedSymbol
  const { data: techsData } = useApi("signals", {
    endpoint: `/signals/${selectedSymbol}/technicals`,
    enabled: !!selectedSymbol,
  });
  const { data: swarmData } = useApi("swarmTopology", {
    endpoint: `/agents/swarm-topology/${selectedSymbol}`,
    enabled: !!selectedSymbol,
  });
  const { data: dataSourcesData, loading: dataSourcesLoading, refetch: refetchDataSources } = useApi("dataSources", {
    pollIntervalMs: 60000,
  });
  const { data: riskData, refetch: refetchRisk } = useApi("risk", {
    endpoint: `/risk/proposal/${selectedSymbol}`,
    enabled: !!selectedSymbol,
  });
  const { data: quotesData, refetch: refetchQuotes } = useApi("quotes", {
    endpoint: `/quotes/${selectedSymbol}/book`,
    pollIntervalMs: 10000,
    enabled: !!selectedSymbol,
  });

  // API online: status check passed OR any data endpoint has returned (so we don't show "offline" once data flows)
  const apiOnline = Boolean(apiStatusData) || !apiStatusError ||
    Boolean(signalsData || portfolioData || indicesData || dataSourcesData);

  // --- SORT MAP (all 15 pills) ---
  const SORT_MAP = useMemo(
    () => ({
      "Composite Score": (a, b) => (b.score || 0) - (a.score || 0),
      "Swarm Leader": (a, b) =>
        (b.swarmVote || "").localeCompare(a.swarmVote || ""),
      "Technical Rank": (a, b) =>
        (b.scores?.technical || 0) - (a.scores?.technical || 0),
      Momentum: (a, b) => (b.momentum || 0) - (a.momentum || 0),
      Breakout: (a, b) => (b.scores?.breakout || 0) - (a.scores?.breakout || 0),
      Rebound: (a, b) => (b.scores?.rebound || 0) - (a.scores?.rebound || 0),
      "Mean Reversion": (a, b) =>
        (b.scores?.meanReversion || 0) - (a.scores?.meanReversion || 0),
      "Kelly Optimal": (a, b) => (b.kellyPercent || 0) - (a.kellyPercent || 0),
      "SHAP Impact": (a, b) =>
        Math.abs(b.shapFeatures?.[0]?.impact || 0) -
        Math.abs(a.shapFeatures?.[0]?.impact || 0),
      "Risk-Reward": (a, b) => (b.rMultiple || 0) - (a.rMultiple || 0),
      "ML Probability": (a, b) => (b.scores?.ml || 0) - (a.scores?.ml || 0),
      Sentiment: (a, b) =>
        (b.scores?.sentiment || 0) - (a.scores?.sentiment || 0),
      "Volume Surge": (a, b) => (b.volSpike || 0) - (a.volSpike || 0),
      "Sector Rotation": (a, b) =>
        (b.scores?.sectorRotation || 0) - (a.scores?.sectorRotation || 0),
      "Options Flow": (a, b) =>
        (b.scores?.optionsFlow || 0) - (a.scores?.optionsFlow || 0),
    }),
    [],
  );

  // --- DATA PROCESSING ---
  const processedSignals = useMemo(() => {
    const signalsArray = signalsData?.signals || [];
    const kellyArray = kellyData?.kellyRanked || kellyData?.kelly || [];
    if (!signalsArray.length) return [];
    let merged = signalsArray.map((sig) => {
      const kelly = kellyArray.find((k) => k.symbol === sig.symbol);
      return {
        ...sig,
        kellyPercent: kelly?.optimalFraction || sig.kellyPercent || 0,
      };
    });
    const sortFn = SORT_MAP[activeSortKey] || SORT_MAP["Composite Score"];
    return merged.sort(sortFn);
  }, [signalsData, kellyData, activeSortKey, SORT_MAP]);

  const scoreFilterSpec = useMemo(() => SCORE_FILTERS.find((f) => f.id === scoreFilter) || SCORE_FILTERS[0], [scoreFilter]);
  const displayedSignals = useMemo(() => {
    if (scoreFilter === "all") return processedSignals;
    return processedSignals.filter((s) => {
      const sc = s.score ?? s.confidence ?? 0;
      return sc >= scoreFilterSpec.min && sc <= scoreFilterSpec.max;
    });
  }, [processedSignals, scoreFilter, scoreFilterSpec]);

  // Auto-select first symbol for right panel only when none selected — stay on dashboard (do not navigate)
  useEffect(() => {
    if (processedSignals.length > 0 && !selectedSymbol) {
      setSelectedSymbol(processedSignals[0].symbol);
    }
  }, [processedSignals, selectedSymbol]);

  const selectedSignal = useMemo(() => {
    const fromTable = processedSignals.find((s) => s.symbol === selectedSymbol) || processedSignals[0];
    return fromTable || null;
  }, [processedSignals, selectedSymbol]);

  // --- EXECUTION HANDLER ---
  const handleExecute = useCallback(
    async (action) => {
      const side = action === "BUY" ? "buy" : "sell";
      const qty = String(riskData?.proposal?.proposedSize || 100);
      if (!window.confirm(`Execute ${action} ${qty} shares of ${selectedSymbol}?`)) return;
      try {
        const body = {
          symbol: selectedSymbol,
          side,
          type: riskData?.proposal?.limitPrice ? "limit" : "market",
          time_in_force: "day",
          qty,
        };
        if (riskData?.proposal?.limitPrice) {
          body.limit_price = String(riskData.proposal.limitPrice);
        }
        if (riskData?.proposal?.stopLoss) {
          body.order_class = "bracket";
          body.stop_loss = { stop_price: String(riskData.proposal.stopLoss) };
          if (riskData?.proposal?.takeProfit) {
            body.take_profit = { limit_price: String(riskData.proposal.takeProfit) };
          }
        }
        const res = await fetch(getApiUrl("orders/advanced"), {
          method: "POST",
          headers: { "Content-Type": "application/json", ...getAuthHeaders() },
          body: JSON.stringify(body),
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          throw new Error(detail?.detail || `HTTP ${res.status}`);
        }
        toast.success(`${action} ${selectedSymbol} executed`);
      } catch (err) {
        log.error("Execution failed:", err);
        toast.error(`Execution failed: ${err.message}`);
      }
    },
    [selectedSymbol, riskData],
  );

  // --- ACTION HANDLERS ---
  const handleRunScan = useCallback(async () => {
    try {
      const res = await fetch(getApiUrl("signals"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        const msg = detail?.detail || detail?.message || `HTTP ${res.status}`;
        log.error("Scan failed:", msg);
        toast?.error?.(`Scan failed: ${msg}`);
        return;
      }
      toast?.success?.("Scan complete");
    } catch (e) {
      log.error("Scan error:", e);
      toast?.error?.(`Scan error: ${e?.message || "network error"}`);
    }
  }, []);
  const handleExecTop5 = useCallback(async () => {
    const top5 = displayedSignals.slice(0, 5);
    if (!top5.length) { toast.warn("No signals to execute"); return; }
    const names = top5.map((s) => `${s.symbol} ${s.direction || "LONG"}`).join(", ");
    if (!window.confirm(`Execute top 5: ${names}?`)) return;
    let ok = 0;
    for (const sig of top5) {
      try {
        const res = await fetch(getApiUrl("orders/advanced"), {
          method: "POST",
          headers: { "Content-Type": "application/json", ...getAuthHeaders() },
          body: JSON.stringify({
            symbol: sig.symbol,
            side: sig.direction === "LONG" ? "buy" : "sell",
            type: "market",
            time_in_force: "day",
            qty: "100",
          }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        ok++;
      } catch (e) {
        log.error("Exec top 5 item failed:", e);
      }
    }
    toast.info(`Exec Top 5: ${ok}/${top5.length} orders sent`);
  }, [displayedSignals]);
  const handleFlatten = useCallback(async () => {
    if (!window.confirm("Flatten ALL positions? This cannot be undone.")) return;
    try {
      const res = await fetch(getApiUrl("orders/flatten-all"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        log.error("Flatten failed:", res.status, err?.detail ?? err);
        toast.error(`Flatten failed: ${err?.detail?.message ?? err?.detail ?? res.statusText}`);
        return;
      }
      toast.success("All positions flattened");
    } catch (e) {
      log.error(e);
      toast.error(`Flatten failed: ${e?.message ?? "network error"}`);
    }
  }, []);
  const handleEmergencyStop = useCallback(async () => {
    if (!window.confirm("EMERGENCY STOP: Cancel all orders and close all positions?")) return;
    try {
      const res = await fetch(getApiUrl("orders/emergency-stop"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        log.error("Emergency stop failed:", res.status, err?.detail ?? err);
        toast.error(`Emergency stop failed: ${err?.detail?.message ?? err?.detail ?? res.statusText}`);
        return;
      }
      toast.success("Emergency stop executed");
    } catch (e) {
      log.error(e);
      toast.error(`Emergency stop failed: ${e?.message ?? "network error"}`);
    }
  }, []);

  // Toggle Manual (shadow) vs Automated (AI/Embodier buys and sells) trading mode
  const handleSetAutoExecute = useCallback(async (enabled) => {
    try {
      const res = await fetch(getApiUrl("metricsSetAutoExecute"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ enabled }),
      });
      const data = res.ok ? await res.json().catch(() => ({})) : null;
      if (!res.ok) {
        log.error("Set auto-execute failed:", res.status, data?.detail ?? data?.error);
        return;
      }
      setAutoExec(!!enabled);
      refetchMetrics();
    } catch (e) {
      log.error("Set auto-execute error:", e);
    }
  }, [refetchMetrics]);

  const handleExportCSV = useCallback(() => {
    const data = displayedSignals;
    if (!data.length) { toast.warn("No signals to export"); return; }
    const headers = ["symbol","direction","score","entry","target","stop","rMultiple","kellyPercent"];
    const rows = data.map(s => headers.map(h => `"${s[h] ?? ""}"`).join(","));
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const fname = `signals_export_${new Date().toISOString().slice(0, 10)}.csv`;
    const a = document.createElement("a"); a.href = url; a.download = fname; a.click();
    URL.revokeObjectURL(url);
    toast.success(`Exported ${data.length} signals`);
  }, [displayedSignals]);

  const handleSpawnAgent = useCallback(() => {
    navigate("/agents");
  }, []);

  const handleRefreshAll = useCallback(() => {
    refetchStatus();
    refetchSignals();
    refetchKelly();
    refetchPortfolio();
    refetchIndices();
    refetchOpenclaw();
    refetchPerformance();
    refetchPerformanceEquity();
    refetchConsensus();
    refetchRiskScore();
    refetchAlerts();
    refetchFlywheel();
    refetchSentiment();
    refetchCognitive();
    refetchDataSources();
    refetchMetrics();
    if (selectedSymbol) {
      refetchRisk();
      refetchQuotes();
    }
  }, [
    refetchStatus, refetchSignals, refetchKelly, refetchPortfolio, refetchIndices,
    refetchOpenclaw, refetchPerformance, refetchPerformanceEquity, refetchConsensus,
    refetchRiskScore, refetchAlerts, refetchFlywheel, refetchSentiment, refetchCognitive,
    refetchDataSources, refetchMetrics, refetchRisk, refetchQuotes, selectedSymbol,
  ]);

  // Council verdict highlight: show cyan glow on row for 1.5s when verdict matches symbol
  useEffect(() => {
    const verdict = councilLatestData?.verdict ?? councilLatestData?.decision ?? councilLatestData;
    const symbol = verdict?.symbol ?? verdict?.ticker ?? councilLatestData?.symbol;
    if (symbol) {
      setCouncilVerdictSymbol(String(symbol).toUpperCase());
      if (councilGlowRef.current) clearTimeout(councilGlowRef.current);
      councilGlowRef.current = setTimeout(() => {
        setCouncilVerdictSymbol(null);
        councilGlowRef.current = null;
      }, 1500);
    }
    return () => {
      if (councilGlowRef.current) clearTimeout(councilGlowRef.current);
    };
  }, [councilLatestData]);

  // --- KEYBOARD SHORTCUTS ---
  useEffect(() => {
    const handler = (e) => {
      if (e.key === "F5") {
        e.preventDefault();
        handleRunScan();
      }
      if (e.key === "F7") {
        e.preventDefault();
        handleExportCSV();
      }
      if (
        e.key === "n" &&
        !e.ctrlKey &&
        !e.metaKey &&
        document.activeElement?.tagName !== "INPUT"
      ) {
        handleSpawnAgent();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handleRunScan, handleExportCSV, handleSpawnAgent]);

  // Safe data extraction
  const portfolio = portfolioData?.portfolio || portfolioData || {};
  const rawIndices = indicesData?.marketIndices || indicesData || {};
  const indices = useMemo(() => {
    const arr = rawIndices?.indices;
    if (Array.isArray(arr)) {
      const map = {};
      arr.forEach((e) => {
        if (e && e.id != null)
          map[e.id] = {
            value: e.value,
            change: e.change,
            price: e.value,
            changePct: e.change,
            ...e,
          };
      });
      return map;
    }
    return rawIndices;
  }, [rawIndices]);
  const openclaw = useMemo(() => {
    const raw = openclawData?.openclaw || openclawData || {};
    const regime = raw.regime === "UNKNOWN" || !raw.regime ? "NEUTRAL" : raw.regime;
    return { ...raw, regime, compositeScore: raw.compositeScore ?? null };
  }, [openclawData]);
  const performance = useMemo(() => {
    const p = performanceData?.performance || performanceData || {};
    const equityCurve = performanceEquityData?.equity_curve ?? performanceEquityData?.equity ?? p.equityCurve ?? [];
    return {
      ...p,
      sharpe: p.sharpe ?? p.sharpeRatio ?? null,
      alpha: p.alpha ?? null,
      winRate: p.winRate ?? p.win_rate ?? null,
      maxDrawdown: p.maxDrawdown ?? p.max_drawdown ?? null,
      equityCurve: Array.isArray(equityCurve) ? equityCurve : [],
    };
  }, [performanceData, performanceEquityData]);
  const techs = useMemo(() => {
    const raw = techsData?.technicals || techsData?.indicators || techsData || {};
    const ind = techsData?.indicators || {};
    return {
      rsi: raw.rsi ?? ind.rsi ?? null,
      macd: raw.macd ?? ind.macd ?? null,
      bb: raw.bb ?? ind.bb ?? null,
      vwap: raw.vwap ?? ind.vwap ?? null,
      ema20: raw.ema20 ?? (ind.ma_20_dist != null ? `MA20 ${Number(ind.ma_20_dist).toFixed(2)}` : null),
      sma50: raw.sma50 ?? ind.sma50 ?? null,
      adx: raw.adx ?? ind.adx ?? null,
      stoch: raw.stoch ?? ind.stoch ?? null,
      driftScore: raw.driftScore ?? raw.drift ?? null,
      shapFeatures: raw.shapFeatures ?? techsData?.shapFeatures ?? [],
      ...raw,
    };
  }, [techsData]);
  const swarm = swarmData?.swarmTopology || swarmData || {};
  const consensus = consensusData?.votes ?? consensusData?.agents ?? swarm?.agents ?? [];
  const consensusVerdict = consensusData?.verdict ?? consensusData?.consensus ?? swarm?.consensus;
  const swarmForConsensus = useMemo(() => ({
    ...swarm,
    agents: Array.isArray(consensus) && consensus.length > 0 ? consensus.map((v) => ({
      name: v.name ?? v.agent_name ?? v.agent,
      vote: v.vote ?? v.verdict,
      confidence: v.confidence ?? v.agreement ?? 50,
    })) : swarm?.agents ?? [],
    consensus: consensusData?.agreement_percent ?? consensusData?.agreement ?? swarm?.consensus,
  }), [swarm, consensus, consensusData]);
  const sourcesList = useMemo(() => {
    const raw = dataSourcesData?.dataSources ?? dataSourcesData?.sources ?? dataSourcesData;
    return Array.isArray(raw) ? raw : (raw && typeof raw === "object" ? Object.values(raw) : []);
  }, [dataSourcesData]);
  const sourcesConnected = useMemo(
    () => sourcesList.filter((s) => (s?.status === "healthy" || s?.status === "active")).length,
    [sourcesList]
  );
  const risk = useMemo(() => {
    const r = riskData?.proposal || riskData || {};
    return {
      limitPrice: r.limitPrice ?? r.limit_price ?? 0,
      shares: r.shares ?? r.proposedSize ?? r.maxShares ?? 0,
      notional: r.notional ?? r.maxNotional ?? 0,
      stopLoss: r.stopLoss ?? r.stop_loss ?? 0,
      target1: r.target1 ?? r.takeProfit ?? r.target ?? 0,
      rr: r.rr ?? r.rMultiple ?? "0",
      ...r,
    };
  }, [riskData]);
  const quotes = useMemo(() => {
    const q = quotesData?.book || quotesData || {};
    const bids = Array.isArray(q.bids) ? q.bids : [];
    const asks = Array.isArray(q.asks) ? q.asks : [];
    const spread = q.spread ?? (asks[0]?.price != null && bids[0]?.price != null ? Number(asks[0].price) - Number(bids[0].price) : 0);
    return {
      bids,
      asks,
      spread: spread != null ? Number(spread) : 0,
      ...q,
    };
  }, [quotesData]);
  const agents = agentsData?.agents || agentsData || {};
  const riskScore = useMemo(() => {
    const r = riskScoreData?.riskScore || riskScoreData || {};
    const score = r.score ?? r.risk_score ?? riskScoreData?.score ?? null;
    return {
      ...r,
      score: typeof score === "number" ? score : null,
      risk_score: r.risk_score ?? score,
      dailyVaR: r.dailyVaR ?? r.riskScore?.dailyVaR,
      correlation: r.correlation ?? r.riskScore?.correlation,
      positionLimit: r.positionLimit ?? r.riskScore?.positionLimit,
      status: r.status ?? r.riskScore?.status ?? "Active",
    };
  }, [riskScoreData]);
  const alerts = alertsData?.alerts || alertsData?.systemAlerts || [];
  const flywheel = useMemo(() => flywheelData?.flywheel || flywheelData || {}, [flywheelData]);
  const globalSentiment = useMemo(() => {
    const s = sentimentData?.sentiment || sentimentData || {};
    const score = s.score ?? s.global_score ?? s.sentiment ?? null;
    return { ...s, score: score != null ? Number(score) : null };
  }, [sentimentData]);

  // --- LOADING / ERROR STATES ---
  // Only show boot screen on very first load (no data AND no error yet)
  if (sigLoading && !signalsData && !sigErr)
    return (
      <div className="h-full w-full bg-[#0B0E14] flex items-center justify-center text-[#00D9FF] font-mono text-xs">
        INITIALIZING EMBODIER NEURAL NET...
      </div>
    );
  /* sigErr no longer blocks the entire page — we show a banner instead
     so that non-signal panels (portfolio, risk, etc.) remain usable. */

  // Only show "API OFFLINE" when the API server is unreachable (status check failed)
  const showApiOffline = !apiOnline && apiStatusError;
  const endpointIssues = [
    portfolioErr && "Portfolio",
    sigErr && "Signals",
    indicesErr && "Market Data",
    openclawErr && "OpenClaw",
  ].filter(Boolean);

  return (
    <div className="-m-6 -mb-10 flex flex-col h-[calc(100%+3.5rem)] w-[calc(100%+3rem)] bg-[#0B0E14] text-[#e5e7eb] font-sans text-[9px] leading-tight overflow-y-auto selection:bg-[#00D9FF]/30">
      {/* API OFFLINE — only when backend is unreachable (status check failed) */}
      {showApiOffline && (
        <div className="px-4 py-1.5 bg-red-500/10 border-b border-red-500/30 text-red-400 text-[10px] flex items-center gap-2 shrink-0 flex-wrap">
          <span className="font-bold">API OFFLINE</span>
          <span>— Backend unreachable. From repo root run:</span>
          <code className="bg-black/30 px-1 rounded">.\scripts\run_all_autorestart.ps1</code>
          <span className="text-red-300/80">or</span>
          <code className="bg-black/30 px-1 rounded">cd backend && .\scripts\run_backend_autorestart.ps1</code>
        </div>
      )}
      {/* Some endpoints unavailable (API is online but a few failed) */}
      {apiOnline && endpointIssues.length > 0 && (
        <div className="px-4 py-1 bg-amber-500/10 border-b border-amber-500/20 text-amber-400 text-[9px] shrink-0">
          <span className="font-bold">Partial:</span> {endpointIssues.join(", ")} — data may be stale
        </div>
      )}
      {/* TOP HEADER BAR */}
      <header className="flex items-center justify-between px-4 py-1.5 border-b border-[rgba(42,52,68,0.5)] bg-[#111827] shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 pr-4 border-r border-[rgba(42,52,68,0.5)]">
            <HexagonLogo />
            <h1 className="text-xs font-bold text-white tracking-widest">
              EMBODIER TRADER
            </h1>
          </div>
          <button
            type="button"
            onClick={handleRefreshAll}
            className="px-2 py-0.5 rounded text-[9px] font-mono font-bold bg-[#00D9FF]/20 text-[#00D9FF] border border-[#00D9FF]/50 hover:bg-[#00D9FF]/30 transition-colors"
          >
            Refresh All
          </button>
          {/* Manual vs Automated trading — lever on landing page */}
          <div className="flex items-center gap-0 rounded border border-[rgba(42,52,68,0.5)] bg-[#0f172a]/80 overflow-hidden">
            <span className="px-2 py-0.5 text-[9px] text-slate-500 font-bold uppercase tracking-wider border-r border-[rgba(42,52,68,0.5)]">
              Trading
            </span>
            <button
              type="button"
              onClick={() => handleSetAutoExecute(false)}
              className={`px-2.5 py-0.5 text-[9px] font-mono font-bold transition-colors ${!autoExec ? "bg-amber-500/25 text-amber-300 border-amber-500/50" : "text-slate-400 hover:bg-white/5 hover:text-slate-300"}`}
              title="You place all trades manually; council runs in shadow (no orders sent)"
            >
              Manual
            </button>
            <button
              type="button"
              onClick={() => handleSetAutoExecute(true)}
              className={`px-2.5 py-0.5 text-[9px] font-mono font-bold transition-colors ${autoExec ? "bg-emerald-500/25 text-emerald-300 border-emerald-500/50" : "text-slate-400 hover:bg-white/5 hover:text-slate-300"}`}
              title="AI and Embodier Trader buy and sell automatically from council verdicts (paper/live)"
            >
              Automated
            </button>
          </div>
          {/* Regime Badges */}
          <div
            className={`px-2 py-0.5 rounded font-bold tracking-wider ${openclaw.regime === "BEAR" ? "bg-red-500/20 text-red-400 border border-red-500/50" : "bg-green-500/20 text-green-400 border border-green-500/50"}`}
          >
            {openclaw.regime || "\u2014"}
          </div>
          <div className="flex items-center gap-1">
            <span className="text-[#94a3b8]">SCORE</span>
            <div className="w-6 h-6 rounded-full border-2 border-green-400 flex items-center justify-center text-[10px] font-mono text-green-400 kpi-num">
              {openclaw.compositeScore != null && openclaw.compositeScore !== "" ? openclaw.compositeScore : "\u2014"}
            </div>
          </div>
          {/* Risk Score Badge */}
          <div
            className={`px-2 py-0.5 rounded font-bold ${(riskScore.score ?? riskScore.risk_score ?? 0) > 70 ? "bg-red-500/20 text-red-400 border border-red-500/50" : (riskScore.score ?? riskScore.risk_score ?? 0) > 40 ? "bg-amber-500/20 text-amber-400 border border-amber-500/50" : "bg-green-500/20 text-green-400 border border-green-500/50"}`}
          >
            RISK {riskScore.score ?? riskScore.risk_score ?? "\u2014"}
          </div>
          {/* Sentiment Badge */}
          <div
            className={`px-2 py-0.5 rounded font-bold ${(globalSentiment.score ?? 0) >= 60 ? "bg-green-500/20 text-green-400" : (globalSentiment.score ?? 0) >= 40 ? "bg-amber-500/20 text-amber-400" : "bg-red-500/20 text-red-400"}`}
          >
            SENT {globalSentiment.score ?? globalSentiment.value ?? "\u2014"}
          </div>
          {/* Data Sources — flows from GET /api/v1/data-sources/ */}
          <button
            type="button"
            onClick={() => navigate("/data-sources")}
            className="px-2 py-0.5 rounded font-bold bg-[#00D9FF]/20 text-[#00D9FF] border border-[#00D9FF]/40 hover:bg-[#00D9FF]/30 transition-colors"
          >
            SOURCES {sourcesConnected}/{sourcesList.length || "\u2014"}
          </button>
        </div>
        {/* KPIs */}
        <div className="flex items-center gap-4 font-mono text-[10px]">
          <div className="flex gap-3 text-[#94a3b8]">
            <span>
              SPX{" "}
              <span className={indices.SPX?.change != null && indices.SPX.change >= 0 ? "text-green-400" : indices.SPX?.change != null ? "text-red-400" : "text-slate-500"}>
                {indices.SPX?.change != null ? `${indices.SPX.change >= 0 ? "+" : ""}${Number(indices.SPX.change).toFixed(2)}%` : "\u2014"}
              </span>
            </span>
            <span>
              NDAQ{" "}
              <span className={indices.NDAQ?.change != null && indices.NDAQ.change >= 0 ? "text-green-400" : indices.NDAQ?.change != null ? "text-red-400" : "text-slate-500"}>
                {indices.NDAQ?.change != null ? `${indices.NDAQ.change >= 0 ? "+" : ""}${Number(indices.NDAQ.change).toFixed(2)}%` : "\u2014"}
              </span>
            </span>
            <span>
              BTC{" "}
              <span className={indices.BTC?.change != null && indices.BTC.change >= 0 ? "text-green-400" : indices.BTC?.change != null ? "text-red-400" : "text-slate-500"}>
                {indices.BTC?.change != null ? `${indices.BTC.change >= 0 ? "+" : ""}${Number(indices.BTC.change).toFixed(2)}%` : "\u2014"}
              </span>
            </span>
          </div>
          <div className="w-px h-4 bg-[#1e293b]"></div>
          <div className="flex gap-4">
            <span>
              Equity{" "}
              <span className="text-white font-mono kpi-num">
                {portfolio.totalEquity != null ? `$${Number(portfolio.totalEquity).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}` : "\u2014"}
              </span>
            </span>
            <span>
              P&L{" "}
              <span className={`font-mono kpi-num ${portfolio.dayPnL != null ? (Number(portfolio.dayPnL) >= 0 ? "text-green-400" : "text-red-400") : "text-slate-500"}`}>
                {portfolio.dayPnL != null ? `${Number(portfolio.dayPnL) >= 0 ? "+" : ""}$${Number(portfolio.dayPnL).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}` : "\u2014"}
              </span>
            </span>
            <span>
              Deployed{" "}
              <span className="text-[#00D9FF] font-mono kpi-num">
                {portfolio.deployedPercent != null ? `${Number(portfolio.deployedPercent).toFixed(1)}%` : "\u2014"}
              </span>
            </span>
            <span>
              Sharpe{" "}
              <span className="text-[#00D9FF] font-mono kpi-num">
                {performance.sharpe != null && performance.sharpe !== "" ? Number(performance.sharpe) : "\u2014"}
              </span>
            </span>
            <span>
              Alpha{" "}
              <span className="text-green-400 font-mono kpi-num">
                {performance.alpha != null && performance.alpha !== "" ? `+${Number(performance.alpha)}%` : "\u2014"}
              </span>
            </span>
            <span>
              Win{" "}
              <span className="text-green-400 font-mono kpi-num">
                {performance.winRate != null && performance.winRate !== "" ? `${Number(performance.winRate)}%` : "\u2014"}
              </span>
            </span>
            <span>
              MaxDD{" "}
              <span className="text-red-400 font-mono kpi-num">
                {performance.maxDrawdown != null && performance.maxDrawdown !== "" ? `${Number(performance.maxDrawdown)}%` : "\u2014"}
              </span>
            </span>
          </div>
        </div>
      </header>

      {/* SCROLLING TICKER STRIP */}
      <TickerStrip indices={indices} signals={processedSignals} onSelectSymbol={setSelectedSymbol} />

      {/* Data Sources strip — API /api/v1/data-sources/ flowing through landing page */}
      {(dataSourcesLoading || sourcesList.length > 0) && (
        <div className="px-4 py-1.5 border-b border-[rgba(42,52,68,0.5)] bg-[#111827]/80 shrink-0 flex items-center gap-4 flex-wrap">
          <span className="text-[9px] font-bold uppercase tracking-wider text-slate-500 font-mono">Data Sources</span>
          {dataSourcesLoading && sourcesList.length === 0 ? (
            <span className="text-[9px] text-slate-500 font-mono">Loading…</span>
          ) : (
          <div className="flex items-center gap-3 flex-wrap">
            {sourcesList.slice(0, 12).map((s, i) => {
              const ok = s?.status === "healthy" || s?.status === "active";
              return (
                <button
                  key={s?.id || s?.name || `ds-${i}`}
                  type="button"
                  onClick={() => navigate("/data-sources")}
                  className="inline-flex items-center gap-1.5 text-[9px] font-mono hover:text-[#00D9FF] transition-colors"
                >
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${ok ? "bg-emerald-400" : "bg-slate-500"}`} />
                  <span className="text-slate-300">{s?.name || s?.id || "—"}</span>
                </button>
              );
            })}
          </div>
          )}
          <button
            type="button"
            onClick={() => navigate("/data-sources")}
            className="text-[9px] font-mono text-[#00D9FF] hover:text-white transition-colors ml-auto"
          >
            View all →
          </button>
        </div>
      )}

      {/* Signal error card with Retry (refetch all) */}
      {sigErr && (
        <div className="mx-4 mt-1 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-[10px] font-mono flex items-center justify-between gap-2 shrink-0">
          <span className="font-bold">SIGNAL API ERROR</span>
          <span className="text-red-400/70 flex-1 truncate">{sigErr.message}</span>
          <button
            type="button"
            onClick={handleRefreshAll}
            className="px-2.5 py-1 rounded bg-red-500/20 hover:bg-red-500/30 text-white font-bold border border-red-500/50 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* MAIN CONTENT AREA: Center Table + Right Panel */}
      <main className="flex flex-1 overflow-hidden">
        {/* CENTER COLUMN: Sort Pills + Table (dominant area); amber top-border when stale */}
        <section className={`flex flex-col flex-1 min-w-0 border-r border-[rgba(42,52,68,0.5)] bg-[#0B0E14] ${sigStale ? "border-t-2 border-amber-500" : ""}`}>
          {/* Sort Pills Row */}
          <div className="flex items-center gap-1.5 px-2 py-1.5 border-b border-[rgba(42,52,68,0.5)] bg-[#111827] shrink-0 overflow-x-auto no-scrollbar">
            {SORT_PILLS.map((pill) => (
              <button
                key={pill}
                onClick={() => setActiveSortKey(pill)}
                className={`whitespace-nowrap px-2 py-0.5 rounded-sm border text-[8px] ${activeSortKey === pill ? "bg-[#00D9FF]/20 text-[#00D9FF] border-[#00D9FF]/50" : "bg-transparent text-[#94a3b8] border-[#374151] hover:border-[#64748b]"} transition-colors`}
              >
                {pill}
              </button>
            ))}
          </div>

          {/* Timeframe + Status Row */}
          <div className="flex items-center justify-between px-2 py-1 border-b border-[rgba(42,52,68,0.5)] bg-[#111827] shrink-0 text-[#94a3b8] font-mono">
            <div className="flex items-center gap-1">
              <span className="text-[8px]">TF:</span>
              {TIMEFRAMES.map((tf) => (
                <button
                  key={tf}
                  onClick={() => setActiveTimeframe(tf)}
                  className={`px-1.5 py-0.5 rounded-sm text-[8px] ${activeTimeframe === tf ? "bg-[#1e293b] text-white" : "hover:bg-[#1e293b]/50"}`}
                >
                  {tf}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-3 text-[8px]">
              <button
                onClick={() => handleSetAutoExecute(!autoExec)}
                className="flex items-center gap-1 cursor-pointer hover:text-white transition-colors"
              >
                <div className={`w-1.5 h-1.5 rounded-full ${autoExec ? "bg-green-500 animate-pulse" : "bg-red-500"}`} />
                Auto-Exec: {autoExec ? "ON" : "OFF"}
              </button>
              <span className="flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" /> LIVE
              </span>
              <span>Flywheel: {flywheel.accuracy != null ? `${Number(flywheel.accuracy)}%` : flywheel.accuracy30d != null ? `${Math.round(Number(flywheel.accuracy30d) * 100)}%` : "\u2014"}</span>
            </div>
          </div>

          {/* MAIN SIGNALS TABLE */}
          <div className="flex-1 overflow-auto bg-[#0B0E14]">
            <table className="w-full text-left font-mono whitespace-nowrap">
              <thead className="sticky top-0 bg-[#111827] text-[10px] uppercase text-slate-500 border-b border-[rgba(42,52,68,0.5)] shadow-md z-10">
                <tr>
                  {TABLE_SORT_COLUMNS.map((col, i) => (
                    <th
                      key={i}
                      className={`px-1.5 py-1 font-semibold ${col.sortKey ? "cursor-pointer hover:text-[#00D9FF] hover:bg-[#1e293b]/50 transition-colors" : ""}`}
                      onClick={col.sortKey ? () => setActiveSortKey(col.sortKey) : undefined}
                    >
                      {col.label}
                    </th>
                  ))}
                  <th className="px-1.5 py-1 font-semibold w-20">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e293b]/50">
                {displayedSignals.map((sig, idx) => {
                  const isSelected = selectedSymbol === sig.symbol;
                  const isLong = sig.direction === "LONG";
                  const dirColor = isLong ? "text-green-400" : "text-red-400";
                  const hasCouncilGlow = councilVerdictSymbol === sig.symbol;
                  return (
                    <tr
                      key={sig.symbol + idx}
                      onClick={() => navigate(`/symbol/${encodeURIComponent(sig.symbol)}`)}
                      className={`cursor-pointer hover:bg-[#1e293b]/30 transition-colors ${isSelected ? "bg-[#164e63]/30 border-l-2 border-[#00D9FF]" : "border-l-2 border-transparent"} ${hasCouncilGlow ? "animate-cyan-glow" : ""}`}
                      style={hasCouncilGlow ? { boxShadow: "inset 0 0 12px rgba(0,217,255,0.4)" } : undefined}
                    >
                      <td className="px-1.5 py-1 text-[0.65rem] text-white font-bold font-mono">{sig.symbol}</td>
                      <td className={`px-1.5 py-1 text-[0.65rem] font-mono ${dirColor}`}>{isLong ? "L" : "S"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem]">
                        <div className="flex items-center gap-1">
                          <span className={`font-mono kpi-num ${(sig.score ?? 0) >= 90 ? "text-green-400" : "text-[#00D9FF]"}`}>{sig.score ?? "\u2014"}</span>
                          <div className="w-12 h-1.5 bg-[#1e293b] rounded-full overflow-hidden">
                            <div className="h-full rounded-full transition-all duration-200" style={{ width: `${sig.score ?? 0}%`, backgroundColor: (sig.score ?? 0) >= 85 ? "#10b981" : (sig.score ?? 0) >= 70 ? "#00D9FF" : (sig.score ?? 0) >= 50 ? "#f59e0b" : "#ef4444" }} />
                          </div>
                        </div>
                      </td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#94a3b8] font-mono">{sig.scores?.regime || "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#94a3b8] font-mono">{sig.scores?.ml || "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#94a3b8] font-mono">{sig.scores?.sentiment || "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#94a3b8] font-mono">{sig.scores?.technical || "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#00D9FF] truncate max-w-[80px] font-mono">{sig.leadAgent || "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#94a3b8] font-mono">{sig.swarmVote || "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#64748b] truncate max-w-[60px] font-mono">{sig.topShap || "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#00D9FF] font-mono">{sig.kellyPercent != null ? `${sig.kellyPercent}%` : "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#94a3b8] font-mono">{sig.entry != null ? `$${Number(sig.entry).toFixed(2)}` : "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-green-400 font-mono">{sig.target != null ? `$${Number(sig.target).toFixed(2)}` : "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-red-400 font-mono">{sig.stop != null ? `$${Number(sig.stop).toFixed(2)}` : "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-white font-mono">{sig.rMultiple != null ? `${Number(sig.rMultiple).toFixed(1)}:1` : "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-green-400 font-mono">{sig.expPnL != null ? `+$${Number(sig.expPnL).toLocaleString()}` : "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#64748b] font-mono">{sig.sector?.substring(0, 3) || "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-green-400 font-mono">{sig.momentum != null ? `+${sig.momentum}` : "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#00D9FF] font-mono">{sig.volSpike != null ? `${sig.volSpike}x` : "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#64748b] truncate max-w-[50px] font-mono">{sig.newsImpact ?? "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#00D9FF] truncate max-w-[60px] font-mono">{sig.pattern ?? "\u2014"}</td>
                      <td className="px-1.5 py-1" onClick={(e) => e.stopPropagation()}>
                        <button
                          type="button"
                          onClick={() => fetchCouncilEvaluate(sig.symbol, "15m", {}).then(() => {}).catch((err) => log.error("Council evaluate failed", err))}
                          className="px-1.5 py-0.5 rounded text-[7px] font-mono font-bold bg-[#00D9FF]/20 text-[#00D9FF] border border-[#00D9FF]/50 hover:bg-[#00D9FF]/30 transition-colors"
                        >
                          Send to Council
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Inline Action Buttons Row */}
          <div className="flex items-center gap-2 px-2 py-1.5 border-t border-[rgba(42,52,68,0.5)] bg-[#111827] shrink-0">
            <button onClick={handleRunScan} className="bg-[#1e293b] hover:bg-[#374151] text-white px-3 py-1 rounded text-[8px] font-mono border border-[#374151]">
              Run Scan [F5]
            </button>
            <button onClick={handleExportCSV} className="bg-[#1e293b] hover:bg-[#374151] text-white px-3 py-1 rounded text-[8px] font-mono border border-[#374151]">
              Export CSV [F7]
            </button>
            <button onClick={handleExecTop5} className="bg-cyan-900/60 hover:bg-cyan-800 text-[#00D9FF] px-3 py-1 rounded text-[8px] font-mono border border-cyan-700/50">
              Exec Top 5
            </button>
            <div className="flex-1" />
            <span className="text-[8px] font-mono text-[#64748b]">
              {displayedSignals.length} signals{scoreFilter !== "all" ? ` (${scoreFilter})` : ""}
            </span>
          </div>

          {/* Alerts Bar */}
          {Array.isArray(alerts) && alerts.length > 0 && (
            <div className="bg-amber-900/30 border-t border-amber-500/50 px-3 py-1 shrink-0 overflow-x-auto no-scrollbar">
              <div className="flex items-center gap-4 text-[8px] font-mono text-amber-400">
                <span className="font-bold">ALERTS:</span>
                {alerts.slice(0, 5).map((a, i) => (
                  <span key={i} className="whitespace-nowrap">{a.message || a.msg || a}</span>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* RIGHT COLUMN: Intelligence Panel (~32%); amber top-border when stale */}
        <section className={`flex flex-col w-[32%] bg-[#111827] overflow-y-auto custom-scrollbar ${sigStale ? "border-t-2 border-amber-500" : ""}`}>
          {/* Symbol search: type ticker and Go to load right-panel data */}
          <div className="flex items-center gap-1.5 px-2.5 py-2 border-b border-[rgba(42,52,68,0.5)]">
            <input
              type="text"
              placeholder="Symbol (e.g. AAPL)"
              value={symbolSearch}
              onChange={(e) => setSymbolSearch(e.target.value || "")}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  const sym = (symbolSearch || "").trim().toUpperCase();
                  if (sym) { setSelectedSymbol(sym); setSymbolSearch(""); }
                }
              }}
              className="flex-1 min-w-0 px-2 py-1.5 rounded bg-[#0B0E14] border border-[#374151] text-white text-[10px] font-mono placeholder:text-[#64748b] focus:border-[#00D9FF] focus:outline-none"
            />
            <button
              type="button"
              onClick={() => {
                const sym = (symbolSearch || "").trim().toUpperCase();
                if (sym) { setSelectedSymbol(sym); setSymbolSearch(""); }
              }}
              className="px-2.5 py-1.5 rounded bg-[#00D9FF]/20 text-[#00D9FF] border border-[#00D9FF]/50 text-[10px] font-mono font-bold hover:bg-[#00D9FF]/30 transition-colors"
            >
              Go
            </button>
          </div>
          {/* Swarm Consensus Bars (prominent at top per mockup) — GET /api/v1/agents/consensus */}
          <div className="border-b border-[rgba(42,52,68,0.5)] p-2.5 space-y-1.5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">SWARM CONSENSUS</h3>
            {(swarmForConsensus.agents || []).slice(0, 6).map((agent, i) => (
              <ConsensusBar
                key={i}
                label={agent.name || `Agent ${i + 1}`}
                buyPct={agent.vote === "BUY" ? agent.confidence || 50 : 100 - (agent.confidence || 50)}
                sellPct={agent.vote === "SELL" ? agent.confidence || 50 : 0}
              />
            ))}
            {(!swarmForConsensus.agents || swarmForConsensus.agents.length === 0) && (
              <div className="text-[8px] text-[#64748b] font-mono py-2 text-center">
                Awaiting swarm agent data...
              </div>
            )}
          </div>

          {/* Signal Strength Bar Chart + filter pills */}
          <div className="border-b border-[rgba(42,52,68,0.5)] p-2.5">
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              {SCORE_FILTERS.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => setScoreFilter(f.id)}
                  className={`px-2 py-0.5 rounded text-[8px] font-mono font-bold border transition-colors ${
                    scoreFilter === f.id
                      ? "bg-[#00D9FF]/20 text-[#00D9FF] border-[#00D9FF]/50"
                      : "bg-[#1e293b]/50 text-[#64748b] border-[#374151] hover:border-[#64748b] hover:text-[#94a3b8]"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <SignalBarChart
              signals={displayedSignals.slice(0, 20)}
              selectedSymbol={selectedSymbol}
              onSelect={setSelectedSymbol}
            />
          </div>

          {/* Regime Donut + Trades Donut Row */}
          <div className="flex gap-2 border-b border-[rgba(42,52,68,0.5)] p-2.5">
            <div className="flex-1 flex flex-col items-center">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono mb-1">REGIME</span>
              <RegimeDonut regime={openclaw.regime} score={openclaw.compositeScore} />
            </div>
            <div className="flex-1 flex flex-col items-center">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono mb-1">TOP TRADES</span>
              <TopTradesDonut
                buyCount={swarm.buyCount || processedSignals.filter((s) => s.direction === "LONG").length}
                sellCount={swarm.sellCount || processedSignals.filter((s) => s.direction === "SHORT").length}
                holdCount={swarm.holdCount || Math.max(1, processedSignals.length - processedSignals.filter((s) => s.direction === "LONG").length - processedSignals.filter((s) => s.direction === "SHORT").length)}
              />
            </div>
          </div>

          {/* Selected Symbol Detail Panel (skeleton when no selection) */}
          {selectedSignal ? (
            <div className="border-b border-[rgba(42,52,68,0.5)] p-2.5 space-y-2">
              <div className="flex justify-between items-center flex-wrap gap-1">
                <h2 className="text-sm font-bold text-white flex items-center gap-1.5">
                  {selectedSignal.symbol}
                  <span className={selectedSignal.direction === "LONG" ? "text-green-400 text-[10px]" : "text-red-400 text-[10px]"}>
                    {selectedSignal.direction || "LONG"}
                  </span>
                </h2>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedSymbolAndUrl(selectedSignal.symbol)}
                    className="text-[10px] font-mono text-[#00D9FF] hover:text-cyan-300 underline"
                  >
                    Open full page
                  </button>
                  <span className="text-lg font-mono font-bold text-[#00D9FF]">{selectedSignal.score ?? 0}</span>
                </div>
              </div>

              {/* Composite Breakdown Bars */}
              <div className="space-y-1 font-mono text-[8px]">
                {[
                  { label: "Overall Score", val: `${selectedSignal.score ?? 0}/100`, pct: selectedSignal.score ?? 0 },
                  { label: "Technical Rank", val: String(selectedSignal.scores?.technical ?? 0), pct: selectedSignal.scores?.technical ?? 0 },
                  { label: "ML Probability", val: `${selectedSignal.scores?.ml ?? 0}%`, pct: selectedSignal.scores?.ml ?? 0 },
                  { label: "Sentiment Pulse", val: String(selectedSignal.scores?.sentiment ?? 0), pct: selectedSignal.scores?.sentiment ?? 0 },
                  { label: "Swarm Consensus", val: `${swarmForConsensus.consensus ?? swarm?.consensus ?? 0}%`, pct: swarmForConsensus.consensus ?? swarm?.consensus ?? 0 },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between">
                    <span className="text-[#94a3b8] w-24">{item.label}</span>
                    <div className="flex-1 mx-2 h-1.5 bg-[#1e293b] rounded-full">
                      <div className="h-full bg-[#00D9FF] rounded-full transition-all" style={{ width: `${Number(item.pct) || 0}%` }} />
                    </div>
                    <span className="text-white w-10 text-right">{item.val}</span>
                  </div>
                ))}
              </div>

              {/* Technical Analysis Grid (— when null, no mock) */}
              <div className="grid grid-cols-2 gap-1 font-mono text-[8px] bg-[#0B0E14] rounded p-1.5 border border-[rgba(42,52,68,0.3)]">
                <div><span className="text-[#64748b]">RSI:</span> <span className="text-green-400">{techs.rsi != null ? techs.rsi : "\u2014"}</span></div>
                <div><span className="text-[#64748b]">MACD:</span> <span className="text-green-400">{techs.macd != null ? techs.macd : "\u2014"}</span></div>
                <div><span className="text-[#64748b]">BB:</span> <span className="text-white">{techs.bb != null && techs.bb !== "" ? techs.bb : "\u2014"}</span></div>
                <div><span className="text-[#64748b]">VWAP:</span> <span className="text-[#00D9FF]">{techs.vwap != null ? techs.vwap : "\u2014"}</span></div>
                <div><span className="text-[#64748b]">20 EMA:</span> <span className="text-white">{techs.ema20 != null && techs.ema20 !== "" ? techs.ema20 : "\u2014"}</span></div>
                <div><span className="text-[#64748b]">50 SMA:</span> <span className="text-green-400">{techs.sma50 != null ? techs.sma50 : "\u2014"}</span></div>
                <div><span className="text-[#64748b]">ADX:</span> <span className="text-white">{techs.adx != null ? techs.adx : "\u2014"}</span></div>
                <div><span className="text-[#64748b]">Stoch:</span> <span className="text-green-400">{techs.stoch != null ? techs.stoch : "\u2014"}</span></div>
              </div>

              {/* SHAP Drivers */}
              <div className="font-mono text-[8px]">
                <div className="flex justify-between mb-1 text-[#64748b]">
                  <span>ML Prob: <span className="text-green-400 font-bold">{selectedSignal.scores?.ml ?? 0}%</span></span>
                  <span>Drift: <span className="text-green-400">{techs.driftScore != null ? techs.driftScore : "\u2014"}</span></span>
                </div>
                <div className="space-y-0.5">
                  {(techs.shapFeatures || selectedSignal.shapFeatures || []).slice(0, 5).map((s) => {
                    const imp = Number(s.impact) || 0;
                    const barW = Math.min(Math.abs(imp) * 500, 100);
                    return (
                      <div key={s.feature} className="flex items-center justify-between">
                        <span className="text-white truncate w-20">{s.feature}</span>
                        <div className="flex-1 flex items-center mx-1.5">
                          {imp < 0 ? (
                            <div className="w-1/2 flex justify-end"><div className="h-1.5 bg-red-500 rounded-sm" style={{ width: `${barW}%` }} /></div>
                          ) : (<div className="w-1/2" />)}
                          {imp > 0 && (
                            <div className="w-1/2"><div className="h-1.5 bg-green-500 rounded-sm" style={{ width: `${barW}%` }} /></div>
                          )}
                        </div>
                        <span className={imp > 0 ? "text-green-400 w-8 text-right" : "text-red-400 w-8 text-right"}>
                          {imp > 0 ? `+${imp.toFixed(2)}` : imp.toFixed(2)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="border-b border-[rgba(42,52,68,0.5)] p-2.5 space-y-2">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          )}

          {/* Risk & Order Proposal */}
          {selectedSignal && (
            <div className="border-b border-[rgba(42,52,68,0.5)] p-2.5 space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">RISK & ORDER PROPOSAL</h3>
              <div className="font-mono text-[8px]">
                <div className="grid grid-cols-2 gap-1 mb-1.5 pb-1.5 border-b border-[rgba(42,52,68,0.3)]">
                  <span className="text-[#94a3b8]">Action: <span className="text-white">{selectedSignal?.direction === "SHORT" ? "Limit Sell" : "Limit Buy"} {risk.limitPrice ?? 0}</span></span>
                  <span className="text-[#94a3b8]">Size: <span className="text-white">{risk.shares ?? 0} shs (${risk.notional ?? 0})</span></span>
                  <span className="text-[#94a3b8]">Stop Loss: <span className="text-red-400">{risk.stopLoss ?? 0}</span></span>
                  <span className="text-[#94a3b8]">Target 1: <span className="text-green-400">{risk.target1 ?? 0}</span></span>
                  <span className="text-[#94a3b8]">R:R Ratio: <span className="text-[#00D9FF]">{risk.rr ?? "0"}</span></span>
                  <span className="text-[#94a3b8]">Kelly: <span className="text-white">{selectedSignal.kellyPercent != null ? `${selectedSignal.kellyPercent}%` : "\u2014"}</span></span>
                </div>
                {/* L2 Order Book */}
                <div className="text-[#64748b] mb-1">L2 BOOK (Spread: ${Number(quotes.spread ?? 0).toFixed(2)})</div>
                <div className="flex flex-col gap-[1px]">
                  {quotes.asks?.slice(0, 3).reverse().map((ask, i) => (
                    <div key={"ask" + i} className="flex items-center text-[7px]">
                      <span className="w-10 text-red-400">{Number(ask.price).toFixed(2)}</span>
                      <span className="w-8 text-right mr-1">{ask.size}</span>
                      <div className="h-1.5 bg-red-500/30 rounded-sm" style={{ width: `${Math.min((Number(ask.size) / 1500) * 100, 100)}%` }} />
                    </div>
                  )) || <div className="text-[#64748b] text-center py-1">Awaiting L2 data...</div>}
                  <div className="h-px bg-[#1e293b] my-0.5" />
                  {quotes.bids?.slice(0, 3).map((bid, i) => (
                    <div key={"bid" + i} className="flex items-center text-[7px]">
                      <span className="w-10 text-green-400">{Number(bid.price).toFixed(2)}</span>
                      <span className="w-8 text-right mr-1">{bid.size}</span>
                      <div className="h-1.5 bg-green-500/30 rounded-sm" style={{ width: `${Math.min((Number(bid.size) / 1500) * 100, 100)}%` }} />
                    </div>
                  )) || <div className="text-[#64748b] text-center py-1">Awaiting L2 data...</div>}
                </div>
              </div>

              {/* Execution Buttons */}
              <div className="grid grid-cols-2 gap-1.5">
                <button onClick={() => handleExecute("BUY")} className="bg-green-600 hover:bg-green-500 text-white font-bold py-1.5 rounded text-[9px] shadow-[0_0_8px_rgba(16,185,129,0.4)]">
                  EXECUTE LONG
                </button>
                <button onClick={() => handleExecute("SELL")} className="bg-red-600 hover:bg-red-500 text-white font-bold py-1.5 rounded text-[9px] shadow-[0_0_8px_rgba(239,68,68,0.4)]">
                  EXECUTE SHORT
                </button>
              </div>
              <div className="grid grid-cols-3 gap-1">
                <button onClick={() => {
                  const body = {
                    symbol: selectedSymbol,
                    side: selectedSignal?.direction === "SHORT" ? "sell" : "buy",
                    type: "limit",
                    time_in_force: "day",
                    qty: String(riskData?.proposal?.proposedSize || 100),
                    limit_price: String(selectedSignal?.entry ?? selectedSignal?.price ?? riskData?.proposal?.limitPrice ?? 0),
                  };
                  fetch(getApiUrl("orders/advanced"), {
                    method: "POST",
                    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
                    body: JSON.stringify(body),
                  }).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
                    .then(() => alert(`Limit order placed: ${selectedSymbol}`))
                    .catch(e => alert(`Limit order failed: ${e.message}`));
                }} className="bg-[#1e293b] hover:bg-cyan-900 text-[#00D9FF] py-1 rounded text-[8px]">Limit</button>
                <button onClick={() => {
                  const body = {
                    symbol: selectedSymbol,
                    side: selectedSignal?.direction === "SHORT" ? "sell" : "buy",
                    type: "stop_limit",
                    time_in_force: "day",
                    qty: String(riskData?.proposal?.proposedSize || 100),
                    limit_price: String(selectedSignal?.entry ?? selectedSignal?.price ?? riskData?.proposal?.limitPrice ?? 0),
                    stop_price: String(selectedSignal?.stop ?? riskData?.proposal?.stopLoss ?? 0),
                  };
                  fetch(getApiUrl("orders/advanced"), {
                    method: "POST",
                    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
                    body: JSON.stringify(body),
                  }).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
                    .then(() => alert(`Stop Limit order placed: ${selectedSymbol}`))
                    .catch(e => alert(`Stop Limit order failed: ${e.message}`));
                }} className="bg-[#1e293b] hover:bg-cyan-900 text-[#00D9FF] py-1 rounded text-[8px]">Stop Limit</button>
                <button onClick={() => { navigate("/trade-execution"); }} className="bg-[#1e293b] hover:bg-amber-900 text-[#f59e0b] py-1 rounded text-[8px]">Modify</button>
              </div>
            </div>
          )}

          {/* Cognitive Intelligence Status (ETBI) */}
          {(() => {
            const cog = cognitiveData || {};
            const metrics = cog.metrics || {};
            const recentSnaps = cog.recent_snapshots || [];
            const lastSnap = recentSnaps.length > 0 ? recentSnaps[recentSnaps.length - 1] : {};
            const mode = (lastSnap.mode || Object.keys(cog.mode_distribution || {})[0] || "exploit").toString().toUpperCase();
            const diversity = metrics.avg_hypothesis_diversity ?? 0;
            const agreement = metrics.avg_agent_agreement ?? 0;
            const memPrec = metrics.avg_memory_precision ?? 0;
            const latencyMs = metrics.avg_latency_ms;
            const circuitOk = latencyMs == null || latencyMs < 800;
            const modeColor = mode === "EXPLOIT" ? "text-green-400" : mode === "EXPLORE" ? "text-amber-400" : mode === "DEFENSIVE" ? "text-red-400" : "text-[#94a3b8]";
            return (
              <div className="border-b border-[rgba(42,52,68,0.5)] p-2.5 space-y-1.5">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">COGNITIVE INTELLIGENCE</h3>
                  <button onClick={() => { navigate("/dashboard"); }} className="text-[7px] text-[#00D9FF] hover:text-white transition-colors">View Full →</button>
                </div>
                <div className="grid grid-cols-2 gap-1 font-mono text-[8px]">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#64748b]">Mode:</span>
                    <span className={`font-bold ${modeColor}`}>{mode}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#64748b]">Circuit:</span>
                    <div className={`w-1.5 h-1.5 rounded-full ${circuitOk ? "bg-green-500" : "bg-red-500 animate-pulse"}`} />
                    <span className={circuitOk ? "text-green-400" : "text-red-400"}>{circuitOk ? "OK" : "TRIP"}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#64748b]">Diversity:</span>
                    <span className="text-white">{Number(diversity).toFixed(2)}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#64748b]">Agreement:</span>
                    <span className="text-white">{(Number(agreement) * 100).toFixed(0)}%</span>
                  </div>
                  <div className="flex items-center gap-1.5 col-span-2">
                    <span className="text-[#64748b]">Memory Precision:</span>
                    <div className="flex-1 h-1.5 bg-[#1e293b] rounded-full overflow-hidden">
                      <div className="h-full bg-[#00D9FF] rounded-full transition-all" style={{ width: `${(Number(memPrec) || 0) * 100}%` }} />
                    </div>
                    <span className="text-white w-8 text-right">{(Number(memPrec) * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Equity Curve + Flywheel (bottom of right panel) */}
          <div className="border-b border-[rgba(42,52,68,0.5)] p-2.5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono mb-1">EQUITY CURVE</h3>
            <MiniEquityCurve points={performance.equityCurve} />
          </div>

          <div className="p-2.5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono mb-2">ML FLYWHEEL</h3>
            <FlywheelPipeline flywheel={flywheel} />
          </div>
        </section>
      </main>

      {/* BOTTOM ACTION BAR */}
      <footer className="flex items-center px-3 py-1 bg-[#0B0E14] border-t border-[rgba(42,52,68,0.5)] shrink-0 font-mono text-[8px] text-[#94a3b8]">
        <div className="flex gap-2">
          <button onClick={handleSpawnAgent} className="bg-[#1e293b] hover:bg-[#374151] text-white px-2 py-0.5 rounded border border-[#374151]">
            Spawn Agent [N]
          </button>
          <button onClick={handleFlatten} className="bg-amber-900/60 text-[#f59e0b] px-2 py-0.5 rounded border border-amber-700/50">
            Flatten All
          </button>
          <button onClick={handleEmergencyStop} className="bg-red-900/70 text-red-400 px-2 py-0.5 rounded font-bold border border-red-700/50">
            EMERGENCY STOP
          </button>
        </div>
      </footer>

      {/* Hidden components that provide data hooks */}
      <div className="hidden">
        <CNSVitals />
        <ProfitBrainBar />
      </div>

      {/* Global CSS */}
      <style
        dangerouslySetInnerHTML={{
          __html: `
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: #0B0E14; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 2px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #00D9FF; }
        @keyframes ticker-scroll { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
        .ticker-strip { animation: ticker-scroll 40s linear infinite; }
        .ticker-strip:hover { animation-play-state: paused; }
        @keyframes ticker-glow { 0%,100% { opacity: 0.7; } 50% { opacity: 1; } }
        .ticker-glow { animation: ticker-glow 2s ease-in-out infinite; }
        .kpi-num { transition: opacity 200ms ease-out, color 200ms ease-out; }
        .heatmap-text { text-shadow: 0 0 2px rgba(0,0,0,0.8); }
        @keyframes cyan-glow { 0% { box-shadow: inset 0 0 16px rgba(0,217,255,0.5); } 100% { box-shadow: inset 0 0 4px rgba(0,217,255,0.2); } }
        .animate-cyan-glow { animation: cyan-glow 1.5s ease-out forwards; }
      `,
        }}
      />
    </div>
  );
}
