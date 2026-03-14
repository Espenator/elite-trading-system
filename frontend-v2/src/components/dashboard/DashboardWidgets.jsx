/**
 * Extracted sub-components for the main Dashboard page.
 * Moved here so that Dashboard.jsx contains a single exported component,
 * which lets Vite React Fast Refresh (HMR) work reliably.
 */
import { useMemo } from "react";

// --- TOP TICKER STRIP (scrolling market tickers) ---
export const TickerStrip = ({ indices, signals, snapshots = {} }) => {
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
export const HexagonLogo = () => (
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
export const RegimeDonut = ({ regime, score }) => {
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
export const TopTradesDonut = ({ buyCount, sellCount, holdCount }) => {
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
export const SignalBarChart = ({ signals, selectedSymbol, onSelect }) => {
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
export const MiniEquityCurve = ({ points }) => {
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
export const AgentConsensusRing = ({ buyPct, sellPct, holdPct, consensus }) => {
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
export const FlywheelPipeline = ({ flywheel }) => {
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
export const ConsensusBar = ({ label, buyPct, sellPct }) => (
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
export const HeatmapGrid = ({ signals }) => {
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

// --- SORT TABLE HEADER ---
export const SortTh = ({ label, colKey, sortCol, sortDir, onSort }) => (
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

// --- CONSTANTS ---
export const SORT_PILLS = [
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
export const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1D", "1W"];
