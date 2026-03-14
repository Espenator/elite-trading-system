import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import log from "@/utils/logger";
import { useApi } from "../hooks/useApi";
import { getApiUrl, getAuthHeaders, extractApiError } from "../config/api";
import CNSVitals from "../components/dashboard/CNSVitals";
import ProfitBrainBar from "../components/dashboard/ProfitBrainBar";
import ws from "../services/websocket";
import ConfirmDialog from "../components/ui/ConfirmDialog";

// --- TOP TICKER STRIP (scrolling market tickers) ---
const TickerStrip = ({ indices, signals, snapshots = {} }) => {
  // indices: symbol-keyed map from marketIndices API; snapshots: Alpaca snapshot data for signal symbols
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
    // Add top signals as tickers — use Alpaca snapshot prices (signal entry is often 0)
    if (signals?.length) {
      signals.slice(0, 12).forEach((sig) => {
        if (!items.find((t) => t.symbol === sig.symbol)) {
          const snap = snapshots[sig.symbol];
          const snapPrice = snap
            ? (snap.latestTrade?.p ?? snap.dailyBar?.c ?? snap.minuteBar?.c ?? null)
            : null;
          const snapChange = snap?.dailyBar?.c && snap?.prevDailyBar?.c
            ? (((snap.dailyBar.c - snap.prevDailyBar.c) / snap.prevDailyBar.c) * 100)
            : null;
          items.push({
            symbol: sig.symbol,
            price: snapPrice ?? (sig.entry > 0 ? sig.entry : null) ?? sig.price ?? null,
            change: snapChange ?? sig.momentum ?? sig.changePct ?? 0,
          });
        }
      });
    }
    // No fallback tickers — only show real API data
    return items;
  }, [indices, signals, snapshots]);

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
            <span
              key={`${t.symbol}-${i}`}
              className="inline-flex items-center gap-1.5 text-[10px] font-mono"
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
            </span>
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



// --- MINI EQUITY CURVE (SVG Sparkline) ---
const MiniEquityCurve = ({ points }) => {
  const pad = 4;
  const w = 280;
  const h = 40;
  const values = (points || []).map((p) => Number(p?.value ?? p?.equity ?? p?.y ?? 0)).filter((v) => !Number.isNaN(v));
  if (!values.length || values.length < 2) {
    const initEquity = points?.[0]?.value ?? points?.[0]?.equity ?? 100000;
    return (
      <div>
        <div className="text-[8px] text-[#64748b] text-center font-mono mb-1">Initial: ${Number(initEquity).toLocaleString()}</div>
        <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="w-full">
          <line x1={pad} y1={h / 2} x2={w - pad} y2={h / 2} stroke="#10b981" strokeWidth="1.5" strokeDasharray="4 2" />
        </svg>
        <div className="text-[7px] text-[#4b5563] text-center font-mono mt-1">No trading data yet — equity will plot as trades resolve</div>
      </div>
    );
  }
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
  const color = change >= 0 ? "#10b981" : "#ef4444";
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
        <span className="text-[#94a3b8]">
          ${first.toLocaleString(undefined, { maximumFractionDigits: 0 })}
        </span>
        <span
          className={
            change >= 0 ? "text-green-400 font-bold" : "text-red-400 font-bold"
          }
        >
          {change >= 0 ? "+" : ""}
          {change.toLocaleString(undefined, { maximumFractionDigits: 0 })}
        </span>
        <span className="text-white">
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
  const acc30 = flywheel?.accuracy30d ?? flywheel?.accuracy ?? 0;
  const acc90 = flywheel?.accuracy90d ?? 0;
  const resolved = flywheel?.resolvedSignals ?? 0;
  const isActive = acc30 > 0 || resolved > 0;
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
          <span className={`font-bold ${acc30 ? "text-[#00D9FF]" : "text-[#4b5563]"}`} title={acc30 ? `30-day accuracy: ${(acc30 * 100).toFixed(1)}%` : "Needs resolved signals to compute"}>
            {acc30 ? `${(acc30 * 100).toFixed(1)}%` : "N/A"}
          </span>
        </div>
        <div>
          <span className="text-[#94a3b8]">90d Acc</span>
          <br />
          <span className={`font-bold ${acc90 ? "text-[#00D9FF]" : "text-[#4b5563]"}`} title={acc90 ? `90-day accuracy: ${(acc90 * 100).toFixed(1)}%` : "Needs 90 days of data to compute"}>
            {acc90 ? `${(acc90 * 100).toFixed(1)}%` : "N/A"}
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

  // Color interpolation: score 0-100 maps to red(0) -> yellow(50) -> green(100)
  const getHeatColor = (score) => {
    const s = Math.min(100, Math.max(0, score || 0));
    if (s >= 70) {
      // green range: interpolate from yellow to bright green
      const t = (s - 70) / 30;
      const r = Math.round(245 * (1 - t));
      const g = Math.round(158 + 97 * t);
      const b = Math.round(11 + 120 * t);
      return `rgb(${r},${g},${b})`;
    }
    if (s >= 40) {
      // yellow range
      const t = (s - 40) / 30;
      const r = Math.round(239 + 6 * t);
      const g = Math.round(68 + 90 * t);
      const b = Math.round(68 - 57 * t);
      return `rgb(${r},${g},${b})`;
    }
    // red range
    const t = s / 40;
    const r = Math.round(127 + 112 * t);
    const g = Math.round(29 + 39 * t);
    const b = Math.round(29 + 39 * t);
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
                  <span className="text-[7px] font-mono font-bold text-white leading-none">
                    {sig.symbol}
                  </span>
                  <span
                    className="text-[7px] font-mono font-bold leading-none"
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

const SortTh = ({ label, colKey, sortCol, sortDir, onSort }) => (
  <th
    className="px-1.5 py-1 font-semibold cursor-pointer select-none hover:text-[#00D9FF] transition-colors"
    onClick={() => onSort(colKey)}
    title={`Sort by ${label}`}
  >
    {label}
    {sortCol === colKey && (
      <span className="ml-0.5 text-[#00D9FF]">{sortDir === "asc" ? "\u25B2" : "\u25BC"}</span>
    )}
  </th>
);

export default function Dashboard() {
  const navigate = useNavigate();
  // --- STATE ---
  const [activeSortKey, setActiveSortKey] = useState("Composite Score");
  const [selectedSymbol, setSelectedSymbol] = useState("SPY"); // default so Price Action chart loads
  const [sortCol, setSortCol] = useState("score"); // column key for table header sort
  const [sortDir, setSortDir] = useState("desc"); // "asc" or "desc"
  const [symbolFilter, setSymbolFilter] = useState("");
  const [dirFilter, setDirFilter] = useState("ALL"); // "ALL", "LONG", "SHORT"
  const [activeTimeframe, setActiveTimeframe] = useState("1h");
  const [autoExec, setAutoExec] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [showFlattenConfirm, setShowFlattenConfirm] = useState(false);
  const [showEmergencyConfirm, setShowEmergencyConfirm] = useState(false);

  // --- WebSocket connection (Layout owns lifecycle, this is just a safety-net connect) ---
  useEffect(() => {
    ws.connect();
    // Do NOT disconnect on unmount — Layout owns the WS lifecycle.
    // Calling ws.disconnect() here kills the connection for all pages.
  }, []);

  // --- SIGNALS FETCH (manual, with timeframe support) ---
  // FIX #38: Manual fetch so timeframe changes trigger immediate re-fetch
  //          using getApiUrl("signals") for correct base URL.
  const [signalsData, setSignalsData] = useState(null);
  const [sigLoading, setSigLoading] = useState(true);
  const [sigErr, setSigErr] = useState(null);
  const [sigStale, setSigStale] = useState(false);
  const signalsAbortRef = useRef(null);

  const fetchSignals = useCallback(async (signal) => {
    const url = `${getApiUrl("signals")}?timeframe=${encodeURIComponent(activeTimeframe)}`;
    try {
      const res = await fetch(url, {
        cache: "no-store",
        headers: getAuthHeaders(),
        signal,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      const json = await res.json();
      if (!signal?.aborted) {
        setSignalsData(json);
        setSigErr(null);
        setSigStale(false);
      }
    } catch (err) {
      if (signal?.aborted || err.name === "AbortError") return;
      setSigErr(err);
    } finally {
      if (!signal?.aborted) setSigLoading(false);
    }
  }, [activeTimeframe]);

  // Re-fetch immediately when timeframe changes
  useEffect(() => {
    if (signalsAbortRef.current) signalsAbortRef.current.abort();
    const ctrl = new AbortController();
    signalsAbortRef.current = ctrl;
    setSigLoading(true);
    fetchSignals(ctrl.signal);
    return () => ctrl.abort();
  }, [fetchSignals]);

  // Poll signals every 5s (HIGH: real-time trading signals)
  useEffect(() => {
    const id = setInterval(() => {
      if (document.hidden) return;
      fetchSignals(signalsAbortRef.current?.signal);
    }, 5000);
    return () => clearInterval(id);
  }, [fetchSignals]);

  // --- API HOOKS (Real-time polling) ---
  const { data: kellyData, error: kellyErr } = useApi("kellyRanked", { pollIntervalMs: 30000 }); // LOW: position sizing
  const { data: portfolioData, error: portfolioErr } = useApi("portfolio", { pollIntervalMs: 5000 }); // HIGH: real-time portfolio
  const { data: indicesData, error: indicesErr } = useApi("marketIndices", {
    pollIntervalMs: 5000,  // HIGH: real-time prices
  });
  const { data: openclawData, error: openclawErr } = useApi("openclaw", { pollIntervalMs: 30000 }); // LOW: regime data
  const { data: performanceData } = useApi("performance", {
    pollIntervalMs: 60000,  // LOW: historical perf
  });
  const { data: agentsData } = useApi("agents", { pollIntervalMs: 15000 }); // MEDIUM: agent status
  const { data: consensusData } = useApi("agentConsensus", { pollIntervalMs: 15000 }); // MEDIUM: consensus
  const { data: performanceEquityData } = useApi("performanceEquity", { pollIntervalMs: 60000 }); // LOW: equity curve
  const { data: riskScoreData } = useApi("riskScore", {
    pollIntervalMs: 15000,  // MEDIUM: risk score
  });
  const { data: alertsData } = useApi("systemAlerts", {
    pollIntervalMs: 15000,  // MEDIUM: alerts
  });
  const { data: flywheelData } = useApi("flywheel", { pollIntervalMs: 60000 }); // LOW: flywheel
  const { data: sentimentData } = useApi("sentiment", {
    pollIntervalMs: 30000,  // LOW: sentiment
  });
  const { data: cognitiveData } = useApi("cognitiveDashboard", { pollIntervalMs: 60000 }); // LOW: cognitive

  // Right Panel specific APIs based on selectedSymbol
  const { data: techsData } = useApi("signals", {
    endpoint: `/signals/${selectedSymbol}/technicals`,
    enabled: !!selectedSymbol,
  });
  const { data: swarmData } = useApi("swarmTopology", {
    endpoint: `/agents/swarm-topology/${selectedSymbol}`,
    enabled: !!selectedSymbol,
  });
  const { data: dataSourcesData } = useApi("dataSources", {
    pollIntervalMs: 60000,
  });
  const { data: riskData } = useApi("risk", {
    endpoint: `/risk/proposal/${selectedSymbol}`,
    enabled: !!selectedSymbol,
  });
  const { data: quotesData } = useApi("quotes", {
    endpoint: `/quotes/${selectedSymbol}/book`,
    pollIntervalMs: 5000,  // HIGH: real-time order book for selected symbol
    enabled: !!selectedSymbol,
  });

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

  const displaySignals = useMemo(() => {
    let list = [...processedSignals];
    // Apply symbol filter
    if (symbolFilter.trim()) {
      const q = symbolFilter.trim().toUpperCase();
      list = list.filter((s) => s.symbol?.toUpperCase().includes(q));
    }
    // Apply direction filter
    if (dirFilter !== "ALL") {
      list = list.filter((s) => s.direction === dirFilter);
    }
    // Apply column sort
    const getVal = (sig) => {
      switch (sortCol) {
        case "symbol": return sig.symbol || "";
        case "direction": return sig.direction || "";
        case "score": return sig.score || 0;
        case "regime": return sig.scores?.regime || 0;
        case "ml": return sig.scores?.ml || 0;
        case "sentiment": return sig.scores?.sentiment || 0;
        case "technical": return sig.scores?.technical || 0;
        case "kelly": return sig.kellyPercent || 0;
        case "entry": return Number(sig.entry) || 0;
        case "target": return Number(sig.target) || 0;
        case "stop": return Number(sig.stop) || 0;
        case "rMultiple": return sig.rMultiple || 0;
        case "momentum": return sig.momentum || 0;
        case "volSpike": return sig.volSpike || 0;
        default: return sig.score || 0;
      }
    };
    list.sort((a, b) => {
      const va = getVal(a);
      const vb = getVal(b);
      if (typeof va === "string") {
        return sortDir === "asc" ? va.localeCompare(vb) : vb.localeCompare(va);
      }
      return sortDir === "asc" ? va - vb : vb - va;
    });
    return list;
  }, [processedSignals, symbolFilter, dirFilter, sortCol, sortDir]);

  const handleColSort = useCallback((colKey) => {
    setSortCol((prev) => {
      if (prev === colKey) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
        return colKey;
      }
      setSortDir("desc");
      return colKey;
    });
  }, []);

  // --- FETCH ALPACA SNAPSHOTS FOR SIGNAL SYMBOLS (ticker strip prices) ---
  const [tickerSnapshots, setTickerSnapshots] = useState({});
  useEffect(() => {
    if (!processedSignals.length) return;
    const symbols = processedSignals
      .slice(0, 12)
      .map((s) => s.symbol)
      .filter(Boolean);
    if (!symbols.length) return;
    const ctrl = new AbortController();
    const url = getApiUrl(`/api/v1/alpaca/snapshots?symbols=${symbols.join(",")}`);
    fetch(url, { signal: ctrl.signal, headers: getAuthHeaders() })
      .then((r) => r.json())
      .then((data) => {
        if (data && typeof data === "object") setTickerSnapshots(data);
      })
      .catch((e) => {
        if (e.name !== "AbortError") log.warn("Ticker snapshot fetch failed:", e);
      });
    // Refresh every 15s, pause when tab is hidden
    const interval = setInterval(() => {
      if (document.hidden) return;
      fetch(url, { headers: getAuthHeaders() })
        .then((r) => r.json())
        .then((data) => {
          if (data && typeof data === "object") setTickerSnapshots(data);
        })
        .catch(() => {});
    }, 15000);
    return () => { ctrl.abort(); clearInterval(interval); };
  }, [processedSignals.map((s) => s.symbol).slice(0, 12).join(",")]);

  // Auto-select first symbol on load
  useEffect(() => {
    if (processedSignals.length > 0 && !selectedSymbol) {
      setSelectedSymbol(processedSignals[0].symbol);
    }
  }, [processedSignals, selectedSymbol]);

  const selectedSignal = useMemo(
    () =>
      processedSignals.find((s) => s.symbol === selectedSymbol) ||
      processedSignals[0],
    [processedSignals, selectedSymbol],
  );

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
    toast.info("Running scan...");
    try {
      const res = await fetch(getApiUrl("signals"), { method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() } });
      if (!res.ok) {
        const msg = await extractApiError(res);
        log.error("Scan failed:", msg);
        toast.error(`Scan failed: ${msg}`);
        return;
      }
      const data = await res.json().catch(() => ({}));
      const count = data?.signals?.length ?? data?.count ?? "?";
      toast.success(`Scan complete — ${count} signals found`);
    } catch (e) {
      log.error("Scan error:", e);
      toast.error(`Scan error: ${e?.message || "network error"}`);
    }
  }, []);
  const handleExecTop5 = useCallback(async () => {
    const top5 = processedSignals.slice(0, 5);
    if (!top5.length) { toast.warn("No signals to execute"); return; }
    const names = top5.map((s) => `${s.symbol} ${s.direction || "LONG"}`).join(", ");
    if (!window.confirm(`Execute top 5: ${names}?`)) return;
    toast.info("Executing top 5 signals...");
    const results = await Promise.allSettled(top5.map(sig =>
      fetch(getApiUrl("orders/advanced"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({
          symbol: sig.symbol,
          side: sig.direction === "LONG" ? "buy" : "sell",
          type: "market",
          time_in_force: "day",
          qty: "100",
        }),
      }).then(r => { if (!r.ok) throw new Error(`${sig.symbol}: HTTP ${r.status}`); return r; })
    ));
    const ok = results.filter(r => r.status === "fulfilled").length;
    const failed = results.filter(r => r.status === "rejected").length;
    if (failed === 0) {
      toast.success(`Top 5: all ${ok} orders placed`);
    } else if (ok === 0) {
      toast.error(`Top 5: all ${top5.length} orders failed`);
    } else {
      toast.warning(`Top 5: ${ok} placed, ${failed} failed`);
    }
  }, [processedSignals]);
  const doFlatten = useCallback(async () => {
    try {
      const res = await fetch(getApiUrl("orders") + "/flatten-all", { method: "POST", headers: getAuthHeaders() });
      if (!res.ok) { const msg = await extractApiError(res); toast.error(`Flatten failed: ${msg}`); return; }
      toast.success("All positions flattened");
    } catch (e) {
      log.error(e);
      toast.error(`Flatten error: ${e.message}`);
    }
  }, []);
  const handleFlatten = useCallback(() => setShowFlattenConfirm(true), []);
  const doEmergencyStop = useCallback(async () => {
    try {
      const res = await fetch(getApiUrl("orders") + "/emergency-stop", { method: "POST", headers: getAuthHeaders() });
      if (!res.ok) { const msg = await extractApiError(res); toast.error(`Emergency stop failed: ${msg}`); return; }
      toast.success("Emergency stop executed");
    } catch (e) {
      log.error(e);
      toast.error(`Emergency stop error: ${e.message}`);
    }
  }, []);
  const handleEmergencyStop = useCallback(() => setShowEmergencyConfirm(true), []);

  // FIX #36: Export CSV with proper feedback, loading state, and error handling
  const handleExportCSV = useCallback(() => {
    try {
      setIsExporting(true);
      const data = displaySignals;
      if (!data.length) { toast.warn("No signals to export"); setIsExporting(false); return; }
      const headers = ["symbol","direction","score","regime","ml","sentiment","technical","entry","target","stop","rMultiple","kellyPercent","momentum","volSpike","pattern"];
      const headerLabels = ["Symbol","Direction","Score","Regime","ML","Sentiment","Technical","Entry","Target","Stop","R-Multiple","Kelly %","Momentum","Vol Spike","Pattern"];
      const getField = (sig, h) => {
        switch (h) {
          case "regime": return sig.scores?.regime ?? "";
          case "ml": return sig.scores?.ml ?? "";
          case "sentiment": return sig.scores?.sentiment ?? "";
          case "technical": return sig.scores?.technical ?? "";
          default: return sig[h] ?? "";
        }
      };
      // CSV escape: wrap in quotes and escape internal quotes
      const esc = (v) => `"${String(v).replace(/"/g, '""')}"`;
      const rows = data.map(s => headers.map(h => esc(getField(s, h))).join(","));
      const csv = [headerLabels.join(","), ...rows].join("\n");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const fname = `signals_export_${activeTimeframe}_${new Date().toISOString().slice(0, 10)}.csv`;
      const a = document.createElement("a");
      a.href = url;
      a.download = fname;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success(`Exported ${data.length} signals to CSV`);
    } catch (err) {
      log.error("CSV export failed:", err);
      toast.error(`CSV export failed: ${err.message || "unknown error"}`);
    } finally {
      // Brief loading state so user sees feedback
      setTimeout(() => setIsExporting(false), 600);
    }
  }, [displaySignals, activeTimeframe]);

  const handleSpawnAgent = useCallback(() => {
    navigate("/agents");
  }, []);

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
  const openclaw = openclawData?.openclaw || openclawData || {};
  const performance = useMemo(() => {
    const p = performanceData?.performance || performanceData || {};
    const equityCurve = performanceEquityData?.equity_curve ?? performanceEquityData?.equity ?? p.equityCurve ?? [];
    return {
      ...p,
      sharpe: p.sharpe ?? p.sharpeRatio ?? 0,
      alpha: p.alpha ?? 0,
      winRate: p.winRate ?? p.win_rate ?? 0,
      maxDrawdown: p.maxDrawdown ?? p.max_drawdown ?? 0,
      equityCurve: Array.isArray(equityCurve) ? equityCurve : [],
    };
  }, [performanceData, performanceEquityData]);
  const techs = useMemo(() => {
    const raw = techsData?.technicals || techsData || {};
    // Backend returns { indicators: { rsi, macd, ... } } — flatten for display
    const ind = raw.indicators || {};
    return { ...raw, ...ind };
  }, [techsData]);
  const swarm = swarmData?.swarmTopology || swarmData || {};
  const consensus = consensusData?.votes ?? consensusData?.agents ?? swarm?.agents ?? [];
  const consensusVerdict = consensusData?.verdict ?? consensusData?.consensus ?? swarm?.consensus;
  const swarmForConsensus = useMemo(() => {
    // Prefer council consensus votes, fall back to swarm topology nodes
    let agentList = [];
    if (Array.isArray(consensus) && consensus.length > 0) {
      agentList = consensus.map((v) => ({
        name: v.name ?? v.agent_name ?? v.agent,
        vote: v.vote ?? v.verdict,
        confidence: v.confidence ?? v.agreement ?? 50,
      }));
    } else if (Array.isArray(swarm?.agents) && swarm.agents.length > 0) {
      agentList = swarm.agents;
    } else if (Array.isArray(swarm?.nodes) && swarm.nodes.length > 0) {
      // Swarm topology returns { nodes: [...] } — show agents (any status)
      agentList = swarm.nodes.map(n => ({
        name: n.name,
        vote: n.status === "running" ? "ACTIVE" : "HOLD",
        confidence: n.win_pct ?? 50,
      }));
    }
    return {
      ...swarm,
      agents: agentList,
      consensus: consensusData?.agreement_percent ?? consensusData?.agreement ?? swarm?.consensus,
    };
  }, [swarm, consensus, consensusData]);
  const sources = dataSourcesData?.dataSources || dataSourcesData || {};
  const risk = riskData?.proposal || riskData || {};
  const quotes = quotesData?.book || quotesData || {};
  const agents = agentsData?.agents || agentsData || {};
  const riskScore = useMemo(() => {
    const r = riskScoreData?.riskScore || riskScoreData || {};
    return {
      ...r,
      score: r.score ?? r.risk_score,
      dailyVaR: r.dailyVaR ?? r.riskScore?.dailyVaR,
      correlation: r.correlation ?? r.riskScore?.correlation,
      positionLimit: r.positionLimit ?? r.riskScore?.positionLimit,
      status: r.status ?? r.riskScore?.status ?? "Active",
    };
  }, [riskScoreData]);
  const alerts = alertsData?.alerts || alertsData?.systemAlerts || [];
  const flywheel = flywheelData?.flywheel || flywheelData || {};
  const globalSentiment = sentimentData?.sentiment || sentimentData || {};

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

  // Aggregate critical API errors for visibility
  const criticalErrors = [
    portfolioErr && 'Portfolio',
    sigErr && 'Signals',
    indicesErr && 'Market Data',
    openclawErr && 'OpenClaw',
  ].filter(Boolean);

  return (
    <div className="-m-6 -mb-10 flex flex-col h-[calc(100%+3.5rem)] w-[calc(100%+3rem)] bg-[#0B0E14] text-[#e5e7eb] font-sans text-[9px] leading-tight overflow-hidden selection:bg-[#00D9FF]/30">
      {/* API ERROR BANNER */}
      {criticalErrors.length > 0 && (
        <div className="px-4 py-1.5 bg-red-500/10 border-b border-red-500/30 text-red-400 text-[10px] flex items-center gap-2 shrink-0">
          <span className="font-bold">API OFFLINE:</span>
          <span>{criticalErrors.join(', ')} — data may be stale or unavailable</span>
        </div>
      )}
      {/* TOP HEADER BAR */}
      <header className="flex items-center justify-between px-4 py-1.5 border-b border-[rgba(42,52,68,0.5)] bg-[#111827] shrink-0 overflow-x-auto no-scrollbar">
        <div className="flex items-center gap-4 shrink-0">
          <div className="flex items-center gap-2 pr-4 border-r border-[rgba(42,52,68,0.5)]">
            <HexagonLogo />
            <h1 className="text-xs font-bold text-white tracking-widest">
              EMBODIER TRADER
            </h1>
          </div>
          {/* Regime Badges */}
          <div
            className={`px-2 py-0.5 rounded font-bold tracking-wider ${openclaw.regime === "BEAR" ? "bg-red-500/20 text-red-400 border border-red-500/50" : (openclaw.regime === "UNKNOWN" || !openclaw.regime) ? "bg-slate-500/20 text-slate-400 border border-slate-500/50" : "bg-green-500/20 text-green-400 border border-green-500/50"}`}
            title={(openclaw.regime === "UNKNOWN" || !openclaw.regime) ? "Regime unknown -- market closed or insufficient data" : `Market regime: ${openclaw.regime}`}
          >
            {openclaw.regime || "\u2014"}
          </div>
          <div className="flex items-center gap-1">
            <span className="text-[#94a3b8]">SCORE</span>
            <div className="w-6 h-6 rounded-full border-2 border-green-400 flex items-center justify-center text-[10px] font-mono text-green-400">
              {openclaw.compositeScore != null && openclaw.compositeScore !== "" ? openclaw.compositeScore : "\u2014"}
            </div>
          </div>
          {/* Risk Score Badge — 100=safest, 0=riskiest */}
          <div
            className={`px-2 py-0.5 rounded font-bold ${(riskScore.score ?? riskScore.risk_score ?? 0) >= 70 ? "bg-green-500/20 text-green-400 border border-green-500/50" : (riskScore.score ?? riskScore.risk_score ?? 0) >= 40 ? "bg-amber-500/20 text-amber-400 border border-amber-500/50" : "bg-red-500/20 text-red-400 border border-red-500/50"}`}
            title="Risk safety score: 100 = all clear (no drawdown, low exposure), 0 = maximum risk"
          >
            RISK {riskScore.score ?? riskScore.risk_score ?? "\u2014"}
          </div>
          {/* Sentiment Badge */}
          <div
            className={`px-2 py-0.5 rounded font-bold ${globalSentiment.score == null && globalSentiment.value == null ? "bg-slate-500/20 text-slate-400" : (globalSentiment.score ?? 0) >= 60 ? "bg-green-500/20 text-green-400" : (globalSentiment.score ?? 0) >= 40 ? "bg-amber-500/20 text-amber-400" : "bg-red-500/20 text-red-400"}`}
            title={globalSentiment.score == null && globalSentiment.value == null ? "No sentiment data -- sentiment providers not returning data" : `Global sentiment score: ${globalSentiment.score ?? globalSentiment.value}`}
          >
            SENT {globalSentiment.score ?? globalSentiment.value ?? "N/A"}
          </div>
        </div>
        {/* KPIs */}
        <div className="flex items-center gap-4 font-mono text-[10px] shrink-0 whitespace-nowrap">
          <div className="flex gap-3 text-[#94a3b8]">
            <span title="S&P 500">
              SPX{" "}
              <span className="text-green-400">
                +{indices.SPX?.change || "\u2014"}%
              </span>
            </span>
            <span title="NASDAQ">
              NDAQ{" "}
              <span className="text-red-400">
                {indices.NDAQ?.change || "\u2014"}%
              </span>
            </span>
            <span title="Bitcoin">
              BTC{" "}
              <span className="text-green-400">
                +{indices.BTC?.change || "\u2014"}%
              </span>
            </span>
          </div>
          <div className="w-px h-4 bg-[#1e293b] shrink-0"></div>
          <div className="flex gap-4">
            <span title="Total Equity">
              Equity{" "}
              <span className="text-white font-mono">
                ${Number(portfolio.totalEquity ?? 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
              </span>
            </span>
            <span title="Day Profit & Loss">
              P&L{" "}
              <span className={`font-mono ${Number(portfolio.dayPnL ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                {Number(portfolio.dayPnL ?? 0) >= 0 ? "+" : ""}${Number(portfolio.dayPnL ?? 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
              </span>
            </span>
            <span title="Capital Deployed">
              Deployed{" "}
              <span className="text-[#00D9FF] font-mono">
                {Number(portfolio.deployedPercent ?? 0).toFixed(1)}%
              </span>
            </span>
            <span title="Sharpe Ratio">
              Sharpe{" "}
              <span className="text-[#00D9FF] font-mono">
                {performance.sharpe != null && performance.sharpe !== "" ? Number(performance.sharpe) : "0"}
              </span>
            </span>
            <span title="Alpha vs Benchmark">
              Alpha{" "}
              <span className="text-green-400 font-mono">
                +{performance.alpha != null && performance.alpha !== "" ? Number(performance.alpha) : "0"}%
              </span>
            </span>
            <span title="Win Rate">
              Win{" "}
              <span className="text-green-400 font-mono">
                {performance.winRate != null && performance.winRate !== "" ? Number(performance.winRate) : "0"}%
              </span>
            </span>
            <span title="Maximum Drawdown">
              MaxDD{" "}
              <span className="text-red-400 font-mono">
                {performance.maxDrawdown != null && performance.maxDrawdown !== "" ? Number(performance.maxDrawdown) : "0"}%
              </span>
            </span>
          </div>
        </div>
      </header>

      {/* SCROLLING TICKER STRIP */}
      <TickerStrip indices={indices} signals={processedSignals} snapshots={tickerSnapshots} />

      {/* Signal-error banner (non-blocking) */}
      {sigErr && (
        <div className="mx-4 mt-1 px-3 py-1 rounded bg-red-500/10 border border-red-500/30 text-red-400 text-[10px] font-mono flex items-center gap-2 shrink-0">
          <span className="font-bold">SIGNAL API OFFLINE</span>
          <span className="text-red-400/70">{sigErr.message}</span>
        </div>
      )}

      {/* MAIN CONTENT AREA: Center Table + Right Panel */}
      <main className="flex flex-col md:flex-row flex-1 overflow-hidden">

        {/* CENTER COLUMN: Sort Pills + Table (dominant area) */}
        <section className="flex flex-col flex-1 min-w-0 md:border-r border-[rgba(42,52,68,0.5)] bg-[#0B0E14] min-h-[300px] md:min-h-0">
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
                  className={`px-1.5 py-0.5 rounded-sm text-[8px] transition-colors ${activeTimeframe === tf ? "bg-[#1e293b] text-white font-bold" : "hover:bg-[#1e293b]/50"}`}
                >
                  {tf}
                </button>
              ))}
              {sigLoading && <span className="text-[7px] text-[#00D9FF] animate-pulse ml-1">loading...</span>}
            </div>
            <div className="flex items-center gap-3 text-[8px]">
              <button
                onClick={() => setAutoExec(!autoExec)}
                className="flex items-center gap-1 cursor-pointer hover:text-white transition-colors"
              >
                <div className={`w-1.5 h-1.5 rounded-full ${autoExec ? "bg-green-500 animate-pulse" : "bg-red-500"}`} />
                Auto-Exec: {autoExec ? "ON" : "OFF"}
              </button>
              <span className="flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" /> LIVE
              </span>
              <span>Flywheel: {flywheel.accuracy ?? (flywheel.accuracy30d != null ? Math.round(Number(flywheel.accuracy30d) * 100) : 0)}%</span>
            </div>
          </div>

          {/* Symbol & Direction Filters */}
          <div className="flex items-center gap-2 px-2 py-1 bg-[#0B0E14] border-b border-[rgba(42,52,68,0.5)] shrink-0">
            <input
              type="text"
              value={symbolFilter}
              onChange={(e) => setSymbolFilter(e.target.value)}
              placeholder="Filter symbol\u2026"
              className="bg-[#1e293b] text-white text-[10px] font-mono px-2 py-0.5 rounded border border-[rgba(42,52,68,0.5)] w-24 outline-none focus:border-[#00D9FF]/50"
            />
            {["ALL", "LONG", "SHORT"].map((d) => (
              <button
                key={d}
                onClick={() => setDirFilter(d)}
                className={`text-[9px] font-mono px-2 py-0.5 rounded ${dirFilter === d ? "bg-[#00D9FF]/20 text-[#00D9FF] border border-[#00D9FF]/40" : "text-[#64748b] hover:text-white border border-transparent"}`}
              >
                {d}
              </button>
            ))}
            <span className="flex-1" />
            <span className="text-[9px] font-mono text-[#64748b]">{displaySignals.length}/{processedSignals.length} signals</span>
          </div>

          {/* MAIN SIGNALS TABLE */}
          <div className="flex-1 overflow-auto bg-[#0B0E14]">
            <table className="w-full min-w-[900px] text-left font-mono whitespace-nowrap">
              <thead className="sticky top-0 bg-[#111827] text-[10px] uppercase text-slate-500 border-b border-[rgba(42,52,68,0.5)] shadow-md z-10">
                <tr>
                  <SortTh label="Sym" colKey="symbol" sortCol={sortCol} sortDir={sortDir} onSort={handleColSort} />
                  <SortTh label="Dir" colKey="direction" sortCol={sortCol} sortDir={sortDir} onSort={handleColSort} />
                  <SortTh label="Score" colKey="score" sortCol={sortCol} sortDir={sortDir} onSort={handleColSort} />
                  <SortTh label="Regime" colKey="regime" sortCol={sortCol} sortDir={sortDir} onSort={handleColSort} />
                  <SortTh label="ML" colKey="ml" sortCol={sortCol} sortDir={sortDir} onSort={handleColSort} />
                  <SortTh label="Sent" colKey="sentiment" sortCol={sortCol} sortDir={sortDir} onSort={handleColSort} />
                  <SortTh label="Tech" colKey="technical" sortCol={sortCol} sortDir={sortDir} onSort={handleColSort} />
                  <th className="px-1.5 py-1 font-semibold">Agent</th>
                  <th className="px-1.5 py-1 font-semibold">Swarm</th>
                  <th className="px-1.5 py-1 font-semibold">SHAP</th>
                  <SortTh label="Kelly" colKey="kelly" sortCol={sortCol} sortDir={sortDir} onSort={handleColSort} />
                  <SortTh label="Entry" colKey="entry" sortCol={sortCol} sortDir={sortDir} onSort={handleColSort} />
                  <SortTh label="Tgt" colKey="target" sortCol={sortCol} sortDir={sortDir} onSort={handleColSort} />
                  <SortTh label="Stop" colKey="stop" sortCol={sortCol} sortDir={sortDir} onSort={handleColSort} />
                  <SortTh label="R-Mult" colKey="rMultiple" sortCol={sortCol} sortDir={sortDir} onSort={handleColSort} />
                  <th className="px-1.5 py-1 font-semibold">P&L</th>
                  <th className="px-1.5 py-1 font-semibold">Sec</th>
                  <SortTh label="Mom" colKey="momentum" sortCol={sortCol} sortDir={sortDir} onSort={handleColSort} />
                  <SortTh label="Vol" colKey="volSpike" sortCol={sortCol} sortDir={sortDir} onSort={handleColSort} />
                  <th className="px-1.5 py-1 font-semibold">News</th>
                  <th className="px-1.5 py-1 font-semibold">Pat</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e293b]/50">
                {displaySignals.map((sig, idx) => {
                  const isSelected = selectedSymbol === sig.symbol;
                  const isLong = sig.direction === "LONG";
                  const dirColor = isLong ? "text-green-400" : "text-red-400";
                  return (
                    <tr
                      key={sig.symbol + idx}
                      onClick={() => setSelectedSymbol(sig.symbol)}
                      className={`cursor-pointer hover:bg-[#1e293b]/30 transition-colors ${isSelected ? "bg-[#164e63]/30 border-l-2 border-[#00D9FF]" : "border-l-2 border-transparent"}`}
                    >
                      <td className="px-1.5 py-1 text-[0.65rem] text-white font-bold font-mono">{sig.symbol}</td>
                      <td className={`px-1.5 py-1 text-[0.65rem] font-mono ${dirColor}`}>{isLong ? "L" : "S"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem]">
                        <div className="flex items-center gap-1">
                          <span className={`font-mono ${sig.score >= 90 ? "text-green-400" : "text-[#00D9FF]"}`}>{sig.score}</span>
                          <div className="w-12 h-1.5 bg-[#1e293b] rounded-full overflow-hidden">
                            <div className="h-full rounded-full" style={{ width: `${sig.score}%`, backgroundColor: sig.score >= 85 ? "#10b981" : sig.score >= 70 ? "#00D9FF" : sig.score >= 50 ? "#f59e0b" : "#ef4444" }} />
                          </div>
                        </div>
                      </td>
                      <td className="px-1.5 py-1 text-[0.65rem] font-mono" title={sig.scores?.regime ? `Regime score: ${sig.scores.regime}` : "Regime detection not active — market may be closed or no regime model loaded"}>
                        {sig.scores?.regime ? <span className="text-[#94a3b8]">{sig.scores.regime}</span> : <span className="text-[#475569] italic">N/A</span>}
                      </td>
                      <td className="px-1.5 py-1 text-[0.65rem] font-mono" title={sig.scores?.ml ? `ML probability: ${sig.scores.ml}%` : "ML model not trained yet — run training pipeline to enable"}>
                        {sig.scores?.ml ? <span className="text-[#94a3b8]">{sig.scores.ml}%</span> : <span className="text-[#475569] italic">No model</span>}
                      </td>
                      <td className="px-1.5 py-1 text-[0.65rem] font-mono" title={sig.scores?.sentiment ? `Sentiment score: ${sig.scores.sentiment}` : "No sentiment data — sentiment providers not returning data"}>
                        {sig.scores?.sentiment ? <span className="text-[#94a3b8]">{sig.scores.sentiment}</span> : <span className="text-[#475569] italic">No data</span>}
                      </td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#94a3b8] font-mono">{sig.scores?.technical || "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#00D9FF] truncate max-w-[80px] font-mono">{sig.leadAgent || "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#94a3b8] font-mono">{sig.swarmVote || "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#64748b] truncate max-w-[60px] font-mono">{sig.topShap || "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#00D9FF] font-mono">{sig.kellyPercent ?? 0}%</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#94a3b8] font-mono">{sig.entry && Number(sig.entry) > 0 ? `$${Number(sig.entry).toFixed(2)}` : "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-green-400 font-mono">{sig.target && Number(sig.target) > 0 ? `$${Number(sig.target).toFixed(2)}` : "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-red-400 font-mono">{sig.stop && Number(sig.stop) > 0 ? `$${Number(sig.stop).toFixed(2)}` : "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-white font-mono">{sig.rMultiple != null ? `${Number(sig.rMultiple).toFixed(1)}:1` : "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-green-400 font-mono">{sig.expPnL != null ? `+$${Number(sig.expPnL).toLocaleString()}` : "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#64748b] font-mono">{sig.sector?.substring(0, 3) || "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-green-400 font-mono">+{sig.momentum || "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#00D9FF] font-mono">{sig.volSpike || "\u2014"}x</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#64748b] truncate max-w-[50px] font-mono">{sig.newsImpact || "\u2014"}</td>
                      <td className="px-1.5 py-1 text-[0.65rem] text-[#00D9FF] truncate max-w-[60px] font-mono">{sig.pattern || "\u2014"}</td>
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
            <button onClick={handleExportCSV} disabled={isExporting} className={`px-3 py-1 rounded text-[8px] font-mono border transition-colors ${isExporting ? "bg-[#00D9FF]/20 text-[#00D9FF] border-[#00D9FF]/50 cursor-wait" : "bg-[#1e293b] hover:bg-[#374151] text-white border-[#374151]"}`}>
              {isExporting ? "Exporting..." : "Export CSV [F7]"}
            </button>
            <button onClick={handleExecTop5} className="bg-cyan-900/60 hover:bg-cyan-800 text-[#00D9FF] px-3 py-1 rounded text-[8px] font-mono border border-cyan-700/50">
              Exec Top 5
            </button>
            <div className="flex-1" />
            <span className="text-[8px] font-mono text-[#64748b]">{displaySignals.length} signals</span>
          </div>

          {/* Alerts Bar */}
          {Array.isArray(alerts) && alerts.length > 0 && (
            <div className="bg-amber-900/30 border-t border-amber-500/50 px-3 py-1 shrink-0">
              <div className="flex items-center gap-4 text-[8px] font-mono text-amber-400 flex-wrap">
                <span className="font-bold shrink-0">ALERTS:</span>
                {alerts.slice(0, 5).map((a, i) => {
                  const msg = a.message || a.msg || (typeof a === "string" ? a : JSON.stringify(a));
                  return (
                    <span key={i} className="break-words" title={msg}>{msg}</span>
                  );
                })}
              </div>
            </div>
          )}
        </section>

        {/* RIGHT COLUMN: Intelligence Panel (~32%) */}
        <section className="flex flex-col w-full md:w-[32%] max-h-[50vh] md:max-h-none bg-[#111827] overflow-y-auto custom-scrollbar border-t md:border-t-0 border-[rgba(42,52,68,0.5)]">
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
              <div className="text-[8px] text-[#64748b] font-mono py-2 text-center space-y-1">
                <div>No agent consensus votes available</div>
                <div className="text-[7px]">Council conference has not run yet, or agents are still initializing. Votes will appear after the first trading conference completes.</div>
              </div>
            )}
          </div>

          {/* Signal Strength Bar Chart */}
          <div className="border-b border-[rgba(42,52,68,0.5)] p-2.5">
            <SignalBarChart
              signals={processedSignals.slice(0, 20)}
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

          {/* Selected Symbol Detail Panel */}
          {selectedSignal && (
            <div className="border-b border-[rgba(42,52,68,0.5)] p-2.5 space-y-2">
              {/* Symbol Header */}
              <div className="flex justify-between items-center">
                <h2 className="text-sm font-bold text-white flex items-center gap-1.5">
                  {selectedSignal.symbol}
                  <span className={selectedSignal.direction === "LONG" ? "text-green-400 text-[10px]" : "text-red-400 text-[10px]"}>
                    {selectedSignal.direction || "LONG"}
                  </span>
                </h2>
                <span className="text-lg font-mono font-bold text-[#00D9FF]">{selectedSignal.score || "\u2014"}</span>
              </div>

              {/* Composite Breakdown Bars */}
              <div className="space-y-1 font-mono text-[8px]">
                {[
                  { label: "Overall Score", val: `${selectedSignal.score || 0}/100`, pct: selectedSignal.score || 0 },
                  { label: "Technical Rank", val: `${selectedSignal.scores?.technical || "\u2014"}`, pct: selectedSignal.scores?.technical || 0 },
                  { label: "ML Probability", val: selectedSignal.scores?.ml ? `${selectedSignal.scores.ml}%` : "No model", pct: selectedSignal.scores?.ml || 0 },
                  { label: "Sentiment Pulse", val: selectedSignal.scores?.sentiment ? `${selectedSignal.scores.sentiment}` : "No data", pct: selectedSignal.scores?.sentiment || 0 },
                  { label: "Swarm Consensus", val: `${swarmForConsensus.consensus ?? swarm.consensus ?? "\u2014"}%`, pct: swarmForConsensus.consensus ?? swarm.consensus ?? 0 },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between">
                    <span className="text-[#94a3b8] w-24">{item.label}</span>
                    <div className="flex-1 mx-2 h-1.5 bg-[#1e293b] rounded-full">
                      <div className="h-full bg-[#00D9FF] rounded-full transition-all" style={{ width: `${item.pct}%` }} />
                    </div>
                    <span className="text-white w-10 text-right">{item.val}</span>
                  </div>
                ))}
              </div>

              {/* Technical Analysis Grid */}
              <div className="font-mono text-[8px] bg-[#0B0E14] rounded p-1.5 border border-[rgba(42,52,68,0.3)]">
                {!techs.rsi && !techs.macd && !techs.vwap && !techs.adx && (
                  <div className="text-[#64748b] text-center py-1 mb-1 border-b border-[rgba(42,52,68,0.3)]">
                    No indicator data for {selectedSignal?.symbol} -- market closed or bars not yet ingested
                  </div>
                )}
              <div className="grid grid-cols-2 gap-1">
                <div><span className="text-[#64748b]">RSI:</span> <span className="text-green-400">{techs.rsi ? (typeof techs.rsi === "number" ? techs.rsi.toFixed(1) : techs.rsi) : "N/A"}</span></div>
                <div><span className="text-[#64748b]">MACD:</span> <span className="text-green-400">{techs.macd ? (typeof techs.macd === "number" ? techs.macd.toFixed(2) : techs.macd) : "N/A"}</span></div>
                <div><span className="text-[#64748b]">BB:</span> <span className="text-white">{techs.bb && techs.bb !== "0" ? techs.bb : "N/A"}</span></div>
                <div><span className="text-[#64748b]">VWAP:</span> <span className="text-[#00D9FF]">{techs.vwap ? (typeof techs.vwap === "number" ? techs.vwap.toFixed(2) : techs.vwap) : "N/A"}</span></div>
                <div><span className="text-[#64748b]">20 EMA:</span> <span className="text-white">{techs.ema20 && techs.ema20 !== "0" ? techs.ema20 : "N/A"}</span></div>
                <div><span className="text-[#64748b]">50 SMA:</span> <span className="text-green-400">{techs.sma50 ? (typeof techs.sma50 === "number" ? techs.sma50.toFixed(2) : techs.sma50) : "N/A"}</span></div>
                <div><span className="text-[#64748b]">ADX:</span> <span className="text-white">{techs.adx ? (typeof techs.adx === "number" ? techs.adx.toFixed(1) : techs.adx) : "N/A"}</span></div>
                <div><span className="text-[#64748b]">Stoch:</span> <span className="text-green-400">{techs.stoch ? (typeof techs.stoch === "number" ? techs.stoch.toFixed(1) : techs.stoch) : "N/A"}</span></div>
              </div>
              </div>

              {/* SHAP Drivers */}
              <div className="font-mono text-[8px]">
                <div className="flex justify-between mb-1 text-[#64748b]">
                  <span>ML Prob: {selectedSignal.scores?.ml ? <span className="text-green-400 font-bold">{selectedSignal.scores.ml}%</span> : <span className="text-[#475569] italic">No model</span>}</span>
                  <span>Drift: {techs.driftScore ? <span className="text-green-400">{techs.driftScore}</span> : <span className="text-[#475569] italic">N/A</span>}</span>
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
          )}

          {/* Risk & Order Proposal */}
          {selectedSignal && (
            <div className="border-b border-[rgba(42,52,68,0.5)] p-2.5 space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">RISK & ORDER PROPOSAL</h3>
              <div className="font-mono text-[8px]">
                <div className="grid grid-cols-2 gap-1 mb-1.5 pb-1.5 border-b border-[rgba(42,52,68,0.3)]">
                  <span className="text-[#94a3b8]">Action: <span className="text-white">{selectedSignal?.direction === 'SHORT' ? 'Limit Sell' : 'Limit Buy'} {risk.limitPrice || "\u2014"}</span></span>
                  <span className="text-[#94a3b8]">Size: <span className="text-white">{risk.shares || "\u2014"} shs (${risk.notional || "\u2014"})</span></span>
                  <span className="text-[#94a3b8]">Stop Loss: <span className="text-red-400">{risk.stopLoss || "\u2014"}</span></span>
                  <span className="text-[#94a3b8]">Target 1: <span className="text-green-400">{risk.target1 || "\u2014"}</span></span>
                  <span className="text-[#94a3b8]">R:R Ratio: <span className="text-[#00D9FF]">{risk.rr || "\u2014"}</span></span>
                  <span className="text-[#94a3b8]">Kelly: <span className="text-white">{selectedSignal.kellyPercent ?? 0}%</span></span>
                </div>
                {/* L2 Order Book */}
                <div className="text-[#64748b] mb-1">L2 BOOK (Spread: ${quotes.spread != null ? Number(quotes.spread).toFixed(2) : "\u2014"})</div>
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
                  const limitPrice = selectedSignal?.entry ?? selectedSignal?.price ?? riskData?.proposal?.limitPrice ?? 0;
                  if (!limitPrice || Number(limitPrice) <= 0) { toast.warn("No valid limit price available for this signal"); return; }
                  const body = {
                    symbol: selectedSymbol,
                    side: selectedSignal?.direction === "SHORT" ? "sell" : "buy",
                    type: "limit",
                    time_in_force: "day",
                    qty: String(riskData?.proposal?.proposedSize || 100),
                    limit_price: String(limitPrice),
                  };
                  fetch(getApiUrl("orders/advanced"), {
                    method: "POST",
                    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
                    body: JSON.stringify(body),
                  }).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
                    .then(() => toast.success(`Limit order placed: ${selectedSymbol} @ $${limitPrice}`))
                    .catch(e => toast.error(`Limit order failed: ${e.message}`));
                }} className="bg-[#1e293b] hover:bg-cyan-900 text-[#00D9FF] py-1 rounded text-[8px]">Limit</button>
                <button onClick={() => {
                  const limitPrice = selectedSignal?.entry ?? selectedSignal?.price ?? riskData?.proposal?.limitPrice ?? 0;
                  const stopPrice = selectedSignal?.stop ?? riskData?.proposal?.stopLoss ?? 0;
                  if (!limitPrice || Number(limitPrice) <= 0) { toast.warn("No valid limit price for stop-limit order"); return; }
                  if (!stopPrice || Number(stopPrice) <= 0) { toast.warn("No valid stop price for stop-limit order"); return; }
                  const body = {
                    symbol: selectedSymbol,
                    side: selectedSignal?.direction === "SHORT" ? "sell" : "buy",
                    type: "stop_limit",
                    time_in_force: "day",
                    qty: String(riskData?.proposal?.proposedSize || 100),
                    limit_price: String(limitPrice),
                    stop_price: String(stopPrice),
                  };
                  fetch(getApiUrl("orders/advanced"), {
                    method: "POST",
                    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
                    body: JSON.stringify(body),
                  }).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
                    .then(() => toast.success(`Stop-Limit placed: ${selectedSymbol} limit $${limitPrice} stop $${stopPrice}`))
                    .catch(e => toast.error(`Stop-Limit failed: ${e.message}`));
                }} className="bg-[#1e293b] hover:bg-cyan-900 text-[#00D9FF] py-1 rounded text-[8px]">Stop Limit</button>
                <button onClick={() => { toast.info("Opening Trade Execution for order modification..."); navigate("/trade-execution"); }} className="bg-[#1e293b] hover:bg-amber-900 text-[#f59e0b] py-1 rounded text-[8px]">Modify</button>
              </div>
            </div>
          )}

          {/* Cognitive Intelligence Status (ETBI) */}
          {(() => {
            const cog = cognitiveData || {};
            const metrics = cog.metrics || {};
            const recentSnaps = cog.recent_snapshots || [];
            const lastSnap = recentSnaps.length > 0 ? recentSnaps[recentSnaps.length - 1] : {};
            const mode = (lastSnap.mode || Object.keys(cog.mode_distribution || {})[0] || "—").toUpperCase();
            const diversity = metrics.avg_hypothesis_diversity;
            const agreement = metrics.avg_agent_agreement;
            const memPrec = metrics.avg_memory_precision;
            const latencyMs = metrics.avg_latency_ms;
            const circuitOk = latencyMs == null || latencyMs < 800;
            const modeColor = mode === "EXPLOIT" ? "text-green-400" : mode === "EXPLORE" ? "text-amber-400" : mode === "DEFENSIVE" ? "text-red-400" : "text-[#94a3b8]";
            return (
              <div className="border-b border-[rgba(42,52,68,0.5)] p-2.5 space-y-1.5">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">COGNITIVE INTELLIGENCE</h3>
                  <button onClick={() => { navigate("/agents"); }} className="text-[7px] text-[#00D9FF] hover:text-white transition-colors">View Full →</button>
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
                    <span className={diversity != null ? "text-white" : "text-[#4b5563]"}>{diversity != null ? Number(diversity).toFixed(2) : "Awaiting data"}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#64748b]">Agreement:</span>
                    <span className={agreement != null ? "text-white" : "text-[#4b5563]"}>{agreement != null ? `${(Number(agreement) * 100).toFixed(0)}%` : "Awaiting data"}</span>
                  </div>
                  <div className="flex items-center gap-1.5 col-span-2">
                    <span className="text-[#64748b]">Memory Precision:</span>
                    <div className="flex-1 h-1.5 bg-[#1e293b] rounded-full overflow-hidden">
                      <div className="h-full bg-[#00D9FF] rounded-full transition-all" style={{ width: `${(memPrec ?? 0) * 100}%` }} />
                    </div>
                    <span className={`w-8 text-right ${memPrec != null ? "text-white" : "text-[#4b5563]"}`}>{memPrec != null ? `${(Number(memPrec) * 100).toFixed(0)}%` : "N/A"}</span>
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
      `,
        }}
      />

      {/* Confirmation Dialogs */}
      <ConfirmDialog
        open={showFlattenConfirm}
        onConfirm={() => { setShowFlattenConfirm(false); doFlatten(); }}
        onCancel={() => setShowFlattenConfirm(false)}
        title="Flatten All Positions"
        description="This will close ALL open positions at market price. This cannot be undone. Are you sure?"
        confirmText="Flatten All"
        variant="warning"
      />
      <ConfirmDialog
        open={showEmergencyConfirm}
        onConfirm={() => { setShowEmergencyConfirm(false); doEmergencyStop(); }}
        onCancel={() => setShowEmergencyConfirm(false)}
        title="Emergency Stop"
        description="This will halt all trading activity immediately, cancel all open orders, and close all positions. Are you sure?"
        confirmText="Emergency Stop"
        variant="danger"
      />
    </div>
  );
}
