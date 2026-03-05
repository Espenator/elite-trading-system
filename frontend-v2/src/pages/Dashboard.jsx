import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import log from "@/utils/logger";
import { useApi } from "../hooks/useApi";
import { getApiUrl, getAuthHeaders } from "../config/api";
import CNSVitals from "../components/dashboard/CNSVitals";
import ProfitBrainBar from "../components/dashboard/ProfitBrainBar";

// --- TOP TICKER STRIP (scrolling market tickers) ---
const TickerStrip = ({ indices, signals }) => {
  const scrollRef = useRef(null);
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
    // Add top signals as tickers if not already present
    if (signals?.length) {
      signals.slice(0, 12).forEach((sig) => {
        if (!items.find((t) => t.symbol === sig.symbol)) {
          items.push({
            symbol: sig.symbol,
            price: sig.entry ?? sig.price ?? null,
            change: sig.momentum ?? sig.changePct ?? 0,
          });
        }
      });
    }
    // Fallback tickers if no data yet
    if (items.length === 0) {
      [
        "SPY",
        "QQQ",
        "AAPL",
        "MSFT",
        "TSLA",
        "AMZN",
        "NVDA",
        "META",
        "GOOGL",
        "BTC",
      ].forEach((s) => items.push({ symbol: s, price: null, change: null }));
    }
    return items;
  }, [indices, signals]);

  // Auto-scroll effect
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    let animId;
    let scrollPos = 0;
    const speed = 0.5;
    const scroll = () => {
      scrollPos += speed;
      if (scrollPos >= el.scrollWidth / 2) scrollPos = 0;
      el.scrollLeft = scrollPos;
      animId = requestAnimationFrame(scroll);
    };
    animId = requestAnimationFrame(scroll);
    return () => cancelAnimationFrame(animId);
  }, [tickers]);

  return (
    <div className="bg-[#111827] border-b border-[rgba(42,52,68,0.5)] shrink-0 overflow-hidden">
      <div
        ref={scrollRef}
        className="flex items-center gap-6 px-3 py-1 overflow-hidden no-scrollbar whitespace-nowrap"
        style={{ scrollBehavior: "auto" }}
      >
        {/* Double the items for seamless loop */}
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
      <div className="flex items-center justify-between px-3 py-1 border-b border-[rgba(42,52,68,0.5)]">
        <span className="text-[8px] font-bold text-[#00D9FF] uppercase tracking-wider">
          Signal Strength
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
              <div
                className={`w-5 rounded-t-sm transition-all duration-200 ${isSelected ? "ring-2 ring-[#00D9FF] shadow-[0_0_8px_rgba(0,217,255,0.4)]" : "group-hover:opacity-100"}`}
                style={{
                  height: `${h}%`,
                  backgroundColor: barColor,
                  opacity: isSelected ? 1 : 0.7,
                  minHeight: "4px",
                }}
                title={`${sig.symbol}: ${sig.score}`}
              />
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

// --- LIGHTWEIGHT CHART (TradingView-style candlestick via dynamic import) ---
/** Normalize time for lightweight-charts: expects yyyy-mm-dd or UTC seconds. */
function normalizeChartTime(time) {
  if (time == null) return null;
  if (typeof time === "number") return time;
  const s = String(time).trim();
  if (!s) return null;
  // Already yyyy-mm-dd
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10);
  // mm/dd/yyyy or mm-dd-yyyy
  const slash = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  const dash = s.match(/^(\d{1,2})-(\d{1,2})-(\d{4})/);
  if (slash) {
    const [, m, d, y] = slash;
    return `${y}-${m.padStart(2, "0")}-${d.padStart(2, "0")}`;
  }
  if (dash) {
    const [, m, d, y] = dash;
    return `${y}-${m.padStart(2, "0")}-${d.padStart(2, "0")}`;
  }
  return s.slice(0, 10);
}

const LWChartFallback = ({
  symbol,
  quotesData,
  signalEntry,
  signalStop,
  signalTarget,
}) => {
  const containerRef = useRef(null);
  const chartInstanceRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    const initChart = async () => {
      if (!containerRef.current) return;
      try {
        const { createChart } = await import("lightweight-charts");
        if (cancelled) return;
        const chart = createChart(containerRef.current, {
          width: containerRef.current.clientWidth,
          height: 260,
          layout: {
            background: { color: "#0B0E14" },
            textColor: "#94a3b8",
            fontSize: 9,
            fontFamily: "'JetBrains Mono', monospace",
          },
          grid: {
            vertLines: { color: "rgba(42,52,68,0.3)" },
            horzLines: { color: "rgba(42,52,68,0.3)" },
          },
          crosshair: {
            mode: 0,
            vertLine: {
              color: "#00D9FF",
              width: 1,
              style: 2,
              labelBackgroundColor: "#00D9FF",
            },
            horzLine: {
              color: "#00D9FF",
              width: 1,
              style: 2,
              labelBackgroundColor: "#00D9FF",
            },
          },
          rightPriceScale: {
            borderColor: "rgba(42,52,68,0.5)",
            scaleMargins: { top: 0.1, bottom: 0.2 },
          },
          timeScale: {
            borderColor: "rgba(42,52,68,0.5)",
            timeVisible: true,
            secondsVisible: false,
          },
        });

        const candleSeries = chart.addCandlestickSeries({
          upColor: "#10b981",
          downColor: "#ef4444",
          borderUpColor: "#10b981",
          borderDownColor: "#ef4444",
          wickUpColor: "#10b981",
          wickDownColor: "#ef4444",
        });

        const volumeSeries = chart.addHistogramSeries({
          color: "#00D9FF",
          priceFormat: { type: "volume" },
          priceScaleId: "",
        });
        volumeSeries
          .priceScale()
          .applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });

        chartInstanceRef.current = { chart, candleSeries, volumeSeries };

        const handleResize = () => {
          if (containerRef.current)
            chart.applyOptions({ width: containerRef.current.clientWidth });
        };
        window.addEventListener("resize", handleResize);
        chartInstanceRef.current.cleanup = () => {
          window.removeEventListener("resize", handleResize);
          chart.remove();
        };
      } catch (err) {
        log.warn("LW Charts init failed:", err);
      }
    };
    initChart();
    return () => {
      cancelled = true;
      if (chartInstanceRef.current?.cleanup) chartInstanceRef.current.cleanup();
      chartInstanceRef.current = null;
    };
  }, []);

  // Update data
  useEffect(() => {
    const inst = chartInstanceRef.current;
    if (!inst?.candleSeries || !quotesData) return;
    const candles =
      quotesData.candles || quotesData.bars || quotesData.ohlcv || [];
    if (!candles.length) return;
    const mapped = candles
      .map((c) => ({
        time: normalizeChartTime(c.time || c.timestamp || c.t),
        open: c.open ?? c.o,
        high: c.high ?? c.h,
        low: c.low ?? c.l,
        close: c.close ?? c.c,
      }))
      .filter((c) => c.time != null && c.open != null)
      .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));
    // Dedupe by time (keep last) so lightweight-charts gets strictly ascending unique times
    const seen = new Set();
    const mappedUnique = mapped.filter((c) => {
      const key = c.time;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
    if (mappedUnique.length) {
      inst.candleSeries.setData(mappedUnique);
      const volData = candles
        .map((c) => ({
          time: normalizeChartTime(c.time || c.timestamp || c.t),
          value: c.volume ?? c.v ?? 0,
          color:
            (c.close ?? c.c) >= (c.open ?? c.o)
              ? "rgba(16,185,129,0.3)"
              : "rgba(239,68,68,0.3)",
        }))
        .filter((v) => v.time != null)
        .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));
      const volSeen = new Set();
      const volDataUnique = volData.filter((v) => {
        if (volSeen.has(v.time)) return false;
        volSeen.add(v.time);
        return true;
      });
      if (volDataUnique.length) inst.volumeSeries.setData(volDataUnique);
    }
    // Price lines
    try {
      if (signalEntry)
        inst.candleSeries.createPriceLine({
          price: signalEntry,
          color: "#00D9FF",
          lineWidth: 1,
          lineStyle: 2,
          title: "Entry",
        });
      if (signalStop)
        inst.candleSeries.createPriceLine({
          price: signalStop,
          color: "#ef4444",
          lineWidth: 1,
          lineStyle: 2,
          title: "Stop",
        });
      if (signalTarget)
        inst.candleSeries.createPriceLine({
          price: signalTarget,
          color: "#10b981",
          lineWidth: 1,
          lineStyle: 2,
          title: "Target",
        });
    } catch (err) {
      log.warn("Chart data update error:", err);
    }
  }, [quotesData, signalEntry, signalStop, signalTarget]);

  return (
    <div className="bg-[#111827] border-l border-[rgba(42,52,68,0.5)] overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1  border-[rgba(42,52,68,0.5)]">
        <span className="text-[8px] font-bold text-[#00D9FF] uppercase tracking-wider">
          {symbol || "CHART"} - Price Action
        </span>
        <div className="flex items-center gap-2 text-[7px] font-mono">
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00D9FF]" /> Entry
          </span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]" /> Target
          </span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#ef4444]" /> Stop
          </span>
        </div>
      </div>
      {!quotesData && symbol && (
        <div className="flex items-center justify-center py-12 text-[10px] text-[#64748b] font-mono">
          Loading candle data for {symbol}…
        </div>
      )}
      {!symbol && (
        <div className="flex items-center justify-center py-12 text-[10px] text-[#64748b] font-mono">
          Select a symbol from the table or score bars
        </div>
      )}
      <div ref={containerRef} className="w-full" style={{ minHeight: 260 }} />
    </div>
  );
};

// --- MINI EQUITY CURVE (SVG Sparkline) ---
const MiniEquityCurve = ({ points }) => {
  if (!points || points.length < 2) {
    return (
      <div className="text-[8px] text-[#64748b] text-center py-4 font-mono">
        No equity data yet
      </div>
    );
  }
  const w = 280,
    h = 80,
    pad = 4;
  const values = points.map((p) => p.value ?? p.equity ?? 0);
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
          <span className="text-[#00D9FF] font-bold">
            {acc30 ? `${(acc30 * 100).toFixed(1)}%` : "\u2014"}
          </span>
        </div>
        <div>
          <span className="text-[#94a3b8]">90d Acc</span>
          <br />
          <span className="text-[#00D9FF] font-bold">
            {acc90 ? `${(acc90 * 100).toFixed(1)}%` : "\u2014"}
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
        <span className="text-[8px] font-bold text-[#00D9FF] uppercase tracking-wider">
          Sector Heatmap
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

export default function Dashboard() {
  // --- STATE ---
  const [activeSortKey, setActiveSortKey] = useState("Composite Score");
  const [selectedSymbol, setSelectedSymbol] = useState("SPY"); // default so Price Action chart loads
  const [activeTimeframe, setActiveTimeframe] = useState("1h");
  const [autoExec, setAutoExec] = useState(false);

  // --- API HOOKS (Real-time polling) ---
  // Intervals tuned to prevent request flooding (max ~2 req/s combined)
  const {
    data: signalsData,
    loading: sigLoading,
    error: sigErr,
  } = useApi("signals", { pollIntervalMs: 15000 });
  const { data: kellyData } = useApi("kellyRanked", { pollIntervalMs: 30000 });
  const { data: portfolioData } = useApi("portfolio", { pollIntervalMs: 15000 });
  const { data: indicesData } = useApi("marketIndices", {
    pollIntervalMs: 15000,
  });
  const { data: openclawData } = useApi("openclaw", { pollIntervalMs: 30000 });
  const { data: performanceData } = useApi("performance", {
    pollIntervalMs: 60000,
  });
  const { data: agentsData } = useApi("agents", { pollIntervalMs: 30000 });
  const { data: riskScoreData } = useApi("riskScore", {
    pollIntervalMs: 30000,
  });
  const { data: alertsData } = useApi("systemAlerts", {
    pollIntervalMs: 30000,
  });
  const { data: flywheelData } = useApi("flywheel", { pollIntervalMs: 60000 });
  const { data: sentimentData } = useApi("sentiment", {
    pollIntervalMs: 30000,
  });

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
    pollIntervalMs: 10000,
    enabled: !!selectedSymbol,
  });
  const { data: candleData } = useApi("quotes", {
    endpoint: `/quotes/${selectedSymbol}/candles?timeframe=${activeTimeframe}`,
    pollIntervalMs: 30000,
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
      try {
        const side = action === "BUY" ? "buy" : "sell";
        const qty = String(riskData?.proposal?.proposedSize || 100);
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
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        alert(`Execution successful: ${action} ${selectedSymbol}`);
      } catch (err) {
        log.error("Execution failed:", err);
      }
    },
    [selectedSymbol, riskData],
  );

  // --- ACTION HANDLERS ---
  const handleRunScan = useCallback(async () => {
    try {
      const res = await fetch(getApiUrl("signals"), { method: "POST", headers: getAuthHeaders() });
      if (!res.ok) log.error("Scan failed:", res.status);
    } catch (e) {
      log.error(e);
    }
  }, []);
  const handleExecTop5 = useCallback(async () => {
    const top5 = processedSignals.slice(0, 5);
    for (const sig of top5) {
      try {
        await fetch(getApiUrl("orders/advanced"), {
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
      } catch (e) {
        log.error(e);
      }
    }
  }, [processedSignals]);
  const handleFlatten = useCallback(async () => {
    try {
      const res = await fetch(getApiUrl("orders") + "/flatten-all", { method: "POST", headers: getAuthHeaders() });
      if (!res.ok) log.error("Flatten failed:", res.status);
    } catch (e) {
      log.error(e);
    }
  }, []);
  const handleEmergencyStop = useCallback(async () => {
    try {
      const res = await fetch(getApiUrl("orders") + "/emergency-stop", { method: "POST", headers: getAuthHeaders() });
      if (!res.ok) log.error("Emergency stop failed:", res.status);
    } catch (e) {
      log.error(e);
    }
  }, []);

  const handleExportCSV = useCallback(() => {
    const data = processedSignals;
    if (!data.length) return;
    const headers = ["symbol","direction","score","entry","target","stop","rMultiple","kellyPercent"];
    const rows = data.map(s => headers.map(h => `"${s[h] ?? ""}"`).join(","));
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "signals.csv"; a.click();
    URL.revokeObjectURL(url);
  }, [processedSignals]);

  const handleSpawnAgent = useCallback(() => {
    window.location.href = "/agents";
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
    return {
      ...p,
      sharpe: p.sharpe ?? p.sharpeRatio ?? 0,
      alpha: p.alpha ?? 0,
      winRate: p.winRate ?? p.win_rate ?? 0,
      maxDrawdown: p.maxDrawdown ?? p.max_drawdown ?? 0,
      equityCurve: p.equityCurve || [],
    };
  }, [performanceData]);
  const techs = techsData?.technicals || techsData || {};
  const swarm = swarmData?.swarmTopology || swarmData || {};
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
      <div className="h-screen w-full bg-[#0B0E14] flex items-center justify-center text-[#00D9FF] font-mono text-xs">
        INITIALIZING EMBODIER NEURAL NET...
      </div>
    );
  /* sigErr no longer blocks the entire page — we show a banner instead
     so that non-signal panels (portfolio, risk, etc.) remain usable. */

  return (
    <div className="flex flex-col h-screen w-full bg-[#0B0E14] text-[#e5e7eb] font-sans text-[9px] leading-tight overflow-hidden selection:bg-[#00D9FF]/30">
      {/* 0. SCROLLING TICKER STRIP */}
      <TickerStrip indices={indices} signals={processedSignals} />

      {/* Signal-error banner (non-blocking) */}
      {sigErr && (
        <div className="mx-4 mt-2 px-3 py-1.5 rounded bg-red-500/10 border border-red-500/30 text-red-400 text-[10px] font-mono flex items-center gap-2 shrink-0">
          <span className="font-bold">SIGNAL API OFFLINE</span>
          <span className="text-red-400/70">{sigErr.message}</span>
        </div>
      )}

      {/* CNS VITALS — homeostasis, circuit breaker, agent health, verdict */}
      <div className="px-4 pt-2 shrink-0">
        <CNSVitals />
      </div>

      {/* PROFIT BRAIN — win rate, PnL, brain weights, feedback loop */}
      <ProfitBrainBar />

      {/* 1. TOP HEADER BAR */}
      <header className="flex items-center justify-between px-4 py-2 border-b border-[rgba(42,52,68,0.5)] bg-[#111827] shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 pr-4 border-r border-[rgba(42,52,68,0.5)]">
            <HexagonLogo />
            <h1 className="text-xs font-bold text-white tracking-widest">
              EMBODIER TRADER
            </h1>
          </div>
          {/* Regime Badges */}
          <div
            className={`px-2 py-0.5 rounded font-bold tracking-wider ${openclaw.regime === "BEAR" ? "bg-red-500/20 text-red-400 border border-red-500/50" : "bg-green-500/20 text-green-400 border border-green-500/50"}`}
          >
            {openclaw.regime || "\u2014"}
          </div>
          <div className="flex items-center gap-1">
            <span className="text-[#94a3b8]">SCORE</span>
            <div className="w-6 h-6 rounded-full border-2 border-green-400 flex items-center justify-center text-[10px] font-mono text-green-400">
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
        </div>
        {/* KPIs */}
        <div className="flex items-center gap-4 font-mono text-[10px]">
          <div className="flex gap-3 text-[#94a3b8]">
            <span>
              SPX{" "}
              <span className="text-green-400">
                +{indices.SPX?.change || "\u2014"}%
              </span>
            </span>
            <span>
              NDAQ{" "}
              <span className="text-red-400">
                {indices.NDAQ?.change || "\u2014"}%
              </span>
            </span>
            <span>
              BTC{" "}
              <span className="text-green-400">
                +{indices.BTC?.change || "\u2014"}%
              </span>
            </span>
          </div>
          <div className="w-px h-4 bg-[#1e293b]"></div>
          <div className="flex gap-4">
            <span>
              Equity{" "}
              <span className="text-white">
                ${Number(portfolio.totalEquity ?? 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
              </span>
            </span>
            <span>
              P&L{" "}
              <span className={Number(portfolio.dayPnL ?? 0) >= 0 ? "text-green-400" : "text-red-400"}>
                {Number(portfolio.dayPnL ?? 0) >= 0 ? "+" : ""}${Number(portfolio.dayPnL ?? 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
              </span>
            </span>
            <span>
              Deployed{" "}
              <span className="text-[#00D9FF]">
                {Number(portfolio.deployedPercent ?? 0).toFixed(1)}%
              </span>
            </span>
            <span>
              Sharpe{" "}
              <span className="text-[#00D9FF]">
                {performance.sharpe != null && performance.sharpe !== "" ? Number(performance.sharpe) : "0"}
              </span>
            </span>
            <span>
              Alpha{" "}
              <span className="text-green-400">
                +{performance.alpha != null && performance.alpha !== "" ? Number(performance.alpha) : "0"}%
              </span>
            </span>
            <span>
              Win{" "}
              <span className="text-green-400">
                {performance.winRate != null && performance.winRate !== "" ? Number(performance.winRate) : "0"}%
              </span>
            </span>
            <span>
              MaxDD{" "}
              <span className="text-red-400">
                {performance.maxDrawdown != null && performance.maxDrawdown !== "" ? Number(performance.maxDrawdown) : "0"}%
              </span>
            </span>
          </div>
        </div>
      </header>

      {/* MAIN CONTENT AREA */}
      <main className="flex flex-1 overflow-hidden">
        {/* CENTER COLUMN: BAR CHART + TABLE (~65%) */}
        <section className="flex flex-col w-[65%] border-r border-[rgba(42,52,68,0.5)] bg-[#0B0E14]">
          {/* Filters & Sort Bar */}
          <div className="flex flex-col border-b border-[rgba(42,52,68,0.5)] bg-[#111827] p-2 gap-2 shrink-0">
            <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-1">
              {SORT_PILLS.map((pill) => (
                <button
                  key={pill}
                  onClick={() => setActiveSortKey(pill)}
                  className={`whitespace-nowrap px-2 py-1 rounded-sm border ${activeSortKey === pill ? "bg-[#00D9FF]/20 text-[#00D9FF] border-[#00D9FF]/50" : "bg-transparent text-[#94a3b8] border-[#374151] hover:border-[#64748b]"} transition-colors`}
                >
                  {pill}
                </button>
              ))}
            </div>
            <div className="flex items-center justify-between text-[#94a3b8] font-mono">
              <div className="flex items-center gap-1">
                <span>TF:</span>
                {TIMEFRAMES.map((tf) => (
                  <button
                    key={tf}
                    onClick={() => setActiveTimeframe(tf)}
                    className={`px-1.5 py-0.5 rounded-sm ${activeTimeframe === tf ? "bg-[#1e293b] text-white" : "hover:bg-[#1e293b]/50"}`}
                  >
                    {tf}
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setAutoExec(!autoExec)}
                  className="flex items-center gap-1 cursor-pointer hover:text-white transition-colors"
                >
                  <div
                    className={`w-1.5 h-1.5 rounded-full ${autoExec ? "bg-green-500 animate-pulse" : "bg-red-500"}`}
                  ></div>
                  Auto-Exec: {autoExec ? "ON" : "OFF"}
                </button>
                <span className="flex items-center gap-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></div>{" "}
                  LIVE
                </span>
                <span>Flywheel: {flywheel.accuracy ?? (flywheel.accuracy30d != null ? Math.round(Number(flywheel.accuracy30d) * 100) : 0)}%</span>
              </div>
            </div>
          </div>

          {/* SIGNAL BAR CHART (NEW - from mockup) */}
          <div className="shrink-0 border-b border-[rgba(42,52,68,0.5)]">
            <SignalBarChart
              signals={processedSignals}
              selectedSymbol={selectedSymbol}
              onSelect={setSelectedSymbol}
            />
          </div>

          {/* MAIN LIGHTWEIGHT CHART */}
          <div className="shrink-0 border-b border-[rgba(42,52,68,0.5)]">
            <LWChartFallback
              symbol={selectedSymbol}
              quotesData={candleData}
              signalEntry={selectedSignal?.entry}
              signalStop={selectedSignal?.stop}
              signalTarget={selectedSignal?.target}
            />
          </div>

          {/* Table Container */}
          <div className="flex-1 overflow-auto bg-[#0B0E14]">
            <table className="w-full text-left font-mono whitespace-nowrap">
              <thead className="sticky top-0 bg-[#111827] text-[#64748b] border-b border-[rgba(42,52,68,0.5)] shadow-md z-10">
                <tr>
                  <th className="p-1.5 font-normal">Sym</th>
                  <th className="p-1.5 font-normal">Dir</th>
                  <th className="p-1.5 font-normal">Score</th>
                  <th className="p-1.5 font-normal">Regime</th>
                  <th className="p-1.5 font-normal">ML</th>
                  <th className="p-1.5 font-normal">Sent</th>
                  <th className="p-1.5 font-normal">Tech</th>
                  <th className="p-1.5 font-normal">Agent</th>
                  <th className="p-1.5 font-normal">Swarm</th>
                  <th className="p-1.5 font-normal">SHAP</th>
                  <th className="p-1.5 font-normal">Kelly</th>
                  <th className="p-1.5 font-normal">Entry</th>
                  <th className="p-1.5 font-normal">Tgt</th>
                  <th className="p-1.5 font-normal">Stop</th>
                  <th className="p-1.5 font-normal">R-Mult</th>
                  <th className="p-1.5 font-normal">P&L</th>
                  <th className="p-1.5 font-normal">Sec</th>
                  <th className="p-1.5 font-normal">Mom</th>
                  <th className="p-1.5 font-normal">Vol</th>
                  <th className="p-1.5 font-normal">News</th>
                  <th className="p-1.5 font-normal">Pat</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e293b]/50">
                {processedSignals.map((sig, idx) => {
                  const isSelected = selectedSymbol === sig.symbol;
                  const isLong = sig.direction === "LONG";
                  const dirColor = isLong ? "text-green-400" : "text-red-400";
                  return (
                    <tr
                      key={sig.symbol + idx}
                      onClick={() => setSelectedSymbol(sig.symbol)}
                      className={`cursor-pointer hover:bg-[#1e293b]/30 transition-colors ${isSelected ? "bg-[#164e63]/30 border-l-2 border-[#00D9FF]" : "border-l-2 border-transparent"}`}
                    >
                      <td className="p-1.5 text-white font-bold">
                        {sig.symbol}
                      </td>
                      <td className={`p-1.5 ${dirColor}`}>
                        {isLong ? "L" : "S"}
                      </td>
                      <td className="p-1.5">
                        <div className="flex items-center gap-1">
                          <span
                            className={
                              sig.score >= 90
                                ? "text-green-400"
                                : "text-[#00D9FF]"
                            }
                          >
                            {sig.score}
                          </span>
                          <div className="w-12 h-1.5 bg-[#1e293b] rounded-full overflow-hidden">
                            <div
                              className="h-full bg-[#00D9FF]"
                              style={{ width: `${sig.score}%` }}
                            ></div>
                          </div>
                        </div>
                      </td>
                      <td className="p-1.5 text-[#94a3b8]">
                        {sig.scores?.regime || "\u2014"}
                      </td>
                      <td className="p-1.5 text-[#94a3b8]">
                        {sig.scores?.ml || "\u2014"}
                      </td>
                      <td className="p-1.5 text-[#94a3b8]">
                        {sig.scores?.sentiment || "\u2014"}
                      </td>
                      <td className="p-1.5 text-[#94a3b8]">
                        {sig.scores?.technical || "\u2014"}
                      </td>
                      <td className="p-1.5 text-[#00D9FF] truncate max-w-[80px]">
                        {sig.leadAgent || "\u2014"}
                      </td>
                      <td className="p-1.5 text-[#94a3b8]">
                        {sig.swarmVote || "\u2014"}
                      </td>
                      <td className="p-1.5 text-[#64748b] truncate max-w-[60px]">
                        {sig.topShap || "\u2014"}
                      </td>
                      <td className="p-1.5 text-[#00D9FF]">
                        {sig.kellyPercent ?? 0}%
                      </td>
                      <td className="p-1.5 text-[#94a3b8]">
                        {sig.entry != null ? `$${Number(sig.entry).toFixed(2)}` : "\u2014"}
                      </td>
                      <td className="p-1.5 text-green-400">
                        {sig.target != null ? `$${Number(sig.target).toFixed(2)}` : "\u2014"}
                      </td>
                      <td className="p-1.5 text-red-400">
                        {sig.stop != null ? `$${Number(sig.stop).toFixed(2)}` : "\u2014"}
                      </td>
                      <td className="p-1.5 text-white">
                        {sig.rMultiple != null ? `${Number(sig.rMultiple).toFixed(1)}:1` : "\u2014"}
                      </td>
                      <td className="p-1.5 text-green-400">
                        {sig.expPnL != null ? `+$${Number(sig.expPnL).toLocaleString()}` : "\u2014"}
                      </td>
                      <td className="p-1.5 text-[#64748b]">
                        {sig.sector?.substring(0, 3) || "\u2014"}
                      </td>
                      <td className="p-1.5 text-green-400">
                        +{sig.momentum || "\u2014"}
                      </td>
                      <td className="p-1.5 text-[#00D9FF]">
                        {sig.volSpike || "\u2014"}x
                      </td>
                      <td className="p-1.5 text-[#64748b] truncate max-w-[50px]">
                        {sig.newsImpact || "\u2014"}
                      </td>
                      <td className="p-1.5 text-[#00D9FF] truncate max-w-[60px]">
                        {sig.pattern || "\u2014"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Alerts Bar */}
          {Array.isArray(alerts) && alerts.length > 0 && (
            <div className="bg-amber-900/30 border-t border-amber-500/50 px-3 py-1 shrink-0 overflow-x-auto no-scrollbar">
              <div className="flex items-center gap-4 text-[8px] font-mono text-amber-400">
                <span className="font-bold">ALERTS:</span>
                {alerts.slice(0, 5).map((a, i) => (
                  <span key={i} className="whitespace-nowrap">
                    {a.message || a.msg || a}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* BOTTOM HEATMAP GRID */}
          <div className="shrink-0">
            <HeatmapGrid signals={processedSignals} />
          </div>
        </section>

        {/* RIGHT COLUMN: ALWAYS-VISIBLE SUMMARY CARDS (~35%) */}
        <section className="flex flex-col w-[35%] bg-[#111827] overflow-y-auto custom-scrollbar p-3 space-y-3">
          {/* TOP ROW: Regime Donut + Agent Consensus */}
          <div className="flex gap-3">
            {/* Regime Donut Ring (NEW) */}
            <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-2 flex flex-col items-center justify-center hover:shadow-[0_0_20px_rgba(0,217,255,0.12)] transition-shadow">
              <span className="text-[8px] text-[#94a3b8] uppercase tracking-wider mb-1">
                REGIME
              </span>
              <RegimeDonut
                regime={openclaw.regime}
                score={openclaw.compositeScore}
              />
            </div>
            {/* Top Trades Donut (from mockup 02) */}
            <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-2 flex flex-col items-center justify-center hover:shadow-[0_0_20px_rgba(0,217,255,0.12)] transition-shadow">
              <span className="text-[8px] text-[#94a3b8] uppercase tracking-wider mb-1">
                TOP TRADES
              </span>
              <TopTradesDonut
                buyCount={
                  swarm.buyCount ||
                  processedSignals.filter((s) => s.direction === "LONG").length
                }
                sellCount={
                  swarm.sellCount ||
                  processedSignals.filter((s) => s.direction === "SHORT").length
                }
                holdCount={
                  swarm.holdCount ||
                  Math.max(
                    1,
                    processedSignals.length -
                      processedSignals.filter((s) => s.direction === "LONG")
                        .length -
                      processedSignals.filter((s) => s.direction === "SHORT")
                        .length,
                  )
                }
              />
            </div>
            {/* Agent Consensus Ring (Enhanced) */}
            <div className="flex-1 bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-2 hover:shadow-[0_0_20px_rgba(0,217,255,0.12)] transition-shadow">
              <h3 className="text-[9px] text-[#00D9FF] font-bold uppercase tracking-wider mb-1">
                Agent Consensus
              </h3>
              <AgentConsensusRing
                buyPct={
                  swarm.buyCount ||
                  processedSignals.filter((s) => s.direction === "LONG").length
                }
                sellPct={
                  swarm.sellCount ||
                  processedSignals.filter((s) => s.direction === "SHORT").length
                }
                holdPct={
                  swarm.holdCount ||
                  Math.max(
                    1,
                    processedSignals.length -
                      processedSignals.filter((s) => s.direction === "LONG")
                        .length -
                      processedSignals.filter((s) => s.direction === "SHORT")
                        .length,
                  )
                }
                consensus={
                  swarm.consensus || openclaw.compositeScore || "\u2014"
                }
              />
            </div>
          </div>

          {/* Swarm Consensus Horizontal Bars (NEW - from mockup) */}
          <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-2 space-y-1.5 hover:shadow-[0_0_20px_rgba(0,217,255,0.12)] transition-shadow">
            <h3 className="text-[9px] text-[#00D9FF] font-bold uppercase tracking-wider">
              Swarm Consensus
            </h3>
            {(swarm.agents || []).slice(0, 6).map((agent, i) => (
              <ConsensusBar
                key={i}
                label={agent.name || `Agent ${i + 1}`}
                buyPct={
                  agent.vote === "BUY"
                    ? agent.confidence || 50
                    : 100 - (agent.confidence || 50)
                }
                sellPct={agent.vote === "SELL" ? agent.confidence || 50 : 0}
              />
            ))}
            {(!swarm.agents || swarm.agents.length === 0) && (
              <>
                <ConsensusBar label="Insight" buyPct={72} sellPct={28} />
                <ConsensusBar label="Scout" buyPct={65} sellPct={35} />
                <ConsensusBar label="Sentinel" buyPct={80} sellPct={20} />
                <ConsensusBar label="Analyst" buyPct={55} sellPct={45} />
              </>
            )}
          </div>

          {/* Macro & Pattern Triggers Card (always visible) */}
          <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-2 hover:shadow-[0_0_20px_rgba(0,217,255,0.12)] transition-shadow">
            <h3 className="text-[9px] text-[#00D9FF] font-bold uppercase tracking-wider mb-2">
              Macro & Pattern Triggers
            </h3>
            <div className="grid grid-cols-2 gap-1 font-mono text-[8px]">
              <div>
                <span className="text-[#94a3b8]">Market Breadth:</span>{" "}
                <span className="text-green-400">
                  +{indices.SPX?.breadth || "\u2014"}%
                </span>
              </div>
              <div>
                <span className="text-[#94a3b8]">VIX Level:</span>{" "}
                <span className="text-[#f59e0b]">
                  {indices.VIX?.value || "\u2014"}
                </span>
              </div>
              <div>
                <span className="text-[#94a3b8]">Sector Lead:</span>{" "}
                <span className="text-[#00D9FF]">
                  {indices.sectorLead || "\u2014"}
                </span>
              </div>
              <div>
                <span className="text-[#94a3b8]">Pattern:</span>{" "}
                <span className="text-green-400">
                  {selectedSignal?.pattern || "\u2014"}
                </span>
              </div>
            </div>
          </div>

          {/* Risk Shield Status Card (always visible) */}
          <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-2 hover:shadow-[0_0_20px_rgba(0,217,255,0.12)] transition-shadow">
            <h3 className="text-[9px] text-[#00D9FF] font-bold uppercase tracking-wider mb-2">
              Risk Shield {riskScore.status || "(Active)"}
            </h3>
            <div className="grid grid-cols-2 gap-1 font-mono text-[8px]">
              <div>
                <span className="text-[#94a3b8]">Daily VaR:</span>{" "}
                <span className="text-red-400">
                  {riskScore.dailyVaR != null && riskScore.dailyVaR !== "" ? riskScore.dailyVaR : "0"}%
                </span>
              </div>
              <div>
                <span className="text-[#94a3b8]">Max Drawdown:</span>{" "}
                <span className="text-red-400">
                  {performance.maxDrawdown != null && performance.maxDrawdown !== "" ? performance.maxDrawdown : "0"}%
                </span>
              </div>
              <div>
                <span className="text-[#94a3b8]">Correlation:</span>{" "}
                <span className="text-[#00D9FF]">
                  {riskScore.correlation != null && riskScore.correlation !== "" ? riskScore.correlation : "0"}
                </span>
              </div>
              <div>
                <span className="text-[#94a3b8]">Position Limit:</span>{" "}
                <span className="text-white">
                  {riskScore.positionLimit != null && riskScore.positionLimit !== "" ? riskScore.positionLimit : "—"}
                </span>
              </div>
            </div>
            <div className="flex gap-1.5 mt-2">
              <button className="flex-1 bg-green-900/50 text-green-400 py-1 rounded text-[8px] font-bold border border-green-800">
                APPROVE RISK
              </button>
              <button className="flex-1 bg-red-900/50 text-red-400 py-1 rounded text-[8px] font-bold border border-red-800">
                HALT SYSTEM
              </button>
            </div>
          </div>

          {/* Equity Curve Chart */}
          <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-2 hover:shadow-[0_0_20px_rgba(0,217,255,0.12)] transition-shadow">
            <h3 className="text-[9px] text-[#00D9FF] font-bold uppercase tracking-wider mb-1">
              Equity Curve
            </h3>
            <MiniEquityCurve points={performance.equityCurve} />
          </div>

          {/* Flywheel Status Pipeline */}
          <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-2 hover:shadow-[0_0_20px_rgba(0,217,255,0.12)] transition-shadow">
            <h3 className="text-[9px] text-[#00D9FF] font-bold uppercase tracking-wider mb-2">
              ML Flywheel
            </h3>
            <FlywheelPipeline flywheel={flywheel} />
          </div>

          {/* SELECTED SYMBOL DETAIL (conditionally expanded) */}
          {selectedSignal && (
            <>
              {/* Header */}
              <div className="flex justify-between items-center pb-2 border-b border-[rgba(42,52,68,0.5)]">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  {selectedSignal.symbol}
                  <span
                    className={
                      selectedSignal.direction === "LONG"
                        ? "text-green-400"
                        : "text-red-400"
                    }
                  >
                    {selectedSignal.direction || "LONG"}
                  </span>
                </h2>
                <div className="flex flex-col items-end">
                  <span className="text-[8px] text-[#94a3b8] uppercase">
                    Composite Score
                  </span>
                  <span className="text-2xl font-mono font-bold text-[#00D9FF]">
                    {selectedSignal.score || "\u2014"}
                  </span>
                </div>
              </div>

              {/* Composite Breakdown */}
              <div className="space-y-1.5">
                <h3 className="text-[9px] text-[#00D9FF] font-bold uppercase tracking-wider">
                  Composite Breakdown
                </h3>
                <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-2 space-y-1 font-mono text-[8px]">
                  {[
                    {
                      label: "Overall Score",
                      val: `${selectedSignal.score || 0}/100`,
                      pct: selectedSignal.score || 0,
                    },
                    {
                      label: "Technical Rank",
                      val: `${selectedSignal.scores?.technical || "\u2014"}`,
                      pct: selectedSignal.scores?.technical || 0,
                    },
                    {
                      label: "ML Probability",
                      val: `${selectedSignal.scores?.ml || "\u2014"}%`,
                      pct: selectedSignal.scores?.ml || 0,
                    },
                    {
                      label: "Sentiment Pulse",
                      val: `${selectedSignal.scores?.sentiment || "\u2014"}`,
                      pct: selectedSignal.scores?.sentiment || 0,
                    },
                    {
                      label: "Swarm Consensus",
                      val: `${swarm.consensus || "\u2014"}%`,
                      pct: swarm.consensus || 0,
                    },
                  ].map((item) => (
                    <div
                      key={item.label}
                      className="flex items-center justify-between"
                    >
                      <span className="text-[#94a3b8] w-24">{item.label}</span>
                      <div className="flex-1 mx-2 h-1 bg-[#1e293b] rounded-full">
                        <div
                          className="h-full bg-[#00D9FF] rounded-full"
                          style={{ width: `${item.pct}%` }}
                        ></div>
                      </div>
                      <span className="text-white w-10 text-right">
                        {item.val}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Technical Analysis */}
              <div className="space-y-1.5">
                <h3 className="text-[9px] text-[#00D9FF] font-bold uppercase tracking-wider">
                  Technical Analysis
                </h3>
                <div className="grid grid-cols-2 gap-1.5 bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-2 font-mono text-[8px]">
                  <div>
                    <span className="text-[#94a3b8]">RSI:</span>{" "}
                    <span className="text-green-400">
                      {techs.rsi || "\u2014"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[#94a3b8]">MACD:</span>{" "}
                    <span className="text-green-400">
                      {techs.macd || "\u2014"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[#94a3b8]">BB:</span>{" "}
                    <span className="text-white">{techs.bb || "\u2014"}</span>
                  </div>
                  <div>
                    <span className="text-[#94a3b8]">VWAP:</span>{" "}
                    <span className="text-[#00D9FF]">
                      {techs.vwap || "\u2014"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[#94a3b8]">20 EMA:</span>{" "}
                    <span className="text-white">
                      {techs.ema20 || "\u2014"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[#94a3b8]">50 SMA:</span>{" "}
                    <span className="text-green-400">
                      {techs.sma50 || "\u2014"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[#94a3b8]">ADX:</span>{" "}
                    <span className="text-white">{techs.adx || "\u2014"}</span>
                  </div>
                  <div>
                    <span className="text-[#94a3b8]">Stoch:</span>{" "}
                    <span className="text-green-400">
                      {techs.stoch || "\u2014"}
                    </span>
                  </div>
                </div>
              </div>

              {/* ML Engine & SHAP */}
              <div className="space-y-1.5">
                <h3 className="text-[9px] text-[#00D9FF] font-bold uppercase tracking-wider">
                  ML Engine & SHAP Drivers
                </h3>
                <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-2 font-mono text-[8px]">
                  <div className="flex justify-between mb-2 pb-2 border-b border-[rgba(42,52,68,0.5)]">
                    <span className="text-[#94a3b8]">
                      Probability LONG:{" "}
                      <span className="text-green-400 font-bold">
                        {selectedSignal.scores?.ml || "\u2014"}%
                      </span>
                    </span>
                    <span className="text-[#94a3b8]">
                      Drift Score:{" "}
                      <span className="text-green-400">
                        {techs.driftScore || "\u2014"}
                      </span>
                    </span>
                  </div>
                  <div className="space-y-1">
                    <div className="flex justify-between text-[#94a3b8] mb-1">
                      <span>Feature</span>
                      <span>Impact</span>
                    </div>
                    {(techs.shapFeatures || selectedSignal.shapFeatures || [])
                      .slice(0, 5)
                      .map((s) => {
                        const imp = Number(s.impact) || 0;
                        const barW = Math.min(Math.abs(imp) * 500, 100);
                        return (
                        <div
                          key={s.feature}
                          className="flex items-center justify-between"
                        >
                          <span className="text-white truncate w-24">
                            {s.feature}
                          </span>
                          <div className="flex-1 flex items-center mx-2">
                            {imp < 0 ? (
                              <div className="w-1/2 flex justify-end">
                                <div
                                  className="h-1.5 bg-red-500"
                                  style={{ width: `${barW}%` }}
                                ></div>
                              </div>
                            ) : (
                              <div className="w-1/2"></div>
                            )}
                            {imp > 0 && (
                              <div className="w-1/2">
                                <div
                                  className="h-1.5 bg-green-500"
                                  style={{ width: `${barW}%` }}
                                ></div>
                              </div>
                            )}
                          </div>
                          <span
                            className={
                              imp > 0
                                ? "text-green-400 w-8 text-right"
                                : "text-red-400 w-8 text-right"
                            }
                          >
                            {imp > 0 ? `+${imp.toFixed(2)}` : imp.toFixed(2)}
                          </span>
                        </div>
                        );
                      })}
                  </div>
                </div>
              </div>

              {/* Risk & Order Proposal */}
              <div className="space-y-1.5">
                <h3 className="text-[9px] text-[#00D9FF] font-bold uppercase tracking-wider">
                  Risk & Order Proposal
                </h3>
                <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-2 font-mono text-[8px]">
                  <div className="text-[#00D9FF] mb-1 font-bold">
                    PROPOSED ENTRY
                  </div>
                  <div className="grid grid-cols-2 gap-1 mb-2 pb-2 border-b border-[rgba(42,52,68,0.5)]/50">
                    <span className="text-[#94a3b8]">
                      Action:{" "}
                      <span className="text-white">
                        Limit Buy {risk.limitPrice || "\u2014"}
                      </span>
                    </span>
                    <span className="text-[#94a3b8]">
                      Size:{" "}
                      <span className="text-white">
                        {risk.shares || "\u2014"} shs ($
                        {risk.notional || "\u2014"})
                      </span>
                    </span>
                    <span className="text-[#94a3b8]">
                      Stop Loss:{" "}
                      <span className="text-red-400">
                        {risk.stopLoss || "\u2014"}
                      </span>
                    </span>
                    <span className="text-[#94a3b8]">
                      Target 1:{" "}
                      <span className="text-green-400">
                        {risk.target1 || "\u2014"}
                      </span>
                    </span>
                    <span className="text-[#94a3b8]">
                      R:R Ratio:{" "}
                      <span className="text-[#00D9FF]">
                        {risk.rr || "\u2014"}
                      </span>
                    </span>
                    <span className="text-[#94a3b8]">
                      Sizing:{" "}
                      <span className="text-white">
                        Kelly {selectedSignal.kellyPercent ?? 0}%
                      </span>
                    </span>
                  </div>
                  {/* L2 Order Book */}
                  <div className="text-[#94a3b8] mb-1">
                    LIVE L2 ORDER BOOK (Spread: $
                    {quotes.spread != null ? Number(quotes.spread).toFixed(2) : "\u2014"})
                  </div>
                  <div className="flex flex-col gap-[1px]">
                    {quotes.asks
                      ?.slice(0, 3)
                      .reverse()
                      .map((ask, i) => (
                        <div
                          key={"ask" + i}
                          className="flex items-center text-[7px]"
                        >
                          <span className="w-10 text-red-400">{Number(ask.price).toFixed(2)}</span>
                          <span className="w-8 text-right mr-1">
                            {ask.size}
                          </span>
                          <div
                            className="h-1.5 bg-red-500/30"
                            style={{ width: `${Math.min((Number(ask.size) / 1500) * 100, 100)}%` }}
                          ></div>
                        </div>
                      )) || (
                      <div className="text-[#64748b] text-center py-1">
                        Awaiting L2 data...
                      </div>
                    )}
                    <div className="h-px bg-[#1e293b] my-0.5"></div>
                    {quotes.bids?.slice(0, 3).map((bid, i) => (
                      <div
                        key={"bid" + i}
                        className="flex items-center text-[7px]"
                      >
                        <span className="w-10 text-green-400">{Number(bid.price).toFixed(2)}</span>
                        <span className="w-8 text-right mr-1">{bid.size}</span>
                        <div
                          className="h-1.5 bg-green-500/30"
                          style={{ width: `${Math.min((Number(bid.size) / 1500) * 100, 100)}%` }}
                        ></div>
                      </div>
                    )) || (
                      <div className="text-[#64748b] text-center py-1">
                        Awaiting L2 data...
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Execution Controls */}
              <div className="pt-2">
                <div className="grid grid-cols-2 gap-1.5 mb-1.5">
                  <button
                    onClick={() => handleExecute("BUY")}
                    className="bg-green-600 hover:bg-green-500 text-white font-bold py-1.5 rounded shadow-[0_0_8px_rgba(16,185,129,0.4)]"
                  >
                    EXECUTE LONG
                  </button>
                  <button
                    onClick={() => handleExecute("SELL")}
                    className="bg-red-600 hover:bg-red-500 text-white font-bold py-1.5 rounded shadow-[0_0_8px_rgba(239,68,68,0.4)]"
                  >
                    EXECUTE SHORT
                  </button>
                </div>
                <div className="grid grid-cols-3 gap-1.5 mb-1.5">
                  <button className="bg-[#1e293b] hover:bg-cyan-900 text-[#00D9FF] py-1 rounded">
                    Limit Order
                  </button>
                  <button className="bg-[#1e293b] hover:bg-cyan-900 text-[#00D9FF] py-1 rounded">
                    Stop Limit
                  </button>
                  <button className="bg-[#1e293b] hover:bg-amber-900 text-[#f59e0b] py-1 rounded">
                    Modify Setup
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-1.5">
                  <button className="bg-blue-900/50 hover:bg-blue-800 text-blue-300 py-1 rounded border border-blue-800">
                    Paper Trade
                  </button>
                  <button className="bg-[#1e293b] hover:bg-[#374151] text-[#94a3b8] py-1 rounded">
                    Cancel / Reject
                  </button>
                </div>
              </div>
            </>
          )}
        </section>
      </main>

      {/* BOTTOM ACTION BAR */}
      <footer className="flex items-center justify-between px-3 py-1.5 bg-[#0B0E14] border-t border-[rgba(42,52,68,0.5)] shrink-0 font-mono text-[8px] text-[#94a3b8]">
        <div className="flex gap-2">
          <button
            onClick={handleRunScan}
            className="bg-[#1e293b] hover:bg-[#1e293b]/80 text-white px-2 py-0.5 rounded"
          >
            Run Scan [F5]
          </button>
          <button onClick={handleSpawnAgent} className="bg-[#1e293b] hover:bg-[#1e293b]/80 text-white px-2 py-0.5 rounded">
            Spawn [N]
          </button>
          <button onClick={handleExportCSV} className="bg-[#1e293b] hover:bg-[#1e293b]/80 text-white px-2 py-0.5 rounded">
            Export [F7]
          </button>
          <button
            onClick={handleExecTop5}
            className="bg-cyan-900 text-[#00D9FF] px-2 py-0.5 rounded"
          >
            Exec Top 5
          </button>
          <button
            onClick={handleFlatten}
            className="bg-amber-900 text-[#f59e0b] px-2 py-0.5 rounded"
          >
            Flatten
          </button>
          <button
            onClick={handleEmergencyStop}
            className="bg-red-900 text-red-400 px-2 py-0.5 rounded font-bold"
          >
            EMERGENCY STOP
          </button>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <div className="w-1.5 h-1.5 rounded-full bg-green-500"></div> WS
          </span>
          <span className="flex items-center gap-1">
            <div className="w-1.5 h-1.5 rounded-full bg-green-500"></div> API
          </span>
          <span>{agents.total || swarm.total || "\u2014"} Agents</span>
          <span>CPU {performance.cpu || "\u2014"}%</span>
          <span>GPU {performance.gpu || "\u2014"}%</span>
          <span>Uptime {performance.uptime || "\u2014"}</span>
        </div>
      </footer>

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
        @keyframes ticker-glow { 0%,100% { opacity: 0.7; } 50% { opacity: 1; } }
        .ticker-glow { animation: ticker-glow 2s ease-in-out infinite; }
      `,
        }}
      />
    </div>
  );
}
